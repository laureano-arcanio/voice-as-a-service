# web — UI de Atentina

SPA en React + Vite + TypeScript (strict). Estructura, entradas y convenciones en
[`docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md), sección "Frontend"; diseño en
[`docs/DESIGN_GUIDELINE_APP.md`](../docs/DESIGN_GUIDELINE_APP.md).

## Correr

| Comando | Qué levanta |
|---|---|
| `make dev-backend` | API de desarrollo sobre SQLite (`scratch/dev.db`, con seed; admin `admin@oime.com.ar` / `admin12345`) en `127.0.0.1:8111`, sin tocar el stack. Necesita `.venv` con Python 3.12 (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`). |
| `cd web && npm install && npm run dev` | UI en `http://localhost:5173`; `/api` va a `VITE_API_PROXY` (default `http://127.0.0.1:8111`, el de arriba). |
| `make web-dev` | La misma UI contra el `app` del stack (`:8011`). Los dos puertos (8111 y 8011) son a propósito. |
| `make web-build` | Build en `web/dist` (la imagen de `app` la compila sola). |
| `make web-check` | ESLint, tipos y Vitest: lo que hay que pasar antes de un commit. |

Otro backend: `VITE_API_PROXY=http://host:puerto npm run dev`.

## Al cambiar la API

`make openapi` exporta el OpenAPI a `web/openapi.json` y corre `npm run gen:api` (regenera
`src/api/schema.d.ts`); después, corregir lo que marque `npm run typecheck`.

## Scripts

| Script | Qué hace |
|---|---|
| `npm run build` | `tsc -b` + build a `web/dist` (cuatro entradas: panel, `llamar`, `telefono`, `crm`) |
| `npm run preview` | sirve `dist` en :4173 con el mismo proxy de `/api` |
| `npm run lint` / `format` | ESLint (flat, typescript-eslint, react-hooks, TanStack Query) / Prettier |
| `npm run typecheck` | `tsc -b` |
| `npm test` | Vitest + Testing Library (jsdom, TZ Buenos Aires) |
| `npm run gen:api` | regenera `src/api/schema.d.ts` desde `openapi.json` (versionado) |
