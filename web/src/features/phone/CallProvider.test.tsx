import { act, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { CallBar } from './CallBar';
import { CallProvider } from './CallProvider';
import { useDirectCall } from './context';
import { FakeRoom, fakeMic, mockApi, PLAN_OK, stubMediaDevices } from './testing';

vi.mock('livekit-client', async () => (await import('./testing')).fakeLivekit());
vi.mock('./ringtone', () => ({ playRingtone: vi.fn() }));

const STARTED = {
  conversation_id: 'conv-1',
  room: 'direct-conv-1',
  status: 'pendiente',
  livekit_url: 'wss://lk.test',
  token: 'tok-1',
  join_url: null,
};

const RING = {
  conversation_id: 'conv-in',
  phone: '+5493515550099',
  contact_id: 'k9',
  contact_name: 'Juan Pérez',
  number_e164: '+541155550000',
  number_label: 'Ventas',
  started_at: '2026-10-27T15:00:00Z',
};

function Harness() {
  const c = useDirectCall();
  return (
    <button
      onClick={() =>
        void c.call(
          { contactId: 'k1', phone: '+5493515551234', name: 'Ana Pérez', fromLabel: '+541155550000' },
          'n1',
        )
      }
    >
      llamar a Ana
    </button>
  );
}

function renderPhone(me = CLIENT_USER) {
  return renderWithProviders(<></>, {
    me,
    routes: [
      {
        path: '*',
        element: (
          <CallProvider>
            <Harness />
            <CallBar />
          </CallProvider>
        ),
      },
    ],
  });
}

function setAvailable(on: boolean) {
  if (on) sessionStorage.setItem('atentina.phone.available', '1');
  else sessionStorage.removeItem('atentina.phone.available');
}

describe('CallProvider', () => {
  beforeEach(() => {
    FakeRoom.all = [];
    stubMediaDevices();
    sessionStorage.clear();
  });
  afterEach(() => vi.unstubAllGlobals());

  it('llama, sigue los estados del worker, marca con el teclado y corta', async () => {
    const seen = mockApi({
      'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK),
      'POST /api/v1/direct-calls': () => jsonResponse(STARTED, 201),
      'POST /api/v1/calls/conv-1/hangup': () => jsonResponse({ hung_up: true }),
    });
    renderPhone();
    await userEvent.click(await screen.findByRole('button', { name: 'llamar a Ana' }));

    expect(await screen.findByText('Llamando')).toBeInTheDocument();
    expect(seen.find((s) => s.method === 'POST' && s.path === '/api/v1/direct-calls')?.body).toEqual({
      contact_id: 'k1',
      phone: null,
      from_number_id: 'n1',
      confirm_opted_out: false,
    });
    const room = FakeRoom.last();
    expect(room.connect).toHaveBeenCalledWith('wss://lk.test', 'tok-1');
    // LiveKit no corta solo al salir de la página (beforeunload se puede cancelar; freeze en el celular).
    expect(room.options.disconnectOnPageLeave).toBe(false);
    expect(room.localParticipant.publishTrack).toHaveBeenCalled();
    expect(sessionStorage.getItem('atentina.phone.call')).toBe('conv-1');
    expect(screen.getByText('Ana Pérez')).toBeInTheDocument();

    act(() => room.data('call_status', { state: 'ringing' }));
    expect(await screen.findByText('Sonando')).toBeInTheDocument();
    act(() => room.data('call_status', { state: 'active' }));
    expect(await screen.findByText('En curso')).toBeInTheDocument();
    act(() => room.data('transcript', { role: 'user', text: 'Hola, ¿quién habla?' }));
    expect(await screen.findByText(/Hola, ¿quién habla\?/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Teclado' }));
    // jsdom no mide la barra: el desplegable queda con display none (hideDetached), por eso `hidden`.
    await userEvent.click(await screen.findByRole('button', { name: '5', hidden: true }));
    await userEvent.click(screen.getByRole('button', { name: '#', hidden: true }));
    expect(room.localParticipant.publishDtmf).toHaveBeenCalledWith(5, '5');
    expect(room.localParticipant.publishDtmf).toHaveBeenCalledWith(11, '#');
    expect(screen.queryByRole('button', { name: '*', hidden: true })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Cortar' }));
    expect(await screen.findByText('Terminada')).toBeInTheDocument();
    expect(seen.some((s) => s.method === 'POST' && s.path === '/api/v1/calls/conv-1/hangup')).toBe(true);
    expect(room.disconnect).toHaveBeenCalled();
    expect(screen.getByRole('link', { name: 'Ver la conversación' })).toHaveAttribute(
      'href',
      '/calls/conv-1',
    );
    expect(sessionStorage.getItem('atentina.phone.call')).toBeNull();
  });

  it('contacto dado de baja: pide confirmación y reintenta con confirm_opted_out', async () => {
    let posts = 0;
    const seen = mockApi({
      'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK),
      'POST /api/v1/direct-calls': () =>
        ++posts === 1
          ? jsonResponse({ detail: 'Este contacto pidió no recibir llamadas', code: 'opted_out' }, 409)
          : jsonResponse(STARTED, 201),
    });
    renderPhone();
    await userEvent.click(await screen.findByRole('button', { name: 'llamar a Ana' }));

    expect(
      await screen.findByText('Este contacto pidió no recibir llamadas. ¿Llamar igual?'),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Llamar igual' }));

    await waitFor(() => expect(FakeRoom.all).toHaveLength(1));
    const bodies = seen.filter((s) => s.path === '/api/v1/direct-calls').map((s) => s.body);
    expect(bodies).toEqual([
      expect.objectContaining({ confirm_opted_out: false }),
      expect.objectContaining({ confirm_opted_out: true }),
    ]);
  });

  it('sin confirmar la baja no llama', async () => {
    const seen = mockApi({
      'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK),
      'POST /api/v1/direct-calls': () => jsonResponse({ detail: 'Baja', code: 'opted_out' }, 409),
    });
    renderPhone();
    await userEvent.click(await screen.findByRole('button', { name: 'llamar a Ana' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Cancelar' }));
    await waitFor(() => expect(screen.queryByText('Conectando')).not.toBeInTheDocument());
    expect(seen.filter((s) => s.path === '/api/v1/direct-calls')).toHaveLength(1);
    expect(FakeRoom.all).toHaveLength(0);
  });

  it('termina cuando el worker avisa que no atendió', async () => {
    mockApi({
      'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK),
      'POST /api/v1/direct-calls': () => jsonResponse(STARTED, 201),
    });
    renderPhone();
    await userEvent.click(await screen.findByRole('button', { name: 'llamar a Ana' }));
    await screen.findByText('Llamando');
    act(() => FakeRoom.last().data('call_status', { state: 'ended', result: 'no_answer' }));
    expect(await screen.findByText('Terminada · no atendió')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Cerrar' }));
    expect(screen.queryByText('Terminada · no atendió')).not.toBeInTheDocument();
  });

  it('número bloqueado: el motivo en la barra, sin room', async () => {
    mockApi({
      'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK),
      'POST /api/v1/direct-calls': () => jsonResponse({ detail: 'Bloqueado', code: 'blocked_number' }, 403),
    });
    renderPhone();
    await userEvent.click(await screen.findByRole('button', { name: 'llamar a Ana' }));
    expect(await screen.findByText('El número está bloqueado')).toBeInTheDocument();
    expect(FakeRoom.all).toHaveLength(0);
  });

  it('micrófono bloqueado: lo dice y no llama', async () => {
    const lk = await import('livekit-client');
    vi.mocked(lk.createLocalAudioTrack).mockRejectedValueOnce(new DOMException('no', 'NotAllowedError'));
    const seen = mockApi({ 'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK) });
    renderPhone();
    await userEvent.click(await screen.findByRole('button', { name: 'llamar a Ana' }));
    expect(await screen.findByText('El micrófono está bloqueado')).toBeInTheDocument();
    expect(seen.some((s) => s.path === '/api/v1/direct-calls')).toBe(false);
  });

  it('al recargar o cerrar la pestaña sale de la room (pagehide), no al pedir confirmación', async () => {
    mockApi({
      'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK),
      'POST /api/v1/direct-calls': () => jsonResponse(STARTED, 201),
    });
    renderPhone();
    await userEvent.click(await screen.findByRole('button', { name: 'llamar a Ana' }));
    await screen.findByText('Llamando');
    const room = FakeRoom.last();
    act(() => void window.dispatchEvent(new Event('beforeunload')));
    expect(room.disconnect).not.toHaveBeenCalled();
    act(() => void window.dispatchEvent(new Event('pagehide')));
    expect(room.disconnect).toHaveBeenCalled();
  });

  it('si no conecta con LiveKit: el motivo en la barra y corta la saliente', async () => {
    const seen = mockApi({
      'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK),
      'POST /api/v1/direct-calls': () => jsonResponse(STARTED, 201),
      'POST /api/v1/calls/conv-1/hangup': () => jsonResponse({ hung_up: true }),
    });
    // Como livekit-client 2.22: emite Disconnected y después rechaza connect.
    FakeRoom.connectError = new Error('could not establish pc connection');
    renderPhone();
    await userEvent.click(await screen.findByRole('button', { name: 'llamar a Ana' }));
    expect(await screen.findByText('No pudimos conectar la llamada')).toBeInTheDocument();
    await waitFor(() =>
      expect(seen.some((s) => s.method === 'POST' && s.path === '/api/v1/calls/conv-1/hangup')).toBe(true),
    );
  });

  it('al recargar con una llamada en curso ofrece volver a entrar', async () => {
    sessionStorage.setItem('atentina.phone.call', 'conv-1');
    const seen = mockApi({
      'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK),
      'GET /api/v1/calls/conv-1': () =>
        jsonResponse({
          id: 'conv-1',
          call: {
            mode: 'directa',
            phone: '+5493515551234',
            client_number: '+541155550000',
            status: 'en_curso',
            started_at: '2026-10-27T15:00:00Z',
          },
        }),
      'POST /api/v1/direct-calls/conv-1/join': () =>
        jsonResponse({ livekit_url: 'wss://lk.test', token: 'tok-2' }),
    });
    renderPhone();
    expect(await screen.findByText('Tenés una llamada en curso')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Volver a entrar' }));
    expect(await screen.findByText('En curso')).toBeInTheDocument();
    expect(FakeRoom.last().connect).toHaveBeenCalledWith('wss://lk.test', 'tok-2');
    expect(seen.some((s) => s.method === 'POST' && s.path === '/api/v1/direct-calls/conv-1/join')).toBe(true);
  });

  it('admin en soporte: Disponible apagado y sin llamar', async () => {
    const seen = mockApi({ 'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK) });
    renderPhone({ ...CLIENT_USER, support: true });
    const sw = await screen.findByRole('switch', { name: 'Disponible' });
    expect(sw).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'llamar a Ana' }));
    expect(seen.some((s) => s.path === '/api/v1/direct-calls')).toBe(false);
  });
});

describe('Timbre', () => {
  beforeEach(() => {
    FakeRoom.all = [];
    stubMediaDevices();
    sessionStorage.clear();
    setAvailable(true);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    setAvailable(false);
  });

  it('Disponible manda el pulso y muestra el timbre; Atender entra En curso', async () => {
    const seen = mockApi({
      'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK),
      'PUT /api/v1/me/presence': () => jsonResponse({ available: true, last_seen: '2026-10-27T15:00:00Z' }),
      'GET /api/v1/me/ringing': () => jsonResponse([RING]),
      'POST /api/v1/direct-calls/conv-in/answer': () =>
        jsonResponse({ livekit_url: 'wss://lk.test', token: 'tok-in' }),
    });
    renderPhone();
    expect(await screen.findByText('Llamada entrante')).toBeInTheDocument();
    expect(screen.getByText('Juan Pérez')).toBeInTheDocument();
    expect(screen.getByText(/a Ventas/)).toBeInTheDocument();
    expect(seen.find((s) => s.method === 'PUT' && s.path === '/api/v1/me/presence')?.body).toEqual({
      available: true,
    });

    await userEvent.click(screen.getByRole('button', { name: 'Atender' }));
    expect(await screen.findByText('En curso')).toBeInTheDocument();
    expect(FakeRoom.last().connect).toHaveBeenCalledWith('wss://lk.test', 'tok-in');
    expect(sessionStorage.getItem('atentina.phone.call')).toBe('conv-in');
  });

  it('al salir del panel suelta la room y el micrófono y deja de estar Disponible', async () => {
    const seen = mockApi({
      'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK),
      'PUT /api/v1/me/presence': () => jsonResponse({ available: true, last_seen: null }),
      'GET /api/v1/me/ringing': () => jsonResponse([RING]),
      'POST /api/v1/direct-calls/conv-in/answer': () =>
        jsonResponse({ livekit_url: 'wss://lk.test', token: 'tok-in' }),
    });
    const view = renderPhone();
    await userEvent.click(await screen.findByRole('button', { name: 'Atender' }));
    expect(await screen.findByText('En curso')).toBeInTheDocument();
    const room = FakeRoom.last();
    fakeMic.stop.mockClear();
    view.unmount();
    expect(room.disconnect).toHaveBeenCalled();
    expect(fakeMic.stop).toHaveBeenCalled();
    await waitFor(() =>
      expect(seen.filter((s) => s.method === 'PUT').map((s) => s.body)).toContainEqual({ available: false }),
    );
  });

  it('micrófono bloqueado al atender: el motivo en el timbre, que sigue sonando', async () => {
    const lk = await import('livekit-client');
    vi.mocked(lk.createLocalAudioTrack).mockRejectedValueOnce(new DOMException('no', 'NotAllowedError'));
    const seen = mockApi({
      'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK),
      'PUT /api/v1/me/presence': () => jsonResponse({ available: true, last_seen: null }),
      'GET /api/v1/me/ringing': () => jsonResponse([RING]),
    });
    renderPhone();
    await userEvent.click(await screen.findByRole('button', { name: 'Atender' }));
    expect(await screen.findByText('El micrófono está bloqueado')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Atender' })).toBeInTheDocument();
    expect(seen.some((s) => s.path === '/api/v1/direct-calls/conv-in/answer')).toBe(false);
  });

  it('si otro la atendió primero: "La atendió otra persona"', async () => {
    mockApi({
      'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK),
      'PUT /api/v1/me/presence': () => jsonResponse({ available: true, last_seen: null }),
      'GET /api/v1/me/ringing': () => jsonResponse([RING]),
      'POST /api/v1/direct-calls/conv-in/answer': () =>
        jsonResponse({ detail: 'Otra persona ya atendió la llamada', code: 'already_answered' }, 409),
    });
    renderPhone();
    await userEvent.click(await screen.findByRole('button', { name: 'Atender' }));
    expect(await screen.findByText('La atendió otra persona')).toBeInTheDocument();
    expect(FakeRoom.all).toHaveLength(0);
  });

  it('Rechazar avisa a la API y apaga el timbre; apagar Disponible manda available=false', async () => {
    const seen = mockApi({
      'GET /api/v1/plan/features': () => jsonResponse(PLAN_OK),
      'PUT /api/v1/me/presence': () => jsonResponse({ available: true, last_seen: null }),
      'GET /api/v1/me/ringing': () => jsonResponse([RING]),
      'POST /api/v1/direct-calls/conv-in/decline': () => new Response(null, { status: 204 }),
    });
    renderPhone();
    await userEvent.click(await screen.findByRole('button', { name: 'Rechazar' }));
    await waitFor(() => expect(screen.queryByText('Llamada entrante')).not.toBeInTheDocument());
    expect(seen.some((s) => s.method === 'POST' && s.path === '/api/v1/direct-calls/conv-in/decline')).toBe(
      true,
    );

    await userEvent.click(screen.getByRole('switch', { name: 'Disponible' }));
    await waitFor(() =>
      expect(seen.filter((s) => s.method === 'PUT').map((s) => s.body)).toContainEqual({ available: false }),
    );
  });
});
