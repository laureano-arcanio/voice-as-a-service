import {
  Alert,
  Autocomplete,
  Button,
  Card,
  Group,
  Modal,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  TagsInput,
  Text,
} from '@mantine/core';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { ApiError, errorMessage } from '@/api/errors';
import type { AgentDetail, LlmConnection } from '@/api/types';
import { useLlmConnections, useLlmModels, useOpenRouterProviders } from '@/features/llm/api';
import { connectionLabel, LOCAL_LABEL } from '@/features/llm/labels';
import { notifyError, notifyInfo } from '@/lib/notify';
import { isRunInProgress, testKeys, useCreateRun, useTestCases } from './api';

const LOCAL = 'local';
const MAX_MODELS = 3;
const MAX_TURNS = 300;
const REPETITIONS = ['5', '10'];

type Row = { connection_id: string | null; model: string; providers: string[] };

const blankRow = (): Row => ({ connection_id: null, model: '', providers: [] });

/** Una fila del modal: la conexión (o el LLM de Atentina), su modelo y, en OpenRouter, los proveedores. */
function RowEditor({
  index,
  row,
  clientId,
  connections,
  onChange,
  onRemove,
}: {
  index: number;
  row: Row;
  clientId: string;
  connections: LlmConnection[];
  onChange: (patch: Partial<Row>) => void;
  onRemove: (() => void) | null;
}) {
  const list = connections;
  const known = list.find((c) => c.id === row.connection_id);
  const kind = known?.kind;
  const models = useLlmModels(clientId, known ? known.id : null);
  // El catálogo público de proveedores: solo en una conexión OpenRouter con modelo.
  const catalog = useOpenRouterProviders(kind === 'openrouter' ? row.model.trim() : '');
  const notFound = catalog.error instanceof ApiError && catalog.error.code === 'model_not_found';
  const options = [
    { value: LOCAL, label: LOCAL_LABEL },
    ...list.map((c) => ({ value: c.id, label: connectionLabel(c) })),
  ];

  const pick = (value: string | null) => {
    if (!value || value === LOCAL) return onChange({ connection_id: null, model: '', providers: [] });
    const connection = list.find((c) => c.id === value);
    onChange({
      connection_id: value,
      model: row.model || connection?.default_model || '',
      // El enrutado por proveedores es solo de OpenRouter: al cambiar de conexión no se arrastra.
      ...(connection?.kind !== 'openrouter' ? { providers: [] } : {}),
    });
  };

  return (
    <Card withBorder p="sm" data-testid={`model-row-${index}`}>
      <Stack gap="xs">
        <Group justify="space-between" gap="sm">
          <Text size="sm" fw={600}>
            Modelo {index + 1}
          </Text>
          {onRemove && (
            <Button
              size="compact-xs"
              variant="subtle"
              color="red"
              leftSection={<IconTrash size={14} />}
              onClick={onRemove}
              aria-label={`Quitar modelo ${index + 1}`}
            >
              Quitar
            </Button>
          )}
        </Group>
        <Group align="flex-end" wrap="wrap" gap="sm">
          <Select
            label="Contesta"
            data={options}
            value={row.connection_id ?? LOCAL}
            onChange={pick}
            allowDeselect={false}
            style={{ flex: '1 1 220px' }}
          />
          {known && (
            <Autocomplete
              label="Modelo del proveedor"
              placeholder={known.default_model || 'nombre del modelo'}
              data={models.data ?? []}
              value={row.model}
              onChange={(model) => onChange({ model })}
              limit={50}
              style={{ flex: '1 1 220px' }}
            />
          )}
        </Group>
        {known && models.isError && (
          <Text size="xs" c="dimmed">
            No se pudo leer la lista de modelos del proveedor: escribí el nombre a mano.
          </Text>
        )}
        {known?.last_test_ok === false && (
          <Text size="xs" c="orange.8">
            La última prueba de la conexión falló
            {known.last_test_detail ? `: ${known.last_test_detail}` : ''}
          </Text>
        )}
        {notFound && (
          <Text size="xs" c="orange.8">
            El modelo no existe en OpenRouter.
          </Text>
        )}
        {kind === 'openrouter' && (
          <TagsInput
            label="Proveedores de OpenRouter"
            description="Opcional: quiénes atienden esta variante. Sin tags, elige OpenRouter."
            placeholder="p. ej. nebius/fp4"
            data={catalog.data?.map((p) => p.tag) ?? []}
            value={row.providers}
            onChange={(providers) => onChange({ providers })}
            maxTags={10}
            clearable
          />
        )}
      </Stack>
    </Card>
  );
}

/** «Probar con otros modelos»: corre la publicada con cada modelo, sin respaldo y sin guardar (T5, T6). */
export function ModelRunModal({
  agent,
  opened,
  onClose,
}: {
  agent: AgentDetail;
  opened: boolean;
  onClose: () => void;
}) {
  const connections = useLlmConnections(agent.client_id);
  const cases = useTestCases(agent.id);
  const createRun = useCreateRun(agent.id);
  const qc = useQueryClient();
  const [rows, setRows] = useState<Row[]>([blankRow()]);
  const [repetitions, setRepetitions] = useState(5);
  const [withoutFallback, setWithoutFallback] = useState(false);

  const caseCount = cases.data?.length ?? 0;
  const variants = 1 + rows.length;
  const total = caseCount * variants * repetitions;
  const missingModel = rows.some((r) => r.connection_id && !r.model.trim());
  const over = total > MAX_TURNS;
  const canRun = !createRun.isPending && !missingModel && !over && caseCount > 0;

  const update = (index: number, patch: Partial<Row>) =>
    setRows((prev) => prev.map((row, n) => (n === index ? { ...row, ...patch } : row)));

  const run = () => {
    createRun.mutate(
      {
        repetitions,
        models: rows.map((r) =>
          r.connection_id
            ? {
                connection_id: r.connection_id,
                model: r.model.trim(),
                ...(r.providers.length ? { providers: r.providers } : {}),
              }
            : { connection_id: null },
        ),
        published_fallback: !withoutFallback,
      },
      {
        onSuccess: () => onClose(),
        onError: (e) => {
          if (!isRunInProgress(e)) return notifyError(e, 'No se pudo correr');
          // La corrida activa se ve en «Última corrida»: se refresca la última y se cierra el modal.
          void qc.invalidateQueries({ queryKey: testKeys.runs(agent.id) });
          notifyInfo('Ya hay una corrida de pruebas en curso: seguí su avance en «Última corrida».');
          onClose();
        },
      },
    );
  };

  return (
    <Modal opened={opened} onClose={onClose} size="lg" title="Probar con otros modelos">
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          Corre la versión publicada con cada modelo, al lado de la publicada y sin guardar nada. Estas variantes van
          sin el respaldo de Atentina: si el proveedor falla, la repetición falla.
        </Text>
        {rows.map((row, index) => (
          <RowEditor
            key={index}
            index={index}
            row={row}
            clientId={agent.client_id}
            connections={connections.data ?? []}
            onChange={(patch) => update(index, patch)}
            onRemove={rows.length > 1 ? () => setRows((prev) => prev.filter((_, n) => n !== index)) : null}
          />
        ))}
        <Group justify="space-between" wrap="wrap" gap="sm">
          <Button
            variant="default"
            size="xs"
            leftSection={<IconPlus size={16} />}
            onClick={() => setRows((prev) => [...prev, blankRow()])}
            disabled={rows.length >= MAX_MODELS}
          >
            Agregar modelo
          </Button>
          <Text size="xs" c={over ? 'red.7' : 'dimmed'}>
            {total} turnos de {MAX_TURNS} ({caseCount} casos × {variants} variantes × {repetitions} repeticiones)
          </Text>
        </Group>
        <Group gap="xl" wrap="wrap">
          <div>
            <Text size="xs" fw={600} mb={4}>
              Repeticiones
            </Text>
            <SegmentedControl
              value={String(repetitions)}
              onChange={(value) => setRepetitions(Number(value))}
              data={REPETITIONS.map((value) => ({ value, label: `${value}×` }))}
            />
          </div>
          <Switch
            label="Publicada sin respaldo"
            checked={withoutFallback}
            onChange={(e) => setWithoutFallback(e.currentTarget.checked)}
            mt="lg"
          />
        </Group>
        {missingModel && (
          <Text size="xs" c="red.7">
            Elegí el modelo de cada conexión.
          </Text>
        )}
        {over && (
          <Text size="xs" c="red.7">
            Con otros modelos son hasta {MAX_TURNS} turnos por corrida: bajá las repeticiones o los modelos.
          </Text>
        )}
        {connections.isError && <Alert color="red">{errorMessage(connections.error)}</Alert>}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={run} disabled={!canRun} loading={createRun.isPending}>
            Correr
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
