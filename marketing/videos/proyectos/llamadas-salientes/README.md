# Llamadas salientes con tu equipo (tutorial)

Cómo dejar listo el teléfono del equipo para llamar a los contactos: el número, el equipo, los contactos y la
llamada, desde el panel y desde la aplicación Teléfono.

## Pedido

> (28-oct-2026, textual) "un nuevo video explicando cómo hacer desde el panel para configurar un número de llamada
> saliente para el cliente y cómo utilizar la app de teléfono para hacer llamadas. Incluye la creación de contactos y
> equipo. El objetivo del video es que un usuario pueda entender cómo iniciar y configurar para hacer llamadas
> salientes utilizando los contactos y la aplicación de teléfono. que sea corto y sencillo de entender. horizontal con
> dos voces para publicar en youtube y link a la documentación"

## Público, mensaje y formato

- **Público:** quien va a usar el teléfono del equipo (un usuario de un cliente) y quien lo configura.
- **Mensaje:** cuatro pasos y ya podés llamar con el número de tu empresa: el número, el equipo, los contactos y el
  teléfono.
- **Formato:** 1920 × 1080, 30 fps, 89,2 s (1:29). Composición `llamadas-salientes` (`src/Video.tsx`). Subtítulos
  quemados (abajo al centro, grafía normal) y música de `scripts/musica.py`. Voces: `paula` (narradora) y `gonzalo`
  (dos líneas: la grabación y los requisitos).
- **Documentación enlazada:** https://atentina.com.ar/plataforma/telefono-del-equipo (página "Teléfono del equipo"
  de la landing, 200 el 28-oct-2026). No hay una página de documentación específica de este flujo: la más cercana
  para API es `/desarrolladores/docs/api#directas`. Va en la pantalla final y en el texto de YouTube
  ([`youtube.md`](youtube.md)).
- **Contexto:** pieza para el canal de YouTube (@atentinaar) y para esa página. Complementa a
  [`primeros-pasos`](../primeros-pasos/README.md) (tutorial vertical para crear un agente) y a
  [`derivaciones`](../derivaciones/README.md). No se subió a ningún lado desde acá.

## Guion (v1)

| Escena | s | Voz | Qué se dice | Qué se ve |
|---|---|---|---|---|
| `intro` | 0–10,4 | paula (l1) | "En este video te mostramos cómo hacer llamadas salientes con tu equipo, desde el panel y desde la aplicación de teléfono. Son cuatro pasos: el número, el equipo, los contactos y el teléfono." | Fondo oscuro: "Llamadas salientes con el número de tu empresa" y los cuatro pasos que aparecen al nombrarlos |
| `numero` | 10,4 | paula (l2) | "Primero, el número. El administrador lo asigna a tu cliente desde Números, y enseguida aparece en tu panel, en Cuenta, Números. Con ese número ya podés llamar." | Capturas reales: Administración › Números con el número Libre y **Asignar**; el diálogo con el cliente elegido; Cuenta › Números del cliente. Tarjetas de ruta |
| `equipo` | 13,0 | paula (l3) | "Segundo, el equipo. En Agenda, Equipo, agregás a cada persona con su nombre, su teléfono y su usuario del panel. Después, en el número, elegís que lo atienda el equipo y sumás a esas personas, para que también reciban las llamadas entrantes." | Equipo › **Agregar persona** (nombre, teléfono, usuario del panel); Cuenta › Números › Editar con **El equipo** y las personas |
| `contactos` | 10,4 | paula (l4) | "Tercero, los contactos. En Agenda, Contactos, tocás Nuevo contacto y cargás el teléfono y el nombre. Si tenés muchos, los importás desde un archivo." | Contactos › **Nuevo contacto** con teléfono, nombre, email y notas; la lista con **Importar CSV** marcado |
| `panel` | 16,2 | paula (l5), gonzalo (l6) | "Cuarto, a llamar. En Canales, Teléfono del equipo, elegís un contacto y tocás Llamar. Hablás desde el navegador, mejor con auriculares, y tu contacto ve el número de tu empresa." / "Las llamadas del equipo se graban y se transcriben siempre. Las encontrás en Conversaciones." | Teléfono del equipo: el menú, el contacto elegido y **Llamar**; tarjeta "Siempre: se graba, se transcribe, queda en Conversaciones" |
| `app` | 16,4 | paula (l7, l8) | "Y si preferís, usá la aplicación Teléfono. Se abre desde el panel, con Abrir aplicación Teléfono, y está pensada para el celular. Elegís un contacto, tocás Llamar, y la llamada sigue en pantalla completa." / "Mientras hablás, podés silenciar el micrófono, usar el teclado o ver los subtítulos." | El botón **Abrir aplicación Teléfono**, `telefono.atentina.com.ar` y un celular con Contactos, la ficha, Sonando y la llamada con **Silenciar, Teclado, Subtítulos** |
| `cierre` | 12,4 | paula (l9, l11), gonzalo (l10) | "Eso es todo: el número, el equipo, los contactos y el teléfono." / "Tené en cuenta que hace falta un plan pago y haber aceptado las condiciones nuevas." / "La guía completa está en la documentación." | Fondo oscuro: los cuatro pasos, "Antes de empezar: plan Mostrador, Sucursal o Red · condiciones nuevas aceptadas" y la URL de la guía |

Locución con `velocidad` 1,05 y `ganancia_db` −1,5 (como `api-desarrolladores`, con las mismas voces).

## Afirmaciones y de dónde salen

| Afirmación | Fuente |
|---|---|
| El administrador asigna el número a un cliente desde Números (**Asignar**), y el cliente lo ve en Cuenta › Números | `docs/GUIA_UI.md` sección 4; `web/src/features/numbers/` |
| Para llamar alcanza con un número asignado a la cuenta (sin Equipo) | `app/services/direct_calls.py` (`prepare_direct_call`: plan, condiciones aceptadas, usuario del cliente, `_caller_id`, minutos y canales); `TelefonoPage.tsx` ("Todavía no tenés un número asignado") |
| El equipo: nombre, teléfono, usuario del panel; asignar personas al número con **El equipo** para las entrantes | `web/src/features/team/MemberModal.tsx`; `docs/GUIA_UI.md` sección 4, punto 3; `docs/LLAMADAS_DIRECTAS_PLAN.md` sección 5 |
| Contactos: **Nuevo contacto** (teléfono, nombre, email, notas) e **Importar CSV** | `web/src/features/contacts/ContactModals.tsx`, `ContactsPage.tsx` |
| Teléfono del equipo en Canales; hablás desde el navegador; el contacto ve el número de la empresa; auriculares | `docs/GUIA_UI.md` ("Teléfono del equipo"); `web/src/features/phone/TelefonoPage.tsx` |
| Toda llamada del equipo se graba y se transcribe, y queda en Conversaciones | `AGENTS.md` (llamadas directas); `docs/LLAMADAS_DIRECTAS_PLAN.md` sección 2 |
| **Abrir aplicación Teléfono**, `telefono.atentina.com.ar`, silenciar, teclado y subtítulos | `docs/LLAMADAS_DIRECTAS_PLAN.md` sección 16; `web/src/telefono/`; `curl` a `https://telefono.atentina.com.ar/`: 200 (28-oct-2026) |
| Planes: todos menos Free (`tiers.direct_calls`); la landing los nombra Mostrador, Sucursal y Red | `docs/LLAMADAS_DIRECTAS_PLAN.md` sección 2; `landing/src/data/site.ts` (`telefono-del-equipo`). En la base el tier de Atentina, `Interno`, también la tiene |
| Hay que haber aceptado las condiciones `2026-10-28` o una posterior (`terms_pending`) | `app/services/legal_gate.py`; `AGENTS.md` |

## Capturas

Del panel real (`web/`) contra un backend aislado (SQLite, :8115, sin LiveKit) con datos ficticios (cliente "Mi
Empresa", usuaria "Ana Ríos", contactos y números de ejemplo), a 1600 × 900 con DPR 1,2 y, la app, a 390 × 844 con
DPR 2. Los scripts quedaron en `capturas/` (copiarlos a `scratch/shots/`, que tiene `puppeteer-core`):

1. `capturas/backend.sh` (backend :8115) y `capturas/seed.py` (tier Sucursal con llamadas directas, cliente, usuaria,
   números, una persona y contactos).
2. En `web/`: `VITE_API_PROXY=http://127.0.0.1:8115 npx vite --port 5177 --strictPort`.
3. `a-admin-asignar.mjs` (admin: Números y Asignar), `b-equipo.mjs`, `c-numero-equipo.mjs`, `d-contactos.mjs`,
   `f-telefono-y-app.mjs` (Teléfono del panel y la app) y `h-retoques.mjs`. Salen a
   `public/proyectos/llamadas-salientes/capturas/`.
4. **Pantallas de llamada de la app (Sonando y En curso):** no hay LiveKit en el backend aislado, así que son el
   componente real `InCallScreen` con un estado fijo (`capturas/pantalla-llamada.tsx.txt`, una página temporal que se
   borró). En el video dicen "datos de ejemplo".
5. Dos trampas: en desarrollo Vite sirve `/telefono` como la app (`telefono.html`), así que el Teléfono del panel se
   abre por navegación interna; y el Chrome del script informa `America/Buenos_Aires`, que el Python del venv local
   no conoce (se reemplaza por `America/Argentina/Buenos_Aires` en la página; en el contenedor de `app` sí existe).

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 28-oct-2026 | 89,2 s | Primera versión | borrador |
