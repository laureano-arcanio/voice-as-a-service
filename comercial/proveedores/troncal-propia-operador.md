# Troncal propia: ser operador con numeración propia en Argentina

Relevado el 26-sep-2026 de ENACOM, normativa en argentina.gob.ar y CABASE (TelXP). Responde a
"si quisiera implementar mi propia troncal SIP y crear números yo mismo, qué se requiere y cómo se
hace". No es asesoramiento legal; los montos son los publicados y algunos pueden estar
desactualizados (se marca cuáles).

## Idea central

Nadie "crea" números: el Plan Fundamental de Numeración Nacional (PFNN, Res. SC 46/97) es del
Estado y ENACOM **asigna bloques de 10.000 números** por área local solo a **licenciatarios con el
servicio de telefonía local registrado**. Tener numeración propia significa ser operador telefónico:
licencia, registro, numeración, interconexión con las demás redes, portabilidad y obligaciones
regulatorias permanentes. La troncal SIP es la parte fácil; Asterisk ya la hace.

Hay tres niveles, de menor a mayor compromiso:

| Nivel | Qué somos | Números | Sirve para |
|---|---|---|---|
| 0. Hoy | Cliente de Anura | De Anura, no cedibles (cl. 26) | Validar y primeros clientes |
| 1. Licenciatario sin red | Licencia TIC + registro de Valor Agregado o Reventa | De un mayorista (troncal SIP mayorista con DIDs a su nombre) | Negociar como prestador, no como cliente; volumen; sin la cláusula de no reventa |
| 2. Operador | Licencia + telefonía local + numeración + interconexión + portabilidad | Propios (bloques de ENACOM) | Escala, independencia, portar números de clientes a nuestra red |

## Nivel 2: qué se requiere, paso a paso

### 1. Sociedad y cuenta en TAD

- Persona jurídica con objeto social que incluya telecomunicaciones. Acta constitutiva, estatuto y
  acta de autoridades vigentes, inscriptos.
- Usuario en Trámites a Distancia (TAD) autorizado por AFIP para la sociedad, e inscripción en el
  RUPECO (Registro Único de Personas Responsables de Servicios de Comunicación) antes de pedir la
  licencia. Todo trámite de ENACOM es por TAD.

### 2. Licencia Única Argentina Digital (Res. MM 697/2017, Reglamento de Licencias)

- **Documentación:** representación del firmante, razón social y CUIT, estatuto y actas inscriptos,
  domicilio real y constituido, correo, declaración jurada de no tener incompatibilidades.
- **Arancel:** 125 PBU-I (Res. ENACOM 1547/2022). La PBU-I es el precio regulado del plan básico de
  internet, $800 por mes desde marzo de 2021 (Res. 205/2021). A ese valor el arancel es $100.000.
  El régimen de PBU se derogó en 2024, así que hay que confirmar con ENACOM qué valor toman hoy.
- **Plazos:** ENACOM tiene 60 días para observar; sin observaciones la licencia se entiende otorgada
  y emite el certificado en 10 días.
- La licencia habilita cualquier servicio TIC en todo el país; lo que se presta se define en el
  registro.

### 3. Registro del servicio (gratuito)

- Comunicación electrónica que identifica la resolución de la licencia, el servicio y la fecha
  estimada de inicio. Para numeración hace falta **Telefonía Local**; conviene sumar Larga Distancia
  Nacional, Valor Agregado y, si se quiere, Internacional.
- **Iniciar la prestación dentro de los 2 años** de la licencia o caduca.

### 4. Numeración (gratuito, por TAD)

- **Geográfica** (trámite ENACOM t5): nota con la cantidad de números, el indicativo interurbano
  (11, 351, 341...) y el área local; copia de la licencia; registro de telefonía local; poder del
  firmante; si ya se tiene numeración, estado de uso. Se asigna por **bloques de 10.000**. Desde la
  Res. 1369/2023 el área local es el indicativo interurbano: 300 áreas en el país.
- **No geográfica** 0800/0810 (trámite t17), mismo esquema.
- **Routing Number** para portabilidad, también a ENACOM.
- Plazos reales: las asignaciones pendientes se destrabaron en marzo de 2024 tras la 1369/2023;
  contar meses, no semanas. El nuevo PFNN estaba encargado para octubre de 2025 y no salió: la
  numeración puede cambiar de estructura.

### 5. Interconexión (Ley 27.078, RGIA Res. 286/2018)

Sin interconexión, nadie puede llamar a nuestros números ni nosotros salir. Todos los licenciatarios
tienen derecho y obligación de interconectarse en condiciones no discriminatorias, con ofertas de
referencia publicadas (Telecom, Telefónica, Claro, 2019).

- **Cargos de referencia** (provisorios, 2018, sin impuestos): terminación fija US$ 0,0045/min,
  terminación móvil US$ 0,0108/min, tránsito local US$ 0,0010/min, transporte larga distancia
  US$ 0,0027/min.
- **Directa con los tres grandes:** negociación bilateral por oferta de referencia, puntos de
  interconexión físicos, garantías. Lento y caro para un operador chico.
- **TelXP de CABASE:** punto neutral SIP con más de 40 operadores, más de 120 códigos de área y más
  de 1 millón de números. Entre socios es *bill & keep* (costo cero por minuto), por enlace de
  Internet, sin tramas ni equipos. Requisitos: socio de CABASE, licencia de telefonía, numeración
  propia (se puede entrar con los trámites en curso) y un softswitch SIP propio o tercerizado.
  Costos publicados: matrícula CABASE $21.000, cuota anual $110.000 (CABA/GBA), expensas TelXP
  $28.444 + IVA por mes, expensas de la comisión de portabilidad (COPON) $41.643 + IVA por mes.
- **Lo que TelXP no resuelve:** las redes que no son socias, es decir Telecom, Movistar y Claro, que
  son casi todos los celulares. Para eso hay que contratar tránsito a un tercero (un socio que venda
  terminación o un carrier). En nuestro caso las salientes son casi todas a celulares: la terminación
  móvil se paga igual, con numeración propia o sin ella.

### 6. Portabilidad numérica (Res. 203/2018, 1509/2020, 32/2022)

- Todo prestador de servicio portable (fijo, móvil, OMV) **debe adherir al contrato con el
  Administrador de la Base de Datos (ABD)** y cursar portaciones en las áreas con más de un
  prestador. Con 300 áreas, eso es casi siempre.
- Modelo de ruteo All Call Query: hay que consultar la base de portados en cada llamada. La
  excepción de Onward Routing venció en abril de 2023.
- Representación ante el COPON: se puede hacer a través de CABASE. Hay proveedores (VoIP Group) que
  venden la base de portabilidad y el softswitch como servicio.
- Es lo que permitiría que un cliente **porte su número a nuestra red**: el beneficio comercial más
  claro del nivel 2.

### 7. Plataforma técnica

Asterisk como está no alcanza para operar: hace falta

- un softswitch o SBC con ruteo por bloque, consulta de portabilidad, CDR y tarificación, y
  seguridad (fraude, límites por cliente);
- redundancia y monitoreo, porque ahora los cortes son nuestros y el Reglamento de Calidad
  (Res. 580/2018) fija indicadores;
- ruteo a servicios especiales y emergencias (911, 10Y, 11Y), obligatorio para un operador;
- capacidad de interceptación legal y guarda de datos de tráfico que exige la normativa.

Todo se puede tercerizar (softswitch en la nube, tránsito, portabilidad), a costo mensual.

### 8. Obligaciones permanentes del licenciatario

- **Tasa de control, fiscalización y verificación: 0,5 % de los ingresos** del servicio, y **aporte
  al Servicio Universal: 1 %** (vence el día 10 del mes subsiguiente). Declaraciones juradas
  periódicas de ingresos e indicadores a ENACOM.
- **Reglamento de Clientes de Servicios TIC (Res. 733-E/2017):** ahora nos aplica a nosotros como
  prestador frente a nuestros clientes, salvo que el contrato sea corporativo, como hace Anura en su
  cláusula 12.
- Comunicar cambios de control societario dentro de los 30 días.
- Causales de caducidad: no iniciar la prestación, falta reiterada de pago de tasas, transferencia
  sin autorización, quiebra.

## Costos y tiempos estimados (nivel 2)

| Concepto | Monto | Periodicidad | Fuente |
|---|---|---|---|
| Licencia | ~$100.000 (125 PBU-I a $800; confirmar) | Única vez | Res. 1547/2022, 205/2021 |
| Numeración, registro, routing number | $0 | — | ENACOM |
| CABASE (matrícula + cuota) | $21.000 + $110.000 | Única + anual | telxp.cabase.org.ar |
| TelXP | $28.444 + IVA | Mensual | ídem |
| COPON (portabilidad) | $41.643 + IVA | Mensual | ídem |
| Tránsito a redes no socias | según carrier, con mínimos | Mensual | a cotizar |
| Softswitch/SBC y base de portabilidad tercerizados | a cotizar | Mensual | VoIP Group u otros |
| Tasa de control + Servicio Universal | 1,5 % de los ingresos | Mensual | Ley 27.078 |
| Abogado regulatorio y horas de gestión | a estimar | Continuo | — |

Los fijos publicados suman del orden de **$90.000 por mes** más tránsito, plataforma y gestión,
contra el abono de Anura de $140.000 que asume la calculadora. La diferencia no está en la cuota:
está en el trabajo, las obligaciones y el tiempo.

Tiempo realista de punta a punta: **6 a 12 meses** (licencia 2 a 4 meses, numeración varios meses,
interconexión y portabilidad en paralelo).

## Qué cambia para el negocio si somos operador

- **Gana:** control total de los números (sin cláusula 26 ni riesgo de rescisión de Anura), sin costo
  por DID, entrantes casi gratis (bill & keep con socios; tránsito con los grandes), portabilidad
  entrante para clientes que quieren traer su número, y una posición de prestador para negociar
  mayorista.
- **No cambia:** la terminación en celulares se paga igual (referencia US$ 0,0108/min más tránsito).
  El ahorro por minuto saliente frente a Anura existe pero no es el motivo.
- **Pierde:** meses de trámite, obligaciones de operador (calidad, clientes, emergencias,
  interceptación, informes, 1,5 % de ingresos) y una plataforma carrier que hoy no tenemos.

## Recomendación

1. **Ahora:** seguir en nivel 0 con el programa de partners de Anura y un segundo proveedor
   (ver [`anura-terminos-2026.md`](anura-terminos-2026.md)).
2. **Cuando haya tracción (decenas de clientes con número nuestro):** pedir la **licencia TIC** con
   registro de Valor Agregado y Reventa (nivel 1). Es barata, tarda 2 a 4 meses y habilita a
   contratar troncales mayoristas con DIDs por volumen como prestador. Conviene registrar
   Telefonía Local en el mismo trámite para no repetirlo.
3. **Nivel 2 solo si** el negocio necesita portabilidad entrante o cientos de DIDs, y con la
   plataforma tercerizada (softswitch, portabilidad, tránsito) antes que construida.

## Preguntas abiertas

- Valor vigente de la PBU-I para el arancel (ENACOM, 0800-333-3344).
- Si un licenciatario con registro de Reventa puede tener DIDs de un mayorista a su nombre
  comercial y qué mayoristas lo ofrecen (Telecom, IPLAN, Metrotel, socios de TelXP).
- Costo y mínimos del tránsito hacia Telecom, Movistar y Claro desde TelXP.
- Estado del nuevo PFNN: si cambia la estructura de numeración, conviene esperar antes de pedir
  bloques.

## Fuentes

- ENACOM: [numeración geográfica (trámite t5)](https://www.enacom.gob.ar/tramites/numeracion-y-senalizacion-solicitud-asignacion-numeracion-geografica_t5),
  [numeración no geográfica (t17)](https://www.enacom.gob.ar/tramites/numeracion-y-senalizacion-solicitud-asignacion-numeracion-geografica-8xy-6xy-_t17),
  [licencias TIC](https://www.enacom.gob.ar/licencia-unica-de-telecomunicaciones_p2360),
  [costos de licencia](https://www.enacom.gob.ar/licencias-de-servicios-de-tecnologias-de-la-informacion-y-las-comunicaciones_p750),
  [interconexión y cargos de referencia](https://enacom.gob.ar/interconexion_p135),
  [ofertas de referencia](https://www.enacom.gob.ar/reglamento-general-de-interconexion-y-acceso_p4004),
  [numeración](https://www.enacom.gob.ar/numeracion_p136).
- Normativa: [Res. 697/2017, Reglamento de Licencias](https://www.argentina.gob.ar/normativa/nacional/norma-305406/actualizacion),
  [Res. 1547/2022, arancel](https://www.argentina.gob.ar/normativa/nacional/norma-369697/texto),
  [Res. 205/2021, PBU-I](https://www.argentina.gob.ar/normativa/nacional/norma-347338/texto),
  [Res. 286/2018, RGIA](https://www.argentina.gob.ar/normativa/nacional/resoluci%C3%B3n-286-2018-310436/texto),
  [Res. 203/2018, portabilidad](https://www.argentina.gob.ar/normativa/nacional/resoluci%C3%B3n-203-2018-308504/texto),
  [Res. 1369/2023, áreas locales](https://www.argentina.gob.ar/normativa/nacional/resoluci%C3%B3n-1369-2023-391800/texto).
- CABASE TelXP: [cómo asociarse](https://telxp.cabase.org.ar/notas/20-11-09-como-asociarte-al-punto-de-interconexion-telxp.html),
  [asociate (costos vigentes)](https://telxp.cabase.org.ar/asociate.html),
  [servicios](https://telxp.cabase.org.ar/servicios.html),
  [portabilidad, estado 2025](https://telxp.cabase.org.ar/notas/25-11-02-portabilidad-numerica-en-la-argentina-estado-de-situacion.html),
  [asignaciones 2024](https://telxp.cabase.org.ar/notas/24-03-05-enacom-asigno-nuevos-recursos-numericos.html).
- [VoIP Group, base de portabilidad para ISPs y cooperativas](https://www.voipgroup.com/produtos/1o-base-de-portabilidad-numerica-de-telefonia-para-isps-cooperativas-y-operadoras-de).
