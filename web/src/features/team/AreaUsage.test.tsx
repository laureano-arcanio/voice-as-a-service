import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { HandoffArea } from '@/api/types';
import { ADMIN, CLIENT_USER, renderWithProviders } from '@/test/render';
import { AreaUsage } from './AreaUsage';

type Usage = HandoffArea['used_by'];
const USO: Usage = {
  agents: [
    { id: 'ag-1', name: 'Sofía', when: 'si piden ventas' },
    { id: 'ag-2', name: 'Lucas', when: '' },
  ],
  phone_numbers: [
    { id: 'n1', e164: '+541152630861', label: 'Local', answer_mode: 'team' },
    { id: 'n2', e164: '+541152630862', label: '', answer_mode: 'agent' },
  ],
  whatsapp_accounts: [{ id: 'w1', display_phone_number: '+54 351 000' }],
};

describe('AreaUsage', () => {
  it('lista agentes con su link, números y WhatsApp', () => {
    renderWithProviders(<AreaUsage usage={USO} />, { me: CLIENT_USER });
    const sofia = screen.getByRole('link', { name: 'Sofía' });
    expect(sofia).toHaveAttribute('href', '/agents/ag-1?tab=herramientas');
    expect(sofia).toHaveAttribute('target', '_blank');
    expect(screen.getByText('si piden ventas')).toBeInTheDocument();
    expect(screen.getByText('Usa «Qué atiende»')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '+541152630861 · Local' })).toHaveAttribute('href', '/account');
    expect(screen.getByText(/\(atiende el equipo\)/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '+54 351 000' })).toHaveAttribute('href', '/whatsapp');
  });

  it('sin agentes dice cómo marcar el área', () => {
    renderWithProviders(<AreaUsage usage={{ agents: [], phone_numbers: [], whatsapp_accounts: [] }} />, {
      me: CLIENT_USER,
    });
    expect(screen.getByText(/Ningún agente deriva a esta área/)).toBeInTheDocument();
  });

  it('un Usuario ve los números sin link a Cuenta ni WhatsApp', () => {
    renderWithProviders(<AreaUsage usage={USO} />, { me: { ...CLIENT_USER, client_role: 'user' } });
    expect(screen.getByRole('link', { name: 'Sofía' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /\+54115263086/ })).toBeNull();
    expect(screen.queryByRole('link', { name: '+54 351 000' })).toBeNull();
    expect(screen.getByText(/\+541152630861 · Local/)).toBeInTheDocument();
  });

  it('el admin de la plataforma ve los links', () => {
    renderWithProviders(<AreaUsage usage={USO} />, { me: ADMIN });
    expect(screen.getByRole('link', { name: '+54 351 000' })).toBeInTheDocument();
  });
});
