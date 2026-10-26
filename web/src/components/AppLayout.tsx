import {
  ActionIcon,
  Anchor,
  AppShell,
  Badge,
  Box,
  Burger,
  Button,
  Group,
  NavLink,
  Stack,
  Text,
  Tooltip,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { useState } from 'react';
import { IconLock, IconLogout, IconUserCircle } from '@tabler/icons-react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router';
import { BrandLogo } from '@/branding/BrandLogo';
import { setPreview, useBranding, useBrandingPreview } from '@/branding/context';
import { useLogout, useMe } from '@/features/auth/api';
import { LegalModal } from '@/features/auth/LegalModal';
import { WelcomeModal } from '@/features/auth/WelcomeModal';
import { usePlanFeatures } from '@/features/billing/features';
import { notifyError } from '@/lib/notify';
import { isAdminOnly, isGroup, navFor, type NavEntry, type NavGroup, type NavItem } from './nav';

const LEGAL_LINKS = [
  ['Condiciones', '/terminos'],
  ['Privacidad', '/privacidad'],
  ['Arrepentimiento', '/arrepentimiento'],
  ['Baja', '/baja'],
] as const;

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
  const plan = usePlanFeatures().data;
  // Marca blanca (docs/MARCA_BLANCA_PLAN.md): logo y colores del cliente en el header; con la vista previa de un
  // admin, un aviso para salir.
  const branding = useBranding();
  const previewing = useBrandingPreview();
  // Grupos abiertos o cerrados a mano; sin tocar, abierto el que tiene la pantalla actual.
  const [groupOpen, setGroupOpen] = useState<Record<string, boolean>>({});

  if (!me) return null;

  const exitPreview = () => {
    setPreview(null);
    window.location.reload();
  };

  // Sin la función en el plan: candado al lado del nombre (la pantalla explica por qué).
  const locked = (item: NavItem) =>
    !!plan &&
    !!item.feature &&
    (Array.isArray(item.feature) ? item.feature : [item.feature]).every(
      (k) => plan.features?.[k]?.enabled === false,
    );
  const navLabel = (item: NavItem) => {
    if (item.to === '/plan' && plan?.free)
      return (
        <Group gap={6} wrap="nowrap">
          {item.label}
          <Badge color="yellow" variant="filled">
            Free
          </Badge>
        </Group>
      );
    if (locked(item))
      return (
        <Group gap={6} wrap="nowrap" justify="space-between">
          {item.label}
          <Tooltip label={`No incluido en tu plan ${plan?.tier_name ?? ''}`} withArrow position="right">
            <IconLock size={14} color="var(--mantine-color-dimmed)" aria-label="No incluido en tu plan" />
          </Tooltip>
        </Group>
      );
    return item.label;
  };

  const doLogout = () =>
    logout.mutate(undefined, {
      onSuccess: () => void navigate('/login', { replace: true }),
      onError: (e) => notifyError(e, 'No se pudo cerrar la sesión'),
    });

  const entries = navFor(me.role);
  const adminItems = entries.filter(isAdminOnly);
  const link = (item: NavItem) => (
    <NavLink
      key={item.to}
      component={Link}
      to={item.to}
      label={navLabel(item)}
      leftSection={<item.icon size={18} />}
      active={isActive(pathname, item.to)}
      onClick={close}
      variant="light"
    />
  );
  const group = (g: NavGroup) => {
    const current = g.items.some((i) => isActive(pathname, i.to));
    return (
      <NavLink
        key={g.label}
        label={
          g.items.every(locked) ? (
            <Group gap={6} wrap="nowrap" justify="space-between">
              {g.label}
              <IconLock size={14} color="var(--mantine-color-dimmed)" aria-label="No incluido en tu plan" />
            </Group>
          ) : (
            g.label
          )
        }
        leftSection={<g.icon size={18} />}
        opened={groupOpen[g.label] ?? current}
        onChange={(o) => setGroupOpen((prev) => ({ ...prev, [g.label]: o }))}
        // Cerrado, marca que la pantalla actual está adentro.
        active={current && !(groupOpen[g.label] ?? current)}
        variant="light"
        childrenOffset={18}
      >
        {g.items.map(link)}
      </NavLink>
    );
  };
  const entry = (e: NavEntry) => (isGroup(e) ? group(e) : link(e));

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 232, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header className={branding ? 'app-header brand-header' : 'app-header'}>
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap">
            <Burger
              opened={opened}
              onClick={toggle}
              hiddenFrom="sm"
              size="sm"
              aria-label="Menú"
              color="var(--app-header-fg)"
            />
            <Link to="/" aria-label="Inicio" style={{ display: 'flex' }}>
              <BrandLogo h={28} />
            </Link>
            {previewing && (
              <Badge color="yellow" variant="filled" visibleFrom="sm">
                Vista previa de la marca
              </Badge>
            )}
          </Group>
          <Group gap="sm" wrap="nowrap">
            {previewing && (
              <Button size="compact-xs" variant="default" onClick={exitPreview}>
                Salir de la vista previa
              </Button>
            )}
            <Stack gap={0} align="flex-end" visibleFrom="xs">
              <Group gap={6} wrap="nowrap">
                <Text size="sm" fw={600} lineClamp={1} c="var(--app-header-fg)">
                  {me.role === 'admin' ? 'Administración' : (me.client_name ?? 'Cliente')}
                </Text>
                {me.role === 'admin' && <Badge color="gray">admin</Badge>}
              </Group>
              <Text size="xs" lineClamp={1} className="app-header-dim">
                {me.name || me.email}
              </Text>
            </Stack>
            <Tooltip label="Mi perfil" withArrow>
              <ActionIcon variant="default" size="lg" component={Link} to="/profile" aria-label="Mi perfil">
                <IconUserCircle size={18} />
              </ActionIcon>
            </Tooltip>
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
            {entries.filter((e) => !isAdminOnly(e)).map(entry)}
            {adminItems.length > 0 && (
              <Text className="label" px="sm" pt="md" pb={4}>
                Administración
              </Text>
            )}
            {adminItems.map(entry)}
          </Stack>
        </AppShell.Section>
        <AppShell.Section>
          <Text size="xs" c="dimmed" px="sm" py="xs" truncate>
            {me.email}
          </Text>
          {branding?.powered_by && (
            <Text size="xs" c="dimmed" px="sm" pb={6} className="app-powered-by">
              Con tecnología de Atentina
            </Text>
          )}
          {/* Botones de arrepentimiento y de baja (Disp. 954/2025): a la vista, también en el panel. */}
          <Group gap={8} px="sm" pb="xs">
            {LEGAL_LINKS.map(([label, path]) => (
              <Anchor
                key={path}
                href={`https://atentina.com.ar${path}`}
                target="_blank"
                rel="noopener noreferrer"
                size="xs"
                c="dimmed"
              >
                {label}
              </Anchor>
            ))}
          </Group>
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main className="app-main">
        <Box maw={1440} mx="auto">
          <Outlet />
        </Box>
        <LegalModal />
        <WelcomeModal />
      </AppShell.Main>
    </AppShell>
  );
}
