import { Alert, Button, Group, Modal, PasswordInput, Stack, Text } from '@mantine/core';
import { useState } from 'react';
import type { WaAccount } from '@/api/types';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useRegisterWaAccount } from './api';

/** Reintenta la suscripcion de la app y el registro del numero (cuenta pendiente). */
export function RegisterModal({ account, onClose }: { account: WaAccount; onClose: () => void }) {
  const [pin, setPin] = useState('');
  const register = useRegisterWaAccount();
  const pinError = pin && !/^\d{6}$/.test(pin) ? 'Son 6 dígitos' : null;

  return (
    <Modal opened onClose={onClose} title={`Reintentar registro de ${account.display_phone_number}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (pinError) return;
          register.mutate(
            { id: account.id, pin: pin || null },
            {
              onSuccess: (a) => {
                notifySuccess(`${a.display_phone_number} conectado.`);
                onClose();
              },
              onError: (err) => notifyError(err, 'Meta no registró el número'),
            },
          );
        }}
      >
        <Stack>
          {account.status_reason && (
            <Alert color="yellow">
              <Text size="sm">Último error: {account.status_reason}</Text>
            </Alert>
          )}
          <Text size="sm">
            Vuelve a suscribir la app a la cuenta de WhatsApp Business y a registrar el número. No hace falta
            repetir la ventana de Meta.
          </Text>
          <PasswordInput
            label="PIN de verificación en dos pasos (opcional)"
            description={
              account.has_pin
                ? 'Vacío: el PIN guardado. Cargá otro solo si Meta dice que el PIN es incorrecto (133005).'
                : 'Vacío: se genera uno nuevo.'
            }
            value={pin}
            onChange={(e) => setPin(e.currentTarget.value.trim())}
            error={pinError}
            maxLength={6}
            inputMode="numeric"
            autoComplete="one-time-code"
            data-autofocus
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={register.isPending} disabled={!!pinError}>
              Reintentar
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
