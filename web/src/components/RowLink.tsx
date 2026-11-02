import { Anchor } from '@mantine/core';
import type { ReactNode } from 'react';
import { Link } from 'react-router';

/** Link dentro de una fila cliqueable, con el aspecto del texto: teclado, lector de pantalla y abrir en otra pestaña. */
export function RowLink({ to, label, children }: { to: string; label: string; children: ReactNode }) {
  return (
    <Anchor component={Link} to={to} c="inherit" size="sm" underline="never" aria-label={label}>
      {children}
    </Anchor>
  );
}
