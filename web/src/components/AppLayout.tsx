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
import { IconLogout } from '@tabler/icons-react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router';
import { useLogout, useMe } from '@/features/auth/api';
import { notifyError } from '@/lib/notify';
import { isAdminOnly, navItemsFor, type NavItem } from './nav';

function isActive(pathname: string, to: string): boolean {
  if (to === '/') return pathname === '/';
  return pathname === to || pathname.startsWith(`${to}/`);
}

export function AppLayout() {
  const [opened, { toggle, close }] = useDisclosure();
  const { data: me } = useMe();
  const logout = useLogout();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  if (!me) return null;

  const doLogout = () =>
    logout.mutate(undefined, {
      onSuccess: () => void navigate('/login', { replace: true }),
      onError: (e) => notifyError(e, 'No se pudo cerrar la sesión'),
    });

  const items = navItemsFor(me.role);
  const adminItems = items.filter(isAdminOnly);
  const link = (item: NavItem) => (
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
  );

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
            <Link to="/" aria-label="Inicio" style={{ display: 'flex' }}>
              <Image src="/atentina-logo.svg" alt="Atentina" h={28} w="auto" />
            </Link>
          </Group>
          <Group gap="sm" wrap="nowrap">
            <Stack gap={0} align="flex-end" visibleFrom="xs">
              <Group gap={6} wrap="nowrap">
                <Text size="sm" fw={600} lineClamp={1}>
                  {me.role === 'admin' ? 'Administración' : (me.client_name ?? 'Cliente')}
                </Text>
                {me.role === 'admin' && <Badge color="gray">admin</Badge>}
              </Group>
              <Text size="xs" c="dimmed" lineClamp={1}>
                {me.name || me.email}
              </Text>
            </Stack>
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
          <Stack gap={2}>
            {items.filter((i) => !isAdminOnly(i)).map(link)}
            {adminItems.length > 0 && (
              <Text className="label" px="sm" pt="md" pb={4}>
                Administración
              </Text>
            )}
            {adminItems.map(link)}
          </Stack>
        </AppShell.Section>
        <AppShell.Section>
          <Text size="xs" c="dimmed" px="sm" py="xs" truncate>
            {me.email}
          </Text>
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main className="app-main">
        <Box maw={1440} mx="auto">
          <Outlet />
        </Box>
      </AppShell.Main>
    </AppShell>
  );
}
