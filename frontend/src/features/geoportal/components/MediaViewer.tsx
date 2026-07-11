import { useState, useEffect } from "react";
import "./MediaViewer.css";

interface MediaViewerProps {
  urls: string[];
  initialIndex?: number;
  onClose: () => void;
}

export default function MediaViewer({ urls, initialIndex = 0, onClose }: MediaViewerProps) {
  const [idx, setIdx] = useState(initialIndex);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft") setIdx((i) => Math.max(0, i - 1));
      if (e.key === "ArrowRight") setIdx((i) => Math.min(urls.length - 1, i + 1));
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [urls.length, onClose]);

  return (
    <div className="wt-viewer-overlay" onClick={onClose}>
      <div className="wt-viewer-box" onClick={(e) => e.stopPropagation()}>
        <button className="wt-viewer-close" onClick={onClose} aria-label="Cerrar">✕</button>

        <img
          className="wt-viewer-img"
          src={urls[idx]}
          alt={`Foto ${idx + 1} de ${urls.length}`}
        />

        {urls.length > 1 && (
          <>
            <button
              className="wt-viewer-nav wt-viewer-prev"
              disabled={idx === 0}
              onClick={() => setIdx((i) => i - 1)}
              aria-label="Foto anterior"
            >
              ‹
            </button>
            <button
              className="wt-viewer-nav wt-viewer-next"
              disabled={idx === urls.length - 1}
              onClick={() => setIdx((i) => i + 1)}
              aria-label="Foto siguiente"
            >
              ›
            </button>
            <div className="wt-viewer-counter">{idx + 1} / {urls.length}</div>
          </>
        )}
      </div>
    </div>
  );
}
