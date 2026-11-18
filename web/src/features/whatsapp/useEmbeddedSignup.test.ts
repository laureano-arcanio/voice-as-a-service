import { describe, expect, it } from 'vitest';
import { signupExtras } from './useEmbeddedSignup';

describe('signupExtras', () => {
  it('v5 con coexistencia: el número sigue en la app', () => {
    expect(signupExtras(true)).toEqual({ version: 'v5', setup: {} });
    expect(signupExtras(undefined)).toEqual({ version: 'v5', setup: {} });
  });

  it('con la coexistencia apagada pide un número nuevo', () => {
    expect(signupExtras(false)).toEqual({
      version: 'v5',
      setup: {},
      features: [{ name: 'whatsapp_business_app_onboarding', enabled: false }],
    });
  });
});
