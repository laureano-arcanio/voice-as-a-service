# Propuesta comercial de Atentina (genérica)

- **Pedido (21-oct-2026, Laureano):** "Revisá el PDF que armamos para Yoiser. Creá uno nuevo pero genérico, que
  incluya toda la propuesta de Atentina, sin ser demasiado largo. Mantené el mismo template y estilo."
- **Destinatario:** cualquier prospecto (empresa o negocio), sin nombre: se manda después de un primer contacto o
  se deja tras una reunión. Voseo, como la landing y el agente comercial.
- **Objetivo:** que entienda qué hace Atentina, por qué canales, qué cuesta y cómo empezar, y que llame o escriba.
- **Formato:** A4, 3 hojas (tope 4). `make doc P=propuesta-atentina V=<n> HOJAS=4`.
- **Base:** estructura, componentes, diagrama y estilo de [`yoizen-propuesta` v1](../yoizen-propuesta/README.md).

## Estructura (v1)

1. **Overview:** h1 "Un agente que atiende a tus clientes por teléfono y por WhatsApp", cuatro cifras, lo que pasa
   hoy frente a lo que aporta Atentina, y el diagrama (canales → agente de Atentina → tu equipo).
2. **Qué incluye:** seis tarjetas (teléfono, WhatsApp, link para llamar, apps e integraciones, panel y API, campañas
   de llamadas como "próximamente"), cuatro usos y el bloque de inferencia propia y privacidad.
3. **Cómo trabajamos, planes y cómo empezar:** quién hace qué, los cuatro planes, cuatro pasos, nota de "hoy y
   próximamente" y el pie de contacto.

## Afirmaciones y de dónde salen

- **0,9 s y "9 de cada 10 respuestas en menos de 1,5 s":** 65 turnos de llamadas reales desde el 7-oct-2026
  (`call_logs.latency`, consulta de `marketing/VIDEOS.md`, leída el 21-oct-2026): mediana 0,93 s, 52 % < 1 s,
  95 % < 1,5 s, 100 % < 2 s.
- **41 voces, 28 femeninas y 13 masculinas:** `landing/src/data/site.ts` y `tts/finetune/voces.tsv`.
- **"4 en 1"**, no "100 % propio": la telefonía es de Anura; WhatsApp pasa por Meta.
- **Planes y precios:** `tiers.price_ars` (Free 0, Mostrador 29.000, Sucursal 99.000; leídos el 21-oct-2026) y
  `site.ts` (Red "a medida", USD aproximados, ítems). Pago con tarjeta por Mercado Pago o transferencia:
  `docs/SUSCRIPCIONES_PLAN.md` (ambos en producción). Sin permanencia: FAQ de `site.ts`.
- **WhatsApp (mensajes, notas de voz con respuesta en audio, llamadas, campañas de mensajes, ruteo por contacto):**
  AGENTS.md y `docs/WHATSAPP_PLAN.md` (fases 1, 4, 5 y 5.6 en producción).
- **Link para llamar:** `docs/LINK_LLAMADA_PLAN.md`, desplegado el 19-oct-2026.
- **Apps e integraciones:** `docs/APPS.md` (primer caso en producción desde el 12-oct-2026; el ejemplo del
  gimnasio no nombra al cliente).
- **Resumen por email:** AGENTS.md, desplegado el 20-oct-2026.
- **Saliente de a una por panel o API:** `POST /api/v1/calls` (`docs/LLAMADAS_SALIENTES_PLAN.md`, sección 2).
- **Privacidad:** inferencia propia (AGENTS.md); la API de motores no guarda textos ni audios (FAQ de `site.ts`).
- **Omitido a propósito:** capacidad en llamadas simultáneas (no hay CAP con Gemma), grabación de audio (apagada y
  la privacidad de la landing dice que no se graba), BYOK de LLM (UI sin desplegar y contradice "sin terceros de
  IA"), cortar y bloquear números (sin desplegar), webhooks (solo los de campañas, sin desplegar), "llamadas
  programadas" de los planes (dependen de las campañas de llamadas), alta del número de WhatsApp desde el panel
  (Embedded Signup sin aprobación de Meta).
- **Próximamente:** campañas de llamadas (implementadas, sin desplegar ni medir).
- **A validar:** que Laureano quiera "próximamente" para las campañas de llamadas; que se ofrezca conectar una
  central o SIP propia "con vos" (lo dice la landing).

## Versiones

| Versión | Fecha | Qué cambió | Estado |
|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 21-oct-2026 | Primera versión | borrador |
