import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import type { ClientLimits, LimitAdjustment, LimitField } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { EmptyState, QueryState } from '@/components/QueryState';
import { numberErrorTitle } from '@/features/numbers/errors';
import { formatDate, formatLimit, fromIsoDate } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useAddLimitAdjustment, useClientLimits, useDeleteLimitAdjustment } from './api';
import { endOfThisMonth, LIMIT_FIELDS, LIMIT_META } from './limits';

type Mode = 'add' | 'set';
type Validity = 'always' | 'month' | 'until';

const STATUS: Record<LimitAdjustment['status'], { label: string; color: string }> = {
  active: { label: 'Vigente', color: 'green' },
  scheduled: { label: 'Programado', color: 'blue' },
  expired: { label: 'Vencido', color: 'gray' },
};

const FIELD_OPTIONS = ['Llamadas', 'Minutos y números', 'API de inferencia'].map((group) => ({
  group,
  items: LIMIT_FIELDS.filter((f) => LIMIT_META[f].group === group).map((f) => ({
    value: f,
    label: LIMIT_META[f].label,
  })),
}));

/** "+10 min", "= 500 min" o "= Ilimitado". */
function adjustmentText(a: Pick<LimitAdjustment, 'field' | 'mode' | 'value'>): string {
  const unit = LIMIT_META[a.field].unit;
  return a.mode === 'add' ? `+${formatLimit(a.value, unit)}` : `= ${formatLimit(a.value, unit)}`;
}

function validityText(a: Pick<LimitAdjustment, 'starts_on' | 'ends_on'>): string {
  const fmt = (d: string) => formatDate(fromIsoDate(d)?.toISOString());
  if (a.starts_on && a.ends_on) return `${fmt(a.starts_on)} al ${fmt(a.ends_on)}`;
  if (a.starts_on) return `Desde el ${fmt(a.starts_on)}`;
  if (a.ends_on) return `Hasta el ${fmt(a.ends_on)}`;
  return 'Permanente';
}

/** Como queda el limite del cliente hoy con lo que se esta cargando (para el modal). */
function preview(row: ClientLimits['limits'][number] | undefined, mode: Mode, value: number | ''): string | null {
  if (!row) return null;
  const unit = LIMIT_META[row.field].unit;
  const now = `Hoy: ${formatLimit(row.effective, unit)}`;
  if (mode === 'set') return `${now} → ${formatLimit(value === '' ? null : value, unit)}`;
  if (row.effective == null) return `${now}. Ya es ilimitado: no hay nada que sumar.`;
  return value === '' ? now : `${now} → ${formatLimit(row.effective + value, unit)}`;
}

function AdjustmentModal({
  clientId,
  limits,
  onClose,
}: {
  clientId: string;
  limits: ClientLimits;
  onClose: () => void;
}) {
  const add = useAddLimitAdjustment(clientId);
  const [field, setField] = useState<LimitField>('inbound_minutes');
  const [mode, setMode] = useState<Mode>('add');
  const [value, setValue] = useState<number | ''>('');
  const [validity, setValidity] = useState<Validity>('always');
  const [until, setUntil] = useState('');
  const [note, setNote] = useState('');
  const row = limits.limits.find((l) => l.field === field);
  const unit = LIMIT_META[field].unit;
  const valid = (mode === 'set' || (value !== '' && value > 0)) && (validity !== 'until' || until !== '');
  const text = preview(row, mode, value);

  const submit = () =>
    add.mutate(
      {
        field,
        mode,
        value: value === '' ? null : value,
        ends_on: validity === 'month' ? endOfThisMonth() : validity === 'until' ? until : null,
        note: note.trim(),
      },
      {
        onSuccess: () => {
          notifySuccess('Ajuste cargado. Rige desde ya.');
          onClose();
        },
        onError: (e) => notifyError(e, numberErrorTitle(e)),
      },
    );

  return (
    <Modal opened onClose={onClose} title="Ajustar un límite del cliente">
      <Stack>
        <Select
          label="Límite"
          data={FIELD_OPTIONS}
          value={field}
          onChange={(v) => v && setField(v as LimitField)}
          allowDeselect={false}
        />
        <Select
          label="Tipo de ajuste"
          data={[
            { value: 'add', label: 'Sumar al tier (ej. 10 minutos más)' },
            { value: 'set', label: 'Reemplazar el límite del tier' },
          ]}
          value={mode}
          onChange={(v) => v && setMode(v as Mode)}
          allowDeselect={false}
        />
        <NumberInput
          label={mode === 'add' ? `Cantidad a sumar${unit ? ` (${unit.trim()})` : ''}` : 'Nuevo límite'}
          placeholder={mode === 'set' ? 'Ilimitado' : undefined}
          description={mode === 'set' ? 'Vacío = ilimitado.' : undefined}
          min={mode === 'add' ? 1 : 0}
          allowDecimal={false}
          allowNegative={false}
          thousandSeparator="."
          decimalSeparator=","
          value={value}
          onChange={(v) => setValue(typeof v === 'number' ? v : '')}
          data-autofocus
        />
        <Select
          label="Vigencia"
          data={[
            { value: 'always', label: 'Permanente' },
            { value: 'month', label: 'Solo este mes' },
            { value: 'until', label: 'Hasta una fecha' },
          ]}
          value={validity}
          onChange={(v) => v && setValidity(v as Validity)}
          allowDeselect={false}
        />
        {validity === 'until' && (
          <TextInput
            type="date"
            label="Último día"
            value={until}
            onChange={(e) => setUntil(e.currentTarget.value)}
          />
        )}
        <TextInput
          label="Motivo"
          description="Opcional: queda en el registro del cliente."
          maxLength={255}
          value={note}
          onChange={(e) => setNote(e.currentTarget.value)}
        />
        {text && (
          <Text size="sm" c="dimmed" aria-live="polite">
            {text}
          </Text>
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancelar
          </Button>
          <Button disabled={!valid} loading={add.isPending} onClick={submit}>
            Cargar ajuste
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

/** Ajustes de limites de un cliente sobre su tier (solo admin): mas minutos, una linea mas, un tope propio. */
export function LimitAdjustmentsCard({ clientId }: { clientId: string }) {
  const limits = useClientLimits(clientId);
  const del = useDeleteLimitAdjustment(clientId);
  const [creating, setCreating] = useState(false);

  const remove = async (a: LimitAdjustment) => {
    const ok = await confirmAction({
      title: 'Quitar ajuste',
      message: `Se quita ${adjustmentText(a)} en "${LIMIT_META[a.field].label}": el cliente vuelve al límite de su tier.`,
      confirmLabel: 'Quitar',
      danger: true,
    });
    if (!ok) return;
    del.mutate(a.id, {
      onSuccess: () => notifySuccess('Ajuste quitado.'),
      onError: (e) => notifyError(e, numberErrorTitle(e)),
    });
  };

  return (
    <Card>
      <Group justify="space-between" mb="xs">
        <Title order={4}>Ajustes de límites</Title>
        <Button
          size="xs"
          leftSection={<IconPlus size={16} />}
          onClick={() => setCreating(true)}
          disabled={!limits.data}
        >
          Nuevo ajuste
        </Button>
      </Group>
      <Text size="sm" c="dimmed" mb="sm">
        Cambian los límites de este cliente sin tocar su tier ni a los demás clientes. Se suman o reemplazan
        el valor del tier y rigen desde ya.
      </Text>
      <QueryState query={limits}>
        {(data) =>
          data.adjustments.length === 0 ? (
            <EmptyState>Sin ajustes: rigen los límites del tier {data.tier_name}.</EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={420}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Límite</Table.Th>
                    <Table.Th ta="right">Ajuste</Table.Th>
                    <Table.Th>Vigencia</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.adjustments.map((a) => (
                    <Table.Tr key={a.id} style={a.status === 'expired' ? { opacity: 0.6 } : undefined}>
                      <Table.Td>
                        <Text size="sm">{LIMIT_META[a.field].label}</Text>
                        {a.note && (
                          <Text size="xs" c="dimmed">
                            {a.note}
                          </Text>
                        )}
                      </Table.Td>
                      <Table.Td ta="right" style={{ whiteSpace: 'nowrap' }} className="mono">
                        {adjustmentText(a)}
                      </Table.Td>
                      <Table.Td>
                        <Group gap={6} wrap="nowrap">
                          <Badge color={STATUS[a.status].color}>{STATUS[a.status].label}</Badge>
                          <Text size="xs" c="dimmed">
                            {validityText(a)}
                          </Text>
                        </Group>
                      </Table.Td>
                      <Table.Td>
                        <Tooltip label="Quitar">
                          <ActionIcon
                            variant="subtle"
                            color="red"
                            onClick={() => void remove(a)}
                            aria-label={`Quitar ajuste de ${LIMIT_META[a.field].label}`}
                          >
                            <IconTrash size={16} />
                          </ActionIcon>
                        </Tooltip>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )
        }
      </QueryState>
      {creating && limits.data && (
        <AdjustmentModal clientId={clientId} limits={limits.data} onClose={() => setCreating(false)} />
      )}
    </Card>
  );
}
