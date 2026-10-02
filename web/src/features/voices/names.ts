// El catalogo (tts/finetune/voces.tsv) tiene los nombres en minuscula y sin tildes: "sofia" -> "Sofía".
const ACCENTED: Record<string, string> = {
  sofia: 'Sofía',
  lucia: 'Lucía',
  veronica: 'Verónica',
  rocio: 'Rocío',
  belen: 'Belén',
  martin: 'Martín',
  nicolas: 'Nicolás',
  joaquin: 'Joaquín',
  tomas: 'Tomás',
};

export function voiceName(id: string): string {
  return ACCENTED[id] ?? id.charAt(0).toUpperCase() + id.slice(1);
}

export const GENDER_LABEL: Record<string, string> = { mujer: 'Mujer', hombre: 'Hombre' };
