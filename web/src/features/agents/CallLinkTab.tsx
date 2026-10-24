import {
  Alert,
  Anchor,
  Avatar,
  Badge,
  Button,
  Card,
  FileButton,
  Group,
  Menu,
  NumberInput,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { Link } from 'react-router';
import {
  IconDots,
  IconExternalLink,
  IconInfoCircle,
  IconLink,
  IconPhone,
  IconPlayerPause,
  IconPlayerPlay,
  IconRefresh,
  IconPhoto,
  IconTrash,
} from '@tabler/icons-react';
import type { Agent, CallLink, CallLinkState } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { CopyIcon } from '@/components/Copy';
import { QueryState } from '@/components/QueryState';
import { useIsAdmin } from '@/features/auth/api';
import { formatNumber } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { initials } from '@/lib/initials';
import {
  useCallLink,
  useCreateCallLink,
  useDeleteCallLink,
  useRemoveCallLinkImage,
  useRotateCallLink,
  useSetCallLinkImage,
  useUpdateCallLink,
} from './callLink';

const IMAGE_MAX_MB = 5;

/** Como se va a ver la pagina publica (la tarjeta de arriba del telefono). */
function Preview({
  name,
  company,
  subtitle,
  image,
}: {
  name: string;
  company: string;
  subtitle: string;
  image: string | null;
}) {
  return (
    <Card bg="gray.0" ta="center" py="xl" style={{ alignSelf: 'start' }}>
      <Stack gap={6} align="center">
        <Avatar
          size={72}
          radius={999}
          color="blue"
          variant="light"
          fw={800}
          src={image}
          bg={image ? 'white' : undefined}
        >
          {initials(company)}
        </Avatar>
        <Text fw={800} fz="xl" ff="heading" mt="xs">
          {name}
          {company && (
            <Text span inherit fw={500} c="gray.7">
              , asistente de
            </Text>
          )}
        </Text>
        <Text c="gray.7" fw={500}>
          {company}
        </Text>
        {subtitle && (
          <Text size="sm" c="dimmed">
            {subtitle}
          </Text>
        )}
        <Avatar size={56} radius={999} color="green" variant="filled" mt="md" aria-hidden>
          <IconPhone size={26} />
        </Avatar>
        <Text size="xs" c="dimmed">
          Llamar
        </Text>
      </Stack>
    </Card>
  );
}

/** La URL del link, para copiarla o abrirla. */
function LinkUrl({ link }: { link: CallLink }) {
  return (
    <Group gap="xs" wrap="nowrap">
      <TextInput
        readOnly
        value={link.url}
        aria-label="URL del link"
        classNames={{ input: 'mono' }}
        style={{ flex: 1 }}
        onFocus={(e) => e.currentTarget.select()}
        rightSection={<CopyIcon value={link.url} label="Copiar link" />}
      />
      <Button
        component="a"
        href={link.url}
        target="_blank"
        rel="noopener"
        variant="default"
        leftSection={<IconExternalLink size={16} />}
      >
        Abrir
      </Button>
    </Group>
  );
}

const minutes = (v: number | string) => (v === '' ? null : Number(v));

function LinkEditor({ agent, state, link }: { agent: Agent; state: CallLinkState; link: CallLink }) {
  const update = useUpdateCallLink(agent.id);
  const rotate = useRotateCallLink(agent.id);
  const del = useDeleteCallLink(agent.id);
  const setImage = useSetCallLinkImage(agent.id);
  const removeImage = useRemoveCallLinkImage(agent.id);
  const form = useForm({
    initialValues: {
      display_name: link.display_name,
      company_name: link.company_name,
      subtitle: link.subtitle,
      max_call_minutes: Math.round(link.max_call_seconds / 60) as number | string,
      max_concurrent: (link.max_concurrent ?? '') as number | string,
      daily_minutes: (link.daily_minutes ?? '') as number | string,
    },
  });
  const v = form.values;

  const save = form.onSubmit((values) =>
    update.mutate(
      {
        display_name: values.display_name,
        company_name: values.company_name,
        subtitle: values.subtitle,
        max_call_seconds: Math.max(1, Number(values.max_call_minutes) || 1) * 60,
        max_concurrent: minutes(values.max_concurrent),
        daily_minutes: minutes(values.daily_minutes),
      },
      {
        onSuccess: (saved) => {
          form.resetDirty();
          form.setInitialValues({ ...values, max_call_minutes: Math.round(saved.max_call_seconds / 60) });
          notifySuccess('Link guardado.');
        },
        onError: (e) => notifyError(e),
      },
    ),
  );

  const togglePause = () =>
    update.mutate(
      { paused: !link.paused },
      {
        onSuccess: () => notifySuccess(link.paused ? 'El link vuelve a atender.' : 'Link pausado.'),
        onError: (e) => notifyError(e),
      },
    );

  const regenerate = async () => {
    const ok = await confirmAction({
      title: 'Regenerar link',
      message: 'Se crea un link nuevo con la misma configuración. El actual deja de funcionar enseguida.',
      confirmLabel: 'Regenerar',
    });
    if (ok)
      rotate.mutate(undefined, {
        onSuccess: () => notifySuccess('Link nuevo creado. Compartí el nuevo.'),
        onError: (e) => notifyError(e),
      });
  };

  const remove = async () => {
    const ok = await confirmAction({
      title: 'Borrar link',
      message: 'El link deja de funcionar. Las conversaciones que entraron por él se conservan.',
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (ok)
      del.mutate(undefined, {
        onSuccess: () => notifySuccess('Link borrado.'),
        onError: (e) => notifyError(e),
      });
  };

  const uploadImage = (file: File | null) => {
    if (!file) return;
    if (file.size > IMAGE_MAX_MB * 1024 * 1024) {
      notifyError(new Error(`La imagen pasa de ${IMAGE_MAX_MB} MB.`));
      return;
    }
    setImage.mutate(file, {
      onSuccess: () => notifySuccess('Imagen actualizada.'),
      onError: (e) => notifyError(e),
    });
  };

  const usage = link.usage;
  return (
    <Stack gap="md">
      <Card>
        <Group justify="space-between" align="flex-start" mb="sm" wrap="nowrap">
          <div>
            <Group gap="xs">
              <Title order={4}>Link para llamar</Title>
              {link.paused ? <Badge color="yellow">Pausado</Badge> : <Badge color="green">Activo</Badge>}
            </Group>
            <Text size="sm" c="dimmed">
              Quien lo abre habla con este agente desde el navegador. Las llamadas usan minutos entrantes del
              plan.
            </Text>
          </div>
          <Group gap="xs" wrap="nowrap">
            <Button
              variant="default"
              leftSection={link.paused ? <IconPlayerPlay size={16} /> : <IconPlayerPause size={16} />}
              onClick={togglePause}
              loading={update.isPending && !form.isDirty()}
            >
              {link.paused ? 'Reanudar' : 'Pausar'}
            </Button>
            <Menu position="bottom-end" withinPortal>
              <Menu.Target>
                <Button variant="default" px="xs" aria-label="Más acciones del link">
                  <IconDots size={18} />
                </Button>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Item leftSection={<IconRefresh size={16} />} onClick={() => void regenerate()}>
                  Regenerar link
                </Menu.Item>
                <Menu.Item color="red" leftSection={<IconTrash size={16} />} onClick={() => void remove()}>
                  Borrar link
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Group>
        <LinkUrl link={link} />
        <Text size="sm" c="dimmed" mt="xs" className="mono">
          Hoy: {usage.calls_today} {usage.calls_today === 1 ? 'llamada' : 'llamadas'} ·{' '}
          {formatNumber(usage.seconds_today / 60)} min · Este mes: {formatNumber(usage.seconds_month / 60)}{' '}
          min
        </Text>
        {!state.enabled && (
          <Alert color="yellow" icon={<IconInfoCircle size={18} />} mt="sm">
            La página pública todavía no está habilitada en el servidor: el link muestra "no disponible".
          </Alert>
        )}
      </Card>

      <form onSubmit={save}>
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
          <Card>
            <Stack gap="sm">
              <Title order={5}>Lo que ve quien llama</Title>
              <Group gap="sm" wrap="nowrap">
                <Avatar
                  size={56}
                  radius={999}
                  color="blue"
                  variant="light"
                  fw={800}
                  src={link.image_url}
                  bg={link.image_url ? 'white' : undefined}
                >
                  {initials(v.company_name.trim() || state.default_company_name)}
                </Avatar>
                <Stack gap={4}>
                  <Group gap="xs">
                    <FileButton onChange={uploadImage} accept="image/png,image/jpeg,image/webp">
                      {(props) => (
                        <Button
                          {...props}
                          variant="default"
                          size="xs"
                          leftSection={<IconPhoto size={14} />}
                          loading={setImage.isPending}
                        >
                          {link.image_url ? 'Cambiar imagen' : 'Subir imagen'}
                        </Button>
                      )}
                    </FileButton>
                    {link.image_url && (
                      <Button
                        variant="subtle"
                        color="gray"
                        size="xs"
                        loading={removeImage.isPending}
                        onClick={() =>
                          removeImage.mutate(undefined, {
                            onSuccess: () => notifySuccess('Volvió la inicial de la empresa.'),
                            onError: (e) => notifyError(e),
                          })
                        }
                      >
                        Quitar
                      </Button>
                    )}
                  </Group>
                  <Text size="xs" c="dimmed">
                    Logo o foto, PNG, JPG o WebP hasta {IMAGE_MAX_MB} MB. Se recorta en círculo. Sin imagen:
                    la inicial de la empresa.
                  </Text>
                </Stack>
              </Group>
              <TextInput
                label="Nombre"
                placeholder={state.default_display_name}
                description="Vacío: el nombre del agente"
                maxLength={64}
                {...form.getInputProps('display_name')}
              />
              <TextInput
                label="Empresa"
                placeholder={state.default_company_name}
                description="Vacío: el nombre del cliente"
                maxLength={128}
                {...form.getInputProps('company_name')}
              />
              <TextInput
                label="Subtítulo"
                placeholder="Turnos y consultas"
                maxLength={120}
                {...form.getInputProps('subtitle')}
              />
              <Title order={5} mt="xs">
                Límites del link
              </Title>
              <Text size="xs" c="dimmed" mt={-8}>
                Además de los del plan. Vacío: sin tope propio.
              </Text>
              <SimpleGrid cols={{ base: 1, xs: 3 }} spacing="sm">
                <NumberInput
                  label="Duración máxima"
                  suffix=" min"
                  min={1}
                  allowDecimal={false}
                  {...form.getInputProps('max_call_minutes')}
                />
                <NumberInput
                  label="Llamadas a la vez"
                  min={0}
                  allowDecimal={false}
                  {...form.getInputProps('max_concurrent')}
                />
                <NumberInput
                  label="Minutos por día"
                  min={0}
                  allowDecimal={false}
                  {...form.getInputProps('daily_minutes')}
                />
              </SimpleGrid>
              <Group justify="flex-end">
                <Button type="submit" disabled={!form.isDirty()} loading={update.isPending && form.isDirty()}>
                  Guardar
                </Button>
              </Group>
            </Stack>
          </Card>
          <Preview
            name={v.display_name.trim() || state.default_display_name}
            company={v.company_name.trim() || state.default_company_name}
            subtitle={v.subtitle.trim()}
            image={link.image_url}
          />
        </SimpleGrid>
      </form>
    </Stack>
  );
}

function NoLink({ agent, state }: { agent: Agent; state: CallLinkState }) {
  const create = useCreateCallLink(agent.id);
  const isAdmin = useIsAdmin();
  const { plan_max: max, plan_used: used } = state;
  const blocked = agent.archived
    ? 'El agente está archivado.'
    : max === 0
      ? 'Tu plan no incluye links para llamar.'
      : max != null && used >= max
        ? `Usaste ${max === 1 ? 'el link' : `los ${max} links`} de tu plan.`
        : null;
  return (
    <Card>
      <Stack gap="sm" align="flex-start">
        <Group gap="xs">
          <IconLink size={20} />
          <Title order={4}>Link para llamar</Title>
        </Group>
        <Text size="sm" c="dimmed" maw={640}>
          Creá un link para que tus clientes hablen con este agente desde el navegador, sin número de
          teléfono. Sirve para la web, las redes, una firma de mail o un QR en el mostrador. Las llamadas usan
          minutos entrantes del plan.
        </Text>
        {blocked && (
          <Text size="sm" c="yellow.7">
            {blocked}
            {isAdmin &&
              max != null &&
              !agent.archived &&
              ' Se cambia en el tier o con un ajuste del cliente.'}
          </Text>
        )}
        <Button
          leftSection={<IconLink size={16} />}
          disabled={!!blocked}
          loading={create.isPending}
          onClick={() =>
            create.mutate(
              {},
              { onSuccess: () => notifySuccess('Link creado.'), onError: (e) => notifyError(e) },
            )
          }
        >
          Crear link
        </Button>
        {!state.enabled && isAdmin && (
          <Text size="xs" c="dimmed">
            Falta habilitar la página pública en el servidor: TURNSTILE_SITE_KEY, TURNSTILE_SECRET_KEY y la
            URL de LiveKit para navegadores (DEMO_LIVEKIT_URL).
          </Text>
        )}
      </Stack>
    </Card>
  );
}

export function CallLinkTab({ agent }: { agent: Agent }) {
  const query = useCallLink(agent.id);
  return (
    <QueryState query={query}>
      {(state) =>
        state.link ? (
          <LinkEditor key={state.link.id} agent={agent} state={state} link={state.link} />
        ) : (
          <NoLink agent={agent} state={state} />
        )
      }
    </QueryState>
  );
}

/**
 * Version corta para "Probar": la URL para copiar o abrir (o el alta) y el link a la
 * configuracion completa, en la pestaña "Link para llamar" del agente.
 */
export function CallLinkCard({ agent }: { agent: Agent }) {
  const query = useCallLink(agent.id);
  return (
    <QueryState query={query}>
      {(state) =>
        state.link ? (
          <Card>
            <Group justify="space-between" align="flex-start" mb="sm" wrap="nowrap">
              <div>
                <Group gap="xs">
                  <Title order={4}>Link para llamar</Title>
                  {state.link.paused ? <Badge color="yellow">Pausado</Badge> : <Badge color="green">Activo</Badge>}
                </Group>
                <Text size="sm" c="dimmed">
                  Abrilo para llamar al agente desde el navegador, como lo va a hacer tu cliente.
                </Text>
              </div>
              <Anchor component={Link} to={`/agents/${agent.id}?tab=link`} size="sm" style={{ whiteSpace: 'nowrap' }}>
                Configurar
              </Anchor>
            </Group>
            <LinkUrl link={state.link} />
          </Card>
        ) : (
          <NoLink agent={agent} state={state} />
        )
      }
    </QueryState>
  );
}
