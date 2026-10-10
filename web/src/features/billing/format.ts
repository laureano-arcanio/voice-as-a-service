import type { Billing, Plan } from '@/api/types';
import { formatDate, formatNumber } from '@/lib/format';

/** Fecha de la API (YYYY-MM-DD) sin pasar por UTC: 9/11/2026. */
export function formatDay(day: string | null | undefined): string {
  return formatDate(day ? `${day}T12:00:00` : null);
}

/** "300 minutos entrantes por mes", o "Minutos entrantes sin límite". */
function amount(
  v: number | null | undefined,
  one: string,
  many: string,
  unlimited: string,
  suffix = '',
): string {
  if (v == null) return unlimited;
  return `${formatNumber(v, 0)} ${v === 1 ? one : many}${suffix}`;
}

/** Lo que incluye un plan, en una lista corta para el cliente. */
export function planFeatures(p: Plan): string[] {
  const out: string[] = [];
  // Lo que vale 0 el plan no lo incluye: no se lista.
  if (p.inbound_minutes !== 0)
    out.push(
      amount(
        p.inbound_minutes,
        'minuto entrante',
        'minutos entrantes',
        'Minutos entrantes sin límite',
        ' por mes',
      ),
    );
  if (p.outbound_minutes !== 0)
    out.push(
      amount(
        p.outbound_minutes,
        'minuto saliente',
        'minutos salientes',
        'Minutos salientes sin límite',
        ' por mes',
      ),
    );
  out.push(
    amount(p.max_concurrent_calls, 'llamada', 'llamadas', 'Llamadas simultáneas sin límite', ' a la vez'),
  );
  if (p.max_phone_numbers !== 0)
    out.push(amount(p.max_phone_numbers, 'número de teléfono', 'números de teléfono', 'Números sin límite'));
  if (p.api_rate_limit !== 0) out.push('Acceso a la API');
  return out;
}

export function hasFiscal(billing: Billing): boolean {
  return !!(billing.fiscal.legal_name && billing.fiscal.tax_id && billing.fiscal.tax_condition);
}
