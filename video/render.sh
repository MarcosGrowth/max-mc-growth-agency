#!/usr/bin/env bash
# Render reproducible del reel MC Growth (9:16, 20 s).
# Pasos: voz → música/mezcla → piezas de Remotion → composición de Hyperframes → portada.
# Requisitos: Node 22+, ffmpeg, Python 3 con numpy/scipy/soundfile, edge-tts (solo para regenerar la voz).
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
COMP="$ROOT/brag-output/composition"

# 1) Voz en off (opcional: los WAV ya están en audio/vo). Usar REGEN_VO=1 para regenerarla.
if [ "${REGEN_VO:-0}" = "1" ]; then ./audio/make_vo.sh; fi

# 2) Música original + mezcla final (-14 LUFS)
python3 audio/build_audio.py
cp audio/out/mix.wav "$COMP/assets/audio/mix.wav"

# 3) Piezas de datos en Remotion (fondo transparente) + cuadros finales
cd remotion
[ -d node_modules ] || npm ci
export REMOTION_BROWSER="${REMOTION_BROWSER:-$(ls "$HOME"/.cache/hyperframes/chrome/chrome-headless-shell/*/chrome-headless-shell-linux64/chrome-headless-shell 2>/dev/null | head -1)}"
for c in MaxAIChat Embudo; do
  npx remotion render "$c" "$COMP/assets/clips/$c.webm" --codec=vp9 --image-format=png --pixel-format=yuva420p
done
npx remotion still MaxAIChat "$COMP/assets/img/chat_final.png" --frame=90 --image-format=png
npx remotion still Embudo "$COMP/assets/img/embudo_final.png" --frame=80 --image-format=png
for f in chat_final embudo_final; do convert "$COMP/assets/img/$f.png" -trim +repage "$COMP/assets/img/$f.png"; done
cd "$COMP"

# 4) Compuerta de calidad + render final
npx hyperframes check
npx hyperframes render --quality high --output ../brag.mp4

# 5) Portada (cuadro de "¿MÁS VENTAS?") fijada como cuadro 0
cd ..
ffmpeg -nostdin -v error -y -ss 2.7 -i brag.mp4 -frames:v 1 -q:v 2 brag.jpg
ffmpeg -nostdin -v error -y -i brag.mp4 -i brag.jpg \
  -filter_complex "[0:v][1:v]overlay=0:0:enable='eq(n,0)'[v]" -map "[v]" -map "0:a?" \
  -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p -c:a copy -movflags +faststart brag.poster.mp4
mv brag.poster.mp4 brag.mp4
echo "Listo: $ROOT/brag-output/brag.mp4"
