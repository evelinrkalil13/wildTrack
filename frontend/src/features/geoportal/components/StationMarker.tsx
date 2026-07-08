import { useMemo } from "react";
import { Marker, Tooltip } from "react-leaflet";
import L from "leaflet";
import type { GeoportalStationRead } from "../api/geoportal.types";
import { StationStatus } from "@/api/types/enums";

function effectiveColor(station: GeoportalStationRead): string {
  if (station.open_alerts_count > 0) return "#e08a1e";
  if (station.status === StationStatus.active) return "#52b788";
  if (station.status === StationStatus.maintenance) return "#e08a1e";
  return "#5f7669";
}

function createDivIcon(color: string, selected: boolean): L.DivIcon {
  const outer = selected
    ? `<circle cx="18" cy="18" r="17" fill="none" stroke="white" stroke-width="2.5"/>`
    : "";
  const html = `
    <svg width="36" height="36" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
      <circle cx="18" cy="18" r="16" fill="${color}" fill-opacity="0.18" stroke="${color}" stroke-width="2"/>
      <circle cx="18" cy="18" r="6" fill="${color}"/>
      ${outer}
    </svg>`;
  return L.divIcon({
    className: "",
    html,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
}

interface StationMarkerProps {
  station: GeoportalStationRead;
  selected: boolean;
  onClick: () => void;
}

export default function StationMarker({ station, selected, onClick }: StationMarkerProps) {
  const icon = useMemo(
    () => createDivIcon(effectiveColor(station), selected),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [station.status, station.open_alerts_count, selected]
  );

  return (
    <Marker
      position={[station.latitude, station.longitude]}
      icon={icon}
      eventHandlers={{ click: onClick }}
    >
      <Tooltip direction="top" offset={[0, -10]}>
        <strong>{station.station_code}</strong>
        <br />
        {station.station_name}
      </Tooltip>
    </Marker>
  );
}
