import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { Billing, FiscalIn, PaymentIn } from '@/api/types';

export const billingKeys = {
  client: (id: string) => ['billing', id] as const,
  subscriptions: ['billing', 'subscriptions'] as const,
  payments: (invoiced: boolean | null) => ['billing', 'payments', invoiced] as const,
};

/** Plan, suscripcion, planes que se pueden contratar, datos fiscales y pagos de un cliente. */
export function useBilling(clientId: string | null | undefined) {
  return useQuery({
    queryKey: billingKeys.client(clientId ?? ''),
    queryFn: () =>
      unwrap(api.GET('/api/v1/clients/{client_id}/billing', { params: { path: { client_id: clientId! } } })),
    enabled: !!clientId,
  });
}

/** Toda mutacion devuelve el BillingOut nuevo: se guarda y se refrescan el cliente y las listas de admin. */
function useBillingMutation<V>(clientId: string, fn: (vars: V) => Promise<Billing>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (billing) => {
      qc.setQueryData(billingKeys.client(clientId), billing);
      void qc.invalidateQueries({ queryKey: ['clients'] });
      void qc.invalidateQueries({ queryKey: ['billing', 'subscriptions'] });
      void qc.invalidateQueries({ queryKey: ['billing', 'payments'] });
    },
  });
}

export function useSubscribe(clientId: string) {
  return useBillingMutation(clientId, (tierId: string) =>
    unwrap(
      api.POST('/api/v1/clients/{client_id}/billing/subscribe', {
        params: { path: { client_id: clientId } },
        body: { tier_id: tierId, method: 'transfer' },
      }),
    ),
  );
}

export function useCancelPlan(clientId: string) {
  return useBillingMutation(clientId, () =>
    unwrap(
      api.POST('/api/v1/clients/{client_id}/billing/cancel', { params: { path: { client_id: clientId } } }),
    ),
  );
}

export function useUpdateFiscal(clientId: string) {
  return useBillingMutation(clientId, (body: FiscalIn) =>
    unwrap(
      api.PUT('/api/v1/clients/{client_id}/billing/fiscal', {
        params: { path: { client_id: clientId } },
        body,
      }),
    ),
  );
}

// ---- admin ----

export function useRecordPayment(clientId: string) {
  return useBillingMutation(clientId, (body: PaymentIn) =>
    unwrap(
      api.POST('/api/v1/clients/{client_id}/billing/payments', {
        params: { path: { client_id: clientId } },
        body,
      }),
    ),
  );
}

export function useSuspendPlan(clientId: string) {
  return useBillingMutation(clientId, () =>
    unwrap(
      api.POST('/api/v1/clients/{client_id}/billing/suspend', { params: { path: { client_id: clientId } } }),
    ),
  );
}

export function useSubscriptions() {
  return useQuery({
    queryKey: billingKeys.subscriptions,
    queryFn: () => unwrap(api.GET('/api/v1/billing/subscriptions')),
  });
}

export function usePayments(invoiced: boolean | null) {
  return useQuery({
    queryKey: billingKeys.payments(invoiced),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/billing/payments', { params: { query: invoiced == null ? {} : { invoiced } } }),
      ),
  });
}

export function useMarkInvoiced() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, invoiced }: { id: string; invoiced: boolean }) =>
      unwrap(
        api.PATCH('/api/v1/billing/payments/{payment_id}', {
          params: { path: { payment_id: id } },
          body: { invoiced },
        }),
      ),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['billing'] }),
  });
}
