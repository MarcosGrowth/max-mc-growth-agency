# api/index.py — Entrypoint serverless para Vercel
# Vercel detecta la variable "app" (ASGI) y sirve el FastAPI existente sin cambios.

from agent.main import app
