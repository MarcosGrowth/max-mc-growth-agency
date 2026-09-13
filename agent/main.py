# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
# Generado por AgentKit para MC Growth Agency — Agente Max

"""
Servidor principal del agente Max.
Funciona con cualquier proveedor (Whapi, Meta, Twilio) gracias a la capa de providers.
"""

import os
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse
from dotenv import load_dotenv

from agent.brain import generar_respuesta, extraer_info_lead
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial, registrar_lead, actualizar_info_lead, obtener_leads, obtener_conversacion, marcar_lead_cerrado, marcar_lead_descartado, cambiar_estado_lead
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
            LINK_AUDITORIA = "calendar.app.google"
            if LINK_AUDITORIA in respuesta:
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
async def api_leads():
    """API: lista todos los leads calificados (para el dashboard o integraciones)."""
    leads = await obtener_leads()
    return {"leads": leads, "total": len(leads)}


@app.get("/leads/{telefono}/conversation")
async def api_conversacion(telefono: str):
    """API: devuelve todos los mensajes de la conversación del lead."""
    return {"telefono": telefono, "messages": await obtener_conversacion(telefono)}


@app.post("/leads/{telefono}/cerrar")
async def cerrar_lead(telefono: str):
    """API: marca un lead como cerrado (cliente ganado)."""
    ok = await marcar_lead_cerrado(telefono)
    if not ok:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    return {"status": "ok", "mensaje": f"Lead {telefono} marcado como cerrado"}


@app.post("/leads/{telefono}/descartar")
async def descartar_lead(telefono: str):
    """API: marca un lead como descartado (no avanzó)."""
    ok = await marcar_lead_descartado(telefono)
    if not ok:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    return {"status": "ok", "mensaje": f"Lead {telefono} marcado como descartado"}


@app.post("/leads/{telefono}/estado")
async def cambiar_estado(telefono: str, request: Request):
    datos = await request.json()
    estado = datos.get("estado", "seguimiento")
    if not await cambiar_estado_lead(telefono, estado):
        raise HTTPException(status_code=400, detail="Estado o lead inválido")
    return {"status": "ok", "estado": estado}


@app.get("/api/channels")
async def api_channels():
    return {"bot_enabled": BOT_ENABLED, "channels": [
        {"id": "whatsapp", "name": "WhatsApp", "status": "connected" if proveedor.__class__.__name__ == "ProveedorMeta" else "backup", "available": True},
        {"id": "instagram", "name": "Instagram", "status": "not_configured", "available": False},
        {"id": "facebook", "name": "Facebook Messenger", "status": "not_configured", "available": False},
        {"id": "linkedin", "name": "LinkedIn", "status": "not_configured", "available": False},
    ]}


@app.post("/api/channels/whatsapp/toggle")
async def toggle_whatsapp():
    global BOT_ENABLED
    BOT_ENABLED = not BOT_ENABLED
    return {"status": "ok", "enabled": BOT_ENABLED}


@app.get("/dashboard-old", response_class=HTMLResponse)
async def dashboard():
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


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_v2():
    """Dashboard CRM: pipeline, conversaciones, sentimiento y canales."""
    return HTMLResponse("""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MC Growth OS</title><style>
:root{--bg:#09090b;--p:#111113;--p2:#18181b;--l:#27272a;--t:#f4f4f5;--m:#a1a1aa;--o:#f47b20}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--t);font:14px system-ui,sans-serif}.top{height:70px;border-bottom:1px solid var(--l);display:flex;justify-content:space-between;align-items:center;padding:0 30px}.brand{display:flex;align-items:center;gap:12px;font-weight:800}.mark{background:var(--o);color:#09090b;border-radius:9px;padding:9px;font-weight:900}.brand small{display:block;color:var(--m);font-size:11px;font-weight:400}.live{color:#86efac;background:#052e16;padding:7px 11px;border-radius:99px;font-size:12px}.wrap{max-width:1500px;margin:auto;padding:28px 30px}.intro h1{margin:0 0 5px;font-size:28px;letter-spacing:-.04em}.intro p{margin:0;color:var(--m)}.tabs{display:flex;gap:5px;border-bottom:1px solid var(--l);margin:25px 0 20px}.tab{background:none;color:var(--m);padding:11px 16px;border-bottom:2px solid transparent}.tab.active{color:var(--t);border-color:var(--o)}.panel{display:none}.panel.active{display:block}.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:22px}.stat,.channel,.card{background:var(--p);border:1px solid var(--l);border-radius:14px}.stat{padding:17px}.stat b{font-size:28px;display:block}.stat span{color:var(--m);font-size:12px}.pipeline{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.stage{background:#0e0e10;border:1px solid var(--l);border-radius:14px;padding:13px;min-height:280px}.stage h3{font-size:13px;margin:0 0 13px;display:flex;justify-content:space-between}.stage h3 span{color:var(--m)}.stage[data-stage=seguimiento] h3{color:#fbbf24}.stage[data-stage=cerrado] h3{color:#86efac}.stage[data-stage=descartado] h3{color:#a1a1aa}.card{padding:14px;margin-bottom:10px}.cardtop{display:flex;justify-content:space-between;gap:8px}.name{font-weight:700}.phone{color:var(--m);font-size:12px;margin-top:3px}.pill{font-size:11px;padding:4px 7px;border-radius:99px;background:#27272a}.positive{background:#86efac;color:#09090b}.neutral{background:#fde68a;color:#09090b}.negative{background:#fca5a5;color:#09090b}.data{margin:12px 0;line-height:1.5;font-size:12px}.data strong{color:#fff}.muted{color:var(--m)}.actions{display:flex;gap:7px}.actions button,.connect{border:0;border-radius:8px;padding:7px 10px;background:#3f3f46;color:#fff;font-size:12px;cursor:pointer}.win{background:#166534!important}.lose{background:#3f3f46!important}.empty{text-align:center;color:#52525b;padding:35px 5px;font-size:12px}.channels{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.channel{padding:18px}.channel h3{margin:11px 0 4px}.channel p{color:var(--m);font-size:12px;line-height:1.5;min-height:36px}.icon{font-size:25px}.status{color:#86efac;font-size:11px}.status.off{color:var(--m)}.connect{width:100%;background:var(--o);color:#09090b;font-weight:700}.connect.off{background:#27272a;color:#fff}.note{margin-top:18px;padding:14px;color:var(--m);border:1px solid var(--l);border-radius:12px;font-size:12px;line-height:1.5}.overlay{display:none;position:fixed;inset:0;background:#000b;z-index:5;padding:5vh 4vw}.modal{max-width:760px;max-height:90vh;overflow:auto;margin:auto;background:var(--p);border:1px solid var(--l);border-radius:14px;padding:22px}.modalhead{display:flex;justify-content:space-between;border-bottom:1px solid var(--l);padding-bottom:14px}.close{background:none;color:var(--m);font-size:22px}.chat{padding-top:16px;display:flex;flex-direction:column;gap:10px}.bubble{max-width:82%;padding:10px 13px;border-radius:13px;white-space:pre-wrap;line-height:1.45}.bubble.user{background:#27272a}.bubble.assistant{align-self:flex-end;background:#7c3f12}.time{display:block;color:var(--m);font-size:10px;margin-top:5px}@media(max-width:900px){.stats{grid-template-columns:repeat(2,1fr)}.pipeline{grid-template-columns:1fr}.channels{grid-template-columns:repeat(2,1fr)}.wrap{padding:22px 15px}}@media(max-width:520px){.channels{grid-template-columns:1fr}}
+<script>
const esc=s=>String(s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
let leads=[]; function stage(l){return l.cerrado?'cerrado':l.descartado?'descartado':'seguimiento'}
function card(l){var s=stage(l), score=l.sentiment_score||50; return '<article class="card" draggable="true" data-tel="'+esc(l.telefono)+'"><div class="cardtop"><div><div class="name">'+esc(l.nombre||'Sin nombre')+'</div><div class="phone">+'+esc(l.telefono.replace('@s.whatsapp.net','').replace('@c.us',''))+'</div></div><span class="pill '+esc(l.sentiment_label||'neutral')+'">'+score+'/100</span></div><div class="data"><div><strong>Rubro:</strong> '+esc(l.rubro)+'</div><div><strong>Presupuesto:</strong> '+esc(l.presupuesto)+'</div><div><strong>Interés:</strong> '+esc(l.interes)+'</div><div class="muted">'+esc(l.resumen)+'</div></div><div class="actions"><button onclick="openChat(\''+encodeURIComponent(l.telefono)+'\',\''+esc(l.nombre||l.telefono)+'\')">Ver chat</button>'+(s==='seguimiento'?'<button class="win" onclick="setStatus(\''+encodeURIComponent(l.telefono)+'\',\'cerrado\')">Cerrar</button><button onclick="setStatus(\''+encodeURIComponent(l.telefono)+'\',\'descartado\')">Descartar</button>':'')+'</div></article>'}
async function load(){var d=await (await fetch('/leads')).json(); leads=d.leads||[]; ['seguimiento','cerrado','descartado'].forEach(function(s){var a=leads.filter(function(l){return stage(l)===s}),el=document.getElementById('col-'+s);el.innerHTML=a.length?a.map(card).join(''):'<div class="empty">Sin leads</div>';document.getElementById('count-'+s).textContent=a.length});document.getElementById('total').textContent=leads.length;document.getElementById('seguimiento').textContent=leads.filter(function(l){return stage(l)==='seguimiento'}).length;document.getElementById('cerrado').textContent=leads.filter(function(l){return stage(l)==='cerrado'}).length;document.getElementById('descartado').textContent=leads.filter(function(l){return stage(l)==='descartado'}).length;var base=leads.length-leads.filter(function(l){return l.descartado}).length;document.getElementById('conversion').textContent=(base?Math.round(leads.filter(function(l){return l.cerrado}).length/base*100):0)+'%';document.querySelectorAll('.card').forEach(function(c){c.addEventListener('dragstart',function(e){e.dataTransfer.setData('tel',c.dataset.tel)})});document.querySelectorAll('.stage').forEach(function(c){c.ondragover=function(e){e.preventDefault()};c.ondrop=function(e){setStatus(encodeURIComponent(e.dataTransfer.getData('tel')),c.dataset.stage)}})}
async function setStatus(t,e){var r=await fetch('/leads/'+t+'/estado',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:e})});if(r.ok)load()}
async function openChat(t,n){var d=await (await fetch('/leads/'+t+'/conversation')).json();document.getElementById('modal-title').textContent=n;document.getElementById('chat').innerHTML=(d.messages||[]).map(function(m){return '<div class="bubble '+m.role+'">'+esc(m.content)+'<span class="time">'+new Date(m.timestamp).toLocaleString('es-AR')+'</span></div>'}).join('')||'<div class="empty">No hay mensajes.</div>';document.getElementById('overlay').style.display='block'}function closeModal(){document.getElementById('overlay').style.display='none'}
async function loadChannels(){var d=await (await fetch('/api/channels')).json();document.getElementById('channels').innerHTML=d.channels.map(function(c){var on=c.id==='whatsapp'&&d.bot_enabled,title=c.id==='whatsapp'?(on?'Conectado':'Pausado'):'No configurado';return '<div class="channel"><div class="icon">'+c.name[0]+'</div><h3>'+c.name+'</h3><div class="status '+(on?'':'off')+'">● '+title+'</div><p>'+(c.id==='whatsapp'?'Meta Cloud API · Bot Max':c.id==='linkedin'?'Disponible en una fase posterior':'Requiere credenciales y Webhook')+'</p><button class="connect '+(on?'':'off')+'" onclick="channelAction(\''+c.id+'\')">'+(c.id==='whatsapp'?(on?'Desconectar bot':'Conectar bot'):'Configurar canal')+'</button></div>'}).join('')}
async function channelAction(id){if(id!=='whatsapp'){alert('Este canal está preparado para conectar sus credenciales y webhook.');return}await fetch('/api/channels/whatsapp/toggle',{method:'POST'});loadChannels()}
document.querySelectorAll('.tab').forEach(function(b){b.onclick=function(){document.querySelectorAll('.tab,.panel').forEach(function(x){x.classList.remove('active')});b.classList.add('active');document.getElementById(b.dataset.tab).classList.add('active');if(b.dataset.tab==='canales')loadChannels()}});load();setInterval(load,30000);
</script></body></html>""")
