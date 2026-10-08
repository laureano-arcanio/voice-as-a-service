# Plan de puesta en marcha y adquisición de clientes

Versión del 2-oct-2026 (la primera, del 26-sep, cerraba el foco en salientes). Se apoya en [`demanda-y-mercado-local.md`](demanda-y-mercado-local.md)
(mercado y competencia), [`../competencia/`](../competencia/) (Botmaker, Vapi),
[`../proveedores/anura-terminos-2026.md`](../proveedores/anura-terminos-2026.md) (telefonía) y la
capacidad medida en [`../capacity/`](../capacity/README.md). Cifras en USD al mayorista de
ARS 1.525.

## 0. Etapa actual: exploración (desde el 2-oct-2026)

El MVP está terminado (voz entrante y saliente, agentes por cliente, demo en la landing). **WhatsApp
(8-oct-2026), adelantado respecto de la hoja de ruta de abajo:** texto, notas de voz, campañas de
plantillas y llamadas por SIP en producción con el número de Atentina; que un cliente conecte su propio
número espera la aprobación de Meta (estado por parte en [`../WHATSAPP_PLAN.md`](../WHATSAPP_PLAN.md)).
Campañas salientes **de voz**, derivación a humano y grabación de llamadas: no implementadas. Esta etapa es un **piloto comercial para descubrir quién paga y por
qué**, no para ejecutar un foco ya elegido.

- Los casos de uso de las secciones 2 y 3 son **hipótesis de partida**, no un límite. Se habla con
  cualquiera que tenga volumen de llamadas o de WhatsApp: entrante, saliente, interno, el rubro
  que sea.
- Cada conversación busca aprender: qué problema tiene, cuánto volumen, cuánto le cuesta hoy, quién
  decide y si pagaría un piloto. Se registra con esos campos, aunque no termine en venta.
- No se construye para un caso hasta que aparece en **3 conversaciones** o hay **un piloto pago**
  que lo pide.
- **Salida de la etapa:** con ~30 conversaciones y 2 o 3 pilotos andando, elegir los 1 o 2
  segmentos con más señal (pagan, repiten, deciden rápido) y recién ahí cerrar el foco.

## 1. Tesis

- El mercado argentino de agentes de IA factura USD 30-50 M en 2026 (voz + texto) y la voz
  telefónica es USD 5-15 M. Es angosto, pero tiene tres nichos con clientes pagos: cobranzas,
  Estado y salud.
- La única ventaja defendible es estructural: con inferencia propia y terminación local se puede
  cobrar USD 0,08-0,15 por minuto, contra 0,19-0,26 que cuesta un agente propio y 0,31 que cobra
  un BPO. Los agentes de voz que se venden hoy en Argentina cobran 0,28-0,35: no ahorran.
- Por eso la hipótesis principal no es "Vapi barato" ni "bot para PyMEs": son **llamadas salientes con
  relación contractual y resultado medible** (cobranza de mora temprana, recordatorios y confirmaciones),
  vendidas al mercado medio y a municipios, a través de quienes ya les venden software.
- Los desarrolladores y las agencias son un canal, no el mercado.

## 2. Hipótesis de foco

Lo que la investigación de mercado señala como más probable. Se valida o se descarta en la etapa
de exploración (sección 0).

### 2.1 Caso de uso inicial

Un solo workflow, con variantes: llamar, identificar a la persona, informar (deuda, cuota,
turno), capturar un resultado (promesa de pago, confirmación, reprogramación) y derivar a un
humano cuando hace falta. Ya hay agentes de referencia de cobranza y turnos en `app/agents/reference/`.

| Variante | Quién la compra | Resultado que mide |
|---|---|---|
| Mora temprana (1 a 60 días) | Estudios de cobranza, cooperativas de crédito, mutuales, fintech chicas | Contactabilidad, promesas de pago, cobrado a 30 días |
| Cuotas y vencimientos | Prepagas regionales, colegios privados, cooperativas eléctricas y de agua, clubes | Cobro en término, llamadas por cobrador |
| Confirmación de turnos | Clínicas, centros de diagnóstico, consultorios grandes | Ausentismo (hoy ~30 %; con recordatorio 8-15 %) |
| Tasas y turnos municipales | Municipios de 20 a 200 mil habitantes | Recaudación, llamadas atendidas sin humano |

### 2.2 Por qué este caso y no otros

- Es el único de Argentina con clientes pagos y cifras públicas de voz con IA (Kleva, Inceptia,
  Onbotgo, Villa María, CABA).
- El comprador mide en pesos y el ROI se demuestra en una campaña de 30 días.
- No lo bloquea el No Llame (Ley 26.951 exceptúa la relación contractual vigente).
- La latencia pesa menos en un guion saliente corto que en atención entrante abierta. Nuestro
  piso medido es 1,66 s de p50; los globales están en 0,5-0,7 s.
- Los tres proveedores locales apuntan a bancos y telcos. El mercado medio está libre.

### 2.3 Dónde no invertir todavía

No es una lista de conversaciones prohibidas: si alguien de estos grupos tiene un problema concreto
y paga un piloto, se explora. Es dónde no poner tiempo de producto ni de prospección activa hasta
que haya señal.

- **Plataforma para desarrolladores como producto principal:** se compite en latencia, features
  y docs contra Vapi y Retell; ARPU bajo y rotación alta. Se ofrece como API mayorista a agencias
  cuando la plataforma esté estable.
- **PyMEs sueltas por venta directa:** ticket de USD 40-150 por mes y costo de adquisición alto.
  Solo a través de canales.
- **Bancos y telcos:** ya los atienden Infobip, Botmaker, Google, Microsoft y NICE.
- **Atención entrante abierta como bandera:** hasta bajar la latencia, la voz entrante se vende
  como complemento (desborde, fuera de horario) y no como reemplazo del centro de atención.

## 3. Propuesta de valor y precio

**Frase:** "Cobrá y confirmá por teléfono a un tercio de lo que cuesta una persona, con voces
argentinas y los datos en el país."

| Argumento | Dato |
|---|---|
| Precio | USD 0,08-0,15 por minuto todo incluido, contra 0,19-0,31 del humano y 0,28-0,35 de los agentes de voz locales |
| Voces | 41 voces argentinas propias, sin acento neutro ni proveedor externo |
| Datos | Inferencia en servidores propios en Argentina; nada sale a OpenAI, Google ni ElevenLabs. Pesa en Estado, salud y cobranzas (Ley 25.326) |
| Telefonía | Números locales y saliente a celulares a ~USD 0,016 el minuto (Twilio: 0,35) |
| Cumplimiento | Se presenta como asistente virtual, respeta horarios (CABA Ley 6171) y deriva a humano; lo que van a exigir los proyectos de ley de cobranzas e IA |

### Modelos de precio

1. **Por resultado (cobranzas):** por llamada atendida o por promesa de pago, con tope mensual.
   Es lo que el comprador de cobranzas ya entiende y ningún revendedor de Vapi puede seguir.
2. **Packs con base fija más minutos (recordatorios, turnos, entrante):** los de la
   [calculadora de costos](../calculadora-costos.html): Inicial, Pyme, Empresa, Corporativo. Son
   escenarios de costos; los planes publicados son los de la landing (Mostrador, Sucursal, Central y Red,
   `landing/src/data/site.ts`). La calculadora no está conectada a los tiers de la base.
   En PyMEs la base fija pesa más que los minutos.
3. **Mayorista para canales:** USD 0,10 por minuto o 20-30 % de comisión recurrente.

## 4. Producto mínimo para salir

Solo lo que necesita el caso de uso; el resto se posterga.

| Bloque | Qué hace falta | Estado |
|---|---|---|
| Campañas salientes | Carga por CSV o API, ventana horaria por provincia, reintentos, detección de contestador, prioridad | A construir sobre `POST /api/v1/calls` (ya con API keys por cliente y límites por tier) |
| Workflow | Identificación, guion por variante, captura de promesa o confirmación, derivación a humano, cierre | Base en `app/agents/reference/` |
| Cumplimiento | Presentación como asistente virtual, aviso de grabación, horarios, registro de contactos por deudor (1 por día, 2 por semana en CABA) | A construir |
| Reportes | Por campaña: contactados, resultado, promesas, minutos, costo por gestión; export CSV | A construir |
| Integración | Webhook de resultado y API para que el software del cliente cargue y lea | Parcial |
| Telefonía | Números de Anura a nuestro nombre, minutos de agente (no reventa de telefonía) | Listo; ver términos de Anura |
| Capacidad | Medida con el LLM anterior (Qwen3.5-9B): 22 llamadas simultáneas en CAP-002, ~32 en CAP-001 (~163.000 minutos por mes en horario comercial con 22). Con Gemma 4 26B, el LLM vigente desde el 6-oct-2026: **sin medir**, y va a ser menos | A medir |
| Calentamiento | El TTS tarda más de 20 s en el primer pedido: calentar antes de cada campaña | Conocido |

Segundo trimestre: WhatsApp en el mismo agente (texto y Calling API), que es donde el cliente de
cobranzas sigue la conversación y la voz saliente más barata (~USD 0,011 por minuto).

## 5. Clientes de diseño (pilotos)

Objetivo: **3 pilotos pagos** en 90 días, idealmente de segmentos distintos para comparar. Los de
la sección 2.1 son los candidatos naturales, pero vale cualquier caso con un problema medible y
alguien que lo pague; el piloto es también la forma de probar un caso nuevo.

| Condición | Detalle |
|---|---|
| Duración | 30 a 60 días |
| Alcance | Una campaña acotada: 2.000 deudores de mora temprana, o 3.000 turnos por mes |
| Precio | Fijo y bajo (cubre telefonía y horas); no gratis, para que el cliente lo mida |
| Línea de base | El cliente entrega su contactabilidad, promesas o ausentismo actuales antes de empezar |
| Métricas | Contactabilidad, resultado por llamada, costo por gestión efectiva contra su costo actual |
| Contrapartida | Si funciona, contrato anual y caso público con números |

El caso público es el activo comercial del primer año: hoy no existe ningún caso privado
argentino con cifras de llamadas automatizadas por IA. El primero que lo publique tiene el
argumento del sector.

## 6. Adquisición de clientes

### 6.1 Red propia (semanas 1 a 4)

- Listar contactos en estudios contables, cooperativas, clínicas, municipios, empresas de
  software y cualquier empresa con mucha atención por teléfono o WhatsApp. Un contador atiende diez PyMEs con problemas de cobranza; un proveedor de sistemas,
  cien.
- Pedir presentaciones, no ventas: "¿me presentás a alguien que haga muchas llamadas o atienda
  mucho por teléfono o WhatsApp?".
- Embudo esperado para 3 pilotos: ~150 contactos, ~30 conversaciones calificadas, ~8 propuestas.

### 6.2 Listas por segmento

| Segmento | Dónde está la lista | A quién buscar |
|---|---|---|
| Estudios de cobranza | ADPRA (cámara del sector); LinkedIn "cobranzas" y "recupero" en Argentina; los estudios que aparecen en denuncias de Defensa del Consumidor (los que más llaman) | Socio o gerente de operaciones |
| Cooperativas y mutuales de crédito | Padrón público del INAES, por provincia y rubro | Gerente o tesorero |
| Cooperativas eléctricas y de agua | FACE, FEDECOBA y federaciones provinciales; más de 500 con cobro mensual a socios | Gerente administrativo |
| Colegios privados | AIEPA y asociaciones provinciales; el cobro de cuotas es su dolor mensual | Administrador o representante legal |
| Clínicas y centros de diagnóstico | ADECRA y CEDIM (más de 420 socios); padrón de prestadores de la Superintendencia | Gerente de turnos o administración |
| Prepagas regionales | Registro de la Superintendencia: 41 entidades, 27 fuera de las 14 grandes | Gerente de afiliaciones o cobranzas |
| Municipios | Listado por provincia; empezar por los de 20 a 200 mil habitantes con Secretaría de Modernización o de Hacienda | Secretario de Modernización, Hacienda o Gobierno |

### 6.3 Canales que multiplican (desde el mes 1, en paralelo)

| Canal | Por qué | Oferta |
|---|---|---|
| Proveedores de software vertical (cobranzas, turnos médicos, cooperativas de servicios, administración escolar, gestión municipal) | Tienen a los clientes, la base de datos y la deuda cargada; les falta la voz | Integración en su producto, 20-30 % recurrente o marca blanca |
| BPOs medianos (Córdoba, Chaco, Tucumán) | Pierden posiciones cada año y sus clientes piden automatizar | La IA con su marca; traen volumen desde el día uno |
| Agencias que revenden Vapi o Retell | Venden voz a PyMEs a USD 0,30 el minuto | Mayorista a 0,10 con voces argentinas y números locales |
| Anura (programa de partners) | Clientes PyME con telefonía instalada; quieren tráfico | Referidos cruzados; el lead ya tiene número |
| Cámaras y federaciones (ADPRA, FACE, ADECRA, jornadas de modernización municipal) | Una charla vale más que cien mails; el tema convoca solo | Charla con datos del informe y una demo en vivo |

### 6.4 Cómo se los contacta

- En esta etapa el mensaje abre una conversación, no vende un caso: "¿qué llamadas o mensajes
  hacen hoy a mano?" rinde más que ofrecer cobranza a quien no cobra por teléfono. El caso de
  uso sale de la charla.

- LinkedIn y correo. No llamadas en frío a personas: el No Llame alcanza a las líneas de
  particulares y la primera impresión de un producto de voz no debe ser una llamada no pedida.
- Mensaje corto con un número y una acción: "Confirmamos turnos o cobramos mora temprana por
  teléfono a un tercio de lo que cuesta una persona. ¿Querés que el agente te llame ahora?" con
  un link donde ponen su número y reciben la llamada en diez segundos. **La demo es la llamada.**
- Municipios: nota formal más contacto al secretario por LinkedIn; propuesta de piloto de 60 días
  como contratación directa (por debajo del monto de licitación), con Villa María como referencia
  de que un municipio ya lo hizo.

### 6.5 Material mínimo antes de salir

- Página con la demo por llamada y una calculadora pública "cuánto te cuesta cada llamada hoy"
  (la lógica ya está en la calculadora de costos).
- Una hoja por segmento: caso de uso, guion de ejemplo, resultado esperado y precio.
- El informe de mercado publicado: posiciona y trae consultas entrantes de quien ya está evaluando.
- Contrato de piloto de dos páginas y contrato anual.

### 6.6 Quién vende

- Meses 1 a 4: el fundador, con presentaciones de la red y las cámaras.
- Con dos casos con números: una persona de ventas a comisión para las listas de 6.2 y el alta de
  canales de 6.3. Los canales se pagan con porcentaje recurrente, no con sueldo.

## 7. Plan a 6 meses

| Mes | Producto | Comercial | Hito |
|---|---|---|---|
| 1 | Demo por llamada en la web (hecha); lo que pida el primer piloto | Lista de 150 contactos; primeras 20 conversaciones registradas; charla pedida en una cámara | Primeras hipótesis validadas o descartadas |
| 2 | Campañas salientes, cumplimiento y reportes si la saliente tiene señal; integración por webhook y CSV | 30 conversaciones; 8 propuestas; primer piloto firmado | Primer piloto en marcha |
| 3 | Ajustes del piloto; reportes por campaña | 3 pilotos firmados; acuerdo con un proveedor de software o un BPO | 3 pilotos en marcha |
| 4 | Resultados medidos; correcciones | Primer piloto a contrato anual; caso escrito | Primer caso con números publicado |
| 5 | WhatsApp texto en el mismo agente | Vendedor a comisión; 2 canales activos | 5 clientes pagos |
| 6 | WhatsApp Calling; API mayorista para agencias | Charla en cámara con el caso; primeros leads de canal | 8-10 clientes; segundo servidor si hace falta |

## 8. Métricas de seguimiento

| Métrica | Objetivo a 6 meses |
|---|---|
| Conversaciones registradas (etapa de exploración) | 30 en 60 días, de al menos 5 rubros |
| Casos de uso que aparecen en 3 o más conversaciones | Los que haya: definen el foco |
| Conversaciones calificadas por mes | 30 |
| Propuestas por mes | 8 |
| Pilotos firmados | 3 en 90 días |
| Conversión piloto a contrato | 2 de 3 |
| Clientes pagos | 8-10 |
| Minutos vendidos por mes | 50-100 mil (30-60 % de un servidor) |
| Ingreso mensual | USD 8-15 k |
| Costo por gestión efectiva en pilotos | 40-60 % menos que el del cliente |
| Casos públicos con números | 1 |

Referencia: un objetivo a tres años de USD 0,5-1,5 M por año son 6-25 servidores como el de
CAP-002 vendiendo el 30 % de su capacidad. El cuello es comercial, no de hardware.

## 9. Riesgos y supuestos

| Riesgo | Mitigación |
|---|---|
| Los pilotos no muestran ahorro porque el guion o la voz no convencen | Medir contactabilidad y resultado por llamada desde la primera semana; iterar guion y voz con el cliente; elegir mora temprana, donde el IVR ya funciona mal |
| Regulación de cobranzas (CABA, proyecto nacional) limita frecuencia y exige presentación como IA | Ya está en el diseño; convertirlo en argumento de venta contra estudios que hostigan |
| Un competidor local baja el precio | Su costo es Vapi más Twilio; no pueden bajar de ~0,20 sin perder. La inferencia propia es la barrera |
| Anura lee el modelo como reventa | Vender minutos de agente sobre números propios; entrar por su programa de partners y dejarlo por escrito |
| Latencia de 1,66 s de p50 en atención entrante | No venderla como bandera hasta bajarla; el saliente corto la tolera |
| Caída del TTS con sobrecarga (más de 100 llamadas) | Tope de concurrencia por servidor y calentamiento antes de cada campaña |
| Ventas lentas en municipios | No depender de ellos en los primeros 90 días; cobranzas y cooperativas deciden más rápido |

## 10. Decisiones abiertas

- Precio por resultado: definir el valor por llamada atendida y por promesa para cada variante.
- Marca y posicionamiento público (nombre, sitio, caso de uso en la portada).
- Hardware de producción y ubicación: propuesta en [`../PRODUCCION.md`](../PRODUCCION.md) (este server, con redundancia al primer cliente); falta quién opera el servicio 24×7.
- Términos de canal (comisión, exclusividad por vertical, marca blanca).
