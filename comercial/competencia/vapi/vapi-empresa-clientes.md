# Vapi: empresa, producto, clientes y posicionamiento

Relevado el 26-sep-2026 de vapi.ai, docs.vapi.ai, prensa (TechCrunch, GlobeNewswire, Forbes) y reseñas de terceros. Las comparativas citadas son de competidores (Retell, Bland, Quiq) y están sesgadas.

## Empresa

- Sede en San Francisco. Fundadores Jordan Dearsley (CEO) y Nikhil Gupta (CTO). Nació como Superpowered (YC W21, notas de reuniones) y pivoteó a Vapi en nov-2023.
- Financiación total USD 72M: seed USD 2,1M; serie A USD 20M (dic-2024, Bessemer); serie B USD 50M (may-2026, Peak XV, con M12 de Microsoft, Kleiner Perkins, Bessemer, YC). Valuación ~USD 500M post-money.
- Ingresos: ARR "de ocho dígitos" según TechCrunch, con ingresos enterprise ×10 en un año. Estimaciones no oficiales: USD 8M en 2025.
- ~100 empleados (may-2026).
- Hitos: 1.000 millones de llamadas acumuladas, 1 a 5 millones por día, más de 1M de desarrolladores registrados, 2,5M de agentes creados. Amazon Ring migró el 100 % de sus llamadas entrantes a Vapi tras evaluar más de 40 proveedores.

## Producto y tecnología

- **Qué es:** orquestador STT → LLM → TTS con telefonía, developer-first. El cliente elige proveedor por etapa y puede traer los suyos (ver [`vapi-canales-integracion.md`](vapi-canales-integracion.md)).
- **Modelos propios:** no tiene LLM ni STT propios. Sí un TTS propio (Vapi Voices, USD 0,0025/min en beta) y un modelo de endpointing propio (fusión de audio y texto para detectar el fin de turno).
- **Latencia:** publica "menos de 500 ms promedio" en la home y "sub-600 ms" en docs. Coval (reseña independiente) mide 500 a 700 ms voz a voz. Un benchmark de Cekura que publica Retell da 3,08 s de respuesta media y 17 % de llamadas que no conectaron. Usuarios reportan 800 a 1.000 ms típicos con picos de 4 a 5 s y degradación con concurrencia alta.
- **Funciones:** Assistants, Squads (multiagente con handoff), Composer (arma agentes desde lenguaje natural), Evals (dic-2025, con CLI para CI), Simulations (llamador de IA con personas y escenarios), Monitoring (parte solo Enterprise), versionado, A/B, logs, alertas.
- **Compliance:** SOC 2 Type II, SOC 3, HIPAA con BAA (USD 2.000/mes), PCI, GDPR. Sin ISO 27001 publicada.
- **Regiones:** nube en EE. UU.; región UE cerrada a nuevos self-service. On-prem solo Enterprise, en la VPC del cliente vía AWS Marketplace, reportando uso a Vapi.
- **Idiomas:** "más de 100", según proveedor. Español disponible por los proveedores (Deepgram multi, Azure, ElevenLabs); la calidad depende del proveedor, no de Vapi. Sin sitio, docs ni soporte en español.
- **Escala publicada:** 62M+ llamadas por mes en enterprise, 99,9 % de uptime en Premier; Instawork 1M+ minutos por mes; Fleetworks 10k+ llamadas por día.

## Base de clientes y segmento

- **Segmento:** infraestructura para desarrolladores ("el Twilio de la voz"), con giro a enterprise desde 2025 (equipo forward-deployed, SSO, RBAC, SLA). Cola larga de más de 1M de devs, startups y agencias; los ingresos crecen por enterprise.
- **Logos:** Amazon Ring, Intuit, ServiceTitan, New York Life, Kavak, GoHealth, Instawork, UnityAI, Cherry, Spring Venture Group, Fleetworks, Ancile, Mindtickle, Luma Health, Ellipsis Health.
- **Verticales:** contact center (Ring), seguros y Medicare (Spring Venture: +25 % de conversión, 4 ingenieros operan 50 agentes), salud, reclutamiento, logística, automotriz, fintech y cobranzas.
- **LATAM y español:** el caso insignia es Kavak (México, Brasil, Argentina, Chile): ventas, agenda de inspecciones, financiación y posventa, con +200 % de ingresos y +30 % de conversión publicados. Sin oficina ni partners en LATAM.
- **Canales de venta:** self-service con tarjeta, ventas enterprise, programa de partners (consultoras, integradores, agencias). Sin white-label ni subcuentas nativas: las agencias revenden con wrappers de terceros.

## Punto fuerte y punto débil

**Punto fuerte: flexibilidad de infraestructura a escala telefónica probada.** Cualquier STT, LLM o TTS por etapa, intercambiables por llamada, con custom LLM, custom STT y custom TTS; SIP trunk propio gratis; SDKs para todo; evals y simulaciones nativas; compliance completo; y el caso Ring como prueba de escala. El precio de plataforma es bajo si el cliente controla el stack. La comunidad de desarrolladores es la más grande del segmento.

**Punto débil: fiabilidad y opacidad.** Quejas recurrentes en G2, Trustpilot y Reddit: latencia variable e impredecible (de 800 ms a 5 s sin cambios del cliente), bugs y breaking changes que tumban agentes en producción (el retiro de Workflows obligó a reconstruir agentes y hubo migraciones a Retell), soporte lento en self-service, precio "oculto" por la suma de pass-throughs, curva técnica alta. G2 ~4,2 con pocas reseñas; Trustpilot ~2,6.

## Competidores que nombran

- **Retell:** low-code, mejor latencia y fiabilidad por defecto en benchmarks propios, 20 líneas incluidas, HIPAA sin cargo, G2 4,8. Vapi responde con "control por componentes para equipos de ingeniería".
- **Bland:** stack propio sin terceros, menos de 500 ms, bundle USD 500 a 1.500/mes, outbound de alto volumen.
- **ElevenLabs Agents:** mejor voz y multilingüe, telefonía menos madura; en la práctica es el TTS dentro de Vapi.
- Sierra, Decagon, PolyAI en CX enterprise; Synthflow, Voiceflow, Thoughtly en low-code.

## Comparación con Botmaker y con este proyecto

| | Vapi | Botmaker Callbots | Este proyecto |
|---|---|---|---|
| Núcleo | Voz, developer-first | Chat y WhatsApp, voz agregada en 2025 | Voz telefónica con inferencia propia |
| Inferencia | Terceros, elegibles, más TTS propio | Terceros (Gemini, OpenAI) | Propia (Qwen3.5-9B, Parakeet, Qwen3-TTS fine-tuneado) |
| Telefonía | SIP propio gratis, Twilio, Telnyx, Vonage, números EE. UU. | Líneas por país, SIP empresarial, WhatsApp Calling | SIP (Asterisk) y LiveKit |
| Mensajería | Chat de texto y SMS EE. UU.; sin WhatsApp | 18 canales, WhatsApp BSP | No |
| Latencia publicada | 500 a 700 ms (independiente); hasta 5 s en quejas | No publica | Medida por test de capacidad (CAP-002) |
| Costo | USD 0,05/min + modelos, ~0,08 a 0,13/min | USD 0,07 por llamada hasta 2 min, 0,30 hasta 60 | Fijo por servidor |
| Datos | Nube EE. UU.; on-prem solo Enterprise | Nube | On-prem por diseño |
| Español y LATAM | Vía proveedores, sin presencia local | Nativo, Argentina y Brasil | Nativo, voces argentinas propias |

**Implicancia.** Vapi es la referencia técnica del segmento y el punto de comparación en latencia y flexibilidad. Lo que no ofrece a un cliente self-service: datos en su propia infraestructura, costo fijo, latencia estable bajo carga, ni voces en español rioplatense. Sus interfaces de custom LLM, STT y TTS son compatibles con lo que este stack ya expone, así que la inferencia de acá podría venderse como proveedor dentro de Vapi.

## Fuentes

- https://vapi.ai · https://vapi.ai/enterprise · https://vapi.ai/customers · https://vapi.ai/customers/kavak · https://vapi.ai/partnerships · https://security.vapi.ai/
- https://vapi.ai/blog/series-b · https://vapi.ai/blog/vapi-secures-20m-to-start-the-voice-revolution-2 · https://vapi.ai/blog/launching-testing-suites
- https://docs.vapi.ai/customization/multilingual · https://docs.vapi.ai/security-and-privacy/hipaa · https://docs.vapi.ai/security-and-privacy/data-flow · https://docs.vapi.ai/observability/evals-advanced · https://docs.vapi.ai/enterprise/plans
- https://techcrunch.com/2026/05/12/vapi-hits-500m-valuation-as-amazon-ring-chose-its-ai-platform-over-40-rivals/ · https://techcrunch.com/2023/11/10/yc-backed-productivity-app-superpowered-pivots-to-become-a-voice-api-platform-for-bots
- https://www.globenewswire.com/news-release/2024/12/12/2996317/0/en/Vapi-Dials-in-20M-in-Series-A-Led-by-Bessemer-to-Bring-AI-Voice-Agents-to-Enterprise.html · https://www.globenewswire.com/news-release/2026/05/12/3292882/0/en/vapi-raises-50m-series-b-as-it-reaches-1-billion-calls-powering-the-next-generation-of-enterprise-voice-ai.html
- https://www.ycombinator.com/companies/vapi · https://www.crunchbase.com/organization/vapi-97c4 · https://aws.amazon.com/marketplace/seller-profile?id=seller-qzlrzime7egtm
- Reseñas independientes: https://www.coval.ai/blog/vapi-review-2026-is-this-voice-ai-platform-right-for-your-project/ · https://www.g2.com/products/vapi-ai/reviews · https://ca.trustpilot.com/review/vapi.ai · https://vapi.ai/community/m/1369815265977700473
- Comparativas de competidores: https://www.retellai.com/blog/retell-vs-bland-vs-vapi-vs-elevenlabs · https://www.retellai.com/blog/vapi-ai-review · https://www.bland.ai/blog/vapi-vs-elevenlabs · https://quiq.com/blog/vapi-ai-review/
