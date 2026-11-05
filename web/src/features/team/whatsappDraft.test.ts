import { describe, expect, it } from 'vitest';
import { fromWhatsappDraft, toWhatsappDraft, whatsappError } from './whatsappDraft';

const SAVED = {
  account_id: 'wa1',
  template: { name: 'equipo_rotacion', language: 'es_AR', params: ['area'] },
  call_template: { name: 'equipo_llamada', language: 'es_AR', params: ['area'] },
  wait_seconds: 90,
};

describe('whatsapp del área', () => {
  it('ida y vuelta conserva cuenta, plantillas, idioma, variables en orden y espera', () => {
    expect(fromWhatsappDraft(toWhatsappDraft(SAVED), 'call')).toEqual(SAVED);
  });

  it('sin cuenta ni plantillas manda null; en un área de aviso no manda la plantilla de la llamada', () => {
    expect(fromWhatsappDraft(toWhatsappDraft(null), 'call')).toBeNull();
    expect(fromWhatsappDraft(toWhatsappDraft(SAVED), 'whatsapp')).not.toHaveProperty('call_template');
  });

  it('un área de aviso exige cuenta y plantilla; la de llamada puede no tener WhatsApp', () => {
    const empty = toWhatsappDraft(null);
    expect(whatsappError(empty, 'call')).toBeNull();
    expect(whatsappError(empty, 'whatsapp')).toMatch(/número de WhatsApp y la plantilla/);
    expect(whatsappError({ ...empty, accountId: 'wa1' }, 'call')).toMatch(/al menos una plantilla/);
    expect(whatsappError({ ...empty, accountId: 'wa1' }, 'whatsapp')).toMatch(/plantilla/);
  });

  it('cliente solo en el aviso; nombres inválidos y valores vacíos se rechazan', () => {
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
    expect(whatsappError(withParam(''), 'call')).toMatch(/elegí qué valor va en \{\{1\}\}/);
    expect(whatsappError(withParam('Ficha'), 'call')).toMatch(/no es un nombre válido/);
    expect(whatsappError(withParam('ficha_2'), 'call')).toBeNull();
  });

  it('la espera va entre 30 y 3600 s en la rotación', () => {
    const d = toWhatsappDraft(SAVED);
    expect(whatsappError({ ...d, waitSeconds: 10 }, 'call')).toMatch(/entre 30 y 3600/);
    expect(whatsappError({ ...d, waitSeconds: '' }, 'call')).toMatch(/entre 30 y 3600/);
    expect(whatsappError({ ...d, waitSeconds: 3600 }, 'call')).toBeNull();
  });
});
