import type { UseFormReturnType } from '@mantine/form';
import { RETRY_RESULTS } from './labels';
import { DEFAULT_TZ, isoToLocal, localToIso } from './schedule';

/** Acceso a los campos de un `useForm` sin atarse a su forma: los grupos de campos se comparten entre
 * el alta de WhatsApp, el de llamadas y la edicion. */
export interface FieldApi {
  props: (path: string) => Record<string, unknown>;
  set: (path: string, value: unknown) => void;
}

export function fieldApi<T>(form: UseFormReturnType<T>): FieldApi {
  return {
    props: (path) => form.getInputProps(path as never) as unknown as Record<string, unknown>,
    set: (path, value) => form.setFieldValue(path as never, value as never),
  };
}

export interface ScheduleValues {
  window_start: number;
  window_end: number;
  rate_per_minute: number;
  /** Dias permitidos como texto ("0" = lunes); vacio = todos. */
  weekdays: string[];
  /** datetime-local en la hora de la campaña; vacio = sin fecha. */
  starts_at: string;
  ends_at: string;
}

export function scheduleDefaults(): ScheduleValues {
  return {
    window_start: 9,
    window_end: 20,
    rate_per_minute: 20,
    weekdays: ['0', '1', '2', '3', '4'],
    starts_at: '',
    ends_at: '',
  };
}

export function scheduleFromCampaign(c: {
  window_start: number;
  window_end: number;
  rate_per_minute: number;
  weekdays?: number[] | null;
  starts_at?: string | null;
  ends_at?: string | null;
  timezone: string;
}): ScheduleValues {
  return {
    window_start: c.window_start,
    window_end: c.window_end,
    rate_per_minute: c.rate_per_minute,
    weekdays: (c.weekdays ?? []).map(String),
    starts_at: isoToLocal(c.starts_at, c.timezone),
    ends_at: isoToLocal(c.ends_at, c.timezone),
  };
}

/** Los campos de horario como los espera la API (`CampaignIn` y `CampaignPatch`). */
export function scheduleBody(v: ScheduleValues, tz = DEFAULT_TZ) {
  const days = v.weekdays.map(Number).sort((a, b) => a - b);
  return {
    window_start: v.window_start,
    window_end: v.window_end,
    rate_per_minute: v.rate_per_minute,
    weekdays: days.length === 0 || days.length === 7 ? null : days,
    starts_at: localToIso(v.starts_at, tz),
    ends_at: localToIso(v.ends_at, tz),
  };
}

export function scheduleErrors(v: ScheduleValues): Record<string, string> {
  const errors: Record<string, string> = {};
  if (v.window_end <= v.window_start) errors.window_end = 'Tiene que ser después del inicio';
  if (v.starts_at && v.ends_at && v.ends_at <= v.starts_at)
    errors.ends_at = 'Tiene que ser posterior al inicio';
  return errors;
}

export interface VoiceRunValues {
  mode: 'sequential' | 'parallel';
  concurrency: number;
  max_attempts: number;
  retry_minutes: number;
  retry_on: string[];
}

export function voiceRunDefaults(): VoiceRunValues {
  return {
    mode: 'sequential',
    concurrency: 1,
    max_attempts: 3,
    retry_minutes: 60,
    retry_on: [...RETRY_RESULTS],
  };
}
