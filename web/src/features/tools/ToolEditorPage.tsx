import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  List,
  SegmentedControl,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconAlertCircle,
  IconArrowLeft,
  IconDeviceFloppy,
  IconHistory,
  IconTrash,
} from '@tabler/icons-react';
import { useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { ApiError } from '@/api/errors';
import type { ClientTool, ToolType } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { JsonEditor } from '@/components/JsonEditor';
import { PageHeader } from '@/components/PageHeader';
import { PlanGate } from '@/components/PlanGate';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useIsAdmin } from '@/features/auth/api';
import { stableJson } from '@/features/agents/draft';
import { CLIENT_TOOL_TYPE } from '@/lib/labels';
import { notifyError, notifySuccess } from '@/lib/notify';
import {
  useCodeTemplate,
  useCreateTool,
  useDeleteTool,
  useTool,
  toolsHref,
  useToolsClient,
  useToolsStatus,
  useUpdateTool,
} from './api';
import {
  emptyDraft,
  errorTab,
  fromToolDraft,
  type Json,
  llmTool,
  requiredSecrets,
  schemaToRows,
  TOOL_SLUG_RE,
  type ToolDraft,
  toolPathLabel,
  toToolDraft,
} from './draft';
import { CodeForm, HttpForm } from './ToolForms';
import { ToolHistory } from './ToolHistory';
import { ToolTestPanel } from './ToolTestPanel';

type Mode = 'form' | 'json';

const canonical = (type: ToolType, d: Json) => stableJson(fromToolDraft(toToolDraft(type, d)));

/** Editor de una herramienta (nueva o existente), con su prueba y lo que ve el modelo. */
function ToolEditor({
  clientId,
  type,
  initial,
  saved,
}: {
  clientId: string;
  type: ToolType;
  initial: ToolDraft;
  /** La herramienta guardada; null si es nueva. */
  saved: ClientTool | null;
}) {
  const isAdmin = useIsAdmin();
  const navigate = useNavigate();
  const status = useToolsStatus();
  const create = useCreateTool(clientId);
  const update = useUpdateTool(clientId);
  const remove = useDeleteTool(clientId);
  const [draft, setDraft] = useState(initial);
  const [slug, setSlug] = useState(saved?.slug ?? '');
  const [mode, setMode] = useState<Mode>('form');
  const [jsonText, setJsonText] = useState('');
  const [tab, setTab] = useState('query');
  const [base, setBase] = useState(() => stableJson(fromToolDraft(initial)));
  const [historyOpen, history] = useDisclosure(false);

  const parsed = useMemo((): Json | null => {
    if (mode === 'form') return fromToolDraft(draft);
    try {
      const v: unknown = JSON.parse(jsonText);
      return v && typeof v === 'object' && !Array.isArray(v) ? (v as Json) : null;
    } catch {
      return null;
    }
  }, [mode, draft, jsonText]);
  const definition = parsed ?? fromToolDraft(draft);
  const dirty = !saved || (parsed !== null && canonical(type, parsed) !== base);
  const secrets = requiredSecrets(type, definition);
  const saveError = (saved ? update.error : create.error) as unknown;
  const errors = saveError instanceof ApiError ? saveError.errors : [];
  const errorTabs = new Set(errors.map((e) => errorTab(e.path, e.message)).filter((t): t is string => !!t));
  const slugError =
    slug && !TOOL_SLUG_RE.test(slug) ? 'Minúsculas, números y _ (ej. consultar_turnos)' : undefined;
  const runnerDown = type === 'code' && status.data?.code_runner === false;

  const switchMode = (next: Mode) => {
    if (next === mode) return;
    if (next === 'json') {
      setJsonText(JSON.stringify(fromToolDraft(draft), null, 2));
      setMode('json');
      return;
    }
    if (!parsed) return notifyError(new Error('Corregí el JSON para volver al formulario.'), 'JSON inválido');
    setDraft(toToolDraft(type, parsed));
    setMode('form');
  };

  const save = () => {
    if (!parsed) return notifyError(new Error('Corregí el JSON antes de guardar.'), 'No se puede guardar');
    if (!saved) {
      if (!slug || slugError) return notifyError(new Error('Poné un nombre válido.'), 'No se puede guardar');
      create.mutate(
        { slug, type, definition: parsed },
        {
          onSuccess: (t) => {
            notifySuccess('Herramienta creada. Elegila en cada agente que la use.');
            void navigate(toolsHref(`/tools/${t.slug}`, clientId, isAdmin), { replace: true });
          },
          onError: (e) => notifyError(e, 'No se pudo guardar'),
        },
      );
      return;
    }
    update.mutate(
      { slug: saved.slug, body: { type, definition: parsed } },
      {
        onSuccess: (t) => {
          setBase(canonical(type, t.definition));
          notifySuccess(
            t.revision === saved.revision
              ? 'Sin cambios.'
              : `Guardada (revisión ${t.revision}). Rige desde ya.`,
          );
        },
        onError: (e) => {
          const tabFor =
            e instanceof ApiError ? e.errors.map((x) => errorTab(x.path, x.message)).find(Boolean) : null;
          if (tabFor) setTab(tabFor);
          notifyError(e, 'No se pudo guardar');
        },
      },
    );
  };

  const del = async () => {
    if (!saved) return;
    const ok = await confirmAction({
      title: `¿Borrar la herramienta ${saved.slug}?`,
      message: saved.used_by.length
        ? `La usan ${saved.used_by.map((a) => a.name).join(', ')}: sacala de cada agente antes.`
        : 'Los agentes ya no la pueden usar. Las conversaciones pasadas se conservan.',
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (ok)
      remove.mutate(saved.slug, {
        onSuccess: () => {
          notifySuccess('Herramienta borrada.');
          void navigate(toolsHref('/tools', clientId, isAdmin));
        },
        onError: (e) => notifyError(e, 'No se pudo borrar'),
      });
  };

  return (
    <Stack gap="md">
      {saved && (
        <ToolHistory
          clientId={clientId}
          slug={saved.slug}
          current={saved.revision}
          opened={historyOpen}
          onClose={history.close}
        />
      )}
      <Card py="sm" className="def-toolbar">
        <Group justify="space-between" wrap="wrap" gap="sm">
          <Group gap="xs">
            <Badge color="gray">{CLIENT_TOOL_TYPE[type]}</Badge>
            {saved && (
              <Text span c="dimmed" className="mono">
                revisión {saved.revision}
              </Text>
            )}
            {saved && dirty && <Badge color="yellow">Cambios sin guardar</Badge>}
            {parsed === null && <Badge color="red">JSON inválido</Badge>}
          </Group>
          <Group gap="xs">
            <SegmentedControl
              size="xs"
              data={[
                { value: 'form', label: 'Formulario' },
                { value: 'json', label: 'JSON' },
              ]}
              value={mode}
              onChange={(v) => switchMode(v as Mode)}
              aria-label="Modo del editor"
            />
            {saved && (
              <Button
                variant="default"
                size="xs"
                leftSection={<IconHistory size={16} />}
                onClick={history.open}
              >
                Historial
              </Button>
            )}
            {saved && (
              <Button
                variant="subtle"
                color="red"
                size="xs"
                leftSection={<IconTrash size={16} />}
                onClick={() => void del()}
              >
                Borrar
              </Button>
            )}
            <Button
              size="xs"
              leftSection={<IconDeviceFloppy size={16} />}
              onClick={save}
              loading={create.isPending || update.isPending}
              disabled={!dirty}
            >
              {saved ? 'Guardar cambios' : 'Crear herramienta'}
            </Button>
          </Group>
        </Group>
      </Card>

      {errors.length > 0 && (
        <Alert color="red" icon={<IconAlertCircle size={18} />} title="No se guardó">
          <List size="sm" spacing={4}>
            {errors.map((e, i) => (
              <List.Item key={i}>
                <Text span size="sm" fw={600}>
                  {toolPathLabel(e.path)}:
                </Text>{' '}
                {e.message}
              </List.Item>
            ))}
          </List>
        </Alert>
      )}

      <Grid gutter="md">
        <Grid.Col span={{ base: 12, lg: 7 }}>
          <Stack gap="md">
            {!saved && (
              <Card>
                <TextInput
                  label="Nombre"
                  description="Con este nombre la ve el agente y la elegís en cada agente. No se puede cambiar después."
                  placeholder="consultar_turnos"
                  classNames={{ input: 'mono' }}
                  value={slug}
                  onChange={(e) => setSlug(e.currentTarget.value.toLowerCase().replace(/[\s-]+/g, '_'))}
                  error={slugError ?? errors.find((e) => e.path === 'slug')?.message}
                  maw={360}
                  data-autofocus
                />
              </Card>
            )}
            {mode === 'json' ? (
              <Card>
                <Title order={4} mb={4}>
                  Definición en JSON
                </Title>
                <Text size="xs" c="dimmed" mb="sm">
                  La misma que arma el formulario (formato en docs/TOOLS_PLAN.md).
                </Text>
                <JsonEditor value={jsonText} onChange={setJsonText} />
              </Card>
            ) : type === 'http' ? (
              <HttpForm
                draft={draft}
                update={setDraft}
                secrets={secrets}
                tab={tab}
                onTab={setTab}
                errorTabs={errorTabs}
              />
            ) : (
              <CodeForm draft={draft} update={setDraft} runnerDown={runnerDown} />
            )}
          </Stack>
        </Grid.Col>
        <Grid.Col span={{ base: 12, lg: 5 }}>
          <Stack gap="md">
            <Card>
              <Title order={4} mb={4}>
                Lo que ve el agente
              </Title>
              <Text size="xs" c="dimmed" mb="sm">
                El nombre, la descripción y los parámetros que completa. Los valores fijos y los secretos no
                los ve.
              </Text>
              <pre className="code" style={{ margin: 0, maxHeight: 360, overflow: 'auto' }}>
                {JSON.stringify(llmTool(slug || saved?.slug || '', type, definition), null, 2)}
              </pre>
              <Text size="sm" fw={600} mt="sm">
                Secretos que pide
              </Text>
              {secrets.length ? (
                <Group gap={6} mt={4}>
                  {secrets.map((s) => (
                    <Badge key={s} color="gray" className="mono">
                      {s}
                    </Badge>
                  ))}
                </Group>
              ) : (
                <Text size="sm" c="dimmed">
                  Ninguno.
                </Text>
              )}
              {secrets.length > 0 && (
                <Text size="xs" c="dimmed" mt={4}>
                  Cada agente que la use tiene que tenerlos cargados (en el agente, sección Herramientas).
                </Text>
              )}
              {saved && saved.used_by.length > 0 && (
                <Text size="xs" c="dimmed" mt="sm">
                  La usan{' '}
                  {saved.used_by.map((a, i) => (
                    <span key={a.id}>
                      {i > 0 && ', '}
                      <Anchor component={Link} to={`/agents/${a.id}`} inherit>
                        {a.name}
                      </Anchor>
                    </span>
                  ))}
                  : los cambios rigen desde ya en sus conversaciones.
                </Text>
              )}
            </Card>
            <ToolTestPanel
              clientId={clientId}
              type={type}
              definition={definition}
              secrets={secrets}
              disabled={
                runnerDown
                  ? 'El sandbox de código no está disponible.'
                  : parsed === null
                    ? 'Corregí el JSON.'
                    : undefined
              }
            />
          </Stack>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}

function NewTool({ clientId, type }: { clientId: string; type: ToolType }) {
  const template = useCodeTemplate(type === 'code');
  if (type === 'http')
    return <ToolEditor clientId={clientId} type="http" initial={emptyDraft('http')} saved={null} />;
  return (
    <PlanGate feature="code_tools" what="herramientas de código">
      <QueryState query={template}>
        {(t) => {
          const d = emptyDraft('code');
          return (
            <ToolEditor
              clientId={clientId}
              type="code"
              initial={{
                ...d,
                code: {
                  ...d.code,
                  code: t.code,
                  parameters: schemaToRows(t.parameters),
                  // Los que usa la funcion de ejemplo, para que se pueda probar tal cual.
                  secrets: [...new Set(t.code.match(/secrets\.([A-Z][A-Z0-9_]+)/g) ?? [])].map((x) =>
                    x.slice(8),
                  ),
                  allowedHosts: [...new Set(t.code.match(/https:\/\/([a-z0-9.-]+)/g) ?? [])].map((x) =>
                    x.slice(8),
                  ),
                },
              }}
              saved={null}
            />
          );
        }}
      </QueryState>
    </PlanGate>
  );
}

function ExistingTool({ clientId, slug }: { clientId: string; slug: string }) {
  const tool = useTool(clientId, slug);
  return (
    <QueryState query={tool}>
      {(t) => {
        const editor = (
          <ToolEditor
            key={t.id}
            clientId={clientId}
            type={t.type}
            initial={toToolDraft(t.type, t.definition)}
            saved={t}
          />
        );
        return t.type === 'code' ? (
          <PlanGate feature="code_tools" what="herramientas de código">
            {editor}
          </PlanGate>
        ) : (
          editor
        );
      }}
    </QueryState>
  );
}

export function ToolEditorPage() {
  const { slug } = useParams();
  const [params] = useSearchParams();
  const isAdmin = useIsAdmin();
  const clientId = useToolsClient();
  const type: ToolType = params.get('type') === 'code' ? 'code' : 'http';
  const isNew = !slug;

  return (
    <>
      <PageHeader
        title={
          isNew
            ? type === 'code'
              ? 'Nueva herramienta de código'
              : 'Nueva herramienta: llamar a una API'
            : slug
        }
        docTitle={isNew ? 'Nueva herramienta' : `Herramienta ${slug}`}
        description={
          type === 'code' && isNew
            ? 'Una función en JavaScript que corre aislada, con los secretos del agente.'
            : isNew
              ? 'Un pedido HTTP a tu sistema. El agente completa los parámetros que marques y el resto va fijo.'
              : undefined
        }
        above={
          <Anchor component={Link} to={toolsHref('/tools', clientId, isAdmin)} size="sm">
            <Group gap={4} component="span">
              <IconArrowLeft size={16} />
              Herramientas
            </Group>
          </Anchor>
        }
      />
      {!clientId ? (
        <EmptyState>Elegí un cliente en Herramientas.</EmptyState>
      ) : (
        <PlanGate feature="custom_tools" what="herramientas para tus agentes">
          {isNew ? (
            <NewTool clientId={clientId} type={type} />
          ) : (
            <ExistingTool clientId={clientId} slug={slug} />
          )}
        </PlanGate>
      )}
    </>
  );
}
