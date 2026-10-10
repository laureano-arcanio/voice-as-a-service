import {
  Badge,
  Button,
  Card,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { DateInput } from '@mantine/dates';
import { useForm } from '@mantine/form';
import { useDisclosure } from '@mantine/hooks';
import type { Billing } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { QueryState } from '@/components/QueryState';
import { useTiers } from '@/features/tiers/api';
import { formatArs, toIsoDate } from '@/lib/format';
import { PAYMENT_METHOD, TAX_CONDITION } from '@/lib/labels';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useBilling, useRecordPayment, useSuspendPlan } from './api';
import { formatDay } from './format';
import { SubscriptionBadge } from './parts';

function PaymentModal({
  billing,
  clientId,
  onClose,
}: {
  billing: Billing;
  clientId: string;
  onClose: () => void;
}) {
  const tiers = useTiers();
  const record = useRecordPayment(clientId);
  const sub = billing.subscription;
  const initialTier = sub?.pending_tier?.id ?? sub?.tier.id ?? '';
  const priceOf = (id: string) => tiers.data?.find((t) => t.id === id)?.price_ars ?? '';
  const form = useForm<{ tier_id: string; amount_ars: number | ''; paid_on: string | null; note: string }>({
    initialValues: {
      tier_id: initialTier,
      amount_ars: sub?.amount_due ?? '',
      paid_on: toIsoDate(new Date()),
      note: '',
    },
    validate: {
      tier_id: (v) => (v ? null : 'Elegí el plan'),
      amount_ars: (v) => (v === '' ? 'Poné el monto' : null),
      paid_on: (v) => (v ? null : 'Poné la fecha'),
    },
  });
  const sellable = (tiers.data ?? []).filter((t) => t.price_ars);
  return (
    <Modal opened onClose={onClose} title="Registrar pago por transferencia">
      <form
        onSubmit={form.onSubmit((v) =>
          record.mutate(
            {
              tier_id: v.tier_id,
              amount_ars: Number(v.amount_ars),
              paid_on: v.paid_on!,
              note: v.note.trim(),
            },
            {
              onSuccess: (b) => {
                notifySuccess(
                  `Pago registrado. Plan activo hasta el ${formatDay(b.subscription?.current_period_end)}.`,
                );
                onClose();
              },
              onError: (e) => notifyError(e, 'No se pudo registrar el pago'),
            },
          ),
        )}
      >
        <Stack gap="sm">
          <Text size="sm" c="dimmed">
            Activa el plan, o lo renueva, por un mes desde el vencimiento actual (o desde hoy). Al cliente le
            llega un mail.
          </Text>
          <Select
            label="Tier"
            data={sellable.map((t) => ({ value: t.id, label: `${t.name} · ${formatArs(t.price_ars)}` }))}
            allowDeselect={false}
            {...form.getInputProps('tier_id')}
            onChange={(v) => {
              form.setFieldValue('tier_id', v ?? '');
              if (v) form.setFieldValue('amount_ars', priceOf(v));
            }}
          />
          <NumberInput
            label="Monto ($)"
            min={0}
            allowDecimal={false}
            thousandSeparator="."
            decimalSeparator=","
            {...form.getInputProps('amount_ars')}
          />
          <DateInput
            label="Fecha del pago"
            valueFormat="DD/MM/YYYY"
            maxDate={toIsoDate(new Date())}
            {...form.getInputProps('paid_on')}
          />
          <TextInput
            label="Nota"
            placeholder="Banco, nº de operación"
            maxLength={255}
            {...form.getInputProps('note')}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={record.isPending}>
              Registrar pago
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

function SubscriptionView({ billing, clientId }: { billing: Billing; clientId: string }) {
  const [paying, pay] = useDisclosure(false);
  const suspend = useSuspendPlan(clientId);
  const sub = billing.subscription;
  const f = billing.fiscal;

  const doSuspend = async () => {
    if (!sub) return;
    const pending = sub.status === 'pending';
    if (
      !(await confirmAction({
        title: pending ? 'Rechazar el pedido' : 'Pasar al gratuito',
        message: pending
          ? `Se cancela el pedido del tier ${sub.tier.name}. El cliente sigue en ${billing.tier.name}.`
          : `El cliente pasa ya al tier gratuito. Los números que no entran quedan suspendidos.`,
        confirmLabel: pending ? 'Rechazar' : 'Pasar al gratuito',
        danger: true,
      }))
    )
      return;
    suspend.mutate(undefined, {
      onSuccess: () => notifySuccess(pending ? 'Pedido rechazado.' : 'Cliente pasado al gratuito.'),
      onError: (e) => notifyError(e),
    });
  };

  return (
    <Stack gap="sm">
      {sub ? (
        <>
          <Group gap="xs">
            <SubscriptionBadge sub={sub} />
            <Badge color="gray">{PAYMENT_METHOD[sub.method] ?? sub.method}</Badge>
          </Group>
          <Text size="sm">
            {sub.status === 'pending'
              ? `Pidió ${sub.tier.name} (${formatArs(sub.amount_due)}). Esperando el comprobante.`
              : `${sub.tier.name}, pago hasta el ${formatDay(sub.current_period_end)}${sub.grace_until ? `, gracia hasta el ${formatDay(sub.grace_until)}` : ''}.`}
          </Text>
          {sub.pending_tier && sub.status !== 'pending' && (
            <Text size="sm" c="dimmed">
              Pidió pasar a {sub.pending_tier.name} con el próximo pago ({formatArs(sub.amount_due)}).
            </Text>
          )}
        </>
      ) : (
        <Text size="sm" c="dimmed">
          Sin plan pago. Tier actual: {billing.tier.name}.
        </Text>
      )}
      {billing.suspended_numbers.length > 0 && (
        <Text size="sm" c="yellow">
          Números suspendidos: <span className="mono">{billing.suspended_numbers.join(', ')}</span>
        </Text>
      )}
      <Stack gap={2}>
        <Text size="xs" c="dimmed">
          Factura
        </Text>
        <Text size="sm" fw={600}>
          {f.legal_name
            ? `${f.legal_name} · CUIT ${f.tax_id} · ${TAX_CONDITION[f.tax_condition] ?? ''}`
            : '–'}
        </Text>
      </Stack>
      <Group justify="flex-end" gap="xs">
        {sub && (
          <Button variant="subtle" color="red" onClick={() => void doSuspend()} loading={suspend.isPending}>
            {sub.status === 'pending' ? 'Rechazar pedido' : 'Pasar al gratuito'}
          </Button>
        )}
        <Button variant="default" onClick={pay.open}>
          Registrar pago
        </Button>
      </Group>
      {paying && <PaymentModal billing={billing} clientId={clientId} onClose={pay.close} />}
    </Stack>
  );
}

/** Ficha del cliente (admin): plan pago, registrar transferencias y pasar al gratuito. */
export function SubscriptionCard({ clientId }: { clientId: string }) {
  const billing = useBilling(clientId);
  return (
    <Card>
      <Title order={4} mb="sm">
        Plan pago
      </Title>
      <QueryState query={billing}>{(b) => <SubscriptionView billing={b} clientId={clientId} />}</QueryState>
    </Card>
  );
}
