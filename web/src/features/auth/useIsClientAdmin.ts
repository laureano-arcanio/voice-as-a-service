import { useCurrentUser } from './api';

/** Admin del cliente: ve y hace lo que un Usuario no (docs/features/EQUIPO_TELEFONIA.md). Un admin de la
 * plataforma y el que entró como el cliente también; `client_role` nulo cuenta como Usuario. */
export function useIsClientAdmin(): boolean {
  const me = useCurrentUser();
  return me.role === 'admin' || me.support || me.client_role === 'admin';
}
