// Índice de la documentación (/desarrolladores/docs): la portada, MCP, API y Tu propio agente. Cada página toma de acá
// su "En esta página" y DocsPage arma con esto la navegación del costado; los ids son los de cada <section>.

export interface DocsSection {
  id: string;
  label: string;
}

export interface DocsGroup {
  key: "intro" | "mcp" | "api" | "propio";
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
      { id: "directas", label: "Llamadas directas" },
      { id: "eventos", label: "Eventos" },
      { id: "reportes", label: "Reportes" },
    ],
  },
  {
    key: "propio",
    title: "Tu propio agente",
    href: "/desarrolladores/docs/tu-propio-agente",
    sections: [
      { id: "que-es", label: "Qué es" },
      { id: "como-funciona", label: "Cómo funciona" },
      { id: "pedido", label: "El pedido" },
      { id: "respuesta", label: "La respuesta" },
      { id: "herramientas", label: "end_call y transfer_call" },
      { id: "configurar", label: "Configurarlo" },
      { id: "ejemplo", label: "Un endpoint de ejemplo" },
      { id: "latencia", label: "Latencia y turnos" },
      { id: "errores", label: "Errores" },
      { id: "planes", label: "Planes, costos y datos" },
    ],
  },
];

export const docsGroup = (key: DocsGroup["key"]) => docsNav.find((g) => g.key === key)!;
