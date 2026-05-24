# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
# Generado por AgentKit para MC Growth Agency — Agente Max

"""
Servidor principal del agente Max.
Funciona con cualquier proveedor (Whapi, Meta, Twilio) gracias a la capa de providers.
Configurado para Whapi.cloud.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial
from agent.providers import obtener_proveedor

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

            # Enviar respuesta por WhatsApp via Whapi.cloud
            enviado = await proveedor.enviar_mensaje(msg.telefono, respuesta)

            if enviado:
                logger.info(f"Respuesta enviada a {msg.telefono} ✓")
            else:
                logger.warning(f"No se pudo enviar respuesta a {msg.telefono}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
