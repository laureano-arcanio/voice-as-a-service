import { describe, expect, it } from 'vitest';
import { waStatusReason } from './labels';

describe('waStatusReason', () => {
  it('traduce la inactividad de Meta', () => {
    expect(waStatusReason('account_update PARTNER_REMOVED PRIMARY_INACTIVITY')).toContain(
      'dejó de abrirse en el teléfono',
    );
    expect(waStatusReason('account_update PARTNER_REMOVED COMPANION_INACTIVITY')).toContain(
      'app de WhatsApp Business',
    );
  });

  it('deja el resto como vino', () => {
    expect(waStatusReason('token_invalid code=190')).toBe('token_invalid code=190');
    expect(waStatusReason(null)).toBeNull();
  });
});
