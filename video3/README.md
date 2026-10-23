# Reel 3 — "Que te compren" (9:16, 38 s, para Meta Ads)

Adaptación de la referencia (plano continuo, narración tranquila) a la oferta de MC Growth, sin precios ni cifras.
Contraste → sistema entero → diagnóstico gratis → videollamada → "Que te compren." + CTA.
El personaje 3D de Marcos (3 poses) se generó en Canva a partir de su foto: `composition/assets/img/presentador.png`, `llamada.jpg` y `pulgar.png`
(diseño de trabajo en Canva: "Personaje MC Growth — exportación").

## Entregables (out/)
- `reel3.mp4` — video final (portada fijada como cuadro 0).
- `reel3.jpg` — portada (el personaje en la llamada con los chips "Gratis / Sin compromiso").
- `ad-copy.md` — textos para el anuncio.

## Cómo está hecho
- `audio/make_vo.py` — voz (Tomás es-AR) con tiempos por palabra → `audio/vo/words.json`.
- `timeline.json` — inicio de cada línea, escenas, frases y palabras en cursiva.
- `build_data.py` — frases, tiempos y envolvente de la voz → `composition/assets/data.js`.
- `audio/build_audio.py` — música original cálida + efectos + voz → `audio/out/mix.wav` (−14 LUFS).
- Remotion (`../video/remotion/src/reel3/`): `R3-Rebote` (personas que rebotan) y `R3-Embudo` (sistema de 4 etapas).
- Hyperframes (`composition/index.html`): prompt, anuncio, tachado, presentador junto al embudo, diagnóstico, llamada con aro que late con la voz y cierre con el personaje.
- `render.sh` — rehace todo.
