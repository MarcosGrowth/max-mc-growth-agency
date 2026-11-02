# Prompt para un chat nuevo de Claude Code (marca nueva)

Antes: creá en GitHub un repositorio privado nuevo (ej. `motion-<marca>`) tildando **"Add a README file"**,
y abrí un chat nuevo de Claude Code sobre ese repositorio. Después pegá esto:

---

Quiero montar en este repositorio un estudio de motion graphics para una marca nueva. Yo no programo: instalá todo y decime qué hacer solo cuando haga falta algo mío.

1. Traé la plantilla del estudio. Está en el repositorio `MarcosGrowth/max-mc-growth-agency`, rama `claude/awesome-babbage-uhmxd1`, carpeta `motion-studio-template/`. Agregá ese repositorio a la sesión solo con acceso de lectura y copiá **únicamente el contenido de esa carpeta** a la raíz de este repositorio, incluida la carpeta oculta `.claude`. No leas ni copies nada más de ese repositorio: el resto es de otra marca y no tiene que influir en este proyecto.
2. Leé `CLAUDE.md` y `README.md` de la plantilla y seguí sus reglas desde ahora.
3. Corré `./setup.sh` y avisame si algo falla. Si una descarga queda bloqueada por la red del entorno, decime qué dominio tengo que habilitar.
4. Hacé commit y push de la plantilla instalada.
5. Pedime **todos juntos, en un solo mensaje**, los datos de la ficha `marca/marca.md`: nombre, Instagram, sitio web, a qué se dedica, cliente ideal, colores, tipografías, logo, estilo visual, qué no va con la marca, si quiero personaje o persona, propuesta de valor, servicios, oferta o CTA real, botón de Meta Ads, qué se puede y qué no se puede decir, voz y música. Decime también qué archivos tengo que subir (logo, tipografías, foto).
6. Con mis respuestas completá `marca/marca.md`, guardá los archivos en `marca/assets/` y, si hay sitio web, revisalo para sacar textos y servicios reales. Hacé commit y push.
7. Cuando esté todo, decime en tres líneas qué quedó listo y pedime el primer video: tema, referencias, duración y si va a pauta. Desde ahí usá la skill motion-reel: guía de estilo, plan y esperá mi aprobación antes de construir.

---

## Para cada video nuevo de esa marca (mismo chat o uno nuevo sobre ese repo)

Usá motion-reel para un reel nuevo sobre [TEMA]. Referencias: [adjuntas o links] — me gusta [qué]. Duración: [X] s, formato reel 9:16, [orgánico / para Meta Ads con el botón "…"]. Voz: [sí, rioplatense / no]. Música: creala. Pedime lo que falte todo junto y mostrame el plan antes de construir.
