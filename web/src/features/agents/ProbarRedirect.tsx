import { Navigate, useSearchParams } from 'react-router';

/** `/probar?agent=x` abre la pestaña Probar de ese agente; sin agente, la lista. */
export function ProbarRedirect() {
  const [params] = useSearchParams();
  const agent = params.get('agent');
  return <Navigate to={agent ? `/agents/${encodeURIComponent(agent)}?tab=probar` : '/agents'} replace />;
}
