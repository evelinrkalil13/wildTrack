import { useEffect, useRef, useState } from "react";
import "../components/GeoportalSidebar.css";
import { Alert, Box, CircularProgress, Tooltip, Typography } from "@mui/material";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import { useGeoportalStations } from "../hooks/useGeoportalStations";
import GeoportalSidebar from "../components/GeoportalSidebar";
import StationMarker from "../components/StationMarker";
import StationDetailPanel from "../components/StationDetailPanel";
import GeoportalLegend from "../components/GeoportalLegend";
import StatsModal from "../components/StatsModal";
import TraceLayer from "../components/TraceLayer";
import AnimalFeedingDashboard from "../components/AnimalFeedingDashboard";
import StationVisitsModal from "../components/StationVisitsModal";
import ExportModal from "../components/ExportModal";
import { useGeoportalStats } from "../hooks/useGeoportalStats";
import type {
  AnimalHistoryResponse,
  AnimalMovement,
  GeoportalStationMapItem,
  TimePeriod,
} from "../api/geoportal.types";

// Injected once into the document: marker + popup CSS matching the reference geoportal
const GEOPORTAL_CSS = `
.marker-ring { background: transparent !important; border: none !important; }

.wt-live-pulse {
  transform-box: fill-box;
  transform-origin: center;
  animation: wtLivePulse 1.8s ease-out infinite;
}
@keyframes wtLivePulse {
  0%   { transform: scale(0.85); opacity: 0.8; }
  100% { transform: scale(1.9); opacity: 0; }
}

.wt-leaflet-popup .leaflet-popup-content-wrapper {
  background: rgba(22,36,29,0.97) !important;
  border: 1px solid #2a4035 !important;
  border-radius: 13px !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5) !important;
  padding: 0 !important;
  color: #e8f0ea !important;
  font-family: 'Inter', system-ui, sans-serif !important;
  backdrop-filter: blur(8px);
}
.wt-leaflet-popup .leaflet-popup-tip-container { display: none; }
.wt-leaflet-popup .leaflet-popup-content { margin: 0 !important; width: auto !important; }
.wt-leaflet-popup .leaflet-popup-close-button {
  color: #8aa395 !important; font-size: 18px !important;
  top: 8px !important; right: 10px !important;
}
.wt-leaflet-popup .leaflet-popup-close-button:hover { color: #e8f0ea !important; }

.wt-popup { padding: 14px 16px; min-width: 230px; }
.wt-popup-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.wt-popup-id { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 10.5px; color: #e08a1e; letter-spacing: 0.4px; }
.wt-popup-status { font-size: 10.5px; font-weight: 500; }
.wt-popup-name { font-family: 'Space Grotesk', sans-serif; font-size: 15px; font-weight: 600; line-height: 1.3; color: #e8f0ea; margin-bottom: 7px; padding-right: 18px; }
.wt-popup-live { display: inline-block; font-size: 10.5px; font-weight: 600; color: #93c5fd; background: rgba(59,130,246,0.16); border: 1px solid #3b82f6; padding: 3px 8px; border-radius: 6px; margin-bottom: 9px; letter-spacing: 0.2px; }
.wt-popup-sector { display: inline-block; font-size: 10.5px; font-weight: 500; padding: 2px 8px; border-radius: 5px; border: 1px solid; margin-bottom: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
.wt-popup-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 11px; background: rgba(15,26,21,0.6); border-radius: 9px; padding: 9px 8px; }
.wt-popup-stat { text-align: center; }
.wt-popup-stat-v { display: block; font-family: 'Space Grotesk', sans-serif; font-size: 18px; font-weight: 600; line-height: 1; color: #e8f0ea; }
.wt-popup-stat-k { display: block; font-size: 9.5px; color: #8aa395; margin-top: 3px; text-transform: uppercase; letter-spacing: 0.4px; }
.wt-popup-row { display: flex; justify-content: space-between; align-items: baseline; font-size: 11.5px; padding: 4px 0; border-top: 1px solid rgba(42,64,53,0.6); color: #e8f0ea; }
.wt-popup-lbl { color: #8aa395; }
.wt-popup-mono { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; }
.wt-popup-btn { display: block; width: 100%; margin-top: 11px; background: #2d6a4f; color: #fff; border: 1px solid #2d6a4f; border-radius: 8px; padding: 8px 12px; font-size: 12.5px; font-weight: 500; font-family: 'Inter', sans-serif; cursor: pointer; text-align: center; transition: background 0.13s; }
.wt-popup-btn:hover { background: #52b788; border-color: #52b788; }

/* ── Trace layer ── */
.wt-trace-stop-wrap { background: transparent !important; border: none !important; }
.wt-trace-stop {
  width: 22px; height: 22px; border-radius: 50%;
  background: #e08a1e; color: #1a1206; border: 2px solid #fff;
  display: flex; align-items: center; justify-content: center;
  font-family: 'Space Grotesk', sans-serif; font-size: 11px; font-weight: 700;
  box-shadow: 0 1px 6px rgba(0,0,0,0.5);
}
.wt-trace-tooltip {
  background: rgba(22,36,29,0.95) !important;
  border: 1px solid #e08a1e !important;
  border-radius: 7px !important;
  color: #e8f0ea !important;
  font-size: 12px !important;
  font-family: 'Inter', sans-serif !important;
  box-shadow: 0 4px 14px rgba(0,0,0,0.4) !important;
  padding: 5px 10px !important;
}
.wt-trace-tooltip::before { display: none !important; }

/* ── Trace banner ── */
.wt-trace-banner {
  position: absolute; top: 12px; left: 50%; transform: translateX(-50%);
  z-index: 1010;
  background: rgba(22,36,29,0.96); border: 1px solid #e08a1e;
  border-radius: 10px; padding: 10px 16px;
  display: flex; align-items: center; gap: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.45);
  font-family: 'Inter', sans-serif; color: #e8f0ea;
  backdrop-filter: blur(6px); white-space: nowrap;
}
.wt-trace-banner-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #e08a1e; box-shadow: 0 0 6px #e08a1e; flex-shrink: 0;
}
.wt-trace-banner-text { font-size: 13px; }
.wt-trace-banner-text strong { color: #e08a1e; font-weight: 600; }
.wt-trace-banner-exits {
  font-size: 11.5px; font-weight: 600; color: #e8f0ea;
  background: rgba(255,255,255,0.08); border: 1px solid #2a4035;
  border-radius: 6px; padding: 4px 10px; cursor: pointer;
  transition: background 0.13s;
}
.wt-trace-banner-exits:hover { background: rgba(255,255,255,0.16); }
`;

const TILE_LAYERS = {
  dark: {
    label: "Oscuro",
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution: '&copy; <a href="https://carto.com">CARTO</a>',
  },
  osm: {
    label: "Mapa",
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution:
      '&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
  },
  terrain: {
    label: "Terreno",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
    attribution: "&copy; Esri",
  },
  satellite: {
    label: "Satélite",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "&copy; Esri",
  },
} as const;

type LayerKey = keyof typeof TILE_LAYERS;

const DEFAULT_CENTER: [number, number] = [4.5709, -74.2973];
const DEFAULT_ZOOM = 6;

function FitBoundsOnLoad({ stations }: { stations: GeoportalStationMapItem[] }) {
  const map = useMap();
  const hasFitted = useRef(false);

  useEffect(() => {
    if (stations.length > 0 && !hasFitted.current) {
      const bounds = L.latLngBounds(
        stations.map((s) => [s.latitude, s.longitude])
      );
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
        hasFitted.current = true;
      }
    }
  }, [map, stations]);

  return null;
}

function LayerSwitcher({
  activeLayer,
  onChange,
}: {
  activeLayer: LayerKey;
  onChange: (l: LayerKey) => void;
}) {
  return (
    <Box
      sx={{ position: "absolute", top: 12, right: 12, zIndex: 1000, display: "flex", gap: 0.5 }}
    >
      {(Object.keys(TILE_LAYERS) as LayerKey[]).map((key) => (
        <Tooltip key={key} title={TILE_LAYERS[key].label}>
          <Box
            onClick={() => onChange(key)}
            sx={{
              px: 1,
              py: 0.4,
              borderRadius: 1,
              cursor: "pointer",
              fontSize: "0.72rem",
              fontWeight: activeLayer === key ? 700 : 400,
              bgcolor: activeLayer === key ? "primary.main" : "background.paper",
              color: activeLayer === key ? "primary.contrastText" : "text.secondary",
              border: "1px solid",
              borderColor: activeLayer === key ? "primary.main" : "divider",
              userSelect: "none",
              "&:hover": { bgcolor: activeLayer === key ? "primary.dark" : "action.hover" },
            }}
          >
            {TILE_LAYERS[key].label}
          </Box>
        </Tooltip>
      ))}
    </Box>
  );
}

export default function GeoportalPage() {
  const [timePeriod, setTimePeriod] = useState<TimePeriod>("7d");
  const { data, isLoading, isError, refetch } = useGeoportalStations(timePeriod);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeLayer, setActiveLayer] = useState<LayerKey>("dark");
  const [map, setMap] = useState<L.Map | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showStats, setShowStats] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [traceAnimal, setTraceAnimal] = useState<AnimalMovement | null>(null);
  const [dashboardAnimalId, setDashboardAnimalId] = useState<string | null>(null);
  const [visitsStationId, setVisitsStationId] = useState<string | null>(null);

  const { data: stats } = useGeoportalStats(timePeriod);

  const stations = data ?? [];
  const selectedSummary =
    stations.find((s) => s.station_id === selectedId) ?? null;

  function handleSelectDetail(station: GeoportalStationMapItem) {
    setSelectedId(station.station_id);
    map?.flyTo([station.latitude, station.longitude], Math.max(map.getZoom(), 13), {
      duration: 0.7,
    });
  }

  function handleClose() {
    setSelectedId(null);
  }

  return (
    <Box sx={{ display: "flex", height: "calc(100vh - 64px)", overflow: "hidden" }}>
      <style>{GEOPORTAL_CSS}</style>

      {/* Export modal */}
      {showExport && (
        <ExportModal
          stations={stations}
          sectors={stats?.sectores ?? []}
          animals={stats?.animales_con_chip ?? []}
          onClose={() => setShowExport(false)}
        />
      )}

      {/* Stats modal */}
      {showStats && (
        <StatsModal
          timePeriod={timePeriod}
          onClose={() => setShowStats(false)}
          onTraceAnimal={(m) => {
            setTraceAnimal(m);
            setShowStats(false);
          }}
        />
      )}

      {/* Station visits modal */}
      {visitsStationId && (
        <StationVisitsModal
          stationId={visitsStationId}
          timePeriod={timePeriod}
          onClose={() => setVisitsStationId(null)}
        />
      )}

      {/* Animal feeding dashboard */}
      {dashboardAnimalId && (
        <AnimalFeedingDashboard
          animalId={dashboardAnimalId}
          initialPeriod="all"
          onClose={() => setDashboardAnimalId(null)}
          onTrace={(history: AnimalHistoryResponse) => {
            // Convert trace_path → synthetic AnimalMovement for the existing TraceLayer
            const syntheticMovement: AnimalMovement = {
              animal_id: history.animal_id,
              rfid_tag: history.rfid_tag,
              species: history.species,
              sex: history.sex,
              distinct_stations: new Set(history.trace_path.map((s) => s.station_id)).size,
              path: history.trace_path.map((s) => s.station_id),
              path_names: history.trace_path.map((s) => s.station_name),
            };
            setTraceAnimal(syntheticMovement);
            setDashboardAnimalId(null);
          }}
        />
      )}

      {/* Sidebar */}
      <GeoportalSidebar
        stations={stations}
        selectedStationId={selectedId}
        onSelect={handleSelectDetail}
        isLoading={isLoading}
        timePeriod={timePeriod}
        onTimePeriodChange={setTimePeriod}
        open={sidebarOpen}
        onStatsOpen={() => setShowStats(true)}
        onExportOpen={() => setShowExport(true)}
      />

      {/* Map area */}
      <Box sx={{ flex: 1, position: "relative", overflow: "hidden" }}>
        {/* Sidebar toggle tab — always visible on the map left edge */}
        <button
          className="wt-sidebar-toggle-tab"
          onClick={() => setSidebarOpen((v) => !v)}
          title={sidebarOpen ? "Ocultar panel lateral" : "Mostrar panel lateral"}
          aria-label={sidebarOpen ? "Ocultar sidebar" : "Mostrar sidebar"}
        >
          {sidebarOpen ? "‹" : "›"}
        </button>
        {isLoading && (
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              zIndex: 1200,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: "rgba(15, 26, 21, 0.6)",
            }}
          >
            <CircularProgress color="primary" size={48} />
          </Box>
        )}

        {isError && (
          <Box
            sx={{
              position: "absolute",
              top: 12,
              left: "50%",
              transform: "translateX(-50%)",
              zIndex: 1200,
              maxWidth: 420,
            }}
          >
            <Alert
              severity="error"
              action={
                <Typography
                  variant="caption"
                  sx={{ cursor: "pointer", textDecoration: "underline" }}
                  onClick={() => refetch()}
                >
                  Reintentar
                </Typography>
              }
            >
              Error al cargar las estaciones.
            </Alert>
          </Box>
        )}

        <MapContainer
          ref={setMap}
          center={DEFAULT_CENTER}
          zoom={DEFAULT_ZOOM}
          style={{ height: "100%", width: "100%" }}
          zoomControl
        >
          <TileLayer
            key={activeLayer}
            url={TILE_LAYERS[activeLayer].url}
            attribution={TILE_LAYERS[activeLayer].attribution}
          />

          <FitBoundsOnLoad stations={stations} />

          {stations.map((station) => (
            <StationMarker
              key={station.station_id}
              station={station}
              selected={station.station_id === selectedId}
              onSelectDetail={handleSelectDetail}
            />
          ))}

          {traceAnimal && (
            <TraceLayer movement={traceAnimal} stations={stations} />
          )}
        </MapContainer>

        {/* Trace banner — rendered over map when a trace is active */}
        {traceAnimal && (
          <div className="wt-trace-banner">
            <span className="wt-trace-banner-dot" />
            <span className="wt-trace-banner-text">
              Trazabilidad{" "}
              <strong>{traceAnimal.rfid_tag}</strong>
              {" · "}
              {traceAnimal.species}
              {" · "}
              {traceAnimal.distinct_stations} estaciones
            </span>
            <button
              className="wt-trace-banner-exits"
              onClick={() => setTraceAnimal(null)}
            >
              ✕ Salir
            </button>
          </div>
        )}

        <LayerSwitcher activeLayer={activeLayer} onChange={setActiveLayer} />

        {/* Legend — rendered over the map, outside MapContainer */}
        <GeoportalLegend />
      </Box>

      {/* Detail panel — opens when a station is selected */}
      {selectedId && selectedSummary && (
        <StationDetailPanel
          stationId={selectedId}
          stationSummary={selectedSummary}
          timePeriod={timePeriod}
          onClose={handleClose}
          onOpenHistory={(animalId) => setDashboardAnimalId(animalId)}
          onOpenVisits={() => setVisitsStationId(selectedId)}
        />
      )}
    </Box>
  );
}
