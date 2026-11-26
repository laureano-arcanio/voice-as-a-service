import { Anchor, List } from '@mantine/core';
import type { FieldError } from '@/api/errors';

/** Lista de errores por campo; cada uno lleva al campo con `onPick`. */
export function ErrorList({
  errors,
  label,
  onPick,
}: {
  errors: FieldError[];
  label: (path: string) => string;
  onPick: (path: string) => void;
}) {
  return (
    <List size="sm" spacing={4}>
      {errors.map((e, i) => (
        <List.Item key={i}>
          {e.path ? (
            <Anchor component="button" type="button" size="sm" onClick={() => onPick(e.path)}>
              {label(e.path)}
            </Anchor>
          ) : null}
          {e.path ? ': ' : ''}
          {e.message}
        </List.Item>
      ))}
    </List>
  );
}
