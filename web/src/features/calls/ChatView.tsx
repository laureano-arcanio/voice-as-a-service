import { Text } from '@mantine/core';
import { IconHeadset, IconMicrophone } from '@tabler/icons-react';
import { Fragment, useEffect, useRef } from 'react';
import { EmptyState } from '@/components/QueryState';
import { prettyJson } from '@/lib/format';
import type { ChatMessage, LlmCall } from '@/api/types';
import { recordingUrl } from './api';

function LlmTraces({ calls, open, title }: { calls: LlmCall[]; open: boolean; title: string }) {
  const totalMs = calls.reduce((a, c) => a + (c.ms ?? 0), 0);
  return (
    // key: el switch general abre o cierra todas; cada una se puede abrir sola.
    <details className="llm" open={open} key={String(open)}>
      <summary>
        {title} ({calls.length} llamada{calls.length > 1 ? 's' : ''} al modelo, {totalMs} ms)
      </summary>
      {calls.map((c, i) => (
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
              Respaldo: {c.fallback_from} falló{c.fallback_reason ? ` (${c.fallback_reason})` : ''} y contestó
              el servidor Atentina.
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
          <pre className="code">{prettyJson(c.output ?? '')}</pre>
        </div>
      ))}
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
