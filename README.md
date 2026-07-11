# WildTrack

Plataforma IoT de monitoreo de fauna silvestre para estaciones de alimentación inteligentes.

## Descripción

WildTrack conecta dispensadores ESP32 con una plataforma web de administración y un geoportal interactivo. Los dispositivos publican eventos de alimentación vía MQTT; el backend los valida, los almacena en MongoDB y los expone a través de una API REST. PostgreSQL/PostGIS guarda los datos maestros (estaciones, zonas, animales, usuarios). MinIO almacena fotos y videos de los eventos.

---

## Stack tecnológico

| Capa | Tecnologías |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic, Motor, aiomqtt |
| Bases de datos | PostgreSQL 16 + PostGIS, MongoDB 7 |
| Almacenamiento | MinIO (S3-compatible) |
| Broker IoT | Eclipse Mosquitto 2.0 |
| Frontend | React 18, TypeScript, Vite, MUI, Leaflet, TanStack Query |
| Infraestructura | Podman / Docker Compose |

---

## Requisitos previos

Antes de empezar, asegúrate de tener instalado:

| Herramienta | Versión mínima | Cómo verificar |
|---|---|---|
| Python | 3.12 | `python3 --version` |
| [uv](https://docs.astral.sh/uv/) | cualquiera | `uv --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Podman **o** Docker | cualquiera | `podman --version` / `docker --version` |
| Podman Compose **o** Docker Compose | cualquiera | `podman compose version` / `docker compose version` |

> **macOS sin Docker Desktop:** usa Podman.
> ```bash
> brew install podman podman-compose
> podman machine init
> podman machine start
> ```

---

## Guía de instalación desde cero

### 1. Clonar el repositorio

```bash
git clone <url-del-repo>
cd wildTrack
```

### 2. Configurar variables de entorno

```bash
cp .env.example backend/.env
```

Abre `backend/.env` y ajusta los valores si es necesario. Los valores por defecto funcionan para desarrollo local:

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5433          # el contenedor expone 5432 interno → 5433 externo
POSTGRES_DB=wildtrack
POSTGRES_USER=wildtrack
POSTGRES_PASSWORD=wildtrack

MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=wildtrack

MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=wildtrack-media

MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_USERNAME=wildtrack_device
MQTT_PASSWORD=wildtrack_pass

JWT_SECRET_KEY=change-me-in-production
```

### 3. Levantar la infraestructura

Desde la **raíz del proyecto** (donde está `compose.infra.yml`):

```bash
# Podman
podman compose -f compose.infra.yml up -d

# Docker
docker compose -f compose.infra.yml up -d
```

Espera a que todos los contenedores estén `healthy`:

```bash
podman compose -f compose.infra.yml ps
# o
docker compose -f compose.infra.yml ps
```

Verás algo así cuando todo esté listo:

```
NAME         STATUS              PORTS
postgres     Up (healthy)        0.0.0.0:5433->5432/tcp
mongodb      Up (healthy)        0.0.0.0:27017->27017/tcp
minio        Up (healthy)        0.0.0.0:9000-9001->9000-9001/tcp
mosquitto    Up (healthy)        0.0.0.0:1883->1883/tcp
```

### 4. Instalar dependencias del backend

```bash
cd backend
uv sync --extra dev
```

Esto crea un virtualenv en `backend/.venv` con todas las dependencias de producción y desarrollo.

### 5. Ejecutar las migraciones de base de datos

```bash
# Desde la raíz del proyecto:
make migrate

# O manualmente:
cd backend && uv run alembic upgrade head
```

Esto crea todas las tablas en PostgreSQL (usuarios, zonas, estaciones, dispositivos, animales, alimentos, etc).

### 6. Verificar que el backend levanta correctamente

```bash
make dev
```

El servidor queda escuchando en `http://0.0.0.0:8000` (accesible también desde otros dispositivos en la red local, útil para el ESP32).

Comprueba el health check:

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

Respuesta esperada:

```json
{
  "status": "ok",
  "checks": {
    "postgres": "ok",
    "mongodb": "ok",
    "minio": "ok",
    "mqtt": "ok"
  }
}
```

Si algún servicio responde `"degraded"`, revisa los logs de la infraestructura:

```bash
podman compose -f compose.infra.yml logs -f
```

### 7. Instalar dependencias del frontend

En otra terminal:

```bash
cd frontend
npm install
```

### 8. Iniciar el frontend

```bash
cd frontend
npm run dev
```

La aplicación queda disponible en **http://localhost:5173**

---

## Levantar todo en orden (resumen rápido)

```bash
# Terminal 1 — infraestructura (solo la primera vez o tras reiniciar la máquina)
podman machine start                          # solo con Podman
podman compose -f compose.infra.yml up -d

# Terminal 1 — migraciones (solo cuando hay cambios en el esquema)
make migrate

# Terminal 2 — backend
make dev

# Terminal 3 — frontend
cd frontend && npm run dev
```

---

## Comandos útiles (`make`)

| Comando | Descripción |
|---|---|
| `make infra-up` | Levanta todos los contenedores de infraestructura |
| `make infra-down` | Detiene los contenedores (datos persistidos en volúmenes) |
| `make infra-logs` | Sigue los logs de todos los contenedores |
| `make migrate` | Aplica migraciones pendientes de Alembic |
| `make migrate-new msg="descripción"` | Genera una nueva migración por autogeneración |
| `make dev` | Inicia el backend con recarga automática (accesible en red local) |
| `make dev-local` | Inicia el backend solo para localhost |
| `make test` | Corre la suite de tests (excluye tests de integración MQTT) |
| `make test-v` | Tests con salida verbosa |
| `make test-mqtt` | Tests de integración MQTT (requiere infraestructura activa) |
| `make lan-ip` | Muestra la IP LAN del Mac (útil para configurar el ESP32) |

---

## Comandos útiles del frontend

```bash
cd frontend
npm run dev        # servidor de desarrollo con HMR
npm run typecheck  # verificación de tipos TypeScript sin compilar
npm run test       # tests en modo watch
npm run test:run   # tests una sola vez (para CI)
npm run build      # build de producción
```

---

## Acceso a los servicios

| Servicio | URL / Puerto | Credenciales por defecto |
|---|---|---|
| API Backend | http://localhost:8000 | — |
| Swagger UI | http://localhost:8000/docs | — |
| Frontend | http://localhost:5173 | admin@wildtrack.local / ChangeThisImmediately! |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| PostgreSQL | localhost:5433 | wildtrack / wildtrack |
| MongoDB | localhost:27017 | sin auth |
| MQTT Broker | localhost:1883 | wildtrack_device / wildtrack_pass |

> El usuario administrador inicial se crea con el script de seed de Slice 1. Si no existe, créalo manualmente desde Swagger (`POST /api/v1/auth/register`).

---

## Datos de demostración (seed)

Para poblar MongoDB con eventos realistas de los últimos 30 días (145 eventos con fotos, rutas de movimiento por animal, identificados y sin identificar):

```bash
cd backend
uv run python scripts/seed_events.py

# Para borrar el seed anterior y regenerar:
uv run python scripts/seed_events.py --clear
```

---

## Simular un dispositivo ESP32 por MQTT

```bash
cd backend

# Evento de sesión de alimentación
uv run python scripts/test_mqtt_publish.py \
  --device-id <uuid-del-dispositivo> \
  --event feeding_session

# Otros tipos disponibles:
#   rfid_failure  — fallo de lectura RFID
#   telemetry     — dato de telemetría (temperatura, humedad, batería)
#   online        — dispositivo conectado
#   offline       — dispositivo desconectado / LWT
#   unknown_device — dispositivo no registrado (para probar rechazo)
```

Para encontrar el UUID de un dispositivo, consúltalo desde Swagger o desde la vista Dispositivos en el frontend.

---

## Ejecutar los tests

```bash
# Suite completa (sin tests de integración MQTT)
make test

# Con detalle
make test-v

# Tests de integración MQTT (requiere infraestructura activa)
make test-mqtt

# TypeScript
cd frontend && npm run typecheck
```

---

## Estructura del proyecto

```
wildTrack/
├── compose.infra.yml              # Contenedores: PostgreSQL, MongoDB, MinIO, Mosquitto
├── config/
│   └── mosquitto/
│       └── mosquitto.conf         # Configuración del broker MQTT
├── Makefile                       # Comandos de desarrollo
├── .env.example                   # Plantilla de variables de entorno
│
├── backend/
│   ├── .env                       # Variables de entorno locales (no commitear)
│   ├── pyproject.toml             # Dependencias Python (gestionadas con uv)
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py                # Factory de la app FastAPI
│   │   └── lifespan.py            # Startup / shutdown (Motor, MQTT)
│   ├── infrastructure/
│   │   ├── postgres.py            # Engine async SQLAlchemy
│   │   ├── mongodb.py             # Cliente Motor + constantes de colecciones
│   │   ├── minio_client.py        # Wrapper del SDK MinIO
│   │   └── health.py              # Router /health
│   ├── migrations/
│   │   └── versions/              # Migraciones Alembic (0001 → 0012)
│   ├── modules/                   # Módulos de negocio
│   │   ├── auth/                  # JWT, registro, login
│   │   ├── users/                 # Gestión de usuarios
│   │   ├── zones/                 # Zonas geográficas (PostGIS)
│   │   ├── stations/              # Estaciones de alimentación
│   │   ├── devices/               # Dispositivos ESP32
│   │   ├── animals/               # Animales + RFID
│   │   ├── foods/                 # Tipos de alimento
│   │   ├── station_foods/         # Asociación estación ↔ alimento
│   │   ├── user_stations/         # Asociación usuario ↔ estación (members)
│   │   ├── iot_events/            # Procesador MQTT + almacenamiento MongoDB
│   │   ├── alerts/                # Alertas operacionales
│   │   ├── geoportal/             # Agregaciones para el mapa
│   │   └── media/                 # Subida de archivos a MinIO
│   ├── shared/
│   │   ├── config.py              # Settings con Pydantic (singleton)
│   │   └── enums.py               # Enumeraciones compartidas
│   ├── scripts/
│   │   ├── seed_events.py         # Genera eventos de demo en MongoDB
│   │   └── test_mqtt_publish.py   # Simula publicaciones MQTT del ESP32
│   └── tests/
│       ├── unit/                  # Tests unitarios por módulo
│       └── integration/           # Tests de integración (MQTT, DB, API)
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── features/              # Módulos de UI por dominio (auth, stations, animals…)
│       ├── pages/                 # Páginas de la SPA (Dashboard, Geoportal…)
│       ├── components/            # Componentes compartidos
│       └── lib/                   # Axios client, helpers
│
└── docs/
    ├── sdd/                       # Documentos de diseño del sistema
    └── decisions/                 # Architecture Decision Records (ADR)
```

---

## Flujo de datos IoT

```
ESP32
  │  MQTT  wildtrack/devices/{id}/events
  ▼
Mosquitto (puerto 1883, auth requerida)
  │
  ▼
Backend — IoT processor
  ├── Valida device_id en PostgreSQL
  ├── Resuelve rfid_tag → animal_id
  ├── Almacena evento en MongoDB (iot_events)
  └── Genera alertas si aplica (alerts)

Frontend / Geoportal
  └── Consulta API REST → datos ya procesados
```

---

## Detener la infraestructura

```bash
# Solo detener (datos intactos)
make infra-down

# Detener y eliminar todos los volúmenes (borra todos los datos)
podman compose -f compose.infra.yml down -v
```
