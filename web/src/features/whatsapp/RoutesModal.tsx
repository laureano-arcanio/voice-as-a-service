import { ActionIcon, Button, Group, Modal, Select, Stack, TagsInput, Text } from '@mantine/core';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import type { WaAccount } from '@/api/types';
import { useAgents } from '@/features/agents/api';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useSetWaRoutes } from './api';

type Row = { agent_id: string; contacts: string[] };

/** Ruteo por contacto de un numero de WhatsApp: los contactos de cada regla los atiende ese
 * agente en los mensajes y las llamadas, en vez del agente por defecto de la cuenta. */
export function WaRoutesModal({ account, onClose }: { account: WaAccount; onClose: () => void }) {
  const agents = useAgents(account.client_id, false);
  const save = useSetWaRoutes();
  const [rows, setRows] = useState<Row[]>(
    account.routes.map((r) => ({ agent_id: r.agent_id, contacts: [...r.contacts] })),
  );

  const options = (agents.data ?? []).map((a) => ({ value: a.id, label: a.name }));
  // Un agente ya usado puede estar archivado: se sigue mostrando para poder sacarlo.
  for (const r of account.routes) {
    if (!options.some((o) => o.value === r.agent_id)) {
      options.push({ value: r.agent_id, label: `${r.agent_name ?? 'Agente'} (archivado)` });
    }
  }
  const incomplete = rows.some((r) => !r.agent_id || r.contacts.length === 0);
  const setRow = (i: number, row: Row) => setRows((prev) => prev.map((r, j) => (j === i ? row : r)));

  return (
    <Modal opened onClose={onClose} title={`Ruteo por contacto · ${account.display_phone_number}`} size="xl">
      <Stack>
        <Text size="sm" c="dimmed">
          Los contactos de cada lista los atiende ese agente en los mensajes y las llamadas de WhatsApp. Los
          demás, {account.agent_name ?? 'el agente por defecto'}. Los operadores siguen como siempre.
        </Text>
        {rows.map((row, i) => (
          <Group key={i} align="flex-end" wrap="nowrap">
            <Select
              label={i === 0 ? 'Agente' : undefined}
              placeholder="Elegí el agente"
              data={options}
              searchable
              style={{ flex: 1 }}
              value={row.agent_id || null}
              onChange={(v) => setRow(i, { ...row, agent_id: v ?? '' })}
            />
            <TagsInput
              label={i === 0 ? 'Contactos que atiende' : undefined}
              placeholder="5491155551234"
              description={i === 0 ? 'WhatsApp con código de país; Enter después de cada uno' : undefined}
              splitChars={[',', ';']}
              style={{ flex: 2 }}
              value={row.contacts}
              onChange={(contacts) => setRow(i, { ...row, contacts })}
            />
            <ActionIcon
              variant="subtle"
              color="red"
              aria-label="Quitar regla"
              onClick={() => setRows((prev) => prev.filter((_, j) => j !== i))}
            >
              <IconTrash size={16} />
            </ActionIcon>
          </Group>
        ))}
        <Group>
          <Button
            variant="default"
            leftSection={<IconPlus size={16} />}
            onClick={() => setRows((prev) => [...prev, { agent_id: '', contacts: [] }])}
          >
            Agregar agente
          </Button>
        </Group>
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            loading={save.isPending}
            disabled={incomplete}
            onClick={() =>
              save.mutate(
                { id: account.id, routes: rows.map((r) => ({ agent_id: r.agent_id, contacts: r.contacts })) },
                {
                  onSuccess: (list) => {
                    notifySuccess(
                      list.length
                        ? `Ruteo por contacto: ${list.length} regla${list.length === 1 ? '' : 's'}.`
                        : 'Ruteo por contacto borrado.',
                    );
                    onClose();
                  },
                  onError: (e) => notifyError(e, 'No se pudo guardar el ruteo'),
                },
              )
            }
          >
            Guardar
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
