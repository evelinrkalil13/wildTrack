import type { GeoportalStationMapItem } from "../api/geoportal.types";
import { StationStatus } from "@/api/types/enums";

const STATUS_LABEL: Record<StationStatus, string> = {
  [StationStatus.active]: "En línea",
  [StationStatus.inactive]: "Inactiva",
  [StationStatus.maintenance]: "Alerta",
  [StationStatus.offline]: "Sin señal",
};

const STATUS_COLOR: Record<StationStatus, string> = {
  [StationStatus.active]: "#52b788",
  [StationStatus.inactive]: "#5f7669",
  [StationStatus.maintenance]: "#e08a1e",
  [StationStatus.offline]: "#5f7669",
};

interface Props {
  station: GeoportalStationMapItem;
  onSelectDetail: () => void;
}

export default function StationPopup({ station, onSelectDetail }: Props) {
  const statusColor = STATUS_COLOR[station.status];
  const statusLabel = STATUS_LABEL[station.status];

  return (
    <div className="wt-popup">
      <div className="wt-popup-head">
        <span className="wt-popup-id">{station.station_code}</span>
        <span className="wt-popup-status" style={{ color: statusColor }}>
          ● {statusLabel}
        </span>
      </div>
      <div className="wt-popup-name">{station.station_name}</div>
      {station.is_live && (
        <div className="wt-popup-live">📡 EN VIVO</div>
      )}
      <div
        className="wt-popup-sector"
        style={{ borderColor: station.zone_color, color: station.zone_color }}
      >
        {station.zone_name}
      </div>
      <div className="wt-popup-stats">
        <div className="wt-popup-stat">
          <span className="wt-popup-stat-v">{station.visitas_total}</span>
          <span className="wt-popup-stat-k">Visitas</span>
        </div>
        <div className="wt-popup-stat">
          <span className="wt-popup-stat-v" style={{ color: "#52b788" }}>
            {station.visitas_identificadas}
          </span>
          <span className="wt-popup-stat-k">Identificados</span>
        </div>
        <div className="wt-popup-stat">
          <span className="wt-popup-stat-v" style={{ color: "#e08a1e" }}>
            {station.visitas_sin_identificar}
          </span>
          <span className="wt-popup-stat-k">Sin ID</span>
        </div>
      </div>
      <div className="wt-popup-row">
        <span className="wt-popup-lbl">Peso promedio</span>
        <span>—</span>
      </div>
      <div className="wt-popup-row">
        <span className="wt-popup-lbl">Último registro</span>
        <span>—</span>
      </div>
      <div className="wt-popup-row">
        <span className="wt-popup-lbl">Coordenadas</span>
        <span className="wt-popup-mono">
          {station.latitude.toFixed(4)}, {station.longitude.toFixed(4)}
        </span>
      </div>
      {station.open_alerts_count > 0 && (
        <div className="wt-popup-row" style={{ color: "#e08a1e" }}>
          <span className="wt-popup-lbl" style={{ color: "#e08a1e" }}>
            Alertas
          </span>
          <span>{station.open_alerts_count} abiertas</span>
        </div>
      )}
      <button
        className="wt-popup-btn"
        data-station-id={station.station_id}
        onClick={onSelectDetail}
      >
        Ver detalles →
      </button>
    </div>
  );
}
