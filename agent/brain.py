# agent/brain.py — Cerebro del agente Max: conexión con Claude API
# Generado por AgentKit para MC Growth Agency

"""
Lógica de IA del agente Max. Lee el system prompt de prompts.yaml
y genera respuestas usando la API de Anthropic Claude.
"""

import os
import yaml
import logging
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("agentkit")

# Cliente de Anthropic (usa la ANTHROPIC_API_KEY del .env)
client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def cargar_config_prompts() -> dict:
    """Lee toda la configuración desde config/prompts.yaml."""
    try:
        with open("config/prompts.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.error("config/prompts.yaml no encontrado")
        return {}


def cargar_system_prompt() -> str:
    """Lee el system prompt de Max desde config/prompts.yaml."""
    config = cargar_config_prompts()
    return config.get(
        "system_prompt",
        "Sos Max, el asistente de MC Growth Agency. Respondé siempre en español."
    )


def obtener_mensaje_error() -> str:
    """Retorna el mensaje de error configurado en prompts.yaml."""
    config = cargar_config_prompts()
    return config.get(
        "error_message",
        "Lo siento, estoy teniendo un problema técnico en este momento. En unos minutos te escribo yo para asegurarme de que te atendemos bien."
    )


def obtener_mensaje_fallback() -> str:
    """Retorna el mensaje de fallback configurado en prompts.yaml."""
    config = cargar_config_prompts()
    return config.get(
        "fallback_message",
        "Disculpá, no entendí bien tu mensaje. ¿Podés contarme un poco más sobre lo que necesitás?"
    )


async def generar_respuesta(mensaje: str, historial: list[dict]) -> str:
    """
    Genera una respuesta usando Claude API.

    Args:
        mensaje: El mensaje nuevo del prospecto
        historial: Lista de mensajes anteriores [{"role": "user/assistant", "content": "..."}]

    Returns:
        La respuesta generada por Max (Claude)
    """
    # Si el mensaje es muy corto o vacío, usar fallback
    if not mensaje or len(mensaje.strip()) < 2:
        return obtener_mensaje_fallback()

    system_prompt = cargar_system_prompt()

    # Construir mensajes para la API: historial + mensaje actual
    mensajes = []
    for msg in historial:
        mensajes.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Agregar el mensaje actual del prospecto
    mensajes.append({
        "role": "user",
        "content": mensaje
    })

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=mensajes
        )

        respuesta = response.content[0].text
        logger.info(
            f"Respuesta generada — "
            f"tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out"
        )
        return respuesta

    except Exception as e:
        logger.error(f"Error Claude API: {e}")
        return obtener_mensaje_error()
