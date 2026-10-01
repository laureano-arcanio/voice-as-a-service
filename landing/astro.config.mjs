// @ts-check
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://atentina.com.ar",
  trailingSlash: "never",
  build: { format: "file", inlineStylesheets: "never" },
  vite: { plugins: [tailwindcss()] },
});
