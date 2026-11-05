# Reel 4 — Manifiesto tipográfico (9:16, 13 s)

"No hacemos solo anuncios. Construimos sistemas." + ráfaga de palabras del sistema → "crecimiento." → logo con glitch
y despegue → CTA "Solicitar diagnóstico" + "Tocá «Más información»". Sin voz: cada cuadro cae en un golpe de la música.

- `timeline.json` — los cuadros (segundo, fondo negro/naranja, líneas; `*palabra*` = acento) y los tiempos del logo y el CTA.
  Cambiando esta lista sale otra versión (por servicio, por industria).
- `audio/build_audio.py` — música generada a partir de los mismos tiempos (usa `motion-studio-template/tools/audio/synth.py`).
- `build_data.py` → `composition/assets/data.js`; `composition/index.html` — composición de Hyperframes.
- `out/manifiesto.mp4` y `out/manifiesto.jpg` (portada fijada como cuadro 0).

Rehacer: `python3 build_data.py && python3 audio/build_audio.py && cp audio/out/mix.wav composition/assets/audio/ && (cd composition && npx hyperframes render --quality high --output ../out/manifiesto.mp4)`
