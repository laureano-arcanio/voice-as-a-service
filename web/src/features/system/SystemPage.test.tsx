import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { SystemGpu, SystemHost, SystemNow } from '@/api/types';
import { ADMIN, jsonResponse, renderWithProviders } from '@/test/render';
import { chartRows } from './format';
import { SystemPage } from './SystemPage';

const GPU: SystemGpu = {
  index: 0,
  name: 'NVIDIA GeForce RTX 3090',
  bus: '04:00.0',
  util_ratio: 0.9,
  memory_used_bytes: 21 * 1024 ** 3,
  memory_total_bytes: 24 * 1024 ** 3,
  power_w: 250,
  power_limit_w: 280,
  temperature_c: 70,
  fan_ratio: 0.45,
  clock_sm_mhz: 1695,
  clock_mem_mhz: 9501,
  pcie: { gen: 3, gen_max: 3, width: 4, width_max: 16 },
  throttle: [],
  throttle_bad: false,
  xid_errors_24h: 0,
  processes: [{ service: 'vllm-llm', memory_bytes: 21 * 1024 ** 3 }],
};

const HOST: SystemHost = {
  host: 'srv',
  collector_age_s: 3,
  uptime_s: 3 * 86400 + 4 * 3600,
  cpu: {
    util_ratio: 0.25,
    cores: 16,
    load1: 2.5,
    load5: 2,
    load15: 1.5,
    pressure_ratio: 0.01,
    temperature_c: 61,
    power_w: 45,
  },
  memory: {
    total_bytes: 64 * 1024 ** 3,
    available_bytes: 16 * 1024 ** 3,
    used_ratio: 0.75,
    swap_total_bytes: 8 * 1024 ** 3,
    swap_used_bytes: 0,
    pressure_ratio: 0,
    oom_kills_24h: 0,
  },
  io_pressure_ratio: 0,
  disks: [
    {
      mountpoint: '/home',
      device: '/dev/nvme1n1p2',
      size_bytes: 1800 * 1024 ** 3,
      avail_bytes: 100 * 1024 ** 3,
      used_ratio: 0.95,
      days_to_full: 4,
    },
  ],
  smart: [],
  network: [{ iface: 'enp5s0', rx_bytes_s: 125000, tx_bytes_s: 250000, errors_s: 0, drops_s: 0 }],
  udp_rcvbuf_errors_s: 0,
  gpus: [
    GPU,
    {
      ...GPU,
      index: 1,
      bus: '07:00.0',
      throttle: ['hw_thermal'],
      throttle_bad: true,
      processes: [
        { service: 'vllm-tts', memory_bytes: 13 * 1024 ** 3 },
        { service: 'otros', memory_bytes: 200 * 1024 ** 2 },
      ],
    },
  ],
  power: { gpus_w: 500, cpu_w: 45, estimated_w: 545 },
  clock: { offset_s: 0.001, synced: true },
  connectivity: { internet_ok: true, public_ip_ok: true, sip: [{ registration: 'anura', ok: false }] },
  services: [
    { service: 'app', up: true, healthy: 1, restarts: 0, cpu_cores: 0.05, memory_bytes: 300 * 1024 ** 2 },
    { service: 'vllm-tts', up: false, healthy: null, restarts: 2, cpu_cores: null, memory_bytes: null },
  ],
  probes: [
    { name: 'LLM', kind: 'interna', target: 'http://vllm-llm:8000/health', ok: true, duration_s: 0.004 },
  ],
  saturation: {
    inference: {
      llm: { running: 3, waiting: 2 },
      tts: { running: 1, waiting: 0 },
      stt: { running: 0, waiting: 0 },
    },
    llm_kv_cache_ratio: 0.4,
    calls_active: 7,
    anura_channels_busy: 9,
    anura_channels_total: 10,
    turn_latency_p95_s: 2.1,
  },
};

const NOW: SystemNow = {
  generated_at: 1_793_190_000,
  hosts: [HOST],
  alerts: [
    {
      name: 'ContenedorCaido',
      severity: 'critical',
      state: 'firing',
      summary: 'Servicio vllm-tts sin correr',
      since: '2026-10-28T10:05:00Z',
      host: 'srv',
    },
  ],
};

function stubApi(now: unknown, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input));
      if (url.pathname === '/api/v1/system/now') return Promise.resolve(jsonResponse(now, status));
      if (url.pathname === '/api/v1/system/history')
        return Promise.resolve(jsonResponse({ window: '24h', step_s: 360, start: 0, end: 1, series: {} }));
      return Promise.resolve(jsonResponse([]));
    }),
  );
}

describe('SystemPage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('muestra alertas, cada GPU con su recorte, servicios caídos y la conectividad', async () => {
    stubApi(NOW);
    renderWithProviders(<SystemPage />, { me: ADMIN });
    expect(await screen.findByText('Servicio vllm-tts sin correr')).toBeInTheDocument();
    expect(screen.getByText('Crítica')).toBeInTheDocument();
    expect(screen.getByText('GPU 0')).toBeInTheDocument();
    expect(screen.getByText('GPU 1')).toBeInTheDocument();
    expect(screen.getByText('Recorte térmico (hardware)')).toBeInTheDocument();
    expect(screen.getByText(/vllm-tts 13 GB · escritorio y otros 200 MB/)).toBeInTheDocument();
    expect(screen.getByText('545 W')).toBeInTheDocument();
    expect(screen.getByText('Caído')).toBeInTheDocument();
    expect(screen.getByText('Sin registro')).toBeInTheDocument();
    expect(screen.getByText('4 días')).toBeInTheDocument();
    expect(screen.getByText('encendido hace 3 d 4 h', { exact: false })).toBeInTheDocument();
  });

  it('sin el monitoreo levantado explica cómo levantarlo', async () => {
    stubApi({ detail: 'El monitoreo no está configurado', code: 'monitoring_off' }, 503);
    renderWithProviders(<SystemPage />, { me: ADMIN });
    expect(await screen.findByText('Sin datos del monitoreo')).toBeInTheDocument();
    expect(screen.getByText('make up-monitoring')).toBeInTheDocument();
  });

  it('el colector del host atrasado se avisa', async () => {
    stubApi({ ...NOW, alerts: [], hosts: [{ ...HOST, collector_age_s: 300 }] });
    renderWithProviders(<SystemPage />, { me: ADMIN });
    expect(await screen.findByText(/no actualiza/)).toBeInTheDocument();
    expect(screen.getByText('Sin alertas')).toBeInTheDocument();
  });
});

describe('chartRows', () => {
  it('alinea varias series por tiempo y escala', () => {
    const rows = chartRows(
      [
        {
          key: 'a',
          label: 'GPU 0',
          series: {
            host: 'srv',
            label: '0',
            points: [
              [0, 0.5],
              [60, 0.6],
            ],
          },
        },
        { key: 'b', label: 'GPU 1', series: { host: 'srv', label: '1', points: [[60, 0.1]] } },
      ],
      false,
      100,
    );
    expect(rows).toHaveLength(2);
    expect(rows[1]).toMatchObject({ a: 60, b: 10 });
  });
});
