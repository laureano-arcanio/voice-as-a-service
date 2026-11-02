# Propuesta para SIM Te Cuida

- **Pedido (2-nov-2026, Laureano, textual):** "Necesitan el plan mostrador para arrancar, pero además necesitan un pequeño
  CRM bastante básico que permita que la gente consulte si la persona que llama o escribe por WhatsApp ya es un cliente o
  no, y que delegue o redireccione la llamada a uno de las personas del staff con el sistema que ya tenemos de rotación. La
  propuesta tiene que incluir la puesta en marcha, número de teléfono, ofrecer un 0800, WhatsApp, integración con llamadas,
  voz y mensajes de texto, además un pequeño CRM donde ellos puedan cargar desde la misma plataforma que les vamos a dar los
  clientes con su número de teléfono y el estado de suscripción. Cuando el staff recibe la llamada, tiene que recibir una
  pequeña minuta de quién es la persona, qué tipos de cuidados recibe y algunos campos más que eventualmente tendremos en la
  tabla y en el sistema de esta empresa. El mecanismo de identificación principal tiene que ser el número de teléfono. Si no
  se encuentra o no existe, tiene que preguntar cómo se llama, o el DNI, o alguna otra información de contacto. Tiene que
  identificar si es una emergencia para priorizar la atención."
- **Cambio para la v2 (2-nov-2026, Laureano, textual):** "Quita la sección piloto y agreguemos una sección presupuesto. En esta
  sección comentamos el costo de 29.000 pesos de base y le vamos a sumar 10.000 pesos más por mantenimiento del sistema CRM
  para el almacenaje de los pacientes y las consultas, y además esto incluye el teléfono 0800 si es que lo quieren. quita
  también la sección oportunidades."
- **Regla nueva del usuario (v2):** sin fondos azul oscuro en todo el documento; todo en blanco o claro, y el azul de marca
  solo para acentos. Se aplica en el `<style>` del documento: `base.css` sigue con el pie oscuro.
- **Destinatario:** responsables de SIM Te Cuida ("SIM Servicios Integrales a Personas en Situaciones Médicas"), todavía sin
  nombre. Agencia de cuidadoras y acompañantes en sanatorio y domicilio, CABA y GBA. En "ustedes", sin saludo personal.
- **Contexto:** SIM se contactó con Laureano (lead entrante, CRM #481). Base de conocimiento:
  [`comercial/demos/simtecuida.md`](../../../../comercial/demos/simtecuida.md) (partes 0, 1, 2, 4, 5 y 7). Formato, estructura y
  estética copiados de [`goldman-propuesta`](../goldman-propuesta/README.md) y
  [`baicenter-propuesta`](../baicenter-propuesta/README.md).
- **Objetivo:** que contraten la línea a $ 39.000 por mes y arranquen con el relevamiento.
- **Formato:** A4, 4 a 6 hojas (salió en 5). `make doc P=simtecuida-propuesta V=<n> HOJAS=6`.
- **Decisiones del pedido:**
  - Presupuesto por mes: plan Mostrador $ 29.000 + mantenimiento del sistema CRM $ 10.000 (incluye el 0800, si lo quieren) =
    $ 39.000. Sin otros cargos ni descuentos. La puesta en marcha se lista como parte de la propuesta, sin precio aparte.
  - Sin piloto, sin oportunidades, sin "lo observado → qué lo resuelve" y sin preguntas para la reunión (estaban en la v1).
  - Capacidad: se define con ellos en el relevamiento, según su guardia. Sin la promesa de dos llamadas simultáneas.
  - Emergencias: priorización de la atención, no un servicio de emergencias. Se promete detectar señales y priorizar, nunca
    detectar siempre. SIM define qué es emergencia y qué se dice si nadie atiende; no se toma solo un mensaje.
  - Datos de salud: una línea (sensibles; tratamiento y retención se acuerdan antes de salir en vivo), sin conclusiones
    legales. La minuta y los cuidados son para el staff.
  - Su WhatsApp actual no se toca salvo que SIM lo decida: punto a definir en el relevamiento.
  - Sin SMS, sin otros idiomas, sin cifras de redes, sin `/admin/`, sin reseñas, sin cita de un dueño, sin competencia.
  - Material de venta: no dice qué está construido (ver "A validar"). Sin logo ni marca de SIM: el nombre escrito.

## Estructura (v2)

1. **Portada y quiénes son:** h1 "Saber quién llama, y que lo urgente pase primero", cuatro cifras (24 h, CABA y GBA, 26, 2 a
   4 h), y "lo que nos pidieron" frente a "lo que incluye".
2. **La solución:** tres canales (línea, 0800 opcional, WhatsApp), el recorrido en cuatro pasos y el diagrama (quien llama →
   canales → agente que identifica y clasifica → su equipo; ficha y panel en la misma plataforma).
3. **Ficha, minuta y emergencias:** mock de la ficha con datos inventados, campos, carga, ejemplo de minuta, quién oye qué y el
   recuadro de emergencias.
4. **El panel:** mock con datos ilustrativos.
5. **Puesta en marcha y presupuesto:** tres pasos (relevamiento, configuración y pruebas, salida en vivo), quién hace qué, su
   WhatsApp, la tabla de presupuesto con dos aclaraciones y el pie de contacto.

## Afirmaciones y de dónde salen (leídas el 2-nov-2026)

Copia local del sitio: `scratch/prospectos/simtecuida/raw/txt/`. Cada cita se volvió a buscar ahí.

- **24 h, 365 días:** "Guardias de 12 y 24 horas los 365 días del año" y "La atención de coordinación funciona las 24 horas"
  ([Servicios](https://simtecuida.com.ar/servicios.html) y [Precios](https://simtecuida.com.ar/precios-cuidadoras-24-horas-caba.html)).
  168 horas por semana: cálculo de la base, parte 0.
- **CABA y GBA, hasta La Plata:** páginas de zona; "todos los municipios de Zona Sur hasta La Plata".
- **26 sanatorios, clínicas y hospitales:** conteo sobre las páginas de zona, recontado para este documento: 11 CABA, 4 norte, 5
  oeste, 6 sur. Las sedes de Trinidad cuentan por separado; el Británico, en CABA y en Vicente López.
- **Asignación en 2 a 4 horas:** "Asignación en 2 a 4 horas para internación o domicilio" (zona oeste; en norte, "en sanatorio o domicilio"). Es su promesa, no verificada; el
  documento dice "prometen".
- **Lo que nos pidieron:** el pedido de Laureano de arriba (D4).
- **Voz con acento argentino:** diferencial de Atentina (TTS propio).
- **Se presenta como asistente virtual, sin indicaciones médicas, pide lo mínimo en una emergencia:** parte 7.3 y partes 8.1 a
  8.3 de la base, que son nuestras y hay que validar con SIM.
- **Plan Mostrador, $ 29.000 por mes:** `landing/src/data/site.ts` y `tiers.price_ars` de la base (2-nov-2026). Es precio final
  (`COBROS.md`). El documento no lista los topes del plan.
- **Mantenimiento del sistema CRM, $ 10.000, incluye el 0800:** pedido de Laureano de la v2. Total: 29.000 + 10.000 = 39.000.
- **"Los minutos que entran por un 0800 descuentan el doble del plan":** `COBROS.md`, entrantes a 0800 ×2.
- **Fichas, minuta y panel:** nombres y números inventados o ilustrativos, rotulados en cada mock. Teléfonos con el formato 5555.
  El panel cierra: 186 consultas = 118 + 44 + 24 = 74 + 96 + 16 = 108 + 78 = 66 + 54 + 31 + 30 + 5; 78 derivadas = 21 + 20 + 19 +
  18; 5 emergencias = 2 + 1 + 1 + 1; 41 % = 76 de 186.
- **Contacto:** `landing/src/data/site.ts`.

## A validar antes de mandarlo

- **$ 10.000 por mes:** el pedido no dice "por mes" para ese monto. Se toma como mensual porque es mantenimiento y Mostrador es
  mensual (criterio del agente principal, a confirmar por Laureano).
- **$ 39.000 frente a la capacidad, lo más importante:** Mostrador publicado tiene 1 llamada a la vez, 300 minutos, 1 número y
  derivación a 1 persona (2 en la base). Tal cual, no hay rotación real y una segunda persona que llama, aunque sea una
  emergencia, encuentra la línea ocupada. La parte 7.6 de la base recomienda más capacidad. El documento titula "$ 39.000 por
  mes" y dice que la capacidad se define en el relevamiento: **no está definido qué pasa con el precio si la guardia pide más**.
  Sucursal ($ 99.000) tampoco resuelve la rotación: deriva a 2.
- **Minutos:** con el 0800, 300 minutos rinden 150. El minuto extra no se vende y la cuota corta al tope (`COBROS.md`): sin
  ajustar el límite, una línea con posibles emergencias puede dejar de atender a fin de mes.
- **Línea más 0800:** son dos números y Mostrador trae uno. El pedido incluye el 0800 en los $ 10.000; el costo por minuto y el
  plazo de alta con Anura están sin verificar. El documento no promete que sea gratis para quien llama (sin fuente en el repo).
- **Cobro:** el plan de $ 39.000 no existe como tier. Falta definir cómo se cobra (tier a medida o ajuste de límites, `COBROS.md`).
- **Puesta en marcha:** queda listada como incluida, sin precio aparte; se puede leer como sin cargo. Confirmar, porque incluye
  carga de clientes y soporte de la configuración.
- **Sin piloto:** antes había una etapa de prueba con decisión; ahora se pasa de pruebas a salida en vivo. Las funciones que siguen
  se comprometen por el precio mensual, y el plazo para construirlas sigue sin estimar (parte 7.5). El documento no da fechas.
- **Funciones presentadas como oferta, contra la parte 7.4 de la base:**
  - **Listo:** número geográfico, 0800, rotación (llama de a una persona, 20 s cada una), minuta hablada antes de marcar 1.
  - **Parcial:** WhatsApp de texto y notas de voz (probado solo con el número de Atentina; número de un cliente sin probar en
    real, alta simple pendiente de Meta). Agenda de contactos (teléfono, nombre, email, notas). Detección de emergencia
    configurable en el agente, **sin eval que la mida**.
  - **No existe:** ficha con DNI, estado de suscripción y cuidados; búsqueda por DNI o nombre; minuta con datos de la ficha;
    derivación o aviso al staff desde WhatsApp ("el aviso lleva la misma minuta", hoja 3); **llamadas de WhatsApp en el número de
    un cliente** (hojas 1 y 2); prioridad de emergencias y timbre simultáneo.
  - **Panel:** parte de las métricas no existe como tal (cliente, nuevo o sin identificar; por DNI o teléfono; emergencias y su
    demora; pasó a la siguiente; por motivo y fuera de horario, a verificar). Tabla de la parte 7.1.
- **Emergencia sin respuesta:** hoy el área solo tiene `fallback` `take_message`. El documento promete que no se toma solo un
  mensaje y que SIM define qué se dice: hay que construirlo antes de salir.
- **Prioridad con rotación secuencial:** con 20 s por persona y unos 15 a 27 s medidos de timbre, minuta y confirmación
  (`EQUIPO_TELEFONIA.md`), una emergencia tarda más si los primeros no atienden. "Una persona en 52 s" del mock es ilustrativo.
- **Reconocer por teléfono:** quien llama con el número oculto cae en el paso "pregunta". Sin verificar cómo llega el número en
  cada canal para este cliente. El teléfono reconoce, no autoriza: quién puede pedir qué (parte 8.2) se define en el
  relevamiento.
- **Su WhatsApp actual:** si está en la app WhatsApp Business, pasarlo a la API necesita coexistencia, con la sincronización
  incompleta. Si no se toca, se usa un número nuevo que **SIM tiene que publicar**: todo su sitio apunta al actual.
- **Datos de salud:** la base los marca como sensibles (Ley 25.326) y deja para un abogado si SIM entra en el art. 8. Consentimiento
  de las familias, retención de transcripciones y grabación, a resolver antes de salir. El documento no cita leyes. El presupuesto
  habla de "almacenaje de los pacientes y las consultas" (texto del pedido), y el resto del documento, de "clientes".
- **"Lo que nos pidieron":** resume el pedido de Laureano; confirmar que SIM lo planteó en esos términos, en especial "emergencia"
  y "suscripción" (lo publicado son abonos mensuales; a relevar).
- **Áreas del diagrama:** son supuestos; el staff real está a relevar. Las cuatro personas del mock son ilustrativas y no estiman
  su tamaño.
- **Otros idiomas:** venden atención en 10 idiomas; el documento no los menciona ni los promete, y el agente tiene voces
  argentinas. Puede surgir en el relevamiento.
- **Sitio:** puede cambiar; releer las cifras de la hoja 1 antes de mandarlo si pasa tiempo.

## Versiones

| Versión | Fecha | Qué cambió | Estado |
|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 2-nov-2026 | Primera versión, con piloto y oportunidades | cerrada (2-nov-2026) |
| [v2](versiones/v2/NOTAS.md) | 2-nov-2026 | Sin piloto ni oportunidades; presupuesto de $ 39.000 por mes; sin fondos oscuros | borrador |
