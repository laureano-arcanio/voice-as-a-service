import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AgentDetail } from '@/api/types';
import { CATALOG } from '@/components/variables/fixtures';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { AgentTestPanel } from './AgentTestPanel';
import { stubMediaDevices } from '@/features/phone/testing';

// Sin micrófono ni servidor de voz en jsdom: lo justo para que el modal llegue a pedir la llamada.
vi.mock('livekit-client', () => ({
  Room: class {
    on() {}
    registerTextStreamHandler() {}
    async connect() {}
    async startAudio() {}
    disconnect() {}
    localParticipant = { identity: 'u', trackPublications: new Map(), publishTrack: async () => {} };
  },
  RoomEvent: {},
  Track: { Kind: { Audio: 'audio' } },
  createLocalAudioTrack: async () => ({ stop() {} }),
}));

const AGENT: AgentDetail = {
  id: 'ag-1',
  client_id: 'c-1',
  name: 'Recepción',
  slug: 'recepcion',
  description: '',
  version: 1,
  archived: false,
  voice: 'sofia',
  objective: '',
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
  definition: {},
} as AgentDetail;

const STATE = { status: 'active', fields: {}, messages: [] };

function mockApi() {
  const calls: { method: string; path: string; body: Record<string, unknown> | null }[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const url = new URL(req.url);
      const text = req.method === 'GET' ? '' : await req.clone().text();
      calls.push({ method: req.method, path: url.pathname, body: text ? JSON.parse(text) : null });
      if (url.pathname === '/api/v1/variables/catalog') return jsonResponse(CATALOG);
      if (req.method === 'POST' && url.pathname === '/api/v1/conversations')
        return jsonResponse({ conversation_id: 'cv-1', state: STATE }, 201);
      if (req.method === 'POST' && url.pathname === '/api/v1/calls') return jsonResponse({ conversation_id: 'cv-2' }, 201);
      if (url.pathname === '/api/v1/calls/cv-2/join')
        return jsonResponse({ livekit_url: 'wss://x', token: 't', room: 'r' });
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return calls;
}

// jsdom no trae mediaDevices: el modal de voz lo pide antes de abrir el micrófono.
beforeEach(() => {
  stubMediaDevices();
  window.sessionStorage.clear();
});
afterEach(() => vi.unstubAllGlobals());

describe('AgentTestPanel', () => {
  it('el chat manda el número simulado y workflows al empezar', async () => {
    const calls = mockApi();
    renderWithProviders(<AgentTestPanel agent={AGENT} />, { me: CLIENT_USER });
    await userEvent.type(screen.getByLabelText('Número de quien llama (simulado)'), ' +5491155551234 ');
    await userEvent.click(screen.getByRole('button', { name: 'Empezar conversación' }));
    await waitFor(() => expect(calls.some((c) => c.path === '/api/v1/conversations')).toBe(true));
    expect(calls.find((c) => c.path === '/api/v1/conversations')?.body).toEqual({
      agent_id: 'ag-1',
      caller_phone: '+5491155551234',
      workflows: true,
    });
  });

  it('sin número, el chat no manda caller_phone', async () => {
    const calls = mockApi();
    renderWithProviders(<AgentTestPanel agent={AGENT} />, { me: CLIENT_USER });
    await userEvent.click(screen.getByRole('button', { name: 'Empezar conversación' }));
    await waitFor(() => expect(calls.some((c) => c.path === '/api/v1/conversations')).toBe(true));
    expect(calls.find((c) => c.path === '/api/v1/conversations')?.body).toEqual({
      agent_id: 'ag-1',
      workflows: true,
    });
  });

  it('Hablar crea la llamada de prueba con el número y workflows', async () => {
    const calls = mockApi();
    renderWithProviders(<AgentTestPanel agent={AGENT} />, { me: CLIENT_USER });
    await userEvent.type(screen.getByLabelText('Número de quien llama (simulado)'), '+5491155551234');
    await userEvent.click(screen.getByRole('button', { name: 'Hablar' }));
    await waitFor(() => expect(calls.some((c) => c.path === '/api/v1/calls' && c.method === 'POST')).toBe(true));
    expect(calls.find((c) => c.path === '/api/v1/calls')?.body).toEqual({
      agent_id: 'ag-1',
      caller_phone: '+5491155551234',
      workflows: true,
    });
  });

  it('el aviso aparece solo si el agente tiene pre-call o post-call', () => {
    const { unmount } = renderWithProviders(<AgentTestPanel agent={AGENT} />, { me: CLIENT_USER });
    expect(screen.queryByText(/ejecutan las herramientas automáticas/)).not.toBeInTheDocument();
    unmount();
    const withPost = { ...AGENT, definition: { workflows: { post_call: { tool: 'x' } } } } as AgentDetail;
    renderWithProviders(<AgentTestPanel agent={withPost} />, { me: CLIENT_USER });
    expect(screen.getAllByText(/ejecutan las herramientas automáticas/).length).toBeGreaterThan(0);
  });

  it('agente archivado: no se puede hablar', () => {
    renderWithProviders(<AgentTestPanel agent={{ ...AGENT, archived: true }} />, { me: CLIENT_USER });
    expect(screen.getByRole('button', { name: 'Hablar' })).toBeDisabled();
  });

  it('los valores de prueba prellenados viajan en el chat y en la llamada', async () => {
    const calls = mockApi();
    const withVars = {
      ...AGENT,
      definition: {
        prompt: 'La deuda es {{deuda}}.',
        variables: [{ name: 'deuda', default: '1000', description: 'Lo que debe' }],
      },
    } as AgentDetail;
    renderWithProviders(<AgentTestPanel agent={withVars} />, { me: CLIENT_USER });
    // La fila de la variable declarada, con su default.
    expect(await screen.findByLabelText('Valor de deuda')).toHaveValue('1000');
    await userEvent.click(screen.getByRole('button', { name: 'Empezar conversación' }));
    await waitFor(() => expect(calls.some((c) => c.path === '/api/v1/conversations')).toBe(true));
    expect(calls.find((c) => c.path === '/api/v1/conversations')?.body).toEqual({
      agent_id: 'ag-1',
      variables: { deuda: '1000' },
      workflows: true,
    });
    await userEvent.click(screen.getByRole('button', { name: 'Hablar' }));
    await waitFor(() => expect(calls.some((c) => c.path === '/api/v1/calls' && c.method === 'POST')).toBe(true));
    expect(calls.find((c) => c.path === '/api/v1/calls')?.body).toEqual({
      agent_id: 'ag-1',
      variables: { deuda: '1000' },
      workflows: true,
    });
  });
});
