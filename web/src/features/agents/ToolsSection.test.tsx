import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ADMIN, jsonResponse, renderWithProviders } from '@/test/render';
import { type Draft, toDraft } from './draft';
import { ToolsEditor } from './ToolsSection';

const APP = {
  id: 'app-1',
  slug: 'sugym-gestion',
  name: 'SUGYM · Gestión',
  client_id: 'c-1',
  client_name: 'SUGYM',
  base_url: 'http://app-sugym-gestion:8000',
  version: '0.1.0',
  status: 'ok',
  last_error: null,
  last_health_at: null,
  created_at: '2026-10-12T10:00:00Z',
  views: [],
  tools: [
    { name: 'buscar_alumno', kind: 'read', description: 'Busca alumnos.' },
    { name: 'baja_alumno', kind: 'destructive', description: 'Da de baja.' },
  ],
};

const BASE = toDraft({
  engine: 'assistant',
  agent: { name: 'Asis', role: 'r', language: 'es-AR' },
  objective: { description: 'o' },
  conversation: { opening: 'Hola', rules: [] },
  fields: {},
  completion: { outcomes: [{ id: 'default', label: 'C', when: {}, message: 'Chau' }] },
  tools: [{ app: 'otra-app', tools: ['*'] }],
});

let last: Draft = BASE;

function Harness() {
  const [draft, setDraft] = useState<Draft>(BASE);
  const update = (fn: (d: Draft) => Draft) =>
    setDraft((d) => {
      last = fn(d);
      return last;
    });
  return <ToolsEditor draft={draft} update={update} clientId="c-1" />;
}

afterEach(() => vi.unstubAllGlobals());

describe('ToolsEditor', () => {
  it('prende una app con todas, elige herramientas y saca una app que ya no es del cliente', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse([APP])),
    );
    renderWithProviders(<Harness />, { me: ADMIN });

    expect(await screen.findByText(/La app otra-app ya no es de este cliente/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Sacar' }));
    expect(last.tools).toEqual([]);

    await userEvent.click(screen.getByRole('switch'));
    expect(last.tools).toEqual([{ app: 'sugym-gestion', tools: ['*'] }]);

    await userEvent.click(screen.getByText('Elegir'));
    expect(last.tools).toEqual([{ app: 'sugym-gestion', tools: ['buscar_alumno', 'baja_alumno'] }]);
    await userEvent.click(screen.getByRole('checkbox', { name: /baja_alumno/ }));
    expect(last.tools).toEqual([{ app: 'sugym-gestion', tools: ['buscar_alumno'] }]);
    expect(screen.getByText('Borra')).toBeInTheDocument();
  });
});
