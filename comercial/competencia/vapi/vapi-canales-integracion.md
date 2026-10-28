# Vapi: canales e integraciones y requisitos

Relevado el 26-sep-2026 de docs.vapi.ai. Vapi es una plataforma de voz: sus "canales" son telefonía, web y apps, y un chat de texto. No tiene los canales de mensajería de Botmaker (WhatsApp, Instagram, etc.).

## Telefonía

| Canal | Cómo se conecta | Requisitos y límites |
|---|---|---|
| Números gratis de Vapi | Se crean en el dashboard | 1 por cuenta sin tarjeta, 5 en Core, 10 en Pro. Solo códigos de área de EE. UU., solo entrantes y solo llamadas nacionales. Transporte sin cargo por minuto |
| Twilio importado | Número + Account SID + Auth Token | Único proveedor con SMS y con transferencias "warm". USD 0,008/min entrante, 0,014 saliente |
| Telnyx importado | Número + API key | Para salientes hay que crear un Outbound Voice Profile en Telnyx. Fuera de Norteamérica puede negociar PCMA y la integración espera PCMU (audio distorsionado); la alternativa es SIP trunk. USD 0,0055/min |
| Vonage importado | Número + credencial (API key y secret), solo por API | Sin guía dedicada. USD 0,0081/min |
| SIP trunk propio (BYO) | Credencial `byo-sip-trunk` + número `byo-phone-number`; guías para Twilio, Telnyx, Plivo, Zadarma, DIDWW, DIDlogic, Amazon Chime y custom | Gateway `sip.vapi.ai` (EE. UU., dos IPs fijas) o `sip.eu.vapi.ai` (UE, una IP). Señalización 5060 UDP/TCP o 5061 TLS; RTP UDP 40000 a 60000. Autenticación por IP o digest. SRTP opcional. Números en E.164. Sin cargo por minuto |
| SIP entrante sin PSTN | URI `{numero}@<credential_id>.sip.vapi.ai` | Sin registro ni autenticación; headers `x-*` llegan como variables |

- **Salientes:** `POST /call` con asistente, número y destinatario; lote con `customers[]`; programables con `schedulePlan`.
- **Campañas:** CSV o carga manual hasta 10.000 contactos, ventana horaria, concurrencia máxima propia, programables hasta 7 días, webhook previo al discado para filtrar, detección de contestador. La configuración queda fija al crearla.
- **Concurrencia:** 4, 10 o 30 líneas según plan, compartidas entre entrantes y salientes; USD 10 por línea extra por mes.
- **Países:** sin lista publicada. Regiones de plataforma EE. UU. y UE, aisladas entre sí; la UE está cerrada a nuevos clientes self-service.
- **Regulación:** guía TCPA para salientes; STIR/SHAKEN "requerido para EE. UU. y Canadá" y se tramita en Twilio Trust Hub (5 a 7 días hábiles); CNAM y reputación de número son pasos del cliente. 10DLC solo para SMS.

## Web y apps

- **Web SDK** `@vapi-ai/web`: WebRTC sobre Daily. Requiere public key (exponible) y assistant ID. Eventos de inicio y fin de llamada, habla, mensajes y errores. Tools del lado cliente sin resultado para el modelo.
- **Widget** `<vapi-widget>` en modo voz, chat o híbrido, por CDN o componente React, con temas y posición.
- **SDKs móviles:** iOS (Swift), Android (Kotlin, minSdk 21, usa Daily), React Native, Flutter, Python. Todos con public key.
- **SDKs de servidor:** TypeScript, Python, Java, Ruby, C#, Go. CLI y servidor MCP para agentes de código.

## Mensajería

- **Chat API** de texto (`POST /chat`): mismo asistente, streaming, modo compatible con OpenAI, sesiones de 24 h. Requiere método de pago cargado.
- **SMS:** solo con número Twilio de EE. UU. importado con SMS habilitado y 10DLC aprobado, tráfico EE. UU. a EE. UU. Solo el cliente inicia. Tool `sms` para mandar un texto durante la llamada.
- **WhatsApp:** no existe integración oficial. Solo por terceros (Make, n8n, Twilio) por fuera de Vapi.

## Herramientas e integraciones de negocio

- **Custom tools:** webhook con `toolCallList` y respuesta por `toolCallId`; modo asíncrono; autenticación Bearer, OAuth2 o HMAC. **API Request** genérico sin envoltorio (patrón recomendado para Make y n8n). Built-in: transferir, cortar, SMS, DTMF (RFC 2833), API request. IPs salientes fijas opcionales.
- **MCP:** tool `mcp` con URL y headers, transporte Streamable HTTP. Zapier solo por MCP; Make y n8n por API Request, MCP o webhook.
- **Nativas por OAuth:** GoHighLevel (contactos, disponibilidad, eventos), Google Calendar, Google Sheets (solo agregar filas), Slack (mensaje a canal). Sin HubSpot ni Salesforce nativos.
- **Transferencia a humano:** tool `transferCall` a E.164 o SIP URI. Blind por defecto, con resumen en header SIP (`refer`, `dial` o `bye`) solo en SIP. Cinco modos "warm" (mensaje, resumen, TwiML, esperar operador) solo sobre Twilio. Entre asistentes, `handoff`.
- **Knowledge bases:** archivos txt, pdf, docx, csv, md, json, xml y otros, recomendado menos de 300 KB; retrieval con Google/Gemini. `custom-knowledge-base` con servidor de búsqueda propio, solo por API.
- **Squads:** varios asistentes con handoff y paso de contexto. **Workflows** visuales: se retiran el 18-ago-2026.

## Proveedores de modelos y BYO

- **STT:** AssemblyAI, Azure, Cartesia, Deepgram, ElevenLabs, Gladia, Google, OpenAI, Soniox, Speechmatics, Talkscriber, xAI. **Custom transcriber** por WebSocket: PCM 16 bits a 16 kHz estéreo (canal cliente y asistente), respuestas parciales y finales.
- **LLM:** Anthropic (directo y Bedrock), Azure OpenAI, Cerebras, DeepInfra, DeepSeek, Google, Groq, Mistral, OpenAI, OpenRouter, Perplexity, Together, xAI y otros. **Custom LLM:** endpoint compatible con OpenAI (`/chat/completions` con SSE), autenticación por API key u OAuth2. Sirve para un vLLM propio si es público.
- **TTS:** Vapi Voices (21 voces propias, V2 con más de 40 idiomas), Azure, Cartesia, Deepgram, ElevenLabs, Hume, Inworld, LMNT, MiniMax, OpenAI, PlayHT, Rime, Sesame y otros. **Custom TTS:** POST con texto y sample rate (8, 16, 22,05 o 24 kHz), respuesta PCM crudo en chunks, con fallback a otras voces.
- **BYO keys** en Integrations; el proveedor factura directo. Grabaciones a S3, GCS, R2 o Supabase; observabilidad con Langfuse.
- **Self-hosted de la plataforma:** solo Enterprise, en la VPC del cliente vía AWS Marketplace; reporta uso a Vapi para facturación. No está en las docs públicas.

## Lectura para este proyecto

- Los tres puntos de extensión (custom LLM compatible con OpenAI, custom transcriber por WebSocket, custom TTS por POST con PCM) son casi lo mismo que expone este stack (`/llm`, `/stt`, `/tts` por el proxy). Un cliente de Vapi podría enchufar esta inferencia como proveedor, y este proyecto podría exponer esas interfaces.
- SIP trunk propio con IPs fijas y E.164: mismo modelo que Asterisk contra LiveKit acá.
- Sin WhatsApp ni mensajería: el terreno de Botmaker. Vapi es voz y teléfono.

## Fuentes

- https://docs.vapi.ai/llms.txt (índice)
- https://docs.vapi.ai/free-telephony · https://docs.vapi.ai/phone-calling · https://docs.vapi.ai/phone-numbers/import-twilio · https://docs.vapi.ai/telnyx · https://docs.vapi.ai/api-reference/phone-numbers/create
- https://docs.vapi.ai/advanced/sip · https://docs.vapi.ai/advanced/sip/sip-trunk · https://docs.vapi.ai/advanced/sip/sip-networking · https://docs.vapi.ai/security-and-privacy/eu-region · https://docs.vapi.ai/security-and-privacy/static-ip-addresses
- https://docs.vapi.ai/calls/outbound-calling · https://docs.vapi.ai/outbound-campaigns/overview · https://docs.vapi.ai/calls/call-concurrency · https://docs.vapi.ai/tcpa-consent
- https://docs.vapi.ai/sdk/web · https://docs.vapi.ai/chat/web-widget · https://github.com/VapiAI/web · https://github.com/VapiAI/client-sdk-android
- https://docs.vapi.ai/chat/quickstart · https://docs.vapi.ai/chat/sms-chat · https://docs.vapi.ai/phone-numbers/inbound-sms · https://docs.vapi.ai/tools/default-tools
- https://docs.vapi.ai/tools/custom-tools · https://docs.vapi.ai/tools/mcp · https://docs.vapi.ai/tools/integrations/make · https://docs.vapi.ai/tools/integrations/n8n · https://docs.vapi.ai/tools/go-high-level · https://docs.vapi.ai/tools/google-calendar · https://docs.vapi.ai/tools/slack
- https://docs.vapi.ai/tools/transfer-call · https://docs.vapi.ai/tools/transfer-call/warm-transfer · https://docs.vapi.ai/squads · https://docs.vapi.ai/workflows/legacy-migration
- https://docs.vapi.ai/knowledge-base · https://docs.vapi.ai/knowledge-base/custom-knowledge-base
- https://docs.vapi.ai/providers/transcriber/overview · https://docs.vapi.ai/providers/model/overview · https://docs.vapi.ai/providers/voice/overview · https://docs.vapi.ai/customization/custom-llm/using-your-server · https://docs.vapi.ai/customization/custom-voices/custom-tts · https://docs.vapi.ai/customization/custom-transcriber
