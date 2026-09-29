import { describe, expect, it } from 'vitest';
import { detailMessage, toApiError } from './errors';

describe('detailMessage', () => {
  it('usa el detail string tal cual', () => {
    expect(detailMessage({ detail: 'El tier tiene clientes asignados' }, 409)).toBe(
      'El tier tiene clientes asignados',
    );
  });

  it('arma una linea por error de validacion de pydantic', () => {
    const body = {
      detail: [
        { loc: ['body', 'e164'], msg: "String should match pattern '^\\+\\d{8,15}$'" },
        { loc: ['body', 'name'], msg: 'Field required' },
      ],
    };
    expect(detailMessage(body, 422)).toBe(
      "e164: String should match pattern '^\\+\\d{8,15}$'\nname: Field required",
    );
  });

  it('cae a un mensaje por estado', () => {
    expect(detailMessage(undefined, 403)).toBe('No tenés permiso para hacer esto.');
    expect(detailMessage(undefined, 418)).toBe('Error 418');
  });

  it('usa el detail de un 500 o 502 JSON', () => {
    const e = toApiError({ detail: 'El LLM no responde', code: 'upstream_error' }, 502);
    expect(e.message).toBe('El LLM no responde');
    expect(e.code).toBe('upstream_error');
    expect(toApiError({ detail: 'Error interno', code: 'internal_error' }, 500).code).toBe('internal_error');
  });

  it('conserva code y errores por campo', () => {
    const e = toApiError(
      {
        detail: 'La definicion del agente no es valida',
        code: 'invalid_definition',
        errors: [{ path: 'agent.voice', message: 'x' }],
      },
      400,
    );
    expect(e.code).toBe('invalid_definition');
    expect(e.errors).toEqual([{ path: 'agent.voice', message: 'x' }]);
  });
});
