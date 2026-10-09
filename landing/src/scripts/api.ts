import { UserFacingError } from "./errors";
import { turnstileToken } from "./turnstile";

const BASE = `${import.meta.env.PUBLIC_API_URL.replace(/\/$/, "")}/api/v1/demo`;
const RENEW_MARGIN_MS = 60_000;

export class ApiError extends UserFacingError {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
  ) {
    super(message);
  }
}

export interface DemoCall {
  conversation_id: string;
  room: string;
  livekit_url: string;
  token: string;
  max_duration_seconds: number;
  result_token: string;
}

export interface DemoField {
  name: string;
  label: string;
  type: string;
  value: unknown;
}

export interface DemoResult {
  final: boolean;
  status: string;
  ended_reason: string;
  duration_seconds: number;
  agent_name: string;
  completed: boolean;
  outcome: { label: string; goal: boolean } | null;
  fields: DemoField[];
  messages: { role: "assistant" | "user"; text: string }[];
}

let session: { token: string; expiresAt: number } | null = null;
let creating: Promise<string> | null = null;

async function send(path: string, init: RequestInit, token?: string): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError("No pudimos conectar con el servidor. Probá de nuevo en un rato.", 0, "network");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    // El 422 de validación trae una lista en detail: un mensaje genérico en lugar de "[object Object]".
    const message = typeof body.detail === "string" ? body.detail : response.status === 422 ? "Revisá los datos y probá de nuevo." : null;
    throw new ApiError(message ?? "Algo salió mal. Probá de nuevo.", response.status, body.code ?? "error");
  }
  return response;
}

async function sessionToken(): Promise<string> {
  if (session && session.expiresAt - RENEW_MARGIN_MS > Date.now()) return session.token;
  creating ??= (async () => {
    try {
      const captcha = await turnstileToken();
      const response = await send("/sessions", { method: "POST", body: JSON.stringify({ turnstile_token: captcha }) });
      const body: { token: string; expires_in: number } = await response.json();
      session = { token: body.token, expiresAt: Date.now() + body.expires_in * 1000 };
      return body.token;
    } finally {
      creating = null;
    }
  })();
  return creating;
}

async function withSession(path: string, init: RequestInit): Promise<Response> {
  try {
    return await send(path, init, await sessionToken());
  } catch (error) {
    if (!(error instanceof ApiError) || error.code !== "session_required") throw error;
    session = null;
    return send(path, init, await sessionToken());
  }
}

export interface ContactRequest {
  name: string;
  company: string;
  email: string | null;
  phone: string;
  message: string;
  page: string;
  website: string;
}

export async function sendContact(request: ContactRequest): Promise<void> {
  await withSession("/contact", { method: "POST", body: JSON.stringify(request) });
}

export async function startCall(agent: string, voice?: string): Promise<DemoCall> {
  const response = await withSession("/calls", { method: "POST", body: JSON.stringify({ agent, voice }) });
  return response.json();
}

export async function callResult(call: DemoCall): Promise<DemoResult> {
  const response = await send(`/calls/${call.conversation_id}`, { method: "GET" }, call.result_token);
  return response.json();
}

/** Sintetiza texto con una voz: PCM crudo (16 bits, mono, 24 kHz) que llega mientras el TTS lo genera. */
export async function synthesizeStream(voice: string, text: string, signal?: AbortSignal): Promise<ReadableStream<Uint8Array>> {
  const response = await withSession("/tts", { method: "POST", body: JSON.stringify({ voice, text, format: "pcm" }), signal });
  if (!response.body) throw new ApiError("No pudimos generar el audio. Probá de nuevo.", 0, "no_stream");
  return response.body;
}
