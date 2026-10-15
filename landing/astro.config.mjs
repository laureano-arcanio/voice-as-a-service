// @ts-check
import sitemap from "@astrojs/sitemap";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "astro/config";

// Páginas que no van al sitemap: el registro es transaccional (noindex) y el 404 no es contenido.
const excluded = new Set(["https://atentina.com.ar/registro", "https://atentina.com.ar/404"]);

export default defineConfig({
  site: "https://atentina.com.ar",
  trailingSlash: "never",
  build: { format: "file", inlineStylesheets: "never" },
  // lastmod: la fecha del build (el sitio es estático y se reconstruye en cada deploy).
  integrations: [sitemap({ filter: (page) => !excluded.has(page.replace(/\/$/, "")), lastmod: new Date() })],
  vite: { plugins: [tailwindcss()] },
});
