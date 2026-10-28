import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { api } from '@/api/client';
import type { Branding } from '@/api/types';
import { useMe } from '@/features/auth/api';
import { BrandingContext, LAST_KEY, readPreview, readStored, writeStored, type BrandingState } from './context';

/**
 * Marca blanca del panel (docs/ARQUITECTURA.md). De dónde sale la marca, en orden:
 * 1. la vista previa de un admin que entró como el cliente (sessionStorage `branding:preview`, el borrador de la
 *    pestaña Marca blanca, docs/ARQUITECTURA.md);
 * 2. la del cliente de la sesión (`me.branding`; la administración, sin marca);
 * 3. sin sesión: la pública de `/login?c=<slug>` o la última que mostró el panel (localStorage
 *    `branding:last`), así el login y la carga no parpadean con el azul de Atentina.
 */

/** El `c=` de la URL (links de los mails y del login con marca). */
function slugFromUrl(): string | null {
  const c = new URLSearchParams(window.location.search).get('c')?.trim() ?? '';
  return /^[a-z0-9_-]{1,64}$/.test(c) ? c : null;
}

export function BrandingProvider({ children }: { children: ReactNode }) {
  const { data: me } = useMe();
  // La pública de `?c=` (llega después del fetch); undefined = todavía no se pidió.
  const [fetched, setFetched] = useState<Branding | null | undefined>(undefined);
  const [preview] = useState<Branding | null>(() => readPreview());
  // La última que mostró el panel (se relee en cada render: es un JSON de unos bytes).
  const stored = readStored(window.localStorage, LAST_KEY);

  // Sin sesión y con `?c=`: la marca pública del cliente (404: no hay marca, y se olvida la recordada).
  useEffect(() => {
    if (me) return;
    const slug = slugFromUrl();
    if (!slug) return;
    let cancelled = false;
    void api
      .GET('/api/v1/public/branding/{slug}', { params: { path: { slug } } })
      .then(({ data }) => {
        if (cancelled) return;
        const b = data ?? null;
        setFetched(b);
        writeStored(window.localStorage, LAST_KEY, b);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [me]);

  // Con sesión de cliente, la suya queda recordada para el próximo login (o se olvida si ya no tiene). La de un
  // cliente en el que entró un admin no: el próximo login sería el del admin.
  useEffect(() => {
    if (me?.role === 'client' && !me.support) writeStored(window.localStorage, LAST_KEY, me.branding ?? null);
  }, [me]);

  const value = useMemo<BrandingState>(() => {
    if (me?.support && preview) return { branding: preview, preview: true };
    if (me) return { branding: me.branding ?? null, preview: false };
    return { branding: fetched === undefined ? stored : fetched, preview: false };
  }, [me, preview, fetched, stored]);

  // Favicon: con marca, uno neutro (un logo horizontal a 16 px no se lee).
  useEffect(() => {
    const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    if (link) link.href = value.branding ? '/panel-mark.svg' : '/atentina-mark.svg';
  }, [value.branding]);

  return <BrandingContext.Provider value={value}>{children}</BrandingContext.Provider>;
}
