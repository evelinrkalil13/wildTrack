import type {
  AnimalMovement,
  FeedingEvent,
  GeoportalRecentEvent,
  GeoportalStationMapItem,
  SectorStatRow,
  StationEventDetail,
} from "../api/geoportal.types";

// ── Primitives ────────────────────────────────────────────────────────────────

function escapeCsv(val: unknown): string {
  const s = val == null ? "" : String(val);
  return s.includes(",") || s.includes('"') || s.includes("\n")
    ? `"${s.replace(/"/g, '""')}"`
    : s;
}

function row(cells: unknown[]): string {
  return cells.map(escapeCsv).join(",");
}

function download(content: string, filename: string, mime: string) {
  const bom = mime.includes("csv") ? "﻿" : "";
  const blob = new Blob([bom + content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Estaciones ────────────────────────────────────────────────────────────────

export function exportStationsCsv(
  stations: GeoportalStationMapItem[],
  filename = "wildtrack_estaciones.csv"
) {
  const header = row([
    "station_id", "code", "name",
    "zone_id", "zone_name",
    "latitude", "longitude",
    "status", "visitas_total", "identificadas", "sin_identificar",
  ]);

  const rows = stations.map((s) =>
    row([
      s.station_id, s.station_code, s.station_name,
      s.zone_id, s.zone_name,
      s.latitude, s.longitude,
      s.status, s.visitas_total, s.visitas_identificadas, s.visitas_sin_identificar,
    ])
  );

  download([header, ...rows].join("\r\n"), filename, "text/csv;charset=utf-8");
}

export function exportStationsGeoJson(
  stations: GeoportalStationMapItem[],
  filename = "wildtrack_estaciones.geojson"
) {
  const features = stations.map((s) => ({
    type: "Feature",
    geometry: { type: "Point", coordinates: [s.longitude, s.latitude] },
    properties: {
      station_id: s.station_id,
      code: s.station_code,
      name: s.station_name,
      zone_id: s.zone_id,
      zone_name: s.zone_name,
      status: s.status,
      visitas_total: s.visitas_total,
      visitas_identificadas: s.visitas_identificadas,
      visitas_sin_identificar: s.visitas_sin_identificar,
    },
  }));

  const geojson = {
    type: "FeatureCollection",
    name: "WildTrack_Estaciones",
    crs: { type: "name", properties: { name: "urn:ogc:def:crs:OGC:1.3:CRS84" } },
    generated: new Date().toISOString(),
    features,
  };

  download(JSON.stringify(geojson, null, 2), filename, "application/geo+json");
}

// ── Sectores ──────────────────────────────────────────────────────────────────

export function exportSectorsCsv(
  sectors: SectorStatRow[],
  filename = "wildtrack_sectores.csv"
) {
  const header = row([
    "zone_id", "zone_name",
    "num_estaciones", "visitas", "identificados", "sin_identificar",
    "pct_sin_id", "peso_promedio_g", "en_alerta",
  ]);

  const rows = sectors.map((s) =>
    row([
      s.zone_id, s.zone_name,
      s.num_estaciones, s.visitas, s.identificados, s.sin_identificar,
      s.pct_sin_id.toFixed(1), s.peso_promedio_g ?? "", s.en_alerta,
    ])
  );

  download([header, ...rows].join("\r\n"), filename, "text/csv;charset=utf-8");
}

// ── Individuos ────────────────────────────────────────────────────────────────

export function exportAnimalsCsv(
  animals: AnimalMovement[],
  filename = "wildtrack_individuos.csv"
) {
  const header = row([
    "animal_id", "rfid_tag", "species", "sex",
    "distinct_stations", "station_path",
  ]);

  const rows = animals.map((a) =>
    row([
      a.animal_id, a.rfid_tag, a.species, a.sex,
      a.distinct_stations, a.path_names.join(" → "),
    ])
  );

  download([header, ...rows].join("\r\n"), filename, "text/csv;charset=utf-8");
}

export function exportAnimalsJson(
  animals: AnimalMovement[],
  filename = "wildtrack_individuos.json"
) {
  const payload = {
    generated: new Date().toISOString(),
    total: animals.length,
    individuals: animals,
  };
  download(JSON.stringify(payload, null, 2), filename, "application/json");
}

// ── Visitas de estación (StationVisitsModal) ──────────────────────────────────

export function exportVisitsCsv(
  events: StationEventDetail[],
  stationId: string,
  filename = `wildtrack_${stationId}_visitas.csv`
) {
  const header = row([
    "event_id", "timestamp",
    "rfid_tag", "animal_id", "animal_species", "animal_sex",
    "is_identified",
    "consumed_g", "temperature_c", "humidity_pct",
    "media_count",
  ]);

  const rows = events.map((e) =>
    row([
      e.event_id, e.timestamp,
      e.rfid_tag ?? "", e.animal_id ?? "",
      e.animal_species ?? "", e.animal_sex ?? "",
      e.is_identified ? "1" : "0",
      e.consumed_g ?? "", e.temperature_c ?? "", e.humidity_pct ?? "",
      e.media_urls.length,
    ])
  );

  download([header, ...rows].join("\r\n"), filename, "text/csv;charset=utf-8");
}

// ── Timeline de animal (AnimalFeedingDashboard) ───────────────────────────────

export function exportTimelineCsv(
  timeline: FeedingEvent[],
  animalId: string,
  filename = `wildtrack_${animalId}_historial.csv`
) {
  const header = row([
    "event_id", "timestamp",
    "station_id", "station_name",
    "consumed_g", "temperature_c", "humidity_pct",
    "media_count",
  ]);

  const rows = timeline.map((e) =>
    row([
      e.event_id, e.timestamp,
      e.station_id, e.station_name,
      e.consumed_g ?? "", e.temperature_c ?? "", e.humidity_pct ?? "",
      e.media_urls.length,
    ])
  );

  download([header, ...rows].join("\r\n"), filename, "text/csv;charset=utf-8");
}

// ── Eventos recientes de estación (StationDetailPanel) ────────────────────────

export function exportRecentEventsCsv(
  events: GeoportalRecentEvent[],
  stationId: string,
  filename = `wildtrack_${stationId}_recientes.csv`
) {
  const header = row([
    "event_id", "timestamp",
    "rfid_tag", "consumed_g", "temperature_c", "humidity_pct",
    "photos_count",
  ]);

  const rows = events.map((e) =>
    row([
      e.event_id, e.timestamp,
      e.rfid_tag ?? "", e.consumed_g ?? "",
      e.temperature_c ?? "", e.humidity_pct ?? "",
      e.photos_count,
    ])
  );

  download([header, ...rows].join("\r\n"), filename, "text/csv;charset=utf-8");
}
