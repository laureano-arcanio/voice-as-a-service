// CSV de lo que muestra una tabla o un grafico (lo arma la UI con los datos que ya tiene).

export interface CsvColumn<T> {
  label: string;
  /** El valor de la celda: una clave de la fila o una funcion. */
  value: keyof T | ((row: T) => unknown);
}

function cell(v: unknown): string {
  if (v == null) return '';
  const s = typeof v === 'object' ? JSON.stringify(v) : String(v);
  // Comillas si hay separador, comillas, saltos de linea o espacios en los bordes.
  return /[",\n\r]|^\s|\s$/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** Texto CSV (coma como separador, CRLF entre filas), con encabezado. Los numeros van crudos (punto decimal). */
export function toCsv<T>(rows: readonly T[], columns: readonly CsvColumn<T>[]): string {
  const head = columns.map((c) => cell(c.label)).join(',');
  const body = rows.map((r) =>
    columns.map((c) => cell(typeof c.value === 'function' ? c.value(r) : r[c.value])).join(','),
  );
  return [head, ...body].join('\r\n');
}

/** Nombre de archivo seguro: minusculas, sin acentos ni espacios. */
export function csvFilename(...parts: (string | null | undefined)[]): string {
  const base = parts
    .filter(Boolean)
    .join('-')
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
  return `${base || 'datos'}.csv`;
}

/** Descarga el CSV en el navegador. Con BOM, asi Excel lee bien los acentos. */
export function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob(['﻿', csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
