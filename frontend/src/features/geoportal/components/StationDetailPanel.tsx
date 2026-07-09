import "./StationDetailPanel.css";
import "./ExportModal.css";
import type {
  ActivityItem,
  ActivityItemType,
  GeoportalAnimalRead,
  GeoportalStationMapItem,
  TimePeriod,
} from "../api/geoportal.types";
import { exportRecentEventsCsv } from "../lib/exportData";
import { StationStatus } from "@/api/types/enums";
import { useStationDetail } from "../hooks/useStationDetail";
import { useStationAnimals } from "../hooks/useStationAnimals";
import { useStationActivity } from "../hooks/useStationActivity";

const DIAS = ["L", "M", "X", "J", "V", "S", "D"];

const ACTIVITY_ICON: Record<ActivityItemType, string> = {
  feeding: "🌿",
  rfid_read: "📡",
  photo: "📷",
  alert: "⚠️",
  telemetry: "📶",
};

const SEX_LABEL: Record<string, string> = {
  male: "♂ Macho",
  female: "♀ Hembra",
  M: "♂ Macho",
  F: "♀ Hembra",
  unknown: "? Desc.",
  desconocido: "? Desc.",
};

const STATUS_LABEL: Record<StationStatus, string> = {
  [StationStatus.active]: "en línea",
  [StationStatus.inactive]: "inactiva",
  [StationStatus.maintenance]: "en mantenimiento",
  [StationStatus.offline]: "sin reportar",
};

function statusDotKey(
  status: StationStatus,
  openAlerts: number
): "online" | "alert" | "offline" {
  if (status === StationStatus.active && openAlerts === 0) return "online";
  if (openAlerts > 0) return "alert";
  return "offline";
}

function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  const min = Math.floor(ms / 60000);
  if (min < 1) return "hace un momento";
  if (min < 60) return `hace ${min} min`;
  const h = Math.floor(min / 60);
  if (h < 24) return `hace ${h} h`;
  return `hace ${Math.floor(h / 24)} días`;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("es-CO", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

interface StationDetailPanelProps {
  stationId: string;
  stationSummary: GeoportalStationMapItem;
  timePeriod: TimePeriod;
  onClose: () => void;
  onOpenHistory: (animalId: string) => void;
  onOpenVisits?: () => void;
  onOpenDarwinCore?: (animalId: string) => void;
}

export default function StationDetailPanel({
  stationId,
  stationSummary,
  timePeriod,
  onClose,
  onOpenHistory,
  onOpenVisits,
  onOpenDarwinCore,
}: StationDetailPanelProps) {
  const { data: detail, isPending: detailPending } = useStationDetail(
    stationId,
    timePeriod
  );
  const { data: animals = [], isPending: animalsPending } = useStationAnimals(
    stationId,
    timePeriod
  );
  const { data: activity = [], isPending: activityPending } =
    useStationActivity(stationId);

  const station = detail ?? stationSummary;
  const dotKey = statusDotKey(station.status, station.open_alerts_count);

  // Last visit from first activity item
  const lastVisitIso =
    activity.find((a) => a.item_type === "feeding" || a.item_type === "rfid_read")
      ?.timestamp ?? null;

  // Frequency chart
  const visitas = detail?.visitas_por_dia ?? [0, 0, 0, 0, 0, 0, 0];
  const peak = Math.max(...visitas);

  return (
    <div className="wt-detail">
      {/* ── Head ── */}
      <div className="wt-detail-head">
        <div className="wt-detail-head-actions">
          {detail?.recent_events && detail.recent_events.length > 0 && (
            <button
              className="btn-download-inline"
              title="Descargar eventos recientes (CSV)"
              aria-label="Descargar CSV"
              onClick={() =>
                exportRecentEventsCsv(detail.recent_events, stationId)
              }
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 16l-5-5h3V4h4v7h3l-5 5zm-6 2h12v2H6v-2z" />
              </svg>
              CSV
            </button>
          )}
          <button className="wt-detail-close" onClick={onClose} aria-label="Cerrar panel">
            ×
          </button>
        </div>
        <div className="wt-detail-eyebrow">
          {stationSummary.station_code}
          {station.is_live && (
            <span className="wt-detail-live-badge" style={{ marginLeft: 8 }}>
              📡 EN VIVO
            </span>
          )}
        </div>
        <h2 className="wt-detail-title">{stationSummary.station_name}</h2>
        <div className="wt-detail-meta">
          <span
            className="wt-detail-status-dot"
            data-s={dotKey}
          />
          <span>
            Última visita {timeAgo(lastVisitIso)} · {STATUS_LABEL[station.status]}
          </span>
        </div>
      </div>

      {/* ── Body ── */}
      <div className="wt-detail-body">

        {/* Alerts banner */}
        {station.open_alerts_count > 0 && (
          <div className="wt-alerts-banner">
            <span>⚠️</span>
            <span>
              {station.open_alerts_count}{" "}
              {station.open_alerts_count === 1 ? "alerta abierta" : "alertas abiertas"}
            </span>
          </div>
        )}

        {/* Zona */}
        <span
          className="wt-zone-chip"
          style={{
            borderColor: stationSummary.zone_color,
            color: stationSummary.zone_color,
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: stationSummary.zone_color,
              flexShrink: 0,
              display: "inline-block",
            }}
          />
          {stationSummary.zone_name}
        </span>

        {/* Stats grid */}
        <div className="wt-section-label" style={{ marginTop: 16 }}>Estadísticas</div>
        {detailPending && !detail ? (
          <SkeletonBlock />
        ) : (
          <>
            <div className="wt-stats-grid">
              <div
                className="wt-stat"
                onClick={onOpenVisits}
                style={
                  onOpenVisits
                    ? { cursor: "pointer", outline: "1px solid transparent" }
                    : undefined
                }
                title={onOpenVisits ? "Ver listado de visitas" : undefined}
              >
                <div
                  className="v"
                  style={onOpenVisits ? { color: "#52b788" } : undefined}
                >
                  {station.visitas_total}
                </div>
                <div className="k">Visitas ↗</div>
              </div>
              <div className="wt-stat peso">
                <div className="v">
                  {detail?.peso_promedio_g != null
                    ? `${detail.peso_promedio_g} g`
                    : "—"}
                </div>
                <div className="k">Peso prom.</div>
              </div>
              <div className="wt-stat peso">
                <div className="v">
                  {detail?.peso_mediana_g != null
                    ? `${detail.peso_mediana_g} g`
                    : "—"}
                </div>
                <div className="k">Mediana</div>
              </div>
            </div>
            <div className="wt-split">
              <div className="wt-stat id">
                <div className="v">{station.visitas_identificadas}</div>
                <div className="k">Identificados</div>
              </div>
              <div className="wt-stat noid">
                <div className="v">{station.visitas_sin_identificar}</div>
                <div className="k">Sin ID</div>
              </div>
            </div>
          </>
        )}

        {/* Frequency chart */}
        <div className="wt-section-label">Frecuencia por día</div>
        {detailPending && !detail ? (
          <SkeletonBlock height={88} />
        ) : (
          <div className="wt-bars" role="img" aria-label="Visitas por día de la semana">
            {visitas.map((v, i) => (
              <div
                className="wt-bar-col"
                key={i}
                data-peak={String(v === peak && peak > 0)}
              >
                <div
                  className="wt-bar"
                  style={{ height: `${peak > 0 ? (v / peak) * 100 : 0}%` }}
                  title={`${v} visitas`}
                />
                <div className="wt-bar-lbl">{DIAS[i]}</div>
              </div>
            ))}
          </div>
        )}

        {/* Telemetry inline */}
        {(detail?.latest_telemetry || (!detailPending && detail)) && (
          <>
            <div className="wt-section-label">Última telemetría</div>
            {detailPending && !detail ? (
              <SkeletonBlock />
            ) : detail?.latest_telemetry ? (
              <div style={{ border: "1px solid #2a4035", borderRadius: 10, padding: "4px 12px" }}>
                {detail.latest_telemetry.temperature_c != null && (
                  <TRow label="Temperatura" value={`${detail.latest_telemetry.temperature_c.toFixed(1)} °C`} />
                )}
                {detail.latest_telemetry.humidity_pct != null && (
                  <TRow label="Humedad" value={`${detail.latest_telemetry.humidity_pct.toFixed(1)} %`} />
                )}
                {detail.latest_telemetry.wifi_rssi_dbm != null && (
                  <TRow label="RSSI Wi-Fi" value={`${detail.latest_telemetry.wifi_rssi_dbm} dBm`} />
                )}
                {detail.latest_telemetry.firmware_version && (
                  <TRow label="Firmware" value={detail.latest_telemetry.firmware_version} mono />
                )}
                <TRow label="Registrado" value={formatTime(detail.latest_telemetry.timestamp)} />
              </div>
            ) : null}
          </>
        )}

        {/* Animals / Individuos */}
        <div className="wt-section-label">
          <span>Individuos con chip ({animals.length})</span>
        </div>
        {animalsPending ? (
          <SkeletonBlock />
        ) : animals.length === 0 ? (
          <div className="wt-ind-empty">Ningún individuo registrado en este periodo.</div>
        ) : (
          <div className="wt-ind-list">
            {animals.map((animal) => (
              <AnimalCard
                key={animal.animal_id}
                animal={animal}
                onOpenHistory={onOpenHistory}
                onOpenDarwinCore={onOpenDarwinCore}
              />
            ))}
          </div>
        )}

        {/* Activity feed */}
        <div className="wt-section-label">Actividad reciente</div>
        {activityPending ? (
          <>
            <SkeletonBlock height={50} />
            <SkeletonBlock height={50} style={{ marginTop: 6 }} />
          </>
        ) : activity.length === 0 ? (
          <div className="wt-activity-empty">Sin actividad registrada.</div>
        ) : (
          <div className="wt-activity-list">
            {activity.map((item, i) => (
              <ActivityFeedItem key={i} item={item} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function AnimalCard({
  animal,
  onOpenHistory,
  onOpenDarwinCore,
}: {
  animal: GeoportalAnimalRead;
  onOpenHistory: (animalId: string) => void;
  onOpenDarwinCore?: (animalId: string) => void;
}) {
  return (
    <div className="wt-ind-card">
      <div className="wt-ind-header">
        <span className="wt-ind-id">{animal.animal_id.slice(0, 8).toUpperCase()}</span>
        <span className="wt-ind-sex">{SEX_LABEL[animal.sex] ?? animal.sex}</span>
      </div>
      <div className="wt-ind-name">{animal.species}</div>
      {animal.estimated_age && (
        <div className="wt-ind-species">{animal.estimated_age}</div>
      )}
      <div className="wt-ind-chip">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor" style={{ flexShrink: 0 }}>
          <path d="M7 2v2H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h2v2h2v-2h6v2h2v-2h2a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2V2h-2v2H9V2zm0 6h10v8H7z" />
        </svg>
        {animal.rfid_tag}
      </div>
      <div className="wt-ind-meta">
        {animal.total_visits} visitas
        {animal.avg_consumed_g != null && ` · ${animal.avg_consumed_g} g prom.`}
        {animal.last_visit && ` · último ${timeAgo(animal.last_visit)}`}
      </div>
      {animal.notes && <div className="wt-ind-notes">{animal.notes}</div>}
      <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
        <button
          className="wt-ind-history-btn"
          style={{ flex: 1 }}
          onClick={() => onOpenHistory(animal.animal_id)}
        >
          Ver historial →
        </button>
        {onOpenDarwinCore && (
          <button
            className="wt-ind-history-btn"
            style={{ flex: 1, borderColor: "#2a4035", color: "#8aa395" }}
            title="Ficha Darwin Core — taxonomía GBIF"
            onClick={() => onOpenDarwinCore(animal.animal_id)}
          >
            Darwin Core
          </button>
        )}
      </div>
    </div>
  );
}

function ActivityFeedItem({ item }: { item: ActivityItem }) {
  return (
    <div className="wt-activity-item">
      <div className="wt-activity-icon" data-type={item.item_type}>
        {ACTIVITY_ICON[item.item_type] ?? "•"}
      </div>
      <div className="wt-activity-body">
        <div className="wt-activity-desc">{item.description}</div>
        {item.rfid_tag && (
          <div className="wt-activity-rfid">🏷 {item.rfid_tag}</div>
        )}
        <div className="wt-activity-time">{formatTime(item.timestamp)}</div>
      </div>
    </div>
  );
}

function TRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="wt-telemetry-row">
      <span className="wt-telemetry-label">{label}</span>
      <span
        className="wt-telemetry-value"
        style={mono ? { fontFamily: "'Space Grotesk', monospace" } : undefined}
      >
        {value}
      </span>
    </div>
  );
}

function SkeletonBlock({
  height = 32,
  style,
}: {
  height?: number;
  style?: React.CSSProperties;
}) {
  return (
    <div
      className="wt-skeleton"
      style={{ height, borderRadius: 8, marginBottom: 4, ...style }}
    />
  );
}
