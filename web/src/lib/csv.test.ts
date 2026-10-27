import { describe, expect, it } from 'vitest';
import { csvFilename, toCsv } from './csv';

describe('toCsv', () => {
  it('encabezado, valores crudos y comillas donde hace falta', () => {
    const rows = [
      { name: 'Turnos, centro', calls: 12, pct: 41.5 },
      { name: 'Dice "hola"', calls: 0, pct: null },
    ];
    const csv = toCsv(rows, [
      { label: 'Agente', value: 'name' },
      { label: 'Llamadas', value: 'calls' },
      { label: '% conversión', value: (r) => r.pct },
    ]);
    expect(csv).toBe('Agente,Llamadas,% conversión\r\n"Turnos, centro",12,41.5\r\n"Dice ""hola""",0,');
  });

  it('sin filas, solo el encabezado', () => {
    expect(toCsv([], [{ label: 'A', value: () => 1 }])).toBe('A');
  });
});

describe('csvFilename', () => {
  it('sin acentos ni espacios', () => {
    expect(csvFilename('reportes', 'Llamadas por línea', '2026-10-01', null)).toBe(
      'reportes-llamadas-por-linea-2026-10-01.csv',
    );
  });
});
