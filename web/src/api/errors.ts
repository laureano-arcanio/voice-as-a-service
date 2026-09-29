/** Error de la API con el cuerpo ya interpretado: {detail, code?, errors?}. */
export interface FieldError {
  path: string;
  message: string;
}

interface PydanticError {
  loc?: (string | number)[];
  msg?: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string | undefined;
  readonly errors: FieldError[];

  constructor(status: number, message: string, code?: string, errors: FieldError[] = []) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.errors = errors;
  }
}

const STATUS_MESSAGES: Record<number, string> = {
  401: 'Tu sesión venció. Ingresá de nuevo.',
  403: 'No tenés permiso para hacer esto.',
  404: 'No existe o no tenés acceso.',
  429: 'Demasiados pedidos. Probá de nuevo en un rato.',
  500: 'Error del servidor.',
  502: 'Un servicio externo no responde.',
  503: 'Servicio no disponible.',
};

/** El `detail` legible: string tal cual; en un 422 de pydantic, una linea por error. */
export function detailMessage(body: unknown, status: number): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string' && detail) return detail;
    if (Array.isArray(detail)) {
      const lines = (detail as PydanticError[]).map((d) => {
        const loc = (d.loc ?? []).filter((p) => p !== 'body' && p !== 'query' && p !== 'path').join('.');
        return loc ? `${loc}: ${d.msg ?? 'inválido'}` : (d.msg ?? 'inválido');
      });
      if (lines.length) return lines.join('\n');
    }
  }
  if (typeof body === 'string' && body.trim() && body.length < 300) return body.trim();
  return STATUS_MESSAGES[status] ?? `Error ${status}`;
}

export function toApiError(body: unknown, status: number): ApiError {
  const obj = body && typeof body === 'object' ? (body as Record<string, unknown>) : {};
  const code = typeof obj.code === 'string' ? obj.code : undefined;
  const errors = Array.isArray(obj.errors)
    ? (obj.errors as unknown[]).filter(
        (e): e is FieldError =>
          !!e && typeof e === 'object' && 'message' in e && typeof (e as FieldError).message === 'string',
      )
    : [];
  return new ApiError(status, detailMessage(body, status), code, errors);
}

/** Mensaje para mostrar de cualquier error (de la API, de red o de JS). */
export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof TypeError) return 'No se pudo conectar con el servidor.';
  if (err instanceof Error) return err.message;
  return 'Error inesperado.';
}
