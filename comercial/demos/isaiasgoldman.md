# Isaías Goldman SA: base de conocimiento para la propuesta (21-oct-2026)

Propuesta para **Isaías Goldman**, presidente y fundador de Isaías Miguel Goldman SA (Córdoba): casa de climatización,
calefacción, refrigeración y equipamiento comercial, con repuestos, instalación, service, obras y cursos de oficio. El
usuario habló con él por teléfono y le pidió que le contara la oferta. Este documento sirve para preparar esa propuesta y
como base de un agente posterior. Todavía no tiene fila en el CRM.

- **Fuentes, leídas el 21-oct-2026:**
  - el sitio isaiasgoldmansa.com (home, categorías, fichas de producto, "Consultar precio", contacto, quiénes somos,
    cursos, sitemap), con `curl` y desde el navegador;
  - la ficha de Google Maps (horarios y reseñas, ordenadas por "valoración más baja" y "más recientes");
  - Instagram y Facebook (solo lo público, sin sesión), Linktree;
  - prensa: 4 notas de InfoNegocios (2015, 2018, 2019 y 2021) y su ficha de empresa (InfoTarjetero);
  - Google Maps de la competencia en Córdoba y los sitios de Climatización Polar, Torralba y Grupo Mondino.
  - Links en la parte 9.
- **Copia local:** `scratch/prospectos/isaiasgoldman/raw/`, con el HTML del sitio y de los competidores, el sitemap y
  `google-maps-resenas.txt` (extractos de las reseñas).
- **No se encontró:** LinkedIn de Isaías ni de sus hijos, entrevistas a Isaías después de 2018, ni datos de facturación.
- **Partes 1 a 5:** datos. Las partes 6 a 8 son nuestras (pistas, caso de uso, oferta y base del agente) y hay que
  validarlas con él.

## 0. Resumen para la propuesta

- **Quién es:** Isaías Miguel Goldman fundó la empresa hacia 1990-1992, como continuación del negocio de su padre,
  "pionero en el rubro de la refrigeración". Pasó de un local de 350 m² con 3 personas a un edificio de 4.500 m² en
  Bv. Bulnes y Pringles, con unos 50 empleados. Hoy la manejan él y sus hijos Jonatan (director comercial) y Carolina
  (directora). Su frase en la prensa: "Nos gusta hacer cosas donde podemos responder".
- **Qué hace la empresa:** vende aires (hogar, comercio y grandes superficies; marca propia "Goldman" sobre BGH, Midea,
  Gree y York), calefacción (calderas Peisa y BGH, radiadores), termotanques solares, heladeras y exhibidoras
  comerciales, repuestos, refrigerante y herramientas. También instala, hace service, hace obras de climatización
  central y dicta cursos presenciales de instalación y reparación de aires. Vende a público, instaladores y empresas
  (Arcor, Georgalos, Mostaza, Porta, entre otras). Es 50 % B2B y 50 % B2C (2018).
- **Su dolor, con evidencia pública:** 4,2 en Google con 1.671 reseñas. Las quejas son de atención, no de producto:
  - **teléfono que no atiende o no devuelve:** "marque al num que figura, nunca atienden"; "siempre te dicen que te
    vuelven a llamar, y no lo hacen";
  - **presupuestos lentos:** "La debilidad es la atencion telefónica y via mail para pedir presupuestos";
  - **técnico que no llega y nadie avisa:** "esperé toda la tarde que venga el técnico que nunca llegó ni tampoco
    avisaron";
  - **precio distinto por WhatsApp y en el local** ("casi el doble");
  - **colas en el mostrador:** "Se tarda muchísimo para atender".
- **Por qué ahora:**
  - el sitio tiene 266 productos **sin ningún precio**: todo termina en "Consultar precio", un formulario por email, o en
    el único WhatsApp (351 386 2886);
  - **la temporada de aires arranca en noviembre**, y con ella el pico de consultas, instalaciones y reclamos;
  - cierran al mediodía (de 13 a 14:30) y a las 18:30, y los sábados a las 13.
- **La propuesta (21-oct-2026, parte 7.1):** atención 24/7 en **0800/0810, WhatsApp y chat en la web**, con triage
  (ventas, instalaciones, productos, precios), respuestas a lo general, **derivación a vendedores y soporte** (transferencia
  de la llamada, relay de WhatsApp, paso a persona en el chat) y **observabilidad para el dueño**: todas las comunicaciones
  de todos los canales en un panel, con métricas por canal y por tipo de consulta. Falta construir la transferencia
  telefónica, el relay de WhatsApp, el chat web y parte de las métricas (parte 7.4).
- **El caso a mostrar:** **"el especialista de guardia"**, un agente en el WhatsApp y en el teléfono que:
  1. cotiza con la lista vigente que ellos le dan: equipo, kit e instalación;
  2. pregunta lo que hace falta para recomendar (ambiente, m², orientación, frío solo o frío/calor);
  3. agenda la instalación o la visita técnica, la confirma el día anterior y avisa si hay demora;
  4. toma reclamos de posventa con número de caso;
  5. le deja al vendedor o al técnico una ficha con todo.
- **El momento wow:** Isaías (o Jonatan) escribe "¿cuánto me sale un split inverter de 3000 frigorías instalado?". Recibe
  en segundos una nota de voz con acento argentino que le pregunta los m² y si lo quiere frío/calor, le cotiza
  con la lista de la demo y le ofrece turno de instalación. Después llama a la línea de demo **a las 13:30**, la hora en
  que su local está cerrado, y lo atiende el mismo agente.

## 1. La persona: Isaías Goldman

- **Nombre completo:** Isaías Miguel Goldman. Presidente de Isaías Miguel Goldman SA (InfoTarjetero, 2026).
- **Origen:** su padre fue "pionero en el rubro de la refrigeración" y la empresa lo continúa "en cierta forma"
  (InfoNegocios, 2018). Jonatan dice que la familia es la tercera generación en el rubro y la segunda al frente de la
  empresa (2021).
- **Fundación:** 1992 según la ficha de la nota de 2018; la de 2019 dice que en 2020 cumplían 30 años. El sitio y
  Facebook dicen "casi 3 décadas" y el banner de "Quiénes somos" dice "30 años".
- **Hitos:**
  - antes de 2014: local en barrio San Vicente, donde "la imagen no coincidía" con lo que buscaba el público
    (Jonatan, 2015). Hay un listado viejo de "Refrigeración Isaías Goldman" en San Jerónimo 2760 (San Vicente) con
    1,9 estrellas en argentino.com.ar: **probablemente** es ese local (no verificado);
  - hacia 2014: mudanza a Bulnes y Pringles, a un ex Supermercados Americanos con fachada restaurada, showroom y
    **galería de arte** en el primer piso (3.000 m² en 2015 y 4.500 m² en 2018);
  - 2018: unidad de arquitectos e ingenieros para climatización central de edificios grandes;
  - escuela de oficios (cursos de instalación y reparación de aires).
- **Familia y decisiones:** las decisiones son familiares: Isaías, Jonatan y Carolina (2021). Gerente comercial: Oscar
  Alejandro Gómez. Comercial: Jesús López. Administración: Lorena Jastreb (InfoTarjetero).
- **Qué dijo en la prensa** (2018, la única nota con citas suyas):
  - "Nos gusta hacer cosas donde podemos responder";
  - "Siempre creí que es bueno tener el depósito lleno de mercadería, aunque esa política hay que soportarla, claro";
  - "Nuestros clientes muchas veces no saben qué marca están comprando".
- **Tono (inferido):** comerciante de la vieja escuela, de stock y de mostrador; la palabra que repite la empresa es
  **responder**. El lema del sitio es "Somos el especialista" y el logo dice "Isaías Goldman, el especialista". No usa
  LinkedIn (no se encontró perfil) y no da entrevistas desde hace años: la voz pública es la de Jonatan y Carolina.
- **Arte:** además de la galería del local, un "Isaias Golman" (sic) figura como colaborador de la muestra Arty Sesion
  del Córdoba Shopping. Es un dato débil, pero sirve para la charla.
- **Hay que preguntarle** si la decisión sobre atención y canales la toma él o Jonatan (director comercial, que en 2015
  quería "armar un gran equipo de ventas para comenzar a delegar operaciones grandes fuera de la familia").

## 2. La empresa: Isaías Miguel Goldman SA

### 2.1 Datos

| Dato | Valor | Fuente |
|---|---|---|
| Razón social | Isaías Miguel Goldman Sociedad Anónima | InfoTarjetero |
| CUIT | 30-70778610-4 | InfoTarjetero. **No verificado en ARCA** |
| Rubro | Comercialización, instalación y mantenimiento de climatización y refrigeración | Sitio, InfoTarjetero |
| Empleados | ~50 (2018 y 2021), la mitad en el área comercial (repuestos y equipamiento); "más de 30" en 2015 | InfoNegocios |
| Tamaño | Pyme Tramo I (2018); InfoTarjetero la marca "Grande" | InfoNegocios, InfoTarjetero |
| Sucursales | Ninguna: una sola casa central. También venden con vendedores en la calle | InfoNegocios 2021 |
| Mercado | Córdoba, con clientes de todo el país; 50 % B2B y 50 % B2C | InfoNegocios 2018-2019 |
| Marcas | Marca propia "Goldman" ("le damos manija"), BGH, Midea, Gree, York, Peisa, Briket; en 2021 también LG, Carrier y Surrey | Sitio, InfoNegocios 2021 |

**Diferencial que declaran:** "Nuestro fuerte es el postventa" (Jonatan, 2021). Gestionan ellos la garantía porque las
de los services oficiales son "lentas", y tienen técnicos propios y recomendados de los que se hacen responsables. **Las
reseñas dicen lo contrario** (parte 5).

### 2.2 Local, horarios y contacto

| Dato | Valor | Nota |
|---|---|---|
| Dirección | Av. (Blvd.) Eduardo Bulnes 1192 esq. Pringles, Córdoba (X5004EFP) | Única sede. Aula taller de los cursos en el mismo lugar |
| Horario | Lu a vie de 8:30 a 13 y de 14:30 a 18:30; sáb de 8:30 a 13; dom cerrado | **Solo en Google Maps.** El sitio no publica horario |
| Teléfono y WhatsApp | 351 386 2886 (`wa.me/543513862886`) | El mismo número en el sitio, Maps, Facebook, Linktree e InfoTarjetero. Es el único teléfono del sitio |
| Otro fijo | 351 589 0033 | Solo aparece en una respuesta del propietario a una reseña (hace un mes) |
| Email | info@isaiasgoldmansa.com | En el sitio está ofuscado (protección de Cloudflare) |
| Formulario | /contacto/: nombre, email, teléfono y mensaje | El botón "Consultar precio" de cada producto lleva acá, con el producto precargado. **No se envió** (regla de no enviar formularios) |
| WhatsApp del sitio | Botón flotante (GetButton) "Envíanos un mensaje", con el texto "¡Hola! Quisiera asesoramiento de un especialista" | Funciona: abre wa.me con el número correcto. No se mandó mensaje |

- **Redes:**
  - Instagram @isaias_goldman: 5.361 seguidores, 1.162 seguidos. Destacadas: Cursos, Local, Comercios, Hogar, Página
    web, Opiniones y Obras. Publica piezas de "Obra de climatización", "Vení a conocer todo lo que tenemos", "¿Sabías
    que?" y "Kit de instalación". **Los comentarios no se pudieron leer** (Instagram pide sesión).
  - Facebook /Isaiasgoldman: 12 mil seguidores, rango de precios "$$"; publicó un video el 20-oct-2026. Comentarios no
    revisados.
  - Linktree: solo WhatsApp y la tienda online.
- **Lo importante:** **un solo número de WhatsApp y teléfono** recibe ventas a público, instaladores, empresas, presupuestos
  de obra, turnos de instalación, service, reclamos de garantía y consultas de cursos. Y el sitio, que no muestra precios,
  manda todo ahí.

### 2.3 El sitio

- **Plataforma:** Tiendanube (tienda 1464552, tema Amazonas). El sitemap lista **266 productos**.
- **Sin precios:** todos los productos muestran **"Consultar precio"** (en el HTML el precio es 0 y `price_short` es nulo).
  El botón no agrega al carrito: lleva al formulario de contacto. El stock sí está cargado (por ejemplo, 16 unidades del
  BGH Silent Air 2700 W), aunque no se muestra.
- **Roto:**
  - el banner **"Preguntas Frecuentes"** de la home lleva a /faq/, que da **404**;
  - /como-comprar/, que está en el sitemap, también da 404;
  - "Quiénes somos" es una imagen: el texto no lo leen ni Google ni un asistente.
- **Clientes que muestran** (carrusel de logos): Georgalos, Arcor, Mostaza, Porta, Universidad Blas Pascal y Pritty.
- **Cookies:** banner "Al navegar por este sitio aceptás el uso de cookies", sin opción de rechazo.

### 2.4 Cursos

- **Curso presencial de reparación de aire acondicionado:** 10 clases de 2 horas, los sábados de 11 a 13, en el aula
  taller de Bulnes 1192. Temario: plaquetas electrónicas, compresor, robinetes, válvula inversora, circuito frigorífico,
  cableado, hidrolavado, bomba de condensado, conversión de frío solo a frío/calor y soldaduras. El último inicio
  publicado es el "sábado 14 de junio".
- **También:** curso de instalación. En la tienda se venden la "Seña" de cada curso, sin precio a la vista.
- **Reseñas:** muchas de 5 estrellas del último año, sobre el profesor (David Quiroga) y lo práctico del curso, y algunas
  negativas: la matrícula de "70mil" que no avisan antes y que "demora aprox 3 meses" (hace 10 meses), y una muy dura
  de hace una semana.
- **Por qué importa:** son consultas repetidas (fecha de inicio, cupo, precio, seña, temario) que hoy entran por el mismo
  WhatsApp que las ventas y los reclamos.

## 3. Productos y precios de referencia

**La empresa no publica precios.** Los de abajo son de mercado, de prensa y de guías de 2026, y sirven solo para la demo.
El agente no los da sin una lista vigente de Goldman.

| Línea | Qué tienen en el sitio | Referencia de mercado (no de Goldman) |
|---|---|---|
| Aires hogar | Split on/off e inverter, frío/calor y frío solo, de 2.700 a 6.700 W: Goldman BGH Silent Air y Cool Time, Midea, Gree, York | Inverter frío/calor: desde ~$ 550.000 (2.700 W) hasta $ 1.500.000 o más (6.000 frigorías), julio de 2026 (servidos.ar). En Mercado Libre, de $ 720.000 a más de $ 1,2 millones (dic-2025, iProUP) |
| Aires comercio y grandes superficies | Piso techo BGH de 3, 5 y 6 TN (220 V y 380 V) | — |
| Instalación | Instalan con técnicos propios o recomendados; venden kits de instalación | Instalación básica de un split en Buenos Aires: $ 135.000 a $ 210.000 (2026). Una reseña de hace un mes habla de "4 millones de pesos en 1 equipo" y de que la instalación de Goldman cuesta el doble |
| Calefacción | Calderas Peisa (Diva, Dual Diva, condensación) y BGH Vesta; radiadores BGH bimetálicos de 1 a 10 elementos; toallero Peisa; tubo radiante; calefacción para exterior | — |
| Equipamiento comercial | Exhibidoras verticales y horizontales Briket (315 a 501 l), freezers, heladeras, bateas, dispensers, extractores, microondas, balanzas | — |
| Termotanques | Solares, eléctricos y a gas | Una reseña cita tubos para termotanque solar a $ 60.000 contra $ 18.500 en otro lado |
| Repuestos y herramientas | Para aire y calefacción, refrigerante, bombas de vacío, sopletes, pestañadoras, taladros, amoladoras | — |
| Cursos | Reparación e instalación de aires, presenciales | Matrícula de $ 70.000 según una reseña (hace 10 meses) |

- **Formas de pago:** en la ficha de producto figura "Transferencia o depósito". En reseñas: "si no es efectivo todo
  lleva intereses" (hace 2 años) y "Tienen plan ahora 12" (hace 4 años). **A confirmar** las vigentes.
- **Garantía e instalación:** según una reseña de hace un mes, la garantía depende de instalar con sus técnicos; el
  propietario respondió que esas condiciones "son informadas al momento de la compra". **Hay que pedir la política
  escrita** antes de que el agente hable de garantía.

## 4. Competencia y contexto

### 4.1 Córdoba (Google Maps, 21-oct-2026)

| Competidor | Google | Qué hace | Atención digital vista |
|---|---|---|---|
| Refrigeración La Valva (Julio A. Roca 409) | 4,5 con 2.447 reseñas | Tienda de aires y refrigeración | Instagram como sitio |
| **Climatización Polar SA** (Fray Mamerto Esquiú 996) | 4,3 con 1.095 | El competidor más parecido: aires, calefacción, repuestos, electricidad, para público, instaladores y constructores | Tiendanube **con precios publicados** (por ejemplo, $ 733.600 y $ 1.540.900) y botón de WhatsApp |
| Isaías Goldman | 4,2 con 1.671 | — | Tiendanube **sin precios**, un WhatsApp |
| Grupo Mondino (David Luque 1522) | 4,5 con 771 | Refrigeración, lavarropas, obras y cámaras frigoríficas | WordPress + WooCommerce, con "Appointment" (turnos) |
| Al-Rep Repuestos (Luis de Góngora 1083) | 4,4 con 719 | Repuestos de aire | WhatsApp como sitio |
| Mister Frío (Vélez Sarsfield 4400) | 4,6 con 418 | Repuestos y service | WhatsApp como sitio |
| Torralba (Duarte Quirós 2466 y sucursal Ruta 20) | 4,5 con 390 | Aires, repuestos, gases, energía solar | Tienda online propia, con 2 locales |
| Climatización La Única | 4,4 a 4,7, con 4 locales | Aires y repuestos en Av. Colón, Vélez Sársfield, Circunvalación y Monseñor Pablo Cabrera | Mercado Shops e Instagram por local |

- **Cadenas y online:** Easy (3,7 con 7.485 reseñas), Cetrogar, Frávega y Mercado Libre venden el equipo. Goldman compite
  por asesoramiento, stock, instalación y posventa, no por precio: las reseñas lo ven "por arriba de la media".
- **IA en el rubro:** en los sitios revisados (Polar, Torralba, Mondino) **no hay chatbot ni agente**; todos usan un
  botón de WhatsApp atendido por personas. No se verificó si alguno tiene bot dentro del WhatsApp. **El primero de
  Córdoba que conteste al instante en temporada se lleva la consulta.**

### 4.2 Contexto del rubro en 2026

- **Estacionalidad:** el pico de aires es de noviembre a febrero, y en invierno el de calefacción. La empresa suma
  calefacción y solar justo para "romper la estacionalidad" (2021), pero el volumen sigue concentrado en verano.
- **Precios:** "se mueven todos los meses y suben fuerte antes del verano" (guía de 2026). Por eso un precio dado por
  WhatsApp envejece rápido, y eso explica la queja de "un precio por Whatsapp y otro en el local".
- **Inverter:** en 2021, el 50 % de los clientes lo pedía, con un sobreprecio del 20 al 25 %.
- **No se encontraron** datos de unidades vendidas en 2026 ni de importaciones.

## 5. Dolores detectados (con evidencia)

Reseñas de Google Maps (fechas relativas al 21-oct-2026). Extractos en `raw/google-maps-resenas.txt`; Google no da link
por reseña, así que el link es el de la ficha (parte 9).

| # | Evidencia | Qué dice | Qué resuelve Atentina |
|---|---|---|---|
| D1 | ivana alancay, 3 estrellas, hace 1 año; Jorge Luis Nahuel, 1 estrella, hace 9 meses | "marque al num que figura, nunca atienden"; "Pésima atención telefónica... Pierden clientes así" | El agente atiende el teléfono siempre, también varias llamadas a la vez |
| D2 | Lucas Andres, 3 estrellas, hace 1 año; Santi Picolet, 2 estrellas, hace 4 años | "siempre te dicen que te vuelven a llamar, y no lo hacen"; "Llame 3 veces para pedir presupuesto... nunca me devolvieron el llamado" | Responde en el momento, y si hace falta un humano deja la ficha con día y franja para la devolución |
| D3 | Estefania Mariani, 4 estrellas, hace 3 años | "La debilidad es la atencion telefónica y via mail para pedir presupuestos, tardan mucho tiempo" | Cotiza al instante con la lista vigente (equipo, kit, instalación) y deja el presupuesto por escrito en el WhatsApp |
| D4 | Cristian Tabares, 1 estrella, hace 1 año | "me pasaron un precio por Whatsapp y al llegar a la sucursal me dieron otro, incluso casi el doble" | Un solo precio, de una sola lista, con fecha y validez: "precio al 21/10, válido por X días" |
| D5 | Amalia Rubio Stang, 2 estrellas, hace 1 año; Lic. Pilar Munoz, 2 estrellas, hace 3 años; Maria Gaina, 1 estrella, hace 1 año | "esperé toda la tarde que venga el técnico que nunca llegó ni tampoco avisaron"; "2 días seguidos por 4 horas cada dia"; "me dejan plantada" | Agenda la visita, la confirma el día anterior por WhatsApp o llamada, y avisa si hay cambio. Campaña saliente de confirmación |
| D6 | Facundo Rinaldi, 1 estrella, hace 1 año; Lucas Martínez, 1 estrella, hace 3 años; Nicolas Marchese, 1 estrella, hace 8 años | Un aire de "5000usd" y lo mandan al 0800 del fabricante; "Desde octubre del año pasado estoy a la espera"; "llamamos 4 veces haciendo el reclamo" | Toma el reclamo con número de caso, datos del equipo y fotos, y le avisa al cliente cada novedad. "Nuestro fuerte es el postventa" se vuelve verificable |
| D7 | ARIEL LESTA, 1 estrella, hace 10 meses; roberto MARETTO, 1 estrella, hace 1 año; Nadia González, 2 estrellas, hace 3 años | "Se tarda muchísimo para atender. Y están todos mirando la compu"; "Una hora de espera" | Pedido por WhatsApp antes de ir (repuestos para instaladores) y aviso de "listo para retirar" |
| D8 | Sitio, 21-oct-2026 | 266 productos sin precio: "Consultar precio" lleva a un formulario por email | El agente es el "Consultar precio": contesta en segundos por WhatsApp |
| D9 | Sitio, 21-oct-2026 | El banner "Preguntas Frecuentes" y /como-comprar/ dan 404; el horario no está publicado | El agente responde horario, formas de pago, envíos, garantía y cursos |
| D10 | Google Maps | Cierran de 13 a 14:30, a las 18:30 y el sábado a las 13 | Atención 24/7 por voz y WhatsApp, justo cuando el instalador o el cliente tiene tiempo |
| D11 | Shirley Cávoli, 3 estrellas, hace 10 meses | La matrícula de 70 mil del curso no la avisan antes | El agente explica el curso completo (fecha, matrícula, seña, temario) antes de inscribir |
| D12 | 1 WhatsApp y 1 teléfono publicados | Público, instaladores, empresas, obras, service, reclamos y cursos entran por el mismo número | Clasifica y deriva a ventas, repuestos, service, obras o cursos |

**Lo que no se pudo verificar:** si el WhatsApp es Business o la app común, cuánto tarda en responder (no se mandó
mensaje), qué preguntan en Instagram y Facebook (los comentarios piden sesión) y cuántas consultas entran por mes.

## 6. Pistas de interés en mensajería de voz, WhatsApp e IA

**Directas (pocas):**

- **Ya canalizan todo a WhatsApp:** botón flotante con "Quisiera asesoramiento de un especialista", Linktree con
  WhatsApp primero, y en sus respuestas a reseñas invitan a "escribirnos por WhatsApp". El canal está; falta quien
  conteste a tiempo y con el mismo precio.
- **Le importa responder:** "Nos gusta hacer cosas donde podemos responder" (Isaías, 2018) y "Nuestro fuerte es el
  postventa" (Jonatan, 2021).
- **Contesta las reseñas, incluso las malas** (en el último año), con plantillas firmadas "Isaias Goldman SA": le importa
  la reputación en Google.
- **Llamó él o atendió:** habló con el usuario por teléfono y pidió la oferta.

**Indirectas:**

- **Invirtieron en imagen y marca:** edificio restaurado, galería de arte, marca propia "Goldman". Un especialista que
  atiende al instante encaja en "Somos el especialista".
- **Quieren delegar fuera de la familia** (Jonatan, 2015) y la mitad de los 50 empleados es comercial: el cuello de
  botella es la atención, no el stock (Isaías: "es bueno tener el depósito lleno").
- **Venden a empresas** (Arcor, Georgalos, Mostaza, Porta): esos clientes esperan respuesta rápida en service.
- **El calendario los apura:** la temporada de aires empieza en semanas.

**Lo que no hay:** ninguna mención pública de CRM, bots, call center ni del ERP que usan. Hay que preguntarlo (parte 8.4).

## 7. El mejor caso de uso: "el especialista de guardia" en el teléfono, el WhatsApp y la web

### 7.1 La propuesta (definida con el usuario el 21-oct-2026)

**Propuesta de valor:** atención 24/7 en los tres canales, respuestas a las consultas generales sin intervención,
**derivación a la persona que corresponde** cuando hace falta y, lo más importante para el dueño, **observabilidad**:
cada comunicación de cada canal registrada y medida en un solo panel.

| Canal | Qué hace el agente | Derivación a una persona |
|---|---|---|
| **1. Línea 0800 / 0810** | Agente de voz que atiende y clasifica: ventas, instalaciones, productos, precios (y posventa) | **Transferencia de la llamada** a un vendedor (o al área que toque), con la ficha de lo hablado |
| **2. WhatsApp** | El mismo agente en texto y notas de voz: clasifica, responde lo general y evalúa si hace falta una persona | **Relay al WhatsApp de un vendedor o de soporte**: la conversación sigue con la persona, con registro |
| **3. Chat en la web** | Asistente embebido en isaiasgoldmansa.com que sabe en qué página está (producto, categoría, cursos) | **Paso a una persona** (por el mismo chat, o por WhatsApp si no hay nadie conectado) |
| **Panel (observabilidad)** | Todas las conversaciones de los tres canales en un lugar, con transcripción, resumen y resultado | Métricas por canal, por tipo de consulta, por resultado, fuera de horario, tiempo de respuesta, derivaciones y a quién |

Por qué la observabilidad pesa tanto: hoy el dueño no sabe cuántas consultas entran, cuántas quedan sin respuesta ni
qué se prometió por WhatsApp (D4, el precio distinto). Las 1.671 reseñas son la única métrica que tiene, y llega tarde.

Lo que el agente sabe hacer en los tres canales, con nombre propio y voz argentina (por ejemplo, "Sofía, de Isaías
Goldman"):

1. **Contesta en segundos, 24/7**, por texto o nota de voz según escriba el cliente, y atiende las llamadas (varias a la
   vez, también al mediodía y de noche).
2. **Asesora como especialista:** ambiente, m² y orientación, frío solo o frío/calor, inverter o no, 220 o 380 V. Recomienda
   frigorías y modelo.
3. **Cotiza con la lista vigente** que Goldman le carga (equipo + kit + instalación), con fecha y validez. **Un solo
   precio** en WhatsApp, teléfono y mostrador (D4).
4. **Agenda la instalación o la visita técnica**, la confirma el día anterior y avisa si se mueve (D5).
5. **Toma reclamos de posventa** con número de caso, modelo, fecha de compra, factura y fotos, y le avisa al cliente (D6).
6. **Le pasa al vendedor o al técnico una ficha:** "Caliente: split inverter 3000 F/C, living 18 m², quiere instalación,
   paga por transferencia, turno el jueves a la tarde".
7. **Atiende los cursos** (fechas, matrícula, seña, temario) e **instaladores** (pedido de repuestos para retirar).

### 7.2 Por qué es el mejor caso

- **Valor medible y con fecha:** en temporada, la consulta que no se contesta en minutos se va a Polar, La Valva o
  Mercado Libre. Métricas del piloto: tiempo a la primera respuesta, llamadas atendidas fuera de horario, presupuestos
  enviados, instalaciones agendadas, visitas confirmadas y reclamos con caso abierto.
- **No cambian nada:** el mismo número y los mismos vendedores y técnicos. No reemplaza a nadie: saca las consultas
  repetidas del mostrador y del teléfono.
- **Responde a sus propias reseñas:** cada dolor de la parte 5 tiene una línea en el agente.
- **Ya lo tenemos hecho** en su mayor parte (parte 7.4).

### 7.3 Guion de la demo (5 minutos, en una reunión o por videollamada)

1. **Antes:**
   - crear el agente `goldman_demo` en el cliente `atentina`, con la base de la parte 8, la voz `sofia` y una **lista de
     precios de demo** (marcada "de referencia");
   - rutear el WhatsApp de demo a ese agente para el número de quien vaya a probar (`wa_routes`, regla por contacto). Si
     prueba Isaías o Jonatan con su celular, pedirles el número antes y agregarlo a la regla.
2. **En vivo, WhatsApp:** escribe "¿Cuánto me sale un split inverter de 3000 frigorías instalado?". Recibe una nota de
   voz: le pregunta los m² y si lo quiere frío/calor, le recomienda el modelo, le pasa el precio de referencia con kit e
   instalación y le ofrece turno.
3. **En vivo, teléfono:** llama a la línea de demo, "como si fueran las 13:30", y pide "el técnico no vino, compré un
   aire hace dos semanas". El agente abre el reclamo, toma modelo, fecha y dirección, y le dice qué sigue.
4. **El wow, saliente:** el agente le pregunta "¿Te llamo ahora y lo vemos en 2 minutos?". Le suena el celular: es la
   llamada saliente por API (o desde la pantalla Llamadas), disparada a mano por nosotros.
5. **Cierre, la observabilidad:** en el panel, las conversaciones de la demo de los dos canales, con transcripción, resumen
   y tipo de consulta, las métricas del período y el **resumen por email** de la llamada, que es lo que recibiría su
   vendedor. Es lo que más le importa al dueño: mostrarlo con calma. Comparación: "La reseña dice 'siempre te dicen que te vuelven a llamar, y no lo
   hacen'; esto fueron 40 segundos".

### 7.4 Qué hay hoy y qué falta

Revisado contra el código el 21-oct-2026:

| Pieza | Estado |
|---|---|
| Agente de voz entrante (número de Anura) | En producción |
| **Línea 0800 / 0810** | Atentina ya tiene un 0800 por Anura, así que el circuito existe. A verificar con Anura: costo por minuto entrante del 0800 (lo paga Goldman) contra el 0810 (costo compartido) y plazo de alta |
| **Triage por tipo de consulta** | Hecho: los `outcomes` de la definición del agente (ventas, instalación, producto, precio, posventa, cursos, fuera de tema) quedan como resultado de cada conversación |
| **Transferencia telefónica a una persona** | **Falta.** No hay transferencia en el worker. Dos caminos: transferencia SIP (REFER) por Asterisk hacia Anura (a verificar que Anura la acepte) o transferencia "con aviso": el agente llama al vendedor por el trunk saliente, le resume y une las dos patas en la room de LiveKit. Decidir qué pasa si el vendedor no atiende (vuelve al agente, toma el pedido y avisa) |
| **Relay de WhatsApp a vendedor / soporte** | **Falta**, diseñado en [`../../WHATSAPP_PLAN.md`](../../docs/WHATSAPP_PLAN.md), 5.8 (a implementar, 21-oct-2026). Para Goldman encaja la variante A (puente por la bandeja: el cliente queda en el número de la empresa, registro completo) con asignación por el agente al terminar el triage |
| **Chat en la web con el contexto de la página** | **Falta.** Existe el motor de texto (el de WhatsApp) y la página "link para llamar" (voz por navegador, con Turnstile), pero no un widget de chat. Hace falta: script embebible, endpoint público con control de abuso (como `/api/v1/demo`), el contexto de la página (URL, producto, precio si lo hubiera) en cada mensaje y el paso a una persona. A verificar: que Tiendanube permita insertar un script de terceros en su plan |
| **Observabilidad** | **Parcial.** Hoy: dashboard con conversaciones totales (y cuántas por WhatsApp), completas, objetivo cumplido, fallidas, minutos, tiempo de respuesta, gráfico diario y tabla con transcripción y resultado. Falta: desglose por tipo de consulta (`outcome`) y por canal (incluido el chat web), fuera de horario, derivaciones (cuántas, a quién, cuánto tardó la persona en tomarla) y la vista unificada por contacto entre canales |
| WhatsApp: texto, notas de voz y llamadas de WhatsApp atendidas por el agente | En producción. Su número se conecta por Embedded Signup (espera la aprobación de Meta) o a mano. **Mover el 351 386 2886 a la Cloud API tiene costo para ellos:** el número deja de andar en la app común del celular. Hay que hablarlo |
| Resumen por email de cada llamada | Desplegado el 20-oct-2026 |
| Llamada saliente individual (API o pantalla Llamadas) | Disponible; la pantalla Llamadas está sin desplegar. Disparo manual en la demo |
| Confirmación de turnos y avisos (D5) | Campañas de WhatsApp: desplegadas. Campañas de llamadas: implementadas, **sin desplegar** ([`../../LLAMADAS_SALIENTES_PLAN.md`](../../docs/LLAMADAS_SALIENTES_PLAN.md)) |
| Lista de precios en el agente | Para la demo y un piloto chico, en la definición del agente (texto). Para 266 productos con stock y precios que cambian cada mes: **falta** una app por cliente con herramientas ([`../../archive/APPS.md`](../../docs/archive/APPS.md)) que lea la lista, el stock de Tiendanube (tiene API) o su sistema de gestión |
| Agenda real de técnicos | **Falta:** app por cliente o integración con lo que usen hoy |
| Número de caso de reclamo y seguimiento | Hoy queda como resultado de la conversación en el panel. Un registro de casos con estado es parte de una app por cliente |
| Ficha al vendedor por WhatsApp | A definir; hoy está en el panel y en el resumen por email |
| Grabación | Existe (`record_audio`), apagada. Antes de usarla con un cliente real hay que avisar a quien llama y corregir la política de privacidad de la landing |

### 7.5 Fases sugeridas

1. **Piloto de 30 días, desde noviembre (inicio de temporada):** 0800/0810 y WhatsApp con triage, respuestas generales,
   derivación a vendedores y el panel con métricas por canal y por tipo de consulta. Línea de base: que ellos midan antes
   cuántas consultas y llamadas entran y cuántas quedan sin respuesta. Lo que llega antes: triage, respuestas y panel
   (existen); la transferencia telefónica y el relay de WhatsApp hay que construirlos (7.4). Si no llegan a noviembre,
   el piloto arranca con derivación por ficha (resumen por email y aviso) y se suman después.
2. **Chat en la web**, con el contexto de la página y el mismo panel.
3. **Posventa:** reclamos con caso, confirmación de visitas el día anterior, aviso de demora.
4. **Instaladores y repuestos:** pedido por WhatsApp y aviso de "listo para retirar" (D7).
5. **Cursos:** inscripción, seña y recordatorio de inicio.
6. **Base de clientes:** mantenimiento antes del verano ("limpieza de filtros": el 90 % de las pérdidas de agua, según
   Jonatan) y antes del invierno (calderas), por campaña. Es facturación de service.
7. **Integración:** catálogo, stock y precio desde su sistema; obras y empresas con un circuito propio.

### 7.6 La oferta (formulable)

- **Qué incluye:** el agente configurado con su catálogo, lista y políticas, en tres canales: **línea 0800/0810**,
  **WhatsApp** (texto y notas de voz) y **chat en la web**; triage por tipo de consulta; **derivación a sus vendedores y a
  soporte** (transferencia de la llamada, relay de WhatsApp, paso a persona en el chat) con la ficha de lo hablado;
  **panel de observabilidad** con todas las comunicaciones y sus métricas; resumen por email de cada conversación;
  ajustes semanales del prompt durante el piloto.
- **Cómo se mide (lo ve el dueño en el panel):** consultas por canal y por tipo (ventas, instalaciones, productos,
  precios, posventa); tiempo a la primera respuesta; atendidas fuera de horario y al mediodía; resueltas por el agente
  contra derivadas; derivaciones por vendedor y cuánto tardó cada uno en tomarlas; presupuestos enviados; instalaciones
  y visitas agendadas; reclamos con caso. Se compara contra la línea de base que entreguen.
- **Piloto:** 30 días (el plan de salida dice de 30 a 60), alcance acotado (aires hogar + posventa), **precio fijo y bajo,
  no gratis** ([`../plan-salida-al-mercado.md`](../plan-salida-al-mercado.md), parte 5). Si funciona: contrato mensual
  y caso público con números.
- **Precios publicados (landing, `landing/src/data/site.ts`):** Mostrador $ 29.000/mes (300 minutos, 1 llamada a la vez,
  1 número), Sucursal $ 99.000/mes (1.200 minutos, 3 a la vez, 3 números, llamadas programadas), Red a medida (más de
  5.000 minutos). Son planes de voz.
- **Pendiente (no documentado, no inventar):**
  - precio del piloto;
  - precio del WhatsApp de texto (mensajes, no minutos) y quién paga las plantillas de Meta;
  - precio de una app por cliente (catálogo, agenda, casos).
  - Con un solo local en temporada, el plan Sucursal es el punto de partida probable para la voz: **a validar con el
    usuario** antes de mandarlo.

## 8. Base para el prompt del agente

### 8.1 Rol y tono

- **Rol:** "Sos Sofía, del equipo de Isaías Goldman, 'el especialista' en climatización de Córdoba desde hace más de 30
  años, en Bv. Bulnes 1192 esquina Pringles. Ayudás a quien consulta a elegir su aire, su calefacción o su equipamiento
  comercial, le pasás el presupuesto, le coordinás la instalación o el service y tomás los reclamos."
- **Tono:** cálido, de vos, seguro, como un vendedor con oficio; frases cortas y sin tecnicismos de más. Por teléfono, una
  pregunta por vez.
- **Lema de la casa:** "Somos el especialista".

### 8.2 Reglas

1. **Precios:** solo de la lista vigente que cargue Goldman, con la fecha y la validez ("precio al 21/10, válido por 5
   días"). Sin lista: "el precio del día te lo paso por acá en un rato; ¿me dejás los datos?". Los de la parte 3 son solo
   para la demo y se dicen "de referencia".
2. **Stock:** no confirmarlo sin el dato de stock; ofrecer reservar o que lo confirme un vendedor.
3. **Recomendación de frigorías:** preguntar m², orientación, si es último piso y cuántas personas; recomendar un rango y
   decir que el vendedor lo confirma. No prometer rendimiento.
4. **Instalación y garantía:** decir lo que diga la política escrita de Goldman (pendiente: parte 8.4). No opinar sobre
   técnicos de terceros. Avisar qué incluye y qué no la instalación (por ejemplo, la parte eléctrica, que una reseña dice
   que no incluyen).
5. **Turnos:** no prometer un día y horario que nadie confirmó. Ofrecer franja (mañana o tarde) y avisar que se confirma
   el día anterior.
6. **Reclamos:** tomar modelo, fecha de compra, número de factura o DNI, dirección, qué pasa y fotos o video. Dar número
   de caso y el próximo paso con fecha. No discutir ni prometer reemplazos.
7. **Derivar:**
   - obras y climatización central, empresas e industrias: a ventas corporativas (pedir empresa, CUIT, rubro y obra);
   - instaladores que compran repuestos: tomar el pedido para retirar;
   - cursos: fecha de inicio, matrícula, seña y temario, de la información vigente.
8. **Horario:** lu a vie de 8:30 a 13 y de 14:30 a 18:30, sáb de 8:30 a 13 (a confirmar con ellos). Fuera de horario,
   tomar la consulta y dar el próximo paso concreto.
9. **Cerrar siempre con un próximo paso:** presupuesto enviado, turno, reserva, caso abierto o llamada de un vendedor
   con día y franja. Nunca "te volvemos a llamar" sin más (D2).

### 8.3 Triage y datos

| Salida | Cuándo | Datos |
|---|---|---|
| **Venta aire hogar, caliente** | Quiere comprar e instalar pronto | Nombre, WhatsApp, ambiente y m², frío solo o frío/calor, inverter, instalación sí o no, barrio, forma de pago, franja para instalar |
| **Venta aire hogar, tibia** | Compara precios | Lo mismo, sin turno. Seguimiento en 48 horas con el precio vigente |
| **Calefacción y termotanques** | Caldera, radiadores, solar | Tipo de vivienda, m², gas natural o envasado, cantidad de ambientes, si hay instalación previa |
| **Comercio, industria u obra** | Equipamiento comercial, piso techo, central, cámaras | Empresa, CUIT, rubro, ubicación, qué necesita y plazo. Derivar a ventas corporativas |
| **Instalador o técnico** | Repuestos, gas, kits, herramientas | Nombre o empresa, lista de artículos, retira o envío, forma de pago |
| **Posventa o reclamo** | Falla, garantía, técnico que no vino | Modelo, fecha de compra, factura o DNI, dirección, descripción, fotos; número de caso |
| **Turno de service** | Mantenimiento o reparación fuera de garantía | Equipo, dirección, problema, franja |
| **Cursos** | Fechas, matrícula, inscripción | Nombre, curso, si ya trabaja en el rubro, cómo paga la seña |
| **Otro** | Administración, proveedores, RR. HH. | El motivo, para derivarlo |

**Resumen al vendedor**, en una línea más los datos. Por ejemplo: "Caliente: split inverter 3000 F/C para living de 18 m²,
Nueva Córdoba, con instalación, transferencia, jueves a la tarde".

### 8.4 Preguntas para la charla (descubrimiento)

1. ¿Cuántas consultas entran por mes por WhatsApp, teléfono, formulario e Instagram, y cuántas en temporada? ¿Qué parte
   llega al mediodía, de noche o el fin de semana?
2. ¿Quién contesta el 351 386 2886? ¿Es WhatsApp Business o la app común? ¿Cuántas personas lo usan? ¿Para qué es el
   351 589 0033?
3. ¿Por qué no publican precios en el sitio? ¿Cada cuánto cambia la lista y dónde está (sistema de gestión, Excel)?
4. ¿Qué sistema usan para stock, facturación y agenda de técnicos? ¿Y para los reclamos?
5. ¿Cuántas instalaciones y visitas de service hacen por semana en temporada? ¿Confirman el turno el día anterior?
6. ¿Cuál es la política escrita de garantía e instalación?
7. ¿Cuánto pesan los instaladores (B2B) contra el público? ¿Y las obras?
8. ¿Les interesa que el agente llame (confirmaciones, devolución de llamados, mantenimiento antes del verano) o solo que
   conteste?
9. ¿Quién decide esto: Isaías, Jonatan o Carolina? ¿Quién sería el responsable del piloto?
10. ¿Nos pasan una lista de precios y los 20 productos más consultados para armar la demo y el piloto?

## 9. Fuentes

- Sitio: https://www.isaiasgoldmansa.com/, /aire-acondicionado/, /quienes-somos/, /contacto/ (y
  /contacto/?product=71158605 desde "Consultar precio"), /cursos/,
  /productos/curso-presencial-de-reparacion-de-aire-acondicionado/,
  /productos/aire-acondicionado-goldman-bgh-split-inverter-silent-air-f-c-2700w/, /sitemap.xml; /faq/ y /como-comprar/
  dan 404.
- Google Maps, Isaias Goldman SA, 4,2 con 1.671 reseñas:
  https://www.google.com/maps/place/Isaias+Goldman+SA/@-31.3998945,-64.1725017,17z/data=!4m6!3m5!1s0x9432a2b52f3c76b3:0x404365a11c66fae
- Redes: https://www.instagram.com/isaias_goldman/, https://www.facebook.com/Isaiasgoldman/,
  https://linktr.ee/isaias_goldman
- Prensa y directorios:
  - InfoNegocios, "Jonatan Goldman (Isaías Goldman)" (18-may-2015):
    https://infonegocios.info/lo-que-viene/jonatan-goldman-isaias-goldman
  - InfoNegocios, "Isaías Goldman no le teme al invierno" (10-may-2018):
    https://infonegocios.info/bien-de-familia/isaias-goldman-no-le-teme-al-invierno-diversificacion-y-foco-en-el-servicio-la-clave-de-la-marca
  - InfoNegocios, "Isaías Goldman suma servicios para grandes obras" (11-jul-2019):
    https://infonegocios.info/bien-de-familia/isaias-goldman-suma-servicios-para-grandes-obras-sin-desatender-las-chicas
  - InfoNegocios, "El objetivo es hacer cada vez más fuerte la marca Goldman" (12-abr-2021):
    https://infonegocios.info/un-cafe-con/el-objetivo-es-hacer-cada-vez-mas-fuerte-la-marca-goldman
  - InfoTarjetero, ficha de empresa y de Isaías Miguel Goldman: https://infonegocios.info/tarjetero/empresa/isaias-goldman,
    https://infonegocios.info/tarjetero/isaias-miguel-goldman
  - InfoNegocios, Arty Sesion en Córdoba Shopping: https://infonegocios.info/y-ademas/arty-sesion-en-cordoba-shopping
  - argentino.com.ar, "Refrigeración Isaías Goldman", San Jerónimo 2760:
    https://www.argentino.com.ar/cordoba-capital/heladeras+comerciales
- Mercado: iProUP, precios en Mercado Libre: https://www.iproup.com/coffee-break/63407-cuanto-cuesta-un-aire-acondicionado-en-mercado-libre;
  servidos.ar, instalación 2026: https://servidos.ar/blog/cuanto-cuesta-instalar-aire-acondicionado-2026
- Competencia: Google Maps, búsqueda "repuestos refrigeración aire acondicionado Córdoba Capital" (21-oct-2026);
  https://www.climatizacionpolar.com.ar/, https://www.torralba.com.ar/, https://grupomondino.com.ar/
