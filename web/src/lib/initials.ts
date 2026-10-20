/** Iniciales para el avatar del link para llamar: "Clínica del Sur" -> "CS". */
export function initials(name: string): string {
  const words = name
    .split(/\s+/)
    .filter((w) => w && /[\p{L}\p{N}]/u.test(w[0]) && !/^(de|del|la|las|los|el|y)$/i.test(w));
  const letters = (words.length > 1 ? [words[0], words[words.length - 1]] : words).map((w) => w[0]);
  return letters.join('').toUpperCase() || '·';
}
