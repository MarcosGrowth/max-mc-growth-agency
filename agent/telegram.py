# agent/telegram.py — Notificaciones Telegram para MC Growth Agency
# Envía alertas al equipo cuando Max califica un lead

import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("agentkit")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


async def notificar_lead_calificado(telefono: str, resumen: str) -> bool:
    """
    Envía una notificación a Telegram cuando Max califica un lead.

    Args:
        telefono: Número del prospecto
        resumen: Últimos mensajes de la conversación (contexto)

    Returns:
        True si la notificación fue enviada exitosamente
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados — notificación omitida")
        return False

    # Limpiar el número para mostrar de forma amigable
    telefono_limpio = telefono.replace("@s.whatsapp.net", "").replace("@c.us", "")

    mensaje = (
        "🔥 *LEAD CALIFICADO — MC Growth Agency*\n\n"
        f"📱 *WhatsApp:* +{telefono_limpio}\n"
        f"🕐 *Hora:* {_hora_actual()}\n\n"
        f"*Contexto de la conversacion:*\n{resumen}\n\n"
        "👆 _Seguimiento manual desde el numero principal de la agencia_"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
            if r.status_code == 200:
                logger.info(f"Notificacion Telegram enviada para lead {telefono_limpio}")
                return True
            else:
                logger.error(f"Error Telegram: {r.status_code} — {r.text}")
                return False
    except Exception as e:
        logger.error(f"Error enviando notificacion Telegram: {e}")
        return False


def _hora_actual() -> str:
    """Retorna la hora actual formateada."""
    from datetime import datetime
    return datetime.now().strftime("%d/%m/%Y %H:%M")
