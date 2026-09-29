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
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      css: false,
      env: { TZ: 'America/Argentina/Buenos_Aires' },
    },
  };
});
