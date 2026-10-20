# Video técnico para Yoizen (integradores)

- **Pedido (20-oct-2026, Laureano):** una animación más técnica para integradores, orientada a Yoizen, que muestre
  cómo pueden sumar llamadas de voz, síntesis y transcripción a los agentes que ya tienen, con las APIs de agentes,
  llamadas y consultas. Objetivo: que vean que integran lo que ya tienen y que es un servicio de voz administrado
  con acceso total a sus datos y configuración.
- **Contexto (reunión con Juan Stamati, Yoizen):** Yoizen tiene omnicanal digital (WhatsApp, web chat, bots
  no-code, IVR, ACD) en Azure EE.UU. y está sumando Asterisk; su orquestador no maneja voz. Necesitan voicebots
  entrantes y salientes, que sus equipos configuren sin depender de Atentina, y escalar. Quedaron por validar
  capacidad, costos y desempeño; Laureano evalúa un SIP trunk con su Asterisk y propuso un piloto sin costo.
  Material escrito para la misma reunión: [`../../../documentos/proyectos/yoizen-propuesta/`](../../../documentos/proyectos/yoizen-propuesta/README.md).
- **Público:** equipo técnico y de producto de Yoizen (CTO, responsable de producto).
- **Formato:** 1920 × 1080, 30 fps, ~70 s. Composición `yoizen` (`src/Video.tsx`).

## Guion (v1)

| Escena | Locución | Qué se ve |
|---|---|---|
| `intro` | y1 | "Atentina × Yoizen · Integración de voz", "Voz con IA para los agentes que ya tienen" |
| `arquitectura` | y2 | Yoizen (sin cambios) ⇄ tres APIs (agentes, llamadas, inferencia) ⇄ Atentina (voz administrada) |
| `agentes` | y3 | Cada parte del bot (instrucciones, saludo, conocimiento, datos) → su clave del JSON; `POST /agents` v1 → `PUT /agents/{id}/definition` v2; `GET /agents/schema`, `POST /agents/validate` |
| `llamadas` | y4 | Web chat "llámenme" → `POST /calls` con `context` → llamada → `GET /calls/{id}` → ticket actualizado; entradas: número, WhatsApp, link web, campañas + webhook, "SIP desde su Asterisk · en evaluación" |
| `inferencia` | y5 | Nota de voz → transcribe → su bot sin cambios → sintetiza → audio; código Python con el SDK de OpenAI |
| `datos` | y6 | Ocho tarjetas con rutas reales (conversación, métricas, grabaciones, reportes, webhook, versiones, LLM propio o el suyo, API keys) y 0,9 s de mediana |
| `cierre` | y7 | "Nosotros operamos, ustedes integran" y cierre oscuro con "Próximo paso: un piloto con un caso real" |

Solo narrador (`lucas`), sin diálogo con audio. El nombre "Yoizen" no se dice (el TTS lo pronunciaba mal): va escrito.

## Afirmaciones y de dónde salen

- **Rutas, JSON y código:** reales (app/api/routers, `docs/API_INFERENCIA.md`), recortados.
- **0,9 s:** mediana en llamadas reales (ver el video general).
- **≈ 70 ms (transcripción) y ≈ 50 ms (primer audio, streaming):** medidos en el servidor (AGENTS.md; API_INFERENCIA.md,
  9-oct-2026). Desde Azure EE.UU. se suma la red.
- **Omitido a propósito:** "hasta 60 llamadas simultáneas" (sin medir con Gemma; CAP-001 con el modelo anterior da ~32).
- **En evaluación / sin desplegar:** SIP trunk desde su Asterisk; campañas, su webhook y su reporte; la pantalla del
  LLM propio (la API sí está); Anthropic sin probar con una key real.
- **41 voces:** todas con acento argentino (aclararlo si preguntan por México, Perú o Colombia).

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 20-oct-2026 | 69,6 s | Primera versión, con "ápi" en español | borrador |
