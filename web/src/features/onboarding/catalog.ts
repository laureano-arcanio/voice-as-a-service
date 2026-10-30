import {
  IconBarbell,
  IconBuildingStore,
  IconHeartbeat,
  IconHome,
  IconReceipt2,
  IconToolsKitchen2,
} from '@tabler/icons-react';
import type { ComponentType } from 'react';
import type { Onboarding } from '@/api/types';

/** Las seis voces del asistente, con su retrato (web/public/voces/<id>.svg). */
export const FEATURED_VOICES = [
  { id: 'sofia', gender: 'mujer', tagline: 'Cálida y cercana' },
  { id: 'paula', gender: 'mujer', tagline: 'Clara y segura' },
  { id: 'valentina', gender: 'mujer', tagline: 'Joven y enérgica' },
  { id: 'gonzalo', gender: 'hombre', tagline: 'Serio y confiable' },
  { id: 'lucas', gender: 'hombre', tagline: 'Amable y dinámico' },
  { id: 'tomas', gender: 'hombre', tagline: 'Relajado y natural' },
] as const;

export const portrait = (voice: string | null | undefined) =>
  FEATURED_VOICES.some((v) => v.id === voice) ? `/voces/${voice}.svg` : null;

/** Lo que muestra cada rubro (el id y el nombre salen de GET /onboarding/industries). */
export const INDUSTRY_UI: Record<string, { icon: ComponentType<{ size?: number; stroke?: number }>; detail: string }> = {
  salud: { icon: IconHeartbeat, detail: 'Da turnos, toma los datos del paciente y responde dudas.' },
  gimnasio: { icon: IconBarbell, detail: 'Cuenta actividades y cuotas, y anota clases de prueba.' },
  inmobiliaria: { icon: IconHome, detail: 'Califica al interesado y coordina visitas.' },
  gastronomia: { icon: IconToolsKitchen2, detail: 'Toma reservas y responde sobre la carta y horarios.' },
  cobranzas: { icon: IconReceipt2, detail: 'Recuerda pagos vencidos y acuerda fecha o cuotas.' },
  otro: { icon: IconBuildingStore, detail: 'Atiende consultas con tu información y toma los datos.' },
};

/** La apertura de muestra para escuchar cada voz, con el nombre de la empresa. */
export const sampleOpening = (voiceName: string, company: string) =>
  `Hola, gracias por comunicarte con ${company}. Te habla ${voiceName}. ¿En qué te puedo ayudar?`;

/** Cuántas llamadas de prueba al celular le quedan al cliente. */
export function trialLeft(status: Onboarding): number {
  const t = status.trial;
  return t.seconds_used >= t.seconds_max - 30 ? 0 : Math.max(t.calls_max - t.calls_used, 0);
}
