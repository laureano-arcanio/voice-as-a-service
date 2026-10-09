// Solo para tests que leen archivos del repo (el proyecto no trae @types/node).
declare module 'node:fs' {
  export function readFileSync(path: URL, encoding: 'utf8'): string;
}
