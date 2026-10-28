# SQL Amoblamientos: base de conocimiento para el primer acercamiento y la propuesta (22-oct-2026)

Primer acercamiento a **SQL Amoblamientos** (Córdoba): fábrica de muebles a medida (cocinas, placares, vestidores,
baños, living) con showroom propio y una red de locales y franquicias en 9 provincias. El dueño es **Jorge Urizar**
(fundador y presidente; se ocupa de la producción); según el usuario, sus hijos llevan la administración y **Pilar
Conte**, asistente de marketing, sería el primer contacto. Lead que pasó el usuario, sin llamada previa. Objetivo:
reunión de relevamiento y piloto de 30 días. El documento sirve para esa reunión, para el PDF y el video de la
propuesta y como base de un agente posterior. Lead 364 en el CRM, cargado el 22-oct-2026 (sin borradores).

**Es la empresa correcta:** el sitio sqlamoblamientos.com.ar, la ficha de InfoNegocios, Google Maps y la prensa
coinciden en el nombre, la casa central (Av. Fuerza Aérea Argentina 3376, Córdoba), el teléfono y en Jorge Urizar como
titular.

- **Fuentes, leídas el 22-oct-2026:**
  - el sitio completo (50 páginas del `sitemap.xml`, API de WordPress, `robots.txt`), con `curl`;
  - Google Maps de 4 locales (casa central, Rafael Núñez, Villa Carlos Paz, Río Cuarto), reseñas por "valoración más
    baja" y "más recientes", desde el navegador;
  - Instagram (perfil público, sin sesión), Linktree, la página `wa.me` del WhatsApp;
  - prensa: InfoNegocios (abr-2025, ago-2025, nov-2025 y su Tarjetero), Punto a Punto (nov-2021), D&F Muebles
    (sep-2015), Economix (jun-2024);
  - videos: 4 entrevistas a Jorge en YouTube (2015, 2020, 2024, 2025), solo título, descripción y vistas;
  - Google Maps de la competencia en Córdoba capital, Carlos Paz y Río Cuarto.
  - Links en la parte 9.
- **Copia local:** `scratch/prospectos/sqlamoblamientos/raw/` (HTML y texto del sitio en `site/`, sitemap, páginas
  de WordPress, `sucursales.txt` con los 20 puntos de venta, notas de prensa, `resenas.txt`, `competencia-maps.txt`,
  Linktree, páginas de los videos).
- **No se encontró:**
  - nada público de **Pilar Conte** (ni LinkedIn ni mención en el sitio o la prensa): el dato es del usuario;
  - los cargos actuales de los hijos: la única mención es de 2015 (**Nicolás y Facundo**, "trabajan a la par mío");
  - emails personales: solo `ventas@` y `consultas@` del dominio, más los de las sucursales;
  - razón social y CUIT (hay una "Sucre Amoblamientos SRL" de Córdoba constituida el 31-dic-1981, el año de
    fundación de SQL: **coincidencia sin verificar**, la ficha está detrás de Cloudflare);
  - la transcripción de los videos (YouTube no la sirvió): no hay citas textuales de video, solo de prensa escrita;
  - Facebook (el navegador no permite leerlo) e Instagram más allá del perfil (pide iniciar sesión).
- **Partes 1 a 5:** datos. Las partes 6 a 8 son nuestras y hay que validarlas con Pilar y con Jorge.

## 0. Resumen para la reunión y la propuesta

- **Quién es:** Jorge Urizar fundó SQL en **1981** (D&F Muebles 2015, Container 2020); es "fundador y presidente"
  (Economix, jun-2024) y "dueño y Gerente General" (Punto a Punto, nov-2021). En 2015 trabajaban con él sus hijos
  **Nicolás y Facundo** y **Gabriel Caligaris** ("si bien no es hijo mío, lo siento de la familia"), que en 2020
  firmaba en Google como "gerente de SQL AMOBLAMIENTOS".
- **Qué hace:** diseña, fabrica e instala muebles **100 % a medida**, sin stock: "cada venta empieza con un trabajo
  consultivo, con la visita a la obra o el estudio de los planos", siguen "varios idas y vueltas con presupuesto
  incluido" y recién con la venta arranca la producción, que lleva **90 a 100 días** (InfoNegocios, abr-2025).
- **Tamaño, con fuente:**

  | Dato | Valor | Fuente |
  |---|---|---|
  | Antigüedad | 45 años (desde 1981) | D&F 2015, Container 2020. El sitio dice "más de 40" y "más de 30"; InfoNegocios 2025, "más de 20" |
  | Planta | 4.000 m², 10 máquinas computarizadas, barrio San Roque | InfoNegocios, 23-abr-2025 |
  | Personal | 70 empleados (2025); 50 colaboradores (2021) | InfoNegocios 2025; Punto a Punto 2021 |
  | Showroom | 400 m² en Av. Rafael Núñez 4550 (abierto en 2025) | InfoNegocios 2025; sitio |
  | Red | 20 puntos de venta en 9 provincias en el sitio (12 franquicias según la prensa de 2025; "más de 30 sucursales" según Instagram) | sitio, /sucursales, 22-oct-2026 |
  | Pandemia | +50 % de facturación | Punto a Punto, 17-nov-2021 |
  | Reseñas | Casa central **4,3 con 183**; Rafael Núñez 4,4 (7); Carlos Paz 4,1 (9); Río Cuarto 4,6 (23): **222 en 4 locales** | Google Maps, 22-oct-2026 |
  | Instagram | 12,6 mil seguidores | @sqlamoblamientos, 22-oct-2026 |
  | Horario casa central | Lun a vie 9-13 y 14-18, sáb 9-13: **44 h abiertas de 168 por semana (26 %)** | sitio y Maps |
  | Canales | 1 WhatsApp central (351 617-5120: widget del sitio, Linktree, Instagram, showroom), fijo 0351 465-4531, `ventas@` y `consultas@`, 2 formularios web, y 20 WhatsApp/emails de sucursales (la mayoría Gmail o Hotmail) | sitio, Linktree |
  | Productos | 11 líneas de cocina en el menú (más Rauvisio), placares, vestidores, baños, living: **ninguno con precio**; el formulario "Cotizar" ofrece rangos de "400.000 a 500.000" a "600.000 o más" (página sin cambios desde oct-2022) | sitio |
  | Videos | 4 entrevistas: 2015 (1.016 vistas), 2020 (255), 2024 (519), 2025 (112) | YouTube, 22-oct-2026 |

- **Citas de Jorge (prensa escrita):**
  - "cumplimos a rajatabla con los tiempos estipulados y nos diferenciamos por hacer amoblamiento absolutamente a
    medida" (Punto a Punto, 2021);
  - "un amoblamiento de cocina a diferencia del resto necesita una venta más profesionalizada" (D&F, 2015);
  - "nos ocupamos personalmente de dar respuestas rápidas a nuestros distribuidores" (D&F, 2015);
  - "desde la pandemia venimos trabajando muy bien" (InfoNegocios, 2025).
- **Los dolores, con evidencia (parte 5):**
  1. **Presupuestos que no llegan:** "aún lo estoy esperando" (Carlos Paz, hace 10 meses); "hace más de 45 días ... nunca
     me enviaron un presupuesto" (casa central, hace 4 años); "dijo que enviarian por mail ... y nunca enviaron nada"
     (hace 8 años). Respuesta de la empresa: "nuestros presupuestos a veces llevan un poco mas de tiempo".
  2. **Plazos y aviso durante la obra:** "nos dijeron que en marzo lo instalarian. Terminaron de instalarmelo en JUNIO"
     (hace 2 años).
  3. **Posventa por mensajes sin respuesta:** "me canse de escribirles durante meses para que me vengan a colocar
     zócalos" (Carlos Paz, hace 1 año).
  4. **Una red de 20 puntos sin un canal común:** cada franquicia con su Gmail o Hotmail y su WhatsApp; el sitio tiene
     páginas viejas de locales que ya no están en el listado.
  5. **74 % de la semana cerrado,** en un rubro donde la decisión se toma en casa y en pareja (inferencia nuestra).
- **Lo que sí funciona (y hay que cuidar):** las reseñas recientes nombran a los asesores (Martín, Fernando, Micaela,
  la Arq. Inés) y elogian el asesoramiento y los plazos. La venta es personal: el agente no reemplaza al asesor, le
  lleva el cliente calificado y no deja que nadie quede esperando.
- **Competencia (Córdoba capital, Maps):** ALB Amoblamientos 4,6 (130, con anuncio pago), NOVO Córdoba 4,7 (67),
  Amoblamientos Brum 4,7 (53), Amoblamientos Córdoba 4,5 (14). SQL es el de **más reseñas** y el de **rating más bajo**
  del grupo.
- **Caso de uso propuesto (parte 7): "el asesor de guardia".** Un agente en el WhatsApp central y en la línea que
  atiende 24/7, califica el proyecto (ciudad, ambiente, medidas o planos, plazo, rango de inversión), lo deriva al
  asesor o a la franquicia que corresponde con una ficha, **sigue el presupuesto hasta que sale**, informa el estado
  del pedido durante los 90 a 100 días y toma reclamos de posventa con número de caso. Para Jorge, un panel con cada
  consulta de cada canal y de cada sucursal.
- **El momento wow:** Pilar (o Jorge) escribe un domingo a la noche "quiero hacer la cocina, tengo 3,20 m de pared,
  ¿cuánto sale?". Recibe en segundos una nota de voz con acento argentino que le pregunta la ciudad, el
  estilo y el plazo, le explica cómo trabaja SQL (medición, render, presupuesto, 90 días) y le ofrece una visita al
  showroom de Rafael Núñez el martes. En el panel aparece la ficha que recibiría Martín el lunes a las 9.
- **Oferta:** piloto de 30 días con el WhatsApp central y la línea de casa central; precio del piloto pendiente
  (parte 7.6).
- **Qué no se pudo verificar:** el rol de Pilar y de los hijos hoy; la razón social; cuántos mensajes y llamadas
  reciben (hay que pedirlo); si el 351 617-5120 es WhatsApp Business (la página `wa.me` muestra el nombre "SQL
  Amoblamientos", que suele indicarlo).

## 1. La persona: Jorge Urizar

- **Cargo:** "titular" (InfoNegocios 2025, Container 2020, En Obras 2015), "fundador y presidente" (Economix 2024),
  "dueño y Gerente General" (Punto a Punto 2021). Según el usuario, hoy se ocupa de la producción.
- **Trayectoria (D&F Muebles, 3-sep-2015):** empezó en 1981 "vendiendo muebles de cocinas económicos, muy básicos";
  pasó la crisis de 2001 ("una muy dura"), invirtió en maquinaria y salió a expandirse por el país con distribuidores.
  En 2015 ya apuntaba al segmento medio-alto, "en el cual el servicio es un tema fundamental", y armaba un plan de
  formación para distribuidores. Usó un PACC (Secretaría PyME) para normalizar la imagen de los locales y destaca el
  Ahora 12 como motor de ventas.
- **Marketing:** "Hace unos años empezamos a trabajar el tema de la marca": isologotipo, eslogan, campaña en TV en
  Córdoba, cartelería en ruta, revistas, internet y redes (D&F 2015, título: "los resultados tras tres años de inversión
  en marketing y publicidad"). Es un dueño que **ya invierte en captar consultas**.
- **Expansión:** 2021, showroom premium en Villa Carlos Paz y planes de "locales propios, dentro y fuera de la
  provincia" y de exportar a "países limítrofes y Miami" (Punto a Punto). 2025, showroom de 400 m² en Rafael Núñez,
  "que servirá de captación de clientes" (InfoNegocios).
- **Familia y equipo:**
  - hijos **Nicolás y Facundo** Urizar (D&F 2015; el usuario dice que llevan la administración; sin fuente actual);
  - **Gabriel Caligaris**, gerente (D&F 2015; respuesta en Google firmada como gerente, hace 6 años);
  - **Pilar Conte**, asistente de marketing (dato del usuario, sin fuente pública);
  - asesores nombrados en reseñas recientes: Martín y Fernando (casa central), Micaela (Carlos Paz), Arq. Inés (Río
    Cuarto).
- **Videos:** "SQL Amoblamientos. Jorge Urizar. En Obras marzo 2015" (5:15, 1.016 vistas: cuenta la historia y muestra
  la fábrica); "Conocé SQL Amoblamientos" (Container TV, nov-2020, 2:03, 255 vistas: pandemia, dólar e inflación);
  Economix programa 2858 (jun-2024, 12:56, 519 vistas); "Un Café con... Jorge Urizar" (InfoNegocios, ago-2025, 9:52,
  112 vistas: franquicias y distribuidores, venta antes de producir, el showroom de zona norte). Sin transcripción.
- **No se encontró:** LinkedIn de Jorge, de sus hijos ni de Pilar.

## 2. La empresa: SQL Amoblamientos

### 2.1 Datos

- **Nombre comercial:** SQL Amoblamientos ("SQL Amoblamientos® | Oficial" en Instagram). Razón social y CUIT: no
  encontrados (ver la coincidencia con "Sucre Amoblamientos SRL", sin verificar).
- **Rubro en el Tarjetero de InfoNegocios:** real estate y construcción. Descripción: "Diseñamos, fabricamos y
  comercializamos amoblamientos personalizados de cocinas, dormitorios, baños y living en todo el país."
- **Fábrica:** 4.000 m², barrio San Roque, 10 máquinas computarizadas, 70 empleados; "maquinaria italiana" y
  "renders hiperrealistas" (InfoNegocios 2025). Instalación con mano de obra propia.
- **Materiales que destacan:** Carpi (Fénix, Brillato, de Italia), Purastone y Neolith para mesadas, laqueados y
  melaminas (Punto a Punto 2021; sitio).
- **Garantía:** 5 años (home del sitio).
- **Río Tercero:** la franquicia de Bolívar 423 nació como **Gutino/Guttino** en 2012 y se unificó con SQL en 2020; habla
  Sandra Colazo y un "Juan" al frente de esa fábrica desde 1996 (InfoNegocios Río Tercero, nov-2025). Anunciaban la
  reinauguración de su showroom el 12 de diciembre.

### 2.2 Locales, horarios y contacto

Los 20 puntos de venta del sitio (/sucursales, modificada el 11-sep-2026), copia en `raw/sucursales.txt`:

| Provincia | Locales | Nombre que figura |
|---|---|---|
| Córdoba (9) | Rafael Núñez 4550 y Fuerza Aérea 3376 (capital), Villa Carlos Paz, Río Cuarto, Jesús María, Río Tercero, Alta Gracia, Oncativo, Santa Rosa de Calamuchita | SQL en los 4 primeros y en Jesús María; el resto, comercios con nombre propio (Guttino, Señora Cocina, BAC, Fogo) |
| Buenos Aires (2) | Junín, Salto | Cota 81, Salto Materiales |
| Chaco, Chubut, Neuquén, San Juan, Santa Fe (1 c/u) | Sáenz Peña, Rawson, Neuquén, San Juan, Santa Fe | Estilo Compushop, Stagnitta Hermanos, SQL, Rinnova, SQL |
| La Rioja (2), San Luis (2) | La Rioja (2), Merlo, Ruta 20 km 8 | Diseño Interior, Sanitarios El Parque, Aberturas Ranelagh, Alucor |

- **Horarios:** casa central lun a vie 9-13 y 14-18, sáb 9-13 (44 h/semana); Rafael Núñez lun a vie 9-18, sáb 9-13
  (49 h); Carlos Paz lun a vie 9-13 y 16-20, sáb 9-13 (44 h); San Juan "horario a coordinar por WhatsApp"; Santa Fe,
  sábados "con cita previa". Domingo, todos cerrados.
- **Canales de casa central, probados sin enviar nada:**
  - **WhatsApp 351 617-5120:** es el del botón flotante del sitio (Joinchat, "Hola 👋! En que podemos ayudarte?"), el del
    Linktree, el del pie de página, el del showroom de Rafael Núñez y el del link de Carlos Paz. La página `wa.me` muestra
    el nombre "SQL Amoblamientos". **Un solo número recibe todo lo digital.**
  - **Fijo 0351 465-4531** (casa central, en Maps y en el sitio). El mismo número aparece como enlace `tel:` en páginas
    de sucursales de otras provincias (Resistencia, Rawson, Salta, San Luis): quien toca "llamar" desde Chaco llama a
    Córdoba.
  - **Emails:** `ventas@sqlamoblamientos.com.ar` (casa central, Tarjetero) y `consultas@sqlamoblamientos.com.ar` (pie de
    todas las páginas y showroom). Río Cuarto: `admin.riocuarto@sqlamoblamientos.com.ar`. Carlos Paz: `sqlvcp@gmail.com`;
    Santa Fe: `sqlamoblamientos.santafe@gmail.com`.
  - **Formularios:** /contacto (email y mensaje) y /cotizar (ciudad entre 13 provincias, tipo de proyecto, inversión
    estimada, adjunto de planos o fotos; Forminator). No se enviaron. /cotizar no está en el menú.
- **Otras consultas del rubro que el sitio no resuelve:** precios, plazos, formas de pago y financiación, zona de
  instalación, cómo es el proceso (medición, render, seña). No hay FAQ.

### 2.3 El sitio

- **Tecnología:** WordPress 7.1.3, tema Flatsome, Contact Form 7 y Forminator, Joinchat (WhatsApp), **píxel de Meta**
  (`643451515826068`); sin Google Analytics visible. Hecho por Pilsen Digital.
- **Contenido:** 50 páginas. 11 líneas de cocina en el menú (Premium Innovation: Americana, Flow, Modena, Carpi Fénix y
  Brillato; Premium: Cristal, Mix, Vetas; Classic: Astro, Eclipse, Nature) y una página de Rauvisio fuera del menú;
  placares con frentes deslizantes, vestidor, respaldo de cama, baño, living. Las fichas traen materiales y colores
  (Flow: 18 colores), **sin precios**.
- **Desactualizado o inconsistente:**
  - antigüedad: "Mas de 40 años eligiéndonos" (home), "más de 30 años de experiencia" (/fabrica-de-muebles-en-cordoba);
  - el sitemap tiene páginas de locales que ya no están en el listado (Villa María, Huinca Renancó, Pilar, Resistencia,
    Salta, San Luis capital, Monseñor Pablo Cabrera 3099);
  - el sitemap expone 8 "featured items" de la plantilla (posters, remeras);
  - el formulario de cotización tiene rangos de inversión de 2022.
- **El sitio tiene texto ajeno escondido:** en la home (la página "carpi", modificada el 12-sep-2026 a las 02:41) hay
  un bloque en alemán sobre mecánicos y apuestas, con un link a un sitio de apuestas, posicionado fuera de la pantalla
  (`left: -995333px`). Es el patrón de un sitio WordPress comprometido para SEO. No lo ve un visitante, sí Google.
  **Útil como gesto en el primer contacto** (avisarles), no como argumento de venta.

### 2.4 Redes, publicaciones y videos

- **Instagram @sqlamoblamientos:** 12,6 mil seguidores, 75 seguidos. Bio: "Más de 40 años creando amoblamientos
  únicos · Diseño | Fabricación | Instalación · Más de 30 sucursales en todo el país". Destacadas: Vestidor, Fénix
  Carpi, Cierre 25, Baño, Living, Cocina, Dormitorio, Showroom, Somos SQL. Hay una cuenta aparte de la franquicia de
  Río Tercero (`sqlamoblamientos.riotercero`). Publicaciones y comentarios no se pudieron leer sin sesión.
- **Facebook:** `sqlamoblamientosoficial` (no se pudo leer).
- **Linktree:** WhatsApp, Instagram y sitio.
- **YouTube:** no tienen canal propio con contenido encontrado; las 4 entrevistas son de medios (parte 1).

### 2.5 El proceso de venta del mueble a medida

Lo que cuenta la prensa (InfoNegocios, abr-2025) y que define el caso de uso:

1. consulta (WhatsApp, local, formulario);
2. trabajo consultivo: visita a la obra o estudio de planos y medidas;
3. diseño con render, "varios idas y vueltas con presupuesto incluido";
4. venta (seña o pago);
5. producción: entre 90 y 100 días;
6. instalación con equipo propio;
7. posventa (garantía de 5 años).

Cada paso tiene un tiempo de espera del cliente; los pasos 3, 5 y 7 son los que aparecen en las quejas (parte 5).

## 3. Productos y precios de referencia

- **Publicados:** ningún precio en el sitio, en Instagram (bio) ni en la prensa.
- **Rangos del formulario /cotizar:** "400.000 a 500.000", "500.000 a 600.00" [sic], "600.000 o más" (sin moneda,
  página de oct-2022). No sirven como referencia hoy.
- **Para la demo:** el agente **no da precios**; explica el proceso y ofrece la medición o la visita al showroom.
  Si SQL quiere, se le carga un rango "desde" por metro lineal que ellos definan. **Sin cifras inventadas.**

## 4. Competencia y contexto

### 4.1 Local (Google Maps, 22-oct-2026)

| Empresa | Rating | Reseñas | Nota |
|---|---|---|---|
| **SQL Amoblamientos OFICIAL** (Fuerza Aérea 3376) | 4,3 | 183 | Temas: diseño 22, cocina 20, precios 15, instalación 12, presupuesto 10, plazos 7 |
| SQL Rafael Núñez 4550 | 4,4 | 7 | Showroom nuevo |
| ALB Amoblamientos SRL (Gral. Alvear 573) | 4,6 | 130 | "Empresa familiar", anuncio pago en Maps |
| NOVO Córdoba (12 de Octubre 2701) | 4,7 | 67 | Muebles a medida y construcción en seco |
| Amoblamientos Brum (Sta. Ana 2547) | 4,7 | 53 | |
| Amoblamientos Córdoba (Bazán de Pedraza 3138) | 4,5 | 14 | |
| Carlos Paz: Calidez 4,6 (111), Soles Muebles 4,6 (52), Bellos Amoblamientos 4,2 (17) | | | "Otras personas también buscan" en la ficha de SQL Carlos Paz (4,1, 9) |
| Río Cuarto: MODDULAR 5,0 (49), MODO 5,0 (10), Mobile 3,8 (15) | | | Junto a SQL Río Cuarto (4,6, 23) |

SQL es la marca más grande y con más reseñas; también la de rating más bajo en capital. Ninguno de los competidores
mostró chat con IA ni precios en Maps (no se recorrieron sus sitios).

### 4.2 Contexto del rubro en 2026

- Los muebles a medida "siguen creciendo como concepto" y crecieron desde la pandemia (Jorge, 2025); la isla y los
  espacios integrados mandan (InfoNegocios Río Tercero, 2025).
- Venta de ticket alto, de meses de decisión, con varias visitas y presupuestos: la consulta que no se contesta pronto
  se va a otro fabricante ("Por suerte hay muchas empresas en el rubro", reseña de hace 4 años).
- El financiamiento pesa: Jorge destacó el Ahora 12 en 2015 y en 2025 la empresa habla de "bancos que hoy dan
  herramientas accesibles".

## 5. Dolores detectados (con evidencia)

Reseñas de Google Maps leídas el 22-oct-2026, sin autores (copia en `raw/resenas.txt`).

- **D1. Presupuestos que no llegan o tardan.** Es la queja más repetida y abarca 8 años y dos locales:
  - "fuimos a pedir presupuesto nos dijo que enviarian por mail ... y nunca enviaron nada" (casa central, 1★, hace 8 años);
  - "hace más de 45 días que concurrí les dejé planos ... y nunca me enviaron un presupuesto o una propuesta. Por suerte
    hay muchas empresas en el rubro" (1★, hace 4 años);
  - "quedaron en pasarme el presupuesto para el día sig. ... quedó en pasarlo el lunes... aún lo estoy esperando" (Carlos
    Paz, 1★, hace 10 meses); la empresa respondió 8 meses después: "nuestros presupuestos a veces llevan un poco mas de
    tiempo";
  - "no me quiso dar un presupuesto... a pesar de tener fotos y medidas" (casa central, 1★, hace 8 meses).
  - "presupuesto" es uno de los temas de Maps (10 reseñas).
- **D2. Plazos de entrega e instalación, y aviso al cliente.** "Pagamos en efectivo la suma total y nos dijeron que en
  marzo lo instalarian. Terminaron de instalarmelo en JUNIO 24'" (1★, hace 2 años); "Demoras en la entrega" (1★, hace 7
  años). Choca con la promesa de Jorge: "cumplimos a rajatabla con los tiempos estipulados". Las reseñas buenas recientes
  dicen lo contrario ("Los plazos de entrega fueron los pactados"): el dolor no es el plazo, es **no saber**.
- **D3. Posventa por mensajes sin respuesta.** "me canse de escribirles durante meses para que me vengan a colocar
  zócalos ... y a arreglar ripado" (Carlos Paz, 1★, hace 1 año); "la falta de interés por solucionar problemas luego de
  varios reclamos" (1★, hace 7 años).
- **D4. Sin un canal de reclamos.** Las respuestas de la empresa en Google piden "un número de contacto" o "que nos
  escriba por msj privado" (2020, 2022): el reclamo llega por la reseña pública porque no hay un lugar donde dejarlo con
  número de caso.
- **D5. Una red grande con contacto disperso.** 20 puntos de venta, 9 provincias, la mayoría con Gmail o Hotmail
  propio; el sitio manda a todos al mismo WhatsApp de Córdoba y pone el fijo de Córdoba en páginas de Chaco o Chubut.
  No hay forma de saber cuántas consultas entran por cada lado ni cuántas se pierden (inferencia: hay que validarlo).
- **D6. Horario.** 44 h abiertas por semana en casa central (26 %): cerrado al mediodía, después de las 18, el sábado a
  la tarde y el domingo. El sitio y el píxel de Meta captan consultas a toda hora; el WhatsApp las recibe y espera.
- **D7. Lo que muestra el showroom contra lo que llega** ("no son de la misma calidad que los que vimos en el showroom",
  hace 2 años) y la instalación (tema de 12 reseñas). Son de producción e instalación: el agente solo puede registrarlos
  bien y dar seguimiento.

## 6. Pistas de interés en voz, WhatsApp e IA

- **Ya invierten en captar consultas:** campañas en TV, ruta y redes (2015), píxel de Meta en el sitio, showroom "que
  servirá de captación de clientes" (2025). Un agente que atiende cada consulta captada es la continuación lógica: no
  hay que convencerlos de que la consulta vale.
- **El WhatsApp es su canal principal:** está en el sitio, el Linktree, Instagram y el showroom. Todo entra por ahí.
- **Marketing es el primer contacto (Pilar):** el argumento para ella es saber **de dónde viene cada consulta y qué pasó
  con ella** (campaña, Instagram, Google, showroom), no solo responder más rápido.
- **Usan tecnología como argumento de venta** ("renders hiperrealistas, comunicación constante y un sistema de
  producción totalmente industrializado", InfoNegocios Río Tercero, 2025). "Comunicación constante" es justo lo que
  falla en las reseñas de D2 y D3.
- **Franquicias:** Jorge habla de dar "respuestas rápidas a nuestros distribuidores" (2015). Un canal central que
  califica y deriva a la franquicia de la zona es un servicio que también le da a la red.
- No hay señales de chatbot, IA ni respuestas automáticas más allá del saludo fijo del botón de WhatsApp.

## 7. El mejor caso de uso: "el asesor de guardia" en el WhatsApp y el teléfono

### 7.1 La propuesta

**Propuesta de valor:** ninguna consulta sin respuesta y ningún presupuesto olvidado. Un agente con voz argentina
atiende el WhatsApp central y la línea de casa central a toda hora, califica el proyecto, lo pone en manos del asesor o
la franquicia que corresponde, le hace seguimiento hasta que sale el presupuesto y acompaña al cliente durante la
producción, la instalación y la posventa. Jorge ve todo en un panel.

**Diagrama: canales → agente → áreas del equipo**

```
 CANALES                         AGENTE "asesor de guardia"            ÁREAS DE SQL
 ───────                         ──────────────────────────            ────────────
 WhatsApp 351 617-5120  ──┐      1. Responde en segundos, 24/7     ┌─► Ventas y diseño: asesores de casa central,
 (sitio, Linktree, IG)    │         (texto o nota de voz)          │   Rafael Núñez, Carlos Paz, Río Cuarto
 Línea 0351 465-4531  ────┼────► 2. Califica: ciudad, ambiente,  ──┼─► Franquicias y distribuidores (por zona)
 Formulario /cotizar  ────┤         medidas/planos, plazo, rango   ├─► Producción (Jorge): estado del pedido
 Link para llamar (web) ──┘      3. Agenda medición o showroom     ├─► Instalación: fecha, aviso, reprogramación
                                 4. Sigue el presupuesto           ├─► Posventa: reclamo con número de caso
                                 5. Informa estado de la obra      ├─► Administración (hijos): pagos, financiación
                                 6. Toma reclamos                  └─► Marketing (Pilar): origen de cada consulta
                                          │
                                          ▼
                         PANEL PARA JORGE: todas las conversaciones, de todos los canales y sucursales
```

| Canal | Qué hace el agente | Paso a una persona |
|---|---|---|
| **WhatsApp central** | Texto y notas de voz; califica, explica el proceso, agenda, informa estado, toma reclamos | Ficha al asesor o a la franquicia (hoy por resumen por email; el relay al WhatsApp del vendedor está por construir, 7.4) |
| **Línea de casa central** | El mismo agente por voz, también al mediodía, de noche y el fin de semana | Ficha por email; la transferencia de la llamada no existe (7.4) |
| **Formulario /cotizar** | (fase 2) que el agente escriba por WhatsApp a quien completó el formulario, en minutos | Igual |
| **Panel** | Todo registrado, con transcripción, resumen y resultado | Métricas de abajo |

**Métricas que querría ver Jorge en el panel:**

| Métrica | Para qué |
|---|---|
| Consultas por canal, por día y por hora (cuántas fuera de horario) | Dimensiona el D6 y la línea de base |
| Consultas por ciudad y sucursal o franquicia destino | Ve la red completa (D5) |
| Tiempo a la primera respuesta | Hoy desconocido |
| Proyectos calificados por ambiente (cocina, placar, vestidor, baño, living) y por rango de inversión | Qué se vende y a quién |
| **Presupuestos pendientes con más de N días**, por asesor | El D1, con nombre y fecha |
| Visitas al showroom y mediciones agendadas | Conversión de la consulta |
| Pedidos en producción contra el plazo prometido (90-100 días) y consultas de "¿cómo va lo mío?" | El D2 |
| Instalaciones agendadas y reprogramadas | El D2 |
| Reclamos de posventa abiertos y días hasta cerrarlos | D3 y D4 |
| Origen de cada consulta (Instagram, anuncio, Google, showroom, referido) | Lo que le sirve a Pilar |

### 7.2 Por qué es el mejor caso

- **La evidencia está en sus propias reseñas:** D1 a D4 son seguimiento y comunicación, no producto.
- **El ticket es alto:** una cocina a medida que se pierde por un presupuesto que no salió vale mucho más que el piloto
  (inferencia; no hay precios publicados para cuantificarlo, pedirlo en la charla).
- **No cambia cómo venden:** el asesor sigue haciendo la medición, el render y el cierre; el agente le saca la primera
  respuesta, la calificación y el seguimiento.
- **Sirve a todos los que van a la reunión:** a Pilar (origen y destino de cada consulta), a los hijos
  (administración: pagos, financiación, estado), a Jorge (producción y la promesa de los plazos).

### 7.3 Guion de la demo (5 minutos)

1. **Antes:** crear el agente `sql_demo` en el cliente `atentina` con la base de la parte 8, voz `sofia` (o una
   masculina del catálogo), las líneas de cocina del sitio y los 20 puntos de venta; rutear el WhatsApp de demo a ese
   agente para el número de quien vaya a probar (`wa_routes`). Pedir el número de Pilar o Jorge antes.
2. **WhatsApp, "domingo a la noche":** "Quiero hacer la cocina, tengo una pared de 3,20 m, ¿cuánto sale?". Nota de voz:
   pregunta ciudad, estilo y plazo, explica el proceso (medición, render, presupuesto, 90 días de fabricación), no
   inventa un precio y ofrece visita al showroom de Rafael Núñez el martes o que un asesor lo llame el lunes.
3. **WhatsApp, cliente de Neuquén:** "Estoy en Neuquén, ¿tienen local?". Le da el local de Juan Julián Lastra 130 con
   su horario y le avisa que se lo pasa a ellos.
4. **Teléfono, posventa:** llama a la línea de demo "como si fueran las 13:30": "me instalaron la cocina hace dos
   semanas y una puerta no cierra". Abre el reclamo, pide dirección, fecha de instalación y que mande fotos (ver 7.4: hoy
   las fotos no se procesan), y le dice qué sigue.
5. **Cierre, el panel:** las tres conversaciones con transcripción, resumen y tipo, y el resumen por email que recibiría
   el asesor. Comparación: "La reseña dice 'aún lo estoy esperando'; esto fueron 40 segundos y quedó registrado".

### 7.4 Qué hay hoy y qué falta

Revisado contra los docs el 22-oct-2026 (mismo estado que en [`isaiasgoldman.md`](isaiasgoldman.md), 7.4):

| Pieza | Estado |
|---|---|
| Agente de voz entrante en un número de Anura | En producción. Su fijo 0351 465-4531 no se mueve: o desvían a un número nuestro (fuera de horario o si no atienden) o se usa un número nuevo. A definir con ellos |
| WhatsApp: texto, notas de voz, llamadas de WhatsApp | En producción. Conectar su 351 617-5120 a la Cloud API tiene costo para ellos: el número deja la app común. La **coexistencia** (seguir usando la app de WhatsApp Business y que la plataforma registre todo) está a implementar ([`../../WHATSAPP_PLAN.md`](../../docs/WHATSAPP_PLAN.md), 5.7). El alta por Embedded Signup espera la aprobación de Meta |
| **Fotos y planos por WhatsApp** | **Falta.** Hoy el agente contesta un mensaje fijo a imágenes y documentos (`WA_UNSUPPORTED_REPLY`). En este rubro los clientes mandan fotos y planos: hace falta guardarlos y pasarlos al asesor con la ficha. El OCR existe solo para operadores de las apps por cliente |
| Triage por tipo de consulta | Hecho con los `outcomes` del agente (presupuesto nuevo, estado de pedido, posventa, franquicias, administración, fuera de tema) |
| Derivación al asesor | **Parcial:** resumen por email de cada llamada (desplegado el 20-oct-2026). El relay al WhatsApp del vendedor (5.8) y la transferencia de llamadas **faltan** |
| Derivación por zona a franquicias | Con la lista de puntos de venta en la definición del agente, el agente da el contacto al cliente. El aviso a la franquicia, hoy por email; con 5.8, por WhatsApp |
| Seguimiento del presupuesto (D1) | **Falta** como función: requiere saber qué presupuestos están pendientes (una app por cliente, [`../../archive/APPS.md`](../../docs/archive/APPS.md), o una planilla que ellos carguen) y avisar al asesor y al cliente. Las campañas de WhatsApp (plantilla a una lista) existen y sirven para un aviso masivo, no para este seguimiento uno a uno |
| Estado del pedido y fecha de instalación (D2) | **Falta:** el dato vive en su sistema o planilla. App por cliente con herramientas que lo lean |
| Reclamos con número de caso (D3, D4) | Hoy queda como resultado de la conversación en el panel; un registro con estado es parte de una app por cliente |
| Panel | **Parcial:** conversaciones, completas, objetivo cumplido, minutos, tiempo de respuesta, gráfico diario, transcripción y resultado. Falta desglose por tipo (`outcome`), por canal, por sucursal destino, fuera de horario y las métricas de presupuestos y obras |
| Origen de la consulta (Pilar) | **Falta:** se puede preguntar en la conversación y guardarlo como dato; el cruce con anuncios de Meta no existe |
| Link para llamar desde la web | Desplegado el 19-oct-2026 (falta una llamada real de punta a punta) |
| Campañas de llamadas salientes | Implementadas, **sin desplegar**: no ofrecer en el piloto |
| Grabación | Existe, apagada; antes de usarla hay que avisar a quien llama y corregir la política de privacidad |
| Capacidad con el LLM vigente (Gemma) | **Sin medir:** no citar cifras de llamadas simultáneas |

### 7.5 Fases sugeridas

1. **Piloto de 30 días:** WhatsApp central y línea de casa central (o desvío fuera de horario), calificación, respuestas
   sobre el proceso y los locales, agenda de visita al showroom o pedido de medición, ficha al asesor por email, reclamos
   de posventa registrados y el panel. Línea de base: que ellos cuenten antes cuántos mensajes y llamadas entran por
   semana y cuántos presupuestos están pendientes.
2. **Fotos y planos** por WhatsApp hacia el asesor, y **relay al WhatsApp del asesor** (5.8).
3. **Seguimiento de presupuestos y estado de obra** con una app por cliente que lea su planilla o sistema.
4. **Red de franquicias:** derivación por zona con aviso por WhatsApp a cada franquicia y métricas por punto de venta.
5. **Formulario /cotizar → WhatsApp** en minutos, y origen de cada consulta para marketing.

### 7.6 La oferta (formulable)

- **Qué incluye:** el agente configurado con su proceso, líneas, locales y políticas, en WhatsApp (texto y notas de voz)
  y en la línea; calificación y derivación con ficha; registro de reclamos; panel; resumen por email de cada
  conversación; ajustes semanales durante el piloto.
- **Cómo se mide:** consultas por canal y hora (cuántas fuera de horario), tiempo a la primera respuesta, proyectos
  calificados, visitas y mediciones agendadas, consultas derivadas por sucursal, reclamos registrados. Contra la línea
  de base que entreguen.
- **Piloto:** 30 días, alcance acotado (casa central y showroom, no toda la red), **precio fijo y bajo, no gratis**
  ([`../plan-salida-al-mercado.md`](../plan-salida-al-mercado.md), parte 5). Si funciona: contrato mensual y sumar
  franquicias.
- **Precios publicados (landing, `landing/src/data/site.ts`):** Mostrador $ 29.000/mes (300 minutos, 1 llamada a la
  vez, 1 número), Sucursal $ 99.000/mes (1.200 minutos, 3 a la vez, 3 números), Red a medida (más de 5.000 minutos).
  Son planes de voz.
- **Pendiente (no documentado, no inventar):** precio del piloto; precio del WhatsApp de texto y quién paga las
  plantillas de Meta; precio de una app por cliente (presupuestos, obras, reclamos). Con dos locales en capital y una red,
  el punto de partida probable para la voz es Sucursal o Red: **a validar con el usuario**.

## 8. Base para el prompt del agente

### 8.1 Rol y tono

- **Rol:** "Sos Sofía, del equipo de SQL Amoblamientos, fábrica cordobesa de muebles a medida desde 1981: cocinas,
  placares, vestidores, baños y living, diseñados, fabricados e instalados por SQL. Ayudás a quien consulta a arrancar
  su proyecto, lo ponés en contacto con el asesor o el local de su zona, le contás cómo va su pedido y tomás los
  reclamos."
- **Tono:** cálido, de vos, con oficio; frases cortas; una pregunta por vez en el teléfono. Cuida al asesor: "te va a
  atender Martín, que es el que te va a hacer el diseño".

### 8.2 Reglas

1. **Sin precios** salvo los que SQL cargue, con fecha. Sin lista: "el presupuesto depende de las medidas y los
   materiales; lo arma un asesor después de medir o con tus planos".
2. **El proceso, siempre igual:** medición o planos → diseño con render → presupuesto → seña → fabricación (90 a 100
   días) → instalación con equipo propio → garantía de 5 años. No prometer otro plazo.
3. **No confirmar fechas de obra ni de instalación** sin el dato del sistema: "lo consulto con producción y te escribo
   hoy antes de las 18".
4. **Siempre un próximo paso con fecha:** visita al showroom, medición, llamada del asesor. Nunca "te pasamos el
   presupuesto" sin día.
5. **Fotos y planos:** pedirlos y avisar que los ve el asesor (cuando el canal los soporte; hoy no, 7.4).
6. **Zona:** si el cliente no es de Córdoba capital o Carlos Paz, darle el local de su zona de la lista (2.2), con el
   nombre del comercio, el horario y el WhatsApp, y avisar a ese local.
7. **Reclamos:** tomar dirección, fecha de instalación, qué pasó y fotos; dar número de caso y plazo de respuesta. No
   discutir responsabilidades.
8. Decir que es un asistente virtual si se lo preguntan. No hablar de la competencia.

### 8.3 Triage y datos

| Salida (`outcome`) | Cuándo | Datos a pedir |
|---|---|---|
| Proyecto nuevo | Quiere cocina, placar, vestidor, baño o living | Nombre, ciudad, ambiente, medidas o planos, obra nueva o remodelación, plazo, rango de inversión, cómo nos conoció |
| Visita o medición | Quiere ver el showroom o que midan | Día y franja, dirección (si es medición), local |
| Estado del presupuesto | Ya consultó y espera | Nombre, local, asesor, fecha de la consulta |
| Estado del pedido | Ya compró | Nombre, número de pedido o fecha de compra, local |
| Posventa / reclamo | Algo falla después de instalar | Dirección, fecha de instalación, qué pasó, fotos |
| Franquicias | Quiere abrir un local SQL | Ciudad, rubro actual, contacto (para la gerencia) |
| Administración | Pagos, facturas, financiación | Nombre, pedido, consulta |
| Fuera de tema | Otra cosa | Cortar con amabilidad |

**Ficha al asesor:** "Proyecto nuevo, cocina en L, 3,20 + 2,40 m, remodelación, Córdoba (Cerro), quiere arrancar en
diciembre, rango medio-alto, vio un anuncio en Instagram. Visita al showroom martes 17 h."

### 8.4 Preguntas para la charla (descubrimiento)

1. ¿Cuántos mensajes de WhatsApp y llamadas entran por semana a casa central y al showroom? ¿Cuántos fuera de horario?
2. ¿Quién contesta el 351 617-5120 hoy, desde qué teléfono, y cómo se reparte entre asesores y franquicias?
3. ¿Cuánto tarda un presupuesto desde la medición? ¿Cuántos están pendientes hoy? ¿Qué pasa cuando no sale?
4. ¿Cuántas consultas terminan en venta, y cuánto vale una cocina promedio?
5. ¿Cómo se entera el cliente del estado de su pedido durante los 90 días? ¿Cuántas consultas de "¿cómo va lo mío?"
   reciben?
6. ¿Cómo llegan y se registran los reclamos de posventa?
7. (Pilar) ¿De dónde vienen las consultas (anuncios, Instagram, Google, showroom)? ¿Lo miden?
8. ¿Qué tendría que pasar en 30 días para seguir? ¿Quién decide: Jorge, los hijos?

## 9. Fuentes

Todas leídas el 22-oct-2026.

- **Sitio:** https://sqlamoblamientos.com.ar/ · /fabrica-de-muebles-en-cordoba/sucursales-de-fabrica-de-muebles-de-cocina/
  · /contacto/ · /cotizar/ · /linea-de-cocinas-a-medida/ · /sitemap.xml · /wp-json/wp/v2/pages · /robots.txt
- **Linktree:** https://linktr.ee/sqlamoblamientosoficial · **WhatsApp:** https://wa.me/5493516175120
- **Instagram:** https://www.instagram.com/sqlamoblamientos/ · **Facebook:** https://www.facebook.com/sqlamoblamientosoficial/
- **Google Maps:** "SQL Amoblamientos OFICIAL" (Av. Fuerza Aérea Argentina 3376), "SQL Amoblamientos Rafael Núñez",
  "SQL Amoblamientos Villa Carlos Paz", "SQL Amoblamientos Rio Cuarto"; búsqueda "amoblamientos de cocina a medida
  Córdoba capital".
- **Prensa:**
  - InfoNegocios, Tarjetero: https://infonegocios.info/tarjetero/empresa/sql-amoblamientos
  - InfoNegocios, 23-abr-2025: https://infonegocios.info/plus/sql-amoblamientos-prepara-el-showroom-mas-importante-de-su-historia-400-m2-sobre-av-rafael-nunez
  - InfoNegocios, Un Café con, 22-ago-2025: https://infonegocios.info/un-cafe-con/sql-amoblamientos-100-personalizados-e-instalados-en-90-dias-showroom-propio-en-zona-norte
  - InfoNegocios Río Tercero, 10-nov-2025: https://infonegocios.info/rio-tercero/sql-amoblamientos-de-emprendimiento-familiar-a-marca-nacional-que-disena-casas-completas
  - Punto a Punto, 17-nov-2021: https://puntoapunto.com.ar/https-puntoapunto-com-ar-sql-amoblamientos-abrio-showroom-en-carlos-paz-y-piensa-en-el-mercado-internacional
  - D&F Muebles, 3-sep-2015: https://maderamen.com.ar/dyf-muebles/2015/09/03/sql-amoblamientos-y-los-resultados-tras-tres-anos-de-inversion-en-marketing-y-publicidad/
  - Economix, 6-jun-2024: https://economixtv.com/programa/sql-la-cordobesa-que-te-hace-tu-cocina-o-placard-a-medida-y-que-ya-es-la-mas-grande-del-pais/
- **Videos:** https://www.youtube.com/watch?v=FLvqUoo0JYM (2015) · https://www.youtube.com/watch?v=mwnJHAnpA9I (2020) ·
  https://www.youtube.com/watch?v=fqN0KkvlSvk (2024) · https://www.youtube.com/watch?v=Hxu5IDKBlRI (2025)
- **Producto (interno):** `landing/src/data/site.ts`, [`../../WHATSAPP_PLAN.md`](../../docs/WHATSAPP_PLAN.md) (5.7, 5.8),
  [`../../LLAMADAS_SALIENTES_PLAN.md`](../../docs/LLAMADAS_SALIENTES_PLAN.md), [`isaiasgoldman.md`](isaiasgoldman.md) (7.4).
