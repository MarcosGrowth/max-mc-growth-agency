#!/usr/bin/env bash
# Render del reel 3 "Que te compren" (9:16, 38 s).
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"; COMP="$ROOT/composition"; mkdir -p out
if [ "${REGEN_VO:-0}" = "1" ]; then python3 audio/make_vo.py; fi
cp audio/vo/words.json ../video/remotion/src/data/reel3_words.json
python3 build_data.py
python3 audio/build_audio.py && cp audio/out/mix.wav "$COMP/assets/audio/mix.wav"
cd ../video/remotion
[ -d node_modules ] || npm ci
export REMOTION_BROWSER="${REMOTION_BROWSER:-$(ls "$HOME"/.cache/hyperframes/chrome/chrome-headless-shell/*/chrome-headless-shell-linux64/chrome-headless-shell 2>/dev/null | head -1)}"
for c in R3-Rebote R3-Embudo; do npx remotion render "$c" "$COMP/assets/clips/$c.webm" --codec=vp9 --image-format=png --pixel-format=yuva420p; done
cd "$COMP"
npx hyperframes check
npx hyperframes render --quality "${QUALITY:-high}" --output "$ROOT/out/reel3.mp4"
cd "$ROOT"
ffmpeg -nostdin -v error -y -ss 29.8 -i out/reel3.mp4 -frames:v 1 -q:v 2 out/reel3.jpg
ffmpeg -nostdin -v error -y -i out/reel3.mp4 -i out/reel3.jpg -filter_complex "[0:v][1:v]overlay=0:0:enable='eq(n,0)'[v]" \
  -map "[v]" -map "0:a?" -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p -c:a copy -movflags +faststart out/tmp.mp4
mv out/tmp.mp4 out/reel3.mp4
echo "Listo: $ROOT/out/reel3.mp4"
