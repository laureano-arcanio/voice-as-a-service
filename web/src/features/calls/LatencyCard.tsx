import { Card, Table, Text, Title } from '@mantine/core';
import { useState } from 'react';
import { CollapsibleCard } from '@/components/CollapsibleCard';
import { formatSeconds } from '@/lib/format';
import type { Latency, LatencyTurn } from './types';

const SUMMARY_KEYS = ['e2e', 'total', 'eou', 'stt', 'endpointing', 'llm', 'llm_total', 'tts'];

const COLUMNS: { key: keyof LatencyTurn; label: string }[] = [
  { key: 'e2e', label: 'E2E' },
  { key: 'total', label: 'Total' },
  { key: 'eou', label: 'EOU' },
  { key: 'stt', label: 'STT' },
  { key: 'endpointing', label: 'Endpointing' },
  { key: 'llm', label: 'LLM' },
  { key: 'llm_total', label: 'LLM total' },
  { key: 'tts', label: 'TTS TTFB' },
  { key: 'tts_audio', label: 'Audio' },
];

function LatencyBody({ latency }: { latency: Latency }) {
  const st = latency.stats ?? {};
  const summary = SUMMARY_KEYS.filter((k) => st[k]).map((k) => ({
    key: k,
    avg: st[k]?.avg,
    max: st[k]?.max,
  }));
  return (
    <>
      <Text size="xs" c="dimmed" mb="xs">
        Segundos desde que el cliente deja de hablar hasta que el agente empieza a sonar. <b>E2E</b> = medido
        por LiveKit hasta el primer audio. <b>Total</b> = EOU (STT + endpointing) + LLM (hasta el primer texto
        del mensaje; el JSON completo en <b>LLM total</b>) + TTS TTFB; no incluye escribir la primera oración.
      </Text>
      <Text size="sm" mb="sm">
        {latency.n_turns} turnos · promedio:{' '}
        {summary.map((s, i) => (
          <span key={s.key}>
            {i > 0 && ' · '}
            {s.key} <b>{formatSeconds(s.avg)}</b> (máx {formatSeconds(s.max)})
          </span>
        ))}
      </Text>
      <Table.ScrollContainer minWidth={760}>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th w={50}>#</Table.Th>
              {COLUMNS.map((c) => (
                <Table.Th key={c.key} ta="right">
                  {c.label}
                </Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(latency.turns ?? []).map((t, i) => (
              <Table.Tr key={i}>
                <Table.Td className="mono">{i + 1}</Table.Td>
                {COLUMNS.map((c) => (
                  <Table.Td key={c.key} ta="right" className="mono" fw={c.key === 'e2e' ? 600 : undefined}>
                    {formatSeconds(t[c.key])}
                  </Table.Td>
                ))}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </>
  );
}

/** Latencia por turno. Para el cliente es un dato tecnico: va plegada bajo "Detalle técnico". */
export function LatencyCard({ latency, folded }: { latency: Latency | null; folded: boolean }) {
  const [opened, setOpened] = useState(false);
  if (!latency?.n_turns) return null;
  if (folded) {
    return (
      <CollapsibleCard title="Detalle técnico" opened={opened} onToggle={() => setOpened((o) => !o)}>
        <Title order={5} mb={4}>
          Latencia por turno
        </Title>
        <LatencyBody latency={latency} />
      </CollapsibleCard>
    );
  }
  return (
    <Card>
      <Title order={4} mb={4}>
        Latencia por turno
      </Title>
      <LatencyBody latency={latency} />
    </Card>
  );
}
