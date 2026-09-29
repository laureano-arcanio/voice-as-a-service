import { Paper, SimpleGrid, Skeleton, Text } from '@mantine/core';
import type { Stats } from '@/api/types';
import { statTiles } from './stats';

const TONE: Record<string, string> = { ok: 'green.7', bad: 'red.7', warn: 'orange.7' };

export function StatsGrid({ stats }: { stats: Stats | undefined }) {
  return (
    <SimpleGrid cols={{ base: 2, sm: 4, xl: 8 }} spacing="sm">
      {(stats ? statTiles(stats) : Array.from({ length: 8 }, () => null)).map((t, i) => (
        <Paper key={t?.label ?? i} p="md" radius="md">
          {t ? (
            <>
              <Text
                fz={22}
                fw={700}
                c={t.tone && (stats?.total || t.tone === 'ok') ? TONE[t.tone] : undefined}
                lh={1.2}
              >
                {t.value}
              </Text>
              <Text size="xs" c="dimmed" mt={4}>
                {t.label}
              </Text>
            </>
          ) : (
            <>
              <Skeleton h={24} w="60%" />
              <Skeleton h={10} mt={8} w="80%" />
            </>
          )}
        </Paper>
      ))}
    </SimpleGrid>
  );
}
