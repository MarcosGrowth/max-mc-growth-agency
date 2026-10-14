#!/usr/bin/env bash
# Genera la voz en off (es-AR, Tomás) línea por línea desde lines.tsv.
# Requiere: pip install edge-tts. Usa el proxy del entorno si existe.
set -euo pipefail
cd "$(dirname "$0")/vo"
PROXY_ARGS=(); [ -n "${HTTPS_PROXY:-}" ] && PROXY_ARGS=(--proxy "$HTTPS_PROXY")
while IFS=$'\t' read -r id rate text; do
  edge-tts "${PROXY_ARGS[@]}" </dev/null --voice es-AR-TomasNeural --rate="$rate" --text "$text" --write-media "$id.mp3"
  ffmpeg -nostdin -v error -y -i "$id.mp3" -af "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse" -ar 48000 -ac 1 "$id.wav"
  printf "%s\t%s\n" "$id" "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$id.wav")"
done < lines.tsv
