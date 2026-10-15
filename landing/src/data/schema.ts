// JSON-LD (schema.org) que cada página pasa a `Base.astro` en `schema`. La `Organization` la pone `Base` en todas.
import { type CapabilityPage, freePlan, type Plan, plans, type Qa } from "./site";

export const SITE = "https://atentina.com.ar";
export const ORG_ID = `${SITE}/#organization`;

const abs = (path: string) => new URL(path, SITE).href;
const clean = (text: string) => text.replace(/<[^>]+>/g, "");

export function webSite() {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "Atentina",
    url: `${SITE}/`,
    inLanguage: "es-AR",
    publisher: { "@id": ORG_ID },
  };
}

/** `FAQPage` con las mismas preguntas que muestra `Faq.astro`. */
export function faqPage(items: Qa[]) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: { "@type": "Answer", text: item.a },
    })),
  };
}

/** `BreadcrumbList`: el último elemento es la página actual. */
export function breadcrumb(trail: { name: string; path: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: trail.map((item, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: item.name,
      item: abs(item.path),
    })),
  };
}

/** Un plan como `Offer`: precio en pesos por mes. "A medida" no lleva precio. */
function offer(plan: Plan, url: string) {
  const amount = plan.price.startsWith("$") ? Number(plan.price.replace(/\D/g, "")) : undefined;
  const base = {
    "@type": "Offer",
    name: plan.name,
    description: `${plan.for} ${plan.items.filter((item) => !item.startsWith("Todo lo que ofrece")).map(clean).join(", ")}.`,
    url,
    priceCurrency: "ARS",
  };
  if (amount === undefined) return base;
  return {
    ...base,
    price: amount,
    priceSpecification: {
      "@type": "UnitPriceSpecification",
      price: amount,
      priceCurrency: "ARS",
      billingDuration: "P1M",
      unitCode: "MON",
    },
  };
}

/** Los planes que muestra `Pricing`: con `free`, también el plan Free. */
export const pricingPlans = (free = false): Plan[] => (free ? [freePlan, ...plans] : plans);

/** `Service` de Atentina; con `plans`, sus precios como `Offer`. */
export function service(opts: { name: string; serviceType: string; description: string; path: string; plans?: Plan[] }) {
  const url = abs(opts.path);
  return {
    "@context": "https://schema.org",
    "@type": "Service",
    name: opts.name,
    serviceType: opts.serviceType,
    description: opts.description,
    url,
    provider: { "@id": ORG_ID },
    areaServed: "AR",
    ...(opts.plans && { offers: opts.plans.map((plan) => offer(plan, `${url}#precios`)) }),
  };
}

/** Todo lo que lleva una página de `/plataforma/<slug>`. */
export function capabilitySchema(page: CapabilityPage, plans: Plan[]) {
  const path = `/plataforma/${page.slug}`;
  return [
    service({ name: page.title, serviceType: page.serviceType, description: page.metaDescription, path, plans }),
    breadcrumb([
      { name: "Atentina", path: "/" },
      { name: "Plataforma", path: "/plataforma" },
      { name: page.title, path },
    ]),
    faqPage(page.faq),
  ];
}

