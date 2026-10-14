# Reel 2 — "Consultas que no compran" (9:16, 38 s, para Meta Ads)

Video educativo con foco en conversión: 3 errores (objetivo, landing, respuesta) → "Es el sistema" → CTA
"Solicitar diagnóstico" + "Tocá «Más información»". Tres versiones de gancho para testear en Meta.

## Entregables (out/)
- `reel2_h1.mp4` — "¿Tus anuncios te traen consultas… que no compran?"
- `reel2_h2.mp4` — "¿Pagás pauta para que te pregunten precio… y desaparezcan?"
- `reel2_h3.mp4` — "Tres errores que hacen que tu anuncio traiga curiosos."
- `reel2_h*.jpg` — portadas (también son el cuadro 0 de cada video).
- `../video2/ad-copy.md` — textos para el anuncio.

## Cómo está hecho
- **Voz:** `audio/make_vo.py` (Tomás es-AR) guarda cada línea y los tiempos de cada palabra en `audio/vo/words.json`.
- **Tiempos:** `timeline.json` (inicio de cada línea, escenas, palabras resaltadas, cortes de subtítulos).
- **Música y mezclas:** `audio/build_audio.py` → `audio/out/mix_h1|h2|h3.wav` (−14 LUFS).
- **Remotion** (`../video/remotion/src/reel2/`): capítulos `R2-Objetivo`, `R2-Landing`, `R2-MaxAI`, sincronizados con las palabras.
- **Subtítulos:** `build_captions.py` → `composition/assets/captions.js`.
- **Hyperframes** (`composition/index.html`): variable `gancho` (h1/h2/h3), subtítulos tipo karaoke, glitch, capítulos, remate y CTA.
- **Render completo:** `video2/render.sh` (`REGEN_VO=1` para regenerar la voz, `QUALITY=draft` para pruebas).

## Zona segura de anuncios
Todo lo importante entre y=270 y y=1250 (Meta tapa el 14 % superior y el 35 % inferior en Reels).
