import { toApiError } from './errors';

interface FetchResult<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

/** Desenvuelve la respuesta de openapi-fetch: los datos, o ApiError si no fue 2xx. */
export async function unwrap<T>(promise: Promise<FetchResult<T>>): Promise<T> {
  const { data, error, response } = await promise;
  if (!response.ok) throw toApiError(error, response.status);
  return data as T;
}
