"use client";

import { useRef, useState } from "react";

interface PdfDropzoneProps {
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  disabled?: boolean;
}

export function PdfDropzone({
  selectedFile,
  onFileSelect,
  disabled = false,
}: PdfDropzoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    if (disabled) return;
    setIsDragOver(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    setIsDragOver(false);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.type === "application/pdf" || file.name.endsWith(".pdf") || file.name.endsWith(".txt")) {
        onFileSelect(file);
      }
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files.length > 0) {
      onFileSelect(e.target.files[0]);
    }
  }

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt,application/pdf,text/plain"
        onChange={handleFileChange}
        style={{ display: "none" }}
        disabled={disabled}
      />

      {!selectedFile ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !disabled && inputRef.current?.click()}
          className={`dropzone ${isDragOver ? "dragging" : ""}`}
        >
          <div className="dropzone-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="12" y1="18" x2="12" y2="12" />
              <line x1="9" y1="15" x2="15" y2="15" />
            </svg>
          </div>
          <h4 className="dropzone-title">Upload Research Paper (PDF / TXT)</h4>
          <p className="dropzone-copy">Drag and drop file here, or click to browse local files</p>
        </div>
      ) : (
        <div
          className="card card-padding"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "14px 18px",
            borderColor: "var(--color-primary)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
            <span style={{ fontSize: "1.5rem" }}>📄</span>
            <div style={{ minWidth: 0 }}>
              <p
                style={{
                  fontSize: "0.92rem",
                  fontWeight: 600,
                  margin: 0,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  color: "var(--text-primary)",
                }}
              >
                {selectedFile.name}
              </p>
              <span style={{ fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
                {formatFileSize(selectedFile.size)}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => onFileSelect(null)}
            disabled={disabled}
            className="icon-button"
            title="Remove file"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
