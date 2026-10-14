#!/usr/bin/env bash
# Render del reel 2 "Consultas que no compran": 3 versiones de gancho (h1, h2, h3), 9:16, 38 s.
# Pasos: voz (opcional) → música/mezclas → piezas de Remotion → subtítulos → check → render ×3 → portadas.
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
COMP="$ROOT/composition"
OUT="$ROOT/out"; mkdir -p "$OUT"

# 1) Voz con tiempos por palabra (los WAV ya están en audio/vo). REGEN_VO=1 la regenera.
if [ "${REGEN_VO:-0}" = "1" ]; then python3 audio/make_vo.py; fi
cp audio/vo/words.json ../video/remotion/src/data/reel2_words.json

# 2) Música + una mezcla por gancho
python3 audio/build_audio.py

# 3) Capítulos en Remotion (transparentes)
cd ../video/remotion
[ -d node_modules ] || npm ci
export REMOTION_BROWSER="${REMOTION_BROWSER:-$(ls "$HOME"/.cache/hyperframes/chrome/chrome-headless-shell/*/chrome-headless-shell-linux64/chrome-headless-shell 2>/dev/null | head -1)}"
for c in R2-Objetivo R2-Landing R2-MaxAI; do
  npx remotion render "$c" "$COMP/assets/clips/$c.webm" --codec=vp9 --image-format=png --pixel-format=yuva420p
done
cd "$ROOT"

# 4) Subtítulos tipo karaoke
python3 build_captions.py

# 5) Check + render de cada versión con su mezcla
cd "$COMP"
npx hyperframes check
for h in h1 h2 h3; do
  cp "$ROOT/audio/out/mix_$h.wav" assets/audio/mix.wav
  npx hyperframes render --quality "${QUALITY:-high}" --variables "{\"gancho\":\"$h\"}" --output "$OUT/reel2_$h.mp4"
  # portada = cuadro fuerte del gancho, fijada como cuadro 0
  ffmpeg -nostdin -v error -y -ss 2.3 -i "$OUT/reel2_$h.mp4" -frames:v 1 -q:v 2 "$OUT/reel2_$h.jpg"
  ffmpeg -nostdin -v error -y -i "$OUT/reel2_$h.mp4" -i "$OUT/reel2_$h.jpg" \
    -filter_complex "[0:v][1:v]overlay=0:0:enable='eq(n,0)'[v]" -map "[v]" -map "0:a?" \
    -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p -c:a copy -movflags +faststart "$OUT/tmp.mp4"
  mv "$OUT/tmp.mp4" "$OUT/reel2_$h.mp4"
done
cp "$ROOT/audio/out/mix_h1.wav" assets/audio/mix.wav
echo "Listo: $OUT"
