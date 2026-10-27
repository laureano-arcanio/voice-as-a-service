import type { ToolType } from '@/api/types';

// Borrador del editor de una herramienta: la definicion (app/tools/schema.py) en filas editables.
// fromToolDraft(toToolDraft(d)) da la misma definicion. Lo que el formulario no conoce se conserva.

export type Json = Record<string, unknown>;
export type ParamType = 'string' | 'integer' | 'number' | 'boolean' | 'array';
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
export type AuthType = 'none' | 'credential' | 'bearer' | 'api_key' | 'basic' | 'oauth2_client_credentials';
export type CredentialType = Exclude<AuthType, 'none' | 'credential'>;

export const PARAM_TYPES: { value: ParamType; label: string }[] = [
  { value: 'string', label: 'Texto' },
  { value: 'integer', label: 'Entero' },
  { value: 'number', label: 'Número' },
  { value: 'boolean', label: 'Sí o no' },
  { value: 'array', label: 'Lista' },
];

export const METHODS: HttpMethod[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];

/** Los tipos de una credencial (y de la autenticacion configurada en la herramienta). */
export const AUTH_TYPES: { value: CredentialType; label: string }[] = [
  { value: 'bearer', label: 'Bearer token' },
  { value: 'api_key', label: 'API key' },
  { value: 'basic', label: 'Usuario y clave (Basic)' },
  { value: 'oauth2_client_credentials', label: 'OAuth2 (client credentials)' },
];

/** Templates de los valores fijos (app/tools/schema.py, NAMESPACES). */
export const TEMPLATE_VARS: { group: string; items: { value: string; label: string }[] }[] = [
  {
    group: 'Conversación',
    items: [
      { value: '{{call.id}}', label: 'Id de la conversación' },
      { value: '{{call.channel}}', label: 'Canal' },
      { value: '{{call.mode}}', label: 'Modo' },
      { value: '{{call.from}}', label: 'Número de quien llama' },
      { value: '{{call.to}}', label: 'Número llamado' },
    ],
  },
  {
    group: 'Agente',
    items: [
      { value: '{{agent.slug}}', label: 'Slug del agente' },
      { value: '{{agent.version}}', label: 'Versión del agente' },
    ],
  },
  {
    group: 'Fecha',
    items: [
      { value: '{{now}}', label: 'Fecha y hora' },
      { value: '{{today}}', label: 'Fecha de hoy' },
    ],
  },
];

export const SECRET_RE = /^[A-Z][A-Z0-9_]{1,63}$/;
export const TOOL_SLUG_RE = /^[a-z][a-z0-9_]{1,63}$/;
export const SIGNING_SECRET = 'ATENTINA_SIGNING_SECRET';
const TEMPLATE_RE = /\{\{\s*([a-z]+)(?:\.([A-Za-z0-9_]+))?\s*\}\}/g;
const PATH_VAR_RE = /\{([A-Za-z_][A-Za-z0-9_]*)\}/g;

/** Una fila de parametro: de la ruta, de la query, del body o de los parametros del codigo. */
export interface ParamRow {
  key: string;
  name: string;
  type: ParamType;
  /** agent: lo completa el agente (lleva descripcion); fixed: valor fijo (literal o template). */
  source: 'agent' | 'fixed';
  description: string;
  /** El valor fijo como texto; las listas, separadas por coma. */
  value: string;
  required: boolean;
  /** Valores posibles (solo con source agent). */
  options: string[];
  /** Claves que el formulario no edita (format, items, propiedades anidadas...): se conservan. */
  extra: Json;
}

export interface HeaderRow {
  key: string;
  name: string;
  value: string;
}

export interface AssignRow {
  key: string;
  var: string;
  path: string;
  hide: boolean;
}

export interface HttpDraft {
  method: HttpMethod;
  url: string;
  path: ParamRow[];
  query: ParamRow[];
  headers: HeaderRow[];
  /** null = sin body. */
  body: ParamRow[] | null;
  contentType: 'application/json' | 'application/x-www-form-urlencoded';
  /** auth tal cual (type, secret, header, prefix, name, in, username, token_url, ...). */
  auth: Json;
  timeoutMs: number;
  retries: number;
  sign: boolean;
}

export interface CodeDraft {
  parameters: ParamRow[];
  code: string;
  secrets: string[];
  allowedHosts: string[];
  timeoutMs: number;
}

export interface ToolDraft {
  type: ToolType;
  description: string;
  confirm: boolean;
  start: string;
  delayed: { text: string; afterMs: number } | null;
  failed: string;
  pick: string[];
  maxChars: number;
  assign: AssignRow[];
  http: HttpDraft;
  code: CodeDraft;
}

export const HTTP_DEFAULTS = { timeoutMs: 8000, retries: 0 };
export const CODE_TIMEOUT_MS = 5000;
export const MAX_CHARS = 4000;
export const DELAYED_MS = 3000;

let seq = 0;
export const newKey = () => `t${++seq}`;

const obj = (x: unknown): Json => (x && typeof x === 'object' && !Array.isArray(x) ? (x as Json) : {});
const str = (x: unknown): string => (typeof x === 'string' ? x : x == null ? '' : String(x));
const num = (x: unknown, d: number) => (typeof x === 'number' ? x : d);
const without = (o: Json, keys: string[]): Json =>
  Object.fromEntries(Object.entries(o).filter(([k]) => !keys.includes(k)));

const isParamType = (t: unknown): t is ParamType =>
  t === 'string' || t === 'integer' || t === 'number' || t === 'boolean' || t === 'array';

/** Valor fijo de la API -> texto del campo. */
function valueText(v: unknown): string {
  if (Array.isArray(v)) return v.map(str).join(', ');
  return str(v);
}

/** Texto del campo -> valor fijo, segun el tipo. Los templates quedan como texto. */
export function parseValue(type: ParamType, text: string): unknown {
  const t = text.trim();
  if (type === 'array')
    return t
      .split(',')
      .map((x) => x.trim())
      .filter(Boolean);
  if ((type === 'integer' || type === 'number') && /^-?\d+(\.\d+)?$/.test(t)) return Number(t);
  if (type === 'boolean' && (t === 'true' || t === 'false')) return t === 'true';
  return text;
}

export function blankParam(name = '', source: ParamRow['source'] = 'agent'): ParamRow {
  return {
    key: newKey(),
    name,
    type: 'string',
    source,
    description: '',
    value: '',
    required: false,
    options: [],
    extra: {},
  };
}

// ---------- parametros de path y query: {nombre: Param} ----------

function toParamRows(raw: unknown, alwaysRequired = false): ParamRow[] {
  return Object.entries(obj(raw)).map(([name, r]) => {
    const p = obj(r);
    const fixed = p.value !== undefined && p.value !== null;
    return {
      key: newKey(),
      name,
      type: isParamType(p.type) ? p.type : 'string',
      source: fixed ? 'fixed' : 'agent',
      description: str(p.description),
      value: fixed ? valueText(p.value) : '',
      required: alwaysRequired || p.required === true,
      options: Array.isArray(p.enum) ? p.enum.map(str) : [],
      extra: without(p, ['type', 'description', 'value', 'required', 'enum']),
    };
  });
}

function enumValues(row: ParamRow): (string | number)[] {
  return row.type === 'integer' || row.type === 'number'
    ? row.options.map((o) => (Number.isNaN(Number(o)) ? o : Number(o)))
    : row.options;
}

function fromParamRows(rows: ParamRow[], withRequired: boolean): Json {
  const out: Json = {};
  for (const r of rows) {
    if (!r.name.trim()) continue;
    out[r.name.trim()] = {
      ...r.extra,
      type: r.type,
      ...(r.source === 'fixed'
        ? { value: parseValue(r.type, r.value) }
        : {
            ...(r.description.trim() ? { description: r.description } : {}),
            ...(r.options.length ? { enum: enumValues(r) } : {}),
          }),
      ...(withRequired && r.required && r.source === 'agent' ? { required: true } : {}),
    };
  }
  return out;
}

// ---------- JSON Schema de tipo object (body y parametros del codigo) ----------

export function schemaToRows(raw: unknown): ParamRow[] {
  const schema = obj(raw);
  const required = new Set(Array.isArray(schema.required) ? schema.required.map(str) : []);
  return Object.entries(obj(schema.properties)).map(([name, r]) => {
    const p = obj(r);
    const fixed = 'value' in p;
    return {
      key: newKey(),
      name,
      // Un tipo que el formulario no edita (object) se conserva en extra.
      type: isParamType(p.type) ? p.type : 'string',
      source: fixed ? 'fixed' : 'agent',
      description: str(p.description),
      value: fixed ? valueText(p.value) : '',
      required: required.has(name),
      options: Array.isArray(p.enum) ? p.enum.map(str) : [],
      extra: without(
        p,
        isParamType(p.type) ? ['type', 'description', 'value', 'enum'] : ['description', 'value', 'enum'],
      ),
    };
  });
}

/** Filas -> {type: object, properties, required}. Las fijas llevan value y no van a required. */
export function rowsToSchema(rows: ParamRow[], base: Json = {}): Json {
  const properties: Json = {};
  const required: string[] = [];
  for (const r of rows) {
    const name = r.name.trim();
    if (!name) continue;
    const nested = 'type' in r.extra;
    properties[name] = {
      ...(nested ? {} : { type: r.type }),
      ...r.extra,
      ...(r.source === 'fixed'
        ? { value: parseValue(r.type, r.value) }
        : {
            ...(r.description.trim() ? { description: r.description } : {}),
            ...(r.options.length ? { enum: enumValues(r) } : {}),
          }),
    };
    if (r.required && r.source === 'agent') required.push(name);
  }
  return {
    ...without(base, ['type', 'properties', 'required']),
    type: 'object',
    properties,
    ...(required.length ? { required } : {}),
  };
}

// ---------- la herramienta ----------

/** Las {variables} de la ruta de la URL, en orden. */
export function urlPathVars(url: string): string[] {
  // Sin el esquema, el host, la query ni el fragmento.
  const path = url.replace(/^[a-z][a-z0-9+.-]*:\/\/[^/?#]*/i, '').split(/[?#]/)[0]!;
  // Las {{variables}} de los templates no son de la ruta.
  const noTemplates = path.replace(/\{\{[^}]*\}\}/g, '');
  const names: string[] = [];
  for (const m of noTemplates.matchAll(PATH_VAR_RE)) if (!names.includes(m[1]!)) names.push(m[1]!);
  return names;
}

/** Ajusta las filas de path a las {variables} de la URL: suma las nuevas y saca las que ya no estan. */
export function syncPathRows(rows: ParamRow[], url: string): ParamRow[] {
  const vars = urlPathVars(url);
  return vars.map((name) => rows.find((r) => r.name === name) ?? { ...blankParam(name), required: true });
}

export function emptyDraft(type: ToolType): ToolDraft {
  return {
    type,
    description: '',
    confirm: false,
    start: '',
    delayed: null,
    failed: '',
    pick: [],
    maxChars: MAX_CHARS,
    assign: [],
    http: {
      method: 'GET',
      url: '',
      path: [],
      query: [],
      headers: [],
      body: null,
      contentType: 'application/json',
      auth: { type: 'none' },
      ...HTTP_DEFAULTS,
      sign: false,
    },
    code: { parameters: [], code: '', secrets: [], allowedHosts: [], timeoutMs: CODE_TIMEOUT_MS },
  };
}

export function toToolDraft(type: ToolType, d: Json): ToolDraft {
  const base = emptyDraft(type);
  const msgs = obj(d.messages);
  const delayed = obj(msgs.delayed);
  const response = obj(d.response);
  const h = obj(d.http);
  const method = str(h.method).toUpperCase();
  return {
    ...base,
    description: str(d.description),
    confirm: d.confirm === true,
    start: str(msgs.start),
    delayed: msgs.delayed ? { text: str(delayed.text), afterMs: num(delayed.after_ms, DELAYED_MS) } : null,
    failed: str(msgs.failed),
    pick: Array.isArray(response.pick) ? response.pick.map(str) : [],
    maxChars: num(response.max_chars, MAX_CHARS),
    assign: (Array.isArray(d.assign) ? d.assign : []).map((r) => {
      const a = obj(r);
      return { key: newKey(), var: str(a.var), path: str(a.path), hide: a.hide === true };
    }),
    http:
      type === 'http'
        ? {
            method: (METHODS as string[]).includes(method) ? (method as HttpMethod) : 'GET',
            url: str(h.url),
            path: toParamRows(h.path, true),
            query: toParamRows(h.query),
            headers: Object.entries(obj(h.headers)).map(([name, value]) => ({
              key: newKey(),
              name,
              value: str(value),
            })),
            body: h.body != null ? schemaToRows(h.body) : null,
            contentType:
              h.content_type === 'application/x-www-form-urlencoded'
                ? 'application/x-www-form-urlencoded'
                : 'application/json',
            auth: { type: 'none', ...obj(h.auth) },
            timeoutMs: num(h.timeout_ms, HTTP_DEFAULTS.timeoutMs),
            retries: num(h.retries, HTTP_DEFAULTS.retries),
            sign: h.sign === true,
          }
        : base.http,
    code:
      type === 'code'
        ? {
            parameters: schemaToRows(d.parameters),
            code: str(d.code),
            secrets: Array.isArray(d.secrets) ? d.secrets.map(str) : [],
            allowedHosts: Array.isArray(d.allowed_hosts) ? d.allowed_hosts.map(str) : [],
            timeoutMs: num(d.timeout_ms, CODE_TIMEOUT_MS),
          }
        : base.code,
  };
}

/** Solo las claves de auth que usa su tipo (el resto el servidor las rechaza o las ignora). */
const AUTH_KEYS: Record<AuthType, string[]> = {
  none: [],
  credential: ['credential'],
  bearer: ['secret', 'header', 'prefix'],
  api_key: ['secret', 'name', 'in'],
  basic: ['secret', 'username'],
  oauth2_client_credentials: ['secret', 'token_url', 'client_id', 'scope', 'audience', 'client_auth'],
};

export function cleanAuth(auth: Json): Json {
  const type = (str(auth.type) || 'none') as AuthType;
  const keys = AUTH_KEYS[type] ?? [];
  const out: Json = { type };
  for (const k of keys) {
    const v = auth[k];
    if (v !== undefined && v !== null && v !== '') out[k] = v;
  }
  return out;
}

export function fromToolDraft(t: ToolDraft): Json {
  const messages: Json = {
    ...(t.start.trim() ? { start: t.start } : {}),
    ...(t.delayed && t.delayed.text.trim()
      ? { delayed: { after_ms: t.delayed.afterMs, text: t.delayed.text } }
      : {}),
    ...(t.failed.trim() ? { failed: t.failed } : {}),
  };
  const common: Json = {
    description: t.description,
    ...(t.confirm ? { confirm: true } : {}),
    ...(Object.keys(messages).length ? { messages } : {}),
    ...(t.pick.length || t.maxChars !== MAX_CHARS
      ? { response: { ...(t.pick.length ? { pick: t.pick } : {}), max_chars: t.maxChars } }
      : {}),
    ...(t.assign.length
      ? {
          assign: t.assign
            .filter((a) => a.var.trim() || a.path.trim())
            .map((a) => ({ var: a.var.trim(), path: a.path.trim(), ...(a.hide ? { hide: true } : {}) })),
        }
      : {}),
  };
  if (t.type === 'code') {
    const c = t.code;
    return {
      ...common,
      parameters: rowsToSchema(c.parameters),
      code: c.code,
      ...(c.secrets.length ? { secrets: c.secrets } : {}),
      ...(c.allowedHosts.length ? { allowed_hosts: c.allowedHosts } : {}),
      ...(c.timeoutMs !== CODE_TIMEOUT_MS ? { timeout_ms: c.timeoutMs } : {}),
    };
  }
  const h = t.http;
  const headers = Object.fromEntries(
    h.headers.filter((r) => r.name.trim()).map((r) => [r.name.trim(), r.value]),
  );
  const withBody = h.body !== null && h.method !== 'GET' && h.method !== 'DELETE';
  const auth = cleanAuth(h.auth);
  return {
    ...common,
    http: {
      method: h.method,
      url: h.url.trim(),
      ...(h.path.length ? { path: fromParamRows(h.path, false) } : {}),
      ...(h.query.length ? { query: fromParamRows(h.query, true) } : {}),
      ...(Object.keys(headers).length ? { headers } : {}),
      ...(withBody ? { body: rowsToSchema(h.body!) } : {}),
      ...(withBody && h.contentType !== 'application/json' ? { content_type: h.contentType } : {}),
      ...(auth.type !== 'none' ? { auth } : {}),
      ...(h.timeoutMs !== HTTP_DEFAULTS.timeoutMs ? { timeout_ms: h.timeoutMs } : {}),
      ...(h.retries !== HTTP_DEFAULTS.retries ? { retries: h.retries } : {}),
      ...(h.sign ? { sign: true } : {}),
    },
  };
}

// ---------- lo que ve el modelo (espejo de llm_parameters en app/tools/schema.py) ----------

function llmParam(p: Json): Json {
  const type = isParamType(p.type) ? p.type : 'string';
  return {
    type,
    ...(p.description ? { description: p.description } : {}),
    ...(Array.isArray(p.enum) && p.enum.length ? { enum: p.enum } : {}),
    ...(p.format ? { format: p.format } : {}),
    ...(type === 'array' ? { items: p.items ?? { type: 'string' } } : {}),
  };
}

/** El JSON Schema de los argumentos que completa el modelo, de una definicion. */
export function llmParameters(type: ToolType, d: Json): Json {
  if (type === 'code') {
    const params = obj(d.parameters);
    return { type: 'object', ...params, properties: obj(params.properties) };
  }
  const h = obj(d.http);
  const props: Json = {};
  const required: string[] = [];
  for (const [name, raw] of Object.entries(obj(h.path))) {
    const p = obj(raw);
    if (p.value == null) {
      props[name] = llmParam(p);
      required.push(name);
    }
  }
  for (const [name, raw] of Object.entries(obj(h.query))) {
    const p = obj(raw);
    if (p.value == null) {
      props[name] = llmParam(p);
      if (p.required === true) required.push(name);
    }
  }
  const body = obj(h.body);
  const bodyProps = Object.entries(obj(body.properties)).filter(([, v]) => !('value' in obj(v)));
  for (const [name, v] of bodyProps) props[name] = v;
  const bodyNames = new Set(bodyProps.map(([n]) => n));
  for (const r of Array.isArray(body.required) ? body.required : [])
    if (bodyNames.has(str(r))) required.push(str(r));
  return { type: 'object', properties: props, ...(required.length ? { required } : {}) };
}

/** Formato de function calling de OpenAI: lo que recibe el modelo. */
/** Notas que el servidor agrega a la descripcion (app/tools/schema.py, openai_tool). */
const CONFIRM_NOTE = 'Antes de usarla, confirmá con la persona lo que vas a hacer.';
const RESULT_NOTE = 'Devuelve {"ok": true, "data": ...} o {"ok": false, "error": ...}.';

export function llmTool(slug: string, type: ToolType, d: Json): Json {
  const description = [str(d.description).trim(), d.confirm === true ? CONFIRM_NOTE : '', RESULT_NOTE]
    .filter(Boolean)
    .join(' ');
  return {
    type: 'function',
    function: {
      name: slug || 'herramienta',
      description,
      parameters: llmParameters(type, d),
    },
  };
}

// ---------- secretos que pide (espejo de required_secrets) ----------

function secretsIn(text: unknown, out: Set<string>) {
  if (typeof text !== 'string') return;
  for (const m of text.matchAll(TEMPLATE_RE)) if (m[1] === 'secrets' && m[2]) out.add(m[2]);
}

/** Lo que hace falta de una credencial para saber sus secretos. */
export type CredentialRef = { slug: string; auth: Json };

/**
 * Los secretos que usa la herramienta (del cliente o del agente). Con una credencial, los de su auth
 * (credentials: las del cliente).
 */
export function requiredSecrets(type: ToolType, d: Json, credentials: CredentialRef[] = []): string[] {
  const out = new Set<string>();
  if (type === 'code') {
    for (const s of Array.isArray(d.secrets) ? d.secrets : []) out.add(str(s));
    return [...out].sort();
  }
  const h = obj(d.http);
  secretsIn(h.url, out);
  let auth = obj(h.auth);
  if (auth.type === 'credential') auth = obj(credentials.find((c) => c.slug === auth.credential)?.auth);
  if (auth.type && auth.type !== 'none' && typeof auth.secret === 'string' && auth.secret)
    out.add(auth.secret);
  secretsIn(auth.username, out);
  secretsIn(auth.client_id, out);
  for (const v of Object.values(obj(h.headers))) secretsIn(v, out);
  for (const p of [...Object.values(obj(h.path)), ...Object.values(obj(h.query))]) {
    const v = obj(p).value;
    for (const x of Array.isArray(v) ? v : [v]) secretsIn(x, out);
  }
  for (const p of Object.values(obj(obj(h.body).properties))) {
    const v = obj(p).value;
    for (const x of Array.isArray(v) ? v : [v]) secretsIn(x, out);
  }
  if (h.sign === true) out.add(SIGNING_SECRET);
  return [...out].sort();
}

// ---------- errores del servidor ----------

const WORDS: Record<string, string> = {
  definition: '',
  slug: 'Nombre',
  type: 'Tipo',
  description: 'Descripción',
  confirm: 'Pedir confirmación',
  messages: 'Voz',
  start: 'al empezar',
  delayed: 'si tarda',
  failed: 'si falla',
  after_ms: 'espera',
  text: 'frase',
  response: 'Respuesta',
  pick: 'campos',
  max_chars: 'largo máximo',
  assign: 'Guardar en variables',
  var: 'variable',
  http: '',
  method: 'Método',
  url: 'URL',
  path: 'Ruta',
  query: 'Query',
  headers: 'Headers',
  body: 'Body',
  content_type: 'formato del body',
  auth: 'Autenticación',
  secret: 'secreto',
  timeout_ms: 'tiempo máximo',
  retries: 'reintentos',
  sign: 'firma',
  parameters: 'Parámetros',
  code: 'Código',
  secrets: 'Secretos que usa',
  allowed_hosts: 'Hosts permitidos',
  properties: '',
  value: 'valor',
};

/** "definition.http.query.dni.description" -> "Query › dni › Descripción". */
export function toolPathLabel(path: string): string {
  const parts = path.split('.');
  return (
    parts
      .map((p, i) => {
        const prev = parts[i - 1];
        // Nombres propios (de un parametro o header): tal cual.
        if (
          prev &&
          ['path', 'query', 'headers', 'properties'].includes(prev) &&
          parts[i - 2] !== 'definition'
        )
          return p;
        if (prev === 'assign' && /^\d+$/.test(p)) return `fila ${Number(p) + 1}`;
        return WORDS[p] ?? p;
      })
      .filter(Boolean)
      .join(' › ') || 'Herramienta'
  );
}

/** Pestaña del editor HTTP donde va un error. */
export function errorTab(path: string, message = ''): string | null {
  const p = path.replace(/^definition\./, '');
  // Los errores de los validadores de http vienen en "definition.http" con la ruta en el mensaje.
  const where = p === 'http' ? (message.match(/^http\.(\w+)/)?.[1] ?? '') : (p.split('.')[1] ?? '');
  if (p.startsWith('messages')) return 'voz';
  if (p.startsWith('response') || p.startsWith('assign')) return 'respuesta';
  if (where === 'path') return 'ruta';
  if (where === 'query') return 'query';
  if (where === 'headers') return 'headers';
  if (where === 'body' || where === 'content_type') return 'body';
  if (where === 'auth') return 'auth';
  return null;
}
