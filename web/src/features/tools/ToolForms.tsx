import { javascript } from '@codemirror/lang-javascript';
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  NumberInput,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Tabs,
  TagsInput,
  Text,
  Textarea,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import CodeMirror from '@uiw/react-codemirror';
import { type ReactNode, useContext, useState } from 'react';
import type { Credential } from '@/api/types';
import { useCredentials } from './api';
import { CredentialModal } from './CredentialModal';
import { CREDENTIAL_TYPE_LABEL, CREDENTIAL_VALUE } from './credentials';
import {
  AUTH_TYPES,
  type AuthType,
  type CodeDraft,
  type CredentialType,
  DELAYED_MS,
  type HttpDraft,
  type HttpMethod,
  type Json,
  METHODS,
  newKey,
  SECRET_RE,
  SIGNING_SECRET,
  syncPathRows,
  type ToolDraft,
} from './draft';
import { ParamsEditor } from './ParamsEditor';
import { SecretInput, TemplateInput } from './TemplateInput';
import { ToolSecretsContext } from './ToolSecretsContext';

type Update = (fn: (d: ToolDraft) => ToolDraft) => void;

const jsExtensions = [javascript({ typescript: true })];

/** Una pestana con errores lleva un punto rojo. */
function TabLabel({ children, error }: { children: ReactNode; error?: boolean }) {
  return (
    <Group gap={6} wrap="nowrap" component="span">
      {children}
      {error && (
        <Text span c="red.6" fw={700} aria-label="con errores">
          •
        </Text>
      )}
    </Group>
  );
}

/** Descripcion para el modelo y el pedido de confirmacion: lo comun a los dos tipos. */
export function HeaderFields({ draft, update }: { draft: ToolDraft; update: Update }) {
  return (
    <Stack gap="sm">
      <Textarea
        label="Qué hace y cuándo usarla"
        description="Es lo que lee el agente para decidir si la llama. Decí qué devuelve y en qué situaciones usarla."
        placeholder="Busca los turnos libres de un día. Usala cuando la persona pide un turno."
        autosize
        minRows={2}
        maxRows={6}
        maxLength={1000}
        value={draft.description}
        onChange={(e) => {
          const description = e.currentTarget.value;
          update((d) => ({ ...d, description }));
        }}
      />
      <Switch
        label="Pedir confirmación antes (se le indica al agente)"
        description="Se agrega a la descripción que le pida el sí a la persona antes de usarla; lo decide el agente. Para las que cambian algo (reservar, cancelar, pagar)."
        checked={draft.confirm}
        onChange={(e) => {
          const confirm = e.currentTarget.checked;
          update((d) => ({ ...d, confirm }));
        }}
      />
    </Stack>
  );
}

/** Parrafo corto al principio de cada seccion: que es y como se usa. */
function SectionIntro({ children }: { children: ReactNode }) {
  return (
    <Text size="xs" c="dimmed" mb="sm">
      {children}
    </Text>
  );
}

function ResponseFields({ draft, update }: { draft: ToolDraft; update: Update }) {
  return (
    <Stack gap="sm">
      <TagsInput
        label="Campos que recibe el agente"
        description="Rutas del resultado, con puntos y [i] (data.items[0].nombre). Vacío: todo el resultado. Menos datos, respuestas más rápidas y precisas."
        placeholder="Enter para agregar"
        value={draft.pick}
        onChange={(pick) => update((d) => ({ ...d, pick }))}
        classNames={{ input: 'mono' }}
      />
      <NumberInput
        label="Largo máximo del resultado"
        description="En caracteres: lo que pase se corta."
        min={200}
        max={15000}
        step={500}
        allowDecimal={false}
        thousandSeparator="."
        decimalSeparator=","
        value={draft.maxChars}
        onChange={(v) => typeof v === 'number' && update((d) => ({ ...d, maxChars: v }))}
        maw={240}
      />
      <div>
        <Text size="sm" fw={600}>
          Guardar en variables
        </Text>
        <Text size="xs" c="dimmed" mb="xs">
          Un valor del resultado que otras herramientas usan como {'{{vars.nombre}}'}. Oculto: no lo ve el
          agente.
        </Text>
        <Stack gap="xs">
          {draft.assign.map((a, i) => (
            <Group key={a.key} gap="xs" wrap="wrap">
              <TextInput
                aria-label={`Variable ${i + 1}`}
                placeholder="cliente_id"
                classNames={{ input: 'mono' }}
                value={a.var}
                onChange={(e) => {
                  const v = e.currentTarget.value;
                  update((d) => ({
                    ...d,
                    assign: d.assign.map((x) => (x.key === a.key ? { ...x, var: v } : x)),
                  }));
                }}
                w={170}
              />
              <TextInput
                aria-label={`Ruta de la variable ${i + 1}`}
                placeholder="data.cliente.id"
                classNames={{ input: 'mono' }}
                value={a.path}
                onChange={(e) => {
                  const path = e.currentTarget.value;
                  update((d) => ({
                    ...d,
                    assign: d.assign.map((x) => (x.key === a.key ? { ...x, path } : x)),
                  }));
                }}
                style={{ flex: 1, minWidth: 180 }}
              />
              <Checkbox
                label="Oculto"
                checked={a.hide}
                onChange={(e) => {
                  const hide = e.currentTarget.checked;
                  update((d) => ({
                    ...d,
                    assign: d.assign.map((x) => (x.key === a.key ? { ...x, hide } : x)),
                  }));
                }}
              />
              <Tooltip label="Quitar" withArrow>
                <ActionIcon
                  variant="subtle"
                  color="red"
                  aria-label={`Quitar la variable ${i + 1}`}
                  onClick={() => update((d) => ({ ...d, assign: d.assign.filter((x) => x.key !== a.key) }))}
                >
                  <IconTrash size={16} />
                </ActionIcon>
              </Tooltip>
            </Group>
          ))}
          <Button
            variant="default"
            size="xs"
            leftSection={<IconPlus size={16} />}
            style={{ alignSelf: 'flex-start' }}
            onClick={() =>
              update((d) => ({
                ...d,
                assign: [...d.assign, { key: newKey(), var: '', path: '', hide: false }],
              }))
            }
          >
            Agregar variable
          </Button>
        </Stack>
      </div>
    </Stack>
  );
}

function VoiceFields({ draft, update }: { draft: ToolDraft; update: Update }) {
  return (
    <Stack gap="sm">
      <TextInput
        label="Al empezar"
        placeholder="Dame un segundo que lo busco."
        maxLength={200}
        value={draft.start}
        onChange={(e) => {
          const start = e.currentTarget.value;
          update((d) => ({ ...d, start }));
        }}
      />
      <Group gap="xs" align="flex-end" wrap="wrap">
        <TextInput
          label="Si tarda"
          placeholder="Sigo buscando, ya casi."
          maxLength={200}
          style={{ flex: 1, minWidth: 220 }}
          value={draft.delayed?.text ?? ''}
          onChange={(e) => {
            const text = e.currentTarget.value;
            update((d) => ({ ...d, delayed: { afterMs: d.delayed?.afterMs ?? DELAYED_MS, text } }));
          }}
        />
        <NumberInput
          label="Después de (ms)"
          min={500}
          max={30000}
          step={500}
          allowDecimal={false}
          w={150}
          value={draft.delayed?.afterMs ?? DELAYED_MS}
          onChange={(v) =>
            typeof v === 'number' &&
            update((d) => ({ ...d, delayed: { text: d.delayed?.text ?? '', afterMs: v } }))
          }
        />
      </Group>
      <TextInput
        label="Si falla"
        placeholder="No pude consultarlo ahora. ¿Querés que te llamen?"
        maxLength={200}
        value={draft.failed}
        onChange={(e) => {
          const failed = e.currentTarget.value;
          update((d) => ({ ...d, failed }));
        }}
      />
    </Stack>
  );
}

function HeadersEditor({ http, setHttp }: { http: HttpDraft; setHttp: (patch: Partial<HttpDraft>) => void }) {
  const rows = http.headers;
  return (
    <Stack gap="xs">
      {rows.length === 0 && (
        <Text size="sm" c="dimmed">
          Sin headers propios. El token de acceso va en Autenticación.
        </Text>
      )}
      {rows.map((r, i) => (
        <Group key={r.key} gap="xs" align="flex-start" wrap="wrap">
          <TextInput
            aria-label={`Nombre del header ${i + 1}`}
            placeholder="X-Sucursal"
            classNames={{ input: 'mono' }}
            value={r.name}
            onChange={(e) => {
              const name = e.currentTarget.value;
              setHttp({ headers: rows.map((x) => (x.key === r.key ? { ...x, name } : x)) });
            }}
            w={{ base: '100%', xs: 200 }}
          />
          <TemplateInput
            aria-label={`Valor del header ${i + 1}`}
            placeholder="centro"
            style={{ flex: 1, minWidth: 220 }}
            value={r.value}
            onChange={(value) =>
              setHttp({ headers: rows.map((x) => (x.key === r.key ? { ...x, value } : x)) })
            }
          />
          <Tooltip label="Quitar" withArrow>
            <ActionIcon
              variant="subtle"
              color="red"
              mt={4}
              aria-label={`Quitar el header ${i + 1}`}
              onClick={() => setHttp({ headers: rows.filter((x) => x.key !== r.key) })}
            >
              <IconTrash size={16} />
            </ActionIcon>
          </Tooltip>
        </Group>
      ))}
      <Button
        variant="default"
        size="xs"
        leftSection={<IconPlus size={16} />}
        style={{ alignSelf: 'flex-start' }}
        onClick={() => setHttp({ headers: [...rows, { key: newKey(), name: '', value: '' }] })}
      >
        Agregar header
      </Button>
    </Stack>
  );
}

/** La autenticacion configurada en la herramienta (sin credencial): la de las herramientas hechas por API. */
function InlineAuth({ auth, set }: { auth: Json; set: (k: string, value: string) => void }) {
  const type = (auth.type as CredentialType) || 'bearer';
  const v = (k: string) => (typeof auth[k] === 'string' ? (auth[k] as string) : '');
  return (
    <Stack gap="sm">
      <Select
        label="Tipo"
        data={AUTH_TYPES}
        value={type}
        allowDeselect={false}
        onChange={(t) => t && set('type', t)}
        maw={320}
      />
      <SecretInput
        label={`Secreto con ${CREDENTIAL_VALUE[type].label.toLowerCase()}`}
        description="El nombre del secreto, no el valor: el valor se carga en Secretos."
        placeholder="CRM_TOKEN"
        value={v('secret')}
        onChange={(x) => set('secret', x)}
        maw={420}
      />
      {type === 'bearer' && (
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          <TextInput
            label="Header"
            placeholder="Authorization"
            value={v('header')}
            onChange={(e) => set('header', e.currentTarget.value)}
          />
          <TextInput
            label="Prefijo"
            placeholder="Bearer "
            value={v('prefix')}
            onChange={(e) => set('prefix', e.currentTarget.value)}
          />
        </SimpleGrid>
      )}
      {type === 'api_key' && (
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          <TextInput
            label="Nombre"
            description="Del header o del parámetro."
            placeholder="X-API-Key"
            value={v('name')}
            onChange={(e) => set('name', e.currentTarget.value)}
          />
          <Select
            label="Va en"
            description="Dónde se manda la key."
            data={[
              { value: 'header', label: 'Un header' },
              { value: 'query', label: 'La query' },
            ]}
            value={v('in') || 'header'}
            allowDeselect={false}
            onChange={(x) => x && set('in', x)}
          />
        </SimpleGrid>
      )}
      {type === 'basic' && (
        <TemplateInput
          label="Usuario"
          placeholder="atentina"
          value={v('username')}
          onChange={(x) => set('username', x)}
          maw={320}
        />
      )}
      {type === 'oauth2_client_credentials' && (
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          <TextInput
            label="URL del token"
            placeholder="https://auth.ejemplo.com/oauth/token"
            value={v('token_url')}
            onChange={(e) => set('token_url', e.currentTarget.value)}
          />
          <TemplateInput label="Client ID" value={v('client_id')} onChange={(x) => set('client_id', x)} />
          <TextInput label="Scope" value={v('scope')} onChange={(e) => set('scope', e.currentTarget.value)} />
          <TextInput
            label="Audience"
            value={v('audience')}
            onChange={(e) => set('audience', e.currentTarget.value)}
          />
          <Select
            label="Cómo se manda el client secret"
            data={[
              { value: 'body', label: 'En el body' },
              { value: 'basic', label: 'Con Basic' },
            ]}
            value={v('client_auth') || 'body'}
            allowDeselect={false}
            onChange={(x) => x && set('client_auth', x)}
          />
        </SimpleGrid>
      )}
    </Stack>
  );
}

const INLINE = '__inline';

function AuthEditor({
  http,
  setHttp,
  clientId,
}: {
  http: HttpDraft;
  setHttp: (patch: Partial<HttpDraft>) => void;
  clientId: string;
}) {
  const credentials = useCredentials(clientId);
  const [modal, setModal] = useState<{ edit?: Credential } | null>(null);
  const auth = http.auth;
  const type = (auth.type as AuthType) || 'none';
  const list = credentials.data ?? [];
  const chosen = type === 'credential' ? list.find((c) => c.slug === auth.credential) : undefined;
  const value = type === 'none' ? 'none' : type === 'credential' ? `c:${String(auth.credential)}` : INLINE;
  const data = [
    { value: 'none', label: 'Sin autenticación' },
    ...list.map((c) => ({
      value: `c:${c.slug}`,
      label: `${c.name} · ${CREDENTIAL_TYPE_LABEL[c.type] ?? c.type}`,
    })),
    ...(type === 'credential' && !chosen && !credentials.isLoading
      ? [{ value, label: `${String(auth.credential)} (no existe)` }]
      : []),
    { value: INLINE, label: 'Configurada en esta herramienta (avanzado)' },
  ];
  const choose = (x: string | null) => {
    if (!x) return;
    if (x === 'none') setHttp({ auth: { type: 'none' } });
    else if (x === INLINE) setHttp({ auth: { type: 'bearer' } });
    else setHttp({ auth: { type: 'credential', credential: x.slice(2) } });
  };

  return (
    <Stack gap="sm">
      <Group gap="xs" align="flex-end" wrap="wrap">
        <Select
          label="Credencial"
          description="La forma de entrar a tu API, guardada una vez y usada por todas las herramientas que la llaman."
          data={data}
          value={value}
          allowDeselect={false}
          onChange={choose}
          style={{ flex: 1, minWidth: 260, maxWidth: 480 }}
        />
        <Button variant="light" leftSection={<IconPlus size={16} />} onClick={() => setModal({})}>
          Nueva credencial
        </Button>
      </Group>
      {type === 'credential' && chosen && (
        <div className="def-item" style={{ padding: 'var(--mantine-spacing-sm)' }}>
          <Group justify="space-between" gap="sm" wrap="wrap">
            <Stack gap={2}>
              <Group gap={6}>
                <Text size="sm" fw={600}>
                  {chosen.name}
                </Text>
                <Badge color="gray">{CREDENTIAL_TYPE_LABEL[chosen.type] ?? chosen.type}</Badge>
                {chosen.secret_set ? (
                  <Badge color="green">Valor cargado</Badge>
                ) : (
                  <Badge color="yellow">Falta el valor</Badge>
                )}
              </Group>
              <Text size="xs" c="dimmed">
                {credentialSummary(chosen)} El valor está en el secreto{' '}
                <span className="mono">{chosen.secret}</span>.
              </Text>
            </Stack>
            <Button size="compact-sm" variant="subtle" onClick={() => setModal({ edit: chosen })}>
              Editar credencial
            </Button>
          </Group>
        </div>
      )}
      {type === 'credential' && !chosen && !credentials.isLoading && (
        <Alert color="yellow">La credencial {String(auth.credential)} no existe. Elegí otra o creala.</Alert>
      )}
      {value === INLINE && <InlineAuth auth={auth} set={(k, x) => setHttp({ auth: { ...auth, [k]: x } })} />}
      <Switch
        label="Firmar el pedido"
        description={`Header X-Atentina-Signature (HMAC-SHA256 del body) con el secreto ${SIGNING_SECRET}, para que tu API verifique que viene de Atentina.`}
        checked={http.sign}
        onChange={(e) => setHttp({ sign: e.currentTarget.checked })}
      />
      {modal && (
        <CredentialModal
          clientId={clientId}
          credential={modal.edit}
          onClose={() => setModal(null)}
          onSaved={(slug) => setHttp({ auth: { type: 'credential', credential: slug } })}
        />
      )}
    </Stack>
  );
}

/** "Header Authorization: Bearer …" o "Header X-API-Key", para reconocer la credencial. */
function credentialSummary(c: Credential): string {
  const a = c.auth;
  const s = (k: string) => (typeof a[k] === 'string' ? (a[k] as string) : '');
  if (c.type === 'bearer') return `Header ${s('header') || 'Authorization'}: ${s('prefix') || 'Bearer '}…`;
  if (c.type === 'api_key') return `${s('in') === 'query' ? 'Parámetro' : 'Header'} ${s('name')}.`;
  if (c.type === 'basic') return `Usuario ${s('username')}.`;
  return `Token de ${s('token_url')}.`;
}

export function HttpForm({
  draft,
  update,
  clientId,
  tab,
  onTab,
  errorTabs,
}: {
  draft: ToolDraft;
  update: Update;
  clientId: string;
  tab: string;
  onTab: (t: string) => void;
  errorTabs: Set<string>;
}) {
  const http = draft.http;
  const setHttp = (patch: Partial<HttpDraft>) => update((d) => ({ ...d, http: { ...d.http, ...patch } }));
  const noBody = http.method === 'GET' || http.method === 'DELETE';

  return (
    <Stack gap="md">
      <Card>
        <Title order={4} mb="sm">
          Request
        </Title>
        <Stack gap="sm">
          <HeaderFields draft={draft} update={update} />
          <Group gap="xs" align="flex-start" wrap="nowrap">
            <Select
              label="Método"
              data={METHODS}
              value={http.method}
              allowDeselect={false}
              onChange={(m) => m && setHttp({ method: m as HttpMethod })}
              w={110}
              style={{ flex: 'none' }}
            />
            <TemplateInput
              label="URL"
              description="Con {variables} en la ruta para los parámetros (https://api.ejemplo.com/clientes/{dni})."
              inputWrapperOrder={['label', 'input', 'description', 'error']}
              placeholder="https://api.ejemplo.com/turnos"
              style={{ flex: 1, minWidth: 0 }}
              value={http.url}
              onChange={(url) =>
                update((d) => ({ ...d, http: { ...d.http, url, path: syncPathRows(d.http.path, url) } }))
              }
            />
          </Group>
          <SimpleGrid cols={{ base: 2, sm: 3 }}>
            <NumberInput
              label="Tiempo máximo (ms)"
              min={500}
              max={30000}
              step={500}
              allowDecimal={false}
              value={http.timeoutMs}
              onChange={(v) => typeof v === 'number' && setHttp({ timeoutMs: v })}
            />
            <NumberInput
              label="Reintentos"
              description="Si falla la conexión o da 5xx."
              inputWrapperOrder={['label', 'input', 'description', 'error']}
              min={0}
              max={2}
              allowDecimal={false}
              value={http.retries}
              onChange={(v) => typeof v === 'number' && setHttp({ retries: v })}
            />
          </SimpleGrid>
        </Stack>
      </Card>

      <Card>
        <Tabs value={tab} onChange={(t) => t && onTab(t)} keepMounted={false}>
          <Tabs.List mb="md">
            <Tabs.Tab value="ruta">
              <TabLabel error={errorTabs.has('ruta')}>Ruta</TabLabel>
            </Tabs.Tab>
            <Tabs.Tab value="query">
              <TabLabel error={errorTabs.has('query')}>Query</TabLabel>
            </Tabs.Tab>
            <Tabs.Tab value="headers">
              <TabLabel error={errorTabs.has('headers')}>Headers</TabLabel>
            </Tabs.Tab>
            <Tabs.Tab value="body" disabled={noBody}>
              <TabLabel error={errorTabs.has('body')}>Body</TabLabel>
            </Tabs.Tab>
            <Tabs.Tab value="auth">
              <TabLabel error={errorTabs.has('auth')}>Autenticación</TabLabel>
            </Tabs.Tab>
            <Tabs.Tab value="respuesta">
              <TabLabel error={errorTabs.has('respuesta')}>Respuesta</TabLabel>
            </Tabs.Tab>
            <Tabs.Tab value="voz">
              <TabLabel error={errorTabs.has('voz')}>Mientras se espera</TabLabel>
            </Tabs.Tab>
          </Tabs.List>
          <Tabs.Panel value="ruta">
            <SectionIntro>
              {
                'Las partes de la URL entre llaves, como {dni} en …/clientes/{dni}. Elegí si cada una la completa el agente con lo que dijo la persona o lleva un valor fijo.'
              }
            </SectionIntro>
            <ParamsEditor
              rows={http.path}
              onChange={(path) => setHttp({ path })}
              fixedNames
              showRequired={false}
              empty="La URL no tiene {variables} en la ruta. Agregalas en la URL (…/clientes/{dni}) y aparecen acá."
            />
          </Tabs.Panel>
          <Tabs.Panel value="query">
            <SectionIntro>
              Los parámetros que van después del ? en la URL (?fecha=2026-10-27). Cada uno lo completa el
              agente o lleva un valor fijo, que puede tener variables.
            </SectionIntro>
            <ParamsEditor
              rows={http.query}
              onChange={(query) => setHttp({ query })}
              empty="Sin parámetros de query (?fecha=…)."
            />
          </Tabs.Panel>
          <Tabs.Panel value="headers">
            <SectionIntro>
              Encabezados extra del pedido, como X-Sucursal. El valor puede llevar variables o secretos; el
              token de acceso va en Autenticación.
            </SectionIntro>
            <HeadersEditor http={http} setHttp={setHttp} />
          </Tabs.Panel>
          <Tabs.Panel value="body">
            <SectionIntro>
              Los datos que se mandan en un POST, PUT o PATCH, en JSON o como formulario. Cada campo lo
              completa el agente o lleva un valor fijo.
            </SectionIntro>
            <Stack gap="sm">
              <Group gap="sm" wrap="wrap">
                <Switch
                  label="Manda un body"
                  checked={http.body !== null}
                  onChange={(e) => setHttp({ body: e.currentTarget.checked ? (http.body ?? []) : null })}
                />
                {http.body !== null && (
                  <SegmentedControl
                    size="xs"
                    aria-label="Formato del body"
                    value={http.contentType}
                    onChange={(v) => setHttp({ contentType: v as HttpDraft['contentType'] })}
                    data={[
                      { value: 'application/json', label: 'JSON' },
                      { value: 'application/x-www-form-urlencoded', label: 'Formulario' },
                    ]}
                  />
                )}
              </Group>
              {http.body !== null && (
                <ParamsEditor
                  rows={http.body}
                  onChange={(body) => setHttp({ body })}
                  label="Campo"
                  addLabel="Agregar campo"
                  empty="Sin campos. Los que completa el agente y los fijos van juntos en el JSON."
                />
              )}
            </Stack>
          </Tabs.Panel>
          <Tabs.Panel value="auth">
            <SectionIntro>
              Cómo se identifica Atentina ante tu API. Elegí una credencial (o creá una acá): se carga una
              vez, la usan todas las herramientas que llaman a esa API y el agente nunca ve el valor.
            </SectionIntro>
            <AuthEditor http={http} setHttp={setHttp} clientId={clientId} />
          </Tabs.Panel>
          <Tabs.Panel value="respuesta">
            <SectionIntro>
              Qué parte del resultado lee el agente y qué valores se guardan para usar en otras herramientas.
            </SectionIntro>
            <ResponseFields draft={draft} update={update} />
          </Tabs.Panel>
          <Tabs.Panel value="voz">
            <SectionIntro>
              Lo que dice el agente en una llamada mientras espera la respuesta, para que no haya silencio.
              Vacío: no dice nada.
            </SectionIntro>
            <VoiceFields draft={draft} update={update} />
          </Tabs.Panel>
        </Tabs>
      </Card>
    </Stack>
  );
}

export function CodeForm({
  draft,
  update,
  runnerDown,
}: {
  draft: ToolDraft;
  update: Update;
  /** El servidor no tiene el sandbox configurado: se puede guardar pero no probar ni usar. */
  runnerDown: boolean;
}) {
  const code = draft.code;
  const setCode = (patch: Partial<CodeDraft>) => update((d) => ({ ...d, code: { ...d.code, ...patch } }));
  const badSecrets = code.secrets.filter((s) => !SECRET_RE.test(s));
  const secretNames = useContext(ToolSecretsContext).names;
  return (
    <Stack gap="md">
      {runnerDown && (
        <Alert color="yellow" title="El sandbox de código no está disponible">
          Podés guardarla, pero no se va a poder probar ni usar en las conversaciones hasta que esté prendido.
        </Alert>
      )}
      <Card>
        <Title order={4} mb="sm">
          Herramienta
        </Title>
        <HeaderFields draft={draft} update={update} />
      </Card>
      <Card>
        <Title order={4} mb={4}>
          Código
        </Title>
        <Text size="xs" c="dimmed" mb="sm">
          JavaScript o TypeScript con un <span className="mono">export default async function</span>. Recibe{' '}
          <span className="mono">args</span>, <span className="mono">secrets</span>,{' '}
          <span className="mono">call</span> y <span className="mono">vars</span>; lo que devuelve es lo que
          lee el agente. <span className="mono">console.log</span> va a la prueba y a la traza.
        </Text>
        <div className="cm-editor-wrap">
          <CodeMirror
            value={code.code}
            onChange={(v) => setCode({ code: v })}
            height="420px"
            theme="light"
            extensions={jsExtensions}
            basicSetup={{ foldGutter: true, autocompletion: true }}
            aria-label="Código de la herramienta"
          />
        </div>
      </Card>
      <Card>
        <Title order={4} mb={4}>
          Parámetros
        </Title>
        <Text size="xs" c="dimmed" mb="sm">
          Lo que completa el agente: llega en <span className="mono">args</span>, ya validado.
        </Text>
        <ParamsEditor
          rows={code.parameters}
          onChange={(parameters) => setCode({ parameters })}
          allowFixed={false}
          empty="Sin parámetros: el agente la llama sin datos."
        />
      </Card>
      <Card>
        <Title order={4} mb="sm">
          Acceso
        </Title>
        <Stack gap="sm">
          <TagsInput
            label="Secretos que usa"
            description="Elegí de los que cargaste o escribí uno nuevo (CRM_TOKEN). Llegan en secrets; el valor se carga en Secretos."
            placeholder="Enter para agregar"
            classNames={{ input: 'mono' }}
            data={secretNames}
            value={code.secrets}
            onChange={(v) => setCode({ secrets: v.map((s) => s.trim().toUpperCase()) })}
            error={badSecrets.length ? `Mayúsculas, números y _: ${badSecrets.join(', ')}` : undefined}
          />
          <TagsInput
            label="Hosts permitidos"
            description="Los dominios a los que puede llamar con fetch (api.ejemplo.com). Sin ninguno, no sale a internet."
            placeholder="Enter para agregar"
            classNames={{ input: 'mono' }}
            value={code.allowedHosts}
            onChange={(v) => setCode({ allowedHosts: v.map((s) => s.trim().toLowerCase()) })}
          />
          <NumberInput
            label="Tiempo máximo (ms)"
            min={500}
            max={30000}
            step={500}
            allowDecimal={false}
            value={code.timeoutMs}
            onChange={(v) => typeof v === 'number' && setCode({ timeoutMs: v })}
            maw={200}
          />
        </Stack>
      </Card>
      <Card>
        <Title order={4} mb="sm">
          Respuesta
        </Title>
        <SectionIntro>
          Qué parte del resultado lee el agente y qué valores se guardan para usar en otras herramientas.
        </SectionIntro>
        <ResponseFields draft={draft} update={update} />
      </Card>
      <Card>
        <Title order={4} mb="sm">
          Mientras se espera
        </Title>
        <SectionIntro>
          Lo que dice el agente en una llamada mientras espera la respuesta, para que no haya silencio. Vacío:
          no dice nada.
        </SectionIntro>
        <VoiceFields draft={draft} update={update} />
      </Card>
    </Stack>
  );
}
