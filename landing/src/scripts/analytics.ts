// Eventos de Google Analytics (GA4). Sin PUBLIC_GA_ID no se carga gtag y track no hace nada.

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
  }
}

export function track(event: string, params: Record<string, string | number> = {}) {
  window.gtag?.("event", event, params);
}

// Clics en WhatsApp, mail y teléfono, en cualquier página. GA4 no mide mailto ni tel por su cuenta.
export function initContactClicks() {
  document.addEventListener("click", (event) => {
    const link = (event.target as Element).closest<HTMLElement>("a[href], [data-open-tel]");
    if (!link) return;
    const href = link.getAttribute("href") ?? "";
    const method = link.hasAttribute("data-open-tel") || href.startsWith("tel:")
      ? "telefono"
      : href.startsWith("mailto:")
        ? "email"
        : href.includes("wa.me/")
          ? "whatsapp"
          : null;
    if (method) track("contact_click", { method, page: location.pathname });
  });
}
