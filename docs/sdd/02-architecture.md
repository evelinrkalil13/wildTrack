# WildTrack Platform — Architecture Document

**Document:** SDD-02 Architecture  
**Version:** 1.0.0  
**Date:** 2026-06-13  
**Status:** Draft — Pending Approval  
**References:** SDD-01 Requirements v1.2.0, ADR-001, ADR-002, ADR-003, ADR-004

---

## Table of Contents

1. [System Context Diagram — C4 Level 1](#1-system-context-diagram--c4-level-1)
2. [Container Diagram — C4 Level 2](#2-container-diagram--c4-level-2)
3. [Component Diagram — C4 Level 3 Backend](#3-component-diagram--c4-level-3-backend)
4. [Backend Modular Monolith](#4-backend-modular-monolith)
5. [Frontend Architecture](#5-frontend-architecture)
6. [Database Architecture](#6-database-architecture)
7. [MQTT Architecture](#7-mqtt-architecture)
8. [Media Storage Architecture](#8-media-storage-architecture)
9. [Geoportal Architecture](#9-geoportal-architecture)
10. [Analytics Architecture](#10-analytics-architecture)
11. [Deployment Architecture](#11-deployment-architecture)
12. [Sequence Diagrams](#12-sequence-diagrams)

---

## 1. System Context Diagram — C4 Level 1

This diagram shows the highest-level boundary of the WildTrack system, who interacts with it, and which external systems it depends on.

**People:** Administrators, Researchers, and Field Operators access the system through a web browser. **External systems:** ESP32 feeder devices communicate via MQTT and never touch the REST API. OpenStreetMap provides base map tiles to the frontend; no user data is sent to it.

```mermaid
flowchart TB
    subgraph people["Platform Users"]
        ADM["👤 Administrator"]
        RES["👤 Researcher"]
        OPR["👤 Field Operator"]
    end

    subgraph ext["External Systems"]
        ESP["🔌 ESP32 Feeder Device\nfield hardware"]
        OSM["🗺️ OpenStreetMap\nmap tile server"]
    end

    subgraph boundary["WildTrack Platform — system boundary"]
        SYS["🌿 WildTrack\nWildlife Monitoring Platform"]
    end

    ADM -->|"HTTPS — web browser"| SYS
    RES -->|"HTTPS — web browser"| SYS
    OPR -->|"HTTPS — web browser"| SYS
    ESP -->|"MQTT — events and telemetry"| SYS
    SYS -->|"HTTPS — map tile requests only"| OSM
```

**Boundary rules:**
- All human interaction enters through the web frontend via HTTPS.
- All device communication enters exclusively through MQTT; devices never call the REST API.
- OpenStreetMap receives only anonymous tile requests; no WildTrack user data leaves the boundary.

---

## 2. Container Diagram — C4 Level 2

This diagram decomposes the system boundary into its deployable containers and shows how they communicate.

```mermaid
flowchart TB
    subgraph browser_layer["Client Layer — Browser"]
        FE["⚛️ Web Application\nReact + Vite + TypeScript\nLeaflet · Recharts / Chart.js\nAxios HTTP client"]
    end

    subgraph backend_layer["Backend Layer"]
        API["🐍 FastAPI Application\nModular Monolith — Python 3.12\nREST API server\nMQTT background subscriber\nJWT auth · Pydantic · SQLAlchemy · Motor"]
    end

    subgraph data_layer["Data Layer"]
        PG[("🐘 PostgreSQL + PostGIS\nMaster Data\nUsers · Zones · Stations\nDevices · Animals · Foods")]
        MG[("🍃 MongoDB\nEvent Store\niot_events · device_telemetry\nalerts · media_metadata\ndead_letter_events")]
        MN[("🪣 MinIO\nObject Storage\nPhotos and Videos\nwildtrack-media bucket")]
    end

    subgraph iot_layer["IoT Layer"]
        BRK["📡 Mosquitto\nMQTT Broker — Port 1883"]
        DEV["🔌 ESP32 Devices\nfield hardware"]
    end

    OSM["🗺️ OpenStreetMap CDN"]

    FE -->|"REST / HTTPS — JSON"| API
    FE -->|"HTTPS — tile requests only"| OSM
    API -->|"SQLAlchemy — SQL and PostGIS queries"| PG
    API -->|"Motor async driver — MongoDB wire protocol"| MG
    API -->|"MinIO SDK — S3-compatible API"| MN
    DEV -->|"MQTT publish — QoS 1"| BRK
    BRK -->|"MQTT subscribe — internal network"| API
```

**Protocol summary:**

| From | To | Protocol | Notes |
|------|----|----------|-------|
| Browser | Backend API | HTTPS / REST | JSON; JWT in Authorization header |
| Browser | OpenStreetMap | HTTPS | Tile fetches only; no auth |
| ESP32 | Mosquitto | MQTT 3.1.1 | QoS 1; no TLS in MVP |
| Mosquitto | Backend | MQTT subscribe | Docker internal network |
| Backend | PostgreSQL | TCP / SQL | SQLAlchemy async connection pool |
| Backend | MongoDB | TCP | Motor async driver |
| Backend | MinIO | HTTP / S3 API | MinIO Python SDK |

---

## 3. Component Diagram — C4 Level 3 Backend

This diagram shows the internal structure of the FastAPI application. Each business module is self-contained with its own router, service, repository, schemas, and models. Shared infrastructure is used by all modules through dependency injection.

```mermaid
flowchart TB
    subgraph entry["Entry Point"]
        MAIN["main.py\nFastAPI app factory\nrouter registration\nlifespan startup and shutdown"]
    end

    subgraph infra["Shared Infrastructure"]
        CFG["config\nPydantic BaseSettings\nenv vars"]
        SEC["security\nJWT · bcrypt"]
        DB["database\nSQLAlchemy async engine\nsession factory"]
        MC["mongo_client\nMotor async client\ncollection accessors"]
        MNC["minio_client\nMinIO SDK wrapper\npre-signed URL generator"]
        MQTT["mqtt_subscriber\naiomqtt client\ntopic dispatcher"]
        DEP["dependencies\nDI providers\ncurrent_user · db_session"]
        EXC["exceptions\nglobal HTTP handlers"]
    end

    subgraph mods["Business Modules"]
        AUTH["auth"]
        USERS["users"]
        ZONES["zones"]
        STA["stations"]
        DEV["devices"]
        ANI["animals"]
        FOOD["food"]
        SFOOD["station_foods"]
        USTA["user_stations"]
        IOT["iot_events"]
        TEL["device_telemetry"]
        ALT["alerts"]
        ANA["analytics"]
        GEO["geoportal"]
        MED["media"]
    end

    MAIN --> infra
    MAIN --> mods
    mods --> infra
    AUTH --> USERS
    IOT --> STA
    IOT --> DEV
    IOT --> ANI
    IOT --> ALT
    TEL --> DEV
    TEL --> ALT
    SFOOD --> STA
    SFOOD --> FOOD
    USTA --> USERS
    USTA --> STA
    DEV --> STA
    ANA --> STA
    ANA --> ZONES
    GEO --> STA
    GEO --> ZONES
    MED --> IOT
    MED --> STA
    MED --> DEV
```

---

## 4. Backend Modular Monolith

### 4.1 Module Responsibilities

| Module | Responsibility | Primary Store |
|--------|---------------|---------------|
| `auth` | Public self-registration, login, JWT issuance | PostgreSQL |
| `users` | User CRUD, role changes, deactivation by admin | PostgreSQL |
| `zones` | Zone registration, coordinates, soft delete | PostgreSQL + PostGIS |
| `stations` | Station lifecycle, location, status, ownership | PostgreSQL + PostGIS |
| `devices` | Device registration, station assignment, firmware and last_seen tracking | PostgreSQL |
| `animals` | Global animal registry, RFID management | PostgreSQL |
| `food` | Food type catalog | PostgreSQL |
| `station_foods` | Food-station associations with active flag | PostgreSQL |
| `user_stations` | User-to-station assignment and access enforcement | PostgreSQL |
| `iot_events` | MQTT feeding event ingestion, validation, RFID resolution, storage | MongoDB |
| `device_telemetry` | MQTT heartbeat ingestion, device status updates | MongoDB + PostgreSQL |
| `alerts` | Alert generation, open/resolved lifecycle | MongoDB |
| `analytics` | Aggregated metrics and time-series queries | MongoDB + PostgreSQL |
| `geoportal` | Read-only spatial and event summary data for the map | PostgreSQL + MongoDB |
| `media` | Media file upload to MinIO, metadata storage | MinIO + MongoDB |

### 4.2 Module Boundary Rules

- Each module's **repository** is the only layer that issues database queries or storage calls.
- Each module's **service** contains all business logic and orchestrates cross-repository calls.
- Each module's **router** handles HTTP routing and input validation only; it delegates to the service immediately.
- Cross-module access is only permitted through service-to-service calls. Repositories never import from other modules.
- `iot_events` and `device_telemetry` handlers may call `alerts.service` to generate alerts. `alerts` never imports from either of them.

### 4.3 Module Dependency Graph

```mermaid
flowchart LR
    subgraph core["Core Modules"]
        AUTH["auth"]
        USERS["users"]
        ZONES["zones"]
        STA["stations"]
        DEV["devices"]
        ANI["animals"]
        FOOD["food"]
    end

    subgraph assoc["Association Modules"]
        SFOOD["station_foods"]
        USTA["user_stations"]
    end

    subgraph pipeline["IoT Pipeline Modules"]
        IOT["iot_events"]
        TEL["device_telemetry"]
        ALT["alerts"]
    end

    subgraph read["Read and Aggregation Modules"]
        ANA["analytics"]
        GEO["geoportal"]
        MED["media"]
    end

    AUTH -->|"reads user by email"| USERS
    SFOOD -->|"validates"| STA
    SFOOD -->|"validates"| FOOD
    USTA -->|"validates"| USERS
    USTA -->|"validates"| STA
    DEV -->|"validates station"| STA
    IOT -->|"validates"| STA
    IOT -->|"validates"| DEV
    IOT -->|"resolves RFID"| ANI
    IOT -->|"generates"| ALT
    TEL -->|"updates"| DEV
    TEL -->|"generates"| ALT
    ANA -->|"reads"| STA
    ANA -->|"reads"| ZONES
    GEO -->|"reads"| STA
    GEO -->|"reads"| ZONES
    MED -->|"reads"| STA
    MED -->|"reads"| DEV
```

---

## 5. Frontend Architecture

The frontend is a React SPA built with Vite and TypeScript. It communicates only with the backend REST API. All map rendering uses Leaflet with OpenStreetMap tiles.

### 5.1 Layer Structure

```mermaid
flowchart TB
    subgraph spa["Browser — React SPA"]
        subgraph pages["Pages (route-level components)"]
            P1["AuthPage\nLogin / Register"]
            P2["DashboardPage\nKPI cards + Charts"]
            P3["ZonesPage"]
            P4["StationsPage\nLocation picker"]
            P5["DevicesPage\nAssignment UI"]
            P6["AnimalsPage\nVisit history"]
            P7["FoodPage"]
            P8["EventsPage\nEvent log + filters"]
            P9["AlertsPage\nOpen / Resolved"]
            P10["GeoportalPage\nLeaflet map + layers"]
            P11["MediaPage\nGallery + preview"]
            P12["UsersPage\nadmin only"]
        end

        subgraph components["Shared Components"]
            C1["MapPicker\nLeaflet location selector\nfor station form"]
            C2["ChartWrapper\nRecharts / Chart.js"]
            C3["DataTable\nsort + filter + paginate"]
            C4["AlertBadge\nopen alert count"]
            C5["StatusChip\nstation / device status color"]
            C6["StationPopup\ngeoportal marker popup"]
        end

        subgraph state["State"]
            S1["authStore\nJWT · user · role"]
            S2["uiStore\nloading · toasts"]
        end

        subgraph services["API Service Layer"]
            SV["authService\nzonesService\nstationsService\ndevicesService\nanimalsService\niotEventsService\ntelemetryService\nalertsService\nanalyticsService\ngeoportalService\nmediaService"]
        end

        subgraph http["HTTP Layer"]
            AX["axios instance\nbaseURL + JWT interceptor\n401 redirect to login"]
        end
    end

    BACKEND["🐍 Backend API"]
    pages --> components
    pages --> state
    pages --> services
    components --> services
    services --> AX
    AX -->|"HTTPS REST"| BACKEND
```

### 5.2 Route Structure

```mermaid
flowchart TB
    ROOT["/"]
    ROOT --> LOGIN["/login"]
    ROOT --> REGISTER["/register"]
    ROOT --> APP["/app  protected by JWT"]
    APP --> DASH["/app/dashboard"]
    APP --> ZONES["/app/zones"]
    APP --> STA["/app/stations"]
    STA --> STA_D["/app/stations/:id"]
    APP --> DEV["/app/devices"]
    APP --> ANI["/app/animals"]
    APP --> FOOD["/app/food"]
    APP --> EVT["/app/events"]
    APP --> ALTS["/app/alerts"]
    APP --> GEO["/app/geoportal"]
    APP --> MEDIA["/app/media"]
    APP --> USRS["/app/users  admin only"]
```

### 5.3 Location Capture Flow

```mermaid
flowchart TB
    FORM["Station Form"]
    FORM --> CHOICE{"Choose location\nmethod"}
    CHOICE -->|"Auto-detect"| GEOAPI["navigator.geolocation\n.getCurrentPosition()"]
    CHOICE -->|"Manual"| MAPPICK["Leaflet MapPicker\nUser clicks map"]
    GEOAPI -->|"lat + lng"| FIELDS["Form fields auto-populated"]
    MAPPICK -->|"lat + lng"| FIELDS
    FIELDS --> SUBMIT["POST /stations\nwith lat + lng in body"]
```

---

## 6. Database Architecture

### 6.1 PostgreSQL — Entity Relationship Diagram

```mermaid
erDiagram
    users {
        uuid id PK
        string name
        string document
        string email UK
        string password_hash
        enum role
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    zones {
        uuid id PK
        string name
        string municipality
        string city
        string country
        float altitude
        float latitude
        float longitude
        geometry geom
        timestamp created_at
        timestamp updated_at
    }

    stations {
        uuid id PK
        string code UK
        string name
        uuid zone_id FK
        float latitude
        float longitude
        geometry geom
        enum status
        timestamp created_at
        timestamp updated_at
    }

    devices {
        uuid id PK
        string serial_number UK
        string name
        uuid station_id FK
        enum status
        string firmware_version
        timestamp last_seen
        timestamp created_at
        timestamp updated_at
    }

    animals {
        uuid id PK
        string rfid_tag UK
        string species
        enum sex
        string estimated_age
        boolean is_identified
        string notes
        timestamp created_at
        timestamp updated_at
    }

    foods {
        uuid id PK
        string name
        string type
        string description
        timestamp created_at
        timestamp updated_at
    }

    station_foods {
        uuid id PK
        uuid station_id FK
        uuid food_id FK
        boolean active
        timestamp created_at
        timestamp updated_at
    }

    user_stations {
        uuid id PK
        uuid user_id FK
        uuid station_id FK
        enum role
        timestamp created_at
        timestamp updated_at
    }

    zones ||--o{ stations : "contains"
    stations ||--o| devices : "has device"
    stations ||--o{ station_foods : "configured with"
    stations ||--o{ user_stations : "has members"
    users ||--o{ user_stations : "assigned to"
    foods ||--o{ station_foods : "used in"
```

### 6.2 PostgreSQL — Enumeration Types

| Table | Column | Values |
|-------|--------|--------|
| `users` | `role` | `admin`, `researcher`, `field_operator` |
| `stations` | `status` | `active`, `inactive`, `maintenance`, `offline` |
| `devices` | `status` | `online`, `offline`, `unassigned` |
| `animals` | `sex` | `male`, `female`, `unknown` |
| `user_stations` | `role` | `owner`, `researcher`, `field_operator` |

### 6.3 MongoDB — Collections Overview

```mermaid
flowchart TB
    subgraph mongo["MongoDB — wildtrack_db"]
        IOT[("iot_events\n──────────────\nevent_id · event_type\nstation_id · device_id\nanimal_id · rfid_tag\ntimestamp · temperature\nhumidity · consumed_grams\ninitial_weight · final_weight\nlatitude · longitude\nmedia_url · device_status\nraw_payload")]

        TEL[("device_telemetry\n──────────────\ntelemetry_id · device_id\nstation_id · timestamp\nfirmware_version\nwifi_signal · uptime\nfree_memory · battery_level\ndevice_status · raw_payload")]

        ALT[("alerts\n──────────────\nalert_id · station_id\ndevice_id · alert_type\nmessage · status\ncreated_at · resolved_at")]

        MED[("media_metadata\n──────────────\nmedia_id · event_id\nstation_id · device_id\nmedia_type · object_key\nurl · file_size_bytes\ncaptured_at")]

        DL[("dead_letter_events\n──────────────\nreceived_at · topic\nraw_payload\nfailure_reason")]
    end
```

### 6.4 MongoDB — Index Strategy

| Collection | Indexes |
|------------|---------|
| `iot_events` | `{station_id, timestamp}`, `{device_id, timestamp}`, `{animal_id}`, `{rfid_tag}`, `{event_type}` |
| `device_telemetry` | `{device_id, timestamp}`, `{station_id, timestamp}` |
| `alerts` | `{station_id, status}`, `{device_id, status}`, `{alert_type, status}` |
| `media_metadata` | `{event_id}`, `{station_id}` |
| `dead_letter_events` | `{received_at}` |

### 6.5 MinIO — Bucket Structure

```mermaid
flowchart TB
    subgraph minio["MinIO — wildtrack-media  private bucket"]
        ROOT["wildtrack-media/"]
        ROOT --> STA["{station_id}/"]
        STA --> YR["{year}/"]
        YR --> MO["{month}/"]
        MO --> OBJ["{device_id}_{timestamp_iso}_{filename}\ne.g. dev-uuid_2026-06-13T10-30-00_photo.jpg"]
    end

    NOTE["Access rules\n──────────────\nBucket: private\nWrite: backend SDK only\nRead: backend proxy or\npre-signed URL with 15 min TTL"]
```

---

## 7. MQTT Architecture

### 7.1 Topic Namespace

| Topic pattern | Publisher | Subscriber | Message type |
|---------------|-----------|------------|-------------|
| `wildtrack/events/{station_id}` | ESP32 | Backend | Feeding event JSON |
| `wildtrack/telemetry/{device_id}` | ESP32 | Backend | Heartbeat JSON |

### 7.2 Message Flow

```mermaid
flowchart TB
    subgraph field["Field — ESP32"]
        SENS["Sensors\nRFID · load cell · temp · humidity · camera"]
        FW["Firmware\nevent builder"]
        PUB_E["MQTT Publish\nwildtrack/events/{station_id}"]
        PUB_T["MQTT Publish\nwildtrack/telemetry/{device_id}"]
        SENS --> FW
        FW --> PUB_E
        FW --> PUB_T
    end

    subgraph broker["Mosquitto — Port 1883"]
        BRK["Topic router\nQoS 1 — at-least-once delivery"]
    end

    subgraph subscriber["Backend — MQTT Subscriber"]
        SUB["mqtt_subscriber\naiomqtt client\nstarts on app lifespan"]
        DISP["Dispatcher\ntopic pattern matching"]
        H_EVT["iot_events.handler"]
        H_TEL["device_telemetry.handler"]
        H_DL["dead_letter handler"]
    end

    PUB_E -->|"QoS 1"| BRK
    PUB_T -->|"QoS 1"| BRK
    BRK --> SUB
    SUB --> DISP
    DISP -->|"events topic"| H_EVT
    DISP -->|"telemetry topic"| H_TEL
    DISP -->|"parse failure"| H_DL
```

### 7.3 Dead-Letter Routing

```mermaid
flowchart TB
    MSG["Incoming MQTT message"]
    MSG --> P1{"JSON parseable?"}
    P1 -->|"No"| DL1["dead_letter_events\nfailure_reason: parse_error"]
    P1 -->|"Yes"| P2{"Pydantic schema\nvalid?"}
    P2 -->|"No"| DL2["dead_letter_events\nfailure_reason: schema_error"]
    P2 -->|"Yes"| P3{"station_id and\ndevice_id exist?"}
    P3 -->|"No"| DL3["dead_letter_events\nfailure_reason: unknown_ids"]
    P3 -->|"Yes"| PROC["Normal processing"]
```

### 7.4 Payload Schemas

```mermaid
flowchart LR
    subgraph ep["Feeding Event Payload"]
        E["event_id: UUID\nevent_type: string\nstation_id: UUID\ndevice_id: UUID\nrfid_tag: string or null\ntimestamp: ISO-8601\ntemperature: float\nhumidity: float\ninitial_weight: float\nfinal_weight: float\nconsumed_grams: float\nlatitude: float\nlongitude: float\nmedia_url: string or null\ndevice_status: string\nraw_payload: object"]
    end

    subgraph tp["Telemetry Heartbeat Payload"]
        T["device_id: UUID\ntimestamp: ISO-8601\nfirmware_version: string\nwifi_signal: int dBm\nuptime: int seconds\nfree_memory: int bytes\nbattery_level: int or null\ndevice_status: string"]
    end
```

---

## 8. Media Storage Architecture

### 8.1 Upload Flow — Backend Proxy

```mermaid
flowchart TB
    subgraph upload["Upload — backend proxy path"]
        CLIENT["Client\nESP32 or browser"]
        CLIENT -->|"POST /media/upload\nmultipart form-data\nfile + event_id + station_id + device_id"| API["Backend API\nmedia router"]
        API -->|"Validate JWT\nValidate event_id exists"| VAL["Validation"]
        VAL -->|"Stream bytes\nobject key: station/year/month/device_ts_name"| MN["MinIO\nwildtrack-media"]
        MN -->|"object_key + internal URL"| API
        API -->|"INSERT media_metadata"| MG["MongoDB\nmedia_metadata"]
        MG --> API
        API -->|"201 Created\nmedia_id + url"| CLIENT
    end
```

### 8.2 Retrieval Flow — Pre-Signed URL

```mermaid
flowchart TB
    subgraph retrieve["Retrieval — pre-signed URL path"]
        BR["Browser"]
        BR -->|"GET /media/presigned/{event_id}"| API["Backend API"]
        API -->|"SELECT media_metadata\nWHERE event_id"| MG["MongoDB"]
        MG -->|"object_key"| API
        API -->|"GeneratePresignedURL\nobject_key  TTL 15 min"| MN["MinIO SDK"]
        MN -->|"presigned_url"| API
        API -->|"200 OK\npresigned_url + expires_in"| BR
        BR -->|"GET presigned_url\ndirect HTTP to MinIO"| MN2["MinIO\ndirect"]
        MN2 -->|"binary file stream"| BR
    end
```

### 8.3 Access Control Model

```mermaid
flowchart LR
    subgraph ac["Access Control"]
        BUCKET["wildtrack-media\nprivate"]
        BACKEND["Backend API\nfull access via SDK\nroot credentials from env vars"]
        BROWSER["Browser\nno direct credentials"]
        ESP["ESP32\nno direct credentials"]
    end

    BACKEND -->|"read + write"| BUCKET
    BACKEND -->|"issues 15-min pre-signed URL"| BROWSER
    BROWSER -->|"time-limited URL only"| BUCKET
    ESP -->|"upload via backend proxy"| BACKEND
```

---

## 9. Geoportal Architecture

### 9.1 Component Structure

```mermaid
flowchart TB
    subgraph geo_page["GeoportalPage — React"]
        subgraph leaflet["Leaflet MapContainer"]
            BASE["TileLayer\nOpenStreetMap tiles"]
            MARKERS["StationMarkerLayer\nCircleMarker per station\ngreen active  red offline\nyellow maintenance  gray inactive"]
            H_ACT["HeatmapLayer\nActivity — event count weight"]
            H_CON["HeatmapLayer\nConsumption — grams weight"]
            ENV_OV["EnvOverlay\ntemp + humidity tooltips"]
            POPUP["StationPopup\nname · zone · status\ndevice last_seen · last event · visits"]
        end

        subgraph ctrl["Controls"]
            LC["LayersControl\ntoggle heatmap layers\ntoggle env overlay"]
            ZF["ZoneFilter\ndropdown"]
        end

        subgraph sidebar["Sidebar"]
            EL["RecentEventList\ngrouped by zone"]
        end
    end

    subgraph api_calls["Backend Calls — geoportalService"]
        A1["GET /geoportal/stations\nGeoJSON FeatureCollection"]
        A2["GET /geoportal/heatmap/activity\nlat lng weight array"]
        A3["GET /geoportal/heatmap/consumption\nlat lng weight array"]
        A4["GET /geoportal/env-readings\nlat lng temp humidity array"]
        A5["GET /geoportal/events-by-zone\nzone grouped event list"]
    end

    MARKERS --> A1
    H_ACT --> A2
    H_CON --> A3
    ENV_OV --> A4
    EL --> A5
    ZF -->|"zone_id filter"| A1
    ZF -->|"zone_id filter"| A5
```

### 9.2 Geoportal Data Assembly

```mermaid
flowchart LR
    subgraph src["Sources"]
        PG["PostgreSQL\nstations + zones\nlocation + status"]
        MG["MongoDB\niot_events\naggregated"]
    end

    subgraph svc["geoportal.service"]
        MERGE["Merge station location\nwith latest event summary"]
        HEAT_A["Aggregate events\nby lat-lng bucket\ncount weight"]
        HEAT_C["Aggregate events\nby lat-lng bucket\ngrams weight"]
        ENV["Aggregate sensor\nreadings by station"]
        ZONE_GRP["Group recent events\nby zone"]
    end

    subgraph out["API Responses"]
        R1["GeoJSON FeatureCollection\nstation markers"]
        R2["Activity heatmap points"]
        R3["Consumption heatmap points"]
        R4["Env reading points"]
        R5["Zone event groups"]
    end

    PG --> MERGE
    MG --> MERGE
    MG --> HEAT_A
    MG --> HEAT_C
    MG --> ENV
    MG --> ZONE_GRP
    MERGE --> R1
    HEAT_A --> R2
    HEAT_C --> R3
    ENV --> R4
    ZONE_GRP --> R5
```

---

## 10. Analytics Architecture

### 10.1 Data Aggregation Pipeline

```mermaid
flowchart TB
    subgraph raw["Raw Sources"]
        PG_S["PostgreSQL\nstations · zones\nanimals · devices"]
        MG_E["MongoDB\niot_events"]
        MG_T["MongoDB\ndevice_telemetry"]
        MG_A["MongoDB\nalerts"]
    end

    subgraph svc["analytics.service — Aggregators"]
        KPI["KPI Aggregator\nstation counts · event totals\nanimal counts · open alerts\ndevice online/offline counts"]
        TS["Time-Series Builder\ngroup by day/week/month\nconsumption + visit counts"]
        ZA["Zone Aggregator\ntotal grams per zone"]
        SA["Station Aggregator\nevent count per station"]
        EA["Env Aggregator\navg temp + humidity per station"]
    end

    subgraph api["Analytics REST Endpoints"]
        R_KPI["GET /analytics/kpi"]
        R_CONS["GET /analytics/consumption\n?from=&to=&granularity="]
        R_VISITS["GET /analytics/visits\n?from=&to=&granularity="]
        R_ZONE["GET /analytics/consumption-by-zone"]
        R_STA["GET /analytics/events-by-station"]
        R_ENV["GET /analytics/env"]
    end

    subgraph dash["Dashboard — React"]
        D1["KPI Cards\nTotal · Active · Offline · Events\nAnimals · Unidentified · Alerts"]
        D2["Consumption Chart\nRecharts LineChart"]
        D3["Visits Chart\nRecharts BarChart"]
        D4["By-Zone Chart"]
        D5["By-Station Chart"]
        D6["Env Comparison Chart"]
    end

    PG_S --> KPI
    MG_E --> KPI
    MG_A --> KPI
    MG_E --> TS
    MG_E --> ZA
    MG_E --> SA
    MG_E --> EA
    MG_T --> EA

    KPI --> R_KPI
    TS --> R_CONS
    TS --> R_VISITS
    ZA --> R_ZONE
    SA --> R_STA
    EA --> R_ENV

    R_KPI --> D1
    R_CONS --> D2
    R_VISITS --> D3
    R_ZONE --> D4
    R_STA --> D5
    R_ENV --> D6
```

### 10.2 Caching Note

The MVP uses no explicit cache layer. Dashboard polling every 60 seconds is the refresh strategy. MongoDB aggregation pipelines are indexed on `station_id` + `timestamp`. Post-MVP, a Redis cache layer can be inserted between the service and the router without changing the API contract.

---

## 11. Deployment Architecture

### 11.1 Docker Compose Services

```mermaid
flowchart TB
    subgraph compose["docker compose — wildtrack network"]
        subgraph data_svcs["Data Services"]
            PG_C["postgres\npostgis/postgis:16-3.4\nPort 5432\nVolume: pg_data"]
            MG_C["mongodb\nmongo:7\nPort 27017\nVolume: mongo_data"]
            MN_C["minio\nminio/minio:latest\nPort 9000 API\nPort 9001 console\nVolume: minio_data"]
        end

        subgraph msg_svcs["Messaging"]
            MQTT_C["mosquitto\neclipse-mosquitto:2\nPort 1883\nVolume: mosquitto_config"]
        end

        subgraph app_svcs["Application Services"]
            BE_C["backend\nBuild: ./backend\nPort 8000\nDepends: postgres · mongodb\nminio · mosquitto"]
            FE_C["frontend\nBuild: ./frontend\nPort 5173 dev / 80 prod\nDepends: backend"]
        end
    end

    subgraph host["Developer Host"]
        BR_H["Browser\nlocalhost:5173"]
        MQTT_H["MQTT test client\nlocalhost:1883"]
        MN_H["MinIO console\nlocalhost:9001"]
    end

    BR_H -->|"HTTP"| FE_C
    BR_H -->|"HTTP direct"| BE_C
    MQTT_H -->|"MQTT"| MQTT_C
    MN_H -->|"HTTP"| MN_C
    FE_C -->|"internal"| BE_C
    BE_C -->|"internal"| PG_C
    BE_C -->|"internal"| MG_C
    BE_C -->|"internal"| MN_C
    BE_C -->|"internal"| MQTT_C
```

### 11.2 Environment Variables

| Service | Variable | Purpose |
|---------|----------|---------|
| backend | `DATABASE_URL` | PostgreSQL connection string |
| backend | `MONGODB_URI` | MongoDB connection string |
| backend | `MINIO_ENDPOINT` | MinIO host:port |
| backend | `MINIO_ACCESS_KEY` | MinIO root user |
| backend | `MINIO_SECRET_KEY` | MinIO root password |
| backend | `MQTT_HOST` | Mosquitto hostname |
| backend | `MQTT_PORT` | Mosquitto port (default 1883) |
| backend | `JWT_SECRET` | HMAC signing secret |
| backend | `JWT_EXPIRY_HOURS` | Token lifetime (default 24) |
| backend | `ADMIN_SEED_EMAIL` | First admin email for bootstrap |
| backend | `ADMIN_SEED_PASSWORD` | First admin password for bootstrap |
| backend | `DEVICE_OFFLINE_THRESHOLD_MINUTES` | Heartbeat absence before device goes offline |
| postgres | `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | DB credentials |
| mongodb | `MONGO_INITDB_ROOT_USERNAME` / `MONGO_INITDB_ROOT_PASSWORD` | DB credentials |
| minio | `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | Object store credentials |

---

## 12. Sequence Diagrams

### 12.1 User Self-Registration

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Frontend
    participant API as Backend API
    participant PG as PostgreSQL

    U->>FE: Fill registration form (name, document, email, password)
    FE->>API: POST /auth/register
    API->>API: Validate Pydantic schema
    API->>PG: SELECT users WHERE email = ?
    PG-->>API: Result

    alt Email already exists
        API-->>FE: 409 Conflict
        FE-->>U: Show error
    else Email available
        API->>API: bcrypt hash password
        API->>PG: INSERT users (role = researcher)
        PG-->>API: user_id
        API-->>FE: 201 Created — user_id + email + role
        FE-->>U: Success — redirect to login
    end
```

### 12.2 Station Creation with Location Capture

```mermaid
sequenceDiagram
    actor U as Researcher
    participant FE as Frontend
    participant GEO as Browser Geolocation
    participant MAP as Leaflet MapPicker
    participant API as Backend API
    participant PG as PostgreSQL

    U->>FE: Open station creation form

    alt Browser geolocation
        U->>FE: Click Detect my location
        FE->>GEO: navigator.geolocation.getCurrentPosition()
        GEO-->>FE: latitude + longitude
        FE-->>U: Auto-populate lat/lng fields
    else Manual map selection
        U->>FE: Click Select on map
        FE-->>U: Show embedded Leaflet map
        U->>MAP: Click point on map
        MAP-->>FE: latitude + longitude
        FE-->>U: Auto-populate lat/lng fields and show pin
    end

    U->>FE: Fill code, name, zone_id and submit
    FE->>API: POST /stations (code, name, zone_id, latitude, longitude)
    API->>API: Validate JWT — role researcher or admin
    API->>PG: SELECT zones WHERE id = zone_id
    PG-->>API: Zone found
    API->>PG: INSERT stations (with geom = ST_Point)
    PG-->>API: station_id
    API->>PG: INSERT user_stations (user_id, station_id, role = owner)
    PG-->>API: OK
    API-->>FE: 201 Created — station_id + status
    FE-->>U: Station appears in list and on map
```

### 12.3 Device Registration and Assignment

```mermaid
sequenceDiagram
    actor A as Admin
    participant FE as Frontend
    participant API as Backend API
    participant PG as PostgreSQL

    A->>FE: Open device form — enter serial_number and name
    FE->>API: POST /devices (serial_number, name)
    API->>API: Validate JWT — role admin
    API->>PG: SELECT devices WHERE serial_number = ?
    PG-->>API: Empty — serial available
    API->>PG: INSERT devices (status = unassigned)
    PG-->>API: device_id
    API-->>FE: 201 Created — device_id + status unassigned
    FE-->>A: Device visible in device list

    A->>FE: Select device — choose station to assign
    FE->>API: PATCH /devices/{device_id}/assign (station_id)
    API->>API: Validate JWT — role admin
    API->>PG: SELECT stations WHERE id = station_id
    PG-->>API: Station exists
    API->>PG: SELECT devices WHERE station_id = ? AND status != unassigned
    PG-->>API: Empty — station has no active device
    API->>PG: UPDATE devices SET station_id = ?, status = online
    PG-->>API: OK
    API-->>FE: 200 OK — device_id + station_id + status online
    FE-->>A: Device shows as assigned and online
```

### 12.4 Feeding Event Ingestion

```mermaid
sequenceDiagram
    participant ESP as ESP32 Device
    participant BRK as Mosquitto
    participant SUB as MQTT Subscriber
    participant HDL as iot_events.handler
    participant PG as PostgreSQL
    participant MG as MongoDB
    participant ALT as alerts.service

    ESP->>BRK: PUBLISH wildtrack/events/{station_id} — event JSON
    BRK->>SUB: Deliver message QoS 1
    SUB->>HDL: Dispatch event topic

    HDL->>HDL: Parse JSON and validate Pydantic schema

    alt Parse or schema failure
        HDL->>MG: INSERT dead_letter_events (raw_payload, failure_reason)
    else Valid
        HDL->>PG: SELECT stations WHERE id = station_id
        PG-->>HDL: Station record

        alt Station not found
            HDL->>MG: INSERT dead_letter_events (failure_reason: unknown_station)
        else Station found
            HDL->>PG: SELECT devices WHERE id = device_id
            PG-->>HDL: Device record
            HDL->>PG: UPDATE devices SET last_seen = NOW(), status = online
            PG-->>HDL: OK

            alt rfid_tag present
                HDL->>PG: SELECT animals WHERE rfid_tag = ?
                PG-->>HDL: animal_id or null
                HDL->>HDL: Enrich event with animal_id
            end

            HDL->>MG: INSERT iot_events (enriched document)
            MG-->>HDL: inserted_id

            alt Event contains anomaly flags
                HDL->>ALT: generate_alert(station_id, device_id, alert_type)
                ALT->>MG: INSERT alerts (status = open)
                MG-->>ALT: alert_id
            end
        end
    end
```

### 12.5 Telemetry Heartbeat

```mermaid
sequenceDiagram
    participant ESP as ESP32 Device
    participant BRK as Mosquitto
    participant SUB as MQTT Subscriber
    participant HDL as device_telemetry.handler
    participant PG as PostgreSQL
    participant MG as MongoDB
    participant ALT as alerts.service

    loop Every 60 seconds
        ESP->>BRK: PUBLISH wildtrack/telemetry/{device_id} — heartbeat JSON
        BRK->>SUB: Deliver message
        SUB->>HDL: Dispatch telemetry topic
        HDL->>HDL: Parse JSON and validate schema
        HDL->>PG: SELECT devices WHERE id = device_id
        PG-->>HDL: Device (previous_status, station_id)
        HDL->>MG: INSERT device_telemetry (heartbeat document)
        MG-->>HDL: inserted_id
        HDL->>PG: UPDATE devices SET firmware_version = ?, last_seen = NOW(), status = online
        PG-->>HDL: OK

        alt Device was previously offline
            HDL->>PG: UPDATE stations SET status = active WHERE id = station_id
            PG-->>HDL: OK
            HDL->>ALT: resolve_alert(station_id, alert_type = device_offline)
            ALT->>MG: UPDATE alerts SET status = resolved, resolved_at = NOW()
            MG-->>ALT: OK
        end
    end
```

### 12.6 Media Upload

```mermaid
sequenceDiagram
    participant ESP as ESP32 Device
    participant API as Backend API
    participant MG as MongoDB
    participant MN as MinIO

    ESP->>API: POST /media/upload — multipart form-data (file, event_id, station_id, device_id, media_type)
    API->>API: Validate fields
    API->>MG: SELECT iot_events WHERE event_id = ?
    MG-->>API: Event exists
    API->>API: Build object_key: station_id/year/month/device_ts_filename
    API->>MN: PUT object (bucket wildtrack-media, key, file bytes)
    MN-->>API: ETag + internal URL
    API->>MG: INSERT media_metadata (event_id, station_id, device_id, object_key, url, file_size_bytes, captured_at)
    MG-->>API: media_id
    API-->>ESP: 201 Created — media_id + url

    Note over API,MN: Retrieval flow

    actor U as User
    U->>API: GET /media/presigned/{event_id}
    API->>MG: SELECT media_metadata WHERE event_id = ?
    MG-->>API: object_key
    API->>MN: GeneratePresignedURL (object_key, TTL 15 min)
    MN-->>API: presigned_url
    API-->>U: 200 OK — presigned_url + expires_in 900
    U->>MN: GET presigned_url — direct to MinIO
    MN-->>U: Binary file stream
```

### 12.7 Geoportal Query

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Frontend GeoportalPage
    participant OSM as OpenStreetMap
    participant API as Backend API
    participant PG as PostgreSQL
    participant MG as MongoDB

    U->>FE: Navigate to /app/geoportal
    FE->>OSM: GET tile tiles (Leaflet auto-fetch)
    OSM-->>FE: Map tile images

    FE->>API: GET /geoportal/stations
    API->>PG: SELECT stations JOIN zones (id, name, lat, lng, status, zone_name)
    PG-->>API: Station rows
    API->>MG: Aggregate iot_events — latest event per station
    MG-->>API: Per-station event summary
    API->>API: Build GeoJSON FeatureCollection
    API-->>FE: GeoJSON features
    FE->>FE: Render CircleMarker per station colored by status
    FE-->>U: Map with station markers

    U->>FE: Click station marker
    FE-->>U: StationPopup with name, zone, status, device last_seen, last event

    U->>FE: Toggle Activity Heatmap
    FE->>API: GET /geoportal/heatmap/activity
    API->>MG: Aggregate iot_events GROUP BY lat-lng bucket
    MG-->>API: Array of lat, lng, weight
    API-->>FE: Heatmap data points
    FE->>FE: Render leaflet-heat layer
    FE-->>U: Activity heatmap visible on map

    U->>FE: Select zone in filter
    FE->>API: GET /geoportal/events-by-zone?zone_id={id}
    API->>MG: Aggregate recent events joined with zone data
    MG-->>API: Zone grouped event list
    API-->>FE: Events by zone
    FE-->>U: Sidebar panel updated
```

---

*End of SDD-02 Architecture Document — v1.0.0*
