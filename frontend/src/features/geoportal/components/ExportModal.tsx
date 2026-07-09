import "./ExportModal.css";
import type {
  AnimalMovement,
  GeoportalStationMapItem,
  SectorStatRow,
} from "../api/geoportal.types";
import {
  exportAnimalsCsv,
  exportAnimalsJson,
  exportSectorsCsv,
  exportStationsCsv,
  exportStationsGeoJson,
} from "../lib/exportData";

interface ExportModalProps {
  stations: GeoportalStationMapItem[];
  sectors: SectorStatRow[];
  animals: AnimalMovement[];
  onClose: () => void;
}

function DownloadIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor" style={{ flexShrink: 0 }}>
      <path d="M12 16l-5-5h3V4h4v7h3l-5 5zm-6 2h12v2H6v-2z" />
    </svg>
  );
}

export default function ExportModal({
  stations,
  sectors,
  animals,
  onClose,
}: ExportModalProps) {
  function handleOverlay(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onClose();
  }

  return (
    <div
      className="wt-export-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="wt-export-title"
      onClick={handleOverlay}
    >
      <div className="wt-export-modal">
        <div className="wt-export-head">
          <div>
            <p id="wt-export-title" className="wt-export-title">
              Exportar datos
            </p>
            <p className="wt-export-subtitle">
              Descarga los registros de campo para análisis externo
            </p>
          </div>
          <button className="wt-export-close" onClick={onClose} aria-label="Cerrar">
            ×
          </button>
        </div>

        <div className="wt-export-cards">

          {/* ── Estaciones ── */}
          <div className="wt-export-card">
            <div className="wt-export-card-head">
              <span className="wt-export-card-icon">📍</span>
              <div className="wt-export-card-info">
                <div className="wt-export-card-title">Catálogo de estaciones</div>
                <div className="wt-export-card-meta">
                  {stations.length} estaciones · coordenadas + estadísticas
                </div>
              </div>
            </div>
            <div className="wt-export-card-desc">
              Ubicaciones georreferenciadas (EPSG:4326) con estadísticas de visitas.
              GeoJSON compatible con QGIS, ArcGIS y otras plataformas SIG.
            </div>
            <div className="wt-export-formats">
              <button
                className="btn-export btn-export-geo"
                onClick={() => exportStationsGeoJson(stations)}
                title="GeoJSON — compatible con QGIS, ArcGIS"
              >
                <DownloadIcon /> GeoJSON
              </button>
              <button
                className="btn-export"
                onClick={() => exportStationsCsv(stations)}
                title="CSV — para Excel o análisis estadístico"
              >
                <DownloadIcon /> CSV
              </button>
            </div>
          </div>

          {/* ── Sectores ── */}
          <div className="wt-export-card">
            <div className="wt-export-card-head">
              <span className="wt-export-card-icon">🗺️</span>
              <div className="wt-export-card-info">
                <div className="wt-export-card-title">Resumen por sectores</div>
                <div className="wt-export-card-meta">
                  {sectors.length} sectores · visitas + alertas
                </div>
              </div>
            </div>
            <div className="wt-export-card-desc">
              Estadísticas agregadas por zona geográfica: número de estaciones,
              visitas totales, porcentaje sin identificar y alertas abiertas.
            </div>
            <div className="wt-export-formats">
              <button
                className="btn-export"
                onClick={() => exportSectorsCsv(sectors)}
              >
                <DownloadIcon /> CSV
              </button>
            </div>
          </div>

          {/* ── Individuos ── */}
          <div className="wt-export-card">
            <div className="wt-export-card-head">
              <span className="wt-export-card-icon">🐾</span>
              <div className="wt-export-card-info">
                <div className="wt-export-card-title">Individuos con chip</div>
                <div className="wt-export-card-meta">
                  {animals.length} individuos · ficha completa
                </div>
              </div>
            </div>
            <div className="wt-export-card-desc">
              Catálogo de animales con chip RFID: especie, sexo, estaciones
              visitadas y ruta entre puntos de alimentación.
            </div>
            <div className="wt-export-formats">
              <button
                className="btn-export"
                onClick={() => exportAnimalsCsv(animals)}
              >
                <DownloadIcon /> CSV
              </button>
              <button
                className="btn-export"
                onClick={() => exportAnimalsJson(animals)}
              >
                <DownloadIcon /> JSON
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
