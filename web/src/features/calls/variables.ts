// Fuentes de las variables en el detalle de la conversación: `progress.variable_sources` de
// app/conversation/variables.py, en palabras.

export function variableSourceLabel(source: string): string {
  if (source === 'system') return 'del sistema';
  if (source === 'default') return 'valor por defecto';
  if (source === 'contact') return 'contacto o campaña';
  if (source === 'request') return 'pedido de la llamada';
  if (source.startsWith('pre_call:')) return `pre-call (${source.slice('pre_call:'.length)})`;
  if (source.startsWith('tool:')) return `herramienta (${source.slice('tool:'.length)})`;
  return source;
}
