import type { LlmConnection, LlmConnectionKind } from '@/api/types';

export const KIND_LABEL: Record<LlmConnectionKind, string> = {
  openai_compatible: 'OpenAI compatible',
  openrouter: 'OpenRouter',
  anthropic: 'Anthropic',
};

export const KIND_HELP: Record<LlmConnectionKind, string> = {
  openai_compatible: 'OpenAI, Groq, Together, DeepSeek o un servidor propio con API de OpenAI.',
  openrouter: 'Una sola clave para modelos de muchos proveedores.',
  anthropic: 'Claude, con la API nativa de Anthropic.',
};

/** Como pide el JSON el proveedor (lo detecta la prueba de la conexion). */
export const JSON_MODE_LABEL: Record<LlmConnection['json_mode'], string> = {
  json_schema: 'JSON estricto',
  json_object: 'JSON con esquema en el prompt',
  prompt: 'Esquema en el prompt',
};

export const LOCAL_LABEL = 'Servidor Atentina';

/** "Mi OpenRouter · …a91f", para elegir una conexion en un selector. */
export const connectionLabel = (c: Pick<LlmConnection, 'name' | 'last4'>) =>
  c.last4 ? `${c.name} · …${c.last4}` : c.name;
