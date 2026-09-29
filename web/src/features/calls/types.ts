import type { CallDetail, CallIn } from '@/api/types';

export type { CallDetail, CallIn };

export interface LatencyStat {
  avg?: number | null;
  max?: number | null;
}

export interface LatencyTurn {
  e2e?: number | null;
  total?: number | null;
  eou?: number | null;
  stt?: number | null;
  endpointing?: number | null;
  llm?: number | null;
  llm_total?: number | null;
  tts?: number | null;
  tts_audio?: number | null;
}

/** CallInfo.latency (libre en el schema). */
export interface Latency {
  n_turns?: number;
  stats?: Record<string, LatencyStat | undefined>;
  turns?: LatencyTurn[];
}

export function asLatency(raw: unknown): Latency | null {
  return raw && typeof raw === 'object' && !Array.isArray(raw) ? (raw as Latency) : null;
}
