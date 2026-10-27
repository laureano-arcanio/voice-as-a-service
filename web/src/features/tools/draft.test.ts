import { describe, expect, it } from 'vitest';
import {
  blankParam,
  errorTab,
  fromToolDraft,
  llmParameters,
  llmTool,
  requiredSecrets,
  rowsToSchema,
  schemaToRows,
  syncPathRows,
  toolPathLabel,
  toToolDraft,
  urlPathVars,
} from './draft';

const HTTP = {
  description: 'Busca turnos libres.',
  confirm: true,
  messages: {
    start: 'Ya lo busco.',
    delayed: { after_ms: 4000, text: 'Sigo buscando.' },
    failed: 'No pude.',
  },
  response: { pick: ['data.turnos'], max_chars: 2000 },
  assign: [{ var: 'cliente_id', path: 'data.id', hide: true }],
  http: {
    method: 'POST',
    url: 'https://api.ejemplo.com/sucursales/{sucursal}/turnos',
    path: { sucursal: { type: 'string', value: 'centro' } },
    query: {
      fecha: { type: 'string', description: 'YYYY-MM-DD', format: 'date', required: true },
      tipo: { type: 'string', description: 'Tipo', enum: ['control', 'urgencia'] },
      tel: { type: 'string', value: '{{call.from}}' },
    },
    headers: { 'X-Sucursal': 'centro', 'X-Token': '{{secrets.OTRO_TOKEN}}' },
    body: {
      type: 'object',
      properties: {
        nombre: { type: 'string', description: 'Nombre' },
        canal: { type: 'string', value: 'atentina' },
        extra: { type: 'object', properties: { a: { type: 'string' } } },
      },
      required: ['nombre'],
    },
    auth: { type: 'bearer', secret: 'CRM_TOKEN' },
    timeout_ms: 5000,
    retries: 1,
    sign: true,
  },
};

const CODE = {
  description: 'Deuda por DNI.',
  parameters: {
    type: 'object',
    properties: { dni: { type: 'string', description: 'DNI sin puntos' } },
    required: ['dni'],
  },
  code: 'export default async function ({ args }) { return { ok: true }; }',
  secrets: ['CRM_TOKEN'],
  allowed_hosts: ['api.crm.com'],
  timeout_ms: 7000,
};

describe('toToolDraft / fromToolDraft', () => {
  it('HTTP: ida y vuelta sin perder nada', () => {
    expect(fromToolDraft(toToolDraft('http', HTTP))).toEqual(HTTP);
  });

  it('código: ida y vuelta', () => {
    expect(fromToolDraft(toToolDraft('code', CODE))).toEqual(CODE);
  });

  it('la definición normalizada del servidor (con defaults) vuelve compacta', () => {
    const normalized = {
      description: 'x',
      confirm: false,
      messages: {},
      response: { pick: [], max_chars: 4000 },
      assign: [],
      http: {
        method: 'GET',
        url: 'https://api.ejemplo.com/x',
        path: {},
        query: { q: { type: 'string', description: 'q', required: false } },
        headers: {},
        content_type: 'application/json',
        auth: { type: 'none', client_auth: 'body' },
        timeout_ms: 8000,
        retries: 0,
        sign: false,
      },
    };
    expect(fromToolDraft(toToolDraft('http', normalized))).toEqual({
      description: 'x',
      http: {
        method: 'GET',
        url: 'https://api.ejemplo.com/x',
        query: { q: { type: 'string', description: 'q' } },
      },
    });
  });

  it('GET no manda body aunque el borrador lo tenga', () => {
    const d = toToolDraft('http', HTTP);
    const out = fromToolDraft({ ...d, http: { ...d.http, method: 'GET' } });
    expect((out.http as Record<string, unknown>).body).toBeUndefined();
  });
});

describe('parámetros', () => {
  it('filas -> JSON Schema: los fijos llevan value y no son obligatorios', () => {
    const rows = [
      { ...blankParam('dni'), description: 'DNI', required: true },
      { ...blankParam('cantidad'), type: 'integer' as const, source: 'fixed' as const, value: '3' },
      { ...blankParam('tags'), type: 'array' as const, source: 'fixed' as const, value: 'a, b' },
      { ...blankParam(''), description: 'sin nombre, se ignora' },
    ];
    expect(rowsToSchema(rows)).toEqual({
      type: 'object',
      properties: {
        dni: { type: 'string', description: 'DNI' },
        cantidad: { type: 'integer', value: 3 },
        tags: { type: 'array', value: ['a', 'b'] },
      },
      required: ['dni'],
    });
  });

  it('JSON Schema -> filas -> el mismo esquema (conserva lo que no edita)', () => {
    const schema = CODE.parameters;
    expect(rowsToSchema(schemaToRows(schema))).toEqual(schema);
    const nested = HTTP.http.body;
    expect(rowsToSchema(schemaToRows(nested))).toEqual(nested);
  });

  it('las {variables} de la URL arman las filas de la ruta', () => {
    expect(urlPathVars('https://api.x.com/a/{id}/b/{otro}?q={x}')).toEqual(['id', 'otro']);
    expect(urlPathVars('https://api.x.com/{{secrets.T}}/x')).toEqual([]);
    const rows = syncPathRows([{ ...blankParam('id'), description: 'el id' }], 'https://x.com/{id}/{dni}');
    expect(rows.map((r) => [r.name, r.description])).toEqual([
      ['id', 'el id'],
      ['dni', ''],
    ]);
    expect(syncPathRows(rows, 'https://x.com/{dni}').map((r) => r.name)).toEqual(['dni']);
  });
});

describe('lo que ve el modelo y los secretos', () => {
  it('llmParameters: solo lo que completa el agente (como app/tools/schema.py)', () => {
    expect(llmParameters('http', HTTP)).toEqual({
      type: 'object',
      properties: {
        fecha: { type: 'string', description: 'YYYY-MM-DD', format: 'date' },
        tipo: { type: 'string', description: 'Tipo', enum: ['control', 'urgencia'] },
        nombre: { type: 'string', description: 'Nombre' },
        extra: { type: 'object', properties: { a: { type: 'string' } } },
      },
      required: ['fecha', 'nombre'],
    });
    expect(llmParameters('code', CODE)).toEqual(CODE.parameters);
  });

  it('requiredSecrets: auth, templates y la firma', () => {
    expect(requiredSecrets('http', HTTP)).toEqual(['ATENTINA_SIGNING_SECRET', 'CRM_TOKEN', 'OTRO_TOKEN']);
    expect(requiredSecrets('code', CODE)).toEqual(['CRM_TOKEN']);
  });
});

describe('errores del servidor', () => {
  it('rótulo y pestaña de cada ruta', () => {
    expect(toolPathLabel('definition.http.query.dni.description')).toBe('Query › dni › Descripción');
    expect(toolPathLabel('slug')).toBe('Nombre');
    expect(errorTab('definition.http.auth')).toBe('auth');
    expect(errorTab('definition.http', 'http.path: las {variables} de la URL')).toBe('ruta');
    expect(errorTab('definition.messages.start')).toBe('voz');
  });
});

describe('llmTool', () => {
  it('agrega a la descripción el pedido de confirmación y el protocolo del resultado, como el servidor', () => {
    const t = llmTool('reservar', 'http', {
      description: 'Reserva.',
      confirm: true,
      http: { method: 'POST', url: 'https://x' },
    });
    expect((t.function as { description: string }).description).toBe(
      'Reserva. Antes de usarla, confirmá con la persona lo que vas a hacer. Devuelve {"ok": true, "data": ...} o {"ok": false, "error": ...}.',
    );
  });
});
