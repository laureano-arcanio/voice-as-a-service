import { Anchor, Badge, Card, Drawer, Group, Stack, Table, Text, Title } from '@mantine/core';
import type { ReactNode } from 'react';
import { Link } from 'react-router';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useSiteDetail } from '../api';
import { DEVICES, KINDS, dayLabel, duration, int, itemLabel } from '../site';
import type { SiteDetail as Detail, SiteDetailKind } from '../types';

function Section({ title, help, children }: { title: string; help?: string; children: ReactNode }) {
  return (
    <Card withBorder>
      <Title order={5} mb={help ? 0 : 'sm'}>
        {title}
      </Title>
      {help && (
        <Text size="xs" c="dimmed" mb="sm">
          {help}
        </Text>
      )}
      {children}
    </Card>
  );
}

/** Tabla con la primera columna de texto y el resto numérico; `wide` agrega scroll horizontal. */
function Grid({
  cols,
  rows,
  num = 3,
  wide,
}: {
  cols: string[];
  rows: ReactNode[][];
  num?: number;
  wide?: number;
}) {
  if (!rows.length) return <EmptyState>Sin datos.</EmptyState>;
  const right = (i: number) => i >= cols.length - num;
  const table = (
    <Table>
      <Table.Thead>
        <Table.Tr>
          {cols.map((c, i) => (
            <Table.Th key={c} ta={right(i) ? 'right' : undefined}>
              {c}
            </Table.Th>
          ))}
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {rows.map((r, n) => (
          <Table.Tr key={n}>
            {r.map((v, i) => (
              <Table.Td key={i} ta={right(i) ? 'right' : undefined} className={right(i) ? 'mono' : undefined}>
                {v}
              </Table.Td>
            ))}
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
  return wide ? <Table.ScrollContainer minWidth={wide}>{table}</Table.ScrollContainer> : table;
}

function Company({ id, name, slug }: { id: number | null; name: string | null; slug: string }) {
  if (!id) return <span className="mono">{slug}</span>;
  return (
    <Anchor component={Link} to={`/leads/${id}`} size="sm" fw={600}>
      {name}
    </Anchor>
  );
}

function Campaign({ name, followUp }: { name: string | null; followUp: boolean }) {
  if (!name)
    return (
      <Text size="sm" c="dimmed">
        —
      </Text>
    );
  return (
    <Group gap={6} wrap="nowrap">
      <Text size="sm">{name}</Text>
      {followUp && (
        <Badge size="xs" variant="light" color="gray">
          Seguimiento
        </Badge>
      )}
    </Group>
  );
}

const page = (p: string | null) => (p ? <span className="mono">{p}</span> : 'Sin dato');
const sums = (x: { sessions: number; views: number; engagement_seconds: number }) => [
  int(x.sessions),
  int(x.views),
  duration(x.engagement_seconds),
];

function Body({ d }: { d: Detail }) {
  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        {int(d.totals.sessions)} sesiones, {int(d.totals.views)} vistas y{' '}
        {duration(d.totals.engagement_seconds)} de interacción desde {d.country}, del {dayLabel(d.start)} al{' '}
        {dayLabel(d.end)}.
        {d.truncated &&
          ' GA devolvió el máximo de filas: el detalle está incompleto, probá un período más corto.'}
      </Text>
      {d.companies.length > 0 && (
        <Section
          title="Empresas"
          help="Las que entraron por un link de nuestros mails (utm_content); el nombre lleva a la ficha del lead."
        >
          <Grid
            cols={['Empresa', 'Mail', 'Ciudad', 'Última', 'Sesiones', 'Vistas', 'Interacción']}
            num={4}
            wide={760}
            rows={d.companies.map((c) => [
              <Company id={c.lead_id} name={c.lead_name} slug={c.utm_content} />,
              <Stack gap={2}>
                {c.campaigns.map((x) => (
                  <Campaign key={`${x.name}-${x.follow_up}`} name={x.name} followUp={x.follow_up} />
                ))}
              </Stack>,
              c.cities.join(', ') || 'Sin dato',
              dayLabel(c.last_day),
              ...sums(c),
            ])}
          />
        </Section>
      )}
      {d.kind !== 'source' && (
        <Section title="Fuente / medio" help="El sitio exacto: chatgpt.com, gemini.google.com, google, etc.">
          <Grid
            cols={['Fuente', 'Sesiones', 'Vistas', 'Interacción']}
            rows={d.sources.map((x) => [x.source_medium, ...sums(x)])}
          />
        </Section>
      )}
      <Section title="Página de entrada" help="Con los parámetros del link, si los traía.">
        <Grid
          cols={['Página', 'Sesiones', 'Vistas', 'Interacción']}
          rows={d.landing_pages.map((x) => [page(x.landing_page), ...sums(x)])}
        />
      </Section>
      <Section
        title="Sesiones"
        help="Agrupadas por día, fuente, campaña, empresa, página de entrada, ciudad y dispositivo: GA no da visitantes sueltos."
      >
        <Grid
          cols={[
            'Día',
            'Fuente',
            'Campaña',
            'Empresa',
            'Entrada',
            'Ciudad',
            'Dispositivo',
            'Sesiones',
            'Vistas',
            'Interacción',
          ]}
          wide={1200}
          rows={d.visits.map((v) => [
            dayLabel(v.day),
            v.source_medium,
            v.campaign_name ? (
              <Campaign name={v.campaign_name} followUp={v.follow_up} />
            ) : (
              (v.utm_campaign ?? '—')
            ),
            v.utm_content ? <Company id={v.lead_id} name={v.lead_name} slug={v.utm_content} /> : '—',
            page(v.landing_page),
            v.city ?? 'Sin dato',
            DEVICES[v.device] ?? v.device,
            ...sums(v),
          ])}
        />
      </Section>
    </Stack>
  );
}

/** Panel lateral con el desglose de un canal, fuente, página, ciudad o dispositivo. */
export function SiteDetailDrawer({
  item,
  days,
  onClose,
}: {
  item: { kind: SiteDetailKind; value: string } | null;
  days: number;
  onClose: () => void;
}) {
  const detail = useSiteDetail(item, days);
  return (
    <Drawer
      opened={!!item}
      onClose={onClose}
      position="right"
      size="80rem"
      title={item && <Title order={4}>{`${KINDS[item.kind]}: ${itemLabel(item.kind, item.value)}`}</Title>}
    >
      {item && <QueryState query={detail}>{(d) => <Body d={d} />}</QueryState>}
    </Drawer>
  );
}
