import { describe, expect, it } from 'vitest';
import { variableSourceLabel } from './variables';

describe('fuente de una variable', () => {
  it('dice en palabras de dónde salió el valor', () => {
    expect(variableSourceLabel('system')).toBe('del sistema');
    expect(variableSourceLabel('default')).toBe('valor por defecto');
    expect(variableSourceLabel('contact')).toBe('contacto o campaña');
    expect(variableSourceLabel('request')).toBe('pedido de la llamada');
    expect(variableSourceLabel('pre_call:consultar_deuda')).toBe('pre-call (consultar_deuda)');
    expect(variableSourceLabel('tool:buscar_cliente')).toBe('herramienta (buscar_cliente)');
    expect(variableSourceLabel('otra')).toBe('otra');
  });
});
