# BAIC Center / Grupo Signature: base de conocimiento para la reunión del 20-oct-2026

Reunión con **Edgardo Fernández Favaron**, presidente de Signature SA (Grupo Signature, Córdoba). El grupo es concesionario
oficial de BAIC (BAIC Center), Arcfox, Mitsubishi (MitsuCenter) y Foton (Córdoba Trucks). Este documento sirve para preparar
la reunión y como base de un agente posterior. Todavía no tiene fila en [`../seguimiento.md`](../archivo/seguimiento.md).

- **Fuentes, leídas el 20-oct-2026:**
  - los sitios del grupo: baicenter.com.ar (home, contacto y una ficha de modelo), arcfoxcordoba.com.ar, mitsucenter.com.ar
    y cordobatrucks.com.ar (home y posventa);
  - su perfil de LinkedIn, con la experiencia, las publicaciones, los comentarios, las reacciones y los intereses, leído
    desde el navegador con sesión;
  - la ficha de Google Maps de BAIC CENTER y prensa local (InfoNegocios, Hoy Día Córdoba, Punto a Punto, Perfil, Cba24n,
    iProfesional), con los links en la parte 9.
- **Copia local:** `scratch/prospectos/baicenter/raw/`, con el HTML de MitsuCenter, Arcfox y Córdoba Trucks. baicenter.com.ar
  devuelve 406 a `curl` y se leyó desde el navegador.
- **Partes 1 a 5:** datos. Las partes 6 a 8 son nuestras (pistas, caso de uso y base del agente) y hay que validarlas con
  Edgardo.

## 0. Resumen para la reunión

- **Quién es:** un vendedor de toda la vida. Fue 23 años gerente comercial de Centro Motor (Toyota) y en 2010 vendió los
  4 primeros Prius del país. En 2017 armó su propio grupo, que hoy tiene 4 o 5 marcas, 2 locales y un taller. Es early
  adopter: trajo el primer sedán eléctrico homologado (BAIC EU5), el TITO de Coradir y Arcfox.
- **Su dolor, con evidencia pública:**
  - dos reseñas de Google se quejan de WhatsApp sin respuesta ("5 días esperando respuesta", con el contacto "en línea");
  - otra cuenta que en el local "tomaron el número y me despacharon", y que al día siguiente le mandaron solo precios;
  - en el sitio de BAIC no funcionan los botones **"Solicitar turno"** ni **"Solicitar Test Drive"**;
  - el menú "Usados" de BAIC y Arcfox lleva a una página que da error 500.
- **Su presión:**
  - desde mayo de 2025 hay **otro concesionario BAIC en Córdoba**, Familia Parra, con 373 reseñas, que también presentó
    Arcfox y "quiere alcanzar el top 10";
  - BAIC lanzó en julio de 2026 el **plan de ahorro de 84 cuotas**, que BAIC Center ya publicita en la home. Eso trae
    muchas consultas chicas y repetidas ("¿cuánto es la cuota?").
- **El caso a mostrar:** un **asesor de IA de guardia** para BAIC, Arcfox, Mitsubishi y Foton:
  1. contesta cada consulta de WhatsApp en segundos, con texto o nota de voz con acento argentino, y atiende el teléfono;
  2. **devuelve la llamada al interesado en menos de un minuto**;
  3. califica la consulta (modelo, uso, plan de ahorro o contado, permuta, plazo);
  4. agenda el test drive o el turno de taller;
  5. le pasa al vendedor una ficha con todo.

  Es lo que pide la reseña: de "5 días esperando" a "te llamo en 40 segundos".
- **El momento wow:** en la reunión, Edgardo le escribe al WhatsApp de la demo "Hola, quiero info de la BJ30 híbrida en
  plan de ahorro". Recibe la respuesta con una nota de voz y, segundos después, **le suena el celular**: es el agente, que
  lo llama por esa consulta y le ofrece un test drive para el sábado.

## 1. La persona: Edgardo Fernández Favaron

- **Cargo actual:** presidente de Signature SA desde mayo de 2017. También figura como director ejecutivo de MitsuCenter
  (desde abril de 2017), de BAIC Center Córdoba (desde marzo de 2018) y de Foton Trucks Córdoba (desde enero de 2018). La
  prensa y Córdoba Trucks lo presentan como "director comercial del Grupo Signature" y como CEO.
- **Antes:** gerente comercial superior de Centro Motor S.A. (Toyota, Córdoba) de noviembre de 1993 a marzo de 2017,
  23 años y 5 meses. Al irse, en marzo de 2017, dijo que lo próximo "sería un emprendimiento personal" (InfoNegocios).
- **Hitos:**
  - 2010: vendió las 4 primeras unidades del Toyota Prius en el país y se quedó una para él;
  - 2023: Grupo Signature cumple 6 años;
  - junio de 2026: BAIC Center cumple 9 años y lanza Arcfox.
- **Estudios:** Colegio Nacional de Charata (Chaco).
- **LinkedIn:**
  - 731 seguidores, 437 contactos, cuenta Premium, con el botón **"Concertar una cita"** activo;
  - titular: "Presidente de empresa en SIGNATURE SA | CONCESIONARIA DE AUTOMÓVILES, UTILITARIOS Y CAMIONES **Mejora
    continua, Estrategia de marketing**";
  - aptitudes visibles: planificación de negocios, **satisfacción del cliente** y gestión comercial.
- **Qué publica** (casi todo de 2024 y 2025, nada en el último año):
  - entregas de flotas Foton: EPEC por licitación pública, AFEMA SA (volcadores y mixer), MD Forniture, HDS Technology;
  - exposiciones: Expo Rural Jesús María 2024, Expo Camarco 2025, Auto Show 2025 y ExpoAgro;
  - el lanzamiento del sitio nuevo de Córdoba Trucks (2024): "¡Estoy emocionado de anunciar el lanzamiento de nuestro
    NUEVO sitio web!";
  - el lanzamiento del BAIC EU5 eléctrico;
  - dos búsquedas de vendedores para Foton (#hiring).
- **Qué sigue y comenta:**
  - Grupo Corven (importador de Foton) y su gerente de producto, Federico Reser;
  - Planeta Camión y otros concesionarios Foton.
  - Entre las Top Voices sigue **solo a una**: Andrés Bruzzoni, fundador de Samu.ai, sobre "forecast y visibilidad de
    pipeline para equipos de ventas B2B". Es la única señal directa de interés en herramientas de IA para ventas.
- **Tono:** entusiasta, con muchos signos de exclamación y emojis. Su frase repetida es "Apoyando a las empresas 💪". La
  empresa usa el lema "El cliente primero".
- **Cómo responde las reseñas:** contesta en persona, incluso las malas. A una queja por WhatsApp respondió: "le pedimos
  disculpas... sirve para mejorar nuestros procesos de atención". A una clienta de 2018 le propuso "Así cambiás tu BAIC X35
  por X55!". **Esa última es, textual, la idea de una campaña de recompra a la base de clientes.**

## 2. La empresa: Grupo Signature (Signature SA)

### 2.1 Marcas y cronología

| Año | Qué suma | Unidad o sitio |
|---|---|---|
| 2017 | Mitsubishi Motors. Según su LinkedIn, llegaron "a los primeros puestos de ventas en el país" | MitsuCenter, mitsucenter.com.ar |
| 2018 | BAIC (autos y SUV) y Foton (utilitarios, camiones y pick-ups) | BAIC Center, baicenter.com.ar; Córdoba Trucks, cordobatrucks.com.ar |
| 2020 | Zanella Z-Truck, de producción nacional | Córdoba Trucks |
| 2022 | Coradir: el auto eléctrico TITO y el utilitario TITA. También NeumaCenter, neumáticos para camiones | "Signature Motors" |
| 2023 | Corven Buses, según la prensa | — |
| 2026 (junio) | Arcfox, la línea premium 100 % eléctrica de BAIC | arcfoxcordoba.com.ar, que remite a BAIC Center |

- **Otros servicios:** usados seleccionados, posventa, repuestos, accesorios, chapa y pintura, créditos prendarios y
  leasing.
- **Vigencia por confirmar:** LinkedIn menciona también CVN Motors (Grupo Iraola). Los sitios de hoy muestran solo BAIC,
  Arcfox, Mitsubishi y Foton (con Zanella en posventa). Hay que confirmar con él qué marcas siguen.

### 2.2 Locales, horarios y contacto

| Local | Dirección | Qué hay | Horario publicado |
|---|---|---|---|
| Casa central | Av. Colón 4875 (esq. Bicentenario de la Industria Nacional), Complejo Terra Forte, Loc. 2 (BAIC/Arcfox) y Loc. 3 (Mitsubishi/Foton), Córdoba | Showroom de 800 m², atención comercial y posventa completa | BAIC, Arcfox y MitsuCenter: lu a vie de 9 a 20 y sáb de 9 a 13. Córdoba Trucks: lu a vie de 9 a 18 y sáb de 9 a 13 |
| Sucursal Norte (Foton) | Av. Circunvalación Norte Agustín Tosco, colectora de Easy, Polígono Punto Norte, naves 3 y 4, Córdoba | 2.500 m². Departamento de ventas corporativas para flotas y división de camiones pesados | Lu a vie de 9 a 18 y sáb de 9 a 13 |

| Canal | Dato | Nota |
|---|---|---|
| Teléfono fijo | (0351) 589-3322 | El mismo para todas las marcas |
| WhatsApp 1 | +54 9 351 353-0785 | El mismo en los 4 sitios, para todas las marcas y los 2 locales. Es el botón flotante de los sitios |
| WhatsApp 2 | +54 9 351 555-0814 | Igual que el 1. Es el teléfono que muestra Google Maps |
| Email | Info@baicenter.com.ar (también lo usa Arcfox), Info@mitsucenter.com.ar, Info@cordobatrucks.com.ar | — |
| Formulario web | baicenter.com.ar/contacto: nombre, apellido, email, teléfono y consulta | "Responderemos tu consulta en el menor tiempo posible" |

- **Redes:** Instagram @baic_center, @mitsucentercordoba, @arcfoxcordoba, @cordoba.trucks y @signature_cordoba. Facebook
  baic.center, mitsucenter.cordoba y effventas ("Signature Motors Córdoba").
- **Lo importante:** **dos WhatsApp y un fijo reciben las consultas de unas 5 marcas, 2 locales, ventas, posventa,
  repuestos y flotas**, mezcladas. El sitio no dice quién atiende cada cosa.

### 2.3 Financiación

- **Bancos:** Bancor, Banco Nación, Santander y Galicia, más créditos propios del concesionario, prendarios y leasing
  (Punto a Punto, junio de 2026; LinkedIn).
- **Plan de ahorro BAIC Plan:** lo lanzó la marca en julio de 2026. Son 84 cuotas, con el 100 % del auto financiado.
  - Modelos: X35, BJ30 4x2 HEV, X55 II Hybrid y Arcfox T1.
  - Cuota inicial del 21-jul al 20-ago de 2026, según iProfesional y 16 Válvulas: entre $ 736.104 (X35) y $ 914.759 (BJ30).
  - En junio, Edgardo dijo que estaba armando un plan propio, y la home de BAIC Center ya muestra el banner "Llegó el plan
    de ahorro: 84 cuotas sin interés".
  - **Corrección (22-oct-2026, Laureano): BAIC Center no ofrece plan de ahorro.** El banner de sus sitios es el BAIC Plan
    de la marca (imagen con la foto del local, link a Arcfox), y el plan propio de junio no salió. Lo confirmado es la
    financiación con los cuatro bancos y el crédito propio (Edgardo, Punto a Punto, 29-jun-2026); la nota no menciona
    leasing ni prendarios, que salen solo de LinkedIn. Las menciones al plan de ahorro de este documento (D8, 7.5, 8.2,
    8.3) quedan sin efecto.

### 2.4 Posventa

- **BAIC:** garantía de 7 años o 100.000 km, lo que ocurra primero. Edgardo la presenta como "la única marca" que la da.
- **Mitsubishi:** garantía de 3 años o 100.000 km.
- **Foton y Zanella:**
  - mantenimiento preventivo, reparación, diagnóstico computarizado, repuestos originales con trazabilidad, garantía oficial
    y "seguimiento de cada intervención";
  - taller móvil Foton;
  - objetivo declarado: "minimizar tiempos de parada".
- **Cómo se pide turno hoy:**
  - en Córdoba Trucks, "Agendá tu turno: contactanos" por WhatsApp o por teléfono;
  - en BAIC, el botón "Solicitar turno" no hace nada (parte 5).

### 2.5 Clientes que muestran

- **Flotas Foton:**
  - EPEC (Empresa Provincial de Energía de Córdoba), por licitación pública: Aumark S3-916;
  - AFEMA SA: Auman C volcadores 8x4 y mixer;
  - MD Forniture y HDS Technology: TM1;
  - transportistas particulares.
- **Autos:** particulares, con reseñas de compradores de X35, X55 y BJ30.

## 3. Productos y precios de referencia

Precios en dólares, salvo que se indique otra cosa. **No son una lista oficial del concesionario**: salen de prensa y de
avisos. El agente no los da sin una lista vigente de Edgardo.

### 3.1 BAIC (BAIC Center)

| Segmento | Modelos en el sitio | Referencia |
|---|---|---|
| SUV | X35 Luxury, X55 II, **X55 II Hybrid** (híbrida no enchufable de rango extendido), X55 Plus | X55 II, de US$ 31.900 a 33.500; X55 Plus, de US$ 39.950 a 42.500 (avisos de octubre de 2026) |
| Todoterreno | BJ30 4x2 y 4x4 (híbrida), BJ40, BJ40 PRO, BJ60, BJ80 | BJ30 híbrida, de US$ 31.900 a 37.500; BJ40 Pro, de US$ 51.500 a 54.500; BJ60, de US$ 69.900 a 78.600 (avisos) |
| Sedán | EU5 (eléctrico, unos 400 km de autonomía), U5 Plus | EU5: US$ 39.900 al lanzamiento (2025) y US$ 23.900 de referencia en junio de 2026 |

- **Equipamiento destacado** (X55 II Hybrid): cámara 360°, vista bajo carrocería, frenado autónomo de emergencia, crucero
  adaptativo, detector de punto ciego y estacionamiento autónomo.
- **Argumentos de la marca:** BAIC fabrica para Mercedes-Benz en China y Edgardo repite que "es el mayor fabricante de
  eléctricos". La garantía es de 7 años.

### 3.2 Arcfox (eléctricos premium, desde junio de 2026)

| Modelo | Tipo | Dato | Precio de lanzamiento en Córdoba (Cba24n, 27-jun-2026) |
|---|---|---|---|
| T1 | SUV subcompacto urbano | 320 km, carga bidireccional | US$ 29.500 |
| Kaola S | Monovolumen de 5 plazas con puertas corredizas | 500 km; del 30 al 80 % en 26 min | US$ 33.800 |
| T5 | SUV mediano | 250 CV, 520 km, 5 estrellas C-NCAP | US$ 39.600 |
| S5 | Sedán | 250 CV, de 0 a 100 en 7 s, 560 km | US$ 39.800 |

Edgardo dice que cargar un eléctrico cuesta "cerca del 15 %" de lo que cuesta el combustible.

### 3.3 Mitsubishi (MitsuCenter)

L200 GLS 6AT 4WD y Outlander 2.5 GLS AT Full.

### 3.4 Foton (Córdoba Trucks)

- **Modelos:** Aumark y Nuevo Aumark 615, Wonder (ultraliviano), TM, Tunland V7, G7 y V9 (pick-ups; la V9 es híbrida de
  48 V), Auman C, D, R y Nuevo Auman R (pesados), y eAumark (eléctrico).
- **Socios de la marca:** Cummins, ZF y Daimler.
- **Importador:** Grupo Corven.

## 4. Competencia y contexto

- **Familia Parra (BAIC):**
  - concesionario oficial BAIC desde abril de 2025, en Av. Castro Barros 1250, Córdoba;
  - 3,6 estrellas con 373 reseñas en Google; BAIC Center tiene 4,0 con 77;
  - la presentación de Arcfox del 27-jun-2026 que cubrió Cba24n fue en su local;
  - Perfil tituló: "De la mano de Parra, BAIC quiere alcanzar el top 10 en ventas";
  - **en la misma ciudad, el mismo cliente consulta a los dos concesionarios BAIC, y gana el que contesta primero y mejor.**
- **Mercado:** según Punto a Punto, el plan de ahorro es cerca del 30 % de las operaciones del sector automotor.
- **Software para concesionarios en nuestro registro:** #182 Asofix (Grupo Tagle, Córdoba) y #163 Tecnom (CRM automotriz con
  IA), los dos como canal y sin respuesta. Si Signature usa uno, la integración con ese sistema puede ser el paso 2, y
  sirve como referencia.

## 5. Dolores detectados (con evidencia)

| # | Evidencia | Qué dice | Qué resuelve Atentina |
|---|---|---|---|
| D1 | Reseña en Google de hace unos 6 meses (Marcelo Suárez) | No contestan los WhatsApp aunque figuren en línea: lleva 5 días esperando respuesta | Respuesta en segundos, 24/7, en los dos WhatsApp |
| D2 | Reseña de hace unos 5 años (Guillermo Martínez), con respuesta del dueño | "Todavía estoy esperando lo que se comprometió enviarme por el WhatsApp" | El agente manda en el momento la ficha, el precio de referencia o el link, y deja asentado lo prometido |
| D3 | Reseña de hace alrededor de un año (Jesús Díaz), con respuesta del dueño | En el local no le ofrecieron forma de pago ni le cerraron la venta; le tomaron el número y al día siguiente le mandaron solo precios | Seguimiento a las 24 y a las 72 horas, por WhatsApp o por llamada, con la pregunta que falta (pago, permuta, test drive) |
| D4 | Sitio de BAIC, 20-oct-2026 | Los botones "Solicitar turno" y "Solicitar Test Drive" no funcionan: el primero no hace nada y el segundo vuelve arriba | Un link de WhatsApp o una llamada que agenda el turno o el test drive |
| D5 | Sitios de BAIC y Arcfox, 20-oct-2026 | El menú "Usados" lleva a mitsucenter.com.ar/usados/, que da error 500 (falta de compatibilidad de PHP) | El agente toma la consulta de usados y de permuta: marca, modelo, año y km |
| D6 | Los 4 sitios | 2 WhatsApp y 1 fijo para 5 marcas, 2 locales, ventas, posventa, repuestos y flotas | Clasifica la consulta y la deriva a la marca, el área y el vendedor que corresponde |
| D7 | LinkedIn (#hiring) | Buscan vendedores para Foton | El agente hace la primera respuesta y la calificación; el vendedor solo atiende consultas calificadas |
| D8 | BAIC Plan, 84 cuotas (julio de 2026) | Muchas consultas de bajo ticket y repetidas: cuota, requisitos, adjudicación | El agente explica el plan y toma los datos; el vendedor cierra |
| D9 | Horarios: cierran a las 20 (a las 18 en Trucks) y los sábados a las 13 | Las consultas de la noche y del domingo esperan, y en ese tiempo el cliente consulta en Familia Parra | Atención 24/7 por voz y WhatsApp |

## 6. Pistas de interés en mensajería de voz, WhatsApp e IA

**Directas (pocas):**

- **Interés en IA para ventas:** de todas las Top Voices de LinkedIn sigue solo a una, sobre IA para el pipeline comercial
  (Andrés Bruzzoni, de Samu.ai).
- **Le importa el proceso:** su titular dice "Mejora continua, Estrategia de marketing", y entre sus aptitudes figura
  "Satisfacción del cliente".
- **Reconoce el problema:** contesta las quejas por WhatsApp hablando de "mejorar nuestros procesos de atención".

**Indirectas (fuertes):**

- **Early adopter de tecnología:** el primer Prius, el primer eléctrico homologado y Arcfox. Su discurso es "innovación" y
  "movilidad inteligente": la home de Arcfox dice "El futuro de la movilidad inteligente", así que un asistente de IA encaja
  en el relato de la marca.
- **Invierte en digital, aunque con resultados flojos:** lanzó un sitio nuevo en 2024 con entusiasmo, pero los botones de
  turno no andan y la página de usados se cae.
- **Ya opera por WhatsApp:** botón flotante en los 4 sitios, mensaje precargado ("Hola! Les escribo desde la página...") y
  el turno de Foton se pide por WhatsApp. El canal está; falta quien conteste.
- **Necesita escala sin sumar gente:** busca vendedores, suma marcas (Arcfox) y canales (el plan de ahorro) y tiene un
  segundo competidor BAIC en la ciudad.
- **Clientes corporativos:** EPEC y flotas. Una línea que atienda las consultas de flota y de posventa de camiones, donde
  cada día parado cuesta plata, es una venta fácil de justificar.

**Lo que no hay:** ninguna mención pública de chatbots, CRM, call center ni agentes de voz. Hay que preguntarle qué usa hoy
(parte 8.4).

## 7. El mejor caso de uso: asesor de IA de guardia que responde y llama en menos de un minuto

### 7.1 La propuesta

Un agente por marca (BAIC/Arcfox, Mitsubishi y Foton), o uno solo que pregunta la marca, en los **dos WhatsApp actuales**
y en el **fijo**:

1. **Responde en segundos, 24/7**, por texto o nota de voz, según cómo escriba el cliente, con voz argentina y nombre propio
   (por ejemplo, "Sofía, de BAIC Center").
2. **Califica** con 5 preguntas: modelo, para qué lo usa, forma de pago (contado, plan de ahorro, crédito o leasing),
   permuta (marca, modelo, año y km) y plazo de compra.
3. **Llama al cliente en menos de un minuto** si dejó el teléfono o escribió fuera de horario y acepta. La llamada sale
   por su número, con la consulta ya cargada: "Hola Marcelo, te llamo de BAIC Center por la BJ30 híbrida que consultaste".
4. **Agenda** el test drive o el turno de taller y lo confirma por WhatsApp.
5. **Le pasa al vendedor una ficha:** "Caliente: BJ30 HEV, plan de ahorro, permuta Gol 2015 con 120.000 km, test drive el
   sábado a las 10". Con el resultado de la conversación y la grabación, si se activa.
6. **Hace seguimiento** a las 24 y a las 72 horas a quien no cerró (D3), y avisa la adjudicación o los vencimientos del plan
   de ahorro.

### 7.2 Por qué es el mejor caso

- **Valor medible:** en autos, la primera respuesta decide a qué concesionario va el cliente, y en Córdoba hay dos BAIC.
  Hoy hay reseñas con 5 días sin respuesta. Métrica del piloto: tiempo a la primera respuesta, porcentaje de consultas
  atendidas fuera de horario, test drives agendados y consultas calificadas que recibe el vendedor.
- **El cliente no cambia nada:** mismos números, mismos vendedores. No reemplaza a nadie y llena la agenda de los que
  están.
- **Wow inmediato:** un auto que "te llama" a los 40 segundos de escribir. Es la experiencia premium que promete Arcfox.
- **Ya lo tenemos hecho:** agente de voz telefónico, WhatsApp con texto, notas de voz y llamadas de WhatsApp atendidas por
  el agente, llamada saliente por API (`POST /api/v1/calls` con `phone`), voces argentinas y apertura pregenerada. Ver la
  parte 7.4.

### 7.3 Guion de la demo en la reunión (5 minutos)

1. **Antes de la reunión:**
   - crear el agente `baicenter_demo` en el cliente `atentina`, con la base de la parte 8 y la voz `sofia`;
   - rutear el WhatsApp de demo a ese agente para el número de quien vaya a probar (`wa_routes`, regla por contacto). Si
     Edgardo prueba con su celular, hay que pedirle el número en la reunión y agregarlo a la regla.
2. **En vivo:** Edgardo escribe "Hola, quiero saber cuánto sale la BJ30 híbrida y si entra en el plan de ahorro". Recibe
   una nota de voz que explica el plan, le pregunta si tiene un usado para entregar y le ofrece un test drive.
3. **El wow:** el agente le pregunta "¿Te llamo ahora y lo vemos en 2 minutos?". Al aceptar, **le suena el celular**. Es la
   llamada saliente por API al número que dio, disparada a mano por nosotros durante la demo. Automatizarla es el paso del
   piloto.
4. **Cierre:** le mostramos en el panel la conversación, el resumen y el resultado, que es lo que recibiría su vendedor.
   Comparación final: "La reseña de Google dice 5 días; esto fueron 40 segundos".
5. **Alternativa sin WhatsApp:** el agente lo llama directo a su celular, o lo llama él a un número de Atentina ruteado
   al agente de demo. El 0810 no sirve: desde el 19-oct es de Erpwoosync.

### 7.4 Qué hay hoy y qué falta

| Pieza | Estado |
|---|---|
| Agente de voz entrante (número Anura o 0810) | En producción |
| WhatsApp: texto, notas de voz y llamadas de WhatsApp atendidas por el agente | En producción. El número del cliente se conecta por Embedded Signup, que espera la aprobación de Meta, o a mano |
| Llamada saliente individual por API | En producción. Disparo manual en la demo |
| Llamada automática a cada consulta nueva (speed-to-lead) | **Falta:** un disparador desde la conversación de WhatsApp o desde el formulario web hacia `POST /api/v1/calls` |
| Seguimiento a las 24 y 72 horas y recompra a la base (X35 → X55) | Campañas de WhatsApp: desplegadas. Campañas de llamadas: implementadas, **sin desplegar** ([`../../LLAMADAS_SALIENTES_PLAN.md`](../../docs/LLAMADAS_SALIENTES_PLAN.md)) |
| Agenda real de test drives y turnos, y stock | **Falta:** una app por cliente con herramientas ([`../../archive/APPS.md`](../../docs/archive/APPS.md)) o la integración con su CRM o su sistema de gestión, si tiene |
| Ficha al vendedor | Hoy queda en el panel y en el resultado de la conversación. Mandarla al WhatsApp del vendedor es un paso a definir |
| Grabación | Existe (`record_audio`), apagada. Antes de usarla con un cliente real hay que avisar a quien llama y corregir la política de privacidad de la landing |

### 7.5 Fases sugeridas (para charlar, no para la primera reunión)

1. **Piloto de 30 días con BAIC/Arcfox:** el WhatsApp 1 y el fijo; respuesta, calificación y ficha al vendedor.
2. **Plan de ahorro:** consultas de suscriptores (cuota, adjudicación, licitación) y avisos por campaña.
3. **Posventa:** turnos y recordatorios de service. La garantía de 7 años de BAIC probablemente exige los services
   oficiales, a confirmar: es retención y facturación de taller.
4. **Foton y flotas:** consultas de las empresas, repuestos y turnos de camiones, en la Sucursal Norte.
5. **Base de clientes:** recompra (la idea de Edgardo: "cambiás tu X35 por X55") y la encuesta de satisfacción después de
   la entrega o del service.

## 8. Base para el prompt del agente

### 8.1 Rol y tono

- **Rol:** "Sos Sofía, del equipo de BAIC Center Córdoba, concesionario oficial BAIC y Arcfox del Grupo Signature, en Av.
  Colón 4875, Complejo Terra Forte. Ayudás a quien consulta a elegir su BAIC o su Arcfox, a entender cómo pagarlo y a
  coordinar un test drive o un turno de taller."
- **Tono:** cálido, de vos, entusiasta pero sin exagerar, frases cortas. Por teléfono: una pregunta por vez.
- **Lema de la casa:** "El cliente primero".

### 8.2 Reglas

1. **Precios:**
   - no dar precios ni cuotas que no estén en la lista vigente que mande el concesionario;
   - sin lista: "el precio del día te lo confirma un asesor; ¿te lo mando por WhatsApp?";
   - los de la parte 3 son solo para la demo y se dicen "de referencia".
2. **Stock y colores:** no confirmarlos. Los confirma el vendedor.
3. **Plan de ahorro:** explicar cómo funciona (84 cuotas, 100 % financiado, adjudicación). Las condiciones y la cuota del
   mes salen de la lista vigente. No prometer la fecha de adjudicación.
4. **Permuta:** tomar marca, modelo, versión, año, km y estado. No tasar.
5. **Garantía:** BAIC, 7 años o 100.000 km; Mitsubishi, 3 años o 100.000 km. Los detalles de cobertura los confirma
   posventa.
6. **Derivar:**
   - Foton, Zanella, camiones y flotas: a Córdoba Trucks, en la Sucursal Norte;
   - Mitsubishi: a MitsuCenter;
   - siempre al mismo número: el grupo comparte los canales.
7. **Horarios:** decir el horario de la parte 2.2. Fuera de horario, agendar el contacto y no prometer una hora que nadie
   va a cumplir.
8. **Cerrar con un próximo paso concreto:** test drive, turno, llamada del asesor con día y franja, o el envío de la ficha.
   Nunca "te contactamos" sin más (D3).

### 8.3 Triage y datos

| Salida | Cuándo | Datos |
|---|---|---|
| **Venta 0 km, caliente** | Quiere comprar en menos de 30 días, sabe cómo pagar o pide test drive | Nombre, WhatsApp, modelo y versión, forma de pago, permuta, plazo y día del test drive |
| **Venta 0 km, tibia** | Compara o averigua el precio y la cuota, sin plazo | Lo mismo, sin el test drive. Seguimiento a las 72 horas |
| **Plan de ahorro** | Pregunta por la cuota, los requisitos o la adjudicación, o ya es suscriptor | Si ya es suscriptor: nombre, DNI o número de grupo y orden, y el motivo. Si es nuevo: como en 0 km |
| **Usado o permuta** | Quiere vender o entregar su usado, o comprar uno | Datos del usado (regla 4) y qué busca |
| **Posventa** | Service, garantía o una falla | Marca, modelo, dominio, km, qué necesita y la franja que prefiere |
| **Repuestos y accesorios** | Pide una pieza | Marca, modelo, año y la pieza |
| **Flota o empresa** | Compra para una empresa, una licitación o varias unidades | Empresa, CUIT, rubro, cantidad, tipo de unidad y contacto. Derivar a ventas corporativas de Foton o a un asesor de BAIC |
| **Otro** | Administración, reclamos o RR. HH. | El motivo, para derivarlo |

**Resumen al vendedor**, en una línea más los datos. Por ejemplo: "Caliente: X55 II Hybrid, plan de ahorro, permuta Corolla
2018, test drive el sábado a las 10".

### 8.4 Preguntas para la reunión (descubrimiento)

1. ¿Cuántas consultas entran por mes por WhatsApp, teléfono, formulario y Mercado Libre, y qué parte llega fuera de
   horario?
2. ¿Quién contesta los dos WhatsApp hoy? ¿Es un número de WhatsApp Business o la app común? ¿Tienen bandeja compartida?
3. ¿Usan un CRM o un sistema de gestión, como Asofix, Tecnom u otro? ¿Dónde quedan las consultas?
4. ¿Cuánto tardan en contestar una consulta, en promedio? ¿Lo miden?
5. Plan de ahorro: ¿operan BAIC Plan, uno propio o los dos? ¿Cuántos suscriptores tienen y qué preguntan?
6. Posventa: ¿cómo se piden los turnos? ¿Cuántos services hacen por mes? ¿Mandan recordatorios?
7. ¿Qué marcas siguen hoy (Zanella, Coradir, CVN, Corven Buses)?
8. ¿Les interesa que el agente llame (saliente) o solo que conteste?
9. ¿Pueden pasarnos una lista de precios vigente para armar el piloto?

## 9. Fuentes

- Sitios: https://www.baicenter.com.ar/, https://www.baicenter.com.ar/contacto/, https://arcfoxcordoba.com.ar/,
  https://mitsucenter.com.ar/, https://cordobatrucks.com.ar/ y https://cordobatrucks.com.ar/posventa/.
- LinkedIn: https://www.linkedin.com/in/edgardo-fernandez-favaron-7a95ba170/, con actividad, comentarios, reacciones e
  intereses.
- Google Maps: BAIC CENTER, Av. Colón 4875, 4,0 con 77 reseñas, filtradas por "whatsapp". BAIC - Familia Parra: 3,6 con 373
  reseñas.
- Prensa:
  - InfoNegocios, "Fernández Favaron deja Centro Motor" (17-mar-2017):
    https://infonegocios.info/infogerentes/fernandez-favaron-deja-centro-motor
  - InfoNegocios, nota del Prius (29-mar-2010):
    https://infonegocios.info/default/antun-se-agranda-favaron-se-electrifica-y-llega-el-auto-a-agua
  - Hoy Día Córdoba, 6 años del Grupo Signature (14-jul-2023):
    https://hoydia.com.ar/negocios-y-empresas/grupo-signature-el-concesionario-oficial-de-marcas-de-prestigio-mundial-cumple-6-anos-en-cordoba/
  - Punto a Punto, Arcfox y el plan de ahorro (29-jun-2026):
    https://puntoapunto.com.ar/baic-presento-en-cordoba-la-linea-premium-arcfox-y-prepara-su-plan-de-ahorro-propio
  - Cba24n, precios de Arcfox (27-jun-2026):
    https://www.cba24n.com.ar/cordoba-motor/arcfox-desembarco-en-cordoba--la-marca-premium-de-baic-llego-con-cuatro-modelos-electricos-y-estos-son-sus-precios_a6a401d5c9aa4f47e01784adf
  - Perfil, Familia Parra es concesionario BAIC (8-abr-2025):
    https://www.perfil.com/noticias/cordoba/la-empresa-china-baic-suma-concesionario-oficial-en-cordoba.phtml
  - iProfesional, BAIC Plan (23-jul-2026):
    https://www.iprofesional.com/autos/460654-china-baic-lanza-plan-de-ahorro-y-permite-comprar-el-bj30-con-cuota-menor-a-1-millon-de-pesos

## 10. Agente y pantalla Llamadas (20-oct-2026, sin desplegar)

- **Pantalla Llamadas** (`/outbound`, en el menú después de Conversaciones): agente, contacto de la agenda u
  otro número, motivo en texto libre (hasta 2000 caracteres) y Llamar. El agente llama con ese motivo como
  contexto. Detalle en [`../../GUIA_UI.md`](../../docs/GUIA_UI.md), "Llamadas".
- **Agente:** Sofía, de BAIC Center (`baicenter_sofia`, motor `classic`, voz `sofia`, resumen por email
  prendido). La definición está en `scratch/baicenter/agente.json`. Todavía no está creado en producción.
  - Apertura: "Hola {{nombre}}, ... Te llamo por la consulta que dejaste en nuestra página. ¿Tenés un minuto?".
  - Confirma el motivo en una frase, no pregunta lo que el motivo ya dice y toma los datos que faltan: área
    (ventas, soporte, administración u otro), detalle, modelo, forma de pago, usado para entregar, urgencia
    (alta, media o baja) y cuándo prefiere que lo llame una persona.
  - Resultados: Ventas, Soporte y Administración, cada uno con su variante "urgente", más Otra consulta,
    Sin interés, Volver a llamar (no podía hablar y dejó un horario) y Sin cierre.
- **Prueba local** (backend de desarrollo con el LLM real, por texto: `scratch/baicenter/prueba_local.py`):
  4 casos, todos con el resultado esperado. Por ejemplo: "BJ30 en plan de ahorro, con un Gol 2015" dio
  Ventas · urgente con los 9 datos; "service de los 20.000 de mi X55" dio Soporte; "ya compré en otro lado"
  dio Sin interés; "estoy manejando, llamame mañana a las diez" dio Volver a llamar.
  - Pendiente: a veces pregunta la forma de pago aunque el motivo ya la dice.
- **Cómo desplegar** (fuera de las llamadas en curso):
  1. recrear `app` y `agent` (`make up-agent`; corta las llamadas en curso). No hay migración.
  2. crear el agente por la API con `scratch/baicenter/agente.json`, en el cliente `atentina` para la
     demo o en uno propio de BAIC. Para salientes, el cliente necesita minutos salientes en el tier y un
     número de origen.
  3. probar con números propios desde Llamadas.
