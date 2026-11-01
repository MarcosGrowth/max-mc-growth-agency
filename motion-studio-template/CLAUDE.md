# Estudio de motion graphics — instrucciones para Claude

Este repositorio produce reels y videos de motion graphics **para una sola marca**: la que está en `marca/marca.md`.

## Reglas de marca (lo primero, siempre)
1. Antes de diseñar, escribir código o proponer nada visual, **leé `marca/marca.md` completo** y mirá `marca/assets/`.
2. Usá **solo** los colores, tipografías, logo, tono, oferta y CTA de esa ficha. No traigas estilos de otras marcas,
   de otros proyectos ni de conversaciones anteriores.
3. Si la ficha tiene campos vacíos que necesitás, **preguntá todo junto, una sola vez**, antes de construir.
4. Si la ficha dice un sitio web, inspeccionalo para sacar textos y servicios reales. Nunca inventes cifras,
   resultados, testimonios, precios ni datos de contacto.

## Herramientas (ya instaladas en `.claude/skills/`)
- **motion-reel**: punto de entrada. Pide los datos, elige herramienta, guía de estilo → plan → construir → revisar 3 rondas.
- **Hyperframes**: composición principal en HTML/GSAP (`npx hyperframes check`, `snapshot`, `render`).
- **Remotion** (`remotion/`): piezas de datos e interfaces animadas, render transparente que se inserta en Hyperframes.
- **Brag**: guion de lanzamiento, efectos de sonido CC0 (`.claude/skills/brag/assets/sfx`) y texto para compartir.
- `tools/voz/make_vo.py`: voz en off con tiempos por palabra (Edge TTS; variable `VOZ`).
- `tools/audio/synth.py`: música original y efectos sintetizados, ducking y mezcla a −14 LUFS.
- `tools/review.sh`: hoja de contacto, prueba de teléfono a 360 px y costura del loop.
- `plantillas/`: composición neutra, `build_data.py` (frases palabra por palabra) y `build_audio_ejemplo.py`.

## Cómo se organiza un reel
Cada video va en `proyectos/<nombre-del-reel>/` con: `timeline.json`, `audio/vo/lines.tsv`, `audio/build_audio.py`,
`build_data.py`, `composition/` (copia de `plantillas/composicion/`), `out/` (video final + portada) y `README.md`.
Las piezas de Remotion de ese reel van en `remotion/src/<nombre-del-reel>/`.

## Proceso (motion-reel)
1. Analizar referencias → `proyectos/<reel>/style_guide.md`.
2. Plan (ángulo, gancho, escenas con tiempos, guion de voz) → **esperar aprobación**.
3. Voz → tiempos → música y mezcla → piezas de Remotion → composición → `npx hyperframes check`.
4. Render borrador → `tools/review.sh` → calificar 1–10 → arreglar los 3 peores problemas. Mínimo 3 rondas.
5. Render final, portada fijada como cuadro 0, texto para compartir.

## Reglas técnicas
- 9:16 = 1080×1920, 30 fps. Zona segura de anuncios: contenido importante entre y=270 y y=1250.
- Todo determinista: nada de `Math.random` sin semilla, relojes ni red en el render. GSAP local en `assets/vendor/`.
- Tipografías locales con `@font-face`. Textos de lectura ≥ 28 px.
- Las keys van en `.env`, nunca en el código ni en el chat.
- Commit y push al terminar cada entrega.
