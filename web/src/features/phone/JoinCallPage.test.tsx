import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { CallBar } from './CallBar';
import { CallProvider } from './CallProvider';
import { JoinCallPage } from './JoinCallPage';
import { FakeRoom, mockApi, PLAN_OK, stubMediaDevices } from './testing';

vi.mock('livekit-client', async () => (await import('./testing')).fakeLivekit());
vi.mock('./ringtone', () => ({ playRingtone: vi.fn() }));

const DETAIL = {
  id: 'conv-api',
  call: {
    mode: 'directa',
    phone: '+5493515551234',
    client_number: '+541155550000',
    status: 'pendiente',
    started_at: null,
  },
  messages: [],
};

function renderJoin() {
  return renderWithProviders(<></>, {
    me: CLIENT_USER,
    path: '/telefono/llamada/conv-api',
    routes: [
      {
        path: '/telefono/llamada/:id',
        element: (
          <CallProvider>
            <JoinCallPage />
            <CallBar />
          </CallProvider>
        ),
      },
    ],
  });
}

describe('JoinCallPage', () => {
  beforeEach(() => {
    FakeRoom.all = [];
    stubMediaDevices();
    sessionStorage.clear();
  });
  afterEach(() => vi.unstubAllGlobals());

  it('entra a la llamada creada por la API y la barra queda Llamando', async () => {
    mockApi({
      'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK),
      'GET /api/v1/calls/conv-api': () => jsonResponse(DETAIL),
      'POST /api/v1/direct-calls/conv-api/join': () =>
        jsonResponse({ livekit_url: 'wss://lk.test', token: 'tj' }),
    });
    renderJoin();
    await userEvent.click(await screen.findByRole('button', { name: 'Entrar a la llamada' }));
    expect(await screen.findByText('Llamando')).toBeInTheDocument();
    expect(FakeRoom.last().connect).toHaveBeenCalledWith('wss://lk.test', 'tj');
    expect(screen.getByText('Estás en la llamada: la seguís en la barra de abajo.')).toBeInTheDocument();
  });

  it('la llamada de otro usuario: lo dice y no ofrece reintentar', async () => {
    mockApi({
      'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK),
      'GET /api/v1/calls/conv-api': () => jsonResponse(DETAIL),
      'POST /api/v1/direct-calls/conv-api/join': () =>
        jsonResponse({ detail: 'La llamada es de otro usuario', code: 'not_your_call' }, 403),
    });
    renderJoin();
    await userEvent.click(await screen.findByRole('button', { name: 'Entrar a la llamada' }));
    expect((await screen.findAllByText('La llamada es de otro usuario')).length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: 'Volver a intentar' })).not.toBeInTheDocument();
    expect(FakeRoom.all).toHaveLength(0);
  });
});
