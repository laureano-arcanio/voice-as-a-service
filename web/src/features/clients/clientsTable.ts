import type { components } from '@/api/schema';

type Client = components['schemas']['ClientOut'];

export type SortKey = 'name' | 'slug' | 'tier' | 'active' | 'agents' | 'numbers' | 'created_at';
export type Sort = { key: SortKey; desc: boolean };

/** Por defecto: los últimos en darse de alta primero. */
export const DEFAULT_SORT: Sort = { key: 'created_at', desc: true };

export const FILTER_ALL = 'all';
export const FILTER_PAYING = 'paying';
const TIER_PREFIX = 'tier:';

function sortValue(c: Client, key: SortKey): string | number {
  switch (key) {
    case 'tier':
      return c.tier.name;
    case 'active':
      return c.active ? 1 : 0;
    case 'agents':
      return c.agents_count ?? 0;
    case 'numbers':
      return c.numbers_count ?? 0;
    case 'created_at':
      return Date.parse(c.created_at);
    default:
      return c[key];
  }
}

export function sortClients(list: Client[], { key, desc }: Sort): Client[] {
  const dir = desc ? -1 : 1;
  return [...list].sort((a, b) => {
    const [x, y] = [sortValue(a, key), sortValue(b, key)];
    const cmp =
      typeof x === 'number' && typeof y === 'number'
        ? x - y
        : String(x).localeCompare(String(y), 'es', { sensitivity: 'base' });
    return cmp * dir || a.name.localeCompare(b.name, 'es');
  });
}

/** Otro clic en la misma columna invierte el orden. Fechas y cantidades empiezan por el mayor. */
export function nextSort(current: Sort, key: SortKey): Sort {
  if (current.key === key) return { key, desc: !current.desc };
  return { key, desc: key === 'created_at' || key === 'agents' || key === 'numbers' };
}

export function filterClients(list: Client[], filter: string): Client[] {
  if (filter === FILTER_ALL) return list;
  if (filter === FILTER_PAYING) return list.filter((c) => c.paying);
  return list.filter((c) => TIER_PREFIX + c.tier.id === filter);
}

/** Todos, Pagos y un filtro por cada tier con clientes (el Free incluido), con su cantidad. */
export function filterOptions(list: Client[]): { value: string; label: string }[] {
  const tiers = new Map<string, { name: string; count: number }>();
  for (const c of list) {
    const tier = tiers.get(c.tier.id) ?? { name: c.tier.name, count: 0 };
    tiers.set(c.tier.id, { ...tier, count: tier.count + 1 });
  }
  return [
    { value: FILTER_ALL, label: `Todos (${list.length})` },
    { value: FILTER_PAYING, label: `Pagos (${list.filter((c) => c.paying).length})` },
    ...[...tiers.entries()]
      .sort(([, a], [, b]) => a.name.localeCompare(b.name, 'es'))
      .map(([id, t]) => ({ value: TIER_PREFIX + id, label: `${t.name} (${t.count})` })),
  ];
}
