import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router';
import { fetchMe, resetSession } from '@/features/auth/api';
import { notifyError } from '@/lib/notify';
import { setSupportClientId } from './session';

/** Entrar como un cliente o volver a la administración. Las query keys no llevan el cliente: al cambiar
 * se borra la caché y se relee `me` antes de navegar. */
export function useSupportSwitch() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [pending, setPending] = useState(false);

  const go = async (clientId: string | null, path: string) => {
    setPending(true);
    setSupportClientId(clientId);
    try {
      resetSession(qc, await fetchMe());
      void navigate(path);
    } catch (e) {
      setSupportClientId(null);
      resetSession(qc, await fetchMe().catch(() => null));
      notifyError(e, 'No se pudo entrar al cliente');
    } finally {
      setPending(false);
    }
  };

  return {
    pending,
    /** Entra al panel del cliente (por defecto, a su inicio). */
    enter: (clientId: string, path = '/') => go(clientId, path),
    /** Vuelve a /admin (o a `path`). */
    exit: (path = '/admin') => go(null, path),
  };
}
