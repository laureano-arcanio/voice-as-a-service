import { Badge, Button, Group, Select, Stack, Text, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import type { Billing, Subscription, TaxCondition } from '@/api/types';
import { CopyIcon } from '@/components/Copy';
import { formatArs } from '@/lib/format';
import { SUBSCRIPTION_STATUS, TAX_CONDITION } from '@/lib/labels';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useUpdateFiscal } from './api';

export function SubscriptionBadge({ sub }: { sub: Subscription }) {
  if (sub.status === 'active' && sub.cancel_at_period_end) return <Badge color="gray">Dado de baja</Badge>;
  const l = SUBSCRIPTION_STATUS[sub.status] ?? { label: sub.status, color: 'gray' };
  return <Badge color={l.color}>{l.label}</Badge>;
}

/** Datos para la transferencia y el monto, para copiar. */
export function BankDetails({ billing, amount }: { billing: Billing; amount: number }) {
  return (
    <Stack gap={6}>
      {billing.bank.map((row) => (
        <Group key={`${row.label}-${row.value}`} justify="space-between" wrap="nowrap" gap="xs">
          <Text size="xs" c="dimmed">
            {row.label}
          </Text>
          <Group gap={4} wrap="nowrap">
            <Text size="sm" fw={600} className="mono">
              {row.value}
            </Text>
            <CopyIcon value={row.value} />
          </Group>
        </Group>
      ))}
      <Group justify="space-between" wrap="nowrap">
        <Text size="xs" c="dimmed">
          Monto
        </Text>
        <Text size="sm" fw={600} className="mono">
          {formatArs(amount)}
        </Text>
      </Group>
      {billing.bank.length === 0 && (
        <Text size="sm" c="dimmed">
          Escribinos a {billing.support_email} y te pasamos los datos de la cuenta.
        </Text>
      )}
    </Stack>
  );
}

const TAX_OPTIONS = Object.entries(TAX_CONDITION).map(([value, label]) => ({ value, label }));

/** Datos para la factura. `onSaved` despues de guardar (para seguir con el pedido del plan). */
export function FiscalForm({
  billing,
  clientId,
  submitLabel = 'Guardar datos',
  onSaved,
}: {
  billing: Billing;
  clientId: string;
  submitLabel?: string;
  onSaved?: () => void;
}) {
  const save = useUpdateFiscal(clientId);
  const form = useForm<{ legal_name: string; tax_id: string; tax_condition: TaxCondition | '' }>({
    initialValues: {
      legal_name: billing.fiscal.legal_name,
      tax_id: billing.fiscal.tax_id,
      tax_condition: billing.fiscal.tax_condition,
    },
    validate: {
      legal_name: (v) => (v.trim() ? null : 'Poné la razón social o tu nombre'),
      tax_id: (v) => (v.replace(/\D/g, '').length === 11 ? null : 'El CUIT tiene 11 números'),
      tax_condition: (v) => (v ? null : 'Elegí la condición frente al IVA'),
    },
  });
  return (
    <form
      onSubmit={form.onSubmit((v) =>
        save.mutate(
          {
            legal_name: v.legal_name.trim(),
            tax_id: v.tax_id,
            tax_condition: v.tax_condition as TaxCondition,
          },
          {
            onSuccess: () => {
              if (onSaved) onSaved();
              else notifySuccess('Datos guardados.');
            },
            onError: (e) => notifyError(e, 'No se pudieron guardar los datos'),
          },
        ),
      )}
      noValidate
    >
      <Stack gap="sm">
        <TextInput label="Razón social o nombre" maxLength={128} {...form.getInputProps('legal_name')} />
        <TextInput label="CUIT" placeholder="20-12345678-9" {...form.getInputProps('tax_id')} />
        <Select
          label="Condición frente al IVA"
          data={TAX_OPTIONS}
          allowDeselect={false}
          {...form.getInputProps('tax_condition')}
        />
        <Group justify="flex-end">
          <Button type="submit" variant={onSaved ? 'filled' : 'default'} loading={save.isPending}>
            {submitLabel}
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
