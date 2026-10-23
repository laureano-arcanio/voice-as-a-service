import {
  ActionIcon,
  AppShell,
  Badge,
  Box,
  Burger,
  Group,
  Image,
  NavLink,
  Stack,
  Text,
  Tooltip,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconChartBar,
  IconLogout,
  IconMail,
  IconSpeakerphone,
  IconTemplate,
  IconUsers,
  IconWorld,
} from '@tabler/icons-react';
import { Link, Outlet, useLocation } from 'react-router';
import { setApiKey, useQueue } from './api';

const NAV = [
  { to: '/', label: 'Tablero', icon: IconChartBar },
  { to: '/leads', label: 'Leads', icon: IconUsers },
  { to: '/campanas', label: 'Campañas', icon: IconSpeakerphone },
  { to: '/plantillas', label: 'Plantillas', icon: IconTemplate },
  { to: '/mensajes', label: 'Mensajes', icon: IconMail },
  { to: '/sitio', label: 'Sitio web', icon: IconWorld },
];

function isActive(pathname: string, to: string): boolean {
  if (to === '/') return pathname === '/';
  return pathname === to || pathname.startsWith(`${to}/`);
}

export function CrmLayout() {
  const [opened, { toggle, close }] = useDisclosure();
  const { pathname } = useLocation();
  const queue = useQueue();
  const q = queue.data;

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 232, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" aria-label="Menú" />
            <Link to="/" aria-label="Tablero" style={{ display: 'flex' }}>
              <Image src="/atentina-logo.svg" alt="Atentina" h={28} w="auto" />
            </Link>
            <Badge color="gray">CRM</Badge>
          </Group>
          <Group gap="sm" wrap="nowrap">
            {q && (
              <Text size="xs" c="dimmed" visibleFrom="xs">
                Cola: <span className="mono">{q.queued}</span> · hoy{' '}
                <span className="mono">
                  {q.sent_today}/{q.daily_max}
                </span>
                {!q.enabled && ' · envío apagado'}
              </Text>
            )}
            <Tooltip label="Salir (olvidar la key)" withArrow>
              <ActionIcon variant="default" size="lg" onClick={() => setApiKey(null)} aria-label="Salir">
                <IconLogout size={18} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="xs">
        <Stack gap={2}>
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              component={Link}
              to={item.to}
              label={item.label}
              leftSection={<item.icon size={18} />}
              active={isActive(pathname, item.to)}
              onClick={close}
              variant="light"
            />
          ))}
        </Stack>
      </AppShell.Navbar>
      <AppShell.Main className="app-main">
        <Box maw={1440} mx="auto">
          <Outlet />
        </Box>
      </AppShell.Main>
    </AppShell>
  );
}
