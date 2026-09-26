# Vapi: precios y planes

Relevado el 26-sep-2026 de https://vapi.ai/pricing y docs.vapi.ai (billing). Valores en dólares. Vapi cobra por uso; los planes ("Success Packages") son opcionales y suman concurrencia, soporte y SLA, no minutos.

## Modelo de cobro

- **Plataforma (hosting): USD 0,05 por minuto** de llamada, prepago con créditos. Cubre la orquestación; no incluye STT, LLM, TTS ni telefonía.
- **Proveedores a costo, sin margen.** Con claves propias (BYOK) el proveedor factura directo y Vapi cobra igual el hosting.
- **Créditos gratis:** USD 5 al crear la cuenta (100 min de hosting). Con saldo cero y sin recarga automática, la cuenta se congela.
- **Granularidad del cobro** (segundo o minuto): no publicada.

## Planes

| | Usage only | Core | Pro | Premier |
|---|---|---|---|---|
| Precio mensual | USD 0 | USD 29 | 10 % del hosting, mínimo USD 999 | a medida |
| Llamadas concurrentes | 4 | 10 | 30 | a medida |
| Organizaciones | 2 | 2 | 10 | a medida |
| Números Vapi incluidos (solo EE. UU., solo entrantes) | 1 | 5 | 10 | a medida |
| Retención de datos crudos | 14 días | 30 días | 180 días | a medida |
| Soporte | Discord y email sin SLA | email, 2 días hábiles | email y Slack, 1 día hábil | equipo nombrado, P0 en 1 h |
| SLA de uptime | no | no | 99 % | 99,9 % |
| Otros | | ZDR | RBAC básico, ZDR | RBAC, SSO, SIP dedicado |

Add-ons en cualquier plan: línea concurrente extra USD 10 por mes; organización extra USD 20 por mes; HIPAA (BAA) USD 2.000 por mes por organización; retención extendida sin precio publicado. Descuentos por volumen "disponibles" sin números.

Programa para startups: 7.500 min gratis por mes durante 12 meses, para empresas de pre-seed a serie A con al menos USD 250k levantados. Aplicaciones en pausa al 26-sep-2026.

## Costos pasantes de proveedores (USD por minuto, rangos del calculador oficial)

| Componente | Proveedor | USD/min |
|---|---|---|
| STT | Deepgram (default) | 0,0095 a 0,0099 |
| STT | AssemblyAI | 0,0052 a 0,0075 |
| STT | OpenAI | 0,0118 a 0,0122 |
| LLM | OpenAI (default) | 0,0077 a 0,0452 |
| LLM | Anthropic | 0,0082 a 0,0366 |
| LLM | Google | 0,0060 a 0,0333 |
| TTS | ElevenLabs (default) | 0,0146 a 0,0238 |
| TTS | Vapi Voices (propias) | 0,0070 a 0,0193 |
| TTS | Cartesia | 0,0069 a 0,0129 |
| Telefonía | Vapi SIP, WebSocket, WebRTC | 0 |
| Telefonía | Twilio | 0,008 entrante, 0,014 saliente |
| Telefonía | Vonage | 0,0081 |
| Telefonía | Telnyx | 0,0055 |

STT se cobra sobre dos canales (cliente y asistente). El LLM se estima con 5 requests por turno y 50 % de cache hit.

## Llamada de 1 minuto con el stack por defecto

| Ítem | USD/min |
|---|---|
| Hosting Vapi | 0,050 |
| STT Deepgram | 0,010 |
| LLM OpenAI | 0,008 a 0,045 |
| TTS ElevenLabs | 0,015 a 0,024 |
| Telefonía Vapi SIP | 0 |
| **Total** | **0,082 a 0,129** |

Ejemplo oficial: 1.000 min por mes cuestan USD 82 a 129. Con Twilio saliente, USD 0,096 a 0,143 por minuto. Stack más barato del calculador (AssemblyAI, Google, Cartesia, SIP Vapi): ~USD 0,068 por minuto. Terceros miden USD 0,07 a 0,33 según stack y modelos.

## Incluido sin cargo aparte

Agentes ilimitados, evals y simulaciones, monitoreo, grabación, transcripción y análisis de llamadas (usa un LLM, costo no desglosado). Grabaciones exportables a S3, GCS, R2 o Supabase. ZDR con cualquier plan pago (excluyente con HIPAA).

## Lectura

- El precio de plataforma es bajo (USD 0,05/min) pero el total real es 2 a 3 veces eso, y depende de qué modelos elija el cliente. El costo se vuelve opaco: queja recurrente en reseñas.
- Contra Botmaker Callbots (USD 0,07 por llamada de hasta 2 min, USD 0,30 hasta 60 min): una llamada de 5 min cuesta USD 0,41 a 0,65 en Vapi y USD 0,30 en Botmaker, más el plan mensual de cada uno.
- Contra este proyecto: el costo por minuto de Vapi es variable y escala lineal con el uso; acá es fijo por servidor (ver [`../../capacity/calculadora-costos.html`](../../capacity/calculadora-costos.html)).

## No publicado

Granularidad del cobro, precio Premier, descuentos por volumen, precio de un número Vapi extra, retención extendida, tarifas por modelo individual, límites de la API.

## Fuentes

- https://vapi.ai/pricing
- https://vapi.ai/startups
- https://docs.vapi.ai/billing/pricing-and-success-packages
- https://docs.vapi.ai/billing/manage-packages-and-add-ons
- https://docs.vapi.ai/billing/manage-billing-and-credits
- https://docs.vapi.ai/billing/purchase-call-concurrency
- https://docs.vapi.ai/calls/call-concurrency
- https://docs.vapi.ai/assistants/model-intelligence/understanding-cost
- https://docs.vapi.ai/free-telephony
- https://docs.vapi.ai/customization/provider-keys
- https://docs.vapi.ai/security-and-privacy/hipaa
- https://docs.vapi.ai/faq
