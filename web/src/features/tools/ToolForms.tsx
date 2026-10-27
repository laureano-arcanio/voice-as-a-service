import { javascript } from '@codemirror/lang-javascript';
import {
  ActionIcon,
  Alert,
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
import type { ReactNode } from 'react';
import {
  AUTH_TYPES,
  type AuthType,
  type CodeDraft,
  DELAYED_MS,
  type HttpDraft,
  type HttpMethod,
  METHODS,
  newKey,
  SECRET_RE,
  SIGNING_SECRET,
  syncPathRows,
  type ToolDraft,
} from './draft';
import { ParamsEditor } from './ParamsEditor';
import { TemplateInput } from './TemplateInput';

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
      <Text size="xs" c="dimmed">
        Lo que dice el agente en una llamada mientras usa la herramienta. Vacío: no dice nada.
      </Text>
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

function HeadersEditor({
  http,
  setHttp,
  secrets,
}: {
  http: HttpDraft;
  setHttp: (patch: Partial<HttpDraft>) => void;
  secrets: string[];
}) {
  const rows = http.headers;
  return (
    <Stack gap="xs">
      {rows.length === 0 && (
        <Text size="sm" c="dimmed">
          Sin headers propios. La autenticación va en su pestaña.
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
            secrets={secrets}
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

function AuthEditor({
  http,
  setHttp,
  secrets,
}: {
  http: HttpDraft;
  setHttp: (patch: Partial<HttpDraft>) => void;
  secrets: string[];
}) {
  const auth = http.auth;
  const type = (auth.type as AuthType) || 'none';
  const v = (k: string) => (typeof auth[k] === 'string' ? (auth[k] as string) : '');
  const set = (k: string, value: string) => setHttp({ auth: { ...auth, [k]: value } });
  const secret = v('secret');
  return (
    <Stack gap="sm">
      <Select
        label="Tipo"
        data={AUTH_TYPES}
        value={type}
        allowDeselect={false}
        onChange={(t) => t && setHttp({ auth: { ...auth, type: t } })}
        maw={320}
      />
      {type !== 'none' && (
        <TextInput
          label={
            type === 'oauth2_client_credentials'
              ? 'Secreto con el client secret'
              : type === 'basic'
                ? 'Secreto con la clave'
                : 'Secreto con el token'
          }
          description="El nombre del secreto, no el valor: el valor se carga en cada agente (sección Herramientas, Secretos)."
          placeholder="CRM_TOKEN"
          classNames={{ input: 'mono' }}
          value={secret}
          onChange={(e) => set('secret', e.currentTarget.value.toUpperCase())}
          error={secret && !SECRET_RE.test(secret) ? 'Mayúsculas, números y _ (ej. CRM_TOKEN)' : undefined}
          maw={320}
        />
      )}
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
          secrets={secrets}
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
          <TemplateInput
            label="Client ID"
            value={v('client_id')}
            onChange={(x) => set('client_id', x)}
            secrets={secrets}
          />
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
      <Switch
        label="Firmar el pedido"
        description={`Header X-Atentina-Signature (HMAC-SHA256 del body) con el secreto ${SIGNING_SECRET} del agente, para que tu API verifique que viene de Atentina.`}
        checked={http.sign}
        onChange={(e) => setHttp({ sign: e.currentTarget.checked })}
      />
    </Stack>
  );
}

export function HttpForm({
  draft,
  update,
  secrets,
  tab,
  onTab,
  errorTabs,
}: {
  draft: ToolDraft;
  update: Update;
  secrets: string[];
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
          Pedido
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
              placeholder="https://api.ejemplo.com/turnos"
              style={{ flex: 1, minWidth: 0 }}
              value={http.url}
              onChange={(url) =>
                update((d) => ({ ...d, http: { ...d.http, url, path: syncPathRows(d.http.path, url) } }))
              }
              secrets={secrets}
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
              <TabLabel error={errorTabs.has('voz')}>Voz</TabLabel>
            </Tabs.Tab>
          </Tabs.List>
          <Tabs.Panel value="ruta">
            <ParamsEditor
              rows={http.path}
              onChange={(path) => setHttp({ path })}
              fixedNames
              showRequired={false}
              secrets={secrets}
              empty="La URL no tiene {variables} en la ruta. Agregalas en la URL (…/clientes/{dni}) y aparecen acá."
            />
          </Tabs.Panel>
          <Tabs.Panel value="query">
            <ParamsEditor
              rows={http.query}
              onChange={(query) => setHttp({ query })}
              secrets={secrets}
              empty="Sin parámetros de query (?fecha=…)."
            />
          </Tabs.Panel>
          <Tabs.Panel value="headers">
            <HeadersEditor http={http} setHttp={setHttp} secrets={secrets} />
          </Tabs.Panel>
          <Tabs.Panel value="body">
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
                  secrets={secrets}
                  label="Campo"
                  addLabel="Agregar campo"
                  empty="Sin campos. Los que completa el agente y los fijos van juntos en el JSON."
                />
              )}
            </Stack>
          </Tabs.Panel>
          <Tabs.Panel value="auth">
            <AuthEditor http={http} setHttp={setHttp} secrets={secrets} />
          </Tabs.Panel>
          <Tabs.Panel value="respuesta">
            <ResponseFields draft={draft} update={update} />
          </Tabs.Panel>
          <Tabs.Panel value="voz">
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
            description="Nombres en mayúsculas (CRM_TOKEN). Llegan en secrets; el valor se carga en cada agente."
            placeholder="Enter para agregar"
            classNames={{ input: 'mono' }}
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
        <ResponseFields draft={draft} update={update} />
      </Card>
      <Card>
        <Title order={4} mb="sm">
          Voz
        </Title>
        <VoiceFields draft={draft} update={update} />
      </Card>
    </Stack>
  );
}
