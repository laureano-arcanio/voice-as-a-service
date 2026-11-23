import { describe, expect, it } from 'vitest';
import { fromWhatsappDraft, toWhatsappDraft, whatsappError } from './whatsappDraft';

const SAVED = {
  account_id: 'wa1',
  template: { name: 'equipo_rotacion', language: 'es_AR', params: ['area'] },
  call_template: { name: 'equipo_llamada', language: 'es_AR', params: ['area'] },
  accept_template: { name: 'equipo_acepta', language: 'es_AR', params: ['area', 'cliente'] },
  wait_seconds: 90,
};

describe('whatsapp del área', () => {
  it('ida y vuelta conserva cuenta, plantillas, idioma, variables en orden y espera', () => {
    expect(fromWhatsappDraft(toWhatsappDraft(SAVED), 'call')).toEqual(SAVED);
  });

  it('sin cuenta ni plantillas manda null; en un área de aviso no manda la plantilla de la llamada ni la de aceptar', () => {
    expect(fromWhatsappDraft(toWhatsappDraft(null), 'call')).toBeNull();
    expect(fromWhatsappDraft(toWhatsappDraft(SAVED), 'whatsapp')).not.toHaveProperty('call_template');
    expect(fromWhatsappDraft(toWhatsappDraft(SAVED), 'whatsapp')).not.toHaveProperty('accept_template');
  });

  it('un área de aviso exige cuenta y plantilla; la de llamada puede no tener WhatsApp', () => {
    const empty = toWhatsappDraft(null);
    expect(whatsappError(empty, 'call')).toBeNull();
    expect(whatsappError(empty, 'whatsapp')).toMatch(/número de WhatsApp y la plantilla/);
    expect(whatsappError({ ...empty, accountId: 'wa1' }, 'call')).toMatch(/al menos una plantilla/);
    expect(whatsappError({ ...empty, accountId: 'wa1' }, 'whatsapp')).toMatch(/plantilla/);
  });

  it('cliente solo en el aviso y al aceptar; nombres inválidos y valores vacíos se rechazan', () => {
    const d = toWhatsappDraft(SAVED);
    const withParam = (param: string) => ({
      ...d,
      template: { ...d.template!, params: [param] },
    });
    expect(whatsappError(withParam('cliente'), 'call')).toMatch(/no sale antes de que alguien acepte/);
    expect(whatsappError(withParam('cliente'), 'whatsapp')).toBeNull();
    expect(
      whatsappError({ ...d, callTemplate: { ...d.callTemplate!, params: ['cliente'] } }, 'call'),
    ).toMatch(/Plantilla de la llamada/);
    // Al aceptar, el teléfono ya se entregó: cliente puede ir.
    expect(whatsappError({ ...d, acceptTemplate: { ...d.acceptTemplate!, params: ['cliente'] } }, 'call')).toBeNull();
    expect(whatsappError(withParam(''), 'call')).toMatch(/elegí qué valor va en \{\{1\}\}/);
    expect(whatsappError(withParam('Ficha'), 'call')).toMatch(/no es un nombre válido/);
    expect(whatsappError(withParam('ficha_2'), 'call')).toBeNull();
  });

  it('un área de llamada puede tener solo la plantilla al aceptar', () => {
    const d = toWhatsappDraft(SAVED);
    const only = { ...d, template: null, callTemplate: null };
    expect(whatsappError(only, 'call')).toBeNull();
    expect(fromWhatsappDraft(only, 'call')).toEqual({
      account_id: 'wa1',
      accept_template: { name: 'equipo_acepta', language: 'es_AR', params: ['area', 'cliente'] },
      wait_seconds: 90,
    });
    const bad = { ...only, acceptTemplate: { ...only.acceptTemplate!, params: [''] } };
    expect(whatsappError(bad, 'call')).toMatch(/Plantilla al aceptar: elegí qué valor va en \{\{1\}\}/);
  });

  it('la espera va entre 30 y 3600 s en la rotación', () => {
    const d = toWhatsappDraft(SAVED);
    expect(whatsappError({ ...d, waitSeconds: 10 }, 'call')).toMatch(/entre 30 y 3600/);
    expect(whatsappError({ ...d, waitSeconds: '' }, 'call')).toMatch(/entre 30 y 3600/);
    expect(whatsappError({ ...d, waitSeconds: 3600 }, 'call')).toBeNull();
  });
});
