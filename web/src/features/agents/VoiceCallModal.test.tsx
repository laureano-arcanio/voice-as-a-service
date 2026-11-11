import { act, screen, waitFor } from '@testing-library/react';
import { createLocalAudioTrack } from 'livekit-client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Agent } from '@/api/types';
import { FakeRoom, stubMediaDevices } from '@/features/phone/testing';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { VoiceCallModal } from './VoiceCallModal';

vi.mock('livekit-client', async () => (await import('@/features/phone/testing')).fakeLivekit());

const AGENT = { id: 'ag-1', name: 'Recepción', voice: 'sofia' } as Agent;

const LEG = { n: 1, of: 2, area: 'Ventas', person: 'Ana', no_answer: false, result: null, phases: [['dialing', 1.5]], total: 3 };
const SNAP = {
  v: 1,
  id: 1,
  state: 'running',
  result: null,
  area: 'Ventas',
  elapsed: 4,
  phase: 'ringing',
  phase_elapsed: 2,
  pre: [['preparing', 1]],
  reroutes: [],
  legs: [LEG],
  total: null,
};

beforeEach(() => {
  FakeRoom.all = [];
  stubMediaDevices();
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL((input instanceof Request ? input : new Request(input)).url);
      if (url.pathname === '/api/v1/calls') return jsonResponse({ conversation_id: 'cv-1' }, 201);
      if (url.pathname === '/api/v1/calls/cv-1/join') return jsonResponse({ livekit_url: 'wss://x', token: 't', room: 'r' });
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

async function open() {
  renderWithProviders(<VoiceCallModal agent={AGENT} opened onClose={() => undefined} />, { me: CLIENT_USER });
  await waitFor(() => expect(FakeRoom.all).toHaveLength(1));
  const room = FakeRoom.last();
  await waitFor(() => expect(room.connect).toHaveBeenCalled());
  act(() => room.emit('trackSubscribed', { kind: 'audio', attach: () => document.createElement('audio') }));
  return room;
}

describe('VoiceCallModal: progreso de la derivación', () => {
  it('muestra el intento, la fase y se actualiza con cada snapshot hasta el final', async () => {
    const room = await open();
    expect(screen.queryByText(/Llamando a Ana/)).toBeNull();
    act(() => room.data('handoff_status', SNAP));
    expect(await screen.findByText('Llamando a Ana (Ventas)')).toBeTruthy();
    expect(screen.getByText(/Sonando: 2 s/)).toBeTruthy();

    act(() => room.data('handoff_status', { ...SNAP, phase: null, legs: [{ ...LEG, result: 'no_answer' }] }));
    expect(screen.getByText('Buscando a la siguiente persona (Ventas)')).toBeTruthy();
    expect(screen.getByText(/No atendió/)).toBeTruthy();

    act(() => room.data('handoff_status', { ...SNAP, state: 'connected', result: 'confirmed', phase: null, total: 31, legs: [{ ...LEG, result: 'confirmed' }] }));
    expect(screen.getByText('Conectado con Ana (Ventas)')).toBeTruthy();
    expect(screen.getByText('31 s')).toBeTruthy();
  });

  it('ignora mensajes rotos, de otra versión y de otros temas', async () => {
    const room = await open();
    act(() => room.data('handoff_status', { ...SNAP, v: 9 }));
    act(() => room.data('transcript', SNAP));
    act(() => room.emit('dataReceived', new TextEncoder().encode('{no'), undefined, undefined, 'handoff_status'));
    expect(screen.queryByText(/Llamando a/)).toBeNull();
  });

  it('una derivación nueva (otro id) reemplaza a la anterior y al desconectar se oculta', async () => {
    const room = await open();
    act(() => room.data('handoff_status', { ...SNAP, state: 'failed', result: 'no_answer', total: 20, phase: null }));
    expect(screen.getByText('No se pudo derivar: Nadie atendió')).toBeTruthy();
    act(() => room.data('handoff_status', { ...SNAP, id: 2, legs: [{ ...LEG, person: 'Beto', result: null }] }));
    expect(screen.getByText('Llamando a Beto (Ventas)')).toBeTruthy();
    expect(screen.queryByText(/No se pudo derivar/)).toBeNull();
    act(() => room.emit('disconnected'));
    expect(screen.queryByText(/Llamando a/)).toBeNull();
  });
});

describe('VoiceCallModal: errores de micrófono', () => {
  async function failed() {
    renderWithProviders(<VoiceCallModal agent={AGENT} opened onClose={() => undefined} />, { me: CLIENT_USER });
    return screen.findByRole('alert', undefined, { timeout: 3000 }).catch(() => null);
  }
  const text = () => document.body.textContent ?? '';

  it('sin mediaDevices (HTTP fuera de localhost) pide HTTPS o localhost y no llama al servidor', async () => {
    Object.defineProperty(navigator, 'mediaDevices', { value: undefined, configurable: true });
    await failed();
    await waitFor(() => expect(text()).toContain('hace falta HTTPS o localhost'));
    expect(text()).not.toContain('con el servidor');
    expect(vi.mocked(fetch)).not.toHaveBeenCalled();
  });

  it('permiso negado explica cómo habilitarlo', async () => {
    vi.mocked(createLocalAudioTrack).mockRejectedValueOnce(new DOMException('x', 'NotAllowedError'));
    await failed();
    await waitFor(() => expect(text()).toContain('El micrófono está bloqueado'));
    expect(text()).not.toContain('con el servidor');
  });

  it('sin dispositivo dice que no hay micrófono', async () => {
    vi.mocked(createLocalAudioTrack).mockRejectedValueOnce(new DOMException('x', 'NotFoundError'));
    await failed();
    await waitFor(() => expect(text()).toContain('No encontramos un micrófono'));
  });

  it('un error del servidor sigue diciendo del servidor', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch'); }));
    await failed();
    await waitFor(() => expect(text()).toContain('No se pudo conectar con el servidor.'));
    expect(text()).not.toContain('micrófono está');
  });
});
