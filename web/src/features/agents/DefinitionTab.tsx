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
  Text,
  Title,
} from '@mantine/core';
import { useDebouncedValue, useDisclosure, useWindowEvent } from '@mantine/hooks';
import { IconAlertCircle, IconDeviceFloppy, IconFileText } from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';
import type { ReactCodeMirrorRef } from '@uiw/react-codemirror';
import { useRef, useState } from 'react';
import { useBlocker } from 'react-router';
import { ApiError, errorMessage, type FieldError } from '@/api/errors';
import type { AgentDetail, Definition } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { JsonEditor } from '@/components/JsonEditor';
import { QueryState } from '@/components/QueryState';
import { useIsAdmin } from '@/features/auth/api';
import { focusOffset } from '@/lib/editor';
import { ENGINE } from '@/lib/labels';
import { notifyError, notifySuccess } from '@/lib/notify';
import { usePromptPreview, useSaveDefinition, validateDefinition } from './api';
import { findPathOffset, parseDefinition, toJsonText } from './definition';
import { DefinitionForm } from './DefinitionForm';
import { type Draft, errorTarget, fromDraft, pathLabel, sectionId, stableJson, toDraft } from './draft';

type Mode = 'form' | 'json';

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

/** El prompt que arma el motor con la definicion en edicion (sin guardarla). */
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
                  <Text span size="xs" c="dimmed" fw={400}>
                    {p.engine === 'classic'
                      ? '· motor clásico: todo el agente va acá'
                      : '· motor estructurado: es igual para todos los agentes'}
                  </Text>
                </Text>
                <pre className="code">{p.system}</pre>
                {p.workflow && (
                  <>
                    <Text size="sm" fw={600}>
                      Definición{' '}
                      <Text span size="xs" c="dimmed" fw={400}>
                        · va en cada turno, junto con la conversación y el estado
                      </Text>
                    </Text>
                    <pre className="code">{p.workflow}</pre>
                  </>
                )}
              </Stack>
            )}
          </QueryState>
        )}
      </Stack>
    </Modal>
  );
}

export function DefinitionTab({ agent }: { agent: AgentDetail }) {
  // El cliente edita por formulario; motor, JSON y prompt son internos (solo admin).
  const isAdmin = useIsAdmin();
  const baseline = canonical(agent.definition);
  const [base, setBase] = useState(baseline);
  const [draft, setDraft] = useState<Draft>(() => toDraft(agent.definition));
  const [mode, setMode] = useState<Mode>('form');
  const [jsonText, setJsonText] = useState('');
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

  const reveal = (path: string) => {
    if (mode === 'json') return focusOffset(editorRef.current, findPathOffset(jsonText, path));
    const target = errorTarget(draft, path);
    if (!target) return;
    let id: string;
    if (target.section === 'dato' || target.section === 'resultado') {
      toggle(target.key, true);
      id = sectionId(`${target.section}-${target.key}`);
    } else id = sectionId(target.section);
    // Despues de desplegar el bloque.
    setTimeout(
      () => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
      220,
    );
  };

  const switchMode = (next: Mode) => {
    if (next === mode) return;
    if (next === 'json') {
      setJsonText(toJsonText(fromDraft(draft)));
      setMode('json');
      return;
    }
    const p = parseDefinition(jsonText);
    if (!p.ok) return notifyError(new Error(p.error), 'Corregí el JSON para volver al formulario');
    setDraft(toDraft(p.value));
    setMode('form');
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
    <Stack gap="md">
      <UnsavedGuard dirty={dirty} />
      {isAdmin && <PromptModal definition={current} opened={promptOpen} onClose={prompt.close} />}
      <Card py="sm" className="def-toolbar">
        <Group justify="space-between" wrap="wrap" gap="sm">
          <Group gap="xs">
            <Text span c="dimmed" className="mono">
              {isAdmin ? `${agent.slug} · v${agent.version}` : `v${agent.version}`}
            </Text>
            {isAdmin && (
              <Badge color="gray">
                {ENGINE[mode === 'form' ? draft.engine : String(current?.engine)] ?? '–'}
              </Badge>
            )}
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
            {isAdmin && (
              <>
                <SegmentedControl
                  size="xs"
                  data={[
                    { value: 'form', label: 'Formulario' },
                    { value: 'json', label: 'JSON' },
                  ]}
                  value={mode}
                  onChange={(v) => switchMode(v as Mode)}
                />
                <Button
                  variant="default"
                  size="xs"
                  leftSection={<IconFileText size={16} />}
                  onClick={prompt.open}
                >
                  Ver prompt
                </Button>
              </>
            )}
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

      {mode === 'form' ? (
        <DefinitionForm
          draft={draft}
          update={update}
          opened={opened}
          toggle={toggle}
          voiceSeed={agent.id}
          showEngine={isAdmin}
        />
      ) : (
        <Card>
          <Title order={4} mb={4}>
            Definición en JSON
          </Title>
          <Text size="xs" c="dimmed" mb="sm">
            La misma definición que arma el formulario. <b>id</b> y <b>version</b> los fija el servidor (el
            slug del agente y la versión siguiente): si los cambiás acá, se ignoran.
          </Text>
          <JsonEditor value={jsonText} onChange={setJsonText} editorRef={editorRef} />
        </Card>
      )}
      <Text size="xs" c="dimmed">
        Guardar crea una versión nueva; las llamadas en curso siguen con la suya.
      </Text>
    </Stack>
  );
}
