# WildTrack Platform — Software Requirements Specification

**Document:** SDD-01 Requirements  
**Version:** 1.2.0  
**Date:** 2026-06-13  
**Status:** Draft — Pending Approval  
**Changelog:**  
- v1.1.0 — Station/Device separation; Animal multi-station redesign; Device module added; device telemetry collection added; MinIO object storage strategy; OFFLINE station status; firmware_version and last_seen on devices; station location registration flows; ADR-004 reference added; acceptance criteria updated.  
- v1.2.0 — Self-registration rules clarified: default role, field requirements, researcher station ownership, admin bootstrap process, station access isolation.
- v1.3.0 — MVP alignment pass: multimedia marked optional/post-MVP; camera implementation and firmware development added to out-of-scope; OTA firmware management clarified as manual USB for MVP; pragmatic local-first deployment note added; MongoDB Atlas free tier option added; out-of-scope section expanded with clear scope boundaries.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [System Goals](#3-system-goals)
4. [MVP Scope](#4-mvp-scope)
5. [Out of Scope](#5-out-of-scope)
6. [Actors and Roles](#6-actors-and-roles)
7. [Functional Requirements by Module](#7-functional-requirements-by-module)
8. [Non-Functional Requirements](#8-non-functional-requirements)
9. [Main User Flows](#9-main-user-flows)
10. [Main IoT Device Flows](#10-main-iot-device-flows)
11. [Data Requirements](#11-data-requirements)
12. [Geoportal Requirements](#12-geoportal-requirements)
13. [Dashboard Requirements](#13-dashboard-requirements)
14. [Alert Requirements](#14-alert-requirements)
15. [MVP Acceptance Criteria](#15-mvp-acceptance-criteria)

---

## 1. Project Overview

WildTrack is an IoT-based wildlife monitoring platform designed to manage and monitor intelligent feeding stations deployed in field environments. The platform connects physical feeding devices (built on ESP32 microcontrollers) with a web-based administration system, a geospatial visualization portal, and an analytics dashboard.

The system distinguishes between two closely related but independent concepts: a **Station** (the logical, administrative entity representing a feeding location) and a **Device** (the physical ESP32 hardware deployed at that location). A device is registered independently and associated with a station; this separation allows hardware to be replaced or reassigned without losing the station's historical data and configuration.

Animals are modeled as global records not tied to a single station. Their associations with stations are derived from visit events, allowing the same animal to be tracked across multiple stations over time.

The backend is a modular FastAPI monolith backed by PostgreSQL/PostGIS for structured master data and MongoDB for IoT event and telemetry storage. Multimedia files captured by devices are stored in a MinIO-compatible S3 object storage service; only URLs and metadata are persisted in MongoDB. The frontend is a React + TypeScript single-page application with Leaflet-based geospatial views. Device communication is handled exclusively through an MQTT broker.

---

## 2. Problem Statement

Wildlife researchers and conservationists operating in remote or semi-remote environments need reliable, structured, and centralized tooling to monitor the feeding behavior of wild animals. Manual observation is expensive, error-prone, and difficult to scale. Existing generic IoT platforms do not support the specific domain needs of wildlife monitoring: RFID-based animal identification, geographic zone management, food consumption measurement, and correlated environmental sensing.

Key problems this system addresses:

- There is no centralized platform to register and monitor multiple feeding stations across different geographic zones.
- Animal visits and consumption events are not reliably captured or associated with identified individuals.
- The same animal may visit multiple stations, but existing approaches force a single-station assignment, losing cross-station behavioral data.
- Field operators have no real-time or near-real-time visibility into station health, device connectivity, firmware state, or environmental conditions.
- There is no structured alert system to notify operators about station failures, device connectivity loss, abnormal behavior, or critical conditions.
- Data gathered by sensors in the field is not currently aggregated in a way that supports ecological analysis or reporting.
- Media files from field devices have no structured storage or retrieval strategy.

---

## 3. System Goals

### Primary Goals

- Provide a centralized web platform to register, manage, and monitor intelligent feeding stations and their associated hardware devices.
- Ingest, validate, and store IoT events and device telemetry from ESP32-based feeding devices via MQTT.
- Associate RFID-tagged feeding events with registered animal records, supporting cross-station animal tracking.
- Enable geographic visualization of station locations, activity, and consumption patterns.
- Provide an analytics dashboard with meaningful metrics for researchers and administrators.
- Generate operational alerts when devices report anomalies, lose connectivity, or fail.
- Store multimedia files in a MinIO-compatible object store and expose them through the API.

### Secondary Goals

- Support multiple users per organization with role-based access to stations.
- Maintain a clean separation between IoT event/telemetry data (MongoDB) and structured master data (PostgreSQL).
- Expose a well-defined REST API that can serve both the frontend and future integrations.
- Make the system deployable locally via Docker Compose for development and field use.
- Track device health independently of station administrative status.

### Design Goals

- Follow Spec-Driven Development: specification and architecture are completed before implementation.
- Apply clean architecture principles within a modular monolith. Avoid overengineering.
- Keep the MVP realistic, buildable, and maintainable by a small team.

---

## 4. MVP Scope

The first deliverable of WildTrack must include the following capabilities:

| # | Feature |
|---|---------|
| 1 | User registration and login with JWT authentication |
| 2 | Role-based access control (admin, researcher, field_operator) |
| 3 | Zone registration with geographic coordinates |
| 4 | Station registration with location capture via browser geolocation or manual map selection |
| 5 | Station status management: active, inactive, maintenance, offline |
| 6 | Device registration and association to stations |
| 7 | Device firmware version tracking and last-seen timestamp |
| 8 | User-station association with role assignment |
| 9 | Animal registration as global records (no fixed station) |
| 10 | Animal-station visit tracking derived from IoT events |
| 11 | Food type registration |
| 12 | Food-to-station association with active/inactive state |
| 13 | MQTT event ingestion from ESP32 devices |
| 14 | IoT event validation and storage in MongoDB |
| 15 | Device telemetry (heartbeat) ingestion and storage in MongoDB |
| 16 | RFID-to-animal resolution on incoming events |
| 17 | Multimedia upload to MinIO object storage; metadata stored in MongoDB — **optional/post-MVP; camera hardware not required for MVP** |
| 18 | Operational alert generation and storage |
| 19 | REST API for dashboard metrics |
| 20 | REST API for geoportal data |
| 21 | React frontend with admin views for all master data |
| 22 | Leaflet geoportal with station map, status color-coding, and event data |
| 23 | Docker Compose environment with all required services |

---

## 5. Out of Scope

The following capabilities are explicitly excluded from the MVP:

- Machine learning or predictive analytics
- Automated image recognition or computer vision
- Native mobile applications (iOS or Android)
- Microservices architecture
- Kubernetes or any container orchestration platform
- Advanced fine-grained role permissions beyond the three base roles
- Payment or subscription systems
- Real-time WebSocket dashboard (may be considered post-MVP if feasible)
- Production cloud deployment automation (CI/CD pipelines, infrastructure-as-code)
- Direct database writes from IoT devices
- Multi-tenant organization management
- Remote firmware update (OTA) management — manual USB reflashing is sufficient for MVP
- Multi-device assignment to a single station simultaneously
- Camera/media capture implementation — the platform schema and API reserve fields for media, but the camera hardware and capture firmware are not required for the MVP; the `media` fields in event payloads may be null
- Firmware development — firmware implementation is outside the scope of this software project; the backend defines an MQTT ingestion contract that firmware must satisfy, but writing or testing firmware code is not a deliverable of this SDD

> **Deployment note:** The MVP is designed to run locally first (Docker Compose on a developer laptop). VPS or cloud deployment is not required before the MVP is considered functional. When ready to share externally, the same Docker Compose configuration deploys to a low-cost VPS (e.g., Hetzner CX32 at ~€14/month) with no architecture changes.

> **MongoDB Atlas note:** For development and MVP testing, MongoDB Atlas free tier (M0 cluster) can replace the self-hosted MongoDB container. Only the `MONGODB_URL` environment variable changes. See SDD-07 §7.7 for details.

---

## 6. Actors and Roles

### 6.1 Human Actors

#### Administrator (`admin`)

The administrator has full access to the platform. Responsibilities include:

- Managing users, zones, stations, devices, animals, and food types
- Assigning users to stations and devices to stations
- Viewing all alerts, events, telemetry, dashboard metrics, and geoportal data
- Configuring system-wide settings

#### Researcher (`researcher`)

The researcher has read access to all data associated with their assigned stations. Responsibilities include:

- Viewing station activity, IoT events, animal records, and device telemetry
- Accessing the analytics dashboard and geoportal
- Generating and reviewing reports (post-MVP)

#### Field Operator (`field_operator`)

The field operator has limited operational access. Responsibilities include:

- Viewing stations they are assigned to
- Viewing recent events, device status, and alerts for their assigned stations
- Registering animals and updating food configurations for their assigned stations

### 6.2 Non-Human Actors

#### IoT Device (ESP32 Feeder)

The embedded feeding device is an independent hardware unit responsible for:

- Detecting animal presence via sensors
- Reading RFID tags
- Measuring food weight and consumption
- Recording temperature and humidity
- Optionally capturing photo or video and uploading media to object storage
- Publishing structured feeding events to the MQTT broker
- Publishing periodic telemetry heartbeats to the MQTT broker

The IoT device is registered in the platform independently of any station. It is subsequently associated with a station by an administrator. The device communicates exclusively via MQTT and never writes directly to any database.

#### MQTT Broker

The MQTT broker (Mosquitto) receives all messages from IoT devices and forwards them to the backend MQTT subscriber. Two topic namespaces are used: one for feeding events and one for device telemetry heartbeats.

#### MinIO Object Storage

MinIO provides S3-compatible object storage for multimedia files (photos and videos) captured by devices. The backend receives a media upload request or a pre-signed URL workflow and stores the binary file in MinIO. Only the resulting object URL and associated metadata are persisted in MongoDB.

---

## 7. Functional Requirements by Module

### 7.1 Auth Module

| ID | Requirement |
|----|-------------|
| FR-AUTH-01 | The system shall expose a public self-registration endpoint. Any visitor may register by submitting name, document, email, and password. No prior authentication or invitation is required. |
| FR-AUTH-02 | Self-registered users shall receive the role `researcher` automatically. No other role may be assigned through the public registration endpoint. |
| FR-AUTH-03 | The system shall hash passwords before storage using a secure algorithm (e.g., bcrypt). |
| FR-AUTH-04 | The system shall authenticate users via email and password and return a signed JWT token. |
| FR-AUTH-05 | The system shall validate JWT tokens on all protected endpoints. |
| FR-AUTH-06 | The system shall reject requests with expired or invalid tokens with HTTP 401. |
| FR-AUTH-07 | Tokens shall include user ID and role as claims. |
| FR-AUTH-08 | The first administrator account shall be created through a seed script or an environment-variable-driven bootstrap process executed at system initialization. It shall not be possible to create an `admin` user through the public registration endpoint. |

### 7.2 Users Module

| ID | Requirement |
|----|-------------|
| FR-USR-01 | The system shall store user profile data including name, document, email, role, `is_active`, and timestamps. |
| FR-USR-02 | An admin shall be able to list all registered users, view any user's profile, deactivate a user account, and change a user's role. |
| FR-USR-03 | A user shall be able to view and update their own profile (name, document, password). A user shall not be able to change their own role. |
| FR-USR-04 | The system shall enforce unique email addresses across all user accounts. |
| FR-USR-05 | The system shall support three roles: `admin`, `researcher`, `field_operator`. |
| FR-USR-06 | Deactivated users shall have all active JWT tokens rejected. Deactivated accounts shall not be able to log in. |

### 7.3 Zones Module

| ID | Requirement |
|----|-------------|
| FR-ZON-01 | The system shall allow admins and researchers to register geographic zones. |
| FR-ZON-02 | A zone shall store name, municipality, city, country, altitude, latitude, longitude, and a PostGIS geometry column. |
| FR-ZON-03 | The system shall allow listing and viewing all zones. |
| FR-ZON-04 | The system shall allow updating and soft-deleting zones. |
| FR-ZON-05 | A zone may contain multiple stations. |

### 7.4 Stations Module

| ID | Requirement |
|----|-------------|
| FR-STA-01 | The system shall allow any authenticated user with the role `researcher` or `admin` to register feeding stations with a unique code, name, and zone assignment. A researcher becomes the owner of any station they create. |
| FR-STA-02 | A station shall have a status field supporting four values: `active`, `inactive`, `maintenance`, and `offline`. |
| FR-STA-03 | The `offline` status shall indicate that the station's associated device has lost connectivity or is not reporting. |
| FR-STA-04 | The system shall allow updating station metadata and status. Only the station owner or an admin may update a station's details. |
| FR-STA-05 | The system shall allow listing stations with optional filtering by zone and status. Admins see all stations; researchers and field operators see only stations they own or are explicitly assigned to through `user_stations`. |
| FR-STA-06 | A station must belong to exactly one zone. |
| FR-STA-07 | The system shall allow viewing a station's associated device, users, food configuration, and recent events. A user may only view this detail for stations they own or are assigned to, unless they are an admin. |
| FR-STA-08 | A station shall store its geographic location as latitude, longitude, and a PostGIS geometry point. |
| FR-STA-09 | The frontend shall support capturing station location via browser Geolocation API (auto-detect). |
| FR-STA-10 | The frontend shall support capturing station location via manual point selection on an interactive Leaflet map. |
| FR-STA-11 | Both location methods shall produce the same latitude/longitude payload submitted to the station creation or update endpoint. |

### 7.5 Devices Module

A Device is an independent entity representing a physical ESP32 hardware unit. It is registered separately from a station and can be associated with a station or unassigned (in storage or being provisioned).

| ID | Requirement |
|----|-------------|
| FR-DEV-01 | The system shall allow admins to register devices with a unique serial number and optional human-readable name. |
| FR-DEV-02 | A device shall store its current firmware version as reported in the most recent telemetry heartbeat. |
| FR-DEV-03 | A device shall store a `last_seen` timestamp updated on every received MQTT message (event or heartbeat). |
| FR-DEV-04 | A device shall have a status field: `online`, `offline`, `unassigned`. |
| FR-DEV-05 | A device may be associated with at most one station at a time. |
| FR-DEV-06 | A station may have at most one active device at a time. |
| FR-DEV-07 | The system shall allow admins to assign a device to a station and to unassign it. |
| FR-DEV-08 | The system shall allow listing devices with optional filtering by status and station assignment. |
| FR-DEV-09 | When a device's `last_seen` exceeds a configurable threshold, the system shall set its status to `offline` and set the associated station's status to `offline`. |
| FR-DEV-10 | The system shall expose an endpoint to retrieve a device's current status, firmware version, and last-seen timestamp. |

### 7.6 Animals Module

Animals are global platform records not permanently tied to a single station. Their associations with stations are inferred from visit events recorded in MongoDB.

| ID | Requirement |
|----|-------------|
| FR-ANI-01 | The system shall allow registering animals with species, sex, estimated age, and optional RFID tag. |
| FR-ANI-02 | Animals shall be registered as global records independent of any station. |
| FR-ANI-03 | The system shall flag animals as identified (RFID present) or unidentified. |
| FR-ANI-04 | The system shall enforce uniqueness of RFID tags across all animals. |
| FR-ANI-05 | The system shall allow listing and updating animal records. |
| FR-ANI-06 | The system shall expose an endpoint returning the list of stations at which a given animal has been observed, derived from IoT event data. |
| FR-ANI-07 | The system shall expose an endpoint returning the list of animals observed at a given station, derived from IoT event data. |

### 7.7 Food Module

| ID | Requirement |
|----|-------------|
| FR-FOD-01 | The system shall allow registering food types with name, type, and description. |
| FR-FOD-02 | The system shall allow listing all registered food types. |
| FR-FOD-03 | The system shall allow updating food type metadata. |

### 7.8 Station Foods Module

| ID | Requirement |
|----|-------------|
| FR-SFD-01 | The system shall allow associating one or more food types with a station. |
| FR-SFD-02 | Each station-food association shall have an active flag. |
| FR-SFD-03 | The system shall allow activating or deactivating a food configuration for a station. |
| FR-SFD-04 | Only one food configuration per station should be active at a time. |

### 7.9 User Stations Module

| ID | Requirement |
|----|-------------|
| FR-UST-01 | The system shall allow admins and station owners (researchers) to assign other users to their stations with a specific role. |
| FR-UST-02 | A user shall only be able to read, write, or manage a station's data if they are the owner of that station or have an explicit entry in `user_stations` for it. There is no implicit cross-user station visibility. |
| FR-UST-03 | Admins are exempt from the station access restriction and may access all stations regardless of assignment. |
| FR-UST-04 | The system shall allow the station owner or an admin to remove a user from a station's `user_stations` entries. |
| FR-UST-05 | The system shall allow listing users assigned to a given station. Only the station owner or an admin may perform this query. |

### 7.10 IoT Events Module

| ID | Requirement |
|----|-------------|
| FR-IOT-01 | The system shall subscribe to the MQTT feeding event topic and receive events from IoT devices. |
| FR-IOT-02 | The system shall validate that the `station_id` and `device_id` referenced in the event exist in the database. |
| FR-IOT-03 | The system shall attempt to resolve the `rfid_tag` field to a registered animal record. |
| FR-IOT-04 | The system shall store validated events in MongoDB with all available telemetry fields. |
| FR-IOT-05 | The system shall store events that fail validation in a dead-letter collection for review. |
| FR-IOT-06 | The system shall expose a REST endpoint to query IoT events by station, device, date range, and event type. |
| FR-IOT-07 | The system shall support the following event types: `feeding_session`, `presence_detected`, `rfid_read`, `sensor_reading`. |
| FR-IOT-08 | Upon processing a valid event, the system shall update the associated device's `last_seen` timestamp. |

### 7.11 Device Telemetry Module

Device telemetry encompasses periodic heartbeat messages sent by devices independent of feeding events. These messages carry device health and status information.

| ID | Requirement |
|----|-------------|
| FR-TEL-01 | The system shall subscribe to the MQTT device telemetry topic and receive heartbeat messages from all registered devices. |
| FR-TEL-02 | Each heartbeat message shall carry at minimum: `device_id`, `firmware_version`, `timestamp`, `wifi_rssi`, `free_heap`, `uptime_seconds`, and `device_status`. |
| FR-TEL-03 | The system shall store each heartbeat document in the `device_telemetry` MongoDB collection. |
| FR-TEL-04 | Upon receiving a heartbeat, the system shall update the device's `firmware_version`, `last_seen`, and `status` fields in PostgreSQL. |
| FR-TEL-05 | The system shall expose a REST endpoint to retrieve the most recent telemetry record for a given device. |
| FR-TEL-06 | The system shall expose a REST endpoint to retrieve historical telemetry for a device over a configurable time range. |

### 7.12 Alerts Module

| ID | Requirement |
|----|-------------|
| FR-ALT-01 | The system shall generate alerts when IoT events or telemetry contain anomaly indicators. |
| FR-ALT-02 | The system shall support the following alert types: `connectivity_lost`, `device_offline`, `empty_tank`, `sensor_failure`, `camera_failure`, `rfid_read_failure`, `inactive_station`, `abnormal_activity`. |
| FR-ALT-03 | Alerts shall be stored in MongoDB and associated with a station ID, device ID (when applicable), and timestamp. |
| FR-ALT-04 | The system shall expose a REST endpoint to list alerts by station, device, and status (open, resolved). |
| FR-ALT-05 | The system shall allow operators to mark alerts as resolved. |

### 7.13 Analytics Module

| ID | Requirement |
|----|-------------|
| FR-ANA-01 | The system shall expose endpoints returning aggregated metrics for the dashboard. |
| FR-ANA-02 | Metrics shall include total stations, active stations, offline stations, total events, identified animals, and unidentified events. |
| FR-ANA-03 | The system shall provide time-series data for food consumption over configurable time ranges. |
| FR-ANA-04 | The system shall provide time-series data for animal visits over configurable time ranges. |
| FR-ANA-05 | The system shall provide consumption aggregated by zone. |
| FR-ANA-06 | The system shall provide event counts aggregated by station. |
| FR-ANA-07 | The system shall provide environmental data (temperature, humidity) grouped by location. |

### 7.14 Geoportal Module

| ID | Requirement |
|----|-------------|
| FR-GEO-01 | The system shall expose a REST endpoint returning station locations with status and summary metadata. |
| FR-GEO-02 | The system shall expose an endpoint returning heatmap data for station activity. |
| FR-GEO-03 | The system shall expose an endpoint returning heatmap data for food consumption. |
| FR-GEO-04 | The system shall expose an endpoint returning recent events grouped by zone. |
| FR-GEO-05 | The system shall expose an endpoint returning environmental readings by geographic location. |
| FR-GEO-06 | All geoportal endpoints shall be read-only. |

### 7.15 Media Module

Media files (photos and videos) captured by field devices are stored in a MinIO-compatible S3 object storage service. The backend stores only object URLs and metadata in MongoDB.

| ID | Requirement |
|----|-------------|
| FR-MED-01 | The system shall accept media file uploads via the backend API and store binary files in MinIO object storage. |
| FR-MED-02 | The system shall store media metadata (object URL, media type, file size, timestamp, station ID, device ID, event ID) in the `media_metadata` MongoDB collection. |
| FR-MED-03 | Binary media files shall never be stored in PostgreSQL or MongoDB. |
| FR-MED-04 | The system shall expose an endpoint to retrieve media metadata by event ID. |
| FR-MED-05 | The system shall expose a pre-signed URL generation endpoint allowing authorized clients to upload media directly to MinIO without proxying through the backend. |
| FR-MED-06 | Media objects shall be organized in MinIO using a bucket structure of `wildtrack-media/{station_id}/{year}/{month}/`. |

---

## 8. Non-Functional Requirements

### 8.1 Performance

| ID | Requirement |
|----|-------------|
| NFR-PER-01 | REST API endpoints shall respond within 500 ms under normal load for read operations. |
| NFR-PER-02 | The MQTT subscriber shall process and store IoT events within 2 seconds of receipt. |
| NFR-PER-03 | The system shall support at least 20 concurrent users in the MVP without degradation. |
| NFR-PER-04 | Media upload to MinIO via the backend proxy shall complete within 10 seconds for files up to 10 MB. |

### 8.2 Security

| ID | Requirement |
|----|-------------|
| NFR-SEC-01 | All API endpoints except registration and login shall require a valid JWT token. |
| NFR-SEC-02 | Passwords shall never be stored in plain text. |
| NFR-SEC-03 | JWT tokens shall expire after a configurable duration (default: 24 hours). |
| NFR-SEC-04 | The API shall validate and sanitize all input data using Pydantic schemas. |
| NFR-SEC-05 | Role-based authorization shall be enforced at the service layer, not only at the route level. |
| NFR-SEC-06 | IoT devices shall not have direct database access. All device communication occurs via MQTT. |
| NFR-SEC-07 | Pre-signed MinIO URLs shall expire after a short, configurable duration (default: 15 minutes). |
| NFR-SEC-08 | The MinIO bucket shall not be publicly accessible; all access shall go through the backend or time-limited pre-signed URLs. |

### 8.3 Reliability

| ID | Requirement |
|----|-------------|
| NFR-REL-01 | The system shall not lose an IoT event that has been received by the MQTT broker, even if downstream processing fails temporarily. |
| NFR-REL-02 | Invalid or unparseable IoT events shall be stored in a dead-letter collection rather than discarded. |
| NFR-REL-03 | The system shall remain operational if MongoDB is temporarily unavailable, and shall recover event processing upon reconnection. |
| NFR-REL-04 | The system shall remain operational if MinIO is temporarily unavailable; media upload failures shall be logged and surfaced as non-fatal errors. |

### 8.4 Maintainability

| ID | Requirement |
|----|-------------|
| NFR-MNT-01 | Each backend module shall encapsulate its own router, schemas, models, repository, service, and exceptions. |
| NFR-MNT-02 | Business logic shall not be placed inside route handlers. |
| NFR-MNT-03 | Database migrations shall be managed via Alembic. |
| NFR-MNT-04 | All environment-specific configuration shall be provided via environment variables, not hardcoded. |

### 8.5 Portability

| ID | Requirement |
|----|-------------|
| NFR-POR-01 | The full system shall be runnable locally using a single `docker compose up` command. |
| NFR-POR-02 | The system shall run on macOS and Linux without modification. |
| NFR-POR-03 | The Docker Compose environment shall include MinIO as a service alongside PostgreSQL, MongoDB, and Mosquitto. |

### 8.6 Observability

| ID | Requirement |
|----|-------------|
| NFR-OBS-01 | The backend shall emit structured logs for all incoming requests, MQTT events, telemetry messages, and errors. |
| NFR-OBS-02 | The system shall expose a health check endpoint (`/health`) that returns the status of all service dependencies, including PostgreSQL, MongoDB, MinIO, and the MQTT broker. |

### 8.7 Scalability (Post-MVP Note)

The MVP does not require horizontal scaling. The modular monolith architecture is designed to allow future decomposition into services if needed, but this is not a current requirement.

---

## 9. Main User Flows

### Flow 1 — User Registration and Login

1. User visits the web application and navigates to the registration page.
2. User submits name, email, and password.
3. System validates input and creates user account with role `researcher` by default.
4. User navigates to the login page.
5. User submits email and password.
6. System returns a signed JWT token.
7. Frontend stores the token and uses it for all subsequent API requests.

### Flow 2 — Zone and Station Setup

1. Admin logs in.
2. Admin navigates to the zone management section and creates a new zone with name and location fields.
3. Admin navigates to the station management section and begins creating a new station.
4. Admin assigns the station to a zone and enters its name and code.
5. **Location capture — option A (browser geolocation):** The frontend prompts the browser's Geolocation API. On approval, latitude and longitude are automatically populated in the form.
6. **Location capture — option B (manual map selection):** Admin clicks a point on the embedded Leaflet map within the station form. Latitude and longitude are populated from the clicked coordinate.
7. Admin submits the station form. The backend stores the location as latitude, longitude, and a PostGIS geometry point.
8. Admin navigates to the device management section and registers an ESP32 device with its serial number.
9. Admin assigns the device to the station just created.
10. Admin associates one or more food types with the station.
11. Admin assigns users to the station with appropriate roles.

### Flow 3 — Animal Registration

1. Field operator or researcher logs in.
2. User navigates to the animal management section.
3. User registers an animal with species, sex, estimated age, and optional RFID tag.
4. System stores the animal as a global record with no fixed station assignment.
5. If an RFID tag is provided, the system marks the animal as identified.
6. Once feeding events are recorded, the animal's station visit history becomes queryable through the events API.

### Flow 4 — Station Activity Monitoring

1. Researcher or admin logs in.
2. User navigates to the dashboard.
3. Dashboard displays summary metrics: active stations, offline stations, recent events, identified animals, open alert count.
4. User selects a specific station.
5. System displays the station's associated device (with firmware version and last-seen timestamp), recent events, and food configuration.
6. User navigates to the geoportal.
7. Geoportal shows a map with all station markers, color-coded by status.
8. User clicks a station marker to view a popup with station name, status, device health, and a link to station details.

### Flow 5 — Alert Review

1. Field operator or admin observes an open alert count in the dashboard.
2. User navigates to the alerts section.
3. System displays a list of open alerts, sorted by timestamp, with station name, device ID, and alert type.
4. User reviews the alert and marks it as resolved after taking corrective action.

### Flow 6 — Media Retrieval

1. User navigates to the event detail view for a feeding session that includes media.
2. Frontend requests media metadata from the backend by event ID.
3. Backend returns the media metadata including the object URL.
4. Frontend requests a pre-signed URL from the backend for the media object.
5. Backend generates a time-limited pre-signed MinIO URL and returns it.
6. Frontend uses the pre-signed URL to load the image or video directly from MinIO.

---

## 10. Main IoT Device Flows

### Flow 1 — Successful Feeding Session Event

1. Animal approaches the feeder. Presence sensor activates.
2. RFID reader attempts to read an animal tag.
3. Camera optionally captures photo or video and uploads the file to MinIO (or sends it to the backend for proxied upload).
4. Temperature and humidity sensors record environmental data.
5. Load cell records initial food weight before the feeding session.
6. Animal feeds. Load cell records final food weight.
7. ESP32 calculates consumed grams (`initial_weight - final_weight`).
8. ESP32 constructs a JSON event payload including `device_id`, `station_id`, all telemetry fields, and the media object URL (if available).
9. ESP32 publishes the event to the MQTT feeding event topic.
10. Backend MQTT subscriber receives the event.
11. Backend validates that `station_id` and `device_id` exist in PostgreSQL.
12. Backend attempts to resolve `rfid_tag` to an animal record in PostgreSQL.
13. Backend enriches the event with `animal_id` if the RFID tag is matched.
14. Backend stores the complete event document in MongoDB (`iot_events` collection).
15. Backend updates the device's `last_seen` timestamp in PostgreSQL.
16. If the event contains anomaly flags, backend generates an alert and stores it in MongoDB.

### Flow 2 — Unidentified Animal Event

1. Steps 1–6 identical to Flow 1.
2. RFID reader fails to read a tag (tag absent or read failure).
3. ESP32 sets `rfid_tag` to null in the event payload.
4. ESP32 publishes the event.
5. Backend receives and validates the event.
6. Backend stores the event with `animal_id: null` and `rfid_tag: null`.
7. Event is recorded as an unidentified feeding session.

### Flow 3 — Device Telemetry Heartbeat

1. Device publishes a periodic heartbeat message to the MQTT telemetry topic (e.g., every 60 seconds).
2. Heartbeat payload includes `device_id`, `firmware_version`, `timestamp`, `wifi_rssi`, `free_heap`, `uptime_seconds`, and `device_status`.
3. Backend MQTT subscriber receives the heartbeat.
4. Backend validates `device_id` existence in PostgreSQL.
5. Backend stores the heartbeat document in MongoDB (`device_telemetry` collection).
6. Backend updates the device's `firmware_version`, `last_seen`, and `status` fields in PostgreSQL.
7. If the device previously had status `offline`, backend sets its status to `online` and evaluates whether the associated station's `offline` status should be lifted.

### Flow 4 — Invalid or Malformed Event

1. ESP32 publishes an event with a missing or unknown `station_id`, invalid field types, or a malformed JSON body.
2. Backend MQTT subscriber receives the message.
3. Backend fails to validate the event.
4. Backend stores the raw payload in the `dead_letter_events` MongoDB collection with the failure reason and timestamp.
5. Backend logs the failure with the topic, timestamp, and reason for rejection.

### Flow 5 — Device Connectivity Loss and Recovery

1. ESP32 loses network connectivity and stops publishing events and heartbeats.
2. A background job in the backend evaluates device `last_seen` timestamps at a configurable interval.
3. When a device's `last_seen` exceeds the offline threshold, the backend sets the device status to `offline` and the associated station status to `offline`.
4. A `device_offline` alert is generated and stored in MongoDB.
5. When the device reconnects and sends a heartbeat (Flow 3), the backend sets device status back to `online`.
6. Backend evaluates whether to automatically lift the station `offline` status or require manual operator confirmation.

---

## 11. Data Requirements

### 11.1 PostgreSQL Master Data

All structured, relational, and geospatial master data is stored in PostgreSQL with the PostGIS extension.

**users** — Platform user accounts  
Fields: `id`, `name`, `document`, `email`, `password_hash`, `role`, `is_active`, `created_at`, `updated_at`

**zones** — Geographic zones where stations are deployed  
Fields: `id`, `name`, `municipality`, `city`, `country`, `altitude`, `latitude`, `longitude`, `geom` (PostGIS geometry), `created_at`, `updated_at`

**stations** — Logical feeding locations registered in the platform  
Fields: `id`, `code` (unique), `name`, `zone_id`, `latitude`, `longitude`, `geom` (PostGIS point), `status` (`active` | `inactive` | `maintenance` | `offline`), `created_at`, `updated_at`

**devices** — Physical ESP32 hardware units  
Fields: `id`, `serial_number` (unique), `name`, `station_id` (nullable FK), `status` (`online` | `offline` | `unassigned`), `firmware_version`, `last_seen`, `created_at`, `updated_at`

**animals** — Wildlife individuals tracked across the platform (not tied to a single station)  
Fields: `id`, `rfid_tag` (unique, nullable), `species`, `sex`, `estimated_age`, `is_identified`, `notes`, `created_at`, `updated_at`

**foods** — Food type catalog  
Fields: `id`, `name`, `type`, `description`, `created_at`, `updated_at`

**station_foods** — Associations between stations and food types  
Fields: `id`, `station_id`, `food_id`, `active`, `created_at`, `updated_at`

**user_stations** — Associations between users and stations  
Fields: `id`, `user_id`, `station_id`, `role`, `created_at`, `updated_at`

> **Note:** There is no `station_id` foreign key on the `animals` table. Animal-to-station associations are derived at query time from the `iot_events` collection in MongoDB by aggregating events that contain a resolved `animal_id` and grouping by `station_id`.

### 11.2 MongoDB Collections

All IoT event data, device telemetry, operational alerts, and media metadata are stored in MongoDB using flexible document schemas.

**iot_events** — Feeding session records and sensor readings from IoT devices  
Key fields: `event_id`, `event_type`, `station_id`, `device_id`, `animal_id`, `rfid_tag`, `timestamp`, `temperature`, `humidity`, `consumed_grams`, `initial_weight`, `final_weight`, `latitude`, `longitude`, `media_url`, `device_status`, `raw_payload`

**device_telemetry** — Periodic heartbeat records from registered devices  
Key fields: `telemetry_id`, `device_id`, `station_id`, `timestamp`, `firmware_version`, `wifi_rssi`, `free_heap`, `uptime_seconds`, `device_status`, `raw_payload`

**alerts** — Operational alerts generated by the backend  
Key fields: `alert_id`, `station_id`, `device_id` (nullable), `alert_type`, `message`, `status` (`open` | `resolved`), `created_at`, `resolved_at`

**media_metadata** — Metadata for photos and videos linked to IoT events  
Key fields: `media_id`, `event_id`, `station_id`, `device_id`, `media_type` (`photo` | `video`), `object_key`, `url`, `file_size_bytes`, `captured_at`

**dead_letter_events** — Raw payloads of events that failed validation  
Key fields: `received_at`, `topic`, `raw_payload`, `failure_reason`

### 11.3 MinIO Object Storage

Binary multimedia files are stored in a MinIO instance configured as a local S3-compatible service. See `docs/decisions/ADR-004-event-storage-strategy.md` for the full rationale.

- **Bucket:** `wildtrack-media`
- **Object key structure:** `{station_id}/{year}/{month}/{device_id}_{timestamp}_{filename}`
- **Access model:** Private bucket; access via backend proxy or time-limited pre-signed URLs (15-minute default expiry)
- **Supported formats:** JPEG, PNG (photos); MP4, AVI (video)
- **Size limit (MVP):** 10 MB per file

### 11.4 Data Retention

No specific data retention or archiving policies are defined for the MVP. All data is retained indefinitely.

### 11.5 Data Integrity Rules

- An animal's RFID tag must be unique across the entire system.
- A station must belong to exactly one zone; a zone may have many stations.
- A station may have at most one assigned device at a time.
- A device may be assigned to at most one station at a time.
- A user may be assigned to many stations; a station may have many users.
- Animals have no direct foreign key to stations. Animal-station relationships are event-derived.
- IoT events must reference a valid `station_id` and `device_id` at the time of ingestion. Invalid references are dead-lettered.
- Binary media files must not be stored in PostgreSQL or MongoDB. Only object keys, URLs, and metadata are persisted.

---

## 12. Geoportal Requirements

The geoportal is a map-based view built with React, Leaflet, and OpenStreetMap tiles. It consumes data exclusively from the backend REST API.

### 12.1 Map Display

| ID | Requirement |
|----|-------------|
| GEO-01 | The geoportal shall display a zoomable, pannable map using OpenStreetMap as the base layer. |
| GEO-02 | Each registered station shall be represented by a marker on the map at its geographic coordinates. |
| GEO-03 | Station markers shall be color-coded by status: green for `active`, gray for `inactive`, yellow for `maintenance`, red for `offline`. |
| GEO-04 | Clicking a station marker shall open a popup with the station name, zone, status, device health summary, and a link to the station detail view. |

### 12.2 Layers and Overlays

| ID | Requirement |
|----|-------------|
| GEO-05 | The geoportal shall include a heatmap layer visualizing station activity intensity (event count by location). |
| GEO-06 | The geoportal shall include a heatmap layer visualizing food consumption by location. |
| GEO-07 | The geoportal shall display temperature and humidity readings as a labeled overlay or tooltip on station markers. |
| GEO-08 | The geoportal shall allow toggling individual layers on and off. |

### 12.3 Event and Zone Data

| ID | Requirement |
|----|-------------|
| GEO-09 | The geoportal shall display recent events grouped by zone in a sidebar or panel. |
| GEO-10 | The geoportal shall allow filtering displayed data by zone. |
| GEO-11 | The geoportal shall show station popup summary data including last event timestamp, total visits, and device last-seen time. |

### 12.4 Technical Constraints

- The geoportal must not query databases directly. It must use the backend REST API.
- Initial map load with all station markers shall complete within 3 seconds under normal conditions.
- The Leaflet map used in the geoportal shall also be reused in the station registration form for manual location selection (see FR-STA-10).

---

## 13. Dashboard Requirements

The analytics dashboard is a data-dense summary view for administrators and researchers. It is displayed as part of the React frontend and consumes the analytics REST API.

### 13.1 Summary Metrics (KPI Cards)

| ID | Requirement |
|----|-------------|
| DSH-01 | The dashboard shall display the total number of registered stations. |
| DSH-02 | The dashboard shall display the number of currently active stations. |
| DSH-03 | The dashboard shall display the number of offline stations. |
| DSH-04 | The dashboard shall display the total number of IoT events recorded. |
| DSH-05 | The dashboard shall display the number of identified animals (with RFID). |
| DSH-06 | The dashboard shall display the number of feeding events with no RFID identification. |

### 13.2 Time-Series Charts

| ID | Requirement |
|----|-------------|
| DSH-07 | The dashboard shall display a line or bar chart of food consumption over time (daily, weekly, monthly granularity). |
| DSH-08 | The dashboard shall display a line or bar chart of animal visits over time. |
| DSH-09 | Time-series charts shall support a date range selector. |

### 13.3 Aggregated Views

| ID | Requirement |
|----|-------------|
| DSH-10 | The dashboard shall display total food consumption grouped by zone. |
| DSH-11 | The dashboard shall display total event counts grouped by station. |
| DSH-12 | The dashboard shall display a comparative chart of temperature and humidity by station or zone. |

### 13.4 Technical Constraints

- All dashboard data shall be fetched from the backend analytics REST API.
- Charts shall use Chart.js or Recharts.
- Dashboard data does not need to be real-time for the MVP; polling every 60 seconds is acceptable.

---

## 14. Alert Requirements

### 14.1 Alert Types

The system must detect and generate the following alert types:

| Alert Type | Trigger Condition |
|------------|------------------|
| `connectivity_lost` | Station has no associated active device, or no events received from the station in a configurable window |
| `device_offline` | A device's `last_seen` exceeds the offline threshold |
| `empty_tank` | Event payload indicates remaining food weight below a configured threshold |
| `sensor_failure` | Event payload contains an error flag for temperature, humidity, or weight sensors |
| `camera_failure` | Event payload indicates camera capture failed when media was expected |
| `rfid_read_failure` | Repeated consecutive events with absent RFID from a station where identified animals are registered |
| `inactive_station` | Station status is `active` but no events have been received in an extended period |
| `abnormal_activity` | Event frequency or consumption values fall outside expected statistical bounds |

### 14.2 Alert Lifecycle

| ID | Requirement |
|----|-------------|
| ALT-01 | Alerts shall be generated automatically by the backend during IoT event and telemetry processing, or by the background device-health monitoring job. |
| ALT-02 | Each alert shall have a status of `open` when created. |
| ALT-03 | Operators shall be able to mark alerts as `resolved` with a timestamp. |
| ALT-04 | Alerts shall be associated with a station ID and, where applicable, a device ID. |
| ALT-05 | The system shall not generate duplicate open alerts of the same type for the same station/device pair simultaneously. |

### 14.3 Alert Visibility

| ID | Requirement |
|----|-------------|
| ALT-06 | Open alerts shall be visible on the main dashboard as a count indicator. |
| ALT-07 | The alert list view shall display alerts sorted by timestamp, filterable by station, device, type, and status. |

---

## 15. MVP Acceptance Criteria

The MVP is considered complete and ready for review when all of the following criteria are met:

### Infrastructure

- [ ] `docker compose up` starts all services without errors: PostgreSQL/PostGIS, MongoDB, Mosquitto, MinIO, backend, and frontend.
- [ ] All PostgreSQL migrations run automatically on backend startup via Alembic.
- [ ] The backend `/health` endpoint returns a healthy status for all dependencies: PostgreSQL, MongoDB, MinIO, and MQTT broker.
- [ ] The MinIO bucket `wildtrack-media` is created automatically on first startup.

### Authentication and Registration

- [ ] Any visitor can self-register via the public endpoint by providing name, document, email, and password.
- [ ] A self-registered user is assigned the role `researcher` automatically; no other role is assignable through this endpoint.
- [ ] A registered user can log in and receive a valid JWT token.
- [ ] Protected endpoints reject requests without a valid JWT with HTTP 401.
- [ ] Endpoints enforce role-based access (admin vs. researcher vs. field_operator).
- [ ] It is not possible to create an `admin` account through the public registration endpoint.
- [ ] The first admin account is created by running the seed script (or bootstrapped via environment variables) without requiring a prior admin to exist.
- [ ] A deactivated user cannot log in and their existing tokens are rejected.

### Master Data Management

- [ ] An admin can create, update, and list zones via the API and the frontend UI.
- [ ] A researcher can create a station; that researcher is recorded as its owner.
- [ ] A researcher can create a station with location captured via browser geolocation.
- [ ] A researcher can create a station with location captured via manual map selection.
- [ ] A researcher can only list, view, and update stations they own or are explicitly assigned to; they cannot see other users' stations.
- [ ] An admin can list, view, and update all stations regardless of ownership.
- [ ] An admin can register a device with a serial number and associate it with a station.
- [ ] A station owner or admin can assign other users to a station via `user_stations`.
- [ ] A user can register animals as global records (no station required).
- [ ] A user can register food types and associate them with stations.

### Device Management

- [ ] A registered device shows correct status (`online`, `offline`, `unassigned`) in the API response.
- [ ] A device's `firmware_version` and `last_seen` are updated when a heartbeat is received via MQTT.
- [ ] When a device's `last_seen` exceeds the threshold, its status becomes `offline` and the associated station status becomes `offline`.
- [ ] A `device_offline` alert is generated when a device goes offline.

### IoT Event Ingestion

- [ ] A simulated ESP32 device can publish a valid feeding event to the MQTT broker.
- [ ] The backend receives and validates the event within 2 seconds.
- [ ] A valid event is stored in MongoDB (`iot_events`) with all telemetry fields populated, including `device_id`.
- [ ] An event with a known RFID tag is resolved to the correct animal record (`animal_id` populated).
- [ ] An event with an unknown or null RFID tag is stored with `animal_id: null`.
- [ ] A malformed or invalid event is stored in `dead_letter_events` and not discarded.

### Device Telemetry

- [ ] A simulated device can publish a heartbeat to the MQTT telemetry topic.
- [ ] The heartbeat is stored in MongoDB (`device_telemetry`).
- [ ] The device's `firmware_version`, `last_seen`, and `status` in PostgreSQL are updated accordingly.
- [ ] The telemetry history endpoint returns multiple heartbeat records for a device.

### Animal Tracking

- [ ] An animal registered globally appears in the animal list without any station assignment.
- [ ] After feeding events are recorded, the animal-stations endpoint returns the stations where that animal has been observed.
- [ ] The station-animals endpoint returns all animals observed at a given station, derived from event data.

### Multimedia

- [ ] A media file upload via the backend API is stored in the MinIO `wildtrack-media` bucket.
- [ ] Metadata (URL, type, event ID, station ID, device ID) is stored in MongoDB (`media_metadata`).
- [ ] A request to the media metadata endpoint by event ID returns the correct record.
- [ ] A request to generate a pre-signed URL returns a time-limited URL that allows direct access to the media object.

### Alerts

- [ ] An event containing a sensor failure flag generates an alert in MongoDB.
- [ ] The alert list endpoint returns open alerts correctly filtered by station and device.
- [ ] An operator can mark an alert as resolved and the status is updated.

### Dashboard

- [ ] The dashboard KPI cards display correct values including active and offline station counts.
- [ ] Consumption and visit charts render with real data from MongoDB.

### Geoportal

- [ ] The map loads and displays all registered station markers at their correct coordinates.
- [ ] Markers are color-coded correctly: green (active), gray (inactive), yellow (maintenance), red (offline).
- [ ] Clicking a station marker opens a popup showing name, status, zone, and device last-seen time.
- [ ] The activity heatmap layer renders correctly on the map.

### General

- [ ] All API endpoints are documented via OpenAPI (auto-generated by FastAPI at `/docs`).
- [ ] No hardcoded credentials or secrets exist in the codebase; all are provided via environment variables.
- [ ] The backend has at least basic integration tests covering auth, station registration, device registration, and event ingestion.

---

*End of SDD-01 Requirements Specification — v1.1.0*
