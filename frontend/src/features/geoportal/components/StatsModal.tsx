import "./StatsModal.css";
import { useState } from "react";
import type {
  AnimalMovement,
  GeoportalStatsResponse,
  SectorStatRow,
  StationStatRow,
  TimePeriod,
} from "../api/geoportal.types";
import { useGeoportalStats } from "../hooks/useGeoportalStats";
import { StationStatus } from "@/api/types/enums";

type Tab = "estaciones" | "sectores" | "individuos";

const SEX_LABEL: Record<string, string> = {
  male: "♂ Macho",
  female: "♀ Hembra",
  M: "♂ Macho",
  F: "♀ Hembra",
  unknown: "? Desc.",
  desconocido: "? Desc.",
};

const STATUS_LABEL: Record<StationStatus, string> = {
  [StationStatus.active]: "En línea",
  [StationStatus.inactive]: "Inactiva",
  [StationStatus.maintenance]: "Mantenimiento",
  [StationStatus.offline]: "Sin señal",
};

const TIME_LABELS: Record<TimePeriod, string> = {
  "24h": "Últimas 24 h",
  "7d": "Últimos 7 días",
  "30d": "Últimos 30 días",
  all: "Todo el tiempo",
};

interface StatsModalProps {
  timePeriod: TimePeriod;
  onClose: () => void;
  onTraceAnimal?: (movement: AnimalMovement) => void;
}

export default function StatsModal({
  timePeriod: initialPeriod,
  onClose,
  onTraceAnimal,
}: StatsModalProps) {
  const [tab, setTab] = useState<Tab>("estaciones");
  const [period, setPeriod] = useState<TimePeriod>(initialPeriod);

  const { data, isPending } = useGeoportalStats(period);

  const movers =
    data?.animales_con_chip.filter((m) => m.distinct_stations > 1) ?? [];

  return (
    <div
      className="wt-modal-overlay"
      role="dialog"
      aria-modal="true"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="wt-modal-stats">
        {/* Head */}
        <div className="wt-modal-head">
          <div>
            <div className="wt-modal-eyebrow">Resumen general</div>
            <div className="wt-modal-title">Estadísticas de WildTrack</div>
            {data && (
              <div className="wt-modal-subtitle">
                {data.total_estaciones} estaciones · {data.total_sectores} sectores ·{" "}
                {data.total_animales_con_chip} individuos con chip
              </div>
            )}
          </div>
          <button className="wt-modal-close" onClick={onClose} aria-label="Cerrar">
            ×
          </button>
        </div>

        {/* Body */}
        <div className="wt-modal-body">
          {/* Period selector */}
          <div className="wt-modal-filters" style={{ marginBottom: 8 }}>
            {(["24h", "7d", "30d", "all"] as TimePeriod[]).map((p) => (
              <button
                key={p}
                className="wt-modal-chip"
                data-active={String(period === p)}
                onClick={() => setPeriod(p)}
              >
                {TIME_LABELS[p]}
              </button>
            ))}
          </div>

          {/* Tab selector */}
          <div className="wt-modal-filters">
            {(["estaciones", "sectores", "individuos"] as Tab[]).map((t) => (
              <button
                key={t}
                className="wt-modal-chip"
                data-active={String(tab === t)}
                onClick={() => setTab(t)}
                style={{ textTransform: "capitalize" }}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Loading */}
          {isPending && (
            <>
              <div className="wt-modal-skeleton" style={{ height: 32, marginBottom: 6 }} />
              <div className="wt-modal-skeleton" style={{ height: 120 }} />
            </>
          )}

          {/* ── Tab: Estaciones ── */}
          {!isPending && data && tab === "estaciones" && (
            <EstacionesTab estaciones={data.estaciones} />
          )}

          {/* ── Tab: Sectores ── */}
          {!isPending && data && tab === "sectores" && (
            <SectoresTab sectores={data.sectores} />
          )}

          {/* ── Tab: Individuos ── */}
          {!isPending && data && tab === "individuos" && (
            <IndividuosTab
              data={data}
              movers={movers}
              onTrace={onTraceAnimal}
              onClose={onClose}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ── Sub-tabs ─────────────────────────────────────────────────────────────────

function EstacionesTab({ estaciones }: { estaciones: StationStatRow[] }) {
  if (estaciones.length === 0)
    return <div className="wt-modal-empty">No hay estaciones registradas.</div>;

  return (
    <div className="wt-stats-table-wrap">
      <table className="wt-stats-table">
        <thead>
          <tr>
            <th>Estación</th>
            <th>Sector</th>
            <th>Visitas</th>
            <th>Identif.</th>
            <th>Sin ID</th>
            <th>Peso prom.</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {estaciones.map((st) => (
            <tr key={st.station_id}>
              <td>
                <div className="wt-td-mono">{st.station_code}</div>
                <div className="wt-td-muted">{st.station_name}</div>
              </td>
              <td>
                <span
                  className="wt-zone-dot"
                  style={{ color: st.zone_color, background: st.zone_color }}
                />
                <span style={{ color: st.zone_color }}>{st.zone_name}</span>
              </td>
              <td className="wt-td-green">{st.visitas}</td>
              <td>{st.identificados}</td>
              <td className="wt-td-amber">{st.sin_identificar}</td>
              <td>{st.peso_promedio_g != null ? `${st.peso_promedio_g} g` : "—"}</td>
              <td style={{ color: st.open_alerts > 0 ? "#e08a1e" : "#52b788", fontSize: 11 }}>
                {STATUS_LABEL[st.status]}
                {st.open_alerts > 0 && ` ⚠ ${st.open_alerts}`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SectoresTab({ sectores }: { sectores: SectorStatRow[] }) {
  if (sectores.length === 0)
    return <div className="wt-modal-empty">No hay sectores registrados.</div>;

  return (
    <div className="wt-stats-table-wrap">
      <table className="wt-stats-table">
        <thead>
          <tr>
            <th>Sector</th>
            <th>Est.</th>
            <th>Visitas</th>
            <th>Identif.</th>
            <th>Sin ID</th>
            <th>% Sin ID</th>
            <th>Peso prom.</th>
            <th>En alerta</th>
          </tr>
        </thead>
        <tbody>
          {sectores.map((sec) => (
            <tr key={sec.zone_id}>
              <td>
                <span
                  className="wt-zone-dot"
                  style={{ color: sec.zone_color, background: sec.zone_color }}
                />
                <span style={{ color: sec.zone_color }}>{sec.zone_name}</span>
              </td>
              <td>{sec.num_estaciones}</td>
              <td className="wt-td-green">{sec.visitas}</td>
              <td>{sec.identificados}</td>
              <td className="wt-td-amber">{sec.sin_identificar}</td>
              <td className="wt-td-amber">{sec.pct_sin_id}%</td>
              <td>{sec.peso_promedio_g != null ? `${sec.peso_promedio_g} g` : "—"}</td>
              <td style={{ color: sec.en_alerta > 0 ? "#e08a1e" : "#52b788" }}>
                {sec.en_alerta}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function IndividuosTab({
  data,
  movers,
  onTrace,
  onClose,
}: {
  data: GeoportalStatsResponse;
  movers: AnimalMovement[];
  onTrace?: (m: AnimalMovement) => void;
  onClose: () => void;
}) {
  const mCount = data.animales_con_chip.filter((m) => m.sex === "male" || m.sex === "M").length;
  const fCount = data.animales_con_chip.filter((m) => m.sex === "female" || m.sex === "F").length;

  return (
    <>
      {/* KPI row */}
      <div className="wt-kpi-row">
        <div className="wt-kpi">
          <div className="wt-kpi-v">{data.total_animales_con_chip}</div>
          <div className="wt-kpi-k">Con chip</div>
        </div>
        <div className="wt-kpi">
          <div className="wt-kpi-v">{data.avistamientos_sin_chip}</div>
          <div className="wt-kpi-k">Sin chip</div>
        </div>
        <div className="wt-kpi">
          <div className="wt-kpi-v">
            {mCount} / {fCount}
          </div>
          <div className="wt-kpi-k">Machos / Hembras</div>
        </div>
        <div className="wt-kpi">
          <div className="wt-kpi-v">{movers.length}</div>
          <div className="wt-kpi-k">Con desplazamiento</div>
        </div>
      </div>

      {/* Clarification note */}
      <div className="wt-modal-note">
        Los avistamientos sin chip no pueden atribuirse a un individuo concreto
        — se cuentan como eventos, no como animales distintos.
        {data.total_visitas > 0 &&
          ` Representan el ${Math.round((data.avistamientos_sin_chip / data.total_visitas) * 100)}% del total de eventos.`}
      </div>

      {/* Movers list */}
      <div className="wt-modal-section-label">
        Individuos con desplazamiento ({movers.length})
      </div>
      {movers.length === 0 ? (
        <div className="wt-modal-empty" style={{ padding: "20px 0" }}>
          Ningún individuo ha visitado más de una estación todavía.
        </div>
      ) : (
        <div className="wt-mover-list">
          {movers.map((m) => (
            <MoverRow
              key={m.animal_id}
              movement={m}
              onTrace={onTrace}
              onClose={onClose}
            />
          ))}
        </div>
      )}
    </>
  );
}

function MoverRow({
  movement,
  onTrace,
  onClose,
}: {
  movement: AnimalMovement;
  onTrace?: (m: AnimalMovement) => void;
  onClose: () => void;
}) {
  const pathLabel = movement.path_names.join(" → ");

  function handleTrace() {
    onClose();
    onTrace?.(movement);
  }

  return (
    <div className="wt-mover-row">
      <div className="wt-mover-info">
        <div className="wt-mover-id">
          {movement.rfid_tag}
          <span className="wt-mover-badge">{movement.distinct_stations} estaciones</span>
        </div>
        <div className="wt-mover-name">
          {movement.species} · {SEX_LABEL[movement.sex] ?? movement.sex}
        </div>
        <div className="wt-mover-path" title={pathLabel}>
          {pathLabel}
        </div>
      </div>
      <button className="wt-btn-trace" onClick={handleTrace}>
        Ver trazabilidad →
      </button>
    </div>
  );
}
