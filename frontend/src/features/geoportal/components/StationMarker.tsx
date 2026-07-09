import { useMemo } from "react";
import { Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import type { GeoportalStationMapItem } from "../api/geoportal.types";
import { StationStatus } from "@/api/types/enums";
import StationPopup from "./StationPopup";

const COLORS = {
  forest: "#2d6a4f",
  amber: "#e08a1e",
  muted: "#5f7669",
  live: "#3b82f6",
};

function buildDivIcon(
  station: GeoportalStationMapItem,
  selected: boolean
): L.DivIcon {
  const visitas = station.visitas_total;
  const isLive = station.is_live;
  const r = Math.max(11, Math.min(26, 11 + visitas * 0.55));
  const size = (r + (isLive ? 10 : 6)) * 2;
  const c = size / 2;

  const baseColor =
    station.status === StationStatus.offline
      ? COLORS.muted
      : isLive
        ? COLORS.live
        : station.open_alerts_count > 0
          ? COLORS.amber
          : COLORS.forest;

  const noIdFrac = visitas > 0 ? station.visitas_sin_identificar / visitas : 0;
  const circumference = 2 * Math.PI * r;
  const amberArc = circumference * noIdFrac;

  const pulse = isLive
    ? `<circle cx="${c}" cy="${c}" r="${r + 3}" fill="none" stroke="${COLORS.live}" stroke-width="2" class="wt-live-pulse"/>`
    : "";

  const ring = `
    ${pulse}
    <circle cx="${c}" cy="${c}" r="${r}" fill="${baseColor}" fill-opacity="0.85"
      stroke="${selected ? "#fff" : "#16241d"}" stroke-width="${selected ? 3 : 2}"/>
    <circle cx="${c}" cy="${c}" r="${r}" fill="none" stroke="${COLORS.amber}" stroke-width="4"
      stroke-dasharray="${amberArc.toFixed(1)} ${circumference.toFixed(1)}" transform="rotate(-90 ${c} ${c})" stroke-linecap="round"/>
    <text x="${c}" y="${c + 4}" text-anchor="middle" fill="#fff"
      font-family="'Space Grotesk',sans-serif" font-size="${r > 16 ? 13 : 11}" font-weight="600">${visitas}</text>
  `;

  const html = `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">${ring}</svg>`;
  return L.divIcon({ html, className: "marker-ring", iconSize: [size, size], iconAnchor: [c, c] });
}

interface StationMarkerProps {
  station: GeoportalStationMapItem;
  selected: boolean;
  onSelectDetail: (station: GeoportalStationMapItem) => void;
}

export default function StationMarker({
  station,
  selected,
  onSelectDetail,
}: StationMarkerProps) {
  const map = useMap();

  const icon = useMemo(
    () => buildDivIcon(station, selected),
    // Rebuild when these fields change
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      station.status,
      station.open_alerts_count,
      station.is_live,
      station.visitas_total,
      station.visitas_sin_identificar,
      selected,
    ]
  );

  function handleSelectDetail() {
    map.closePopup();
    onSelectDetail(station);
  }

  return (
    <Marker position={[station.latitude, station.longitude]} icon={icon}>
      <Popup className="wt-leaflet-popup" maxWidth={280}>
        <StationPopup station={station} onSelectDetail={handleSelectDetail} />
      </Popup>
    </Marker>
  );
}
