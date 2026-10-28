// @ts-check
import sitemap from "@astrojs/sitemap";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "astro/config";

// Páginas que no van al sitemap: el registro es transaccional (noindex), el 404 no es contenido y las versiones
// de /terminos y /privacidad son noindex (LegalDoc.astro).
const excluded = new Set(["https://atentina.com.ar/registro", "https://atentina.com.ar/404"]);
const versioned = /^https:\/\/atentina\.com\.ar\/(terminos|privacidad)\/[^/]+$/;

export default defineConfig({
  site: "https://atentina.com.ar",
  trailingSlash: "never",
  build: { format: "file", inlineStylesheets: "never" },
  // Sin lastmod: con la fecha del build todas las páginas cambiaban en cada deploy y Google deja de usar el dato.
  integrations: [
    sitemap({
      filter: (page) => {
        const url = page.replace(/\/$/, "");
        return !excluded.has(url) && !versioned.test(url);
      },
    }),
  ],
  vite: { plugins: [tailwindcss()] },
});
