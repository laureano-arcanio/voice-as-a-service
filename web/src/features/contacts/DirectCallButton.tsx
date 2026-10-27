import { ActionIcon, Button, Tooltip } from '@mantine/core';
import { IconPhone } from '@tabler/icons-react';
import type { Contact } from '@/api/types';
import { useCurrentUser } from '@/features/auth/api';
import { useFeatureLock } from '@/features/billing/features';
import { usePhoneNumbers } from '@/features/numbers/api';
import { useOptionalDirectCall } from '@/features/phone/context';
import { storedFrom } from '@/features/phone/storage';
import { useBlockedNumbers } from './api';

/**
 * Llamar a un contacto desde el navegador, sin agente (llamada directa): sale desde el número que el usuario
 * eligió en Teléfono (o el primero de su cuenta) y sigue en la barra de abajo. Apagado, con el motivo en un
 * tooltip, si el plan no la incluye, el número está bloqueado, ya hay otra llamada o un admin está en soporte.
 */
export function DirectCallButton({
  contact,
  variant = 'icon',
}: {
  contact: Pick<Contact, 'id' | 'phone' | 'name'>;
  variant?: 'icon' | 'button';
}) {
  const phone = useOptionalDirectCall();
  const me = useCurrentUser();
  const lock = useFeatureLock('direct_calls');
  const numbers = usePhoneNumbers();
  const blocked = useBlockedNumbers();

  // Sin el provider (fuera del panel del cliente) no hay teléfono.
  if (!phone) return null;

  const own = (numbers.data ?? []).filter((n) => n.client_id === me.client_id);
  const from = own.find((n) => n.id === storedFrom.get(me.id)) ?? own[0] ?? null;
  const isBlocked = (blocked.data ?? []).some((b) => b.phone === contact.phone);
  const reason = lock.locked
    ? `Tu plan ${lock.tierName} no incluye llamadas directas.`
    : phone.disabledReason
      ? phone.disabledReason
      : isBlocked
        ? 'El número está bloqueado: desbloquealo en Contactos, Números bloqueados.'
        : phone.busy
          ? 'Ya estás en una llamada.'
          : numbers.data && !from
            ? 'Hace falta un número asignado a tu cuenta para llamar.'
            : null;
  const who = contact.name || contact.phone;
  const start = () => {
    if (reason) return;
    void phone.call(
      {
        contactId: contact.id,
        phone: contact.phone,
        name: contact.name,
        fromLabel: from ? (from.label ? `${from.e164} · ${from.label}` : from.e164) : null,
      },
      from?.id ?? null,
    );
  };

  return (
    <Tooltip label={reason ?? 'Llamar desde el navegador'} withArrow multiline w={reason ? 240 : undefined}>
      {variant === 'button' ? (
        <Button
          variant="default"
          leftSection={<IconPhone size={18} />}
          aria-label={`Llamar a ${who}`}
          data-disabled={!!reason || undefined}
          aria-disabled={!!reason || undefined}
          onClick={(e) => (reason ? e.preventDefault() : start())}
        >
          Llamar
        </Button>
      ) : (
        <ActionIcon
          variant="subtle"
          aria-label={`Llamar a ${who}`}
          data-disabled={!!reason || undefined}
          aria-disabled={!!reason || undefined}
          onClick={(e) => (reason ? e.preventDefault() : start())}
        >
          <IconPhone size={16} />
        </ActionIcon>
      )}
    </Tooltip>
  );
}
