import { Alert, Badge, List, Stack, Text } from '@mantine/core';
import { INTENTS } from '../format';
import type { Message } from '../types';

/** Intencion de una respuesta (LLM); "Revisar" si no se pudo analizar o el LLM no esta seguro. */
export function IntentBadge({ m }: { m: Message }) {
  const a = m.analysis;
  if (!a) return null;
  if (a.status === 'error') return <Badge color="yellow">Sin analizar</Badge>;
  const intent = a.intencion ? INTENTS[a.intencion] : null;
  return (
    <>
      {intent && <Badge color={intent.color}>{intent.label}</Badge>}
      {a.status === 'low_confidence' && <Badge color="yellow">Revisar</Badge>}
    </>
  );
}

/** Lo que dijo el LLM de una respuesta y lo que se cambio en el lead. */
export function AnalysisCard({ m }: { m: Message }) {
  const a = m.analysis;
  if (!a) return null;
  if (a.status === 'error')
    return (
      <Alert color="yellow" title="Sin analizar">
        El LLM no respondió: la respuesta quedó registrada y el lead pasó a «Respondió». Revisala a mano.
      </Alert>
    );
  return (
    <Alert color={a.status === 'low_confidence' ? 'yellow' : 'blue'} variant="light">
      <Stack gap={4}>
        <Text size="sm" fw={600}>
          {a.intencion ? INTENTS[a.intencion].label : 'Respuesta'}
          {a.confianza !== undefined && (
            <Text span size="xs" c="dimmed" fw={400}>
              {' '}
              · confianza {Math.round(a.confianza * 100)} %{a.matched_by ? ` · por ${a.matched_by}` : ''}
            </Text>
          )}
        </Text>
        {a.resumen && <Text size="sm">{a.resumen}</Text>}
        {a.status === 'low_confidence' && (
          <Text size="sm">El LLM no está seguro: no se cambió nada más que la etapa. Revisala.</Text>
        )}
        {a.applied && a.applied.length > 0 && (
          <List size="sm" spacing={0}>
            {a.applied.map((x) => (
              <List.Item key={x}>{x}</List.Item>
            ))}
          </List>
        )}
      </Stack>
    </Alert>
  );
}
