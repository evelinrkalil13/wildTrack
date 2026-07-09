# WildTrack — Geoportal Enhancement Plan

**Document:** SDD-10  
**Version:** 2.0.0  
**Status:** Approved  
**Branch base:** `feature/slice-7-geoportal-v2`  
**Reference:** `/Users/evelyn.rendon/Desktop/UNIVERSIDAD/Geoportal-`  
**Changelog:**
- v1.0.0 — Plan inicial, 8 slices verticales.
- v2.0.0 — Revisión arquitectónica: endpoint principal lean, endpoints especializados, `GeoportalAggregationService`, filtro temporal global, roadmap PostGIS, panel de actividad reciente, estrategia de compatibilidad con FE-6.

---

## Tabla de Contenido

1. [Contexto](#1-contexto)
2. [Mapa de Conceptos](#2-mapa-de-conceptos)
3. [Decisiones Arquitectónicas](#3-decisiones-arquitectónicas)
4. [Contrato de Endpoints](#4-contrato-de-endpoints)
5. [GeoportalAggregationService](#5-geoportalaggregationservice)
6. [TimeFilter Global](#6-timefilter-global)
7. [Estrategia de Compatibilidad FE-6](#7-estrategia-de-compatibilidad-fe-6)
8. [Roadmap PostGIS](#8-roadmap-postgis)
9. [Sub-Slices de Implementación](#9-sub-slices-de-implementación)
10. [Panel de Actividad Reciente](#10-panel-de-actividad-reciente)
11. [Resumen de Archivos](#11-resumen-de-archivos)
12. [Orden de Implementación](#12-orden-de-implementación)
13. [Features Omitidos](#13-features-omitidos)
14. [Definition of Done](#14-definition-of-done)

---

## 1. Contexto

El geoportal actual (FE-6) cubre aproximadamente el 25% de las funcionalidades del geoportal de referencia. Este documento define el plan para alcanzar paridad completa manteniendo tres principios no negociables:

1. **Endpoint `GET /geoportal/stations` permanece pequeño y estable** — solo alimenta el mapa y la barra lateral.
2. **Sin lógica duplicada** — un `GeoportalAggregationService` centralizado computa todos los stats.
3. **Sin regresiones en FE-6** — cada sub-slice construye encima de lo existente.

**Baseline FE-6 (lo que ya funciona):**
- Mapa Leaflet con marcadores de tamaño fijo, coloreados por estado
- Sidebar: lista plana, 3 KPI cards, búsqueda
- Panel de detalle: dispositivo, telemetría, últimos 3 eventos con fotos
- `GET /api/v1/geoportal/stations` → `GeoportalStationRead[]`

**Lo que se construye en este plan:**
- Marcadores que codifican datos (tamaño, arco, pulso)
- Sidebar con jerarquía de sectores y chips de filtro
- Panel de detalle enriquecido (stats, frecuencia, animales, actividad reciente)
- Modal de Estadísticas (3 pestañas)
- Dashboard de historial de alimentación + trazabilidad
- Modal de Visitas con timeline y visor de fotos
- Exportación CSV/JSON/GeoJSON
- Filtro temporal global en todos los dashboards

---

## 2. Mapa de Conceptos

| Referencia | WildTrack Backend | Observaciones |
|---|---|---|
| `Individual` | `Animal` (tabla `animals`) | `rfid_tag`, `species`, `sex`, `estimated_age`, `notes` |
| `common_name` | `species` | Usar `species` como nombre display |
| `Sector` | `Zone` (tabla `zones`) | Agregar columna `color VARCHAR(7)` |
| `WildEvent` | `iot_event` (MongoDB) | `rfid_tag`, `consumed_g`, `temperature_c`, `humidity_pct`, `media_url` |
| `visitas` | `count(iot_events)` por station | MongoDB aggregation |
| `identificados` | `count WHERE rfid_tag != null` | MongoDB aggregation |
| `noIdentificados` | `count WHERE rfid_tag IS null` | MongoDB aggregation |
| `pesoPromedio` | `avg(consumed_g)` | MongoDB aggregation |
| `pesoMediana` | `sorted list → median` | Calculado en Python |
| `visitasPorDia` | `group_by(day_of_week)` | MongoDB aggregation |
| `is_live` | `device.status == "online"` | Tabla `devices` |
| `photo_ref` | `media_urls[]` | Ya en `GeoportalRecentEvent` |

---

## 3. Decisiones Arquitectónicas

### ADR-GEO-01: Endpoint de lista lean

**Problema:** `GET /geoportal/stations` tiene riesgo de crecer ilimitadamente si se agrega lógica en cada sub-slice.

**Decisión:** El endpoint de lista devuelve **únicamente** los campos necesarios para renderizar el mapa y la barra lateral. Toda la información detallada (medianas, frecuencia semanal, animales, telemetría completa, timeline) se obtiene mediante endpoints especializados llamados **on demand** cuando el usuario selecciona una estación.

**Consecuencia:** `StationDetailPanel.tsx` pasa a hacer su propia llamada a `GET /geoportal/stations/{station_id}` en lugar de reutilizar los datos de la lista.

---

### ADR-GEO-02: GeoportalAggregationService

**Problema:** Múltiples endpoints necesitan calcular los mismos stats (visitas totales, identificados, peso promedio). Sin centralización se duplica la lógica MongoDB.

**Decisión:** Crear `GeoportalAggregationService` como clase de servicio interna. Todos los endpoints del módulo geoportal invocan este servicio. El repositorio solo hace I/O.

**Separación de capas:**

```
Router  →  Service  →  AggregationService  →  Repository  →  MongoDB / PostgreSQL
```

---

### ADR-GEO-03: TimeFilter como parámetro transversal

**Problema:** Los KPIs del mapa, el modal de estadísticas, el historial de animales y el panel de detalle tienen ventanas temporales distintas si no se estandarizan.

**Decisión:** Definir `TimeFilter` como un enum compartido (`24h` | `7d` | `30d` | `all`). Todo endpoint que computa stats acepta `time_filter: TimeFilter = TimeFilter.d7` como query param. El `AggregationService` convierte el filtro en un `datetime` cutoff antes de ejecutar cada pipeline de MongoDB.

---

### ADR-GEO-04: PostGIS para análisis espacial

**Problema:** El mapa es actualmente una colección de markers sin capacidad de análisis espacial.

**Decisión:** Los endpoints de estadísticas y filtros geográficos aprovecharán PostGIS para consultas de área. Se define un roadmap explícito (ver sección 8). No se implementa en MVP pero el diseño de datos lo permite desde ya (columnas `geom` ya existen en `zones`).

---

### ADR-GEO-05: Panel de Actividad Reciente

**Problema:** La sección "últimos eventos" del panel de detalle actual muestra solo eventos de alimentación. El sistema genera múltiples tipos de actividad (alertas, telemetría, RFID, fotos) que no se visualizan.

**Decisión:** Reemplazar la sección de "Eventos Recientes" estática por un **feed cronológico de actividad** que unifica todos los tipos de evento del sistema, haciendo el panel más informativo y el sistema más "vivo".

---

## 4. Contrato de Endpoints

### Endpoints existentes (no modificar)

| Método | Path | Cambio |
|---|---|---|
| `GET` | `/geoportal/stations` | **Solo se agregan campos lean** (ver schema v2 abajo) |

### Endpoints nuevos

| Método | Path | Slice | Responsabilidad |
|---|---|---|---|
| `GET` | `/geoportal/stations/{station_id}` | GEO-2 | Detalle completo de una estación |
| `GET` | `/geoportal/stations/{station_id}/animals` | GEO-4 | Animales asociados a la estación |
| `GET` | `/geoportal/stations/{station_id}/events` | GEO-7 | Timeline paginado de eventos |
| `GET` | `/geoportal/stations/{station_id}/activity` | GEO-4 | Feed de actividad reciente |
| `GET` | `/geoportal/stats` | GEO-5 | Estadísticas globales (3 pestañas) |
| `GET` | `/geoportal/animals/{animal_id}/history` | GEO-6 | Historial completo del animal |

Todos los endpoints que computan stats aceptan `?time_filter=24h|7d|30d|all` (default `7d`).

### Schema v2 de `GET /geoportal/stations` (lean)

```python
class GeoportalStationMapItem(BaseModel):
    """Lean — solo para mapa y sidebar."""
    station_id: str
    station_code: str
    station_name: str
    latitude: float
    longitude: float
    status: StationStatus
    zone_id: str
    zone_name: str
    zone_color: str = "#52b788"
    device_status: Optional[DeviceStatus] = None
    open_alerts_count: int = 0
    is_live: bool = False
    # Stats básicos (calculados con time_filter)
    visitas_total: int = 0
    visitas_identificadas: int = 0
    visitas_sin_identificar: int = 0
```

> **Nota de migración:** El schema anterior (`GeoportalStationRead`) incluía `device`, `latest_telemetry` y `recent_events`. Esos campos se eliminan del endpoint de lista y se mueven a `GET /geoportal/stations/{station_id}`. Ver sección 7 para la estrategia de transición.

### Schema de `GET /geoportal/stations/{station_id}` (detalle completo)

```python
class GeoportalStationDetail(BaseModel):
    """Completo — llamado on-demand al seleccionar una estación."""
    # Todos los campos de GeoportalStationMapItem
    station_id: str
    station_code: str
    station_name: str
    latitude: float
    longitude: float
    status: StationStatus
    zone_id: str
    zone_name: str
    zone_color: str
    device_status: Optional[DeviceStatus]
    open_alerts_count: int
    is_live: bool
    visitas_total: int
    visitas_identificadas: int
    visitas_sin_identificar: int
    # Campos adicionales solo en detalle
    food_type: Optional[str]
    device: Optional[GeoportalDeviceInfo]
    latest_telemetry: Optional[GeoportalTelemetry]
    peso_promedio_g: Optional[float]
    peso_mediana_g: Optional[float]
    visitas_por_dia: list[int]  # 7 valores Mon-Sun
    recent_activity: list[ActivityItem]  # feed unificado
```

---

## 5. GeoportalAggregationService

**Archivo:** `backend/modules/geoportal/aggregation.py`

Este servicio interno concentra toda la lógica de cálculo. Los routers nunca llaman directamente al repositorio para computar stats.

```python
class GeoportalAggregationService:

    @staticmethod
    async def compute_station_counts(
        time_filter: TimeFilter
    ) -> dict[str, StationCounts]:
        """
        Retorna dict keyed por station_id con:
        { visitas_total, visitas_identificadas, visitas_sin_identificar }
        Usado por: GET /geoportal/stations, GET /geoportal/stats
        """

    @staticmethod
    async def compute_station_detail_stats(
        station_id: str, time_filter: TimeFilter
    ) -> StationDetailStats:
        """
        Retorna stats completos para una sola estación:
        { ...counts, peso_promedio_g, peso_mediana_g, visitas_por_dia[7] }
        Usado por: GET /geoportal/stations/{id}
        """

    @staticmethod
    async def compute_sector_summaries(
        stations: list, counts: dict, time_filter: TimeFilter
    ) -> list[SectorSummary]:
        """
        Agrega counts por zone_id.
        Usado por: GET /geoportal/stats (tab Sectores)
        """

    @staticmethod
    async def compute_animal_movements(
        time_filter: TimeFilter
    ) -> list[AnimalMovement]:
        """
        Identifica animales que visitaron más de una estación.
        Pipeline MongoDB: group by rfid_tag → distinct station_ids → filter > 1
        Usado por: GET /geoportal/stats (tab Individuos)
        """

    @staticmethod
    async def compute_animal_history(
        rfid_tag: str, time_filter: TimeFilter, limit: int = 50
    ) -> AnimalHistoryData:
        """
        Historial completo para un RFID: timeline, ranking, actividad semanal,
        trace_path, insight_text.
        Usado por: GET /geoportal/animals/{id}/history
        """

    @staticmethod
    def generate_insight_text(
        feeder_ranking: list[FeederRankItem], total_estaciones: int
    ) -> str:
        """
        Genera texto de comportamiento:
        - 1 estación → "Todos los registros en EST-01 — sin desplazamientos"
        - top >= 70% → "Preferencia marcada: 72% en EST-01"
        - else → "Distribución equilibrada entre múltiples comederos"
        """
```

**Regla de responsabilidad:**
- `GeoportalRepository` — solo I/O (queries MongoDB + PostgreSQL)
- `GeoportalAggregationService` — solo cálculos sobre datos ya traídos
- `GeoportalService` — orquesta repository + aggregation → response schema

---

## 6. TimeFilter Global

**Definición** en `backend/shared/enums.py`:

```python
class TimeFilter(str, Enum):
    h24 = "24h"
    d7 = "7d"
    d30 = "30d"
    all = "all"
```

**Helper** en `backend/modules/geoportal/aggregation.py`:

```python
def get_time_cutoff(time_filter: TimeFilter) -> Optional[datetime]:
    now = datetime.now(timezone.utc)
    cutoffs = {
        TimeFilter.h24: timedelta(hours=24),
        TimeFilter.d7:  timedelta(days=7),
        TimeFilter.d30: timedelta(days=30),
    }
    delta = cutoffs.get(time_filter)
    return (now - delta) if delta else None  # None = sin filtro
```

**Uso en MongoDB pipelines:**

```python
match_stage = {"station_id": {"$ne": None}}
if cutoff:
    match_stage["ingested_at"] = {"$gte": cutoff}
```

**Aplicación en endpoints:**

| Endpoint | Param | Default |
|---|---|---|
| `GET /geoportal/stations` | `?time_filter=` | `7d` |
| `GET /geoportal/stations/{id}` | `?time_filter=` | `7d` |
| `GET /geoportal/stats` | `?time_filter=` | `7d` |
| `GET /geoportal/stations/{id}/events` | `?time_filter=` | `all` |
| `GET /geoportal/animals/{id}/history` | `?time_filter=` | `all` |

**Frontend — Selector de periodo:**

Un componente `TimePeriodSelector` en la cabecera del geoportal (o sidebar footer) permite al usuario cambiar el periodo global. Su valor se almacena en un `useState` en `GeoportalPage.tsx` y se pasa como prop/parámetro a todos los hooks que consumen endpoints con stats.

```typescript
type TimePeriod = "24h" | "7d" | "30d" | "all";
const [timePeriod, setTimePeriod] = useState<TimePeriod>("7d");
```

---

## 7. Estrategia de Compatibilidad FE-6

La transición del schema `GeoportalStationRead` (v1, con `device`, `latest_telemetry`, `recent_events`) al schema `GeoportalStationMapItem` (v2, lean) se hace en dos pasos para evitar romper FE-6:

### Paso 1 — GEO-2 (backend primero)
1. Crear `GET /geoportal/stations/{station_id}` con `GeoportalStationDetail` (incluye todos los campos del v1 más los nuevos).
2. Modificar `GET /geoportal/stations` para retornar `GeoportalStationMapItem[]` (lean).
3. El FE-6 actual usa `station.device`, `station.latest_telemetry`, `station.recent_events` del panel de detalle — estos dejan de venir del list endpoint.

### Paso 2 — GEO-2 (frontend, mismo PR)
4. Actualizar `StationDetailPanel.tsx`: al abrir un panel, hacer `GET /geoportal/stations/{id}` y usar esa respuesta para dispositivo, telemetría y eventos recientes.
5. Los hooks `useGeoportalStations` y `useStationDetail` son independientes.

**Resultado:** El mapa y la barra lateral siguen funcionando igual (solo usan campos del schema lean que se mantienen). El panel de detalle pasa a llamar al endpoint especializado, eliminando la necesidad de los campos eliminados del list endpoint.

**No se modifica:** ningún endpoint fuera del módulo `geoportal`. Ningún componente de la barra lateral ni del mapa consume `device`, `latest_telemetry` ni `recent_events` directamente — solo el panel de detalle.

---

## 8. Roadmap PostGIS

Estas funcionalidades no se implementan en los sub-slices actuales, pero el diseño del sistema debe soportarlas. Se incluyen en el roadmap para informar decisiones de datos.

### Heatmap de actividad

- **Backend:** `GET /geoportal/heatmap?time_filter=7d` — retorna array de `{lat, lng, intensity}` donde `intensity = visitas_total` por estación o, con PostGIS, interpolado por celda de grilla (`ST_SnapToGrid`).
- **Frontend:** Leaflet plugin `leaflet.heat` sobre la capa del mapa.

### Clustering de estaciones

- **Frontend:** librería `supercluster` (client-side) para agrupar marcadores cuando hay zoom out.
- **Backend:** Alternativa — `GET /geoportal/clusters?zoom=&bbox=` usando `ST_ClusterKMeans` de PostGIS.

### Consultas espaciales por zona

- **Backend:** `GET /geoportal/stats?zone_id=` con filtro `ST_Within(station.geom, zone.geom)` para delimitación geográfica precisa en lugar de `zone_id == x`.
- Útil cuando zonas tienen formas irregulares y una estación está geográficamente dentro de múltiples zonas.

### Filtros geográficos (radio de búsqueda)

- **Backend:** `GET /geoportal/stations?lat=&lng=&radius_km=` usando `ST_DWithin(geom, ST_MakePoint(lng, lat)::geography, radius_meters)`.
- **Frontend:** El usuario dibuja un círculo en el mapa → filtra la lista del sidebar.

### Requerimiento de datos

Para aprovechar PostGIS, las estaciones necesitan una columna `geom GEOMETRY(Point, 4326)`. Esta columna **ya existe en el modelo de datos** (ver SDD-03). La migration `0002_create_zones_table.py` ya incluye `geom` en `zones`. Se debe verificar que `stations` también tiene su columna `geom` actualizada.

---

## 9. Sub-Slices de Implementación

---

### GEO-2: Marcadores Ricos + Endpoint de Detalle
**Duración estimada:** 2.5 días  
**Branch:** `feature/geo-2-rich-markers`

#### Objetivo
Reemplazar los marcadores fijos por marcadores que codifican datos. Separar el endpoint de lista del endpoint de detalle. Agregar la leyenda y el popup de Leaflet.

#### Backend

**Migration:** `0009_add_zone_color.py`
```sql
ALTER TABLE zones ADD COLUMN color VARCHAR(7) NOT NULL DEFAULT '#52b788';
```

**`modules/geoportal/schemas.py`** — agregar:
- `GeoportalStationMapItem` — schema lean del list endpoint
- `GeoportalStationDetail` — schema completo del detail endpoint
- `ActivityItem` — item del feed de actividad (ver sección 10)

**`modules/geoportal/aggregation.py`** — crear:
- `GeoportalAggregationService` con `compute_station_counts(time_filter)` y `compute_station_detail_stats(station_id, time_filter)`

**`modules/geoportal/repository.py`** — agregar:
- `get_zone_colors(session)` — SELECT id, color FROM zones
- `get_device_statuses(session)` — SELECT station_id, status FROM devices WHERE station_id IS NOT NULL
- `get_station_event_counts(cutoff)` — MongoDB: `{$match, $group: {_id: station_id, total, identified, unidentified}}`
- `get_station_detail(session, station_id)` — query completa para una sola estación

**`modules/geoportal/service.py`** — modificar:
- `list_stations(session, time_filter)` → retorna `list[GeoportalStationMapItem]` usando el `AggregationService`
- `get_station_detail(session, station_id, time_filter)` → retorna `GeoportalStationDetail`

**`modules/geoportal/router.py`** — agregar:
```python
@router.get("/stations/{station_id}", response_model=GeoportalStationDetail)
async def get_station_detail(
    station_id: str,
    time_filter: TimeFilter = TimeFilter.d7,
    session: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user),
):
    return await GeoportalService.get_station_detail(session, station_id, time_filter)
```

**Tests:** 4 unit + 3 integration nuevos

#### Frontend

**`geoportal/api/geoportal.types.ts`** — reemplazar `GeoportalStationRead` por `GeoportalStationMapItem` y agregar `GeoportalStationDetail`.

**`geoportal/api/geoportal.api.ts`** — agregar `getStationDetail(stationId, timePeriod)`.

**`geoportal/hooks/useStationDetail.ts`** — hook on-demand:
```typescript
export function useStationDetail(stationId: string | null, timePeriod: TimePeriod) {
  return useQuery({
    queryKey: ["geoportal-station", stationId, timePeriod],
    queryFn: () => getStationDetail(stationId!, timePeriod),
    enabled: !!stationId,
    staleTime: 30_000,
  });
}
```

**`geoportal/components/StationMarker.tsx`** — reescritura de `createDivIcon`:
```
radius = 11 + min(station.visitas_total / 10, 15)   → rango 11–26px
texto central = visitas_total (blanco, bold)
arco ámbar = strokeDasharray proporcional a (sin_id / total) × circumference
is_live = segundo círculo exterior, @keyframes pulse, color #3b82f6
offline/sin datos = gris #5f7669, radio mínimo 11px
seleccionado = ring blanco exterior 2px
```

SVG resultante por marcador (sin dependencias externas):
```svg
<svg width="{2r+8}" height="{2r+8}">
  <!-- Fondo circular -->
  <circle cx="..." cy="..." r="{r}" fill="{color}" fill-opacity="0.9"/>
  <!-- Arco ámbar % sin identificar -->
  <circle cx="..." cy="..." r="{r-3}" fill="none" stroke="#e08a1e"
          stroke-width="3" stroke-dasharray="{arc} {total}"/>
  <!-- Texto visitas -->
  <text x="..." y="..." fill="white" font-weight="bold">{visitas}</text>
  <!-- Anillo pulsante (solo si is_live) -->
  <circle class="pulse-ring" r="{r+4}" fill="none" stroke="#3b82f6"/>
</svg>
```

CSS animation (inyectada una vez en `GeoportalPage.tsx`):
```css
@keyframes geo-pulse {
  0%   { r: {r+4}px; opacity: 0.6; }
  100% { r: {r+10}px; opacity: 0; }
}
.pulse-ring { animation: geo-pulse 2s ease-out infinite; }
```

**`geoportal/components/GeoportalLegend.tsx`** — nuevo:
```
┌─────────────────────────────┐
│ Cómo leer el mapa           │
│ ● Tamaño = nº de visitas    │
│ ◔ Arco = % sin identificar  │
│ ● Gris = offline            │
│ 📡 Azul pulsante = en vivo  │
└─────────────────────────────┘
```
Posición: `absolute bottom-8 left-4 z-[1000]` (sobre el mapa, bajo controles Leaflet).

**`geoportal/components/StationPopup.tsx`** — nuevo popup Leaflet:
- Clic en marcador → popup primero (280px)
- Contenido: código + nombre + badge zona (color), grid Visitas/Identificados/Sin ID, botón "Ver detalles →"
- "Ver detalles" → cierra popup + abre panel lateral

**`geoportal/components/StationDetailPanel.tsx`** — modificar:
- Reemplazar lectura de `station.device`, `station.latest_telemetry`, `station.recent_events` del objeto del mapa
- Por llamada a `useStationDetail(selectedStationId, timePeriod)` para obtener datos frescos

**`geoportal/pages/GeoportalPage.tsx`** — agregar:
- `[timePeriod, setTimePeriod]` state
- `<GeoportalLegend />`
- Inyección del CSS de animación `pulse`

**Acceptance Criteria:**
- [ ] Marcadores escalan con visitas (rango 11–26px) 
- [ ] Arco ámbar visible cuando hay visitas sin identificar
- [ ] Anillo pulsante azul en estaciones con device online
- [ ] Leyenda visible, colapsable con clic
- [ ] Clic en marcador → popup → "Ver detalles" → panel
- [ ] Panel de detalle llama a `GET /geoportal/stations/{id}` (no usa campos del list)
- [ ] `GET /geoportal/stations` sigue funcionando (compatible con FE-6 excepto campos eliminados)
- [ ] `tsc --noEmit` limpio, `pytest` sin regresiones

---

### GEO-3: Sidebar con Jerarquía de Sectores
**Duración estimada:** 1.5 días  
**Branch:** `feature/geo-3-sector-sidebar`

#### Objetivo
Reorganizar el sidebar: sectores colapsables, chips de filtro, selector de periodo temporal, footer con acciones.

#### Backend
Sin cambios de backend en este slice. Todos los datos necesarios vienen del endpoint lean (que ya incluye `zone_id`, `zone_name`, `zone_color`, `is_live`, `visitas_total`, `open_alerts_count`).

#### Frontend

**`geoportal/components/GeoportalSidebar.tsx`** — reescritura completa:

```
┌──────────────────────────────────┐
│ WildTrack Geoportal   [👤] [×]   │
│ ┌────────────────────────────┐   │
│ │ 🔍 Buscar estación...      │   │
│ └────────────────────────────┘   │
│ [Todas] [En alerta 2] [Sin ID]   │  ← chips
│ Periodo: [▼ Últimos 7 días]       │  ← selector temporal
│ ─── ● online  ● alerta  ─ offline│
│                                  │
│ ▼ ● NORTE  (3 est.)          [+] │  ← zona colapsable
│   ●  EST-01  STA-001  🔴2    47  │
│   ●  EST-02  STA-002         12  │
│   📡 EST-03  STA-003         31  │  ← is_live
│                                  │
│ ▶ ● CENTRO  (2 est.)         [+] │  ← colapsado
│                                  │
│ [▸ Expandir todo][◂ Colapsar todo]│
├──────────────────────────────────┤
│ [📊 Estadísticas] [⬇ Exportar]   │
└──────────────────────────────────┘
```

**Lógica de agrupación:**
```typescript
const stationsByZone = useMemo(() => {
  return filteredStations.reduce((acc, s) => {
    const key = s.zone_id;
    if (!acc[key]) acc[key] = { zone_name: s.zone_name, zone_color: s.zone_color, stations: [] };
    acc[key].stations.push(s);
    return acc;
  }, {} as Record<string, ZoneGroup>);
}, [filteredStations]);
```

**Chips de filtro:**
- `todas` → sin filtro adicional
- `en alerta` → `open_alerts_count > 0`
- `sin identificar` → `visitas_sin_identificar > 0`

**Selector temporal:** `<TimePeriodSelector>` con 4 opciones (24h, 7d, 30d, Todo). Al cambiar, notifica al `GeoportalPage` que actualiza el `timePeriod` state y refetcha.

**Acceptance Criteria:**
- [ ] Estaciones agrupadas por zona con cabecera colapsable (chevron animado)
- [ ] Color dot de zona en la cabecera del grupo
- [ ] Los 3 chips filtran la lista en tiempo real
- [ ] El selector de periodo funciona y actualiza los conteos
- [ ] Badge 📡 en estaciones `is_live`
- [ ] Número de visitas right-aligned en cada fila
- [ ] Botones de footer presentes (stats y export)

---

### GEO-4: Panel de Detalle + Actividad Reciente
**Duración estimada:** 2.5 días  
**Branch:** `feature/geo-4-detail-panel`

#### Objetivo
Enriquecer el panel de detalle con stats de peso, gráfico de frecuencia, lista de animales con chip y el nuevo feed de **Actividad Reciente**.

#### Backend

**Endpoint:** `GET /api/v1/geoportal/stations/{station_id}/animals`  
**Query param:** `?time_filter=7d`  
**Response:**
```python
class GeoportalAnimalRead(BaseModel):
    animal_id: str
    rfid_tag: str
    species: str
    sex: str
    estimated_age: Optional[str]
    notes: Optional[str]
    registered_at: datetime
    total_visits: int
    last_visit: Optional[datetime]
    avg_consumed_g: Optional[float]
```

**Endpoint:** `GET /api/v1/geoportal/stations/{station_id}/activity`  
**Query param:** `?limit=20`  
**Response:** `list[ActivityItem]` (ver sección 10)

**`modules/geoportal/aggregation.py`** — agregar:
- `compute_station_animals(session, station_id, time_filter)` — JOIN animals + iot_events por rfid_tag
- `build_activity_feed(session, station_id, limit)` — unifica iot_events + alerts + device_telemetry

**Tests:** 3 unit + 2 integration

#### Frontend

**`geoportal/components/StationDetailPanel.tsx`** — nueva estructura:

```
┌──────────────────────────────────────┐
│ [×] EST-01  Comedero Norte  📡       │
│ ● Activa · última visita hace 2h     │
│ 📅 Periodo: [▼ 7 días]   [⬇ CSV]   │
├──────────────────────────────────────┤
│ ESTADÍSTICAS (7 días)                │
│ ┌──────┐┌──────┐┌──────┐┌──────┐   │
│ │  47  ││  32  ││  15  ││ 248g │   │
│ │Visitas││ ID   ││Sin ID││ Peso │   │
│ └──────┘└──────┘└──────┘└──────┘   │
│ mediana: 234g                        │
├──────────────────────────────────────┤
│ FRECUENCIA DE VISITAS                │
│  L    M    X    J    V    S    D     │
│  ▐█▌  ▐▌   ▐██▌ ▐█▌  ▐▌   ▐▌  ▐▌  │
│  Día más activo: Miércoles           │
├──────────────────────────────────────┤
│ ANIMALES CON CHIP (3)  [+ Registrar] │
│ ┌──────────────────────────────────┐ │
│ │ ♂ A-003 · Oso hormiguero        │ │
│ │ chip: 123456789012345 · 12 vis. │ │
│ │ [Ver historial →]               │ │
│ └──────────────────────────────────┘ │
├──────────────────────────────────────┤
│ ACTIVIDAD RECIENTE                   │
│ 🍽 Alimentación · EST-01 · hace 2h  │
│ 📷 Foto capturada · hace 2h         │
│ 🏷 RFID A-003 · hace 2h            │
│ ⚠ Alerta: nivel bajo · hace 4h     │
│ 📡 Telemetría recibida · hace 10m  │
├──────────────────────────────────────┤
│ DISPOSITIVO | TELEMETRÍA             │
│ CONTRATO DE DATOS                   │
└──────────────────────────────────────┘
```

**Nuevos sub-componentes:**
- `StationStatsGrid` — 4 cards: Visitas / ID / Sin ID / Peso prom + mediana
- `VisitFrequencyChart` — 7 barras SVG inline (L–D), pico a 100%, "Día más activo: X"
- `AnimalCard` — sex badge + species + rfid_tag + total_visits + botón "Ver historial →"
- `RecentActivityFeed` — ver sección 10
- `DataContractTable` — tabla: Campo | Valor actual | Rango | Estado ✓/⚠

**Hooks nuevos:**
- `useStationAnimals(stationId, timePeriod)` — staleTime 60s
- `useStationActivity(stationId)` — staleTime 30s, refetchInterval 60s

El selector de periodo del panel de detalle es **independiente** del selector del sidebar: el usuario puede ver el mapa con stats de 7 días y el panel de una estación con stats de 30 días.

**Acceptance Criteria:**
- [ ] Stats cards muestran datos del `useStationDetail` (no del list endpoint)
- [ ] El gráfico de frecuencia renderiza 7 barras con pico correcto
- [ ] La lista de animales muestra rfid_tag + visit count
- [ ] "Ver historial →" abre `AnimalFeedingDashboard` (GEO-6)
- [ ] El feed de actividad reciente muestra eventos mixtos ordenados cronológicamente
- [ ] La tabla de contrato muestra flags ⚠ cuando los valores están fuera de rango

---

### GEO-5: Modal de Estadísticas (3 Pestañas)
**Duración estimada:** 2.5 días  
**Branch:** `feature/geo-5-stats-modal`

#### Backend

**Endpoint:** `GET /api/v1/geoportal/stats?time_filter=7d`

```python
class StationStatRow(BaseModel):
    station_id: str; station_name: str
    zone_id: str; zone_name: str; zone_color: str
    visitas: int; identificados: int; sin_identificar: int
    peso_promedio_g: Optional[float]
    status: StationStatus; open_alerts: int

class SectorStatRow(BaseModel):
    zone_id: str; zone_name: str; zone_color: str
    num_estaciones: int
    visitas: int; identificados: int; sin_identificar: int
    pct_sin_id: float
    peso_promedio_g: Optional[float]
    en_alerta: int

class AnimalMovement(BaseModel):
    animal_id: str; rfid_tag: str; species: str; sex: str
    distinct_stations: int
    path: list[str]       # station_ids en orden cronológico (deduplicado)
    path_names: list[str] # nombres de estaciones

class GeoportalStatsResponse(BaseModel):
    time_filter: str
    total_estaciones: int; total_sectores: int
    total_animales_con_chip: int; total_visitas: int
    avistamientos_sin_chip: int
    estaciones: list[StationStatRow]
    sectores: list[SectorStatRow]
    animales_con_chip: list[AnimalMovement]
```

Toda la lógica de agregación pasa por `GeoportalAggregationService.compute_sector_summaries()` y `compute_animal_movements()` — sin lógica duplicada con GEO-2 o GEO-4.

**Tests:** 3 unit + 2 integration

#### Frontend — `StatsModal.tsx`

```
┌─────────────────────────────────────────────┐
│ Resumen general — WildTrack          [×]    │
│ 12 est · 4 sectores · 8 con chip           │
│ Periodo: [▼ Últimos 7 días]                 │
├─────────────────────────────────────────────┤
│ [Estaciones] [Sectores] [Individuos]        │
├─────────────────────────────────────────────┤
│ TAB 1 — Estaciones (ordenadas por visitas)  │
│ ID      Sector   Vis. ID  Sin  Peso  Estado │
│ EST-01  ●NORTE   47   32   15  248g  ●     │
│                                             │
│ TAB 2 — Sectores                            │
│ Sector  Est. Vis.  ID  Sin  %Sin  Peso Alertas│
│ ●NORTE   3  120   80   40   33%  228g   1  │
│                                             │
│ TAB 3 — Individuos                          │
│ ┌────┐ ┌────┐ ┌────┐ ┌────┐               │
│ │  8 │ │156 │ │5♂3♀│ │  2 │               │
│ │chip│ │s/ID│ │sexo│ │mov.│               │
│ └────┘ └────┘ └────┘ └────┘               │
│                                             │
│ Individuos con desplazamiento (2)           │
│ ┌─────────────────────────────────┐         │
│ │ A-003 · ♂ · Oso hormiguero     │         │
│ │ EST-01 → EST-03 → EST-01       │         │
│ │ [Ver trazabilidad en el mapa →]│         │
│ └─────────────────────────────────┘         │
└─────────────────────────────────────────────┘
```

**Hook:** `useGeoportalStats(timePeriod)` — staleTime 120s.

**Interacción "Ver trazabilidad en el mapa →":**
1. Cierra el modal
2. Llama a `setTraceAnimal({ path, animal })` en `GeoportalPage`
3. `GeoportalPage` renderiza `<TraceLayer>` (implementado en GEO-6)

**Acceptance Criteria:**
- [ ] Modal se abre desde el botón "Estadísticas" del sidebar footer
- [ ] El selector de periodo del modal funciona independientemente
- [ ] Tab Estaciones ordena por visitas desc
- [ ] Tab Sectores muestra % sin ID correctamente calculado
- [ ] Tab Individuos: 4 KPIs correctos + tarjetas de desplazamiento
- [ ] "Ver trazabilidad en el mapa" activa la trace view

---

### GEO-6: Dashboard de Alimentación + Trazabilidad
**Duración estimada:** 3 días  
**Branch:** `feature/geo-6-animal-feeding`

#### Backend

**Endpoint:** `GET /api/v1/geoportal/animals/{animal_id}/history?time_filter=all`

```python
class FeedingEvent(BaseModel):
    event_id: str; station_id: str; station_name: str
    timestamp: datetime; consumed_g: Optional[float]
    temperature_c: Optional[float]; humidity_pct: Optional[float]
    media_urls: list[str] = []

class FeederRankItem(BaseModel):
    station_id: str; station_name: str
    visits: int; pct: float; is_primary: bool

class AnimalHistoryResponse(BaseModel):
    animal_id: str; rfid_tag: str; species: str; sex: str
    estimated_age: Optional[str]; notes: Optional[str]
    total_alimentaciones: int; total_estaciones: int
    dias_activo: int; peso_promedio_g: Optional[float]
    actividad_semanal: list[int]  # 7 valores Lun–Dom
    feeder_ranking: list[FeederRankItem]
    timeline: list[FeedingEvent]  # últimos 50
    trace_path: list[TraceStop]   # [{station_id, station_name, lat, lng, timestamp}]
    insight_text: str
    time_filter: str
```

Toda la computación pasa por `GeoportalAggregationService.compute_animal_history()`.

**Tests:** 2 unit + 2 integration

#### Frontend — `AnimalFeedingDashboard.tsx`

```
┌──────────────────────────────────────────────────┐
│ A-003 · chip 123456789012345                     │
│ Historial de alimentación — Oso hormiguero       │
│ Tremarctos ornatus                               │
│ Periodo: [▼ Todo]  [Ver ruta en mapa] [⬇CSV][×] │
├──────────────────────────────────────────────────┤
│ 📊 Preferencia marcada: 75% en Comedero Norte   │
├──────────────────────────────────────────────────┤
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐            │
│ │  47  │ │  3   │ │  22  │ │ 248g │            │
│ │Alim. │ │Est.  │ │Días  │ │Peso  │            │
│ └──────┘ └──────┘ └──────┘ └──────┘            │
├────────────────────┬─────────────────────────────┤
│ COMEDEROS VISITADOS│ ACTIVIDAD SEMANAL           │
│ ★ EST-01 ████ 35(75%)│  L  M  X  J  V  S  D    │
│ 2. EST-03 ██   8(17%)│  ▐█▌ ▐▌ ▐██▌ ...        │
│ 3. EST-02 █    4 (8%)│  Día más activo: Mié     │
├────────────────────────────────────────────────  ┤
│ LÍNEA DE TIEMPO (últimos 50)                     │
│ EST-01 · Comedero Norte · 248g · 📷 · hace 2h   │
│ EST-01 · Comedero Norte · 231g · -   · hace 5h  │
│ EST-03 · Comedero Sur   · 195g · -   · hace 1d  │
└──────────────────────────────────────────────────┘
```

**`TraceLayer.tsx`** — nuevo componente Leaflet:
- Recibe `tracePath: TraceStop[]`
- `<Polyline positions={coords} dashArray="6 4" color="#e08a1e" weight={3}/>`
- `<CircleMarker>` numerados en cada parada (1, 2, 3...)
- Banner en mapa: "Trazabilidad A-003 (Oso hormiguero) · 3 paradas" + botón "✕ Salir"
- Al salir: `setTraceAnimal(null)`, `map.fitBounds(originalBounds)`

**Estado en `GeoportalPage.tsx`:**
```typescript
const [traceAnimal, setTraceAnimal] = useState<TraceData | null>(null);
// Activado desde StatsModal (GEO-5) y AnimalFeedingDashboard
```

**Acceptance Criteria:**
- [ ] Dashboard se abre desde "Ver historial →" en `AnimalCard`
- [ ] Los 4 KPIs muestran datos reales
- [ ] Ranking de comederos con barras de porcentaje
- [ ] Actividad semanal con 7 barras y día pico resaltado
- [ ] Timeline muestra 50 eventos con estación + peso + icono foto
- [ ] `insight_text` correcto según la distribución
- [ ] "Ver ruta en el mapa" activa `<TraceLayer>` con la polyline y stops numerados
- [ ] Botón "Salir" en el banner limpia la trace view
- [ ] CSV descarga con BOM UTF-8

---

### GEO-7: Modal de Visitas por Estación
**Duración estimada:** 1.5 días  
**Branch:** `feature/geo-7-visits-modal`

#### Backend

**Endpoint:** `GET /api/v1/geoportal/stations/{station_id}/events`  
**Params:** `page` (default 1), `page_size` (default 20), `filter` (all|identified|unidentified), `time_filter`

```python
class StationEventDetail(BaseModel):
    event_id: str; timestamp: datetime
    rfid_tag: Optional[str]; animal_id: Optional[str]
    animal_species: Optional[str]; animal_sex: Optional[str]
    consumed_g: Optional[float]
    temperature_c: Optional[float]; humidity_pct: Optional[float]
    media_urls: list[str] = []; is_identified: bool

class StationEventsResponse(BaseModel):
    station_id: str; station_name: str
    total: int; identificadas: int; sin_identificar: int
    page: int; pages: int
    events: list[StationEventDetail]
```

**Lógica:** para eventos con `rfid_tag`, join con `animals` en PostgreSQL para agregar `species` y `sex`.

**Tests:** 2 unit + 2 integration

#### Frontend — `StationVisitsModal.tsx`

```
┌──────────────────────────────────────────────────┐
│ EST-01 | Visitas — Comedero Norte         [⬇][×] │
│ 47 visitas · 32 identificadas · 15 sin ID        │
├──────────────────────────────────────────────────┤
│ [Todas (47)] [Identificadas (32)] [Sin ID (15)]  │
├──────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────┐ │
│ │ [📷]  15 Jun 14:32 · hace 2h                │ │
│ │       A-003 · ♂ · Oso hormiguero            │ │
│ │       chip: 123456789012345                 │ │
│ │       248g ✓   22°C ✓   65% ✓             │ │
│ └──────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────┐ │
│ │ [📷✗]  15 Jun 12:10 · hace 4h               │ │
│ │        Sin identificar — sin chip RFID      │ │
│ │        45g ⚠   38°C ⚠   18% ⚠             │ │
│ └──────────────────────────────────────────────┘ │
│ [Cargar más]                                     │
└──────────────────────────────────────────────────┘
```

**Umbrales de anomalía:**
| Campo | Rango normal | Flag |
|---|---|---|
| `consumed_g` | ≥ 50g | ⚠ rojo si < 50 |
| `temperature_c` | 10–40 °C | ⚠ ámbar si fuera |
| `humidity_pct` | 20–95 % | ⚠ ámbar si fuera |

**Visor de fotos** (nested modal): imagen grande + evento completo + crédito "Vía MinIO / WildTrack".

**Trigger:** el número de visitas en `StationStatsGrid` es clickable → abre este modal.

**Acceptance Criteria:**
- [ ] Modal se abre al hacer clic en el conteo de visitas del panel de detalle
- [ ] Los 3 chips de filtro funcionan correctamente
- [ ] Las anomalías muestran indicadores ⚠ con los umbrales correctos
- [ ] El visor de fotos se abre al clic en `[📷]` (solo si hay media_urls)
- [ ] La paginación "Cargar más" funciona (página siguiente via React Query)

---

### GEO-8: Exportación de Datos
**Duración estimada:** 1 día  
**Branch:** `feature/geo-8-export`

#### Frontend — `ExportModal.tsx` (client-side, sin nuevos endpoints)

Los datos se construyen a partir de lo ya cacheado en React Query.

| Dataset | Formato | Fuente de datos |
|---|---|---|
| Eventos de estación seleccionada | CSV | `useStationEvents` |
| Todas las estaciones | CSV · GeoJSON | `useGeoportalStations` |
| Animales con chip | CSV | `useGeoportalStats` |

**CSV de eventos:** `event_id, station_id, station_name, timestamp, rfid_tag, animal_species, consumed_g, temperature_c, humidity_pct`

**GeoJSON de estaciones:**
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "geometry": { "type": "Point", "coordinates": [lng, lat] },
    "properties": { "station_id": "...", "name": "...", "zone": "...", "status": "...", "visitas": 47 }
  }]
}
```

**CSV de animales:** `animal_id, rfid_tag, species, sex, estimated_age, registered_at, total_visits, avg_consumed_g`

**Generación:** `Blob` + `URL.createObjectURL` + `<a download>` programático. BOM `﻿` en CSV.  
Nombres de archivo: `wildtrack_eventos_EST-01_20260708.csv`

**Acceptance Criteria:**
- [ ] Modal muestra las 3 secciones con botones de formato
- [ ] CSV de eventos descarga con BOM y datos correctos
- [ ] GeoJSON válido (verificable en geojson.io)
- [ ] Nombres de archivo con fecha actual

---

## 10. Panel de Actividad Reciente

Este bloque reemplaza la sección "Eventos Recientes" actual del `StationDetailPanel`.

### Schema

```python
class ActivityItemType(str, Enum):
    feeding       = "feeding"       # sesión de alimentación (iot_event)
    rfid_read     = "rfid_read"     # lectura RFID exitosa
    photo         = "photo"         # fotografía capturada
    alert         = "alert"         # alerta generada
    telemetry     = "telemetry"     # telemetría recibida del dispositivo

class ActivityItem(BaseModel):
    item_type: ActivityItemType
    timestamp: datetime
    description: str          # texto legible: "Alimentación · 248g consumidos"
    rfid_tag: Optional[str]   # si aplica
    animal_species: Optional[str]  # si se identificó
    media_urls: list[str] = []
    severity: Optional[str]   # "info" | "warning" | "critical" (para alertas)
```

**Construcción** en `GeoportalAggregationService.build_activity_feed(station_id, limit)`:

```python
# Fuentes unificadas y ordenadas por timestamp desc:
# 1. MongoDB iot_events → ActivityItemType.feeding + .rfid_read + .photo
# 2. MongoDB alerts → ActivityItemType.alert
# 3. MongoDB device_telemetry → ActivityItemType.telemetry (solo el más reciente)
```

**Iconos por tipo en el frontend:**

| Tipo | Icono | Color |
|---|---|---|
| `feeding` | 🍽 | verde |
| `rfid_read` | 🏷 | azul |
| `photo` | 📷 | neutro |
| `alert` | ⚠ | ámbar / rojo según severity |
| `telemetry` | 📡 | gris |

**Componente:** `RecentActivityFeed.tsx`
- Lista de `ActivityItem` ordenada cronológicamente
- Timestamp relativo (hace 2h, hace 1d)
- Para alertas con `severity: "critical"`: fondo ámbar suave
- Si `media_urls.length > 0`: thumbnail miniatura inline
- Si `rfid_tag` identificado: texto azul con nombre del animal

---

## 11. Resumen de Archivos

### Backend — Nuevos / Modificados

| Archivo | Tipo | Slice |
|---|---|---|
| `migrations/versions/0009_add_zone_color.py` | Nueva migration | GEO-2 |
| `shared/enums.py` | Modificar — agregar `TimeFilter` | GEO-2 |
| `modules/geoportal/schemas.py` | Modificar — `MapItem`, `Detail`, `ActivityItem`, todos los nuevos schemas | GEO-2, 4, 5, 6, 7 |
| `modules/geoportal/aggregation.py` | **Nuevo** — `GeoportalAggregationService` | GEO-2 |
| `modules/geoportal/repository.py` | Modificar — 8 métodos nuevos | GEO-2, 4, 5, 6, 7 |
| `modules/geoportal/service.py` | Modificar — delegar a `AggregationService` | GEO-2, 4, 5, 6 |
| `modules/geoportal/router.py` | Modificar — 5 endpoints nuevos | GEO-2, 4, 5, 6, 7 |
| `tests/unit/test_geoportal_service.py` | Modificar — +12 tests | GEO-2, 4, 5, 6, 7 |
| `tests/integration/test_geoportal_api.py` | Modificar — +10 tests | GEO-2, 4, 5, 6, 7 |

### Frontend — Nuevos / Modificados

| Archivo | Tipo | Slice |
|---|---|---|
| `geoportal/api/geoportal.types.ts` | Modificar — nuevos tipos | GEO-2 |
| `geoportal/api/geoportal.api.ts` | Modificar — 4 nuevas funciones | GEO-2, 4, 5, 6, 7 |
| `geoportal/hooks/useStationDetail.ts` | **Nuevo** | GEO-2 |
| `geoportal/hooks/useStationAnimals.ts` | **Nuevo** | GEO-4 |
| `geoportal/hooks/useStationActivity.ts` | **Nuevo** | GEO-4 |
| `geoportal/hooks/useGeoportalStats.ts` | **Nuevo** | GEO-5 |
| `geoportal/hooks/useAnimalHistory.ts` | **Nuevo** | GEO-6 |
| `geoportal/hooks/useStationEvents.ts` | **Nuevo** | GEO-7 |
| `geoportal/components/StationMarker.tsx` | Modificar — scaling, arc, pulse | GEO-2 |
| `geoportal/components/GeoportalLegend.tsx` | **Nuevo** | GEO-2 |
| `geoportal/components/StationPopup.tsx` | **Nuevo** | GEO-2 |
| `geoportal/components/GeoportalSidebar.tsx` | Modificar — sector groups, chips, temporal | GEO-3 |
| `geoportal/components/TimePeriodSelector.tsx` | **Nuevo** | GEO-3 |
| `geoportal/components/StationDetailPanel.tsx` | Modificar — nueva estructura completa | GEO-4 |
| `geoportal/components/StationStatsGrid.tsx` | **Nuevo** | GEO-4 |
| `geoportal/components/VisitFrequencyChart.tsx` | **Nuevo** | GEO-4 |
| `geoportal/components/AnimalCard.tsx` | **Nuevo** | GEO-4 |
| `geoportal/components/RecentActivityFeed.tsx` | **Nuevo** | GEO-4 |
| `geoportal/components/DataContractTable.tsx` | **Nuevo** | GEO-4 |
| `geoportal/components/StatsModal.tsx` | **Nuevo** | GEO-5 |
| `geoportal/components/AnimalFeedingDashboard.tsx` | **Nuevo** | GEO-6 |
| `geoportal/components/TraceLayer.tsx` | **Nuevo** | GEO-6 |
| `geoportal/components/StationVisitsModal.tsx` | **Nuevo** | GEO-7 |
| `geoportal/components/ExportModal.tsx` | **Nuevo** | GEO-8 |
| `geoportal/pages/GeoportalPage.tsx` | Modificar — trace state, modals, time period | GEO-2, 3, 5, 6 |

---

## 12. Orden de Implementación

```
GEO-2 (Marcadores + endpoint detalle)
    ↓
GEO-3 (Sidebar sectores) ─── paralelo ─── GEO-4 (Panel detalle + actividad)
                                               ↓
                                          GEO-5 (Stats modal)
                                               ↓
                                          GEO-6 (Animal history + trace)
                                               ↓
                              GEO-7 (Visits modal) ─── GEO-8 (Export)
```

**GEO-2** debe ir primero porque establece el schema lean, el `AggregationService` y el endpoint de detalle que todos los siguientes slices consumen.

**GEO-3 y GEO-4** pueden desarrollarse en paralelo: no comparten archivos backend y solo GEO-3 modifica el sidebar mientras GEO-4 modifica el detail panel.

**GEO-7 y GEO-8** son independientes entre sí.

---

## 13. Features Omitidos

| Feature | Razón |
|---|---|
| Ficha Darwin Core / taxonomía | No hay datos taxonómicos en el sistema |
| Modal "Crear sector/zona" | Gestionado en `ZonesPage` |
| Modal "Crear estación" | Gestionado en `StationsPage` |
| Modal "Enlazar dispositivo" | Gestionado en `DevicesPage` |
| Foto de referencia de especie | Sin base de datos de imágenes de especies |
| Badge IUCN | Sin datos de conservación |
| Heatmap, clustering, filtros geográficos | PostGIS roadmap (sección 8) — no en MVP |

---

## 14. Definition of Done

Por cada sub-slice antes de hacer merge a `feature/slice-7-geoportal-v2`:

- [ ] Backend: todos los endpoints nuevos visibles en Swagger (`/docs`)
- [ ] Backend: `python -m pytest --tb=short -q` → 0 failures, 0 errors
- [ ] Backend: ningún endpoint nuevo tiene lógica de negocio en el router (solo delega al service)
- [ ] Backend: toda computación de stats pasa por `GeoportalAggregationService`
- [ ] Frontend: `./node_modules/.bin/tsc --noEmit` → 0 errors
- [ ] Frontend: feature verificado manualmente en navegador (golden path + edge cases)
- [ ] Frontend: sin `console.error` en DevTools durante navegación normal
- [ ] Frontend: FE-6 baseline no regresa (mapa carga, sidebar muestra estaciones, panel de detalle abre)
- [ ] Git: rama `feature/geo-X-nombre` con PR hacia `feature/slice-7-geoportal-v2`
