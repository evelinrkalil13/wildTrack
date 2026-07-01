# WildTrack — Development Roadmap

**Document:** SDD-09  
**Version:** 2.0.0  
**Status:** Approved  
**Changelog:**  
- v1.0.0 — Initial roadmap. Horizontal-layer phases (all backend first, then all frontend).
- v2.0.0 — Refactored to vertical-slice strategy: each slice delivers backend + frontend together per module. Phases 0 → Bootstrap; Slices 1–5 → module-by-module full-stack; Slice 6 → MQTT ingestion; Slice 7 → Geoportal; Slice 8 → Analytics. ADR-026 and ADR-027 incorporated.

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [Overall Strategy](#2-overall-strategy)
3. [Implementation Order](#3-implementation-order)
4. [Phase 0 — Project Bootstrap](#4-phase-0--project-bootstrap)
5. [Slice 1 — Auth](#5-slice-1--auth)
6. [Slice 2 — Zones](#6-slice-2--zones)
7. [Slice 3 — Stations](#7-slice-3--stations)
8. [Slice 4 — Devices](#8-slice-4--devices)
9. [Slice 5 — Animals, Foods, and Associations](#9-slice-5--animals-foods-and-associations)
10. [Slice 6 — MQTT Event Ingestion](#10-slice-6--mqtt-event-ingestion)
11. [Slice 7 — Geoportal](#11-slice-7--geoportal)
12. [Slice 8 — Analytics / Dashboard](#12-slice-8--analytics--dashboard)
13. [Phase Final — Integration and Stabilization](#13-phase-final--integration-and-stabilization)
14. [Definition of Done Per Slice](#14-definition-of-done-per-slice)
15. [Git Branch Strategy](#15-git-branch-strategy)
16. [Commit Strategy](#16-commit-strategy)
17. [What to Build First vs. Postpone](#17-what-to-build-first-vs-postpone)
18. [Manual Verification Checklist](#18-manual-verification-checklist)

---

## 1. Purpose and Scope

This document is the practical implementation guide for WildTrack. It bridges the specification documents (SDD-01 through SDD-08) and actual code writing. It defines the order of work, acceptance criteria, Git conventions, and a clear line between MVP deliverables and future work.

**This document assumes all specification documents (SDD-01 through SDD-09) have been reviewed and accepted before implementation begins.**

---

## 2. Overall Strategy

### Vertical Slices — Not Horizontal Layers

Each slice delivers a **complete, usable capability**: the backend endpoint, the frontend page, and the tests. After each slice, the platform has more working features than before — not just more untested backend code.

**Wrong approach (horizontal):**
```
→ All DB migrations → All backend modules → All frontend pages → Integration test everything
```
This delays the first working screen to week 6 and makes bugs extremely hard to trace.

**Right approach (vertical slices):**
```
→ Auth BE + Auth FE → Zones BE + Zones FE → Stations BE + Stations FE → ...
```
After Auth Slice: you can log in.  
After Zones Slice: you can log in and create a zone.  
After Stations Slice: you can see stations on the map.  
After MQTT Slice: events from the device appear live.

### Other principles

**Local first.** The entire MVP runs on a developer laptop. No VPS or cloud account is required before the MVP is functional.

**Test as you go.** Each slice includes backend unit tests and at least one integration test before moving to the next slice.

**No implementation before spec approval.** The spec documents define the contract. If a spec detail is unclear, update the SDD first, then implement.

**Frontend scaffold is a one-time setup.** The Vite + React project is created during Phase 0 alongside the FastAPI scaffold. Individual pages are added slice by slice.

---

## 3. Implementation Order

```
Phase 0: Bootstrap (infra + both project scaffolds)
  ↓
Slice 1: Auth         (BE: /auth, /users/me  |  FE: Login, Register, protected routes)
  ↓
Slice 2: Zones        (BE: /zones CRUD        |  FE: Zone list + create)
  ↓
Slice 3: Stations     (BE: /stations CRUD     |  FE: Station list + create + MapPicker)
  ↓
Slice 4: Devices      (BE: /devices CRUD + assign  |  FE: Device list + assign/unassign)
  ↓
Slice 5: Animals + Foods + Associations
          (BE: /animals, /foods, /station_foods, /user_stations
           FE: Animals list + create; Foods list + assign to station)
  ↓
Slice 6: MQTT Ingestion  (BE only: MQTT pipeline + alerts API  |  FE: Alert list)
  ↓
Slice 7: Geoportal    (BE: /geoportal          |  FE: Leaflet map + heatmap)
  ↓
Slice 8: Analytics    (BE: /analytics           |  FE: Dashboard charts + summary cards)
  ↓
Phase Final: Integration and Stabilization
```

---

## 4. Phase 0 — Project Bootstrap

**Goal:** Both the backend and frontend scaffolds boot. The infra stack starts with one command. The developer can reach `/health` and see the frontend placeholder page.

### 4.1 Infrastructure tasks

- [ ] Create repository on GitHub; initialize `main` branch with protection
- [ ] Create directory structure: `app/`, `frontend/`, `docs/`, `scripts/`, `migrations/`, `tests/`
- [ ] Create `compose.infra.yml` with services: `postgres` (postgis/postgis:16-3.4), `mongodb` (mongo:7.0), `minio` (minio/minio), `mosquitto` (eclipse-mosquitto:2.0)
- [ ] Configure Mosquitto for local plain MQTT: port `1883`, `allow_anonymous true`
- [ ] Write MinIO init script (`scripts/init_minio.sh`) — creates `wildtrack-media` bucket
- [ ] Create `.env.example` with all variable names (no values); copy to `.env` for local dev

### 4.2 Backend tasks

- [ ] Create `pyproject.toml` with all dependencies (Python 3.12); verify `python --version` reports 3.12
- [ ] Create FastAPI `app/main.py` with lifespan context and router registration stub
- [ ] Create `/health` endpoint returning `{ "status": "ok", "timestamp": "..." }`
- [ ] Configure SQLAlchemy 2.x async engine (`asyncpg`) in `infrastructure/postgres.py`
- [ ] Configure Motor async MongoDB client in `infrastructure/mongodb.py` with collection name constants
- [ ] Configure Alembic: `alembic init migrations`; create initial empty revision
- [ ] Create `shared/base_model.py`: SQLAlchemy `Base` with `id`, `created_at`, `updated_at`, `deleted_at`

### 4.3 Frontend tasks

- [ ] Scaffold Vite + React + TypeScript: `npm create vite@latest frontend -- --template react-ts`
- [ ] Install core dependencies: `axios`, `@tanstack/react-query`, `react-router-dom`, `react-hook-form`, `zod`, `@hookform/resolvers`, `leaflet`, `react-leaflet`, `recharts`
- [ ] Create `src/api/client.ts`: Axios instance with `baseURL`, JWT `Authorization` header interceptor, 401 redirect
- [ ] Create `src/router.tsx`: React Router v6 with placeholder routes and `<ProtectedRoute>` component
- [ ] Create placeholder `<App />` that renders "WildTrack loading…" — confirms Vite builds and HMR works

### 4.4 Verification

- [ ] `docker compose -f compose.infra.yml up -d` — all four services healthy
- [ ] `GET http://localhost:8000/health` → `{ "status": "ok" }`
- [ ] `http://localhost:5173` → placeholder page loads in browser

---

## 5. Slice 1 — Auth

**Goal:** Users can register and log in. JWT tokens are issued and validated. Admin is seeded. The frontend shows a working Login page and a Register page. Protected routes redirect to login when unauthenticated.

### Backend

- [ ] Alembic migration: `users` table (`id`, `name`, `document`, `email`, `password_hash`, `role`, `created_at`, `updated_at`, `deleted_at`)
- [ ] `modules/auth/`: router, schemas (`RegisterRequest`, `LoginRequest`, `TokenResponse`), service, repository, exceptions
- [ ] `shared/jwt.py`: `create_access_token()`, `create_refresh_token()`, `decode_token()` — HS256, 24-hour access, 7-day refresh
- [ ] `shared/security.py`: `hash_password()`, `verify_password()` — bcrypt work factor 12
- [ ] `dependencies.py`: `get_current_user` dependency using JWT Bearer header
- [ ] `POST /auth/register` — role locked to `researcher`; returns `UserRead`
- [ ] `POST /auth/login` — returns `TokenResponse { access_token, refresh_token, token_type }`
- [ ] `POST /auth/refresh` — validates refresh token; returns new access token
- [ ] `modules/users/`: `GET /users/me`, `GET /users/{id}` (admin), `GET /users` (admin), `PATCH /users/{id}` (admin)
- [ ] `scripts/seed_admin.py` — creates admin user from `ADMIN_EMAIL` + `ADMIN_PASSWORD` env vars

**Backend tests:**
- [ ] `test_auth_service.py`: register, login, token decode, duplicate email → 409
- [ ] `test_auth_api.py`: register → login → `GET /users/me` end-to-end
- [ ] `test_users_api.py`: researcher can't access `GET /users`; admin can

### Frontend

- [ ] `src/features/auth/LoginPage.tsx` — email + password form; calls `POST /auth/login`; stores token in `localStorage` key `wt_token`; redirects to dashboard
- [ ] `src/features/auth/RegisterPage.tsx` — name, email, password form; calls `POST /auth/register`; redirects to login on success
- [ ] `src/context/AuthContext.tsx` — `useAuth()` hook: `{ user, login(), logout(), isAuthenticated }`; reads `wt_token`; decodes JWT claims
- [ ] `<ProtectedRoute>` component: redirects to `/login` if `!isAuthenticated`
- [ ] Navigation bar with user name display + logout button
- [ ] Axios interceptor: on 401 response → `logout()` → redirect to `/login`

**Slice 1 done when:** Admin can log in via API and via browser. Researcher can self-register via browser. Protected route redirects work. Duplicate email shows error message in UI.

---

## 6. Slice 2 — Zones

**Goal:** Admin and researcher can create, update, and list zones. Admin can soft-delete zones. Zone data includes geographic coordinates stored in PostGIS. The frontend shows a simple Zones management page.

> **Authorization correction (SDD-04 is authoritative):** POST and PATCH zones are allowed for `admin` **or** `researcher`. DELETE is `admin` only. All authenticated users (including `field_operator`) can read zones via GET.

### Backend

- [x] Alembic migration 0004: `zones` table with PostGIS `geom GEOMETRY(POINT, 4326)` column, GiST index (`ix_zones_geom`), partial unique index `(lower(name), lower(country)) WHERE deleted_at IS NULL`, and `set_zones_updated_at` trigger
- [x] Alembic migration 0005: drop duplicate auto-created GiST index (`idx_zones_geom`) — GeoAlchemy2 auto-creates it during `create_table`; only `ix_zones_geom` is kept
- [x] PostGIS extension: `CREATE EXTENSION IF NOT EXISTS postgis;` in migration 0004
- [x] `modules/zones/`: router, schemas (`ZoneCreate`, `ZoneRead`, `ZoneUpdate`, `ZoneListResponse`), models, repository, service, exceptions
- [x] `POST /zones` (`admin` or `researcher`) — stores `latitude`/`longitude` as PostGIS POINT; returns `ZoneRead`
- [x] `GET /zones` — paginated list; supports `?country=` filter (case-insensitive); all authenticated users
- [x] `GET /zones/{id}` — single zone; all authenticated users
- [x] `PATCH /zones/{id}` (`admin` or `researcher`) — partial update; re-computes `geom` when lat/lon change
- [x] `DELETE /zones/{id}` (`admin` only) — soft delete; blocked if zone has active stations

> **Known stub — `ZoneRepository.has_active_stations`:** Returns `False` unconditionally in Slice 2 because the `stations` table does not yet exist. This will be replaced in Slice 3 when the stations module is implemented. Until then, `DELETE /zones/{id}` always succeeds (assuming the zone exists), regardless of station assignments.

- [x] `shared/pagination.py`: `PaginatedResponse[T]`, `paginate()`, `make_paginated_response()`
- [x] `app/dependencies.py`: `require_role()`, `require_admin`, `require_researcher_or_above`

**Backend tests (completed):**
- [x] `test_zones_service.py` (12 unit tests): create, get, list, update, delete, conflict, not-found, stub station guard
- [x] `test_zones_api.py` (21 integration mock tests): admin/researcher/field_operator authorization for all 5 endpoints; 401 without auth; 409/404/400 error codes
- [x] `test_zones_db_api.py` (12 real-DB tests): full CRUD against PostgreSQL+PostGIS; country filter (exact and case-insensitive); geom column populated via `ST_AsText`; soft-delete excludes records from list

### Frontend

- [ ] `src/features/zones/ZonesListPage.tsx` — table of zones; `GET /zones` via TanStack Query key `["zones"]`; support `?country=` filter input
- [ ] `src/features/zones/ZoneCreatePage.tsx` — form with name, municipality, city, country, altitude, lat, lon; submits `POST /zones`
- [ ] Add Zones link to navigation (admin/researcher only, conditionally rendered)
- [ ] Error and loading states via TanStack Query

**Slice 2 done when:** Researcher or admin can create a zone via the browser form. Zone appears in the zones list. Country filter works. Admin can delete a zone.

---

## 7. Slice 3 — Stations

**Goal:** Researchers can register stations with geographic location (browser geolocation or manual map selection). Station detail page shows the assigned device and zone. A basic Leaflet map preview is visible on the create form.

### Backend

- [x] Alembic migration 0006: `stations` table with `station_status` enum, PostGIS POINT, all indexes, trigger
- [x] Alembic migration 0007: `user_stations` table with `station_user_role` enum, partial unique index, trigger
- [x] `modules/stations/`: full CRUD (exceptions, models, schemas, repository, service, router)
- [x] `modules/user_stations/`: models + repository (service/endpoints deferred to Slice 5)
- [x] `POST /stations` — auto-assigns creating user as station owner via `user_stations` (role: `owner`); stores PostGIS POINT
- [x] `GET /stations` — researcher sees only stations they are members of; admin sees all; filters: `zone_id`, `status`
- [x] `GET /stations/{id}` — returns minimal `StationRead` (id, code, name, zone_id, lat, lon, status, timestamps); device/food/member_count deferred to Slice 4/5
- [x] `PATCH /stations/{id}` — owner or admin; validates zone_id if changed
- [x] `DELETE /stations/{id}` — owner or admin; soft-deletes station + all user_stations rows
- [x] `ZoneRepository.has_active_stations()` stub replaced with real query against `stations` table
- [ ] `PATCH /devices/{device_id}/assign` — deferred to Slice 4
- [ ] `PATCH /devices/{device_id}/unassign` — deferred to Slice 4

**Authorization (Slice 3):**
- `POST /stations`: `admin` or `researcher`
- `GET /stations`: any authenticated user (scoped by membership for non-admin)
- `GET /stations/{id}`: admin or member
- `PATCH /stations/{id}`: admin or station owner
- `DELETE /stations/{id}`: admin or station owner

**Backend tests:**
- [x] `test_stations_service.py`: 15 unit tests covering all service paths, all authorization branches
- [x] `test_stations_api.py`: 18 mocked integration tests covering all 5 endpoints, all auth scenarios
- [x] `test_stations_db_api.py`: 14 real-DB tests (CRUD, access scoping, geom verification, zone deletion blocked)

### Frontend

- [ ] `src/features/stations/StationsListPage.tsx` — card or table list; `["stations"]` query key
- [ ] `src/features/stations/StationCreatePage.tsx` — form with zone select, station name, code, and `<MapPicker>` component
- [ ] `src/components/organisms/MapPicker.tsx` — Leaflet map; shows draggable marker; pre-fills from browser `navigator.geolocation`; exposes `{ lat, lon }` to parent form
- [ ] `src/features/stations/StationDetailPage.tsx` — shows station info, zone, current device, current food

**Slice 3 done when:** Researcher creates a station, picks its location on the map, and sees it appear in the station list and detail page.

---

## 8. Slice 4 — Devices

**Goal:** Admin can register devices by entering a serial number. Admin can assign a device to a station and unassign it. The Devices page shows assignment status.

### Backend

- [x] Alembic migration: `devices` table (`id`, `serial_number`, `mac_address` [nullable], `name`, `station_id`, `status`, `firmware_version`, `last_seen`, `created_at`, `updated_at`, `deleted_at`) — `device_status` enum: `online`, `offline`, `unassigned`; partial unique on serial, partial unique one-device-per-station; CHECK constraint enforcing status ↔ station_id integrity
- [x] `modules/devices/`: exceptions, models, schemas, repository, service, router
- [x] `POST /devices` (admin) — serial_number uniqueness enforced; returns `DeviceRead` with `status=unassigned`; optional `mac_address` (informational only, non-unique)
- [x] `GET /devices` — admin sees all (including unassigned); researcher sees only devices assigned to their stations; filters: `status`, `station_id`
- [x] `GET /devices/{id}` — admin or station member; returns `DeviceRead` with `station_code` (resolved via LEFT JOIN)
- [x] `PATCH /devices/{id}` (admin) — update `name` only
- [x] `DELETE /devices/{id}` (admin) — soft delete; auto-unassigns from station before deleting
- [x] `PATCH /devices/{id}/assign` (admin) — validates device is unassigned, station exists, station has no active device; sets `status=online`
- [x] `PATCH /devices/{id}/unassign` (admin) — validates device is assigned; sets `station_id=NULL`, `status=unassigned`
- [x] `stations/service.py` `delete_station` updated: calls `DeviceRepository.unassign_from_station` before soft-deleting station (cascade unassign)
- [x] `GET /devices/{id}/telemetry` and `/latest` — **deferred to Slice 6 (MongoDB not yet configured)**

**Backend tests:**
- [x] `test_devices_service.py`: 22 unit tests — create (happy path, serial conflict), get (admin any device, non-admin blocked on unassigned/non-member), list (admin vs. non-admin scoping, filters), update, assign (happy path, already assigned, station has device, station not found), unassign (happy path, not assigned), delete (unassigned, auto-unassign assigned, not found)
- [x] `test_devices_api.py`: 22 mocked API tests — all 7 endpoints, auth enforcement (401/403), 400/404/409 error paths, filter passthrough
- [x] `test_devices_db_api.py`: 15 real-DB tests — create/duplicate serial, admin vs. researcher access, assign/unassign, at-most-one-device constraint, delete device, station delete cascades device unassign

### Frontend

- [ ] `src/features/devices/DevicesListPage.tsx` — lists devices; shows status badge (`online` / `offline` / `unassigned`); shows assigned station
- [ ] `src/features/devices/DeviceCreatePage.tsx` — serial_number + optional name form; admin only
- [ ] Device assign/unassign action on Station Detail page (admin button)
- [ ] Copy `device_id` to clipboard action (for firmware provisioning)

**Slice 4 done when:** Admin registers a device, assigns it to a station, and sees its status in the Devices list and on the Station Detail page.

---

## 9. Slice 5 — Animals, Foods, and Associations

**Goal:** Researchers can register animals with RFID tags. Admin can create food types. Station owners can assign food to their station. The Animals page is visible to any station member.

### Backend

- [x] Alembic migration 0009: `animal_sex` enum + `animals` table (`id`, `rfid_tag` [partial unique nullable], `species`, `sex`, `estimated_age`, `is_identified`, `notes`, `deleted_at`, `created_at`, `updated_at`)
- [x] Alembic migration 0010: `foods` table (`id`, `name` [partial unique active], `type`, `description`, `deleted_at`, `created_at`, `updated_at`)
- [x] Alembic migration 0011: `station_foods` table — no `deleted_at`; `active` flag; partial unique `(station_id) WHERE active = TRUE`; FK cascade/restrict
- [x] `modules/animals/`: full CRUD — `POST`, `GET` (list + filters), `GET /{id}`, `PATCH /{id}`, `DELETE /{id}` (admin); `is_identified` auto-maintained from `rfid_tag`
- [x] `GET /animals/{id}/stations` — stub returning `stations: []`; MongoDB query deferred to Slice 6
- [x] `modules/foods/`: `POST`, `GET` (list), `GET /{id}`, `PATCH /{id}` (researcher/admin), `DELETE /{id}` (admin); blocked if food is active at any station
- [x] `modules/station_foods/`: `POST /stations/{id}/foods`, `GET /stations/{id}/foods`, `PATCH /{sfid}/activate`, `PATCH /{sfid}/deactivate`, `DELETE /{sfid}` — atomic active-food swap; blocked delete if active
- [x] `modules/user_stations/`: extended with service + schemas + router — `POST /stations/{id}/members`, `GET /stations/{id}/members`, `PATCH /stations/{id}/members/{us_id}`, `DELETE /stations/{id}/members/{us_id}`; cannot assign/change/remove owner role
- [x] `shared/enums.py`: `AnimalSex` enum added
- [x] `StationFoodRead` includes `food_name` and `food_type` (JOIN with foods)
- [x] `MemberRead` includes `user_name` and `user_email` (JOIN with users)

**Discrepancy resolutions applied:**
- SDD-09 listed `user_stations` table migration as Slice 5 work — already created in migration 0007 (Slice 3); skipped.
- SDD-09 described only POST + DELETE for members; SDD-04 §13 defines 4 endpoints — all 4 implemented per SDD-04.
- `GET /animals/{id}/stations` requires MongoDB; stub returns empty list until Slice 6 wires Motor client.

**Backend tests:**
- [x] `test_animals_service.py` (20 unit tests): create, RFID conflict → 409, `is_identified` sync on update/clear, get, list, delete, stations stub
- [x] `test_foods_service.py` (15 unit tests): create, name conflict → 409, update, delete blocked by active station, delete allowed, list
- [x] `test_station_foods_service.py` (18 unit tests): add food, active swap, food already associated → 409, station not found → 404, activate/deactivate, cannot remove active → 400, non-owner → 403
- [x] `test_members_service.py` (15 unit tests): assign, already member → 409, cannot assign owner, non-owner → 403, update role, cannot change owner, remove, cannot remove owner
- [x] `test_animals_api.py` (18 mocked API tests): all 6 endpoints; 401/403/404/409; field validation
- [x] `test_foods_api.py` (16 mocked API tests): all 5 endpoints; field_operator blocked → 403; FOOD_IN_USE → 400
- [x] `test_station_foods_api.py` (13 mocked API tests): all 5 endpoints; CANNOT_REMOVE_ACTIVE → 400; FOOD_ALREADY_ASSOCIATED → 409
- [x] `test_members_api.py` (14 mocked API tests): all 4 endpoints; owner role → 422; CANNOT_REMOVE_OWNER → 400; CANNOT_CHANGE_OWNER → 400
- [x] `test_animals_db_api.py` (11 real-DB tests): create with/without RFID; duplicate RFID → 409; update RFID syncs `is_identified`; filters; stations stub; admin delete; non-admin blocked
- [x] `test_foods_db_api.py` (8 real-DB tests): create; duplicate name → 409; field_operator blocked; get/update; admin delete; researcher blocked
- [x] `test_station_foods_db_api.py` (7 real-DB tests): add; active swap; duplicate → 409; activate/deactivate cycle; cannot remove active → 400; remove inactive → 204; catalog delete blocked when active
- [x] `test_members_db_api.py` (8 real-DB tests): assign; cannot assign owner → 422; duplicate → 409; list includes owner; update role; cannot remove owner → 400; remove → 204; non-member cannot list → 403

### Frontend

- [ ] `src/features/animals/AnimalsListPage.tsx` — searchable table; `["animals"]` query key
- [ ] `src/features/animals/AnimalCreatePage.tsx` — species, sex, estimated age, RFID tag; optional fields clearly labelled
- [ ] `src/features/animals/AnimalDetailPage.tsx` — shows RFID tag; lists stations visited (from `GET /animals/{id}/stations`)
- [ ] `src/features/foods/FoodsListPage.tsx` — list of food types
- [ ] `src/features/foods/FoodAssignPage.tsx` — assign/activate food on station (linked from Station Detail)
- [ ] Station Detail: Members section — list members; add/remove member form (owner/admin)

**Slice 5 done when:** Researcher registers an animal with an RFID tag. Admin assigns a food type to a station. Station member list is correct.

---

## 10. Slice 6 — MQTT Event Ingestion

**Goal:** A test script publishes a `feeding_session` event to Mosquitto. The backend validates it, stores it in MongoDB, resolves the RFID tag to an animal, and generates an alert if conditions are met. Alert list is visible in the frontend.

### Backend

- [ ] Add MQTT client library to `pyproject.toml` (`aiomqtt` recommended; `asyncio-mqtt` as fallback)
- [ ] `infrastructure/mqtt/client.py` — connect, subscribe to `wildtrack/#`, reconnect loop with exponential backoff
- [ ] `infrastructure/mqtt/dispatcher.py` — topic-prefix routing to handlers; catch-all dead-letter on uncaught exception
- [ ] `infrastructure/mqtt/topics.py` — string constants for all topics
- [ ] `iot_events` ingestion handler — full pipeline per SDD-08 §20.7:
  - JSON parse → schema validate (`EventPayloadSchema`) → station lookup → device lookup → RFID resolve → MongoDB insert (`iot_events`) → alert evaluation
- [ ] `telemetry` ingestion handler — heartbeat parse → `device_telemetry` MongoDB insert → `devices.last_seen_at` + `firmware_version` PostgreSQL update
- [ ] LWT handler — `status: offline` → `devices.status = offline` + station status update + alert insert
- [ ] `dead_letter_events` MongoDB collection and writer function
- [ ] `modules/alerts/`: router, schemas, MongoDB repository, service
  - `GET /alerts` — paginated; filterable by status (`open` / `resolved`) and station
  - `PATCH /alerts/{id}/resolve`
- [ ] Wire MQTT client startup/shutdown in `app/lifespan.py`
- [ ] `scripts/test_mqtt_publish.py` — CLI tool: `--event feeding_session|presence_detected|telemetry|unknown_station`

**Backend tests:**
- [ ] `test_event_handler.py`: valid event → MongoDB insert; RFID resolved; RFID unknown → null animal_id
- [ ] `test_dead_letter.py`: unknown station → dead-letter document; schema error → dead-letter document
- [ ] `test_lw_handler.py`: offline LWT → device status updated; alert inserted
- [ ] `test_telemetry_handler.py`: heartbeat → device_telemetry insert; last_seen_at updated

### Frontend

- [ ] `src/features/alerts/AlertsListPage.tsx` — table of open alerts; resolve action button; `["alerts"]` query key; auto-refetch every 30 seconds
- [ ] Alert badge in navigation bar — count of open alerts (refetches every 60 seconds)

**Slice 6 done when:** `python scripts/test_mqtt_publish.py --event feeding_session` runs → event appears in MongoDB `iot_events` → event count visible in the (placeholder) dashboard → alert page loads.

---

## 11. Slice 7 — Geoportal

**Goal:** A Leaflet map shows all active stations with color-coded status markers. Clicking a marker opens a popup with station summary and recent events. A heatmap layer shows feeding activity density.

### Backend

- [ ] `modules/geoportal/`: router, schemas, MongoDB + PostgreSQL repositories, service
- [ ] `GET /geoportal/stations` — all active stations with `{ id, name, code, status, latitude, longitude, last_event_at, event_count_7d, active_food_name, device_status }`; popup data included in station list response
- [ ] `GET /geoportal/heatmap/activity` — feeding activity heatmap points: `[{ lat, lon, weight }]`; weight = event count per location bucket
- [ ] `GET /geoportal/heatmap/consumption` — food consumption heatmap points: `[{ lat, lon, weight }]`; weight = total consumed_grams
- [ ] `GET /geoportal/env-readings` — average temperature and humidity readings by location
- [ ] `GET /geoportal/events-by-zone` — recent events grouped by zone for sidebar panel
- [ ] `scripts/seed_demo_data.py` — creates 2–3 zones, 3–5 stations, 5–10 animals, 50–100 synthetic events in MongoDB

**Backend tests:**
- [ ] `test_geoportal_api.py`: stations list returns correct fields; heatmap/activity and heatmap/consumption return arrays; events-by-zone returns grouped result

### Frontend

- [ ] `src/features/geoportal/GeoportalPage.tsx` — full-height Leaflet map using `react-leaflet`
- [ ] Station markers — color by status: green (online), yellow (offline), grey (unassigned/inactive)
- [ ] Station popup — name, status, active food, last seen, 3 most recent events
- [ ] Heatmap layer — using Leaflet.heat plugin or a custom circle-marker approximation
- [ ] Layer toggle — checkboxes for: Stations, Activity Heatmap, Consumption Heatmap (defaults: stations + activity on; consumption off)
- [ ] Environmental overlay (optional layer) — `GET /geoportal/env-readings` — pin icons at station locations with temperature label
- [ ] Geoportal link in navigation (visible to all authenticated users)

**Slice 7 done when:** Run `scripts/seed_demo_data.py` → open Geoportal page → station markers appear → click a marker → popup shows station info and recent events → heatmap layer visible.

---

## 12. Slice 8 — Analytics / Dashboard

**Goal:** The Dashboard home page shows platform summary cards and two charts: consumption over time, and visits over time. Charts are populated with seeded or real event data.

### Backend

- [ ] `modules/analytics/`: router, schemas, MongoDB aggregation repository, service
- [ ] `GET /analytics/kpi` — `{ total_stations, active_stations, disconnected_stations, total_events, identified_animals, unidentified_events }` (`KpiResponse`)
- [ ] `GET /analytics/consumption` — query params: `from`, `to`, `station_id` (optional); returns `[{ date, consumed_grams }]`
- [ ] `GET /analytics/visits` — returns `[{ date, visit_count }]`
- [ ] `GET /analytics/consumption-by-zone` — returns `[{ zone_id, zone_name, total_consumed_grams }]`
- [ ] `GET /analytics/events-by-station` — returns `[{ station_id, station_name, event_count }]`
- [ ] `GET /analytics/env` — returns `[{ date, avg_temperature_c, avg_humidity_pct }]`

**Backend tests:**
- [ ] `test_analytics_api.py`: kpi returns correct totals from seeded data; consumption returns time-series array

### Frontend

- [ ] `src/features/dashboard/DashboardPage.tsx` — default landing page after login
- [ ] Summary cards row: Total Stations · Active Stations · Disconnected · Total Events · Identified Animals · Unidentified Events — from `GET /analytics/kpi`
- [ ] Consumption over time chart — Recharts `<LineChart>`; `["analytics", "consumption"]` query key
- [ ] Visits over time chart — Recharts `<BarChart>`; `["analytics", "visits"]` query key
- [ ] Events by station chart — Recharts `<BarChart horizontal>`; `["analytics", "events-by-station"]` query key
- [ ] Date range picker (start/end date inputs) — updates all chart queries

**Slice 8 done when:** Dashboard loads with populated summary cards and at least two charts showing data from seeded events.

---

## 13. Phase Final — Integration and Stabilization

**Goal:** End-to-end flow works from MQTT event to dashboard display. All tests pass. Docker Compose full-stack boots cleanly. README is accurate.

### Tasks

- [ ] Run full manual verification checklist (§18)
- [ ] Run `pytest --cov=app tests/` — verify ≥ 80% coverage on all service modules
- [ ] Run `docker compose up` full stack — verify all containers healthy (`docker compose ps`)
- [ ] Review all API endpoints against SDD-04 — confirm no endpoint is missing or misnamed
- [ ] Verify `/docs` (FastAPI Swagger) shows all endpoints with correct request/response schemas
- [ ] Update `.env.example` — confirm all variables used anywhere in code are documented
- [ ] Write `README.md`: prerequisites, quick-start (infra → seed admin → run backend → run frontend), MQTT test script usage, seed demo data
- [ ] Search codebase: `grep -r "localhost" app/` — confirm no hardcoded host names remain (should use env vars)
- [ ] Search codebase: `grep -r "password\|secret\|key" app/ --include="*.py" -i` — confirm no hardcoded secrets
- [ ] Resolve all `# TODO` comments or file as GitHub Issues
- [ ] Tag release: `git tag v1.0.0-mvp`

---

## 14. Definition of Done Per Slice

| Slice | Backend done when | Frontend done when |
|-------|------------------|--------------------|
| Phase 0 | `GET /health` returns 200; infra stack starts; Alembic configured | Vite dev server starts; placeholder page loads at `:5173` |
| Slice 1 — Auth | `POST /auth/register` and `POST /auth/login` tested; admin seed works | Login page works; register page works; protected routes redirect to `/login` |
| Slice 2 — Zones | `GET /zones` and `POST /zones` tested; PostGIS verified | Zone list and create form work; admin-only create enforced in UI |
| Slice 3 — Stations | `GET /stations` (scoped) and `POST /stations` tested; PostGIS POINT stored | Station list and create form work; MapPicker shows location on map |
| Slice 4 — Devices | `POST /devices`, assign/unassign tested; serial_number conflict → 409 | Device list and create form work; assign action on station detail works |
| Slice 5 — Animals/Foods | Animals, foods, station_foods, user_stations all CRUD tested | Animals list and create work; food assignment on station detail works |
| Slice 6 — MQTT Ingestion | Test script publishes event → MongoDB `iot_events` doc exists; dead-letter works; LWT tested | Alerts page shows open alerts; badge count in nav updates |
| Slice 7 — Geoportal | All five geoportal endpoints (`/stations`, `/heatmap/activity`, `/heatmap/consumption`, `/env-readings`, `/events-by-zone`) return correct data with seeded dataset | Station markers visible on map; popup shows station summary; activity and consumption heatmap layers toggle independently |
| Slice 8 — Analytics | All six analytics endpoints (`/kpi`, `/consumption`, `/visits`, `/consumption-by-zone`, `/events-by-station`, `/env`) return correct data with seeded dataset | Dashboard KPI cards populated; at least two charts render with real data |
| Phase Final | `pytest` ≥ 80% coverage; full Docker Compose stack healthy | Full manual checklist passes; no build errors |

---

## 15. Git Branch Strategy

### Branch Names

| Purpose | Pattern | Example |
|---------|---------|---------|
| Main (protected) | `main` | `main` |
| Development integration | `develop` | `develop` |
| Phase or slice | `slice/{n}-{name}` | `slice/1-auth`, `slice/6-mqtt` |
| Single feature | `feat/{module}-{description}` | `feat/stations-map-picker` |
| Bug fix | `fix/{description}` | `fix/jwt-expiry-validation` |
| Documentation | `docs/{description}` | `docs/update-sdd-08-rfid` |
| Refactor | `refactor/{description}` | `refactor/extract-base-repository` |
| Chore | `chore/{description}` | `chore/add-gitignore` |

### Merge Strategy

- Slice branches: develop backend tasks → commit → develop frontend tasks → commit → merge into `develop` via PR
- Each slice branch covers both backend and frontend for that module
- `develop` merges into `main` only when the slice is complete (both BE and FE, tests passing)
- Tag after each slice: `git tag v0.1.0` (auth), `v0.2.0` (zones), …, `v0.8.0` (analytics), `v1.0.0-mvp` (final)
- No direct commits to `main`

---

## 16. Commit Strategy

### Commit Message Format

```
<type>(<scope>): <short summary>

[optional body]
[optional footer: BREAKING CHANGE, Closes #issue]
```

### Commit Types

| Type | When to use |
|------|------------|
| `feat` | New feature, endpoint, or page |
| `fix` | Bug fix |
| `test` | Adding or updating tests |
| `docs` | Documentation changes |
| `chore` | Tooling, deps, config, scripts |
| `refactor` | Code restructure without behavior change |
| `perf` | Performance improvement |
| `style` | Formatting only (no logic change) |

### Scope Examples

`auth`, `users`, `zones`, `stations`, `devices`, `animals`, `foods`, `mqtt`, `alerts`, `geoportal`, `analytics`, `frontend`, `infra`, `docker`, `alembic`

### Commit Examples

```
feat(auth): implement JWT login endpoint with bcrypt validation

feat(auth): add Login and Register pages with form validation

feat(stations): store station location as PostGIS POINT

feat(stations): add MapPicker component with geolocation pre-fill

feat(mqtt): add event dispatcher with dead-letter fallback

test(animals): add RFID uniqueness conflict test

chore(docker): add compose.infra.yml with four core services
```

### Commit Frequency

- Commit after each logical unit (one endpoint, one page, one test suite, one migration)
- Within a slice, alternate backend and frontend commits — don't batch all backend then all frontend
- Push at end of each working session
- Tag stable states at slice completion

---

## 17. What to Build First vs. Postpone

### Build in MVP

| Item | Why |
|------|-----|
| Auth + JWT (BE + FE) | Every other slice depends on it |
| Zones + Stations + Devices (BE + FE) | Core domain; required for MQTT ingestion (station/device validation) |
| Animals + RFID (BE + FE) | Required for event RFID resolution |
| MQTT ingestion pipeline (BE) + Alerts (FE) | Core product value; validates the hardware ingestion contract |
| Geoportal API + map view (BE + FE) | Demonstrates spatial value; required for academic presentation |
| Analytics API + dashboard (BE + FE) | Shows research value without complex ML |
| Docker Compose infra | Required for local testing and future deployment |

### Postpone to Post-MVP

| Item | Why |
|------|-----|
| OTA firmware management | No firmware is being written; manual USB reflashing is sufficient |
| Camera / media capture | Camera hardware not required; schema reserves fields |
| Real-time WebSocket events | Polling (TanStack Query `refetchInterval`) is sufficient for MVP |
| Staged rollout / group device commands | Requires multiple physical devices to test |
| MinIO presigned URL for camera | Depends on camera hardware being ready |
| Machine learning / anomaly detection | Future work; out of scope |
| Kubernetes / cloud deployment automation | VPS with Docker Compose is sufficient |
| Multi-tenant organizations | Project is single-tenant for MVP |
| Advanced role permissions | Three roles are sufficient |
| Payment / subscription | Not applicable |
| 125 kHz LF RFID (PIT microchip) support | MFRC522 is 13.56 MHz HF; LF requires different hardware |
| MongoDB Time Series collections | Standard collections are sufficient at MVP scale; migration path documented in ADR-026 |
| Automated device provisioning portal | Manual config via USB serial is sufficient for MVP (ADR-027) |

---

## 18. Manual Verification Checklist

Run this checklist at Phase Final and after any significant change.

### 18.1 Infrastructure

- [ ] `docker compose -f compose.infra.yml up -d` — all four services healthy
- [ ] `GET http://localhost:8000/health` → `{ "status": "ok" }`
- [ ] PostgreSQL: `psql -U wildtrack -d wildtrack -c "SELECT PostGIS_Version();"` — returns version string
- [ ] MongoDB: `mongosh --eval "db.adminCommand({ ping: 1 })"` → `{ ok: 1 }`
- [ ] MinIO console: `http://localhost:9001` — accessible; `wildtrack-media` bucket exists
- [ ] Mosquitto: `mosquitto_pub -h localhost -p 1883 -t test/ping -m hello` — no error

### 18.2 Auth

- [ ] `POST /auth/register` with valid payload → 201; role = `researcher`
- [ ] `POST /auth/register` with duplicate email → 409 Conflict
- [ ] `POST /auth/login` → 200; `access_token` and `refresh_token` present
- [ ] `POST /auth/login` wrong password → 401
- [ ] `GET /users/me` with valid Bearer → 200; user data returned
- [ ] `GET /users/me` without token → 401
- [ ] `GET /users` with researcher token → 403
- [ ] `GET /users` with admin token → 200; list returned
- [ ] Frontend: Login page submits → redirected to dashboard
- [ ] Frontend: Register page submits → redirected to login
- [ ] Frontend: Accessing `/stations` without token → redirected to `/login`

### 18.3 Zones and Stations

- [ ] `POST /zones` (admin) → 201 Created
- [ ] `POST /zones` (researcher) → 403 Forbidden
- [ ] `GET /zones` (researcher) → 200; list returned
- [ ] `POST /stations` (researcher) → 201; researcher auto-assigned as member
- [ ] `GET /stations` (researcher) → only own stations returned
- [ ] `GET /stations` (admin) → all stations returned
- [ ] Station location stored: verify `geom` IS NOT NULL via `SELECT ST_AsText(geom) FROM stations`
- [ ] Frontend: Zone create form submits → zone appears in list
- [ ] Frontend: Station create form → MapPicker shows location marker → station appears in list

### 18.4 Devices

- [ ] `POST /devices` (admin) → 201; `device_id` (UUID) returned
- [ ] `POST /devices` with duplicate `serial_number` → 409
- [ ] `PATCH /devices/{id}/assign` → 200; device `status = online` (or `offline` until MQTT heartbeat)
- [ ] `GET /stations/{id}` → `device` field populated with device summary
- [ ] Frontend: Device list shows assignment status; assign button appears for admin

### 18.5 Animals and Foods

- [ ] `POST /animals` → 201 with RFID tag
- [ ] `POST /animals` with duplicate RFID → 409
- [ ] `POST /foods` (admin) → 201
- [ ] `POST /stations/{id}/foods` → 201; food assigned as active
- [ ] `GET /animals/{id}` → returns animal data
- [ ] Frontend: Animal create form submits → animal appears in list
- [ ] Frontend: Food assignment on Station Detail → food name shown in station info

### 18.6 MQTT Event Ingestion

- [ ] `python scripts/test_mqtt_publish.py --event feeding_session` → no error
- [ ] MongoDB `iot_events` collection: document inserted with correct fields
- [ ] `animal_id` populated when RFID tag matches registered animal
- [ ] `animal_id` is null when RFID tag is unknown
- [ ] `python scripts/test_mqtt_publish.py --event unknown_station` → dead-letter document in `dead_letter_events`
- [ ] Telemetry heartbeat → `device_telemetry` document inserted; `devices.last_seen_at` updated
- [ ] LWT offline → `devices.status = offline`; alert inserted in `alerts` collection
- [ ] Frontend: Alerts page shows open alert from LWT; resolve button resolves it

### 18.7 Geoportal

- [ ] `python scripts/seed_demo_data.py` → creates demo data without errors
- [ ] `GET /geoportal/stations` → list with lat/lon, status, event count; popup data embedded
- [ ] `GET /geoportal/heatmap/activity` → array of `{ lat, lon, weight }` activity points
- [ ] `GET /geoportal/heatmap/consumption` → array of `{ lat, lon, weight }` consumption points
- [ ] `GET /geoportal/events-by-zone` → events grouped by zone
- [ ] Frontend: Geoportal page loads; station markers visible; clicking marker opens popup; heatmap layer toggles (activity / consumption) work

### 18.8 Analytics / Dashboard

- [ ] `GET /analytics/kpi` → non-zero counts after seeding
- [ ] `GET /analytics/consumption` → time-series array with at least 1 record
- [ ] `GET /analytics/visits` → time-series array
- [ ] `GET /analytics/events-by-station` → array with station names and counts
- [ ] `GET /analytics/env` → time-series array with temperature and humidity
- [ ] Frontend: Dashboard summary cards show correct numbers; at least two charts render with data

### 18.9 Final Quality

- [ ] `pytest --cov=app tests/ --cov-report=term-missing` → service layer coverage ≥ 80%
- [ ] `docker compose up` (full stack) → all containers healthy; `GET /health` accessible
- [ ] `http://localhost:5173` (or `:3000`) → frontend loads; no console errors
- [ ] `http://localhost:8000/docs` → all API endpoints listed with correct schemas
- [ ] Codebase: no hardcoded secrets, passwords, or `localhost` references outside env var loading
- [ ] `README.md` exists and quick-start instructions are accurate

---

*This roadmap is a living document. Update task checkboxes as items are completed. Create GitHub Issues for any blocked item. Tag `v1.0.0-mvp` when Phase Final checklist passes.*
