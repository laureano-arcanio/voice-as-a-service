import { Badge, Group, Tooltip } from '@mantine/core';
import { Dash } from '@/components/Badges';

/** Etiquetas de un contacto, como pildoras grises; las que sobran, en un "+N". */
export function TagBadges({ tags, max = 4 }: { tags: string[]; max?: number }) {
  if (tags.length === 0) return <Dash />;
  return (
    <Group gap={4}>
      {tags.slice(0, max).map((t) => (
        <Badge key={t} color="gray">
          {t}
        </Badge>
      ))}
      {tags.length > max && (
        <Tooltip label={tags.slice(max).join(', ')} withArrow>
          <Badge color="gray">+{tags.length - max}</Badge>
        </Tooltip>
      )}
    </Group>
  );
}
