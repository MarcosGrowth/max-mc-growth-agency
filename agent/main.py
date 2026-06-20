# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
# Generado por AgentKit para MC Growth Agency — Agente Max

"""
Servidor principal del agente Max.
Funciona con cualquier proveedor (Whapi, Meta, Twilio) gracias a la capa de providers.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial, registrar_lead, obtener_leads, marcar_lead_cerrado
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
            LINK_AUDITORIA = "calendar.app.google"
            if LINK_AUDITORIA in respuesta:
                es_nuevo = await registrar_lead(msg.telefono)
                if es_nuevo:
                    # Armar resumen de los últimos 3 mensajes del usuario
                    historial_reciente = await obtener_historial(msg.telefono, limite=6)
                    mensajes_usuario = [
                        m["content"] for m in historial_reciente if m["role"] == "user"
                    ]
                    resumen = "\n".join(f"• {m}" for m in mensajes_usuario[-3:])
                    await notificar_lead_calificado(msg.telefono, resumen)
                    logger.info(f"Lead calificado notificado: {msg.telefono}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Dashboard de leads ──────────────────────────────────────────────────────

@app.get("/leads")
async def api_leads():
    """API: lista todos los leads calificados (para el dashboard o integraciones)."""
    leads = await obtener_leads()
    return {"leads": leads, "total": len(leads)}


@app.post("/leads/{telefono}/cerrar")
async def cerrar_lead(telefono: str):
    """API: marca un lead como cerrado (cliente ganado)."""
    ok = await marcar_lead_cerrado(telefono)
    if not ok:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    return {"status": "ok", "mensaje": f"Lead {telefono} marcado como cerrado"}


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Dashboard web en tiempo real — leads calificados por Max."""
    leads = await obtener_leads()
    total = len(leads)
    calificados = sum(1 for l in leads if not l["cerrado"])
    cerrados = sum(1 for l in leads if l["cerrado"])

    filas = ""
    for lead in leads:
        tel = lead["telefono"].replace("@s.whatsapp.net", "").replace("@c.us", "")
        fecha = lead["timestamp"][:16].replace("T", " ")
        estado = "Cerrado" if lead["cerrado"] else "Calificado"
        color = "#22c55e" if lead["cerrado"] else "#f59e0b"
        boton = "" if lead["cerrado"] else f'<button onclick="cerrar(\'{lead["telefono"]}\')" style="background:#22c55e;color:white;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:13px;">Cerrado</button>'
        filas += f"""
        <tr>
          <td style="padding:12px 16px;">+{tel}</td>
          <td style="padding:12px 16px;">{fecha}</td>
          <td style="padding:12px 16px;"><span style="background:{color};color:white;padding:3px 10px;border-radius:12px;font-size:12px;">{estado}</span></td>
          <td style="padding:12px 16px;">{boton}</td>
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
    .stats {{ display: flex; gap: 16px; padding: 24px 32px; }}
    .stat {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px 24px; flex: 1; }}
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
    <div class="stat"><div class="num">{total}</div><div class="label">Total leads calificados</div></div>
    <div class="stat"><div class="num" style="color:#f59e0b;">{calificados}</div><div class="label">En seguimiento</div></div>
    <div class="stat"><div class="num" style="color:#22c55e;">{cerrados}</div><div class="label">Cerrados (clientes)</div></div>
    <div class="stat"><div class="num" style="color:#60a5fa;">{round(cerrados/total*100) if total > 0 else 0}%</div><div class="label">Tasa de conversion</div></div>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>WhatsApp</th><th>Fecha</th><th>Estado</th><th>Accion</th></tr></thead>
      <tbody>{filas if filas else '<tr><td colspan="4" style="padding:32px;text-align:center;color:#64748b;">Sin leads aun. Max esta listo para calificar.</td></tr>'}</tbody>
    </table>
  </div>
  <p class="refresh">Ultima actualizacion: {leads[0]["timestamp"][:16].replace("T", " ") if leads else "—"} · <a href="/dashboard">Actualizar</a></p>
  <script>
    async function cerrar(telefono) {{
      if (!confirm('Marcar este lead como cerrado?')) return;
      const r = await fetch('/leads/' + encodeURIComponent(telefono) + '/cerrar', {{method: 'POST'}});
      if (r.ok) location.reload();
      else alert('Error al cerrar el lead');
    }}
    setTimeout(() => location.reload(), 30000);
  </script>
</body>
</html>"""
    return html
