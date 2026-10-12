import {
  Alert,
  Anchor,
  Badge,
  Button,
  Checkbox,
  Group,
  SegmentedControl,
  Stack,
  Switch,
  Text,
} from '@mantine/core';
import { Link } from 'react-router';
import type { App } from '@/api/types';
import { QueryState } from '@/components/QueryState';
import { useApps } from '@/features/apps/api';
import { useIsAdmin } from '@/features/auth/api';
import { TOOL_KIND } from '@/lib/labels';
import type { Draft, ToolGrantDraft } from './draft';
import { setGrant } from './grants';

const count = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

function AppGrant({
  app,
  grant,
  onChange,
}: {
  app: App;
  grant: ToolGrantDraft | undefined;
  onChange: (tools: string[] | null) => void;
}) {
  const tools = app.tools ?? [];
  const all = grant?.tools.includes('*') ?? false;
  return (
    <div className="def-item" style={{ padding: 'var(--mantine-spacing-sm)' }}>
      <Group justify="space-between" wrap="wrap" gap="sm">
        <Switch
          checked={!!grant}
          onChange={(e) => onChange(e.currentTarget.checked ? ['*'] : null)}
          label={
            <Text size="sm" fw={600} span>
              {app.name}{' '}
              <Text span size="xs" c="dimmed" className="mono">
                {app.slug}
              </Text>
            </Text>
          }
        />
        {grant && (
          <SegmentedControl
            size="xs"
            value={all ? 'all' : 'some'}
            onChange={(v) => onChange(v === 'all' ? ['*'] : tools.map((t) => t.name))}
            data={[
              { value: 'all', label: 'Todas' },
              { value: 'some', label: 'Elegir' },
            ]}
            aria-label={`Herramientas de ${app.name}`}
          />
        )}
      </Group>
      {grant && !all && (
        <Checkbox.Group value={grant.tools} onChange={(v) => onChange(v)} mt="sm">
          <Stack gap={6}>
            {tools.map((t) => {
              const k = TOOL_KIND[t.kind] ?? { label: t.kind, color: 'gray' };
              return (
                <Checkbox
                  key={t.name}
                  value={t.name}
                  label={
                    <Group gap={6} wrap="nowrap" component="span">
                      <Text span className="mono" size="sm">
                        {t.name}
                      </Text>
                      <Badge color={k.color}>{k.label}</Badge>
                    </Group>
                  }
                  description={t.description}
                />
              );
            })}
          </Stack>
        </Checkbox.Group>
      )}
      {grant && all && (
        <Text size="xs" c="dimmed" mt={6}>
          {count(tools.length, 'herramienta', 'herramientas')} y{' '}
          {count(app.views?.length ?? 0, 'vista', 'vistas')}, incluidas las que se agreguen en versiones
          nuevas de la app.
        </Text>
      )}
    </div>
  );
}

/** Herramientas del motor assistant: las de las apps del cliente del agente. */
export function ToolsEditor({
  draft,
  update,
  clientId,
}: {
  draft: Draft;
  update: (fn: (d: Draft) => Draft) => void;
  clientId: string;
}) {
  const isAdmin = useIsAdmin();
  const apps = useApps(clientId);
  const change = (app: string, next: string[] | null) =>
    update((d) => ({ ...d, tools: setGrant(d.tools, app, next) }));

  return (
    <QueryState query={apps}>
      {(list) => {
        const known = new Set(list.map((a) => a.slug));
        const missing = draft.tools.filter((g) => !known.has(g.app));
        return (
          <Stack gap="xs">
            {list.length === 0 && (
              <Text size="sm" c="dimmed">
                Este cliente no tiene apps.{' '}
                {isAdmin ? (
                  <>
                    Asignale una en{' '}
                    <Anchor component={Link} to="/apps" inherit>
                      Apps
                    </Anchor>
                    .
                  </>
                ) : (
                  'Escribinos para armar la de tu negocio.'
                )}
              </Text>
            )}
            {list.map((a) => (
              <AppGrant
                key={a.id}
                app={a}
                grant={draft.tools.find((g) => g.app === a.slug)}
                onChange={(next) => change(a.slug, next)}
              />
            ))}
            {missing.map((g) => (
              <Alert key={g.app} color="yellow" title={`La app ${g.app} ya no es de este cliente`}>
                <Group justify="space-between" gap="xs">
                  <Text size="sm">Sacala para poder guardar.</Text>
                  <Button size="compact-sm" variant="subtle" color="red" onClick={() => change(g.app, null)}>
                    Sacar
                  </Button>
                </Group>
              </Alert>
            ))}
            {list.length > 0 && draft.tools.length === 0 && (
              <Text size="xs" c="dimmed">
                Sin herramientas, el asistente no puede ver ni registrar datos.
              </Text>
            )}
          </Stack>
        );
      }}
    </QueryState>
  );
}
