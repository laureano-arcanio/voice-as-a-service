import { createContext, useContext } from 'react';
import type { Ringing } from './types';

/**
 * Fases de la llamada del panel: micrófono → pedido a la API y la room → Llamando (el worker marca) →
 * Sonando → En curso → Terminada. `error` es una que no llegó a empezar (micrófono, plan, número).
 */
export type CallPhase = 'idle' | 'mic' | 'connecting' | 'dialing' | 'ringing' | 'active' | 'ended' | 'error';

/** Cómo terminó: los resultados del worker y `hangup` (la cortó el usuario antes de que atiendan). */
export type CallResult = 'completed' | 'no_answer' | 'busy' | 'failed' | 'hangup';

export const LIVE_PHASES: CallPhase[] = ['mic', 'connecting', 'dialing', 'ringing', 'active'];

/** A quién se llama (o quién llama, en una entrante) y desde qué línea, para la barra. */
export interface CallTarget {
  contactId?: string | null;
  phone?: string | null;
  name?: string | null;
  /** El número de salida (o la línea de la entrante), como se muestra. */
  fromLabel?: string | null;
}

export interface CallProblem {
  title: string;
  message: string;
  code?: string;
}

export interface TranscriptLine {
  id: number;
  who: string;
  /** Lo dijo el usuario del panel (o la persona del equipo). */
  mine: boolean;
  text: string;
}

export interface JoinOutcome {
  ok: boolean;
  code?: string;
  problem?: CallProblem;
}

export interface DirectCallValue {
  phase: CallPhase;
  direction: 'outbound' | 'inbound' | null;
  conversationId: string | null;
  target: CallTarget | null;
  /** El plan incluye llamadas directas (sin eso no se muestra la barra). */
  enabled: boolean;
  /** Desde cuándo está En curso (ms), para el cronómetro. */
  startedAt: number | null;
  endedAt: number | null;
  result: CallResult | null;
  error: CallProblem | null;
  muted: boolean;
  /** El navegador no dejó reproducir el audio sin un clic. */
  audioBlocked: boolean;
  transcript: TranscriptLine[];
  /** Hay una llamada (o se está armando): no se puede empezar otra. */
  busy: boolean;
  /** Recargó con una llamada en curso: la que puede retomar con "Volver a entrar". */
  rejoinId: string | null;
  /** Por qué no puede llamar ni atender (admin en soporte); null si puede. */
  disabledReason: string | null;
  call: (target: CallTarget, fromNumberId?: string | null, confirmOptedOut?: boolean) => Promise<boolean>;
  join: (conversationId: string) => Promise<JoinOutcome>;
  answer: (ring: Ringing) => Promise<boolean>;
  hangup: () => void;
  toggleMute: () => void;
  dtmf: (digit: string) => void;
  startAudio: () => void;
  /** Cierra la barra de una llamada terminada o con error. */
  dismiss: () => void;
  dismissRejoin: () => void;
}

export interface PresenceValue {
  available: boolean;
  setAvailable: (on: boolean) => void;
  /** Entrantes que le suenan (sin las rechazadas). */
  rings: Ringing[];
  decline: (ring: Ringing) => void;
  disabledReason: string | null;
}

export const DirectCallContext = createContext<DirectCallValue | null>(null);
export const PresenceContext = createContext<PresenceValue | null>(null);

/** La llamada del panel (CallProvider, en el layout del cliente). */
export function useDirectCall(): DirectCallValue {
  const v = useContext(DirectCallContext);
  if (!v) throw new Error('useDirectCall fuera del CallProvider');
  return v;
}

/** Igual que useDirectCall, pero null fuera del panel del cliente (la administración no tiene teléfono). */
export function useOptionalDirectCall(): DirectCallValue | null {
  return useContext(DirectCallContext);
}

/** Disponible para atender en el panel y el timbre de las entrantes. */
export function usePresence(): PresenceValue {
  const v = useContext(PresenceContext);
  if (!v) throw new Error('usePresence fuera del CallProvider');
  return v;
}

export function useOptionalPresence(): PresenceValue | null {
  return useContext(PresenceContext);
}

/**
 * Alto de la barra de llamada (el footer del AppShell), o null si no se muestra: sin el plan, fuera del
 * panel del cliente o mientras carga. Compacta sin llamada (solo Disponible); más alta en el celular.
 */
export function useCallBarHeight(): number | { base: number; sm: number } | null {
  const call = useOptionalDirectCall();
  const presence = useOptionalPresence();
  if (!call || !presence) return null;
  const idle = call.phase === 'idle' && !call.rejoinId && presence.rings.length === 0;
  if (!call.enabled && idle) return null;
  return idle ? 48 : { base: 120, sm: 64 };
}

/** Dígitos del teclado: 0-9 y #. Sin `*`: en Anura corta la otra llamada de la cuenta (AGENTS.md). */
export const DTMF_KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '#'] as const;

/** Código RFC 4733 del dígito (0-9 = 0-9, # = 11). */
export function dtmfCode(digit: string): number | null {
  if (digit === '#') return 11;
  return /^\d$/.test(digit) ? Number(digit) : null;
}
