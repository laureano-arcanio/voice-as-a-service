import type { components } from '@/api/schema';

type S = components['schemas'];

// Llamadas directas (docs/LLAMADAS_DIRECTAS_PLAN.md, sección 13).
export type DirectCallIn = S['DirectCallIn'];
export type DirectCallOut = S['DirectCallOut'];
export type DirectJoin = S['DirectJoinOut'];
export type Presence = S['PresenceOut'];
export type Ringing = S['RingingOut'];
export type TeamPresence = S['TeamPresenceOut'];
export type DirectCallSettings = S['DirectCallSettings'];

/** Estado de la llamada que publica el worker en el tema `call_status` (solo la saliente). */
export interface CallStatusData {
  state: 'joining' | 'dialing' | 'ringing' | 'active' | 'ended';
  result?: 'completed' | 'no_answer' | 'busy' | 'failed';
}

/** Una frase transcripta, tema `transcript`: el contacto es `user`; el usuario o la persona, `assistant`. */
export interface TranscriptData {
  role: 'user' | 'assistant';
  person?: string | null;
  text: string;
}
