import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '@/test/render';
import { CATALOG, DECLARED } from './fixtures';
import { VariableField, type VariableFieldProps } from './VariableField';

function Harness({ initial = '', ...rest }: Partial<VariableFieldProps> & { initial?: string }) {
  const [value, setValue] = useState(initial);
  return (
    <VariableField
      field="tool"
      catalog={CATALOG}
      declared={DECLARED}
      label="Valor"
      {...rest}
      value={value}
      onChange={setValue}
    />
  );
}

const input = () => screen.getByLabelText('Valor') as HTMLInputElement;
const optionNames = () =>
  screen.queryAllByRole('option', { hidden: true }).map((o) => o.querySelector('p')?.textContent);

describe('VariableField', () => {
  it('al tipear {{ lista declaradas y del sistema; seguir tipeando filtra', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Harness />);
    await user.click(input());
    await user.type(input(), '{{{{');
    await waitFor(() =>
      expect(optionNames()).toEqual([
        'nombre',
        'deuda',
        'call.phone',
        'today',
        'call.summary',
        'fields.<campo>',
        'secrets.<NOMBRE>',
      ]),
    );
    await user.type(input(), 'ph');
    await waitFor(() => expect(optionNames()).toEqual(['call.phone']));
  });

  it('Enter inserta la primera y deja el cursor al final', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Harness initial="Hola " />);
    await user.click(input());
    await user.keyboard('{End}{{{{');
    await user.keyboard('to');
    await waitFor(() => expect(optionNames()).toEqual(['today']));
    await user.keyboard('{Enter}');
    expect(input().value).toBe('Hola {{today}}');
    expect(input().selectionStart).toBe(14);
    await waitFor(() => expect(screen.queryAllByRole('option', { hidden: true })).toHaveLength(0));
  });

  it('flechas eligen otra y Tab la inserta', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Harness />);
    await user.click(input());
    await user.keyboard('{{{{{ArrowDown}');
    await waitFor(() => expect(optionNames().length).toBeGreaterThan(1));
    await user.keyboard('{Tab}');
    expect(input().value).toBe('{{deuda}}');
  });

  it('clic en una opción inserta y se come el }} siguiente', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Harness initial="{{no}} fin" />);
    await user.click(input());
    input().setSelectionRange(4, 4);
    await user.keyboard('{ArrowRight}{ArrowLeft}');
    await waitFor(() => expect(optionNames()).toEqual(['nombre', 'secrets.<NOMBRE>']));
    await user.click(screen.getAllByRole('option', { hidden: true })[0]!);
    expect(input().value).toBe('{{nombre}} fin');
  });

  it('{{x}} ya cerrada no abre la lista', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Harness initial="{{nombre}}" />);
    await user.click(input());
    expect(screen.queryAllByRole('option', { hidden: true })).toHaveLength(0);
  });

  it('lista las variables usadas sin fuente, no las conocidas', async () => {
    renderWithProviders(<Harness initial="{{nombre}} {{today}} {{rara}} {{secrets.X}}" field="prompt" />);
    const note = await screen.findByTestId('unknown-variables');
    expect(note).toHaveTextContent('{{rara}}, {{secrets.X}}');
    expect(note).not.toHaveTextContent('{{nombre}}');
    expect(note).not.toHaveTextContent('{{today}}');
  });

  it('multiline usa un textarea', async () => {
    renderWithProviders(<Harness multiline />);
    expect(input().tagName).toBe('TEXTAREA');
  });

  it('Escape cierra sin insertar', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Harness />);
    await user.click(input());
    await user.keyboard('{{{{');
    await waitFor(() => expect(optionNames().length).toBeGreaterThan(0));
    await user.keyboard('{Escape}');
    await waitFor(() => expect(input()).not.toHaveAttribute('data-expanded'));
    expect(input().value).toBe('{{');
  });

  it('opensAt decide si la lista puede abrirse en esa posición', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Harness opensAt={(text) => text.startsWith('/')} />);
    await user.click(input());
    await user.type(input(), '{{{{');
    expect(screen.queryAllByRole('option', { hidden: true })).toHaveLength(0);
    await user.clear(input());
    await user.type(input(), '/{{{{');
    await waitFor(() => expect(optionNames()).toContain('nombre'));
  });
});
