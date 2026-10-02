import { describe, expect, it } from 'vitest';
import { isFacebookOrigin, parseSignupMessage } from './facebook';
import { normalizeTemplateName, placeholderError, placeholderNumbers, templateBody } from './templates';

describe('isFacebookOrigin', () => {
  it('acepta facebook.com y sus subdominios por https', () => {
    expect(isFacebookOrigin('https://www.facebook.com')).toBe(true);
    expect(isFacebookOrigin('https://facebook.com')).toBe(true);
    expect(isFacebookOrigin('https://business.facebook.com')).toBe(true);
  });

  it('rechaza lo que el endsWith del ejemplo de Meta dejaria pasar', () => {
    expect(isFacebookOrigin('https://evilfacebook.com')).toBe(false);
    expect(isFacebookOrigin('https://facebook.com.evil.net')).toBe(false);
    expect(isFacebookOrigin('http://www.facebook.com')).toBe(false);
    expect(isFacebookOrigin('null')).toBe(false);
  });
});

describe('parseSignupMessage', () => {
  const finish = {
    type: 'WA_EMBEDDED_SIGNUP',
    event: 'FINISH',
    data: { phone_number_id: '111', waba_id: '222', business_id: '333' },
  };

  it('FINISH como string JSON (asi lo manda Meta)', () => {
    expect(parseSignupMessage(JSON.stringify(finish))).toEqual({
      kind: 'finish',
      event: 'FINISH',
      waba_id: '222',
      phone_number_id: '111',
      business_id: '333',
    });
  });

  it('coexistencia y solo WABA', () => {
    const coex = parseSignupMessage({ ...finish, event: 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING' });
    expect(coex).toMatchObject({ kind: 'finish', event: 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING' });
    const only = parseSignupMessage({
      type: 'WA_EMBEDDED_SIGNUP',
      event: 'FINISH_ONLY_WABA',
      data: { waba_id: '222' },
    });
    expect(only).toMatchObject({ kind: 'finish', event: 'FINISH_ONLY_WABA', phone_number_id: '' });
  });

  it('cancelacion con el paso y error con la sesion', () => {
    expect(
      parseSignupMessage({
        type: 'WA_EMBEDDED_SIGNUP',
        event: 'CANCEL',
        data: { current_step: 'PHONE_NUMBER_SETUP' },
      }),
    ).toEqual({ kind: 'cancel', step: 'PHONE_NUMBER_SETUP' });
    expect(
      parseSignupMessage({
        type: 'WA_EMBEDDED_SIGNUP',
        event: 'CANCEL',
        data: { error_message: 'falló', error_code: 524126, session_id: 'abc' },
      }),
    ).toEqual({ kind: 'error', message: 'falló', code: '524126', sessionId: 'abc' });
  });

  it('ignora mensajes que no son del alta y marca eventos no soportados', () => {
    expect(parseSignupMessage('no es json')).toBeNull();
    expect(parseSignupMessage({ type: 'OTRA_COSA' })).toBeNull();
    expect(parseSignupMessage(null)).toBeNull();
    expect(
      parseSignupMessage({
        type: 'WA_EMBEDDED_SIGNUP',
        event: 'FINISH_OBO_MIGRATION',
        data: { waba_id: '1' },
      }),
    ).toEqual({
      kind: 'unsupported',
      event: 'FINISH_OBO_MIGRATION',
    });
  });

  it('IDs que no son digitos no pasan', () => {
    expect(parseSignupMessage({ ...finish, data: { waba_id: '22a', phone_number_id: '1' } })).toMatchObject({
      kind: 'error',
    });
    expect(
      parseSignupMessage({ ...finish, data: { waba_id: '22', phone_number_id: '1;x', business_id: 'x' } }),
    ).toEqual({
      kind: 'finish',
      event: 'FINISH',
      waba_id: '22',
      phone_number_id: '',
      business_id: null,
    });
  });
});

describe('plantillas', () => {
  it('variables seguidas', () => {
    expect(placeholderNumbers('Hola {{1}}, turno {{2}} y {{ 1 }}')).toEqual([1, 2]);
    expect(placeholderError('Hola {{1}} {{2}}')).toBeNull();
    expect(placeholderError('Hola {{2}}')).not.toBeNull();
    expect(placeholderError('Hola {{1}} {{3}}')).not.toBeNull();
    expect(placeholderError('Sin variables')).toBeNull();
  });

  it('nombre normalizado para Meta', () => {
    expect(normalizeTemplateName('Recordatorio de Turno Ñandú')).toBe('recordatorio_de_turno_nandu');
  });

  it('cuerpo desde los componentes', () => {
    expect(
      templateBody([
        { type: 'HEADER', text: 'x' },
        { type: 'BODY', text: 'Hola {{1}}' },
      ]),
    ).toBe('Hola {{1}}');
    expect(templateBody([])).toBe('');
  });
});
