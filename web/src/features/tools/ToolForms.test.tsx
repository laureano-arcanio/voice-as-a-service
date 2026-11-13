import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { ExtraVariable } from '@/components/variables';
import { CATALOG } from '@/components/variables/fixtures';
import { jsonResponse, renderWithProviders } from '@/test/render';
import { emptyDraft, newKey, type ToolDraft } from './draft';
import { HttpForm } from './ToolForms';
import { ToolSecretsContext } from './ToolSecretsContext';

vi.stubGlobal(
  'fetch',
  vi.fn(async (input: RequestInfo | URL) => {
    const req = input instanceof Request ? input : new Request(input);
    if (new URL(req.url).pathname === '/api/v1/variables/catalog') return jsonResponse(CATALOG);
    return jsonResponse({ detail: 'no mock' }, 404);
  }),
);

function Harness({
  tab = 'headers',
  extra = [],
  url = 'https://api.ejemplo.com',
  header = '',
}: {
  tab?: string;
  extra?: ExtraVariable[];
  url?: string;
  header?: string;
}) {
  const [draft, setDraft] = useState<ToolDraft>(() => {
    const d = emptyDraft('http');
    return {
      ...d,
      http: { ...d.http, url, headers: [{ key: newKey(), name: 'X-Deuda', value: header }] },
    };
  });
  const [active, setActive] = useState(tab);
  return (
    <ToolSecretsContext.Provider value={{ names: ['CRM_TOKEN'] }}>
      <HttpForm
        draft={draft}
        update={setDraft}
        clientId="c-1"
        tab={active}
        onTab={setActive}
        errorTabs={new Set()}
        extra={extra}
      />
    </ToolSecretsContext.Provider>
  );
}

const optionNames = () =>
  screen
    .queryAllByRole('option', { hidden: true })
    .flatMap((o) => (o.querySelector('p')?.textContent ? [o.querySelector('p')!.textContent!] : []));

describe('HttpForm: variables', () => {
  it('en un header, {{se ofrece el secreto del cliente por nombre', async () => {
    renderWithProviders(<Harness extra={[{ name: 'deuda', description: 'La deuda' }]} />);
    const input = screen.getByLabelText('Valor del header 1');
    await userEvent.click(input);
    await userEvent.type(input, '{{{{se');
    await waitFor(() => expect(optionNames()).toContain('secrets.CRM_TOKEN'));
  });

  it('la URL no ofrece variables en el host', async () => {
    renderWithProviders(<Harness tab="ruta" />);
    const input = screen.getByLabelText('URL');
    await userEvent.click(input);
    await userEvent.keyboard('{End}');
    await userEvent.type(input, '{{{{');
    await waitFor(() => expect(input).toHaveValue('https://api.ejemplo.com{{'));
    expect(input).not.toHaveAttribute('data-expanded');
    expect(optionNames()).toHaveLength(0);

    await userEvent.clear(input);
    await userEvent.type(input, 'https://api.ejemplo.com/clientes/{{{{');
    await waitFor(() => expect(optionNames()).toContain('call.phone'));
  });
});
