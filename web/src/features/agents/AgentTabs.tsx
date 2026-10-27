import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  List,
  Modal,
  SegmentedControl,
  Stack,
  Tabs,
  Text,
  Title,
} from '@mantine/core';
import { useDebouncedValue, useDisclosure, useWindowEvent } from '@mantine/hooks';
import {
  IconAlertCircle,
  IconCpu,
  IconDeviceFloppy,
  IconFileCode,
  IconFileText,
  IconHistory,
  IconInfoCircle,
  IconLink,
  IconListDetails,
  IconMessage,
  IconMicrophone,
  IconPlayerPlay,
  IconTool,
} from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';
import type { ReactCodeMirrorRef } from '@uiw/react-codemirror';
import type { ComponentType } from 'react';
import { useRef, useState } from 'react';
import { useBlocker, useSearchParams } from 'react-router';
import { ApiError, errorMessage, type FieldError } from '@/api/errors';
import type { AgentDetail, Definition } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { JsonEditor } from '@/components/JsonEditor';
import { QueryState } from '@/components/QueryState';
import { focusOffset } from '@/lib/editor';
import { notifyError, notifySuccess } from '@/lib/notify';
import { usePromptPreview, useSaveDefinition, validateDefinition } from './api';
import { AgentTestPanel } from './AgentTestPanel';
import { CallLinkTab } from './CallLinkTab';
import { findPathOffset, parseDefinition, toJsonText } from './definition';
import { DefinitionForm } from './DefinitionForm';
import {
  type Draft,
  errorTarget,
  fromDraft,
  type Part,
  PARTS,
  pathLabel,
  SECTION_PART,
  sectionId,
  stableJson,
  toDraft,
} from './draft';
import { VersionsTab } from './VersionsTab';
import { WorkflowSummary } from './WorkflowSummary';

/** Las pestañas del agente. Las de edicion (PARTS y json) comparten un borrador y una barra de guardado. */
type Tab = 'resumen' | Part | 'json' | 'versiones' | 'probar' | 'link';
const TABS: Tab[] = ['resumen', ...PARTS, 'json', 'versiones', 'probar', 'link'];
const TAB_META: Record<Tab, { label: string; icon: ComponentType<{ size?: number }> }> = {
  resumen: { label: 'Resumen', icon: IconInfoCircle },
  conversacion: { label: 'Conversación', icon: IconMessage },
  datos: { label: 'Datos', icon: IconListDetails },
  herramientas: { label: 'Herramientas', icon: IconTool },
  voz: { label: 'Voz y canales', icon: IconMicrophone },
  modelo: { label: 'Modelo', icon: IconCpu },
  json: { label: 'JSON', icon: IconFileCode },
  versiones: { label: 'Versiones', icon: IconHistory },
  probar: { label: 'Probar', icon: IconPlayerPlay },
  link: { label: 'Link para llamar', icon: IconLink },
};
const isPart = (t: Tab): t is Part => (PARTS as string[]).includes(t);
const isEditing = (t: Tab) => isPart(t) || t === 'json';

/** `?tab=`: `definicion` (la pestaña única de antes) abre Conversación. */
function tabFromParams(params: URLSearchParams): Tab {
  const raw = params.get('tab') ?? 'resumen';
  const t = (raw === 'definicion' ? 'conversacion' : raw) as Tab;
  return TABS.includes(t) ? t : 'resumen';
}

/** La definicion como la deja el formulario: para comparar sin importar el formato. */
const canonical = (d: Definition) => stableJson(fromDraft(toDraft(d)));

function toFieldErrors(errors: Record<string, unknown>[] | undefined): FieldError[] {
  return (errors ?? []).map((e) => ({ path: String(e.path ?? ''), message: String(e.message ?? '') }));
}

function ErrorList({
  errors,
  label,
  onPick,
}: {
  errors: FieldError[];
  label: (path: string) => string;
  onPick: (path: string) => void;
}) {
  return (
    <List size="sm" spacing={4}>
      {errors.map((e, i) => (
        <List.Item key={i}>
          {e.path ? (
            <Anchor component="button" type="button" size="sm" onClick={() => onPick(e.path)}>
              {label(e.path)}
            </Anchor>
          ) : null}
          {e.path ? ': ' : ''}
          {e.message}
        </List.Item>
      ))}
    </List>
  );
}

/** Aviso al salir con cambios sin guardar (navegacion interna y cierre de pestaña). */
function UnsavedGuard({ dirty }: { dirty: boolean }) {
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) => dirty && currentLocation.pathname !== nextLocation.pathname,
  );
  useWindowEvent('beforeunload', (e) => {
    if (dirty) e.preventDefault();
  });
  return (
    <Modal opened={blocker.state === 'blocked'} onClose={() => blocker.reset?.()} title="Cambios sin guardar">
      <Text size="sm">La definición tiene cambios sin guardar. Si salís, se pierden.</Text>
      <Group justify="flex-end" mt="md">
        <Button variant="default" onClick={() => blocker.reset?.()}>
          Seguir editando
        </Button>
        <Button color="red" onClick={() => blocker.proceed?.()}>
          Salir sin guardar
        </Button>
      </Group>
    </Modal>
  );
}

/** El prompt que arma la plataforma con la definicion en edicion (sin guardarla). */
function PromptModal({
  definition,
  opened,
  onClose,
}: {
  definition: Definition | null;
  opened: boolean;
  onClose: () => void;
}) {
  const [channel, setChannel] = useState<'voice' | 'whatsapp'>('voice');
  const query = usePromptPreview(definition ?? {}, channel, opened && definition !== null);
  return (
    <Modal opened={opened} onClose={onClose} title="Prompt generado" size="xl">
      <Stack gap="sm">
        <Text size="sm" c="dimmed">
          Se arma de la definición, con los cambios sin guardar: no hay un prompt aparte para editar.
        </Text>
        <SegmentedControl
          w="fit-content"
          data={[
            { value: 'voice', label: 'Llamada' },
            { value: 'whatsapp', label: 'WhatsApp' },
          ]}
          value={channel}
          onChange={(v) => setChannel(v as 'voice' | 'whatsapp')}
        />
        {definition === null ? (
          <Alert color="red" icon={<IconAlertCircle size={18} />}>
            El JSON no es válido: corregilo para ver el prompt.
          </Alert>
        ) : (
          <QueryState query={query}>
            {(p) => (
              <Stack gap="sm">
                <Text size="sm" fw={600}>
                  Prompt de sistema{' '}
                  {definition?.external ? (
                    <Text span size="xs" c="dimmed" fw={400}>
                      · tu propio agente: el prompt de sistema opcional que va antes de la conversación
                    </Text>
                  ) : null}
                </Text>
                <pre className="code">{p.system}</pre>
              </Stack>
            )}
          </QueryState>
        )}
      </Stack>
    </Modal>
  );
}

export function AgentTabs({ agent }: { agent: AgentDetail }) {
  const [params, setParams] = useSearchParams();
  const tab = tabFromParams(params);
  const mode = tab === 'json' ? 'json' : 'form';
  const baseline = canonical(agent.definition);
  const [base, setBase] = useState(baseline);
  const [draft, setDraft] = useState<Draft>(() => toDraft(agent.definition));
  const [jsonText, setJsonText] = useState(() => toJsonText(agent.definition));
  const [opened, setOpened] = useState<Set<string>>(() => new Set());
  const [promptOpen, prompt] = useDisclosure(false);
  const editorRef = useRef<ReactCodeMirrorRef>(null);
  const save = useSaveDefinition(agent.id);

  // La definicion en edicion: la del formulario o la del JSON (null si no parsea).
  const parsedJson = mode === 'json' ? parseDefinition(jsonText) : null;
  const current: Definition | null =
    mode === 'form' ? fromDraft(draft) : parsedJson?.ok ? parsedJson.value : null;
  const currentKey = current ? canonical(current) : `json:${jsonText}`;
  const dirty = currentKey !== base;

  // Llego una version nueva (guardado, restauracion u otra sesion): si no hay cambios, se muestra.
  if (baseline !== base) {
    setBase(baseline);
    if (!dirty) {
      setDraft(toDraft(agent.definition));
      setJsonText(toJsonText(agent.definition));
    }
  }

  const [debounced] = useDebouncedValue(current ? JSON.stringify(current) : null, 500);
  const validation = useQuery({
    queryKey: ['agents', 'validate', agent.id, debounced],
    queryFn: ({ signal }) => validateDefinition(JSON.parse(debounced!) as Definition, signal),
    enabled: debounced !== null,
    staleTime: Infinity,
    gcTime: 30_000,
  });
  const stale = (current ? JSON.stringify(current) : null) !== debounced || validation.isFetching;
  const errors = validation.data?.valid === false ? toFieldErrors(validation.data.errors) : [];
  const saveErrors = save.error instanceof ApiError ? save.error.errors : [];

  const update = (fn: (d: Draft) => Draft) => setDraft(fn);
  const toggle = (key: string, open?: boolean) =>
    setOpened((prev) => {
      const next = new Set(prev);
      if (open ?? !next.has(key)) next.add(key);
      else next.delete(key);
      return next;
    });

  const goTo = (next: Tab) =>
    setParams(
      (prev) => {
        const p = new URLSearchParams(prev);
        if (next === 'resumen') p.delete('tab');
        else p.set('tab', next);
        return p;
      },
      { replace: true },
    );

  // Cambiar de pestaña conserva el borrador. Al salir de JSON, lo que esta escrito pasa al formulario:
  // si no parsea, no se sale (se perderia).
  const changeTab = (next: Tab) => {
    if (next === tab) return;
    if (tab === 'json') {
      const p = parseDefinition(jsonText);
      if (!p.ok) return notifyError(new Error(p.error), 'Corregí el JSON para salir de esta pestaña');
      setDraft(toDraft(p.value));
    } else if (next === 'json') setJsonText(toJsonText(fromDraft(draft)));
    goTo(next);
  };

  // Lleva al campo de un error: en JSON, al offset; en el formulario, a la pestaña y la seccion.
  const reveal = (path: string) => {
    if (mode === 'json') return focusOffset(editorRef.current, findPathOffset(jsonText, path));
    const target = errorTarget(draft, path);
    if (!target) return;
    let id: string;
    if (target.section === 'dato' || target.section === 'resultado') {
      toggle(target.key, true);
      id = sectionId(`${target.section}-${target.key}`);
    } else id = sectionId(target.section);
    const part = SECTION_PART[target.section];
    if (part && part !== tab) goTo(part);
    // Despues de cambiar de pestaña y desplegar el bloque.
    setTimeout(
      () => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
      220,
    );
  };

  const doSave = () => {
    if (!current) return notifyError(new Error('Corregí el JSON antes de guardar.'), 'No se puede guardar');
    const prevVersion = agent.version;
    save.mutate(current, {
      onSuccess: (saved) => {
        const savedKey = canonical(saved.definition);
        setBase(savedKey);
        // id y version los fija el servidor; si no cambio nada mas, el formulario queda como esta.
        setDraft((d) => {
          const next = {
            ...toDraft(saved.definition),
            fields: d.fields,
            outcomes: d.outcomes,
            rules: d.rules,
          };
          return stableJson(fromDraft(next)) === savedKey ? next : toDraft(saved.definition);
        });
        setJsonText(toJsonText(saved.definition));
        if (saved.version === prevVersion)
          notifySuccess('La definición es igual a la vigente.', 'Sin cambios');
        else notifySuccess(`Versión ${saved.version} guardada.`);
      },
      onError: (e) => notifyError(e, 'No se pudo guardar'),
    });
  };

  const discard = async () => {
    if (
      await confirmAction({
        title: 'Descartar cambios',
        message: 'Volvés a la versión guardada.',
        danger: true,
        confirmLabel: 'Descartar',
      })
    ) {
      setDraft(toDraft(agent.definition));
      setJsonText(toJsonText(agent.definition));
    }
  };

  const label = (path: string) => (mode === 'form' ? pathLabel(draft, path) : path);

  return (
    <Tabs value={tab} onChange={(v) => v && changeTab(v as Tab)} keepMounted>
      <UnsavedGuard dirty={dirty} />
      <PromptModal definition={current} opened={promptOpen} onClose={prompt.close} />
      <Tabs.List mb="md">
        {TABS.map((t) => {
          const Icon = TAB_META[t].icon;
          return (
            <Tabs.Tab key={t} value={t} leftSection={<Icon size={16} />}>
              {TAB_META[t].label}
            </Tabs.Tab>
          );
        })}
      </Tabs.List>

      {isEditing(tab) && (
        <Stack gap="md">
          <Card py="sm" className="def-toolbar">
            <Group justify="space-between" wrap="wrap" gap="sm">
              <Group gap="xs">
                <Text span c="dimmed" className="mono">
                  {`${agent.slug} · v${agent.version}`}
                </Text>
                {dirty && <Badge color="yellow">Cambios sin guardar</Badge>}
                {current === null ? (
                  <Badge color="red">JSON inválido</Badge>
                ) : stale ? (
                  <Badge color="gray">Validando…</Badge>
                ) : errors.length ? (
                  <Badge color="red">{errors.length === 1 ? '1 error' : `${errors.length} errores`}</Badge>
                ) : validation.data?.valid ? (
                  <Badge color="green">Válida</Badge>
                ) : null}
              </Group>
              <Group gap="xs">
                <Button
                  variant="default"
                  size="xs"
                  leftSection={<IconFileText size={16} />}
                  onClick={prompt.open}
                >
                  Ver prompt
                </Button>
                <Button variant="default" size="xs" onClick={() => void discard()} disabled={!dirty}>
                  Descartar
                </Button>
                <Button
                  size="xs"
                  leftSection={<IconDeviceFloppy size={16} />}
                  onClick={doSave}
                  loading={save.isPending}
                  disabled={!dirty}
                >
                  Guardar versión nueva
                </Button>
              </Group>
            </Group>
          </Card>

          {parsedJson && !parsedJson.ok && (
            <Alert color="red" icon={<IconAlertCircle size={18} />}>
              {parsedJson.error}
            </Alert>
          )}
          {validation.isError && (
            <Alert color="red" icon={<IconAlertCircle size={18} />}>
              No se pudo validar: {errorMessage(validation.error)}
            </Alert>
          )}
          {errors.length > 0 && !stale && (
            <Alert color="red" icon={<IconAlertCircle size={18} />} title="La definición no es válida">
              <ErrorList errors={errors} label={label} onPick={reveal} />
            </Alert>
          )}
          {saveErrors.length > 0 && (
            <Alert color="red" title="No se guardó">
              <ErrorList errors={saveErrors} label={label} onPick={reveal} />
            </Alert>
          )}

          {isPart(tab) ? (
            <DefinitionForm
              part={tab}
              draft={draft}
              update={update}
              opened={opened}
              toggle={toggle}
              voiceSeed={agent.id}
              clientId={agent.client_id}
              agentId={agent.id}
              errors={[...saveErrors, ...errors]}
            />
          ) : (
            <Card>
              <Title order={4} mb={4}>
                Definición en JSON
              </Title>
              <Text size="xs" c="dimmed" mb="sm">
                La misma definición que arman las otras pestañas. <b>id</b> y <b>version</b> los fija el
                servidor (el slug del agente y la versión siguiente): si los cambiás acá, se ignoran.
              </Text>
              <JsonEditor value={jsonText} onChange={setJsonText} editorRef={editorRef} />
            </Card>
          )}
          <Text size="xs" c="dimmed">
            Guardar crea una versión nueva con lo de todas las pestañas; las llamadas en curso siguen con la
            suya.
          </Text>
        </Stack>
      )}

      <Tabs.Panel value="resumen">
        <WorkflowSummary definition={agent.definition} clientId={agent.client_id} />
      </Tabs.Panel>
      <Tabs.Panel value="versiones">
        <VersionsTab agent={agent} />
      </Tabs.Panel>
      <Tabs.Panel value="probar">
        <AgentTestPanel agent={agent} />
      </Tabs.Panel>
      <Tabs.Panel value="link">
        <CallLinkTab agent={agent} />
      </Tabs.Panel>
    </Tabs>
  );
}
