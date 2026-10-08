# Botmaker: Callbots (voz telefónica en tiempo real)

Relevado el 26-sep-2026 desde el centro de ayuda de Botmaker (help.botmaker.com, categoría "Callbots y WhatsApp Calling"), la página del producto y notas de prensa del lanzamiento. Es el producto comparable con este proyecto.

## Qué es

- Bot de voz con IA que atiende llamadas entrantes y hace salientes, por línea telefónica y por llamadas de WhatsApp Business. Lanzado el 22-ago-2025.
- Botmaker lo describe como "responde en tiempo real" y "respetando el ritmo del habla". Se diseña sin código en el mismo Botdesigner que los chatbots, con menús por teclado (IVR/DTMF) o lenguaje natural.
- Dos modos:
  - Flujo clásico: el bot no se deja interrumpir; empieza a escuchar después del mensaje inicial y del primer menú.
  - Agente de IA generativo: admite interrupción (barge-in), usa variables, acciones y bases de contenido. Se elige el modelo por agente; en prensa nombran "Lara, Gemini y OpenAI".
- Acciones en la llamada: transferir a un equipo o agente humano, cortar, enviar SMS o WhatsApp al número que llamó, música de espera.
- Un agente humano atiende una sola llamada a la vez por número de canal. Los equipos de atención se configuran para chatbots, mailbots y callbots.

## Canales de voz

| Canal | Cómo se conecta | Requisitos |
|---|---|---|
| Línea comprada en Botmaker | Canales > Líneas telefónicas, elegir país y número | Precio por país en Configuración > Cuenta > Productos y consumos; en Argentina piden prueba de posesión |
| Línea propia por SIP | Se piden datos de contacto y el equipo de Botmaker coordina parámetros y pruebas | Solo centrales o PBX con SIP; no admiten móviles ni líneas personales |
| WhatsApp Business Calling API | Canales > WhatsApp Business > "Llamadas habilitadas", asignar un Callbot | Número de WhatsApp Business con llamadas habilitadas; un Callbot por línea; el ícono de llamada aparece al instante para los usuarios |

- Llamadas salientes por WhatsApp: el usuario tiene que aceptar una plantilla de permiso (aprobada por Meta; la default tiene botones "No permitir", "Permitir temporalmente", "Permitir siempre"). El permiso temporal dura 6 días y hay tope de 5 intentos por día. No hay salientes automáticas sin ese permiso. Las salientes documentadas las inicia un agente desde una conversación activa.
- Una línea nueva se enruta al Callbot y a la cola por defecto hasta que se reasigna.
- Admiten llamadas internacionales.

## Costos

| Concepto | Precio |
|---|---|
| Llamada hasta 2 min (Botmaker, cualquier canal, entrante o saliente) | USD 0,07 |
| Llamada de 2 a 60 min | USD 0,30 |
| Más de 60 min | se cobra como dos llamadas de 60 |
| WhatsApp entrante (iniciada por el usuario) | sin cargo de Meta, solo el fijo de Botmaker |
| WhatsApp saliente (Meta, pulsos de 6 s; 1:01 se cobra como 1:06) | por minuto según país y volumen, ver tabla |

Tarifas de Meta por minuto en llamadas salientes de WhatsApp (de menor a mayor volumen):

| País | USD/min |
|---|---|
| Argentina | 0,0101 a 0,0046 |
| Chile | 0,0121 a 0,0055 |
| Colombia | 0,0111 a 0,0039 |
| México | 0,0094 a 0,0038 |
| Perú | 0,0121 a 0,0059 |

Estos costos van sobre el plan mensual (ver [`botmaker-precios-planes.md`](botmaker-precios-planes.md)). "Audio a texto" figura con 0 minutos incluidos en los tres planes, así que es un extra pago sin precio publicado.

## Lo que no documentan

- Proveedor de STT y TTS, voces e idiomas disponibles.
- Latencia medida y concurrencia máxima de llamadas.
- Grabación o transcripción de llamadas.
- Llamadas salientes automáticas por bot (campañas de voz): solo se documentan las iniciadas por un agente por WhatsApp, con permiso previo.
- Recomendaciones publicadas: flujos cortos y guiados, horarios de atención, avisar al usuario antes de llamar, probar con varios usuarios, música de espera liviana y libre de derechos.

## Comparación con este proyecto

- Mismo producto: STT, LLM y TTS sobre SIP o WhatsApp, con handoff a humanos y motor de flujos.
- Botmaker usa inferencia de terceros y cobra por llamada (USD 0,07 hasta 2 min, USD 0,30 hasta 60 min); acá la inferencia es propia y el costo es el hardware (ver [`../../calculadora-costos.html`](../../calculadora-costos.html)).
- Botmaker no publica latencia ni concurrencia; acá están medidas en [`../../capacity/`](../../capacity/README.md) (CAP-002: ~22 llamadas con p95 de espera ≤ 2,8 s por servidor).

## Punto fuerte y base de clientes

**Punto fuerte: WhatsApp.** Botmaker es Business Solution Provider oficial de Meta desde hace años y el producto está construido alrededor de eso: alta self-service del número, plantillas, notificaciones masivas, cobro por "conversación de 24 h" que calca el modelo de Meta, y Central.chat, que existe para esquivar el cobro por mensaje de Meta desde oct-2026. El resto de los 18 canales son OAuth con proveedores de terceros que cualquier competidor conecta igual, y varios no están documentados. Lo que vende es una bandeja única para WhatsApp con bots, agentes humanos y ahora voz, sin código, con precio de entrada bajo (USD 149) y presencia local en Argentina, Brasil, Colombia y México.

**Base de clientes: grandes marcas B2C de LATAM con alto volumen de atención.** Casos publicados: telcos (Movistar, Claro), bancos y fintech (Naranja X, Sicoob, Sicredi, MetLife), retail (Carrefour, Sodimac, Frávega, OXXO, Payless, Adidas), automotrices (Ford, Toyota, Volkswagen), viajes (Despegar, JetSmart, British Airways), consumo masivo (Mondelez, Nespresso, Molinos) y gobierno (Boti, Ciudad de Buenos Aires, 82 % de consultas resueltas sin humano). Empresas con call center propio y mucho tráfico entrante por WhatsApp, sobre todo en Argentina y Brasil. Dicen "miles de empresas" en más de 40 países; los planes de USD 149 a 499 son la puerta de entrada y los logos son cuentas Enterprise a medida.

**Implicancia para este proyecto.** Callbots es reciente (ago-2025) y es un agregado a una plataforma de chat, no su núcleo: no publican latencia, concurrencia, proveedor de voz ni grabación. Compiten de igual a igual solo en telefonía por SIP y por WhatsApp Calling. La diferencia defendible acá es lo que ellos no tienen: inferencia propia con latencia medida y costo por llamada que no escala con el uso.

Fuentes: https://botmaker.com/es/ (logos y sectores), https://botmaker.com/es/nuestros-clientes/todos-los-clientes/, https://botmaker.com/es/nosotros.

## Fuentes

- https://botmaker.com/es/plataforma/callbots/
- https://help.botmaker.com/es/help/935191477994746702 (índice Callbots y WhatsApp Calling)
- https://help.botmaker.com/es/help/5624682634600006528 (qué es Callbots)
- https://help.botmaker.com/es/help/7332603463511756292 (líneas telefónicas y SIP)
- https://help.botmaker.com/es/help/7317995494363787503 (WhatsApp Business Calling API)
- https://help.botmaker.com/es/help/6289341022228115541 (llamada saliente desde WhatsApp)
- https://help.botmaker.com/es/help/6236534031781092803 (acciones del Callbot)
- https://help.botmaker.com/es/help/6176937968607125961 (agentes de IA en Callbots)
- https://help.botmaker.com/es/help/6883093253609289451 (recomendaciones de uso)
- https://help.botmaker.com/es/help/7011303113786771165 (cobro y costos de llamadas)
- https://help.botmaker.com/es/help/9159703660773739063 (FAQ)
- https://mercado.com.ar/ruta-digital/botmaker-lanza-callbots-con-ia-para-atencion-por-voz-en-whatsapp/
- https://inversorlatam.com/botmaker-llamadas-de-voz-con-ia-por-telefono-y-whatsapp/
