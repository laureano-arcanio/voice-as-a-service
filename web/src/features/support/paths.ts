import { useIsAdmin } from '@/features/auth/api';

/** Para las pantallas que están en las dos áreas (Inicio, Reportes, Conversaciones, Uso de la API): la ruta en el
 * área actual. `areaPath('/calls/1')` es `/admin/calls/1` en la administración y `/calls/1` en el cliente. */
export function useAreaPath(): (path: string) => string {
  const isAdmin = useIsAdmin();
  return (path) => (isAdmin ? `/admin${path === '/' ? '' : path}` : path);
}
