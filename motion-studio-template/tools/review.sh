#!/usr/bin/env bash
# Revisión visual: hoja de contacto, prueba de teléfono a 360 px y costura del loop.
# Uso: video/review.sh <video.mp4> <carpeta-salida>
set -euo pipefail
IN="$1"; OUT="$2"; mkdir -p "$OUT"
# Hoja de contacto: un cuadro cada 0.5 s (40 cuadros), con el tiempo impreso
ffmpeg -nostdin -v error -y -i "$IN" -vf "fps=${CONTACT_FPS:-2},scale=216:-1,drawtext=text='%{pts\:hms}':x=6:y=6:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.6,tile=8x5" -frames:v 1 "$OUT/contact.jpg"
# Prueba de teléfono: cuadros clave a 360 px de ancho
for t in ${PHONE_TIMES:-1.6 2.6 4.8 8.9 10.9 12.5 13.5 14.4 15.2 16.8 18.6 19.5}; do
  ffmpeg -nostdin -v error -y -ss "$t" -i "$IN" -frames:v 1 -vf scale=360:-1 "$OUT/phone_$t.png"
done
montage "$OUT"/phone_*.png -tile 6x2 -geometry +6+6 -background '#222' "$OUT/phone.png" 2>/dev/null || convert "$OUT"/phone_*.png +append "$OUT/phone.png"
# Costura del loop: últimos 3 cuadros + primeros 3
N=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$IN")
ffmpeg -nostdin -v error -y -i "$IN" -vf "select='gte(n\,$((N-3)))+lt(n\,3)',scale=270:-1,tile=6x1" -vsync vfr -frames:v 1 "$OUT/seam.jpg"
echo "ok: $OUT"
