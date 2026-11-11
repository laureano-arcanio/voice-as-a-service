import { Group, Paper, Stack, Text } from '@mantine/core';
import { IconCheck, IconPhoneCall, IconPhoneOff } from '@tabler/icons-react';
import { useEffect, useState } from 'react';
import { buildView, type HandoffMode, type HandoffSnapshot } from '@/lib/handoffProgress';

interface Props {
  snapshot: HandoffSnapshot;
  /** `Date.now()` del navegador cuando llegó el snapshot: de ahí corren los contadores. */
  receivedAt: number;
  mode?: HandoffMode;
}

/** Derivación a una persona en curso o terminada: a quién se llama, en qué fase y cuánto va. */
export function HandoffProgress({ snapshot, receivedAt, mode = 'names' }: Props) {
  const [now, setNow] = useState(() => Date.now());
  const running = snapshot.state === 'running';
  useEffect(() => {
    if (!running) return;
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, [running, snapshot, receivedAt]);
  const v = buildView(snapshot, mode, receivedAt, now);
  const icon = running ? (
    <span className="live-dot" aria-hidden />
  ) : v.state === 'failed' ? (
    <IconPhoneOff size={16} color="var(--mantine-color-red-6)" aria-hidden />
  ) : v.state === 'connected' ? (
    <IconCheck size={16} color="var(--mantine-color-green-6)" aria-hidden />
  ) : (
    <IconPhoneCall size={16} aria-hidden />
  );
  return (
    <Paper withBorder radius="lg" p="sm" w="100%" data-handoff={v.state} aria-live="polite">
      <Stack gap={6}>
        <Group gap={8} wrap="nowrap" align="flex-start">
          <span style={{ paddingTop: 4, display: 'inline-flex' }}>{icon}</span>
          <Stack gap={0} style={{ minWidth: 0, flex: 1 }}>
            <Text size="sm" fw={600}>
              {v.headline}
            </Text>
            {v.note && (
              <Text size="xs" c="dimmed">
                {v.note}
              </Text>
            )}
          </Stack>
          <Text size="xs" c="dimmed" className="mono" aria-label="Tiempo total">
            {v.total}
          </Text>
        </Group>
        {v.live && (
          <Text size="sm" className="mono" data-live>
            {v.live}
          </Text>
        )}
        {(v.attempts.length > 0 || v.extra.length > 0) && (
          <Stack gap={4} pt={4} style={{ borderTop: '1px solid var(--app-line)' }}>
            {v.extra.map((e) => (
              <Text key={e} size="xs" c="dimmed">
                {e}
              </Text>
            ))}
            {v.attempts.map((a, i) => (
              <Text key={i} size="xs" c="gray.7">
                <b>{a.who}</b>
                {a.note ? ` · ${a.note}` : ''}
                {a.result ? ` · ${a.result}` : ''}
                {a.detail && (
                  <Text span size="xs" c="dimmed">
                    {' '}
                    · {a.detail}
                  </Text>
                )}
              </Text>
            ))}
          </Stack>
        )}
      </Stack>
    </Paper>
  );
}
