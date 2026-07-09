import { useEffect, useState } from "react";
import "./StationVisitsModal.css";
import "./ExportModal.css";
import { useStationEvents } from "../hooks/useStationEvents";
import type {
  EventFilter,
  StationEventDetail,
  TimePeriod,
} from "../api/geoportal.types";
import { exportVisitsCsv } from "../lib/exportData";

interface StationVisitsModalProps {
  stationId: string;
  timePeriod: TimePeriod;
  onClose: () => void;
}

export default function StationVisitsModal({
  stationId,
  timePeriod,
  onClose,
}: StationVisitsModalProps) {
  const [filter, setFilter] = useState<EventFilter>("all");
  const [page, setPage] = useState(1);
  const [allEvents, setAllEvents] = useState<StationEventDetail[]>([]);

  const { data, isFetching, isError } = useStationEvents(
    stationId,
    page,
    filter,
    timePeriod
  );

  useEffect(() => {
    if (!data) return;
    setAllEvents((prev) =>
      page === 1 ? data.events : [...prev, ...data.events]
    );
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  function changeFilter(f: EventFilter) {
    if (f === filter) return;
    setFilter(f);
    setPage(1);
    setAllEvents([]);
  }

  function handleOverlayClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onClose();
  }

  const isInitialLoading = isFetching && page === 1 && allEvents.length === 0;
  const hasMore = data ? page < data.pages : false;
  const totalAll =
    data != null ? data.identificadas + data.sin_identificar : null;

  return (
    <div className="wt-visits-overlay" onClick={handleOverlayClick}>
      <div className="wt-visits-modal">
        {/* ── Head ── */}
        <div className="wt-visits-head">
          <div className="wt-visits-head-row">
            <div className="wt-visits-title-group">
              <p className="wt-visits-title">Visitas registradas</p>
              <p className="wt-visits-subtitle">{data?.station_name ?? "…"}</p>
            </div>
            <div style={{ display: "flex", gap: 6, alignItems: "center", flexShrink: 0 }}>
              {allEvents.length > 0 && (
                <button
                  className="btn-download-inline"
                  title="Descargar visitas cargadas (CSV)"
                  aria-label="Descargar CSV"
                  onClick={() => exportVisitsCsv(allEvents, stationId)}
                >
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 16l-5-5h3V4h4v7h3l-5 5zm-6 2h12v2H6v-2z" />
                  </svg>
                  CSV
                </button>
              )}
              <button
                className="wt-visits-close"
                onClick={onClose}
                aria-label="Cerrar"
              >
                ×
              </button>
            </div>
          </div>

          <div className="wt-visits-filters">
            <button
              className="wt-visits-chip"
              data-active={String(filter === "all")}
              onClick={() => changeFilter("all")}
            >
              Todas{totalAll !== null ? ` (${totalAll})` : ""}
            </button>
            <button
              className="wt-visits-chip"
              data-active={String(filter === "identified")}
              onClick={() => changeFilter("identified")}
            >
              Con chip{data != null ? ` (${data.identificadas})` : ""}
            </button>
            <button
              className="wt-visits-chip"
              data-active={String(filter === "unidentified")}
              onClick={() => changeFilter("unidentified")}
            >
              Sin ID{data != null ? ` (${data.sin_identificar})` : ""}
            </button>
          </div>
        </div>

        {/* ── Body ── */}
        <div className="wt-visits-body">
          {isInitialLoading ? (
            <>
              <div className="wt-visits-skeleton" style={{ height: 118 }} />
              <div className="wt-visits-skeleton" style={{ height: 118 }} />
              <div className="wt-visits-skeleton" style={{ height: 118 }} />
            </>
          ) : isError ? (
            <div className="wt-visits-empty">
              No se pudieron cargar las visitas.
            </div>
          ) : allEvents.length === 0 ? (
            <div className="wt-visits-empty">
              Sin visitas registradas
              {filter !== "all" ? " con este filtro" : ""}.
            </div>
          ) : (
            <>
              {allEvents.map((ev) => (
                <VisitCard key={ev.event_id} event={ev} />
              ))}

              {hasMore && (
                <button
                  className="wt-visits-load-more"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={isFetching}
                >
                  {isFetching ? "Cargando…" : "Cargar más visitas"}
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

const SEX_LABEL: Record<string, string> = {
  male: "Macho",
  female: "Hembra",
  M: "Macho",
  F: "Hembra",
  unknown: "Desconocido",
};

function isConsumedAnomaly(g: number | null): boolean {
  return g !== null && g < 50;
}
function isTempAnomaly(t: number | null): boolean {
  return t !== null && (t < 10 || t > 40);
}
function isHumidityAnomaly(h: number | null): boolean {
  return h !== null && (h < 20 || h > 95);
}

function formatTs(iso: string): string {
  return new Date(iso).toLocaleString("es-CO", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function VisitCard({ event }: { event: StationEventDetail }) {
  const hasPhoto = event.media_urls.length > 0;
  const consumedFlag = isConsumedAnomaly(event.consumed_g);
  const tempFlag = isTempAnomaly(event.temperature_c);
  const humFlag = isHumidityAnomaly(event.humidity_pct);

  return (
    <div className="wt-visit-card">
      {/* Top row: photo link + timestamp */}
      <div className="wt-visit-card-top">
        <button
          className="wt-visit-photo"
          data-has={String(hasPhoto)}
          disabled={!hasPhoto}
          onClick={
            hasPhoto
              ? () => window.open(event.media_urls[0], "_blank")
              : undefined
          }
        >
          <svg
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="currentColor"
          >
            <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3 3.5-4.5 4.5 6H5l3.5-4.5z" />
          </svg>
          {hasPhoto ? `${event.media_urls.length} foto${event.media_urls.length > 1 ? "s" : ""}` : "Sin foto"}
        </button>
        <span className="wt-visit-ts">{formatTs(event.timestamp)}</span>
      </div>

      {/* Identity row */}
      {event.is_identified ? (
        <div className="wt-visit-id-row">
          <div className="wt-visit-animal-info">
            {event.animal_id && (
              <div className="wt-visit-animal-id">
                #{event.animal_id.slice(0, 8).toUpperCase()}
              </div>
            )}
            {event.animal_species && (
              <div className="wt-visit-animal-name">{event.animal_species}</div>
            )}
            {event.animal_sex && (
              <div className="wt-visit-animal-sex">
                {SEX_LABEL[event.animal_sex] ?? event.animal_sex}
              </div>
            )}
          </div>
          {event.rfid_tag && (
            <span className="wt-visit-rfid">{event.rfid_tag}</span>
          )}
        </div>
      ) : (
        <div className="wt-visit-unid">
          Sin identificar
          {event.rfid_tag ? ` · Tag: ${event.rfid_tag}` : ""}
        </div>
      )}

      {/* Metrics */}
      <div className="wt-visit-metrics">
        <div className="wt-visit-metric">
          <div
            className="wt-visit-metric-v"
            data-flag={String(consumedFlag)}
          >
            {event.consumed_g != null ? `${event.consumed_g} g` : "—"}
          </div>
          <div className="wt-visit-metric-k">Consumo</div>
        </div>
        <div className="wt-visit-metric">
          <div
            className="wt-visit-metric-v"
            data-flag={String(tempFlag)}
          >
            {event.temperature_c != null
              ? `${event.temperature_c.toFixed(1)} °C`
              : "—"}
          </div>
          <div className="wt-visit-metric-k">Temp.</div>
        </div>
        <div className="wt-visit-metric">
          <div
            className="wt-visit-metric-v"
            data-flag={String(humFlag)}
          >
            {event.humidity_pct != null
              ? `${event.humidity_pct.toFixed(0)} %`
              : "—"}
          </div>
          <div className="wt-visit-metric-k">Humedad</div>
        </div>
      </div>
    </div>
  );
}
