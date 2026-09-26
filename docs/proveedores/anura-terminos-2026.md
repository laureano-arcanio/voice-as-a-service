# Anura: Términos y Condiciones 2026 frente al modelo de packs con minutos

Análisis del 26-sep-2026 de [`Términos y Condiciones 2026.pdf`](Términos%20y%20Condiciones%202026.pdf)
(CITILAN ARGENTINA S.A., marca Anura, 34 cláusulas, generado el 17-mar-2026). No es asesoramiento
legal: marca qué cláusulas afectan el negocio y qué conviene validar con un abogado y con Anura.

**Modelo evaluado:** nosotros contratamos números a Anura y vendemos a clientes finales packs de
agente de voz con minutos asignados. Anura solo incide en el costo del minuto y del número.

## Veredicto

- **El modelo se puede implementar, pero no como "reventa de números ni de minutos de Anura".**
  La cláusula 26 lo prohíbe expresamente. Lo que sí es defendible: vender un **servicio de agente
  de voz** (software + operación) que atiende y hace llamadas por líneas **nuestras**. El cliente
  compra minutos de agente, no un número ni un servicio de telefonía. El número queda a nuestro
  nombre, en nuestra cuenta, y el cliente no toca el panel de Anura.
- **Hay que hablar con Anura antes de escalar.** Tienen [programa de partners](https://www.anura.com.ar/partners/)
  ("Para ofrecer Anura", ISPs, "Para integrar plataformas") sin condiciones publicadas. Conviene
  entrar por ahí y dejar por escrito que el uso (agente de IA sobre números propios, muchos DIDs,
  tráfico automatizado) está aceptado. Si no, una sola cuenta con decenas de números y tráfico
  de terceros puede leerse como reventa y darles causal de cancelación inmediata (32 c).
- **Riesgo regulatorio a confirmar con abogado:** en Argentina la "reventa de servicios de
  telecomunicaciones" es un servicio TIC que exige Licencia Única (Ley 27.078, registro en ENACOM).
  Vender software que atiende llamadas sobre líneas de un licenciatario no debería serlo, pero
  cómo redactemos la oferta (minutos de agente vs. minutos de teléfono) define de qué lado cae.

## Cláusulas que afectan el negocio

| Cl. | Qué dice | Impacto en el modelo |
|---|---|---|
| **26** | Uso exclusivo del Usuario; **no revender, ceder ni transferir** el Servicio ni el número | La cláusula central. No se puede asignar un número "del cliente" ni facturarle telefonía de Anura. El número es nuestro siempre; el cliente no lo puede portar ni llevarse |
| **8, 9** | Prohibido "inclusión, distribución, comercialización" del Servicio; no usar marcas de Anura | Marca blanca de nuestro lado: no decir "número Anura" ni "minutos Anura" en la oferta |
| **32 c** | Somos responsables de impedir mal uso o abuso; Anura **cancela de inmediato** sin declaración judicial | El abuso de un cliente (salientes masivas, spam) nos tira toda la cuenta, con todos los números. Exige política de uso y suspensión inmediata por cliente |
| **31** | 12 meses con renovación automática, pero **cualquiera rescinde sin causa** | Anura puede cortarnos sin motivo. Riesgo de concentración: si se van los números, se van los de todos los clientes |
| **16** | Se factura **por minuto entero**, aunque se use una fracción; se paga independientemente del uso | Cada llamada nos cuesta `ceil(duración)`. Una saliente que cae en contestador o corta a los 10 s cuesta un minuto. Facturar al cliente también por minuto iniciado |
| **15** | Postpago: abono adelantado + consumos a mes vencido (local, LDN, internacional, **celular**). Prepago: carga mínima, **vence a los 180 días**, sin reembolso al cancelar | Las entrantes no aparecen entre los consumos: confirmar que son gratis (la calculadora lo asume). Casi todo destino en Argentina es celular: ese es el precio saliente que importa. Si usamos prepago, nuestros packs deben vencer antes que la carga |
| **14** | Precios en **pesos**, los cambian con **15 días** de aviso; se aceptan si no damos de baja | No vender packs anuales a precio fijo en pesos sin cláusula de ajuste. Trasladar el cambio de precio con el mismo plazo o menos |
| **17, 18** | Volante el 1.° día hábil, vence el **14**; sin pago se suspenden las **salientes**; a los 10 días cancelan todo. Mora automática: IPC + 5 % mensual + gastos; **reconexión = 2 abonos** | Cobrar a los clientes antes del 10 (adelantado, con débito). Un atraso nuestro corta las salientes de todos. Las entrantes siguen: los agentes de atención sobreviven a una suspensión |
| **19** | Pueden informarnos a Veraz/Nosis | Disciplina de tesorería |
| **21, 22** | No garantizan calidad (no es Servicio Básico Telefónico); solo descuentan proporcional del abono por cortes propios; **sin lucro cesante** ni daños indirectos | No podemos dar un SLA de telefonía respaldado por Anura. Nuestro SLA debe ser espejo: crédito proporcional, sin lucro cesante |
| **27** | Sin ruteo a emergencias (911, 10Y, 11Y) salvo que lo configure el usuario | Avisar al cliente que el número no reemplaza su línea ni sirve para emergencias |
| **24** | Grabaciones opcionales, 6 meses en el panel, uso bajo exclusiva responsabilidad del Usuario; Anura no divulga salvo oficio judicial | Grabamos nosotros (LiveKit). La responsabilidad por grabar, avisar y proteger datos (Ley 25.326) es nuestra y del cliente: trasladarla |
| **12** | Plan corporativo: no aplica el Reglamento de Clientes TIC (Res. 733-E/2017) | Anura nos trata como empresa. Si nosotros vendemos a personas humanas, nos aplica Defensa del Consumidor (24.240). Vender solo a CUIT |
| **7** | Revocación dentro de 10 días corridos de validada la transacción, irrenunciable | Al alta de cada número hay que contar ese plazo. Espejarlo o no según segmento (B2B puede no darlo) |
| **Intro, 3, 6** | Solicitud firmada por apoderado, con poder, entregada en **48 h**; validación hasta 48 h hábiles; verificación crediticia; pueden pedir **garantía o fiador** | Alta lenta y con papeles. Averiguar si sumar números dentro de la cuenta es trámite o autoservicio, y el plazo |
| **13** | Productos (teléfonos IP) al contado | No aplica: no usamos equipos. Ojo con 31: sin devolver equipos no procesan la baja |
| **20** | Pueden cambiar los T&C y negar acceso sin aviso por uso "inconveniente" | Sumar al riesgo de concentración |
| **33** | Tribunales Civil y Comercial Federal de CABA | — |

Detalle menor: el encabezado dice Esmeralda 770 piso 12 "A" y el pie Carlos Pellegrini 1069 piso 8.
Confirmar el domicilio a la hora de notificar fehacientemente.

## Limitaciones que nos impone

1. **El número no es transferible.** Un cliente que se va pierde el número. No hay portabilidad
   saliente porque el titular somos nosotros y la cesión está prohibida.
2. **Un solo punto de falla comercial.** Anura puede rescindir sin causa (31), cancelar por abuso (32 c)
   o cambiar los T&C (20). Sin segundo proveedor, todos los clientes dependen de una cuenta.
3. **Costo por minuto redondeado hacia arriba** (16). Para llamadas de duración media D minutos, el
   redondeo agrega ~0,5 min: +25 % con D = 2, +17 % con D = 3. En salientes, las que no conectan
   con una persona (contestador, corte rápido) pagan un minuto completo.
4. **Precio en pesos, ajustable con 15 días** (14). No podemos comprometer precios a largo plazo.
5. **Cobro el 14 sin gracia** (17, 18): mora automática, reconexión de dos abonos. La caja tiene que
   estar antes de que cobre Anura.
6. **Sin SLA de calidad ni de disponibilidad** (21, 22). Solo crédito proporcional por cortes propios.
7. **Sin ruteo a emergencias** (27).
8. **Responsabilidad total por el uso** (32 c, 10): respondemos por lo que hagan nuestros clientes.
9. **Alta con firma y poder** (intro, 3, 6): no hay onboarding instantáneo de números.
10. **Nada dice de canales simultáneos por número o por cuenta**, de tráfico automatizado, de caller
    ID ni de cantidad máxima de números: son los datos que faltan para dimensionar.

## Limitaciones que hay que trasladar al cliente

Cada una es espejo de una cláusula de Anura; si no se traslada, la absorbemos nosotros.

| Nuestra cláusula | Espejo de |
|---|---|
| El número lo provee y es titular el prestador; no se cede, no se porta, puede cambiar por causas del operador. Para conservar un número propio, el cliente trae su línea (desvío o troncal SIP) | 26, 31 |
| Solo personas jurídicas o con CUIT; plan corporativo, no consumidor | 12 |
| Minutos por **minuto iniciado**, entrantes y salientes, incluidos contestador y cortes | 16 |
| Los minutos del pack **vencen** (mensual sin acumulación, o tope de 180 días); sin reembolso de minutos no usados al cancelar | 15 |
| Precios en pesos ajustables con aviso de 15 días o menos; o precio atado a otra referencia | 14 |
| Pago adelantado antes del día ~10; sin pago se suspenden salientes, luego el servicio; cargo de reconexión | 17, 18 |
| Sin garantía de calidad de la red telefónica; crédito proporcional por cortes propios; sin lucro cesante ni daños indirectos | 21, 22 |
| No es servicio telefónico básico ni sirve para emergencias | 22, 27 |
| **Política de uso aceptable:** prohibidas las salientes masivas no solicitadas; cumplir el Registro No Llame (Ley 26.951); avisar que habla con un sistema automatizado y que se graba; suspensión inmediata por abuso; el cliente indemniza | 32 c, 10, 24 |
| El cliente es responsable del contenido del agente (lo que dice, lo que promete, los datos que pide) y del tratamiento de datos de sus llamantes (Ley 25.326); nosotros somos encargados del tratamiento | 24, 4 |
| Grabaciones y transcripciones con retención definida (p. ej. 6 meses), descargables | 24 |
| Podemos cambiar los términos con aviso; el cliente puede dar de baja | 20 |
| Marca: el cliente no menciona al operador telefónico | 9 |

## Decisiones de producto y segmentos que se desprenden

- **Producto = minutos de agente, no minutos de teléfono.** La unidad vendida es el minuto de
  conversación con el agente (inferencia + operación). La telefonía es un insumo. Esta redacción
  es la que separa el modelo de la reventa (26) y de la licencia TIC.
- **Solo B2B.** Alta con CUIT y razón social; espeja 12 y evita Defensa del Consumidor.
- **Tres formas de conectar el número, tres segmentos:**
  1. **Número nuestro** (pyme sin línea, o que quiere una línea nueva para el agente): más simple,
     margen sobre el DID, pero el número no es del cliente. Decirlo desde la oferta.
  2. **Desvío desde la línea del cliente** a nuestro número: el cliente conserva su número y paga
     el desvío a su operador. Sin cambio en nuestra infraestructura. Es el camino para el cliente
     que ya tiene un número conocido.
  3. **Troncal SIP del cliente** (empresas con PBX): el cliente entra por SIP a nuestro LiveKit;
     Anura no participa; sin costo de telefonía nuestro. Es el modelo BYO de Vapi
     (`docs/competencia/vapi/vapi-canales-integracion.md`). Hoy Asterisk solo está preparado para
     Anura; habría que abrir un troncal por cliente.
- **Entrantes y salientes son productos distintos.**
  - Entrante: costo casi solo inferencia (si Anura confirma entrante gratis), sin riesgo de abuso,
    sobrevive a una suspensión de salientes. Es el producto principal.
  - Saliente: paga el minuto a celular con redondeo, lleva el riesgo de 32 c y el Registro No Llame.
    Ofrecerlo restringido a recordatorios y confirmaciones a contactos propios con consentimiento,
    con tope de llamadas por día por cliente y sin campañas frías, al menos hasta tener acuerdo
    escrito con Anura.
- **Packs mensuales sin acumulación** (o con tope de 180 días si se usa prepago de Anura), pago
  adelantado por débito automático, precio revisable mes a mes. Los competidores (Botmaker, Vapi)
  facturan en dólares y por mes.
- **Precio del minuto:** cargar el redondeo de 16 en el costo de la calculadora
  (`docs/capacity/calculadora-costos.html`): el costo de Anura por minuto vendido no es `$/min`,
  es `$/min × (1 + 0,5/D)`. Y agregar el costo del DID por cliente a la base fija del plan.
- **Un DID por cliente** para rutear la entrante al workflow. El costo mensual del número marca el
  piso de la base fija del plan más chico. Averiguar si hay descuento por volumen de DIDs.
- **Segundo proveedor** antes de tener más de un puñado de clientes con número nuestro: Asterisk
  ya abstrae la troncal. Candidatos a relevar en `docs/proveedores/`.
- **Contrato con el cliente:** "el número puede cambiar por causas del operador" no es opcional.
  Sin esa cláusula, una rescisión de Anura (31) se convierte en incumplimiento nuestro.

## Preguntas para Anura (comercial y partners)

Lo que el T&C no dice y hace falta para cerrar precios y capacidad:

1. Lista de precios: abono, costo mensual por DID, minuto a celular, a fijo, LDN, y **si la entrante
   tiene costo**.
2. **Canales simultáneos** por número y por cuenta, y costo del canal extra. Nuestra capacidad es
   ~22 llamadas simultáneas por server (CAP-002); la troncal tiene que acompañar.
3. Cantidad máxima de números por cuenta, ciudades disponibles, 0800/0810, y **plazo y trámite
   para sumar un número** (¿autoservicio en el panel? ¿API?).
4. Política sobre **tráfico automatizado** (agente de IA que atiende y llama) y sobre salientes en
   volumen. Que quede por escrito.
5. Caller ID en salientes: ¿solo el número propio? ¿se puede presentar otro número de la cuenta?
6. Programa de partners: modalidad para "plataforma que integra Anura", si permite números a
   nombre del partner al servicio de terceros, descuentos por volumen, quién factura.
7. Portabilidad: ¿pueden recibir un número que trae el cliente y dejarlo en **su** cuenta con
   la terminal registrada por nosotros? Sería una cuarta variante del segmento 2.
8. Cómo se maneja la suspensión por falta de pago con varios números (¿toda la cuenta?).
9. Confirmar que los 10 días de revocación (7) y la firma con poder aplican por alta de número o
   solo al alta de la cuenta.

## Fuentes

- El PDF en esta carpeta.
- [Programa de partners de Anura](https://www.anura.com.ar/partners/) y
  ["Ofrecé Anura"](https://www.anura.com.ar/partners/ofrecer-anura/): tres categorías, sin
  condiciones publicadas; formulario en `/partners/formulario-partners/`.
- [Precios de Anura](https://www.anura.com.ar/precios/): sin precios publicados; incluye
  grabaciones, APIs, numeración de varias ciudades, 0800/0810 y portabilidad; cotizan por contacto.
- [ENACOM, Registro de Servicios TIC](https://www.enacom.gob.ar/institucional/nuevo-reglamento-de-registro-de-servicios-tic_n1195):
  la reventa de servicios de telecomunicaciones es un servicio TIC registrable con Licencia Única.
