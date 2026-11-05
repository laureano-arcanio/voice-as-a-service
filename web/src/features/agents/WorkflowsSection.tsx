import { Alert, Anchor, NumberInput, Select, Stack, Text } from '@mantine/core';
import { Link } from 'react-router';
import type { FieldError } from '@/api/errors';
import type { ClientTool } from '@/api/types';
import { QueryState } from '@/components/QueryState';
import { llmParameters } from '@/features/tools/draft';
import { useTools } from '@/features/tools/api';
import { CLIENT_TOOL_TYPE } from '@/lib/labels';
import { type Draft, PRE_CALL_TIMEOUT, type PostCallWhen, type WorkflowsDraft } from './draft';

const WHEN_OPTIONS: { value: PostCallWhen; label: string }[] = [
  { value: 'handoff_accepted', label: 'Cuando una persona del equipo acepta la derivación' },
  { value: 'always', label: 'Siempre, al terminar la conversación' },
];

/** Mensaje del error de la ruta (del guardado), o undefined. */
const errorAt = (errors: FieldError[], path: string) => errors.find((e) => e.path === path)?.message;

/** La herramienta tiene parámetros que completa el modelo: en un workflow todos los valores van fijos. */
function hasModelParams(t: ClientTool): boolean {
  const props = llmParameters(t.type, t.definition).properties;
  return !!props && typeof props === 'object' && Object.keys(props).length > 0;
}

/** El post-call se reintenta con la misma clave: solo una http que no sea GET la lleva. */
function canPostCall(t: ClientTool): boolean {
  if (t.type !== 'http') return false;
  const http = t.definition.http as { method?: unknown } | undefined;
  return String(http?.method ?? 'GET').toUpperCase() !== 'GET';
}

/**
 * Herramientas automáticas del agente (docs/features/HERRAMIENTAS.md): una antes de la conversación y otra
 * después. Las corre la plataforma, el modelo no las ve: se ofrecen solo las que no piden nada al modelo.
 */
export function WorkflowsEditor({
  draft,
  update,
  clientId,
  errors = [],
}: {
  draft: Draft;
  update: (fn: (d: Draft) => Draft) => void;
  clientId: string;
  /** Errores del servidor (guardado), con su ruta: van en cada campo. */
  errors?: FieldError[];
}) {
  const tools = useTools(clientId);
  const w = draft.workflows;
  const set = (patch: Partial<WorkflowsDraft>) =>
    update((d) => ({ ...d, workflows: { ...d.workflows, ...patch } }));

  return (
    <QueryState query={tools}>
      {(list) => {
        const bySlug = new Map(list.map((t) => [t.slug, t]));
        // Con tu propio agente el modelo no ve herramientas de Atentina: no se guardan, no cuentan como visibles.
        const visible = new Set(draft.external ? [] : draft.clientTools.map((g) => g.tool));
        // Se ofrecen las libres de parametros del modelo y no usadas como herramienta visible ni en el otro lugar.
        const options = (accept: (t: ClientTool) => boolean, other: string | undefined, current: string) =>
          list
            .filter((t) => t.slug === current || (accept(t) && !hasModelParams(t) && !visible.has(t.slug)))
            .filter((t) => t.slug !== other)
            .map((t) => ({ value: t.slug, label: `${t.slug} · ${CLIENT_TOOL_TYPE[t.type] ?? t.type}` }));
        // Una elegida que ya no sirve (se borró o cambió): se avisa; el servidor también la rechaza al guardar.
        const problem = (slug: string, accept: (t: ClientTool) => boolean): string | null => {
          const t = bySlug.get(slug);
          if (!t) return `La herramienta ${slug} ya no existe.`;
          if (visible.has(slug)) return `${slug} también es una herramienta del agente: el modelo la vería.`;
          if (hasModelParams(t)) return `${slug} tiene parámetros que completa el modelo: no sirve acá.`;
          if (!accept(t)) return `${slug} no sirve para esto.`;
          return null;
        };
        const pre = w.preCall;
        const post = w.postCall;
        const preProblem = pre ? problem(pre.tool, () => true) : null;
        const postProblem = post ? problem(post.tool, canPostCall) : null;

        if (!list.length && !pre && !post)
          return (
            <Text size="sm" c="dimmed">
              Todavía no hay herramientas.{' '}
              <Anchor component={Link} to="/tools" inherit>
                Creá una en Herramientas
              </Anchor>{' '}
              (una API de tu sistema) y elegila acá.
            </Text>
          );

        return (
          <Stack gap="md">
            <Stack gap="xs" className="def-item" style={{ padding: 'var(--mantine-spacing-sm)' }}>
              <Select
                label="Antes de la conversación"
                description="Corre apenas entra la llamada o el chat (por ejemplo, buscar a la persona por su teléfono). Lo que devuelve llega al agente como datos del contacto, según lo que cada valor tenga para mostrar u ocultar."
                placeholder="Ninguna"
                data={options(() => true, post?.tool, pre?.tool ?? '')}
                value={pre?.tool ?? null}
                onChange={(tool) =>
                  set({
                    preCall: tool ? { tool, timeoutMs: pre?.timeoutMs ?? PRE_CALL_TIMEOUT.default } : null,
                  })
                }
                error={errorAt(errors, 'workflows.pre_call.tool')}
                searchable
                clearable
                classNames={{ input: 'mono' }}
              />
              {preProblem && <Alert color="yellow">{preProblem}</Alert>}
              {pre && (
                <NumberInput
                  label="Tiempo máximo de espera"
                  description="Si no responde en este tiempo, la conversación sigue sin esos datos."
                  min={PRE_CALL_TIMEOUT.min}
                  max={PRE_CALL_TIMEOUT.max}
                  step={100}
                  suffix=" ms"
                  allowDecimal={false}
                  allowNegative={false}
                  value={pre.timeoutMs}
                  onChange={(v) =>
                    set({
                      preCall: { ...pre, timeoutMs: typeof v === 'number' ? v : PRE_CALL_TIMEOUT.default },
                    })
                  }
                  error={errorAt(errors, 'workflows.pre_call.timeout_ms')}
                  w={{ base: '100%', xs: 260 }}
                />
              )}
            </Stack>

            <Stack gap="xs" className="def-item" style={{ padding: 'var(--mantine-spacing-sm)' }}>
              <Select
                label="Después de la conversación"
                description="Corre una sola vez y se reintenta si falla la conexión (por ejemplo, registrar un cobro). Tiene que ser una API que no sea de solo lectura (GET)."
                placeholder="Ninguna"
                data={options(canPostCall, pre?.tool, post?.tool ?? '')}
                value={post?.tool ?? null}
                onChange={(tool) =>
                  set({
                    postCall: tool ? { tool, when: post?.when ?? 'handoff_accepted' } : null,
                  })
                }
                error={errorAt(errors, 'workflows.post_call.tool')}
                searchable
                clearable
                classNames={{ input: 'mono' }}
              />
              {postProblem && <Alert color="yellow">{postProblem}</Alert>}
              {post && (
                <Select
                  label="Cuándo corre"
                  data={WHEN_OPTIONS}
                  value={post.when}
                  onChange={(when) => when && set({ postCall: { ...post, when: when as PostCallWhen } })}
                  allowDeselect={false}
                  error={errorAt(errors, 'workflows.post_call.when')}
                  maw={420}
                />
              )}
              {post?.when === 'handoff_accepted' && !draft.handoff.areas.length && (
                // Sin áreas no hay derivación, y nadie acepta: la condición no se cumple nunca.
                <Alert color="yellow">
                  Este agente no tiene áreas de derivación: nadie va a aceptar una derivación y esta
                  herramienta no va a correr. Agregá un área en «Derivación a personas» o elegí «Siempre, al
                  terminar la conversación».
                </Alert>
              )}
            </Stack>

            <Text size="xs" c="dimmed">
              Se ofrecen las herramientas con todos sus valores fijos: las que completa el modelo no sirven
              acá.{' '}
              <Anchor component={Link} to="/tools" inherit>
                Ver herramientas
              </Anchor>
            </Text>
          </Stack>
        );
      }}
    </QueryState>
  );
}
