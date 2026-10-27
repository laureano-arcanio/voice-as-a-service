import { AUTH_TYPES, type CredentialType } from './draft';

/** Lo que pide cada tipo como valor secreto. */
export const CREDENTIAL_VALUE: Record<CredentialType, { label: string; suffix: string }> = {
  bearer: { label: 'Token', suffix: 'TOKEN' },
  api_key: { label: 'API key', suffix: 'KEY' },
  basic: { label: 'Clave', suffix: 'PASSWORD' },
  oauth2_client_credentials: { label: 'Client secret', suffix: 'CLIENT_SECRET' },
};

export const CREDENTIAL_TYPE_LABEL: Record<string, string> = Object.fromEntries(
  AUTH_TYPES.map((t) => [t.value, t.label]),
);

/** "API del CRM" -> "api_del_crm" (slug de herramientas: minusculas, numeros y _). */
export function slugify(name: string): string {
  const s = name
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 48);
  return /^[a-z]/.test(s) ? s : `api_${s}`.replace(/_+$/, '');
}
