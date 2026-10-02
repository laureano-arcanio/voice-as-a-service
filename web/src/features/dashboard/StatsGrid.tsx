import { Card, SimpleGrid, Skeleton, Stack, Text } from '@mantine/core';
import type { Stats } from '@/api/types';
import { useIsAdmin } from '@/features/auth/api';
import { statTiles } from './stats';

export function StatsGrid({ stats }: { stats: Stats | undefined }) {
  const isAdmin = useIsAdmin();
  return (
    <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="md">
      {(stats ? statTiles(stats, isAdmin) : Array.from({ length: 8 }, () => null)).map((t, i) => (
        <Card key={t?.label ?? i} padding="md">
          {t ? (
            <Stack gap={6} justify="space-between" h="100%">
              <Text className="label">{t.label}</Text>
              <Text className="metric" c={t.tone}>
                {t.value}
                {t.sub && (
                  <Text span size="sm" fw={500} c="dimmed" ff="text" ml={8} style={{ letterSpacing: 0 }}>
                    {t.sub}
                  </Text>
                )}
              </Text>
            </Stack>
          ) : (
            <>
              <Skeleton h={12} w="70%" />
              <Skeleton h={28} mt={10} w="45%" />
            </>
          )}
        </Card>
      ))}
    </SimpleGrid>
  );
}
