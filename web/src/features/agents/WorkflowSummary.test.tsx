import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { Definition } from '@/api/types';
import { CLIENT_USER, renderWithProviders } from '@/test/render';
import { WorkflowSummary } from './WorkflowSummary';

const DEF = {
  id: 'a',
  version: 4,
  agent: { name: 'Sofía', language: 'es-AR', voice: 'sofia' },
  prompt: '# Identidad\nSos Sofía.\n\n# Objetivo\nCobrar.',
  first_message: 'Hola, {{nombre}}',
  variables: [{ name: 'deuda', default: '1000', description: 'Lo que debe' }],
  analysis: {
    summary: true,
    instructions: 'Extraé lo que dijo.',
    fields: [{ name: 'quiere_pagar', label: 'Quiere pagar', description: 'Si dijo que sí', type: 'boolean' }],
    outcomes: [{ id: 'pago', label: 'Promete pagar', when: { quiere_pagar: true }, goal: true }],
  },
} as Definition;

describe('WorkflowSummary', () => {
  it('muestra prompt, variables y análisis, sin obligatorio ni mensaje de cierre', () => {
    renderWithProviders(<WorkflowSummary definition={DEF} />, { me: CLIENT_USER });
    expect(screen.getByText(/Sos Sofía/)).toBeInTheDocument();
    expect(screen.getByText('Variables')).toBeInTheDocument();
    expect(screen.getByText('{{deuda}}')).toBeInTheDocument();
    expect(screen.getByText('Lo que debe')).toBeInTheDocument();
    expect(screen.getByText('Análisis al terminar')).toBeInTheDocument();
    expect(screen.getByText('Sí, un párrafo')).toBeInTheDocument();
    expect(screen.getByText('Quiere pagar')).toBeInTheDocument();
    expect(screen.queryByText(/Obligatorio/)).toBeNull();
    expect(screen.queryByText(/Mensaje de cierre/)).toBeNull();
  });

  it('sin variables no muestra la tabla', () => {
    renderWithProviders(<WorkflowSummary definition={{ ...DEF, variables: undefined }} />, {
      me: CLIENT_USER,
    });
    expect(screen.queryByText('Variables')).toBeNull();
  });
});
