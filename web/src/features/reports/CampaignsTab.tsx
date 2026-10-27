import { Anchor, Badge, SimpleGrid, Stack } from '@mantine/core';
import { Link } from 'react-router';
import { HourHeatmap } from '@/components/HourHeatmap';
import { QueryState } from '@/components/QueryState';
import { CAMPAIGN_STATUS } from '@/features/campaigns/labels';
import { formatNumber } from '@/lib/format';
import { useReport } from './api';
import { CHANNEL_LABEL, NO_CONTACT_REASON, label } from './labels';
import { ReportCard, TableCard, type Column } from './parts';
import type { CampaignsReport, Channel, ReportQuery } from './types';

type Campaign = CampaignsReport['campaigns'][number];
type NoContact = CampaignsReport['no_contact'][number];

const CAMPAIGN_COLS: Column<Campaign>[] = [
  {
    label: 'Campaña',
    value: 'name',
    render: (r) => (
      <Anchor component={Link} to={`/campaigns/${r.campaign_id}`} size="sm">
        {r.name}
      </Anchor>
    ),
  },
  { label: 'Canal', value: (r) => CHANNEL_LABEL[r.channel as Channel] ?? r.channel },
  {
    label: 'Estado',
    value: (r) => CAMPAIGN_STATUS[r.status]?.label ?? r.status,
    render: (r) => {
      const s = CAMPAIGN_STATUS[r.status] ?? { label: r.status, color: 'gray' };
      return <Badge color={s.color}>{s.label}</Badge>;
    },
  },
  { label: 'Contactos', value: 'contacts', num: true },
  { label: 'Intentos', value: 'attempts', num: true },
  { label: 'Contactados', value: 'reached', num: true },
  { label: 'Completas', value: 'complete', num: true },
  { label: 'Objetivo', value: 'goal', num: true },
  { label: 'Bajas', value: 'optouts', num: true },
  { label: 'Minutos', value: 'minutes', num: true },
];

const NO_CONTACT_COLS: Column<NoContact>[] = [
  { label: 'Motivo', value: (r) => label(NO_CONTACT_REASON, r.reason) },
  { label: 'Contactos', value: 'count', num: true },
];

export function CampaignsTab({ query }: { query: ReportQuery }) {
  const report = useReport('campaigns', query);
  return (
    <QueryState query={report}>
      {(r) => (
        <Stack gap="md">
          <TableCard
            title="Campañas"
            description="Las campañas con actividad en el período."
            rows={r.campaigns}
            columns={CAMPAIGN_COLS}
            empty="Sin campañas en el período."
            sortable
            rowKey={(x) => x.campaign_id}
          />
          <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
            <TableCard
              title="Por qué no se contactó"
              rows={r.no_contact}
              columns={NO_CONTACT_COLS}
              empty="Se contactó a todos."
              rowKey={(x) => x.reason}
            />
            <ReportCard
              title="Mejor horario"
              description="Porcentaje de contactos que atendieron o respondieron, por día y hora."
              csv={{
                rows: r.best_hours,
                columns: [
                  { label: 'Día (0 = lunes)', value: 'weekday' },
                  { label: 'Hora', value: 'hour' },
                  { label: 'Intentos', value: 'attempts' },
                  { label: 'Contactados', value: 'reached' },
                ],
              }}
            >
              <HourHeatmap
                caption="Porcentaje de contactos alcanzados por día de la semana y hora"
                unit="%"
                cells={r.best_hours.map((c) => ({
                  weekday: c.weekday,
                  hour: c.hour,
                  value: c.attempts ? (c.reached / c.attempts) * 100 : 0,
                  detail: `${c.reached} de ${c.attempts} (${formatNumber(c.attempts ? (c.reached / c.attempts) * 100 : 0, 0)}%)`,
                }))}
              />
            </ReportCard>
          </SimpleGrid>
        </Stack>
      )}
    </QueryState>
  );
}
