import { describe, expect, it } from 'vitest';
import { ApiError } from '@/api/errors';
import { callErrorInfo } from './errors';

describe('callErrorInfo', () => {
  it('saliente sin numero propio: dice que hace falta un numero', () => {
    const e = new ApiError(409, 'El cliente no tiene un número propio', 'no_caller_id');
    expect(callErrorInfo(e, true).message).toBe('Asigná un número al cliente para hacer salientes.');
    const client = callErrorInfo(e, false);
    expect(client.color).toBe('yellow');
    expect(client.message).toMatch(/número propio/);
  });

  it('plataforma al maximo: no culpa al plan del cliente', () => {
    const e = new ApiError(
      429,
      'En este momento estamos al máximo de llamadas simultáneas.',
      'platform_busy',
    );
    const info = callErrorInfo(e, false);
    expect(info.title).toBe('Plataforma al máximo de llamadas');
    expect(info.message).toMatch(/al máximo/);
  });

  it('limite del plan y cuenta inactiva', () => {
    expect(callErrorInfo(new ApiError(429, 'x', 'outbound_minutes'), false).title).toBe(
      'Sin minutos salientes este mes',
    );
    expect(callErrorInfo(new ApiError(403, 'x', 'client_inactive'), false).title).toBe(
      'Cuenta en solo lectura',
    );
    expect(callErrorInfo(new ApiError(502, 'LiveKit no responde'), false)).toEqual({
      title: 'No se pudo iniciar la llamada',
      message: 'LiveKit no responde',
      color: 'red',
    });
  });
});
