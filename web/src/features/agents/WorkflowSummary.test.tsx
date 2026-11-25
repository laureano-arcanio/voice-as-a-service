import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { Definition } from '@/api/types';
import { CLIENT_USER, renderWithProviders } from '@/test/render';
import { WorkflowSummary } from './WorkflowSummary';

const ANALYSIS = {
  summary: true,
  instructions: 'Extraé lo que dijo.',
  fields: [{ name: 'quiere_pagar', label: 'Quiere pagar', description: 'Si dijo que sí', type: 'boolean' }],
};
const DEF = {
  id: 'a',
  version: 4,
  agent: { name: 'Sofía', language: 'es-AR', voice: 'sofia' },
  prompt: '# Identidad\nSos Sofía.\n\n# Objetivo\nCobrar.',
  first_message: 'Hola, {{nombre}}',
  variables: [{ name: 'deuda', default: '1000', description: 'Lo que debe' }],
  analysis: ANALYSIS,
} as Definition;

describe('WorkflowSummary', () => {
  it('muestra prompt, variables y análisis, sin resultados ni mensaje de cierre', () => {
    renderWithProviders(<WorkflowSummary definition={DEF} />, { me: CLIENT_USER });
    expect(screen.getByText(/Sos Sofía/)).toBeInTheDocument();
    expect(screen.getByText('Variables')).toBeInTheDocument();
    expect(screen.getByText('{{deuda}}')).toBeInTheDocument();
    expect(screen.getByText('Lo que debe')).toBeInTheDocument();
    expect(screen.getByText('Análisis al terminar')).toBeInTheDocument();
    expect(screen.getByText('Sí, un párrafo')).toBeInTheDocument();
    expect(screen.getByText('Quiere pagar')).toBeInTheDocument();
    expect(screen.queryByText('Resultados')).toBeNull();
    expect(screen.queryByText(/Mensaje de cierre/)).toBeNull();
  });

  it('prompt del análisis vacío: el de la plataforma, y las instrucciones viejas con su nota', () => {
    renderWithProviders(<WorkflowSummary definition={DEF} />, { me: CLIENT_USER });
    expect(screen.getByText('Prompt del análisis')).toBeInTheDocument();
    expect(screen.getByText('El de la plataforma')).toBeInTheDocument();
    expect(
      screen.getByText(/Instrucciones de una versión anterior/),
    ).toBeInTheDocument();
    expect(screen.getByText('Extraé lo que dijo.')).toBeInTheDocument();
  });

  it('con prompt del análisis propio muestra sus primeras líneas, sin la nota', () => {
    const def = {
      ...DEF,
      analysis: {
        ...ANALYSIS,
        prompt: 'Sos el extractor de esta cuenta.\nMirá la deuda.\nIgnorá los chistes.',
      },
    } as Definition;
    renderWithProviders(<WorkflowSummary definition={def} />, { me: CLIENT_USER });
    expect(screen.getByText(/Sos el extractor de esta cuenta/)).toBeInTheDocument();
    expect(screen.getByText(/Mirá la deuda/)).toBeInTheDocument();
    expect(screen.queryByText('El de la plataforma')).toBeNull();
    expect(screen.queryByText(/Instrucciones de una versión anterior/)).toBeNull();
  });

  it('sin variables no muestra la tabla', () => {
    renderWithProviders(<WorkflowSummary definition={{ ...DEF, variables: undefined }} />, {
      me: CLIENT_USER,
    });
    expect(screen.queryByText('Variables')).toBeNull();
  });
});
