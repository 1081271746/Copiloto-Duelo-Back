# Co-Piloto de Duelo — Backend

API en Python y FastAPI para acompañamiento emocional durante el duelo. Incluye diario privado, reflexión mediante Groq, biblioteca de ejercicios, seguimiento, alertas y eventos privados mediante WebSockets y Redis Pub/Sub.

**No sustituye psicología, psiquiatría, terapia ni atención médica. No realiza diagnósticos y no contacta automáticamente a emergencias.** Las cinco categorías del duelo son referencias opcionales y no lineales; no son una escala de recuperación ni etapas obligatorias.

Este repositorio contiene exclusivamente el backend. La documentación interactiva de FastAPI no es un frontend del producto.

## 1. Requisitos

- Python 3.12 o posterior.
- Redis real en ejecución. No se usa un sustituto en memoria.
- Una clave propia de Groq para realizar análisis reales.
- Dependencias de `requirements.txt`.

La disponibilidad de un modelo y sus cuotas dependen de la cuenta de Groq. No se garantiza acceso gratuito ni una cuota estudiantil. `GROQ_MODEL` permite seleccionar un modelo habilitado en tu cuenta.

Para obtener una clave, inicia sesión en [Groq Console](https://console.groq.com/), abre [API Keys](https://console.groq.com/keys) y crea una clave para este backend. Guárdala únicamente como `GROQ_API_KEY` en tu `.env` local o gestor de secretos. Nunca la envíes al frontend, la pegues en documentación ni la subas a Git.

## 2. Ejecutar localmente

Desde la raíz de este repositorio:

```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

Edita `.env`. Configura `GROQ_API_KEY` si vas a realizar análisis; puede permanecer vacía para trabajar con el resto del backend. Configura `JWT_SECRET` con al menos 32 caracteres aleatorios. Puedes generar un valor localmente:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Guárdalo únicamente en `.env` o en un gestor de secretos; no lo publiques. En Replit también se admite el secreto existente `SESSION_SECRET` como respaldo cuando `JWT_SECRET` está vacío.

Inicia Redis en otra terminal:

```bash
redis-server --bind 127.0.0.1 --port 6379 --save "" --appendonly no
redis-cli ping
```

La respuesta esperada al segundo comando es `PONG`. Redis solo gestiona eventos, coordinación y límites; la información permanente se almacena en SQL. No expongas Redis directamente a Internet. Para instalaciones remotas configura autenticación, TLS y una red privada.

Inicializa la base y la biblioteca:

```bash
python -m seed
```

Inicia la API:

```bash
python -m uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --ws-max-size 16384 --no-access-log
```

- Documentación Swagger: `http://localhost:8000/api/docs`
- Documentación ReDoc: `http://localhost:8000/api/redoc`
- Contrato OpenAPI generado por FastAPI: `http://localhost:8000/api/openapi.json`
- Salud: `http://localhost:8000/api/healthz`
- WebSocket: `ws://localhost:8000/api/ws`

La aplicación inicializa las tablas inexistentes y la biblioteca al arrancar. La inicialización es idempotente; no altera esquemas preexistentes. Antes de ejecutar varias instancias contra una base nueva, ejecuta `python -m seed` una sola vez.

## 3. Variables de entorno

| Variable | Uso |
|---|---|
| `APP_ENV` | Etiqueta del entorno; por defecto `development` |
| `APP_DATABASE_URL` | Por defecto `sqlite:///./copilot.db`; separada de conexiones heredadas de la plataforma |
| `JWT_SECRET` | Secreto JWT de al menos 32 caracteres; obligatorio fuera del respaldo `SESSION_SECRET` |
| `JWT_ISSUER` / `JWT_AUDIENCE` | Emisor y audiencia verificados de los tokens |
| `ACCESS_TOKEN_MINUTES` | Duración de acceso; por defecto 30 minutos |
| `REDIS_URL` | Conexión Redis; por defecto base 0 en `127.0.0.1:6379` |
| `CORS_ORIGINS` | Orígenes explícitos separados por comas; inicialmente `http://localhost:4200` |
| `GROQ_API_KEY` | Clave propia de Groq; vacía deshabilita únicamente el análisis |
| `GROQ_MODEL` | Modelo configurable; inicialmente `openai/gpt-oss-120b` |
| `GROQ_TIMEOUT_SECONDS` | Tiempo máximo total de la llamada a Groq; inicialmente 20 |
| `GROQ_REQUESTS_PER_MINUTE` | Límite global compartido para ese modelo; inicialmente 5 |
| `AI_DAILY_USER_LIMIT` | Máximo de intentos de análisis por usuario y día UTC; inicialmente 20 |
| `DEFAULT_COUNTRY` | País del seed de demostración; inicialmente `CO` |
| `EMERGENCY_RESOURCES_JSON` | Recursos de emergencia por código de país |
| `DEMO_PASSWORD` | Contraseña local para crear usuarios ficticios mediante `--demo`; sin valor predeterminado |
| `TEST_REDIS_URL` | Redis local exclusivo de pruebas, obligatoriamente base 15 |

Cada usuario configura su país mediante registro o edición de perfil. Se usa el país del usuario para la orientación de seguridad, no geolocalización automática. En el ejemplo colombiano se incluye el número general de emergencias `123` y un enlace oficial; **no se afirma que exista una línea especializada disponible en todos los territorios**. El responsable de la instalación debe verificar y mantener los recursos de cada ubicación. Un país sin configuración recibe orientación para acudir a urgencias o consultar su número local.

## 4. Datos ficticios

La biblioteca contiene seis ejercicios de ejemplo y tres recursos. Los ejercicios permiten detener la actividad si aumenta el malestar; no se exige aceptar la pérdida ni cerrar el duelo.

Para crear además dos perfiles ficticios y sus entradas, análisis, una actividad realizada y una alerta:

1. Define `DEMO_PASSWORD` en tu `.env` local.
2. Ejecuta:

```bash
python -m seed --demo
```

Se crean `demo1@example.com` y `demo2@example.com`. La contraseña no se imprime ni se guarda en el repositorio. Los análisis del seed están marcados `seed-fixture-not-gemini`: son datos ficticios, no resultados reales de IA. Repetir el comando no duplica los datos ni cambia contraseñas existentes. No ejecutes este seed en producción.

## 5. Autenticación y aislamiento

El cliente envía:

```http
Authorization: Bearer <access_token>
```

- Registro con email normalizado y contraseña de 12 a 128 caracteres.
- Hash Argon2id, nunca contraseñas en texto plano.
- JWT HS256 con algoritmo fijo, expiración, emisor, audiencia, identificador de sesión y versión del usuario.
- Las sesiones se guardan en SQL. Cerrar sesión revoca ese token.
- Cambiar contraseña invalida todos los tokens anteriores del usuario.
- No hay token de refresco: al expirar, el usuario vuelve a iniciar sesión.
- Las consultas privadas filtran siempre por usuario. Un identificador ajeno responde `404`.
- Registro: 10 solicitudes por IP/minuto. Login: 20 solicitudes por IP/minuto. Ambos límites son compartidos mediante Redis y fallan explícitamente si no se puede aplicar el límite.
- No se añadieron roles administrativos: no hay una función de moderación ni acceso al diario de otras personas.

Si hay un proxy delante de la API, configura correctamente qué encabezados reenviados son confiables. No confíes en encabezados arbitrarios del cliente para determinar la IP. No habilites CORS con `*`.

## 6. Arquitectura

```text
app/
  ai/             Cliente Groq mediante HTTPX, sin acceso a la base de datos
  core/           Configuración, dependencias y errores
  database/       SQLAlchemy, sesiones y claves foráneas
  models/         Entidades y relaciones SQL
  repositories/   Consultas privadas reutilizables
  schemas/        Contratos y validación Pydantic
  security/       JWT, sesiones y Argon2id
  services/       Diario, seguridad, análisis, biblioteca, seguimiento y Redis
  routers/        Endpoints HTTP
  websocket/      Autenticación y administrador de conexiones
  main.py         Factoría de aplicación e inicialización
seed/             Biblioteca y datos ficticios explícitos
tests/            Pruebas con SQLite temporal, Redis real y Groq controlado
```

Patrones aplicados:

- **Repository** para búsquedas privadas consistentes y aislamiento.
- **Service Layer** para reglas de negocio y coordinación.
- **Dependency Injection** de FastAPI para usuario y sesión; el analizador se inyecta en la aplicación y se reemplaza en pruebas.
- **Factory** mediante `create_app`, que permite configurar instancias independientes.
- **Publish/Subscribe y Fan-Out** con Redis para distribuir eventos entre procesos.

No se añadieron jerarquías de estrategias ni patrones decorativos sin una necesidad concreta.

## 7. Análisis con Groq

`app/ai/groq.py` implementa `GroqAnalyzer` mediante HTTPX asíncrono, autenticación Bearer y `https://api.groq.com/openai/v1/chat/completions`. No se necesita el SDK de OpenAI ni el SDK de Groq.

El modelo inicial `openai/gpt-oss-120b` figura en el [catálogo oficial](https://console.groq.com/docs/model/openai/gpt-oss-120b) y admite [salida estructurada](https://console.groq.com/docs/structured-outputs). Se solicita `json_schema` con `strict: true` para este modelo y `openai/gpt-oss-20b`, usando el esquema `AnalysisResult` existente sin modificarlo. `openai/gpt-oss-safeguard-20b` usa `json_schema` de mejor esfuerzo. Otros modelos configurados usan `json_object` con el esquema en las instrucciones y la misma validación Pydantic obligatoria; verifica que el modelo elegido admita ese modo. No hay reintentos automáticos ni degradación silenciosa si el proveedor rechaza el formato.

La documentación acredita compatibilidad del modelo, no disponibilidad ni cuota en una cuenta particular. Las pruebas no realizan llamadas reales.

El análisis se solicita explícitamente después de guardar una entrada:

```http
POST /api/journal/{entry_id}/analyze
```

1. Se verifica la propiedad de la entrada.
2. Se comprueba la configuración de Groq.
3. Se toma un bloqueo distribuido de corta duración por entrada.
4. Se aplican cuotas atómicas en Redis, por modelo y por usuario.
5. Se envían la entrada actual y hasta cinco entradas anteriores del mismo usuario, recortadas a 2.000 caracteres cada una.
6. Groq responde en JSON conforme al esquema de emociones, categorías, motivos, patrones, recomendaciones por categoría y nivel de riesgo.
7. Pydantic rechaza campos adicionales, categorías desconocidas, confianza fuera de rango o texto excesivo.
8. El riesgo final nunca puede ser menor al detectado por las reglas independientes.
9. Se guarda el análisis asociado a la versión de la entrada y se publican eventos.

Groq no recibe herramientas ni acceso a SQL. Las recomendaciones concretas provienen de la biblioteca local; Groq solo propone categorías permitidas. Una actualización durante el análisis provoca `409`; no se guarda un resultado correspondiente a una versión diferente. Editar una entrada conserva el historial, pero sus recomendaciones antiguas dejan de considerarse actuales.

Errores controlados: `503` por falta de configuración, acceso denegado (`401`/`403` del proveedor) o indisponibilidad; `504` por timeout; `429` por cuotas; `502` por JSON inválido, respuesta incompleta o bloqueada. No se fabrica un análisis alternativo si Groq falla. Los intentos fallidos también consumen el límite local para evitar reintentos ilimitados. Se rechazan negativas del modelo y llamadas a herramientas aunque incluyan contenido JSON. Los cuerpos de error del proveedor nunca se devuelven al cliente.

La descarga HTTP se lee por bloques, con un máximo de 100.000 bytes y un plazo total `GROQ_TIMEOUT_SECONDS` además del timeout de transporte. No se habilita SSE: `stream: false` solicita una respuesta completa, y leerla por bloques solo limita memoria y tiempo.

**Privacidad:** este proceso envía contenido emocional sensible a Groq. Antes de usarlo con personas reales se necesita consentimiento informado y revisar las condiciones de tratamiento y retención de datos del nuevo proveedor. No habilites IA con datos reales sin esa revisión.

### Compatibilidad de la migración

No cambian endpoints, tablas, `AnalysisResult`, cuerpos de respuesta ni protocolo de eventos. En `/api/healthz`, `gemini_configured` se sustituye por `groq_configured`: indica presencia de clave, no comprueba acceso ni cuota remotos.

Las únicas referencias históricas a Gemini que se conservan deliberadamente son:

- Los códigos públicos de error `gemini_not_configured`, `gemini_access_denied`, `gemini_quota_exceeded`, `gemini_unavailable`, `gemini_timeout`, `gemini_invalid_response` y `gemini_incomplete_response`, junto con sus pruebas. Ahora describen fallos de Groq, pero mantienen exactamente los valores que un frontend existente puede interpretar y el formato `{"detail": "código"}`.
- `app/ai/gemini.py` es solo un alias de importación de `GroqAnalyzer`; conserva el módulo anterior sin mantener un cliente ni llamadas a Google. La aplicación usa directamente el módulo nuevo.
- La clave Redis diaria `gemini:<user_id>:<fecha_UTC>` conserva el contador ya consumido por cada usuario durante el cambio de proveedor. El límite global por modelo usa `groq:global:<modelo>`.
- El marcador ficticio `seed-fixture-not-gemini` permanece para no reinterpretar el historial de demostración; nunca identifica un análisis real.
- Una prueba de configuración comprueba que variables antiguas `GEMINI_*` no habilitan la nueva integración.

Las variables de ejecución son exclusivamente `GROQ_*`; no hay fallback al proveedor anterior. Al actualizar una instalación, edita manualmente tu `.env` privado según `.env.example`, configura la nueva clave y reinicia el proceso. No copies `.env.example` encima de un `.env` existente: sobrescribiría tu configuración. No se modifica ni se migra automáticamente ningún `.env`, análisis histórico o dato de usuarios.

## 8. Seguridad emocional

La creación y edición del diario ejecutan reglas determinísticas sin llamar a Groq. Las reglas normalizan acentos y buscan señales explícitas en español e inglés. La IA puede complementar y elevar el nivel, no rebajarlo.

Los niveles son `none`, `low`, `moderate`, `high` y `critical`. Las alertas guardan códigos de regla, nivel, origen y orientación, sin copiar fragmentos del diario. No se escriben entradas, contraseñas ni respuestas de Groq en logs.

Ante riesgo se entrega un mensaje empático, contacto con alguien de confianza, orientación profesional y recursos de la ubicación configurada. Se suspenden las recomendaciones genéricas. Marcar una alerta como leída no equivale a certificar que el riesgo desapareció. Se mantiene el bloqueo de actividades cuando hay alertas pendientes o señales actuales.

**Límites importantes:** las reglas pueden producir falsos positivos y falsos negativos, incluyendo negaciones, citas o lenguaje indirecto. No constituyen una evaluación clínica. No hay vigilancia humana, seguimiento de emergencias, garantía de detección ni integración con servicios de emergencia. Se requiere revisión profesional antes de un uso asistencial real.

Eliminar una entrada elimina sus análisis y desvincula sus ejercicios realizados. Las alertas mínimas se conservan sin el texto y sin la referencia a la entrada eliminada. Antes de producción debe definirse una política de retención y eliminación completa de cuenta; esta API no implementa eliminación de cuenta.

## 9. WebSockets, Redis y Fan-Out

Cada instancia mantiene únicamente sus conexiones locales. Todas se suscriben al patrón Redis `copilot:users:*`. Los productores publican en `copilot:users:<user_id>` y cada instancia reenvía el evento solo a las conexiones autenticadas de ese usuario.

El cliente no puede elegir un usuario ni suscribirse a un canal. La autenticación se envía en el primer mensaje, nunca como parámetro de URL:

```javascript
const socket = new WebSocket("ws://localhost:8000/api/ws");
socket.onopen = () => socket.send(JSON.stringify({
  type: "authenticate",
  access_token: accessToken
}));
socket.onmessage = event => console.log(JSON.parse(event.data));
```

Este ejemplo ilustra el protocolo; no es una implementación de frontend.

El servidor responde `{"type":"ready","user_id":"...","delivery":"at_most_once"}`. Luego el único mensaje permitido del cliente es `{"type":"ping"}`, que recibe `{"type":"pong"}`. No se permite publicar eventos ni solicitar canales arbitrarios. La autenticación inicial tiene un timeout de 10 segundos y el límite de mensaje es de 8 KiB. Los mensajes ping tienen límite compartido de 120/minuto por usuario.

Eventos de dominio:

- `journal.created`, `journal.updated`, `journal.deleted`
- `analysis.completed`
- `recommendation.created`
- `safety.alert`
- `tracking.updated`

Los eventos contienen identificadores y metadatos, no texto del diario. El cliente consulta después los endpoints autorizados. También hay eventos internos de revocación de sesiones; no se reenvían como información del diario.

La expiración y revocación se revisan durante la conexión; los cierres de sesión y cambios de contraseña se distribuyen entre instancias. Ante pérdida de Redis, los WebSockets se cierran con `1012` y el suscriptor reintenta con espera progresiva hasta 10 segundos. El cliente debe reconectar con espera progresiva y volver a consultar el estado HTTP. `1008` indica autenticación/protocolo inválido, `1009` tamaño excesivo y `1013` indisponibilidad al conectar.

**Garantía real:** Redis Pub/Sub entrega como máximo una vez, sin historial, confirmación del cliente ni repetición. Un evento perdido durante una desconexión no se recupera de Redis. `realtime_delivered` indica que Redis aceptó la publicación, no que un navegador confirmó recepción. Si Redis falla al publicar, el diario permanece guardado y se devuelve `false`; no se informa que el guardado falló. No se implementó un outbox transaccional ni entrega garantizada.

### Probar dos instancias

Tras inicializar una vez la base de datos, ejecuta las dos instancias desde el mismo directorio y con el mismo `.env`:

```bash
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8001 --no-access-log
```

Autentica dos WebSockets del mismo usuario, uno en cada puerto. Crear una entrada por HTTP envía el mismo identificador de evento a ambas conexiones. Una conexión de otro usuario no recibe ese evento. Las pruebas automatizadas verifican este escenario y fuerzan una desconexión real de Redis para comprobar la recuperación.

## 10. Endpoints

Todos llevan el prefijo `/api`. Salvo salud, documentación, registro y login, requieren JWT; el WebSocket autentica con su primer mensaje.

| Método | Ruta | Función |
|---|---|---|
| GET | `/api` | Información de la API |
| GET | `/api/healthz` | SQL, suscriptor Redis y presencia de configuración Groq |
| POST | `/api/auth/register` | Registrar |
| POST | `/api/auth/login` | Iniciar sesión |
| POST | `/api/auth/logout` | Revocar sesión |
| GET / PATCH | `/api/users/me` | Consultar / editar nombre y país |
| POST | `/api/users/me/password` | Cambiar contraseña y revocar sesiones |
| POST / GET | `/api/journal` | Crear / listar entradas |
| GET / PATCH / DELETE | `/api/journal/{entry_id}` | Consultar / editar / eliminar |
| POST | `/api/journal/{entry_id}/analyze` | Analizar con Groq |
| GET | `/api/journal/{entry_id}/analyses` | Historial de análisis de una entrada |
| GET | `/api/analyses` | Historial privado de análisis |
| GET | `/api/analyses/{analysis_id}` | Detalle de análisis |
| GET | `/api/exercises` | Biblioteca; filtro `category` |
| GET | `/api/exercises/{exercise_id}` | Instrucciones de ejercicio |
| POST | `/api/exercises/{exercise_id}/complete` | Registrar actividad; `analysis_id` opcional y privado |
| GET | `/api/exercise-history` | Actividades realizadas |
| GET | `/api/resources` | Recursos por país y categoría |
| GET | `/api/recommendations` | Ejercicios del último análisis vigente u orientación de seguridad |
| GET | `/api/alerts` | Alertas privadas |
| GET | `/api/alerts/{alert_id}` | Detalle |
| POST | `/api/alerts/{alert_id}/acknowledge` | Marcar como leída |
| GET | `/api/safety/resources` | Orientación según país del perfil |
| GET | `/api/tracking/summary` | Resumen; `days` entre 1 y 365 |
| GET | `/api/tracking/trends` | Estados por fecha y frecuencias descriptivas |
| GET | `/api/tracking/timeline` | Línea de tiempo de entradas, análisis, actividades y alertas |
| WS | `/api/ws` | Canal privado autenticado |

Las listas aceptan `limit` entre 1 y 100 y `offset` desde 0, salvo recomendaciones que devuelve como máximo 10 ejercicios. Seguimiento usa 30 días por defecto. Las frecuencias de IA consideran como máximo los 5.000 análisis más recientes del periodo y devuelven `truncated` cuando aplica. Los agregados de entradas se calculan en SQL. Los resúmenes no son evaluaciones clínicas.

El contrato completo de cuerpos y respuestas se consulta en OpenAPI. Las entradas admiten hasta 10.000 caracteres, las notas de ejercicios 2.000 y los cuerpos HTTP 64 KiB. `recorded_at` exige una zona horaria cuando se proporciona.

## 11. Pruebas

Inicia Redis local. Las pruebas usan SQLite temporal y **eliminan el contenido de la base Redis 15**, que debe reservarse exclusivamente para pruebas. Rechazan hosts remotos y bases Redis distintas de 15. No apuntes nunca a datos reales.

```bash
python -m pytest -q
```

Opcionalmente:

```bash
TEST_REDIS_URL=redis://127.0.0.1:6379/15 python -m pytest -q
```

Se prueban autenticación, revocación, validación, CRUD, aislamiento, Groq con transporte HTTP controlado, ausencia de clave, errores `401`/`403`/`429`, desconexión, timeouts de transporte y totales, tamaños máximos, JSON inválido, respuestas incompletas, rechazos, validación Pydantic, modos de salida estructurada y configuración `GROQ_*`. También historial, recomendaciones, cambios concurrentes, alertas, seed, seguimiento, WebSockets, Fan-Out entre instancias, desconexiones, reconexión de Redis y persistencia cuando falla la publicación. Las pruebas de Groq no consumen solicitudes reales ni demuestran que una cuenta tenga cuota disponible.

## 12. PostgreSQL e integración posterior

Los modelos usan SQLAlchemy y tipos SQL portables. Para una futura migración:

1. Realiza una copia de seguridad y define migraciones de esquema y datos.
2. Instala el controlador PostgreSQL compatible: `python -m pip install "psycopg[binary]"`.
3. Configura `APP_DATABASE_URL=postgresql+psycopg://...` mediante secretos.
4. Inicializa y migra explícitamente los datos; cambiar la URL no mueve los datos de SQLite.
5. Ejecuta la suite también contra PostgreSQL antes de producción. En esta entrega solo se verificó SQLite.

No es necesario reconstruir modelos ni repositorios. `create_all` no reemplaza un sistema de migraciones y no actualiza tablas existentes.

Angular puede consumir JSON mediante Bearer JWT y usar el protocolo WebSocket descrito. Configura su origen exacto en `CORS_ORIGINS`, usa HTTPS/WSS fuera del equipo local y no almacenes contenido emocional en logs del navegador. No se desarrolló Angular ni otro frontend.

## 13. Antes de un uso real

- Configurar y verificar Groq con una cuenta autorizada y cuota disponible.
- Mantener Redis accesible de forma privada y usar una base SQL persistente con copias de seguridad.
- Usar TLS, secretos propios por entorno y supervisión operativa sin contenido sensible.
- Revisar clínicamente las reglas, ejercicios y recursos locales.
- Establecer consentimiento, control de acceso operativo, políticas de privacidad, retención y eliminación.
- Evaluar cifrado en reposo y obligaciones legales. SQLite aquí no incorpora cifrado de aplicación.
- Definir procesos de incidentes; esta API no promete disponibilidad clínica ni atención de crisis.

Los datos universitarios de demostración no convierten la aplicación en un servicio de salud validado.

## 14. Operación, compatibilidad y comprobaciones de mantenimiento

### Cambios compatibles y configuración

Las mejoras de mantenimiento conservan las carpetas, las rutas HTTP, el protocolo de eventos públicos y las tablas existentes. No se añadieron dependencias ni se trasladaron módulos. Los rechazos nuevos se limitan a configuración inválida, mensajes malformados o credenciales inconsistentes.

- `GROQ_TIMEOUT_SECONDS` debe ser finito, mayor que cero y como máximo 300 segundos.
- Emisor y audiencia JWT no pueden estar vacíos; el secreto tampoco puede consistir en espacios.
- Los orígenes CORS deben tener la forma `https://dominio:puerto`, sin rutas, credenciales, fragmentos ni comodines. Las solicitudes preflight conservan su funcionamiento.
- Los recursos de emergencia deben ser un objeto por país con código de dos letras mayúsculas, textos no vacíos y enlaces HTTP/HTTPS sin credenciales.
- Los nombres de modelo aceptan un identificador o `organización/modelo`, sin segmentos relativos, URL ni parámetros.
- Las representaciones de configuración ocultan secretos y conexiones SQL/Redis, porque estas últimas también pueden contener credenciales.

El acceso se contrasta tanto con la expiración JWT como con la sesión persistida. Cerrar una sesión no revoca otras sesiones del mismo usuario; cambiar la contraseña sí las revoca todas. La misma distinción se comprueba para conexiones WebSocket.

Las fechas nuevas se normalizan a UTC antes de persistir y se recuperan con zona horaria. Esto corrige la pérdida del desplazamiento horario en SQLite sin alterar columnas. Las fechas históricas guardadas sin zona se interpretan como UTC; si una instalación antigua guardó horas locales, debe revisarlas antes de asumir que representan UTC. No se modifica automáticamente el contenido histórico.

Los datos privados y los errores HTTP esperados incluyen `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` y `Referrer-Policy: no-referrer`. Esto no sustituye HTTPS, un almacenamiento seguro del token ni las políticas de privacidad.

### Copias de seguridad de SQLite

No copies sin coordinación el archivo de una base que está recibiendo escrituras. Para una copia consistente puedes usar la función de respaldo de SQLite desde el directorio del backend:

```bash
python - <<'PY'
import sqlite3
from contextlib import closing

with closing(sqlite3.connect("copilot.db")) as source:
    with closing(sqlite3.connect("copilot-backup.db")) as destination:
        source.backup(destination)
        assert destination.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
print("Copia consistente verificada")
PY
```

La copia contiene información sensible aunque no esté en Git. Protégela con controles de acceso, cifrado y una política de retención; no la adjuntes a incidencias ni la publiques. El ejemplo usa el archivo SQLite predeterminado: si cambiaste `APP_DATABASE_URL`, adapta la ubicación deliberadamente.

Para restaurar, detén todas las instancias, conserva primero una copia de la base actual y verifica la integridad del respaldo. Reemplazar la base elimina los cambios posteriores a ese respaldo; no se debe ejecutar esa operación automáticamente ni con el servicio recibiendo escrituras.

### Errores y reintentos del cliente

| Estado | Acción recomendada |
|---|---|
| `401` | Volver a autenticar; no repetir indefinidamente el mismo token |
| `404` | Tratar el recurso como inexistente o no autorizado; no revela su propietario |
| `409` | Consultar la versión actual o esperar al análisis en curso antes de decidir un nuevo intento |
| `413` | Reducir el cuerpo; reenviarlo igual seguirá fallando |
| `422` | Corregir campos según el contrato; la respuesta no repite el contenido enviado |
| `429` | Respetar `Retry-After` y reducir la frecuencia |
| `502`, `503`, `504` en análisis | Mantener la entrada ya guardada, mostrar indisponibilidad y ofrecer reintento con espera |

Crear entradas o registrar ejercicios no es idempotente: no repitas automáticamente un `POST` tras perder la conexión sin comprobar primero el historial. Un bloqueo de análisis impide ejecuciones simultáneas para esa entrada, pero no deduplica intentos sucesivos ya finalizados.

Una edición vacía del diario conserva versión y fecha, y no publica un evento nuevo. Borrar una entrada no borra el registro de ejercicios realizados, pero elimina su vínculo al análisis eliminado. Los errores de Groq no producen resultados ficticios ni dejan un bloqueo permanente; un proceso no libera un bloqueo que ya pertenezca a otro.

### Comprobación antes de subir cambios

```bash
python -m pytest -q
python -m compileall -q app seed
git diff --check
git status --short
```

Comprueba que no aparezcan bases de datos, respaldos, `.env` ni credenciales. Las pruebas específicas de Redis desconectan únicamente su propio suscriptor, no todos los clientes del servidor. Todas las pruebas de IA siguen usando datos ficticios y transportes controlados; pasar la suite no verifica cuota real de Groq ni aptitud clínica.
