import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { useEffect, useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ChatMessage, HandoffArea } from '@/api/types';
import { ChatView } from '@/features/calls/ChatView';
import { ADMIN, CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { theme } from '@/theme';
import { type Draft, fromDraft, stableJson, toDraft } from './draft';
import { HandoffEditor } from './HandoffSection';

const VENTAS: HandoffArea = {
  id: 'a1',
  client_id: 'c-1',
  name: 'Ventas',
  description: 'Precios y presupuestos',
  active: true,
  member_ids: ['m1'],
  strategy: 'sequential',
  ring_seconds: 20,
  schedule: null,
  schedule_text: 'los lunes de 09:00 a 18:00',
  open_now: false,
  fallback: 'take_message',
  on_person_hangup: 'resume',
  return_digits: '2',
  wa_reply_minutes: 10,
  messages: {},
  created_at: '2026-10-20T12:00:00Z',
};
const ADMINISTRACION: HandoffArea = {
  ...VENTAS,
  id: 'a2',
  name: 'Administración',
  description: '',
  active: false,
};

const DEF = {
  id: 'a',
  version: 1,
  agent: { name: 'S', role: 'r', language: 'es-AR' },
  objective: { description: 'x' },
  conversation: { opening: 'Hola', rules: [] },
  knowledge: '',
  fields: { nombre: { priority: 10, description: 'n', type: 'string', required: true, question: '?' } },
  completion: {
    when: 'all_required_fields_completed',
    outcomes: [{ id: 'ok', label: 'ok', when: {}, message: 'm', goal: true }],
  },
};

const latest = { current: null as unknown as Draft };

function Harness({ initial, errors }: { initial: Draft; errors?: { path: string; message: string }[] }) {
  const [draft, setDraft] = useState(initial);
  useEffect(() => {
    latest.current = draft;
  }, [draft]);
  return <HandoffEditor draft={draft} update={(fn) => setDraft(fn)} clientId="c-1" errors={errors} />;
}

function mockApi(areas: HandoffArea[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: Request | string) => {
      const url = new URL(typeof input === 'string' ? input : input.url, 'http://x');
      if (url.pathname === '/api/v1/hold-music') return jsonResponse({ tracks: ['default', 'piano'] });
      if (url.pathname === '/api/v1/handoff-areas') return jsonResponse(areas);
      return jsonResponse({ detail: 'no' }, 404);
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('draft: handoff', () => {
  it('sin handoff y sin áreas no lo manda; con handoff previo lo conserva igual', () => {
    expect(fromDraft(toDraft(DEF))).not.toHaveProperty('handoff');
    const withHandoff = {
      ...DEF,
      handoff: {
        areas: [{ area_id: 'a1', when: 'Si pregunta precios' }],
        hold_music: { enabled: false, track: 'piano', volume: 0.55 },
      },
    };
    expect(fromDraft(toDraft(withHandoff)).handoff).toEqual(withHandoff.handoff);
    const empty = {
      ...DEF,
      handoff: { areas: [], hold_music: { enabled: true, track: 'default', volume: 0.3 } },
    };
    expect(stableJson(fromDraft(toDraft(empty)))).toBe(stableJson({ ...empty, version: 1 }));
  });
});

describe('HandoffEditor', () => {
  it('marca un área, pone cuándo, y ajusta la música de espera', async () => {
    mockApi([VENTAS, ADMINISTRACION]);
    renderWithProviders(<Harness initial={toDraft(DEF)} />, { me: CLIENT_USER });

    expect(await screen.findByText('Ventas')).toBeInTheDocument();
    expect(screen.getAllByText('Los lunes de 09:00 a 18:00')).toHaveLength(2);
    expect(screen.getByText('Inactiva')).toBeInTheDocument();
    // Sin áreas, no hay música para elegir.
    expect(screen.queryByText('Música de espera')).not.toBeInTheDocument();

    const [ventas] = screen.getAllByRole('checkbox', { name: 'Puede pasarle llamadas' });
    await userEvent.click(ventas!);
    const when = screen.getByRole('textbox', { name: /Cuándo pasarla/ });
    expect(when).toHaveAttribute('placeholder', 'Precios y presupuestos');
    await userEvent.type(when, 'Si pide un presupuesto');

    expect(screen.getByRole('switch', { name: /Música de espera/ })).toBeChecked();
    expect(screen.getByRole('textbox', { name: 'Tema' })).toHaveValue('Música de espera estándar');
    await userEvent.click(screen.getByRole('switch', { name: /Música de espera/ }));
    expect(screen.queryByRole('textbox', { name: 'Tema' })).not.toBeInTheDocument();

    expect(fromDraft(latest.current).handoff).toEqual({
      areas: [{ area_id: 'a1', when: 'Si pide un presupuesto' }],
      hold_music: { enabled: false, track: 'default', volume: 0.3 },
    });

    await userEvent.click(screen.getAllByRole('checkbox', { name: 'Puede pasarle llamadas' })[0]!);
    expect(fromDraft(latest.current)).not.toHaveProperty('handoff');
  });

  it('sin áreas lleva a Equipo', async () => {
    mockApi([]);
    renderWithProviders(<Harness initial={toDraft(DEF)} />, { me: ADMIN });
    expect(await screen.findByText(/todavía no tiene áreas/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Crealas en Equipo' })).toHaveAttribute(
      'href',
      '/team?client=c-1',
    );
  });

  it('muestra los errores del guardado en su campo y el área borrada', async () => {
    mockApi([VENTAS]);
    const initial = toDraft({
      ...DEF,
      handoff: {
        areas: [
          { area_id: 'a1', when: '' },
          { area_id: 'vieja', when: '' },
        ],
        hold_music: { enabled: true, track: 'jazz', volume: 0.3 },
      },
    });
    renderWithProviders(
      <Harness
        initial={initial}
        errors={[
          { path: 'handoff.areas.1.area_id', message: 'El área no existe o es de otro cliente.' },
          { path: 'handoff.hold_music.track', message: "No hay un tema de espera 'jazz'" },
        ]}
      />,
      { me: CLIENT_USER },
    );
    expect(await screen.findByText(/El área no existe o es de otro cliente/)).toBeInTheDocument();
    expect(screen.getByText("No hay un tema de espera 'jazz'")).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Sacar' }));
    expect(latest.current.handoff.areas).toEqual([{ areaId: 'a1', when: '' }]);
  });
});

describe('ChatView con derivación', () => {
  it('marca a la persona del equipo y el comienzo del tramo', () => {
    const at = '2026-10-23T12:00:00Z';
    const messages = [
      { role: 'assistant', text: 'Te paso con Ventas.', at },
      { role: 'user', text: 'Hola', at, handoff_leg: 'l1' },
      { role: 'assistant', text: 'Hola, soy Ana.', at, handoff_leg: 'l1', person: 'Ana Pérez' },
      { role: 'assistant', text: '¿Algo más?', at },
    ] as ChatMessage[];
    render(
      <MantineProvider theme={theme}>
        <ChatView messages={messages} agentLabel="Sofía" />
      </MantineProvider>,
    );
    expect(screen.getAllByText('Sofía')).toHaveLength(2);
    const [start, end] = screen.getAllByRole('separator');
    expect(start).toHaveTextContent('Llamada con Ana Pérez');
    expect(end).toHaveTextContent('Vuelve Sofía');
    expect(screen.getByText('Ana Pérez (equipo)')).toBeInTheDocument();
  });
});
