import { useEffect } from "react";
import { useMap, Polyline, Marker, Tooltip } from "react-leaflet";
import L from "leaflet";
import type { AnimalMovement, GeoportalStationMapItem } from "../api/geoportal.types";

// Numbered amber stop marker matching reference .trace-stop-marker
function makeStopIcon(num: number): L.DivIcon {
  return L.divIcon({
    html: `<div class="wt-trace-stop">${num}</div>`,
    className: "wt-trace-stop-wrap",
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
}

interface TraceLayerProps {
  movement: AnimalMovement;
  stations: GeoportalStationMapItem[];
}

export default function TraceLayer({ movement, stations }: TraceLayerProps) {
  const map = useMap();

  const stationMap = new Map(stations.map((s) => [s.station_id, s]));

  // Build ordered stop list from deduped path
  const stops = movement.path
    .map((sid, i) => {
      const s = stationMap.get(sid);
      if (!s) return null;
      return {
        lat: s.latitude,
        lng: s.longitude,
        name: movement.path_names[i] ?? sid,
        stopNum: i + 1,
      };
    })
    .filter(Boolean) as { lat: number; lng: number; name: string; stopNum: number }[];

  const coords: [number, number][] = stops.map((s) => [s.lat, s.lng]);

  // Fit map to trace when mounted
  useEffect(() => {
    if (coords.length === 0) return;
    const bounds = L.latLngBounds(coords);
    if (bounds.isValid()) {
      map.fitBounds(bounds.pad(0.4), { duration: 0.7 });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (stops.length === 0) return null;

  return (
    <>
      {/* Dashed polyline path */}
      <Polyline
        positions={coords}
        pathOptions={{ color: "#e08a1e", weight: 3, dashArray: "8 5", opacity: 0.9 }}
      />

      {/* Numbered stop markers */}
      {stops.map((stop, i) => (
        <Marker
          key={`trace-stop-${i}`}
          position={[stop.lat, stop.lng]}
          icon={makeStopIcon(stop.stopNum)}
          zIndexOffset={500 + i}
        >
          <Tooltip
            permanent={false}
            direction="top"
            offset={[0, -14]}
            opacity={0.97}
            className="wt-trace-tooltip"
          >
            <span>
              <strong>#{stop.stopNum}</strong> {stop.name}
            </span>
          </Tooltip>
        </Marker>
      ))}
    </>
  );
}
