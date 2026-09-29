import { Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import type { ReactNode } from 'react';

/** Confirmacion con modal; resuelve true si confirma. */
export function confirmAction({
  title,
  message,
  confirmLabel = 'Confirmar',
  danger = false,
}: {
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  danger?: boolean;
}): Promise<boolean> {
  return new Promise((resolve) => {
    modals.openConfirmModal({
      title,
      children: typeof message === 'string' ? <Text size="sm">{message}</Text> : message,
      labels: { confirm: confirmLabel, cancel: 'Cancelar' },
      confirmProps: danger ? { color: 'red' } : undefined,
      onConfirm: () => resolve(true),
      onCancel: () => resolve(false),
      onClose: () => resolve(false),
    });
  });
}
