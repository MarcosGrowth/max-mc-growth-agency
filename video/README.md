# Reel MC Growth — estudio de motion graphics

Reel vertical de 20 s (1080×1920, 30 fps) para Instagram, hecho con **Brag** (flujo, guion, share copy),
**Hyperframes** (composición, cámara 3D, texto cinético) y **Remotion** (piezas de datos reutilizables).

## Entregables
- `brag-output/brag.mp4` — video final con voz, música y efectos.
- `brag-output/brag.jpg` — portada (también es el cuadro 0 del video).
- `brag-output/share-copy.txt` — texto para publicar.
- `brag-output/brag-plan.md` — plan, storyboard y guion de voz con tiempos.
- `../docs/style_guide.md` — guía de estilo (referencias + marca de growth.mcmarketingdig.com).

## Estructura
- `audio/cues.json` — hoja única de tiempos (voz, momentos, efectos).
- `audio/vo/` — voz en off (es-AR, Tomás) línea por línea; `make_vo.sh` la regenera.
- `audio/build_audio.py` — música original generada por código + mezcla con ducking (−14 LUFS).
- `remotion/` — componentes `MaxAIChat` y `Embudo`; sus datos están en `remotion/src/data/*.json`.
- `brag-output/composition/` — composición de Hyperframes (`index.html` + assets).
- `render.sh` — rehace todo: audio → Remotion → check → render → portada.
- `review.sh` — hoja de contacto, prueba de teléfono a 360 px y costura del loop.

## Comandos
- Previsualizar: `cd video/brag-output/composition && npx hyperframes preview`
- Editar las piezas de datos: `cd video/remotion && npm run dev`
- Renderizar todo: `video/render.sh` (con `REGEN_VO=1` regenera la voz)

## Créditos de audio
Efectos de interfaz e impactos: paquete de Brag (Kenney, CC0). Música: original, generada por `build_audio.py`.
Voz: Microsoft Edge TTS, voz es-AR-TomasNeural (servicio en línea sin key; revisar sus términos para uso comercial).
