import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { ChatMessage } from '@/api/types';
import { renderWithProviders } from '@/test/render';
import { ChatView } from './ChatView';

describe('ChatView: traza de herramientas', () => {
  it('muestra la herramienta con estado, argumentos y resultado, y el tope de vueltas', () => {
    const messages = [
      {
        role: 'assistant',
        text: 'Tenés turno el lunes.',
        llm: [
          { kind: 'turno', input: '', ms: 300, output: '' },
          {
            kind: 'herramienta',
            input: 'consultar_turnos {"fecha": "2026-10-27"}',
            ms: 120,
            output: '{"ok": true, "data": {"turnos": ["10:00"]}}',
            tool: { slug: 'consultar_turnos', type: 'http', revision: 3, ok: true, status: 200, ms: 118 },
          },
          { kind: 'control', input: 'reservar', ms: 0, output: 'tope de 3 vueltas con herramientas' },
        ],
      },
    ] as ChatMessage[];
    renderWithProviders(<ChatView messages={messages} showLlm />);
    expect(screen.getByText(/1 llamada al modelo, 1 herramienta,/)).toBeInTheDocument();
    expect(screen.getByText('consultar_turnos')).toBeInTheDocument();
    expect(screen.getByText('Funcionó')).toBeInTheDocument();
    expect(screen.getByText('HTTP 200')).toBeInTheDocument();
    expect(screen.getByText(/"fecha": "2026-10-27"/)).toBeInTheDocument();
    expect(screen.getByText('tope de 3 vueltas con herramientas')).toBeInTheDocument();
  });

  it('las herramientas de la plataforma del turno se leen aparte del texto', () => {
    const messages = [
      {
        role: 'assistant',
        text: 'Listo, te paso.',
        llm: [
          {
            kind: 'turno',
            input: 'pasame con ventas',
            ms: 400,
            output: 'Listo, te paso.\n[{"tool": "transfer_call", "arguments": "{\\"area\\": \\"ventas\\"}"}]',
          },
        ],
      },
    ] as ChatMessage[];
    renderWithProviders(<ChatView messages={messages} showLlm />);
    expect(screen.getByText('Listo, te paso.', { selector: 'pre' })).toBeInTheDocument();
    expect(screen.getByText('transfer_call')).toBeInTheDocument();
    expect(screen.getByText(/area: "ventas"/)).toBeInTheDocument();
  });
});
