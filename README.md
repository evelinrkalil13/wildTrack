# WildTrack

IoT-based wildlife monitoring platform for intelligent feeding stations.

## Slice 0 — Bootstrap

This slice sets up the infrastructure and a working `/health` endpoint. No business logic yet.

### Prerequisites

- Python 3.12 (use `pyenv` or `mise` to pin it — see `.python-version`)
- [`uv`](https://github.com/astral-sh/uv) (`pip install uv` or `brew install uv`)
- Podman or Docker with Compose support

### Quick start

**1. Copy environment file**

```bash
cp .env.example .env
# Edit .env if you need different passwords or ports.
```

**2. Start infrastructure**

```bash
# Using Podman (recommended on macOS without Docker Desktop):
podman machine start          # if not already running
podman compose -f compose.infra.yml up -d

# Using Docker:
docker compose -f compose.infra.yml up -d
```

Wait for all four containers to be healthy:

```bash
podman compose -f compose.infra.yml ps
# or
docker compose -f compose.infra.yml ps
```

**3. Install Python dependencies**

```bash
cd backend
uv sync
```

**4. Run database migrations**

```bash
cd backend
uv run alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade ...
```

After Slice 1, `alembic current` should report the latest auth migration at head.

**5. Start the API**

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**6. Check health**

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

Expected response (all services up):
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

If any service is down, the status will be `"degraded"` and HTTP 503.

### Run tests

```bash
cd backend
uv sync --extra dev
uv run python -m pytest -v
```

Most tests mock infrastructure. The DB-backed auth integration test is skipped unless
`RUN_DB_INTEGRATION_TESTS=1` is set and PostgreSQL is running.

### Project structure

```
wildTrack/
├── compose.infra.yml          # Infrastructure containers
├── config/
│   └── mosquitto/
│       └── mosquitto.conf     # MQTT broker config
├── .env.example               # Environment variable template
├── backend/
│   ├── pyproject.toml         # Python package + deps
│   ├── alembic.ini
│   ├── app/
│   │   ├── lifespan.py        # FastAPI lifespan (Motor shutdown)
│   │   └── main.py            # App factory
│   ├── infrastructure/
│   │   ├── postgres.py        # SQLAlchemy async engine
│   │   ├── mongodb.py         # Motor client + collection constants
│   │   ├── minio_client.py    # MinIO SDK wrapper
│   │   └── health.py          # /health router
│   ├── migrations/
│   │   ├── env.py             # Alembic async env
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_empty_baseline.py
│   ├── shared/
│   │   └── config.py          # Pydantic Settings singleton
│   └── tests/
│       ├── conftest.py
│       └── test_health.py
└── docs/                      # SDD specification documents
```

### Infrastructure services

| Service    | Port  | Purpose                        |
|------------|-------|-------------------------------|
| PostgreSQL | 5432  | Master data (PostGIS enabled)  |
| MongoDB    | 27017 | IoT events, alerts, telemetry  |
| MinIO      | 9000  | Object storage (media files)   |
| MinIO UI   | 9001  | Web console                    |
| Mosquitto  | 1883  | MQTT broker for IoT devices    |

### Stop infrastructure

```bash
podman compose -f compose.infra.yml down
# Add -v to also delete all data volumes.
```
