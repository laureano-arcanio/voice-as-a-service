import { Text } from '@mantine/core';
import { IconMicrophone } from '@tabler/icons-react';
import { useEffect, useRef } from 'react';
import { EmptyState } from '@/components/QueryState';
import { prettyJson } from '@/lib/format';
import type { ChatMessage, LlmCall } from '@/api/types';

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
          </div>
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

/** Burbujas agente / interesado; baja sola al llegar mensajes nuevos. */
export function ChatView({
  messages,
  showLlm = false,
  llmTitle = 'Salida del LLM',
  agentLabel = 'Agente IA',
  userLabel = 'Interesado',
  maxHeight,
}: {
  messages: ChatMessage[];
  showLlm?: boolean;
  /** Titulo del detalle plegado de cada mensaje. */
  llmTitle?: string;
  agentLabel?: string;
  userLabel?: string;
  maxHeight?: number;
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
      {messages.map((m, i) => (
        <div key={i} className={`bubble ${m.role === 'assistant' ? 'agent' : 'client'}`}>
          <span className="who label">{m.role === 'assistant' ? agentLabel : userLabel}</span>
          {m.voice_note && (
            <span className="voice-note">
              <IconMicrophone size={12} aria-hidden />
              {m.role === 'assistant' ? 'Enviada como nota de voz' : 'Transcripción de nota de voz'}
            </span>
          )}
          {m.text}
          {m.llm && m.llm.length > 0 && <LlmTraces calls={m.llm} open={showLlm} title={llmTitle} />}
        </div>
      ))}
    </div>
  );
}
