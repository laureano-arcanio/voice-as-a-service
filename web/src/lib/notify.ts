import { notifications } from '@mantine/notifications';
import { errorMessage } from '@/api/errors';
import type { Invite } from '@/api/types';

export function notifySuccess(message: string, title?: string) {
  notifications.show({ color: 'green', title, message });
}

export function notifyError(err: unknown, title = 'No se pudo completar') {
  notifications.show({ color: 'red', title, message: errorMessage(err), autoClose: 8000 });
}

/** Resultado del mail para crear la clave (alta de cliente o reenvio). */
export function notifyInvite(invite: Invite, prefix = '') {
  if (invite.status === 'sent') {
    notifySuccess(`${prefix}Mandamos el email a ${invite.email} para que cree su clave.`);
  } else if (invite.status === 'disabled') {
    notifications.show({
      color: 'yellow',
      message: `${prefix}No se mandó el email a ${invite.email}: el servidor no tiene Resend configurado (RESEND_API_KEY).`,
      autoClose: 10000,
    });
  } else {
    notifications.show({
      color: 'red',
      title: 'No se pudo mandar el email',
      message: `${prefix}${invite.email}: ${invite.error ?? 'error de Resend'}. Reenvialo desde Usuarios.`,
      autoClose: 10000,
    });
  }
}
