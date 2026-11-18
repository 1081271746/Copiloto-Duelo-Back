CREDENCIALES PARA INICIAR:

CORREO: sebitasroja7@gmail.com
CONTRASEÑA: sebas1081274756


# Co-Piloto de Duelo 
### Plataforma inteligente de acompañamiento emocional durante el proceso de duelo

## 1. Descripción general

**Co-Piloto de Duelo** es una plataforma web diseñada para brindar acompañamiento emocional a personas que atraviesan un proceso de duelo.

Su objetivo es ofrecer un espacio digital donde los usuarios puedan expresar sus emociones, registrar sus experiencias, realizar ejercicios de acompañamiento y consultar recursos de apoyo.

El sistema integra inteligencia artificial mediante Groq para procesar solicitudes y generar respuestas de acompañamiento contextualizadas. También incorpora mecanismos de seguimiento, análisis emocional y alertas de seguridad para identificar situaciones que puedan requerir atención especial.

La plataforma está construida mediante una arquitectura cliente-servidor que separa el frontend, el backend, la base de datos y los servicios de comunicación en tiempo real.

Co-Piloto de Duelo no pretende reemplazar la atención psicológica ni la intervención de profesionales de salud mental. Su finalidad es ofrecer una herramienta tecnológica de apoyo durante el proceso de duelo.

---

# 2. Objetivos del proyecto

## Objetivo general

Desarrollar una plataforma web inteligente que facilite el acompañamiento emocional durante el proceso de duelo mediante herramientas de registro personal, ejercicios, análisis de información e inteligencia artificial.

## Objetivos específicos

- Proporcionar un espacio digital para expresar y registrar emociones.
- Facilitar el seguimiento del proceso de duelo.
- Incorporar inteligencia artificial para generar respuestas de acompañamiento.
- Permitir el registro de experiencias personales mediante un diario emocional.
- Ofrecer ejercicios y actividades de acompañamiento.
- Proporcionar recursos de orientación y apoyo.
- Identificar posibles situaciones de riesgo mediante mecanismos de seguridad.
- Mantener la información de cada usuario de manera organizada y protegida.
- Incorporar comunicación en tiempo real mediante WebSockets y Redis.
- Ofrecer una arquitectura escalable y preparada para producción.

---

# 3. Tecnologías utilizadas

El proyecto utiliza diferentes tecnologías para desarrollar, conectar y desplegar sus componentes.

## 3.1. Frontend

| Tecnología | Función |
|---|---|
| Angular 21 | Framework para desarrollar la interfaz web. |
| TypeScript | Lenguaje principal del frontend. |
| HTML5 | Estructura de las páginas y componentes. |
| CSS3 | Diseño y presentación visual. |
| RxJS | Administración de operaciones asíncronas y flujos de datos. |
| Angular Router | Navegación entre las diferentes secciones de la aplicación. |

El frontend permite que los usuarios interactúen con las funcionalidades del sistema.

Está organizado mediante componentes y servicios que se comunican con el backend utilizando solicitudes HTTP y conexiones WebSocket.

Entre las funcionalidades visuales contempladas se encuentran:

- Inicio de sesión.
- Registro de usuarios.
- Dashboard principal.
- Diario emocional.
- Seguimiento emocional.
- Ejercicios de acompañamiento.
- Biblioteca de recursos.
- Configuración de usuario.
- Soporte y orientación.

## 3.2. Backend

| Tecnología | Función |
|---|---|
| Python 3.14 | Lenguaje de programación del backend. |
| FastAPI | Desarrollo de la API REST. |
| SQLAlchemy | Comunicación con PostgreSQL mediante ORM. |
| Pydantic | Validación y estructuración de datos. |
| Alembic | Administración de migraciones de la base de datos. |
| HTTPX | Comunicación HTTP con servicios externos. |
| Uvicorn | Servidor ASGI utilizado para ejecutar FastAPI. |

El backend contiene la lógica principal de la plataforma.

Sus responsabilidades incluyen:

- Administrar usuarios y sesiones.
- Validar las solicitudes recibidas.
- Procesar los registros emocionales.
- Gestionar ejercicios y recursos.
- Comunicarse con Groq.
- Administrar las alertas de seguridad.
- Gestionar las conexiones WebSocket.
- Consultar y almacenar información en PostgreSQL.

## 3.3. Base de datos

**PostgreSQL**

PostgreSQL se utiliza para almacenar de manera persistente la información de la aplicación.

La base de datos permite mantener los registros relacionados con usuarios, sesiones, diarios, análisis emocionales, ejercicios y alertas.

La comunicación se realiza mediante SQLAlchemy.

Para administrar los cambios de estructura se utiliza Alembic, permitiendo ejecutar migraciones de manera controlada.

## 3.4. Redis

**Redis**

Redis se utiliza como componente de comunicación y coordinación en tiempo real.

En Co-Piloto de Duelo se integra con el mecanismo de publicación y suscripción, conocido como Pub/Sub.

Este mecanismo permite distribuir mensajes entre componentes que necesitan intercambiar información sin depender exclusivamente de conexiones directas.

Sus responsabilidades incluyen:

- Publicación de mensajes.
- Suscripción a canales.
- Distribución de eventos.
- Apoyo a la comunicación en tiempo real.
- Coordinación de eventos relacionados con WebSockets.

Redis no reemplaza PostgreSQL como base de datos principal del sistema.

## 3.5. Inteligencia artificial

**Groq API**

Groq se integra como proveedor externo de inteligencia artificial.

La comunicación se realiza desde el backend utilizando HTTPX.

| Elemento | Configuración |
|---|---|
| Proveedor | Groq |
| Modelo | `openai/gpt-oss-120b` |
| Comunicación | HTTP |
| Cliente | HTTPX |
| Configuración | Variables de entorno |
| Función | Procesamiento de solicitudes de acompañamiento emocional |

El modelo recibe las solicitudes preparadas por el backend y genera respuestas que posteriormente son procesadas y entregadas al frontend.

La clave de acceso se administra mediante la variable `GROQ_API_KEY`.

La credencial nunca debe exponerse directamente en el frontend.

---

# 4. Integración de inteligencia artificial con Groq

Uno de los componentes principales de Co-Piloto de Duelo es la integración de inteligencia artificial.

Su propósito es proporcionar respuestas de acompañamiento emocional que tengan en cuenta el contexto de las solicitudes realizadas por el usuario.

## ¿Cómo funciona?

1. El usuario escribe una solicitud o expresa una situación emocional desde la interfaz.
2. El frontend envía la información al backend.
3. FastAPI recibe y valida la solicitud.
4. El backend prepara la información necesaria para el procesamiento.
5. Se realiza una petición HTTP a Groq mediante HTTPX.
6. Groq procesa el contenido utilizando el modelo configurado.
7. El backend recibe la respuesta.
8. La respuesta se procesa y se devuelve al frontend.
9. El usuario visualiza el resultado en la aplicación.

## Modelo utilizado

`openai/gpt-oss-120b`

Se configura mediante:

```env
GROQ_MODEL=openai/gpt-oss-120b
```

La credencial se configura mediante:

```env
GROQ_API_KEY=tu_clave_de_groq
```

## Funciones de la inteligencia artificial

La integración permite incorporar capacidades de:

- Comprensión de solicitudes escritas.
- Generación de respuestas de acompañamiento.
- Procesamiento contextual de las conversaciones.
- Orientación sobre situaciones relacionadas con el duelo.
- Apoyo en la reflexión y expresión emocional.

La inteligencia artificial funciona como un recurso complementario de acompañamiento y no como sustituto de un profesional de salud mental.

---

# 5. Módulos principales del sistema

## 5.1. Autenticación y administración de usuarios

Este módulo permite controlar el acceso a la plataforma.

Incluye mecanismos de registro, inicio de sesión y administración de sesiones.

### Tecnologías utilizadas

- FastAPI.
- JWT.
- Argon2.
- PostgreSQL.
- SQLAlchemy.

### Funcionamiento

1. El usuario introduce sus credenciales.
2. El backend recibe la solicitud.
3. Se validan las credenciales.
4. Las contraseñas se protegen mediante hashing con Argon2.
5. Si la autenticación es correcta, se generan los mecanismos de acceso correspondientes.
6. El frontend conserva la sesión de acuerdo con el flujo de autenticación implementado.

El sistema utiliza JWT para gestionar los tokens de autenticación y sesiones persistentes mediante la estructura de sesiones de la base de datos.

También contempla mecanismos de renovación de acceso y cierre de sesión.

## 5.2. Dashboard principal

El dashboard es el espacio central desde el cual el usuario puede consultar información y acceder a las funcionalidades de la plataforma.

Su finalidad es facilitar la navegación y presentar información relevante del proceso de acompañamiento.

Entre los elementos contemplados se encuentran:

- Resumen de actividad.
- Acceso al diario emocional.
- Acceso a ejercicios.
- Consulta de recursos.
- Seguimiento emocional.
- Acciones rápidas.

## 5.3. Diario emocional

El diario emocional permite registrar experiencias personales relacionadas con el proceso de duelo.

Su finalidad es proporcionar un espacio privado donde el usuario pueda escribir sus pensamientos, recuerdos y emociones.

### Funcionamiento

1. El usuario accede al diario.
2. Registra una nueva entrada.
3. El frontend envía la información al backend.
4. FastAPI valida los datos.
5. SQLAlchemy administra su almacenamiento en PostgreSQL.
6. El usuario puede consultar sus registros posteriormente.

La información almacenada permite mantener un historial de experiencias personales.

## 5.4. Análisis emocional

Este módulo permite trabajar con información relacionada con las emociones registradas por el usuario.

Su finalidad es apoyar el seguimiento del proceso emocional mediante el análisis de la información disponible.

El sistema contempla el almacenamiento de resultados de análisis emocionales en la base de datos.

La inteligencia artificial puede utilizarse como parte del procesamiento de solicitudes relacionadas con el acompañamiento.

Los resultados son orientativos y no representan diagnósticos psicológicos o médicos.

## 5.5. Ejercicios de acompañamiento

La plataforma incorpora un módulo de ejercicios orientados al acompañamiento durante el proceso de duelo.

Su propósito es ofrecer actividades que permitan al usuario realizar procesos de reflexión y expresión emocional.

La base de datos contempla:

- Información de ejercicios.
- Registros de ejercicios completados.

Esto permite organizar los ejercicios y mantener información relacionada con su realización.

## 5.6. Biblioteca de recursos

Este módulo permite organizar y consultar recursos de apoyo relacionados con el proceso de duelo.

Su finalidad es centralizar información que pueda resultar útil para los usuarios durante su proceso de acompañamiento.

Los recursos se administran desde el backend y se almacenan en PostgreSQL.

## 5.7. Alertas de seguridad

La seguridad emocional es un aspecto importante del proyecto.

Por esta razón, el backend contempla un módulo de alertas de seguridad que permite registrar situaciones que puedan requerir atención especial.

Su objetivo es apoyar la identificación y el seguimiento de situaciones de riesgo.

La estructura de datos contempla registros de alertas asociados a la información del sistema.

Este mecanismo no sustituye protocolos de emergencia ni garantiza por sí solo la detección de todas las situaciones de riesgo.

## 5.8. Soporte

El módulo de soporte proporciona un espacio para acceder a información de ayuda y orientación dentro de la plataforma.

Está pensado para facilitar la consulta de información relacionada con el funcionamiento del sistema y el acompañamiento.

---

# 6. Comunicación en tiempo real: WebSockets y Redis Pub/Sub

Una característica técnica importante de Co-Piloto de Duelo es la incorporación de comunicación en tiempo real.

Para esto se utilizan WebSockets junto con Redis Pub/Sub.

## 6.1. WebSockets

WebSocket permite establecer una conexión persistente entre el navegador y el backend.

A diferencia de una solicitud HTTP tradicional, no es necesario iniciar una nueva petición para cada intercambio de mensajes.

Esto permite una comunicación bidireccional.

### Funcionamiento

1. El frontend solicita establecer una conexión WebSocket.
2. FastAPI recibe la solicitud.
3. Se establece la conexión.
4. El servidor y el cliente pueden intercambiar mensajes.
5. Los eventos se procesan mientras la conexión permanece activa.

## 6.2. Redis Pub/Sub

Redis utiliza un mecanismo de publicación y suscripción para distribuir mensajes entre componentes.

### Funcionamiento

1. Un componente publica un mensaje en un canal.
2. Redis recibe el mensaje.
3. Los componentes suscritos al canal reciben el evento.
4. Los servicios correspondientes pueden procesar la información.
5. El backend puede transmitir los eventos al cliente mediante WebSockets.

### ¿Por qué utilizar ambos?

WebSockets permite mantener la comunicación entre el navegador y el servidor.

Redis Pub/Sub permite distribuir eventos entre componentes del backend.

La combinación facilita una arquitectura preparada para gestionar comunicación en tiempo real y distribuir eventos entre diferentes procesos.

---

# 7. Arquitectura general del sistema

Co-Piloto de Duelo utiliza una arquitectura separada por responsabilidades.

## Componentes

### 1. Frontend

Desarrollado con Angular 21.

Es responsable de la interfaz gráfica, navegación, formularios y comunicación con el backend.

### 2. Backend

Desarrollado con FastAPI.

Administra la lógica de negocio, autenticación, validaciones, procesamiento de información e integración con servicios externos.

### 3. PostgreSQL

Es la base de datos principal y almacena la información persistente.

### 4. Redis

Administra la distribución de mensajes mediante Pub/Sub y apoya la comunicación en tiempo real.

### 5. Groq

Es el servicio externo utilizado para el procesamiento de solicitudes mediante inteligencia artificial.

## Diagrama de arquitectura

```text
                  USUARIO
                     |
                     v
             ANGULAR 21 FRONTEND
                     |
             HTTP / WEBSOCKET
                     |
                     v
                FASTAPI
               BACKEND
                     |
        +------------+------------+
        |            |            |
        v            v            v
   POSTGRESQL      REDIS        GROQ API
        |         PUB/SUB      GPT-OSS-120B
        |            |            |
        v            v            v
   INFORMACIÓN   EVENTOS       RESPUESTAS
   PERSISTENTE   EN TIEMPO     DE IA
                 REAL
        |            |            |
        +------------+------------+
                     |
                     v
               RESPUESTA
                     |
                     v
             ANGULAR 21 FRONTEND
```

---

# 8. Estructura de la base de datos

El backend utiliza PostgreSQL como base de datos principal.

La migración inicial identificada es:

`44ac0350f98c_initial_postgresql_schema.py`

Esta migración crea ocho tablas principales.

| Tabla | Función |
|---|---|
| `users` | Información de los usuarios registrados. |
| `token_sessions` | Administración de sesiones y tokens. |
| `journal_entries` | Entradas del diario personal. |
| `emotional_analyses` | Almacenamiento de análisis emocionales. |
| `exercises` | Información de los ejercicios de acompañamiento. |
| `resources` | Recursos de apoyo disponibles. |
| `exercise_completions` | Registro de ejercicios completados. |
| `safety_alerts` | Registro de alertas de seguridad. |

## Administración de migraciones

Se utiliza Alembic para mantener controlada la evolución de la estructura de la base de datos.

Comando para aplicar las migraciones:

```bash
python -m alembic upgrade head
```

Este proceso permite actualizar el esquema de PostgreSQL de acuerdo con las migraciones disponibles.

---

# 9. API REST

El backend proporciona servicios mediante una API REST desarrollada con FastAPI.

La API permite realizar operaciones relacionadas con:

- Usuarios.
- Autenticación.
- Sesiones.
- Diario emocional.
- Análisis emocionales.
- Ejercicios.
- Recursos.
- Alertas de seguridad.

Las solicitudes y respuestas utilizan estructuras JSON.

## Documentación de la API

FastAPI genera documentación interactiva mediante Swagger y OpenAPI.

En el entorno local:

```text
http://127.0.0.1:8000/api/docs
```

En producción:

```text
https://copiloto-duelo-back-production-de6a5b1f.up.railway.app/api/docs
```

## Health Check

El backend dispone de un endpoint de verificación:

```text
GET /api/healthz
```

Este endpoint permite comprobar el estado general de los servicios.

La respuesta verificada en producción fue:

```json
{
  "status": "ok",
  "database": "ok",
  "redis": true,
  "groq_configured": true
}
```

Esto confirma que el backend puede comunicarse con PostgreSQL y Redis y que la configuración de Groq está disponible.

---

# 10. Seguridad del sistema

Co-Piloto de Duelo contempla diferentes mecanismos de seguridad.

## 10.1. Autenticación JWT

Se utilizan tokens JWT para gestionar el acceso a los recursos protegidos.

## 10.2. Protección de contraseñas

Se utiliza Argon2 para almacenar contraseñas mediante hashing seguro, evitando guardar las contraseñas originales.

## 10.3. Sesiones

La tabla `token_sessions` permite mantener información relacionada con las sesiones y los tokens de acceso.

## 10.4. Variables de entorno

Las credenciales y configuraciones sensibles se administran mediante variables de entorno.

## 10.5. CORS

Se utiliza Cross-Origin Resource Sharing para controlar qué orígenes pueden realizar solicitudes al backend.

## 10.6. Seguridad de WebSockets

El backend contempla validaciones de origen y mecanismos de autenticación para gestionar las conexiones WebSocket.

## 10.7. Seguridad emocional

La plataforma incorpora un módulo de alertas para apoyar la identificación de situaciones que puedan requerir atención especial.

La información emocional debe tratarse como información sensible y protegerse mediante controles de acceso adecuados.

---

# 11. Variables de entorno

La configuración del backend utiliza variables de entorno.

Entre las principales se encuentran:

```env
APP_ENV=production

APP_DATABASE_URL=postgresql://...

REDIS_URL=redis://...

GROQ_API_KEY=...

GROQ_MODEL=openai/gpt-oss-120b

GROQ_TIMEOUT_SECONDS=20

GROQ_REQUESTS_PER_MINUTE=5

AI_DAILY_USER_LIMIT=20

JWT_SECRET=...

JWT_ISSUER=grief-copilot

JWT_AUDIENCE=grief-copilot-api

ACCESS_TOKEN_MINUTES=30

DEFAULT_COUNTRY=CO

CORS_ORIGINS=http://localhost:4200
```

Los valores reales deben configurarse en Railway o en el archivo `.env` local.

**Importante:** no se deben publicar claves privadas, contraseñas, tokens ni credenciales de servicios en GitHub.

---

# 12. Pruebas y validaciones

El proyecto cuenta con pruebas automatizadas para verificar el funcionamiento del backend.

Durante el desarrollo se registró el siguiente resultado:

**209 pruebas aprobadas, con una advertencia.**

Las pruebas permiten comprobar diferentes aspectos del sistema, incluyendo:

- Validación de información.
- Funcionamiento de componentes del backend.
- Operaciones de la aplicación.
- Comportamiento de servicios.
- Manejo de solicitudes y respuestas.

También se verificó la conexión de producción con PostgreSQL, Redis y Groq mediante el endpoint de salud.

---

# 13. Despliegue en Railway

El proyecto utiliza Railway como plataforma de despliegue.

La infraestructura se encuentra organizada en cuatro servicios principales.

| Servicio | Responsabilidad |
|---|---|
| Co-Piloto-de-Duelo-Front | Aplicación Angular. |
| Copiloto-Duelo-Back | API FastAPI. |
| PostgreSQL | Base de datos principal. |
| Redis | Comunicación Pub/Sub. |

## Backend

El backend se despliega mediante el servicio:

`Copiloto-Duelo-Back`

Comando de inicio:

```bash
uvicorn app.main:create_app --factory --host 0.0.0.0 --port $PORT
```

Antes de iniciar el servicio se ejecutan las migraciones:

```bash
python -m alembic upgrade head
```

## Frontend

El frontend se encuentra en el repositorio:

`Co-Piloto-de-Duelo-Front`

Se utiliza Docker para construir la aplicación y Nginx para servir los archivos de producción.

La imagen utiliza:

- Node.js 24.
- PNPM 12.18.0.
- Angular 21.
- Nginx.

El archivo `Dockerfile` contiene las instrucciones para instalar las dependencias, compilar Angular y preparar el servidor web.

## Dominios de producción

Frontend:

https://co-piloto-de-duelo-front-production.up.railway.app

Backend:

https://copiloto-duelo-back-production-de6a5b1f.up.railway.app

Documentación:

https://copiloto-duelo-back-production-de6a5b1f.up.railway.app/api/docs

Verificación:

https://copiloto-duelo-back-production-de6a5b1f.up.railway.app/api/healthz

---

# 14. Ejecución en entorno local

## 14.1. Backend

### Requisitos

- Python 3.14.
- PostgreSQL.
- Redis.
- Clave de acceso a Groq.
- Git.

### Crear entorno virtual

```powershell
python -m venv .venv
```

### Activar entorno virtual

```powershell
.venv\Scripts\activate
```

### Instalar dependencias

```powershell
pip install -r requirements.txt
```

### Configurar variables de entorno

Crear el archivo `.env` con las credenciales y configuraciones necesarias.

### Ejecutar migraciones

```powershell
python -m alembic upgrade head
```

### Iniciar FastAPI

```powershell
uvicorn app.main:create_app --factory --reload
```

El backend estará disponible en:

```text
http://127.0.0.1:8000
```

Documentación:

```text
http://127.0.0.1:8000/api/docs
```

## 14.2. Frontend

### Requisitos

- Node.js 24.
- PNPM 12.18.0.

### Instalar dependencias

```powershell
pnpm install --frozen-lockfile
```

### Iniciar Angular

```powershell
pnpm start
```

La aplicación estará disponible normalmente en:

```text
http://localhost:4200
```

### Construir para producción

```powershell
pnpm build
```

### Ejecutar pruebas

```powershell
pnpm test
```

### Verificar tipos

```powershell
pnpm typecheck
```

---

# 15. Estructura general del proyecto

La organización se divide en dos repositorios independientes.

## Backend

```text
Co-Piloto-de-Duelo-Back/
│
├── app/
│   ├── core/
│   │   └── config.py
│   │
│   ├── database/
│   │
│   ├── models/
│   │
│   ├── routers/
│   │
│   ├── schemas/
│   │
│   ├── services/
│   │
│   ├── websocket/
│   │   └── router.py
│   │
│   └── main.py
│
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
│
├── tests/
│
├── alembic.ini
├── requirements.txt
└── .env
```

## Frontend

```text
Co-Piloto-de-Duelo-Front/
│
├── src/
│   ├── app/
│   │   ├── core/
│   │   ├── components/
│   │   ├── services/
│   │   └── pages/
│   │
│   └── styles.css
│
├── public/
│   └── config.js
│
├── Dockerfile
├── nginx.conf.template
├── angular.json
├── package.json
├── pnpm-lock.yaml
└── pnpm-workspace.yaml
```

La estructura representa la organización general de los componentes; los directorios concretos pueden variar según la versión del repositorio.

---

# 16. Buenas prácticas implementadas

Durante el desarrollo se aplicaron diferentes prácticas de ingeniería de software:

- Separación entre frontend y backend.
- Arquitectura modular.
- Validación de información mediante Pydantic.
- Uso de ORM con SQLAlchemy.
- Migraciones controladas mediante Alembic.
- Autenticación mediante JWT.
- Protección de contraseñas con Argon2.
- Uso de variables de entorno.
- Comunicación asíncrona mediante WebSockets.
- Distribución de eventos con Redis Pub/Sub.
- Integración de servicios externos mediante HTTPX.
- Pruebas automatizadas.
- Control de versiones mediante Git.
- Despliegue mediante Railway.
- Contenerización del frontend mediante Docker.

---

# 17. Estado del proyecto

Co-Piloto de Duelo cuenta con una infraestructura de producción desplegada en Railway.

Se encuentran desplegados:

- Frontend Angular.
- Backend FastAPI.
- PostgreSQL.
- Redis.

El backend tiene una verificación de salud satisfactoria, con conexión confirmada a PostgreSQL y Redis y configuración de Groq disponible.

El frontend también fue construido y desplegado correctamente mediante Docker y Nginx.

**Estado importante:** aunque ambos servicios están desplegados, el flujo de inicio de sesión desde el dominio público todavía requiere validación y corrección. Por tanto, no se considera que toda la experiencia de usuario en producción esté completamente verificada.

---

# 18. Conclusión

Co-Piloto de Duelo es una plataforma que combina desarrollo web, inteligencia artificial, almacenamiento de información y comunicación en tiempo real para ofrecer herramientas de acompañamiento durante el proceso de duelo.

La utilización de Angular permite desarrollar una interfaz modular e interactiva. FastAPI administra la lógica del sistema y PostgreSQL mantiene la información persistente.

La integración con Groq permite incorporar procesamiento mediante inteligencia artificial, mientras que Redis y WebSockets proporcionan mecanismos de comunicación en tiempo real.

La arquitectura implementada permite mantener separados los diferentes componentes y facilita su mantenimiento, evolución y despliegue.

El proyecto busca demostrar cómo la ingeniería de software y la inteligencia artificial pueden utilizarse para desarrollar herramientas tecnológicas orientadas al acompañamiento emocional.

---

**Co-Piloto de Duelo 🕊️**

*Tecnología e inteligencia artificial al servicio del acompañamiento emocional.*
