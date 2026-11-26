import type { Check, Preview, TestCaseCreate, ToolResult } from './api';

/** El body de crear/probar: la copia que vio el modal, con sus chequeos. */
export function buildCaseBody(
  preview: Preview,
  values: { conversationId: string; messageIndex: number; name: string; checks: Check[]; knownFailure?: boolean },
): TestCaseCreate {
  const toolResults: ToolResult[] = preview.reply.tool_calls.map((call, i) => ({
    name: call.name,
    arguments: call.arguments ?? {},
    result: preview.reply.tool_results[i] ?? '',
  }));
  return {
    conversation_id: values.conversationId,
    message_index: values.messageIndex,
    name: values.name.trim(),
    checks: values.checks,
    known_failure: values.knownFailure ?? false,
    messages: preview.snapshot.messages,
    user_message: preview.snapshot.user_message,
    tool_results: toolResults,
  };
}

/** Suma "no dice esto" al texto seleccionado en la respuesta del agente (sin duplicarlo). */
export function addNoDice(checks: Check[], text: string): Check[] {
  const clean = text.replace(/\s+/g, ' ').trim();
  if (!clean) return checks;
  if (checks.some((c) => c.type === 'no_dice' && c.text === clean)) return checks;
  return [...checks, { type: 'no_dice', text: clean }];
}
