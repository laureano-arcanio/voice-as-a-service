import { Anchor, Badge, Button, Group, Menu, Text } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconArchive,
  IconArrowLeft,
  IconDots,
  IconPencil,
  IconRestore,
  IconTrash,
} from '@tabler/icons-react';
import { Link, useNavigate, useParams } from 'react-router';
import { ApiError } from '@/api/errors';
import type { AgentDetail } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { QueryState } from '@/components/QueryState';
import { useIsAdmin } from '@/features/auth/api';
import { useClients } from '@/features/clients/api';
import { formatDateTime } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useAgent, useDeleteAgent, useUpdateAgent } from './api';
import { AgentTabs } from './AgentTabs';
import { EditAgentModal } from './EditAgentModal';

function AgentActions({ agent }: { agent: AgentDetail }) {
  const [editing, edit] = useDisclosure(false);
  const update = useUpdateAgent(agent.id);
  const del = useDeleteAgent();
  const navigate = useNavigate();

  const toggleArchive = async () => {
    const archiving = !agent.archived;
    if (
      archiving &&
      !(await confirmAction({
        title: 'Archivar agente',
        message: 'No se va a poder usar en llamadas nuevas. Su historial se conserva y lo podés desarchivar.',
        confirmLabel: 'Archivar',
      }))
    ) {
      return;
    }
    update.mutate(
      { archived: archiving },
      {
        onSuccess: () => notifySuccess(archiving ? 'Agente archivado.' : 'Agente desarchivado.'),
        onError: (e) => notifyError(e),
      },
    );
  };

  const remove = async () => {
    const ok = await confirmAction({
      title: 'Borrar agente',
      message: `Se borra "${agent.name}" con todas sus versiones. Solo se puede si no tiene conversaciones.`,
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (!ok) return;
    del.mutate(agent.id, {
      onSuccess: () => {
        notifySuccess('Agente borrado.');
        void navigate('/agents', { replace: true });
      },
      onError: (e) =>
        e instanceof ApiError && e.status === 409
          ? notifyError(e, 'Tiene conversaciones: archivalo en vez de borrarlo')
          : notifyError(e, 'No se pudo borrar'),
    });
  };

  return (
    <>
      <Button variant="default" leftSection={<IconPencil size={16} />} onClick={edit.open}>
        Editar
      </Button>
      <Menu position="bottom-end" withinPortal>
        <Menu.Target>
          <Button variant="default" px="xs" aria-label="Más acciones">
            <IconDots size={18} />
          </Button>
        </Menu.Target>
        <Menu.Dropdown>
          <Menu.Item
            leftSection={agent.archived ? <IconRestore size={16} /> : <IconArchive size={16} />}
            onClick={() => void toggleArchive()}
          >
            {agent.archived ? 'Desarchivar' : 'Archivar'}
          </Menu.Item>
          <Menu.Item color="red" leftSection={<IconTrash size={16} />} onClick={() => void remove()}>
            Borrar
          </Menu.Item>
        </Menu.Dropdown>
      </Menu>
      <EditAgentModal key={`${agent.id}-${editing}`} agent={agent} opened={editing} onClose={edit.close} />
    </>
  );
}

function AgentView({ agent }: { agent: AgentDetail }) {
  const isAdmin = useIsAdmin();
  const clients = useClients(isAdmin);
  const client = clients.data?.find((c) => c.id === agent.client_id);

  return (
    <>
      <PageHeader
        above={
          <Button
            component={Link}
            to="/agents"
            variant="subtle"
            size="compact-sm"
            leftSection={<IconArrowLeft size={16} />}
            w="fit-content"
          >
            Agentes
          </Button>
        }
        docTitle={agent.name}
        title={
          <Group gap="sm" component="span">
            {agent.name}
            <Text span c="dimmed" className="mono">
              v{agent.version}
            </Text>
            {agent.own_agent && <Badge color="gray">Tu propio agente</Badge>}
            {agent.archived && <Badge color="gray">Archivado</Badge>}
          </Group>
        }
        description={
          <>
            {/* El slug es interno, como en la lista. */}
            {isAdmin && (
              <>
                <Text span className="mono">
                  {agent.slug}
                </Text>
                {' · '}
              </>
            )}
            {isAdmin ? 'voz ' : 'Voz '}
            {agent.voice ?? 'predeterminada'}
            {client && (
              <>
                {' · '}
                <Anchor component={Link} to={`/clients/${client.id}`} size="sm">
                  {client.name}
                </Anchor>
              </>
            )}
            {' · actualizado '}
            {formatDateTime(agent.updated_at)}
            {agent.description && (
              <Text size="sm" c="dimmed" mt={4}>
                {agent.description}
              </Text>
            )}
          </>
        }
        actions={<AgentActions agent={agent} />}
      />
      <AgentTabs agent={agent} />
    </>
  );
}

export function AgentDetailPage() {
  const { id } = useParams();
  const query = useAgent(id);
  return <QueryState query={query}>{(agent) => <AgentView key={agent.id} agent={agent} />}</QueryState>;
}
