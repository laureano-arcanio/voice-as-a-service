import { useDocumentTitle } from '@mantine/hooks';
import { createContext, useContext } from 'react';
import type { Branding } from '@/api/types';

/** Marca blanca del panel (docs/MARCA_BLANCA_PLAN.md): el contexto y sus hooks. El provider está en Provider.tsx. */

export const LAST_KEY = 'branding:last';
export const PREVIEW_KEY = 'branding:preview';

export interface BrandingState {
  branding: Branding | null;
  /** La marca viene de la vista previa de un admin ("Ver el panel como el cliente"). */
  preview: boolean;
}

export const BrandingContext = createContext<BrandingState>({ branding: null, preview: false });

export function readStored(storage: Storage, key: string): Branding | null {
  try {
    const raw = storage.getItem(key);
    if (!raw) return null;
    const b = JSON.parse(raw) as Branding;
    return b && typeof b.slug === 'string' && typeof b.color_primary === 'string' ? b : null;
  } catch {
    return null;
  }
}

export function writeStored(storage: Storage, key: string, value: Branding | null) {
  try {
    if (value) storage.setItem(key, JSON.stringify(value));
    else storage.removeItem(key);
  } catch {
    // modo privado o sin espacio: sin memoria, nada más
  }
}

export function readPreview(): Branding | null {
  return readStored(window.sessionStorage, PREVIEW_KEY);
}

export function setPreview(value: Branding | null) {
  writeStored(window.sessionStorage, PREVIEW_KEY, value);
}

export function useBranding(): Branding | null {
  return useContext(BrandingContext).branding;
}

export function useBrandingPreview(): boolean {
  return useContext(BrandingContext).preview;
}

/** Nombre de la marca para los títulos: el del cliente con marca blanca, o Atentina. */
export function useBrandName(): string {
  return useBranding()?.name ?? 'Atentina';
}

/** Título de la pestaña: "Conversaciones · Yoizen" o "Conversaciones · Atentina". */
export function usePageTitle(title?: string) {
  const brand = useBrandName();
  useDocumentTitle(title ? `${title} · ${brand}` : brand);
}
