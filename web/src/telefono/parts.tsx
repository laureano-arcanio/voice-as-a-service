import {
  IconPhoneIncoming,
  IconPhoneOutgoing,
  IconPhoneX,
  IconUser,
} from '@tabler/icons-react';
import type { CallSummary } from '@/api/types';
import { callDirection } from './calls';

/** Iniciales del nombre, o el ícono de persona para un número sin nombre. */
export function Avatar({
  name,
  size = 'md',
  ringing,
}: {
  name?: string | null;
  size?: 'md' | 'lg' | 'xl';
  ringing?: boolean;
}) {
  const initials = (name ?? '')
    .split(/\s+/)
    .filter((w) => /^\p{L}/u.test(w))
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join('');
  return (
    <span className="tel-avatar" data-size={size} data-ringing={ringing || undefined} aria-hidden="true">
      {initials || <IconUser size={size === 'xl' ? 48 : size === 'lg' ? 32 : 20} />}
    </span>
  );
}

export function DirectionIcon({ c }: { c: CallSummary }) {
  const { kind, missed } = callDirection(c);
  if (missed) return <IconPhoneX size={16} className="tel-dir" data-missed aria-label="No se completó" />;
  return kind === 'out' ? (
    <IconPhoneOutgoing size={16} className="tel-dir" aria-label="Saliente" />
  ) : (
    <IconPhoneIncoming size={16} className="tel-dir" aria-label="Entrante" />
  );
}
