import { Card, Group, SimpleGrid, Skeleton, Stack, Table, Text, Title, UnstyledButton } from '@mantine/core';
import { IconArrowDownRight, IconArrowUpRight, IconChevronDown, IconChevronUp } from '@tabler/icons-react';
import { useContext, useState, type ReactNode } from 'react';
import { Dash } from '@/components/Badges';
import { CsvButton } from '@/components/CsvButton';
import { EmptyState } from '@/components/QueryState';
import { csvFilename, type CsvColumn } from '@/lib/csv';
import { formatNumber } from '@/lib/format';
import { ReportContext, type Kpi } from './format';

export interface Column<T> extends CsvColumn<T> {
  /** Lo que se muestra; por defecto el valor (numeros con formato, vacio como raya). */
  render?: (row: T) => ReactNode;
  /** Numero: a la derecha, en mono. */
  num?: boolean;
}

export interface CsvData<T> {
  rows: readonly T[];
  columns: readonly CsvColumn<T>[];
}

/** Tarjeta de un bloque del reporte: titulo, "Descargar CSV" a la derecha y el contenido. */
export function ReportCard<T>({
  title,
  description,
  csv,
  children,
}: {
  title: string;
  description?: ReactNode;
  csv?: CsvData<T>;
  children: ReactNode;
}) {
  const ctx = useContext(ReportContext);
  return (
    <Card>
      <Group justify="space-between" align="flex-start" mb="md" gap="xs">
        <Stack gap={2}>
          <Title order={4}>{title}</Title>
          {description && (
            <Text size="xs" c="dimmed">
              {description}
            </Text>
          )}
        </Stack>
        {csv && (
          <CsvButton
            filename={csvFilename('reporte', ctx.tab, title, ctx.from, ctx.to)}
            rows={csv.rows}
            columns={csv.columns}
          />
        )}
      </Group>
      {children}
    </Card>
  );
}

function valueOf<T>(row: T, c: CsvColumn<T>): unknown {
  return typeof c.value === 'function' ? c.value(row) : row[c.value];
}

function show(v: unknown): ReactNode {
  if (v == null || v === '') return <Dash />;
  if (typeof v === 'number') return formatNumber(v);
  return String(v);
}

/** Tabla de un reporte. Con `sortable`, los encabezados ordenan (click otra vez invierte). */
export function ReportTable<T>({
  rows,
  columns,
  empty = 'Sin datos en el período.',
  sortable = false,
  rowKey,
}: {
  rows: readonly T[];
  columns: readonly Column<T>[];
  empty?: string;
  sortable?: boolean;
  rowKey?: (row: T, i: number) => string;
}) {
  const [sort, setSort] = useState<{ col: number; desc: boolean } | null>(null);
  if (!rows.length) return <EmptyState>{empty}</EmptyState>;
  const sorted = sort
    ? [...rows].sort((a, b) => {
        const x = valueOf(a, columns[sort.col]!);
        const y = valueOf(b, columns[sort.col]!);
        if (x == null) return 1;
        if (y == null) return -1;
        const r = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y));
        return sort.desc ? -r : r;
      })
    : rows;
  return (
    <Table.ScrollContainer minWidth={Math.min(900, columns.length * 120)} type="native">
      <Table>
        <Table.Thead>
          <Table.Tr>
            {columns.map((c, i) => {
              const active = sort?.col === i;
              return (
                <Table.Th
                  key={c.label}
                  ta={c.num ? 'right' : undefined}
                  aria-sort={active ? (sort.desc ? 'descending' : 'ascending') : undefined}
                >
                  {sortable ? (
                    <UnstyledButton
                      className="label"
                      onClick={() =>
                        setSort(active ? { col: i, desc: !sort.desc } : { col: i, desc: !!c.num })
                      }
                    >
                      <Group gap={2} wrap="nowrap" justify={c.num ? 'flex-end' : undefined}>
                        {c.label}
                        {active && (sort.desc ? <IconChevronDown size={12} /> : <IconChevronUp size={12} />)}
                      </Group>
                    </UnstyledButton>
                  ) : (
                    c.label
                  )}
                </Table.Th>
              );
            })}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {sorted.map((r, i) => (
            <Table.Tr key={rowKey ? rowKey(r, i) : i}>
              {columns.map((c) => (
                <Table.Td
                  key={c.label}
                  ta={c.num ? 'right' : undefined}
                  className={c.num ? 'mono' : undefined}
                >
                  {c.render ? c.render(r) : show(valueOf(r, c))}
                </Table.Td>
              ))}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

/** Tabla dentro de su tarjeta, con el CSV de las mismas columnas. */
export function TableCard<T>({
  title,
  description,
  rows,
  columns,
  empty,
  sortable,
  rowKey,
}: {
  title: string;
  description?: ReactNode;
  rows: readonly T[];
  columns: readonly Column<T>[];
  empty?: string;
  sortable?: boolean;
  rowKey?: (row: T, i: number) => string;
}) {
  return (
    <ReportCard title={title} description={description} csv={{ rows, columns }}>
      <ReportTable rows={rows} columns={columns} empty={empty} sortable={sortable} rowKey={rowKey} />
    </ReportCard>
  );
}

/** Fila de metricas: rotulo, numero y, si hay, la variacion contra el periodo anterior (en neutro). */
export function KpiGrid({ kpis, cols = 4 }: { kpis: Kpi[] | null; cols?: number }) {
  return (
    <SimpleGrid cols={{ base: 2, sm: cols }} spacing="md">
      {(kpis ?? Array.from({ length: cols }, () => null)).map((k, i) => (
        <Card key={k?.label ?? i} padding="md">
          {k ? (
            <Stack gap={6} justify="space-between" h="100%">
              <Text className="label">{k.label}</Text>
              <Text className="metric" c={k.tone}>
                {k.value}
                {k.sub && (
                  <Text span size="sm" fw={500} c="dimmed" ff="text" ml={8} style={{ letterSpacing: 0 }}>
                    {k.sub}
                  </Text>
                )}
              </Text>
              {k.delta !== undefined && (
                <Group gap={4} c="dimmed">
                  {k.delta ? (
                    <>
                      {k.delta.up ? (
                        <IconArrowUpRight size={16} aria-hidden />
                      ) : (
                        <IconArrowDownRight size={16} aria-hidden />
                      )}
                      <Text size="xs" c="dimmed">
                        {k.delta.text} vs. período anterior
                      </Text>
                    </>
                  ) : (
                    <Text size="xs" c="dimmed">
                      Sin datos del período anterior
                    </Text>
                  )}
                </Group>
              )}
            </Stack>
          ) : (
            <>
              <Skeleton h={12} w="70%" />
              <Skeleton h={28} mt={10} w="45%" />
            </>
          )}
        </Card>
      ))}
    </SimpleGrid>
  );
}
