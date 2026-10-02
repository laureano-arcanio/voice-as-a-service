import { Alert, Anchor, Badge, Button, Card, Group, List, Modal, Stack, Text, Title } from '@mantine/core';
import { useDebouncedValue, useWindowEvent } from '@mantine/hooks';
import { IconAlertCircle, IconCircleCheck, IconDeviceFloppy } from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';
import type { ReactCodeMirrorRef } from '@uiw/react-codemirror';
import { useRef, useState } from 'react';
import { useBlocker } from 'react-router';
import { ApiError, errorMessage, type FieldError } from '@/api/errors';
import type { AgentDetail } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { JsonEditor } from '@/components/JsonEditor';
import { focusOffset } from '@/lib/editor';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useSaveDefinition, validateDefinition } from './api';
import { findPathOffset, parseDefinition, toJsonText } from './definition';

function toFieldErrors(errors: Record<string, unknown>[] | undefined): FieldError[] {
  return (errors ?? []).map((e) => ({ path: String(e.path ?? ''), message: String(e.message ?? '') }));
}

function ErrorList({ errors, onPick }: { errors: FieldError[]; onPick: (path: string) => void }) {
  return (
    <List size="sm" spacing={4}>
      {errors.map((e, i) => (
        <List.Item key={i}>
          {e.path ? (
            <Anchor
              component="button"
              type="button"
              size="sm"
              className="mono"
              onClick={() => onPick(e.path)}
            >
              {e.path}
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

export function DefinitionTab({ agent, canEdit }: { agent: AgentDetail; canEdit: boolean }) {
  const baseline = toJsonText(agent.definition);
  const [base, setBase] = useState(baseline);
  const [draft, setDraft] = useState(baseline);
  // Llego una version nueva (guardado, restauracion u otra sesion): si no hay cambios, se muestra.
  if (baseline !== base) {
    setBase(baseline);
    if (draft === base) setDraft(baseline);
  }
  const dirty = draft !== base;
  const editorRef = useRef<ReactCodeMirrorRef>(null);
  const save = useSaveDefinition(agent.id);

  const [debounced] = useDebouncedValue(draft, 500);
  const parsed = parseDefinition(debounced);
  const validation = useQuery({
    queryKey: ['agents', 'validate', agent.id, debounced],
    queryFn: ({ signal }) => {
      const p = parseDefinition(debounced);
      if (!p.ok) throw new Error(p.error);
      return validateDefinition(p.value, signal);
    },
    enabled: canEdit && parsed.ok,
    staleTime: Infinity,
    gcTime: 30_000,
  });

  const pick = (path: string) => focusOffset(editorRef.current, findPathOffset(draft, path));

  const doSave = () => {
    const p = parseDefinition(draft);
    if (!p.ok) return notifyError(new Error(p.error), 'No se puede guardar');
    const prevVersion = agent.version;
    save.mutate(p.value, {
      onSuccess: (saved) => {
        const text = toJsonText(saved.definition);
        setBase(text);
        setDraft(text);
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
      setDraft(base);
    }
  };

  const format = () => {
    const p = parseDefinition(draft);
    if (p.ok) setDraft(toJsonText(p.value));
  };

  const saveErrors = save.error instanceof ApiError ? save.error.errors : [];
  const stale = debounced !== draft;

  return (
    <Stack gap="md">
      {canEdit && <UnsavedGuard dirty={dirty} />}
      <Card>
        <Group justify="space-between" mb="sm" wrap="wrap">
          <Group gap="xs">
            <Text span c="dimmed" className="mono">
              {agent.slug} · v{agent.version}
            </Text>
            {dirty && <Badge color="yellow">Cambios sin guardar</Badge>}
          </Group>
          {canEdit ? (
            <Group gap="xs">
              <Button variant="default" size="xs" onClick={format}>
                Formatear
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
          ) : (
            <Text size="xs" c="dimmed">
              Solo lectura: la edita un administrador.
            </Text>
          )}
        </Group>
        <Text size="xs" c="dimmed" mb="sm">
          <b>id</b> y <b>version</b> los fija el servidor (el slug del agente y la versión siguiente): si los
          cambiás acá, se ignoran. Guardar crea una versión nueva; las llamadas en curso siguen con la suya.
        </Text>
        <JsonEditor
          value={draft}
          onChange={canEdit ? setDraft : undefined}
          readOnly={!canEdit}
          editorRef={editorRef}
        />
      </Card>

      {canEdit && (
        <Card>
          <Title order={4} mb="sm">
            Validación {stale || validation.isFetching ? '…' : ''}
          </Title>
          {!parsed.ok ? (
            <Alert color="red" icon={<IconAlertCircle size={18} />}>
              {parsed.error}
            </Alert>
          ) : validation.isError ? (
            <Alert color="red" icon={<IconAlertCircle size={18} />}>
              {errorMessage(validation.error)}
            </Alert>
          ) : validation.data?.valid === false ? (
            <Alert color="red" icon={<IconAlertCircle size={18} />} title="La definición no es válida">
              <ErrorList errors={toFieldErrors(validation.data.errors)} onPick={pick} />
            </Alert>
          ) : validation.data?.valid ? (
            <Alert color="green" icon={<IconCircleCheck size={18} />}>
              Definición válida.
            </Alert>
          ) : (
            <Text size="sm" c="dimmed">
              Validando…
            </Text>
          )}
          {saveErrors.length > 0 && (
            <Alert color="red" mt="sm" title="No se guardó">
              <ErrorList errors={saveErrors} onPick={pick} />
            </Alert>
          )}
        </Card>
      )}
    </Stack>
  );
}
