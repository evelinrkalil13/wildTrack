# WildTrack Platform — REST API Contract

**Document:** SDD-04 API Contract  
**Version:** 1.0.0  
**Date:** 2026-06-13  
**Status:** Draft — Pending Approval  
**References:** SDD-01 Requirements v1.2.0, SDD-03 Data Model v1.0.0

---

## Table of Contents

1. [API Overview](#1-api-overview)
2. [Common Schemas](#2-common-schemas)
3. [Error Catalog](#3-error-catalog)
4. [Authorization Matrix](#4-authorization-matrix)
5. [Authentication Endpoints](#5-authentication-endpoints)
6. [User Endpoints](#6-user-endpoints)
7. [Zone Endpoints](#7-zone-endpoints)
8. [Station Endpoints](#8-station-endpoints)
9. [Device Endpoints](#9-device-endpoints)
10. [Animal Endpoints](#10-animal-endpoints)
11. [Food Endpoints](#11-food-endpoints)
12. [Station Food Endpoints](#12-station-food-endpoints)
13. [User-Station Assignment Endpoints](#13-user-station-assignment-endpoints)
14. [IoT Event Endpoints](#14-iot-event-endpoints)
15. [Geoportal Endpoints](#15-geoportal-endpoints)
16. [Analytics and Dashboard Endpoints](#16-analytics-and-dashboard-endpoints)
17. [Alert Endpoints](#17-alert-endpoints)
18. [Media Endpoints](#18-media-endpoints)

---

## 1. API Overview

### 1.1 Base URL

```
http://localhost:8000/api/v1
```

All endpoints are prefixed with `/api/v1`. The version prefix allows non-breaking evolution of the API.

### 1.2 Authentication

All endpoints except `POST /auth/register` and `POST /auth/login` require a valid JWT Bearer token.

```
Authorization: Bearer <jwt_token>
```

Tokens are issued by `POST /auth/login` and expire after a configurable duration (default 24 hours).

### 1.3 Content Types

| Direction | Content-Type |
|-----------|-------------|
| Request body (JSON) | `application/json` |
| Request body (file upload) | `multipart/form-data` |
| All responses | `application/json` |

### 1.4 Pagination

All list endpoints support pagination via query parameters. Responses follow the same envelope:

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | `1` | Page number (1-indexed) |
| `page_size` | integer | `20` | Items per page. Maximum: `100` |

**Paginated response envelope:**

```json
{
  "items": [...],
  "total": 84,
  "page": 1,
  "page_size": 20,
  "pages": 5
}
```

### 1.5 Date and Time Format

All timestamps are returned as **ISO 8601 strings in UTC**: `"2026-06-13T10:30:00Z"`. Timestamps in request bodies must also be ISO 8601 UTC.

### 1.6 UUID Format

All `id` fields are **UUID v7 strings** in lowercase hyphenated format: `"019281a8-5e2c-7f00-b3d4-a1e2f3c4d5e6"`.

### 1.7 Soft-Deleted Records

Soft-deleted records (`deleted_at IS NOT NULL`) are never returned by any endpoint unless the caller is an admin and explicitly requests them (post-MVP feature). All standard responses show only active records.

### 1.8 Health Check

```
GET /health
```

Returns the operational status of all backend dependencies. No authentication required.

**Response 200:**
```json
{
  "status": "ok",
  "dependencies": {
    "postgres": "ok",
    "mongodb": "ok",
    "minio": "ok",
    "mqtt": "ok"
  },
  "version": "1.0.0"
}
```

If any dependency is unavailable, `status` is `"degraded"` and the affected dependency shows `"error"`.

---

## 2. Common Schemas

Reusable schema components referenced throughout this document.

### 2.1 UserSummary

Compact user representation used in nested responses.

```json
{
  "id": "019281a8-5e2c-7f00-b3d4-a1e2f3c4d5e6",
  "name": "Ana Martínez",
  "email": "ana@example.com",
  "role": "researcher"
}
```

### 2.2 StationSummary

Compact station representation used in nested responses.

```json
{
  "id": "019281a9-ab12-7c00-9f3e-b2d3e4f5a6b7",
  "code": "STA-001",
  "name": "North Ridge Feeder",
  "status": "active"
}
```

### 2.3 DeviceSummary

```json
{
  "id": "019281aa-cd34-7e00-af5c-c3d4e5f6a7b8",
  "serial_number": "WT-ESP32-0042",
  "status": "online",
  "firmware_version": "1.4.2",
  "last_seen": "2026-06-13T10:28:00Z"
}
```

### 2.4 PaginatedList

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20,
  "pages": 0
}
```

### 2.5 ValidationError (HTTP 422)

FastAPI returns this format automatically for Pydantic schema failures.

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

### 2.6 BusinessError (HTTP 4xx)

Used for all business logic errors (conflict, not found, forbidden, etc.).

```json
{
  "detail": "A user with this email already exists.",
  "code": "EMAIL_ALREADY_EXISTS"
}
```

---

## 3. Error Catalog

| HTTP Code | Code String | When Used |
|-----------|-------------|-----------|
| `400` | `BAD_REQUEST` | Malformed request that passes Pydantic but fails business pre-conditions |
| `401` | `UNAUTHORIZED` | Missing, expired, or invalid JWT token |
| `403` | `FORBIDDEN` | Token is valid but the user lacks permission for this action |
| `404` | `NOT_FOUND` | Requested resource does not exist or is soft-deleted |
| `409` | `CONFLICT` | Unique constraint violation (duplicate email, code, serial, RFID tag) |
| `413` | `PAYLOAD_TOO_LARGE` | Upload file exceeds the 10 MB limit |
| `415` | `UNSUPPORTED_MEDIA_TYPE` | Uploaded file MIME type is not permitted |
| `422` | — | Pydantic schema validation failure (FastAPI built-in) |
| `500` | `INTERNAL_ERROR` | Unhandled server-side error |

---

## 4. Authorization Matrix

| Role | Self-data | Own stations | Any station | Any user | Devices | Admin ops |
|------|-----------|-------------|-------------|----------|---------|-----------|
| `admin` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `researcher` | ✅ | ✅ | ❌ | ❌ | Read only | ❌ |
| `field_operator` | ✅ | Assigned only | ❌ | ❌ | Read only | ❌ |

**Station access rule:** A non-admin user may access a station if and only if they have an active row in `user_stations` linking them to that station. Researchers additionally access stations they created (as `owner`).

---

## 5. Authentication Endpoints

### 5.1 Register

```
POST /auth/register
```

**Purpose:** Self-register a new user account. Available to anyone without authentication. All self-registered users receive `role = researcher`.

**Authorization:** Public

**Request body:**
```json
{
  "name": "Ana Martínez",
  "document": "1234567890",
  "email": "ana@example.com",
  "password": "SecurePass123!"
}
```

**Field rules:**

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `name` | string | YES | 2–255 characters, non-empty after trim |
| `document` | string | YES | 5–50 characters |
| `email` | string | YES | Valid email format; unique among active users |
| `password` | string | YES | 8–128 characters; at least one uppercase, one lowercase, one digit |

**Response 201 Created:**
```json
{
  "id": "019281a8-5e2c-7f00-b3d4-a1e2f3c4d5e6",
  "name": "Ana Martínez",
  "email": "ana@example.com",
  "role": "researcher",
  "is_active": true,
  "created_at": "2026-06-13T10:00:00Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `409` | `EMAIL_ALREADY_EXISTS` | Email is already registered and active |
| `422` | — | Schema validation failure |

---

### 5.2 Login

```
POST /auth/login
```

**Purpose:** Authenticate with email and password. Returns a JWT access token.

**Authorization:** Public

**Request body:**
```json
{
  "email": "ana@example.com",
  "password": "SecurePass123!"
}
```

**Field rules:**

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `email` | string | YES | Valid email format |
| `password` | string | YES | Non-empty |

**Response 200 OK:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "019281a8-5e2c-7f00-b3d4-a1e2f3c4d5e6",
    "name": "Ana Martínez",
    "email": "ana@example.com",
    "role": "researcher"
  }
}
```

**Token claims:**
```json
{
  "sub": "019281a8-5e2c-7f00-b3d4-a1e2f3c4d5e6",
  "role": "researcher",
  "iat": 1718272800,
  "exp": 1718359200
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `401` | `INVALID_CREDENTIALS` | Email not found or password incorrect |
| `403` | `ACCOUNT_INACTIVE` | Account exists but `is_active = false` |
| `422` | — | Schema validation failure |

---

### 5.3 Get Current User

```
GET /auth/me
```

**Purpose:** Return the profile of the currently authenticated user.

**Authorization:** Authenticated (any role)

**Response 200 OK:**
```json
{
  "id": "019281a8-5e2c-7f00-b3d4-a1e2f3c4d5e6",
  "name": "Ana Martínez",
  "document": "1234567890",
  "email": "ana@example.com",
  "role": "researcher",
  "is_active": true,
  "created_at": "2026-06-13T10:00:00Z",
  "updated_at": "2026-06-13T10:00:00Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `401` | `UNAUTHORIZED` | Missing or invalid token |

---

## 6. User Endpoints

### 6.1 List Users

```
GET /users
```

**Purpose:** List all registered users. Admin only.

**Authorization:** `admin`

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `role` | string | Filter by role: `admin`, `researcher`, `field_operator` |
| `is_active` | boolean | Filter by account status |
| `page` | integer | Page number (default `1`) |
| `page_size` | integer | Items per page (default `20`, max `100`) |

**Response 200 OK:**
```json
{
  "items": [
    {
      "id": "019281a8-5e2c-7f00-b3d4-a1e2f3c4d5e6",
      "name": "Ana Martínez",
      "document": "1234567890",
      "email": "ana@example.com",
      "role": "researcher",
      "is_active": true,
      "created_at": "2026-06-13T10:00:00Z",
      "updated_at": "2026-06-13T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `401` | `UNAUTHORIZED` | Missing or invalid token |
| `403` | `FORBIDDEN` | Caller is not admin |

---

### 6.2 Get User

```
GET /users/{user_id}
```

**Purpose:** Return a single user's full profile. Admin can retrieve any user; authenticated users can retrieve only their own profile (use `GET /auth/me` for self).

**Authorization:** `admin` (any user) or self

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | UUID | Target user identifier |

**Response 200 OK:**
```json
{
  "id": "019281a8-5e2c-7f00-b3d4-a1e2f3c4d5e6",
  "name": "Ana Martínez",
  "document": "1234567890",
  "email": "ana@example.com",
  "role": "researcher",
  "is_active": true,
  "created_at": "2026-06-13T10:00:00Z",
  "updated_at": "2026-06-13T10:00:00Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `401` | `UNAUTHORIZED` | Missing or invalid token |
| `403` | `FORBIDDEN` | Non-admin requesting another user's profile |
| `404` | `NOT_FOUND` | User does not exist or is soft-deleted |

---

### 6.3 Update Own Profile

```
PATCH /users/{user_id}
```

**Purpose:** Update the name, document, or password of a user's own profile. Users cannot change their own role via this endpoint.

**Authorization:** Self only (the token `sub` must match `user_id`)

**Request body (all fields optional):**
```json
{
  "name": "Ana Martínez Ruiz",
  "document": "0987654321",
  "password": "NewSecurePass456!"
}
```

**Field rules:**

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `name` | string | NO | 2–255 characters |
| `document` | string | NO | 5–50 characters |
| `password` | string | NO | 8–128 characters; same complexity rules as registration |

**Response 200 OK:** Full user object (same as `GET /users/{user_id}`).

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `403` | `FORBIDDEN` | Caller is not the target user |
| `404` | `NOT_FOUND` | User not found |
| `422` | — | Validation failure |

---

### 6.4 Change User Role

```
PATCH /users/{user_id}/role
```

**Purpose:** Change a user's platform role. Admin only. A user cannot change their own role.

**Authorization:** `admin`

**Request body:**
```json
{
  "role": "field_operator"
}
```

**Field rules:**

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `role` | string | YES | One of: `admin`, `researcher`, `field_operator` |

**Response 200 OK:** Full user object with updated role.

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `400` | `SELF_ROLE_CHANGE` | Admin attempting to change their own role |
| `403` | `FORBIDDEN` | Caller is not admin |
| `404` | `NOT_FOUND` | User not found |

---

### 6.5 Deactivate User

```
PATCH /users/{user_id}/deactivate
```

**Purpose:** Set `is_active = false`. The user can no longer log in and existing tokens are rejected. Admin only.

**Authorization:** `admin`

**Request body:** None

**Response 200 OK:**
```json
{
  "id": "019281a8-5e2c-7f00-b3d4-a1e2f3c4d5e6",
  "is_active": false,
  "updated_at": "2026-06-13T11:00:00Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `400` | `ALREADY_INACTIVE` | User is already deactivated |
| `400` | `SELF_DEACTIVATE` | Admin attempting to deactivate their own account |
| `403` | `FORBIDDEN` | Caller is not admin |
| `404` | `NOT_FOUND` | User not found |

---

### 6.6 Activate User

```
PATCH /users/{user_id}/activate
```

**Purpose:** Set `is_active = true`. Re-enables login for a previously deactivated user. Admin only.

**Authorization:** `admin`

**Request body:** None

**Response 200 OK:** Full user object with `is_active: true`.

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `400` | `ALREADY_ACTIVE` | User is already active |
| `403` | `FORBIDDEN` | Caller is not admin |
| `404` | `NOT_FOUND` | User not found |

---

## 7. Zone Endpoints

### 7.1 Create Zone

```
POST /zones
```

**Purpose:** Register a new geographic zone.

**Authorization:** `admin` or `researcher`

**Request body:**
```json
{
  "name": "Andean Forest Reserve — Block A",
  "municipality": "La Calera",
  "city": "Bogotá",
  "country": "Colombia",
  "altitude": 2850.5,
  "latitude": 4.7110,
  "longitude": -74.0721
}
```

**Field rules:**

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `name` | string | YES | 2–255 characters; unique per country among active zones |
| `municipality` | string | NO | Max 255 characters |
| `city` | string | YES | Max 255 characters |
| `country` | string | YES | Max 100 characters |
| `altitude` | number | NO | Any numeric value (meters) |
| `latitude` | number | YES | Between −90 and +90 |
| `longitude` | number | YES | Between −180 and +180 |

**Response 201 Created:**
```json
{
  "id": "019281ab-ef56-7100-8c6d-d4e5f6a7b8c9",
  "name": "Andean Forest Reserve — Block A",
  "municipality": "La Calera",
  "city": "Bogotá",
  "country": "Colombia",
  "altitude": 2850.5,
  "latitude": 4.7110,
  "longitude": -74.0721,
  "created_at": "2026-06-13T10:00:00Z",
  "updated_at": "2026-06-13T10:00:00Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `409` | `ZONE_NAME_EXISTS` | Name + country combination already exists |
| `422` | — | Validation failure (lat/lng out of range, missing required fields) |

---

### 7.2 List Zones

```
GET /zones
```

**Purpose:** Return all active zones.

**Authorization:** Authenticated (any role)

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `country` | string | Filter by country name |
| `page` | integer | Default `1` |
| `page_size` | integer | Default `20`, max `100` |

**Response 200 OK:** Paginated list of zone objects (same schema as Create Zone response).

---

### 7.3 Get Zone

```
GET /zones/{zone_id}
```

**Purpose:** Return a single zone by ID.

**Authorization:** Authenticated (any role)

**Response 200 OK:** Single zone object.

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `404` | `NOT_FOUND` | Zone not found or soft-deleted |

---

### 7.4 Update Zone

```
PATCH /zones/{zone_id}
```

**Purpose:** Update one or more fields of an existing zone. All fields are optional.

**Authorization:** `admin` or `researcher`

**Request body (all fields optional):**
```json
{
  "name": "Andean Forest Reserve — Block A North",
  "altitude": 2900.0,
  "latitude": 4.7200,
  "longitude": -74.0800
}
```

**Response 200 OK:** Updated zone object.

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `404` | `NOT_FOUND` | Zone not found |
| `409` | `ZONE_NAME_EXISTS` | Updated name conflicts with another active zone |

---

### 7.5 Delete Zone (Soft)

```
DELETE /zones/{zone_id}
```

**Purpose:** Soft-delete a zone by setting `deleted_at`. Cannot delete a zone that has active stations.

**Authorization:** `admin`

**Response 204 No Content**

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `400` | `ZONE_HAS_STATIONS` | Zone has one or more active stations |
| `403` | `FORBIDDEN` | Caller is not admin |
| `404` | `NOT_FOUND` | Zone not found |

---

## 8. Station Endpoints

### 8.1 Create Station

```
POST /stations
```

**Purpose:** Register a new feeding station. The authenticated user is automatically assigned as `owner` in `user_stations`. Location is submitted as latitude and longitude captured either from the browser Geolocation API or from a manual Leaflet map selection.

**Authorization:** `admin` or `researcher`

**Request body:**
```json
{
  "code": "STA-001",
  "name": "North Ridge Feeder",
  "zone_id": "019281ab-ef56-7100-8c6d-d4e5f6a7b8c9",
  "latitude": 4.7125,
  "longitude": -74.0710
}
```

**Field rules:**

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `code` | string | YES | 2–50 chars; uppercase alphanumeric and hyphens only; unique among active stations |
| `name` | string | YES | 2–255 characters |
| `zone_id` | UUID | YES | Must reference an existing active zone |
| `latitude` | number | YES | Between −90 and +90 |
| `longitude` | number | YES | Between −180 and +180 |

**Response 201 Created:**
```json
{
  "id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
  "code": "STA-001",
  "name": "North Ridge Feeder",
  "zone_id": "019281ab-ef56-7100-8c6d-d4e5f6a7b8c9",
  "zone_name": "Andean Forest Reserve — Block A",
  "latitude": 4.7125,
  "longitude": -74.0710,
  "status": "active",
  "device": null,
  "created_at": "2026-06-13T10:05:00Z",
  "updated_at": "2026-06-13T10:05:00Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `404` | `NOT_FOUND` | `zone_id` does not exist |
| `409` | `STATION_CODE_EXISTS` | A station with this code already exists |
| `422` | — | Validation failure |

---

### 8.2 List Stations

```
GET /stations
```

**Purpose:** List stations visible to the authenticated user. Admins see all stations. Researchers and field operators see only stations they own or are assigned to.

**Authorization:** Authenticated (any role)

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `zone_id` | UUID | Filter by zone |
| `status` | string | Filter by status: `active`, `inactive`, `maintenance`, `offline` |
| `page` | integer | Default `1` |
| `page_size` | integer | Default `20`, max `100` |

**Response 200 OK:** Paginated list of station objects.

---

### 8.3 Get Station

```
GET /stations/{station_id}
```

**Purpose:** Return full details of a station including its current device, active food configuration, and assigned user list.

**Authorization:** Admin, or user assigned to this station

**Response 200 OK:**
```json
{
  "id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
  "code": "STA-001",
  "name": "North Ridge Feeder",
  "zone_id": "019281ab-ef56-7100-8c6d-d4e5f6a7b8c9",
  "zone_name": "Andean Forest Reserve — Block A",
  "latitude": 4.7125,
  "longitude": -74.0710,
  "status": "active",
  "device": {
    "id": "019281aa-cd34-7e00-af5c-c3d4e5f6a7b8",
    "serial_number": "WT-ESP32-0042",
    "status": "online",
    "firmware_version": "1.4.2",
    "last_seen": "2026-06-13T10:28:00Z"
  },
  "active_food": {
    "id": "019281ad-5678-7300-be8f-f6a7b8c9d0e1",
    "food_id": "019281ae-90ab-7400-cf90-a7b8c9d0e1f2",
    "food_name": "Mixed Seeds",
    "active": true
  },
  "member_count": 3,
  "created_at": "2026-06-13T10:05:00Z",
  "updated_at": "2026-06-13T10:05:00Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `403` | `FORBIDDEN` | User is not assigned to this station |
| `404` | `NOT_FOUND` | Station not found |

---

### 8.4 Update Station

```
PATCH /stations/{station_id}
```

**Purpose:** Update station metadata or status. All fields are optional.

**Authorization:** Admin or station owner

**Request body:**
```json
{
  "name": "North Ridge Feeder — Primary",
  "status": "maintenance",
  "latitude": 4.7130,
  "longitude": -74.0715
}
```

**Field rules:**

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `name` | string | NO | 2–255 characters |
| `status` | string | NO | `active`, `inactive`, `maintenance`, `offline` |
| `latitude` | number | NO | Between −90 and +90 |
| `longitude` | number | NO | Between −180 and +180 |
| `zone_id` | UUID | NO | Must reference an existing active zone |

**Response 200 OK:** Updated station object (same schema as Get Station).

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `403` | `FORBIDDEN` | Caller is not admin or station owner |
| `404` | `NOT_FOUND` | Station not found |

---

### 8.5 Delete Station (Soft)

```
DELETE /stations/{station_id}
```

**Purpose:** Soft-delete a station. Cascades soft-delete to all `user_stations` rows. Sets any assigned device's `station_id = NULL` and `status = unassigned`.

**Authorization:** Admin or station owner

**Response 204 No Content**

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `403` | `FORBIDDEN` | Caller is not admin or owner |
| `404` | `NOT_FOUND` | Station not found |

---

### 8.6 Get Station Events

```
GET /stations/{station_id}/events
```

**Purpose:** Return IoT events recorded at this station. Results are from MongoDB, sorted by `timestamp` descending.

**Authorization:** Admin or user assigned to this station

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `event_type` | string | Filter by event type |
| `from` | ISO 8601 | Start of time range (inclusive) |
| `to` | ISO 8601 | End of time range (inclusive) |
| `page` | integer | Default `1` |
| `page_size` | integer | Default `20`, max `100` |

**Response 200 OK:**
```json
{
  "items": [
    {
      "event_id": "019281af-bcde-7500-d0a1-b8c9d0e1f2a3",
      "event_type": "feeding_session",
      "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
      "device_id": "019281aa-cd34-7e00-af5c-c3d4e5f6a7b8",
      "animal_id": "019281b0-def0-7600-e1b2-c9d0e1f2a3b4",
      "rfid_tag": "RFID-00A1B2C3",
      "timestamp": "2026-06-13T09:45:00Z",
      "temperature": 18.4,
      "humidity": 72.1,
      "consumed_grams": 45.2,
      "media_url": null,
      "device_status": "ok",
      "ingested_at": "2026-06-13T09:45:02Z"
    }
  ],
  "total": 128,
  "page": 1,
  "page_size": 20,
  "pages": 7
}
```

---

### 8.7 Get Station Animals

```
GET /stations/{station_id}/animals
```

**Purpose:** Return all animals that have been observed at this station, derived from `iot_events` records that carry a resolved `animal_id` for this station. Results include the last observed timestamp and total visit count.

**Authorization:** Admin or user assigned to this station

**Response 200 OK:**
```json
{
  "items": [
    {
      "animal_id": "019281b0-def0-7600-e1b2-c9d0e1f2a3b4",
      "rfid_tag": "RFID-00A1B2C3",
      "species": "Tremarctos ornatus",
      "sex": "female",
      "is_identified": true,
      "visit_count": 14,
      "first_seen": "2026-05-01T08:12:00Z",
      "last_seen": "2026-06-13T09:45:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

---

## 9. Device Endpoints

### 9.1 Register Device

```
POST /devices
```

**Purpose:** Register a new physical ESP32 device. The device starts with `status = unassigned` and is not linked to any station.

**Authorization:** `admin`

**Request body:**
```json
{
  "serial_number": "WT-ESP32-0042",
  "name": "Feeder Alpha — North Trail"
}
```

**Field rules:**

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `serial_number` | string | YES | 3–100 characters; unique among active devices |
| `name` | string | NO | Max 255 characters |

**Response 201 Created:**
```json
{
  "id": "019281aa-cd34-7e00-af5c-c3d4e5f6a7b8",
  "serial_number": "WT-ESP32-0042",
  "name": "Feeder Alpha — North Trail",
  "station_id": null,
  "status": "unassigned",
  "firmware_version": null,
  "last_seen": null,
  "created_at": "2026-06-13T10:10:00Z",
  "updated_at": "2026-06-13T10:10:00Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `403` | `FORBIDDEN` | Caller is not admin |
| `409` | `SERIAL_EXISTS` | Serial number already registered |

---

### 9.2 List Devices

```
GET /devices
```

**Purpose:** List all active devices. Admins see all; non-admins see only devices assigned to stations they are assigned to.

**Authorization:** Authenticated (any role)

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by: `online`, `offline`, `unassigned` |
| `station_id` | UUID | Filter by assigned station |
| `page` | integer | Default `1` |
| `page_size` | integer | Default `20`, max `100` |

**Response 200 OK:** Paginated list of device objects.

---

### 9.3 Get Device

```
GET /devices/{device_id}
```

**Purpose:** Return a single device with full detail.

**Authorization:** Admin, or user assigned to the station this device is assigned to

**Response 200 OK:**
```json
{
  "id": "019281aa-cd34-7e00-af5c-c3d4e5f6a7b8",
  "serial_number": "WT-ESP32-0042",
  "name": "Feeder Alpha — North Trail",
  "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
  "station_code": "STA-001",
  "status": "online",
  "firmware_version": "1.4.2",
  "last_seen": "2026-06-13T10:28:00Z",
  "created_at": "2026-06-13T10:10:00Z",
  "updated_at": "2026-06-13T10:28:00Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `403` | `FORBIDDEN` | User not assigned to this device's station |
| `404` | `NOT_FOUND` | Device not found |

---

### 9.4 Update Device

```
PATCH /devices/{device_id}
```

**Purpose:** Update the device name. Admin only; `serial_number` and status fields cannot be changed via this endpoint.

**Authorization:** `admin`

**Request body:**
```json
{
  "name": "Feeder Alpha — North Trail (replaced)"
}
```

**Response 200 OK:** Updated device object.

---

### 9.5 Assign Device to Station

```
PATCH /devices/{device_id}/assign
```

**Purpose:** Link a device to a station. The station must have no currently active device. The device's status becomes `online`.

**Authorization:** `admin`

**Request body:**
```json
{
  "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0"
}
```

**Field rules:**

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `station_id` | UUID | YES | Must reference an existing active station that has no assigned device |

**Response 200 OK:**
```json
{
  "id": "019281aa-cd34-7e00-af5c-c3d4e5f6a7b8",
  "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
  "status": "online",
  "updated_at": "2026-06-13T10:15:00Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `400` | `DEVICE_ALREADY_ASSIGNED` | Device is already assigned to a station |
| `400` | `STATION_HAS_DEVICE` | Target station already has an active device |
| `403` | `FORBIDDEN` | Caller is not admin |
| `404` | `NOT_FOUND` | Device or station not found |

---

### 9.6 Unassign Device from Station

```
PATCH /devices/{device_id}/unassign
```

**Purpose:** Remove a device from its current station. Sets `station_id = NULL` and `status = unassigned`. The station's status is not automatically changed; an admin must update it separately.

**Authorization:** `admin`

**Request body:** None

**Response 200 OK:**
```json
{
  "id": "019281aa-cd34-7e00-af5c-c3d4e5f6a7b8",
  "station_id": null,
  "status": "unassigned",
  "updated_at": "2026-06-13T11:00:00Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `400` | `DEVICE_NOT_ASSIGNED` | Device is already unassigned |
| `403` | `FORBIDDEN` | Caller is not admin |
| `404` | `NOT_FOUND` | Device not found |

---

### 9.7 Get Device Telemetry

```
GET /devices/{device_id}/telemetry
```

**Purpose:** Return paginated historical telemetry heartbeat records for a device from MongoDB.

**Authorization:** Admin, or user assigned to this device's station

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `from` | ISO 8601 | Start of time range |
| `to` | ISO 8601 | End of time range |
| `page` | integer | Default `1` |
| `page_size` | integer | Default `20`, max `100` |

**Response 200 OK:**
```json
{
  "items": [
    {
      "telemetry_id": "019281b1-a1b2-7700-f2c3-d0e1f2a3b4c5",
      "device_id": "019281aa-cd34-7e00-af5c-c3d4e5f6a7b8",
      "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
      "timestamp": "2026-06-13T10:28:00Z",
      "firmware_version": "1.4.2",
      "wifi_signal": -58,
      "uptime": 86400,
      "free_memory": 142336,
      "battery_level": null,
      "device_status": "ok"
    }
  ],
  "total": 1440,
  "page": 1,
  "page_size": 20,
  "pages": 72
}
```

---

### 9.8 Get Device Latest Telemetry

```
GET /devices/{device_id}/telemetry/latest
```

**Purpose:** Return only the most recent telemetry heartbeat document for a device.

**Authorization:** Admin, or user assigned to this device's station

**Response 200 OK:** Single telemetry object (same schema as one item from paginated list).

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `404` | `NO_TELEMETRY` | No heartbeat has been received for this device yet |

---

### 9.9 Delete Device (Soft)

```
DELETE /devices/{device_id}
```

**Purpose:** Soft-delete a device. If the device is assigned to a station, it is automatically unassigned first.

**Authorization:** `admin`

**Response 204 No Content**

---

## 10. Animal Endpoints

### 10.1 Register Animal

```
POST /animals
```

**Purpose:** Register a new animal as a global platform record. No station assignment is required.

**Authorization:** `admin`, `researcher`, or `field_operator`

**Request body:**
```json
{
  "rfid_tag": "RFID-00A1B2C3",
  "species": "Tremarctos ornatus",
  "sex": "female",
  "estimated_age": "adult (~4–6 years)",
  "notes": "Distinctive white patch on left shoulder"
}
```

**Field rules:**

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `rfid_tag` | string | NO | Max 100 chars; unique among active animals when provided |
| `species` | string | YES | 2–255 characters, non-empty |
| `sex` | string | NO | `male`, `female`, `unknown` (default: `unknown`) |
| `estimated_age` | string | NO | Max 100 characters; free text |
| `notes` | string | NO | Free text, no length limit |

**Response 201 Created:**
```json
{
  "id": "019281b0-def0-7600-e1b2-c9d0e1f2a3b4",
  "rfid_tag": "RFID-00A1B2C3",
  "species": "Tremarctos ornatus",
  "sex": "female",
  "estimated_age": "adult (~4–6 years)",
  "is_identified": true,
  "notes": "Distinctive white patch on left shoulder",
  "created_at": "2026-06-13T10:20:00Z",
  "updated_at": "2026-06-13T10:20:00Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `409` | `RFID_TAG_EXISTS` | The RFID tag is already registered to another animal |
| `422` | — | Validation failure |

---

### 10.2 List Animals

```
GET /animals
```

**Purpose:** Return all active animal records.

**Authorization:** Authenticated (any role)

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `species` | string | Partial case-insensitive match |
| `sex` | string | `male`, `female`, `unknown` |
| `is_identified` | boolean | Filter tagged vs untagged animals |
| `page` | integer | Default `1` |
| `page_size` | integer | Default `20`, max `100` |

**Response 200 OK:** Paginated list of animal objects.

---

### 10.3 Get Animal

```
GET /animals/{animal_id}
```

**Purpose:** Return a single animal's full profile.

**Authorization:** Authenticated (any role)

**Response 200 OK:** Single animal object (same schema as Create Animal response).

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `404` | `NOT_FOUND` | Animal not found or soft-deleted |

---

### 10.4 Get Animal Station History

```
GET /animals/{animal_id}/stations
```

**Purpose:** Return the list of stations where this animal has been observed, derived from `iot_events` in MongoDB. Includes visit statistics per station.

**Authorization:** Authenticated (any role)

**Response 200 OK:**
```json
{
  "animal_id": "019281b0-def0-7600-e1b2-c9d0e1f2a3b4",
  "rfid_tag": "RFID-00A1B2C3",
  "stations": [
    {
      "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
      "station_code": "STA-001",
      "station_name": "North Ridge Feeder",
      "visit_count": 14,
      "total_consumed_grams": 632.8,
      "first_seen": "2026-05-01T08:12:00Z",
      "last_seen": "2026-06-13T09:45:00Z"
    }
  ]
}
```

---

### 10.5 Update Animal

```
PATCH /animals/{animal_id}
```

**Purpose:** Update one or more fields of an animal record.

**Authorization:** `admin`, `researcher`, or `field_operator`

**Request body (all fields optional):**
```json
{
  "rfid_tag": "RFID-00A1B2C4",
  "sex": "male",
  "estimated_age": "adult (~5–7 years)",
  "notes": "Re-tagged after field recapture"
}
```

**Response 200 OK:** Updated animal object.

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `404` | `NOT_FOUND` | Animal not found |
| `409` | `RFID_TAG_EXISTS` | New RFID tag already in use |

---

### 10.6 Delete Animal (Soft)

```
DELETE /animals/{animal_id}
```

**Purpose:** Soft-delete an animal record. Historical events referencing this `animal_id` in MongoDB are not affected.

**Authorization:** `admin`

**Response 204 No Content**

---

## 11. Food Endpoints

### 11.1 Create Food Type

```
POST /foods
```

**Purpose:** Add a new food type to the platform catalog.

**Authorization:** `admin` or `researcher`

**Request body:**
```json
{
  "name": "Mixed Seeds",
  "type": "seeds",
  "description": "A blend of sunflower, millet, and safflower seeds suitable for small and medium birds."
}
```

**Field rules:**

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `name` | string | YES | 2–255 chars; unique among active foods |
| `type` | string | YES | Max 100 chars (free text: `seeds`, `pellets`, `fruit`, etc.) |
| `description` | string | NO | Free text |

**Response 201 Created:**
```json
{
  "id": "019281ae-90ab-7400-cf90-a7b8c9d0e1f2",
  "name": "Mixed Seeds",
  "type": "seeds",
  "description": "A blend of sunflower, millet, and safflower seeds suitable for small and medium birds.",
  "created_at": "2026-06-13T10:25:00Z",
  "updated_at": "2026-06-13T10:25:00Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `409` | `FOOD_NAME_EXISTS` | Food type name already in use |

---

### 11.2 List Food Types

```
GET /foods
```

**Authorization:** Authenticated (any role)

**Response 200 OK:** Paginated list of food objects.

---

### 11.3 Get Food Type

```
GET /foods/{food_id}
```

**Authorization:** Authenticated (any role)

**Response 200 OK:** Single food object.

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `404` | `NOT_FOUND` | Food type not found |

---

### 11.4 Update Food Type

```
PATCH /foods/{food_id}
```

**Authorization:** `admin` or `researcher`

**Request body (all fields optional):**
```json
{
  "name": "Premium Mixed Seeds",
  "description": "Upgraded blend with added nyjer seeds."
}
```

**Response 200 OK:** Updated food object.

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `404` | `NOT_FOUND` | Food type not found |
| `409` | `FOOD_NAME_EXISTS` | Updated name conflicts with existing active food |

---

### 11.5 Delete Food Type (Soft)

```
DELETE /foods/{food_id}
```

**Purpose:** Soft-delete a food type. Cannot delete if it is the active food for any station.

**Authorization:** `admin`

**Response 204 No Content**

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `400` | `FOOD_IN_USE` | Food is set as the active configuration for one or more stations |
| `404` | `NOT_FOUND` | Food type not found |

---

## 12. Station Food Endpoints

### 12.1 Add Food to Station

```
POST /stations/{station_id}/foods
```

**Purpose:** Associate a food type with a station. If `active = true`, any existing active food configuration for the station is first deactivated.

**Authorization:** Admin or station owner

**Request body:**
```json
{
  "food_id": "019281ae-90ab-7400-cf90-a7b8c9d0e1f2",
  "active": true
}
```

**Field rules:**

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `food_id` | UUID | YES | Must reference an existing active food type |
| `active` | boolean | NO | Default `true`. If `true`, deactivates any current active food for this station |

**Response 201 Created:**
```json
{
  "id": "019281ad-5678-7300-be8f-f6a7b8c9d0e1",
  "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
  "food_id": "019281ae-90ab-7400-cf90-a7b8c9d0e1f2",
  "food_name": "Mixed Seeds",
  "active": true,
  "created_at": "2026-06-13T10:30:00Z",
  "updated_at": "2026-06-13T10:30:00Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `404` | `NOT_FOUND` | Station or food type not found |
| `409` | `FOOD_ALREADY_ASSOCIATED` | This food is already associated with this station |

---

### 12.2 List Station Foods

```
GET /stations/{station_id}/foods
```

**Purpose:** Return all food associations for a station (both active and inactive).

**Authorization:** Admin or user assigned to this station

**Response 200 OK:**
```json
{
  "items": [
    {
      "id": "019281ad-5678-7300-be8f-f6a7b8c9d0e1",
      "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
      "food_id": "019281ae-90ab-7400-cf90-a7b8c9d0e1f2",
      "food_name": "Mixed Seeds",
      "food_type": "seeds",
      "active": true,
      "created_at": "2026-06-13T10:30:00Z",
      "updated_at": "2026-06-13T10:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

---

### 12.3 Set Active Food

```
PATCH /stations/{station_id}/foods/{station_food_id}/activate
```

**Purpose:** Mark a specific station-food association as active. Deactivates any other currently active association for the same station.

**Authorization:** Admin or station owner

**Request body:** None

**Response 200 OK:** Updated station food object with `active: true`.

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `400` | `ALREADY_ACTIVE` | This association is already active |
| `404` | `NOT_FOUND` | Station or station-food association not found |

---

### 12.4 Deactivate Station Food

```
PATCH /stations/{station_id}/foods/{station_food_id}/deactivate
```

**Purpose:** Mark a station-food association as inactive.

**Authorization:** Admin or station owner

**Request body:** None

**Response 200 OK:** Updated station food object with `active: false`.

---

### 12.5 Remove Food from Station

```
DELETE /stations/{station_id}/foods/{station_food_id}
```

**Purpose:** Hard-delete the station-food association. Cannot remove the active food configuration.

**Authorization:** Admin or station owner

**Response 204 No Content**

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `400` | `CANNOT_REMOVE_ACTIVE` | Cannot remove the currently active food — deactivate it first |
| `404` | `NOT_FOUND` | Association not found |

---

## 13. User-Station Assignment Endpoints

### 13.1 Assign User to Station

```
POST /stations/{station_id}/members
```

**Purpose:** Grant a user access to a station with a specific role. Only the station owner or an admin may perform this action.

**Authorization:** Admin or station owner

**Request body:**
```json
{
  "user_id": "019281b2-c3d4-7800-a3b4-e1f2a3b4c5d6",
  "role": "field_operator"
}
```

**Field rules:**

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `user_id` | UUID | YES | Must reference an active user |
| `role` | string | YES | `researcher` or `field_operator` (cannot assign `owner` via this endpoint) |

**Response 201 Created:**
```json
{
  "id": "019281b3-d4e5-7900-b4c5-f2a3b4c5d6e7",
  "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
  "user_id": "019281b2-c3d4-7800-a3b4-e1f2a3b4c5d6",
  "user_name": "Carlos Rivera",
  "user_email": "carlos@example.com",
  "role": "field_operator",
  "created_at": "2026-06-13T10:35:00Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `400` | `CANNOT_ASSIGN_OWNER` | Role `owner` cannot be assigned via this endpoint |
| `403` | `FORBIDDEN` | Caller is not admin or station owner |
| `404` | `NOT_FOUND` | Station or user not found |
| `409` | `ALREADY_MEMBER` | User already has an active assignment for this station |

---

### 13.2 List Station Members

```
GET /stations/{station_id}/members
```

**Purpose:** List all users currently assigned to this station.

**Authorization:** Admin or user assigned to this station

**Response 200 OK:**
```json
{
  "items": [
    {
      "id": "019281b3-d4e5-7900-b4c5-f2a3b4c5d6e7",
      "user_id": "019281a8-5e2c-7f00-b3d4-a1e2f3c4d5e6",
      "user_name": "Ana Martínez",
      "user_email": "ana@example.com",
      "role": "owner",
      "created_at": "2026-06-13T10:05:00Z"
    },
    {
      "id": "019281b3-d4e5-7900-b4c5-f2a3b4c5d6e7",
      "user_id": "019281b2-c3d4-7800-a3b4-e1f2a3b4c5d6",
      "user_name": "Carlos Rivera",
      "user_email": "carlos@example.com",
      "role": "field_operator",
      "created_at": "2026-06-13T10:35:00Z"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

---

### 13.3 Update Member Role

```
PATCH /stations/{station_id}/members/{user_station_id}
```

**Purpose:** Change a member's role in this station. Cannot change the role of the station owner.

**Authorization:** Admin or station owner

**Request body:**
```json
{
  "role": "researcher"
}
```

**Field rules:**

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `role` | string | YES | `researcher` or `field_operator` |

**Response 200 OK:** Updated member record.

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `400` | `CANNOT_CHANGE_OWNER` | Cannot change role of the station owner |
| `403` | `FORBIDDEN` | Caller is not admin or station owner |
| `404` | `NOT_FOUND` | Assignment not found |

---

### 13.4 Remove Member from Station

```
DELETE /stations/{station_id}/members/{user_station_id}
```

**Purpose:** Soft-delete the user-station assignment, revoking that user's access to the station. Cannot remove the station owner.

**Authorization:** Admin or station owner

**Response 204 No Content**

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `400` | `CANNOT_REMOVE_OWNER` | Cannot remove the station owner via this endpoint — delete the station instead |
| `403` | `FORBIDDEN` | Caller is not admin or station owner |
| `404` | `NOT_FOUND` | Assignment not found |

---

## 14. IoT Event Endpoints

### 14.1 List Events

```
GET /events
```

**Purpose:** Query IoT events across all accessible stations. Data is read from MongoDB `iot_events`.

**Authorization:** Authenticated. Non-admins see only events for stations they are assigned to.

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `station_id` | UUID | Filter by station |
| `device_id` | UUID | Filter by device |
| `animal_id` | UUID | Filter by resolved animal |
| `event_type` | string | `feeding_session`, `presence_detected`, `rfid_read`, `sensor_reading` |
| `from` | ISO 8601 | Start of time range (inclusive) |
| `to` | ISO 8601 | End of time range (inclusive) |
| `page` | integer | Default `1` |
| `page_size` | integer | Default `20`, max `100` |

**Response 200 OK:**
```json
{
  "items": [
    {
      "event_id": "019281af-bcde-7500-d0a1-b8c9d0e1f2a3",
      "event_type": "feeding_session",
      "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
      "station_code": "STA-001",
      "device_id": "019281aa-cd34-7e00-af5c-c3d4e5f6a7b8",
      "animal_id": "019281b0-def0-7600-e1b2-c9d0e1f2a3b4",
      "rfid_tag": "RFID-00A1B2C3",
      "timestamp": "2026-06-13T09:45:00Z",
      "temperature": 18.4,
      "humidity": 72.1,
      "initial_weight": 500.0,
      "final_weight": 454.8,
      "consumed_grams": 45.2,
      "latitude": 4.7125,
      "longitude": -74.0710,
      "media_url": null,
      "device_status": "ok",
      "ingested_at": "2026-06-13T09:45:02Z"
    }
  ],
  "total": 1284,
  "page": 1,
  "page_size": 20,
  "pages": 65
}
```

---

### 14.2 Get Event

```
GET /events/{event_id}
```

**Purpose:** Return a single IoT event document by `event_id`. Data is read from MongoDB.

**Authorization:** Admin or user assigned to the event's station

**Response 200 OK:** Single event object (same schema as list item).

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `403` | `FORBIDDEN` | User not assigned to the event's station |
| `404` | `NOT_FOUND` | Event not found in MongoDB |

---

## 15. Geoportal Endpoints

All geoportal endpoints are read-only. They combine data from PostgreSQL and MongoDB to build the responses for the Leaflet-based map view.

### 15.1 Get Station Map Data

```
GET /geoportal/stations
```

**Purpose:** Return all active stations as a GeoJSON FeatureCollection enriched with the latest event summary per station. Used to render markers on the Leaflet map.

**Authorization:** Authenticated (any role). Non-admins receive only stations they are assigned to.

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `zone_id` | UUID | Filter markers by zone |
| `status` | string | Filter by station status |

**Response 200 OK:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-74.0710, 4.7125]
      },
      "properties": {
        "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
        "code": "STA-001",
        "name": "North Ridge Feeder",
        "zone_id": "019281ab-ef56-7100-8c6d-d4e5f6a7b8c9",
        "zone_name": "Andean Forest Reserve — Block A",
        "status": "active",
        "device_status": "online",
        "device_last_seen": "2026-06-13T10:28:00Z",
        "last_event_at": "2026-06-13T09:45:00Z",
        "total_events_today": 12
      }
    }
  ],
  "generated_at": "2026-06-13T10:30:00Z"
}
```

---

### 15.2 Get Activity Heatmap

```
GET /geoportal/heatmap/activity
```

**Purpose:** Return weighted data points for a Leaflet heatmap layer representing event frequency per location.

**Authorization:** Authenticated (any role)

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `zone_id` | UUID | Restrict to stations in a specific zone |
| `from` | ISO 8601 | Start of aggregation window (default: last 7 days) |
| `to` | ISO 8601 | End of aggregation window |

**Response 200 OK:**
```json
{
  "layer": "activity",
  "from": "2026-06-06T00:00:00Z",
  "to": "2026-06-13T00:00:00Z",
  "points": [
    {
      "latitude": 4.7125,
      "longitude": -74.0710,
      "weight": 128,
      "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
      "station_code": "STA-001"
    }
  ]
}
```

---

### 15.3 Get Consumption Heatmap

```
GET /geoportal/heatmap/consumption
```

**Purpose:** Return weighted data points where the weight represents total grams consumed per station location.

**Authorization:** Authenticated (any role)

**Query parameters:** Same as Activity Heatmap.

**Response 200 OK:**
```json
{
  "layer": "consumption",
  "from": "2026-06-06T00:00:00Z",
  "to": "2026-06-13T00:00:00Z",
  "points": [
    {
      "latitude": 4.7125,
      "longitude": -74.0710,
      "weight": 3240.5,
      "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
      "station_code": "STA-001"
    }
  ]
}
```

---

### 15.4 Get Environmental Readings

```
GET /geoportal/env-readings
```

**Purpose:** Return the most recent temperature and humidity reading per station, formatted for map overlay tooltips.

**Authorization:** Authenticated (any role)

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `zone_id` | UUID | Filter by zone |

**Response 200 OK:**
```json
{
  "readings": [
    {
      "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
      "station_code": "STA-001",
      "latitude": 4.7125,
      "longitude": -74.0710,
      "temperature": 18.4,
      "humidity": 72.1,
      "recorded_at": "2026-06-13T09:45:00Z"
    }
  ],
  "generated_at": "2026-06-13T10:30:00Z"
}
```

---

### 15.5 Get Events by Zone

```
GET /geoportal/events-by-zone
```

**Purpose:** Return recent events grouped by zone for the geoportal sidebar panel.

**Authorization:** Authenticated (any role)

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `zone_id` | UUID | Return only one zone |
| `limit_per_zone` | integer | Max events per zone (default `5`, max `20`) |

**Response 200 OK:**
```json
{
  "zones": [
    {
      "zone_id": "019281ab-ef56-7100-8c6d-d4e5f6a7b8c9",
      "zone_name": "Andean Forest Reserve — Block A",
      "recent_events": [
        {
          "event_id": "019281af-bcde-7500-d0a1-b8c9d0e1f2a3",
          "station_code": "STA-001",
          "event_type": "feeding_session",
          "timestamp": "2026-06-13T09:45:00Z",
          "consumed_grams": 45.2,
          "animal_identified": true
        }
      ]
    }
  ]
}
```

---

## 16. Analytics and Dashboard Endpoints

### 16.1 Get KPI Summary

```
GET /analytics/kpi
```

**Purpose:** Return the key performance indicator values displayed on the main dashboard cards.

**Authorization:** Authenticated (any role). Non-admins receive KPIs scoped to their assigned stations only.

**Response 200 OK:**
```json
{
  "stations": {
    "total": 12,
    "active": 9,
    "inactive": 1,
    "maintenance": 1,
    "offline": 1
  },
  "devices": {
    "total": 12,
    "online": 9,
    "offline": 2,
    "unassigned": 1
  },
  "events": {
    "total_all_time": 18432,
    "last_24h": 312,
    "last_7d": 1840
  },
  "animals": {
    "total_registered": 38,
    "identified": 25,
    "unidentified": 13
  },
  "alerts": {
    "open": 4
  },
  "generated_at": "2026-06-13T10:30:00Z"
}
```

---

### 16.2 Get Consumption Time Series

```
GET /analytics/consumption
```

**Purpose:** Return food consumption aggregated over time for chart rendering.

**Authorization:** Authenticated (any role)

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `from` | ISO 8601 | Start of range (default: 30 days ago) |
| `to` | ISO 8601 | End of range (default: now) |
| `granularity` | string | `day`, `week`, `month` (default: `day`) |
| `station_id` | UUID | Scope to a single station |
| `zone_id` | UUID | Scope to a zone |

**Response 200 OK:**
```json
{
  "metric": "consumption_grams",
  "granularity": "day",
  "from": "2026-05-14T00:00:00Z",
  "to": "2026-06-13T00:00:00Z",
  "series": [
    { "period": "2026-06-13", "value": 1240.5 },
    { "period": "2026-06-12", "value": 1380.0 },
    { "period": "2026-06-11", "value": 960.3 }
  ]
}
```

---

### 16.3 Get Visit Time Series

```
GET /analytics/visits
```

**Purpose:** Return animal visit (feeding event) counts aggregated over time.

**Authorization:** Authenticated (any role)

**Query parameters:** Same as `/analytics/consumption`.

**Response 200 OK:**
```json
{
  "metric": "visit_count",
  "granularity": "day",
  "from": "2026-05-14T00:00:00Z",
  "to": "2026-06-13T00:00:00Z",
  "series": [
    { "period": "2026-06-13", "value": 28 },
    { "period": "2026-06-12", "value": 31 },
    { "period": "2026-06-11", "value": 22 }
  ]
}
```

---

### 16.4 Get Consumption by Zone

```
GET /analytics/consumption-by-zone
```

**Purpose:** Return total food consumption grouped by zone for bar chart rendering.

**Authorization:** Authenticated (any role)

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `from` | ISO 8601 | Start of range (default: last 30 days) |
| `to` | ISO 8601 | End of range |

**Response 200 OK:**
```json
{
  "from": "2026-05-14T00:00:00Z",
  "to": "2026-06-13T00:00:00Z",
  "zones": [
    {
      "zone_id": "019281ab-ef56-7100-8c6d-d4e5f6a7b8c9",
      "zone_name": "Andean Forest Reserve — Block A",
      "total_consumed_grams": 18432.6,
      "station_count": 4,
      "event_count": 842
    }
  ]
}
```

---

### 16.5 Get Events by Station

```
GET /analytics/events-by-station
```

**Purpose:** Return event counts grouped by station for bar chart rendering.

**Authorization:** Authenticated (any role)

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `zone_id` | UUID | Filter to stations in a zone |
| `from` | ISO 8601 | Start of range |
| `to` | ISO 8601 | End of range |

**Response 200 OK:**
```json
{
  "stations": [
    {
      "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
      "station_code": "STA-001",
      "station_name": "North Ridge Feeder",
      "event_count": 312,
      "feeding_sessions": 280,
      "identified_visits": 198
    }
  ]
}
```

---

### 16.6 Get Environmental Data

```
GET /analytics/env
```

**Purpose:** Return average temperature and humidity readings per station or zone for comparison chart.

**Authorization:** Authenticated (any role)

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `zone_id` | UUID | Scope to a zone |
| `from` | ISO 8601 | Start of range (default: last 7 days) |
| `to` | ISO 8601 | End of range |

**Response 200 OK:**
```json
{
  "from": "2026-06-06T00:00:00Z",
  "to": "2026-06-13T00:00:00Z",
  "stations": [
    {
      "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
      "station_code": "STA-001",
      "avg_temperature": 17.8,
      "min_temperature": 11.2,
      "max_temperature": 23.4,
      "avg_humidity": 74.5,
      "reading_count": 336
    }
  ]
}
```

---

## 17. Alert Endpoints

### 17.1 List Alerts

```
GET /alerts
```

**Purpose:** Return operational alerts. Non-admins see only alerts for stations they are assigned to.

**Authorization:** Authenticated (any role)

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `station_id` | UUID | Filter by station |
| `device_id` | UUID | Filter by device |
| `alert_type` | string | Filter by alert type (see Alert Types table in SDD-01 §14) |
| `status` | string | `open`, `resolved` (default: `open`) |
| `from` | ISO 8601 | Filter by `created_at` start |
| `to` | ISO 8601 | Filter by `created_at` end |
| `page` | integer | Default `1` |
| `page_size` | integer | Default `20`, max `100` |

**Response 200 OK:**
```json
{
  "items": [
    {
      "alert_id": "019281b4-e5f6-7a00-c5d6-a3b4c5d6e7f8",
      "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
      "station_code": "STA-001",
      "station_name": "North Ridge Feeder",
      "device_id": "019281aa-cd34-7e00-af5c-c3d4e5f6a7b8",
      "alert_type": "sensor_failure",
      "message": "Temperature sensor reported an error value during feeding session.",
      "status": "open",
      "created_at": "2026-06-13T08:12:00Z",
      "resolved_at": null
    }
  ],
  "total": 4,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

---

### 17.2 Get Alert

```
GET /alerts/{alert_id}
```

**Purpose:** Return a single alert document.

**Authorization:** Admin or user assigned to the alert's station

**Response 200 OK:** Single alert object (same schema as list item).

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `403` | `FORBIDDEN` | User not assigned to the alert's station |
| `404` | `NOT_FOUND` | Alert not found |

---

### 17.3 Resolve Alert

```
PATCH /alerts/{alert_id}/resolve
```

**Purpose:** Mark an alert as resolved. Sets `status = resolved` and `resolved_at = now()`.

**Authorization:** Admin, station owner, or user assigned to the alert's station with role `field_operator` or above

**Request body:** None

**Response 200 OK:**
```json
{
  "alert_id": "019281b4-e5f6-7a00-c5d6-a3b4c5d6e7f8",
  "status": "resolved",
  "resolved_at": "2026-06-13T11:00:00Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `400` | `ALREADY_RESOLVED` | Alert is already in resolved state |
| `403` | `FORBIDDEN` | User not assigned to this station |
| `404` | `NOT_FOUND` | Alert not found |

---

## 18. Media Endpoints

### 18.1 Upload Media File

```
POST /media/upload
```

**Purpose:** Upload a photo or video captured by an ESP32 device or submitted via the web UI. The binary file is stored in MinIO; metadata is stored in MongoDB `media_metadata`.

**Authorization:** Authenticated (any role with access to the station)

**Request body:** `multipart/form-data`

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `file` | binary | YES | JPEG, PNG, MP4, or AVI; max 10 MB |
| `event_id` | string (UUID) | YES | Must reference an existing `iot_events` document |
| `station_id` | string (UUID) | YES | Must reference an existing active station the caller can access |
| `device_id` | string (UUID) | YES | Must reference an existing active device |
| `media_type` | string | YES | `photo` or `video` |
| `captured_at` | ISO 8601 | YES | Timestamp of capture from the device clock |

**Response 201 Created:**
```json
{
  "media_id": "019281b5-f6a7-7b00-d6e7-b4c5d6e7f8a9",
  "event_id": "019281af-bcde-7500-d0a1-b8c9d0e1f2a3",
  "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
  "device_id": "019281aa-cd34-7e00-af5c-c3d4e5f6a7b8",
  "media_type": "photo",
  "object_key": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0/2026/06/019281aa-cd34-7e00-af5c-c3d4e5f6a7b8_2026-06-13T09-45-00Z_photo.jpg",
  "url": "http://minio:9000/wildtrack-media/019281ac-1234.../photo.jpg",
  "file_size_bytes": 2457600,
  "captured_at": "2026-06-13T09:45:00Z",
  "ingested_at": "2026-06-13T09:45:03Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `400` | `EVENT_NOT_FOUND` | `event_id` does not reference an existing IoT event |
| `403` | `FORBIDDEN` | User not assigned to the given station |
| `413` | `PAYLOAD_TOO_LARGE` | File exceeds 10 MB |
| `415` | `UNSUPPORTED_MEDIA_TYPE` | File MIME type is not `image/jpeg`, `image/png`, `video/mp4`, or `video/x-msvideo` |

---

### 18.2 Get Media Metadata

```
GET /media/{event_id}
```

**Purpose:** Return the metadata record for the media file associated with a given event.

**Authorization:** Admin or user assigned to the event's station

**Response 200 OK:**
```json
{
  "media_id": "019281b5-f6a7-7b00-d6e7-b4c5d6e7f8a9",
  "event_id": "019281af-bcde-7500-d0a1-b8c9d0e1f2a3",
  "station_id": "019281ac-1234-7200-ad7e-e5f6a7b8c9d0",
  "device_id": "019281aa-cd34-7e00-af5c-c3d4e5f6a7b8",
  "media_type": "photo",
  "object_key": "019281ac-1234-7200.../photo.jpg",
  "file_size_bytes": 2457600,
  "captured_at": "2026-06-13T09:45:00Z",
  "ingested_at": "2026-06-13T09:45:03Z"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `403` | `FORBIDDEN` | User not assigned to the event's station |
| `404` | `NOT_FOUND` | No media associated with this event |

---

### 18.3 Get Pre-Signed Access URL

```
GET /media/{event_id}/presigned
```

**Purpose:** Generate a time-limited pre-signed MinIO URL that grants direct read access to the media object. The URL is valid for 15 minutes (configurable). The frontend uses this URL to load the image or video directly from MinIO without routing the binary through the backend.

**Authorization:** Admin or user assigned to the event's station

**Response 200 OK:**
```json
{
  "media_id": "019281b5-f6a7-7b00-d6e7-b4c5d6e7f8a9",
  "event_id": "019281af-bcde-7500-d0a1-b8c9d0e1f2a3",
  "presigned_url": "http://localhost:9000/wildtrack-media/019281ac.../photo.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...&X-Amz-Expires=900&X-Amz-Signature=...",
  "expires_in": 900,
  "expires_at": "2026-06-13T10:45:00Z",
  "media_type": "photo"
}
```

**Error responses:**

| Code | Code String | Condition |
|------|-------------|-----------|
| `403` | `FORBIDDEN` | User not assigned to the event's station |
| `404` | `NOT_FOUND` | No media found for this event |
| `502` | `MINIO_UNAVAILABLE` | MinIO service did not respond during pre-signed URL generation |

---

*End of SDD-04 API Contract — v1.0.0*
