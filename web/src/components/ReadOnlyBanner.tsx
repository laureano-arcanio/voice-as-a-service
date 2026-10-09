import { Alert } from '@mantine/core';
import { IconLock } from '@tabler/icons-react';
import { useReadOnly } from '@/features/auth/readOnly';

/** Aviso fijo arriba de cada pantalla cuando la cuenta del cliente esta inactiva. */
export function ReadOnlyBanner() {
  if (!useReadOnly()) return null;
  return (
    <Alert color="yellow" icon={<IconLock size={18} />} title="Cuenta en solo lectura" mb="md">
      Podés ver y exportar el historial, pero no hacer llamadas, usar WhatsApp ni campañas, probar agentes o
      voces, ni crear API keys. Escribinos para reactivar la cuenta.
    </Alert>
  );
}
