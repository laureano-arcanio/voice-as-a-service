# Derivaciones (tutorial vertical)

Video para clientes: cómo funciona la transferencia de llamadas a personas del equipo y cómo se configura
(Equipo, áreas y la sección Derivación a personas del agente), con capturas reales del panel en un teléfono.

## Pedido

> Crea un video explicativo de como se crean agentes con transferencia de llamadas, equipo, area como se
> configura. corto, que se entienda. utiliza screens de pantalla en cada paso, version mobile. Primero explica
> como funciona con un diagrama, muchos usuarios ->ciclo de agente-> transferencias por areas.

Formato de referencia: el tutorial vertical [`primeros-pasos`](../primeros-pasos/README.md).

## Público y mensaje

Cliente que ya tiene un agente y quiere que pase llamadas a su gente. Mensaje: el agente atiende y, cuando hace
falta, pasa la llamada al área que corresponde; se configura en tres lugares (Equipo, el área y el agente).

Formato 1080 × 1920 (9:16), ~80 s, narradora `paula` y `pablo` en dos líneas (espera y guardado), música propia.

## Guion

| Escena | Voz | Qué se dice | Qué se ve |
|---|---|---|---|
| `intro` | d1 paula | Tu agente atiende las llamadas y, cuando hace falta, se las pasa a una persona de tu equipo. Te muestro cómo. | Fondo oscuro, logo, "Tu agente atiende y, cuando hace falta, **te pasa la llamada.**" |
| `ciclo` | d2 paula | Llaman muchos clientes. El agente escucha, entiende y responde, en un ciclo, turno a turno. | Diagrama: cinco clientes llamando → el agente (logo) en un ciclo Escucha → Entiende → Responde, con el nodo activo resaltado. |
| `areas` | d3 paula | Si alguien pide hablar con una persona, elige el área que corresponde y llama a su gente en orden, dentro del horario. | Diagrama: el agente y tres áreas (Ventas, Soporte técnico, Administración) con horario y personas numeradas; la llamada viaja a Ventas y suena Lucía (1), después Diego (2). |
| `espera` | d4 pablo | Mientras suena, el cliente escucha música de espera. A la persona le cuenta de qué se trata, y la conecta cuando marca uno. | Diagrama: el cliente con "Música de espera"; Lucía escucha el aviso "Derivación de Ventas: … Marcá 1 para atender."; tecla 1 y "Conectados". |
| `fallback` | d5 paula | Si nadie atiende, o el área está fuera de horario, el agente vuelve y toma el mensaje. | Diagrama: Lucía y Diego "No atiende", Administración "Fuera de horario", el agente dice el mensaje por defecto "No pude comunicarte con Ventas…". |
| `equipo` | d6 paula | Para configurarlo, abrí Equipo en el menú y agregá a cada persona con su teléfono. | Capturas: `01-menu` (toque en Equipo) → `02-equipo` (toque en Agregar persona) → `03-persona` (modal con Lucía Romero) → `04-equipo-con-lucia` (aviso "se sumó al equipo"). |
| `area` | d7 paula | Después, creá un área: el nombre, qué atiende, y las personas, en el orden en que se las llama. | Capturas: `04-equipo-con-lucia` (toque en Crear área) → `05-area-top` (Nueva área: Ventas, qué atiende, Lucía 1 y Diego 2, En orden, timbre 20 s), con un acercamiento del 12 %. |
| `horario` | d8 paula | Cargá su horario. Los mensajes, como el aviso a la persona, ya vienen escritos y los podés cambiar. | Capturas: `07-area-horario` (sin Atiende siempre: lunes a viernes 9 a 18 y sábado 9 a 13) → `09-area-mensajes` (textos por defecto). |
| `agente` | d9 paula | En tu agente, abrí Derivación a personas y marcá a qué áreas puede pasar la llamada. Si querés, aclarale cuándo. | Capturas: `12-agente-derivacion` (toques en cada "Puede pasarle llamadas") → `12b-agente-ventas` ("Cuándo pasarla" de Ventas escrito). |
| `guardar` | d10 pablo | La música de espera viene prendida. Guardá, y queda como una versión nueva del agente. | Capturas: `13-agente-musica` (toque en Música de espera) → `14-guardado` ("Versión 2 guardada."). |
| `resultado` | d11 paula | En cada conversación vas a ver el tramo con la persona del equipo, con su nombre. | Captura: `16-llamada-tramo` (Conversación con el separador "Llamada con Lucía Romero" y sus mensajes "(equipo)"), con un acercamiento del 10 %. |
| `cierre` | d12 paula | Tu agente resuelve lo que puede, y lo demás se lo pasa a tu equipo. | Fondo oscuro, logo, "Tu agente resuelve lo que puede. **Lo demás, tu equipo.**", `app.atentina.com.ar → Equipo`. |

## Afirmaciones y fuentes

- **Equipo, áreas y derivación en el agente; desplegado el 23-oct-2026 (fases 1 y 2), sin probar todavía con
  llamadas reales.** [`docs/features/EQUIPO_TELEFONIA.md`](../../../../docs/features/EQUIPO_TELEFONIA.md)
  (13.4 "Falta"). El video no dice que esté probado en producción.
- **Personas con teléfono (solo Argentina); áreas con qué atiende, personas en orden (En orden o Rotativa),
  timbre por persona, horario por día, días cerrados, tecla de vuelta a la IA y mensajes por defecto.**
  `web/src/features/team/` (`MemberModal.tsx`, `AreaModal.tsx`, `labels.ts`) y
  [`docs/GUIA_UI.md`](../../../../docs/GUIA_UI.md), "Equipo".
- **El agente elige el área, llama a sus personas en orden dentro del horario; fuera de horario no deriva y toma
  el mensaje; si nadie atiende, vuelve con el mensaje "no_answer" y toma el mensaje.** DERIVACIONES_PLAN 13.1.
- **Música de espera solo al cliente, prendida por defecto; aviso (whisper) solo a la persona y conexión con el
  1.** DERIVACIONES_PLAN 13.1, pasos 2 a 5; `HandoffSection.tsx`. El texto del aviso es el default
  ("Derivación de {{area}}: {{resumen}}. Marcá 1 para atender."), con un resumen ilustrativo.
- **"Derivación a personas" en el editor del agente: "Puede pasarle llamadas", "Cuándo pasarla" y Música de
  espera (tema estándar, volumen 30 %).** `web/src/features/agents/HandoffSection.tsx`.
- **Solo el motor clásico deriva.** Los agentes que crea un cliente son clásicos (`NewAgentModal.tsx`), así que
  el video no lo menciona.
- **Guardar crea una versión nueva.** GUIA_UI, "Crear el agente".
- **La conversación muestra el tramo con la persona ("Llamada con <persona>", "<persona> (equipo)").**
  `web/src/features/calls/ChatView.tsx` y GUIA_UI, "Detalle de una llamada".
- **Sin cifras** de latencia, capacidad ni llamadas simultáneas ("llaman muchos clientes" no promete un número).

**Ilustrativo:** la empresa "Aires del Sur", las personas (Lucía Romero, Diego Ferreyra, Martina Sosa, Julián
Ortiz), sus teléfonos (351 555-01xx), las áreas y horarios, el cliente "Marcos Vera" y toda la conversación de
`16-llamada-tramo` (la llamada no existió: el detalle se armó interceptando `GET /calls/<id>` con mensajes de
ejemplo, el mismo formato que la API devuelve para un tramo derivado). Los diagramas son ilustrativos.

## Capturas

Reales, del panel (`web/`, Vite) contra un backend de desarrollo aislado (SQLite propia, puerto 8112, sin
LiveKit, Resend ni WhatsApp), con un usuario de cliente de ejemplo, en Chrome headless a 390 × 844 con DPR 2 y
`es-ES` para ver las horas en 24 h. No se tocó el stack en vivo ni se crearon llamadas (los `POST /calls` se
cortan). Los scripts quedaron en `capturas/` (copiar los `.mjs` a `scratch/shots/`, que tiene puppeteer):

1. `capturas/backend.sh` (backend :8112) y `npx vite --port 5174` en `web/` con `VITE_API_PROXY=http://127.0.0.1:8112`.
2. `capturas/seed.py` (cliente, usuario, equipo, áreas y agente), después `capturas/reset.py` (saca a Lucía y
   Ventas y crea un agente nuevo, para capturar sus altas desde la UI).
3. `node derivaciones_video.mjs` y `node derivaciones_llamada.mjs`; las elegidas van a
   `public/proyectos/derivaciones/capturas/`.

## Decisiones

- **Voces:** `paula` narra; `pablo` en d4 (la espera) y d10 (guardar), como contrapunto.
- **Toques y zoom:** un círculo azul marca cada toque; dos acercamientos suaves (área y resultado).
- **Sin el panel de derivaciones:** es la fase 4, no está construido; el resultado se muestra en el detalle de
  la conversación, que sí muestra el tramo con la persona.

## Versiones

| Versión | Estado | Qué cambió |
|---|---|---|
| v1 | borrador | Primera versión: diagrama (ciclo, áreas, espera, si nadie atiende) y cinco pasos con capturas reales. |
