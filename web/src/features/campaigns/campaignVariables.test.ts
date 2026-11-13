import { describe, expect, it } from 'vitest';
import { CATALOG } from '@/components/variables/fixtures';
import type { VariableSpec } from '@/features/agents/definition';
import {
  applyMapping,
  csvColumns,
  defaultMapping,
  mappingAlerts,
  variableKey,
  variableMapping,
} from './campaignVariables';

const VAR = (name: string, def = ''): VariableSpec => ({ name, default: def, description: '' });

describe('columnas del CSV de una campaña', () => {
  it('normaliza el nombre de la columna como el backend', () => {
    expect(variableKey('Nombre Cliente')).toBe('nombre_cliente');
    expect(variableKey('  Fecha Vence  ')).toBe('fecha_vence');
    expect(variableKey('Deuda USD')).toBe('deuda_usd');
  });

  it('separa los roles, las variables y lo que el backend ignora', () => {
    const cols = csvColumns('telefono,Nombre Cliente,2cuotas,channel,Nombre Cliente,Deuda', CATALOG);
    expect(cols.map((c) => [c.header, c.name, c.data, c.problem])).toEqual([
      ['telefono', 'telefono', false, undefined],
      ['Nombre Cliente', 'nombre_cliente', true, undefined],
      ['2cuotas', '2cuotas', false, 'nombre inválido'],
      ['channel', 'channel', false, 'es del sistema'],
      ['Nombre Cliente', 'nombre_cliente', false, 'repetida: llega la primera'],
      ['Deuda', 'deuda', true, undefined],
    ]);
  });

  it('preselecciona la columna con el mismo nombre y deja el resto en su default', () => {
    const cols = csvColumns('telefono,Nombre Cliente,deuda', CATALOG);
    const vars = [VAR('nombre_cliente', 'Ana'), VAR('deuda', '1000'), VAR('motivo')];
    const defaults = defaultMapping(vars, cols);
    expect(defaults).toEqual({ nombre_cliente: 1, deuda: 2 });
    expect(variableMapping(vars.map((v) => v.name), defaults)).toEqual({ nombre_cliente: 1, deuda: 2 });
    // Elegir "sin columna" en deuda gana sobre la que traía el CSV.
    expect(variableMapping(vars.map((v) => v.name), defaults, { deuda: null })).toEqual({
      nombre_cliente: 1,
    });
  });

  it('reescribe el encabezado con el nombre de la variable y quita la que no se usa', () => {
    const csv = 'telefono,Nombre Cliente,deuda\n3515551234,Ana,500\n';
    const cols = csvColumns(csv, CATALOG);
    const mapping = { nombre_cliente: 1 };
    // deuda existe en el CSV pero se eligió su default: se quita la columna.
    expect(applyMapping(csv, cols, mapping, ['nombre_cliente', 'deuda'])).toBe(
      'telefono,nombre_cliente\n3515551234,Ana\n',
    );
    // Mapear una columna de nombre distinto también la renombra.
    expect(applyMapping(csv, cols, { deuda: 2, nombre_cliente: 1 }, ['nombre_cliente', 'deuda'])).toBe(
      'telefono,nombre_cliente,deuda\n3515551234,Ana,500\n',
    );
    // Sin mapeo ni variables, el CSV viaja tal cual.
    const plano = 'telefono;nombre\n3515551234;"Ana, la jefa"';
    expect(applyMapping(plano, csvColumns(plano, CATALOG), {}, [])).toBe(plano);
  });

  it('avisa la variable sin default ni columna, las columnas sueltas y las ignoradas', () => {
    const csv = 'telefono,Nombre Cliente,Deuda,2cuotas';
    const cols = csvColumns(csv, CATALOG);
    const vars = [VAR('nombre_cliente'), VAR('deuda', '1000'), VAR('motivo')];
    const alerts = mappingAlerts({
      variables: vars,
      columns: cols,
      mapping: defaultMapping(vars, cols),
      contactIds: ['k1'],
      catalog: CATALOG,
    });
    expect(alerts.empty).toEqual(['motivo']);
    expect(alerts.columnsLeft.map((c) => c.header)).toEqual([]);
    expect(alerts.ignored.map((c) => c.header)).toEqual(['2cuotas']);
    expect(alerts.overLimit).toBeNull();
    expect(alerts.agendaMissing).toEqual(['nombre_cliente', 'deuda', 'motivo']);
  });
});
