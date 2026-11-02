import { describe, expect, it } from 'vitest';
import type { components } from '@/api/schema';
import {
  DEFAULT_SORT,
  FILTER_ALL,
  FILTER_PAYING,
  filterClients,
  filterOptions,
  nextSort,
  sortClients,
} from './clientsTable';

type Client = components['schemas']['ClientOut'];

function client(name: string, tier: string, created_at: string, extra: Partial<Client> = {}): Client {
  return {
    id: name,
    name,
    slug: name.toLowerCase(),
    active: true,
    tier: { id: tier, name: tier },
    created_at,
    ...extra,
  } as Client;
}

const LIST = [
  client('Beta', 'Free', '2026-10-01T10:00:00Z', { agents_count: 5 }),
  client('Alfa', 'Sucursal', '2026-10-20T10:00:00Z', { agents_count: 1 }),
  client('Openpass', 'Mostrador', '2026-11-01T05:00:00Z', { paying: true, agents_count: 10 }),
  client('Cimepa', 'Mostrador', '2026-10-28T10:00:00Z'),
];

const names = (list: Client[]) => list.map((c) => c.name);

describe('tabla de clientes', () => {
  it('por defecto muestra primero las altas más nuevas', () => {
    expect(names(sortClients(LIST, DEFAULT_SORT))).toEqual(['Openpass', 'Cimepa', 'Alfa', 'Beta']);
  });

  it('ordena por texto y por cantidad, no como texto', () => {
    expect(names(sortClients(LIST, { key: 'name', desc: false }))).toEqual(['Alfa', 'Beta', 'Cimepa', 'Openpass']);
    expect(names(sortClients(LIST, { key: 'agents', desc: true }))).toEqual(['Openpass', 'Beta', 'Alfa', 'Cimepa']);
  });

  it('otro clic invierte el orden; una columna nueva arranca según su tipo', () => {
    expect(nextSort(DEFAULT_SORT, 'created_at')).toEqual({ key: 'created_at', desc: false });
    expect(nextSort(DEFAULT_SORT, 'name')).toEqual({ key: 'name', desc: false });
    expect(nextSort(DEFAULT_SORT, 'numbers')).toEqual({ key: 'numbers', desc: true });
  });

  it('Pagos son los que tienen plan pago vigente, no los que están en un tier con precio', () => {
    expect(names(filterClients(LIST, FILTER_PAYING))).toEqual(['Openpass']);
    expect(filterClients(LIST, FILTER_ALL)).toHaveLength(4);
  });

  it('ofrece un filtro por cada tier, con su cantidad', () => {
    const options = filterOptions(LIST);
    expect(options.map((o) => o.label)).toEqual([
      'Todos (4)',
      'Pagos (1)',
      'Free (1)',
      'Mostrador (2)',
      'Sucursal (1)',
    ]);
    const mostrador = options.find((o) => o.label.startsWith('Mostrador'))!.value;
    expect(names(filterClients(LIST, mostrador))).toEqual(['Openpass', 'Cimepa']);
  });
});
