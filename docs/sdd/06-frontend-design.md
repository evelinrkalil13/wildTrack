# WildTrack Platform — Frontend Design

**Document:** SDD-06 Frontend Design  
**Version:** 2.0.0  
**Date:** 2026-07-07  
**Status:** Approved  
**References:** SDD-01 Requirements, SDD-02 Architecture, SDD-04 API Contract, SDD-08 Device IoT Design

---

## Table of Contents

1. [Objetivo y principios](#1-objetivo-y-principios)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Estructura de carpetas](#3-estructura-de-carpetas)
4. [Layout y navegación](#4-layout-y-navegación)
5. [Autenticación y autorización](#5-autenticación-y-autorización)
6. [Cliente HTTP y estado del servidor](#6-cliente-http-y-estado-del-servidor)
7. [Features](#7-features)
8. [Geoportal](#8-geoportal)
9. [Dashboard](#9-dashboard)
10. [Formularios](#10-formularios)
11. [Manejo de errores y carga](#11-manejo-de-errores-y-carga)
12. [Tema visual](#12-tema-visual)
13. [Integración del Geoportal existente](#13-integración-del-geoportal-existente)
14. [Variables de entorno](#14-variables-de-entorno)

---

## 1. Objetivo y principios

El frontend de WildTrack es una **Single Page Application (SPA)** que permite administrar el sistema completo de monitoreo de fauna.

**Principios no negociables:**

- El frontend **no contiene lógica de negocio**. Toda validación de dominio, permisos y reglas viven en el backend.
- El frontend **solo consume la API REST** del backend (`/api/v1`). Nunca accede directamente a PostgreSQL, MongoDB, MinIO ni MQTT.
- El estado del servidor vive en **TanStack Query**. No se copian datos de la API a `useState`.
- Las reglas de autorización del frontend son **solo UI** — el backend siempre es la autoridad real.

---

## 2. Stack tecnológico

| Concerní | Tecnología | Versión objetivo |
|----------|-----------|-----------------|
| Framework | React | 18 |
| Bundler | Vite | 5 |
| Lenguaje | TypeScript | 5 |
| Router | React Router | 6 |
| Estado servidor | TanStack Query (React Query) | 5 |
| HTTP | Axios | 1 |
| UI components | Material UI (MUI) | 5 |
| Mapa | Leaflet + React Leaflet | 4 |
| Gráficas | Recharts | 2 |
| Formularios | React Hook Form | 7 |
| Validación esquemas | Zod | 3 |
| Tests | Vitest + Testing Library | — |

**Decisiones clave:**

- **MUI** provee el sistema de componentes base (Button, TextField, Table, Dialog, etc.). No se construye un sistema de diseño desde cero en el MVP.
- **TanStack Query** es la única fuente de verdad para datos del servidor. No hay Redux ni Zustand.
- **Zod** define los schemas de validación de formularios y también valida las respuestas de la API en desarrollo.
- **React Router v6** maneja toda la navegación con code splitting por ruta via `React.lazy`.

---

## 3. Estructura de carpetas

```
frontend/
├── public/
├── src/
│   ├── api/
│   │   ├── client.ts              # Instancia Axios con interceptores
│   │   └── types/
│   │       ├── common.types.ts    # PaginatedList, ApiError
│   │       └── enums.ts           # Enums que espeja el backend
│   ├── components/                # Componentes reutilizables globales
│   │   ├── DataTable/
│   │   ├── ConfirmDialog/
│   │   ├── StatusBadge/
│   │   ├── EmptyState/
│   │   └── PageHeader/
│   ├── features/
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── zones/
│   │   ├── stations/
│   │   ├── devices/
│   │   ├── animals/
│   │   ├── foods/
│   │   ├── alerts/
│   │   ├── telemetry/
│   │   ├── analytics/
│   │   └── geoportal/
│   ├── hooks/
│   │   ├── useCurrentUser.ts
│   │   └── usePermissions.ts
│   ├── layouts/
│   │   ├── AppLayout.tsx          # TopNav + Sidebar + Outlet
│   │   ├── AuthLayout.tsx         # Centrado, sin nav
│   │   └── MapLayout.tsx          # Full-screen Leaflet
│   ├── pages/                     # Componentes de ruta (lazy)
│   ├── router/
│   │   ├── routes.tsx             # createBrowserRouter
│   │   └── guards.tsx             # RequireAuth, RequireRole
│   ├── store/
│   │   └── auth.context.tsx       # JWT + user actual
│   ├── theme/
│   │   └── theme.ts               # MUI createTheme — paleta verde
│   ├── types/                     # Tipos TypeScript compartidos
│   ├── utils/                     # Funciones puras (fecha, formato)
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── vite.config.ts
├── tsconfig.json
└── .env.example
```

### Estructura de cada feature

Cada feature sigue la misma estructura interna:

```
features/stations/
├── api/
│   ├── stations.api.ts        # Funciones Axios tipadas
│   └── stations.types.ts      # Tipos request/response (espeja SDD-04)
├── hooks/
│   ├── useStations.ts         # useQuery list
│   ├── useStation.ts          # useQuery detail
│   └── useStationMutations.ts # useMutation create/update/delete
├── components/
│   ├── StationTable/
│   ├── StationForm/
│   └── StationStatusBadge/
└── index.ts
```

---

## 4. Layout y navegación

### Layout principal (AppLayout)

```
┌─────────────────────────────────────────────────────┐
│ TopNav  [Logo]  [Alertas abiertas 🔔]  [Avatar ▾]  │  ← fijo
├───────────┬─────────────────────────────────────────┤
│           │                                         │
│  Sidebar  │  <Outlet />                             │  ← scrollable
│  (fijo)   │  Contenido de la página                 │
│           │                                         │
└───────────┴─────────────────────────────────────────┘
```

### Navegación del Sidebar

| Enlace | Ruta | Roles |
|--------|------|-------|
| Dashboard | `/app/dashboard` | todos |
| Geoportal | `/app/map` | todos |
| Estaciones | `/app/stations` | todos |
| Animales | `/app/animals` | todos |
| Alertas | `/app/alerts` | todos |
| Dispositivos | `/app/devices` | admin |
| Zonas | `/app/zones` | admin, researcher |
| Alimentos | `/app/foods` | admin, researcher |
| Usuarios | `/app/users` | admin |

### Árbol de rutas

```
/
├── /auth/login
├── /auth/register
└── /app                         ← RequireAuth
    ├── /app/dashboard
    ├── /app/map
    ├── /app/stations
    │   ├── /app/stations/new
    │   ├── /app/stations/:id
    │   ├── /app/stations/:id/edit
    │   ├── /app/stations/:id/members
    │   ├── /app/stations/:id/foods
    │   └── /app/stations/:id/events
    ├── /app/devices
    │   ├── /app/devices/new       ← RequireRole admin
    │   └── /app/devices/:id
    ├── /app/zones                 ← RequireRole admin,researcher
    ├── /app/animals
    │   ├── /app/animals/new
    │   └── /app/animals/:id
    ├── /app/foods                 ← RequireRole admin,researcher
    ├── /app/alerts
    ├── /app/users                 ← RequireRole admin
    └── /app/profile
```

Cada componente de página es importado con `React.lazy()` para code splitting automático.

---

## 5. Autenticación y autorización

### Flujo de login

```
Usuario → POST /auth/login → { access_token, user }
       → AuthContext.setAuth(token, user)
       → localStorage.setItem("wt_token", token)
       → navigate("/app/dashboard")
```

### Persistencia del token

- Token almacenado en `localStorage` bajo clave `wt_token`.
- Al cargar la app, `AuthProvider` lee el token, verifica expiración del payload JWT, y restaura la sesión si es válido.
- Para producción se recomienda migrar a HttpOnly cookie (ver ADR-010 en la versión anterior del documento).

### Interceptor de Axios

El interceptor de request inyecta `Authorization: Bearer <token>` en cada request. El interceptor de response captura `401` → llama `clearAuth()` → redirige a `/auth/login`.

### Guards de ruta

- **`RequireAuth`**: verifica que exista token válido. Si no, redirige a `/auth/login?returnTo=<ruta actual>`.
- **`RequireRole`**: recibe lista de roles permitidos. Si el usuario no tiene el rol, renderiza `ForbiddenPage`.

### Adaptación de UI por rol

El frontend adapta la UI al rol del usuario — qué botones se muestran, qué enlaces aparecen en el sidebar. **Esto es solo UI**, el backend rechaza cualquier acción no autorizada con `403`.

| Acción | admin | researcher | field_operator |
|--------|-------|-----------|----------------|
| Crear estación | ✓ | ✓ | — |
| Asignar dispositivo | ✓ | — | — |
| Registrar animal | ✓ | ✓ | ✓ |
| Resolver alerta | ✓ | ✓ | ✓ |
| Gestionar usuarios | ✓ | — | — |

---

## 6. Cliente HTTP y estado del servidor

### Instancia Axios (`api/client.ts`)

- `baseURL`: leída de `VITE_API_BASE_URL`
- Request interceptor: inyecta `Authorization` header
- Response interceptor: normaliza errores a `ApiError { status, code, message }`

### TanStack Query

Configuración global del `QueryClient`:

| Opción | Valor |
|--------|-------|
| `staleTime` | 30 segundos |
| `gcTime` | 5 minutos |
| `retry` | 1 (no reintentar en 4xx) |
| `refetchOnWindowFocus` | true |

**Convención de query keys:**

```typescript
// features/stations/hooks/keys.ts
export const stationKeys = {
  all:    () => ["stations"] as const,
  list:   (f: StationFilters) => ["stations", "list", f] as const,
  detail: (id: string) => ["stations", "detail", id] as const,
}
```

**Después de cada mutación**, se invalida la jerarquía de keys con `queryClient.invalidateQueries(stationKeys.all())` para que las listas se refresquen automáticamente.

**Paginación en URL**: `page` y `page_size` se almacenan como query params de la URL via `useSearchParams` — preserva estado en navegación y permite bookmark.

---

## 7. Features

### 7.1 Auth
- Página de login con validación Zod
- Página de registro
- No auto-login tras registro — redirige a login con toast de confirmación

### 7.2 Dashboard
Tarjetas KPI y gráficas. Detalle en [§9](#9-dashboard).

### 7.3 Zonas
- Tabla con nombre, municipio, país, coordenadas
- CRUD completo
- Formulario con campos de coordenadas manuales (no mapa en MVP)

### 7.4 Estaciones
- Tabla con código, nombre, zona, estado
- CRUD con formulario de dos pasos:
  - Paso 1: nombre, código, zona
  - Paso 2: ubicación con `MapPicker` (Leaflet con marcador arrastrable + botón "usar mi ubicación")
- Vista de detalle con pestañas: **Info / Eventos / Animales / Alimentos / Miembros**
- Filtros: status, zona

### 7.5 Dispositivos
- Tabla con serial, nombre, estación asignada, estado online/offline, último heartbeat
- CRUD
- Asignar / desasignar estación
- Indicador visual del estado del dispositivo (verde: online, rojo: offline, gris: sin asignar)

### 7.6 Animales
- Tabla con especie, sexo, RFID tag, estación, estado de identificación
- CRUD
- Historial de visitas (eventos IoT donde el RFID matcheó a este animal)
- Filtros: estación, identificado/no identificado

### 7.7 Alimentos
- Tabla con nombre, tipo, descripción
- CRUD
- Activar / desactivar alimento por estación (via `station_foods`)

### 7.8 Alertas
- Tabla de alertas abiertas con tipo, estación, dispositivo, fecha
- Resolver alerta (PATCH)
- Historial de alertas resueltas
- Badge en el TopNav con el conteo de alertas abiertas

### 7.9 Telemetría
- Vista por dispositivo con últimas lecturas de temperatura y humedad
- Consumida desde los documentos de telemetría de MongoDB via la API

### 7.10 Analytics
Gráficas de analítica. Detalle en [§9](#9-dashboard).

### 7.11 Geoportal
Mapa interactivo. Detalle en [§8](#8-geoportal).

---

## 8. Geoportal

El Geoportal es la vista operativa central del sistema.

### Datos consumidos (todos via API)

| Dato | Endpoint |
|------|---------|
| Estaciones con coordenadas | `GET /stations` |
| Eventos recientes | `GET /iot-events` |
| Animales | `GET /animals` |
| Alertas abiertas | `GET /alerts` |

El Geoportal **no accede directamente a ninguna base de datos**.

### Componentes

```
GeoportalPage
├── MapLayout (Leaflet full-screen)
├── ControlPanel (panel flotante colapsable)
│   ├── ZoneFilter
│   ├── LayerToggle
│   └── StationListPanel
│       └── StationListItem (click → centra mapa y abre popup)
└── LeafletMapContainer
    ├── StationMarkerLayer    ← siempre visible
    ├── ActivityHeatmapLayer  ← togglable
    └── EventsLayer           ← togglable
```

### Popup de estación

```
┌─────────────────────────────────────┐
│  STA-001 · Comedero Norte           │
│  Estado: ● Activo                   │
│  Zona: Reserva Forestal A           │
│  Último evento: hace 12 min         │
│  Dispositivo: WT-0042 (online)      │
│                                     │
│  [Ver detalle →]                    │
└─────────────────────────────────────┘
```

### Color de markers por estado

| Estado estación | Color |
|----------------|-------|
| active | Verde |
| inactive | Gris |
| maintenance | Ámbar |
| offline (device) | Rojo |

### Refresco automático

TanStack Query con `refetchInterval: 60_000` — el mapa se actualiza cada 60 segundos sin recargar la página.

### MapPicker (selector de ubicación en formularios)

Usado en el formulario de creación/edición de estaciones. Leaflet embebido dentro del form con un marcador arrastrable. Al soltar el marcador, se emite `onChange(lat, lng)` que React Hook Form captura como valores del campo.

---

## 9. Dashboard

### KPI cards (fila superior)

Consumidas desde `GET /analytics/kpi`:

| Tarjeta | Métrica |
|---------|---------|
| Estaciones totales | count |
| Estaciones activas | count |
| Dispositivos offline | count |
| Eventos totales | count (período) |
| Alertas abiertas | count |

### Gráficas (Recharts)

| Gráfica | Tipo | Endpoint |
|---------|------|---------|
| Consumo en el tiempo | Line | `GET /analytics/consumption` |
| Visitas en el tiempo | Line | `GET /analytics/visits` |
| Consumo por zona | Bar | `GET /analytics/consumption-by-zone` |
| Eventos por estación | Bar horizontal | `GET /analytics/events-by-station` |
| Temperatura y humedad | Multi-line | `GET /analytics/env-readings` |

Todas las gráficas comparten un **date range filter** (`from` / `to`) almacenado en la URL. Al cambiar el rango, todas refrescan simultáneamente.

### Panel de alertas recientes

Lista de las últimas alertas abiertas con botón de resolución directa. Usa el mismo endpoint que la feature de Alertas.

---

## 10. Formularios

- **React Hook Form** maneja estado del formulario
- **Zod** define el schema de validación
- **`zodResolver`** conecta ambos

### Comportamiento estándar

1. Validación en `onSubmit` (no `onChange`) para no molestar al usuario mientras escribe
2. Botón submit deshabilitado y con spinner mientras la mutación está pendiente
3. Errores de campo inline debajo del input
4. Errores de servidor (409 conflicto) mapeados de vuelta al campo correspondiente con `setError`
5. Cualquier otro error de API → toast de error

### Mapeo errores servidor → campo

| Código de error backend | Campo afectado |
|------------------------|----------------|
| `EMAIL_ALREADY_EXISTS` | email |
| `STATION_CODE_EXISTS` | code |
| `RFID_TAG_EXISTS` | rfid_tag |
| `SERIAL_EXISTS` | serial_number |
| `FOOD_NAME_EXISTS` | name |

---

## 11. Manejo de errores y carga

### Loading states

| Situación | UI |
|-----------|-----|
| Carga inicial de página | Skeleton (MUI Skeleton) — estructura de la página vacía animada |
| Sub-sección cargando | CircularProgress (MUI) en la sección |
| Mutación pendiente | Botón deshabilitado + spinner |
| Sin datos | `EmptyState` component con mensaje y acción sugerida |

### Errores de API

| Status | Comportamiento |
|--------|---------------|
| 401 | Interceptor → clear auth → redirect `/auth/login` |
| 403 | Toast: "No tienes permiso para esta acción" |
| 404 | Toast o página NotFound según contexto |
| 409 | Error inline en el campo del formulario |
| 422 | Toast con detalle del error |
| 500 | Toast: "Algo salió mal. Intenta de nuevo." |
| Sin red | Toast: "Sin conexión. Verifica tu red." |

### Toast notifications

Provider global (`ToastContext`). Tipos: `success`, `error`, `warning`, `info`. Auto-dismiss en 4 segundos (errores: 6 segundos). Apilados en la esquina inferior derecha.

---

## 12. Tema visual

### Principios

- Minimalista — mucho espacio, pocas sombras
- Paleta verde natural (wildlife / naturaleza)
- Tipografía limpia, neutra
- Íconos de Material UI (`@mui/icons-material`)
- Sin animaciones llamativas — transiciones sutiles (150–250 ms)

### Paleta de colores (MUI theme)

```typescript
// theme/theme.ts
const theme = createTheme({
  palette: {
    primary: {
      main: "#2E7D32",    // verde bosque
      light: "#43A047",
      dark: "#1B5E20",
    },
    secondary: {
      main: "#78909C",    // gris azulado neutro
    },
    error:   { main: "#C62828" },
    warning: { main: "#F57F17" },
    success: { main: "#2E7D32" },
    background: {
      default: "#F5F5F5",
      paper: "#FFFFFF",
    },
  },
  typography: {
    fontFamily: "'Inter', 'Roboto', sans-serif",
  },
  shape: {
    borderRadius: 8,
  },
});
```

### Colores semánticos de estado

| Estado | Color | Uso |
|--------|-------|-----|
| active / online | `success.main` — verde | Badges, markers |
| inactive | `text.disabled` — gris | Badges, markers |
| maintenance | `warning.main` — ámbar | Badges, markers |
| offline / error | `error.main` — rojo | Badges, markers |

---

## 13. Integración del Geoportal existente

Existe un proyecto Geoportal previo que puede usarse como **referencia de inspiración**.

**Se puede reutilizar:**

- Layout general del mapa
- Estilos visuales del control panel
- Iconografía y markers personalizados
- Lógica de inicialización de Leaflet

**No se reutiliza:**

- Lógica de negocio
- Mocks o datos hardcodeados
- Servicios o llamadas HTTP directas
- Modelos de datos propios

Todo el acceso a datos **debe pasar por la API REST del backend** de WildTrack. Cualquier componente del geoportal existente que lea datos debe ser adaptado para consumir TanStack Query hooks que llaman a `/api/v1`.

---

## 14. Variables de entorno

```bash
# frontend/.env.example

# URL base de la API del backend
VITE_API_BASE_URL=http://localhost:8000/api/v1

# Intervalo de refresco del mapa (ms)
VITE_MAP_REFRESH_INTERVAL_MS=60000

# Tile layer de OpenStreetMap (por defecto público)
VITE_MAP_TILE_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
```

Las variables con prefijo `VITE_` son las únicas inyectadas por Vite al bundle del cliente. No almacenar secrets aquí.

---

*SDD-06 Frontend Design — v2.0.0 — 2026-07-07*
