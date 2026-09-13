# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
# Generado por AgentKit para MC Growth Agency — Agente Max

"""
Servidor principal del agente Max.
Funciona con cualquier proveedor (Whapi, Meta, Twilio) gracias a la capa de providers.
"""

import os
import json
import secrets
import hmac
import hashlib
import time
import csv
import io
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends, status, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import PlainTextResponse, HTMLResponse, RedirectResponse, StreamingResponse
from dotenv import load_dotenv

from agent.brain import generar_respuesta, extraer_info_lead
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial, registrar_lead, actualizar_info_lead, obtener_leads, obtener_conversacion, obtener_conversaciones, obtener_todos_los_mensajes, marcar_lead_cerrado, marcar_lead_descartado, cambiar_estado_lead
from agent.providers import obtener_proveedor
from agent.telegram import notificar_lead_calificado

load_dotenv()

# Configuración de logging según entorno
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("agentkit")

# Proveedor de WhatsApp (Whapi.cloud, configurado en .env)
proveedor = obtener_proveedor()
PORT = int(os.getenv("PORT", 8000))
BOT_ENABLED = True
security = HTTPBasic(auto_error=False)
SESSION_COOKIE = "mc_growth_session"


def _firma_sesion(timestamp: str) -> str:
    secreto = os.getenv("DASHBOARD_PASSWORD", "")
    return hmac.new(secreto.encode(), timestamp.encode(), hashlib.sha256).hexdigest()


def _sesion_valida(request: Request) -> bool:
    cookie = request.cookies.get(SESSION_COOKIE, "")
    try:
        timestamp, firma = cookie.split(".", 1)
        vigente = time.time() - int(timestamp) < 60 * 60 * 12
        return vigente and secrets.compare_digest(firma, _firma_sesion(timestamp))
    except (ValueError, TypeError):
        return False


def autenticar_dashboard(request: Request, credentials: HTTPBasicCredentials | None = Depends(security)):
    """Protege el dashboard sin exponer credenciales en el código."""
    usuario = os.getenv("DASHBOARD_USERNAME")
    clave = os.getenv("DASHBOARD_PASSWORD")
    if not usuario or not clave:
        raise HTTPException(status_code=503, detail="Dashboard no configurado: faltan credenciales")
    if _sesion_valida(request):
        return usuario
    usuario_ok = bool(credentials) and secrets.compare_digest(credentials.username, usuario)
    clave_ok = bool(credentials) and secrets.compare_digest(credentials.password, clave)
    if not (usuario_ok and clave_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar el servidor."""
    await inicializar_db()
    logger.info("Base de datos inicializada ✓")
    logger.info(f"Agente Max listo en puerto {PORT} ✓")
    logger.info(f"Proveedor WhatsApp: {proveedor.__class__.__name__} ✓")
    yield


app = FastAPI(
    title="Max — Agente IA de MC Growth Agency",
    description="Agente comercial para calificación de leads y agendamiento de auditorías",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def health_check():
    """Endpoint de salud para Railway y monitoreo."""
    return {
        "status": "ok",
        "agente": "Max",
        "negocio": "MC Growth Agency",
        "proveedor": proveedor.__class__.__name__
    }


@app.head("/")
async def health_check_head():
    """HEAD para UptimeRobot — responde 200 sin cuerpo."""
    return PlainTextResponse("", status_code=200)


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    """
    Verificación GET del webhook.
    Requerido por Meta Cloud API. No-op para Whapi.cloud.
    """
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    """
    Recibe mensajes de WhatsApp via Whapi.cloud.
    Procesa el mensaje, genera respuesta con Claude y la envía de vuelta.

    Flujo:
    1. Parsear webhook → normalizar mensaje
    2. Obtener historial de conversación
    3. Generar respuesta con Max (Claude)
    4. Guardar en memoria
    5. Enviar respuesta por WhatsApp
    """
    try:
        if not BOT_ENABLED:
            return {"status": "paused"}
        # Parsear el webhook — el proveedor normaliza el formato
        mensajes = await proveedor.parsear_webhook(request)

        for msg in mensajes:
            # Ignorar mensajes propios del agente o vacíos
            if msg.es_propio or not msg.texto:
                continue

            logger.info(f"Mensaje recibido de {msg.telefono}: {msg.texto[:80]}...")

            # Obtener historial ANTES de guardar el mensaje actual
            # (evita duplicados — brain.py agrega el mensaje al construir los mensajes)
            historial = await obtener_historial(msg.telefono)

            # Generar respuesta con Claude (Max)
            respuesta = await generar_respuesta(msg.texto, historial)

            # Guardar mensaje del prospecto y respuesta de Max en memoria
            await guardar_mensaje(msg.telefono, "user", msg.texto)
            await guardar_mensaje(msg.telefono, "assistant", respuesta)

            # Enviar respuesta por WhatsApp via el proveedor
            enviado = await proveedor.enviar_mensaje(msg.telefono, respuesta)

            if enviado:
                logger.info(f"Respuesta enviada a {msg.telefono} ✓")
            else:
                logger.warning(f"No se pudo enviar respuesta a {msg.telefono}")

            # Detectar si Max propuso la auditoría gratuita (lead calificado)
            respuesta_normalizada = respuesta.lower()
            LINK_AUDITORIA = "calendar.app.google"
            calificacion_explicita = (
                "calific" in respuesta_normalizada
                and "auditor" in respuesta_normalizada
                and "no calific" not in respuesta_normalizada
            )
            if LINK_AUDITORIA in respuesta_normalizada or calificacion_explicita:
                es_nuevo = await registrar_lead(msg.telefono)
                if es_nuevo:
                    # Obtener historial completo para extraer info estructurada
                    historial_completo = await obtener_historial(msg.telefono, limite=30)
                    # Extraer datos del lead con Claude Haiku
                    info = await extraer_info_lead(historial_completo)
                    await actualizar_info_lead(
                        msg.telefono,
                        nombre=info.get("nombre", "No indicó"),
                        rubro=info.get("rubro", "No indicó"),
                        presupuesto=info.get("presupuesto", "No indicó"),
                        interes=info.get("interes", "No indicó"),
                        sentiment_score=info.get("sentiment_score", 50),
                        sentiment_label=info.get("sentiment_label", "neutral"),
                        resumen=info.get("resumen", "No disponible"),
                    )
                    await notificar_lead_calificado(msg.telefono, info)
                    logger.info(f"Lead calificado notificado: {msg.telefono}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Dashboard de leads ──────────────────────────────────────────────────────

@app.get("/leads")
async def api_leads(_usuario: str = Depends(autenticar_dashboard)):
    """API: lista todos los leads calificados (para el dashboard o integraciones)."""
    leads = await obtener_leads()
    return {"leads": leads, "total": len(leads)}


@app.get("/leads/{telefono}/conversation")
async def api_conversacion(telefono: str, _usuario: str = Depends(autenticar_dashboard)):
    """API: devuelve todos los mensajes de la conversación del lead."""
    return {"telefono": telefono, "messages": await obtener_conversacion(telefono)}


@app.get("/conversaciones")
async def api_conversaciones(_usuario: str = Depends(autenticar_dashboard)):
    """API: todos los contactos que hablaron con Max, calificados o no."""
    return {"conversaciones": await obtener_conversaciones()}


def _csv_response(nombre: str, encabezados: list[str], filas: list[list]) -> StreamingResponse:
    """Genera CSV UTF-8 compatible con Excel y Google Sheets."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(encabezados)
    writer.writerows(filas)
    contenido = "\ufeff" + buffer.getvalue()
    return StreamingResponse(
        iter([contenido]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@app.get("/export/leads.csv")
async def exportar_leads_csv(_usuario: str = Depends(autenticar_dashboard)):
    """Exporta toda la base de leads sin eliminar ni modificar registros."""
    leads = await obtener_leads()
    filas = []
    for lead in leads:
        estado = "cerrado" if lead["cerrado"] else "descartado" if lead["descartado"] else "seguimiento"
        filas.append([
            lead["telefono"], lead["nombre"], lead["rubro"], lead["presupuesto"],
            lead["interes"], lead["sentiment_score"], lead["sentiment_label"],
            lead["resumen"], estado, lead["timestamp"],
        ])
    return _csv_response(
        "mc-growth-leads.csv",
        ["telefono", "nombre", "rubro", "presupuesto", "interes", "sentiment_score", "sentiment_label", "resumen", "estado", "fecha"],
        filas,
    )


@app.get("/export/conversaciones.csv")
async def exportar_conversaciones_csv(_usuario: str = Depends(autenticar_dashboard)):
    """Exporta todos los mensajes para respaldo y auditoría."""
    mensajes = await obtener_todos_los_mensajes()
    return _csv_response(
        "mc-growth-conversaciones.csv",
        ["telefono", "role", "mensaje", "fecha"],
        [[m["telefono"], m["role"], m["content"], m["timestamp"]] for m in mensajes],
    )


@app.post("/leads/{telefono}/cerrar")
async def cerrar_lead(telefono: str, _usuario: str = Depends(autenticar_dashboard)):
    """API: marca un lead como cerrado (cliente ganado)."""
    ok = await marcar_lead_cerrado(telefono)
    if not ok:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    return {"status": "ok", "mensaje": f"Lead {telefono} marcado como cerrado"}


@app.post("/leads/{telefono}/descartar")
async def descartar_lead(telefono: str, _usuario: str = Depends(autenticar_dashboard)):
    """API: marca un lead como descartado (no avanzó)."""
    ok = await marcar_lead_descartado(telefono)
    if not ok:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    return {"status": "ok", "mensaje": f"Lead {telefono} marcado como descartado"}


@app.post("/leads/{telefono}/estado")
async def cambiar_estado(telefono: str, request: Request, _usuario: str = Depends(autenticar_dashboard)):
    datos = await request.json()
    estado = datos.get("estado", "seguimiento")
    if not await cambiar_estado_lead(telefono, estado):
        raise HTTPException(status_code=400, detail="Estado o lead inválido")
    return {"status": "ok", "estado": estado}


@app.get("/api/channels")
async def api_channels(_usuario: str = Depends(autenticar_dashboard)):
    return {"bot_enabled": BOT_ENABLED, "channels": [
        {"id": "whatsapp", "name": "WhatsApp", "status": "connected" if proveedor.__class__.__name__ == "ProveedorMeta" else "backup", "available": True},
        {"id": "instagram", "name": "Instagram", "status": "not_configured", "available": False},
        {"id": "facebook", "name": "Facebook Messenger", "status": "not_configured", "available": False},
        {"id": "linkedin", "name": "LinkedIn", "status": "not_configured", "available": False},
    ]}


@app.post("/api/demo/seed")
async def seed_demo_data(_usuario: str = Depends(autenticar_dashboard)):
    """Crea leads ficticios para probar el dashboard. No usa datos reales."""
    demos = [
        ("5491100000001", "Lucía Demo", "Desarrolladora inmobiliaria", "USD 1.000/mes", "Más leads calificados para un lanzamiento", 84, "positivo", "Tiene campaña activa y busca mejorar la calidad de sus consultas.", "seguimiento"),
        ("5491100000002", "Tomás Demo", "Inmobiliaria", "USD 700/mes", "Automatizar la respuesta inicial", 67, "positivo", "Cuenta con equipo comercial y quiere implementar pronto.", "cerrado"),
        ("5491100000003", "Sofía Demo", "Estudio de arquitectura", "No indicó", "Landing de conversión", 48, "neutral", "Está explorando alternativas para más adelante.", "descartado"),
    ]
    creados = 0
    for telefono, nombre, rubro, presupuesto, interes, score, etiqueta, resumen, estado in demos:
        if await registrar_lead(telefono):
            await actualizar_info_lead(telefono, nombre, rubro, presupuesto, interes, score, etiqueta, resumen)
            await guardar_mensaje(telefono, "user", f"Hola, soy {nombre}. Necesito ayuda para conseguir más oportunidades.")
            await guardar_mensaje(telefono, "assistant", "¡Hola! Cuéntame un poco sobre tu negocio y qué objetivo quieres lograr.")
            await guardar_mensaje(telefono, "user", f"Somos una {rubro.lower()} y nos interesa {interes.lower()}.")
            await cambiar_estado_lead(telefono, estado)
            creados += 1
    return {"status": "ok", "creados": creados, "mensaje": "Datos demo listos"}


@app.post("/api/channels/whatsapp/toggle")
async def toggle_whatsapp(_usuario: str = Depends(autenticar_dashboard)):
    global BOT_ENABLED
    BOT_ENABLED = not BOT_ENABLED
    return {"status": "ok", "enabled": BOT_ENABLED}


@app.get("/dashboard-old", response_class=HTMLResponse)
async def dashboard(_usuario: str = Depends(autenticar_dashboard)):
    """Dashboard web en tiempo real — leads calificados por Max."""
    leads = await obtener_leads()
    total = len(leads)
    en_seguimiento = sum(1 for l in leads if not l["cerrado"] and not l["descartado"])
    cerrados = sum(1 for l in leads if l["cerrado"])
    descartados = sum(1 for l in leads if l["descartado"])
    tasa = round(cerrados / (total - descartados) * 100) if (total - descartados) > 0 else 0

    filas = ""
    for lead in leads:
        tel = lead["telefono"].replace("@s.whatsapp.net", "").replace("@c.us", "")
        fecha = lead["timestamp"][:16].replace("T", " ")

        nombre = lead.get("nombre", "—")
        rubro = lead.get("rubro", "—")
        presupuesto = lead.get("presupuesto", "—")
        interes = lead.get("interes", "—")

        if lead["cerrado"]:
            estado = "Cerrado"
            color = "#22c55e"
            botones = ""
        elif lead["descartado"]:
            estado = "Descartado"
            color = "#64748b"
            botones = ""
        else:
            estado = "En seguimiento"
            color = "#f59e0b"
            botones = (
                f'<button onclick="cerrar(\'{lead["telefono"]}\')" '
                f'style="background:#22c55e;color:white;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:13px;margin-right:6px;">Cerrado</button>'
                f'<button onclick="descartar(\'{lead["telefono"]}\')" '
                f'style="background:#475569;color:white;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:13px;">Descartar</button>'
            )

        filas += f"""
        <tr>
          <td style="padding:12px 16px;">+{tel}<br><span style="color:#64748b;font-size:12px;">{nombre}</span></td>
          <td style="padding:12px 16px;">{rubro}</td>
          <td style="padding:12px 16px;">{presupuesto}</td>
          <td style="padding:12px 16px;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{interes}">{interes}</td>
          <td style="padding:12px 16px;">{fecha}<br><span style="background:{color};color:white;padding:2px 8px;border-radius:10px;font-size:11px;">{estado}</span></td>
          <td style="padding:12px 16px;">{botones}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard — Max / MC Growth Agency</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }}
    .header {{ background: #1e293b; padding: 24px 32px; border-bottom: 1px solid #334155; }}
    .header h1 {{ font-size: 22px; font-weight: 700; color: #f1f5f9; }}
    .header p {{ color: #94a3b8; font-size: 14px; margin-top: 4px; }}
    .stats {{ display: flex; gap: 16px; padding: 24px 32px; flex-wrap: wrap; }}
    .stat {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px 24px; flex: 1; min-width: 140px; }}
    .stat .num {{ font-size: 36px; font-weight: 800; color: #f1f5f9; }}
    .stat .label {{ color: #94a3b8; font-size: 13px; margin-top: 4px; }}
    .table-wrap {{ margin: 0 32px 32px; background: #1e293b; border: 1px solid #334155; border-radius: 12px; overflow: hidden; }}
    table {{ width: 100%; border-collapse: collapse; }}
    thead tr {{ background: #0f172a; }}
    th {{ padding: 12px 16px; text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; }}
    tbody tr {{ border-top: 1px solid #334155; }}
    tbody tr:hover {{ background: #0f172a; }}
    .refresh {{ margin: 0 32px 24px; color: #64748b; font-size: 13px; }}
    a {{ color: #60a5fa; text-decoration: none; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>Max — Dashboard de Leads</h1>
    <p>MC Growth Agency · Actualizacion automatica cada 30 segundos</p>
  </div>
  <div class="stats">
    <div class="stat"><div class="num">{total}</div><div class="label">Leads calificados</div></div>
    <div class="stat"><div class="num" style="color:#f59e0b;">{en_seguimiento}</div><div class="label">En seguimiento</div></div>
    <div class="stat"><div class="num" style="color:#22c55e;">{cerrados}</div><div class="label">Cerrados</div></div>
    <div class="stat"><div class="num" style="color:#64748b;">{descartados}</div><div class="label">Descartados</div></div>
    <div class="stat"><div class="num" style="color:#60a5fa;">{tasa}%</div><div class="label">Tasa de conversion</div></div>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>WhatsApp</th><th>Rubro</th><th>Presupuesto ads</th><th>Interes</th><th>Fecha / Estado</th><th>Acciones</th></tr></thead>
      <tbody>{filas if filas else '<tr><td colspan="6" style="padding:32px;text-align:center;color:#64748b;">Sin leads aun. Max esta listo para calificar.</td></tr>'}</tbody>
    </table>
  </div>
  <p class="refresh">Ultima actualizacion: {leads[0]["timestamp"][:16].replace("T", " ") if leads else "—"} · <a href="/dashboard">Actualizar</a></p>
  <script>
    async function cerrar(telefono) {{
      if (!confirm('Marcar como Cerrado (cliente ganado)?')) return;
      const r = await fetch('/leads/' + encodeURIComponent(telefono) + '/cerrar', {{method: 'POST'}});
      if (r.ok) location.reload();
      else alert('Error');
    }}
    async function descartar(telefono) {{
      if (!confirm('Marcar como Descartado (no avanzo)?')) return;
      const r = await fetch('/leads/' + encodeURIComponent(telefono) + '/descartar', {{method: 'POST'}});
      if (r.ok) location.reload();
      else alert('Error');
    }}
    setTimeout(() => location.reload(), 30000);
  </script>
</body>
</html>"""
    return html


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return HTMLResponse("""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Acceso · MC Growth OS</title><style>body{margin:0;background:#09090b;color:#f4f4f5;font:14px system-ui;display:grid;place-items:center;min-height:100vh}.box{width:min(360px,calc(100% - 40px));background:#111113;border:1px solid #27272a;border-radius:16px;padding:28px}.mark{display:inline-block;background:#f47b20;color:#09090b;border-radius:9px;padding:9px;font-weight:900;margin-bottom:16px}h1{font-size:22px;margin:0 0 6px}p{color:#a1a1aa;margin:0 0 22px}label{display:block;color:#a1a1aa;font-size:12px;margin:13px 0 6px}input{width:100%;padding:11px;border-radius:8px;border:1px solid #3f3f46;background:#18181b;color:#fff;box-sizing:border-box}button{width:100%;margin-top:20px;padding:11px;border:0;border-radius:8px;background:#f47b20;color:#09090b;font-weight:800;cursor:pointer}</style></head><body><form class="box" method="post"><div class="mark">MC</div><h1>MC Growth OS</h1><p>Ingresá para ver tus oportunidades.</p><label>Usuario</label><input name="usuario" autocomplete="username" required><label>Contraseña</label><input name="clave" type="password" autocomplete="current-password" required><button>Ingresar al dashboard</button></form></body></html>""")


@app.post("/login")
async def login(usuario: str = Form(...), clave: str = Form(...)):
    esperado_usuario = os.getenv("DASHBOARD_USERNAME", "")
    esperado_clave = os.getenv("DASHBOARD_PASSWORD", "")
    if not esperado_usuario or not esperado_clave or not secrets.compare_digest(usuario, esperado_usuario) or not secrets.compare_digest(clave, esperado_clave):
        return HTMLResponse("<p style='font-family:system-ui;padding:30px'>Usuario o contraseña incorrectos. <a href='/login'>Volver</a></p>", status_code=401)
    timestamp = str(int(time.time()))
    response = RedirectResponse("/dashboard", status_code=303)
    # El navegador embebido puede no conservar cookies marcadas como Secure;
    # el transporte sigue protegido por HTTPS en Render.
    response.set_cookie(SESSION_COOKIE, timestamp + "." + _firma_sesion(timestamp), httponly=True, secure=False, samesite="lax", max_age=60 * 60 * 12)
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_v2(request: Request):
    if not _sesion_valida(request):
        return RedirectResponse("/login", status_code=303)
    """Dashboard CRM: pipeline, conversaciones, sentimiento y canales."""
    response = HTMLResponse("""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MC Growth OS</title><style>
:root{--bg:#09090b;--p:#111113;--p2:#18181b;--l:#27272a;--t:#f4f4f5;--m:#a1a1aa;--o:#f47b20}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--t);font:14px system-ui,sans-serif}.top{height:70px;border-bottom:1px solid var(--l);display:flex;justify-content:space-between;align-items:center;padding:0 30px}.brand{display:flex;align-items:center;gap:12px;font-weight:800}.mark{background:var(--o);color:#09090b;border-radius:9px;padding:9px;font-weight:900}.brand small{display:block;color:var(--m);font-size:11px;font-weight:400}.live{color:#86efac;background:#052e16;padding:7px 11px;border-radius:99px;font-size:12px}.wrap{max-width:1500px;margin:auto;padding:28px 30px}.intro h1{margin:0 0 5px;font-size:28px;letter-spacing:-.04em}.intro p{margin:0;color:var(--m)}.tabs{display:flex;gap:5px;border-bottom:1px solid var(--l);margin:25px 0 20px}.tab{background:none;color:var(--m);padding:11px 16px;border-bottom:2px solid transparent}.tab.active{color:var(--t);border-color:var(--o)}.panel{display:none}.panel.active{display:block}.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:22px}.stat,.channel,.card{background:var(--p);border:1px solid var(--l);border-radius:14px}.stat{padding:17px}.stat b{font-size:28px;display:block}.stat span{color:var(--m);font-size:12px}.pipeline{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.stage{background:#0e0e10;border:1px solid var(--l);border-radius:14px;padding:13px;min-height:280px}.stage h3{font-size:13px;margin:0 0 13px;display:flex;justify-content:space-between}.stage h3 span{color:var(--m)}.stage[data-stage=seguimiento] h3{color:#fbbf24}.stage[data-stage=cerrado] h3{color:#86efac}.stage[data-stage=descartado] h3{color:#a1a1aa}.card{padding:14px;margin-bottom:10px}.cardtop{display:flex;justify-content:space-between;gap:8px}.name{font-weight:700}.phone{color:var(--m);font-size:12px;margin-top:3px}.pill{font-size:11px;padding:4px 7px;border-radius:99px;background:#27272a}.positive{background:#86efac;color:#09090b}.neutral{background:#fde68a;color:#09090b}.negative{background:#fca5a5;color:#09090b}.data{margin:12px 0;line-height:1.5;font-size:12px}.data strong{color:#fff}.muted{color:var(--m)}.actions{display:flex;gap:7px}.actions button,.connect{border:0;border-radius:8px;padding:7px 10px;background:#3f3f46;color:#fff;font-size:12px;cursor:pointer}.win{background:#166534!important}.lose{background:#3f3f46!important}.empty{text-align:center;color:#52525b;padding:35px 5px;font-size:12px}.channels{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.channel{padding:18px}.channel h3{margin:11px 0 4px}.channel p{color:var(--m);font-size:12px;line-height:1.5;min-height:36px}.icon{font-size:25px}.status{color:#86efac;font-size:11px}.status.off{color:var(--m)}.connect{width:100%;background:var(--o);color:#09090b;font-weight:700}.connect.off{background:#27272a;color:#fff}.note{margin-top:18px;padding:14px;color:var(--m);border:1px solid var(--l);border-radius:12px;font-size:12px;line-height:1.5}.overlay{display:none;position:fixed;inset:0;background:#000b;z-index:5;padding:5vh 4vw}.modal{max-width:760px;max-height:90vh;overflow:auto;margin:auto;background:var(--p);border:1px solid var(--l);border-radius:14px;padding:22px}.modalhead{display:flex;justify-content:space-between;border-bottom:1px solid var(--l);padding-bottom:14px}.close{background:none;color:var(--m);font-size:22px}.chat{padding-top:16px;display:flex;flex-direction:column;gap:10px}.bubble{max-width:82%;padding:10px 13px;border-radius:13px;white-space:pre-wrap;line-height:1.45}.bubble.user{background:#27272a}.bubble.assistant{align-self:flex-end;background:#7c3f12}.time{display:block;color:var(--m);font-size:10px;margin-top:5px}@media(max-width:900px){.stats{grid-template-columns:repeat(2,1fr)}.pipeline{grid-template-columns:1fr}.channels{grid-template-columns:repeat(2,1fr)}.wrap{padding:22px 15px}}@media(max-width:520px){.channels{grid-template-columns:1fr}}
</style></head><body><header class="top"><div class="brand"><div class="mark">MC</div><div>MC Growth <small>Growth OS · Lead intelligence</small></div></div><div class="live">● Max operativo</div></header><main class="wrap"><section class="intro"><h1>Pipeline de oportunidades</h1><p>Convertí conversaciones en decisiones comerciales.</p></section><nav class="tabs"><button class="tab active" data-tab="pipeline">Pipeline</button><button class="tab" data-tab="canales">Canales</button></nav><section id="pipeline" class="panel active"><div class="stats"><div class="stat"><b id="total">0</b><span>Leads calificados</span></div><div class="stat"><b id="seguimiento" style="color:#fbbf24">0</b><span>En seguimiento</span></div><div class="stat"><b id="cerrado" style="color:#86efac">0</b><span>Cerrados</span></div><div class="stat"><b id="descartado">0</b><span>Descartados</span></div><div class="stat"><b id="conversion" style="color:#f47b20">0%</b><span>Conversión</span></div></div><div class="pipeline"><div class="stage" data-stage="seguimiento"><h3>En seguimiento <span id="count-seguimiento">0</span></h3><div id="col-seguimiento"></div></div><div class="stage" data-stage="cerrado"><h3>Cerrados <span id="count-cerrado">0</span></h3><div id="col-cerrado"></div></div><div class="stage" data-stage="descartado"><h3>Descartados <span id="count-descartado">0</span></h3><div id="col-descartado"></div></div></div><div class="note">Arrastrá una tarjeta entre columnas. Abrí un lead para ver la conversación completa que tuvo con Max.</div></section><section id="canales" class="panel"><div class="channels" id="channels"></div><div class="note"><strong>Canales:</strong> WhatsApp está conectado a Meta Cloud API. Instagram y Facebook requieren sus Webhooks de Meta; LinkedIn requiere permisos específicos.</div></section></main><div class="overlay" id="overlay"><div class="modal"><div class="modalhead"><div><h2 id="modal-title" style="margin:0 0 4px">Conversación</h2><span id="modal-sub" class="muted"></span></div><button class="close" onclick="closeModal()">×</button></div><div class="chat" id="chat"></div></div></div><script>
const esc=s=>String(s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
let leads=[]; function stage(l){return l.cerrado?'cerrado':l.descartado?'descartado':'seguimiento'}
function card(l){var s=stage(l),score=l.sentiment_score||50;return '<article class="card" draggable="true" data-tel="'+esc(l.telefono)+'"><div class="cardtop"><div><div class="name">'+esc(l.nombre||'Sin nombre')+'</div><div class="phone">+'+esc(l.telefono.replace('@s.whatsapp.net','').replace('@c.us',''))+'</div></div><span class="pill '+esc(l.sentiment_label||'neutral')+'">'+score+'/100</span></div><div class="data"><div><strong>Rubro:</strong> '+esc(l.rubro)+'</div><div><strong>Presupuesto:</strong> '+esc(l.presupuesto)+'</div><div><strong>Interés:</strong> '+esc(l.interes)+'</div><div class="muted">'+esc(l.resumen)+'</div></div><div class="actions"><button class="open-chat" data-tel="'+esc(l.telefono)+'">Ver chat</button>'+(s==='seguimiento'?'<button class="win close-lead" data-tel="'+esc(l.telefono)+'">Cerrar</button><button class="discard-lead" data-tel="'+esc(l.telefono)+'">Descartar</button>':'')+'</div></article>'}
async function load(){var d=await (await fetch('/leads')).json(); leads=d.leads||[]; ['seguimiento','cerrado','descartado'].forEach(function(s){var a=leads.filter(function(l){return stage(l)===s}),el=document.getElementById('col-'+s);el.innerHTML=a.length?a.map(card).join(''):'<div class="empty">Sin leads</div>';document.getElementById('count-'+s).textContent=a.length});document.getElementById('total').textContent=leads.length;document.getElementById('seguimiento').textContent=leads.filter(function(l){return stage(l)==='seguimiento'}).length;document.getElementById('cerrado').textContent=leads.filter(function(l){return stage(l)==='cerrado'}).length;document.getElementById('descartado').textContent=leads.filter(function(l){return stage(l)==='descartado'}).length;var base=leads.length-leads.filter(function(l){return l.descartado}).length;document.getElementById('conversion').textContent=(base?Math.round(leads.filter(function(l){return l.cerrado}).length/base*100):0)+'%';document.querySelectorAll('.card').forEach(function(c){c.addEventListener('dragstart',function(e){e.dataTransfer.setData('tel',c.dataset.tel)})});document.querySelectorAll('.stage').forEach(function(c){c.ondragover=function(e){e.preventDefault()};c.ondrop=function(e){setStatus(encodeURIComponent(e.dataTransfer.getData('tel')),c.dataset.stage)}})}
async function setStatus(t,e){var r=await fetch('/leads/'+t+'/estado',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:e})});if(r.ok)load()}
async function openChat(t,n){var d=await (await fetch('/leads/'+t+'/conversation')).json();document.getElementById('modal-title').textContent=n;document.getElementById('chat').innerHTML=(d.messages||[]).map(function(m){return '<div class="bubble '+m.role+'">'+esc(m.content)+'<span class="time">'+new Date(m.timestamp).toLocaleString('es-AR')+'</span></div>'}).join('')||'<div class="empty">No hay mensajes.</div>';document.getElementById('overlay').style.display='block'}function closeModal(){document.getElementById('overlay').style.display='none'}
async function loadChannels(){var d=await (await fetch('/api/channels')).json();document.getElementById('channels').innerHTML=d.channels.map(function(c){var on=c.id==='whatsapp'&&d.bot_enabled,title=c.id==='whatsapp'?(on?'Conectado':'Pausado'):'No configurado';return '<div class="channel"><div class="icon">'+c.name[0]+'</div><h3>'+c.name+'</h3><div class="status '+(on?'':'off')+'">● '+title+'</div><p>'+(c.id==='whatsapp'?'Meta Cloud API · Bot Max':c.id==='linkedin'?'Disponible en una fase posterior':'Requiere credenciales y Webhook')+'</p><button class="connect channel-action '+(on?'':'off')+'" data-channel="'+c.id+'">'+(c.id==='whatsapp'?(on?'Desconectar bot':'Conectar bot'):'Configurar canal')+'</button></div>'}).join('')}
async function channelAction(id){if(id!=='whatsapp'){alert('Este canal está preparado para conectar sus credenciales y webhook.');return}await fetch('/api/channels/whatsapp/toggle',{method:'POST'});loadChannels()}
document.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;var t=b.dataset.tel;if(b.classList.contains('open-chat')){var l=leads.find(function(x){return x.telefono===t});openChat(encodeURIComponent(t),l?(l.nombre||t):t)}if(b.classList.contains('close-lead'))setStatus(encodeURIComponent(t),'cerrado');if(b.classList.contains('discard-lead'))setStatus(encodeURIComponent(t),'descartado')});
document.addEventListener('click',function(e){var b=e.target.closest('.channel-action');if(b)channelAction(b.dataset.channel)});
document.addEventListener('click',function(e){var b=e.target.closest('.open-inbox-chat');if(b){var l=leads.find(function(x){return x.telefono===b.dataset.tel});openChat(encodeURIComponent(b.dataset.tel),l?(l.nombre||b.dataset.tel):b.dataset.tel)}});
async function seedDemo(){var r=await fetch('/api/demo/seed',{method:'POST'});var d=await r.json();alert(d.mensaje+' ('+d.creados+' nuevos)');load()}
async function loadInbox(){var d=await (await fetch('/conversaciones')).json(),leadsMap={};leads.forEach(function(l){leadsMap[l.telefono]=l});var box=document.getElementById('inbox-list');if(!box)return;box.innerHTML=(d.conversaciones||[]).map(function(c){var l=leadsMap[c.telefono],nombre=l?(l.nombre||'Sin nombre'):'Contacto nuevo',estado=l?(stage(l)==='seguimiento'?'Calificado · seguimiento':stage(l)==='cerrado'?'Cerrado':'Descartado'):'En conversación';return '<article class="card"><div class="cardtop"><div><div class="name">'+esc(nombre)+'</div><div class="phone">+'+esc(c.telefono.replace('@s.whatsapp.net','').replace('@c.us',''))+'</div></div><span class="pill">'+estado+'</span></div><div class="data"><div><strong>Mensajes:</strong> '+c.mensajes+'</div><div class="muted">Último contacto: '+new Date(c.ultimo_mensaje).toLocaleString('es-AR')+'</div></div><div class="actions"><button class="open-inbox-chat" data-tel="'+esc(c.telefono)+'">Ver conversación</button></div></article>'}).join('')||'<div class="empty">Todavía no hay conversaciones.</div>'}
document.querySelector('.top').insertAdjacentHTML('beforeend','<button class="connect" style="width:auto;margin-right:8px">Cargar datos demo</button><a class="connect" style="display:inline-block;text-decoration:none;margin-right:8px" href="/export/leads.csv">Exportar leads</a><a class="connect" style="display:inline-block;text-decoration:none;margin-right:20px" href="/export/conversaciones.csv">Exportar chats</a>');document.querySelector('.top .connect').onclick=seedDemo;
document.querySelector('.tabs').insertAdjacentHTML('beforeend','<button class="tab" data-tab="inbox">Bandeja</button>');document.querySelector('main').insertAdjacentHTML('beforeend','<section id="inbox" class="panel"><div id="inbox-list" class="pipeline" style="grid-template-columns:repeat(3,1fr)"></div><div class="note">Acá aparecen todos los contactos que hablaron con Max, incluso los que todavía no completaron la calificación.</div></section>');document.querySelectorAll('.tab').forEach(function(b){b.onclick=function(){document.querySelectorAll('.tab,.panel').forEach(function(x){x.classList.remove('active')});b.classList.add('active');document.getElementById(b.dataset.tab).classList.add('active');if(b.dataset.tab==='canales')loadChannels();if(b.dataset.tab==='inbox')loadInbox()}});load();setInterval(load,30000);
</script></body></html>""")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response
