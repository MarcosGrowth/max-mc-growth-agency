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
from fastapi.responses import PlainTextResponse, HTMLResponse, RedirectResponse, StreamingResponse, FileResponse
from dotenv import load_dotenv

from agent.brain import generar_respuesta, extraer_info_lead
from agent.memory import DATABASE_URL, inicializar_db, guardar_mensaje, obtener_historial, registrar_lead, actualizar_info_lead, obtener_leads, obtener_conversacion, obtener_conversaciones, obtener_todos_los_mensajes, marcar_lead_cerrado, marcar_lead_descartado, cambiar_estado_lead, actualizar_seguimiento_lead, eliminar_lead, obtener_canal, obtener_canales, guardar_canal, alternar_canal, obtener_control_contacto, establecer_control_contacto
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
instagram = None
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


@app.get("/branding/mc-logo.png")
async def mc_logo():
    """Logo oficial de MC Marketing, extraído de la propuesta de marca."""
    return FileResponse("assets/mc-marketing-logo.png", media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/")
async def health_check():
    """Endpoint de salud para Railway y monitoreo."""
    return {
        "status": "ok",
        "agente": "Max",
        "negocio": "MC Growth Agency",
        "proveedor": proveedor.__class__.__name__,
        "persistencia": "PostgreSQL" if DATABASE_URL.startswith("postgres") else "SQLite",
        "entorno": ENVIRONMENT,
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
            # Los ecos humanos de Coexistence se guardan y pausan Max.
            # Así el comercial puede responder desde WhatsApp Business sin
            # que el bot interrumpa o envíe una segunda respuesta.
            if msg.es_propio:
                if msg.origen == "human" and msg.texto:
                    await guardar_mensaje(msg.telefono, "assistant", msg.texto, fuente="human")
                    await establecer_control_contacto(msg.telefono, False, "Equipo comercial", "Mensaje enviado desde WhatsApp Business")
                    logger.info(f"Toma humana detectada para {msg.telefono}; Max pausado")
                continue
            if not msg.texto:
                continue

            control = await obtener_control_contacto(msg.telefono)
            if not control["bot_activo"]:
                await guardar_mensaje(msg.telefono, "user", msg.texto, fuente="user")
                logger.info(f"Mensaje guardado sin respuesta: Max pausado para {msg.telefono}")
                continue

            logger.info(f"Mensaje recibido de {msg.telefono}: {msg.texto[:80]}...")
            proveedor_mensaje = proveedor
            if msg.canal_id and proveedor.__class__.__name__ == "ProveedorMeta":
                canal = await obtener_canal(msg.canal_id)
                if canal:
                    from agent.providers.meta import ProveedorMeta
                    proveedor_mensaje = ProveedorMeta(canal.access_token, canal.phone_number_id, canal.verify_token)

            # Obtener historial ANTES de guardar el mensaje actual
            # (evita duplicados — brain.py agrega el mensaje al construir los mensajes)
            historial = await obtener_historial(msg.telefono)

            # Generar respuesta con Claude (Max)
            respuesta = await generar_respuesta(msg.texto, historial)

            # Guardar mensaje del prospecto y respuesta de Max en memoria
            await guardar_mensaje(msg.telefono, "user", msg.texto, fuente="user")
            await guardar_mensaje(msg.telefono, "assistant", respuesta, fuente="bot")

            # Enviar respuesta por WhatsApp via el proveedor
            enviado = await proveedor_mensaje.enviar_mensaje(msg.telefono, respuesta)

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


@app.get("/instagram/webhook")
async def instagram_verificacion(request: Request):
    from agent.providers.instagram import ProveedorInstagram
    resultado = await ProveedorInstagram().validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    raise HTTPException(status_code=403, detail="Verificación de Instagram inválida")


@app.post("/instagram/webhook")
async def instagram_webhook(request: Request):
    """Recibe DMs de Instagram y los procesa con el mismo Max."""
    from agent.providers.instagram import ProveedorInstagram
    ig = ProveedorInstagram()
    try:
        mensajes = await ig.parsear_webhook(request)
        for msg in mensajes:
            historial = await obtener_historial(msg.telefono)
            respuesta = await generar_respuesta(msg.texto, historial)
            await guardar_mensaje(msg.telefono, "user", msg.texto)
            await guardar_mensaje(msg.telefono, "assistant", respuesta)
            await ig.enviar_mensaje(msg.telefono, respuesta)
            respuesta_normalizada = respuesta.lower()
            calificacion_explicita = (
                "calific" in respuesta_normalizada
                and "auditor" in respuesta_normalizada
                and "no calific" not in respuesta_normalizada
            )
            if "calendar.app.google" in respuesta_normalizada or calificacion_explicita:
                es_nuevo = await registrar_lead(msg.telefono)
                if es_nuevo:
                    info = await extraer_info_lead(await obtener_historial(msg.telefono, limite=30))
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
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error en webhook Instagram: {e}")
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
    # El punto y coma permite que Excel en configuración regional argentina
    # distribuya automáticamente cada campo en su propia columna.
    writer = csv.writer(buffer, delimiter=";")
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
            lead["resumen"], lead["nota"], lead["proxima_accion"], estado, lead["timestamp"],
        ])
    return _csv_response(
        "mc-growth-leads.csv",
        ["telefono", "nombre", "rubro", "presupuesto", "interes", "sentiment_score", "sentiment_label", "resumen", "nota_interna", "proxima_accion", "estado", "fecha"],
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


@app.post("/leads/{telefono}/seguimiento")
async def guardar_seguimiento(telefono: str, request: Request, _usuario: str = Depends(autenticar_dashboard)):
    """Guarda la nota interna y la próxima acción comercial del lead."""
    datos = await request.json()
    ok = await actualizar_seguimiento_lead(
        telefono,
        nota=str(datos.get("nota", "")),
        proxima_accion=str(datos.get("proxima_accion", "")),
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    return {"status": "ok"}


@app.get("/contacts/{telefono}/control")
async def estado_control_contacto(telefono: str, _usuario: str = Depends(autenticar_dashboard)):
    """Devuelve quién tiene el control de la conversación."""
    return await obtener_control_contacto(telefono)


@app.post("/contacts/{telefono}/takeover")
async def tomar_control_contacto(telefono: str, _usuario: str = Depends(autenticar_dashboard)):
    """Pausa Max para que el equipo continúe desde WhatsApp Business."""
    return {"status": "ok", **await establecer_control_contacto(telefono, False, "Equipo comercial", "Toma manual desde el dashboard")}


@app.post("/contacts/{telefono}/resume")
async def reactivar_max_contacto(telefono: str, _usuario: str = Depends(autenticar_dashboard)):
    """Reactiva Max para ese contacto, sin borrar el historial."""
    return {"status": "ok", **await establecer_control_contacto(telefono, True)}


@app.delete("/leads/{telefono}")
async def eliminar_lead_api(telefono: str, _usuario: str = Depends(autenticar_dashboard)):
    """Elimina un lead y su conversación sólo mediante una acción explícita."""
    if not await eliminar_lead(telefono):
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    return {"status": "ok", "mensaje": "Lead y conversación eliminados"}


@app.get("/api/channels")
async def api_channels(_usuario: str = Depends(autenticar_dashboard)):
    canales = await obtener_canales()
    return {"bot_enabled": BOT_ENABLED, "channels": canales, "other_channels": [
        {"id": "instagram", "name": "Instagram", "status": "not_configured", "available": False},
        {"id": "facebook", "name": "Facebook Messenger", "status": "not_configured", "available": False},
        {"id": "linkedin", "name": "LinkedIn", "status": "not_configured", "available": False},
    ]}


@app.get("/api/system/status")
async def api_system_status(_usuario: str = Depends(autenticar_dashboard)):
    """Estado operativo sin exponer credenciales ni la URL de conexión."""
    return {
        "status": "ok",
        "persistencia": "PostgreSQL" if DATABASE_URL.startswith("postgres") else "SQLite",
        "entorno": ENVIRONMENT,
        "bot": "activo" if BOT_ENABLED else "pausado",
    }


@app.get("/api/meta/embedded-signup/config")
async def embedded_signup_config(_usuario: str = Depends(autenticar_dashboard)):
    """Devuelve sólo datos públicos necesarios para abrir el diálogo de Meta."""
    return {
        "app_id": os.getenv("META_APP_ID", "1016554401027275"),
        "config_id": os.getenv("META_EMBEDDED_SIGNUP_CONFIG_ID", "1398042952535570"),
        "version": "v26.0",
    }


@app.post("/api/channels")
async def crear_canal(payload: dict, _usuario: str = Depends(autenticar_dashboard)):
    if payload.get("tipo") != "whatsapp" or not all(payload.get(k) for k in ("nombre", "phone_number_id", "access_token")):
        raise HTTPException(status_code=400, detail="Para WhatsApp se requiere nombre, Phone Number ID y token")
    return await guardar_canal(payload["nombre"], "whatsapp", payload["phone_number_id"], payload["access_token"], payload.get("verify_token", os.getenv("META_VERIFY_TOKEN", "mcgrowth-webhook-2026")))


@app.post("/api/channels/{canal_id}/toggle")
async def toggle_canal(canal_id: int, _usuario: str = Depends(autenticar_dashboard)):
    return {"status": "ok", "activo": await alternar_canal(canal_id)}


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
:root{--bg:#09090b;--p:#111113;--p2:#18181b;--l:#27272a;--t:#f4f4f5;--m:#a1a1aa;--o:#f47b20;--o2:#ff9a4d;--blue:#3b82f6}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(ellipse at 15% -10%,rgba(244,123,32,.13),transparent 38%),radial-gradient(ellipse at 90% 0%,rgba(59,130,246,.11),transparent 30%),var(--bg);color:var(--t);font:14px 'Geist',system-ui,sans-serif;min-height:100vh}.top{height:70px;border-bottom:1px solid var(--l);display:flex;justify-content:space-between;align-items:center;padding:0 30px;background:rgba(9,9,11,.82);backdrop-filter:blur(16px);position:sticky;top:0;z-index:4}.brand{display:flex;align-items:center;gap:12px;font-weight:800;letter-spacing:-.02em}.mark{background:linear-gradient(135deg,var(--o),var(--o2));color:#09090b;border-radius:9px;padding:9px;font-weight:900;box-shadow:0 0 24px rgba(244,123,32,.25)}.brand small{display:block;color:var(--m);font-size:11px;font-weight:400;letter-spacing:0}.live{color:#86efac;background:#052e16;padding:7px 11px;border-radius:99px;font-size:12px}.wrap{max-width:1500px;margin:auto;padding:28px 30px;position:relative}.wrap:before{content:'';position:absolute;inset:0;pointer-events:none;opacity:.22;background-image:radial-gradient(circle at 20% 20%,#fff 0 1px,transparent 1.5px),radial-gradient(circle at 80% 35%,var(--o2) 0 1px,transparent 1.5px),radial-gradient(circle at 55% 75%,#fff 0 1px,transparent 1.5px);background-size:180px 160px,260px 220px,320px 280px;animation:drift 18s linear infinite}@keyframes drift{to{background-position:40px 25px,-30px 45px,20px -35px}}.intro,.tabs,.panel{position:relative}.intro h1{margin:0 0 5px;font-size:28px;letter-spacing:-.04em}.intro p{margin:0;color:var(--m)}.tabs{display:flex;gap:5px;border-bottom:1px solid var(--l);margin:25px 0 20px}.tab{background:none;color:var(--m);padding:11px 16px;border-bottom:2px solid transparent}.tab.active{color:var(--t);border-color:var(--o)}.panel{display:none}.panel.active{display:block}.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:22px}.stat,.channel,.card{background:rgba(17,17,19,.88);border:1px solid var(--l);border-radius:14px}.stat{padding:17px;transition:transform .2s,border-color .2s}.stat:hover,.channel:hover,.card:hover{transform:translateY(-2px);border-color:rgba(244,123,32,.35)}.stat b{font-size:28px;display:block}.stat span{color:var(--m);font-size:12px}.pipeline{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.stage{background:rgba(14,14,16,.82);border:1px solid var(--l);border-radius:14px;padding:13px;min-height:280px}.stage h3{font-size:13px;margin:0 0 13px;display:flex;justify-content:space-between}.stage h3 span{color:var(--m)}.stage[data-stage=seguimiento] h3{color:#fbbf24}.stage[data-stage=cerrado] h3{color:#86efac}.stage[data-stage=descartado] h3{color:#a1a1aa}.card{padding:14px;margin-bottom:10px}.cardtop{display:flex;justify-content:space-between;gap:8px}.name{font-weight:700}.phone{color:var(--m);font-size:12px;margin-top:3px}.pill{font-size:11px;padding:4px 7px;border-radius:99px;background:#27272a}.positive{background:#86efac;color:#09090b}.neutral{background:#fde68a;color:#09090b}.negative{background:#fca5a5;color:#09090b}.data{margin:12px 0;line-height:1.5;font-size:12px}.data strong{color:#fff}.muted{color:var(--m)}.actions{display:flex;gap:7px;flex-wrap:wrap}.actions button,.connect{border:0;border-radius:8px;padding:7px 10px;background:#3f3f46;color:#fff;font-size:12px;cursor:pointer}.win{background:#166534!important}.lose{background:#3f3f46!important}.empty{text-align:center;color:#52525b;padding:35px 5px;font-size:12px}.channels{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.channel{padding:18px;transition:transform .2s,border-color .2s}.channel h3{margin:11px 0 4px}.channel p{color:var(--m);font-size:12px;line-height:1.5;min-height:36px}.icon{font-size:25px}.status{color:#86efac;font-size:11px}.status.off{color:var(--m)}.connect{width:100%;background:linear-gradient(135deg,var(--o),var(--o2));color:#09090b;font-weight:700}.connect.off{background:#27272a;color:#fff}.note{margin-top:18px;padding:14px;color:var(--m);border:1px solid var(--l);border-radius:12px;font-size:12px;line-height:1.5}.overlay{display:none;position:fixed;inset:0;background:#000b;z-index:5;padding:5vh 4vw}.modal{max-width:760px;max-height:90vh;overflow:auto;margin:auto;background:var(--p);border:1px solid var(--l);border-radius:14px;padding:22px}.modalhead{display:flex;justify-content:space-between;border-bottom:1px solid var(--l);padding-bottom:14px}.close{background:none;color:var(--m);font-size:22px}.chat{padding-top:16px;display:flex;flex-direction:column;gap:10px}.bubble{max-width:82%;padding:10px 13px;border-radius:13px;white-space:pre-wrap;line-height:1.45}.bubble.user{background:#27272a}.bubble.assistant{align-self:flex-end;background:#7c3f12}.time{display:block;color:var(--m);font-size:10px;margin-top:5px}@media(max-width:900px){.stats{grid-template-columns:repeat(2,1fr)}.pipeline{grid-template-columns:1fr}.channels{grid-template-columns:repeat(2,1fr)}.wrap{padding:22px 15px}}@media(max-width:520px){.channels{grid-template-columns:1fr}}
</style></head><body><header class="top"><div class="brand"><div class="mark">MC</div><div>MC Growth <small>Growth OS · Lead intelligence</small></div></div><div class="live">● Max operativo</div></header><main class="wrap"><section class="intro"><h1>Pipeline de oportunidades</h1><p>Convertí conversaciones en decisiones comerciales.</p></section><nav class="tabs"><button class="tab active" data-tab="pipeline">Pipeline</button><button class="tab" data-tab="canales">Canales</button></nav><section id="pipeline" class="panel active"><div class="stats"><div class="stat"><b id="total">0</b><span>Leads calificados</span></div><div class="stat"><b id="seguimiento" style="color:#fbbf24">0</b><span>En seguimiento</span></div><div class="stat"><b id="cerrado" style="color:#86efac">0</b><span>Cerrados</span></div><div class="stat"><b id="descartado">0</b><span>Descartados</span></div><div class="stat"><b id="conversion" style="color:#f47b20">0%</b><span>Conversión</span></div></div><div class="pipeline"><div class="stage" data-stage="seguimiento"><h3>En seguimiento <span id="count-seguimiento">0</span></h3><div id="col-seguimiento"></div></div><div class="stage" data-stage="cerrado"><h3>Cerrados <span id="count-cerrado">0</span></h3><div id="col-cerrado"></div></div><div class="stage" data-stage="descartado"><h3>Descartados <span id="count-descartado">0</span></h3><div id="col-descartado"></div></div></div><div class="note">Arrastrá una tarjeta entre columnas. Abrí un lead para ver la conversación completa que tuvo con Max.</div></section><section id="canales" class="panel"><div class="channels" id="channels"></div><div class="note"><strong>Canales:</strong> WhatsApp está conectado a Meta Cloud API. Instagram y Facebook requieren sus Webhooks de Meta; LinkedIn requiere permisos específicos.</div></section></main><div class="overlay" id="overlay"><div class="modal"><div class="modalhead"><div><h2 id="modal-title" style="margin:0 0 4px">Conversación</h2><span id="modal-sub" class="muted"></span></div><button class="close" onclick="closeModal()">×</button></div><div class="chat" id="chat"></div></div></div><script>
const esc=s=>String(s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
let leads=[]; function stage(l){return l.cerrado?'cerrado':l.descartado?'descartado':'seguimiento'}
function card(l){var s=stage(l),score=l.sentiment_score||50;return '<article class="card" draggable="true" data-tel="'+esc(l.telefono)+'"><div class="cardtop"><div><div class="name">'+esc(l.nombre||'Sin nombre')+'</div><div class="phone">+'+esc(l.telefono.replace('@s.whatsapp.net','').replace('@c.us',''))+'</div></div><span class="pill '+esc(l.sentiment_label||'neutral')+'">'+score+'/100</span></div><div class="data"><div><strong>Rubro:</strong> '+esc(l.rubro)+'</div><div><strong>Presupuesto:</strong> '+esc(l.presupuesto)+'</div><div><strong>Interés:</strong> '+esc(l.interes)+'</div><div class="muted">'+esc(l.resumen)+'</div></div><div class="actions"><button class="open-chat" data-tel="'+esc(l.telefono)+'">Ver chat</button><button class="takeover" data-tel="'+esc(l.telefono)+'">Pausar Max</button><button class="resume-max" data-tel="'+esc(l.telefono)+'">Reactivar Max</button>'+(s==='seguimiento'?'<button class="win close-lead" data-tel="'+esc(l.telefono)+'">Cerrar</button><button class="discard-lead" data-tel="'+esc(l.telefono)+'">Descartar</button>':'')+'<button class="delete-lead" data-tel="'+esc(l.telefono)+'">Eliminar</button></div></article>'}
async function load(){var d=await (await fetch('/leads')).json(); leads=d.leads||[]; ['seguimiento','cerrado','descartado'].forEach(function(s){var a=leads.filter(function(l){return stage(l)===s}),el=document.getElementById('col-'+s);el.innerHTML=a.length?a.map(card).join(''):'<div class="empty">Sin leads</div>';document.getElementById('count-'+s).textContent=a.length});document.getElementById('total').textContent=leads.length;document.getElementById('seguimiento').textContent=leads.filter(function(l){return stage(l)==='seguimiento'}).length;document.getElementById('cerrado').textContent=leads.filter(function(l){return stage(l)==='cerrado'}).length;document.getElementById('descartado').textContent=leads.filter(function(l){return stage(l)==='descartado'}).length;var base=leads.length-leads.filter(function(l){return l.descartado}).length;document.getElementById('conversion').textContent=(base?Math.round(leads.filter(function(l){return l.cerrado}).length/base*100):0)+'%';document.querySelectorAll('.card').forEach(function(c){c.addEventListener('dragstart',function(e){e.dataTransfer.setData('tel',c.dataset.tel)})});document.querySelectorAll('.stage').forEach(function(c){c.ondragover=function(e){e.preventDefault()};c.ondrop=function(e){setStatus(encodeURIComponent(e.dataTransfer.getData('tel')),c.dataset.stage)}})}
async function setStatus(t,e){var r=await fetch('/leads/'+t+'/estado',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:e})});if(r.ok)load()}
async function openChat(t,n){var d=await (await fetch('/leads/'+t+'/conversation')).json();document.getElementById('modal-title').textContent=n;document.getElementById('chat').innerHTML=(d.messages||[]).map(function(m){return '<div class="bubble '+m.role+'">'+esc(m.content)+'<span class="time">'+new Date(m.timestamp).toLocaleString('es-AR')+'</span></div>'}).join('')||'<div class="empty">No hay mensajes.</div>';document.getElementById('overlay').style.display='block'}function closeModal(){document.getElementById('overlay').style.display='none'}
async function loadChannels(){var d=await (await fetch('/api/channels')).json(),html=(d.channels||[]).map(function(c){var on=c.activo&&d.bot_enabled;return '<div class="channel"><div class="icon">W</div><h3>'+esc(c.nombre)+'</h3><div class="status '+(on?'':'off')+'">● '+(on?'Conectado':'Pausado')+'</div><p>WhatsApp Cloud API · '+esc(c.phone_number_id)+'</p><button class="connect channel-action '+(on?'':'off')+'" data-channel-id="'+c.id+'">'+(on?'Desconectar':'Conectar')+'</button></div>'}).join('');html+='<div class="channel"><div class="icon">＋</div><h3>Agregar WhatsApp</h3><div class="status off">● Nuevo número</div><p>Conectá otro Phone Number ID de Meta.</p><button class="connect channel-add">Agregar número</button></div><div class="channel"><div class="icon">↔</div><h3>WhatsApp Coexistence</h3><div class="status off">● Vincular app existente</div><p>Conservá el WhatsApp Business del equipo y probá la conexión oficial de Meta.</p><button class="connect embedded-signup">Conectar con Meta</button></div>';html+=(d.other_channels||[]).map(function(c){return '<div class="channel"><div class="icon">'+c.name[0]+'</div><h3>'+c.name+'</h3><div class="status off">● Próximamente</div><p>Requiere credenciales y Webhook.</p><button class="connect off" disabled>Próximamente</button></div>'}).join('');document.getElementById('channels').innerHTML=html}
async function channelAction(id){await fetch('/api/channels/'+id+'/toggle',{method:'POST'});loadChannels()}
async function addChannel(){var nombre=prompt('Nombre para diferenciar este número:');if(!nombre)return;var phone=prompt('Phone Number ID de Meta:');if(!phone)return;var token=prompt('Token permanente de Meta (no lo compartas):');if(!token)return;var r=await fetch('/api/channels',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nombre:nombre,tipo:'whatsapp',phone_number_id:phone,access_token:token})});if(!r.ok){alert('No se pudo guardar el canal');return}alert('Número agregado correctamente');loadChannels()}
document.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;var t=b.dataset.tel;if(b.classList.contains('open-chat')){var l=leads.find(function(x){return x.telefono===t});openChat(encodeURIComponent(t),l?(l.nombre||t):t)}if(b.classList.contains('close-lead'))setStatus(encodeURIComponent(t),'cerrado');if(b.classList.contains('discard-lead'))setStatus(encodeURIComponent(t),'descartado')});
document.addEventListener('click',async function(e){var b=e.target.closest('.takeover,.resume-max');if(!b)return;var t=encodeURIComponent(b.dataset.tel),path=b.classList.contains('takeover')?'takeover':'resume';var r=await fetch('/contacts/'+t+'/'+path,{method:'POST'});if(r.ok){alert(path==='takeover'?'Max pausado. El comercial puede continuar desde WhatsApp Business.':'Max reactivado para este contacto.');load()}else alert('No se pudo actualizar el control de la conversación')});
document.addEventListener('click',async function(e){var b=e.target.closest('.delete-lead');if(!b)return;if(!confirm('Eliminar definitivamente este lead y toda su conversación? Esta acción no se puede deshacer.'))return;var r=await fetch('/leads/'+encodeURIComponent(b.dataset.tel),{method:'DELETE'});if(r.ok)load();else alert('No se pudo eliminar el lead')});
document.addEventListener('click',function(e){if(e.target.closest('.channel-add'))addChannel();var b=e.target.closest('.channel-action');if(b)channelAction(b.dataset.channelId)});
var embeddedSignupPromise=null;
function prepararEmbeddedSignup(){if(embeddedSignupPromise)return embeddedSignupPromise;embeddedSignupPromise=(async function(){var cfg=await (await fetch('/api/meta/embedded-signup/config',{cache:'no-store'})).json();if(!window.FB){await new Promise(function(resolve,reject){var s=document.createElement('script');s.src='https://connect.facebook.net/en_US/sdk.js';s.onload=resolve;s.onerror=function(){reject(new Error('El navegador no pudo cargar el SDK de Meta'))};document.head.appendChild(s)});if(!window.FB)throw new Error('El SDK de Meta no quedó disponible');window.FB.init({appId:cfg.app_id,cookie:true,xfbml:false,version:cfg.version})}return cfg})().catch(function(err){embeddedSignupPromise=null;throw err});return embeddedSignupPromise}
function abrirEmbeddedSignup(){prepararEmbeddedSignup().then(function(cfg){if(!window.FB||typeof window.FB.login!=='function')throw new Error('El SDK de Meta no está disponible en este navegador');window.FB.login(function(response){if(response.authResponse&&response.authResponse.code){alert('Meta autorizó el flujo. Estamos listos para completar el intercambio seguro en el servidor.')}else if(response.authResponse){alert('Meta respondió, pero no devolvió código de autorización. Revisemos el flujo.')}else{alert('La vinculación fue cancelada o Meta no la habilitó para esta cuenta.')}},{config_id:cfg.config_id,response_type:'code',override_default_response_type:true,extras:{feature:'whatsapp_embedded_signup',sessionInfoVersion:'3'}})}).catch(function(err){alert('No se pudo abrir Meta: '+err.message+' Probá desde Chrome o Edge si estás dentro del navegador interno.')})}
prepararEmbeddedSignup();
document.addEventListener('click',function(e){if(e.target.closest('.embedded-signup'))abrirEmbeddedSignup()});
document.addEventListener('click',function(e){var b=e.target.closest('.open-inbox-chat');if(b){var l=leads.find(function(x){return x.telefono===b.dataset.tel});openChat(encodeURIComponent(b.dataset.tel),l?(l.nombre||b.dataset.tel):b.dataset.tel)}});
function renderInsights(){var box=document.getElementById('insights');if(!box){document.querySelector('#pipeline .stats').insertAdjacentHTML('afterend','<section id="insights" aria-label="Resumen visual" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:0 0 22px"></section>');box=document.getElementById('insights')}var total=leads.length,avg=total?Math.round(leads.reduce(function(a,l){return a+(Number(l.sentiment_score)||50)},0)/total):0,pos=leads.filter(function(l){return l.sentiment_label==='positivo'}).length,neu=leads.filter(function(l){return l.sentiment_label==='neutral'}).length,neg=leads.filter(function(l){return l.sentiment_label==='negativo'}).length,max=Math.max(pos,neu,neg,1);box.innerHTML='<div style="background:rgba(17,17,19,.88);border:1px solid #27272a;border-radius:14px;padding:16px"><div style="color:#a1a1aa;font-size:11px;text-transform:uppercase;letter-spacing:1px">Sentimiento promedio</div><strong style="display:block;font-size:28px;color:'+(avg>=70?'#86efac':avg>=45?'#fbbf24':'#fca5a5')+'">'+avg+'/100</strong><span style="color:#a1a1aa;font-size:12px">Lectura general de los leads</span></div><div style="background:rgba(17,17,19,.88);border:1px solid #27272a;border-radius:14px;padding:16px"><div style="color:#a1a1aa;font-size:11px;text-transform:uppercase;letter-spacing:1px">Distribución emocional</div><div style="display:flex;align-items:end;gap:8px;height:38px;margin:8px 0"><div title="Positivo: '+pos+'" style="height:'+Math.max(6,Math.round(pos/max*100))+'%;flex:1;background:#22c55e;border-radius:5px 5px 2px 2px"></div><div title="Neutral: '+neu+'" style="height:'+Math.max(6,Math.round(neu/max*100))+'%;flex:1;background:#f59e0b;border-radius:5px 5px 2px 2px"></div><div title="Negativo: '+neg+'" style="height:'+Math.max(6,Math.round(neg/max*100))+'%;flex:1;background:#ef4444;border-radius:5px 5px 2px 2px"></div></div><span style="color:#a1a1aa;font-size:12px">Positivo '+pos+' · Neutral '+neu+' · Negativo '+neg+'</span></div><div style="background:rgba(17,17,19,.88);border:1px solid #27272a;border-radius:14px;padding:16px"><div style="color:#a1a1aa;font-size:11px;text-transform:uppercase;letter-spacing:1px">Oportunidades visibles</div><strong style="display:block;font-size:28px;color:#f47b20">'+total+'</strong><span style="color:#a1a1aa;font-size:12px">Leads calificados en el pipeline</span></div>'}
function setupFilters(){if(document.getElementById('lead-filters'))return;document.querySelector('#pipeline .stats').insertAdjacentHTML('beforebegin','<div id="lead-filters" style="display:flex;gap:8px;flex-wrap:wrap;margin:0 0 16px"><input id="lead-search" placeholder="Buscar por nombre, teléfono, rubro o interés" style="flex:1;min-width:240px;background:#18181b;color:#f4f4f5;border:1px solid #3f3f46;border-radius:8px;padding:10px"><select id="sentiment-filter" style="background:#18181b;color:#f4f4f5;border:1px solid #3f3f46;border-radius:8px;padding:10px"><option value="">Todos los sentimientos</option><option value="positivo">Positivos</option><option value="neutral">Neutrales</option><option value="negativo">Negativos</option></select><button id="clear-filters" style="border:0;border-radius:8px;padding:10px 13px;background:#3f3f46;color:#fff;cursor:pointer">Limpiar</button></div>');var apply=function(){var q=(document.getElementById('lead-search').value||'').toLowerCase().trim(),sent=document.getElementById('sentiment-filter').value;document.querySelectorAll('.card[data-tel]').forEach(function(c){var l=leads.find(function(x){return x.telefono===c.dataset.tel}),hay=l&&[l.nombre,l.telefono,l.rubro,l.presupuesto,l.interes,l.resumen].join(' ').toLowerCase().indexOf(q)>=0,ok=!sent||l.sentiment_label===sent;c.style.display=hay&&ok?'':'none'});};document.getElementById('lead-search').addEventListener('input',apply);document.getElementById('sentiment-filter').addEventListener('change',apply);document.getElementById('clear-filters').onclick=function(){document.getElementById('lead-search').value='';document.getElementById('sentiment-filter').value='';apply()}}
function decorateFollowupCards(){document.querySelectorAll('.card[data-tel]').forEach(function(c){var l=leads.find(function(x){return x.telefono===c.dataset.tel});if(!l)return;var data=c.querySelector('.data'),actions=c.querySelector('.actions');if(data&&!data.querySelector('.followup-data'))data.insertAdjacentHTML('beforeend','<div class="muted followup-data" style="margin-top:8px"><strong>Nota:</strong> '+esc(l.nota||'Sin nota')+'<br><strong>Próxima:</strong> '+esc(l.proxima_accion||'Sin definir')+'</div>');if(actions&&!actions.querySelector('.edit-followup'))actions.insertAdjacentHTML('afterbegin','<button class="edit-followup" data-tel="'+esc(l.telefono)+'">Seguimiento</button>')})}
var loadWithInsights=load;load=async function(){await loadWithInsights();renderInsights();setupFilters();decorateFollowupCards()};
function openFollowup(t){var l=leads.find(function(x){return x.telefono===t});if(!l)return;var old=document.getElementById('followup-dialog');if(old)old.remove();var box=document.createElement('div');box.id='followup-dialog';box.style='position:fixed;inset:0;background:#000b;z-index:20;display:flex;align-items:center;justify-content:center;padding:20px';box.innerHTML='<div style="width:min(560px,100%);background:#111113;border:1px solid #3f3f46;border-radius:16px;padding:22px;box-shadow:0 20px 60px #000"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px"><h2 style="margin:0">Seguimiento comercial</h2><button id="cancel-followup" style="background:none;border:0;color:#a1a1aa;font-size:24px;cursor:pointer">×</button></div><label style="display:block;color:#a1a1aa;font-size:12px;margin:0 0 6px">Nota interna</label><textarea id="followup-note" rows="4" style="width:100%;box-sizing:border-box;background:#18181b;color:#f4f4f5;border:1px solid #3f3f46;border-radius:8px;padding:10px;resize:vertical">'+esc(l.nota||'')+'</textarea><label style="display:block;color:#a1a1aa;font-size:12px;margin:14px 0 6px">Próxima acción</label><input id="followup-next" value="'+esc(l.proxima_accion||'')+'" placeholder="Ej: llamar el jueves por la tarde" style="width:100%;box-sizing:border-box;background:#18181b;color:#f4f4f5;border:1px solid #3f3f46;border-radius:8px;padding:10px"><div style="display:flex;justify-content:flex-end;gap:8px;margin-top:18px"><button id="cancel-followup-2" class="actions button" style="border:1px solid #3f3f46;border-radius:8px;padding:9px 13px;background:#27272a;color:#fff;cursor:pointer">Cancelar</button><button id="save-followup" style="border:0;border-radius:8px;padding:9px 13px;background:#f47b20;color:#09090b;font-weight:700;cursor:pointer">Guardar seguimiento</button></div></div>';document.body.appendChild(box);var close=function(){box.remove()};document.getElementById('cancel-followup').onclick=close;document.getElementById('cancel-followup-2').onclick=close;document.getElementById('save-followup').onclick=async function(){var r=await fetch('/leads/'+encodeURIComponent(t)+'/seguimiento',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nota:document.getElementById('followup-note').value,proxima_accion:document.getElementById('followup-next').value})});if(r.ok){close();load()}else alert('No se pudo guardar el seguimiento')}}
document.addEventListener('click',function(e){var b=e.target.closest('.edit-followup');if(b)openFollowup(b.dataset.tel)});
async function seedDemo(){var r=await fetch('/api/demo/seed',{method:'POST'});var d=await r.json();alert(d.mensaje+' ('+d.creados+' nuevos)');load()}
async function loadInbox(){var d=await (await fetch('/conversaciones')).json(),leadsMap={};leads.forEach(function(l){leadsMap[l.telefono]=l});var box=document.getElementById('inbox-list');if(!box)return;box.innerHTML=(d.conversaciones||[]).map(function(c){var l=leadsMap[c.telefono],nombre=l?(l.nombre||'Sin nombre'):'Contacto nuevo',estado=l?(stage(l)==='seguimiento'?'Calificado · seguimiento':stage(l)==='cerrado'?'Cerrado':'Descartado'):'En conversación';return '<article class="card"><div class="cardtop"><div><div class="name">'+esc(nombre)+'</div><div class="phone">+'+esc(c.telefono.replace('@s.whatsapp.net','').replace('@c.us',''))+'</div></div><span class="pill">'+estado+'</span></div><div class="data"><div><strong>Mensajes:</strong> '+c.mensajes+'</div><div class="muted">Último contacto: '+new Date(c.ultimo_mensaje).toLocaleString('es-AR')+'</div></div><div class="actions"><button class="open-inbox-chat" data-tel="'+esc(c.telefono)+'">Ver conversación</button></div></article>'}).join('')||'<div class="empty">Todavía no hay conversaciones.</div>'}
document.querySelector('.top').insertAdjacentHTML('beforeend','<button class="connect" style="width:auto;margin-right:8px">Cargar datos demo</button><a class="connect" style="display:inline-block;text-decoration:none;margin-right:8px" href="/export/leads.csv">Exportar leads</a><a class="connect" style="display:inline-block;text-decoration:none;margin-right:20px" href="/export/conversaciones.csv">Exportar chats</a>');document.querySelector('.top .connect').onclick=seedDemo;
document.querySelector('.tabs').insertAdjacentHTML('beforeend','<button class="tab" data-tab="inbox">Bandeja</button>');document.querySelector('main').insertAdjacentHTML('beforeend','<section id="inbox" class="panel"><div id="inbox-list" class="pipeline" style="grid-template-columns:repeat(3,1fr)"></div><div class="note">Acá aparecen todos los contactos que hablaron con Max, incluso los que todavía no completaron la calificación.</div></section>');document.querySelectorAll('.tab').forEach(function(b){b.onclick=function(){document.querySelectorAll('.tab,.panel').forEach(function(x){x.classList.remove('active')});b.classList.add('active');document.getElementById(b.dataset.tab).classList.add('active');if(b.dataset.tab==='canales')loadChannels();if(b.dataset.tab==='inbox')loadInbox()}});load();setInterval(load,30000);
</script></body></html>""")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.body = response.body.replace(
        '<header class="top"><div class="brand"><div class="mark">MC</div><div>MC Growth <small>Growth OS · Lead intelligence</small></div></div><div class="live">● Max operativo</div></header>'.encode("utf-8"),
        '<header class="top" style="height:72px;padding:0 32px"><div class="brand" style="gap:0"><img src="/branding/mc-logo.png" alt="MC Marketing" style="width:154px;height:auto;display:block;filter:drop-shadow(0 0 12px rgba(244,123,32,.28))"></div><div class="live">● Max operativo</div></header>'.encode("utf-8"),
        1,
    )
    response.body = response.body.replace(
        b'<div class="mark">MC</div>',
        b'<div class="mark" aria-label="MC Marketing"><img src="/branding/mc-logo.png" alt="MC Marketing" style="width:24px;height:24px;display:block;object-fit:contain"></div>',
        1,
    )
    response.headers["Content-Length"] = str(len(response.body))
    return response
