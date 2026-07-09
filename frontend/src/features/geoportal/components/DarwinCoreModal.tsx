import "./DarwinCoreModal.css";
import { useDarwinCore } from "../hooks/useDarwinCore";
import type { DarwinCoreObservation, DarwinCoreSourceStatus, GbifTaxonomy } from "../api/geoportal.types";

const SEX_LABEL: Record<string, string> = {
  male: "♂ Macho",
  female: "♀ Hembra",
  M: "♂ Macho",
  F: "♀ Hembra",
  unknown: "Desconocido",
};

const STATUS_BADGE: Record<DarwinCoreSourceStatus, { label: string; hint: string }> = {
  ok: {
    label: "✓ Coincidencia exacta",
    hint: "Alta confianza en GBIF.",
  },
  fuzzy_match: {
    label: "⚠ Coincidencia aproximada",
    hint: "Verifique el nombre científico.",
  },
  not_found: {
    label: "✗ No encontrado en GBIF",
    hint: "El nombre no arrojó resultados.",
  },
  unavailable: {
    label: "! GBIF no disponible",
    hint: "Intente de nuevo más tarde.",
  },
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function Val({ v }: { v: string | number | null | undefined }) {
  if (v === null || v === undefined || v === "") {
    return <span className="wt-dc-obs-value" data-null="true">sin datos</span>;
  }
  return <span className="wt-dc-obs-value">{v}</span>;
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function TaxonomySection({ tax }: { tax: GbifTaxonomy }) {
  const rows: [string, string | null][] = [
    ["Reino", tax.kingdom],
    ["Filo", tax.phylum],
    ["Clase", tax.taxon_class],
    ["Orden", tax.order],
    ["Familia", tax.family],
    ["Género", tax.genus],
    ["Epíteto específico", tax.specific_epithet],
    ["Rango taxonómico", tax.taxon_rank],
    ["Nombre científico", tax.scientific_name],
    ["Autoría", tax.scientific_name_authorship],
    ["Nombre vernáculo", tax.vernacular_name],
    ["Confianza GBIF", tax.gbif_confidence != null ? `${tax.gbif_confidence}%` : null],
  ];

  return (
    <div className="wt-dc-section">
      <div className="wt-dc-section-title">Taxonomía</div>
      <div className="wt-dc-tax-grid">
        {rows.map(([label, value]) => (
          <div className="wt-dc-tax-row" key={label}>
            <span>{label}</span>
            <span>{value ?? "—"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TaxonomyUnavailable({ status }: { status: DarwinCoreSourceStatus }) {
  const messages: Record<string, string> = {
    not_found:
      "No se encontró esta especie en GBIF. Verifique que el nombre científico esté correctamente escrito (ej: Puma concolor).",
    unavailable:
      "No fue posible consultar GBIF en este momento. Intente de nuevo más tarde.",
  };

  return (
    <div className="wt-dc-section">
      <div className="wt-dc-section-title">Taxonomía</div>
      <div
        className="wt-dc-taxonomy-notice"
        data-kind={status === "unavailable" ? "unavailable" : undefined}
      >
        <span>{status === "unavailable" ? "⚡" : "🔍"}</span>
        <span>{messages[status] ?? "Información taxonómica no disponible."}</span>
      </div>
    </div>
  );
}

function ObservationSection({ obs }: { obs: DarwinCoreObservation }) {
  return (
    <div className="wt-dc-section">
      <div className="wt-dc-section-title">Observación · Ubicación</div>
      <div className="wt-dc-obs-grid">
        {obs.catalog_number && (
          <div className="wt-dc-obs-row">
            <span className="wt-dc-obs-label">RFID</span>
            <Val v={obs.catalog_number} />
          </div>
        )}
        <div className="wt-dc-obs-row">
          <span className="wt-dc-obs-label">Fecha del evento</span>
          <Val v={formatDate(obs.event_date)} />
        </div>
        <div className="wt-dc-obs-row">
          <span className="wt-dc-obs-label">Sexo</span>
          <Val v={obs.sex ? (SEX_LABEL[obs.sex] ?? obs.sex) : null} />
        </div>
        {obs.life_stage && (
          <div className="wt-dc-obs-row">
            <span className="wt-dc-obs-label">Etapa de vida</span>
            <Val v={obs.life_stage} />
          </div>
        )}
        <div className="wt-dc-obs-row">
          <span className="wt-dc-obs-label">Latitud / Longitud</span>
          <Val v={
            obs.decimal_latitude != null && obs.decimal_longitude != null
              ? `${obs.decimal_latitude.toFixed(5)}, ${obs.decimal_longitude.toFixed(5)}`
              : null
          } />
        </div>
        <div className="wt-dc-obs-row">
          <span className="wt-dc-obs-label">País · Municipio</span>
          <Val v={[obs.country, obs.municipality].filter(Boolean).join(" · ") || null} />
        </div>
        <div className="wt-dc-obs-row">
          <span className="wt-dc-obs-label">Localidad</span>
          <Val v={obs.locality} />
        </div>
        <div className="wt-dc-obs-row">
          <span className="wt-dc-obs-label">Institución · Colección</span>
          <Val v={`${obs.institution_code} / ${obs.collection_code}`} />
        </div>
        <div className="wt-dc-obs-row">
          <span className="wt-dc-obs-label">Licencia</span>
          <Val v={obs.license} />
        </div>
        {obs.occurrence_remarks && (
          <div className="wt-dc-obs-row">
            <span className="wt-dc-obs-label">Notas</span>
            <Val v={obs.occurrence_remarks} />
          </div>
        )}
      </div>
    </div>
  );
}

function Attribution({
  gbifUrl,
  gbifLicense,
}: {
  gbifUrl: string | null;
  gbifLicense: string;
}) {
  return (
    <div className="wt-dc-attribution">
      <div className="wt-dc-attribution-title">Fuente de información</div>
      <div className="wt-dc-attribution-row">
        <span>
          Taxonomía obtenida de{" "}
          <strong style={{ color: "#e8f0ea" }}>
            GBIF — Global Biodiversity Information Facility
          </strong>
        </span>
      </div>
      <div className="wt-dc-attribution-row">
        {gbifUrl ? (
          <a
            className="wt-dc-attribution-link"
            href={gbifUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            Abrir ficha en GBIF ↗
          </a>
        ) : (
          <span style={{ color: "#4a6358", fontSize: 11 }}>
            Ficha GBIF no disponible
          </span>
        )}
        <span className="wt-dc-attribution-license">{gbifLicense}</span>
      </div>
      <div style={{ color: "#4a6358", fontSize: 10.5, marginTop: 2 }}>
        Registro de observación generado por WildTrack Biomonitoring System
      </div>
    </div>
  );
}

function SkeletonBody() {
  return (
    <div className="wt-dc-body" style={{ padding: "16px 20px" }}>
      {[100, 70, 90, 60, 80, 75].map((w, i) => (
        <div
          key={i}
          className="wt-dc-skeleton wt-dc-skel-line"
          style={{ width: `${w}%` }}
        />
      ))}
    </div>
  );
}

// ── Main modal ─────────────────────────────────────────────────────────────────

interface DarwinCoreModalProps {
  animalId: string;
  onClose: () => void;
}

export default function DarwinCoreModal({ animalId, onClose }: DarwinCoreModalProps) {
  const { data, isPending, isError, error } = useDarwinCore(animalId);

  const is404 =
    isError &&
    (error as { response?: { status?: number } })?.response?.status === 404;

  const badge = data ? STATUS_BADGE[data.source_status] : null;

  return (
    <div
      className="wt-dc-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="wt-dc-modal">
        {/* Header — always shown */}
        <div className="wt-dc-header">
          <div className="wt-dc-header-left">
            <span className="wt-dc-eyebrow">Darwin Core · Ficha de especie</span>
            {data ? (
              <>
                <div className="wt-dc-species-name">{data.species}</div>
                {data.taxonomy?.vernacular_name && (
                  <div className="wt-dc-vernacular">{data.taxonomy.vernacular_name}</div>
                )}
              </>
            ) : is404 ? (
              <div className="wt-dc-species-name" style={{ fontStyle: "normal", color: "#8aa395" }}>
                Animal no encontrado
              </div>
            ) : (
              <div
                className="wt-dc-skeleton wt-dc-skel-line"
                style={{ width: 180, height: 18, marginTop: 4 }}
              />
            )}
          </div>
          <button className="wt-dc-close" onClick={onClose} aria-label="Cerrar">×</button>
        </div>

        {/* Status badge */}
        {badge && (
          <div className="wt-dc-status-bar">
            <span className="wt-dc-badge" data-status={data!.source_status}>
              {badge.label}
            </span>
            <span className="wt-dc-status-hint">{badge.hint}</span>
          </div>
        )}

        {/* Body */}
        {isPending && <SkeletonBody />}

        {is404 && (
          <div className="wt-dc-error-body">
            <div className="wt-dc-error-icon">🦎</div>
            <div className="wt-dc-error-title">Animal no encontrado</div>
            <div className="wt-dc-error-sub">
              Este animal no existe en la plataforma o fue eliminado. Verifique que el
              identificador sea correcto.
            </div>
          </div>
        )}

        {isError && !is404 && (
          <div className="wt-dc-error-body">
            <div className="wt-dc-error-icon">⚡</div>
            <div className="wt-dc-error-title">Error al cargar la ficha</div>
            <div className="wt-dc-error-sub">
              No se pudo conectar con el servidor. Verifique su conexión e intente de nuevo.
            </div>
          </div>
        )}

        {data && (
          <>
            <div className="wt-dc-body">
              {/* Taxonomy */}
              {data.taxonomy ? (
                <TaxonomySection tax={data.taxonomy} />
              ) : (
                <TaxonomyUnavailable status={data.source_status} />
              )}

              {/* Observation */}
              <ObservationSection obs={data.observation} />
            </div>

            {/* Attribution — outside scroll so always visible */}
            <Attribution
              gbifUrl={data.sources.taxonomy.url}
              gbifLicense={data.sources.taxonomy.license}
            />
          </>
        )}
      </div>
    </div>
  );
}
