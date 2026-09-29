import { Anchor, Badge, Button, Group, Menu, Tabs, Text } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconArchive,
  IconArrowLeft,
  IconDots,
  IconFileCode,
  IconHistory,
  IconInfoCircle,
  IconPencil,
  IconPlayerPlay,
  IconRestore,
  IconTrash,
} from '@tabler/icons-react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { ApiError } from '@/api/errors';
import type { AgentDetail } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { QueryState } from '@/components/QueryState';
import { useIsAdmin } from '@/features/auth/api';
import { useClients } from '@/features/clients/api';
import { formatDateTime } from '@/lib/format';
import { ENGINE } from '@/lib/labels';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useAgent, useDeleteAgent, useUpdateAgent } from './api';
import { DefinitionTab } from './DefinitionTab';
import { EditAgentModal } from './EditAgentModal';
import { TestTab } from './TestTab';
import { VersionsTab } from './VersionsTab';
import { WorkflowSummary } from './WorkflowSummary';

const TABS = ['resumen', 'definicion', 'versiones', 'probar'] as const;
type Tab = (typeof TABS)[number];

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
  const [params, setParams] = useSearchParams();
  const tab: Tab = TABS.includes(params.get('tab') as Tab) ? (params.get('tab') as Tab) : 'resumen';
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
            <Badge variant="default">v{agent.version}</Badge>
            {agent.archived && <Badge color="gray">Archivado</Badge>}
          </Group>
        }
        description={
          <>
            <Text span className="mono" size="sm">
              {agent.slug}
            </Text>
            {' · '}
            {ENGINE[agent.engine] ?? agent.engine}
            {' · voz '}
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
        actions={isAdmin ? <AgentActions agent={agent} /> : undefined}
      />
      <Tabs
        value={tab}
        onChange={(v) =>
          setParams(
            (prev) => {
              const next = new URLSearchParams(prev);
              if (!v || v === 'resumen') next.delete('tab');
              else next.set('tab', v);
              return next;
            },
            { replace: true },
          )
        }
        keepMounted
      >
        <Tabs.List mb="md">
          <Tabs.Tab value="resumen" leftSection={<IconInfoCircle size={16} />}>
            Resumen
          </Tabs.Tab>
          <Tabs.Tab value="definicion" leftSection={<IconFileCode size={16} />}>
            Definición
          </Tabs.Tab>
          <Tabs.Tab value="versiones" leftSection={<IconHistory size={16} />}>
            Versiones
          </Tabs.Tab>
          <Tabs.Tab value="probar" leftSection={<IconPlayerPlay size={16} />}>
            Probar
          </Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="resumen">
          <WorkflowSummary definition={agent.definition} />
        </Tabs.Panel>
        <Tabs.Panel value="definicion">
          <DefinitionTab agent={agent} canEdit={isAdmin} />
        </Tabs.Panel>
        <Tabs.Panel value="versiones">
          <VersionsTab agent={agent} canEdit={isAdmin} />
        </Tabs.Panel>
        <Tabs.Panel value="probar">
          <TestTab agent={agent} />
        </Tabs.Panel>
      </Tabs>
    </>
  );
}

export function AgentDetailPage() {
  const { id } = useParams();
  const query = useAgent(id);
  return <QueryState query={query}>{(agent) => <AgentView key={agent.id} agent={agent} />}</QueryState>;
}
