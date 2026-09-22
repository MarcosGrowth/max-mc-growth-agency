# MC Growth OS — guía base para replicar clientes

Este repositorio es la base del producto. Cada cliente debe tener su propia instancia de Render, su propia base PostgreSQL y sus propias credenciales de Meta/Anthropic.

## Arquitectura recomendada

```text
WhatsApp API del cliente
        ↓
     Max + FastAPI
        ↓
  PostgreSQL del cliente
        ↓
 Dashboard privado + Telegram
```

El número humano del cliente puede seguir funcionando en WhatsApp Business App para el seguimiento manual. La instancia de Max usa un número API separado, salvo que el cliente contrate una solución de coexistencia mediante un BSP/Tech Provider.

## Crear una instancia nueva

1. Duplicar este repositorio para el cliente.
2. Crear un servicio web independiente en Render conectado al repositorio.
3. Crear un proyecto PostgreSQL independiente, por ejemplo en Supabase.
4. Cargar las variables de entorno del cliente en Render.
5. Configurar `config/business.yaml`, `config/prompts.yaml` y la carpeta `knowledge/`.
6. Crear el número de WhatsApp Cloud API y configurar el webhook.
7. Configurar el bot de Telegram y su `TELEGRAM_CHAT_ID`.
8. Definir `DASHBOARD_USERNAME` y una contraseña única.
9. Probar salud, login, conversación, lead calificado, Telegram, dashboard y exportaciones.

## Checklist antes de entregar una instancia

- Confirmar que `/api/system/status` informa `PostgreSQL` y `production`.
- Enviar una conversación de prueba y verificar que queda visible en **Bandeja**.
- Verificar extracción de nombre, rubro, presupuesto, interés y sentimiento.
- Confirmar recepción de Telegram y carga del lead en **Pipeline**.
- Probar **Seguimiento**, **Datos comerciales**, **Pausar Max**, **Cerrar**, **Descartar** y exportación CSV.
- Configurar una rutina de backup del proyecto PostgreSQL antes de comenzar campañas reales.
- Guardar en un inventario privado los IDs y nombres de cada canal; nunca poner tokens en el repositorio.

El endpoint autenticado `/api/system/status` confirma el entorno y si la instancia está usando PostgreSQL o SQLite, sin mostrar credenciales.

## Variables mínimas de producción

```env
ANTHROPIC_API_KEY=
WHATSAPP_PROVIDER=meta
META_ACCESS_TOKEN=
META_PHONE_NUMBER_ID=
META_VERIFY_TOKEN=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DATABASE_URL=postgresql+asyncpg://...
ENVIRONMENT=production
DASHBOARD_USERNAME=
DASHBOARD_PASSWORD=
```

## Regla de datos

En producción nunca usar SQLite. Render puede reemplazar el disco local durante un deploy o reinicio. PostgreSQL es la fuente permanente para leads, conversaciones, estados y canales.

## Flujo comercial

```text
Lead escribe → Max conversa → se guarda todo el chat
       ↓
Se califica → Telegram avisa → aparece en seguimiento
       ↓
Comercial responde desde su WhatsApp Business
       ↓
El equipo marca cerrado, descartado o mantiene seguimiento
```

## Canales

- WhatsApp Cloud API: disponible para Max.
- Instagram/Facebook: requieren app, permisos y webhooks de Meta.
- WhatsApp Business App + Cloud API en el mismo número: requiere Embedded Signup habilitado para BSP/Tech Provider; no asumirlo como función gratuita de una app común.

## Cambios del núcleo

Las mejoras generales del dashboard se hacen en este repositorio base. Luego se publican por Git y se actualizan las instancias de clientes después de probarlas en MC Growth OS.

Las credenciales, prompts, datos de negocio y bases de datos nunca se comparten entre clientes.

## Alcance actual del producto

El núcleo está listo para operar con WhatsApp Cloud API: calificación, memoria, Telegram, sentimiento,
pipeline, conversaciones, notas internas, control humano y exportación. Instagram y Facebook quedan como
integraciones posteriores porque su puesta en producción depende de la verificación, permisos y revisión de
Meta de cada aplicación. No deben bloquear la entrega inicial de un cliente por WhatsApp.
