import type { HandoffArea } from '@/api/types';

// Borrador del bloque `whatsapp` de un area (app/services/handoff.py, validate_whatsapp): cuenta, plantillas con
// los valores de cada {{n}} y la espera por persona en la rotacion.

export type AreaWhatsapp = NonNullable<HandoffArea['whatsapp']>;

export interface TemplateDraft {
  name: string;
  language: string;
  /** Un valor por cada {{n}} del cuerpo, en orden. */
  params: string[];
}

export interface WhatsappDraft {
  /** '' = el area no usa WhatsApp. */
  accountId: string;
  template: TemplateDraft | null;
  callTemplate: TemplateDraft | null;
  /** A la persona que acepta la derivacion; a diferencia de las otras, puede llevar cliente. */
  acceptTemplate: TemplateDraft | null;
  waitSeconds: number | string;
  /** Un switch por momento (area de llamada); apagarlo deja la plantilla en null. */
  callOn: boolean;
  acceptOn: boolean;
  rotationOn: boolean;
}

export const WAIT_SECONDS = { default: 120, min: 30, max: 3600 };
/** Los valores que da la plataforma; ademas, cualquier variable del pre-call del agente. */
export const BASE_VARIABLES = ['area', 'persona', 'cliente', 'resumen', 'horario'];
const PARAM_NAME = /^[a-z][a-z0-9_]*$/;

const toTemplate = (t: AreaWhatsapp['template']): TemplateDraft | null =>
  t ? { name: t.name, language: t.language, params: [...(t.params ?? [])] } : null;

export function toWhatsappDraft(w: HandoffArea['whatsapp'] | undefined): WhatsappDraft {
  return {
    accountId: w?.account_id ?? '',
    template: toTemplate(w?.template),
    callTemplate: toTemplate(w?.call_template),
    acceptTemplate: toTemplate(w?.accept_template),
    waitSeconds: w?.wait_seconds ?? WAIT_SECONDS.default,
    callOn: !!w?.call_template,
    acceptOn: !!w?.accept_template,
    rotationOn: !!w?.template,
  };
}

const fromTemplate = (t: TemplateDraft) => ({
  name: t.name,
  language: t.language,
  params: t.params.map((p) => p.trim()),
});

/** El bloque a mandar (las plantillas ya son null si su momento esta apagado), o null si el area no usa WhatsApp. En un area de aviso no hay plantilla de llamada ni de aceptar. */
export function fromWhatsappDraft(d: WhatsappDraft, delivery: string): AreaWhatsapp | null {
  const call = delivery === 'call' ? d.callTemplate : null;
  const accept = delivery === 'call' ? d.acceptTemplate : null;
  if (!d.accountId && !d.template && !call && !accept) return null;
  return {
    account_id: d.accountId,
    ...(d.template ? { template: fromTemplate(d.template) } : {}),
    ...(call ? { call_template: fromTemplate(call) } : {}),
    ...(accept ? { accept_template: fromTemplate(accept) } : {}),
    wait_seconds: typeof d.waitSeconds === 'number' ? d.waitSeconds : WAIT_SECONDS.default,
  };
}

function templateError(t: TemplateDraft, label: string, allowClient: boolean): string | null {
  for (const [i, p] of t.params.entries()) {
    const name = p.trim();
    if (!name) return `${label}: elegí qué valor va en {{${i + 1}}}.`;
    if (!PARAM_NAME.test(name))
      return `${label}: «${name}» no es un nombre válido (minúsculas, números y _).`;
    if (name === 'cliente' && !allowClient)
      return `${label}: el teléfono de la persona (cliente) no sale antes de que alguien acepte.`;
  }
  return null;
}

/** Error del bloque, o null. Espeja lo que valida el servidor, para avisar antes de guardar. */
export function whatsappError(d: WhatsappDraft, delivery: string): string | null {
  const notice = delivery === 'whatsapp';
  const call = notice ? null : d.callTemplate;
  const accept = notice ? null : d.acceptTemplate;
  if (!d.accountId && !d.template && !call && !accept) {
    return notice ? 'Elegí el número de WhatsApp y la plantilla del aviso.' : null;
  }
  if (!notice && !d.accountId && (d.callOn || d.acceptOn || d.rotationOn))
    return 'Elegí el número de WhatsApp.';
  if (!d.accountId) return 'Elegí el número de WhatsApp.';
  if (notice && !d.template) return 'Elegí la plantilla del aviso.';
  if (!notice) {
    // Un switch prendido sin plantilla, o ningun momento prendido con una cuenta elegida.
    if (d.callOn && !d.callTemplate) return 'Al sonar: elegí la plantilla o apagalo.';
    if (d.acceptOn && !d.acceptTemplate) return 'Al aceptar: elegí la plantilla o apagalo.';
    if (d.rotationOn && !d.template) return 'Rotación por WhatsApp de texto: elegí la plantilla o apagalo.';
    if (!d.template && !call && !accept) return 'Prendé al menos un momento o quitá el número.';
  }
  const label = notice ? 'Plantilla del aviso' : 'Plantilla de rotación';
  const err =
    (d.template && templateError(d.template, label, notice)) ||
    (call && templateError(call, 'Plantilla de la llamada', false)) ||
    // Al aceptar ya se entregó el teléfono de la persona: cliente puede ir.
    (accept && templateError(accept, 'Plantilla al aceptar', true)) ||
    null;
  if (err) return err;
  const wait = d.waitSeconds;
  if (
    !notice &&
    d.template &&
    !(typeof wait === 'number' && wait >= WAIT_SECONDS.min && wait <= WAIT_SECONDS.max)
  )
    return `La espera por persona va entre ${WAIT_SECONDS.min} y ${WAIT_SECONDS.max} segundos.`;
  return null;
}
