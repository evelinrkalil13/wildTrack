import { useState } from "react";
import "./AnimalFeedingDashboard.css";
import "./ExportModal.css";
import type {
  AnimalHistoryResponse,
  FeedingEvent,
  FeederRankItem,
  TimePeriod,
} from "../api/geoportal.types";
import { useAnimalHistory } from "../hooks/useAnimalHistory";
import { exportTimelineCsv } from "../lib/exportData";

const DIAS = ["L", "M", "X", "J", "V", "S", "D"];
const DIAS_FULL = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

const SEX_LABEL: Record<string, string> = {
  male: "♂ Macho",
  female: "♀ Hembra",
  M: "♂ Macho",
  F: "♀ Hembra",
  unknown: "? Desc.",
};

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("es-CO", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

interface AnimalFeedingDashboardProps {
  animalId: string;
  initialPeriod?: TimePeriod;
  onClose: () => void;
  onTrace: (history: AnimalHistoryResponse) => void;
}

export default function AnimalFeedingDashboard({
  animalId,
  initialPeriod = "all",
  onClose,
  onTrace,
}: AnimalFeedingDashboardProps) {
  const [localPeriod, setLocalPeriod] = useState<TimePeriod>(initialPeriod);
  const { data: history, isPending, isError } = useAnimalHistory(animalId, localPeriod);

  return (
    <div
      className="wt-dash-overlay"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="wt-dash">
        <DashHead
          history={history}
          period={localPeriod}
          onPeriodChange={setLocalPeriod}
          onClose={onClose}
          onTrace={() => history && onTrace(history)}
        />
        <div className="wt-dash-body">
          {isPending && <DashSkeleton />}
          {isError && (
            <div className="wt-dash-empty">Error al cargar el historial.</div>
          )}
          {!isPending && !isError && history && <DashBody history={history} />}
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ───────────────────────────────────────────────────────────

function DashHead({
  history,
  period,
  onPeriodChange,
  onClose,
  onTrace,
}: {
  history: AnimalHistoryResponse | undefined;
  period: TimePeriod;
  onPeriodChange: (p: TimePeriod) => void;
  onClose: () => void;
  onTrace: () => void;
}) {
  const hasTrace = !!history && history.trace_path.length > 0;
  return (
    <div className="wt-dash-head">
      <div className="wt-dash-head-top">
        <div className="wt-dash-id-row">
          {history && (
            <>
              <span className="wt-dash-id">
                {history.animal_id.slice(0, 8).toUpperCase()}
              </span>
              <span className="wt-dash-rfid">{history.rfid_tag}</span>
            </>
          )}
        </div>
        <div className="wt-dash-actions">
          <select
            className="wt-dash-period"
            value={period}
            onChange={(e) => onPeriodChange(e.target.value as TimePeriod)}
            aria-label="Periodo de tiempo"
          >
            <option value="24h">24 h</option>
            <option value="7d">7 días</option>
            <option value="30d">30 días</option>
            <option value="all">Todo</option>
          </select>
          <button
            className="wt-dash-btn-trace"
            onClick={onTrace}
            disabled={!hasTrace}
            title={hasTrace ? "Ver ruta en el mapa" : "Sin datos de ruta"}
          >
            Ver ruta →
          </button>
          {history && history.timeline.length > 0 && (
            <button
              className="btn-download-inline"
              title="Descargar historial de alimentación (CSV)"
              aria-label="Descargar CSV"
              onClick={() =>
                exportTimelineCsv(history.timeline, history.animal_id)
              }
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 16l-5-5h3V4h4v7h3l-5 5zm-6 2h12v2H6v-2z" />
              </svg>
              CSV
            </button>
          )}
          <button
            className="wt-dash-btn-close"
            onClick={onClose}
            aria-label="Cerrar dashboard"
          >
            &times;
          </button>
        </div>
      </div>
      {history && (
        <>
          <div className="wt-dash-title">
            Historial de alimentación — {history.species}
          </div>
          <div className="wt-dash-subtitle">
            {SEX_LABEL[history.sex] ?? history.sex}
            {history.estimated_age && ` · ${history.estimated_age}`}
          </div>
        </>
      )}
    </div>
  );
}

function DashBody({ history }: { history: AnimalHistoryResponse }) {
  const vals = history.actividad_semanal;
  const peak = Math.max(...vals, 1);
  const peakIdx = vals.indexOf(Math.max(...vals));

  return (
    <>
      {/* Insight */}
      <div className="wt-dash-insight">
        <span className="wt-dash-insight-icon">🔍</span>
        <span>{history.insight_text}</span>
      </div>

      {/* KPIs */}
      <div className="wt-dash-kpi-row">
        <Kpi value={history.total_alimentaciones} label="Alimentaciones" />
        <Kpi value={history.total_estaciones} label="Comederos" />
        <Kpi value={history.dias_activo} label="Días activo" />
        <Kpi
          value={history.peso_promedio_g != null ? `${history.peso_promedio_g} g` : "—"}
          label="Peso prom."
        />
      </div>

      {/* Two-column: ranking + weekly chart */}
      {(history.feeder_ranking.length > 0 || vals.some(Boolean)) && (
        <div className="wt-dash-cols">
          <div className="wt-dash-col">
            <div className="wt-dash-section-label">Comederos visitados</div>
            <div className="wt-dash-station-list">
              {history.feeder_ranking.map((item, i) => (
                <FeederRow key={item.station_id} item={item} rank={i + 1} />
              ))}
            </div>
          </div>

          <div className="wt-dash-col">
            <div className="wt-dash-section-label">Actividad semanal</div>
            <div
              className="wt-dash-dow-chart"
              role="img"
              aria-label="Actividad por día de la semana"
            >
              {vals.map((v, i) => (
                <div className="wt-dash-dow-col" key={i}>
                  <div
                    className="wt-dash-dow-bar"
                    data-peak={String(v === peak && peak > 0)}
                    style={{ height: `${peak > 0 ? (v / peak) * 100 : 0}%` }}
                    title={`${v} visitas`}
                  />
                  <div className="wt-dash-dow-lbl">{DIAS[i]}</div>
                </div>
              ))}
            </div>
            {peak > 0 && (
              <div className="wt-dash-dow-note">
                Día más activo: {DIAS_FULL[peakIdx] ?? "—"}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="wt-dash-section-label" style={{ marginTop: 4 }}>
        Línea de tiempo ({history.timeline.length} eventos)
      </div>
      {history.timeline.length === 0 ? (
        <div className="wt-dash-empty">Sin eventos en este periodo.</div>
      ) : (
        <div className="wt-dash-timeline">
          {history.timeline.map((ev) => (
            <EventRow key={ev.event_id} ev={ev} />
          ))}
        </div>
      )}
    </>
  );
}

function Kpi({ value, label }: { value: string | number; label: string }) {
  return (
    <div className="wt-dash-kpi">
      <div className="wt-dash-kpi-v">{value}</div>
      <div className="wt-dash-kpi-k">{label}</div>
    </div>
  );
}

function FeederRow({ item, rank }: { item: FeederRankItem; rank: number }) {
  return (
    <div className="wt-dash-srow">
      <div className="wt-dash-srow-label">
        <div className="wt-dash-srow-id">
          <span style={{ color: "#8aa395", fontSize: 10 }}>{rank}.</span>
          {item.is_primary && (
            <span className="wt-dash-srow-primary">★ Principal</span>
          )}
        </div>
        <div className="wt-dash-srow-name" title={item.station_name}>
          {item.station_name}
        </div>
      </div>
      <div className="wt-dash-srow-bar-wrap">
        <div
          className="wt-dash-srow-bar"
          data-top={String(item.is_primary)}
          style={{ width: `${item.pct}%` }}
        />
      </div>
      <div className="wt-dash-srow-count">
        <span className="wt-dash-srow-n">{item.visits}</span>
        <span className="wt-dash-srow-pct">{item.pct.toFixed(0)}%</span>
      </div>
    </div>
  );
}

function EventRow({ ev }: { ev: FeedingEvent }) {
  const hasPhoto = ev.media_urls.length > 0;
  return (
    <div className="wt-dash-ev">
      <div className="wt-dash-ev-station-col">
        <div className="wt-dash-ev-stid">{ev.station_id.slice(0, 8).toUpperCase()}</div>
        <div className="wt-dash-ev-stname">{ev.station_name}</div>
      </div>
      <div className="wt-dash-ev-weight">
        {ev.consumed_g != null ? `${ev.consumed_g.toFixed(0)} g` : "—"}
      </div>
      <div className="wt-dash-ev-photo">
        {hasPhoto ? (
          <span className="wt-dash-ev-has-photo">📷</span>
        ) : (
          <span className="wt-dash-ev-no-photo">—</span>
        )}
      </div>
      <div className="wt-dash-ev-ts">{formatTime(ev.timestamp)}</div>
    </div>
  );
}

function DashSkeleton() {
  return (
    <>
      <div className="wt-dash-skeleton" style={{ height: 44, marginBottom: 16 }} />
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4,1fr)",
          gap: 10,
          marginBottom: 20,
        }}
      >
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="wt-dash-skeleton" style={{ height: 64 }} />
        ))}
      </div>
      <div className="wt-dash-skeleton" style={{ height: 120, marginBottom: 20 }} />
      {[0, 1, 2].map((i) => (
        <div key={i} className="wt-dash-skeleton" style={{ height: 48, marginBottom: 6 }} />
      ))}
    </>
  );
}
