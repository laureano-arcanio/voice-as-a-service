import { Alert, Anchor, Card, Center, Grid, List, Loader, Stack, Text, Title } from '@mantine/core';
import { IconAlertCircle, IconCheck } from '@tabler/icons-react';
import { useEffect, useRef, useState } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router';
import { errorMessage } from '@/api/errors';
import type { Billing, Plan } from '@/api/types';
import { PageHeader } from '@/components/PageHeader';
import { QueryState } from '@/components/QueryState';
import { useCurrentUser } from '@/features/auth/api';
import { formatArs } from '@/lib/format';
import { notifySuccess } from '@/lib/notify';
import { useBilling, useSubscribe } from './api';
import { hasFiscal, planFeatures } from './format';
import { type BrickController, mountCardBrick } from './mercadopago';
import { FiscalForm } from './parts';

const CONTAINER = 'card-payment-brick';

function CardBrick({ billing, clientId, plan }: { billing: Billing; clientId: string; plan: Plan }) {
  const me = useCurrentUser();
  const subscribe = useSubscribe(clientId);
  const navigate = useNavigate();
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<BrickController | null>(null);

  useEffect(() => {
    let cancelled = false;
    mountCardBrick({
      publicKey: billing.mp_public_key!,
      containerId: CONTAINER,
      amount: plan.price_ars,
      email: me.email,
      onReady: () => setReady(true),
      onError: (message) => setError(message),
      onSubmit: (data) =>
        new Promise<void>((resolve, reject) => {
          setError(null);
          subscribe.mutate(
            { tierId: plan.id, method: 'mercadopago', cardTokenId: data.token },
            {
              onSuccess: (b) => {
                resolve();
                notifySuccess(
                  b.subscription?.status === 'active'
                    ? `Pago aprobado. Ya estás en el plan ${plan.name}.`
                    : 'Estamos confirmando el pago con Mercado Pago.',
                );
                void navigate('/plan', { replace: true });
              },
              onError: (e) => {
                setError(errorMessage(e));
                reject(e);
              },
            },
          );
        }),
    })
      .then((c) => {
        if (cancelled) c.unmount();
        else controller.current = c;
      })
      .catch((e: Error) => setError(e.message));
    return () => {
      cancelled = true;
      controller.current?.unmount();
      controller.current = null;
    };
    // El brick se monta una vez por plan; las mutaciones usan el estado actual.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plan.id, billing.mp_public_key]);

  return (
    <Stack gap="sm">
      {!ready && !error && (
        <Center py="xl">
          <Loader size="sm" aria-label="Cargando el formulario de pago" />
        </Center>
      )}
      {error && (
        <Alert color="red" icon={<IconAlertCircle size={18} />} role="alert">
          {error}
        </Alert>
      )}
      <div id={CONTAINER} />
    </Stack>
  );
}

function CheckoutView({ billing, clientId, plan }: { billing: Billing; clientId: string; plan: Plan }) {
  const sub = billing.subscription;
  if (!billing.mp_public_key || (sub && sub.status !== 'pending' && sub.method === 'mercadopago')) {
    return <Navigate to="/plan" replace />;
  }
  return (
    <Grid gutter="md">
      <Grid.Col span={{ base: 12, md: 5 }}>
        <Card>
          <Title order={4} mb="xs">
            Plan {plan.name}
          </Title>
          <Text className="metric">{formatArs(plan.price_ars)}</Text>
          <Text size="xs" c="dimmed" mb="md">
            por mes, precio final
          </Text>
          <List size="sm" spacing={4} icon={<IconCheck size={16} />} center mb="md">
            {planFeatures(plan).map((f) => (
              <List.Item key={f}>{f}</List.Item>
            ))}
          </List>
          <Text size="sm" c="dimmed">
            Se cobra hoy y después cada mes, con débito automático de Mercado Pago. Lo das de baja cuando
            quieras desde Plan. ¿Preferís transferencia?{' '}
            <Anchor component={Link} to={`/plan?tier=${encodeURIComponent(plan.name)}`} size="sm">
              Pagar por transferencia
            </Anchor>
          </Text>
        </Card>
      </Grid.Col>
      <Grid.Col span={{ base: 12, md: 7 }}>
        <Card>
          {hasFiscal(billing) ? (
            <>
              <Title order={4} mb="sm">
                Datos de la tarjeta
              </Title>
              <CardBrick billing={billing} clientId={clientId} plan={plan} />
            </>
          ) : (
            <>
              <Title order={4} mb="xs">
                Datos para la factura
              </Title>
              <Text size="sm" c="dimmed" mb="sm">
                Antes de pagar, completá los datos para emitirte la factura.
              </Text>
              <FiscalForm billing={billing} clientId={clientId} submitLabel="Continuar" onSaved={() => {}} />
            </>
          )}
        </Card>
      </Grid.Col>
    </Grid>
  );
}

/** Pago de un plan con tarjeta (Card Payment Brick de Mercado Pago), en /plan/pagar?tier=<id>. Se abre con
 * navegacion completa: la CSP de esta ruta permite el SDK de MP. */
export function CheckoutPage() {
  const me = useCurrentUser();
  const billing = useBilling(me.client_id);
  const [params] = useSearchParams();
  const tierId = params.get('tier') ?? '';
  if (!me.client_id) return null;
  return (
    <QueryState query={billing}>
      {(b) => {
        const plan = b.plans.find((p) => p.id === tierId);
        if (!plan) return <Navigate to="/plan" replace />;
        return (
          <>
            <PageHeader
              title={`Pagar el plan ${plan.name}`}
              description="Débito automático con tarjeta de crédito o débito, por Mercado Pago."
            />
            <CheckoutView billing={b} clientId={me.client_id!} plan={plan} />
          </>
        );
      }}
    </QueryState>
  );
}
