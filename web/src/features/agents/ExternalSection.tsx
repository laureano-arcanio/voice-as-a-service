import {
  Alert,
  Button,
  Group,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  Textarea,
  TextInput,
} from '@mantine/core';
import { Link } from 'react-router';
import type { FieldError } from '@/api/errors';
import { PlanGate } from '@/components/PlanGate';
import { useLlmConnections, useTestLlmConnection } from '@/features/llm/api';
import { notifyError, notifySuccess } from '@/lib/notify';
import { connectionLabel } from '@/features/llm/labels';
import { useAreas } from '@/features/team/api';
import { type Draft, EXTERNAL_DEFAULTS, type ExternalDraft } from './draft';

/** Tu propio agente (docs/features/LLM_CONEXIONES.md): cada turno lo contesta el endpoint del cliente. Prenderlo
 * pone definition.external; apagarlo lo saca. */
export function ExternalSection({
  draft,
  update,
  clientId,
  errors = [],
}: {
  draft: Draft;
  update: (fn: (d: Draft) => Draft) => void;
  clientId: string;
  errors?: FieldError[];
}) {
  const connections = useLlmConnections(clientId);
  const test = useTestLlmConnection(clientId);
  const areas = useAreas(clientId);
  const on = draft.external !== null;
  const ext = draft.external;
  const endpoints = (connections.data ?? []).filter((c) => c.kind === 'openai_compatible');
  const current = endpoints.find((c) => c.id === ext?.connection);
  const connectionsLink = '/models';
  const errorOf = (field: string) => errors.find((e) => e.path === `external.${field}`)?.message;
  const set = (patch: Partial<ExternalDraft>) =>
    update((d) => ({
      ...d,
      external: { ...(d.external ?? { connection: '', ...EXTERNAL_DEFAULTS }), ...patch },
    }));

  const areaName = new Map((areas.data ?? []).map((a) => [a.id, a.name]));
  const onErrorsOptions = [
    { value: 'hang_up', label: 'Cortar la llamada' },
    ...draft.handoff.areas.map((a) => ({
      value: `transfer:${a.areaId}`,
      label: `Pasar la llamada a ${areaName.get(a.areaId) ?? 'un área'}`,
    })),
  ];

  return (
    <PlanGate feature="external_agent" what="usar tu propio agente">
      <Stack gap="sm">
        <Switch
          label="Que conteste tu propio agente"
          description="En cada turno, Atentina le manda la conversación a tu endpoint (compatible con la API de OpenAI, con streaming) y dice lo que responde. La voz, la telefonía, la grabación y los minutos siguen siendo de Atentina; el prompt, las herramientas y los datos, de tu agente."
          checked={on}
          onChange={(e) => {
            const checked = e.currentTarget.checked;
            update((d) => ({
              ...d,
              external: checked
                ? (d.external ?? { connection: endpoints[0]?.id ?? '', ...EXTERNAL_DEFAULTS })
                : null,
            }));
          }}
        />
        {on && ext && (
          <>
            {connections.isSuccess && endpoints.length === 0 ? (
              <Alert color="blue">
                <Stack gap="xs" align="flex-start">
                  <Text size="sm">
                    Cargá la URL de tu endpoint como una conexión <b>OpenAI compatible</b>, con la API key que
                    tu endpoint espera, y elegila acá.
                  </Text>
                  <Button component={Link} to={connectionsLink} size="xs" variant="light">
                    Cargar el endpoint
                  </Button>
                </Stack>
              </Alert>
            ) : (
              <SimpleGrid cols={{ base: 1, sm: 2 }}>
                <Select
                  label="Endpoint"
                  description="La conexión con la URL y la API key de tu agente."
                  placeholder="Elegí una conexión"
                  data={endpoints.map((c) => ({ value: c.id, label: connectionLabel(c) }))}
                  value={ext.connection || null}
                  onChange={(v) => set({ connection: v ?? '' })}
                  error={errorOf('connection')}
                  allowDeselect={false}
                />
                <TextInput
                  label="Modelo"
                  description="Va en model de cada pedido: con un solo endpoint para varios agentes, tu endpoint los distingue por este valor."
                  placeholder={current?.default_model || 'el de la conexión'}
                  value={ext.model}
                  onChange={(e) => set({ model: e.currentTarget.value })}
                  error={errorOf('model')}
                />
              </SimpleGrid>
            )}
            {current && (
              <Group gap="sm" wrap="nowrap" align="center">
                <Button
                  size="xs"
                  variant="default"
                  loading={test.isPending}
                  onClick={() =>
                    test.mutate(
                      { id: current.id, model: ext.model.trim() || undefined, mode: 'external' },
                      {
                        onSuccess: (c) =>
                          c.last_test_ok
                            ? notifySuccess(`Tu agente respondió (${c.last_test_detail}).`)
                            : notifyError(c.last_test_detail, 'Tu agente no respondió'),
                        onError: (e) => notifyError(e, 'No se pudo probar el endpoint'),
                      },
                    )
                  }
                >
                  Probar el endpoint
                </Button>
                <Text size="xs" c="dimmed">
                  Le manda un turno de prueba, como los de una llamada, y mide cuánto tarda el primer texto.
                  Si pasa de un segundo, la conversación se va a sentir lenta.
                </Text>
              </Group>
            )}
            <Textarea
              label="Prompt de sistema (opcional)"
              description="Se antepone a la conversación en cada pedido. Vacío: solo los mensajes, el prompt lo pone tu agente."
              autosize
              minRows={2}
              maxRows={10}
              value={ext.system}
              onChange={(e) => set({ system: e.currentTarget.value })}
              error={errorOf('system')}
            />
            <TextInput
              label="Mensaje si tu agente no responde"
              description="Lo dice el agente si el endpoint da error o no empieza a responder a tiempo."
              value={ext.errorMessage}
              onChange={(e) => set({ errorMessage: e.currentTarget.value })}
              error={errorOf('error_message')}
            />
            <SimpleGrid cols={{ base: 1, sm: 3 }}>
              <NumberInput
                label="Espera del primer texto (ms)"
                description="Si no llega texto en este tiempo, el turno cuenta como error."
                value={ext.firstTokenTimeoutMs}
                onChange={(v) =>
                  set({
                    firstTokenTimeoutMs: typeof v === 'number' ? v : EXTERNAL_DEFAULTS.firstTokenTimeoutMs,
                  })
                }
                min={500}
                max={20_000}
                step={500}
                allowDecimal={false}
                error={errorOf('first_token_timeout_ms')}
              />
              <NumberInput
                label="Errores seguidos"
                description="Cuántos turnos fallidos se toleran antes de lo de al lado."
                value={ext.maxErrors}
                onChange={(v) => set({ maxErrors: typeof v === 'number' ? v : EXTERNAL_DEFAULTS.maxErrors })}
                min={1}
                max={10}
                allowDecimal={false}
                error={errorOf('max_errors')}
              />
              <Select
                label="Después de esos errores"
                description="Las áreas salen de Derivación a personas."
                data={onErrorsOptions}
                value={onErrorsOptions.some((o) => o.value === ext.onErrors) ? ext.onErrors : 'hang_up'}
                onChange={(v) => set({ onErrors: v ?? 'hang_up' })}
                error={errorOf('on_errors')}
                allowDeselect={false}
              />
            </SimpleGrid>
            <Text size="xs" c="dimmed">
              Tu agente recibe dos herramientas: end_call (cortar, con el resultado de la conversación) y, si
              el agente tiene áreas, transfer_call (pasar la llamada). Los datos de la llamada llegan en los
              headers X-Atentina-*.
            </Text>
          </>
        )}
      </Stack>
    </PlanGate>
  );
}
