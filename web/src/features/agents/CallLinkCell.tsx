import { Anchor, Button, Group, Tooltip } from '@mantine/core';
import { IconLink } from '@tabler/icons-react';
import type { Agent } from '@/api/types';
import { Dash } from '@/components/Badges';
import { CopyIcon } from '@/components/Copy';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useCreateCallLink } from './callLink';

/** Columna "Link para llamar" de la lista de agentes: la URL con copiar, o el botón para crearlo. */
export function CallLinkCell({ agent }: { agent: Agent }) {
  const create = useCreateCallLink(agent.id);
  const url = agent.call_link_url;
  if (url) {
    const cut = url.lastIndexOf('/');
    const host = url.slice(0, cut).replace(/^https?:\/\//, '');
    const token = url.slice(cut + 1);
    return (
      <Group gap={4} wrap="nowrap">
        <Tooltip label={`Abrir ${url}`} withArrow>
          <Anchor
            href={url}
            target="_blank"
            rel="noopener"
            size="xs"
            className="mono"
            style={{ whiteSpace: 'nowrap' }}
          >
            {/* Dominio arriba y código del link abajo, para que entre en la columna. */}
            {host}/
            <br />
            {token}
          </Anchor>
        </Tooltip>
        <CopyIcon value={url} label="Copiar link" />
      </Group>
    );
  }
  if (agent.archived) return <Dash />;
  return (
    <Button
      variant="default"
      size="compact-sm"
      leftSection={<IconLink size={14} />}
      loading={create.isPending}
      onClick={() =>
        create.mutate(
          {},
          {
            onSuccess: () => notifySuccess('Link creado: ya lo podés copiar.'),
            onError: (e) => notifyError(e, 'No se pudo crear el link'),
          },
        )
      }
    >
      Crear link
    </Button>
  );
}
