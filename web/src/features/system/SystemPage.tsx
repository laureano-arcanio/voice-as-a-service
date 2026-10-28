import { LineChart } from '@mantine/charts';
import {
  Alert,
  Badge,
  Card,
  Group,
  Progress,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { IconAlertTriangle, IconCheck } from '@tabler/icons-react';
import { useState, type ReactNode } from 'react';
import { ApiError } from '@/api/errors';
import type { SystemGpu, SystemHost, SystemNow, SystemSeries } from '@/api/types';
import { Dash } from '@/components/Badges';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { KpiGrid } from '@/features/reports/parts';
import { ALERT_SEVERITY, GPU_THROTTLE } from '@/lib/labels';
import { formatDateTime, formatMs, formatNumber } from '@/lib/format';
import { useSystemEvents, useSystemHistory, useSystemNow, useSystemPeaks, type SystemWindow } from './api';
import {
  bitrate,
  bytes,
  celsius,
  chartRows,
  epochDateTime,
  pct,
  uptime,
  usageTone,
  watts,
  type ChartLine,
} from './format';

const WINDOWS: { value: SystemWindow; label: string }[] = [
  { value: '1h', label: '1 h' },
  { value: '6h', label: '6 h' },
  { value: '24h', label: '24 h' },
  { value: '7d', label: '7 días' },
];
const CHART_COLORS = ['var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)'];

/** Hardware y servicios de cada server (docs/OBSERVABILIDAD.md): solo el admin. */
export function SystemPage() {
  const now = useSystemNow();
  const [window, setWindow] = useState<SystemWindow>('24h');
  const off = now.error instanceof ApiError && now.error.status === 503;
  return (
    <>
      <PageHeader
        title="Sistema"
        description="CPU, memoria, GPUs, discos, conectividad y servicios de cada server. Se actualiza cada 10 s."
      />
      {off ? (
        <Alert color="yellow" icon={<IconAlertTriangle size={18} />} title="Sin datos del monitoreo">
          Prometheus no responde: levantalo con <span className="mono">make up-monitoring</span> (y el
          colector del host con <span className="mono">make monitoring-host-install</span>).
        </Alert>
      ) : (
        <QueryState query={now}>
          {(n) => (
            <Stack gap="lg">
              <AlertsCard alerts={n.alerts} />
              {n.hosts.length === 0 && (
                <EmptyState>Prometheus no tiene datos de ningún server todavía.</EmptyState>
              )}
              {n.hosts.map((h) => (
                <HostSection key={h.host} host={h} showName={n.hosts.length > 1} />
              ))}
              <Group justify="space-between" align="flex-end">
                <Title order={3}>Historia</Title>
                <SegmentedControl
                  size="xs"
                  value={window}
                  onChange={(v) => setWindow(v as SystemWindow)}
                  data={WINDOWS}
                  aria-label="Ventana"
                />
              </Group>
              <HistoryCharts window={window} />
              <EventsCard window={window} />
              <PeaksCard />
            </Stack>
          )}
        </QueryState>
      )}
    </>
  );
}

function SeverityBadge({ severity, pending }: { severity: string; pending?: boolean }) {
  const l = ALERT_SEVERITY[severity] ?? { label: severity, color: 'gray' };
  return <Badge color={pending ? 'gray' : l.color}>{pending ? `${l.label} (confirmando)` : l.label}</Badge>;
}

function AlertsCard({ alerts }: { alerts: SystemNow['alerts'] }) {
  return (
    <Card>
      <Group justify="space-between" mb={alerts.length ? 'sm' : 0}>
        <Title order={4}>Alertas activas</Title>
        {!alerts.length && (
          <Badge color="green" leftSection={<IconCheck size={12} />}>
            Sin alertas
          </Badge>
        )}
      </Group>
      {alerts.length > 0 && (
        <Stack gap="xs">
          {alerts.map((a) => (
            <Group key={`${a.name}-${a.summary}`} gap="xs" align="flex-start">
              <SeverityBadge severity={a.severity} pending={a.state === 'pending'} />
              <Text size="sm" style={{ flex: 1, minWidth: 200 }}>
                {a.summary || a.name}
              </Text>
              <Text size="xs" c="dimmed">
                desde {formatDateTime(a.since)}
              </Text>
            </Group>
          ))}
        </Stack>
      )}
    </Card>
  );
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Card>
      <Stack gap={2} mb="md">
        <Title order={4}>{title}</Title>
        {description && (
          <Text size="xs" c="dimmed">
            {description}
          </Text>
        )}
      </Stack>
      {children}
    </Card>
  );
}

function Meter({
  label,
  ratio,
  detail,
  reserved = false,
}: {
  label: string;
  ratio: number | null | undefined;
  detail: string;
  /** Uso reservado a propósito (la VRAM del LLM): sin color de alerta. */
  reserved?: boolean;
}) {
  const tone = reserved ? 'green' : usageTone(ratio);
  return (
    <Stack gap={4}>
      <Group justify="space-between" gap="xs" wrap="nowrap">
        <Text size="sm">{label}</Text>
        <Text size="sm" c={tone === 'green' ? 'dimmed' : tone} fw={tone === 'green' ? 400 : 600}>
          {detail}
        </Text>
      </Group>
      <Progress
        value={ratio == null ? 0 : Math.min(ratio * 100, 100)}
        color={tone}
        size="sm"
        aria-label={`${label}: ${pct(ratio)}`}
      />
    </Stack>
  );
}

function OkBadge({
  ok,
  yes = 'OK',
  no = 'Falla',
}: {
  ok: boolean | null | undefined;
  yes?: string;
  no?: string;
}) {
  if (ok == null) return <Dash />;
  return <Badge color={ok ? 'green' : 'red'}>{ok ? yes : no}</Badge>;
}

function HostSection({ host: h, showName }: { host: SystemHost; showName: boolean }) {
  const stale = h.collector_age_s == null || h.collector_age_s > 60;
  const sat = h.saturation;
  return (
    <Stack gap="md">
      <Group justify="space-between" align="baseline">
        <Title order={3}>{showName ? h.host : 'Server'}</Title>
        <Text size="xs" c="dimmed">
          {h.host} · encendido hace {uptime(h.uptime_s)}
        </Text>
      </Group>
      {stale && (
        <Alert color="red" icon={<IconAlertTriangle size={18} />}>
          El colector del host (atentina-hostmon) no actualiza: faltan GPUs, servicios, SMART y SIP. Revisarlo
          con <span className="mono">journalctl -u atentina-hostmon</span>.
        </Alert>
      )}
      <KpiGrid
        cols={6}
        kpis={[
          { label: 'CPU', value: pct(h.cpu.util_ratio), tone: tone(h.cpu.util_ratio) },
          { label: 'RAM', value: pct(h.memory.used_ratio), tone: tone(h.memory.used_ratio) },
          { label: 'Consumo estimado', value: watts(h.power.estimated_w), sub: 'GPUs + CPU' },
          { label: 'Llamadas activas', value: formatNumber(sat.calls_active, 0) },
          {
            label: 'Canales de Anura',
            value: formatNumber(sat.anura_channels_busy, 0),
            sub:
              sat.anura_channels_total != null
                ? `de ${formatNumber(sat.anura_channels_total, 0)}`
                : undefined,
            tone:
              sat.anura_channels_busy != null &&
              sat.anura_channels_total != null &&
              sat.anura_channels_busy >= sat.anura_channels_total - 1
                ? 'yellow'
                : undefined,
          },
          {
            label: 'p95 por turno',
            value: sat.turn_latency_p95_s == null ? '–' : formatMs(sat.turn_latency_p95_s * 1000),
            sub: 'últimos 15 min',
            tone: (sat.turn_latency_p95_s ?? 0) > 3 ? 'yellow' : undefined,
          },
        ]}
      />
      {h.gpus.length > 0 && (
        <SimpleGrid cols={{ base: 1, lg: Math.min(h.gpus.length, 2) }} spacing="md">
          {h.gpus.map((g) => (
            <GpuCard key={g.index} gpu={g} />
          ))}
        </SimpleGrid>
      )}
      <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
        <HostCard host={h} />
        <SaturationCard host={h} />
      </SimpleGrid>
      <DisksCard host={h} />
      <ServicesCard host={h} />
      <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
        <ConnectivityCard host={h} />
        <NetworkCard host={h} />
      </SimpleGrid>
    </Stack>
  );
}

function tone(ratio: number | null | undefined): 'red' | 'yellow' | undefined {
  const t = usageTone(ratio);
  return t === 'green' ? undefined : t;
}

function GpuCard({ gpu: g }: { gpu: SystemGpu }) {
  const memRatio = g.memory_total_bytes ? (g.memory_used_bytes ?? 0) / g.memory_total_bytes : null;
  const powerRatio = g.power_limit_w ? (g.power_w ?? 0) / g.power_limit_w : null;
  const throttle = g.throttle.filter((r) => r !== 'sw_power_cap' || (g.util_ratio ?? 0) > 0.05);
  return (
    <Card>
      <Group justify="space-between" mb="md" align="flex-start" gap="xs">
        <Stack gap={0}>
          <Title order={4}>GPU {g.index}</Title>
          <Text size="xs" c="dimmed">
            {g.name} · <span className="mono">{g.bus}</span>
          </Text>
        </Stack>
        <Group gap={6}>
          {throttle.map((r) => {
            const l = GPU_THROTTLE[r] ?? { label: r, color: 'gray' };
            return (
              <Badge key={r} color={l.color}>
                {l.label}
              </Badge>
            );
          })}
          {(g.xid_errors_24h ?? 0) > 0 && (
            <Badge color="red">Errores XID: {formatNumber(g.xid_errors_24h, 0)}</Badge>
          )}
        </Group>
      </Group>
      <Stack gap="sm">
        <Meter label="Uso" ratio={g.util_ratio} detail={pct(g.util_ratio)} />
        <Meter
          label="VRAM"
          ratio={memRatio}
          reserved={g.processes.some((p) => p.service === 'vllm-llm')}
          detail={`${bytes(g.memory_used_bytes)} de ${bytes(g.memory_total_bytes)}`}
        />
        <Meter
          label="Potencia"
          ratio={powerRatio}
          detail={`${watts(g.power_w)} de ${watts(g.power_limit_w)}`}
        />
        <Group gap="lg">
          <Fact
            label="Temperatura"
            value={celsius(g.temperature_c)}
            tone={(g.temperature_c ?? 0) > 83 ? 'red' : undefined}
          />
          <Fact label="Ventilador" value={pct(g.fan_ratio)} />
          <Fact
            label="Reloj"
            value={g.clock_sm_mhz == null ? '–' : `${formatNumber(g.clock_sm_mhz, 0)} MHz`}
          />
          <Fact
            label="PCIe"
            value={
              g.pcie.gen == null
                ? '–'
                : `gen${formatNumber(g.pcie.gen, 0)} x${formatNumber(g.pcie.width, 0)} (máx. gen${formatNumber(g.pcie.gen_max, 0)} x${formatNumber(g.pcie.width_max, 0)})`
            }
          />
        </Group>
        {g.processes.length > 0 && (
          <Text size="xs" c="dimmed">
            VRAM por servicio:{' '}
            {g.processes
              .map(
                (p) => `${p.service === 'otros' ? 'escritorio y otros' : p.service} ${bytes(p.memory_bytes)}`,
              )
              .join(' · ')}
          </Text>
        )}
      </Stack>
    </Card>
  );
}

function Fact({ label, value, tone }: { label: string; value: string; tone?: 'red' | 'yellow' }) {
  return (
    <Stack gap={0}>
      <Text className="label">{label}</Text>
      <Text size="sm" c={tone} fw={tone ? 600 : 400}>
        {value}
      </Text>
    </Stack>
  );
}

function HostCard({ host: h }: { host: SystemHost }) {
  const m = h.memory;
  return (
    <Section
      title="CPU y memoria"
      description="Presión: % del tiempo con tareas esperando (saturación real)."
    >
      <Stack gap="sm">
        <Meter
          label={`CPU (${formatNumber(h.cpu.cores, 0)} hilos)`}
          ratio={h.cpu.util_ratio}
          detail={pct(h.cpu.util_ratio)}
        />
        <Meter
          label="RAM"
          ratio={m.used_ratio}
          detail={`${bytes((m.total_bytes ?? 0) - (m.available_bytes ?? 0))} de ${bytes(m.total_bytes)}`}
        />
        <Group gap="lg">
          <Fact
            label="Carga 1/5/15"
            value={[h.cpu.load1, h.cpu.load5, h.cpu.load15].map((v) => formatNumber(v, 1)).join(' / ')}
          />
          <Fact
            label="Presión CPU"
            value={pct(h.cpu.pressure_ratio, 1)}
            tone={(h.cpu.pressure_ratio ?? 0) > 0.2 ? 'yellow' : undefined}
          />
          <Fact label="Presión RAM" value={pct(m.pressure_ratio, 1)} />
          <Fact label="Presión disco" value={pct(h.io_pressure_ratio, 1)} />
        </Group>
        <Group gap="lg">
          <Fact
            label="Temperatura CPU"
            value={celsius(h.cpu.temperature_c)}
            tone={(h.cpu.temperature_c ?? 0) > 90 ? 'yellow' : undefined}
          />
          <Fact label="Potencia CPU" value={watts(h.cpu.power_w)} />
          <Fact label="Swap" value={`${bytes(m.swap_used_bytes)} de ${bytes(m.swap_total_bytes)}`} />
          <Fact
            label="OOM (24 h)"
            value={formatNumber(m.oom_kills_24h, 0)}
            tone={(m.oom_kills_24h ?? 0) > 0 ? 'red' : undefined}
          />
        </Group>
      </Stack>
    </Section>
  );
}

function SaturationCard({ host: h }: { host: SystemHost }) {
  const sat = h.saturation;
  const rows = [
    { name: 'LLM', q: sat.inference.llm },
    { name: 'TTS', q: sat.inference.tts },
    { name: 'STT', q: sat.inference.stt },
  ];
  return (
    <Section
      title="Inferencia"
      description="Pedidos en curso y en cola: una cola que no baja es saturación. KV cache en tokens (del TTS, el talker: no publica su total; el STT no tiene)."
    >
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Motor</Table.Th>
            <Table.Th ta="right">En curso</Table.Th>
            <Table.Th ta="right">En cola</Table.Th>
            <Table.Th ta="right">KV en uso</Table.Th>
            <Table.Th ta="right">KV total</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map(({ name, q }) => (
            <Table.Tr key={name}>
              <Table.Td>{name}</Table.Td>
              <Table.Td ta="right" className="mono">
                {formatNumber(q?.running, 0)}
              </Table.Td>
              <Table.Td ta="right" className="mono" c={(q?.waiting ?? 0) > 0 ? 'yellow' : undefined}>
                {formatNumber(q?.waiting, 0)}
              </Table.Td>
              <Table.Td ta="right" className="mono" c={(q?.kv_cache_ratio ?? 0) > 0.9 ? 'yellow' : undefined}>
                {q?.kv_cache_ratio == null
                  ? formatNumber(null)
                  : q.kv_cache_used_tokens == null
                    ? pct(q.kv_cache_ratio)
                    : `${formatNumber(q.kv_cache_used_tokens, 0)} (${pct(q.kv_cache_ratio)})`}
              </Table.Td>
              <Table.Td ta="right" className="mono">
                {formatNumber(q?.kv_cache_tokens, 0)}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Section>
  );
}

function DisksCard({ host: h }: { host: SystemHost }) {
  return (
    <Section title="Discos" description="Días hasta llenarse: al ritmo de las últimas 6 h.">
      <Table.ScrollContainer minWidth={560}>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Montaje</Table.Th>
              <Table.Th>Uso</Table.Th>
              <Table.Th ta="right">Libre</Table.Th>
              <Table.Th ta="right">Se llena en</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {h.disks.map((d) => (
              <Table.Tr key={d.mountpoint}>
                <Table.Td className="mono">{d.mountpoint}</Table.Td>
                <Table.Td w="40%">
                  <Meter label={d.device} ratio={d.used_ratio} detail={pct(d.used_ratio)} />
                </Table.Td>
                <Table.Td ta="right" className="mono">
                  {bytes(d.avail_bytes)} de {bytes(d.size_bytes)}
                </Table.Td>
                <Table.Td ta="right" c={d.days_to_full != null && d.days_to_full < 7 ? 'red' : undefined}>
                  {d.days_to_full == null ? <Dash /> : `${formatNumber(d.days_to_full, 1)} días`}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
      {h.smart.length > 0 && (
        <Table.ScrollContainer minWidth={560} mt="md">
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Disco</Table.Th>
                <Table.Th>SMART</Table.Th>
                <Table.Th ta="right">Desgaste</Table.Th>
                <Table.Th ta="right">Errores</Table.Th>
                <Table.Th ta="right">Temperatura</Table.Th>
                <Table.Th ta="right">Ocupado</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {h.smart.map((s) => (
                <Table.Tr key={s.device}>
                  <Table.Td>
                    <span className="mono">{s.device}</span>{' '}
                    <Text span size="xs" c="dimmed">
                      {s.model}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <OkBadge ok={s.ok} />
                  </Table.Td>
                  <Table.Td ta="right" c={(s.wear_ratio ?? 0) > 0.8 ? 'yellow' : undefined}>
                    {pct(s.wear_ratio)}
                  </Table.Td>
                  <Table.Td ta="right" c={(s.media_errors ?? 0) > 0 ? 'red' : undefined}>
                    {formatNumber(s.media_errors, 0)}
                  </Table.Td>
                  <Table.Td ta="right">{celsius(s.temperature_c)}</Table.Td>
                  <Table.Td ta="right">{pct(s.io_busy_ratio)}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Section>
  );
}

function ServicesCard({ host: h }: { host: SystemHost }) {
  return (
    <Section title="Servicios" description="Contenedores de Atentina; los de otros proyectos no se muestran.">
      <Table.ScrollContainer minWidth={560}>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Servicio</Table.Th>
              <Table.Th>Estado</Table.Th>
              <Table.Th ta="right">Reinicios</Table.Th>
              <Table.Th ta="right">CPU</Table.Th>
              <Table.Th ta="right">RAM</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {h.services.map((s) => (
              <Table.Tr key={s.service}>
                <Table.Td className="mono">{s.service}</Table.Td>
                <Table.Td>
                  {!s.up ? (
                    <Badge color="red">Caído</Badge>
                  ) : s.healthy === 0 ? (
                    <Badge color="red">Unhealthy</Badge>
                  ) : s.healthy === 0.5 ? (
                    <Badge color="yellow">Arrancando</Badge>
                  ) : (
                    <Badge color="green">Arriba</Badge>
                  )}
                </Table.Td>
                <Table.Td ta="right" className="mono" c={(s.restarts ?? 0) > 0 ? 'yellow' : undefined}>
                  {formatNumber(s.restarts, 0)}
                </Table.Td>
                <Table.Td ta="right" className="mono">
                  {s.cpu_cores == null ? <Dash /> : `${formatNumber(s.cpu_cores, 2)} núcleos`}
                </Table.Td>
                <Table.Td ta="right" className="mono">
                  {bytes(s.memory_bytes)}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Section>
  );
}

function ConnectivityCard({ host: h }: { host: SystemHost }) {
  const c = h.connectivity;
  return (
    <Section
      title="Conectividad"
      description="Sondas desde el server: internas cada 15 s, externas cada 30 s."
    >
      <Stack gap="sm">
        <Group gap="lg">
          <Stack gap={2}>
            <Text className="label">Internet</Text>
            <OkBadge ok={c.internet_ok} />
          </Stack>
          <Stack gap={2}>
            <Text className="label">IP pública</Text>
            <OkBadge ok={c.public_ip_ok} yes="La fija" no="Cambió" />
          </Stack>
          {c.sip.map((s) => (
            <Stack gap={2} key={s.registration}>
              <Text className="label">SIP {s.registration}</Text>
              <OkBadge ok={s.ok} yes="Registrado" no="Sin registro" />
            </Stack>
          ))}
          <Stack gap={2}>
            <Text className="label">Reloj</Text>
            <OkBadge ok={h.clock.synced} yes="Sincronizado" no="Sin NTP" />
          </Stack>
        </Group>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Destino</Table.Th>
              <Table.Th>Estado</Table.Th>
              <Table.Th ta="right">Tiempo</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {h.probes.map((p) => (
              <Table.Tr key={`${p.kind}-${p.name}`}>
                <Table.Td>
                  {p.name}{' '}
                  <Text span size="xs" c="dimmed">
                    {p.kind}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <OkBadge ok={p.ok} />
                </Table.Td>
                <Table.Td ta="right" className="mono">
                  {p.duration_s == null ? <Dash /> : formatMs(p.duration_s * 1000)}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Stack>
    </Section>
  );
}

function NetworkCard({ host: h }: { host: SystemHost }) {
  return (
    <Section
      title="Red"
      description={`Paquetes UDP descartados por el kernel (audio perdido): ${formatNumber(h.udp_rcvbuf_errors_s, 1)}/s.`}
    >
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Interfaz</Table.Th>
            <Table.Th ta="right">Entrada</Table.Th>
            <Table.Th ta="right">Salida</Table.Th>
            <Table.Th ta="right">Errores/s</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {h.network.map((n) => (
            <Table.Tr key={n.iface}>
              <Table.Td className="mono">{n.iface}</Table.Td>
              <Table.Td ta="right" className="mono">
                {bitrate(n.rx_bytes_s)}
              </Table.Td>
              <Table.Td ta="right" className="mono">
                {bitrate(n.tx_bytes_s)}
              </Table.Td>
              <Table.Td
                ta="right"
                className="mono"
                c={(n.errors_s ?? 0) + (n.drops_s ?? 0) > 0 ? 'yellow' : undefined}
              >
                {formatNumber((n.errors_s ?? 0) + (n.drops_s ?? 0), 1)}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Section>
  );
}

// --- Historia ------------------------------------------------------------------------------------

function linesOf(series: SystemSeries[] | undefined, name: (s: SystemSeries) => string): ChartLine[] {
  return (series ?? []).map((s, i) => ({ key: `s${i}`, label: name(s), series: s }));
}

function HistoryChart({
  title,
  description,
  lines,
  withDay,
  unit,
  scale = 1,
  digits = 0,
}: {
  title: string;
  description?: string;
  lines: ChartLine[];
  withDay: boolean;
  unit: string;
  scale?: number;
  digits?: number;
}) {
  const rows = chartRows(lines, withDay, scale);
  return (
    <Section title={title} description={description}>
      {lines.length === 0 ? (
        <EmptyState>Sin datos en la ventana.</EmptyState>
      ) : (
        <LineChart
          h={200}
          data={rows}
          dataKey="time"
          withLegend={lines.length > 1}
          legendProps={{ verticalAlign: 'bottom' }}
          unit={unit}
          valueFormatter={(v) => formatNumber(v, digits)}
          curveType="linear"
          // Con pocos puntos (recién levantado) una línea no se ve: se marcan los puntos.
          withDots={rows.length < 30}
          connectNulls
          series={lines.map((l, i) => ({
            name: l.key,
            label: l.label,
            color: CHART_COLORS[i % CHART_COLORS.length],
          }))}
        />
      )}
    </Section>
  );
}

function HistoryCharts({ window }: { window: SystemWindow }) {
  const history = useSystemHistory(window);
  const withDay = window === '7d';
  return (
    <QueryState query={history}>
      {(r) => {
        const s = r.series;
        const multiHost =
          new Set(
            Object.values(s)
              .flat()
              .map((x) => x.host),
          ).size > 1;
        const host = (x: SystemSeries) => (multiHost ? `${x.host} ` : '');
        const gpu = (x: SystemSeries) => `${host(x)}GPU ${x.label}`;
        return (
          <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
            <HistoryChart
              title="CPU y RAM"
              lines={[
                ...linesOf(s.cpu_util, (x) => `${host(x)}CPU`),
                ...linesOf(s.memory_used, (x) => `${host(x)}RAM`).map((l) => ({ ...l, key: `m${l.key}` })),
              ]}
              withDay={withDay}
              unit=" %"
              scale={100}
            />
            <HistoryChart
              title="Uso de cada GPU"
              description="Máximo de cada punto del gráfico."
              lines={linesOf(s.gpu_util, gpu)}
              withDay={withDay}
              unit=" %"
              scale={100}
            />
            <HistoryChart
              title="Potencia de cada GPU"
              description="Máximo de cada punto. El tope es 280 W por GPU."
              lines={linesOf(s.gpu_power, gpu)}
              withDay={withDay}
              unit=" W"
            />
            <HistoryChart
              title="Consumo estimado"
              description="GPUs + paquete de la CPU; sin medidor de pared."
              lines={linesOf(s.power_total, (x) => `${host(x)}Total`)}
              withDay={withDay}
              unit=" W"
            />
            <HistoryChart
              title="Temperatura de cada GPU"
              lines={linesOf(s.gpu_temp, gpu)}
              withDay={withDay}
              unit=" °C"
            />
            <HistoryChart
              title="VRAM de cada GPU"
              lines={linesOf(s.gpu_memory, gpu)}
              withDay={withDay}
              unit=" %"
              scale={100}
            />
            <HistoryChart
              title="Llamadas activas y KV cache del LLM"
              lines={[
                ...linesOf(s.calls_active, (x) => `${host(x)}Llamadas`),
                ...linesOf(s.llm_kv_cache, (x) => `${host(x)}KV cache (%)`).map((l) => ({
                  ...l,
                  key: `k${l.key}`,
                  series: {
                    ...l.series,
                    points: l.series.points.map(([t, v]) => [t, v == null ? null : v * 100]),
                  },
                })),
              ]}
              withDay={withDay}
              unit=""
            />
            <HistoryChart
              title="Red"
              lines={[
                ...linesOf(s.net_rx, (x) => `${host(x)}Entrada`),
                ...linesOf(s.net_tx, (x) => `${host(x)}Salida`).map((l) => ({ ...l, key: `t${l.key}` })),
              ]}
              withDay={withDay}
              unit=" Mbit/s"
              scale={8 / 1e6}
              digits={1}
            />
          </SimpleGrid>
        );
      }}
    </QueryState>
  );
}

function EventsCard({ window }: { window: SystemWindow }) {
  const events = useSystemEvents(window);
  return (
    <Section
      title="Eventos"
      description="Alertas que se dispararon en la ventana: para explicar un pico o una caída."
    >
      <QueryState query={events}>
        {(rows) =>
          rows.length === 0 ? (
            <EmptyState>Sin alertas en la ventana.</EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={560}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Alerta</Table.Th>
                    <Table.Th>Gravedad</Table.Th>
                    <Table.Th>Desde</Table.Th>
                    <Table.Th>Hasta</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {rows.map((e) => (
                    <Table.Tr key={`${e.name}-${e.detail}-${e.start}`}>
                      <Table.Td>
                        <span className="mono">{e.name}</span>{' '}
                        <Text span size="xs" c="dimmed">
                          {e.detail}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <SeverityBadge severity={e.severity} />
                      </Table.Td>
                      <Table.Td>{epochDateTime(e.start)}</Table.Td>
                      <Table.Td>
                        {e.end == null ? <Badge color="red">Activa</Badge> : epochDateTime(e.end)}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )
        }
      </QueryState>
    </Section>
  );
}

function PeaksCard() {
  const peaks = useSystemPeaks();
  return (
    <Section title="Picos por día" description="El máximo de cada día de los últimos 7.">
      <QueryState query={peaks}>
        {(rows) =>
          rows.length === 0 ? (
            <EmptyState>Sin datos todavía.</EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={720}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Día</Table.Th>
                    <Table.Th ta="right">CPU</Table.Th>
                    <Table.Th ta="right">RAM</Table.Th>
                    <Table.Th ta="right">GPU</Table.Th>
                    <Table.Th ta="right">Potencia GPUs</Table.Th>
                    <Table.Th ta="right">Temp. GPU</Table.Th>
                    <Table.Th ta="right">KV cache</Table.Th>
                    <Table.Th ta="right">Llamadas</Table.Th>
                    <Table.Th ta="right">Alertas críticas</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {rows.map((p) => (
                    <Table.Tr key={`${p.host}-${p.day_end}`}>
                      <Table.Td>{dayOf(p.day_end)}</Table.Td>
                      <Table.Td ta="right">{pct(p.cpu_util_max)}</Table.Td>
                      <Table.Td ta="right">{pct(p.memory_used_max)}</Table.Td>
                      <Table.Td ta="right">{pct(p.gpu_util_max)}</Table.Td>
                      <Table.Td ta="right">{watts(p.gpu_power_max_w)}</Table.Td>
                      <Table.Td ta="right">{celsius(p.gpu_temp_max_c)}</Table.Td>
                      <Table.Td ta="right">{pct(p.llm_kv_cache_max)}</Table.Td>
                      <Table.Td ta="right">{formatNumber(p.calls_active_max, 0)}</Table.Td>
                      <Table.Td ta="right" c={(p.alerts_critical ?? 0) > 0 ? 'red' : undefined}>
                        {formatNumber(p.alerts_critical ?? 0, 0)}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )
        }
      </QueryState>
    </Section>
  );
}

/** El día que cierra en `dayEnd` (medianoche local): 27/10. */
function dayOf(dayEnd: number): string {
  const d = new Date((dayEnd - 3600) * 1000);
  return `${d.getDate()}/${d.getMonth() + 1}`;
}
