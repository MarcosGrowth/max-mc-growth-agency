# Prompt para arrancar un chat nuevo

Copiá y pegá esto como primer mensaje en un chat nuevo de Claude Code abierto **sobre este repositorio**
(después de completar `marca/marca.md` y subir los archivos a `marca/assets/`).
Adjuntá también los videos o imágenes de referencia.

---

```
Usá motion-reel para hacer un reel de [TEMA / QUÉ QUERÉS COMUNICAR].

Marca: leé marca/marca.md y los archivos de marca/assets/ ANTES de proponer nada. Usá solo esa marca.
Referencias: [adjuntas y/o links de Instagram]. Me gusta de ellas: [ritmo / animaciones / voz / storytelling / estética].
Duración: [15 / 20 / 30 / 40] segundos. Formato: [reel 9:16 / también 4:5 o 16:9].
Uso: [orgánico / lo voy a promocionar en Meta Ads con el botón "…"].
Voz en off: [sí, español rioplatense / no]. Música: [creala / uso este archivo].

Primero instalá lo que falte corriendo ./setup.sh y decime solo si necesitás algo mío.
Después pedime los datos que falten, todos juntos, armá la guía de estilo y el plan, y no construyas
hasta que lo apruebe. Usá las 3 herramientas (Brag, Hyperframes y Remotion) donde aporten.
Al terminar: video final, portada, textos para el anuncio, y subí todo al repo.
```

---

## Qué tenés que tener listo antes de pegarlo
1. `marca/marca.md` completo (mínimo: nombre, colores, tipografías, logo, propuesta de valor, CTA real).
2. En `marca/assets/`: logo (PNG transparente o SVG), tipografías (.woff2/.ttf) si no son de Google Fonts,
   y la foto si querés un personaje o una persona en el video.
3. Las referencias: subí los videos al chat o pegá los links.
4. Si va a pauta: qué botón vas a usar en Meta y si la oferta es gratis / tiene precio (sin precio, no se menciona).
5. Opcional: key de ElevenLabs en `.env` si querés una voz con licencia comercial.

## Para un video nuevo de la misma marca
Mismo chat o uno nuevo sobre este repo: "Usá motion-reel para un reel nuevo sobre [tema], con estas referencias…".
La marca ya está en la ficha; no hace falta repetirla.

## Para otra marca distinta
Hacé **otro repositorio** desde esta plantilla (ver README) y abrí **otro chat**. No mezcles marcas en un mismo repo ni en un mismo chat.
