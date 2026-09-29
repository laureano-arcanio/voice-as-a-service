/** Ejemplo de uso de una API key: lanzar una llamada saliente. */
export function curlExample(origin: string, key: string, agentId = '<agent_id>') {
  return `curl -X POST ${origin}/api/v1/calls \\
  -H "Authorization: Bearer ${key}" \\
  -H 'Content-Type: application/json' \\
  -d '{"agent_id":"${agentId}","phone":"+549..."}'`;
}
