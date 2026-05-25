# agent/providers/meta.py — Adaptador para Meta WhatsApp Cloud API
# Generado por AgentKit para MC Growth Agency

import os
import logging
import httpx
from fastapi import Request
from agent.providers.base import ProveedorWhatsApp, MensajeEntrante

logger = logging.getLogger("agentkit")


class ProveedorMeta(ProveedorWhatsApp):
    """Proveedor de WhatsApp usando la API oficial de Meta (Cloud API)."""

    def __init__(self):
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("META_PHONE_NUMBER_ID")
        self.verify_token = os.getenv("META_VERIFY_TOKEN", "mcgrowth-webhook-2026")
        self.api_version = "v21.0"

    async def validar_webhook(self, request: Request) -> int | None:
        """Meta requiere verificación GET con hub.verify_token."""
        params = request.query_params
        mode = params.get("hub.mode")
        token = params.get("hub.verify_token")
        challenge = params.get("hub.challenge")
        if mode == "subscribe" and token == self.verify_token:
            logger.info("Webhook de Meta verificado correctamente")
            return int(challenge)
        logger.warning(f"Verificación de webhook fallida — token recibido: {token}")
        return None

    async def parsear_webhook(self, request: Request) -> list[MensajeEntrante]:
        """Parsea el payload anidado de Meta Cloud API."""
        body = await request.json()
        mensajes = []
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    if msg.get("type") == "text":
                        mensajes.append(MensajeEntrante(
                            telefono=msg.get("from", ""),
                            texto=msg.get("text", {}).get("body", ""),
                            mensaje_id=msg.get("id", ""),
                            es_propio=False,
                        ))
                    elif msg.get("type") == "audio":
                        # Audio recibido — por ahora lo ignoramos con mensaje amigable
                        mensajes.append(MensajeEntrante(
                            telefono=msg.get("from", ""),
                            texto="[El usuario envió un audio]",
                            mensaje_id=msg.get("id", ""),
                            es_propio=False,
                        ))
        return mensajes

    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        """Envía mensaje via Meta WhatsApp Cloud API."""
        if not self.access_token or not self.phone_number_id:
            logger.warning("META_ACCESS_TOKEN o META_PHONE_NUMBER_ID no configurados")
            return False

        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": telefono,
            "type": "text",
            "text": {"body": mensaje},
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(url, json=payload, headers=headers)
                if r.status_code != 200:
                    logger.error(f"Error Meta API: {r.status_code} — {r.text}")
                    return False
                return True
        except httpx.TimeoutException:
            logger.error("Timeout al enviar mensaje via Meta API")
            return False
        except Exception as e:
            logger.error(f"Error inesperado enviando mensaje: {e}")
            return False
