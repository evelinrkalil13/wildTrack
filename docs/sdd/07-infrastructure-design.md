# WildTrack Platform — Infrastructure Architecture

**Document:** SDD-07 Infrastructure Design  
**Version:** 1.0.0  
**Date:** 2026-06-13  
**Status:** Draft — Pending Approval  
**References:** SDD-01 Requirements v1.2.0, SDD-02 Architecture v1.0.0, SDD-05 Backend Design v1.0.0, SDD-06 Frontend Design v1.0.0

---

## Table of Contents

1. [Infrastructure Overview](#1-infrastructure-overview)
2. [Local Development Architecture](#2-local-development-architecture)
3. [Docker Architecture](#3-docker-architecture)
4. [Docker Compose Design](#4-docker-compose-design)
5. [Network Design](#5-network-design)
6. [PostgreSQL Design](#6-postgresql-design)
7. [MongoDB Design](#7-mongodb-design)
8. [MinIO Design](#8-minio-design)
9. [MQTT Broker Design](#9-mqtt-broker-design)
10. [Environment Variables Strategy](#10-environment-variables-strategy)
11. [Backup Strategy](#11-backup-strategy)
12. [Observability Strategy](#12-observability-strategy)
13. [Logging Strategy](#13-logging-strategy)
14. [Security Strategy](#14-security-strategy)
15. [CI/CD Strategy](#15-cicd-strategy)
16. [GitHub Repository Strategy](#16-github-repository-strategy)
17. [Deployment Strategy](#17-deployment-strategy)
18. [VPS Deployment Option](#18-vps-deployment-option)
19. [AWS Deployment Option](#19-aws-deployment-option)
20. [Cost Analysis MVP](#20-cost-analysis-mvp)
21. [Infrastructure ADRs](#21-infrastructure-adrs)

---

## 1. Infrastructure Overview

### 1.1 Design Principles

WildTrack's infrastructure follows five principles:

**Simplicity first.** The MVP runs entirely on a single machine (local or a small VPS) using Docker Compose. No Kubernetes, no container orchestration, no service mesh.

**Low operational cost.** The entire MVP stack is self-hosted using open-source tools. No managed cloud database subscriptions are required for development or early production.

**Portability.** Every service is containerized. Moving from a developer laptop to a VPS to a cloud provider requires only changing environment variables and a Docker host.

**Future-ready.** The architecture is designed so that individual components (PostgreSQL → RDS, MongoDB → Atlas, MinIO → S3, MQTT → IoT Core) can be replaced with managed equivalents without code changes. Only environment variables change.

**Secure by default.** All inter-service communication happens on private Docker networks. No database or broker port is exposed to the public internet in production.

### 1.2 Component Map

```mermaid
flowchart TD
    subgraph Internet
        U[Browser / Researcher]
        D[ESP32 Device\nin the field]
    end

    subgraph Docker Host
        subgraph frontend_net
            FE[Frontend\nReact + Vite\nNginx]
        end

        subgraph backend_net
            BE[Backend\nFastAPI]
            PG[(PostgreSQL\n+ PostGIS)]
            MG[(MongoDB)]
            MQ[MQTT Broker\nMosquitto]
            MN[MinIO\nObject Storage]
        end

        NX[Nginx Reverse Proxy\nSSL Termination]
    end

    U -->|HTTPS 443| NX
    D -->|MQTT 8883 TLS| NX
    NX -->|HTTP| FE
    NX -->|HTTP| BE
    NX -->|MQTT| MQ
    BE --> PG
    BE --> MG
    BE --> MN
    BE --> MQ
    FE -->|API calls via NX| BE
```

### 1.3 Service Inventory

| Service | Image | Purpose | Exposed port (local) | Exposed port (prod) |
|---------|-------|---------|---------------------|---------------------|
| `postgres` | `postgis/postgis:16-3.4` | Relational master data | 5432 | None (internal) |
| `mongodb` | `mongo:7.0` | IoT events, telemetry, alerts | 27017 | None (internal) |
| `minio` | `minio/minio:latest` | Object storage for media | 9000, 9001 | None (internal) |
| `mosquitto` | `eclipse-mosquitto:2.0` | MQTT message broker | 1883 | 8883 (TLS, prod) |
| `backend` | `wildtrack/backend:latest` | FastAPI application | 8000 | None (via proxy) |
| `frontend` | `wildtrack/frontend:latest` | React SPA served by Nginx | 3000 | None (via proxy) |
| `nginx` | `nginx:1.25-alpine` | Reverse proxy + SSL (prod) | — | 80, 443 |

---

## 2. Local Development Architecture

### 2.1 Developer Workflow

In local development, backend and frontend run outside Docker (for fast HMR and debugger support), while infrastructure services (PostgreSQL, MongoDB, MinIO, Mosquitto) run inside Docker Compose.

```mermaid
flowchart TD
    subgraph Developer Machine
        subgraph Terminal 1
            BE[FastAPI\nuvicorn --reload\nlocalhost:8000]
        end
        subgraph Terminal 2
            FE[Vite Dev Server\nlocalhost:5173]
        end
        subgraph Docker Compose - infra profile
            PG[(PostgreSQL :5432)]
            MG[(MongoDB :27017)]
            MN[MinIO :9000/:9001]
            MQ[Mosquitto :1883]
        end
    end

    FE -->|API proxy\n/api/v1 → :8000| BE
    BE --> PG
    BE --> MG
    BE --> MN
    BE --> MQ
```

### 2.2 Developer Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker Desktop (or Podman Desktop) | Latest | Run infrastructure services |
| Python | 3.12 | Backend runtime |
| `uv` or `pip` | Latest | Python dependency management |
| Node.js | 20 LTS | Frontend runtime |
| npm | 10+ | Frontend package management |
| Git | 2.40+ | Version control |

> **Note:** The CLAUDE.md records that the developer's machine has Python 3.14 installed. The project pins Python to **3.12** for dependency compatibility. Use `pyenv` or `uv` to manage the Python version locally.

### 2.3 Infrastructure-Only Docker Compose Profile

A dedicated `compose.infra.yml` file starts only the four infrastructure services. Developers run this once and leave it running. The backend and frontend start separately outside Docker.

```
compose.infra.yml
├── postgres       ← port 5432 exposed to host
├── mongodb        ← port 27017 exposed to host
├── minio          ← ports 9000 (API) and 9001 (console) exposed to host
└── mosquitto      ← port 1883 exposed to host (no auth in dev)
```

### 2.4 Vite Proxy Configuration

The Vite dev server proxies all requests starting with `/api/` to `http://localhost:8000`. This avoids CORS issues during development. No CORS configuration is needed on the backend for the frontend in development mode.

### 2.5 Hot Reload Behavior

| Layer | Reload trigger | Mechanism |
|-------|---------------|-----------|
| Backend | Any `.py` file change | `uvicorn --reload` watches `app/` and `modules/` |
| Frontend | Any `.tsx`, `.ts`, `.scss` change | Vite HMR injects updates without page reload |
| Infrastructure | `compose.infra.yml` change | `docker compose up -d` re-creates affected services |

---

## 3. Docker Architecture

### 3.1 Image Build Strategy

Each application service (backend, frontend) has its own `Dockerfile`. Infrastructure services (PostgreSQL, MongoDB, MinIO, Mosquitto) use official public images with configuration mounted as volumes — they have no custom `Dockerfile`.

### 3.2 Backend `Dockerfile` Design

Build strategy: **multi-stage** to minimize the final image size.

```mermaid
flowchart LR
    A[Stage 1: builder\npython:3.12-slim\nInstall dependencies\nCompile wheels] --> B[Stage 2: runtime\npython:3.12-slim\nCopy wheels\nCopy app code\nNon-root user\nExpose 8000]
```

**Stage 1 (builder):**
- Base: `python:3.12-slim`
- Install system build dependencies (`gcc`, `libpq-dev`)
- Install Python packages into `/install` directory
- No application code in this stage

**Stage 2 (runtime):**
- Base: `python:3.12-slim` (clean, no build tools)
- Copy compiled wheels from builder stage
- Copy application source
- Create non-root user `wildtrack` (UID 1001)
- Set `WORKDIR /app`
- Expose port `8000`
- `CMD`: run Alembic migrations first, then start Uvicorn

### 3.3 Frontend `Dockerfile` Design

Build strategy: **multi-stage** — Vite builds static assets, Nginx serves them.

```mermaid
flowchart LR
    A[Stage 1: builder\nnode:20-alpine\nnpm ci\nvite build\nOutputs dist/] --> B[Stage 2: runtime\nnginx:1.25-alpine\nCopy dist/ to /usr/share/nginx/html\nCopy nginx.conf\nExpose 80]
```

**Stage 1 (builder):**
- Base: `node:20-alpine`
- Copy `package.json` and `package-lock.json`
- `npm ci` (frozen install from lockfile)
- Copy source and run `vite build`
- Output: `dist/` directory

**Stage 2 (runtime):**
- Base: `nginx:1.25-alpine`
- Copy `dist/` from builder stage
- Mount `nginx.conf` that enables `try_files $uri /index.html` for SPA routing
- No Node.js in the final image

### 3.4 Image Tagging Convention

| Environment | Tag pattern | Example |
|-------------|------------|---------|
| Local build | `latest` | `wildtrack/backend:latest` |
| CI build | `git-{short SHA}` | `wildtrack/backend:git-a1b2c3d` |
| Release | `{semver}` | `wildtrack/backend:1.0.0` |

Images are built by CI on every push to `main`. Release tags are created when a Git tag is pushed.

### 3.5 Base Image Selection Rationale

| Service | Base image | Why |
|---------|-----------|-----|
| Backend | `python:3.12-slim` | Minimal Debian base; avoids `alpine` C-extension issues with `asyncpg` |
| Frontend (build) | `node:20-alpine` | Alpine is safe for pure Node builds |
| Frontend (serve) | `nginx:1.25-alpine` | Minimal static file server |
| PostgreSQL | `postgis/postgis:16-3.4` | Official image with PostGIS pre-installed |
| MongoDB | `mongo:7.0` | Official image; long-term support release |
| MinIO | `minio/minio:latest` | Official image; pegged to latest stable by digest in production |
| Mosquitto | `eclipse-mosquitto:2.0` | Official Eclipse Foundation image |

---

## 4. Docker Compose Design

### 4.1 Compose File Strategy

Two Compose files serve different contexts:

| File | Purpose |
|------|---------|
| `compose.infra.yml` | Local development: infrastructure services only |
| `compose.yml` | Full stack: all services including backend and frontend |

In CI and production, `compose.yml` is the authoritative file. In local development, developers use `compose.infra.yml` alongside native backend and frontend processes.

### 4.2 Service Definitions

```mermaid
flowchart TD
    subgraph compose.yml
        FE[frontend\nwildtrack/frontend:latest\nPort 3000]
        BE[backend\nwildtrack/backend:latest\nPort 8000]
        PG[(postgres\npostgis/postgis:16-3.4\nPort 5432)]
        MG[(mongodb\nmongo:7.0\nPort 27017)]
        MN[minio\nminio/minio:latest\nPort 9000/9001]
        MQ[mosquitto\neclipse-mosquitto:2.0\nPort 1883/8883]
    end

    BE -->|depends_on healthy| PG
    BE -->|depends_on healthy| MG
    BE -->|depends_on healthy| MN
    BE -->|depends_on healthy| MQ
    FE -->|depends_on healthy| BE
```

### 4.3 Health Checks

Every infrastructure service has a health check. The backend and frontend `depends_on` conditions use `service_healthy` so they only start after their dependencies pass the health check.

| Service | Health check command | Interval | Start period |
|---------|---------------------|----------|-------------|
| `postgres` | `pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}` | 5s | 10s |
| `mongodb` | `mongosh --eval "db.adminCommand('ping')"` | 5s | 15s |
| `minio` | `mc ready local` | 10s | 20s |
| `mosquitto` | `mosquitto_sub -t '$SYS/#' -C 1 -i healthcheck -W 3` | 10s | 5s |
| `backend` | `curl -f http://localhost:8000/health` | 10s | 30s |

### 4.4 Volume Declarations

All persistent data is stored in named Docker volumes managed by Docker Compose. Bind mounts are used only for configuration files.

| Volume | Service | Purpose |
|--------|---------|---------|
| `postgres_data` | postgres | PostgreSQL data directory (`/var/lib/postgresql/data`) |
| `mongodb_data` | mongodb | MongoDB data directory (`/data/db`) |
| `minio_data` | minio | MinIO object storage (`/data`) |
| `mosquitto_data` | mosquitto | Mosquitto persistence directory (`/mosquitto/data`) |
| `mosquitto_log` | mosquitto | Mosquitto log files (`/mosquitto/log`) |

Configuration files are mounted as read-only bind mounts:

| Bind mount source | Target in container | Service |
|-------------------|---------------------|---------|
| `./config/mosquitto/mosquitto.conf` | `/mosquitto/config/mosquitto.conf` | mosquitto |
| `./config/mosquitto/passwd` | `/mosquitto/config/passwd` | mosquitto |
| `./config/nginx/nginx.conf` | `/etc/nginx/nginx.conf` | nginx (prod) |

### 4.5 Resource Limits

All services in `compose.yml` declare memory and CPU limits to prevent runaway containers from starving the host.

| Service | Memory limit | CPU limit |
|---------|-------------|-----------|
| `postgres` | 512 MB | 1.0 |
| `mongodb` | 512 MB | 1.0 |
| `minio` | 256 MB | 0.5 |
| `mosquitto` | 64 MB | 0.25 |
| `backend` | 512 MB | 1.0 |
| `frontend` | 64 MB | 0.25 |

These limits are appropriate for a VPS with 2–4 GB RAM running the full MVP stack.

### 4.6 Restart Policy

All services use `restart: unless-stopped`. This ensures services restart automatically after a host reboot or after Docker daemon restarts, but do not restart if manually stopped by an operator.

---

## 5. Network Design

### 5.1 Network Topology

WildTrack uses two isolated Docker networks. Services only join the networks they need.

```mermaid
flowchart TD
    subgraph wildtrack_public
        NX[nginx\nReverse proxy]
        FE[frontend]
        BE[backend]
    end

    subgraph wildtrack_private
        BE2[backend]
        PG[(postgres)]
        MG[(mongodb)]
        MN[minio]
        MQ[mosquitto]
    end

    Internet -->|443 HTTPS\n8883 MQTTS| NX
    NX --> FE
    NX --> BE
    BE -.->|same container\ndual-homed| BE2
    BE2 --> PG
    BE2 --> MG
    BE2 --> MN
    BE2 --> MQ
```

### 5.2 Network Definitions

| Network | Driver | Purpose |
|---------|--------|---------|
| `wildtrack_public` | `bridge` | Connects Nginx to backend and frontend; Nginx is the only service here that receives external traffic |
| `wildtrack_private` | `bridge` | Connects backend to all data services; completely isolated from external access |

**Key rule:** `postgres`, `mongodb`, `minio`, and `mosquitto` are **only** on `wildtrack_private`. They are never reachable from outside the Docker host.

### 5.3 Port Exposure Policy

| Service | Local dev ports (host:container) | Production ports |
|---------|----------------------------------|-----------------|
| `postgres` | `5432:5432` | None (private network only) |
| `mongodb` | `27017:27017` | None (private network only) |
| `minio` API | `9000:9000` | None (internal); presigned URLs route via Nginx |
| `minio` console | `9001:9001` | None (local dev and VPN only) |
| `mosquitto` | `1883:1883` (dev), `8883:8883` (prod) | `8883` only (TLS) |
| `backend` | `8000:8000` | None (behind Nginx) |
| `frontend` | `3000:80` | None (behind Nginx) |
| `nginx` | — | `80`, `443` |

### 5.4 Internal DNS

Docker Compose assigns each service a hostname equal to its service name. The backend connects to PostgreSQL at `postgres:5432`, MongoDB at `mongodb:27017`, MinIO at `minio:9000`, and Mosquitto at `mosquitto:1883`. No IP addresses are hardcoded.

### 5.5 Nginx Routing Rules (Production)

```mermaid
flowchart TD
    A[Incoming request] --> B{Host + Path}
    B -->|GET /api/* | C[Proxy to backend:8000]
    B -->|GET /* | D[Proxy to frontend:80]
    B -->|CONNECT mqtt.wildtrack.local:8883| E[TCP stream to mosquitto:8883]
    C --> F[FastAPI]
    D --> G[Nginx SPA server]
    E --> H[Mosquitto TLS]
```

Nginx terminates TLS for HTTP traffic. MQTT TLS termination is handled by Mosquitto directly using its own certificate (Nginx passes through the TCP stream).

---

## 6. PostgreSQL Design

### 6.1 Image and Version

**Image:** `postgis/postgis:16-3.4`  
**PostgreSQL version:** 16  
**PostGIS version:** 3.4  

PostgreSQL 16 is the current LTS release. PostGIS 3.4 includes support for `GEOMETRY(POINT, 4326)` and the spatial index functions required by WildTrack.

### 6.2 Initialization

On first startup, PostgreSQL runs any `.sql` files found in `/docker-entrypoint-initdb.d/`. WildTrack mounts one init script:

`init.sql`:
1. Creates the `wildtrack` database (if not already the default)
2. Enables the `postgis` extension: `CREATE EXTENSION IF NOT EXISTS postgis;`
3. Enables `uuid-ossp` extension (for UUID generation fallback): `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`

Schema migrations (tables, indexes, constraints) are run by Alembic on backend startup, not in the init script. The init script only creates extensions.

### 6.3 Configuration Tuning

The following PostgreSQL parameters are set via environment variables or a mounted `postgresql.conf`:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `max_connections` | 50 | MVP has one backend instance; 50 is safe for the connection pool |
| `shared_buffers` | 128MB | 25% of 512MB container memory limit |
| `work_mem` | 4MB | Sufficient for analytic queries at MVP scale |
| `wal_level` | `replica` | Required for future streaming replication |
| `log_min_duration_statement` | `500` | Log slow queries (>500ms) for development; disabled in prod |

### 6.4 Connection Pooling

The backend uses **SQLAlchemy's built-in async connection pool** (`AsyncEngine` with `pool_size=10`, `max_overflow=5`). No external connection pooler (PgBouncer) is included in the MVP.

**PgBouncer** should be added when:
- Multiple backend instances run simultaneously, or
- The number of concurrent connections approaches `max_connections`

### 6.5 Data Volume and Backup

PostgreSQL data is stored in the `postgres_data` named volume mounted at `/var/lib/postgresql/data`.

For backup details, see §11.

### 6.6 PostGIS Spatial Configuration

All spatial columns use **SRID 4326** (WGS 84 geographic coordinates). GiST indexes are created on all geometry columns. Spatial queries use `ST_DWithin` for proximity and `ST_AsGeoJSON` for GeoJSON serialization in geoportal queries.

---

## 7. MongoDB Design

### 7.1 Image and Version

**Image:** `mongo:7.0`  
**MongoDB version:** 7.0 (LTS)

MongoDB 7.0 includes time-series collection improvements and the aggregation operators used by WildTrack's analytics pipeline.

### 7.2 Initialization

MongoDB does not use a separate init script. The backend creates collections and indexes via Motor on first startup. The `infrastructure/mongodb.py` module includes an `initialize_collections()` function called during application lifespan startup that:

1. Creates each collection if it does not exist
2. Creates all defined indexes (see §7.3)

This is idempotent — safe to run on every startup.

### 7.3 Index Strategy

| Collection | Index | Type | Purpose |
|------------|-------|------|---------|
| `iot_events` | `station_id` | Single-field | Filter events by station |
| `iot_events` | `device_id` | Single-field | Filter events by device |
| `iot_events` | `animal_id` | Sparse | Filter events where animal was identified |
| `iot_events` | `timestamp` (desc) | Single-field | Time-range queries; most recent first |
| `iot_events` | `(station_id, timestamp)` | Compound | Station timeline queries |
| `device_telemetry` | `(device_id, timestamp)` | Compound | Device heartbeat timeline |
| `device_telemetry` | `timestamp` (desc, TTL) | TTL | Auto-expire records older than 90 days |
| `alerts` | `station_id` | Single-field | Filter alerts by station |
| `alerts` | `(status, created_at)` | Compound | Open alert queries sorted by age |
| `media_metadata` | `event_id` | Unique | One media document per event |
| `dead_letter_events` | `received_at` (desc) | Single-field | Review most recent failures first |

### 7.4 TTL Index for Telemetry

Device telemetry heartbeats are high-volume records. A **TTL index** on `device_telemetry.timestamp` automatically expires documents older than 90 days. This prevents unbounded collection growth without a manual cleanup job.

The TTL value is configurable via the `TELEMETRY_TTL_DAYS` environment variable (default: 90).

### 7.5 WiredTiger Storage Engine

MongoDB 7.0 uses **WiredTiger** by default. WildTrack does not change this. WiredTiger's document-level locking and compression are appropriate for the write patterns generated by IoT event ingestion.

### 7.6 Authentication

In development, MongoDB uses no authentication (the `mongo:7.0` image default). In production, the `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD` environment variables enable authentication. The backend connection URI includes credentials:

```
mongodb://{MONGODB_USER}:{MONGODB_PASSWORD}@mongodb:27017/{MONGODB_DB}?authSource=admin
```

### 7.7 MongoDB Atlas Free Tier (Alternative for Development/MVP)

> **Option:** For development and MVP, MongoDB Atlas free tier (M0 cluster, 512 MB storage) can replace the self-hosted `mongo:7.0` container. This eliminates the need to run a local MongoDB container and simplifies setup for developers who prefer a managed cloud database.

To use Atlas instead of the local container:
1. Create a free MongoDB Atlas account and provision an M0 cluster.
2. Allowlist your IP address in Atlas Network Access.
3. Create a database user with read/write permissions.
4. Replace `MONGODB_URL` in `.env` with the Atlas connection string:
   ```
   mongodb+srv://{user}:{password}@cluster0.xxxxx.mongodb.net/{MONGODB_DB}?retryWrites=true&w=majority
   ```
5. Remove (or skip starting) the `mongodb` service in `compose.infra.yml`.

**When to prefer Atlas:** Initial development, CI test environments, or any context where running Docker locally is inconvenient.

**When to prefer self-hosted:** Production VPS deployments (avoids data leaving your infrastructure), offline development, or when Atlas free tier limits (512 MB, shared cluster) are exceeded.

The backend Motor connection code is identical for both options — only the `MONGODB_URL` environment variable changes.

---

## 8. MinIO Design

### 8.1 Image and Version

**Image:** `minio/minio:latest` (pinned to a specific digest in production)

MinIO provides an S3-compatible API. The WildTrack backend uses the MinIO Python SDK, which is fully compatible with AWS S3. Migrating from MinIO to S3 in production requires changing only environment variables.

### 8.2 Startup and Bucket Initialization

MinIO starts as a server with a single data directory. On first startup, the `wildtrack-media` bucket must be created. This is handled by a one-time initialization script (`scripts/init_minio.sh`) run via a `minio-init` service in `compose.yml` that exits after completing bucket setup.

The `minio-init` service:
1. Waits for MinIO to be healthy
2. Creates the `wildtrack-media` bucket using `mc mb`
3. Sets bucket policy to **private** (no anonymous access)
4. Exits with code 0

### 8.3 Storage Layout

```mermaid
flowchart TD
    A[wildtrack-media\nbucket] --> B[{station_id}/]
    B --> C[{year}/]
    C --> D[{month}/]
    D --> E[{device_id}_{timestamp}_{filename}]
```

Object key format: `{station_id}/{year}/{month}/{device_id}_{timestamp_utc}_{original_filename}`

Example: `019281ac-1234.../2026/06/019281aa-cd34..._2026-06-13T09-45-00Z_capture.jpg`

### 8.4 Access Control

The bucket is **private**. Access is controlled by two mechanisms:

- **Backend SDK access:** The backend uses `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` credentials (root credentials in MVP) to upload objects and generate presigned URLs.
- **Presigned URLs:** The browser receives a time-limited presigned URL (15-minute TTL) from `GET /media/{event_id}/presigned`. The browser accesses the object directly via this URL. No traffic routes through the FastAPI backend.

In production, MinIO is not exposed to the public internet. Presigned URLs point to a path behind the Nginx reverse proxy (`/minio-internal/`) which proxies to MinIO on the private network.

### 8.5 Console Access

MinIO includes a web console at port `9001`. In development this is exposed on `localhost:9001`. In production it is accessible only via an SSH tunnel or VPN — it is not exposed through Nginx.

### 8.6 Data Volume

MinIO data is stored in the `minio_data` named volume mounted at `/data`.

---

## 9. MQTT Broker Design

### 9.1 Image and Version

**Image:** `eclipse-mosquitto:2.0`  

Mosquitto 2.0 is the current stable release. It supports MQTT 3.1.1 and MQTT 5.0, configurable TLS, username/password authentication, and ACL-based topic authorization.

### 9.2 Configuration File

Mosquitto is configured via a mounted `mosquitto.conf` file. Key configuration sections:

> **Local development:** Use plain MQTT on port `1883` with `allow_anonymous true`. No certificates or password files are required for local testing. TLS and authentication are production requirements only.

| Section | Development | Production |
|---------|------------|------------|
| Listener | `1883` (plain TCP, no auth) | `8883` (TLS, auth required) |
| Authentication | `allow_anonymous true` | `allow_anonymous false` |
| Password file | Not set | `/mosquitto/config/passwd` |
| Persistence | `true` | `true` |
| Persistence location | `/mosquitto/data` | `/mosquitto/data` |
| Logging | `stdout` | `stdout` + `/mosquitto/log/mosquitto.log` |

### 9.3 Topic Structure

| Topic | Publisher | Subscriber | QoS |
|-------|-----------|-----------|-----|
| `wildtrack/events/{station_id}` | ESP32 device | Backend | 1 |
| `wildtrack/telemetry/{device_id}` | ESP32 device | Backend | 1 |
| `wildtrack/status/{device_id}` | ESP32 device (LWT) | Backend | 1 |

**Last Will and Testament (LWT):** Each ESP32 connects with a LWT message on `wildtrack/status/{device_id}` with payload `offline`. When a device unexpectedly disconnects, Mosquitto publishes this message automatically. The backend subscribes to `wildtrack/status/#` and processes offline notifications to update device status.

### 9.4 QoS Policy

**QoS 1 (At Least Once)** is used for all event and telemetry topics. This guarantees that messages are delivered even if the broker or backend is temporarily unavailable, with the trade-off of possible duplicate delivery. The backend handles duplicates gracefully: events with the same `event_id` are idempotent (MongoDB's `insertOne` is protected by a unique index on `event_id`).

### 9.5 Authentication in Production

In production, each ESP32 device authenticates with a unique username and password. The `mosquitto_passwd` utility creates the hashed password file. ACLs restrict each device to publishing only to its own topic prefix:

| Username | Publish permission | Subscribe permission |
|----------|--------------------|---------------------|
| `device-{device_id}` | `wildtrack/events/{station_id}`, `wildtrack/telemetry/{device_id}`, `wildtrack/status/{device_id}` | None |
| `backend` | None | `wildtrack/events/#`, `wildtrack/telemetry/#`, `wildtrack/status/#` |

### 9.6 TLS in Production

In production, Mosquitto uses TLS on port `8883`. The TLS certificate is the same certificate used by Nginx (Let's Encrypt or self-signed). Mosquitto requires:
- `cafile`: CA certificate
- `certfile`: Server certificate
- `keyfile`: Private key

Certificates are mounted from the same volume used by Nginx.

### 9.7 Persistence

Mosquitto persistence is enabled with `persistence true`. In-flight QoS 1 messages and subscription state are stored in `/mosquitto/data`. This ensures that if Mosquitto restarts, buffered messages are not lost.

---

## 10. Environment Variables Strategy

### 10.1 Variable Scopes

Environment variables are split by scope to prevent accidental leakage:

```mermaid
flowchart TD
    A[.env.backend] --> B[backend container]
    C[.env.frontend] --> D[frontend container\nbuild-time VITE_ vars]
    E[.env.infra] --> F[postgres container]
    E --> G[mongodb container]
    E --> H[minio container]
    E --> I[mosquitto container]
```

### 10.2 Backend Environment Variables

Full reference — all variables consumed by the FastAPI backend:

| Variable | Example | Required | Description |
|----------|---------|----------|-------------|
| `APP_ENV` | `development` | YES | `development`, `test`, or `production` |
| `LOG_LEVEL` | `INFO` | NO | Python logging level |
| `DEBUG` | `true` | NO | Enables verbose tracing |
| `JWT_SECRET_KEY` | `{random 64-char string}` | YES | HS256 signing secret — must be secret |
| `JWT_EXPIRY_SECONDS` | `86400` | NO | Token lifetime in seconds |
| `POSTGRES_HOST` | `postgres` | YES | Service name in Docker network |
| `POSTGRES_PORT` | `5432` | NO | Default 5432 |
| `POSTGRES_DB` | `wildtrack` | YES | Database name |
| `POSTGRES_USER` | `wildtrack` | YES | Database user |
| `POSTGRES_PASSWORD` | `{secret}` | YES | Database password |
| `MONGODB_URI` | `mongodb://wildtrack:pass@mongodb:27017/wildtrack?authSource=admin` | YES | Full URI including credentials |
| `MONGODB_DB` | `wildtrack` | YES | MongoDB database name |
| `MINIO_ENDPOINT` | `minio:9000` | YES | MinIO service endpoint |
| `MINIO_ACCESS_KEY` | `{access key}` | YES | MinIO credentials |
| `MINIO_SECRET_KEY` | `{secret key}` | YES | MinIO credentials |
| `MINIO_BUCKET` | `wildtrack-media` | YES | Target bucket name |
| `MINIO_USE_SSL` | `false` | NO | `true` in production with TLS |
| `MINIO_PRESIGNED_URL_EXPIRY` | `900` | NO | Seconds; default 15 minutes |
| `MQTT_HOST` | `mosquitto` | YES | Service name in Docker network |
| `MQTT_PORT` | `1883` | YES | `8883` in production |
| `MQTT_CLIENT_ID` | `wildtrack-backend` | NO | MQTT client identifier |
| `MQTT_USERNAME` | `backend` | NO | Required in production |
| `MQTT_PASSWORD` | `{secret}` | NO | Required in production |
| `DEVICE_OFFLINE_THRESHOLD_MINUTES` | `10` | NO | Minutes since last_seen before offline |
| `DEVICE_HEALTH_CHECK_INTERVAL_SECONDS` | `300` | NO | Background task frequency |
| `EMPTY_TANK_THRESHOLD_GRAMS` | `50` | NO | Alert trigger threshold |
| `MEDIA_MAX_UPLOAD_SIZE_BYTES` | `10485760` | NO | 10 MB default |
| `TELEMETRY_TTL_DAYS` | `90` | NO | MongoDB TTL for telemetry documents |
| `ADMIN_SEED_EMAIL` | `admin@wildtrack.local` | YES (seed) | First admin bootstrap email |
| `ADMIN_SEED_PASSWORD` | `{secret}` | YES (seed) | First admin bootstrap password |

### 10.3 Frontend Environment Variables

Vite exposes only variables prefixed with `VITE_` to the browser bundle. All other variables are build-time only.

| Variable | Example | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Backend API URL; rewritten per environment |
| `VITE_MAP_TILE_URL` | `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` | OpenStreetMap tile source |
| `VITE_MAP_REFRESH_INTERVAL_MS` | `60000` | Geoportal auto-refresh interval |

> ⚠️ Never place secrets in `VITE_` variables. They are embedded in the JavaScript bundle and readable by any user.

### 10.4 Infrastructure Environment Variables

| Variable | Service | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | postgres | Superuser login name |
| `POSTGRES_PASSWORD` | postgres | Superuser password |
| `POSTGRES_DB` | postgres | Database created on first startup |
| `MONGO_INITDB_ROOT_USERNAME` | mongodb | Root admin username |
| `MONGO_INITDB_ROOT_PASSWORD` | mongodb | Root admin password |
| `MINIO_ROOT_USER` | minio | MinIO root access key |
| `MINIO_ROOT_PASSWORD` | minio | MinIO root secret key |

### 10.5 Secret Management by Environment

| Environment | Method |
|-------------|--------|
| Local development | `.env` files in project root (gitignored) |
| CI (GitHub Actions) | GitHub Actions Secrets |
| VPS production | `.env` file owned by `root`, permissions `600` |
| Cloud production (future) | AWS Secrets Manager / HashiCorp Vault |

`.env.example` files (one per scope) are committed to source control with placeholder values. Actual `.env` files are listed in `.gitignore`.

---

## 11. Backup Strategy

### 11.1 Backup Scope

| Data source | Backup method | Frequency | Retention |
|------------|--------------|-----------|-----------|
| PostgreSQL | `pg_dump` (custom format) | Daily | 7 daily, 4 weekly |
| MongoDB | `mongodump` | Daily | 7 daily, 4 weekly |
| MinIO objects | `mc mirror` to secondary storage | Daily | 30 days |
| Mosquitto persistence | Volume snapshot | Daily | 7 daily |

### 11.2 PostgreSQL Backup

```mermaid
flowchart LR
    A[Daily cron job\nor Docker timer] --> B[pg_dump\ncustom format\n-Fc flag]
    B --> C[/backups/postgres/\nwildtrack_{date}.dump]
    C --> D[Retention script\ndelete files > 7 days]
```

`pg_dump` runs inside the `postgres` container (or as a separate `backup` service in Compose):

- Format: custom (`-Fc`) for selective restore capability
- Output: `/backups/postgres/wildtrack_YYYY-MM-DD.dump`
- Restore: `pg_restore -d wildtrack -Fc wildtrack_YYYY-MM-DD.dump`

### 11.3 MongoDB Backup

`mongodump` runs inside the `mongodb` container:

- Output: `/backups/mongodb/YYYY-MM-DD/` (BSON directory)
- Compression: `--gzip` flag
- Restore: `mongorestore --gzip /backups/mongodb/YYYY-MM-DD/`

### 11.4 MinIO Backup

MinIO objects are mirrored daily to a secondary location using the MinIO Client (`mc mirror`):

**MVP targets (in order of preference):**
1. A separate mounted disk or NFS share on the same VPS
2. A second MinIO instance on a different machine
3. Rclone sync to any S3-compatible target (Backblaze B2, Cloudflare R2, AWS S3)

`mc mirror` performs incremental sync — only changed or new objects are copied.

### 11.5 Backup Volume Mount

A dedicated `backup` Docker volume is mounted by the backup services:

```
/backups/
├── postgres/
│   ├── wildtrack_2026-06-13.dump
│   └── wildtrack_2026-06-12.dump
├── mongodb/
│   ├── 2026-06-13/
│   └── 2026-06-12/
└── minio/
    └── mirror target (if local disk)
```

### 11.6 Restore Procedure

A documented runbook in `docs/operations/restore.md` covers the restore procedure for each data source. The MVP restoration target is **< 1 hour** for a complete restore from the most recent daily backup.

### 11.7 Backup Verification

Backups are verified weekly by restoring to a temporary container and running a health check:
- PostgreSQL: `pg_restore` + `SELECT COUNT(*) FROM stations`
- MongoDB: `mongorestore` + `db.iot_events.countDocuments({})`
- MinIO: `mc ls` to confirm objects exist at the mirror target

---

## 12. Observability Strategy

### 12.1 MVP Observability Stack

The MVP uses a lightweight, self-hosted observability approach. No external APM service is required.

```mermaid
flowchart TD
    subgraph Application
        BE[Backend\nFastAPI]
        FE[Frontend\nNginx]
        MQ[Mosquitto]
        PG[PostgreSQL]
    end

    subgraph Observability Stack - Optional MVP
        PR[Prometheus\nMetrics scraper]
        GF[Grafana\nDashboards]
        LA[Loki\nLog aggregation]
    end

    BE -->|/metrics\nPrometheus format| PR
    FE -->|access logs| LA
    MQ -->|$SYS/ metrics| PR
    PR --> GF
    LA --> GF
```

The observability stack (Prometheus + Grafana + Loki) is defined as an **optional** Docker Compose profile (`--profile monitoring`). It is not required for the MVP to function and is off by default in development.

### 12.2 Backend Metrics

The FastAPI backend exposes a `/metrics` endpoint via `prometheus-fastapi-instrumentator`. This automatically provides:

- Request count per endpoint
- Request latency histogram per endpoint
- HTTP error rate per status code
- Active connections

Custom business metrics (added as needed):

| Metric | Type | Description |
|--------|------|-------------|
| `wildtrack_iot_events_ingested_total` | Counter | Total MQTT events successfully processed |
| `wildtrack_dead_letter_total` | Counter | Total events sent to dead letter |
| `wildtrack_device_offline_count` | Gauge | Currently offline devices |
| `wildtrack_alert_open_count` | Gauge | Currently open alerts |

### 12.3 Grafana Dashboards (Optional)

Pre-configured Grafana dashboards are stored as JSON provisioning files in `config/grafana/dashboards/`:

| Dashboard | Purpose |
|-----------|---------|
| Backend Overview | Request rate, latency percentiles, error rate |
| IoT Ingestion | Events/min, dead letters, MQTT connected clients |
| Database Health | PostgreSQL connection count, query time, MongoDB op count |
| Business KPIs | Active stations, events/hour, open alerts |

### 12.4 Uptime Monitoring

In production, a simple HTTP uptime check on `GET /health` is configured via:

- **Self-hosted:** [Uptime Kuma](https://github.com/louislam/uptime-kuma) (single Docker container, can run on the same VPS)
- **Free external:** Better Uptime free tier, UptimeRobot free tier

The `/health` endpoint returns the status of all dependencies and is the authoritative health signal.

---

## 13. Logging Strategy

### 13.1 Log Collection Architecture

```mermaid
flowchart LR
    A[Backend\nJSON logs\nstdout] --> C[Docker log driver]
    B[Nginx\naccess logs\nstdout] --> C
    D[Mosquitto\nstdout] --> C
    C --> E{Log destination}
    E -->|development| F[docker logs\ntail -f]
    E -->|production basic| G[Journald\nor Docker log files]
    E -->|production full| H[Loki\nvia Promtail]
    H --> I[Grafana\nlog exploration]
```

### 13.2 Log Format

All application logs (backend) are emitted as **structured JSON** in production and as human-readable colored text in development. The format is controlled by `APP_ENV`.

**Production JSON log line fields:**

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO 8601 | Log event time |
| `level` | string | `INFO`, `WARNING`, `ERROR` |
| `logger` | string | Logger name (module path) |
| `message` | string | Human-readable message |
| `request_id` | UUID | Correlates all logs for one HTTP request |
| `user_id` | UUID \| null | Authenticated user if available |
| `duration_ms` | number | Response duration (HTTP request logs only) |
| `status_code` | number | HTTP status (HTTP request logs only) |
| `event_id` | UUID \| null | IoT event ID (ingestion logs only) |

### 13.3 Log Rotation

Docker log files are managed with Docker's `json-file` log driver with rotation:

```
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "5"
```

This keeps a maximum of 50 MB of logs per container on disk. In production with Loki, logs are exported before rotation and the local file limit is kept smaller.

### 13.4 Log Levels per Environment

| Environment | Default log level | Slow query logging |
|-------------|------------------|-------------------|
| `development` | `DEBUG` | Yes (>500ms) |
| `test` | `WARNING` | No |
| `production` | `INFO` | No (use APM for this) |

---

## 14. Security Strategy

### 14.1 Security Layers

```mermaid
flowchart TD
    A[Internet] --> B[Firewall\nOnly 80, 443, 8883 open]
    B --> C[Nginx\nTLS termination\nRate limiting\nSecurity headers]
    C --> D[FastAPI\nJWT validation\nInput validation\nRole checks]
    D --> E[Private Docker network\nNo external DB access]
    E --> F[PostgreSQL\nAuthenticated connection\nPrinciple of least privilege]
    E --> G[MongoDB\nAuthenticated connection]
    E --> H[MinIO\nAuthenticated\nPrivate bucket]
    E --> I[Mosquitto\nAuth required\nACL per device]
```

### 14.2 Network Security

**Firewall rules (VPS production):**

| Port | Protocol | Allowed from | Purpose |
|------|----------|-------------|---------|
| 22 | TCP | Operator IPs only | SSH admin access |
| 80 | TCP | Anywhere | HTTP (redirects to 443) |
| 443 | TCP | Anywhere | HTTPS |
| 8883 | TCP | Anywhere | MQTT over TLS |
| All other ports | — | Deny | Database ports never exposed |

`ufw` (Uncomplicated Firewall) is used on Ubuntu VPS. Default policy: deny incoming, allow outgoing.

### 14.3 TLS Configuration

**Nginx TLS settings:**

| Setting | Value |
|---------|-------|
| Protocols | TLSv1.2, TLSv1.3 |
| Ciphers | ECDHE-ECDSA-AES128-GCM-SHA256, ECDHE-RSA-AES128-GCM-SHA256 (and TLS 1.3 defaults) |
| HSTS | `Strict-Transport-Security: max-age=31536000` |
| Certificate | Let's Encrypt (auto-renewal via Certbot or `nginx-proxy-acme`) |

**MQTT TLS:** Mosquitto uses the same certificate as Nginx, renewed via the same Certbot process.

### 14.4 HTTP Security Headers

Nginx adds the following security headers on all responses:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'; img-src 'self' *.openstreetmap.org data:; connect-src 'self' {minio_presigned_domain}` |

### 14.5 Application Security

| Concern | Mitigation |
|---------|-----------|
| Password storage | bcrypt with work factor 12 |
| JWT security | HS256 with 64-character random secret; 24-hour expiry |
| SQL injection | SQLAlchemy ORM with parameterized queries; no raw SQL string concatenation |
| Input validation | Pydantic schemas on all API inputs; Zod on all form inputs |
| File upload | MIME type validation, 10 MB size limit, random object key (not original filename exposed) |
| Rate limiting | Nginx `limit_req_zone` on `/api/auth/*` endpoints (max 10 req/minute per IP) |
| CORS | FastAPI CORS middleware restricted to the frontend origin |
| Secrets in logs | Log interceptor strips `password`, `token`, `Authorization` fields |

### 14.6 Container Security

| Practice | Implementation |
|----------|---------------|
| Non-root user | Backend container runs as UID 1001 (`wildtrack`) |
| Read-only filesystem | Backend and frontend containers use `read_only: true` with a writable tmpfs for `/tmp` |
| No privileged containers | No container uses `privileged: true` |
| Image scanning | CI scans images with Trivy before push (see §15) |
| No secrets in images | All secrets passed via environment variables; never in `Dockerfile` or image layers |

---

## 15. CI/CD Strategy

### 15.1 Pipeline Overview

```mermaid
flowchart TD
    A[Git push to any branch] --> B[CI: Test pipeline]
    B --> C[Backend tests\npytest]
    B --> D[Frontend tests\nVitest]
    C --> E{Tests pass?}
    D --> E
    E -->|no| F[Fail: notify developer]
    E -->|yes| G{Is branch main?}
    G -->|no| H[Done: PR ready to merge]
    G -->|yes| I[CI: Build pipeline]
    I --> J[Build backend image]
    I --> K[Build frontend image]
    J --> L[Scan with Trivy]
    K --> L
    L --> M[Push to GHCR]
    M --> N[Deploy pipeline\ntrigger optional]
    N --> O[SSH to VPS\ndocker compose pull\ndocker compose up -d]
```

### 15.2 GitHub Actions Workflows

Three workflow files in `.github/workflows/`:

**`test.yml`** — runs on every push to every branch:
- Backend: set up Python 3.12, install dependencies, run `pytest` with coverage
- Frontend: set up Node 20, `npm ci`, run `vitest run --coverage`
- Lint: `ruff` (backend) and `eslint` (frontend)
- Type check: `mypy` (backend) and `tsc --noEmit` (frontend)

**`build.yml`** — runs on push to `main` only:
- Build backend Docker image
- Build frontend Docker image with `VITE_API_BASE_URL` from GitHub Secrets
- Scan both images with `aquasecurity/trivy-action`
- Push to GitHub Container Registry (`ghcr.io/{org}/wildtrack-backend:{sha}`)

**`deploy.yml`** — triggered manually or after `build.yml` succeeds on `main`:
- SSH to the production VPS
- Pull new images from GHCR
- Run `docker compose up -d --remove-orphans`
- Verify health: `curl /health` within 60 seconds
- Roll back if health check fails: `docker compose up -d --no-deps backend@{previous_sha}`

### 15.3 Branch Strategy

| Branch | Purpose | Protected |
|--------|---------|-----------|
| `main` | Production-ready code; all CI must pass | YES |
| `develop` | Integration branch; PRs merge here first | YES |
| `feature/{name}` | Individual feature development | NO |
| `fix/{name}` | Bug fixes | NO |
| `docs/{name}` | Documentation updates | NO |

### 15.4 Pull Request Requirements

Before a PR can merge to `main`:
- All CI tests pass (backend + frontend)
- Lint and type checks pass
- At least one approving review
- No merge conflicts
- Coverage does not drop below threshold

### 15.5 Dependency Updates

**Dependabot** is configured for:
- Python dependencies (`pyproject.toml`) — weekly PRs
- npm dependencies (`package.json`) — weekly PRs
- Docker base image digests — monthly PRs

---

## 16. GitHub Repository Strategy

### 16.1 Repository Structure

WildTrack is organized as a **monorepo** — backend, frontend, infrastructure, and documentation in a single repository.

```
wildtrack/
├── backend/                   # FastAPI application
├── frontend/                  # React application
├── config/                    # Service configuration files
│   ├── mosquitto/
│   ├── nginx/
│   └── grafana/               # Optional monitoring
├── docs/
│   ├── sdd/                   # Specification documents
│   ├── decisions/             # Architecture Decision Records
│   └── operations/            # Runbooks (restore, deploy, etc.)
├── scripts/                   # Operational scripts
├── compose.yml                # Full stack Compose
├── compose.infra.yml          # Infrastructure-only Compose
├── .github/
│   ├── workflows/             # CI/CD pipelines
│   └── PULL_REQUEST_TEMPLATE.md
├── .gitignore
├── CLAUDE.md                  # Project context for AI assistants
└── README.md
```

### 16.2 `.gitignore` Essentials

The following are always excluded from source control:

```
# Environment files
.env
.env.*
!.env.example

# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/
htmlcov/

# Node
node_modules/
dist/

# Docker generated
postgres_data/
mongodb_data/
minio_data/

# Certificates
*.pem
*.key
*.crt

# IDE
.vscode/settings.json
.idea/
```

### 16.3 Repository Secrets (GitHub Actions)

Secrets stored in GitHub Secrets (`Settings → Secrets → Actions`):

| Secret | Used by |
|--------|---------|
| `JWT_SECRET_KEY` | `build.yml` (injected into image labels or deploy env) |
| `POSTGRES_PASSWORD` | `deploy.yml` |
| `MONGODB_PASSWORD` | `deploy.yml` |
| `MINIO_SECRET_KEY` | `deploy.yml` |
| `MQTT_BACKEND_PASSWORD` | `deploy.yml` |
| `ADMIN_SEED_PASSWORD` | `deploy.yml` (first deploy only) |
| `VPS_SSH_KEY` | `deploy.yml` |
| `VPS_HOST` | `deploy.yml` |
| `GHCR_TOKEN` | `build.yml` (push to GHCR) |

### 16.4 Issue and PR Templates

A `PULL_REQUEST_TEMPLATE.md` prompts contributors to:
- Link the issue being resolved
- Describe what was changed and why
- Note any migration or deployment steps
- Confirm tests were run locally

---

## 17. Deployment Strategy

> **Pragmatic deployment principle:** The WildTrack MVP is designed to run locally first. A developer can start the entire stack on a laptop with `docker compose up`. Cloud or VPS deployment is not required to build, test, or demonstrate the MVP. When ready to share externally, the stack deploys to a single low-cost VPS (e.g., Hetzner CX32 at ~€14/month) with no architecture changes — only environment variables and `.env` files change.

### 17.1 Deployment Environments

| Environment | Infrastructure | Access |
|-------------|---------------|--------|
| `local` | Developer laptop — `compose.infra.yml` + native processes | Developer only |
| `staging` | VPS (same setup as prod, smaller instance) | Team only |
| `production` | VPS or cloud | Public |

The MVP does not require a staging environment to begin. A single VPS running production is sufficient until the team grows.

### 17.2 First Deployment Steps

```mermaid
flowchart TD
    A[Provision VPS\nUbuntu 22.04 LTS] --> B[Install Docker Engine\n+ Docker Compose plugin]
    B --> C[Configure UFW firewall\n22 SSH, 80 HTTP, 443 HTTPS, 8883 MQTT]
    C --> D[Create wildtrack user\nAdd to docker group]
    D --> E[Clone repository\nto /opt/wildtrack]
    E --> F[Create .env files\nwith production secrets]
    F --> G[Pull images from GHCR\ndocker compose pull]
    G --> H[Start infrastructure services\ndocker compose up -d postgres mongodb minio mosquitto]
    H --> I[Run MinIO init script\ndocker compose run minio-init]
    I --> J[Start backend\ndocker compose up -d backend]
    J --> K[Run admin seed script\ndocker compose exec backend python scripts/seed_admin.py]
    K --> L[Start frontend + nginx\ndocker compose up -d frontend nginx]
    L --> M[Configure DNS\nA record → VPS IP]
    M --> N[Issue TLS certificate\ncertbot --nginx]
    N --> O[Verify /health endpoint]
```

### 17.3 Update Procedure

Standard update (zero-downtime for the stateless backend):

1. CI builds and pushes new image to GHCR on merge to `main`
2. `deploy.yml` runs `docker compose pull backend`
3. `docker compose up -d --no-deps backend` — Docker replaces the old container with the new one
4. Wait for health check to pass (30-second window)
5. If health check fails, redeploy previous image tag

**Note:** True zero-downtime requires multiple backend instances behind a load balancer. The MVP with a single backend container has approximately 3–5 seconds of unavailability during container restart. This is acceptable for the MVP.

---

## 18. VPS Deployment Option

### 18.1 Recommended VPS Specifications (MVP)

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 2 GB | 4 GB |
| Storage | 40 GB SSD | 80 GB SSD |
| Network | 100 Mbps | 1 Gbps |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

**Recommended providers:** Hetzner Cloud (best price/performance in Europe), DigitalOcean Droplet, Linode/Akamai Cloud, OVHcloud VPS.

### 18.2 Resource Allocation on 4 GB VPS

```mermaid
pie title RAM Allocation (4 GB VPS)
    "PostgreSQL 512 MB" : 512
    "MongoDB 512 MB" : 512
    "Backend 512 MB" : 512
    "MinIO 256 MB" : 256
    "Frontend/Nginx 64 MB" : 64
    "Mosquitto 64 MB" : 64
    "Monitoring stack 512 MB" : 512
    "OS + overhead 1024 MB" : 1024
```

### 18.3 VPS Architecture Diagram

```mermaid
flowchart TD
    subgraph Hetzner CX22 - 4GB VPS
        UFW[UFW Firewall]
        NX[Nginx\nSSL + Reverse Proxy]
        FE[Frontend Container\nNginx SPA]
        BE[Backend Container\nFastAPI + Uvicorn]
        PG[(PostgreSQL\n+ PostGIS)]
        MG[(MongoDB)]
        MN[MinIO]
        MQ[Mosquitto\nMQTT over TLS]
        subgraph Volumes
            V1[postgres_data]
            V2[mongodb_data]
            V3[minio_data]
            V4[backup_data]
        end
    end

    Internet --> UFW
    UFW -->|443| NX
    UFW -->|8883| MQ
    NX --> FE
    NX --> BE
    BE --> PG
    BE --> MG
    BE --> MN
    BE --> MQ
    PG --- V1
    MG --- V2
    MN --- V3
```

### 18.4 Storage Planning

| Data source | Initial size | 6-month estimate | 12-month estimate |
|------------|-------------|-----------------|------------------|
| PostgreSQL | < 100 MB | ~ 200 MB | ~ 500 MB |
| MongoDB (events) | < 500 MB | ~ 5 GB | ~ 15 GB |
| MinIO (media) | 0 | ~ 10 GB | ~ 30 GB |
| Backups | 0 | ~ 15 GB | ~ 45 GB |
| **Total** | **< 1 GB** | **~ 30 GB** | **~ 91 GB** |

A 80 GB SSD covers 12 months of operation. At the 12-month mark, media files older than 12 months can be migrated to cheaper cold storage (Backblaze B2, Cloudflare R2) and removed from MinIO.

### 18.5 Backup Storage

VPS provider block storage (or an attached additional volume) of 100 GB is mounted at `/backups`. This is separate from the OS disk to ensure backups survive an OS reinstall.

---

## 19. AWS Deployment Option

### 19.1 Architecture Overview

The AWS deployment replaces self-hosted services with managed equivalents. This eliminates operational overhead at the cost of increased monthly spend.

```mermaid
flowchart TD
    subgraph AWS Region
        subgraph VPC
            subgraph Public Subnet
                ALB[Application Load Balancer\nHTTPS 443]
                NLB[Network Load Balancer\nMQTT 8883]
            end
            subgraph Private Subnet
                ECS[ECS Fargate\nBackend Task]
                S3FC[ECS Fargate\nFrontend via CloudFront]
            end
            subgraph Data Subnet
                RDS[(RDS PostgreSQL 16\n+ PostGIS)]
                MGO[(DocumentDB\nor MongoDB Atlas)]
                IOT[AWS IoT Core\nor Amazon MQ]
            end
        end
        S3[S3 Bucket\nMedia Storage]
        CF[CloudFront CDN\nFrontend Assets]
        SM[Secrets Manager\nAll credentials]
        CW[CloudWatch\nLogs + Metrics]
    end

    Internet -->|443| ALB
    Internet -->|8883| NLB
    ALB --> ECS
    NLB --> IOT
    ECS --> RDS
    ECS --> MGO
    ECS --> S3
    ECS --> IOT
    CF --> S3FC
```

### 19.2 AWS Service Mapping

| WildTrack component | AWS managed equivalent |
|--------------------|----------------------|
| PostgreSQL + PostGIS | RDS for PostgreSQL 16 with `postgis` extension |
| MongoDB | Amazon DocumentDB 5.0 (MongoDB compatible) |
| MinIO | S3 Standard storage class |
| Mosquitto | AWS IoT Core (MQTT) or Amazon MQ for RabbitMQ |
| Backend containers | ECS Fargate (serverless containers) |
| Frontend | S3 static website + CloudFront CDN |
| Nginx | Application Load Balancer |
| Secrets | AWS Secrets Manager |
| Logs | CloudWatch Logs |

### 19.3 Migration Path

Migration from VPS to AWS requires:

1. **No code changes** — all connection strings are environment variables
2. **Database migration:** `pg_dump` → restore to RDS; `mongodump` → restore to DocumentDB
3. **Media migration:** `aws s3 sync` from MinIO to S3
4. **DNS update:** Point domain to ALB
5. **Environment variable update:** Replace Docker service hostnames with AWS endpoint URLs

The estimated migration time is less than one day for the MVP data volume.

---

## 20. Cost Analysis MVP

### 20.1 Local Development Cost

| Item | Monthly cost |
|------|-------------|
| Developer laptop (existing) | $0 |
| Docker Desktop (personal use) | $0 |
| All software (open source) | $0 |
| **Total** | **$0/month** |

### 20.2 VPS Deployment Cost

**Hetzner Cloud (Europe, recommended):**

| Resource | Spec | Monthly cost (EUR) |
|----------|------|------------------|
| CX22 VPS | 2 vCPU, 4 GB RAM, 40 GB SSD | €4.51 |
| CX32 VPS (recommended) | 4 vCPU, 8 GB RAM, 80 GB SSD | €8.21 |
| Additional Volume 100 GB | Backup storage | €4.90 |
| Snapshot (monthly) | Full VPS snapshot | ~€0.50 |
| **Total (CX22)** | | **~€10/month** |
| **Total (CX32)** | | **~€14/month** |

**DigitalOcean (alternative):**

| Resource | Spec | Monthly cost (USD) |
|----------|------|------------------|
| Basic Droplet | 2 vCPU, 4 GB RAM, 80 GB SSD | $24/month |
| Volume 100 GB | Backup storage | $10/month |
| **Total** | | **~$34/month** |

**Recommended VPS choice: Hetzner CX32 (~€14/month)** for the MVP. It provides sufficient headroom for the full stack plus backups.

### 20.3 AWS Deployment Cost (Estimate)

AWS costs depend heavily on traffic. The following estimates assume a small-team deployment with moderate IoT event volume (1,000 events/day).

| Service | Configuration | Monthly cost (USD) |
|---------|--------------|------------------|
| RDS PostgreSQL | `db.t4g.micro`, 20 GB storage | ~$15 |
| DocumentDB | `db.t4g.medium`, 1 instance | ~$60 |
| ECS Fargate (backend) | 0.25 vCPU, 0.5 GB, ~720 hrs | ~$10 |
| S3 (media) | 10 GB storage + requests | ~$1 |
| CloudFront | 10 GB transfer | ~$1 |
| ALB | 1 LCU × 720 hrs | ~$18 |
| AWS IoT Core | 1,000 msgs/day × 30 days | ~$1 |
| Secrets Manager | 5 secrets | ~$2 |
| CloudWatch Logs | 5 GB/month | ~$3 |
| **Total** | | **~$111/month** |

> ⚠️ DocumentDB alone represents 54% of the AWS cost. Replacing it with MongoDB Atlas Flex (pay-per-use) or MongoDB Atlas M10 ($~57/month) is comparable. Alternatively, running MongoDB on an EC2 instance reduces cost significantly.

### 20.4 Cost Recommendation

| Phase | Recommendation | Monthly cost |
|-------|---------------|-------------|
| Development | Local Docker Compose | $0 |
| MVP production (1–20 users) | Hetzner CX32 VPS | ~€14 (~$15) |
| Growth (20–200 users) | Hetzner CX52 or DigitalOcean | ~$40–60 |
| Scale (200+ users) | AWS or GCP managed services | ~$100–300+ |

**The VPS option is strongly recommended for the MVP.** The managed AWS services add cost and complexity that is not justified until user volume or reliability requirements increase significantly.

---

## 21. Infrastructure ADRs

### ADR-016 — Container Runtime: Docker vs. Podman

**Question:** Should WildTrack use Docker (requires Docker daemon) or Podman (daemonless, rootless) for local development and production?

**Context:** The CLAUDE.md notes the developer's machine has Podman installed. `compose.yml` syntax is compatible with both `docker compose` and `podman compose`.

**MVP Decision:** Docker Engine for production (better Compose support, wider documentation, simpler CI integration). Podman Compose is supported for local development and noted in the README. Production deployment instructions target Docker.

**Why an ADR:** The two runtimes have subtle behavioral differences in volume permission handling and network naming that affect first-run experience.

---

### ADR-017 — Database Hosting: Self-Hosted vs. Managed

**Question:** Should PostgreSQL and MongoDB run as self-hosted containers or use managed services (RDS, Atlas) even for the MVP?

**Decision:** Self-hosted via Docker Compose for the MVP. Managed services are the production target but add ~$80–100/month to cost with no benefit at small scale.

**Migration trigger:** When uptime SLA requirements exceed what a single-operator can maintain (99.5%+), or when the database instance needs read replicas for performance.

**Why an ADR:** This is a cost and operational complexity decision that must be explicit and revisited at defined growth milestones.

---

### ADR-018 — MQTT Broker: Mosquitto vs. AWS IoT Core vs. HiveMQ

**Question:** Should WildTrack use self-hosted Mosquitto, AWS IoT Core, or HiveMQ Cloud for MQTT?

**Decision:** Self-hosted Mosquitto for the MVP. Mosquitto is well-documented, free, and sufficient for the expected device count (< 100 devices).

**Alternatives and triggers:**

| Alternative | Trigger to switch |
|-------------|------------------|
| AWS IoT Core | Device count > 1,000; need built-in device registry and shadow support |
| HiveMQ Cloud | Need enterprise multi-tenancy, MQTT 5.0 features, or SLA-backed broker |

**Why an ADR:** The MQTT broker choice affects device firmware (connection endpoint, TLS certificate), backend (client library), and infrastructure. Changing it after devices are deployed requires a firmware update campaign.

---

### ADR-019 — Object Storage: MinIO vs. Cloudflare R2 vs. AWS S3

**Question:** For production, should media files use self-hosted MinIO, Cloudflare R2, or AWS S3?

**Decision:** Self-hosted MinIO for the MVP. The MinIO SDK is fully S3-compatible; switching to R2 or S3 later requires only a change to four environment variables.

**Cost comparison (10 GB stored, 50 GB egress/month):**

| Provider | Storage | Egress | Total/month |
|----------|---------|--------|------------|
| MinIO (self-hosted) | Included in VPS disk | Included in VPS bandwidth | $0 additional |
| Cloudflare R2 | $0.015/GB | Free egress | ~$0.15 |
| AWS S3 Standard | $0.023/GB | $0.09/GB | ~$4.73 |

**Recommendation for production scale:** Cloudflare R2. Zero egress fees make it significantly cheaper than S3 when presigned URLs are delivered directly to browsers.

**Why an ADR:** Object storage choice affects presigned URL domain, CORS configuration, and backup strategy.

---

### ADR-020 — Reverse Proxy: Nginx vs. Caddy vs. Traefik

**Question:** Should the reverse proxy be Nginx, Caddy, or Traefik?

**Decision:** Nginx for the MVP. Nginx has the most documentation, predictable behavior, and the team is likely already familiar with it.

**Caddy advantage:** Automatic HTTPS with Let's Encrypt via a single configuration line — no Certbot required. Consider Caddy if the Nginx TLS renewal process proves operationally burdensome.

**Traefik advantage:** Native Docker label-based routing — no static config file. Better suited when the number of services behind the proxy grows beyond 5–6.

**Why an ADR:** The reverse proxy is a critical path for all traffic. Changing it post-deployment requires DNS/cert handling and downtime for reconfiguration.

---

### ADR-026 — MongoDB Time Series Collections: Standard vs. Time Series Collection Type

**Question:** Should the `device_telemetry` and `iot_events` MongoDB collections use the standard collection type or MongoDB's native Time Series collection type (available since MongoDB 5.0)?

**Decision:** Use standard collections for the MVP. Migrate `device_telemetry` to a Time Series collection post-MVP if write volume or storage cost becomes a bottleneck.

**Rationale for standard collections in MVP:**

- Standard collections require no special creation syntax and work with existing Motor code with no changes to insert or query calls.
- `iot_events` write volume in the MVP (a handful of stations, infrequent events) is not high enough to justify the added operational complexity.
- `device_telemetry` is higher frequency (one document per device per 60 seconds), but even at 10 devices this is 14,400 documents per day — well within standard collection performance.
- A TTL index on `device_telemetry.timestamp` (90-day expiry) already controls unbounded growth without Time Series overhead.
- Time Series collections have constraints: documents cannot be updated or deleted individually; only TTL-based expiry is supported. This removes flexibility during early development when schema adjustments are common.

**Rationale for Time Series post-MVP:**

MongoDB Time Series collections store time-sequenced data in compressed internal buckets. For high-frequency IoT telemetry at scale (100+ devices, sub-minute heartbeats), they provide:
- 60–80% storage reduction compared to standard collections
- Faster range queries (time-range scans are bucket-aware)
- Built-in bucketing by `metaField` (e.g., `device_id`) and `timeField` (e.g., `timestamp`)

**Migration path (post-MVP):**
1. Create a new Time Series collection: `db.createCollection("device_telemetry_ts", { timeseries: { timeField: "timestamp", metaField: "device_id", granularity: "minutes" } })`
2. Copy existing data via aggregation pipeline
3. Update `COLLECTION_TELEMETRY` constant in `infrastructure/mongodb.py`
4. No other backend code changes required — Motor insert/query calls are identical

**Consequence:** The Motor collection initialization code in `infrastructure/mongodb.py` must be written so the collection name is a constant (`COLLECTION_TELEMETRY = "device_telemetry"`), making the future rename a one-line change.

**Why an ADR:** The choice of collection type is irreversible for existing data; migration requires a data copy. Documenting this decision ensures the team knows when and why to revisit it.

---

*End of SDD-07 Infrastructure Design — v1.1.0*
