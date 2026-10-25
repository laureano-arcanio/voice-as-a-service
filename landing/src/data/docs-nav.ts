// Índice de la documentación (/desarrolladores/docs): la portada, MCP arriba y API abajo. Cada página toma de acá
// su "En esta página" y DocsPage arma con esto la navegación del costado; los ids son los de cada <section>.

export interface DocsSection {
  id: string;
  label: string;
}

export interface DocsGroup {
  key: "intro" | "mcp" | "api";
  title: string;
  href: string;
  sections: DocsSection[];
}

export const docsNav: DocsGroup[] = [
  {
    key: "intro",
    title: "Introducción",
    href: "/desarrolladores/docs",
    sections: [
      { id: "formas", label: "MCP o API" },
      { id: "como-funciona", label: "Cómo funciona" },
    ],
  },
  {
    key: "mcp",
    title: "MCP para agentes de IA",
    href: "/desarrolladores/docs/mcp",
    sections: [
      { id: "que-es", label: "Qué es" },
      { id: "conectar", label: "Conectar tu agente" },
      { id: "api-key", label: "Con una API key" },
      { id: "planes", label: "Qué incluye cada plan" },
      { id: "herramientas", label: "Herramientas" },
      { id: "seguridad", label: "Seguridad y datos" },
      { id: "guias", label: "Guías y prompts" },
    ],
  },
  {
    key: "api",
    title: "API",
    href: "/desarrolladores/docs/api",
    sections: [
      { id: "dos-apis", label: "Las dos APIs" },
      { id: "empezar", label: "Empezar" },
      { id: "keys", label: "API keys y alcances" },
      { id: "endpoints", label: "Endpoints" },
      { id: "streaming", label: "Streaming" },
      { id: "limites", label: "Límites y consumo" },
      { id: "errores", label: "Errores" },
      { id: "planes", label: "Qué incluye cada plan" },
      { id: "agentes", label: "Agentes y llamadas" },
      { id: "byok", label: "Tu propio LLM" },
      { id: "cortar", label: "Cortar y bloquear" },
      { id: "contactos", label: "Contactos" },
      { id: "campanas", label: "Campañas" },
      { id: "webhook", label: "Webhook" },
      { id: "derivaciones", label: "Equipo y derivaciones" },
      { id: "eventos", label: "Eventos" },
    ],
  },
];

export const docsGroup = (key: DocsGroup["key"]) => docsNav.find((g) => g.key === key)!;
