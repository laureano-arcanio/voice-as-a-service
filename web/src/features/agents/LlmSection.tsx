import {
  ActionIcon,
  Alert,
  Autocomplete,
  Button,
  Group,
  NumberInput,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  Text,
  Tooltip,
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { IconKey, IconPlus, IconShieldLock, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router';
import type { LlmConnection, LlmParamSpec, LlmProviderSpec } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { useIsAdmin } from '@/features/auth/api';
import { useLlmConnections, useLlmModels, useLlmParams } from '@/features/llm/api';
import { connectionLabel, KIND_LABEL, LOCAL_LABEL } from '@/features/llm/labels';
import { blankStage, type Draft, type LlmDraft, type LlmStageDraft, MAX_LLM_STAGES, type ParamDraft } from './draft';
import { GenerationEditor } from './GenerationEditor';

const LOCAL = 'local';
const ATENTINA = 'atentina';
const BYOK = 'byok';
const GAP = 3;     // turnos de diferencia que propone una etapa nueva

function stageProvider(stage: LlmStageDraft, connections: LlmConnection[]): string {
  if (!stage.connection) return 'vllm';
  return connections.find((c) => c.id === stage.connection)?.kind ?? 'vllm';
}

const providerName = (kind: string, providers: LlmProviderSpec[]) =>
  kind === 'vllm' ? LOCAL_LABEL : (providers.find((p) => p.kind === kind)?.label ?? kind);

const paramsOf = (kind: string, providers: LlmProviderSpec[]) => providers.find((p) => p.kind === kind)?.params ?? [];

/** Defaults efectivos: los del nivel de abajo pisados por los cambios de este. */
const withRows = (base: Record<string, unknown>, rows: ParamDraft[]) => ({
  ...base,
  ...Object.fromEntries(rows.map((r) => [r.name, r.value])),
});

function StageRow({
  index,
  stage,
  clientId,
  connections,
  providers,
  allSpecs,
  defaults,
  unlocked,
  onUnlock,
  onChange,
  onRemove,
}: {
  index: number;
  stage: LlmStageDraft;
  clientId: string;
  connections: LlmConnection[];
  providers: LlmProviderSpec[];
  allSpecs: Map<string, LlmParamSpec>;
  /** Lo que rige en esta etapa si no se cambia nada, por proveedor. */
  defaults: (kind: string) => Record<string, unknown>;
  unlocked: boolean;
  onUnlock: () => void;
  onChange: (patch: Partial<LlmStageDraft>) => void;
  onRemove: (() => void) | null;
}) {
  const external = stage.connection !== null;
  const known = connections.find((c) => c.id === stage.connection);
  const models = useLlmModels(clientId, known ? known.id : null);
  const kind = stageProvider(stage, connections);

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
        <Group justify="space-between" gap="sm">
          <Text size="sm" fw={600}>
            Etapa {index + 1}
          </Text>
          {onRemove && (
            <Tooltip label="Quitar etapa" withArrow>
              <ActionIcon color="red" variant="subtle" aria-label="Quitar etapa" onClick={onRemove}>
                <IconTrash size={18} />
              </ActionIcon>
            </Tooltip>
          )}
        </Group>
        <Group align="flex-end" wrap="wrap" gap="sm">
          <NumberInput
            label="Desde el turno"
            value={stage.fromTurn}
            onChange={(v) => onChange({ fromTurn: typeof v === 'number' ? Math.max(1, Math.floor(v)) : 1 })}
            min={1}
            step={1}
            allowDecimal={false}
            disabled={index === 0}
            w={170}
          />
          <Select
            label="Contesta"
            data={options}
            value={stage.connection ?? LOCAL}
            onChange={pick}
            allowDeselect={false}
            style={{ flex: '1 1 220px' }}
          />
          {external && (
            <Autocomplete
              label="Modelo del proveedor"
              placeholder={known?.default_model || 'nombre del modelo'}
              data={models.data ?? []}
              value={stage.model}
              onChange={(model) => onChange({ model })}
              limit={50}
              style={{ flex: '1 1 220px' }}
            />
          )}
        </Group>
        {external && models.isError && (
          <Text size="xs" c="dimmed">
            No se pudo leer la lista de modelos del proveedor: escribí el nombre a mano.
          </Text>
        )}
        <GenerationEditor
          rows={stage.generation}
          specs={paramsOf(kind, providers)}
          allSpecs={allSpecs}
          defaults={defaults(kind)}
          unlocked={unlocked}
          onUnlock={onUnlock}
          onChange={(generation) => onChange({ generation })}
          label="Parámetros de esta etapa"
          notApplies={`No lo usa ${providerName(kind, providers)}: se descarta.`}
        />
      </Stack>
    </div>
  );
}

/** Que modelo contesta: el de Atentina (default, en el servidor propio) o, con claves propias (BYOK), un
 * proveedor por etapa de la conversacion; y con que parametros de generacion (app/llm/params.py). */
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
  const narrow = useMediaQuery('(max-width: 36em)');
  const list = useLlmConnections(clientId);
  const catalog = useLlmParams();
  const connections = list.data ?? [];
  const providers = catalog.data?.providers ?? [];
  const allSpecs = new Map(providers.flatMap((p) => p.params).map((s) => [s.name, s]));
  const connectionsLink = isAdmin ? `/clients/${clientId}?tab=modelos` : '/models';

  const byok = draft.llm !== null;
  const llm: LlmDraft = draft.llm ?? { stages: [blankStage(1)], fallbackLocal: true };
  const setLlm = (fn: (l: LlmDraft) => LlmDraft) => update((d) => ({ ...d, llm: fn(d.llm ?? llm) }));
  const patchStage = (key: string, patch: Partial<LlmStageDraft>) =>
    setLlm((l) => ({ ...l, stages: l.stages.map((st) => (st.key === key ? { ...st, ...patch } : st)) }));

  // Cambiar parametros se confirma una vez por edicion; si ya hay cambios, no se pregunta.
  const [unlocked, setUnlocked] = useState(
    () => draft.generation.length > 0 || (draft.llm?.stages.some((s) => s.generation.length > 0) ?? false),
  );
  const unlock = async () => {
    const ok = await confirmAction({
      title: '¿Cambiar los parámetros del modelo?',
      message:
        'Los valores por defecto son los recomendados para este modelo. Cambiarlos puede hacer que el agente ' +
        'conteste más lento, más largo o con menos precisión. Después de guardar, probalo con una llamada o el chat.',
      confirmLabel: 'Cambiar',
    });
    if (ok) setUnlocked(true);
  };

  // Los defaults del LLM local (su configuracion; lo que no aparece lo decide el servidor).
  const local: Record<string, unknown> = catalog.data?.local_defaults ?? {};
  const kinds = byok ? [...new Set(llm.stages.map((st) => stageProvider(st, connections)))] : ['vllm'];
  // Los del agente rigen en todas las etapas: se muestran los de los proveedores en uso, y el default del
  // servidor propio solo si es el unico.
  const globalSpecs = [...new Map(kinds.flatMap((k) => paramsOf(k, providers)).map((s) => [s.name, s])).values()];
  const globalDefaults = kinds.length === 1 && kinds[0] === 'vllm' ? local : {};
  const stageDefaults = (kind: string) => withRows(kind === 'vllm' ? local : {}, draft.generation);

  const setMode = async (mode: string) => {
    if (mode === BYOK) {
      const first = connections[0];
      if (!first) return;
      update((d) => ({
        ...d,
        llm: { stages: [{ ...blankStage(1), connection: first.id, model: first.default_model ?? '' }], fallbackLocal: true },
      }));
      return;
    }
    const ok = await confirmAction({
      title: `¿Volver a ${LOCAL_LABEL}?`,
      message: 'Se quitan las etapas y sus parámetros: toda la conversación la contesta el modelo de Atentina.',
      confirmLabel: 'Volver',
    });
    if (ok) update((d) => ({ ...d, llm: null }));
  };

  const noKeys = list.isSuccess && connections.length === 0;
  const external = byok ? llm.stages.filter((st) => st.connection !== null) : [];
  const last = llm.stages[llm.stages.length - 1]!;
  const where = (st: LlmStageDraft) => {
    const c = connections.find((x) => x.id === st.connection);
    return `${c ? KIND_LABEL[c.kind] : 'un proveedor externo'}${st.model ? ` (${st.model})` : ''}`;
  };

  return (
    <Stack gap="md">
      <Stack gap={6}>
        <SegmentedControl
          value={byok ? BYOK : ATENTINA}
          onChange={setMode}
          data={[
            { value: ATENTINA, label: `Modelo ${LOCAL_LABEL}` },
            { value: BYOK, label: 'Mis proveedores, por etapas', disabled: !byok && connections.length === 0 },
          ]}
          fullWidth
          orientation={narrow ? 'vertical' : 'horizontal'}
          aria-label="Modelo"
        />
        <Text size="xs" c="dimmed">
          {byok
            ? 'Cada etapa es un tramo de la conversación con su modelo: tus proveedores (BYOK) o el de Atentina.'
            : 'El modelo de Atentina, en nuestros servidores: la conversación no sale de Atentina. Es el recomendado.'}
        </Text>
      </Stack>

      {!byok && noKeys && (
        <Alert color="blue" variant="light" icon={<IconKey size={18} />} title="¿Querés usar otro modelo?">
          <Stack gap="xs" align="flex-start">
            <Text size="sm">
              Cargá la clave de tu proveedor (OpenAI, Anthropic, OpenRouter u otro compatible) en Modelos. Después
              vas a poder elegir qué modelo contesta cada etapa de la conversación.
            </Text>
            <Button component={Link} to={connectionsLink} size="xs" variant="light">
              Cargar una clave
            </Button>
          </Stack>
        </Alert>
      )}

      {/* Con etapas, los parametros van en cada una; los del agente se ven solo si ya hay (rigen en todas). */}
      {(!byok || draft.generation.length > 0) && (
        <GenerationEditor
          rows={draft.generation}
          specs={globalSpecs}
          allSpecs={allSpecs}
          defaults={globalDefaults}
          unlocked={unlocked}
          onUnlock={unlock}
          onChange={(generation) => update((d) => ({ ...d, generation }))}
          label={byok ? 'Configurar parámetros para todas las etapas' : 'Configurar parámetros del modelo'}
          notApplies="No lo usa ningún modelo de este agente: se descarta."
        />
      )}

      {byok && (
        <Stack gap="sm">
          <Text size="xs" c="dimmed">
            El turno es el mensaje número N de la persona: la apertura del agente no cuenta. Ejemplo: Anthropic
            del turno 1 al 3 y {LOCAL_LABEL} desde el 4. Hasta {MAX_LLM_STAGES} etapas.
          </Text>
          {llm.stages.map((st, i) => (
            <StageRow
              key={st.key}
              index={i}
              stage={st}
              clientId={clientId}
              connections={connections}
              providers={providers}
              allSpecs={allSpecs}
              defaults={stageDefaults}
              unlocked={unlocked}
              onUnlock={unlock}
              onChange={(patch) => patchStage(st.key, patch)}
              onRemove={
                i === 0 ? null : () => setLlm((l) => ({ ...l, stages: l.stages.filter((x) => x.key !== st.key) }))
              }
            />
          ))}
          <Button
            variant="default"
            size="xs"
            w="fit-content"
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
        </Stack>
      )}

      {external.length > 0 && (
        <>
          <Switch
            label={`Usar ${LOCAL_LABEL} si el proveedor falla`}
            description="Con esto apagado, un error del proveedor corta el turno."
            checked={llm.fallbackLocal}
            onChange={(e) => {
              const fallbackLocal = e.currentTarget.checked;
              setLlm((l) => ({ ...l, fallbackLocal }));
            }}
          />
          <Alert color="yellow" icon={<IconShieldLock size={18} />} title="Las conversaciones salen de Atentina">
            {external.map((st) => (
              <div key={st.key}>
                Desde el turno {st.fromTurn}, este agente manda la conversación a {where(st)}.
              </div>
            ))}
            {last.connection === null && llm.stages.length > 1 && (
              <div>
                Desde el turno {last.fromTurn} vuelve a {LOCAL_LABEL}.
              </div>
            )}
          </Alert>
        </>
      )}
    </Stack>
  );
}
