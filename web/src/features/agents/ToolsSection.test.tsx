import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ClientTool } from '@/api/types';
import { ADMIN, jsonResponse, renderWithProviders } from '@/test/render';
import { type Draft, fromDraft, toDraft } from './draft';
import { ClientToolsEditor } from './ToolsSection';

const TOOL: ClientTool = {
  id: 't-1',
  slug: 'reservar_turno',
  type: 'http',
  definition: { description: 'Reserva un turno.', confirm: true, http: { method: 'POST', url: 'https://x' } },
  revision: 1,
  secrets: [],
  llm_tool: null,
  used_by: [],
  last_test_at: null,
  last_test_ok: null,
  last_test_detail: '',
  created_at: '2026-10-26T10:00:00Z',
  updated_at: '2026-10-26T10:00:00Z',
};

const BASE = toDraft({
  agent: { name: 'Sofía', role: 'r', language: 'es-AR' },
  objective: { description: 'o' },
  conversation: { opening: 'Hola', rules: [] },
  fields: {},
  completion: { outcomes: [{ id: 'default', label: 'C', when: {}, message: 'Chau' }] },
  // Una entrada vieja de apps se descarta al leer.
  tools: [{ tool: 'borrada' }, { app: 'otra-app', tools: ['*'] }],
});

let last: Draft = BASE;

function Harness() {
  const [draft, setDraft] = useState<Draft>(BASE);
  const update = (fn: (d: Draft) => Draft) =>
    setDraft((d) => {
      last = fn(d);
      return last;
    });
  return <ClientToolsEditor draft={draft} update={update} clientId="c-1" />;
}

afterEach(() => vi.unstubAllGlobals());

describe('ClientToolsEditor', () => {
  it('saca una herramienta borrada y edita el tope y el mensaje', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse([TOOL])),
    );
    renderWithProviders(<Harness />, { me: ADMIN });

    expect(await screen.findByText(/La herramienta borrada ya no existe/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Sacar' }));
    expect(last.clientTools).toEqual([]);
    expect(fromDraft(last)).not.toHaveProperty('tools');

    last = { ...last, clientTools: [{ key: 'k', tool: 'reservar_turno' }] };
    expect(fromDraft(last).tools).toEqual([{ tool: 'reservar_turno' }]);
  });

  it('muestra la herramienta elegida con "Pide confirmación" y manda tool_settings', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse([TOOL])),
    );
    last = { ...BASE, clientTools: [{ key: 'k1', tool: 'reservar_turno' }] };
    function H() {
      const [draft, setDraft] = useState<Draft>(last);
      const update = (fn: (d: Draft) => Draft) =>
        setDraft((d) => {
          last = fn(d);
          return last;
        });
      return <ClientToolsEditor draft={draft} update={update} clientId="c-1" />;
    }
    renderWithProviders(<H />, { me: ADMIN });
    expect(await screen.findByText('Pide confirmación')).toBeInTheDocument();
    await userEvent.type(screen.getByRole('textbox', { name: /Vueltas con herramientas/ }), '5');
    await userEvent.type(screen.getByRole('textbox', { name: /Mensaje al llegar al tope/ }), 'Uy, no pude.');
    expect(fromDraft(last).tool_settings).toEqual({ max_calls_per_turn: 5, limit_message: 'Uy, no pude.' });
  });
});
