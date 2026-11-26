import { Badge, Card, Divider, Group, Paper, Stack, Text } from '@mantine/core';
import { IconArrowRight, IconCheck, IconX } from '@tabler/icons-react';
import type { CaseResult, Repetition, VariantResult } from './api';
import { fallbackCount, fallbackReason, llmLabel, variantLabel } from './api';

function Highlight({ text, span }: { text: string; span?: string }) {
  if (!span) return <>{text || <Text span c="dimmed">(sin texto)</Text>}</>;
  const i = text.indexOf(span);
  if (i < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, i)}
      <mark data-testid="check-span">{span}</mark>
      {text.slice(i + span.length)}
    </>
  );
}

function passColor(passed: number, total: number) {
  if (total === 0) return 'gray';
  if (passed === total) return 'green';
  if (passed === 0) return 'red';
  return 'yellow';
}

function RepetitionRow({ rep, index }: { rep: Repetition; index: number }) {
  const llm = llmLabel(rep.llm);
  return (
    <Paper withBorder p="sm" data-testid="repetition">
      <Group gap="xs" mb={4}>
        <Text size="xs" c="dimmed">
          Repetición {index + 1}
        </Text>
        <Badge size="xs" color={rep.passed ? 'green' : 'red'} leftSection={rep.passed ? <IconCheck size={10} /> : <IconX size={10} />}>
          {rep.passed ? 'Pasa' : 'Falla'}
        </Badge>
        <Text size="xs" c="dimmed">
          {rep.ms} ms
        </Text>
        {llm && (
          <Text size="xs" c={rep.llm.fallback_from ? 'orange.8' : 'dimmed'}>
            {llm}
          </Text>
        )}
      </Group>
      <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
        <Highlight text={rep.text} span={rep.failures.find((f) => f.span)?.span} />
      </Text>
      {rep.handoff && (
        <Text size="xs" mt={4}>
          <IconArrowRight size={12} aria-hidden /> Derivó a <b>{rep.handoff}</b>
        </Text>
      )}
      {rep.tools.length > 0 && (
        <Text size="xs" mt={4} c="dimmed">
          Herramientas: {rep.tools.map((t) => `${t.name}${t.recorded ? '' : ' (sin resultado grabado)'}`).join(', ')}
        </Text>
      )}
      {rep.failures.length > 0 && (
        <Stack gap={2} mt={4}>
          {rep.failures.map((f, i) => (
            <Text key={i} size="xs" c="red.7">
              {f.message}
              {f.span && (
                <Text span c="dimmed">
                  {' '}
                  («{f.span}»)
                </Text>
              )}
            </Text>
          ))}
        </Stack>
      )}
      {rep.error && (
        <Text size="xs" c="red.7" mt={4}>
          {rep.error}
        </Text>
      )}
    </Paper>
  );
}

function VariantBlock({ variant }: { variant: VariantResult }) {
  const fallbacks = fallbackCount(variant);
  const reason = fallbackReason(variant);
  return (
    <Stack gap="xs">
      <Group gap="xs">
        <Badge color="gray">{variantLabel(variant.key, variant.label)}</Badge>
        <Badge color={passColor(variant.passed, variant.total)}>
          pasa {variant.passed}/{variant.total}
        </Badge>
        {variant.errors > 0 && <Badge color="red">{variant.errors} con error</Badge>}
        {fallbacks > 0 && (
          <Badge color="orange">
            {`${fallbacks} de ${variant.total} las contestó el respaldo local${reason ? ` (${reason})` : ''}`}
          </Badge>
        )}
      </Group>
      {variant.repetitions.map((rep, i) => (
        <RepetitionRow key={i} rep={rep} index={i} />
      ))}
    </Stack>
  );
}

/** Las respuestas de una corrida, por caso y variante (app/agent_tests/runner.py). */
export function RunResults({ results }: { results: CaseResult[] }) {
  if (!results.length) return <Text size="sm" c="dimmed">Todavía no hay resultados.</Text>;
  return (
    <Stack gap="md">
      {results.map((item) => (
        <Card key={item.case_id} withBorder>
          <Group gap="xs" mb="xs">
            <Text fw={600}>{item.name || 'Caso'}</Text>
            {item.known_failure && <Badge color="gray">Falla conocida</Badge>}
          </Group>
          {item.variants.map((variant) => (
            <div key={variant.key}>
              <VariantBlock variant={variant} />
              <Divider my="sm" />
            </div>
          ))}
        </Card>
      ))}
    </Stack>
  );
}
