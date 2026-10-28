/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

// Dev: /api va al backend (por defecto el de desarrollo en 127.0.0.1:8111, ver README).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.VITE_API_PROXY || 'http://127.0.0.1:8111';
  const proxy = { '/api': { target: apiTarget, changeOrigin: false } };
  return {
    base: '/',
    plugins: [react()],
    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
    server: { proxy },
    preview: { proxy },
    build: {
      outDir: 'dist',
      emptyOutDir: true,
      chunkSizeWarningLimit: 1500,
      // Cuatro paginas: el panel (index.html), la del link para llamar (llamar.html, sin React), el
      // teléfono del equipo tipo Android (telefono.html; docs/LLAMADAS_DIRECTAS_PLAN.md, sección 16) y el
      // CRM de ventas (crm.html, lo sirve el servicio crm; docs/CRM_PLAN.md).
      rollupOptions: {
        input: {
          main: fileURLToPath(new URL('./index.html', import.meta.url)),
          llamar: fileURLToPath(new URL('./llamar.html', import.meta.url)),
          telefono: fileURLToPath(new URL('./telefono.html', import.meta.url)),
          crm: fileURLToPath(new URL('./crm.html', import.meta.url)),
        },
      },
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      css: false,
      // Con la máquina cargada (otras sesiones, todos los workers en paralelo) las pantallas pesadas pasan los 5 s.
      testTimeout: 15_000,
      env: { TZ: 'America/Argentina/Buenos_Aires' },
    },
  };
});
