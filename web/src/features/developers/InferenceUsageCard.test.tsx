import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { InferenceUsage } from '@/api/types';
import { jsonResponse, renderWithProviders } from '@/test/render';
import { InferenceMeters, InferenceUsageCard } from './InferenceUsageCard';

const USAGE: InferenceUsage = {
  month: '2026-10',
  period_start: '2026-10-01',
  period_end: '2026-11-01',
  rate_limit: 60,
  llm_input_tokens: { used: 900, limit: 1000, remaining: 100 },
  llm_output_tokens: { used: 10, limit: null, remaining: null },
  tts_minutes: { used: 0, limit: 0, remaining: 0 },
  stt_minutes: { used: 2.5, limit: 10, remaining: 7.5 },
  requests: { llm: 4, stt: 2, tts: 0 },
  keys: [
    {
      key_id: 'k1',
      name: 'CRM',
      prefix: 'vaas_abc',
      revoked: false,
      scopes: ['llm', 'stt'],
      requests: { llm: 4, stt: 2, tts: 0 },
      llm_input_tokens: 900,
      llm_output_tokens: 10,
      tts_minutes: 0,
      stt_minutes: 2.5,
    },
  ],
};

describe('InferenceMeters', () => {
  it('muestra cada cupo: con límite, ilimitado y no incluido', () => {
    renderWithProviders(<InferenceMeters usage={USAGE} />);
    expect(
      screen.getByRole('progressbar', { name: 'LLM · tokens de entrada: 90% usado' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('progressbar', { name: 'LLM · tokens de salida: ilimitado' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: 'Transcripción (STT): 25% usado' })).toBeInTheDocument();
    // TTS con límite 0: el plan no lo incluye, sin barra.
    expect(screen.getByText('No incluido en el plan')).toBeInTheDocument();
    expect(screen.queryByRole('progressbar', { name: /Síntesis/ })).not.toBeInTheDocument();
    expect(screen.getByText(/Hasta 60 pedidos por minuto/)).toBeInTheDocument();
    expect(screen.getByText(/4 LLM, 2 STT, 0 TTS/)).toBeInTheDocument();
  });

  it('sin tope de pedidos lo dice', () => {
    renderWithProviders(<InferenceMeters usage={{ ...USAGE, rate_limit: null }} />);
    expect(screen.getByText(/Sin tope de pedidos por minuto/)).toBeInTheDocument();
  });

  it('con el plan cerrado lo dice', () => {
    renderWithProviders(<InferenceMeters usage={{ ...USAGE, rate_limit: 0 }} />);
    expect(screen.getByText(/Tu plan no incluye la API de inferencia/)).toBeInTheDocument();
  });
});

describe('InferenceUsageCard', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('pide el consumo del mes y lo muestra con el desglose por key', async () => {
    const urls: string[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        urls.push(new URL(input instanceof Request ? input.url : String(input)).pathname);
        return Promise.resolve(jsonResponse(USAGE));
      }),
    );
    renderWithProviders(<InferenceUsageCard clientId="c-1" month="2026-10" onMonth={() => {}} />);
    expect(await screen.findByText('Consumo de la API')).toBeInTheDocument();
    expect(await screen.findByText(/Período: 01\/10\/2026 al 31\/10\/2026/)).toBeInTheDocument();
    expect(await screen.findByText('CRM')).toBeInTheDocument();
    expect(screen.getByText('900 / 10')).toBeInTheDocument();
    expect(urls[0]).toBe('/api/v1/clients/c-1/inference-usage');
  });
});
