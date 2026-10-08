# web — UI de Atentina

SPA en React 19 + Vite + TypeScript (strict). Reemplazó al dashboard Jinja (`templates/`, `static/`, borrados en sep-2026).
FastAPI sirve el build: `web/dist/assets/*` estático y cualquier otra ruta → `index.html`.

## Correr

```bash
cd web
npm install
npm run dev          # http://localhost:5173, /api va a VITE_API_PROXY (default http://127.0.0.1:8111)
```

Backend de desarrollo (SQLite en `scratch/dev.db`, con seed; admin `admin@oime.com.ar` / `admin12345`):
`make dev-backend` (`scripts/dev_backend.sh`) levanta la API en 127.0.0.1:8111, sin tocar el stack. Necesita
un `.venv` con Python 3.12 (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`).

Otro backend: `VITE_API_PROXY=http://host:puerto npm run dev`. `make web-dev` usa el `app` del stack
(:8011) en lugar del de desarrollo (:8111): los dos puertos son a propósito.

| Script                    | Qué hace                                                                 |
| ------------------------- | ------------------------------------------------------------------------ |
| `npm run build`           | `tsc -b` + build a `web/dist`                                            |
| `npm run preview`         | sirve `dist` en :4173 con el mismo proxy de `/api`                       |
| `npm run lint` / `format` | ESLint (flat, typescript-eslint, react-hooks, TanStack Query) / Prettier |
| `npm run typecheck`       | `tsc -b`                                                                 |
| `npm test`                | Vitest + Testing Library (jsdom, TZ Buenos Aires)                        |
| `npm run gen:api`         | regenera `src/api/schema.d.ts` desde `openapi.json` (versionado)         |

Al cambiar la API: exportar el OpenAPI a `web/openapi.json`, `npm run gen:api` y corregir lo que marque `tsc`.

## Estructura

- `src/api/`: cliente tipado (`openapi-fetch`), `ApiError` (lee `detail`, `code`, `errors`), alias de tipos.
  Sesión por cookie httpOnly: el front no maneja tokens. Un 401 con sesión abierta la cierra y va a `/login`.
- `src/features/<recurso>/`: páginas, componentes y hooks de TanStack Query (`api.ts`) de cada recurso:
  `auth`, `dashboard`, `calls`, `agents`, `clients` (incluye números, API keys, consumo y Mi cuenta), `tiers`,
  `users`, `voices`.
- `src/components/`: layout (AppShell), badges, confirmaciones, editor JSON (CodeMirror), estados de carga.
- `src/lib/`: formatos (`es-AR`, hora local), etiquetas de estados, diff de líneas, notificaciones.
- `src/router.tsx`: rutas con carga diferida por página y guardas por rol (`admin` / `client`).

Filtros del dashboard, pestañas y mes de consumo van en la URL (se pueden compartir).
Tema Mantine con la marca (azul `#2456e6`, solo claro; `src/theme.ts` y `src/styles.css`), según
[`docs/DESIGN_GUIDELINE_APP.md`](../docs/DESIGN_GUIDELINE_APP.md). Tipografías servidas por la app (`@fontsource`);
logos en `public/`, copiados de `docs/brand/`.
