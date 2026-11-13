import type { VariableCatalog } from './catalog';

/** Catálogo mínimo con la forma de `GET /variables/catalog`, para los tests. */
export const CATALOG: VariableCatalog = {
  name_pattern: '^[a-z][a-z0-9_]{0,63}$',
  reserved: ['channel', 'today', 'now'],
  reserved_prefixes: ['call.', 'agent.', 'secrets.', 'fields.'],
  limits: { max_variables: 30, max_value_chars: 2000 },
  system: [
    {
      name: 'call.phone',
      description: 'Número de la otra punta',
      example: '+5491155550000',
      applies_to: ['prompt', 'first_message', 'tool', 'handoff'],
    },
    {
      name: 'today',
      description: 'Fecha de inicio',
      example: 'jueves 2026-11-12',
      applies_to: ['prompt', 'first_message', 'analysis', 'handoff', 'tool'],
    },
    { name: 'call.summary', description: 'Resumen del análisis', example: '…', applies_to: ['tool'] },
    { name: 'fields.<campo>', description: 'Dato del análisis', example: 'true', applies_to: ['tool'] },
    { name: 'area', description: 'Área a la que se deriva', example: 'Ventas', applies_to: ['handoff'] },
  ],
};

export const DECLARED = [
  { name: 'nombre', description: 'Nombre del cliente' },
  { name: 'deuda', description: '' },
];
