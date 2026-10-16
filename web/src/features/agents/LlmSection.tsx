import { ActionIcon, Alert, Anchor, Autocomplete, Button, Group, NumberInput, Select, Stack, Switch, Text, Tooltip } from '@mantine/core';
import { IconPlus, IconShieldLock, IconTrash } from '@tabler/icons-react';
import { Link } from 'react-router';
import type { LlmConnection, LlmProviderSpec } from '@/api/types';
import { useIsAdmin } from '@/features/auth/api';
import { useLlmConnections, useLlmModels, useLlmParams } from '@/features/llm/api';
import { connectionLabel, KIND_LABEL, LOCAL_LABEL } from '@/features/llm/labels';
import { blankStage, type Draft, type LlmDraft, type LlmStageDraft, MAX_LLM_STAGES } from './draft';
import { GenerationEditor, type LocalDefaults } from './GenerationEditor';

const LOCAL = 'local';
const GAP = 3;     // turnos de diferencia que propone una etapa nueva

function stageProvider(stage: LlmStageDraft, connections: LlmConnection[]): string {
  if (!stage.connection) return 'vllm';
  return connections.find((c) => c.id === stage.connection)?.kind ?? 'vllm';
}

function StageRow({
  index,
  stage,
  clientId,
  connections,
  providers,
  localDefaults,
  engine,
  onChange,
  onRemove,
}: {
  index: number;
  stage: LlmStageDraft;
  clientId: string;
  connections: LlmConnection[];
  providers: LlmProviderSpec[];
  localDefaults: LocalDefaults;
  engine: string;
  onChange: (patch: Partial<LlmStageDraft>) => void;
  onRemove: (() => void) | null;
}) {
  const external = stage.connection !== null;
  const known = connections.find((c) => c.id === stage.connection);
  const models = useLlmModels(clientId, known ? known.id : null);

  const options = [
    { value: LOCAL, label: LOCAL_LABEL },
    ...connections.map((c) => ({ value: c.id, label: connectionLabel(c) })),
    // Una conexion dada de baja sigue en la definicion: se ve y se puede cambiar.
    ...(stage.connection && !known
      ? [{ value: stage.connection, label: 'Conexión dada de baja', disabled: true }]
      : []),
  ];

  const pick = (value: string | null) => {
    if (!value || value === LOCAL) return onChange({ connection: null, model: '' });
    const c = connections.find((x) => x.id === value);
    onChange({ connection: value, model: stage.model || c?.default_model || '' });
  };

  return (
    <div className="def-item" style={{ padding: 'var(--mantine-spacing-sm)' }}>
      <Stack gap="xs">
        <Group align="flex-end" wrap="wrap" gap="sm">
          <NumberInput
            label={index === 0 ? 'Desde el turno' : `Etapa ${index + 1}: desde el turno`}
            description={index === 0 ? 'Siempre el primero.' : undefined}
            value={stage.fromTurn}
            onChange={(v) => onChange({ fromTurn: typeof v === 'number' ? Math.max(1, Math.floor(v)) : 1 })}
            min={1}
            step={1}
            allowDecimal={false}
            disabled={index === 0}
            w={index === 0 ? 150 : 190}
          />
          <Select
            label="Modelo de lenguaje"
            data={options}
            value={stage.connection ?? LOCAL}
            onChange={pick}
            allowDeselect={false}
            style={{ flex: '1 1 220px' }}
          />
          {external && (
            <Autocomplete
              label="Modelo"
              placeholder={known?.default_model || 'nombre del modelo'}
              data={models.data ?? []}
              value={stage.model}
              onChange={(model) => onChange({ model })}
              limit={50}
              style={{ flex: '1 1 220px' }}
            />
          )}
          {onRemove && (
            <Tooltip label="Quitar etapa" withArrow>
              <ActionIcon color="red" variant="subtle" aria-label="Quitar etapa" onClick={onRemove}>
                <IconTrash size={18} />
              </ActionIcon>
            </Tooltip>
          )}
        </Group>
        {external && models.isError && (
          <Text size="xs" c="dimmed">
            No se pudo leer la lista de modelos del proveedor: escribí el nombre a mano.
          </Text>
        )}
        <GenerationEditor
          rows={stage.generation}
          provider={stageProvider(stage, connections)}
          engine={engine}
          providers={providers}
          localDefaults={localDefaults}
          onChange={(generation) => onChange({ generation })}
          compact
        />
      </Stack>
    </div>
  );
}

/** Que LLM contesta cada tramo de la conversacion (servidor propio o una conexion del cliente) y con
 * que parametros de generacion (app/llm/params.py). */
export function LlmSection({
  draft,
  update,
  clientId,
}: {
  draft: Draft;
  update: (fn: (d: Draft) => Draft) => void;
  clientId: string;
}) {
  const isAdmin = useIsAdmin();
  const list = useLlmConnections(clientId);
  const catalog = useLlmParams();
  const connections = list.data ?? [];
  const providers = catalog.data?.providers ?? [];
  const localDefaults: LocalDefaults = catalog.data?.local_defaults ?? {};
  const llm: LlmDraft = draft.llm ?? { stages: [blankStage(1)], fallbackLocal: true };
  const setLlm = (fn: (l: LlmDraft) => LlmDraft) => update((d) => ({ ...d, llm: fn(d.llm ?? llm) }));
  const patchStage = (key: string, patch: Partial<LlmStageDraft>) =>
    setLlm((l) => ({ ...l, stages: l.stages.map((st) => (st.key === key ? { ...st, ...patch } : st)) }));

  const external = llm.stages.filter((st) => st.connection !== null);
  const last = llm.stages[llm.stages.length - 1]!;
  const where = (st: LlmStageDraft) => {
    const c = connections.find((x) => x.id === st.connection);
    return `${c ? KIND_LABEL[c.kind] : 'un proveedor externo'}${st.model ? ` (${st.model})` : ''}`;
  };
  const connectionsLink = isAdmin ? `/clients/${clientId}?tab=modelos` : '/models';

  return (
    <Stack gap="md">
      <Stack gap="xs">
        <Text size="sm" fw={500}>
          Parámetros por defecto
        </Text>
        <Text size="xs" c="dimmed">
          Temperatura, razonamiento, tope de tokens y demás, para toda la conversación. El proveedor manda solo
          los que soporta; el resto se descarta. Cada etapa puede pisarlos.
        </Text>
        <GenerationEditor
          rows={draft.generation}
          provider={stageProvider(llm.stages[0]!, connections)}
          engine={draft.engine}
          providers={providers}
          localDefaults={localDefaults}
          onChange={(generation) => update((d) => ({ ...d, generation }))}
        />
      </Stack>

      <Stack gap="sm">
        <Text size="xs" c="dimmed">
          Por defecto contesta el {LOCAL_LABEL}. Con tus propias claves podés usar otro proveedor desde cierto
          turno, o al revés. El turno es el mensaje número N de la persona: la apertura del agente no cuenta.
        </Text>
        {llm.stages.map((st, i) => (
          <StageRow
            key={st.key}
            index={i}
            stage={st}
            clientId={clientId}
            connections={connections}
            providers={providers}
            localDefaults={localDefaults}
            engine={draft.engine}
            onChange={(patch) => patchStage(st.key, patch)}
            onRemove={
              i === 0 ? null : () => setLlm((l) => ({ ...l, stages: l.stages.filter((x) => x.key !== st.key) }))
            }
          />
        ))}
        <Group justify="space-between" gap="sm">
          <Button
            variant="default"
            size="xs"
            leftSection={<IconPlus size={16} />}
            disabled={llm.stages.length >= MAX_LLM_STAGES}
            onClick={() =>
              setLlm((l) => ({
                ...l,
                stages: [...l.stages, blankStage(Math.max(...l.stages.map((s) => s.fromTurn)) + GAP)],
              }))
            }
          >
            Agregar etapa
          </Button>
          {list.isSuccess && connections.length === 0 && (
            <Text size="xs" c="dimmed">
              Todavía no cargaste conexiones.{' '}
              <Anchor component={Link} to={connectionsLink} size="xs">
                Cargar una
              </Anchor>
            </Text>
          )}
        </Group>
      </Stack>

      {external.length > 0 && (
        <>
          <Switch
            label="Usar el servidor Atentina si el proveedor falla"
            description="Con esto apagado, un error del proveedor corta el turno."
            checked={llm.fallbackLocal}
            onChange={(e) => {
              const fallbackLocal = e.currentTarget.checked;
              setLlm((l) => ({ ...l, fallbackLocal }));
            }}
          />
          <Alert color="yellow" icon={<IconShieldLock size={18} />} title="Las conversaciones salen del servidor">
            {external.map((st) => (
              <div key={st.key}>
                Desde el turno {st.fromTurn}, este agente manda la conversación a {where(st)}.
              </div>
            ))}
            {last.connection === null && llm.stages.length > 1 && (
              <div>
                Desde el turno {last.fromTurn} vuelve al {LOCAL_LABEL}.
              </div>
            )}
          </Alert>
        </>
      )}
    </Stack>
  );
}
