import { Text } from '@mantine/core';
import { useEffect, useRef } from 'react';
import { prettyJson } from '@/lib/format';
import type { ChatMessage, LlmCall } from '@/api/types';

function LlmTraces({ calls, open }: { calls: LlmCall[]; open: boolean }) {
  const totalMs = calls.reduce((a, c) => a + (c.ms ?? 0), 0);
  return (
    // key: el switch general abre o cierra todas; cada una se puede abrir sola.
    <details className="llm" open={open} key={String(open)}>
      <summary>
        Salida del LLM ({calls.length} llamada{calls.length > 1 ? 's' : ''}, {totalMs} ms)
      </summary>
      {calls.map((c, i) => (
        <div className="llm-call" key={i}>
          <div>
            <b>{c.kind ?? 'llm'}</b>{' '}
            <Text span size="xs" c="dimmed">
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
  agentLabel = 'Agente IA',
  userLabel = 'Interesado',
  maxHeight,
}: {
  messages: ChatMessage[];
  showLlm?: boolean;
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
    return (
      <Text size="sm" c="dimmed" ta="center" py="md">
        Todavía no hay mensajes.
      </Text>
    );
  }
  return (
    <div className="chat" ref={ref} style={maxHeight ? { maxHeight } : undefined}>
      {messages.map((m, i) => (
        <div key={i} className={`bubble ${m.role === 'assistant' ? 'agent' : 'client'}`}>
          <span className="who">{m.role === 'assistant' ? agentLabel : userLabel}</span>
          {m.text}
          {m.llm && m.llm.length > 0 && <LlmTraces calls={m.llm} open={showLlm} />}
        </div>
      ))}
    </div>
  );
}
