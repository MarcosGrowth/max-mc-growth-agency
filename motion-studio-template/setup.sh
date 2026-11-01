#!/usr/bin/env bash
# Instala todo lo necesario para el estudio (idempotente). Requiere Node 22+, Python 3.11+ y ffmpeg.
set -euo pipefail
cd "$(dirname "$0")"
echo "== Verificando requisitos"
node --version; python3 --version; ffmpeg -version | head -1
echo "== Paquetes de Python (voz, audio, transcripción, descarga de referencias)"
pip install -q edge-tts numpy scipy soundfile faster-whisper yt-dlp
echo "== Navegador para render de Hyperframes"
npx -y hyperframes browser ensure
echo "== Proyecto de Remotion"
(cd remotion && npm install)
echo "== Diagnóstico"
npx -y hyperframes doctor || true
echo "Listo. Remotion usa el navegador de Hyperframes: exportá REMOTION_BROWSER con la ruta del chrome-headless-shell si pide descargar otro."
