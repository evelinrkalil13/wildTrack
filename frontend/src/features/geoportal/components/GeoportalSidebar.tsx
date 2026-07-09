import { useState, useMemo } from "react";
import type { GeoportalStationMapItem, TimePeriod } from "../api/geoportal.types";
import { StationStatus } from "@/api/types/enums";
import "./GeoportalSidebar.css";

type FilterMode = "todas" | "alerta" | "noid";

type ZoneGroup = {
  zone_id: string;
  zone_name: string;
  zone_color: string;
  stations: GeoportalStationMapItem[];
};

function ChevronIcon({ collapsed }: { collapsed: boolean }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      style={{
        flexShrink: 0,
        transition: "transform 0.2s",
        transform: collapsed ? "rotate(-90deg)" : "rotate(0deg)",
      }}
    >
      <path
        d="M2.5 4.5L6 8l3.5-3.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function BarChartIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <path d="M4 20V10h3v10H4zm6.5 0V4h3v16h-3zM17 20v-7h3v7h-3z" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 16l-5-5h3V4h4v7h3l-5 5zm-6 2h12v2H6v-2z" />
    </svg>
  );
}

function statusDotKey(s: GeoportalStationMapItem): "online" | "alert" | "offline" {
  if (s.open_alerts_count > 0) return "alert";
  if (s.status === StationStatus.active) return "online";
  return "offline";
}

interface GeoportalSidebarProps {
  stations: GeoportalStationMapItem[];
  selectedStationId: string | null;
  onSelect: (station: GeoportalStationMapItem) => void;
  isLoading: boolean;
  timePeriod: TimePeriod;
  onTimePeriodChange: (t: TimePeriod) => void;
  onStatsOpen: () => void;
  onExportOpen: () => void;
  open: boolean;
}

export default function GeoportalSidebar({
  stations,
  selectedStationId,
  onSelect,
  isLoading,
  timePeriod,
  onTimePeriodChange,
  onStatsOpen,
  onExportOpen,
  open,
}: GeoportalSidebarProps) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterMode>("todas");
  const [collapsedZones, setCollapsedZones] = useState<Set<string>>(new Set());

  const alertCount = stations.filter((s) => s.open_alerts_count > 0).length;
  const noidCount = stations.filter((s) => s.visitas_sin_identificar > 0).length;
  const totalEventos = stations.reduce((acc, s) => acc + s.visitas_total, 0);

  const filtered = useMemo(() => {
    let list = stations;
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(
        (s) =>
          s.station_name.toLowerCase().includes(q) ||
          s.station_code.toLowerCase().includes(q)
      );
    }
    if (filter === "alerta") list = list.filter((s) => s.open_alerts_count > 0);
    if (filter === "noid") list = list.filter((s) => s.visitas_sin_identificar > 0);
    return list;
  }, [stations, query, filter]);

  const zoneGroups = useMemo(() => {
    const map = new Map<string, ZoneGroup>();
    for (const s of filtered) {
      if (!map.has(s.zone_id)) {
        map.set(s.zone_id, {
          zone_id: s.zone_id,
          zone_name: s.zone_name,
          zone_color: s.zone_color,
          stations: [],
        });
      }
      map.get(s.zone_id)!.stations.push(s);
    }
    return [...map.values()];
  }, [filtered]);

  function toggleZone(zoneId: string) {
    setCollapsedZones((prev) => {
      const next = new Set(prev);
      next.has(zoneId) ? next.delete(zoneId) : next.add(zoneId);
      return next;
    });
  }

  return (
    <aside className="wt-sidebar" data-open={String(open)}>
      {/* KPI row */}
      <div className="kpis">
        <div className="kpi">
          <div className="num">{isLoading ? "—" : stations.length}</div>
          <div className="lbl">Estaciones</div>
        </div>
        <div className="kpi">
          <div className="num">{isLoading ? "—" : totalEventos}</div>
          <div className="lbl">Eventos</div>
        </div>
        <div className="kpi alert">
          <div className="num">{isLoading ? "—" : alertCount}</div>
          <div className="lbl">Alertas</div>
        </div>
      </div>

      {/* Controls */}
      <div className="controls">
        <input
          className="search"
          placeholder="Buscar estación…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Buscar estación"
        />

        <div className="filters" role="group" aria-label="Filtrar estaciones">
          <button
            className="chip"
            data-active={filter === "todas"}
            onClick={() => setFilter("todas")}
          >
            Todas
          </button>
          <button
            className="chip"
            data-active={filter === "alerta"}
            onClick={() => setFilter("alerta")}
          >
            Alerta{alertCount > 0 ? ` (${alertCount})` : ""}
          </button>
          <button
            className="chip"
            data-active={filter === "noid"}
            onClick={() => setFilter("noid")}
          >
            Sin ID{noidCount > 0 ? ` (${noidCount})` : ""}
          </button>
        </div>

        <select
          className="time-select"
          value={timePeriod}
          onChange={(e) => onTimePeriodChange(e.target.value as TimePeriod)}
          aria-label="Periodo de tiempo"
        >
          <option value="24h">Últimas 24 h</option>
          <option value="7d">Últimos 7 días</option>
          <option value="30d">Últimos 30 días</option>
          <option value="all">Todo el tiempo</option>
        </select>

        <div className="status-legend" aria-label="Leyenda de estado">
          <span className="legend-title">Estado de estaciones:</span>
          <span className="legend-item">
            <span className="st-status" data-s="online" />
            En línea
          </span>
          <span className="legend-item">
            <span className="st-status" data-s="alert" />
            Alerta
          </span>
          <span className="legend-item">
            <span className="st-status" data-s="offline" />
            Sin señal
          </span>
        </div>
      </div>

      {/* Station list grouped by zone */}
      <div className="station-list">
        {isLoading && (
          <div className="loading">Cargando estaciones…</div>
        )}

        {!isLoading && zoneGroups.length === 0 && (
          <div className="empty">
            {query || filter !== "todas"
              ? "Ninguna estación coincide."
              : "Sin estaciones registradas."}
          </div>
        )}

        {!isLoading &&
          zoneGroups.map((zone) => {
            const isCollapsed = collapsedZones.has(zone.zone_id);
            return (
              <div key={zone.zone_id} className="sector-group">
                <button
                  className="sector-toggle"
                  onClick={() => toggleZone(zone.zone_id)}
                  aria-expanded={!isCollapsed}
                  aria-label={`${isCollapsed ? "Expandir" : "Colapsar"} zona ${zone.zone_name}`}
                >
                  <ChevronIcon collapsed={isCollapsed} />
                  <span
                    className="sector-color-dot"
                    style={{
                      background: zone.zone_color,
                      color: zone.zone_color,
                    }}
                  />
                  <span className="sector-name">{zone.zone_name}</span>
                  <span className="sector-desc">
                    {zone.stations.length} est.
                  </span>
                </button>

                {!isCollapsed &&
                  zone.stations.map((st) => (
                    <button
                      key={st.station_id}
                      className="st-row"
                      data-active={st.station_id === selectedStationId}
                      style={
                        { "--sector-color": zone.zone_color } as React.CSSProperties
                      }
                      onClick={() => onSelect(st)}
                    >
                      <span className="st-status" data-s={statusDotKey(st)} />
                      <span className="st-main">
                        <span className="st-name">{st.station_name}</span>
                        <span className="st-sub">
                          {st.station_code}
                          {st.visitas_sin_identificar > 0 &&
                            ` · ${st.visitas_sin_identificar} sin ID`}
                          {st.is_live && (
                            <span className="live-badge">📡 EN VIVO</span>
                          )}
                        </span>
                      </span>
                      <span className="st-count">{st.visitas_total}</span>
                    </button>
                  ))}
              </div>
            );
          })}
      </div>

      {/* Footer — placeholder buttons until GEO-5 and GEO-8 */}
      <div className="sidebar-footer">
        <button
          className="btn-footer"
          onClick={onStatsOpen}
          title="Ver estadísticas globales"
        >
          <BarChartIcon />
          Estadísticas
        </button>
        <button
          className="btn-footer"
          onClick={onExportOpen}
          title="Exportar datos"
        >
          <DownloadIcon />
          Exportar
        </button>
      </div>
    </aside>
  );
}
