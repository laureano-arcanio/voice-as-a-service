// Lo que el teléfono recuerda en el navegador. Todo con try/catch: en una ventana privada o con los datos
// del sitio bloqueados, el acceso puede fallar y el panel sigue igual.

const CALL_KEY = 'atentina.phone.call';
const AVAILABLE_KEY = 'atentina.phone.available';
const fromKey = (userId: string) => `atentina.phone.from.${userId}`;

function read(storage: () => Storage, key: string): string | null {
  try {
    return storage().getItem(key);
  } catch {
    return null;
  }
}

function write(storage: () => Storage, key: string, value: string | null) {
  try {
    if (value === null) storage().removeItem(key);
    else storage().setItem(key, value);
  } catch {
    // sin almacenamiento: no se recuerda
  }
}

const session = () => window.sessionStorage;
const local = () => window.localStorage;

/** La llamada en curso de esta pestaña: al recargar, "Volver a entrar". */
export const storedCall = {
  get: () => read(session, CALL_KEY),
  set: (id: string | null) => write(session, CALL_KEY, id),
};

/** Disponible en esta pestaña (sobrevive a la recarga, no a otra pestaña). */
export const storedAvailable = {
  get: () => read(session, AVAILABLE_KEY) === '1',
  set: (on: boolean) => write(session, AVAILABLE_KEY, on ? '1' : null),
};

/** El número de salida elegido, por usuario. */
export const storedFrom = {
  get: (userId: string) => read(local, fromKey(userId)),
  set: (userId: string, numberId: string | null) => write(local, fromKey(userId), numberId),
};
