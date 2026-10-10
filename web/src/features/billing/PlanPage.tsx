import {
  Alert,
  Box,
  Button,
  Card,
  Divider,
  Group,
  List,
  Modal,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { IconAlertTriangle, IconCheck, IconInfoCircle } from '@tabler/icons-react';
import { useState } from 'react';
import { useSearchParams } from 'react-router';
import type { Billing, Plan } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useCurrentUser } from '@/features/auth/api';
import { formatArs } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useBilling, useCancelPlan, useSubscribe } from './api';
import { formatDay, hasFiscal, planFeatures } from './format';
import { BankDetails, FiscalForm, SubscriptionBadge } from './parts';

/** Pedido de un plan: datos para la factura (si faltan) y despues los datos de la transferencia. */
function SubscribeModal({
  billing,
  clientId,
  plan,
  onClose,
}: {
  billing: Billing;
  clientId: string;
  plan: Plan;
  onClose: () => void;
}) {
  const subscribe = useSubscribe(clientId);
  const [step, setStep] = useState<'fiscal' | 'confirm' | 'done'>(hasFiscal(billing) ? 'confirm' : 'fiscal');
  const active = billing.subscription?.status === 'active' || billing.subscription?.status === 'past_due';

  const confirm = () =>
    subscribe.mutate(plan.id, {
      onSuccess: () => setStep('done'),
      onError: (e) => notifyError(e, 'No se pudo pedir el plan'),
    });

  return (
    <Modal opened onClose={onClose} title={`Plan ${plan.name}`}>
      {step === 'fiscal' && (
        <Stack gap="sm">
          <Text size="sm">Para emitirte la factura necesitamos estos datos.</Text>
          <FiscalForm
            billing={billing}
            clientId={clientId}
            submitLabel="Continuar"
            onSaved={() => setStep('confirm')}
          />
        </Stack>
      )}
      {step === 'confirm' && (
        <Stack gap="md">
          <Text size="sm">
            {active
              ? `Pasás al plan ${plan.name} con tu próximo pago, de ${formatArs(plan.price_ars)} por mes.`
              : `El plan ${plan.name} cuesta ${formatArs(plan.price_ars)} por mes. Se paga por transferencia y lo activamos cuando confirmamos el pago.`}
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button onClick={confirm} loading={subscribe.isPending}>
              Pedir el plan
            </Button>
          </Group>
        </Stack>
      )}
      {step === 'done' && (
        <Stack gap="md">
          <Alert color="green" icon={<IconCheck size={18} />}>
            Pedido registrado. También te mandamos estos datos por mail.
          </Alert>
          <Text size="sm">Transferí el monto a esta cuenta:</Text>
          <BankDetails billing={subscribe.data ?? billing} amount={plan.price_ars} />
          <Text size="sm">
            Después mandá el comprobante a <b>{billing.support_email}</b>.{' '}
            {active ? 'El cambio se aplica con ese pago.' : 'Activamos el plan apenas confirmamos el pago.'}
          </Text>
          <Group justify="flex-end">
            <Button onClick={onClose}>Listo</Button>
          </Group>
        </Stack>
      )}
    </Modal>
  );
}

function CurrentPlanCard({ billing, clientId }: { billing: Billing; clientId: string }) {
  const cancel = useCancelPlan(clientId);
  const sub = billing.subscription;
  const isPaid = sub && sub.status !== 'pending';

  const doCancel = async () => {
    if (!sub) return;
    const pending = sub.status === 'pending';
    if (
      !(await confirmAction({
        title: pending ? 'Cancelar el pedido' : 'Dar de baja el plan',
        message: pending
          ? `Se cancela el pedido del plan ${sub.tier.name}. Si ya transferiste, escribinos a ${billing.support_email}.`
          : sub.status === 'past_due'
            ? 'La cuenta pasa al plan gratuito ahora.'
            : `El plan ${sub.tier.name} sigue hasta el ${formatDay(sub.current_period_end)}; después la cuenta pasa al plan gratuito.`,
        confirmLabel: pending ? 'Cancelar el pedido' : 'Dar de baja',
        danger: true,
      }))
    )
      return;
    cancel.mutate(undefined, {
      onSuccess: () => notifySuccess(pending ? 'Pedido cancelado.' : 'Plan dado de baja.'),
      onError: (e) => notifyError(e),
    });
  };

  return (
    <Card>
      <Group justify="space-between" mb="sm">
        <Title order={4}>Tu plan</Title>
        {sub && isPaid && <SubscriptionBadge sub={sub} />}
      </Group>
      <Group align="baseline" gap="xs">
        <Text className="metric">{billing.tier.name}</Text>
        <Text size="sm" c="dimmed">
          {billing.tier_price_ars ? `${formatArs(billing.tier_price_ars)} por mes` : 'Gratis'}
        </Text>
      </Group>
      {sub && isPaid && (
        <Stack gap={4} mt="sm">
          <Text size="sm">
            {sub.status === 'past_due'
              ? `Venció el ${formatDay(sub.current_period_end)} y no registramos el pago. Sigue activo hasta el ${formatDay(sub.grace_until)}; después pasa al plan gratuito.`
              : sub.cancel_at_period_end
                ? `Dado de baja: sigue hasta el ${formatDay(sub.current_period_end)} y después pasa al plan gratuito.`
                : `Pago hasta el ${formatDay(sub.current_period_end)}. Para renovarlo, transferí ${formatArs(sub.amount_due)} antes de esa fecha.`}
          </Text>
          {sub.pending_tier && (
            <Text size="sm" c="dimmed">
              Con el próximo pago pasás al plan {sub.pending_tier.name}.
            </Text>
          )}
        </Stack>
      )}
      {sub?.status === 'pending' && (
        <Alert
          color="yellow"
          icon={<IconInfoCircle size={18} />}
          mt="md"
          title={`Pediste el plan ${sub.tier.name}`}
        >
          <Stack gap="sm">
            <Text size="sm">
              Lo activamos cuando confirmamos la transferencia. Mandá el comprobante a {billing.support_email}
              .
            </Text>
            <BankDetails billing={billing} amount={sub.amount_due} />
          </Stack>
        </Alert>
      )}
      {(sub?.status === 'past_due' || (sub?.status === 'active' && !sub.cancel_at_period_end)) && (
        <Box mt="md">
          <Divider mb="sm" label="Datos para la transferencia" labelPosition="left" />
          <BankDetails billing={billing} amount={sub.amount_due} />
        </Box>
      )}
      {sub && !(sub.status === 'active' && sub.cancel_at_period_end) && (
        <Group justify="flex-end" mt="md">
          <Button variant="subtle" color="red" onClick={() => void doCancel()} loading={cancel.isPending}>
            {sub.status === 'pending' ? 'Cancelar el pedido' : 'Dar de baja el plan'}
          </Button>
        </Group>
      )}
    </Card>
  );
}

function PlansCard({ billing, onPick }: { billing: Billing; onPick: (p: Plan) => void }) {
  const sub = billing.subscription;
  const current = sub && sub.status !== 'pending' ? sub.tier.id : billing.tier.id;
  const requested = sub?.status === 'pending' ? sub.tier.id : sub?.pending_tier?.id;
  return (
    <Card>
      <Title order={4} mb="xs">
        Planes
      </Title>
      <Text size="sm" c="dimmed" mb="md">
        Precio final por mes, en pesos. Sin permanencia: los minutos no se acumulan de un mes a otro.
      </Text>
      {billing.plans.length === 0 ? (
        <EmptyState>
          Por ahora no hay planes para contratar desde acá. Escribinos a {billing.support_email}.
        </EmptyState>
      ) : (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
          {billing.plans.map((p) => {
            const isCurrent = p.id === current && !!sub && sub.status !== 'pending';
            const isRequested = p.id === requested;
            return (
              <Stack key={p.id} className="plan-option" data-current={isCurrent || undefined} gap="sm">
                <div>
                  <Text fw={700}>{p.name}</Text>
                  <Text className="metric">{formatArs(p.price_ars)}</Text>
                  <Text size="xs" c="dimmed">
                    por mes
                  </Text>
                </div>
                {p.description && <Text size="sm">{p.description}</Text>}
                <List size="sm" spacing={4} icon={<IconCheck size={16} />} center>
                  {planFeatures(p).map((f) => (
                    <List.Item key={f}>{f}</List.Item>
                  ))}
                </List>
                <Button
                  mt="auto"
                  variant={isCurrent || isRequested ? 'default' : 'filled'}
                  disabled={isCurrent || isRequested}
                  onClick={() => onPick(p)}
                >
                  {isCurrent ? 'Tu plan actual' : isRequested ? 'Pedido' : 'Elegir este plan'}
                </Button>
              </Stack>
            );
          })}
        </SimpleGrid>
      )}
    </Card>
  );
}

function PaymentsCard({ billing }: { billing: Billing }) {
  return (
    <Card>
      <Title order={4} mb="sm">
        Pagos
      </Title>
      {billing.payments.length === 0 ? (
        <EmptyState>Todavía no hay pagos registrados.</EmptyState>
      ) : (
        <Table.ScrollContainer minWidth={420}>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Fecha</Table.Th>
                <Table.Th>Plan</Table.Th>
                <Table.Th>Cubre hasta</Table.Th>
                <Table.Th ta="right">Monto</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {billing.payments.map((p) => (
                <Table.Tr key={p.id}>
                  <Table.Td>{formatDay(p.paid_on)}</Table.Td>
                  <Table.Td>{p.tier_name ?? '–'}</Table.Td>
                  <Table.Td>{formatDay(p.period_end)}</Table.Td>
                  <Table.Td ta="right" className="mono">
                    {formatArs(p.amount_ars)}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Card>
  );
}

function PlanView({ billing, clientId }: { billing: Billing; clientId: string }) {
  const [params, setParams] = useSearchParams();
  // La landing manda a /plan?tier=<nombre> despues del registro: abre ese plan.
  const wanted = params.get('tier')?.toLowerCase();
  const initial = wanted
    ? billing.plans.find((p) => p.name.toLowerCase() === wanted || p.id === wanted)
    : undefined;
  const [picked, setPicked] = useState<Plan | null>(initial ?? null);
  const close = () => {
    setPicked(null);
    if (params.has('tier')) setParams({}, { replace: true });
  };

  return (
    <Stack gap="md">
      {billing.suspended_numbers.length > 0 && (
        <Alert color="yellow" icon={<IconAlertTriangle size={18} />} title="Números sin atender">
          Tu plan no incluye {billing.suspended_numbers.join(', ')}. Están reservados por un tiempo: elegí un
          plan con más números para recuperarlos.
        </Alert>
      )}
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <CurrentPlanCard billing={billing} clientId={clientId} />
        <Card>
          <Title order={4} mb="sm">
            Datos para la factura
          </Title>
          <FiscalForm key={JSON.stringify(billing.fiscal)} billing={billing} clientId={clientId} />
        </Card>
      </SimpleGrid>
      <PlansCard billing={billing} onPick={setPicked} />
      <PaymentsCard billing={billing} />
      {picked && <SubscribeModal billing={billing} clientId={clientId} plan={picked} onClose={close} />}
    </Stack>
  );
}

/** Plan y pago del cliente: plan actual, planes para contratar, datos de factura y pagos. */
export function PlanPage() {
  const me = useCurrentUser();
  const billing = useBilling(me.client_id);
  if (!me.client_id) return null;
  return (
    <>
      <PageHeader title="Plan" description="Tu plan, cómo pagarlo y los pagos registrados." />
      <QueryState query={billing}>{(b) => <PlanView billing={b} clientId={me.client_id!} />}</QueryState>
    </>
  );
}
