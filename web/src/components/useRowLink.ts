import type { MouseEvent } from 'react';
import { useNavigate } from 'react-router';

/**
 * Fila de tabla que abre un detalle: `<Table.Tr {...rowLink(path)}>`. No abre desde los controles de la fila ni al
 * seleccionar texto para copiarlo. Acompañarla con un `RowLink`, que da el acceso por teclado.
 */
export function useRowLink() {
  const navigate = useNavigate();
  return (to: string) => ({
    style: { cursor: 'pointer' },
    onClick: (e: MouseEvent<HTMLTableRowElement>) => {
      if ((e.target as Element).closest('a, button, input, label')) return;
      if (window.getSelection()?.toString()) return;
      void navigate(to);
    },
  });
}
