import { useEffect, useRef, useState } from "react";
import { Alert, Box, CircularProgress, Tooltip, Typography } from "@mui/material";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import { useGeoportalStations } from "../hooks/useGeoportalStations";
import GeoportalSidebar from "../components/GeoportalSidebar";
import StationMarker from "../components/StationMarker";
import StationDetailPanel from "../components/StationDetailPanel";
import type { GeoportalStationRead } from "../api/geoportal.types";

const TILE_LAYERS = {
  dark: {
    label: "Oscuro",
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution: '&copy; <a href="https://carto.com">CARTO</a>',
  },
  osm: {
    label: "Mapa",
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
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

// Colombia approximate center
const DEFAULT_CENTER: [number, number] = [4.5709, -74.2973];
const DEFAULT_ZOOM = 6;

function FitBoundsOnLoad({ stations }: { stations: GeoportalStationRead[] }) {
  const map = useMap();
  const hasFitted = useRef(false);

  useEffect(() => {
    if (stations.length > 0 && !hasFitted.current) {
      const bounds = L.latLngBounds(stations.map((s) => [s.latitude, s.longitude]));
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
      sx={{
        position: "absolute",
        top: 12,
        right: 12,
        zIndex: 1000,
        display: "flex",
        gap: 0.5,
      }}
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
  const { data, isLoading, isError, refetch } = useGeoportalStations();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeLayer, setActiveLayer] = useState<LayerKey>("dark");
  const [map, setMap] = useState<L.Map | null>(null);

  const stations = data ?? [];
  const selectedStation = stations.find((s) => s.station_id === selectedId) ?? null;

  function handleSelect(station: GeoportalStationRead) {
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
      {/* Sidebar */}
      <GeoportalSidebar
        stations={stations}
        selectedStationId={selectedId}
        onSelect={handleSelect}
        isLoading={isLoading}
      />

      {/* Map area */}
      <Box sx={{ flex: 1, position: "relative", overflow: "hidden" }}>
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
          <Box sx={{ position: "absolute", top: 12, left: "50%", transform: "translateX(-50%)", zIndex: 1200, maxWidth: 420 }}>
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
              onClick={() => handleSelect(station)}
            />
          ))}
        </MapContainer>

        <LayerSwitcher activeLayer={activeLayer} onChange={setActiveLayer} />
      </Box>

      {/* Detail panel */}
      {selectedStation && (
        <StationDetailPanel station={selectedStation} onClose={handleClose} />
      )}
    </Box>
  );
}
