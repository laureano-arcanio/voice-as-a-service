import { Box, Image, Stack, Text } from '@mantine/core';
import type { Branding } from '@/api/types';
import { useBranding } from './context';

/** El logo del panel: el del cliente con marca blanca (o su nombre en texto si no subió uno), o el de Atentina. */
export function BrandLogo({ h = 28, branding }: { h?: number; branding?: Branding | null }) {
  const current = useBranding();
  const b = branding === undefined ? current : branding;
  if (!b) return <Image src="/atentina-logo.svg" alt="Atentina" h={h} w="auto" />;
  if (b.logo_url) {
    return (
      <Image
        src={b.logo_url}
        alt={b.name}
        h={h}
        w={b.logo_ratio ? Math.round(h * b.logo_ratio) : 'auto'}
        fit="contain"
        style={{ flex: 'none' }}
      />
    );
  }
  return (
    <Text fw={700} fz={h >= 40 ? 'xl' : 'lg'} c="var(--app-header-fg)" lineClamp={1} style={{ letterSpacing: '-0.015em' }}>
      {b.name}
    </Text>
  );
}

/**
 * Logo de las pantallas sin menú (login, crear clave, bienvenida). Con marca, va sobre una pastilla del color
 * del encabezado: así un logotipo pensado para un header oscuro también se ve sobre el lienzo claro.
 */
export function AuthLogo({ tagline }: { tagline?: string }) {
  const b = useBranding();
  if (!b) {
    return (
      <Stack align="center" mb="lg">
        <Image src="/atentina-logo.svg" alt="Atentina" h={40} w="auto" />
        {tagline && (
          <Text c="dimmed" size="sm">
            {tagline}
          </Text>
        )}
      </Stack>
    );
  }
  const onWhite = b.color_header.toLowerCase() === '#ffffff';
  return (
    <Stack align="center" mb="lg">
      <Box
        px="xl"
        py="md"
        style={{
          background: b.color_header,
          borderRadius: 16,
          border: onWhite ? '1px solid var(--app-line)' : undefined,
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <BrandLogo h={40} />
      </Box>
    </Stack>
  );
}
