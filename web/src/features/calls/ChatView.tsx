import { Badge, Group, Text } from '@mantine/core';
import { IconHeadset, IconMicrophone } from '@tabler/icons-react';
import { Fragment, useEffect, useRef } from 'react';
import { EmptyState } from '@/components/QueryState';
import { prettyJson } from '@/lib/format';
import type { ChatMessage, LlmCall } from '@/api/types';
import { recordingUrl } from './api';

/** Detalle de una herramienta del cliente en la traza (docs/TOOLS_PLAN.md). */
interface ToolTraceInfo {
  slug?: string;
  type?: string;
  revision?: number;
  ok?: boolean;
  status?: number | null;
  ms?: number;
  request?: unknown;
  logs?: string[];
}

/** Entradas de la traza que no son llamadas al modelo. */
const NOT_LLM = new Set(['herramienta', 'control']);

/** Una linea de la salida del turno con llamadas a herramientas: [{tool, arguments}]. */
type ToolCallLine = { tool: string; arguments: unknown }[];

function parseToolCalls(line: string): ToolCallLine | null {
  if (!line.startsWith('[')) return null;
  try {
    const v: unknown = JSON.parse(line);
    if (
      Array.isArray(v) &&
      v.length > 0 &&
      v.every((x) => x && typeof x === 'object' && typeof (x as { tool?: unknown }).tool === 'string')
    )
      return v as ToolCallLine;
  } catch {
    // texto comun
  }
  return null;
}

/** Argumentos en una linea: {"reason": "x"} -> reason: "x". */
function argsText(args: unknown): string {
  let v = args;
  if (typeof v === 'string') {
    try {
      v = JSON.parse(v);
    } catch {
      return v as string;
    }
  }
  if (v && typeof v === 'object' && !Array.isArray(v))
    return Object.entries(v)
      .map(([k, x]) => `${k}: ${JSON.stringify(x)}`)
      .join(', ');
  return JSON.stringify(v);
}

/** Salida del turno: el texto y, aparte, las herramientas que llamó (end_call, transfer_call, las del cliente). */
function TurnOutput({ output }: { output: string }) {
  const lines = output.split('\n');
  if (!lines.some((l) => parseToolCalls(l.trim()))) return <pre className="code">{prettyJson(output)}</pre>;
  const blocks: ({ text: string } | { calls: ToolCallLine })[] = [];
  for (const line of lines) {
    const calls = parseToolCalls(line.trim());
    const prev = blocks.at(-1);
    if (calls) blocks.push({ calls });
    else if (prev && 'text' in prev) prev.text += `\n${line}`;
    else blocks.push({ text: line });
  }
  return (
    <>
      {blocks.map((b, i) =>
        'calls' in b ? (
          b.calls.map((c, j) => (
            <Text key={`${i}-${j}`} size="xs" className="mono">
              → <b>{c.tool}</b>({argsText(c.arguments)})
            </Text>
          ))
        ) : b.text.trim() ? (
          <pre className="code" key={i}>
            {b.text.trim()}
          </pre>
        ) : null,
      )}
    </>
  );
}

function ControlTrace({ c }: { c: LlmCall }) {
  return (
    <div className="llm-call">
      <Group gap={6}>
        <b>control</b>
        <Badge color="yellow">{c.output}</Badge>
        {c.input && (
          <Text span size="xs" c="dimmed" className="mono">
            {c.input}
          </Text>
        )}
      </Group>
    </div>
  );
}

/** "slug {json}" -> nombre y argumentos. */
function splitToolInput(input: string): { name: string; args: string } {
  const i = input.indexOf(' ');
  return i < 0 ? { name: input, args: '' } : { name: input.slice(0, i), args: input.slice(i + 1) };
}

function ToolTrace({ c }: { c: LlmCall }) {
  const info = (c as LlmCall & { tool?: ToolTraceInfo }).tool;
  const { name, args } = splitToolInput(c.input);
  // Sin el detalle, el resultado dice si fallo.
  const ok = info?.ok ?? !/^(ERROR:|\{"ok":\s*false)/.test(c.output ?? '');
  return (
    <div className="llm-call">
      <Group gap={6}>
        <b>herramienta</b>
        <Text span className="mono" size="xs" fw={600}>
          {info?.slug ?? name}
        </Text>
        <Badge color={ok ? 'green' : 'red'}>{ok ? 'Funcionó' : 'Falló'}</Badge>
        {info?.status != null && (
          <Text span size="xs" c="dimmed" className="mono">
            HTTP {info.status}
          </Text>
        )}
        <Text span size="xs" c="dimmed" className="mono">
          {c.ms ?? '–'} ms
        </Text>
        {info?.revision != null && (
          <Text span size="xs" c="dimmed" className="mono">
            rev. {info.revision}
          </Text>
        )}
      </Group>
      {args && (
        <>
          <Text size="xs" c="dimmed">
            argumentos:
          </Text>
          <pre className="code">{prettyJson(args)}</pre>
        </>
      )}
      {info?.request != null && (
        <>
          <Text size="xs" c="dimmed">
            pedido:
          </Text>
          <pre className="code">{prettyJson(info.request)}</pre>
        </>
      )}
      {info?.logs && info.logs.length > 0 && (
        <>
          <Text size="xs" c="dimmed">
            logs:
          </Text>
          <pre className="code">{info.logs.join('\n')}</pre>
        </>
      )}
      <Text size="xs" c="dimmed">
        resultado:
      </Text>
      <pre className="code">{prettyJson(c.output ?? '')}</pre>
    </div>
  );
}

function LlmTraces({ calls, open, title }: { calls: LlmCall[]; open: boolean; title: string }) {
  const totalMs = calls.reduce((a, c) => a + (c.ms ?? 0), 0);
  const tools = calls.filter((c) => c.kind === 'herramienta').length;
  const llm = calls.filter((c) => !NOT_LLM.has(c.kind)).length;
  return (
    // key: el switch general abre o cierra todas; cada una se puede abrir sola.
    <details className="llm" open={open} key={String(open)}>
      <summary>
        {title} ({llm} llamada{llm !== 1 ? 's' : ''} al modelo
        {tools ? `, ${tools} herramienta${tools > 1 ? 's' : ''}` : ''}, {totalMs} ms)
      </summary>
      {calls.map((c, i) =>
        c.kind === 'herramienta' ? (
          <ToolTrace c={c} key={i} />
        ) : c.kind === 'control' ? (
          <ControlTrace c={c} key={i} />
        ) : (
          <div className="llm-call" key={i}>
            <div>
              <b>{c.kind ?? 'llm'}</b>{' '}
              <Text span size="xs" c="dimmed" className="mono">
                {c.ms ?? '–'} ms
              </Text>
              {c.first_token_ms != null && (
                <Text span size="xs" c="dimmed" className="mono">
                  {' · '}primer texto {c.first_token_ms} ms
                </Text>
              )}
              {c.provider && (
                <Text span size="xs" c="dimmed" className="mono">
                  {' · '}
                  {c.model ? `${c.provider}:${c.model}` : c.provider}
                </Text>
              )}
            </div>
            {c.error && (
              <Text size="xs" c="red.7">
                Error: {c.error}
              </Text>
            )}
            {c.fallback_from && (
              <Text size="xs" c="yellow.7">
                Respaldo: {c.fallback_from} falló{c.fallback_reason ? ` (${c.fallback_reason})` : ''} y
                contestó el servidor Atentina.
              </Text>
            )}
            {c.input && (
              <Text size="xs" c="dimmed">
                entrada: {c.input}
              </Text>
            )}
            {c.reasoning && (
              <>
                <Text size="xs" c="dimmed">
                  razonamiento:
                </Text>
                <pre className="code">{c.reasoning}</pre>
              </>
            )}
            <TurnOutput output={c.output ?? ''} />
          </div>
        ),
      )}
    </details>
  );
}

/** Persona del equipo del tramo que empieza en el mensaje i (derivacion), o null si no empieza uno. */
function legStart(messages: ChatMessage[], i: number): string | null {
  const leg = messages[i]?.handoff_leg;
  if (!leg || messages[i - 1]?.handoff_leg === leg) return null;
  return messages.find((m) => m.handoff_leg === leg && m.person)?.person ?? '';
}

/** Termino un tramo con la persona y sigue el agente. */
const legEnd = (messages: ChatMessage[], i: number) =>
  !!messages[i - 1]?.handoff_leg && !messages[i]?.handoff_leg;

/** Burbujas agente / interesado; baja sola al llegar mensajes nuevos. Lo que habló una persona del equipo
 * (llamada derivada) va con su nombre, y cada tramo con ella arranca con un separador. */
export function ChatView({
  messages,
  showLlm = false,
  llmTitle = 'Salida del LLM',
  agentLabel = 'Agente IA',
  userLabel = 'Interesado',
  maxHeight,
  conversationId,
}: {
  messages: ChatMessage[];
  showLlm?: boolean;
  /** Titulo del detalle plegado de cada mensaje. */
  llmTitle?: string;
  agentLabel?: string;
  userLabel?: string;
  maxHeight?: number;
  /** Para el reproductor de cada mensaje grabado (agent.record_audio). */
  conversationId?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const count = messages.length;
  useEffect(() => {
    const el = ref.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [count]);

  if (!count) {
    return <EmptyState>Todavía no hay mensajes.</EmptyState>;
  }
  return (
    <div className="chat" ref={ref} style={maxHeight ? { maxHeight } : undefined}>
      {messages.map((m, i) => {
        const leg = legStart(messages, i);
        const person = m.role === 'assistant' && m.person;
        return (
          <Fragment key={i}>
            {leg !== null && (
              <div className="chat-leg label" role="separator">
                <IconHeadset size={16} aria-hidden />
                {leg ? `Llamada con ${leg}` : 'Llamada con el equipo'}
              </div>
            )}
            {legEnd(messages, i) && (
              <div className="chat-leg label" role="separator">
                Vuelve {agentLabel}
              </div>
            )}
            <div
              className={`bubble ${m.role === 'assistant' ? (person ? 'agent team' : 'agent') : 'client'}`}
            >
              <span className="who label">
                {person ? `${m.person} (equipo)` : m.role === 'assistant' ? agentLabel : userLabel}
              </span>
              {m.voice_note && (
                <span className="voice-note">
                  <IconMicrophone size={12} aria-hidden />
                  {m.role === 'assistant' ? 'Enviada como nota de voz' : 'Transcripción de nota de voz'}
                </span>
              )}
              {m.text}
              {conversationId && m.recording != null && (
                <audio
                  controls
                  preload="none"
                  className="bubble-recording"
                  src={recordingUrl(conversationId, m.recording)}
                />
              )}
              {m.llm && m.llm.length > 0 && <LlmTraces calls={m.llm} open={showLlm} title={llmTitle} />}
            </div>
          </Fragment>
        );
      })}
    </div>
  );
}
