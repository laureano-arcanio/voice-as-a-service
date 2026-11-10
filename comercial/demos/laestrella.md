# Empresa La Estrella: base de conocimiento para la propuesta (7-nov-2026)

Empresa La Estrella S.R.L. es una empresa familiar de colectivos de corta y media distancia de Resistencia (Chaco), con
89 años en enero de 2024, según su gerente. Une Resistencia con unas 60 localidades del interior chaqueño. El usuario
habló con ellos el 6-nov-2026: están interesados en contratar. Quieren 6 puntos de atención, mantener sus números,
desviarlos a un agente de Atentina y que el agente derive a una persona o sucursal solo cuando haga falta. El documento
sirve para preparar la propuesta y como base del agente. Lead en el CRM: ver la parte 9.

- **Fuentes, leídas el 7-nov-2026:** el sitio completo (es una sola página, más `horarios.js` con todos los horarios y el
  portal de pasajes de Micronauta); directorios (latinoplaces, que copia la ficha de mapas con 14 reseñas, La Guía Online,
  Punto Pasajes, eldirectorio); las páginas de las terminales de Resistencia, Sáenz Peña, Villa Ángela, Charata y Castelli
  (terminaldemicros.com.ar); agregadores de pasajes (Central de Pasajes, CheckMyBus, Bookaway); Diario Norte (10 y
  12-ene-2024, 28-jul y 5-ago-2026), El Mirador Chaco y Región Litoral; la Res. 437/2019 de Transporte de la Nación.
  Links en la parte 10.
- **Copia local:** `scratch/prospectos/laestrella/raw/` (HTML del sitio, `horarios.txt` con las 37 salidas,
  `resenas.txt`, notas de prensa, PDF de la resolución).
- **No se encontró:** la ficha de Google Maps en directo (en esta sesión no había navegador; se usó la copia de
  latinoplaces); Facebook o Instagram oficiales con su URL (hay rastros de una página de Facebook con botón de WhatsApp);
  LinkedIn; ningún email de una persona; la lista oficial de sucursales o boleterías.
- **Partes 1 a 5:** datos. Las partes 6 a 8 son nuestras y hay que validarlas con la empresa.

## 0. Resumen para la propuesta

- **Quién es:** colectivos interurbanos del Chaco, con sede en Ameghino 768 (Resistencia) y boletería 12 en la Terminal de
  Ómnibus de Resistencia. Tiene 13 corredores (ida y vuelta) y 37 salidas en el sitio, más alquiler de unidades (45, 58
  o 62 asientos), paquetería y una tarjeta prepaga con recarga por Mercado Pago. El gerente que habla con la prensa es
  **Francisco Ptak** (Diario Norte, ene-2024).
- **Su contexto:** el sector está en crisis. En ene-2024 hubo un paro de UTA en La Estrella por salarios atrasados, y Ptak
  dijo que ya no hay refuerzos, que hay "un ómnibus por servicio y horario" y que dejaron de ir a Castelli. En 2026 el Gran
  Resistencia perdió el 31 % de los pasajeros (2024 a 2025) y la provincia lanza ChacoBus (GPS, app, billeteras). Una
  empresa que recorta personal y servicios necesita atender más con menos gente: es el argumento.
- **Dolores, con evidencia:**
  1. **Horarios contradictorios por canal:** el sitio tiene `horarios.js` de jun-2023 (y la página, de ene-2024), sigue
     mostrando el corredor por Castelli que el gerente dijo que se dejó, y no coincide con la terminal de Sáenz Peña (3:15,
     4:50, 9:00, 18:00 y 18:30 contra 9:00, 17:00, 18:00 y 18:05 en el sitio). Reseña: "Actualicen los horarios de
     atención [...] cierran a las 19:30 y acá dice a las 20:00".
  2. **Mostrador saturado:** "Me costó dejar un paquete para envío. Ya que se encontraba muy sobrecargado la compra de
     boletos". Boletos, encomiendas y consultas pasan por la misma gente.
  3. **Canales digitales rotos:** el formulario de alquiler del sitio envía a `email-alquiler.php`, que da 404; el de
     contacto está comentado en el HTML; el botón de WhatsApp del portal de pasajes apunta a `5493` (un número
     incompleto); el ícono de Facebook del sitio no tiene link.
  4. **Muchos números sueltos:** 3 fijos en el sitio, otro en la terminal, otro en Sáenz Peña y un WhatsApp que solo
     publican terceros. Cada uno contesta lo mismo: horarios, precios, equipaje, encomiendas, devoluciones.
- **Competencia:** en sus corredores, La Termal (boletería 13), Cruz del Sur (que el gerente nombra junto a La Estrella:
  "La Estrella Cruz del Sur"), Bermejo Bus y, en larga distancia, Flecha Bus. Una reseña la llama "monopolio" en el tramo
  Resistencia a Villa Ángela. No se encontró a ninguna con agente de voz o bot.
- **Caso de uso:** un **agente de boletería** que atiende los 6 números (desviados) y el WhatsApp. Contesta horarios por
  tramo y día, paradas, equipaje, devoluciones, encomiendas, alquiler y tarjeta, y deriva a la boletería o sucursal que
  corresponde solo para lo que no puede resolver (venta con asiento, reclamo, encomienda perdida, presupuesto de alquiler).
- **Oferta:** piloto de 30 a 60 días, con los 6 números desviados, precio fijo a definir (6 puntos superan el plan
  Sucursal, de 3 números: es plan Red, a medida, parte 7.6).
- **Qué no se pudo verificar:** con quién habló el usuario, cuáles son los 6 puntos, el volumen de llamadas, la vigencia
  de los horarios y precios, quién es hoy el dueño o socio gerente, y si las líneas de las sucursales permiten desvío.

## 1. La persona: Francisco Ptak

- **Cargo:** gerente de La Estrella (Diario Norte, 10 y 12-ene-2024). En la entrevista de NORTE Play (10-ene-2024) se lo
  presenta como "el gerente de La Estrella Cruz del Sur".
- **Frases propias (10-ene-2024):** "Estamos muy lejos de salvar los costos operativos. Además de nosotros y otra empresa
  del interior decidimos reducir algunos servicios". "Ya no hay adicionales ni refuerzos. En algunos casos se redujeron
  distancias, con cabeceras que ya no se cumplen como antes". Dijo que en "los 89 años de existencia de la empresa nunca se
  había convocado a un paro provincial". Pidió extender la vida útil de las unidades y habló de subsidios que cubren $ 500
  a $ 700 de un costo de $ 1.500 por km.
- **No se encontró:** LinkedIn, email, otras entrevistas, ni si es dueño o empleado. Un directorio (sin acceso, 403)
  atribuye la fundación a un Francisco Ptak que empezó con un minibús Makallé a Resistencia, y menciona a un hijo,
  Estanislao Francisco Ptak; **no verificado**, solo se leyó el resumen del buscador.

## 2. La empresa: Empresa La Estrella S.R.L.

### 2.1 Datos

| Dato | Valor | Fuente |
|---|---|---|
| Razón social | EMPRESA LA ESTRELLA S.R.L. | Res. 437/2019, Transporte de la Nación (anexo de subsidios, jurisdicción provincial Chaco) |
| CUIT | 34-54636455-2 | Ídem. CUIT Online lista el mismo CUIT como "Empresa La Estrella S.A.", y Región Litoral usa "S.A.": a confirmar |
| Sede | Ameghino 768, Resistencia (H3500) | sitio (lo escribe "Ameguino") |
| Antigüedad | 89 años en ene-2024 (fundada hacia 1935) | Diario Norte, 10-ene-2024, por el gerente |
| Personal | Administrativos, choferes, mecánicos, auxiliares y "boleterías del interior"; "familias enteras" | sitio, "Conocenos" |
| Subsidio nacional 2019 | $ 166.338,33 (La Termal: $ 105.000) | Res. 437/2019 |
| Legislatura Chaco 2016 | Res. 92: pide extender su recorrido | Boletín Oficial Chaco n.º 9925 |
| Paro de UTA | 12-ene-2024 (salarios de diciembre), con Cruz del Sur y Bermejo Bus; se levantó el 13 | Diario Norte |

### 2.2 Locales, horarios y contacto

| Punto | Dirección | Teléfono | Fuente |
|---|---|---|---|
| Sede (administración, alquiler, encomiendas) | Ameghino 768, Resistencia | (0362) 443-1251, 442-3695 y 442-1300 | sitio (los tres con `tel:`) |
| Boletería 12, Terminal de Resistencia | Av. Mac Lean 2347 | (0362) 446-0905 | terminaldemicros.com.ar; Región Litoral (2022) |
| Terminal de Sáenz Peña | F. Canteros entre Jujuy y San Luis | (0364) 442-5414 | terminaldemicros.com.ar |
| Villa Ángela | Terminal, Av. Kennedy 880 | (3624) 460905 (el de Resistencia) | terminaldemicros.com.ar |
| Charata | Terminal, Ituzaingó 160 | "Consultar en boletería" | terminaldemicros.com.ar |
| WhatsApp | | +54 9 362 533-0352 | Punto Pasajes, terminaldemicros y un link de Facebook (`entry_point=page_cta`) que copia un sitio de estudiantes (feb-2022). **No está en el sitio oficial** |
| Email | | empresalaestrellasrl@gmail.com | sitio |

- **Horarios de atención publicados:** Región Litoral (jul-2022): lunes a sábado de 7 a 20 y domingos de 18 a 20.
  Latinoplaces (copia de mapas): lun, mar, vie y sáb de 9 a 19; mié y jue de 10 a 19; dom de 11 a 19. Una reseña dice
  que a la tarde cierran a las 19:30. **Tres versiones distintas.**
- **Formularios:** alquiler de unidades (desde, hasta, fechas y horas de ida y vuelta, motivo, asientos 45, 58 o 62, si
  quiere servicio a bordo, nombre, teléfono, email, mensaje) que envía a `email-alquiler.php`, que da **404** (comprobado
  con HEAD, sin enviar nada). El formulario "Hablá con nosotros" está comentado en el HTML: se ve el título sin campos.
- **Portal de pasajes** (Micronauta, `micronauta.dnsalias.net/web/urbano/?conf=laestrella`): "Compra tu pasaje", registro
  con nombre, apellido, CUIL y email, y tarjeta con saldo y recarga por Mercado Pago ("Su Recarga estará disponible en el
  coche dentro de las 24 Horas"). El botón WhatsApp lleva a `5493` (la configuración pública devuelve
  `"whatsapp": "5493"`): no funciona.
- **Venta online por terceros:** Central de Pasajes y CheckMyBus venden sus tramos (Sáenz Peña, Villa Ángela, Machagai,
  Quitilipi a Resistencia).
- No se llamó ni se escribió a ningún número.

### 2.3 El sitio

- HTML estático en Apache, diseñado por Estudio Boris. Última modificación: 8-ene-2024 (página) y 26-jun-2023
  (`horarios.js`). Sin Analytics, píxel ni chat. Sin `robots.txt` ni sitemap (404).
- Secciones: buscador de horarios, alquiler de unidades, servicio ("semi-cama y cama | TV-Video | Baño | Aire
  climatizado | mini bar | telefonía celular | GPS"), paquetería, equipaje y condiciones, "Conocenos", contacto con mapa.
- El buscador de horarios no tiene precios.

### 2.4 Redes, publicaciones y videos

- El sitio tiene un ícono de Facebook con `href="#"`. El Mirador Chaco (ene-2024) cuenta que el levantamiento del paro "lo
  confirmaron desde la empresa la Estrella en su cuenta en redes sociales". Un link copiado de su Facebook lleva al
  WhatsApp +54 9 362 533-0352. No se encontró la URL de la página ni Instagram, YouTube o LinkedIn.

### 2.5 Recorridos, condiciones y servicios (lo que el agente tiene que saber)

**Corredores y salidas según el sitio** (37 salidas, 62 localidades; detalle por parada en
`raw/horarios.txt`; vigencia a confirmar):

| Corredor (ida / vuelta) | Paradas principales | Salidas desde Resistencia | Salidas hacia Resistencia |
|---|---|---|---|
| Resistencia a Sáenz Peña | Puerto Bastiani, Makallé, Lapachito, La Escondida, Pcia. de la Plaza, Machagai, Quitilipi | 4:00 (L-S), 14:00, 17:00 y 20:00 (todos los días y feriados) | 9:00 y 18:00 (todos los días); 17:00 directo (L-V); 18:05 por Quitilipi (D) |
| Resistencia a Santa Sylvina (3 variantes) | La Tigra, La Clotilde, San Bernardo, Villa Ángela, Coronel Du Graty; o por Sáenz Peña; o por Quitilipi y Villa Berthet | 4:00 (L-S, por Sáenz Peña), 12:30 (L-S), 15:00 (todos, por Quitilipi), 17:15 (D-V) | 1:00 (L-S, por Machagai), 3:00 y 10:45 (L-S), 15:15 (D-V y feriados); Villa Ángela 16:35 (D) |
| Resistencia a Colonia Elisa, Colonias Unidas, Laguna Limpia y Las Garcitas | Puerto Tirol, Colonia Popular, Laguna Blanca, Makallé, La Verde, La Escondida, Ing. Barbhet (así en el sitio), Capitán Solari, La Pastoril | 6:30, 11:00, 12:30, 15:30, 17:30, 20:00 | 4:10, 4:30, 12:30, 13:15, 16:00, 18:15 (D) |
| Resistencia a Miraflores | Sáenz Peña, las Pampas, Tres Isletas, J. J. Castelli, Indiana, Guadalupe | 12:30 (L-S) | 2:00 (L-S) |
| Resistencia a Tres Isletas | por Colonias Unidas, Las Garcitas y cruces de rutas 10, 4 y 44 | 15:30 (L-S) | 3:15 (L-S) |
| Resistencia a Hermoso Campo y Gancedo | Campo Largo, Corzuela, Las Breñas, Charata, General Pinedo, Itín, General Capdevila | 12:30 (L-S), 15:00 (todos) | 1:20 y 1:30 (L-S) |

**Condiciones de los pasajes (sitio, textual o casi):**
- Devolución (Res. 1317/53): 70 % dentro de las 24 h previas a la salida; 80 % entre 48 y 24 h; 90 % con más de 48 h.
  Solo al titular, con DNI. Los boletos pagados con tarjeta de crédito, débito u orden oficial "No se tomaran en
  devolución bajo ningún concepto". No hay canje por cambio de fecha u hora.
- Equipaje: 15 kg en bodega sin cargo (Res. 47/95) y 5 kg de mano; el exceso se paga según lista; todo equipaje etiquetado
  con comprobante de la empresa; Gendarmería puede requisar. No se permiten tóxicos, explosivos, inflamables, alimentos
  (carne, verduras, frutas), motos ni bicicletas.
- Menores de 5 años no pagan y no tienen asiento (con documento). El asiento puede cambiar si cambia la unidad. Seguro
  contra terceros transportados.
- Descuento de estudiante con certificado de alumno regular (sitio de estudiantes de la UNNE, feb-2022; a confirmar).

## 3. Productos y precios de referencia

- **No hay precios publicados** en el sitio. CheckMyBus muestra tarifas en dólares de un agregador (USD 9 a 12 por tramo,
  nov-2026): no sirven como precio para el agente. Los pide la empresa.
- Alquiler de unidades de 45, 58 y 62 asientos, con o sin servicio a bordo, para excursiones o movilidad en destino; La
  Guía Online suma traslados a aeropuertos, eventos, viajes escolares y transporte de empleados. Sin precios.
- Paquetería (encomiendas) en sus agencias. Sin tarifas publicadas.
- Tarjeta prepaga con recarga online.

## 4. Competencia y contexto

### 4.1 Local

| Empresa | Dónde se cruza | Contacto público | Atención digital |
|---|---|---|---|
| La Termal | Sáenz Peña, Castelli, Tres Isletas, Miraflores; boletería 13 de la TOR, (0362) 446-6195 | terminaldemicros.com.ar | No se encontró bot |
| Cruz del Sur | Interior del Chaco; el gerente aparece como "de La Estrella Cruz del Sur" | Diario Norte | No se verificó |
| Bermejo Bus | Media distancia, paró junto a La Estrella en ene-2024 | Diario Norte | No se verificó |
| Flecha Bus | Larga distancia por Castelli y Resistencia | terminaldemicros.com.ar | Venta online propia |

- Calificaciones: Central de Pasajes, 4,18 con 83 opiniones (41 de 5, 27 de 4, 7 de 3, 5 de 2 y 3 de 1); copia de la ficha
  de mapas, 3,4 con 14 reseñas (2022 a 2024).
- Ojo: Plataforma10 tiene otra "La Estrella" con terminales en Buenos Aires: no es esta empresa.

### 4.2 Contexto del transporte en el Chaco en 2026

- Cetach (28-jul-2026): el Gran Resistencia pasó de 265 colectivos en 2024 a 165 hoy; 25,4 millones de pasajeros en 2024
  y 17,5 en 2025 (-31 %); proyecta -61 % entre 2024 y 2026. Costo técnico de $ 4.200 por km y el Estado reconoce
  $ 2.900. Hay despidos y suspensiones.
- Gobierno (5-ago-2026): ERSA deja líneas urbanas y la provincia prepara una licitación y el programa **ChacoBus**
  (GPS, app de recorridos, cámaras, billeteras virtuales), con prueba piloto en Navarro. Es urbano, no interurbano, pero
  marca hacia dónde va la provincia.

## 5. Dolores detectados (con evidencia)

| # | Evidencia | Cita o dato | Qué haría el agente |
|---|---|---|---|
| D1 | Sitio contra terminal de Sáenz Peña; corredor por Castelli que el gerente dijo que dejaron | 5 horarios distintos Sáenz Peña a Resistencia; `horarios.js` de jun-2023 | Una sola tabla de horarios cargada por la empresa, con fecha de vigencia, la misma en teléfono y WhatsApp |
| D2 | Reseña, may-2023 | "Actualicen los horarios de atención [...] cierran a las 19:30 y acá dice a las 20:00" | Dice el horario de cada boletería, y fuera de horario atiende igual |
| D3 | Reseña, jun-2023 | "Me costó dejar un paquete para envío. Ya que se encontraba muy sobrecargado la compra de boletos" | Saca del mostrador las consultas (horario, equipaje, encomiendas), que se repiten |
| D4 | Sitio y portal | Formulario de alquiler a una URL 404; WhatsApp del portal a `5493`; contacto sin campos | Toma el pedido de alquiler completo por voz o WhatsApp y se lo pasa a quien cotiza |
| D5 | Reseñas, ene-2023 y jul-2022 | Asiento numerado y "sentate donde sea"; "NUNCA CUMPLEN CON EL HORIOS" | Registra el reclamo con tramo, fecha y número de boleto, y lo deriva; no lo resuelve solo |
| D6 | Gerente, ene-2024 | "Ya no hay adicionales ni refuerzos"; personal reducido | Atiende varias llamadas a la vez sin sumar gente |

## 6. Pistas de interés en voz, WhatsApp e IA

- Lo pidieron ellos: 6 puntos, mantener los números, desviar al agente y derivar solo cuando haga falta (charla del
  6-nov-2026).
- Ya venden online por un tercero (Micronauta, con Mercado Pago) y por agregadores: no les es ajeno lo digital.
- Tienen un WhatsApp que circula en terminales y agregadores, pero el del portal está roto.

## 7. El mejor caso de uso: agente de boletería con derivación por sucursal

### 7.1 La propuesta

Un agente que atiende los números de los 6 puntos (desviados a 6 números de Atentina, uno por punto) y el WhatsApp, con
voz argentina. Sabe desde qué punto entró la llamada, porque cada desvío llega a un número distinto. Responde horarios,
paradas, días y feriados, equipaje, devoluciones, encomiendas, alquiler y tarjeta. Deriva a la persona del punto
correspondiente cuando el pasajero quiere comprar con asiento, reclamar, rastrear una encomienda o cerrar un alquiler, y
si nadie atiende, toma el mensaje.

### 7.2 Por qué es el mejor caso

- Es lo que pidieron, y las consultas (horario, parada, equipaje) son repetidas y están escritas en su sitio.
- Corrige D1 y D2: una sola fuente de horarios para todos los canales.
- Entrante: no corre el riesgo de las salientes ni el Registro No Llame.

### 7.3 Guion de la demo (5 minutos)

1. Llamada al número de la terminal de Sáenz Peña: "¿A qué hora sale mañana domingo para Resistencia?". El agente da las
   salidas del domingo, la parada y la hora de llegada.
2. "¿Puedo llevar una bicicleta?" → no; "¿y cuánto equipaje?" → 15 kg en bodega y 5 de mano.
3. "Quiero devolver un pasaje que pagué con débito" → explica la condición y ofrece pasarlo con la boletería.
4. **Momento wow:** "Necesito un colectivo de 45 asientos para un viaje de egresados a Corrientes el 12 de diciembre". El
   agente toma todos los datos del formulario roto (desde, hasta, fechas, asientos, servicio a bordo, contacto) y le llega
   un WhatsApp con la ficha a quien cotiza en la sede, mientras el pasajero sigue en la línea.
5. Pide hablar con alguien: el agente deriva a la boletería de Sáenz Peña; si no atiende en 20 s, toma el mensaje.

### 7.4 Qué hay hoy y qué falta (interno, verificado contra los docs el 7-nov-2026)

| Necesidad | Estado | Fuente |
|---|---|---|
| Atender por teléfono con número de Atentina (Anura) | En producción | `docs/TELEFONIA_ANURA.md` |
| Mantener su número: desvío desde su línea a nuestro número | Sin cambio de infraestructura; el desvío lo contrata el cliente con su operador | `comercial/proveedores/anura-terminos-2026.md` |
| Saber a qué punto llamaron | Con varios números en la cuenta, Anura manda el número marcado; un número de Atentina por punto | `docs/TELEFONIA_ANURA.md`, "Número marcado" |
| Derivar a una persona o área, con horario, rotación y toma de mensaje | En producción (probada con llamadas reales el 30-oct-2026) | `docs/features/EQUIPO_TELEFONIA.md` |
| Aviso de derivación por WhatsApp a la persona | Implementado y probado en local; sin desplegar | `docs/features/WHATSAPP.md` |
| WhatsApp con el número propio del cliente | Desplegado con la app de Meta del cliente, sin probar con un número real; el alta con la app de Atentina espera a Meta | `docs/features/WHATSAPP.md` |
| Tabla de horarios consultable | Se carga en la definición del agente; una herramienta que lea una planilla está en `docs/features/HERRAMIENTAS.md`. Falta decidir el formato con ellos | — |
| Venta de pasajes con asiento | **No existe:** su sistema es Micronauta. El agente deriva o manda el link | — |

**Riesgos a resolver antes de ofrecer:**
- **El desvío y la derivación no pueden usar el mismo número.** Si la boletería desvía su fijo al agente, derivarle
  la llamada a ese fijo vuelve al agente. Cada punto tiene que tener otro destino para la derivación: un celular, otra
  línea o el panel o la app `telefono.` de Atentina. Preguntarlo en la próxima charla.
- **Canales:** la cuenta de Anura tiene 10 canales en total y una derivación ocupa 2. Con 6 puntos y temporada alta
  (diciembre y enero) hay que medir las llamadas simultáneas que tienen y verlo con Anura antes de comprometer.
- **Desvío:** confirmar con su operador (fijos de Telecom en el 0362, probablemente) si permite desvío incondicional,
  qué cuesta y si pasa el número de quien llama.
- **Capacidad del LLM vigente** sin medir: no prometer cuántas llamadas a la vez.
- **Plan:** el Sucursal tiene 3 números ($ 99.000 por mes, 1.200 minutos, 3 llamadas a la vez, derivación a 2 personas);
  6 puntos es plan Red, a medida, y su precio no está definido. Además `EQUIPO_TELEFONIA.md` dice que el tier Sucursal
  admite 5 personas y la landing dice 2: corregir antes de cotizar.

### 7.5 Fases sugeridas

1. **Semana 1:** cargar horarios, condiciones, boleterías y horarios de atención; un número de Atentina por punto;
   desviar primero 1 o 2 puntos (la sede y la terminal de Resistencia).
2. **Semanas 2 a 4:** sumar los otros 4 puntos y el WhatsApp; derivación por punto con toma de mensaje.
3. **Mes 2:** alquiler con ficha por WhatsApp a quien cotiza; reporte de consultas por tipo y por punto.

### 7.6 La oferta

- Piloto de 30 a 60 días con los 6 puntos, precio fijo y bajo, no gratis (plan, sección 5). Precio: **pendiente**
  (plan Red a medida).
- Línea de base que tienen que dar ellos: llamadas por día por punto, cuántas no se atienden y las horas pico.
- Métricas: llamadas atendidas, resueltas sin derivar, derivadas por motivo y punto, mensajes tomados, pedidos de
  alquiler.

## 8. Base para el prompt del agente

### 8.1 Rol y tono

"Atención de Empresa La Estrella". Voz argentina cálida y clara, de boletería del interior: breve, con horarios dichos
despacio ("sale a las doce y media, llega a Villa Ángela a las cuatro y veinticinco"). Tuteo o usted: preguntarles.

### 8.2 Reglas

- Horarios y paradas, solo los de la tabla vigente, con su fecha; si un tramo no está, no inventarlo: derivar.
- No vende ni reserva asientos: deriva a la boletería o pasa el link de compra.
- Precios, solo si la empresa carga una lista con fecha.
- Devoluciones y equipaje, con las condiciones del sitio, sin excepciones.
- Reclamos: tomar tramo, fecha, hora, número de boleto y contacto, y derivar.

### 8.3 Triage y datos

| Salida | Cuándo | Datos a pedir |
|---|---|---|
| Responde solo | Horarios, paradas, días y feriados, equipaje, menores, devoluciones (cómo), dónde está cada boletería y cuándo abre | Origen, destino y día |
| Boletería del punto | Comprar o reservar con asiento, cambiar o devolver un boleto, pago con tarjeta | Nombre, DNI del titular, tramo y fecha |
| Encomiendas | Enviar o rastrear un paquete | Origen, destino, remitente, destinatario y comprobante |
| Sede (alquiler) | Presupuesto de alquiler de unidades | Desde, hasta, fechas y horas, motivo, asientos, servicio a bordo, contacto |
| Administración | Reclamos, objetos perdidos, tarjeta prepaga sin saldo | Tramo, fecha, hora, boleto o número de tarjeta |
| Toma de mensaje | Nadie atiende o es fuera de horario | Motivo y teléfono para la devolución |

Resumen a la persona (WhatsApp): punto donde llamó, motivo, tramo y fecha, datos tomados y teléfono.

### 8.4 Preguntas para la próxima charla

1. ¿Cuáles son los 6 puntos (dirección, teléfono, horario y quién atiende en cada uno)?
2. ¿Cuántas llamadas por día entran a cada número, cuántas no atienden y en qué horas? ¿Cuánto crece en diciembre y enero?
3. ¿Qué preguntan más? ¿Quién atiende hoy y cuánto les cuesta (personas y horas)?
4. ¿A qué número se deriva en cada punto, si el fijo queda desviado? ¿Tienen celulares de las boleterías?
5. ¿Su operador permite el desvío? ¿Quieren desviar siempre, o solo cuando está ocupado o no atienden?
6. ¿Cuál es la tabla de horarios vigente y quién la actualiza? ¿Hay lista de precios que el agente pueda decir?
7. ¿El WhatsApp +54 9 362 533-0352 es de ellos? ¿Quién lo contesta?
8. ¿Quién decide y firma? ¿Qué tendría que pasar en 30 días para seguir?

## 9. CRM

Lead "Empresa La Estrella" (empresalaestrella.com), etapa `charla_hecha`, etiquetas `caliente`, `chaco` y `transporte`;
actividad `meeting` del 6-nov-2026 con lo que contaron; próxima acción: confirmar los 6 puntos y armar la propuesta del
piloto.

## 10. Fuentes (leídas el 7-nov-2026)

- Sitio: https://www.empresalaestrella.com/ (y `resources/js/horarios.js`); portal de pasajes:
  https://micronauta.dnsalias.net/web/urbano/?conf=laestrella
- Prensa: https://www.diarionorte.com/249594-por-primera-vez-en-89-anos-trabajadores-analizan-impulsar-una-medida-en-dos-companias-provinciales-
  (10-ene-2024); https://www.diarionorte.com/249815-acreditaron-sueldos-a-trabajadores-de-la-estrella-y-cruz-del-sur-
  (12-ene-2024); https://www.diarionorte.com/331159-la-caida-del-61-de-los-pasajeros-y-un-38-menos-de-colectivos-en-la-calle-explican-la-crisis
  (28-jul-2026); https://www.diarionorte.com/331538-el-gobierno-prepara-la-licitacion-de-las-lineas-en-conflicto-mientras-presenta-chacobus
  (5-ago-2026); https://elmiradorchaco.com/tag/la-estrella/
- Oficiales: https://www.transporte.gob.ar/UserFiles/pdfs/subsidios/sistau/documentos/Res%20437%20-%204-3%20Ago-19.pdf;
  https://chaco.gob.ar/uploads/boletines/boletin-9925-65b119505cb45771818857.pdf
- Terminales: https://www.terminaldemicros.com.ar/resistencia.html, /roque-saenz-pena.html, /villa-angela.html,
  /charata.html, /castelli-chaco.html
- Directorios y reseñas: https://ar.latinoplaces.com/chaco/la-estrella-srl-85974; https://laguiaonline.com.ar/businesses/la-estrella-srl;
  https://puntopasajes.com.ar/empresas-de-bus/la-estrella; https://www.regionlitoral.net/2021/08/horarios-la-estrella-sa-resistencia.html;
  https://unespaciofau.wixsite.com/website/post/horarios-colectivos-resistencia-interior;
  https://www.centraldepasajes.com.ar/empresas-de-micro/la-estrella.html; https://www.checkmybus.com/coach-providers/empresa-la-estrella
