# Demanda de agentes de IA de voz y texto: mundo y Argentina (sep-2026)

Relevado el 26-sep-2026 con búsquedas web (cuatro barridos: mercado global, Argentina,
oferta local y regulación/costos de canal). Notas crudas con todas las fuentes en
`scratch/mercado/` (no versionado). Tipo de cambio: mayorista ARS 1.525/USD.
Complementa [`../competencia/`](../competencia/) (Botmaker, Vapi) y
[`../proveedores/anura-terminos-2026.md`](../proveedores/anura-terminos-2026.md).

Calidad de las fuentes: **A** primaria (Meta, SEC, Gartner, ENACOM, CACC, Ministerio de
Trabajo), **B** prensa especializada, **C** consultoras de reportes en serie o blogs de
proveedores (solo orden de magnitud; difieren ×2-3 entre sí). Lo marcado **est.** es cálculo
propio con los supuestos explícitos.

## 1. Resumen

- **Mundo:** el mercado directo de agentes de voz con IA es chico todavía (USD 2,3-2,5 mil M en
  2025, fuentes C, creciendo ~40 % anual) frente a lo que sustituye: 17 M de agentes humanos y
  USD 100-120 mil M solo en outsourcing. La demanda real medida hoy: ~100-150 M de llamadas IA por
  mes entre Vapi y Retell, 10 M de conversaciones IA por semana en WhatsApp/Messenger (Meta), y
  ~USD 1,3 mil M de ARR sumando las diez plataformas líderes. Solo 5 % de los líderes de servicio
  tenía voicebots generativos en producción a fines de 2024 y solo 20 % reporta reducción de
  plantilla por IA (Gartner, 2025).
- **Argentina, demanda real:** la voz con IA tiene clientes pagos en tres nichos: **cobranzas**
  (Kleva, Inceptia, Onbotgo, Vozy: bancos, fintech, DirecTV, Ualá), **gobierno** (CABA línea 147
  por ~USD 2 M, Villa María, Zárate, Mendoza) y **PyMEs por agencias** (ContactShip, Anunzi,
  Tec5: USD 30-800 por mes). En banca y telcos la automatización con IA generativa ya resuelve
  ~60 % de consultas, pero por **WhatsApp**, no por teléfono. No hay ningún caso público 2025-26
  de empresa privada argentina con cifras de llamadas telefónicas automatizadas por IA.
- **Tamaño del mercado local (est.):**

  | | 2026 | 2029 |
  |---|---|---|
  | Gasto en atención humana sustituible (mercado interno) | USD 1,5-2,2 mil M por año | — |
  | Plataformas de agentes IA, voz + texto, facturación en Argentina | **USD 30-50 M** | **USD 70-200 M** (central ~120) |
  | De eso, voz telefónica con IA | **USD 5-15 M** | **USD 30-60 M** |

- **Canal:** WhatsApp domina (93-99 % de penetración; 84 % de los argentinos habla con marcas por
  WhatsApp y 8 de 10 lo prefiere al teléfono). La voz móvil cae 20 % por año (78,7 → 39,4 mil M de
  minutos entre 2019 y 2025, ENACOM) y el SMS quedó como canal de notificación (2,7 mil M por año,
  todo OTP y avisos). La voz queda para cobranzas, urgencias, mayores, salud y organismos públicos,
  y cada vez más **dentro de WhatsApp** (Calling API, saliente ~USD 0,011 por minuto).
- **Precio:** un agente propio cuesta USD 0,19 por minuto de conversación (salario CCT 781/20
  de ARS 992 k más cargas, sobre 156 h pagadas, 77 % productivas y 70 % de ocupación) y ~0,26
  con puesto y supervisión; comprado a un BPO, USD 0,31 por minuto productivo (precio de venta
  CACC, sep-2026). Los agentes de voz llave en mano que se venden en Argentina cobran USD 0,28-0,35
  por minuto: **cuestan lo mismo que un BPO y más que un empleado propio**. Las plataformas
  globales salen USD 0,08-0,15 por minuto más telefonía, pero a celulares argentinos Twilio cobra
  USD 0,35 por minuto. El espacio para inferencia propia con terminación local (Anura ~USD 0,016)
  es cobrar USD 0,08-0,15 todo incluido: 1,5 a 3 veces más barato que un agente propio y 2 a 4
  veces que un BPO. Ver 3.1.

## 2. Mundo: demanda real

### 2.1 Tamaño y adopción

| Dato | Valor | Fuente | Cal. |
|---|---|---|---|
| Agentes de voz IA | USD 2,3-2,5 mil M (2025) → 27-35 mil M (2032-33), CAGR 39-42 % | Grand View, MarketsandMarkets | C |
| IA conversacional (voz + texto) | USD 14-17 mil M (2025), CAGR 20-24 %; servicios de software > USD 32 mil M en 2028 (IDC, CAGR 40 %) | Grand View, M&M, IDC | C / A |
| CRM Customer Service & Support (incl. CCaaS) | USD 43 mil M (2024), +13,7 % | Gartner Market Share | A |
| Outsourcing de contact centers | USD 103-120 mil M (2025); ~17 M de agentes humanos, mano de obra hasta 95 % del costo | Grand View; Gartner | C / A |
| CPaaS | USD 30 mil M (2025) → 34 mil M (2026); SMS > 50 % del ingreso; tráfico A2P SMS en baja (1,9 T 2023 → < 1,5 T 2029) | Juniper | A |
| Mensajería OTT de negocios (WhatsApp y otros) | 390 mil M de mensajes (2025) → 560 mil M (2027); USD 3,6 → 9,8 mil M (2029) | Juniper | A |
| Voicebots generativos en producción | 5 % desplegado, 11 % piloto, 44 % explorando (n=187) | Gartner, dic-2024 | A |
| Contact centers con IA generativa desplegada | 1 de 6 (n=600) | Deloitte, 2024 | A |
| Interacciones automatizadas | 10 % en 2026 (vs 1,6 % en 2022); Gartner predice 80 % de problemas comunes sin humano en 2029 | Gartner | A |
| Reducción real de plantilla por IA | solo 20 % la reporta; 55 % mantiene plantilla con más volumen (n=321); 50 % de los que recortaron recontratará para 2027 | Gartner, dic-2025 / feb-2026 | A |
| Presión por implementar IA | 91 % de los líderes de servicio | Gartner, feb-2026 | A |
| Gasto enterprise en IA generativa | USD 37 mil M (2025, ×3); 76 % comprado, no construido | Menlo Ventures | A |

### 2.2 Señales de mercado privado

| Empresa | ARR | Valuación / ronda | Volumen |
|---|---|---|---|
| ElevenLabs | USD 600 M (jun-26); enterprise 51 % | USD 11 mil M | Revolut, Klarna |
| Sierra (texto y voz enterprise) | USD 150 M (feb-26) | USD 15 mil M, Serie E 950 M (may-26) | precio por resolución ~USD 1-2,5 |
| Decagon | ~USD 100 M (jul-26 est.) | USD 4,5 mil M | contratos USD 105-923 k por año |
| Cresta | > USD 100 M (abr-26) | — | — |
| Retell | USD 60 M (jun-26, ×6 en un año, 30 empleados) | ~USD 5 M levantados | 55 M llamadas/mes |
| Vapi | "8 dígitos" | USD 500 M, Serie B 50 M (may-26) | 62 M llamadas/mes; Amazon Ring |
| Parloa | USD 52 M (2025 est.) | USD 3 mil M (ene-26) | — |
| PolyAI | USD 40 M (2025 est.) | USD 750 M | — |
| Cognigy | ~USD 38 M | comprada por NICE, USD 955 M (sep-25) | — |
| Gupshup | — | — | 500 M llamadas/mes; voz IA self-serve USD 0,035/min (sep-26) |
| NICE / Genesys / Five9 | IA: USD 362 M / > 400 M / > 150 M de ARR, +66 a +78 % | — | IA en 100 % de los deals de NICE |
| Meta (WhatsApp pago) | ingreso "otros" USD 1,0 mil M por trimestre (Q2-26, +73 %); run-rate USD 2 mil M a fin de 2025 | — | 10 M conversaciones IA/semana; > 1 M negocios usan Meta Business Agent |

Fuentes: TechCrunch, Bloomberg, Axios, Sacra, SEC (10-Q de Meta, 6-K de NICE), blogs de las
empresas. Lectura: el dinero va a plataformas de **texto y voz enterprise** (Sierra, Decagon,
Cresta) y a **infraestructura de voz para desarrolladores** (ElevenLabs, Vapi, Retell). Los
incumbentes de contact center convierten su base instalada a IA a +60-80 % anual.

### 2.3 Precios de referencia (USD por minuto)

| Oferta | USD/min | Nota |
|---|---|---|
| Plataforma sola (BYOK) | Vapi 0,05; Retell 0,07; Twilio ConversationRelay 0,07; Gupshup 0,035 | sin STT, LLM, TTS ni telefonía |
| Todo incluido | 0,08-0,15 básico; 0,25-0,33 premium; ElevenLabs Agents 0,08-0,24; Bland 0,11-0,14 | telefonía EE. UU. ~0,013 por pata |
| Texto por resultado | Sierra ~1-2,5 por resolución; Decagon ~0,99 por conversación | enterprise |
| Referencia humana | USD 6-8 por interacción; teléfono 17-25 | SQM/Forrester vía blogs (C) |

## 3. Argentina: base de datos

### 3.1 Lo que se sustituye: atención humana

| Dato | Valor | Fuente | Cal. |
|---|---|---|---|
| Puestos en contact centers tercerizados | ~50.000 (pico 75.000 en 2008; −3.000 por año); Córdoba 38 %, CABA+PBA 27 %, Tucumán 14 %, Chaco 13 % | CACC, El Economista, Perfil | A/B |
| Ocupación "operador telefónico" registrada | 23.051 (2022, 0,4 % del empleo registrado) | Min. Trabajo (OOA) | A |
| Agentes in-house (bancos, telcos, prepagas, retail) | **no publicado**; est. 35-55 k por el ratio mundial de Gartner (17 M / 8.000 M hab. → 98 k totales en Argentina) | est. | — |
| Exportación del sector | **no publicado**; señal: carga impositiva 50 % vs 30 % regional, licitaciones se van a Paraguay/Perú/Colombia | El Economista | B |
| Precio de venta estándar de un BPO (CACC) | hora productiva ARS 28.217 = **USD 18,5 = 0,31 por minuto productivo**; hora login 23.538 (sep-2026; ene-2025: 19.212). Es precio neto sin IVA e incluye infraestructura, indirectos, impuestos y rentabilidad | CACC, Sistema de Costos | A |
| Posición full time comprada a un BPO (156 h) | ≈ ARS 4,4 M ≈ **USD 2.900 por mes** | est. sobre CACC | — |
| Salario de un operador (CCT 781/20, Operación A, 36 h, ago-2026) | **ARS 992.227** brutos (incluye ARS 25 k no remunerativos); Operación B 1.007.234; + presentismo 8,33 % y 1 % por año de antigüedad. Salario mínimo de sep-2026: ARS 383.800 | FAECYS-CACC vía El Destape, iProfesional; Res. 4/2026 | A/B |
| Costo empresa de ese operador | ≈ **ARS 1,5 M ≈ USD 985 por mes**: bruto 1,07 M + contribuciones patronales y ART ~30 % + SAC | est. sobre la escala | — |
| Mercado de outsourcing de contact center | USD 1.405 M (2024) → 2.418 M (2030) | Grand View | C |
| Volumen de llamadas del sector | **no publicado**; Konecta Argentina > 25 M contactos/año (2020) | Cronista | B |

**Cuánto cuesta un minuto humano (est., sep-2026, ARS 1.525/USD).** El minuto de IA se paga solo
mientras hay conversación, así que la comparación correcta es por minuto de conversación.

| Escalón | Cálculo | ARS/min | USD/min |
|---|---|---|---|
| Costo empresa por minuto pagado | ARS 1,5 M / (156 h × 60) | 160 | 0,105 |
| Por minuto productivo | pagado / 77 % (pausas, capacitación, ausentismo) | 208 | 0,14 |
| **Por minuto de conversación, agente propio** | productivo / 70 % de ocupación | **297** | **0,19** |
| Agente propio con puesto, supervisión, software y telefonía | × 1,35 | ~400 | ~0,26 |
| **Comprado a un BPO, por minuto productivo** | precio CACC 28.217 / 60 | **470** | **0,31** |
| Comprado a un BPO, por minuto de conversación | / 70 % de ocupación | 672 | 0,44 |

El precio del BPO es 2,3 veces el costo laboral por hora productiva, lo normal en la industria
(la mano de obra es 45-55 % del precio). Un agente de IA a USD 0,08-0,15 por minuto de
conversación es 1,3-2,4 veces más barato que el costo laboral puro, 1,8-3,3 veces que un agente
propio con sus costos de puesto y 2-4 veces que un BPO.

### 3.2 Base de empresas

| Segmento | Cantidad | Fuente |
|---|---|---|
| Empresas empleadoras formales | 525.538 (abr-2025): < 10 empleados 84 % (~441 k); 10-50: 13 % (~68 k); 51-100: 2 % (~10,5 k); > 100: 9.939 | UCEMA sobre OEDE/ARCA |
| Bancos | 78 entidades | BCRA |
| Fintech | 1.027 empresas, > 40.000 empleados | CAF, nov-2025 |
| Seguros | 189 aseguradoras, ~50.000 productores | SSN |
| Prepagas | 41 registradas; 14 concentran 90 % de 6,8 M de afiliados (OSDE 2,1 M, Swiss 1,0 M, Galeno 0,75 M) | SSN, 2026 |
| Clínicas y sanatorios privados con internación | 1.543 (ADECRA+CEDIM agrupan > 420) | La Nación, ADECRA |
| Licenciatarios de telecomunicaciones | 4.720 CUIT (2.299 ISP) | ENACOM, padrón |
| Comercio electrónico | 2.400 socios CACE; 25,1 M compradores; ARS 35,3 billones (2025) | CACE |
| Educación privada | ~17.000 instituciones | AIEPA |
| Gastronomía | ~40.000 restaurantes | FEHGRA |
| Inmobiliarias, concesionarias, estudios de cobranza, utilities | **sin conteo confiable** | — |

### 3.3 Canales

| Dato | Valor | Fuente | Cal. |
|---|---|---|---|
| Usuarios de internet | 41,6 M (90,6 %); 64,6 M de accesos móviles (86 % prepago) | Infobip; ENACOM T4-2025 | A |
| Penetración de WhatsApp | 93,3 % de la audiencia online (Statista); 99 % (Infobip); ~36 M de usuarios; 29,5 h por mes por usuario, el mayor uso del mundo | Statista, Infobip, Comscore | A/B |
| WhatsApp con empresas | 84 % habla con marcas por WhatsApp; 8 de 10 adultos mensajea a una empresa al menos una vez por semana y lo prefiere al teléfono; 66 % contrató un servicio y 62 % compró por WhatsApp | Meta/Kantar, Infobip (2025-26) | A/B |
| Minutos salientes móviles | 78.737 M (2019) → 49.467 M (2024) → **39.378 M (2025, −20 %)**; llamadas 30.130 M → 13.132 M | ENACOM datos abiertos | A |
| SMS salientes | 10.933 M (2019) → 2.266 M (2024) → 2.673 M (2025, +18 %, rebote por OTP y avisos A2P, est.) | ENACOM | A |
| Precio Meta por mensaje entregado, Argentina | marketing USD 0,0618; utility y autenticación 0,012-0,026 (según fuente); servicio gratis hasta 1-oct-2026, después 1.000 por mes y luego 0,026. Facturación en ARS desde abr-2026 | Meta vía Cliengo, Leadsales | A/B |
| WhatsApp Calling API | entrante gratis; saliente ~USD 0,011/min a Argentina (est. respond.io), pulsos de 6 s; requiere plantilla de permiso del usuario | Meta, respond.io | A/C |
| Telefonía a celular argentino | Twilio USD 0,353/min; fijo 0,060; DID USD 6-8 por mes. Terminación local (Anura, Personal, IPLAN): sin tarifario público; en la calculadora se usa ARS 25/min ≈ USD 0,016 | Twilio, Zadarma | A |
| SMS A2P | Twilio USD 0,103 lista (hasta 0,025 en volumen); Plivo 0,053; Claro directo ~ARS 0,50 (est.) | Twilio, sent.dm | A/C |

### 3.4 Adopción de IA en empresas argentinas

| Dato | Valor | Fuente |
|---|---|---|
| PyMEs industriales y de software (10-249 empleados, n=402) | 41,6 % usa alguna IA; 56 % en etapa experimental; **4 % con presupuesto asignado** | CEPE-UTDT / Fundar / FOP, abr-2026 |
| Empresas > 50 empleados | 63 % usa IA generativa | CACE, 2026 |
| Grandes empresas | 74 % aumentará presupuesto de IA en dos años | Microsoft, 2025 |
| Banca | hasta 60 % de consultas resueltas sin humano; mensajería banca/fintech +54 % anual | Infobip, abr-2026 |
| Facturación industria del software | USD 22.221 M (2024, +13 %); 20 % viene del sector financiero | CESSI |

### 3.5 Señales de demanda con dinero atrás

| Caso | Canal | Dato | Fecha |
|---|---|---|---|
| GCBA, línea 147 (Solar Insights, ElevenLabs) | voz telefónica | licitación ARS 3.021 M ≈ **USD 2 M** (suscripción ElevenLabs 950 M; contingencia 1.198 M; soporte 873 M) | ago-2026 |
| Villa María (Córdoba), Anunzi | voz | 13.325 llamadas en 7 meses, 85 % resueltas sin humano, puesta en marcha en 4 semanas | 2026 |
| Zárate (PBA), ATM Mendoza | WhatsApp + voz | ARS 75 M; ARS 20 M | 2025 |
| Kleva (AR), cobranzas por voz | voz saliente | ronda USD 1,5 M; DirecTV, ON City, Vana, Banco de Guayaquil; −30 % de costo, +3 % de recupero | may-2026 |
| Inceptia (AR), cobranzas y ventas | voz | 80 M llamadas/mes (LATAM), 150 empresas, "40-60 % del costo humano" | 2026 |
| Onbotgo (CL, oficina BA) | voz | 500 k cuentas/día; Ualá, Telefónica, Mapfre | 2026 |
| ContactShip (AR) | voz + WhatsApp | 2 M llamadas/mes declaradas; USD 30-799 por mes; Assist Card | 2026 |
| Botmaker Callbots (AR) | voz telefónica y WhatsApp | USD 0,07 por llamada ≤ 2 min, 0,30 hasta 60 min; Mercado Libre, Frávega, Swiss Medical, Toyota | ago-2025 |
| Banco Macro (MacroChat), Galicia (Gala) | WhatsApp texto | 1 M de clientes; 5 M+ de 44 M de interacciones (2024) | 2025-26 |
| Telecom Argentina | texto | IA generativa resuelve ~60 % sin humano | jun-2025 |
| Mercado Pago | voz y texto en la app | asistente con 100+ funciones para todos los usuarios | 2026 |
| Darwin AI (AR/BR) | WhatsApp, IG y llamadas | seed USD 4,5 M; > USD 2 M de ARR en 20 países | ago-2025 |
| Empleo | — | 367 avisos "IA conversacional" en LinkedIn Argentina (ruidoso) | sep-2026 |

## 4. Cálculo del mercado local

Tres métodos independientes; los tres convergen en el mismo orden de magnitud. Todo es **est.**
salvo los insumos citados en la sección 3.

### 4.1 Método A: gasto en atención humana que puede migrar

| Paso | Cálculo | Bajo | Central | Alto |
|---|---|---|---|---|
| Posiciones tercerizadas para el mercado interno | 50.000 × (1 − exportación 45 / 35 / 25 %) | 27.500 | 32.500 | 37.500 |
| Venta anual del outsourcing interno | × USD 2.900 × 12 | USD 957 M | USD 1.131 M | USD 1.305 M |
| Agentes in-house | ratio Gartner → 98 k totales − 50 k tercerizados | 35.000 | 48.000 | 55.000 |
| Costo anual in-house | × USD 1.200 / 1.300 / 1.400 (laboral + puesto) × 12 | USD 504 M | USD 749 M | USD 924 M |
| **Gasto sustituible** | suma | **USD 1,5 mil M** | **USD 1,9 mil M** | **USD 2,2 mil M** |
| Cuota automatizada 2026 | Gartner mundo 10 %; Argentina atrasada | 5 % | 6,5 % | 8 % |
| Precio IA / costo humano | USD 0,08-0,15 por min contra 0,19 (propio) a 0,31 (BPO) | 0,3 | 0,45 | 0,6 |
| **Mercado IA 2026** | gasto × cuota × precio relativo | **USD 22 M** | **USD 56 M** | **USD 106 M** |
| Cuota automatizada 2029 | Gartner predice 80 % de casos comunes; usamos 20-30 % del volumen | 20 % | 25 % | 30 % |
| **Mercado IA 2029** | | **USD 90 M** | **USD 214 M** | **USD 396 M** |

El dato de Grand View (USD 1.405 M de outsourcing en 2024) cae dentro del rango de la fila 2,
lo que valida el orden de magnitud aunque la fuente sea C.

### 4.2 Método B: minutos de voz

| Paso | Cálculo | Bajo | Central | Alto |
|---|---|---|---|---|
| Agentes para el mercado interno | tercerizados internos + in-house | 60.000 | 80.000 | 90.000 |
| Minutos de conversación por agente y mes | 156 h × 60 × ocupación 60 / 65 / 70 % | 5.616 | 6.084 | 6.552 |
| Minutos totales por año | | 4,0 mil M | 5,8 mil M | 7,1 mil M |
| Parte que es voz (el resto es chat y WhatsApp) | 50 / 60 / 70 % | **2,0 mil M** | **3,5 mil M** | **5,0 mil M** |
| Minutos de voz automatizables en 2029 | × 25 % | 500 M | 875 M | 1.250 M |
| **Mercado de voz IA 2029** | × USD 0,08 / 0,10 / 0,12 | **USD 40 M** | **USD 88 M** | **USD 150 M** |

Verificación: 3,5 mil M de minutos de contact center por año son ~9 % de los 39 mil M de minutos
salientes móviles de 2025 (ENACOM), sin contar la red fija. Plausible.

Las **100 cuentas grandes** (bancos, telcos, prepagas, utilities, retail, Estado) concentran
~60 % de ese volumen: ~290 M de minutos por mes, unos 2,9 M por mes cada una. Automatizar
25 % de una sola de esas cuentas a USD 0,10 son ~USD 870 k por año. Ahí está el dinero, y ahí
compiten Infobip, Botmaker, Google, Microsoft, NICE y Genesys.

### 4.3 Método C: empresas × ticket (lo que facturan las plataformas)

| Segmento | Empresas objetivo | Ticket anual | SAM (todas adoptaran) | Adopción 2026 | 2026 | Adopción 2029 | 2029 |
|---|---|---|---|---|---|---|---|
| Grandes (> 100 empleados) con atención masiva a consumidores | 9.939 × 15 % = 1.500 | USD 60.000 (USD 5.000 por mes; los top-100 mucho más, ver 4.2) | USD 89 M | 30 % | USD 27 M | 60 % | USD 54 M |
| Medianas y pequeñas (10-100) de servicios B2C | 78.500 × 40 % = 31.400 | USD 1.800 (USD 150 por mes: Botmaker 149, ContactShip 150, Cliengo 119) | USD 57 M | 8 % | USD 4,5 M | 25 % | USD 14 M |
| Micro con teléfono intensivo (consultorios, inmobiliarias, restaurantes, concesionarias, estudios) | 441.000 × 12 % = 53.000 | USD 480 (USD 40 por mes) | USD 25 M | 3 % | USD 0,8 M | 12 % | USD 3 M |
| **Total** | | | **USD 171 M** | | **USD 32 M** | | **USD 71 M** |

Si a las 100 cuentas grandes se les aplica el ticket por volumen del método B (USD 88 M en 2029
en lugar de 100 × 60 k = 6 M), el total 2029 sube a ~USD 150 M.

Verificación con Meta: WhatsApp cobra a las empresas ~USD 4 mil M por año (run-rate Q2-26).
Argentina es 1,2 % de los usuarios de WhatsApp pero uno de los países de mayor uso comercial;
con 1,5-2,5 % del total, las empresas argentinas le pagan a Meta **USD 60-100 M por año** solo
por mensajes. Las plataformas (BSP) facturan encima de eso planes y consumo, lo que da un
mercado de automatización por WhatsApp de al menos USD 20-40 M hoy, coherente con el método C.

### 4.4 Convergencia

| | Método A (gasto) | Método B (minutos) | Método C (empresas) | **Estimación** |
|---|---|---|---|---|
| Mercado IA voz + texto, 2026 | 22-106 M | — | 32 M | **USD 30-50 M** |
| Mercado IA voz + texto, 2029 | 90-396 M | — | 71-150 M | **USD 70-200 M, central ~120** |
| Solo voz telefónica, 2026 | — | — | 15-25 % del total | **USD 5-15 M** |
| Solo voz telefónica, 2029 | — | 40-150 M | 30-40 % del total | **USD 30-60 M** |

La voz es la parte chica hoy porque la demanda argentina se volcó a WhatsApp y porque el 5 % de
voicebots generativos en producción (Gartner, mundo) acá es menor todavía. Crece más rápido que
el texto por tres razones: cobranzas (contactabilidad), organismos públicos (147, municipios) y
la llegada de la voz dentro de WhatsApp.

### 4.5 Qué parte es alcanzable para este proyecto (SOM)

Un servidor CAP-002 (22 llamadas simultáneas con p95 ≤ 2,8 s) produce ~163.000 minutos por mes
en horario comercial (8 h × 22 días, 70 % de ocupación). A USD 0,10-0,15 por minuto son
USD 16-24 k por mes vendiendo todo, o USD 5-7 k vendiendo el 30 % que asume la calculadora.

| Referencia | Minutos por mes | Facturación anual a USD 0,10-0,15 | Servers (al 30 % de venta) |
|---|---|---|---|
| Todo el mercado de voz IA de Argentina 2026 (USD 5-15 M) | 3-12 M | — | 60-250 |
| 1 % del mercado de voz 2029 (USD 0,3-0,6 M) | 200-500 k | USD 0,3-0,6 M | 4-10 |
| Una prepaga o banco mediano con 25 % automatizado | ~700 k | USD 0,85 M | 15 |
| 100 PyMEs con el pack "Pyme" (1.800 min) | 180 k | USD 0,2 M + bases fijas | 4 |

Un objetivo a tres años de USD 0,5-1,5 M por año (0,5-1,5 % del mercado de voz de 2029) son
6-25 servers como el de CAP-002 vendiendo el 30 % de su capacidad, o 2-8 vendiéndola toda. Las bases fijas de la calculadora (ARS 30-200 k por plan) pesan más que los minutos
en las PyMEs.

## 5. Dónde está la demanda, por vertical y canal

| Vertical | Canal que pide | Caso de uso | Evidencia local | Precio que paga hoy |
|---|---|---|---|---|
| Bancos, fintech, cobranzas | voz saliente + WhatsApp | mora temprana, promesas de pago, recordatorios; contactabilidad 25-30 % y callbot recupera 15-25 % de contactados vs 8-12 % del IVR | Kleva, Inceptia, Onbotgo, Vozy; Naranja X, Mercado Pago y Galicia concentran más de la mitad de los morosos | "40-60 % del costo humano" (sobre el precio BPO) = USD 0,12-0,19/min |
| Estado (ciudad, municipios, agencias) | voz entrante | líneas de atención al vecino, turnos, reclamos | CABA 147 USD 2 M; Villa María 85 % sin humano; Zárate, Mendoza | licitaciones de ARS 20 M a 3.000 M |
| Salud privada (prepagas, clínicas, diagnóstico, consultorios) | WhatsApp + voz entrante | turnos, confirmación (ausentismo 30 % baja a 8-15 % con recordatorio), autorizaciones | Swiss Medical con Botmaker; agencias Botias, MednIA, Runia | PyME USD 30-150/mes; grandes a cotizar |
| Telcos e ISPs (4.720 licenciatarios) | texto, voz entrante | soporte técnico de primer nivel, reclamos, bajas | Telecom 60 % resuelto por IA; Claro con S1 Gateway | enterprise |
| Comercio electrónico y retail | WhatsApp | estado de pedido, cambios, ventas | Mercado Libre y Frávega con Botmaker; 63 % de empresas > 50 usan IA generativa | USD 149-499/mes + Meta |
| Seguros | voz + WhatsApp | siniestros, cotización, cobranza de pólizas | Galicia Seguros (Laia), Assist Card (ContactShip), Mapfre (Onbotgo) | enterprise |
| PyMEs de servicios (inmobiliarias, concesionarias, gastronomía, educación privada, estudios) | WhatsApp, algo de voz | recepción 24×7, calificación de leads, reservas | agencias a USD 30-800/mes; 36 % de inmobiliarias usaba IA en 2024 | USD 30-300/mes |
| SMS | notificación | OTP, avisos de turno, cobranza | 2,7 mil M de SMS por año, rebote 2025 por A2P | USD 0,025-0,10 por SMS; no es canal de agente |

## 6. Condiciones de contorno en Argentina

- **Regulación (menos restrictiva que Chile, Colombia, Brasil y España; parecida a México):**
  - Ley 26.951 (No Llame) es opt-out: prohíbe publicidad y venta no solicitadas; permite llamar
    con relación contractual vigente (lu-vi 9-21, sáb 9-13), lo que cubre cobranzas, turnos y
    encuestas de clientes. Consultar el padrón cada 30 días. Multas bajas (hasta ARS 100 k por
    infracción) pero por cada llamada denunciada, y con **responsabilidad solidaria del que
    contrata** (Res. AAIP 170/25, automotriz multada por sus concesionarios).
  - Cobranzas: sin norma nacional de horarios (proyecto 4384-D-2026 en comisión); CABA Ley 6171
    (lu-vi 8-20, sáb 8-12) y proyecto de sep-2026 que limita a 1 contacto por día y exige que los
    **agentes de IA avisen que lo son y ofrezcan un humano**. Denuncias por hostigamiento en PBA:
    393 (2024) → 1.237 (ene-may 2026).
  - Sin ley de IA ni obligación vigente de declarar voz sintética; el proyecto Brügge (jul-2026)
    la exigiría. Conviene diseñar el agente para que se presente como asistente virtual.
  - Sin prefijo ni identificación obligatoria de llamadas automáticas (Chile 809, España 400).
  - Licencia TIC (Ley 27.078): operar agentes sobre líneas de un licenciatario no la exige;
    revender minutos o números sí. Ver [`anura-terminos-2026.md`](../proveedores/anura-terminos-2026.md).
- **Costos de canal:** la voz a celulares por proveedores globales (USD 0,35/min) es el costo que
  hace inviable el saliente con Twilio; la terminación local y WhatsApp Calling (~USD 0,011) lo
  resuelven. Meta empieza a cobrar los mensajes de servicio el 1-oct-2026 (1.000 gratis por
  número y mes, luego ~USD 0,026): sube el costo del texto y mejora el relativo de la voz.
- **Dolarización de precios:** los competidores cobran en USD (Botmaker, ContactShip, Vapi, Meta
  desde abr-2026 en ARS al cambio). El precio de venta del BPO (CACC) subió 47 % en pesos en 20
  meses y quedó casi fijo en dólares (~USD 18,5 por hora).

## 7. Implicancias para este proyecto

1. **El ahorro es el argumento y hoy nadie lo ofrece en Argentina.** Los agentes de voz llave en
   mano locales (USD 0,28-0,35 por minuto) cuestan lo mismo que un BPO (0,31) y más que un agente
   propio (0,19 por minuto de conversación, 0,26 con puesto y supervisión). Con inferencia propia
   y terminación local hay margen para cobrar USD 0,08-0,15 y seguir ganando: 1,5-3 veces menos
   que un agente propio y 2-4 veces menos que un BPO. Esa brecha es la única razón para que una
   PyME o un municipio cambie.
2. **Los nichos con demanda probada son cobranzas, Estado y salud (turnos).** Son entrantes o
   salientes con relación contractual, así que el No Llame no los bloquea. Cobranzas exige la
   presentación como IA y derivación a humano; conviene tenerlo en el workflow.
3. **WhatsApp tiene que ser un canal del mismo agente**, en texto y en voz (Calling API): ahí
   está el 80 % de la demanda de texto y la voz saliente más barata. Botmaker ya lo hace.
4. **SMS solo para avisos** (turnos, OTP, recordatorio de pago), no como canal conversacional.
5. **El mercado de voz IA de 2026 entero cabe en 60-250 servers como el de CAP-002.** No hace
   falta más capacidad que la de un rack para los primeros años; el cuello es comercial.
6. **Las 100 cuentas grandes tienen el 60 % del volumen** y ya las atienden Infobip, Botmaker,
   Google, Microsoft y NICE. El espacio propio está en medianas, PyMEs, municipios y clínicas,
   donde el ticket es USD 40-300 por mes y pesa más la base fija que el minuto.

## 8. Vacíos y calidad de los datos

- No hay dato público de: agentes in-house en Argentina, exportación del sector contact center,
  volumen de llamadas agregado, empresas argentinas con WhatsApp Business API, tráfico A2P
  separado del P2P, tarifario SIP local en pesos, tarifa oficial de Meta Calling para Argentina,
  inscriptos al No Llame después de 2022, conteo de inmobiliarias, concesionarias y estudios de
  cobranza. Cada uno fue estimado con el supuesto indicado y un rango.
- Los tamaños de mercado mundiales son de consultoras C, con diferencias ×2-3 entre firmas; se
  usaron solo como orden de magnitud. La adopción y el dinero real salen de fuentes A (Gartner,
  Meta, SEC, ENACOM, CACC).
- Los porcentajes de ahorro y recupero de los proveedores (Inceptia, Kleva, ContactShip) no están
  auditados.
- Google Trends, comprar.gob.ar y Bumeran no pudieron leerse.

## 9. Fuentes principales

- Gartner: [80 % agéntico en 2029](https://www.gartner.com/en/newsroom/press-releases/2025-03-05-gartner-predicts-agentic-ai-will-autonomously-resolve-80-percent-of-common-customer-service-issues-without-human-intervention-by-20290), [solo 20 % redujo plantilla](https://www.gartner.com/en/newsroom/press-releases/2025-12-02-gartner-survey-finds-only-20-percent-of-customer-service-leaders-report-ai-driven-headcount-reduction), [voicebots generativos 5 %](https://www.gartner.com/en/newsroom/press-releases/2024-12-09-gartner-survey-reveals-85-percent-of-customer-service-leaders-will-explore-or-pilot-customer-facing-conversational-genai-in-2025), [17 M de agentes](https://www.gartner.com/en/newsroom/press-releases/2022-08-31-gartner-predicts-conversational-ai-will-reduce-contac).
- Meta: [10-Q Q2-2026](https://www.sec.gov/Archives/edgar/data/0001326801/000162828026050705/meta-20260630.htm), [precios de WhatsApp](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing), [Calling API](https://developers.facebook.com/documentation/business-messaging/whatsapp/calling/pricing).
- Juniper: [CPaaS](https://www.globenewswire.com/news-release/2025/04/22/3065137/0/en/CPaaS-Revenue-to-Exceed-34bn-Next-Year-as-AdTech-Partnerships-Drive-Growth.html), [OTT business messaging](https://www.juniperresearch.com/press/ott-business-messaging-traffic-to-grow-45-percent-globally/).
- Plataformas: [ElevenLabs USD 500 M ARR](https://elevenlabs.io/blog/500m-arr-and-new-investors), [Sierra](https://techcrunch.com/2026/05/04/sierra-raises-950m-as-the-race-to-own-enterprise-ai-gets-serious/), [Vapi](https://techcrunch.com/2026/05/12/vapi-hits-500m-valuation-as-amazon-ring-chose-its-ai-platform-over-40-rivals/), [Retell](https://sacra.com/research/retell-ai-60m-yr-up-650-yoy/), [NICE 6-K](https://www.sec.gov/Archives/edgar/data/0001003935/000117891326002406/exhibit_99-1.htm), [Gupshup voz](https://www.prnewswire.com/news-releases/gupshup-launches-self-serve-voice-ai-platform-extending-conversational-engagement-into-phone-calls-302869131.html).
- Argentina: [CACC Sistema de Costos ene-25 a sep-26](https://www.cacc.org.ar/sistema-estadistico-de-costos-de-centros-de-contacto-ene-25-sep-26/) (precio de venta, no costo), [escala CCT 781/20 ago-2026](https://www.eldestapeweb.com/economia/cuanto-gana-trabajador-call-center-agosto-2026-salario-cobra-argentina-202681315305), [salario mínimo sep-2026](https://chequeado.com/el-explicador/el-salario-minimo-sera-de-383-800-en-septiembre-de-2026-y-acumula-una-caida-real-del-397-desde-noviembre-de-2023/), [cargas sociales 2026](https://yo-facturo.com/blog/cargas-sociales-en-argentina-2026/), [El Economista, call centers](https://eleconomista.com.ar/economia/call-centers-alerta-n6682), [Min. Trabajo, operador telefónico](https://www.argentina.gob.ar/sites/default/files/ooa_sintesis_operadortelefonico.pdf), [UCEMA, PyMEs sep-2025](https://ucema.edu.ar/sites/default/files/2025-09/IndicadoresUCEMA_PyMEs092025_0.pdf), [ENACOM minutos](https://indicadores.enacom.gob.ar/DatosAbiertos/ComunicacionesMoviles/minutos), [ENACOM SMS](https://indicadores.enacom.gob.ar/DatosAbiertos/ComunicacionesMoviles/sms), [encuesta IA en PyMEs 2026](https://nadia.ar/extras/nadia_encuesta_pymesARG2026.pdf), [WhatsApp y marcas, Meta/Kantar](https://insiderlatam.com/whatsapp-se-consolida-como-canal-comercial-84-de-los-argentinos-usan-la-app-para-comunicarse-con-las-marcas/), [Twilio precios Argentina](https://www.twilio.com/en-us/voice/pricing/ar).
- Casos: [licitación CABA 147](https://seccionciudad.com.ar/2026/08/18/las-llamadas-de-vecinos-al-gobierno-de-la-ciudad-ahora-seran-atendidas-por-ia-que-imita-la-voz-humana/), [Kleva](https://www.lanacion.com.ar/economia/IA/crearon-agentes-de-ia-para-cobranzas-y-levantaron-us15-millones-para-expandirse-en-america-latina-nid22052026/), [Darwin AI](https://www.lanacion.com.ar/economia/IA/la-startup-argentina-que-levanto-millones-y-promete-cambiar-como-trabajan-las-empresas-nid25082025/), [Galicia](https://www.lanacion.com.ar/economia/IA/un-cambio-cultural-banco-galicia-apuesta-por-la-ia-generativa-para-transformar-la-atencion-al-nid30062025/), [Telecom 60 %](https://www.iprofesional.com/tecnologia/430167-movistar-telecom-aplican-inteligencia-artificial-sin-que-te-des-cuenta-como-la-usan), [Inceptia](https://inceptia.ai/), [ContactShip](https://contactship.ai/), [Anunzi](https://ai.anunzi.net/).
- Regulación: [Ley 26.951](https://www.argentina.gob.ar/normativa/nacional/norma-233066/actualizacion), [Res. AAIP 126/2024](https://servicios.infoleg.gob.ar/infolegInternet/anexos/395000-399999/399750/norma.htm), [responsabilidad solidaria](https://allende.com/privacidad-y-ciberseguridad/la-autoridad-de-proteccion-de-datos-sienta-precedente-sobre-responsabilidad-solidaria-respecto-al-registro-no-llame-10-29-2025/), [CABA Ley 6171](https://www.cedom.gob.ar/legislacion/normas/leyes/RepoLeyes/ley6171.html), [proyecto cobranzas nacional](https://www.parlamentario.com/2026/09/02/buscan-regular-las-cobranzas-extrajudiciales-y-prevenir-practicas-abusivas/).
