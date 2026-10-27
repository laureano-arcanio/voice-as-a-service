import {
  Alert,
  Anchor,
  Badge,
  Button,
  Group,
  MultiSelect,
  NumberInput,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { Link } from 'react-router';
import { QueryState } from '@/components/QueryState';
import { useIsAdmin } from '@/features/auth/api';
import { toolsHref, useAgentSecrets, useClientSecrets, useTools } from '@/features/tools/api';
import { CLIENT_TOOL_TYPE } from '@/lib/labels';
import { type ClientToolGrantDraft, type Draft, newKey, TOOL_SETTINGS } from './draft';

/** Herramientas del cliente (APIs y codigo, docs/TOOLS_PLAN.md): todos los agentes menos tu propio agente. */
export function ClientToolsEditor({
  draft,
  update,
  clientId,
  agentId,
}: {
  draft: Draft;
  update: (fn: (d: Draft) => Draft) => void;
  clientId: string;
  /** El agente guardado: sus valores propios cuentan como cargados. */
  agentId?: string;
}) {
  const isAdmin = useIsAdmin();
  const tools = useTools(clientId);
  const clientSecrets = useClientSecrets(clientId);
  const agentSecrets = useAgentSecrets(agentId);
  // Los secretos que tiene el agente: los del cliente y los propios.
  const have = new Set([
    ...(clientSecrets.data ?? []).filter((s) => !s.missing).map((s) => s.name),
    ...(agentSecrets.data ?? []).filter((s) => s.source === 'agent').map((s) => s.name),
  ]);
  const secretsLoaded = clientSecrets.isSuccess && (!agentId || agentSecrets.isSuccess);
  const toolsLink = toolsHref('/tools', clientId, isAdmin);
  const setGrants = (fn: (g: ClientToolGrantDraft[]) => ClientToolGrantDraft[]) =>
    update((d) => ({ ...d, clientTools: fn(d.clientTools) }));

  return (
    <QueryState query={tools}>
      {(list) => {
        const bySlug = new Map(list.map((t) => [t.slug, t]));
        const missing = draft.clientTools.filter((g) => !bySlug.has(g.tool));
        if (!list.length && !draft.clientTools.length)
          return (
            <Text size="sm" c="dimmed">
              Todavía no hay herramientas.{' '}
              <Anchor component={Link} to={toolsLink} inherit>
                Creá una en Herramientas
              </Anchor>{' '}
              (una API de tu sistema o una función) y elegila acá.
            </Text>
          );
        return (
          <Stack gap="xs">
            <MultiSelect
              label="Herramientas"
              description={
                <>
                  Las que puede usar este agente.{' '}
                  <Anchor component={Link} to={toolsLink} inherit>
                    Ver todas
                  </Anchor>
                </>
              }
              placeholder={draft.clientTools.length ? undefined : 'Elegí herramientas'}
              data={list.map((t) => ({
                value: t.slug,
                label: `${t.slug} · ${CLIENT_TOOL_TYPE[t.type] ?? t.type}`,
              }))}
              value={draft.clientTools.filter((g) => bySlug.has(g.tool)).map((g) => g.tool)}
              onChange={(slugs) =>
                setGrants((grants) => [
                  ...grants.filter((g) => slugs.includes(g.tool) || !bySlug.has(g.tool)),
                  ...slugs
                    .filter((s) => !grants.some((g) => g.tool === s))
                    .map((tool) => ({ key: newKey(), tool })),
                ])
              }
              searchable
              classNames={{ pill: 'mono' }}
            />
            {draft.clientTools
              .filter((g) => bySlug.has(g.tool))
              .map((g) => {
                const t = bySlug.get(g.tool)!;
                const confirm = t.definition.confirm === true;
                const lacking = secretsLoaded ? t.secrets.filter((x) => !have.has(x)) : [];
                return (
                  <div key={g.key} className="def-item" style={{ padding: 'var(--mantine-spacing-sm)' }}>
                    <Group justify="space-between" gap="sm" wrap="wrap">
                      <div style={{ flex: 1, minWidth: 200 }}>
                        <Group gap={6}>
                          <Anchor
                            component={Link}
                            to={toolsHref(`/tools/${t.slug}`, clientId, isAdmin)}
                            className="mono"
                            size="sm"
                            fw={600}
                          >
                            {t.slug}
                          </Anchor>
                          <Badge color="gray">{CLIENT_TOOL_TYPE[t.type] ?? t.type}</Badge>
                          {confirm && <Badge color="blue">Pide confirmación</Badge>}
                          {lacking.length > 0 && (
                            <Badge color="yellow" title="Cargalo abajo, en Secretos">
                              Falta {lacking.join(', ')}
                            </Badge>
                          )}
                        </Group>
                        <Text size="xs" c="dimmed" lineClamp={2}>
                          {String(t.definition.description ?? '')}
                        </Text>
                      </div>
                    </Group>
                  </div>
                );
              })}
            {missing.map((g) => (
              <Alert key={g.key} color="yellow" title={`La herramienta ${g.tool} ya no existe`}>
                <Group justify="space-between" gap="xs">
                  <Text size="sm">Sacala para poder guardar.</Text>
                  <Button
                    size="compact-sm"
                    variant="subtle"
                    color="red"
                    onClick={() => setGrants((grants) => grants.filter((x) => x.key !== g.key))}
                  >
                    Sacar
                  </Button>
                </Group>
              </Alert>
            ))}
            {draft.clientTools.length > 0 && (
              <Group gap="sm" align="flex-start" wrap="wrap">
                <NumberInput
                  label="Vueltas con herramientas por turno"
                  description={`Al llegar al tope, el turno termina con el mensaje de al lado. Vacío: ${TOOL_SETTINGS.maxCallsPerTurn}.`}
                  placeholder={String(TOOL_SETTINGS.maxCallsPerTurn)}
                  min={1}
                  max={10}
                  allowDecimal={false}
                  value={draft.maxToolCallsPerTurn ?? ''}
                  onChange={(v) =>
                    update((d) => ({ ...d, maxToolCallsPerTurn: typeof v === 'number' ? v : null }))
                  }
                  w={260}
                />
                <TextInput
                  label="Mensaje al llegar al tope"
                  description="Lo dice el agente en lugar de la respuesta. Vacío: el de la plataforma."
                  placeholder={TOOL_SETTINGS.limitMessage}
                  maxLength={300}
                  value={draft.toolLimitMessage}
                  onChange={(e) => {
                    const v = e.currentTarget.value;
                    update((d) => ({ ...d, toolLimitMessage: v }));
                  }}
                  style={{ flex: 1, minWidth: 240 }}
                />
              </Group>
            )}
          </Stack>
        );
      }}
    </QueryState>
  );
}
