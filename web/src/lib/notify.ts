import { notifications } from '@mantine/notifications';
import { errorMessage } from '@/api/errors';

export function notifySuccess(message: string, title?: string) {
  notifications.show({ color: 'green', title, message });
}

export function notifyError(err: unknown, title = 'No se pudo completar') {
  notifications.show({ color: 'red', title, message: errorMessage(err), autoClose: 8000 });
}
