import { BarChart, LineChart } from '@mantine/charts';
import {
  ActionIcon,
  Card,
  Group,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
} from '@mantine/core';
import { IconRefresh } from '@tabler/icons-react';
import { useState, type ReactNode } from 'react';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useRefreshSite, useSite } from '../api';
import type { SiteReport, SiteTotals } from '../types';

const RANGES = [
  { value: '7', label: '7 días' },
  { value: '28', label: '28 días' },
  { value: '90', label: '90 días' },
];

// Nombres de GA (en inglés) a los de la guía; lo que no está, tal cual.
const CHANNELS: Record<string, string> = {
  Direct: 'Directo',
  Email: 'Email',
  'Organic Search': 'Búsqueda orgánica',
  'Paid Search': 'Búsqueda paga',
  'AI Assistant': 'Asistentes de IA',
  'Organic Social': 'Redes',
  'Paid Social': 'Redes pagas',
  'Organic Video': 'Video',
  Referral: 'Otros sitios',
  Display: 'Display',
  Unassigned: 'Sin asignar',
};
const DEVICES: Record<string, string> = { desktop: 'Computadora', mobile: 'Celular', tablet: 'Tablet' };

const int = (n: number) => n.toLocaleString('es-AR');
const pct = (a: number, b: number) => (b ? `${Math.round((100 * a) / b)} %` : '—');
const dayLabel = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;

function duration(sec: number): string {
  const s = Math.round(sec);
  return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${s % 60} s`;
}

/** Variación contra el período anterior; sin datos antes, nada. */
function Delta({ now, before }: { now: number; before: number }) {
  if (!before) return null;
  const d = Math.round((100 * (now - before)) / before);
  return (
    <Text size="xs" c={d > 0 ? 'green' : d < 0 ? 'red' : 'dimmed'}>
      {d > 0 ? '+' : ''}
      {d} % contra el período anterior
    </Text>
  );
}

function Metric({
  label,
  value,
  k,
  r,
}: {
  label: string;
  value: string;
  k: keyof SiteTotals;
  r: SiteReport;
}) {
  return (
    <Card withBorder p="md">
      <Text className="label">{label}</Text>
      <Text className="metric">{value}</Text>
      <Delta now={r.totals[k]} before={r.previous[k]} />
    </Card>
  );
}

function Section({ title, help, children }: { title: string; help?: string; children: ReactNode }) {
  return (
    <Card withBorder>
      <Title order={4} mb={help ? 0 : 'md'}>
        {title}
      </Title>
      {help && (
        <Text size="xs" c="dimmed" mb="md">
          {help}
        </Text>
      )}
      {children}
    </Card>
  );
}

function Rows<T>({ items, cols, row }: { items: T[]; cols: string[]; row: (x: T) => ReactNode[] }) {
  if (!items.length) return <EmptyState>Sin datos en el período.</EmptyState>;
  return (
    <Table>
      <Table.Thead>
        <Table.Tr>
          {cols.map((c, i) => (
            <Table.Th key={c} ta={i ? 'right' : undefined}>
              {c}
            </Table.Th>
          ))}
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {items.map((x, n) => (
          <Table.Tr key={n}>
            {row(x).map((v, i) => (
              <Table.Td key={i} ta={i ? 'right' : undefined} className={i ? 'mono' : undefined}>
                {v}
              </Table.Td>
            ))}
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}

function Report({ r }: { r: SiteReport }) {
  const t = r.totals;
  const days = r.by_day.map((d) => ({ ...d, day: dayLabel(d.day) }));
  const channels = r.channels.map((c) => ({ ...c, channel: CHANNELS[c.channel] ?? c.channel }));
  return (
    <Stack gap="md">
      <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }}>
        <Metric label="Usuarios" value={int(t.users)} k="users" r={r} />
        <Metric label="Usuarios nuevos" value={int(t.new_users)} k="new_users" r={r} />
        <Metric label="Sesiones" value={int(t.sessions)} k="sessions" r={r} />
        <Metric label="Vistas de página" value={int(t.views)} k="views" r={r} />
        <Metric
          label="Sesiones con interacción"
          value={pct(t.engagement_rate, 1)}
          k="engagement_rate"
          r={r}
        />
        <Metric
          label="Duración media"
          value={duration(t.avg_session_seconds)}
          k="avg_session_seconds"
          r={r}
        />
      </SimpleGrid>
      <Section title="Por día" help="Hoy aparece incompleto: GA tarda unas horas en procesar.">
        {t.sessions ? (
          <LineChart
            h={260}
            data={days}
            dataKey="day"
            withLegend
            legendProps={{ verticalAlign: 'bottom' }}
            yAxisProps={{ allowDecimals: false }}
            strokeWidth={2}
            curveType="linear"
            series={[
              { name: 'users', label: 'Usuarios', color: 'var(--chart-1)' },
              { name: 'sessions', label: 'Sesiones', color: 'var(--chart-2)' },
              { name: 'views', label: 'Vistas', color: 'var(--chart-3)' },
            ]}
          />
        ) : (
          <EmptyState>Sin visitas desde {r.country} en el período.</EmptyState>
        )}
      </Section>
      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <Section title="Canales" help="De dónde llegó cada sesión, según la agrupación de GA.">
          {channels.length ? (
            <BarChart
              h={Math.max(160, channels.length * 44)}
              data={channels}
              dataKey="channel"
              orientation="vertical"
              withLegend
              legendProps={{ verticalAlign: 'bottom' }}
              yAxisProps={{ width: 130 }}
              xAxisProps={{ allowDecimals: false }}
              maxBarWidth={28}
              series={[
                { name: 'sessions', label: 'Sesiones', color: 'var(--chart-1)' },
                { name: 'users', label: 'Usuarios', color: 'var(--chart-2)' },
              ]}
            />
          ) : (
            <EmptyState>Sin datos en el período.</EmptyState>
          )}
        </Section>
        <Section title="Páginas más vistas">
          <Rows
            items={r.pages}
            cols={['Página', 'Vistas', 'Usuarios']}
            row={(p) => [<span className="mono">{p.path}</span>, int(p.views), int(p.users)]}
          />
        </Section>
      </SimpleGrid>
      <SimpleGrid cols={{ base: 1, md: 3 }}>
        <Section title="Fuente / medio">
          <Rows
            items={r.sources}
            cols={['Fuente', 'Sesiones', 'Usuarios']}
            row={(x) => [x.source_medium, int(x.sessions), int(x.users)]}
          />
        </Section>
        <Section title="Ciudades">
          <Rows
            items={r.cities}
            cols={['Ciudad', 'Usuarios']}
            row={(x) => [x.city === '(not set)' ? 'Sin dato' : x.city, int(x.users)]}
          />
        </Section>
        <Section title="Dispositivos">
          <Rows
            items={r.devices}
            cols={['Dispositivo', 'Usuarios', '%']}
            row={(x) => [DEVICES[x.device] ?? x.device, int(x.users), pct(x.users, t.users)]}
          />
        </Section>
      </SimpleGrid>
    </Stack>
  );
}

export function SitePage() {
  const [days, setDays] = useState('28');
  const site = useSite(Number(days));
  const refresh = useRefreshSite(Number(days));
  const r = site.data;
  return (
    <>
      <PageHeader
        title="Sitio web"
        description={
          r
            ? `Google Analytics, solo visitas desde ${r.country}: ${int(r.totals.users)} de ${int(r.all_users)} usuarios en el período; el resto es casi todo robots. Del ${dayLabel(r.start)} al ${dayLabel(r.end)}.`
            : 'Google Analytics, solo visitas desde Argentina: el resto es casi todo robots.'
        }
        actions={
          <Group gap="sm" wrap="nowrap">
            <SegmentedControl data={RANGES} value={days} onChange={setDays} />
            <Tooltip label="Volver a consultar GA (se guarda 10 minutos)" withArrow>
              <ActionIcon
                variant="default"
                size="lg"
                onClick={() => refresh.mutate()}
                loading={refresh.isPending}
                aria-label="Actualizar"
              >
                <IconRefresh size={18} />
              </ActionIcon>
            </Tooltip>
          </Group>
        }
      />
      <QueryState query={site}>{(data) => <Report r={data} />}</QueryState>
    </>
  );
}
