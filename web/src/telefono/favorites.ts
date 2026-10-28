// Favoritos del teléfono: por usuario y en este navegador (como los de la app del celular). Se guarda una copia
// del nombre y el teléfono para mostrarlos sin pedir cada contacto; al tocarlo se llama por el contacto (contact_id).
import { useCallback, useState } from 'react';

export interface Favorite {
  id: string;
  name: string | null;
  phone: string;
}

const key = (userId: string) => `atentina.phone.favorites.${userId}`;
const MAX = 24;

function load(userId: string): Favorite[] {
  try {
    const raw = window.localStorage.getItem(key(userId));
    const list: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(list)
      ? list.filter((f): f is Favorite => !!f && typeof f.id === 'string' && typeof f.phone === 'string')
      : [];
  } catch {
    return [];
  }
}

function save(userId: string, list: Favorite[]) {
  try {
    window.localStorage.setItem(key(userId), JSON.stringify(list));
  } catch {
    // sin almacenamiento: los favoritos duran lo que la pestaña
  }
}

export function useFavorites(userId: string) {
  const [list, setList] = useState<Favorite[]>(() => load(userId));
  const toggle = useCallback(
    (f: Favorite) =>
      setList((prev) => {
        const next = prev.some((x) => x.id === f.id)
          ? prev.filter((x) => x.id !== f.id)
          : [...prev, f].slice(-MAX);
        save(userId, next);
        return next;
      }),
    [userId],
  );
  const has = useCallback((id: string) => list.some((x) => x.id === id), [list]);
  return { list, toggle, has };
}
