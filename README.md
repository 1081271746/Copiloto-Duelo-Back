# Co-Piloto de Duelo — Backend

API en Python y FastAPI para acompañamiento emocional durante el duelo. Incluye diario privado, reflexión mediante Gemini, biblioteca de ejercicios, seguimiento, alertas y eventos privados mediante WebSockets y Redis Pub/Sub.

**No sustituye psicología, psiquiatría, terapia ni atención médica. No realiza diagnósticos y no contacta automáticamente a emergencias.** Las cinco categorías del duelo son referencias opcionales y no lineales; no son una escala de recuperación ni etapas obligatorias.

Este repositorio contiene exclusivamente el backend. La documentación interactiva de FastAPI no es un frontend del producto.

## 1. Requisitos

- Python 3.12 o posterior.
- Redis real en ejecución. No se usa un sustituto en memoria.
- Una clave propia de Google Gemini para realizar análisis reales.
- Dependencias de `requirements.txt`.

La disponibilidad de un modelo y las cuotas gratuitas dependen de la cuenta de Google. No se garantiza acceso gratuito ni una cuota estudiantil. `GEMINI_MODEL` permite seleccionar un modelo habilitado en tu cuenta.

## 2. Ejecutar localmente

Desde la raíz de este repositorio:

```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

Edita `.env`. Configura `JWT_SECRET` con al menos 32 caracteres aleatorios. Puedes generar un valor localmente:

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
| `GEMINI_API_KEY` | Clave propia de Gemini; vacía deshabilita únicamente el análisis |
| `GEMINI_MODEL` | Modelo configurable; inicialmente `gemini-2.5-flash` |
| `GEMINI_TIMEOUT_SECONDS` | Tiempo máximo de la llamada a Gemini; inicialmente 20 |
| `GEMINI_REQUESTS_PER_MINUTE` | Límite global compartido para ese modelo; inicialmente 5 |
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
  ai/             Cliente Gemini, sin acceso a la base de datos
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
tests/            Pruebas con SQLite temporal, Redis real y Gemini controlado
```

Patrones aplicados:

- **Repository** para búsquedas privadas consistentes y aislamiento.
- **Service Layer** para reglas de negocio y coordinación.
- **Dependency Injection** de FastAPI para usuario y sesión; el analizador se inyecta en la aplicación y se reemplaza en pruebas.
- **Factory** mediante `create_app`, que permite configurar instancias independientes.
- **Publish/Subscribe y Fan-Out** con Redis para distribuir eventos entre procesos.

No se añadieron jerarquías de estrategias ni patrones decorativos sin una necesidad concreta.

## 7. Análisis con Gemini

El análisis se solicita explícitamente después de guardar una entrada:

```http
POST /api/journal/{entry_id}/analyze
```

1. Se verifica la propiedad de la entrada.
2. Se comprueba la configuración de Gemini.
3. Se toma un bloqueo distribuido de corta duración por entrada.
4. Se aplican cuotas atómicas en Redis, por modelo y por usuario.
5. Se envían la entrada actual y hasta cinco entradas anteriores del mismo usuario, recortadas a 2.000 caracteres cada una.
6. Gemini responde en JSON conforme al esquema de emociones, categorías, motivos, patrones, recomendaciones por categoría y nivel de riesgo.
7. Pydantic rechaza campos adicionales, categorías desconocidas, confianza fuera de rango o texto excesivo.
8. El riesgo final nunca puede ser menor al detectado por las reglas independientes.
9. Se guarda el análisis asociado a la versión de la entrada y se publican eventos.

Gemini no recibe herramientas ni acceso a SQL. Las recomendaciones concretas provienen de la biblioteca local; Gemini solo propone categorías permitidas. Una actualización durante el análisis provoca `409`; no se guarda un resultado correspondiente a una versión diferente. Editar una entrada conserva el historial, pero sus recomendaciones antiguas dejan de considerarse actuales.

Errores controlados: `503` por falta de configuración, acceso denegado o indisponibilidad; `504` por timeout; `429` por cuotas; `502` por JSON inválido, respuesta incompleta o bloqueada. No se fabrica un análisis alternativo si Gemini falla. Los intentos fallidos también consumen el límite local para evitar reintentos ilimitados.

**Privacidad:** este proceso envía contenido emocional sensible a Google. Antes de usarlo con personas reales se necesita consentimiento informado y revisar las condiciones de tratamiento y retención de datos del proveedor. No habilites IA con datos reales sin esa revisión.

## 8. Seguridad emocional

La creación y edición del diario ejecutan reglas determinísticas sin llamar a Gemini. Las reglas normalizan acentos y buscan señales explícitas en español e inglés. La IA puede complementar y elevar el nivel, no rebajarlo.

Los niveles son `none`, `low`, `moderate`, `high` y `critical`. Las alertas guardan códigos de regla, nivel, origen y orientación, sin copiar fragmentos del diario. No se escriben entradas, contraseñas ni respuestas de Gemini en logs.

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
| GET | `/api/healthz` | SQL, suscriptor Redis y presencia de configuración Gemini |
| POST | `/api/auth/register` | Registrar |
| POST | `/api/auth/login` | Iniciar sesión |
| POST | `/api/auth/logout` | Revocar sesión |
| GET / PATCH | `/api/users/me` | Consultar / editar nombre y país |
| POST | `/api/users/me/password` | Cambiar contraseña y revocar sesiones |
| POST / GET | `/api/journal` | Crear / listar entradas |
| GET / PATCH / DELETE | `/api/journal/{entry_id}` | Consultar / editar / eliminar |
| POST | `/api/journal/{entry_id}/analyze` | Analizar con Gemini |
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

Se prueban autenticación, revocación, validación, CRUD, aislamiento, Gemini con transporte HTTP controlado, timeouts, cuotas, historial, recomendaciones, cambios concurrentes, alertas, seed, seguimiento, WebSockets, Fan-Out entre instancias, desconexiones, reconexión de Redis y persistencia cuando falla la publicación. Las pruebas de Gemini no consumen solicitudes reales ni demuestran que una cuenta tenga cuota disponible.

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

- Configurar y verificar Gemini con una cuenta autorizada y cuota disponible.
- Mantener Redis accesible de forma privada y usar una base SQL persistente con copias de seguridad.
- Usar TLS, secretos propios por entorno y supervisión operativa sin contenido sensible.
- Revisar clínicamente las reglas, ejercicios y recursos locales.
- Establecer consentimiento, control de acceso operativo, políticas de privacidad, retención y eliminación.
- Evaluar cifrado en reposo y obligaciones legales. SQLite aquí no incorpora cifrado de aplicación.
- Definir procesos de incidentes; esta API no promete disponibilidad clínica ni atención de crisis.

Los datos universitarios de demostración no convierten la aplicación en un servicio de salud validado.
