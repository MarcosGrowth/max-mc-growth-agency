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


async def notificar_lead_calificado(telefono: str, info: dict) -> bool:
    """
    Envía una notificación a Telegram cuando Max califica un lead.

    Args:
        telefono: Número del prospecto
        info: Dict con nombre, rubro, presupuesto, interes extraídos por Claude

    Returns:
        True si la notificación fue enviada exitosamente
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados — notificación omitida")
        return False

    telefono_limpio = telefono.replace("@s.whatsapp.net", "").replace("@c.us", "")

    nombre = info.get("nombre", "No indicó")
    rubro = info.get("rubro", "No indicó")
    presupuesto = info.get("presupuesto", "No indicó")
    interes = info.get("interes", "No indicó")

    mensaje = (
        "🔥 *LEAD CALIFICADO — MC Growth Agency*\n\n"
        f"📱 *WhatsApp:* +{telefono_limpio}\n"
        f"👤 *Nombre:* {nombre}\n"
        f"🏢 *Rubro:* {rubro}\n"
        f"💰 *Presupuesto en ads:* {presupuesto}\n"
        f"🎯 *Interés:* {interes}\n"
        f"🕐 *Hora:* {_hora_actual()}\n\n"
        "👆 _Hacer seguimiento desde el numero principal_"
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


async def notificar_nuevo_mensaje(telefono: str, mensaje: str) -> bool:
    """
    Avisa a Telegram cada vez que alguien le escribe a Max, calificado o no.
    Pensado como notificación rápida mientras no hay otro canal de atención en vivo.

    Args:
        telefono: Número del contacto
        mensaje: Texto que mandó
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados — notificación omitida")
        return False

    telefono_limpio = telefono.replace("@s.whatsapp.net", "").replace("@c.us", "")
    texto_corto = mensaje if len(mensaje) <= 300 else mensaje[:300] + "…"

    mensaje_telegram = (
        "💬 *Nuevo mensaje — MC Growth Agency*\n\n"
        f"📱 *WhatsApp:* +{telefono_limpio}\n"
        f"🗨️ *Dice:* {texto_corto}\n"
        f"🕐 *Hora:* {_hora_actual()}"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje_telegram,
        "parse_mode": "Markdown",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
            if r.status_code == 200:
                return True
            else:
                logger.error(f"Error Telegram (nuevo mensaje): {r.status_code} — {r.text}")
                return False
    except Exception as e:
        logger.error(f"Error enviando notificacion Telegram (nuevo mensaje): {e}")
        return False


def _hora_actual() -> str:
    """Retorna la hora actual formateada."""
    from datetime import datetime
    return datetime.now().strftime("%d/%m/%Y %H:%M")
