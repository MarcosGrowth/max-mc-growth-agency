# Motion Studio — plantilla

Estudio de motion graphics con Claude Code: **Brag + Hyperframes + Remotion**, voz en off con tiempos por
palabra, música original generada y revisión en 3 rondas. Una plantilla neutra: **un repositorio por marca**.

## Arrancar una marca nueva (5 pasos)
1. **Crear el repo de la marca** desde esta plantilla (en GitHub: botón *Use this template* → *Create a new repository*,
   nombre ej. `motion-<marca>`, privado). Si no es un template, descargá el ZIP y subilo a un repo nuevo.
2. **Completar `marca/marca.md`** y subir a `marca/assets/` el logo, las tipografías y, si querés personaje, una foto.
3. **Abrir un chat nuevo** de Claude Code sobre ese repositorio (no uses el chat de otra marca).
4. **Pegar el prompt** de `PROMPT_INICIAL.md` completando los corchetes y adjuntar las referencias.
5. **Aprobar el plan** que te propone; después construye, revisa, renderiza y sube todo.

## Estructura
- `CLAUDE.md` — reglas que Claude sigue en este repo (lee la ficha de marca primero).
- `marca/` — ficha de marca y archivos (la única fuente de estética).
- `.claude/skills/` — motion-reel, Hyperframes, Remotion y Brag.
- `tools/` — voz (`voz/make_vo.py`), audio (`audio/synth.py`) y revisión (`review.sh`).
- `plantillas/` — composición neutra, `build_data.py` y ejemplo de `build_audio.py`.
- `remotion/` — proyecto de Remotion para piezas de datos (UI animadas, gráficos).
- `proyectos/` — un subdirectorio por video.
- `setup.sh` — instala todo.

## Créditos
Efectos de sonido: paquete de Brag (Kenney, CC0). Música: generada por código. Voz: Microsoft Edge TTS
(servicio en línea sin key; para pauta paga conviene una voz con licencia comercial, por ejemplo ElevenLabs).
Remotion es gratis para equipos de hasta 3 personas; con 4 o más necesita licencia de empresa.
