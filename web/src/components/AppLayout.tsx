import {
  ActionIcon,
  AppShell,
  Badge,
  Burger,
  Group,
  Image,
  NavLink,
  Stack,
  Text,
  Tooltip,
  useComputedColorScheme,
  useMantineColorScheme,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconLogout, IconMoon, IconSun } from '@tabler/icons-react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router';
import { useLogout, useMe } from '@/features/auth/api';
import { notifyError } from '@/lib/notify';
import { navItemsFor } from './nav';

function isActive(pathname: string, to: string): boolean {
  if (to === '/') return pathname === '/' || pathname.startsWith('/calls');
  return pathname === to || pathname.startsWith(`${to}/`);
}

function ThemeToggle() {
  const { setColorScheme } = useMantineColorScheme();
  const scheme = useComputedColorScheme('light');
  const next = scheme === 'dark' ? 'light' : 'dark';
  return (
    <Tooltip label={scheme === 'dark' ? 'Modo claro' : 'Modo oscuro'} withArrow>
      <ActionIcon variant="default" size="lg" onClick={() => setColorScheme(next)} aria-label="Cambiar tema">
        {scheme === 'dark' ? <IconSun size={18} /> : <IconMoon size={18} />}
      </ActionIcon>
    </Tooltip>
  );
}

export function AppLayout() {
  const [opened, { toggle, close }] = useDisclosure();
  const { data: me } = useMe();
  const logout = useLogout();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const scheme = useComputedColorScheme('light');

  if (!me) return null;

  const doLogout = () =>
    logout.mutate(undefined, {
      onSuccess: () => void navigate('/login', { replace: true }),
      onError: (e) => notifyError(e, 'No se pudo cerrar la sesión'),
    });

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 220, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" aria-label="Menú" />
            <Link to="/" aria-label="Inicio" style={{ display: 'flex' }}>
              <Image
                src={scheme === 'dark' ? '/atentina-logo-blanco.svg' : '/atentina-logo.svg'}
                alt="Atentina"
                h={30}
                w="auto"
              />
            </Link>
          </Group>
          <Group gap="sm" wrap="nowrap">
            <Stack gap={0} align="flex-end" visibleFrom="xs">
              <Group gap={6} wrap="nowrap">
                <Text size="sm" fw={600} lineClamp={1}>
                  {me.role === 'admin' ? 'Administración' : (me.client_name ?? 'Cliente')}
                </Text>
                {me.role === 'admin' && (
                  <Badge size="xs" color="amber" variant="filled">
                    admin
                  </Badge>
                )}
              </Group>
              <Text size="xs" c="dimmed" lineClamp={1}>
                {me.name || me.email}
              </Text>
            </Stack>
            <ThemeToggle />
            <Tooltip label="Salir" withArrow>
              <ActionIcon
                variant="default"
                size="lg"
                onClick={doLogout}
                loading={logout.isPending}
                aria-label="Salir"
              >
                <IconLogout size={18} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs">
        <AppShell.Section grow>
          {navItemsFor(me.role).map((item) => (
            <NavLink
              key={item.to}
              component={Link}
              to={item.to}
              label={item.label}
              leftSection={<item.icon size={18} stroke={1.7} />}
              active={isActive(pathname, item.to)}
              onClick={close}
              variant="light"
              style={{ borderRadius: 'var(--mantine-radius-sm)' }}
            />
          ))}
        </AppShell.Section>
        <AppShell.Section>
          <Text size="xs" c="dimmed" px="sm" py="xs">
            {me.email}
          </Text>
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main className="app-main">
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
