import {
  Alert,
  Box,
  Button,
  Card,
  ColorInput,
  FileButton,
  Grid,
  Group,
  Image,
  Stack,
  Switch,
  Text,
  Title,
} from '@mantine/core';
import { IconLock, IconUpload, IconX } from '@tabler/icons-react';
import { useState } from 'react';
import { ApiError } from '@/api/errors';
import type { Branding, BrandingAdmin, Client } from '@/api/types';
import { contrast, INK, isHex, MIN_CONTRAST, scale, textOn, WHITE } from '@/branding/color';
import { supportUrl } from '@/features/support/session';
import { QueryState } from '@/components/QueryState';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useClientBranding, useRemoveBrandingLogo, useSetBrandingLogo, useUpdateBranding } from './branding';

const LOGO_MAX_MB = 2;
// Los de la marca de Atentina, como punto de partida.
const SWATCHES = ['#2456e6', '#0b1220', '#ffffff', '#b45309', '#0d9488', '#147a46', '#4d39c3'];

interface Values {
  enabled: boolean;
  color_primary: string;
  color_header: string;
  color_accent: string;
  powered_by: boolean;
}

function values(b: BrandingAdmin): Values {
  return {
    enabled: b.enabled,
    color_primary: b.color_primary,
    color_header: b.color_header,
    color_accent: b.color_accent,
    powered_by: b.powered_by ?? true,
  };
}

function suggested(err: unknown): string | null {
  if (!(err instanceof ApiError) || err.code !== 'color_contrast') return null;
  const first = (err.errors as { suggested?: string }[] | undefined)?.[0];
  return first?.suggested ?? null;
}

/** Cómo se ve el panel con esos colores: header, menú, botones, estados y un gráfico (estático, con las
 * mismas reglas que la app: la escala del primario pisa a `blue`, los estados no cambian). */
function BrandPreview({ v, logoUrl, logoRatio, name }: { v: Values; logoUrl: string | null; logoRatio: number | null; name: string }) {
  const ok = isHex(v.color_primary) && isHex(v.color_header) && isHex(v.color_accent);
  const primary = ok ? scale(v.color_primary) : scale('#2456e6');
  const header = ok ? v.color_header : WHITE;
  const headerFg = textOn(header);
  const accent = ok ? v.color_accent : '#b45309';
  const bars = [
    [34, 18],
    [48, 22],
    [40, 30],
    [56, 26],
    [62, 38],
    [30, 14],
  ];
  const pill = (bg: string, fg: string, label: string) => (
    <span
      style={{
        display: 'inline-block',
        background: bg,
        color: fg,
        fontSize: 12,
        fontWeight: 600,
        padding: '2px 9px',
        borderRadius: 999,
      }}
    >
      {label}
    </span>
  );
  return (
    <Box
      style={{
        border: '1px solid var(--app-line)',
        borderRadius: 12,
        overflow: 'hidden',
        background: 'var(--app-canvas)',
        fontSize: 13,
      }}
      aria-label="Vista previa"
    >
      <Box
        style={{
          height: 44,
          background: header,
          color: headerFg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 12px',
          borderBottom: `1px solid ${header.toLowerCase() === WHITE ? 'var(--app-line)' : `color-mix(in srgb, ${headerFg} 20%, transparent)`}`,
        }}
      >
        {logoUrl ? (
          <Image src={logoUrl} alt={name} h={22} w={logoRatio ? Math.round(22 * logoRatio) : 'auto'} fit="contain" />
        ) : (
          <Text fw={700} size="sm" c={headerFg}>
            {name}
          </Text>
        )}
        <Text size="xs" c={headerFg} style={{ opacity: 0.8 }}>
          maria@empresa.com
        </Text>
      </Box>
      <Box style={{ display: 'flex', minHeight: 170 }}>
        <Box style={{ width: 120, background: WHITE, borderRight: '1px solid var(--app-line)', padding: 6 }}>
          {['Inicio', 'Conversaciones', 'Agentes', 'Contactos'].map((item, i) => (
            <Box
              key={item}
              style={{
                padding: '5px 8px',
                borderRadius: 6,
                fontSize: 12,
                background: i === 1 ? primary[0] : undefined,
                color: i === 1 ? primary[6] : INK,
                fontWeight: i === 1 ? 600 : 400,
              }}
            >
              {item}
            </Box>
          ))}
        </Box>
        <Box style={{ flex: 1, padding: 10 }}>
          <Group justify="space-between" mb={8} wrap="nowrap">
            <Text fw={700} size="sm">
              Conversaciones
            </Text>
            <Group gap={6} wrap="nowrap">
              <Box
                style={{
                  border: '1px solid var(--mantine-color-gray-4)',
                  background: WHITE,
                  borderRadius: 8,
                  padding: '4px 10px',
                  fontSize: 12,
                  fontWeight: 600,
                }}
              >
                Exportar
              </Box>
              <Box
                style={{ background: primary[6], color: WHITE, borderRadius: 8, padding: '4px 10px', fontSize: 12, fontWeight: 600 }}
              >
                Nueva llamada
              </Box>
            </Group>
          </Group>
          <Group gap={6} mb={8}>
            {pill(primary[0], primary[6], 'En curso')}
            {pill('var(--mantine-color-green-0)', 'var(--mantine-color-green-6)', 'Finalizada')}
            {pill('var(--mantine-color-yellow-0)', 'var(--mantine-color-yellow-6)', 'Rechazada')}
            {pill('var(--mantine-color-red-0)', 'var(--mantine-color-red-6)', 'Fallida')}
            {pill('var(--mantine-color-gray-2)', 'var(--mantine-color-gray-7)', 'Pendiente')}
          </Group>
          <Box style={{ display: 'flex', gap: 8, alignItems: 'flex-end', height: 64 }}>
            {bars.map(([a, b], i) => (
              <Box key={i} style={{ display: 'flex', gap: 2, alignItems: 'flex-end', flex: 1 }}>
                <Box style={{ flex: 1, height: a, background: primary[6], borderRadius: '3px 3px 0 0' }} />
                <Box style={{ flex: 1, height: b, background: accent, borderRadius: '3px 3px 0 0' }} />
              </Box>
            ))}
          </Box>
          <Text size="xs" mt={6} style={{ color: primary[6], textDecoration: 'underline' }}>
            Ver el consumo
          </Text>
        </Box>
      </Box>
    </Box>
  );
}

function BrandingForm({ client, data }: { client: Client; data: BrandingAdmin }) {
  const update = useUpdateBranding(client.id);
  const setLogo = useSetBrandingLogo(client.id);
  const removeLogo = useRemoveBrandingLogo(client.id);
  const [v, setV] = useState<Values>(() => values(data));
  const saved = values(data);
  const dirty = JSON.stringify(v) !== JSON.stringify(saved);
  const primaryOk = isHex(v.color_primary);
  const ratio = primaryOk ? contrast(WHITE, v.color_primary) : 0;
  const hint = suggested(update.error);

  const save = () =>
    update.mutate(v, {
      onSuccess: (r) => notifySuccess(r.active ? 'Marca guardada: el cliente ya la ve.' : 'Marca guardada.'),
      onError: (e) => notifyError(e, 'No se pudo guardar la marca'),
    });

  const upload = (file: File | null) => {
    if (!file) return;
    if (file.size > LOGO_MAX_MB * 1024 * 1024) {
      notifyError(new Error(`El logo pasa de ${LOGO_MAX_MB} MB.`));
      return;
    }
    setLogo.mutate(file, {
      onSuccess: () => notifySuccess('Logo subido.'),
      onError: (e) => notifyError(e, 'No se pudo subir el logo'),
    });
  };

  const previewAsClient = () => {
    const branding: Branding = {
      slug: client.slug,
      name: client.name,
      logo_url: data.logo_url ?? null,
      logo_ratio: data.logo_ratio ?? null,
      color_primary: isHex(v.color_primary) ? v.color_primary.toLowerCase() : '#2456e6',
      color_header: isHex(v.color_header) ? v.color_header.toLowerCase() : WHITE,
      color_accent: isHex(v.color_accent) ? v.color_accent.toLowerCase() : '#b45309',
      header_fg: textOn(isHex(v.color_header) ? v.color_header : WHITE),
      powered_by: v.powered_by,
    };
    // Otra pestaña, como el cliente y con el borrador; esta sigue en /admin.
    window.open(supportUrl(client.id, branding), '_blank', 'noopener');
  };

  const color = (field: 'color_primary' | 'color_header' | 'color_accent') => ({
    value: v[field],
    onChange: (c: string) => setV((prev) => ({ ...prev, [field]: c })),
    format: 'hex' as const,
    swatches: SWATCHES,
    swatchesPerRow: 7,
    withEyeDropper: false,
  });

  return (
    <Grid gutter="md">
      <Grid.Col span={{ base: 12, lg: 6 }}>
        <Card>
          <Stack gap="md">
            <Title order={4}>Marca blanca</Title>
            {!data.available && (
              <Alert color="yellow" icon={<IconLock size={18} />}>
                El plan {client.tier.name} no incluye la marca blanca: lo que se guarde acá no se muestra hasta que
                el cliente pase a un plan que la incluya.
              </Alert>
            )}
            <Switch
              label="Mostrar el panel con la marca del cliente"
              description="Sus usuarios ven el logo y los colores de acá en vez de los de Atentina."
              checked={v.enabled}
              onChange={(e) => {
                const on = e.currentTarget.checked;
                setV((prev) => ({ ...prev, enabled: on }));
              }}
            />
            <Stack gap={6}>
              <Text size="sm" fw={600}>
                Logo
              </Text>
              <Group gap="md" align="flex-start" wrap="nowrap">
                <Group gap="xs" wrap="nowrap">
                  {[WHITE, isHex(v.color_header) ? v.color_header : WHITE].map((bg, i) => (
                    <Box
                      key={i}
                      style={{
                        width: 132,
                        height: 56,
                        background: bg,
                        border: '1px solid var(--app-line)',
                        borderRadius: 10,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: 8,
                      }}
                      title={i === 0 ? 'Sobre blanco (login)' : 'Sobre el encabezado'}
                    >
                      {data.logo_url ? (
                        <Image src={data.logo_url} alt={client.name} h={28} w="auto" fit="contain" mah={40} maw={116} />
                      ) : (
                        <Text size="sm" fw={700} c={textOn(bg)}>
                          {client.name}
                        </Text>
                      )}
                    </Box>
                  ))}
                </Group>
                <Stack gap={6}>
                  <Group gap="xs">
                    <FileButton onChange={upload} accept="image/png,image/jpeg,image/webp,image/svg+xml">
                      {(props) => (
                        <Button
                          {...props}
                          size="xs"
                          variant="default"
                          leftSection={<IconUpload size={14} />}
                          loading={setLogo.isPending}
                        >
                          {data.logo_url ? 'Cambiar logo' : 'Subir logo'}
                        </Button>
                      )}
                    </FileButton>
                    {data.logo_url && (
                      <Button
                        size="xs"
                        variant="subtle"
                        color="red"
                        leftSection={<IconX size={14} />}
                        loading={removeLogo.isPending}
                        onClick={() =>
                          removeLogo.mutate(undefined, {
                            onSuccess: () => notifySuccess('Logo quitado.'),
                            onError: (e) => notifyError(e),
                          })
                        }
                      >
                        Quitar
                      </Button>
                    )}
                  </Group>
                  <Text size="xs" c="dimmed">
                    PNG, JPG, WebP (hasta {LOGO_MAX_MB} MB) o SVG (hasta 200 KB). Va a 28 px de alto en el header y a
                    40 en el login, sobre el color del encabezado: subí uno que se lea sobre ese fondo. Sin logo, el
                    nombre en texto.
                  </Text>
                </Stack>
              </Group>
            </Stack>
            <ColorInput
              label="Primario"
              description="Botones, links, lo seleccionado y la primera serie de los gráficos."
              error={
                primaryOk && ratio < MIN_CONTRAST
                  ? `Da ${ratio.toFixed(2).replace('.', ',')}:1 con blanco; hace falta 4,5:1.`
                  : undefined
              }
              {...color('color_primary')}
            />
            {primaryOk && ratio >= MIN_CONTRAST && (
              <Text size="xs" c="dimmed" mt={-10}>
                Contraste con blanco: {ratio.toFixed(2).replace('.', ',')}:1 ✓
              </Text>
            )}
            {hint && (
              <Group gap="xs" mt={-8}>
                <Text size="xs" c="dimmed">
                  Sugerido:
                </Text>
                <Button
                  size="compact-xs"
                  variant="light"
                  onClick={() => setV((prev) => ({ ...prev, color_primary: hint }))}
                >
                  Usar {hint}
                </Button>
              </Group>
            )}
            <ColorInput
              label="Encabezado"
              description={`Fondo de la barra superior. Texto: ${isHex(v.color_header) && textOn(v.color_header) === WHITE ? 'blanco' : 'oscuro'}.`}
              {...color('color_header')}
            />
            <ColorInput
              label="Acento"
              description="Segunda serie de los gráficos. Evitá verdes, amarillos y rojos: son estados."
              {...color('color_accent')}
            />
            <Switch
              label='Mostrar "Con tecnología de Atentina" al pie del menú'
              checked={v.powered_by}
              onChange={(e) => {
                const on = e.currentTarget.checked;
                setV((prev) => ({ ...prev, powered_by: on }));
              }}
            />
            <Group justify="space-between">
              <Button variant="default" size="xs" onClick={previewAsClient}>
                Ver el panel como el cliente
              </Button>
              <Button onClick={save} disabled={!dirty || !primaryOk || ratio < MIN_CONTRAST} loading={update.isPending}>
                Guardar
              </Button>
            </Group>
          </Stack>
        </Card>
      </Grid.Col>
      <Grid.Col span={{ base: 12, lg: 6 }}>
        <Card>
          <Stack gap="sm">
            <Group justify="space-between">
              <Title order={4}>Vista previa</Title>
              <Text size="xs" c="dimmed">
                {data.active ? 'El cliente la está viendo' : 'No se muestra todavía'}
              </Text>
            </Group>
            <BrandPreview v={v} logoUrl={data.logo_url ?? null} logoRatio={data.logo_ratio ?? null} name={client.name} />
            <Text size="xs" c="dimmed">
              Verde, amarillo, rojo y gris no cambian: son estados. El login va a{' '}
              <Text span inherit className="mono">
                /login?c={client.slug}
              </Text>
              ; los mails de alta y de clave ya llevan ese parámetro.
            </Text>
          </Stack>
        </Card>
      </Grid.Col>
    </Grid>
  );
}

export function BrandingTab({ client }: { client: Client }) {
  const query = useClientBranding(client.id);
  return <QueryState query={query}>{(data) => <BrandingForm key={data.logo_url ?? 'none'} client={client} data={data} />}</QueryState>;
}
