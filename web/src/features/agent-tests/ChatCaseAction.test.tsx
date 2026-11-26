import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ChatMessage } from '@/api/types';
import { renderWithProviders } from '@/test/render';
import { ChatView } from '@/features/calls/ChatView';

const messages = [
  { role: 'assistant', text: 'Hola, soy Sofía.' },
  { role: 'user', text: '¿Hay salidas a Castelli?' },
  { role: 'assistant', text: 'Hay dos salidas.' },
  { role: 'assistant', text: 'Te paso con una persona.', person: 'Ana' },
  { role: 'user', text: 'Hola', handoff_leg: 'leg-1' },
  { role: 'assistant', text: 'Hola, te atiende Ana.', person: 'Ana', handoff_leg: 'leg-1' },
] as ChatMessage[];

describe('ChatView: crear caso de prueba', () => {
  it('la acción aparece en la respuesta del agente después de un mensaje del usuario', () => {
    const onCreateCase = vi.fn();
    renderWithProviders(<ChatView messages={messages} onCreateCase={onCreateCase} />);
    const actions = screen.getAllByRole('button', { name: 'Crear caso de prueba' });
    // Solo la respuesta a «¿Hay salidas a Castelli?»: no la apertura, ni lo que habló una persona del equipo.
    expect(actions).toHaveLength(1);
    actions[0].click();
    expect(onCreateCase).toHaveBeenCalledWith(1);
  });

  it('sin la prop no cambia nada', () => {
    renderWithProviders(<ChatView messages={messages} />);
    expect(screen.queryByRole('button', { name: 'Crear caso de prueba' })).not.toBeInTheDocument();
  });
});
