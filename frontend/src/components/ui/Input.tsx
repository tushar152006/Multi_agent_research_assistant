import React, { InputHTMLAttributes, SelectHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export function Input({ label, id, className = '', ...props }: InputProps) {
  const inputId = id || label.toLowerCase().replace(/\s+/g, '-');
  
  return (
    <div className={`input-group ${className}`} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <label htmlFor={inputId} style={{ font: "var(--caption)", color: "var(--color-text-muted)", letterSpacing: "0.06em" }}>
        {label}
      </label>
      <input 
        id={inputId}
        className="control-select"
        style={{ width: "100%", height: 42, background: "var(--color-surface-elevated)", border: "1px solid var(--color-border)", borderRadius: 10, padding: "0 12px", color: "var(--color-text-primary)", fontSize: 14 }}
        {...props}
      />
    </div>
  );
}

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
}

export function Textarea({ label, id, className = '', ...props }: TextareaProps) {
  const inputId = id || label.toLowerCase().replace(/\s+/g, '-');
  
  return (
    <div className={`input-group ${className}`} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <label htmlFor={inputId} style={{ font: "var(--caption)", color: "var(--color-text-muted)", letterSpacing: "0.06em" }}>
        {label}
      </label>
      <textarea 
        id={inputId}
        className="query-input"
        style={{ width: "100%", minHeight: 90, padding: 12, border: "1px solid var(--color-border)", borderRadius: 12, background: "var(--color-surface-elevated)", color: "var(--color-text-primary)", resize: "vertical" }}
        {...props}
      />
    </div>
  );
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: { label: string; value: string }[];
}

export function Select({ label, id, options, className = '', ...props }: SelectProps) {
  const selectId = id || label.toLowerCase().replace(/\s+/g, '-');
  
  return (
    <div className={`input-group ${className}`} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <label htmlFor={selectId} style={{ font: "var(--caption)", color: "var(--color-text-muted)", letterSpacing: "0.06em" }}>
        {label}
      </label>
      <select 
        id={selectId}
        className="control-select"
        style={{ width: "100%", cursor: "pointer" }}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
