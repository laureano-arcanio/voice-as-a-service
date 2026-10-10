import {
  Alert,
  Anchor,
  Box,
  Button,
  Card,
  Center,
  Grid,
  Group,
  Input,
  List,
  Loader,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconAlertCircle, IconCheck } from '@tabler/icons-react';
import { useEffect, useState } from 'react';
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
import { type CardForm, type FieldName, mountCardForm } from './mercadopago';
import { FiscalForm } from './parts';

const CONTAINERS: Record<FieldName, string> = {
  cardNumber: 'mp-card-number',
  expirationDate: 'mp-card-expiry',
  securityCode: 'mp-card-cvv',
};

/** Contenedor de un campo seguro de MP (iframe) con el aspecto de un input de Mantine (`.mp-secure`). */
function SecureField({ label, name, focused }: { label: string; name: FieldName; focused: boolean }) {
  return (
    <Input.Wrapper label={label}>
      <div id={CONTAINERS[name]} className="mp-secure" data-focused={focused || undefined} />
    </Input.Wrapper>
  );
}

function CardFields({ billing, clientId, plan }: { billing: Billing; clientId: string; plan: Plan }) {
  const subscribe = useSubscribe(clientId);
  const navigate = useNavigate();
  const [card, setCard] = useState<CardForm | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [paying, setPaying] = useState(false);
  const [focused, setFocused] = useState<FieldName | null>(null);
  const form = useForm({
    initialValues: { holder: '', docType: 'DNI', docNumber: '' },
    validate: {
      holder: (v) => (v.trim() ? null : 'Poné el nombre como figura en la tarjeta'),
      docNumber: (v) => (v.replace(/\D/g, '') ? null : 'Poné el número de documento'),
    },
  });

  useEffect(() => {
    let cancelled = false;
    let mounted: CardForm | null = null;
    mountCardForm({
      publicKey: billing.mp_public_key!,
      containers: CONTAINERS,
      onFocus: (field, isFocused) => setFocused(isFocused ? field : null),
    })
      .then((c) => {
        mounted = c;
        if (cancelled) c.unmount();
        else setCard(c);
      })
      .catch((e: Error) => setError(e.message));
    return () => {
      cancelled = true;
      mounted?.unmount();
    };
  }, [billing.mp_public_key]);

  const pay = form.onSubmit(async (v) => {
    if (!card) return;
    setError(null);
    setPaying(true);
    try {
      const token = await card.createToken(v.holder.trim(), v.docType, v.docNumber.replace(/\D/g, ''));
      const b = await subscribe.mutateAsync({ tierId: plan.id, method: 'mercadopago', cardTokenId: token });
      notifySuccess(
        b.subscription?.status === 'active'
          ? `Pago aprobado. Ya estás en el plan ${plan.name}.`
          : 'Estamos confirmando el pago con Mercado Pago.',
      );
      void navigate('/plan', { replace: true });
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setPaying(false);
    }
  });

  return (
    <form onSubmit={pay} noValidate>
      <Stack gap="sm">
        {!card && !error && (
          <Center py="md">
            <Loader size="sm" aria-label="Cargando el formulario de pago" />
          </Center>
        )}
        {/* Visible desde antes de montar: los iframes de MP se traban si su contenedor no se ve. */}
        <Box>
          <Stack gap="sm">
            <SecureField label="Número de tarjeta" name="cardNumber" focused={focused === 'cardNumber'} />
            <SimpleGrid cols={2}>
              <SecureField label="Vencimiento" name="expirationDate" focused={focused === 'expirationDate'} />
              <SecureField
                label="Código de seguridad"
                name="securityCode"
                focused={focused === 'securityCode'}
              />
            </SimpleGrid>
            <TextInput
              label="Nombre del titular, como figura en la tarjeta"
              placeholder="María López"
              autoComplete="cc-name"
              {...form.getInputProps('holder')}
            />
            <Group gap="xs" align="flex-start" grow preventGrowOverflow={false}>
              <Select
                label="Documento"
                data={(card?.identificationTypes ?? [{ id: 'DNI', name: 'DNI' }]).map((t) => ({
                  value: t.id,
                  label: t.name,
                }))}
                allowDeselect={false}
                maw={120}
                {...form.getInputProps('docType')}
              />
              <TextInput
                label="Número"
                placeholder="30123456"
                inputMode="numeric"
                {...form.getInputProps('docNumber')}
              />
            </Group>
          </Stack>
        </Box>
        {error && (
          <Alert color="red" icon={<IconAlertCircle size={18} />} role="alert">
            {error}
          </Alert>
        )}
        <Button type="submit" loading={paying} disabled={!card} fullWidth>
          Pagar {formatArs(plan.price_ars)}
        </Button>
      </Stack>
    </form>
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
              <CardFields billing={billing} clientId={clientId} plan={plan} />
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
