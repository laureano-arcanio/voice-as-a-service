import { Alert, Button, Group, List, Modal, Select, Stack, Text } from '@mantine/core';
import { useState } from 'react';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useBulkDrafts, useCampaigns, useTemplates } from '../api';
import { MESSAGE_KIND_OPTIONS } from '../format';
import type { BulkDraftResult, MessageKind } from '../types';

/**
 * Borradores de una plantilla para varios leads. Con `byCampaign` (seguimientos de "Hoy") cada lead va
 * a su campaña y solo se elige la plantilla; si no, se elige campaña, plantilla y tipo.
 */
export function BulkDraftsModal({
  opened,
  onClose,
  leadIds,
  byCampaign,
  defaultKind = 'first',
  names,
}: {
  opened: boolean;
  onClose: (done: boolean) => void;
  leadIds: number[];
  byCampaign?: Record<number, number[]>;
  defaultKind?: MessageKind;
  names?: Record<number, string>;
}) {
  const campaigns = useCampaigns();
  const templates = useTemplates();
  const bulk = useBulkDrafts();
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const [kind, setKind] = useState<MessageKind>(defaultKind);
  const [templateId, setTemplateId] = useState<string | null>(null);
  const [result, setResult] = useState<BulkDraftResult | null>(null);
  const [running, setRunning] = useState(false);

  const tplOptions = (templates.data ?? [])
    .filter((t) => t.kind === kind || t.kind === 'other')
    .map((t) => ({ value: String(t.id), label: t.name }));
  const campOptions = (campaigns.data ?? []).map((c) => ({
    value: String(c.id),
    label: `${c.name} (${c.slug})`,
  }));

  const close = () => {
    const done = !!result;
    setResult(null);
    setTemplateId(null);
    onClose(done);
  };

  const run = async () => {
    if (!templateId) return;
    const groups: [number, number[]][] = byCampaign
      ? Object.entries(byCampaign).map(([c, ids]) => [Number(c), ids])
      : campaignId
        ? [[Number(campaignId), leadIds]]
        : [];
    setRunning(true);
    const acc: BulkDraftResult = { created: [], skipped: [] };
    try {
      for (const [cid, ids] of groups) {
        const r = await bulk.mutateAsync({
          campaignId: cid,
          lead_ids: ids,
          template_id: Number(templateId),
          kind,
        });
        acc.created.push(...r.created);
        acc.skipped.push(...r.skipped);
      }
      setResult(acc);
      if (acc.created.length) notifySuccess(`${acc.created.length} borradores listos para revisar en Hoy.`);
    } catch (e) {
      notifyError(e, 'No se pudieron armar los borradores');
    } finally {
      setRunning(false);
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={close}
      title={byCampaign ? 'Armar seguimientos' : 'Armar borradores'}
      size="lg"
    >
      {result ? (
        <Stack>
          <Text size="sm">
            <b>{result.created.length}</b> borradores creados. Quedan en <b>Hoy</b> para revisar y aprobar.
          </Text>
          {result.skipped.length > 0 && (
            <Alert color="yellow" title={`${result.skipped.length} salteados`}>
              <List size="sm" spacing={2}>
                {result.skipped.map((s) => (
                  <List.Item key={s.lead_id}>
                    {names?.[s.lead_id] ?? `Lead ${s.lead_id}`}: {s.reason}
                  </List.Item>
                ))}
              </List>
            </Alert>
          )}
          <Group justify="flex-end">
            <Button onClick={close}>Listo</Button>
          </Group>
        </Stack>
      ) : (
        <Stack>
          <Text size="sm" c="dimmed">
            {leadIds.length} leads. Se crean borradores: no sale nada hasta que los apruebes.
          </Text>
          {!byCampaign && (
            <>
              <Select
                label="Campaña"
                data={campOptions}
                value={campaignId}
                onChange={setCampaignId}
                searchable
                placeholder="Elegí una campaña"
              />
              <Select
                label="Tipo"
                data={MESSAGE_KIND_OPTIONS}
                value={kind}
                onChange={(v) => {
                  setKind((v as MessageKind) ?? 'first');
                  setTemplateId(null);
                }}
                allowDeselect={false}
              />
            </>
          )}
          <Select
            label="Plantilla"
            data={tplOptions}
            value={templateId}
            onChange={setTemplateId}
            searchable
            placeholder={tplOptions.length ? 'Elegí una plantilla' : 'No hay plantillas de este tipo'}
            description={
              kind === 'follow_up'
                ? 'El seguimiento va en el hilo del primer mail: el asunto es "Re: …"'
                : undefined
            }
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={close}>
              Cancelar
            </Button>
            <Button
              onClick={() => void run()}
              loading={running}
              disabled={!templateId || (!byCampaign && !campaignId)}
            >
              Armar borradores
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  );
}
