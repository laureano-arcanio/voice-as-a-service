import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { components } from '@/api/schema';

export type TestCaseDetail = components['schemas']['TestCaseDetailOut'];
export type TestCaseSummary = components['schemas']['TestCaseSummaryOut'];
export type TestRun = components['schemas']['TestRunOut'];
export type TestRunCreate = components['schemas']['TestRunCreateIn'];
export type TestCaseCreate = components['schemas']['TestCaseCreateIn'];
export type TestCaseUpdate = components['schemas']['TestCaseUpdateIn'];

/** Un chequeo determinista (app/agent_tests/checks.py). */
export type Check = {
  type: string;
  tool?: string;
  area?: string;
  text?: string;
  argumentos_contienen?: string;
};

export type ToolResult = { name: string; arguments?: unknown; result: string };

/** Lo que recibio el modelo en el turno y lo que contesto el agente. */
export type Preview = {
  snapshot: {
    messages: { role: 'assistant' | 'user'; text: string; [key: string]: unknown }[];
    user_message: string;
    [key: string]: unknown;
  };
  reply: { text: string; tool_calls: { name: string; arguments?: unknown }[]; handoff?: string | null; tool_results: string[] };
  checks: Check[];
};

export type Repetition = {
  text: string;
  tool_calls: { name: string; arguments?: unknown }[];
  handoff?: string | null;
  status?: string | null;
  failures: { check: Check; message: string; span?: string }[];
  error?: string | null;
  ms: number;
  input_tokens: number;
  output_tokens: number;
  llm: Record<string, unknown>;
  tools: { name: string; arguments?: unknown; result: string; recorded: boolean }[];
  passed: boolean;
};

export type VariantResult = {
  key: string;
  version: number;
  passed: number;
  total: number;
  errors: number;
  repetitions: Repetition[];
};

export type CaseResult = {
  case_id: string;
  name: string;
  known_failure: boolean;
  variants: VariantResult[];
};

export const CHECK_TYPES = [
  ['usa_herramienta', 'Usó una herramienta'],
  ['no_usa_herramienta', 'No usó una herramienta'],
  ['deriva_a', 'Derivó a un área'],
  ['no_deriva', 'No derivó'],
  ['dice', 'Dijo'],
  ['no_dice', 'No dijo'],
  ['empieza_con', 'Empieza con'],
  ['datos_de_la_herramienta', 'Los datos salieron de la herramienta'],
] as const;

export const checkLabel = (type: string) =>
  CHECK_TYPES.find(([value]) => value === type)?.[1] ?? type;

export const variantLabel = (key: string) =>
  key === 'publicada' ? 'Publicada' : key === 'borrador' ? 'Cambios sin guardar' : key;

export const testKeys = {
  cases: (agentId: string) => ['agent-tests', 'cases', agentId] as const,
  case: (agentId: string, caseId: string) => ['agent-tests', 'case', agentId, caseId] as const,
  runs: (agentId: string) => ['agent-tests', 'runs', agentId] as const,
  run: (agentId: string, runId: string) => ['agent-tests', 'run', agentId, runId] as const,
};

export function useTestCases(agentId: string, enabled = true) {
  return useQuery({
    queryKey: testKeys.cases(agentId),
    queryFn: () =>
      unwrap(api.GET('/api/v1/agents/{agent_id}/test-cases', { params: { path: { agent_id: agentId } } })),
    enabled: !!agentId && enabled,
  });
}

export function useTestCase(agentId: string, caseId: string | null) {
  return useQuery({
    queryKey: testKeys.case(agentId, caseId ?? ''),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/agents/{agent_id}/test-cases/{case_id}', {
          params: { path: { agent_id: agentId, case_id: caseId! } },
        }),
      ),
    enabled: !!agentId && !!caseId,
  });
}

export function usePreviewCase(agentId: string) {
  return useMutation({
    mutationFn: (body: { conversation_id: string; message_index: number }) =>
      unwrap(
        api.POST('/api/v1/agents/{agent_id}/test-cases/preview', {
          params: { path: { agent_id: agentId } },
          body,
        }),
      ) as Promise<Preview>,
  });
}

function useInvalidateCases(agentId: string) {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: testKeys.cases(agentId) });
    void qc.invalidateQueries({ queryKey: ['agent-tests', 'case', agentId] });
  };
}

export function useCreateCase(agentId: string) {
  const invalidate = useInvalidateCases(agentId);
  return useMutation({
    mutationFn: (body: TestCaseCreate) =>
      unwrap(
        api.POST('/api/v1/agents/{agent_id}/test-cases', {
          params: { path: { agent_id: agentId } },
          body,
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useUpdateCase(agentId: string, caseId: string) {
  const invalidate = useInvalidateCases(agentId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TestCaseUpdate) =>
      unwrap(
        api.PATCH('/api/v1/agents/{agent_id}/test-cases/{case_id}', {
          params: { path: { agent_id: agentId, case_id: caseId } },
          body,
        }),
      ),
    onSuccess: (data) => {
      qc.setQueryData(testKeys.case(agentId, caseId), data);
      invalidate();
    },
  });
}

export function useDeleteCase(agentId: string) {
  const invalidate = useInvalidateCases(agentId);
  return useMutation({
    mutationFn: (caseId: string) =>
      unwrap(
        api.DELETE('/api/v1/agents/{agent_id}/test-cases/{case_id}', {
          params: { path: { agent_id: agentId, case_id: caseId } },
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useCreateRun(agentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TestRunCreate) =>
      unwrap(
        api.POST('/api/v1/agents/{agent_id}/test-runs', {
          params: { path: { agent_id: agentId } },
          body,
        }),
      ),
    onSuccess: (run) => {
      qc.setQueryData(testKeys.run(agentId, run.id), run);
      void qc.invalidateQueries({ queryKey: testKeys.runs(agentId) });
    },
  });
}

export function useTestRun(agentId: string, runId: string | null) {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: testKeys.run(agentId, runId ?? ''),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/agents/{agent_id}/test-runs/{run_id}', {
          params: { path: { agent_id: agentId, run_id: runId! } },
        }),
      ),
    enabled: !!agentId && !!runId,
    // Mientras corre se consulta cada 2 s; al terminar, se queda quieta.
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'queued' || status === 'running' ? 2000 : false;
    },
  });
  const status = query.data?.status;
  // Al terminar, la lista de casos y el detalle muestran el pasa X/N nuevo sin recargar.
  useEffect(() => {
    if (status !== 'done' && status !== 'failed') return;
    void qc.invalidateQueries({ queryKey: testKeys.cases(agentId) });
    void qc.invalidateQueries({ queryKey: ['agent-tests', 'case', agentId] });
    void qc.invalidateQueries({ queryKey: testKeys.runs(agentId) });
  }, [status, agentId, qc]);
  return query;
}

export function useTestRuns(agentId: string, enabled = true) {
  return useQuery({
    queryKey: testKeys.runs(agentId),
    queryFn: () =>
      unwrap(api.GET('/api/v1/agents/{agent_id}/test-runs', { params: { path: { agent_id: agentId } } })),
    enabled: !!agentId && enabled,
  });
}

export const caseResults = (run: TestRun | undefined): CaseResult[] =>
  (run?.results ?? []) as unknown as CaseResult[];

/** Los mensajes del snapshot con el turno del usuario, como los muestra ChatView. */
export const snapshotMessages = (preview: Preview | TestCaseDetail | undefined) => {
  if (!preview) return [];
  const snapshot = preview.snapshot as Preview['snapshot'] | null | undefined;
  if (!snapshot) return [];
  return [...(snapshot.messages ?? []), { role: 'user' as const, text: snapshot.user_message }];
};

/** "pasa 4/5" de una variante guardada en el resumen de una corrida (los dicts vienen del backend). */
export const variantPass = (variant: Record<string, unknown>) =>
  `pasa ${Number(variant.passed ?? 0)}/${Number(variant.total ?? 0)}`;

export const summaryText = (summary?: { variants?: Record<string, unknown>[] } | null) =>
  (summary?.variants ?? []).map((v) => `${variantLabel(String(v.key ?? ''))}: ${variantPass(v)}`).join(' · ');

/** Los chequeos como texto para el detalle. */
export const describeCheck = (check: Check): string => {
  const base = checkLabel(check.type);
  if (check.type === 'usa_herramienta')
    return `${base}: ${check.tool ?? ''}${check.argumentos_contienen ? ` (args: ${check.argumentos_contienen})` : ''}`;
  if (check.type === 'no_usa_herramienta') return `${base}${check.tool ? `: ${check.tool}` : ''}`;
  if (check.type === 'deriva_a') return `${base}: ${check.area ?? ''}`;
  if (check.text) return `${base} «${check.text}»`;
  return base;
};

/** Los casos cuyo borrador rinde menos que la publicada. */
export const worsening = (results: CaseResult[]) =>
  results.filter((item) => {
    const published = item.variants.find((v) => v.key === 'publicada');
    const draft = item.variants.find((v) => v.key === 'borrador');
    return !!draft && !!published && draft.passed < published.passed;
  });
