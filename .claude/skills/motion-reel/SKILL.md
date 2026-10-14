---
name: motion-reel
description: Hace un video de motion graphics renderizado desde código, eligiendo la herramienta correcta entre Brag, Hyperframes y Remotion. Úsala cuando el usuario pida un video de lanzamiento, un reel de producto, un showreel, un explicador animado, un anuncio en motion o una serie de videos con datos.
---

# Motion reel

## Datos que se piden primero (todos juntos, una sola vez)
Qué se va a mostrar (proyecto, URL o tema), duración, formatos (9:16 / 1:1 / 16:9), el tono, una
referencia (un frame, un video o una carpeta de imágenes) y la música (un archivo o "créala").

## Elegir la herramienta
- Lanzamiento de un proyecto o un sitio, de 15 a 25 segundos: /brag. En Opus 5.5 pasa solo a brag-slim.
  Si el usuario quiere voz, usar /brag --full --voice.
- Video a medida, más largo o que no es un lanzamiento: /hyperframes.
- Una serie, una plantilla o videos que cambian según datos: Remotion con /remotion-create.
Decir en una línea cuál se eligió y por qué.

## Proceso
1. Si hay referencia, escribir docs/style_guide.md (ritmo, cortes, textura, cómo entra el texto) y
   enseñarla. Los colores y las tipografías salen del proyecto, no de la referencia.
2. Escribir el plan (ángulo, gancho, escenas con duración) y esperar el visto bueno antes de construir.
3. Construir con la herramienta elegida y pasar su compuerta: npx hyperframes check en Hyperframes y
   Brag, un frame con npx remotion still en Remotion.
4. Con ffmpeg, generar una hoja de contacto, una prueba de teléfono a 360 px y la costura del loop.
   Mirarlas, calificar del 1 al 10 y arreglar los 3 peores problemas. Mínimo 3 rondas.
5. Render final en los formatos pedidos.
6. Entregar el video, la portada y el texto para compartir. Decir qué se mejoraría después.

## Reglas duras
- Solo la interfaz real del producto. Nunca inventes pantallas, cifras ni testimonios.
- Todo frame es función pura del tiempo: nada de timers, de transiciones que corran solas ni de Math.random.
- Cada 2 a 4 segundos pasa algo nuevo.
- Prohibido: etiquetas en las esquinas, marcos, título centrado sobre degradado, todo entrando con fade.
- Las llaves van en .env, nunca en un prompt.
- Remotion es gratis hasta 3 personas por empresa; con 4 o más, avisar de la licencia.
