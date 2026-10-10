import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Divider,
  Group,
  Modal,
  NumberInput,
  type NumberInputProps,
  SimpleGrid,
  Stack,
  Switch,
  Table,
  Text,
  Textarea,
  TextInput,
  Tooltip,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconPencil, IconPlus, IconTrash } from '@tabler/icons-react';
import { type ReactNode, useState } from 'react';
import { ApiError } from '@/api/errors';
import type { Tier } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatApiLimit, formatArs, formatLimit } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { numberErrorTitle } from '@/features/numbers/errors';
import { useDeleteTier, useSaveTier, useTiers } from './api';

type Limit = number | '';

const toLimit = (v: Limit): number | null => (v === '' ? null : v);

/** Limite de un tier: vacio = ilimitado (la ayuda va una sola vez, arriba del formulario). */
function LimitInput(props: NumberInputProps) {
  return (
    <NumberInput
      placeholder="Ilimitado"
      min={0}
      allowDecimal={false}
      allowNegative={false}
      thousandSeparator="."
      decimalSeparator=","
      {...props}
    />
  );
}

/** Seccion del formulario: titulo y los campos en `cols` columnas desde `sm` (una en el movil). */
function Section({ title, cols, children }: { title?: string; cols: number; children: ReactNode }) {
  return (
    <>
      {title && <Divider label={title} labelPosition="left" mt="xs" />}
      <SimpleGrid cols={{ base: 1, sm: cols }}>{children}</SimpleGrid>
    </>
  );
}

function TierModal({ tier, onClose }: { tier: Tier | null; onClose: () => void }) {
  const save = useSaveTier();
  const form = useForm<{
    name: string;
    description: string;
    max_concurrent_calls: Limit;
    inbound_minutes: Limit;
    outbound_minutes: Limit;
    max_phone_numbers: Limit;
    max_calls_per_hour: Limit;
    max_calls_per_day: Limit;
    max_calls_per_month: Limit;
    api_llm_input_tokens: Limit;
    api_llm_output_tokens: Limit;
    api_tts_minutes: Limit;
    api_stt_minutes: Limit;
    api_rate_limit: Limit;
    price_ars: Limit;
    public: boolean;
    sort: number | '';
  }>({
    initialValues: {
      name: tier?.name ?? '',
      description: tier?.description ?? '',
      max_concurrent_calls: tier?.max_concurrent_calls ?? '',
      inbound_minutes: tier?.inbound_minutes ?? '',
      outbound_minutes: tier?.outbound_minutes ?? '',
      max_phone_numbers: tier?.max_phone_numbers ?? '',
      max_calls_per_hour: tier?.max_calls_per_hour ?? '',
      max_calls_per_day: tier?.max_calls_per_day ?? '',
      max_calls_per_month: tier?.max_calls_per_month ?? '',
      // Un tier nuevo arranca sin inferencia (0) y con 60 pedidos por minuto, como en la API.
      api_llm_input_tokens: tier ? (tier.api_llm_input_tokens ?? '') : 0,
      api_llm_output_tokens: tier ? (tier.api_llm_output_tokens ?? '') : 0,
      api_tts_minutes: tier ? (tier.api_tts_minutes ?? '') : 0,
      api_stt_minutes: tier ? (tier.api_stt_minutes ?? '') : 0,
      api_rate_limit: tier ? (tier.api_rate_limit ?? '') : 60,
      price_ars: tier?.price_ars ?? '',
      public: tier?.public ?? false,
      sort: tier?.sort ?? 0,
    },
    validate: {
      name: (v) => (v.trim() ? null : 'Poné un nombre'),
      public: (v, values) =>
        v && values.price_ars === '' ? 'Un tier público necesita precio (0 = gratis)' : null,
    },
  });

  return (
    <Modal opened onClose={onClose} title={tier ? `Editar tier ${tier.name}` : 'Nuevo tier'} size="xl">
      <form
        onSubmit={form.onSubmit((v) =>
          save.mutate(
            {
              id: tier?.id,
              body: {
                name: v.name.trim(),
                description: v.description.trim(),
                max_concurrent_calls: toLimit(v.max_concurrent_calls),
                inbound_minutes: toLimit(v.inbound_minutes),
                outbound_minutes: toLimit(v.outbound_minutes),
                max_phone_numbers: toLimit(v.max_phone_numbers),
                max_calls_per_hour: toLimit(v.max_calls_per_hour),
                max_calls_per_day: toLimit(v.max_calls_per_day),
                max_calls_per_month: toLimit(v.max_calls_per_month),
                api_llm_input_tokens: toLimit(v.api_llm_input_tokens),
                api_llm_output_tokens: toLimit(v.api_llm_output_tokens),
                api_tts_minutes: toLimit(v.api_tts_minutes),
                api_stt_minutes: toLimit(v.api_stt_minutes),
                api_rate_limit: toLimit(v.api_rate_limit),
                price_ars: toLimit(v.price_ars),
                public: v.public,
                sort: v.sort === '' ? 0 : v.sort,
              },
            },
            {
              onSuccess: () => {
                notifySuccess(tier ? 'Tier actualizado. Aplica desde ya al mes en curso.' : 'Tier creado.');
                onClose();
              },
              onError: (e) => notifyError(e, numberErrorTitle(e)),
            },
          ),
        )}
      >
        <Stack>
          <Section cols={2}>
            <TextInput label="Nombre" maxLength={64} data-autofocus {...form.getInputProps('name')} />
            <Textarea label="Descripción" autosize minRows={1} {...form.getInputProps('description')} />
          </Section>
          <Text size="xs" c="dimmed">
            Un campo vacío es ilimitado. En la API de inferencia, 0 es no incluido.
          </Text>
          <Section title="Llamadas" cols={4}>
            <LimitInput label="Simultáneas" {...form.getInputProps('max_concurrent_calls')} />
            <LimitInput label="Por hora" {...form.getInputProps('max_calls_per_hour')} />
            <LimitInput label="Por día" {...form.getInputProps('max_calls_per_day')} />
            <LimitInput label="Por mes" {...form.getInputProps('max_calls_per_month')} />
          </Section>
          <Section title="Minutos por mes y números" cols={3}>
            <LimitInput label="Minutos entrantes" {...form.getInputProps('inbound_minutes')} />
            <LimitInput label="Minutos salientes" {...form.getInputProps('outbound_minutes')} />
            <LimitInput label="Números" {...form.getInputProps('max_phone_numbers')} />
          </Section>
          <Section
            title="API de inferencia por mes (solo uso por API key, no cuenta los agentes integrados)"
            cols={3}
          >
            <LimitInput label="Tokens de entrada del LLM" {...form.getInputProps('api_llm_input_tokens')} />
            <LimitInput label="Tokens de salida del LLM" {...form.getInputProps('api_llm_output_tokens')} />
            <LimitInput label="Minutos de síntesis (TTS)" {...form.getInputProps('api_tts_minutes')} />
            <LimitInput label="Minutos de transcripción (STT)" {...form.getInputProps('api_stt_minutes')} />
            <LimitInput label="Pedidos por minuto" {...form.getInputProps('api_rate_limit')} />
          </Section>
          <Section title="Venta por el dashboard" cols={3}>
            <NumberInput
              label="Precio por mes ($)"
              description="Vacío: no se vende por el dashboard. 0: gratis (el del registro)."
              min={0}
              allowDecimal={false}
              allowNegative={false}
              thousandSeparator="."
              decimalSeparator=","
              {...form.getInputProps('price_ars')}
            />
            <NumberInput
              label="Orden"
              description="En la pantalla Plan, menor primero."
              allowDecimal={false}
              {...form.getInputProps('sort')}
            />
            <Switch
              label="Público"
              description="Se ofrece en el registro y en la pantalla Plan."
              mt="md"
              {...form.getInputProps('public', { type: 'checkbox' })}
            />
          </Section>
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={save.isPending}>
              Guardar
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export function TiersPage() {
  const tiers = useTiers();
  const del = useDeleteTier();
  const [editing, setEditing] = useState<Tier | 'new' | null>(null);

  const remove = async (t: Tier) => {
    if (
      !(await confirmAction({
        title: 'Borrar tier',
        message: `Se borra "${t.name}".`,
        confirmLabel: 'Borrar',
        danger: true,
      }))
    )
      return;
    del.mutate(t.id, {
      onSuccess: () => notifySuccess('Tier borrado.'),
      onError: (e) =>
        notifyError(
          e,
          e instanceof ApiError && e.status === 409 ? 'Tiene clientes: pasalos a otro tier antes' : undefined,
        ),
    });
  };

  return (
    <>
      <PageHeader
        title="Tiers"
        description="Límites por cliente: llamadas simultáneas y por hora, día y mes, minutos entrantes y salientes por mes, números y cupos de la API de inferencia (LLM, TTS, STT)."
        actions={
          <Button leftSection={<IconPlus size={18} />} onClick={() => setEditing('new')}>
            Nuevo tier
          </Button>
        }
      />
      <Card>
        <QueryState query={tiers}>
          {(list) =>
            list.length === 0 ? (
              <EmptyState>No hay tiers.</EmptyState>
            ) : (
              <Table.ScrollContainer minWidth={1200}>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Nombre</Table.Th>
                      <Table.Th ta="right">Precio/mes</Table.Th>
                      <Table.Th ta="right">Simultáneas</Table.Th>
                      <Table.Th ta="right">Llamadas hora / día / mes</Table.Th>
                      <Table.Th ta="right">Min. entrantes/mes</Table.Th>
                      <Table.Th ta="right">Min. salientes/mes</Table.Th>
                      <Table.Th ta="right">Números</Table.Th>
                      <Table.Th ta="right">API: LLM ent./sal. (tokens)</Table.Th>
                      <Table.Th ta="right">API: TTS / STT (min)</Table.Th>
                      <Table.Th ta="right">API: pedidos/min</Table.Th>
                      <Table.Th ta="right">Clientes</Table.Th>
                      <Table.Th />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {list.map((t) => (
                      <Table.Tr key={t.id}>
                        <Table.Td>
                          <Group gap={6} wrap="nowrap">
                            <Text size="sm" fw={600}>
                              {t.name}
                            </Text>
                            {t.public && <Badge color="gray">público</Badge>}
                          </Group>
                          {t.description && (
                            <Text size="xs" c="dimmed">
                              {t.description}
                            </Text>
                          )}
                        </Table.Td>
                        <Table.Td ta="right" className="mono">
                          {formatArs(t.price_ars)}
                        </Table.Td>
                        <Table.Td ta="right">{formatLimit(t.max_concurrent_calls)}</Table.Td>
                        <Table.Td ta="right" style={{ whiteSpace: 'nowrap' }}>
                          {formatLimit(t.max_calls_per_hour)} / {formatLimit(t.max_calls_per_day)} /{' '}
                          {formatLimit(t.max_calls_per_month)}
                        </Table.Td>
                        <Table.Td ta="right">{formatLimit(t.inbound_minutes)}</Table.Td>
                        <Table.Td ta="right">{formatLimit(t.outbound_minutes)}</Table.Td>
                        <Table.Td ta="right">{formatLimit(t.max_phone_numbers)}</Table.Td>
                        <Table.Td ta="right" style={{ whiteSpace: 'nowrap' }}>
                          {formatApiLimit(t.api_llm_input_tokens)} / {formatApiLimit(t.api_llm_output_tokens)}
                        </Table.Td>
                        <Table.Td ta="right" style={{ whiteSpace: 'nowrap' }}>
                          {formatApiLimit(t.api_tts_minutes)} / {formatApiLimit(t.api_stt_minutes)}
                        </Table.Td>
                        <Table.Td ta="right">{formatApiLimit(t.api_rate_limit)}</Table.Td>
                        <Table.Td ta="right">{t.clients_count ?? 0}</Table.Td>
                        <Table.Td>
                          <Group gap={4} justify="flex-end" wrap="nowrap">
                            <Tooltip label="Editar">
                              <ActionIcon
                                variant="subtle"
                                color="gray"
                                onClick={() => setEditing(t)}
                                aria-label="Editar tier"
                              >
                                <IconPencil size={16} />
                              </ActionIcon>
                            </Tooltip>
                            <Tooltip label={t.clients_count ? 'Tiene clientes asignados' : 'Borrar'}>
                              <ActionIcon
                                variant="subtle"
                                color="red"
                                onClick={() => void remove(t)}
                                aria-label="Borrar tier"
                              >
                                <IconTrash size={16} />
                              </ActionIcon>
                            </Tooltip>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )
          }
        </QueryState>
      </Card>
      {editing && (
        <TierModal
          key={editing === 'new' ? 'new' : editing.id}
          tier={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
        />
      )}
    </>
  );
}
