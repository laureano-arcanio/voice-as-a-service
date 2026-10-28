# Seguimiento comercial

> **Congelado el 21-oct-2026.** El registro vigente es el CRM (`http://127.0.0.1:8030`, `make crm-up`; API en [`../CRM_API.md`](../../docs/CRM_API.md)), cargado desde este archivo, los `envios/` y el historial de Resend. No editar: lo nuevo va al CRM.

Registro de cada contacto: qué se envió, cuándo, si hubo seguimiento y qué contestó. Es la fuente
de verdad de la etapa de exploración ([`plan-salida-al-mercado.md`](../plan-salida-al-mercado.md),
sección 0). Los textos exactos de cada envío están en [`envios/`](envios/).

Actualizado: 21-oct-2026.

## Resumen

| Métrica | Valor | Objetivo (plan, sección 8) |
|---|---|---|
| Contactos enviados | 322 (por email: 170 hasta el 8-oct, 22 primeros contactos el 14-oct, #179–200, 60 el 15-oct, #201–268 sin los 8 descartados por 403, asunto «Llamadas de voz», 2 rebotaron (#213 y #214), 20 el 15-oct, #272–291, software con producto propio, asunto «Consulta», y 50 el 15-oct, #292–341 (tanda 2 del mismo segmento, E1–E50; 21 por Resend desde hola@atentina.com.ar y 29 desde laureano@atentina.net), asunto «Consulta»; seguimiento de los del 15-oct el 21-oct; hasta el 8-oct figuraba 171 porque contaba a Integrando Salud, #99, que respondió por LinkedIn sin mail) | ~150 |
| Borradores sin enviar | 7 (canales del 6-oct que salieron por LinkedIn, L2–L7 y L9: #92–95, 97, 98 y 100; el mail no salió). Partners 2 y 3 y las dos tandas de software con producto propio: enviados el 15-oct | — |
| Descartados sin enviar | 8 (el sitio respondió 403: #202, 203, 235, 251, 256, 257, 262, 267) | — |
| Contactos por LinkedIn (aparte, ver abajo) | 28 enviados, 1 borrador | — |
| Contactos que llegaron por otra vía (referidos, sin envío) | 3 (#269 ERP local, #270 gimnasio, #271 Inthegra: mail nuevo a hola@ el 14-oct) | — |
| Con seguimiento enviado | 103 (11 de la tanda 1 el 5-oct; 66 el 14-oct: #12–41, 10 canales del 6-oct y 26 partners del 7-oct; 6 de los 8 que hicieron clic (según Resend: #72 el 15-oct; #175, 154, 163, 67 y 44 el 14-oct a las 6:4x desde hola@atentina.net; #173 no salió y fue el 21-oct; #47 según el usuario ya recibió varias tandas); 11 el 19-oct, los que hicieron clic, con link al calendario: #205, 209, 224, 227, 230, 252, 287, 294, 300, 319 y 333, hasta el 26-oct). Esperando respuesta: 77 (9 del 21-oct, hasta el 28-oct: #341, 187, 198, 185, 68, 241, 173, 320 y 325; 63 del 14-oct, hasta el 21-oct: de los 66 no llegaron 3, Ithreex y Henka, dirección suprimida tras el rebote del 7-oct, y Making Sense, que rebotó; 5 de los que hicieron clic, hasta el 22-oct: AYI #175 ya respondió por teléfono) | — |
| Sin respuesta (cerrados) | 11 (tanda 1, #1–11, desde el 12-oct) | — |
| Con seguimiento vencido sin enviar | 73: 40 mutuales de Córdoba (#42–91 sin las 6 que rebotaron ni #44, 47, 67 y 72; vencía el 9-oct) y 33 partners del 8-oct (#140–178 sin MINDO #169, BIT #174 ni #154, 163, 173 y 175; vencía el 15-oct), sin texto. De los 8 que hicieron clic salieron 6 (ver "Con seguimiento enviado"); Puntonet #173 salió el 21-oct. **Propuesta (no aplicada, falta el OK del usuario):** pasar las 40 mutuales restantes a `sin respuesta`: 10 días desde el envío, sin respuesta y sin clic en el link | — |
| Rebotes | 26 direcciones en 26 contactos (export de Resend del 19-oct; lista completa en [`blacklist.md`](blacklist.md)). No llegó ningún mail en 23 (#43, 45, 49, 62, 73, 78, 79, 105, 114, 134, 139, 174, 213, 214, 226, 239, 290, 297, 322, 324, 335, 338, 340); en 3 rebotó una segunda dirección y otro mail sí llegó (#7, #10, #126). A reenviar a otra casilla publicada: 6 (#49, 62, 78, 114, 139; #126 el seguimiento), más los 11 nuevos del 19-oct si su ficha tiene otra. Descartados por email: 7 (#45, 73, 79, 134, 174, 213, 214) | — |
| Respuestas | 8 (Integrando Salud, Yoizen, Raptiv, Nybble, MINDO, Datawise, AYI Group: por teléfono el 15-oct, después del seguimiento; Zennon BI #227: atendió nuestra llamada el 19-oct, interesado); además, Inthegra (#271) escribió sin envío nuestro | — |
| Clics en el link (Google Analytics, acumulado al 21-oct) | 35 contactos (44 combinaciones de campaña y contenido, usuarios activos y eventos; al 15-oct: 25 contactos y 29 combinaciones, usuarios y sesiones). Con varios usuarios, **prioridad alta**: #119 Consultores en IT (7 y 2 con el seguimiento), #117 ARTECH (3 y 4) y #137 Brain Food (4), los tres con su seguimiento ya enviado: segundo contacto por teléfono o LinkedIn, sin mail nuevo. Clic en el seguimiento del 19-oct: #224 Accedra, #230 Silogik, #209 C&S y #205 TGV. Del GA del 21-oct entra a la tanda de seguimientos solo #241 Olpa Group (borrador); el resto ya tuvo seguimiento o está en conversación. Detalle en "Clics en el link" | — |
| No interesa | 2 (Datawise, #191: ya tienen esta solución; Integrando Salud, #99, 19-oct: siguen con su proveedor actual) | — |
| Charlas agendadas | 2 (partner de una empresa grande de salud, empresa a confirmar; Yoizen #106, con Juan Stamati, fecha a confirmar; #269 Erpwoosync: charla hecha por teléfono el 19-oct) | — |
| Conversaciones registradas | 6 (Raptiv, MINDO, gimnasio, AYI Group, Zennon BI, Erpwoosync; 2 rubros: integradores de IA y gimnasio) | 30 en 60 días, de 5 rubros o más |
| Propuestas | 0 | ~8 |
| Pilotos | 0 | 3 en 90 días |

## Contactos

Una fila por empresa. Fechas en formato `d-mes` del 2026. `—` es "todavía no".

| # | Empresa | Rubro, lugar | Tipo | Email | Web | 1.er envío | Seguimiento | Respuesta | Estado | Próxima acción |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Instituto Oulton | Diagnóstico por imágenes, Córdoba | cliente | info@oulton.com.ar | https://institutoulton.com.ar | 2-oct | 5-oct, a gustavofoa@oulton.com.ar | — | sin respuesta | — (sin respuesta desde el 12-oct) |
| 2 | Cooperativa de Electricidad Bariloche (CEB) | Cooperativa eléctrica, Río Negro | cliente | correspondencia@ceb.coop | https://www.ceb.coop | 2-oct | 5-oct, a fchueri@ceb.coop | — | sin respuesta | — (sin respuesta desde el 12-oct) |
| 3 | AMUR (Asociación Mutual Ruralista) | Mutual de salud, Santa Fe | cliente | info@amur.com.ar | https://www.amur.com.ar | 2-oct | 5-oct, a comunicaciones@amur.com.ar | — | sin respuesta | — (sin respuesta desde el 12-oct) |
| 4 | MIS – Mutual Integral de Servicios | Mutual de préstamos, Santo Tomé (Santa Fe) | cliente | contacto@mis.org.ar | https://www.mis.org.ar | 2-oct | 5-oct, a jsala@mis.org.ar | — | sin respuesta | — (sin respuesta desde el 12-oct) |
| 5 | ISEP | Colegio privado, Mendoza | cliente | informes@isep.edu.ar | https://isep.edu.ar | 2-oct | 5-oct, a admisiones.nivelprimario@isep.edu.ar | — | sin respuesta | — (sin respuesta desde el 12-oct) |
| 6 | GestarCoop | Software para cooperativas, Córdoba | canal | info@migestarcoop.com | https://migestarcoop.com | 2-oct | 5-oct, mismo hilo | — | sin respuesta | — (sin respuesta desde el 12-oct) |
| 7 | Alianza Cobros | Estudio de cobranzas, CABA | cliente | propuestas@alianzacobros.com.ar | https://alianzacobros.com.ar | 2-oct | 5-oct, a lboechi@alianzacobros.com.ar | 5-oct: rebotó lboechi@ (segundo envío; no existe la casilla). El 1.er envío a propuestas@ no rebotó | sin respuesta | — (sin respuesta desde el 12-oct; no queda otro email publicado) |
| 8 | Paktar Cobranzas & BPO | Contact center, San Miguel (Bs. As.) | canal | info@paktar.com.ar | https://www.paktar.com.ar | 2-oct | 5-oct, mismo hilo | — | sin respuesta | — (sin respuesta desde el 12-oct) |
| 9 | Yacoub | Inmobiliaria, La Plata | cliente | info@yacoub.com.ar | https://yacoub.com.ar | 2-oct | 5-oct, a administracion@yacoub.com.ar | — | sin respuesta | — (sin respuesta desde el 12-oct) |
| 10 | Grupo Silva (Silva Mobility) | Concesionaria, Tucumán | cliente | contacto@gruposilva.com.ar | https://silvamobility.com.ar | 2-oct | 5-oct, a marketing@gruposilva.com.ar | 2-oct: rebotó contacto@ (1.er envío; no existe la casilla). El del 5-oct a marketing@ no rebotó | sin respuesta | — (sin respuesta desde el 12-oct; queda consultas@gruposilva.com.ar sin usar) |
| 11 | Browix | Software de gestión de personal, Córdoba | cliente y canal | info@browix.com | https://browix.com | 2-oct | 5-oct, mismo hilo | — | sin respuesta | — (sin respuesta desde el 12-oct) |
| 12 | Cotesma | Cooperativa de telecomunicaciones, San Martín de los Andes (Neuquén) | cliente | fabian.pell@cotesma.com.ar | https://www.cotesma.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 13 | Sanatorio El Carmen | Sanatorio privado, Salta | cliente | info@sanatorioelcarmen.com.ar | https://www.sanatorioelcarmen.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 14 | Unisem | Emergencias médicas, Santa Fe | cliente | fernandobaez@unisem.com.ar | https://www.unisem.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo, texto de [`envios/2026-10-07-unisem-seguimiento.md`](envios/2026-10-07-unisem-seguimiento.md) | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 15 | Municipalidad de Trelew | Municipio, Chubut | cliente | coordintendencia@trelew.gov.ar | https://www.trelew.gov.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 16 | UCU (Universidad de Concepción del Uruguay) | Universidad privada, Entre Ríos | cliente | academica@ucu.edu.ar | https://ucu.edu.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 17 | Aulica (Netbel) | Software de gestión para colegios, Córdoba | canal | info@aulica.com.ar | https://aulica.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 18 | Fiter | Cadena de gimnasios, CABA y Gran Buenos Aires | cliente | hola@fiter.com.ar | https://fiter.com/AR | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 19 | USS | Seguridad electrónica y monitoreo, Vicente López (Bs. As.) | cliente | ekbal@uss.com.ar | https://uss.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 20 | Río Uruguay | Transporte de pasajeros y encomiendas, Posadas (Misiones) | cliente | info@riouruguaybus.com.ar | https://www.riouruguaybus.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 21 | El Norte Seguros | Compañía de seguros, San Francisco (Córdoba) | cliente | rbai@elnorte.com.ar | https://www.elnorte.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 22 | Laboratorio D'Agostino-Bruno | Laboratorio de análisis clínicos, La Plata (Bs. As.) | cliente | palonso@dagostino-bruno.com.ar | https://dagostino-bruno.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 23 | IACA Laboratorios | Laboratorio de análisis clínicos, Bahía Blanca (Bs. As.) | cliente | gugentili@iaca.com.ar | https://iaca.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 24 | SIMEPA | Prepaga regional, Santa Rosa, La Pampa | cliente | comercial@simepa.com.ar | https://simepa.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 25 | Consulmed | Odontología en red, CABA | cliente | comercial@consulmed.com.ar | https://www.consulmed.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 26 | Eoftalmo | Clínica oftalmológica, San Juan | cliente | info@eoftalmo.com | https://eoftalmo.com | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 27 | Municipalidad de Goya | Municipio, Goya, Corrientes | cliente | modernizacion@goya.gob.ar | https://www.goya.gob.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 28 | CPE (Cooperativa Popular de Electricidad de Santa Rosa) | Cooperativa eléctrica y de telecomunicaciones, Santa Rosa (La Pampa) | cliente | creditosycobranzas@cpe.com.ar | https://www.cpe.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 29 | Cooperativa 16 de Octubre (Coop16) | Cooperativa de servicios públicos, Esquel y Trevelin, Chubut | cliente | secretariacda@coop16.com.ar | https://coop16.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 30 | CELTA (Cooperativa Eléctrica de Tres Arroyos) | Cooperativa de servicios múltiples, Tres Arroyos (Bs. As.) | cliente | comercial@celta.com.ar | https://www.celtatsas.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 31 | COTEL (Cooperativa Telefónica y Otros Servicios de Villa Gesell) | Cooperativa de telecomunicaciones, Villa Gesell (Bs. As.) | cliente | comercial@cotel.com.ar | https://cotel.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 32 | Elebar (Santa Mónica S.A.) | Tarjeta de crédito regional, Tandil (Bs. As.) | cliente | pbernatene@elebar.com.ar | https://www.elebar.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct. Hipótesis, sin evidencia: Elebar es cliente de Inthegra (#271), que nos escribió el 14-oct; puede que le hayan reenviado nuestro mail |
| 33 | Empresur S.A. (Tarjeta Qida) | Financiera regional, Comodoro Rivadavia, Chubut | cliente | epini@empresurfinanzas.com.ar | https://qida.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 34 | Tarjeta Sucrédito (Valle Fértil S.A.) | Tarjeta de crédito regional, San Miguel de Tucumán, Tucumán | cliente | jorgeblanco@tarjetasucredito.com.ar | https://www.tarjetasucredito.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct. Hipótesis, sin evidencia: Sucrédito es cliente de Inthegra (#271), que nos escribió el 14-oct; puede que le hayan reenviado nuestro mail |
| 35 | Gran Cooperativa (Grancoop) | Cooperativa de crédito, CABA | cliente | gbalice@grancoop.com.ar | https://grancoop.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 36 | Derka y Vargas S.A. | Concesionario Toyota, Sáenz Peña (Chaco) | cliente | contacto@derkayvargas.com.ar | https://www.derkayvargas.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 37 | Instituto Superior Juan XXIII (Obra de Don Bosco) | Instituto terciario privado, Bahía Blanca (Bs. As.) | cliente | amandara@donbosco.org.ar | https://www.juan23.edu.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 38 | Colegio Belgrano | Colegio privado, Salta | cliente | replegal@colegiobelgrano.edu.ar | https://colegiobelgrano.edu.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 39 | NeyTI SAS | Software de gestión municipal y educativa, Sáenz Peña (Chaco) | canal | niznardo@neyti.com.ar | https://neyti.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 40 | Censys S.A. | Software para financieras, Yerba Buena (Tucumán) | canal | apaez@censys.com.ar | https://www.censys.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 41 | SISA (Sisa Latam) | Software de gestión comercial para empresas de agua, Buenos Aires | canal | guillermo.tejerina@sisa.com.ar | https://www.sisa.com.ar | 5-oct | 14-oct (vencía el 9-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 42 | Mutual MAS (empleados del Ministerio de Acción Social) | Mutual de ayuda económica, Córdoba capital (Córdoba) | cliente | jquevedo@mutualmas.org | https://www.mutualmas.org | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 43 | Mutual de Empleados del Banco de la Provincia de Córdoba (AMEBPC) | Mutual de ayuda económica, Córdoba capital (Córdoba) | cliente | administracion@mutualbpc.com.ar | https://mutualbpc.com.ar | 5-oct | — | 19-oct (export de Resend): rebotó administracion@mutualbpc.com.ar, envío del 5-oct; el mail no llegó | descartado | No mandar más mails a administracion@mutualbpc.com.ar ([`blacklist.md`](blacklist.md)). Si la ficha tiene otra casilla publicada, reenviar ahí; si no, LinkedIn o teléfono |
| 44 | Asociación Mutualista del Docente (AMD) | Mutual de ayuda económica, Córdoba capital (Córdoba) | cliente | privada@amdcba.org.ar | https://www.amdcba.org.ar | 5-oct | 14-oct 6:4x, mismo hilo, desde hola@atentina.net (según Resend; figuraba 15-oct) | — | seguimiento enviado | Si no contesta, `sin respuesta` el 22-oct |
| 45 | Mutual de Empleados de la Policía de Córdoba (AMEPPC) | Mutual de ayuda económica, Córdoba capital (Córdoba) | cliente | afiliaciones@amepcba.org | https://mutualpolicia.org.ar | 5-oct | — | 5-oct: rebotó afiliaciones@ (no existe la casilla); el mail no llegó | descartado | Sin email válido: era el único publicado. El sitio atiende por teléfono y WhatsApp por área (ficha A4 de la cuarta tanda); sin formulario ni LinkedIn anotados |
| 46 | Círculo de Suboficiales y Agentes, Mutual Policía de Córdoba | Mutual de ayuda económica, Córdoba capital (Córdoba) | cliente | prensaelcirculo@gmail.com | https://circulopoliciacba.org.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 47 | Mutual Celesol (Red Unisol) | Mutual de ayuda económica, Córdoba capital (Córdoba) | cliente | info@redunisol.com.ar | https://www.redunisol.com.ar | 5-oct | 15-oct, mismo hilo (según el usuario, ya recibió varias tandas; Resend al 20-oct solo muestra el 1.er mail) | — | seguimiento enviado | Sin más mails (ya recibió varias tandas). Si no contesta, `sin respuesta` el 22-oct |
| 48 | Asociación Mutualista Argentina Nueva (AMAN) | Mutual de ayuda económica, Córdoba capital (Córdoba) | cliente | aman@mutualaman.com | https://mutualaman.com | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 49 | Asociación Mutual Conexo | Mutual de ayuda económica, Córdoba capital (Córdoba) | cliente | info@mutualconexo.com | https://mutualconexo.com.ar | 5-oct | — | 5-oct: rebotó info@ (no existe la casilla); el mail no llegó | descartado | Descartado el 21-oct a pedido del usuario: la dirección rebotó ([`blacklist.md`](blacklist.md)); sin más mails |
| 50 | Asociación Mutual La Mediterránea | Mutual de ayuda económica, Córdoba capital (Córdoba) | cliente | hernan.garbero@lamediterranea.ar | https://lamediterranea.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 51 | Asociación Mutual Carlos Mugica | Mutual de ayuda económica, Córdoba capital (Córdoba) | cliente | mutualcarlosmugica@gmail.com | https://mutualcarlosmugica.com.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 52 | AMMA (Asociación Mutual Mercantil Argentina) | Mutual de ayuda económica, Villa María (Córdoba) | cliente | fperetti@amma.org.ar | http://new.amma.org.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 53 | Mutual Sudecor | Mutual de ayuda económica, Bell Ville (Córdoba) | cliente | oscarmargaria@mutual-sudecor.com.ar | http://mutual-sudecor.com.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 54 | AMA (Asociación Mutual Arroyito) | Mutual de ayuda económica, Arroyito (Córdoba) | cliente | info@asocmutualarroyito.com.ar | https://asocmutualarroyito.com.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 55 | Mutual COYSPU | Mutual de ayuda económica, Marcos Juárez (Córdoba) | cliente | mutual@coyspu.com.ar | https://www.mutualcoyspu.com.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 56 | Mutual Club Jorge Newbery | Mutual de ayuda económica, Ucacha (Córdoba) | cliente | newbery@ucachanet.com.ar | https://mutualnewbery.com.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 57 | Mutual VGB | Mutual de ayuda económica, Villa General Belgrano (Córdoba) | cliente | serv.asis@mutualvgb.com.ar | https://mutualvgb.com.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 58 | AMCeP (Asociación Mutual del Centro de Punilla) | Mutual de ayuda económica, Valle Hermoso (Córdoba) | cliente | mutualamcep@gmail.com | https://www.amcep.mutual.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 59 | Mutual Sportivo Belgrano | Mutual de ayuda económica, La Para (Córdoba) | cliente | comunicacion@mutualspbelgrano.com | https://www.mutualspbelgrano.com | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 60 | Asociación Mutual 22 de Septiembre | Mutual de ayuda económica, Cruz del Eje (Córdoba) | cliente | mutual.areacontable@gmail.com | https://mutual22deseptiembre.com | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 61 | Mutual Club Atlético Santa Rosa | Mutual de ayuda económica, Villa Santa Rosa (Córdoba) | cliente | contadora@mutualatletico.com.ar | https://mutualatletico.com.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 62 | Mutual 9 de Julio (Mutual de Asociados de la Asociación Deportiva 9 de Julio) | Mutual de ayuda económica, Morteros (Córdoba) | cliente | info@mutual9dejulio.com.ar | https://www.mutual9dejulio.com.ar | 5-oct | — | 5-oct: rebotó info@ (no existe la casilla); el mail no llegó | descartado | Descartado el 21-oct a pedido del usuario: la dirección rebotó ([`blacklist.md`](blacklist.md)); sin más mails |
| 63 | Mutual Almafuerte (Asociación Mutual del Club Almafuerte de Las Varillas) | Mutual de ayuda económica, Las Varillas (Córdoba) | cliente | david.protti@mutualalmafuerte.com.ar | https://mutualalmafuerte.com.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct. 21-oct: no figura ningún mail suyo en Resend (el 1.er mail no habría salido); fuera de la tanda de seguimientos, confirmar |
| 64 | Mutual Unión (A. M. de Asociados del Club Atlético Unión) | Mutual de ayuda económica, Alicia (Córdoba) | cliente | gerencia@mutualunion.com.ar | https://www.mutualunion.com.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 65 | Mutual 9 de Julio Olímpico (A. M. 9 de Julio Olímpico Freyre) | Mutual de ayuda económica, Freyre (Córdoba) | cliente | gerencia@mutual9defreyre.com.ar | https://www.mutual9defreyre.com.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 66 | Mutual Sportivo San Jorge y Centro Juvenil Milmar | Mutual de ayuda económica, Morteros (Córdoba) | cliente | mutualsanjorgemilmar@coopmorteros.com.ar | — | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 67 | Mutual TOJU | Mutual de ayuda económica, Justiniano Posse (Córdoba) | cliente | info@mutualtoju.com.ar | https://mutualtoju.com.ar | 5-oct | 14-oct 6:4x, mismo hilo, desde hola@atentina.net (según Resend; figuraba 15-oct) | — | seguimiento enviado | Si no contesta, `sin respuesta` el 22-oct. GA 21-oct: 2/14 con el 1.er mail; sin mail nuevo (ver [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md), 21-oct) |
| 68 | Asociación Mutual Bell | Mutual de ayuda económica, Bell Ville (Córdoba) | cliente | gerencia@mutualbell.com.ar | https://mutualbell.com.ar | 5-oct | 21-oct, mismo hilo, desde laureano@atentina.net (llamada de 5 minutos, sin calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md); Resend: entregado) | — | seguimiento enviado | Si no contesta, `sin respuesta` el 28-oct. 19-oct: llamada nuestra al (03537) 42-6433, no atendió (datos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) |
| 69 | Lambert Mutual (Tarjeta Monte Maíz) | Mutual (ayuda económica sin confirmar), Monte Maíz (Córdoba) | cliente | lambertm@futurnetmm.com.ar | http://tarjetamontemaiz.com.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 70 | Mutual de Asociados de Justiniano Posse | Mutual de ayuda económica, Justiniano Posse (Córdoba) | cliente | mutualdeasociados@nodosud.com.ar | — | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 71 | Mutual del Independiente Foot Ball Club (Pascanas) | Mutual de ayuda económica, Pascanas (Córdoba) | cliente | mutualindependiente@pascanasisp.com.ar | — | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 72 | Sporting Club Mutual Social, Deportivo, Cultural y Biblioteca | Mutual de ayuda económica, Corral de Bustos (Córdoba) | cliente | mutualsporting@emprenditel.com.ar | https://www.sportingclub.com.ar | 5-oct | 15-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 22-oct |
| 73 | Mutual Metropolitana | Mutual de ayuda económica, Corral de Bustos (Córdoba) | cliente | mutualmetropolitana@yahoo.com.ar | https://mutualmetropolitana.com.ar | 5-oct | — | 5-oct: rebotó (casilla de Yahoo deshabilitada); el mail no llegó | descartado | Sin email válido: formulario o WhatsApp del sitio (https://mutualmetropolitana.com.ar; número no anotado en la ficha G3-2); sin LinkedIn anotado |
| 74 | Mutual de Asociados del Club Atlético San Carlos | Mutual de ayuda económica, Los Surgentes (Córdoba) | cliente | administracion@mutualsancarlos.com.ar | https://mutualsancarlos.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 75 | Club Atlético Social Corralense A. M. | Mutual de ayuda económica, Corral de Bustos (Córdoba) | cliente | ezequiel@corralense.com.ar | http://corralense.com.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 76 | Mutual de Asociados del Club Atlético San Martín (Monte Buey) | Mutual (ayuda económica sin confirmar), Monte Buey (Córdoba) | cliente | mariaelenacingolani@gmail.com | — | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 77 | Mutual de las Comunidades | Mutual de ayuda económica, General Deheza (Córdoba) | cliente | mantuna@mcomunidades.com.ar | https://mutualdelascomunidades.com.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 78 | Mutual Soberanía | Mutual de ayuda económica, Río Cuarto (Córdoba) | cliente | contacto@mutualsoberania.com.ar | https://mutualsoberania.com.ar | 5-oct | — | 5-oct: rebotó contacto@ (no existe la casilla); el mail no llegó | descartado | Descartado el 21-oct a pedido del usuario: la dirección rebotó ([`blacklist.md`](blacklist.md)); sin más mails |
| 79 | Mutual de Asociados del Club Atlético Atenas | Mutual de ayuda económica, Ucacha (Córdoba) | cliente | ca-atenas@hotmail.com | — | 5-oct | — | 5-oct: rebotó (casilla de Hotmail no disponible, 550 5.5.0: deshabilitada o inexistente); el mail no llegó | descartado | Sin email válido: no tiene sitio, formulario ni LinkedIn en la ficha G4-3 (solo padrón INAES y notas de FEMUCOR) |
| 80 | Mutual del Personal Civil Taller Regional Río Cuarto | Mutual de ayuda económica, Río Cuarto (Córdoba) | cliente | mutualpctr@hotmail.com.ar | https://www.mutualpersonalcivil.org | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 81 | Sociedad Italiana de Socorros Mutuos Puerta Pía | Mutual (ayuda económica sin confirmar), Río Cuarto (Córdoba) | cliente | sociedaditalianariocuarto@gmail.com | — | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 82 | Mutual Oncativo (A. M. Oncativo de Socios y Adherentes del Club Deportivo y Cultural Unión) | Mutual (ayuda económica sin confirmar), Oncativo (Córdoba) | cliente | mutualoncativo@gmail.com | — | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 83 | Asociación Mutual Médica de Villa María (SOS Salud) | Mutual (ayuda económica sin confirmar), Villa María (Córdoba) | cliente | comunicacion@sossalud.com.ar | https://sossalud.com.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 84 | Sociedad Italiana de Socorros Mutuos "Italia Unida" | Mutual (ayuda económica sin confirmar), Villa María (Córdoba) | cliente | redin001@hotmail.com | — (sociedaditalianavillamaria.com bloquea robots) | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 85 | AMISVIMA (Asociación Mutual Integración Solidaria Villa María) | Mutual (ayuda económica sin confirmar), Villa María (Córdoba) | cliente | jorge_sienra@yahoo.com.ar | — | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 86 | Sociedad Italiana de Socorros Mutuos Social, Cultural y Deportiva "Roma" | Mutual (ayuda económica sin confirmar), Villa del Rosario (Córdoba) | cliente | sociedaditalianavdr@hotmail.com | — | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 87 | AMCeCIS (Asociación Mutual del Centro Comercial, Industrial y de Servicios de Río Tercero) | Mutual de ayuda económica, Río Tercero (Córdoba) | cliente | prensa@amcecis.mutual.ar | https://amcecis.mutual.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 88 | AMECOL (Asociación Mutualista de Empleados de Comercio de Laboulaye) | Mutual (ayuda económica sin confirmar), Laboulaye (Córdoba) | cliente | admamecol@gmail.com | — | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 89 | Asociación Mutual Empleados Municipales de Río Tercero y Zona | Mutual (ayuda económica sin confirmar), Río Tercero (Córdoba) | cliente | suoem_rio3@yahoo.com.ar | — | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 90 | Asociación Mutual del Centro Comercial de Hernando | Mutual (ayuda económica sin confirmar), Hernando (Córdoba) | cliente | dgastaudo@coop-her.com.ar | — | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 91 | Asociación Mutual del Centro Comercial e Industrial de Tancacha | Mutual (ayuda económica sin confirmar), Tancacha (Córdoba) | cliente | mutual@ccitancacha.com.ar | https://www.ccitancacha.com.ar | 5-oct | — | — | enviado | Seguimiento el 9-oct |
| 92 | Neo Consultores S.A. | Software para mutuales y cooperativas, Rosario | canal | info@gruponeosistemas.com | https://neoconsultores.ar | — | — | — | borrador | Mensaje por LinkedIn el 6-oct (L2); el mail no salió |
| 93 | Nexa Tech | Software para mutuales y cooperativas, Pergamino | canal | info@nexa.com.ar | https://nexa.com.ar | — | — | — | borrador | Mensaje por LinkedIn el 6-oct (L3); el mail no salió |
| 94 | EVOL SRL | Software para mutuales y cooperativas, provincia de Buenos Aires | canal | ventas@evol.com.ar | https://evol.com.ar | — | — | — | borrador | Mensaje por LinkedIn el 6-oct (L4); el mail no salió. GA 21-oct: 3/12 con `canales1/evol`: sigue sin confirmar si el mail salió; sin hilo, no va seguimiento por mail (ver [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md), 21-oct) |
| 95 | Solsoft SRL | Software para mutuales y cooperativas, San Francisco | canal | solsoft@solsoft.com.ar | https://www.solsoft.com.ar | — | — | — | borrador | Mensaje por LinkedIn el 6-oct (L5); el mail no salió |
| 96 | Kernel Informática | Software para mutuales y cooperativas, Rosario | canal | sistemas@kernelinformatica.com.ar | https://www.kernelinformatica.com.ar | 6-oct | 14-oct (vencía el 13-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 97 | RAS (Rent A Soft S.A.) | Software para salud, Godoy Cruz | canal | info@plataforma-ras.com | https://plataforma-ras.com | — | — | — | borrador | Mensaje por LinkedIn el 6-oct (L6); el mail no salió |
| 98 | Grupo Cormos (DrApp) | Software para salud, CABA | canal | hola@cormos.com.ar | https://www.cormos.com.ar | — | — | — | borrador | Mensaje por LinkedIn el 6-oct (L7); el mail no salió |
| 99 | Integrando Salud | Software para salud, Leandro N. Alem | canal | partners@integrandosalud.com | https://integrandosalud.com | — | — | 7-oct (LinkedIn, L8): derivan a Jaqueline Gutiérrez, encargada de partnership. 19-oct (informado por el usuario): van a continuar con su proveedor actual (cuál, a confirmar) | no interesa | — (no insistir; ver [`blacklist.md`](blacklist.md), "No contactar") |
| 100 | Alephoo | Software para salud, Campana | canal | info@alephoo.com | https://www.alephoo.com | — | — | — | borrador | Mensaje por LinkedIn el 6-oct (L9); el mail no salió |
| 101 | Tekhne S.A. | Software para salud, CABA y San Fernando del Valle de Catamarca | canal | contacto@tekhne.com.ar | https://www.tekhne.com.ar | 6-oct | 14-oct (vencía el 13-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 102 | Engage SC (Soluciones Tecnológicas S.A.) | Software de contact center, CRM y cobranzas, CABA | canal | agurmandi@soluciones-ar.com.ar | https://engage-sc.com.ar | 6-oct | 14-oct (vencía el 13-oct), mismo hilo, con CC a anibalc@soluciones-ar.com.ar | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 103 | Teleprom (Teleprom Argentina S.A.) | Software de contact center, CRM y cobranzas, Córdoba capital | canal | ventas@teleprom.com | https://teleprom.com | 6-oct | 14-oct (vencía el 13-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 104 | Freetech Solutions (Telecomunicaciones Unificadas SRL), OMniLeads | Software de contact center, CRM y cobranzas, Córdoba capital | canal | info@freetechsolutions.com.ar | https://www.freetechsolutions.com.ar | 6-oct | 14-oct (vencía el 13-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct. GA 21-oct: 1/4; sin mail nuevo (ver [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md), 21-oct) |
| 105 | TecnoVoz (Tecno Voz Noroeste S.A.) | Software de contact center, CRM y cobranzas, CABA | canal | info@tecnovoz.com | https://tecnovoz.com.ar | 6-oct | 14-oct (vencía el 13-oct), mismo hilo | 19-oct (export de Resend): rebotó info@tecnovoz.com, envío del 6-oct y el seguimiento del 14-oct; el mail no llegó | descartado | No mandar más mails a info@tecnovoz.com ([`blacklist.md`](blacklist.md)). Si la ficha tiene otra casilla publicada, reenviar ahí; si no, LinkedIn o teléfono |
| 106 | Yoizen (Yoizen S.A.) | Plataforma omnicanal de atención (WhatsApp BSP, Meta Business Partner) y agentes de IA, CABA | canal | ventas@yoizen.com | https://yoizen.com | 6-oct | 19-oct, a Nicolás y Juan Stamati en el hilo de la presentación | 7-oct (LinkedIn): pasan el contacto al equipo de producto. 14 o 15-oct (email; fecha exacta a confirmar): Nicolás (probablemente Nicolás Podrojsky, CEO; a confirmar) presenta a Juan Stamati, responsable de alianzas (email a confirmar: va en copia en ese hilo), "para que puedan tener una conversación". 19-oct: follow-up nuestro a Nicolás y Juan en ese hilo, propone una llamada de 5 min para que evalúen ahí si sigue con una demo. 19-oct: reunión con Juan Stamati agendada (fecha a confirmar). Es Juan Pablo Stamati: Product Owner en el blog de Yoizen (9-feb-2026) y "Strategic Alliances Sales Manager" en LinkedIn; en 2024 figuraba en Avaya | charla agendada | Hacer la reunión (preparada el 19-oct: hipótesis, proveedor de voz para su suite, por SIP de WhatsApp Calling o telefonía y por API) y cargarla en "Conversaciones". Ojo, posible competidor: venden agentes de IA en WhatsApp y su LinkedIn usa #VoiceBots |
| 107 | Chatsell | Integrador o agencia de automatización e IA, Córdoba capital | canal | comercial@chatsell.net | https://chatsell.net | 6-oct | 14-oct (vencía el 13-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct. GA 21-oct: 1/8; sin mail nuevo (ver [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md), 21-oct) |
| 108 | Origami Software | Integrador o agencia de automatización e IA, Mendoza | canal | info@origami-soft.com | https://www.origami-soft.com | 6-oct | 14-oct (vencía el 13-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 109 | Raptiv | Integrador o agencia de automatización e IA, Nordelta | canal | hola@raptiv.io | https://raptiv.io | 6-oct | — | 7-oct: responde Federico Vara (director, fvara@raptiv.io, +54 11 6481-1776, linkedin.com/in/fedevara), interesado en usarlo en sus apps; propone reunión. 9-oct (informado): charla hecha, positiva (fecha exacta a confirmar); demo enviada a Raptiv o a MINDO (a confirmar a cuál) | charla hecha | Confirmar con el usuario si la demo fue a Raptiv o a MINDO, y el próximo paso acordado (ver "Conversaciones") |
| 110 | Etixen | Integrador o agencia de automatización e IA, Buenos Aires | canal | gparadelo@etixen.com | https://etixen.com | 6-oct | 14-oct (vencía el 13-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 111 | StorySelling | Integrador o agencia de automatización e IA, Buenos Aires | canal | contacto@storyselling.la | https://www.storyselling.la | 6-oct | 14-oct (vencía el 13-oct), mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct |
| 112 | Kunan | Consultora tecnológica, Córdoba capital | canal | daniel.ibanez@kunan.com.ar | https://kunan.com.ar | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S1 de la tanda); WhatsApp publicado: +54 351 276-4175 (pendiente, ver S1 de la tanda) |
| 113 | Aionixs | Agencia de IA, Buenos Aires | canal | fabrizio@aionixs.com | https://www.aionixs.com | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S2 de la tanda) |
| 114 | Ithreex Global | IA as a Service, Córdoba capital | canal | dyvanoff@ithreexglobal.com | https://ithreexglobal.com | 7-oct | 14-oct, mismo hilo, a la dirección que rebotó (probablemente no salió: Resend suprime la dirección) | 7-oct: rebotó dyvanoff@ (503 No routes found, sin ruta MX al enviar; el 15-oct el dominio tiene MX de Google y de Maileroo mezclados: puede ser configuración del destinatario); no llegó ningún mail | descartado | Descartado el 21-oct a pedido del usuario: la dirección rebotó ([`blacklist.md`](blacklist.md)); sin más mails |
| 115 | Crombie | Software a medida e IA para fintech y retail, Santa Fe capital | canal | mariano.dimaggio@crombie.dev | https://crombie.dev | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S4 de la tanda); WhatsApp publicado: +54 9 342 412-1195 (pendiente, ver S4 de la tanda) |
| 116 | NeuralSoft | ERP en la nube (MyLogic) con IA, CRM, BPM, Rosario | canal | german.viceconti@neuralsoft.com | https://www.neuralsoft.com | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S5 de la tanda); WhatsApp publicado: +54 9 11 5884-6241 (pendiente, ver S5 de la tanda) |
| 117 | ARTECH | Consultora, CABA | canal | sgalera@artech-consulting.com | https://www.artech-consulting.com.ar | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | **Prioridad alta** (4 usuarios con el primer mail y 4 con el seguimiento, ver "Clics en el link"): segundo contacto a Santiago Galera, CEO (★ de la ficha), por LinkedIn (https://www.linkedin.com/in/galera/; nota y mensaje en S6 de la tanda) o por teléfono (+54 11 5353-2253, del sitio) proponiendo una llamada, sin mencionar el clic. Si no contesta, `sin respuesta` el 21-oct. GA 21-oct: 3/15 con el 1.er mail y 4/22 con el seguimiento: sigue en prioridad alta; sin mail nuevo, llamar o LinkedIn (ver [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md), 21-oct) |
| 118 | AGOS | Software factory y servicios IT, CABA | canal | michnowicz@agos.global | https://agos.global | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S7 de la tanda) |
| 119 | Consultores en IT S.A. | RPA + IA para procesos administrativos, infraestructura y ciberseguridad, Rosario | canal | diegor@consultoresenit.com.ar | https://www.consultoresenit.com.ar | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | **Prioridad alta** (7 usuarios con el primer mail y 2 con el seguimiento, ver "Clics en el link"): segundo contacto a Diego Ríos (★ de la ficha) por LinkedIn (https://www.linkedin.com/in/diego-rios-23a98215/; nota y mensaje en S8 de la tanda) o por teléfono (+54 341 527-8964, del sitio) proponiendo una llamada, sin mencionar el clic. WhatsApp publicado: +54 9 341 280-1694. Si no contesta, `sin respuesta` el 21-oct. GA 21-oct: 7 usuarios/35 eventos con el 1.er mail y 2/10 con el seguimiento: sigue en prioridad alta; sin mail nuevo (ya tuvo su seguimiento), llamar o LinkedIn (ver [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md), 21-oct) |
| 120 | Cumbresoft | GovTech, Mendoza capital | canal | tomaseliseo@cumbresoft.com | https://cumbresoft.com | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S9 de la tanda) |
| 121 | Dicsys | Consultora de datos e IA, Córdoba capital | canal | augusto.widmer@dicsys.com | https://www.dicsys.ai | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S10 de la tanda) |
| 122 | Ecosistemas Global | Servicios IT, CABA | canal | vorciuoli@ecosistemas.com.ar | https://ecosistemasglobal.com | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S11 de la tanda); WhatsApp publicado: +54 11 2180-8261 (pendiente, ver S11 de la tanda) |
| 123 | Exomindset | IA y datos, La Calera | canal | marcelo.franceschini@exomindset.co | https://exomindset.com | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S12 de la tanda) |
| 124 | JEMER | Software a medida, integración y automatización para fintech, servicios públicos, retail y clubes, Córdoba capital | canal | agustin@jemersoft.com | https://jemer.co | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S13 de la tanda) |
| 125 | KINETIC Corp | Consultora de IA, Córdoba capital | canal | rodrigo.porta@kinetic-corp.com | https://kinetic-corp.com | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S14 de la tanda) |
| 126 | Making Sense | Desarrollo de software, IA, UX, modernización y automatización de procesos, Mar del Plata | canal | mlaguna@makingsense.com | https://makingsense.com | 7-oct | 14-oct, mismo hilo (rebotó) | 14-oct: rebotó el seguimiento a mlaguna@ (no existe la casilla); el 1.er envío del 7-oct no figura como rebote | descartado | Descartado el 21-oct a pedido del usuario: la dirección rebotó ([`blacklist.md`](blacklist.md)); sin más mails |
| 127 | Holon Software | GovTech, Villa María | canal | marcelo.paris@holon.com.ar | http://www.holon.com.ar | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S16 de la tanda) |
| 128 | Widergy | Plataforma omnicanal con agentes de IA para utilities (luz, gas, agua), CABA | canal | sales@widergy.com | https://widergy.com | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S17 de la tanda). GA 21-oct: 3/16; sin mail nuevo (LinkedIn) (ver [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md), 21-oct) |
| 129 | Devlights | Software factory, Corrientes capital | canal | contact@devlights.com | https://devlights.com | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S18 de la tanda) |
| 130 | Nybble Group | Transformación digital, CABA | canal | sales@nybblegroup.com | https://www.nybblegroup.com | 7-oct | — | 9-oct (informado; fecha exacta a confirmar): Facundo Galán (cargo y email a confirmar) responde por email con interés | respondió | Seguimiento a Facundo Galán en el mismo hilo (fecha a definir); reemplaza el seguimiento del 14-oct a sales@ |
| 131 | Infolytics | IA y analítica, CABA | canal | info@infolytics.ai | https://infolytics.ai | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S20 de la tanda); WhatsApp publicado: +54 9 11 8031-0366 (pendiente, ver S20 de la tanda). GA 21-oct: 3/17 y 1/4 con el seguimiento; sin mail nuevo (WhatsApp o LinkedIn) (ver [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md), 21-oct) |
| 132 | GMO Solutions | Consultora tecnológica, San Juan capital | canal | info@gmosolutions.com.ar | https://gmosolutions.com.ar | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S21 de la tanda); WhatsApp publicado: +1 914 336-4117 (EE. UU.) (pendiente, ver S21 de la tanda) |
| 133 | Quanam | Consultora de transformación digital, Montevideo (Uruguay) | canal | quanam@quanam.com | https://quanam.com | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S22 de la tanda). GA 21-oct: 3/16 y 1/5 con el seguimiento; sin mail nuevo (LinkedIn) (ver [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md), 21-oct) |
| 134 | Henka (Digital Henka) | Consultora de innovación ágil, sin ciudad publicada (Uruguay) | canal | hello@digitalhenka.com | https://henka.ai | 7-oct | 14-oct, mismo hilo, a la dirección que rebotó (probablemente no salió: Resend suprime la dirección) | 7-oct: rebotó hello@ (no existe la casilla); no llegó ningún mail | descartado | Sin email válido: LinkedIn (S23: empresa y personas enlazadas en /sobre-nosotros) o formulario https://henka.ai/contact; WhatsApp publicado +598 93 880 344 (ver S23) |
| 135 | Accuratio | Servicios IT, Montevideo, Buenos Aires y Santiago (Uruguay y Argentina) | canal | contactuy@accuratio.global | https://accuratio.global | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S24 de la tanda); WhatsApp publicado: +54 9 11 2274-7080 (pendiente, ver S24 de la tanda) |
| 136 | FutureFlow | Consultora de IA y automatización, Providencia, Santiago (Chile) | canal | hola@futureflow.cl | https://futureflow.cl | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S25 de la tanda); WhatsApp publicado: +56 9 2196 9200 (pendiente, ver S25 de la tanda) |
| 137 | Brain Food | Consultora de ciencia de datos, Las Condes, Santiago (Chile) | canal | contacto@brainfood.cl | https://brainfood.cl | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | **Prioridad alta** (4 usuarios, ver "Clics en el link"): segundo contacto proponiendo una llamada, sin mencionar el clic; la ficha no tiene persona con nombre: por LinkedIn a la empresa (https://cl.linkedin.com/company/brain-food-spa; nota y mensaje en S26 de la tanda) o por teléfono (+56 9 5169 5577, del sitio, Chile). Si no contesta, `sin respuesta` el 21-oct. GA 21-oct: 4/18: sigue en prioridad alta; sin mail nuevo, llamar o LinkedIn (ver [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md), 21-oct) |
| 138 | Sinnetic | Investigación de mercados, analítica de datos y consultoría en data science e IA, Bogotá (Colombia) | canal | contacto@sinnetic.com | https://www.sinnetic.com | 7-oct | 14-oct, mismo hilo | — | seguimiento enviado | Si no contesta, `sin respuesta` el 21-oct; LinkedIn pendiente (nota y mensaje en S27 de la tanda); WhatsApp publicado: +57 318 024 2831 (pendiente, ver S27 de la tanda) |
| 139 | Biwares | Consultora de negocio y tecnología, CABA | canal | drivero@biwares.com | https://www.biwares.com | 8-oct | — | 8-oct: rebotó drivero@ (no existe la casilla); el mail no llegó | descartado | Descartado el 21-oct a pedido del usuario: la dirección rebotó ([`blacklist.md`](blacklist.md)); sin más mails |
| 140 | Duotach | Consultora de software y automatización con IA, CABA | canal | contact@duotach.com | https://duotach.com | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S2 de la tanda 2); WhatsApp publicado: +54 9 11 2516-1395 (pendiente, ver S2 de la tanda 2) |
| 141 | Quilsoft | Partner Silver de Odoo, CABA | canal | info@quilsoft.com | https://www.quilsoft.com | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S3 de la tanda 2); WhatsApp publicado: +54 9 11 7078-0612 (pendiente, ver S3 de la tanda 2) |
| 142 | BamAI | Consultora de automatización con IA para pymes, CABA | canal | contacto@bamai.ar | https://bamai.ar | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S4 de la tanda 2); WhatsApp publicado: +54 9 11 2277-7497 (pendiente, ver S4 de la tanda 2) |
| 143 | AIViento | Consultoría de IA para empresas, CABA | canal | contacto@aiviento.com | https://www.aiviento.com | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S5 de la tanda 2); WhatsApp publicado: +54 9 11 2555-4381 (pendiente, ver S5 de la tanda 2) |
| 144 | Bombieri | Consultora de transformación digital, CABA | canal | ventas@bombieri.com.ar | https://www.bombieri.com.ar | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S6 de la tanda 2); WhatsApp publicado: +54 9 11 3134-6000 y +54 9 344 268-4457 (pendiente, ver S6 de la tanda 2) |
| 145 | booleAr S.A. | Servicios, SaaS, IA, automatización y modernización de sistemas críticos (finanzas, salud, agro), CABA | canal | info@boolear.com | https://www.boolear.com | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S7 de la tanda 2) |
| 146 | Grupo Esfera | Desarrollo de software y agilidad organizacional potenciados por IA, CABA | canal | comercial@grupoesfera.com.ar | https://www.grupoesfera.com.ar | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S8 de la tanda 2) |
| 147 | Eryx | Cooperativa de trabajo y software factory, CABA | canal | info@eryx.co | https://eryx.co | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S9 de la tanda 2) |
| 148 | 7Puentes | Consultora de machine learning e IA, Buenos Aires | canal | info@7puentes.com | https://7puentes.com | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S10 de la tanda 2) |
| 149 | Accion Point | Software a medida y core bancario (Bantotal) con agentes de IA, CABA | canal | marketing@accionpoint.com | https://accionpoint.com | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S11 de la tanda 2); WhatsApp publicado: +54 9 11 3831-4111 (pendiente, ver S11 de la tanda 2) |
| 150 | Medve | Software factory, CABA | canal | info@medve.com.ar | https://www.medve.com.ar | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S12 de la tanda 2); WhatsApp publicado: +54 9 11 6637-6176 (pendiente, ver S12 de la tanda 2) |
| 151 | Unitech | GovTech, CABA | canal | comercial@unitech-corp.com | https://www.unitech.com.ar | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S13 de la tanda 2) |
| 152 | Xelere | Ciberseguridad y gestión de servicios de TI (ITSM) con IA, CABA | canal | info@xelere.com | https://www.xelere.com | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S14 de la tanda 2); WhatsApp publicado: +54 9 11 2306-3378 (pendiente, ver S14 de la tanda 2) |
| 153 | QActions | QA, RPA e IA para calidad de software, Buenos Aires | canal | info@qactions.com | https://qactions.com | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S15 de la tanda 2); WhatsApp publicado: +54 9 11 6423-5643 (pendiente, ver S15 de la tanda 2) |
| 154 | Mooving (Mooving Tech S.A.U.) | Consultoría estratégica, IA empresarial (Senda, agentes cognitivos) y arquitectura de datos para retail y utilities, CABA | canal | hola@moovingtech.com | https://mooving.ai | 8-oct | 14-oct 6:4x, mismo hilo, desde hola@atentina.net (según Resend; figuraba 15-oct) | — | seguimiento enviado | Si no contesta, `sin respuesta` el 22-oct; LinkedIn pendiente (nota y mensaje en S16 de la tanda 2); WhatsApp publicado: +54 9 11 5136-1574 (pendiente, ver S16 de la tanda 2). GA 21-oct: 3/15; sin mail nuevo (WhatsApp o LinkedIn) (ver [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md), 21-oct) |
| 155 | OneInfo Consulting | Consultora de CX, CRM e IA, CABA | canal | info@oneinfoconsulting.com | https://www.oneinfoconsulting.com | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S17 de la tanda 2) |
| 156 | Kopernicus | Consultoría IT y arquitectura tecnológica para aseguradoras, San Isidro | canal | ramos.gaston@kopernicus.tech | https://www.kopernicus.com.ar | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S18 de la tanda 2) |
| 157 | Innen | Estudio de software, automatización e IA 'con foco humano', Buenos Aires | canal | team@innen.io | https://innen.io | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S19 de la tanda 2) |
| 158 | Zarego | Desarrollo de software a medida e ingeniería de IA (nearshore para EE. UU.), CABA | canal | hello@zarego.com | https://zarego.com | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S20 de la tanda 2) |
| 159 | 404 // Software crafters | Estudio de software, Buenos Aires | canal | info@proyecto404.com | https://proyecto404.com | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S21) |
| 160 | Grupo Kelsoft | Servicios y consultoría de IT + IA, CABA | canal | negocios@grupokelsoft.com | https://grupokelsoft.com | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S22). 21-oct: no figura ningún mail suyo en Resend (el 1.er mail no habría salido); fuera de la tanda de seguimientos, confirmar |
| 161 | Infogestión | Consultoría digital para pymes, La Plata | canal | info@infogestion.com.ar | https://infogestion.com.ar | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S23) |
| 162 | Julasoft | Software a medida, IA y machine learning, automatización inteligente para empresas y organismos, La Plata | canal | info@julasoft.com | https://www.julasoft.com | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S24); WhatsApp publicado: +54 9 221 570-6102 (pendiente, ver S24 de la tanda 2) |
| 163 | Tecnom | CRM automotriz con IA (Tecna) para concesionarios, La Plata | canal | ventas@tecnom.com.ar | https://www.tecnom.com.ar | 8-oct | 14-oct 6:4x, mismo hilo, desde hola@atentina.net (según Resend; figuraba 15-oct) | — | seguimiento enviado | Si no contesta, `sin respuesta` el 22-oct; LinkedIn pendiente (nota y mensaje en S25); WhatsApp publicado: +54 9 2241 52-7982 (pendiente, ver S25 de la tanda 2). GA 21-oct: 2/9; sin mail nuevo (WhatsApp o LinkedIn) (ver [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md), 21-oct) |
| 164 | Quales Group | Consultora de datos e IA, CABA | canal | info@qualesgroup.com | https://www.qualesgroup.com | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S26) |
| 165 | Snoop Consulting | Servicios de software y transformación digital con IA, La Plata | canal | atencion@snoop.ar | https://www.snoopconsulting.com | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S27); WhatsApp publicado: +54 9 11 6997-1830 (pendiente, ver S27 de la tanda 2) |
| 166 | BlueDraft | Consultora de analítica de datos, modelos financieros e IA, La Plata | canal | hello@bluedraft.com.ar | https://www.bluedraft.com.ar | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S28) |
| 167 | Avalith | Software 'human-led, AI-accelerated', Mar del Plata | canal | hello@avalith.net | https://avalith.net | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S29) |
| 168 | Aoki Tech | Agentes de IA, ERP y gestión para pymes, Mar del Plata | canal | sofia@aokitech.com.ar | https://aokitech.com.ar | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S30) |
| 169 | MINDO | Agentes de IA para e-commerce en WhatsApp e Instagram, Mar del Plata | canal | contacto@mindosoftware.com | https://mindosoftware.com | 8-oct | — | 9-oct (informado): charla hecha, positiva (persona y fecha exacta a confirmar); pyme integradora; demo enviada a Raptiv o a MINDO (a confirmar a cuál) | charla hecha | Confirmar con el usuario con quién fue la charla, si la demo fue a MINDO o a Raptiv, y el próximo paso; ya no va el seguimiento del 15-oct |
| 170 | NexoSmart | Software factory y company builder, Bahía Blanca | canal | maximo@sales.nexosmart.com.ar | https://www.nexosmart.com.ar | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S32); WhatsApp publicado: +54 9 291 507-8136 (pendiente, ver S32 de la tanda 2) |
| 171 | VGS | Desarrollo de software, ERP propio y 'AI con VGS Labs', Bahía Blanca | canal | info@vgs.com.ar | https://vgs.com.ar | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S33) |
| 172 | Vortex | Consultora de plataformas digitales AI-First, Córdoba capital | canal | jorge.nieves@vortex-it.com | https://vortex-it.com | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S34); WhatsApp publicado: +54 9 351 510-4734 (pendiente, ver S34 de la tanda 2) |
| 173 | Puntonet Tech (Punto Net Soluciones SRL) | Consultora tecnológica, Villa Carlos Paz | canal | edutra@puntonet.tech | https://www.puntonet.tech | 8-oct | 21-oct, mismo hilo, desde laureano@atentina.net (llamada de 5 minutos, sin calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md); Resend: entregado) | — | seguimiento enviado | Si no contesta, `sin respuesta` el 28-oct; LinkedIn pendiente (nota y mensaje en S35). GA 21-oct: 2/13; sin mail nuevo (LinkedIn) (ver [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md), 21-oct) |
| 174 | BIT S.A. | Software y agentes de IA para agro, logística y empresas (Agrobit, SAP Agro, Admis ERP), Villa María | canal | bit@bit.com.ar | https://www.bit.com.ar | 8-oct | — | 8-oct: rebotó bit@ (550 5.4.1 Access denied, Exchange Online: puede ser configuración del destinatario, no necesariamente casilla inexistente); el mail no llegó | descartado | Sin email válido: formulario https://www.bit.com.ar/contacto.html o LinkedIn (nota y mensaje en S36); el seguimiento del 15-oct no aplica |
| 175 | AYI Group (BADI S.A.) | Servicios IT, Córdoba capital | canal | hi@ayi.group | https://ayi.group | 8-oct | 14-oct 6:4x, mismo hilo, desde hola@atentina.net (según Resend; figuraba 15-oct) | 15-oct: charla telefónica con Luciano Fuccia (cargo a confirmar; luciano.fuccia@ayi.group, lo dio en la charla). Llamó tres veces al 0800 de Atentina (13, 14 y 15-oct) y cortó cuando el agente le preguntó la empresa; Laureano lo llamó. Positiva: van a evaluar el producto como reemplazo de Twilio (voz y telefonía por API para lo que construyen) | charla hecha | Follow-up el mié 21-oct a luciano.fuccia@ayi.group ★ (mismo hilo), borrador en [`envios/2026-10-21-ayi-seguimiento.md`](envios/2026-10-21-ayi-seguimiento.md). Ya no aplica `sin respuesta` el 22-oct ni la prioridad por clics. Detalle en "Conversaciones" |
| 176 | Peperina Software | Modernización de sistemas críticos con agentes de IA (GovTech y empresas), Córdoba capital | canal | sergio.maurenzi@peperina.io | https://peperina.io | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S38) |
| 177 | Skater Elephant (Resolution 8 Software SAS) | Consultora de IA, Córdoba capital | canal | hello@skaterelephant.com | https://skaterelephant.com/es | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S39) |
| 178 | Digital Motus | Software a medida, nube y DevOps, Río Ceballos | canal | ignacio.lozita@digitalmotus.io | https://www.digitalmotus.io/es | 8-oct | — | — | enviado | Seguimiento el 15-oct (el 12 es feriado); LinkedIn pendiente (nota y mensaje en S40); WhatsApp publicado: +54 9 351 591-4862 (pendiente, ver S40 de la tanda 2) |
| 179 | Vippinn | Partner Gold de Odoo y servicios SAP, software a medida e IA en procesos de negocio, Córdoba capital | canal | dcarrizo@vippinn.com | https://www.vippinn.com | 14-oct | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S41); WhatsApp publicado: +54 9 351 809-4455 (pendiente, ver S41 de la tanda 2) |
| 180 | Ascentio Technologies | Ingeniería de sistemas, Córdoba capital | canal | manderson@ascentio.com.ar | https://www.ascentio.com.ar | 14-oct | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S42) |
| 181 | HMM Global (Home Medical Management) | Software vertical, Córdoba capital | canal | dgerosa@hmmglobal.com | https://hmmglobal.com | 14-oct | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S43) |
| 182 | Asofix (Grupo Tagle) | Software vertical SaaS con IA para la gestión comercial de concesionarios, fabricantes y agencias de usados, Córdoba capital | canal | pablo.leoni@grupotagle.com.ar | https://www.asofix.com | 14-oct | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S44); WhatsApp publicado: +54 351 345-5100 (pendiente, ver S44 de la tanda 2) |
| 183 | Syloper | Software factory, Rosario | canal | agustin@syloper.com | https://www.syloper.com | 14-oct | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S45) |
| 184 | Santa Fe Sistemas (Grupo SFS) | Software vertical de salud, Santa Fe capital | canal | comercial@sfs.com.ar | https://www.sfs.com.ar | 14-oct | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S46); WhatsApp publicado: +54 9 342 479-0990 (pendiente, ver S46 de la tanda 2) |
| 185 | EximIA Solutions (Technology Service SAS) | Automatización con RPA, agentes de IA y machine learning para bancos, utilities, salud y retail, Rosario | canal | info@eximia.ar | https://eximia.ar | 14-oct | 21-oct, mismo hilo, desde laureano@atentina.net (llamada de 5 minutos, sin calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md); Resend: entregado) | — | seguimiento enviado | Si no contesta, `sin respuesta` el 28-oct; LinkedIn pendiente (nota y mensaje en S47). 19-oct: llamada nuestra al +54 9 3417 20-3719, no atendió (datos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) |
| 186 | Human Tech 4.0 (Business Buggers SRL) | Consultoría tecnológica, talento y capacitación para industria 4.0, con IA aplicada y consorcios de innovación, Rosario | canal | pablo.crembil@humantech40.com.ar | https://www.humantech40.com.ar | 14-oct | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S48); WhatsApp publicado: +54 9 11 5853-3333 (pendiente, ver S48 de la tanda 2) |
| 187 | Autologica | Software vertical, Rosario | canal | info@autologica.com | https://www.autologica.com/es | 14-oct, asunto «Consulta» (prueba) | 21-oct, mismo hilo, desde laureano@atentina.net (llamada de 5 minutos, sin calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md); Resend: entregado) | — | seguimiento enviado | Si no contesta, `sin respuesta` el 28-oct; LinkedIn pendiente (nota y mensaje en S49). 19-oct: llamada nuestra al +54 9 3416 92-0050, no atendió (datos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) |
| 188 | Kodear | Desarrollo de soluciones digitales a medida, automatización y e-commerce, Rosario | canal | dgiovanon@kodear.net | https://kodear.dev | 14-oct, asunto «Consulta» (prueba) | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S50); WhatsApp publicado: +54 9 11 7143-9021 (pendiente, ver S50 de la tanda 2) |
| 189 | Efficast | Plataforma industrial IoT con agentes de IA (monitoreo de planta, reportes, supervisor de IA en WhatsApp), Rosario | canal | simon@efficast.ai | https://efficast.ai | 14-oct, asunto «Consulta» (prueba) | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S51); WhatsApp publicado: +54 9 341 655-5097 (pendiente, ver S51 de la tanda 2) |
| 190 | Nonlinear Tecnología | Optimización de cadenas de suministro, logística de última milla y analítica predictiva, Santa Fe capital | canal | contacto@nonlinear.com.ar | https://nonlinear.com.ar | 14-oct, asunto «Consulta» (prueba) | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S52); WhatsApp publicado: +54 9 342 487-6180 (pendiente, ver S52 de la tanda 2) |
| 191 | Datawise | Servicios IT, Rosario | canal | diego.garcia@datawise.com.ar | https://datawise.com.ar | 14-oct, asunto «Consulta» (prueba) | — | 14-oct: ya tienen esta solución (respondió al primer mail; cuenta en la prueba de asunto) | no interesa | — (no va el seguimiento del 20-oct ni el LinkedIn; posible competidor, ver "Competidores que aparecen") |
| 192 | Midas Consultores | Consultora tecnológica, Mendoza capital | canal | comercial@midasconsultores.com.ar | https://midasconsultores.com.ar | 14-oct, asunto «Consulta» (prueba) | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S54) |
| 193 | Merovingian Data | Consultora de datos, analítica e IA (dashboards, arquitectura de datos, ML), Mendoza capital | canal | mj@merovingiandata.com | https://merovingiandata.com | 14-oct, asunto «Consulta» (prueba) | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S55); WhatsApp publicado: +54 9 261 650-8040 (pendiente, ver S55 de la tanda 2) |
| 194 | Quinto Impacto | Transformación digital e IA, Luján de Cuyo | canal | hola@quintoimpacto.net | https://quintoimpacto.net | 14-oct, asunto «Consulta» (prueba) | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S56) |
| 195 | Axis Human (Inamika Interactive S.A.) | Integración de IA y software a medida, Mendoza capital | canal | info@axishuman.ai | https://axishuman.ai | 14-oct, asunto «Consulta» (prueba) | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S57) |
| 196 | Griftin (Área Clave Consultoría Estratégica SRL) | Outsourcing IT, experiencias inmersivas y agentes de IA para WhatsApp Business (Meta Tech Provider), Yerba Buena | canal | contacto@griftin.com.ar | https://griftin.com.ar | 14-oct, asunto «Consulta» (prueba) | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S58); WhatsApp publicado: +54 9 381 369-3980 (pendiente, ver S58 de la tanda 2) |
| 197 | MBM Sistemas | Software vertical para laboratorios bioquímicos (mbm Lab, en la nube, con IA), Salta capital | canal | ventas@mbmsistemas.com.ar | https://www.mbmsistemas.com.ar | 14-oct, asunto «Consulta» (prueba) | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S59); WhatsApp publicado: +54 9 387 406-0585 (pendiente, ver S59 de la tanda 2) |
| 198 | Blackfish Argentina | Software factory e implementadora de Odoo, Salta capital | canal | info@blackfish.com.ar | https://www.blackfish.com.ar | 14-oct, asunto «Consulta» (prueba) | 21-oct, mismo hilo, desde laureano@atentina.net (llamada de 5 minutos, sin calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md); Resend: entregado) | — | seguimiento enviado | Si no contesta, `sin respuesta` el 28-oct; LinkedIn pendiente (nota y mensaje en S60). 19-oct: llamada nuestra al +54 9 387 457-6457, no atendió (datos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) |
| 199 | Devoo | Implementadora de Odoo, desarrollo web y chatbots de WhatsApp con ChatGPT, Concordia | canal | info@devoo.io | https://devoo.io | 14-oct, asunto «Consulta» (prueba) | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S61) |
| 200 | Sudata | Consultora de BI, modelos predictivos y automatización con IA para pymes, Chaco | canal | contacto@sudata.co | https://sudata.co | 14-oct, asunto «Consulta» (prueba) | — | — | enviado | Seguimiento el 20-oct (texto enviado en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)); LinkedIn pendiente (nota y mensaje en S62). 21-oct: no figura ningún mail suyo en Resend (el 1.er mail no habría salido); fuera de la tanda de seguimientos, confirmar |
| 201 | Crenein | Software vertical para ISP (C-Network, C-Stock, C-Bills) y consultoría de IA con orquestación de agentes, Chaco | canal | comercial@crenein.com | https://crenein.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S63 de la tanda 2); LinkedIn pendiente (nota y mensaje en S63); WhatsApp publicado: +54 9 372 548-2757 (pendiente, ver S63 de la tanda 2) |
| 202 | iSource | Software vertical de gestión para clínicas, sanatorios y obras sociales, Corrientes capital | canal | martindebiasi@isource.com.ar | https://isource.com.ar | — | — | — | descartado | — (no va: el sitio respondió 403; lo sacó el usuario el 14-oct, sin enviar) |
| 203 | Yugoo | ERP propio e implementación de Odoo, logística e IA (agentes conectados al ERP), Corrientes capital | canal | info@yugoo.com.ar | https://www.yugoo.com.ar | — | — | — | descartado | — (no va: el sitio respondió 403; lo sacó el usuario el 14-oct, sin enviar) |
| 204 | Pipe Tech | Software a medida, IA aplicada, automatización de procesos y bots conversacionales, Pilar | canal | frojas@pipe.com.ar | https://www.pipe.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S1 de la tanda 3); LinkedIn pendiente (nota y mensaje en S1) |
| 205 | TGV | Software a medida e implementación de SAP y JD Edwards, CABA | canal | mkt@tgv.com.ar | https://www.tgv.com.ar | 15-oct, asunto «Llamadas de voz» | 19-oct, mismo hilo (recordatorio con link al calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) | — | seguimiento enviado | 19-oct: llamada nuestra al +54 11 7145-2924, no atendió. Si no contesta, `sin respuesta` el 26-oct |
| 206 | Mutt Data | Consultora de datos e IA, CABA | canal | sales@muttdata.ai | https://muttdata.ai | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S3 de la tanda 3); LinkedIn pendiente (nota y mensaje en S3) |
| 207 | Pigmalion Software | Desarrollo de software y productos digitales, CABA | canal | hello@pigmalion.co | https://pigmalion.co | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S4 de la tanda 3); LinkedIn pendiente (nota y mensaje en S4) |
| 208 | Tekne Data Labs | Consultora de datos e IA, CABA | canal | info@teknedatalabs.com | https://teknedatalabs.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S5 de la tanda 3); LinkedIn pendiente (nota y mensaje en S5) |
| 209 | C&S Informática | Soluciones tecnológicas a medida con IA, automatización y analítica de datos, CABA | canal | info@cys.com.ar | https://www.cys.com.ar | 15-oct, asunto «Llamadas de voz» | 19-oct, mismo hilo (recordatorio con link al calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) | — | seguimiento enviado | 19-oct: llamada nuestra al +54 11 4326-3099, no atendió. Si no contesta, `sin respuesta` el 26-oct |
| 210 | Appstract | Software a medida, automatización de procesos e integración de sistemas con IA, CABA | canal | sales@appstract.us | https://appstract.us | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S7 de la tanda 3); LinkedIn pendiente (nota y mensaje en S7) |
| 211 | IT Maker | Consultora de integración y analítica de datos, gobierno de datos e IA, CABA | canal | info@itmaker.com.ar | https://www.itmaker.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S8 de la tanda 3); LinkedIn pendiente (nota y mensaje en S8) |
| 212 | Big Data Estratégico | Consultora chica de transformación digital, datos e IA, CABA | canal | info@bigdataestrategico.com | https://bigdataestrategico.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S9 de la tanda 3); LinkedIn pendiente (nota y mensaje en S9); WhatsApp publicado: +54 9 11 5920-3837 (pendiente, ver S9 de la tanda 3) |
| 213 | Cloud Solutions LATAM | Zoho Advanced Partner, Buenos Aires | canal | hola@cloudsolutionslatam.com | https://www.cloudsolutionslatam.com | 15-oct, asunto «Llamadas de voz» | — | 15-oct: rebotó hola@ (no existe la casilla); el mail no llegó | descartado | Sin email válido: formulario https://www.cloudsolutionslatam.com/contacto o LinkedIn (nota y mensaje en S10 de la tanda 3) |
| 214 | HabSar | Agencia técnica y HubSpot Solutions Provider, Buenos Aires | canal | contact@habsar.com | https://www.habsar.com | 15-oct, asunto «Llamadas de voz» | — | 15-oct: rebotó contact@ (no existe la casilla); el mail no llegó | descartado | Sin email válido: formulario https://www.habsar.com/contacto o LinkedIn (nota y mensaje en S11 de la tanda 3); WhatsApp publicado +54 11 3934-2834 (ver S11 de la tanda 3) |
| 215 | Axcelere | Partner Gold de Odoo, CABA | canal | hola@axcelere.com | https://www.axcelere.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S12 de la tanda 3); LinkedIn pendiente (nota y mensaje en S12); WhatsApp publicado: https (pendiente, ver S12 de la tanda 3) |
| 216 | Blueorange Group | Partner Gold de Odoo con localización argentina propia, San Martín | canal | contacto@blueorange.com.ar | https://www.blueorange.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S13 de la tanda 3); LinkedIn pendiente (nota y mensaje en S13); WhatsApp publicado: Comercial +54 9 11 3058-1769 (texto del pie); soporte https (pendiente, ver S13 de la tanda 3) |
| 217 | Axioma IT Solutions | Software factory y staff augmentation, CABA | canal | axel.diaz@axiomait.com | https://axiomait.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S14 de la tanda 3); LinkedIn pendiente (nota y mensaje en S14); WhatsApp publicado: +54 9 11 4978-4822 (pendiente, ver S14 de la tanda 3) |
| 218 | Hitofusion (Yügo SAS) | Partner Gold de Odoo, Florida | canal | lucas@hitofusion.com | https://www.hitofusion.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S15 de la tanda 3); LinkedIn pendiente (nota y mensaje en S15); WhatsApp publicado: +54 9 11 7100-6160 (pendiente, ver S15 de la tanda 3) |
| 219 | MG Intelligence | Partner de Odoo, Lomas de San Isidro | canal | gflores@mgintelligence.com | https://www.mgintelligence.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S16 de la tanda 3); LinkedIn pendiente (nota y mensaje en S16) |
| 220 | Chroma Agency | Implementación de Odoo ERP y consultoría de negocios, CABA | canal | web@chroma.agency | https://chroma.agency | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S17 de la tanda 3); LinkedIn pendiente (nota y mensaje en S17) |
| 221 | ITBS Business Solutions | Partner Silver de Odoo y canal oficial de Buenos Aires Software (BAS), CABA | canal | contacto@it-bs.com.ar | https://www.it-bs.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S18 de la tanda 3); LinkedIn pendiente (nota y mensaje en S18); WhatsApp publicado: +54 9 11 7547-3844 (pendiente, ver S18 de la tanda 3) |
| 222 | Sysmo | Consultora de software a medida para empresas y gobiernos, Buenos Aires | canal | info@sysmo.com.ar | https://sysmo.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S19 de la tanda 3); LinkedIn pendiente (nota y mensaje en S19) |
| 223 | RockingData | Consultora de IA, machine learning y datos, CABA | canal | hello@rockingdata.com.ar | https://rockingdata.ai | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S20 de la tanda 3); LinkedIn pendiente (nota y mensaje en S20); WhatsApp publicado: +54 11 3172-2737 (pendiente, ver S20 de la tanda 3) |
| 224 | Accedra | Infraestructura IT, ciberseguridad, consultoría Microsoft y 'Software & AI' para empresas, CABA | canal | info@accedra.com.ar | https://www.accedra.com.ar | 15-oct, asunto «Llamadas de voz» | 19-oct, mismo hilo (recordatorio con link al calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) | — | seguimiento enviado | 19-oct: llamada nuestra al +54 11 5365-9887, no atendió. Si no contesta, `sin respuesta` el 26-oct |
| 225 | BGlobal Solutions | Premier Partner de Creatio (CRM y BPM no-code con agentes de IA), Buenos Aires | canal | info@bglobalsolutions.com | https://bglobalsolutions.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S22 de la tanda 3); LinkedIn pendiente (nota y mensaje en S22) |
| 226 | PositiveIT | Integradora de CRM (Salesforce, SugarCRM, Zoho), marketing automation, agentes de IA y bots, Morón | canal | info@positiveit.com.ar | https://www.positiveit.com.ar | 15-oct, asunto «Llamadas de voz» | — | 19-oct (export de Resend): rebotó info@positiveit.com.ar, envío del 15-oct; el mail no llegó | descartado | No mandar más mails a info@positiveit.com.ar ([`blacklist.md`](blacklist.md)). Si la ficha tiene otra casilla publicada, reenviar ahí; si no, LinkedIn o teléfono |
| 227 | Zennon BI | Partner de Microsoft Dynamics 365 y Power Platform, CABA | canal | contacto@zennonbi.com | https://zennonbi.com | 15-oct, asunto «Llamadas de voz» | 19-oct, mismo hilo (recordatorio con link al calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) | 19-oct: llamada nuestra al +54 9 11 5402-0593 (móvil del sitio); atendió Cristian Ventura (fundador y CEO, a confirmar), interesado; Laureano le pasó para agendar una reunión | charla hecha | Agendar la reunión con Cristian Ventura y confirmar fecha; ver "Conversaciones". Teléfonos y personas en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md). 19-oct: le llegó también el recordatorio con el link al calendario |
| 228 | GrowIT | Transformación digital, Buenos Aires | canal | contacto@growit.com.ar | https://growit.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S25 de la tanda 3); LinkedIn pendiente (nota y mensaje en S25) |
| 229 | Quantit | Desarrollo de IA a medida y ciencia de datos, Buenos Aires | canal | somos@bequantit.com | https://bequantit.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S26 de la tanda 3); LinkedIn pendiente (nota y mensaje en S26) |
| 230 | Silogik | Aceleración de procesos de negocio (BPA), RPA, integración de sistemas, analítica y desarrollo web y mobile, Buenos Aires | canal | info@silogik.com | https://www.silogik.com | 15-oct, asunto «Llamadas de voz» | 19-oct, mismo hilo (recordatorio con link al calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) | — | seguimiento enviado | 19-oct: llamada nuestra al +52 55 8852 2761, no atendió. Si no contesta, `sin respuesta` el 26-oct |
| 231 | Proda Software | Partner de Zoho (Zoho One, CRM, Creator, Analytics), Bernal | canal | german@prodasoftware.com | https://www.prodasoftware.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S28 de la tanda 3); LinkedIn pendiente (nota y mensaje en S28) |
| 232 | Datcom Software | Software para logística, trazabilidad y almacenaje (Dettron WMS) con IA y BI, Mar del Plata | canal | info@datcom.io | https://www.datcom.io | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S29 de la tanda 3); LinkedIn pendiente (nota y mensaje en S29) |
| 233 | Potencia Technologies | Productos SaaS nativos en IA para RRHH (SITA, selector de talentos) con WhatsApp Bot, Buenos Aires | canal | info@potenciatech.ar | https://www.potenciatech.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S30 de la tanda 3); LinkedIn pendiente (nota y mensaje en S30) |
| 234 | GiGa Global | Partner Gold de Odoo, Córdoba capital | canal | hola@gigaglobal.com.ar | https://www.gigaglobal.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S31 de la tanda 3); LinkedIn pendiente (nota y mensaje en S31); WhatsApp publicado: +54 9 351 612-7500 (pendiente, ver S31 de la tanda 3) |
| 235 | Global Think Technology | Consultora tecnológica AI-first, Córdoba capital | canal | dghione@globalthinktec.com | https://globalthink.io | — | — | — | descartado | — (no va: el sitio respondió 403; lo sacó el usuario el 14-oct, sin enviar) |
| 236 | Mindfactory | GovTech, Córdoba capital | canal | sebastian.sosa@mindfactory.ar | https://www.mindfactory.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S33 de la tanda 3); LinkedIn pendiente (nota y mensaje en S33) |
| 237 | Program Consultores (PGM) | Software de gestión para municipios, comunas y cooperativas de servicios públicos, Córdoba capital | canal | agiraudo@municipalidad.com | https://www.municipalidad.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S34 de la tanda 3); LinkedIn pendiente (nota y mensaje en S34) |
| 238 | Emser | Consultora tecnológica, Córdoba capital | canal | Jburkle@emser.net | http://www.emser.net | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S35 de la tanda 3); LinkedIn pendiente (nota y mensaje en S35) |
| 239 | DinoCloud | AWS Premier Partner, Córdoba capital | canal | info@dinocloud.co | https://dinocloud.co | 15-oct, asunto «Llamadas de voz» | — | 19-oct (export de Resend): rebotó info@dinocloud.co, envío del 15-oct; el mail no llegó | descartado | No mandar más mails a info@dinocloud.co ([`blacklist.md`](blacklist.md)). Si la ficha tiene otra casilla publicada, reenviar ahí; si no, LinkedIn o teléfono |
| 240 | Vatrox | Integración de plataformas y datos, DevOps y procesos apoyados por IA aplicada (banca, seguros, retail), Córdoba capital | canal | contacto@vatrox.com | https://vatrox.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S37 de la tanda 3); LinkedIn pendiente (nota y mensaje en S37) |
| 241 | Olpa Group | Consultora AI-native, Córdoba capital | canal | info@olpagroup.com | https://olpagroup.com | 15-oct, asunto «Llamadas de voz» | 21-oct, mismo hilo, desde laureano@atentina.net (llamada de 5 minutos, sin calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md); Resend: entregado) | — | seguimiento enviado | Si no contesta, `sin respuesta` el 28-oct, desde laureano@atentina.net, la casilla del 1.er mail según Resend (GA 21-oct: 1 usuario/16 eventos); ★ persona sin email: Gonzalo Gallerano, fundador y CEO (+54 9 351 753-2299). Primer mail en S38 de la tanda 3; LinkedIn pendiente (nota y mensaje en S38); WhatsApp publicado: +54 9 351 753-2299 (pendiente, ver S38 de la tanda 3) |
| 242 | Castelsoft | Implementación de Odoo con IA ('implementación aumentada'), Córdoba capital | canal | info@castelsoft.com | https://castelsoft.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S39 de la tanda 3); LinkedIn pendiente (nota y mensaje en S39) |
| 243 | Dynetis | Consultoría en Odoo, integraciones (pagos, logística, BI) y datos, Villa Carlos Paz | canal | pablo.molla@dynetis.com | https://www.dynetis.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S40 de la tanda 3); LinkedIn pendiente (nota y mensaje en S40) |
| 244 | Glowix / Neos Tech | Plataforma comercial B2B y partner de Microsoft Dynamics GP, Villa María | canal | ggomezarrufat@neos.com.ar | https://www.neos.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S41 de la tanda 3); LinkedIn pendiente (nota y mensaje en S41) |
| 245 | Psiware | Desarrollo de software con IA, automatización y datos, Rosario | canal | contact@psiware.com.ar | https://www.psiware.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S42 de la tanda 3); LinkedIn pendiente (nota y mensaje en S42) |
| 246 | Idear Tech | Software para gobiernos y empresas (GovTech, FinTech) con low-code e IA, Rosario | canal | negocios@ideartechcorp.com | https://ideartechcorp.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S43 de la tanda 3); LinkedIn pendiente (nota y mensaje en S43); WhatsApp publicado: +54 9 341 665-6506 (pendiente, ver S43 de la tanda 3) |
| 247 | Inteligencia Analítica | Consultora de Business Intelligence y Data Analytics, Rosario | canal | contacto@inteligenciaanalitica.com | https://www.inteligenciaanalitica.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S44 de la tanda 3); LinkedIn pendiente (nota y mensaje en S44) |
| 248 | Grupo Aicon | ERP especializado por rubro (sindicatos, obras sociales, mutuales, financieras, mayoristas, droguerías) con IA, Rosario | canal | administracion@grupoaicon.com.ar | https://grupoaicon.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S45 de la tanda 3); LinkedIn pendiente (nota y mensaje en S45); WhatsApp publicado: +54 9 341 690-6680 (pendiente, ver S45 de la tanda 3) |
| 249 | Alchemid | Partner Silver de Odoo, Rafaela | canal | contacto@alchemid.com | https://www.alchemid.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S46 de la tanda 3); LinkedIn pendiente (nota y mensaje en S46); WhatsApp publicado: +54 9 3492 21-9294 (pendiente, ver S46 de la tanda 3) |
| 250 | M3C Software | ERP de gestión integral para pymes con programa de partners (#M3Cpartner), Rosario | canal | comercial@m3csoftware.com.ar | https://m3csoftware.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S47 de la tanda 3); LinkedIn pendiente (nota y mensaje en S47) |
| 251 | ERPYCA | Partner oficial de Odoo con conectores propios (pagos, logística, control horario), Rosario | canal | gaspar@erpyca.com | https://erpyca.com | — | — | — | descartado | — (no va: el sitio respondió 403; lo sacó el usuario el 14-oct, sin enviar) |
| 252 | devFactory | ERP SaaS con asistente de IA para pymes, Luján de Cuyo | canal | contact@devfactory.ar | https://devfactory.ar | 15-oct, asunto «Llamadas de voz» | 19-oct, mismo hilo (recordatorio con link al calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) | — | seguimiento enviado | 19-oct: llamada nuestra al +54 261 525-0354, no atendió. Si no contesta, `sin respuesta` el 26-oct |
| 253 | Solutions Hub / AGP & ROD Servicios | Consultoría SAP (S/4HANA, SuccessFactors, BTP), Mendoza capital | canal | rodrigo.lopez@solutionshub.com.ar | https://solutionshub.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S50 de la tanda 3); LinkedIn pendiente (nota y mensaje en S50); WhatsApp publicado: +54 9 261 501-8054 (pendiente, ver S50 de la tanda 3) |
| 254 | Alpardata | Partner Silver de Odoo, Guaymallén | canal | joaquin@alpardata.com.ar | https://www.alpardata.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S51 de la tanda 3); LinkedIn pendiente (nota y mensaje en S51); WhatsApp publicado: +54 9 261 685-3970 (pendiente, ver S51 de la tanda 3) |
| 255 | Hexium Software Factory | Software factory y partner oficial de Odoo, Godoy Cruz | canal | info@hexium.com.ar | https://hexium.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S52 de la tanda 3); LinkedIn pendiente (nota y mensaje en S52); WhatsApp publicado: +54 9 261 248-6994 (pendiente, ver S52 de la tanda 3) |
| 256 | Corpora | IA generativa accesible y automatización no-code para pymes, con mentoría, Maipú | canal | gerencia@somoscorpora.com | https://www.somoscorpora.com | — | — | — | descartado | — (no va: el sitio respondió 403; lo sacó el usuario el 14-oct, sin enviar) |
| 257 | GoodComex (Full Comex SAS) | Partner Silver de Odoo, Mendoza | canal | marcelo.vazquez@goodcomex.com | https://goodcomex.com | — | — | — | descartado | — (no va: el sitio respondió 403; lo sacó el usuario el 14-oct, sin enviar) |
| 258 | Solution IT (SIT) | Desarrollo de software e IA (GPT, LLM) para empresas de Neuquén, Neuquén capital | canal | info@solution-it.com.ar | https://www.solution-it.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S55 de la tanda 3); LinkedIn pendiente (nota y mensaje en S55) |
| 259 | PuntoGap | Software a medida y consultoría de IA para Oil & Gas y retail, Neuquén capital | canal | info@puntogap.com | https://www.puntogap.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S56 de la tanda 3); LinkedIn pendiente (nota y mensaje en S56) |
| 260 | Pragmática Consultores | Partner de SAP Business One para Oil & Gas y minería, Neuquén capital | canal | info@pragmaticaconsultores.com | https://www.pragmaticaconsultores.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S57 de la tanda 3); LinkedIn pendiente (nota y mensaje en S57); WhatsApp publicado: +54 299 546-1483 (pendiente, ver S57 de la tanda 3) |
| 261 | DITyC | Consultora de tecnología, Neuquén capital | canal | info@dityc.com.ar | https://www.dityc.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S58 de la tanda 3); LinkedIn pendiente (nota y mensaje en S58); WhatsApp publicado: +54 9 299 633-2007 (pendiente, ver S58 de la tanda 3) |
| 262 | Patagonian | Software factory con práctica de IA agéntica, General Roca | canal | info@patagonian.com | https://patagonian.com | — | — | — | descartado | — (no va: el sitio respondió 403; lo sacó el usuario el 14-oct, sin enviar) |
| 263 | Waiki Consultores en Sistemas | Implementación de Odoo con módulos propios (sueldos argentinos, tableros, suscripciones), Cipolletti | canal | info@waiki.com.ar | https://waiki.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S60 de la tanda 3); LinkedIn pendiente (nota y mensaje en S60) |
| 264 | Ingenio Solutions | Partner Silver de Odoo para fábricas de alimentos, distribuidoras y minería, Chajarí | canal | contacto@ingeniosolutions.com.ar | https://ingeniosolutions.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S61 de la tanda 3); LinkedIn pendiente (nota y mensaje en S61); WhatsApp publicado: +54 9 11 4038-1050 (pendiente, ver S61 de la tanda 3) |
| 265 | Quay | Transformación digital, Concordia | canal | info@quay.com.ar | https://quay.com.ar | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S62 de la tanda 3); LinkedIn pendiente (nota y mensaje en S62) |
| 266 | Tecopens Consulting | Consultoría de transformación digital para pymes del NOA, San Miguel de Tucumán | canal | equipo@tecopensconsulting.com | https://www.tecopensconsulting.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S63 de la tanda 3); LinkedIn pendiente (nota y mensaje en S63) |
| 267 | Grupo Orange | Soluciones tecnológicas integrales en Salta y el norte, Salta capital | canal | info@grupoorange.com.ar | https://grupoorange.com.ar | — | — | — | descartado | — (no va: el sitio respondió 403; lo sacó el usuario el 14-oct, sin enviar) |
| 268 | Grupo Mill | Consultora de profesionalización de pymes con servicios de inteligencia artificial, datos y agro, Santa Rosa | canal | comunicacion@grupomill.com | https://grupomill.com | 15-oct, asunto «Llamadas de voz» | — | — | enviado | Seguimiento el 21-oct, una línea en el mismo hilo (sin redactar; primer mail en S65 de la tanda 3); LinkedIn pendiente (nota y mensaje en S65); WhatsApp publicado: +54 9 2954 33-0420 (pendiente, ver S65 de la tanda 3) |
| 269 | Erpwoosync (antes «ERP local, nombre a confirmar») | Servicios de ERP, lugar a confirmar | canal | — | — | — (llegó por un contacto del usuario, sin envío) | — | 9-oct: charla agendada (informado por el usuario). 19-oct: Laureano lo llamó y atendió Gabriel (escrito «Gabrien»; nombre y cargo a confirmar); positiva: Laureano le arma una demo de llamadas telefónicas con un 0810 | charla hecha | Armar la demo de llamadas telefónicas con número 0810 para Gabriel y avisarle; ver "Conversaciones" |
| 270 | Gimnasio (nombre a confirmar) | Gimnasio con 200 alumnos, lugar a confirmar | cliente | — | — | — (sin envío) | — | 9-oct (informado): charla hecha; necesitan agentes para varias cosas | charla hecha | Armar el prototipo para la venta (alcance y fecha a definir); falta nombre, contacto y lugar |
| 271 | Inthegra Software | Software sobre Oracle (salud, crédito y tarjetas, ERP retail, CRM, AI Chatbot), Córdoba | canal | nicolas.escobar@inthegrasoftware.com | https://inthegrasoftware.com | — (no le escribimos: mail entrante a hola@ el 14-oct, 10:29; origen probable, sin evidencia: Elebar #32 o Sucrédito #34 les reenvió nuestro mail) || 19-oct, desde larcanio@gmail.com | 14-oct: Nicolás Escobar (auxiliar de marketing), asunto «Consulta sobre posibles integraciones – Inthegra»: preguntan si buscamos un socio tecnológico para integraciones o alianzas comerciales, y si hay una necesidad concreta; adjuntan su brochure institucional; ofrecen reunión. 19-oct (8:10): follow-up nuestro a Nicolás desde larcanio@gmail.com, propone una llamada de 5 min para que decida ahí si sigue (la respuesta anterior a su mail no está registrada: a confirmar fecha y casilla) | follow-up enviado | Esperar respuesta a la propuesta de llamada de 5 min. Ver la nota de abajo |
| 272 | NexHub | Software de gestión comercial propio (POS/ERP, facturación ARCA), Argentina | canal | clientes@nexhub.com.ar | https://nexhub.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 273 | Wynges (Líder Gestión ERP) | ERP propio para pymes, Argentina | canal | info@lidergestion.com | https://wynges.com | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 274 | GestorUno | ERP SaaS propio para pymes, Rosario (Santa Fe) | canal | ventas@gestoruno.com | https://gestoruno.com | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 275 | Tribot ERP | ERP propio + app móvil + e-commerce para pymes, Rosario (Santa Fe) | canal | juan.manuel@tribot.net | https://tribot.net | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 276 | CG Software | Gestión y facturación AFIP/ARCA propia con tienda online, Argentina | canal | grossocristian.cg@gmail.com | https://www.cgsoftware.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 277 | iCOMM | Plataforma propia de gestión multisectorial para pymes, Argentina | canal | info@icomm.app | https://icomm.app | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 278 | Prysma Software (MiGestion) | ERP SaaS propio para pymes, Argentina | canal | info@prysmasoft.com | https://migestion.app | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 279 | KM44 | Sistema contable propio para estudios contables y consorcios, Argentina | canal | info@km44.com.ar | https://km44.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 280 | Aguazul Sistemas (MyEstudio) | Sistema web propio para estudios contables y pymes, Argentina | canal | info@myestudio.com.ar | https://myestudio.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 281 | Estudio Digital | Software de gestión propio para estudios contables, Argentina | canal | soporte@miestudiodigital.com.ar | https://miestudiodigital.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 282 | Contala | Software propio para estudios contables, Argentina | canal | soporte@contala.com.ar | https://www.contala.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 283 | ConsorcioSimple | Software propio de administración de consorcios, Argentina | canal | info@consorciosimple.com.ar | https://consorciosimple.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 284 | Kavanagh Group (Kavanagh Cloud) | Software propio de administración de consorcios, Argentina | canal | ventas@kavanaghgroup.com.ar | https://www.kavanaghgroup.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 285 | Octopus | Software propio de administración de consorcios y barrios con IA, Argentina | canal | info@octopus.com.ar | https://www.octopus.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 286 | JUDICO | Software propio de gestión jurídica con IA, Argentina | canal | judico@judico.com.ar | https://www.judico.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 287 | Estudio360 | Software propio de gestión para estudios jurídicos, Buenos Aires | canal | francisco.degrandis@estudio360.com.ar | https://estudio360.com.ar | 15-oct | 19-oct, mismo hilo (recordatorio con link al calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) | — | seguimiento enviado | Si no contesta, `sin respuesta` el 26-oct |
| 288 | RivoLegal | Software propio de gestión jurídica con IA, Buenos Aires | canal | ventas@rivolegal.com | https://rivolegal.com | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 289 | Themis | Software propio de gestión para estudios jurídicos, Argentina | canal | contacto@themis.com.ar | https://themis.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 290 | AgroGi (CampoGi) | Software de gestión agropecuaria propio, Argentina | canal | info@agrogi.com.ar | https://agrogi.com.ar | 15-oct | — | 19-oct (export de Resend): rebotó info@agrogi.com.ar, envío del 15-oct; el mail no llegó | descartado | No mandar más mails a info@agrogi.com.ar ([`blacklist.md`](blacklist.md)). Si la ficha tiene otra casilla publicada, reenviar ahí; si no, LinkedIn o teléfono |
| 291 | America GIS (AGIS Agro) | Software de gestión agrícola y contabilidad agropecuaria propio, Argentina | canal | info@americagis.com.ar | https://americagis.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 292 | GENUBE | Software de gestión escolar integral (administración, cobranza, académico, sueldos), San Miguel de Tucumán (Tucumán) | canal | info@genube.com | https://genube.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 293 | EDUCARF | Software de gestión escolar y campus virtual para colegios, Argentina (sin ciudad publicada) | canal | hola@educarf.com | https://educarf.com | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 294 | Clínica Online | Turnos, historia clínica y teleconsultas para profesionales y centros de salud, Argentina (sin ciudad publicada) | canal | soporte@clinicaonline.com.ar | https://www.clinicaonline.com.ar | 15-oct | 19-oct, mismo hilo (recordatorio con link al calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) | — | seguimiento enviado | 19-oct: llamada nuestra al +54 11 5803-3388, no atendió. Si no contesta, `sin respuesta` el 26-oct |
| 295 | ConsultSmart | Turnos e historias clínicas para consultorios y clínicas (escritorio + web), Argentina (servidor propio en Buenos Aires) | canal | info@consultsmart.com.ar | https://www.consultsmart.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 296 | DocSuite | Turnos, historia clínica y confirmación por WhatsApp para consultorios y policonsultorios, Argentina (sin ciudad publicada) | canal | contacto@docsuite.ar | https://docsuite.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 297 | POSIT | Sistema POS y de gestión gastronómica y para comercios con facturación ARCA, Argentina (sin ciudad publicada) | canal | comercial@positsistema.com | https://www.positsistema.com | 15-oct | — | 19-oct (export de Resend): rebotó comercial@positsistema.com, envío del 15-oct (dos envíos); el mail no llegó | descartado | No mandar más mails a comercial@positsistema.com ([`blacklist.md`](blacklist.md)). Si la ficha tiene otra casilla publicada, reenviar ahí; si no, LinkedIn o teléfono |
| 298 | Nikao | Sistema POS para restaurantes y cafeterías con facturación ARCA, Argentina (sin ciudad publicada) | canal | info@nikao.com.ar | https://nikao.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 299 | Upfit | Software de gestión para gimnasios con app para alumnos y profes, Argentina (sin ciudad publicada) | canal | soporte@upfit.ar | https://www.upfit.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 300 | Gymzoft | ERP para gimnasios y centros deportivos (reservas, AFIP, app propia), Argentina (sin ciudad publicada) | canal | info.fizoft@gmail.com | https://gymzoft.com | 15-oct | 19-oct, mismo hilo (recordatorio con link al calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) | — | seguimiento enviado | 19-oct: llamada nuestra al +54 2657 67-5900, no atendió. Si no contesta, `sin respuesta` el 26-oct |
| 301 | Gympas | Software de gestión integral para gimnasios (accesos, membresías, caja, ARCA), Argentina (sin ciudad publicada) | canal | gympas.ar@gmail.com | https://www.gympas.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 302 | Oliauto | Sistema para concesionarias de automotores (ventas, stock, taller, contabilidad), Argentina (sin ciudad publicada) | canal | ventas@oliauto.com.ar | http://www.oliauto.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 303 | Frontera Sistemas (Antares 86) | CRM y gestión de taller para talleres mecánicos y concesionarias, Argentina (sin ciudad publicada) | canal | clientes@fronterasistemas.com | https://fronterasistemas.com | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 304 | Valbará (TMS) | TMS: software propio de gestión de transporte, Argentina (sin ciudad publicada) | canal | valbara@valbara.com.ar | https://www.valbara.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 305 | FonteSoft (TMS) | TMS propio para transporte de carga general, Argentina (sin ciudad publicada) | canal | administracion@fontesoft.com | http://www.fontesoft.com | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 306 | CRISTAL+ | Software propio de gestión para transporte y logística (TMS/FMS/WMS), Argentina (sin ciudad publicada) | canal | ventas@digital-express.com.ar | https://softwarecristal.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 307 | Nousaris | TMS + administración (producto propio) para operación y gestión, Argentina (sin ciudad publicada) | canal | info@nousaris.com | https://nousaris.com | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 308 | e-Sueldos | Sistema de liquidación de sueldos y RRHH online (260 convenios), Mendoza (Mendoza) | canal | info@e-sueldos.com | https://e-sueldos.com | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 309 | Sueldos Net | Software de liquidación de sueldos con soporte experto, Mar del Plata (Buenos Aires) | canal | info@sueldosnet.com | https://www.sueldosnet.com | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 310 | GestiónClub | Sistema de gestión para clubes deportivos, hecho en San Luis, San Luis (San Luis) | canal | gestionclub.ar@gmail.com | https://gestionclub.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 311 | Onix (SIRF) | Software propio para la industria farmacéutica (farmacias, droguerías, laboratorios), CABA (Buenos Aires) | canal | info@onixsa.com.ar | https://www.onixsa.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 312 | AlfaBeta (Winfarma) | Software para farmacias (Winfarma), Argentina (sin ciudad publicada) | canal | suscripciones@alfabeta.net | https://www.winfarma.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 313 | SiCoFa | Sistema de gestión para farmacias, Argentina (sin ciudad publicada) | canal | info@sicofa.com.ar | https://sicofa.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 314 | OpenPlus | Software de gestión para droguerías, farmacias e indumentaria, con IA, Argentina (sin ciudad publicada) | canal | info@openplus.com.ar | https://openplus.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 315 | Gestión Comercio | Software de gestión para kioscos y comercios minoristas (ARCA), Argentina (sin ciudad publicada) | canal | gestionesucomercio@gmail.com | https://gestioncomercio.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 316 | enorden | Software de gestión comercial para comercios físicos y ecommerce, con IA, Argentina (sin ciudad publicada) | canal | contacto@enorden.net | https://enorden.net | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 317 | Creadores de Soft | Software de gestión hotelera y de spa (producto propio), Argentina (sin ciudad publicada) | canal | ventas@creadoresdesoft.com.ar | https://www.creadoresdesoft.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 318 | Aturna VET | Software de gestión veterinaria (turnos, internaciones, stock), Argentina (sin ciudad publicada) | canal | info@northar.com.ar | https://www.aturna-vet.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 319 | Denteo | Software de gestión odontológica (clínica, laboratorio y app), Argentina (sin ciudad publicada) | canal | info@denteo.com.ar | https://denteo.com.ar | 15-oct | 19-oct, mismo hilo (recordatorio con link al calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) | — | seguimiento enviado | 19-oct: llamada nuestra al +54 9 3482 20-1213, no atendió. Si no contesta, `sin respuesta` el 26-oct |
| 320 | Dentry | Software de gestión para consultorios odontológicos, Rosario (Santa Fe) | canal | contacto@dentry.com.ar | https://www.dentry.com.ar | 15-oct | 21-oct, mismo hilo, desde hola@atentina.com.ar (llamada de 5 minutos, sin calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) | — | seguimiento enviado | Si no contesta, `sin respuesta` el 28-oct; LinkedIn pendiente |
| 321 | Agroconexiones | Software de gestión agropecuaria (Agro Panel), Argentina (sin ciudad publicada) | canal | agroconexiones.com@gmail.com | https://agroconexiones.com | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 322 | Legio | Sistema de gestión jurídica con IA para estudios de abogados, Argentina (sin ciudad publicada) | canal | privacidad@legio.ai | https://www.legio.com.ar | 15-oct | — | 19-oct (export de Resend): rebotó privacidad@legio.ai, envío del 15-oct; el mail no llegó | descartado | No mandar más mails a privacidad@legio.ai ([`blacklist.md`](blacklist.md)). Si la ficha tiene otra casilla publicada, reenviar ahí; si no, LinkedIn o teléfono |
| 323 | Sauce Gestión | ERP para pymes argentinas (facturación ARCA, stock, cuentas corrientes), Argentina (sin ciudad publicada) | canal | info@saucegestion.com | https://saucegestion.com | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 324 | Facturarg | ERP en la nube con AFIP, tienda online e IA (producto propio), Argentina (sin ciudad publicada) | canal | soporte@facturarg.com | https://facturarg.com | 15-oct | — | 19-oct (export de Resend): rebotó soporte@facturarg.com, envío del 15-oct; el mail no llegó | descartado | No mandar más mails a soporte@facturarg.com ([`blacklist.md`](blacklist.md)). Si la ficha tiene otra casilla publicada, reenviar ahí; si no, LinkedIn o teléfono |
| 325 | Orion Sistemas | Software de gestión cloud (ERP, inmobiliarias, estudios contables), 20+ años, Argentina (sin ciudad publicada) | canal | hola@orion.ar | https://orion.com.ar | 15-oct | 21-oct, mismo hilo, desde laureano@atentina.net (llamada de 5 minutos, sin calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) | — | seguimiento enviado | Si no contesta, `sin respuesta` el 28-oct; LinkedIn pendiente. 19-oct: llamada nuestra al +54 9 11 2321-6228, no atendió (datos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) |
| 326 | Staciona | Software propio para estacionamientos, Argentina (sin ciudad publicada) | canal | ayuda@staciona.com.ar | https://staciona.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 327 | AdminParking | Software para estacionamientos, garages y cocheras, Argentina (versión es-ar) | canal | hola@adminparking.com | https://adminparking.com | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 328 | Visionsoft | Software para ópticas (recetas, stock, facturación ARCA), Argentina y México | canal | sistemasvisionsoft@gmail.com | https://www.visionsoft.app | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 329 | Fudo | POS y gestión para gastronomía (SaaS propio), Argentina (sin ciudad publicada) | canal | hola@fu.do | https://fu.do | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 330 | Maxirest | Software de gestión gastronómica (all in one), Zárate (Buenos Aires) | canal | 100plan@maxirest.com | https://maxirest.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 331 | ClinIA | Sistema de gestión para clínicas y centros de salud con IA, Argentina (sin ciudad publicada) | canal | administracion@clinia.com.ar | https://www.clinia.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 332 | iNOTARY | Sistema de gestión notarial con IA, Argentina (sin ciudad publicada) | canal | soporte@inotary.ar | https://www.inotary.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 333 | Fixa (Mutual Core) | Software propio de gestión integral para mutuales, Rosario (Santa Fe) | canal | info@fixa.com.ar | https://www.fixa.com.ar | 15-oct | 19-oct, mismo hilo (recordatorio con link al calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) | — | seguimiento enviado | Si no contesta, `sin respuesta` el 26-oct |
| 334 | SINADY | Software de gestión de servicios para vehículos, Córdoba (Córdoba) | canal | consultas@sinady.com.ar | https://sinady.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 335 | Flota360 | Software propio de gestión de flotas, Argentina (sin ciudad publicada) | canal | soporte@flota360.com.ar | https://www.flota360.com.ar | 15-oct | — | 19-oct (export de Resend): rebotó soporte@flota360.com.ar, envío del 15-oct; el mail no llegó | descartado | No mandar más mails a soporte@flota360.com.ar ([`blacklist.md`](blacklist.md)). Si la ficha tiene otra casilla publicada, reenviar ahí; si no, LinkedIn o teléfono |
| 336 | Power System (idata) | Sistema idata para administración de consorcios y barrios cerrados, Argentina (sin ciudad publicada) | canal | power@powersystem.com.ar | https://www.powersystem.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 337 | MeSumo | Plataforma SaaS para ONGs (actividades, pagos y donaciones), Buenos Aires (Argentina) | canal | contacto@mesumo.app | https://mesumo.app | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 338 | ProCurva | Sistema de gestión para negocios de indumentaria, Rosario (Santa Fe) | canal | hola@procurva.com | https://procurva.com | 15-oct | — | 19-oct (export de Resend): rebotó hola@procurva.com, envío del 15-oct; el mail no llegó | descartado | No mandar más mails a hola@procurva.com ([`blacklist.md`](blacklist.md)). Si la ficha tiene otra casilla publicada, reenviar ahí; si no, LinkedIn o teléfono |
| 339 | Total Stock | Sistema de gestión para tiendas de ropa (stock por talle y color), Argentina (sin ciudad publicada) | canal | info@totalstock.com.ar | https://www.totalstock.com.ar | 15-oct | — | — | enviado | Seguimiento el 21-oct, mismo hilo (una línea, sin redactar); LinkedIn pendiente |
| 340 | Aumo | Sistema para tiendas de ropa (stock, ventas, caja y catálogo), Argentina (sin ciudad publicada) | canal | hola@aumo.com.ar | https://aumo.com.ar | 15-oct | — | 19-oct (export de Resend): rebotó hola@aumo.com.ar, envío del 15-oct; el mail no llegó | descartado | No mandar más mails a hola@aumo.com.ar ([`blacklist.md`](blacklist.md)). Si la ficha tiene otra casilla publicada, reenviar ahí; si no, LinkedIn o teléfono |
| 341 | Qontabiliza | ERP argentino para pymes (facturación ARCA, administración y contable), Argentina (sin ciudad publicada) | canal | administracion@q-company.ar | https://qontabiliza.ar | 15-oct | 21-oct, mismo hilo, desde laureano@atentina.net (llamada de 5 minutos, sin calendario; textos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md); Resend: entregado) | — | seguimiento enviado | Si no contesta, `sin respuesta` el 28-oct; LinkedIn pendiente. 19-oct: llamada nuestra al +54 9 11 3021-5567, no atendió (datos en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md)) |

**Charla agendada con un partner de una empresa grande de salud (informado el 9-oct-2026):** el usuario no dijo
cuál. Puede ser Integrando Salud (#99 / L8), pero no está confirmado: sus filas quedan como estaban hasta confirmarlo.
Falta la empresa y la fecha.

**Inthegra Software (#271), 14-oct-2026.** Mail nuevo a hola@atentina.com.ar (10:29), no respuesta a un hilo nuestro:
"Gracias por contactarnos y compartirnos información sobre Atentina". Preguntan (1) si buscamos un socio tecnológico para
integraciones con otros sistemas o alianzas comerciales para llegar a nuevos clientes, y (2) si hay una necesidad de integración
o un proyecto en curso. Adjuntan "Brochure - Inthegra Abril 2026 (1).pdf" (institucional). Ofrecen reunión. No hay otros mails
de Inthegra en Gmail, y Elebar (#32) y Sucrédito (#34) no respondieron (verificado por el usuario el 14-oct). Hipótesis sobre
el origen, sin evidencia: uno de esos dos clientes suyos les reenvió nuestro mail.
Datos del sitio (leído el 14-oct-2026, `robots.txt` abierto; copia en `scratch/prospectos/inthegra/`):

- Qué hacen: software sobre Oracle (APEX, OCI) para salud (prepagas, emergencias, medicina laboral), crédito y tarjetas, ERP
  retail, CRM y un "AI Chatbot" de atención y cobranzas por WhatsApp; más de 20 años, más de 150 clientes, Córdoba
  (WhatsApp +54 9 351 739-3307).
- Clientes publicados: Elebar (en la home, originación de créditos) y Sucrédito / Valle Fértil SA (dos casos de éxito: el core
  financiero de tarjetas y préstamos y la alta online con biometría). De ahí la hipótesis del reenvío.
- Programa de partners (`/partners.html`): cuatro modelos. El que encaja es el 03, "Partner Tecnológico / Integración", para
  empresas de IA, comunicaciones y WhatsApp con producto propio, con ofertas conjuntas. WhatsApp de partners +54 9 351 787-0115.
- Superposición: su AI Chatbot hace cobranza y atención por WhatsApp, como nuestro WhatsApp. Voz no publican: ahí está el
  complemento (cobranza y recordatorios por teléfono, turnos de salud, atención).

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | nicolas.escobar@inthegrasoftware.com | persona | Nicolás Escobar, auxiliar de marketing (firma) | su mail del 14-oct a hola@ (verificado en Gmail por el usuario); no figura en el sitio |
| | comercial@inthegrasoftware.com | área | consultas comerciales y ventas | https://inthegrasoftware.com/contacto.html (14-oct-2026) |
| | productos@inthegrasoftware.com | área | productos | ídem |
| | servicios@inthegrasoftware.com | área | servicios Oracle y consultoría | ídem |
| | contacto@inthegrasoftware.com | atención | casilla general | https://inthegrasoftware.com/ (14-oct-2026) |

Personas sin email publicado (`/equipo_gestion.html`): Mariano Vocos (CEO y fundador), Martín Líder Medina (CTO y fundador),
Eric Galíndez (manager comercial), Diego Vottero (project leader Credit), Gabriel Arias (project leader Health).

### Cómo se llena

- **1.er envío / Seguimiento:** la fecha en que salió. Máximo un seguimiento por contacto; si
  tampoco contesta, pasa a `sin respuesta` a los 7 días.
- **Respuesta:** fecha y una línea con lo que dijo (`9-oct: piden llamada, escribe la gerente`).
  Un rebote va acá (`rebotó`) y el estado pasa a `descartado` o se busca otro email.
- **Estado:** uno de
  `borrador` (redactado, sin enviar) → `enviado` → `seguimiento enviado` → `respondió` →
  `charla agendada` → `charla hecha` → `propuesta` → `piloto`; o `sin respuesta`, `no interesa`, `descartado`.
- **Email:** el destinatario, que es el ★ de la tanda (el de mayor potencial). Todos los emails
  encontrados por empresa están en el `.md` y el `.csv` de su tanda; formato en [`envios/README.md`](envios/README.md).
  En un contacto ya enviado queda la dirección a la que salió; el ★ va en "Próxima acción" si es otro.
- **Próxima acción:** qué y cuándo. Si no hay nada que hacer, `—`.
- No se borra una fila: un contacto cerrado queda con su estado final.

## Envíos

| Fecha | Tanda | Cantidad | Desde | Textos |
|---|---|---|---|---|
| 2-oct | Primeros 10, uno o dos por rubro | 10 | laureano@atentina.com.ar | [`envios/2026-10-02-primeros-10.md`](envios/2026-10-02-primeros-10.md) |
| 2-oct | Browix (ventas) | 1 | laureano@atentina.com.ar | [`envios/2026-10-02-browix.md`](envios/2026-10-02-browix.md) |
| 5-oct | Tanda 1, segundo envío al ★ con texto de IA (8 mails nuevos, 3 en el mismo hilo) | 11 | laureano@atentina.com.ar | [`envios/2026-10-05-tanda1-reenvio.md`](envios/2026-10-05-tanda1-reenvio.md) |
| 5-oct | Segunda tanda, texto de IA | 10 | laureano@atentina.com.ar | [`envios/2026-10-02-segunda-tanda.md`](envios/2026-10-02-segunda-tanda.md) |
| 5-oct | Tercera tanda, texto de IA | 20 | laureano@atentina.com.ar | [`envios/2026-10-05-tercera-tanda.md`](envios/2026-10-05-tercera-tanda.md) |
| 5-oct | Cuarta tanda, mutuales de ayuda económica de Córdoba, partes A a D | 20 | laureano@atentina.com.ar | [`a`](envios/2026-10-05-cuarta-tanda-a.md), [`b`](envios/2026-10-05-cuarta-tanda-b.md), [`c`](envios/2026-10-05-cuarta-tanda-c.md), [`d`](envios/2026-10-05-cuarta-tanda-d.md) |
| 5-oct | Quinta tanda, mutuales del interior este y sur de Córdoba (12 sin ayuda económica confirmada) | 30 | laureano@atentina.com.ar | [`g1`](envios/2026-10-05-quinta-tanda-g1.md), [`g2`](envios/2026-10-05-quinta-tanda-g2.md), [`g3`](envios/2026-10-05-quinta-tanda-g3.md), [`g4`](envios/2026-10-05-quinta-tanda-g4.md), [`g5`](envios/2026-10-05-quinta-tanda-g5.md), [`g6`](envios/2026-10-05-quinta-tanda-g6.md) |
| 6-oct | Canales: 12 aliados sin LinkedIn enviado (parte C, parte D, Kernel y Tekhne) | 12 | laureano@atentina.com.ar | [`a`](envios/2026-10-06-canales-a.md), [`b`](envios/2026-10-06-canales-b.md), [`c`](envios/2026-10-06-canales-c.md), [`d`](envios/2026-10-06-canales-d.md) |
| 7-oct | Software e IA (partners): 27 consultoras e integradores que ya venden IA, `canales2` | 27 | laureano@atentina.com.ar | [`envios/2026-10-07-software-ia-partners.md`](envios/2026-10-07-software-ia-partners.md) |
| 8-oct | Software e IA (partners), tanda 2: S1 a S40, `canales3` | 40 | laureano@atentina.com.ar | [`envios/2026-10-07-software-ia-partners-2.md`](envios/2026-10-07-software-ia-partners-2.md) |
| 14-oct | Seguimientos en el mismo hilo, texto personalizado por empresa: vencidos del 9-oct (#12–41, Unisem con su texto), vencidos del 13-oct (#96, 101–105, 107, 108, 110, 111; #102 con CC a anibalc@) y del 14-oct (#112–138 sin Nybble); link `follow_up_<campaña>` | 66 | laureano@atentina.com.ar | [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md) |
| 14-oct | Software e IA (partners), tanda 2: S41 a S62 (#179–200), `canales3`, presentación, cierre y asunto en variantes; **#187–200 con asunto "Consulta"** (prueba) | 22 | laureano@atentina.com.ar | [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md) |
| 15-oct | Partners 2 y 3 pendientes, texto nuevo y asunto «Llamadas de voz» (`canales3` y `canales4`): #201, #204–234, #236–250, #252–255, #258–261, #263–266 y #268 (avisos del usuario: "enviado hasta el #260" y después "todos los mensajes enviados hasta 268"; sin los descartados por 403: #202, 203, 235, 251, 256, 257, 262, 267). #213 y #214 rebotaron. Los textos que salieron son los de las tandas (nota del 15-oct al principio de cada una; HTML de envío `scratch/envios/2026-10-14-pendientes.html`, idéntico); no hay archivo de enviados aparte | 60 (58 entregados) | laureano@atentina.com.ar | [`envios/2026-10-07-software-ia-partners-2.md`](envios/2026-10-07-software-ia-partners-2.md) (S63), [`envios/2026-10-07-software-ia-partners-3.md`](envios/2026-10-07-software-ia-partners-3.md) |
| 15-oct | Seguimientos en el mismo hilo a los que hicieron clic en el link y no respondieron: partners #175, 154, 173, 163 (`follow_up_canales_3`, vencían hoy) y mutuales #67, 72 (`follow_up_tanda_5`) y #44, 47 (`follow_up_tanda_4`, vencían el 9-oct); texto personalizado por empresa | 8 | laureano@atentina.com.ar | [`envios/2026-10-15-seguimientos.md`](envios/2026-10-15-seguimientos.md) |
| 15-oct | Software con producto propio (ERP/contable/administración/consorcios/jurídico/agro), 20 (#272–291), asunto «Consulta» | 20 | laureano@atentina.com.ar | [`envios/2026-10-15-erp-contable.md`](envios/2026-10-15-erp-contable.md) |
| 15-oct | Software con producto propio, tanda 2, E10–E30 (#301–321), asunto «Consulta» (envío por Resend) | 21 | hola@atentina.com.ar (Resend) | [`envios/2026-10-15-erp-contable-2.md`](envios/2026-10-15-erp-contable-2.md) |
| 15-oct | Software con producto propio, tanda 2, E1–E9 y E31–E50 (#292–300 y #322–341), asunto «Consulta» (envío por Resend) | 29 | laureano@atentina.net (Resend) | [`envios/2026-10-15-erp-contable-2.md`](envios/2026-10-15-erp-contable-2.md) |
| 21-oct | Seguimientos por clic, llamada de 5 minutos sin calendario (#341, 187, 198, 185, 68, 241, 173, 320 y 325) | 9 | laureano@atentina.net (Dentry #320 desde hola@atentina.com.ar) | [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md) |
| 21-oct | Seguimientos pendientes, borrador: 121 de las tandas del 14 y 15-oct, 32 partners del 8-oct y 37 mutuales del 5-oct; llamada de 5 minutos, sin calendario (HTML con avance guardado: `scratch/envios/2026-10-21-seguimientos-pendientes.html`) | 190 (sin enviar) | la casilla del 1.er mail | [`envios/2026-10-21-seguimientos-pendientes.md`](envios/2026-10-21-seguimientos-pendientes.md) |

Tanda de software e IA (partners), contactos 112 a 138: **email enviado el 7-oct-2026** (los 27); seguimiento en el mismo hilo
**enviado el 14-oct** (26; Nybble no, respondió). **LinkedIn pendiente** para los 27: la nota de invitación y el mensaje largo de cada empresa
están en [`envios/2026-10-07-software-ia-partners.md`](envios/2026-10-07-software-ia-partners.md); al enviarlos, fila en "LinkedIn"
con `utm_source=linkedin`. **WhatsApp**: 11 de las 27 publican un número (buscado el 7-oct-2026; número y fuente en "Otros canales"
de cada empresa en el `.md` y columna `whatsapp` del `.csv`, y en "Próxima acción" de cada fila); canal pendiente, sin mensaje
redactado. Aionixs no se recorrió (robots.txt). Reservas en `scratch/prospectos/software-ia/notas.md`.

Tanda 2 de software e IA (partners), contactos 139 a 203, `canales3`: **S1 a S40 (contactos 139 a 178) enviados por email el 8-oct-2026**, seguimiento el 15-oct (4 días hábiles; el 12 es feriado); **S41 a S62 (179 a 200) enviados el 14-oct-2026** (textos como salieron en [`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md)), seguimiento el 20-oct; S63 (Crenein, 201) enviado el 15-oct con el texto nuevo (asunto «Llamadas de voz», el de S63 en el `.md`), seguimiento el 21-oct; S64 y S65 (iSource y Yugoo, 202 y 203) descartados porque el sitio respondió 403. La tanda tiene 65 empresas (toda Argentina: CABA,
GBA y provincia de Buenos Aires 33, Córdoba 11, Santa Fe 9, Mendoza 4, Salta 2, Chaco 2, Corrientes 2, Tucumán 1, Entre Ríos 1; 19 con
email de persona, 46 a casilla de área o de atención). Textos, nota y mensaje de LinkedIn por empresa en
[`envios/2026-10-07-software-ia-partners-2.md`](envios/2026-10-07-software-ia-partners-2.md); ficha en el `.csv` del mismo nombre.
Al enviarse: fila en esta tabla, fecha en "1.er envío" y estado `enviado`, 3 o 4 por hora (dos o tres días hábiles). **WhatsApp**: 29
de las 65 publican un número (buscado el 7-oct-2026; en "Otros canales" del `.md`, columna `whatsapp` del `.csv` y "Próxima acción");
canal pendiente, sin mensaje redactado. Avisos para revisar antes de enviar (iSource, Yugoo, Syloper, Snoop, Datawise, Human Tech 4.0,
encajes parciales, ciudades de directorios externos) en la sección "Para revisar antes de enviar" del `.md`. Reservas y descartes en
`scratch/prospectos/software-ia-2/notas_bsas.md` y `notas_interior.md`.

Tanda 3 de software e IA (partners), contactos 204 a 268, `canales4`: **enviados el 15-oct-2026 todos los que quedaban, hasta el #268** (59: las 65 sin los 6 descartados por 403; texto y asunto «Llamadas de voz» de la nota del 15-oct del `.md`; #213 y #214 rebotaron), seguimiento el 21-oct; no queda ninguno en borrador (65 empresas de toda Argentina: CABA 15,
GBA 6, Mar del Plata 1 y provincia de Buenos Aires sin ciudad publicada 8; Córdoba 11, Santa Fe 7, Mendoza 6, Neuquén 4, Río Negro 2,
Entre Ríos 2, Tucumán 1, Salta 1, La Pampa 1; 15 con email de persona, 50 a casilla de área o de atención). Textos, nota y mensaje de
LinkedIn por empresa en [`envios/2026-10-07-software-ia-partners-3.md`](envios/2026-10-07-software-ia-partners-3.md); ficha en el
`.csv` del mismo nombre. Al enviarse: fila en esta tabla, fecha en "1.er envío" y estado `enviado`, 3 o 4 por hora (dos o tres días
hábiles). **WhatsApp**: 25 de las 65 publican un número (buscado el 7-oct-2026; en "Otros canales" del `.md`, columna `whatsapp` del
`.csv` y "Próxima acción"); canal pendiente, sin mensaje redactado. Avisos para revisar antes de enviar (cargos no publicados de
Axioma IT, Hitofusion y MG Intelligence; ciudad sin verificar de Quantit y Silogik; partners sin IA publicada; C&S sin texto en el
sitio; WhatsApp de EE. UU. de TGV; seis sitios del interior leídos con user-agent de navegador; encajes parciales; nombres incompletos
en ★ de persona) en la sección "Para revisar antes de enviar" del `.md`. Reservas y descartes (Moment of People entre ellas) en
`scratch/prospectos/software-ia-3/bsas/notas_bsas.md` e `interior/notas_interior.md`.

**Partners 2 y 3, lo que queda (14-oct-2026):** se descartaron sin enviar, porque el sitio respondió 403, iSource (202), Yugoo (203),
Global Think (235), ERPYCA (251), Corpora (256), GoodComex (257), Patagonian (262) y Grupo Orange (267). Quedaban 60 en borrador
(Crenein, 201, y 204 a 268 sin los descartados). El 15-oct el texto y el asunto («Llamadas de voz») se reemplazaron en los `.md` de
las tandas (nota del 15-oct al principio de cada una), y `scratch/envios/2026-10-14-pendientes.html` se regeneró con
`scratch/envios/gen_pendientes.py`, idéntico a las tandas: el texto que va es el del `.md`. **15-oct:** salieron 54 ("enviado hasta el
#260"; #213 y #214 rebotaron) y después los 6 que quedaban (#261, 263, 264, 265, 266 y 268; "todos los mensajes enviados
hasta 268"): 60 en total, no queda ninguno en borrador.

**Envío del 14-oct-2026: cómo se registró.** El usuario avisó "enviados hasta #200; desde #187 a #200 cambié el asunto a
'Consulta'". Es la lectura de ese mensaje: el HTML de envío (`scratch/envios/2026-10-14-pendientes.html`) pone los 66
seguimientos antes de los primeros contactos, así que "hasta #200" se tomó como los 66 seguimientos más los primeros contactos
#179–200. Si no fue así, corregir las filas y este resumen. Los textos y asuntos tal como salieron están en
[`envios/2026-10-14-enviados.md`](envios/2026-10-14-enviados.md); los `.md` de cada tanda conservan los textos viejos.

**Rebotes (15-oct-2026).** Salen de la lista de supresiones de Resend que pasó el usuario (15 direcciones, todas `bounce`, del 2 al
15-oct; fecha de "Respuesta" en hora de Argentina, ninguna cambia de día). Resend no vuelve a mandar a una dirección suprimida: por eso los
seguimientos del 14-oct a Ithreex y Henka probablemente no salieron (confirmar en el log de Resend). 12 son casilla inexistente o
deshabilitada (definitivo); BIT (#174, 550 5.4.1 Access denied, Exchange Online) e Ithreex (#114, 503 No routes found) pueden ser de
configuración del destinatario. La casilla alternativa propuesta en cada "Próxima acción" sale de la tabla de emails de su tanda; el ★ del
`.md` y del `.csv` no se cambió.

### Prueba de asunto (14-oct-2026)

Primeros contactos a partners (`canales3`), mismo día y mismas variantes de texto; solo cambia el asunto. Comparar la tasa de
respuesta (respuestas sobre enviados, sin contar rebotes; una negativa cuenta como respuesta) cuando pasen los seguimientos del 20-oct. En "Contactos", los de la
prueba dicen `asunto «Consulta» (prueba)` en "1.er envío". Los clics son una señal más débil que la respuesta: un clic de
1 usuario puede ser el escáner del correo, y la referencia lleva 7 días contra 1 de la prueba y el control.

| Grupo | Contactos | Asunto | Enviados | Rebotes | Respuestas | Tasa | Clics (GA, al 15-oct) |
|---|---|---|---|---|---|---|---|
| Prueba | #187–200 | "Consulta" | 14 | 0 | 1 (Datawise, #191, 14-oct: no interesa, ya tienen la solución) | 7 % (parcial, al 14-oct) | 2 de 14 (Autologica y Blackfish, 1 usuario cada una), más Datawise (2 usuarios), que respondió |
| Control, mismo día | #179–186 | variantes con el nombre de la empresa ("Telefonía con IA para los clientes de X", "X: agentes de IA que atienden el teléfono", etc.) | 8 | 0 | — | — | 1 de 8 (EximIA, 1 usuario) |
| Referencia | #139–178 (8-oct) | "Voz y telefonía para los agentes de IA de X" | 40 | 2 (Biwares #139, BIT #174): 38 entregados | 2 (MINDO; AYI #175, por teléfono el 15-oct, después del seguimiento) | 5 % (parcial, al 15-oct) | 4 de 40 (AYI 4 usuarios, Mooving 3, Puntonet 2, Tecnom 2; Datawise es #191, del grupo de prueba) |
| Texto nuevo (15-oct) | #201, #204–268 sin los descartados por 403 (`canales3` y `canales4`) | "Llamadas de voz" | 60 | 2 (Cloud Solutions #213, HabSar #214): 58 entregados | — | — | 1 de 58 (C&S, #209, 1 usuario), a pocas horas del envío |

Reservas con email publicado, sin enviar (emails verificados el 5-oct-2026):

- Infotech (sistema de turnos HORAS): solo info@infotech.com.ar; no publican emails de personas.
- Estratega Software (software para cooperativas, Rosario): ★ mcattaneo@estrategasoftware.com.ar
  (Mariano Cattaneo, socio y presidente; catálogo 2015 del Polo Tecnológico Rosario, puede rebotar),
  ventas@estrategasoftware.com.ar (Wayback, 2018) y contactanos@estrategasoftware.com.ar (atención).

## Envíos según Resend (21-oct)

Historial completo de Resend (2 al 20-oct: 484 mails, 451 comerciales y 33 transaccionales), bajado el 21-oct a `scratch/resend/emails.json` (`scratch/resend/bajar.py`, key de `scratch/.resend-setup-key`: la de `.env` solo envía). Incluye lo que sale por Gmail desde laureano@atentina.com.ar, laureano@atentina.net y hola@atentina.net.

- **20-oct: ningún mail comercial.** Los seguimientos que figuraban para el 20-oct (#185, 187 y 198) no salieron; tampoco el de Mutual Bell (#68, "9-oct"). Último envío comercial: 19-oct (los 11 seguimientos por clic y el mail a Cristian Ventura, #227).
- **Con 3 mails (no mandarles más por mail; teléfono o LinkedIn):**
  - TGV #205 y C&S #209: «Consulta» el 14-oct, «Llamadas de voz» el 15-oct y seguimiento el 19-oct.
  - Gymzoft #300 y Clínica Online #294: el 1.er mail salió dos veces el 16-oct (8:46 y 10:30–10:43) y seguimiento el 19-oct.
  - Quanam #133, Infolytics #131, Widergy #128, Consultores en IT #119, ARTECH #117 y Freetech #104: el seguimiento del 14-oct salió dos veces (6:4x y 7:2x).
  - UCU y Unisem: el 1.er mail dos veces (UCU el 5-oct; Unisem el 5 y el 7-oct) y seguimiento el 14-oct.
- **Mismo 1.er mail dos veces el 16-oct:** Upfit, Nikao, Docsuite, Consultsmart, Educarf, Genube y Posit (rebotó las dos).
- **Dos primeros mails distintos** («Consulta» el 14-oct y «Llamadas de voz» el 15-oct): Appstract, Tekne Data Labs, Pigmalion, Mutt Data, Pipe y Crenein.
- **Fechas corregidas:** los seguimientos "del 15-oct" de #175, 154, 163, 67 y 44 salieron el 14-oct a las 6:4x desde hola@atentina.net (el de Mooving con asunto «RE: consulta»); solo el de #72 salió el 15-oct. #173 y 47 no salieron.
- **EVOL #94:** sin mails en Resend (el contacto fue solo por LinkedIn).

## LinkedIn

Canal aparte del email, para gente que ya conocemos (dueños, CTOs). Una fila por empresa y persona;
no cuenta en "Contactos enviados". Mismos estados que en "Cómo se llena" (sin `descartado` por rebote:
acá es `no acepta` si no aceptan la conexión). Máximo un seguimiento, ~4 días hábiles después.
Si la charla avanza, entra en "Conversaciones" como cualquier otra.

| # | Empresa | Rubro, lugar | Tipo | Persona, cargo | Vínculo | Perfil | Texto | Enviado | Seguimiento | Respuesta | Estado | Próxima acción |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L1 | Darwoft | Software a medida, Córdoba | canal (aliado/integración) | Christian Bullockes (verificar escritura), CTO | lo conoce el usuario | — | [`envios/2026-10-06-linkedin.md`](envios/2026-10-06-linkedin.md) | — | — | — | borrador | Enviar el mensaje (con el link con UTM `utm_source=linkedin`) y anotar la fecha |
| L2 | Neo Consultores S.A. | Software para mutuales y cooperativas, Rosario | canal | — | — | https://www.linkedin.com/company/80429658 | [`envios/2026-10-06-canales-a.md`](envios/2026-10-06-canales-a.md) | 6-oct | — | — | enviado | Seguimiento por LinkedIn el 13-oct (contacto #92) |
| L3 | Nexa Tech | Software para mutuales y cooperativas, Pergamino | canal | — | — | https://www.linkedin.com/company/nexatechok | [`envios/2026-10-06-canales-a.md`](envios/2026-10-06-canales-a.md) | 6-oct | — | — | enviado | Seguimiento por LinkedIn el 13-oct (contacto #93) |
| L4 | EVOL SRL | Software para mutuales y cooperativas, provincia de Buenos Aires | canal | — | — | https://www.linkedin.com/in/evol-srl-7b31a3105 | [`envios/2026-10-06-canales-a.md`](envios/2026-10-06-canales-a.md) | 6-oct | — | — | enviado | Seguimiento por LinkedIn el 13-oct (contacto #94) |
| L5 | Solsoft SRL | Software para mutuales y cooperativas, San Francisco | canal | — | — | https://www.linkedin.com/company/solsoftsrl | [`envios/2026-10-06-canales-a.md`](envios/2026-10-06-canales-a.md) | 6-oct | — | — | enviado | Seguimiento por LinkedIn el 13-oct (contacto #95) |
| L6 | RAS (Rent A Soft S.A.) | Software para salud, Godoy Cruz | canal | — | — | https://www.linkedin.com/products/ras-rent-a-soft-sa-ras-salud/ | [`envios/2026-10-06-canales-b.md`](envios/2026-10-06-canales-b.md) | 6-oct | — | — | enviado | Seguimiento por LinkedIn el 13-oct (contacto #97) |
| L7 | Grupo Cormos (DrApp) | Software para salud, CABA | canal | — | — | https://www.linkedin.com/company/grupocormos | [`envios/2026-10-06-canales-b.md`](envios/2026-10-06-canales-b.md) | 6-oct | — | — | enviado | Seguimiento por LinkedIn el 13-oct (contacto #98) |
| L8 | Integrando Salud | Software para salud, Leandro N. Alem | canal | Jaqueline Gutiérrez, encargada de partnership (contacto que pasaron) | — | https://www.linkedin.com/company/integrandosalud/ | [`envios/2026-10-06-canales-b.md`](envios/2026-10-06-canales-b.md) | 6-oct | — | 7-oct: derivan a Jaqueline Gutiérrez | respondió | Escribirle a Jaqueline hoy: presentación y charla de 15 min |
| L9 | Alephoo | Software para salud, Campana | canal | — | — | https://www.linkedin.com/company/10177982 | [`envios/2026-10-06-canales-b.md`](envios/2026-10-06-canales-b.md) | 6-oct | — | — | enviado | Seguimiento por LinkedIn el 13-oct (contacto #100) |
| L10 | Sanatorio Anchorena San Martín | Sanatorio, San Martín (GBA) | cliente | Marco David Andave, Jefe de atención al paciente - Supervisor de Hotelería | — | https://www.linkedin.com/sales/lead/ACwAACBFF1EB6NSJSTQ--CpOQHkuHXhky2C7m3I | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L11 | Sanatorio Sagrado Corazón | Sanatorio, CABA | cliente | Candice Selecki, Jefa de Gestión de Pacientes | — | https://www.linkedin.com/sales/lead/ACwAAB2VLqYBnoAPQ3drpJd1csAGFHxInyt0qbo | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L12 | Fundación Hospitalaria | Hospital, CABA | cliente | Felipe Saez, Jefe de Gestión en atención al paciente | — | https://www.linkedin.com/sales/lead/ACwAAA15-dIB4GU4_dmvsaM-OGyZuPFIE64v0VM | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L13 | ICBA Instituto Cardiovascular | Clínica cardiovascular, CABA | cliente | Silvina Stephani Ferradas, Jefa de Gestión Operativa de Pacientes | — | https://www.linkedin.com/sales/lead/ACwAAAdIsfABAalfXVtPgWAxIhLrin9FF_5wXHE | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L14 | IAF (Instituto Alexander Fleming) | Clínica oncológica, CABA | cliente | Diego Zentner, Jefe de contact center | — | https://www.linkedin.com/sales/lead/ACwAAAZwQnYBMlDOcmFHLuv4Y7ZbkhifpZ_kqTM | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L15 | Centro Médico Deragopyan | Diagnóstico por imágenes, CABA | cliente | Ornella Corigliano, Jefa de Atención al paciente | — | https://www.linkedin.com/sales/lead/ACwAAD7Za3oBvSh_fyjhZBc4hiqqBmQiFOdE6OI | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L16 | ARGUS Diagnóstico Médico | Diagnóstico por imágenes, GBA norte | cliente | Agustina Jiménez, Coordinadora de la central única de turnos | — | https://www.linkedin.com/sales/lead/ACwAAC0FKXMBm8wJSPP-uw1xFbUF9A10q_ww0nk | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L17 | Labmedicina | Laboratorio, — | cliente | Delia Benítez, Jefa de hospitales - Atención al cliente | — | https://www.linkedin.com/sales/lead/ACwAAAqGzowBJgmFv1thIEiu2bOQDTFZaTlYE8o | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L18 | Cibic Laboratorios (Rosario) | Laboratorio, Rosario y Funes | cliente | Lucio Caneda, Responsable de Experiencia del Usuario | — | https://www.linkedin.com/sales/lead/ACwAABhbGl4Bd49JIJwRZWf-UgBf_nu5SfF2wOI | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L19 | Vacunar | Vacunatorios, — | cliente | Fernanda Rojas, Coordinadora de atención al paciente | — | https://www.linkedin.com/sales/lead/ACwAABhLXEABDIaNM9j7MgNsSGoibz-oyL7m0_g | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L20 | Clínica San Camilo | Clínica, CABA | cliente | Luis Cervio, Director general | — | https://www.linkedin.com/sales/lead/ACwAAAr4MoABX2RZUcW-n-Jwab2XrevJZcehP00 | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L21 | Sanatorio Anchorena Recoleta | Sanatorio, CABA | cliente | Francisco Longo, Director general | — | https://www.linkedin.com/sales/lead/ACwAABkdfg8BBUKT23K-HCo-lJRFGxoXLJtjuxs | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L22 | Sanatorio Colegiales | Sanatorio, CABA | cliente | Eduardo Zalis, Director | — | https://www.linkedin.com/sales/lead/ACwAAASfFWUBsF-MJEjFRSsKMSMzcipK9Ci-FMg | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L23 | Sanatorio Juncal | Sanatorio, Temperley (GBA) | cliente | Diego Marucco, Gerente General | — | https://www.linkedin.com/sales/lead/ACwAAAh_HgkBG4bRfsRMqjd2JbGOh2T1tKCP53k | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L24 | Sanatorio del Oeste | Sanatorio, GBA oeste | cliente | Pablo Marucho, Director Médico Ejecutivo | — | https://www.linkedin.com/sales/lead/ACwAAEHH8WoBenA2BFf7swBq-H9MjS_huh-zfrM | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L25 | Sanatorio Clínica Modelo de Morón | Sanatorio, Morón (GBA) | cliente | Gustavo Borello, Director médico (sustituye al ★ original, José Luis Leone: su cargo real ahí es Coordinador de Docencia e Investigación, no decisor) | — | https://www.linkedin.com/sales/lead/ACwAAE0UnJ4BAtPM0N8jmQ8FoAceCwxgvmHhCUk | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L26 | Sanatorio Modelo Quilmes | Sanatorio, Quilmes (GBA) | cliente | Guillermo Malah, Gerente de Abastecimiento y Director | — | https://www.linkedin.com/sales/lead/ACwAAAKaCXMBU0HAtMJaBlS-AA0gJtrYOQOMd9M | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L27 | Clínica Adventista Belgrano | Clínica, CABA | cliente | Milton Rodríguez Müller, Director médico | — | https://www.linkedin.com/sales/lead/ACwAADmLAEMBAGQTrOZk-ypnN4UFwjAJUhQIeR8 | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L28 | Clínica Universitaria Reina Fabiola (Córdoba) | Clínica universitaria, Córdoba | cliente | María Belén Jávega, Gerente de Calidad y Operaciones | — | https://www.linkedin.com/sales/lead/ACwAAAhP9sUBr3UJHzPk8on6k6bNhQff1sD6jak | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |
| L29 | DIM Centros de Salud | Red de +15 centros, GBA oeste y CABA | cliente | Oscar Montaña, Director General | — | https://www.linkedin.com/sales/lead/ACwAAALH4SABJUyV9dgKDEETh873Ah-497q4rtE | [`envios/2026-10-07-linkedin-salud.md`](envios/2026-10-07-linkedin-salud.md) | 7-oct | — | — | enviado | Seguimiento el 13-oct (el 12 es feriado) |

**Sanatorio Británico (Rosario), sin enviar:** los dos contactos de la tanda (★ Lourdes Vázquez, 2.º Isabel
Iberbuden) resuelven en Sales Navigator a personas en Asunción, Paraguay, no a Rosario — probablemente el
buscador tomó otro "Sanatorio Británico" (hay uno en Paraguay). No se envió ninguna invitación a esta cuenta;
falta rehacer la búsqueda de contactos antes de retomarla.

Los mensajes L2 a L9 (6-oct) salieron **sin UTM**: sus visitas aparecen en GA como fuente `linkedin.com` / `lnkd.in`
(canal Organic Social), sin la empresa. Para atribuirlas, cruzar fecha, hora y ciudad (Explorar).

Link con UTM: `https://atentina.com.ar?utm_source=linkedin&utm_campaign=linkedin&utm_content=<empresa>`
(mismo reporte de Google Analytics que en "Links con UTM", se ve por fuente `linkedin`).

## Links con UTM

Desde la segunda tanda, el link de cada mail lleva `?utm_source=email&utm_campaign=<tanda>&utm_content=<empresa>`.
En Google Analytics: Informes → Adquisición → Adquisición de tráfico, con la dimensión secundaria
"Contenido del anuncio de la sesión manual" (`utm_content`) o "Campaña de la sesión" (`utm_campaign`).
Mide visitas al sitio y, con los eventos de [`../LANDING.md`](../../docs/LANDING.md), si probaron la demo; no mide aperturas.
El primer envío a los contactos 1 a 11 (2-oct) salió sin UTM; el segundo lleva `utm_campaign=tanda1b`.

**Seguimientos (desde el 14-oct-2026):** el link lleva `utm_campaign=follow_up_<campaña original con "_" antes del número>`
y el mismo `utm_content` de la tabla; así se separan las visitas del seguimiento de las del primer mail.

| Campaña del seguimiento | Campaña original | Contactos | Cantidad | Enviado |
|---|---|---|---|---|
| follow_up_tanda_2 | tanda2 | #12–21 | 10 | 14-oct |
| follow_up_tanda_3 | tanda3 | #22–41 | 20 | 14-oct |
| follow_up_canales_1 | canales1 | #96, 101–105, 107, 108, 110, 111 | 10 | 14-oct |
| follow_up_canales_2 | canales2 | #112–138 sin #130 | 26 | 14-oct |
| follow_up_canales_3 | canales3 | #154, 163, 173, 175 | 4 | 15-oct |
| follow_up_tanda_4 | tanda4 | #44, 47 | 2 | 15-oct |
| follow_up_tanda_5 | tanda5 | #67, 72 | 2 | 15-oct |
| follow_up_canales_4 | canales4 | #205, 209, 224, 227, 230, 252 | 6 | 19-oct |
| follow_up_canales_5 | canales5 | #287 | 1 | 19-oct |
| follow_up_canales_6 | canales6 | #294, 300, 319, 333 | 4 | 19-oct |
| follow_up_canales_3_charla | canales3 | #175 | 1 | borrador para el 21-oct (después de la charla del 15-oct) |

**Seguimiento después de una charla:** `utm_campaign=follow_up_<campaña original>_charla`, mismo `utm_content`; así se separa de las visitas del seguimiento en frío.

**Los 41 mails del 5-oct (`tanda1b`, `tanda2`, `tanda3`) salieron con el link mal armado** (error de
`scripts/mercado/envio_html.py`, corregido el 5-oct): el `&` quedó como `&amp;`, así que a GA llega `utm_source=email`
pero campaña y contenido llegan como parámetros `amp;utm_campaign` y `amp;utm_content`. Para encontrarlos: Explorar →
dimensión "Ubicación de la página" (`page_location`) que contenga `utm_content=<empresa>`. Desde la tanda 4 el link va bien.

| # | Empresa | utm_campaign | utm_content |
|---|---|---|---|
| 1 | Instituto Oulton | tanda1b | oulton |
| 2 | Cooperativa de Electricidad Bariloche (CEB) | tanda1b | ceb |
| 3 | AMUR (Asociación Mutual Ruralista) | tanda1b | amur |
| 4 | MIS – Mutual Integral de Servicios | tanda1b | mis |
| 5 | ISEP (Instituto ISEP) | tanda1b | isep |
| 6 | GestarCoop | tanda1b | gestarcoop |
| 7 | Alianza Cobros | tanda1b | alianza-cobros |
| 8 | Paktar Cobranzas & BPO | tanda1b | paktar |
| 9 | Yacoub | tanda1b | yacoub |
| 10 | Grupo Silva (Silva Mobility) | tanda1b | grupo-silva |
| 11 | Browix | tanda1b | browix |
| 12 | Cotesma (Cooperativa Telefónica de San Martín de los Andes) | tanda2 | cotesma |
| 13 | Sanatorio El Carmen | tanda2 | sanatorio-el-carmen |
| 14 | Unisem | tanda2 | unisem |
| 15 | Municipalidad de Trelew | tanda2 | trelew |
| 16 | UCU (Universidad de Concepción del Uruguay) | tanda2 | ucu |
| 17 | Aulica (Netbel) | tanda2 | aulica |
| 18 | Fiter | tanda2 | fiter |
| 19 | USS | tanda2 | uss |
| 20 | Río Uruguay | tanda2 | rio-uruguay |
| 21 | El Norte Seguros | tanda2 | el-norte-seguros |
| 22 | Laboratorio D'Agostino-Bruno | tanda3 | dagostino-bruno |
| 23 | IACA Laboratorios | tanda3 | iaca |
| 24 | SIMEPA | tanda3 | simepa |
| 25 | Consulmed | tanda3 | consulmed |
| 26 | Eoftalmo | tanda3 | eoftalmo |
| 27 | Municipalidad de Goya | tanda3 | goya |
| 28 | CPE (Cooperativa Popular de Electricidad de Santa Rosa) | tanda3 | cpe |
| 29 | Cooperativa 16 de Octubre (Coop16) | tanda3 | coop16 |
| 30 | CELTA (Cooperativa Eléctrica de Tres Arroyos) | tanda3 | celta |
| 31 | COTEL (Cooperativa Telefónica y Otros Servicios de Villa Gesell) | tanda3 | cotel |
| 32 | Elebar (Santa Mónica S.A.) | tanda3 | elebar |
| 33 | Empresur S.A. (Tarjeta Qida) | tanda3 | qida |
| 34 | Tarjeta Sucrédito (Valle Fértil S.A.) | tanda3 | sucredito |
| 35 | Gran Cooperativa (Grancoop) | tanda3 | grancoop |
| 36 | Derka y Vargas S.A. | tanda3 | derka-vargas |
| 37 | Instituto Superior Juan XXIII (Obra de Don Bosco) | tanda3 | juan23 |
| 38 | Colegio Belgrano | tanda3 | colegio-belgrano |
| 39 | NeyTI SAS | tanda3 | neyti |
| 40 | Censys S.A. | tanda3 | censys |
| 41 | SISA (Sisa Latam) | tanda3 | sisa |
| 42 | Mutual MAS (empleados del Ministerio de Acción Social) | tanda4 | mutual-mas |
| 43 | Mutual de Empleados del Banco de la Provincia de Córdoba (AMEBPC) | tanda4 | amebpc |
| 44 | Asociación Mutualista del Docente (AMD) | tanda4 | amd |
| 45 | Mutual de Empleados de la Policía de Córdoba (AMEPPC) | tanda4 | ameppc |
| 46 | Círculo de Suboficiales y Agentes, Mutual Policía de Córdoba | tanda4 | circulo-policia |
| 47 | Mutual Celesol (Red Unisol) | tanda4 | celesol |
| 48 | Asociación Mutualista Argentina Nueva (AMAN) | tanda4 | aman |
| 49 | Asociación Mutual Conexo | tanda4 | conexo |
| 50 | Asociación Mutual La Mediterránea | tanda4 | la-mediterranea |
| 51 | Asociación Mutual Carlos Mugica | tanda4 | carlos-mugica |
| 52 | AMMA (Asociación Mutual Mercantil Argentina) | tanda4 | amma |
| 53 | Mutual Sudecor | tanda4 | sudecor |
| 54 | AMA (Asociación Mutual Arroyito) | tanda4 | ama-arroyito |
| 55 | Mutual COYSPU | tanda4 | coyspu |
| 56 | Mutual Club Jorge Newbery | tanda4 | newbery |
| 57 | Mutual VGB | tanda4 | mutual-vgb |
| 58 | AMCeP (Asociación Mutual del Centro de Punilla) | tanda4 | amcep |
| 59 | Mutual Sportivo Belgrano | tanda4 | sportivo-belgrano |
| 60 | Asociación Mutual 22 de Septiembre | tanda4 | 22-septiembre |
| 61 | Mutual Club Atlético Santa Rosa | tanda4 | atletico-santa-rosa |
| 62 | Mutual 9 de Julio (Mutual de Asociados de la Asociación Deportiva 9 de Julio) | tanda5 | 9dejulio-morteros |
| 63 | Mutual Almafuerte (Asociación Mutual del Club Almafuerte de Las Varillas) | tanda5 | almafuerte |
| 64 | Mutual Unión (A. M. de Asociados del Club Atlético Unión) | tanda5 | mutual-union |
| 65 | Mutual 9 de Julio Olímpico (A. M. 9 de Julio Olímpico Freyre) | tanda5 | 9dejulio-freyre |
| 66 | Mutual Sportivo San Jorge y Centro Juvenil Milmar | tanda5 | san-jorge-milmar |
| 67 | Mutual TOJU | tanda5 | toju |
| 68 | Asociación Mutual Bell | tanda5 | mutual-bell |
| 69 | Lambert Mutual (Tarjeta Monte Maíz) | tanda5 | lambert |
| 70 | Mutual de Asociados de Justiniano Posse | tanda5 | asociados-jposse |
| 71 | Mutual del Independiente Foot Ball Club (Pascanas) | tanda5 | independiente-pascanas |
| 72 | Sporting Club Mutual Social, Deportivo, Cultural y Biblioteca | tanda5 | sporting-corral |
| 73 | Mutual Metropolitana | tanda5 | metropolitana |
| 74 | Mutual de Asociados del Club Atlético San Carlos | tanda5 | san-carlos-surgentes |
| 75 | Club Atlético Social Corralense A. M. | tanda5 | corralense |
| 76 | Mutual de Asociados del Club Atlético San Martín (Monte Buey) | tanda5 | san-martin-monte-buey |
| 77 | Mutual de las Comunidades | tanda5 | comunidades |
| 78 | Mutual Soberanía | tanda5 | soberania |
| 79 | Mutual de Asociados del Club Atlético Atenas | tanda5 | atenas-ucacha |
| 80 | Mutual del Personal Civil Taller Regional Río Cuarto | tanda5 | pctr-rio-cuarto |
| 81 | Sociedad Italiana de Socorros Mutuos Puerta Pía | tanda5 | italiana-rio-cuarto |
| 82 | Mutual Oncativo (A. M. Oncativo de Socios y Adherentes del Club Deportivo y Cultural Unión) | tanda5 | oncativo |
| 83 | Asociación Mutual Médica de Villa María (SOS Salud) | tanda5 | sos-salud |
| 84 | Sociedad Italiana de Socorros Mutuos "Italia Unida" | tanda5 | italia-unida |
| 85 | AMISVIMA (Asociación Mutual Integración Solidaria Villa María) | tanda5 | amisvima |
| 86 | Sociedad Italiana de Socorros Mutuos Social, Cultural y Deportiva "Roma" | tanda5 | italiana-vdr |
| 87 | AMCeCIS (Asociación Mutual del Centro Comercial, Industrial y de Servicios de Río Tercero) | tanda5 | amcecis |
| 88 | AMECOL (Asociación Mutualista de Empleados de Comercio de Laboulaye) | tanda5 | amecol |
| 89 | Asociación Mutual Empleados Municipales de Río Tercero y Zona | tanda5 | municipales-rio-tercero |
| 90 | Asociación Mutual del Centro Comercial de Hernando | tanda5 | centro-comercial-hernando |
| 91 | Asociación Mutual del Centro Comercial e Industrial de Tancacha | tanda5 | cci-tancacha |
| 92 | Neo Consultores S.A. | canales1 | neo-consultores |
| 93 | Nexa Tech | canales1 | nexa |
| 94 | EVOL SRL | canales1 | evol |
| 95 | Solsoft SRL | canales1 | solsoft |
| 96 | Kernel Informática | canales1 | kernel |
| 97 | RAS (Rent A Soft S.A.) | canales1 | ras |
| 98 | Grupo Cormos (DrApp) | canales1 | cormos |
| 99 | Integrando Salud | canales1 | integrando-salud |
| 100 | Alephoo | canales1 | alephoo |
| 101 | Tekhne S.A. | canales1 | tekhne |
| 102 | Engage SC (Soluciones Tecnológicas S.A.) | canales1 | engage |
| 103 | Teleprom (Teleprom Argentina S.A.) | canales1 | teleprom |
| 104 | Freetech Solutions (Telecomunicaciones Unificadas SRL), OMniLeads | canales1 | freetech |
| 105 | TecnoVoz (Tecno Voz Noroeste S.A.) | canales1 | tecnovoz |
| 106 | Yoizen (Yoizen S.A.) | canales1 | yoizen |
| 107 | Chatsell | canales1 | chatsell |
| 108 | Origami Software | canales1 | origami |
| 109 | Raptiv | canales1 | raptiv |
| 110 | Etixen | canales1 | etixen |
| 111 | StorySelling | canales1 | storyselling |
| 112 | Kunan | canales2 | kunan |
| 113 | Aionixs | canales2 | aionixs |
| 114 | Ithreex Global | canales2 | ithreex |
| 115 | Crombie | canales2 | crombie |
| 116 | NeuralSoft | canales2 | neuralsoft |
| 117 | ARTECH | canales2 | artech |
| 118 | AGOS | canales2 | agos |
| 119 | Consultores en IT S.A. | canales2 | consultores-en-it |
| 120 | Cumbresoft | canales2 | cumbresoft |
| 121 | Dicsys | canales2 | dicsys |
| 122 | Ecosistemas Global | canales2 | ecosistemas |
| 123 | Exomindset | canales2 | exomindset |
| 124 | JEMER | canales2 | jemer |
| 125 | KINETIC Corp | canales2 | kinetic |
| 126 | Making Sense | canales2 | makingsense |
| 127 | Holon Software | canales2 | holon |
| 128 | Widergy | canales2 | widergy |
| 129 | Devlights | canales2 | devlights |
| 130 | Nybble Group | canales2 | nybble |
| 131 | Infolytics | canales2 | infolytics |
| 132 | GMO Solutions | canales2 | gmo |
| 133 | Quanam | canales2 | quanam |
| 134 | Henka (Digital Henka) | canales2 | henka |
| 135 | Accuratio | canales2 | accuratio |
| 136 | FutureFlow | canales2 | futureflow |
| 137 | Brain Food | canales2 | brainfood |
| 138 | Sinnetic | canales2 | sinnetic |
| 139 | Biwares | canales3 | biwares |
| 140 | Duotach | canales3 | duotach |
| 141 | Quilsoft | canales3 | quilsoft |
| 142 | BamAI | canales3 | bamai |
| 143 | AIViento | canales3 | aiviento |
| 144 | Bombieri | canales3 | bombieri |
| 145 | booleAr S.A. | canales3 | boolear |
| 146 | Grupo Esfera | canales3 | grupoesfera |
| 147 | Eryx | canales3 | eryx |
| 148 | 7Puentes | canales3 | 7puentes |
| 149 | Accion Point | canales3 | accionpoint |
| 150 | Medve | canales3 | medve |
| 151 | Unitech | canales3 | unitech |
| 152 | Xelere | canales3 | xelere |
| 153 | QActions | canales3 | qactions |
| 154 | Mooving (Mooving Tech S.A.U.) | canales3 | mooving |
| 155 | OneInfo Consulting | canales3 | oneinfo |
| 156 | Kopernicus | canales3 | kopernicus |
| 157 | Innen | canales3 | innen |
| 158 | Zarego | canales3 | zarego |
| 159 | 404 // Software crafters | canales3 | 404 |
| 160 | Grupo Kelsoft | canales3 | kelsoft |
| 161 | Infogestión | canales3 | infogestion |
| 162 | Julasoft | canales3 | julasoft |
| 163 | Tecnom | canales3 | tecnom |
| 164 | Quales Group | canales3 | quales |
| 165 | Snoop Consulting | canales3 | snoop |
| 166 | BlueDraft | canales3 | bluedraft |
| 167 | Avalith | canales3 | avalith |
| 168 | Aoki Tech | canales3 | aoki |
| 169 | MINDO | canales3 | mindo |
| 170 | NexoSmart | canales3 | nexosmart |
| 171 | VGS | canales3 | vgs |
| 172 | Vortex | canales3 | vortex |
| 173 | Puntonet Tech (Punto Net Soluciones SRL) | canales3 | puntonet |
| 174 | BIT S.A. | canales3 | bit |
| 175 | AYI Group (BADI S.A.) | canales3 | ayi |
| 176 | Peperina Software | canales3 | peperina |
| 177 | Skater Elephant (Resolution 8 Software SAS) | canales3 | skaterelephant |
| 178 | Digital Motus | canales3 | digitalmotus |
| 179 | Vippinn | canales3 | vippinn |
| 180 | Ascentio Technologies | canales3 | ascentio |
| 181 | HMM Global (Home Medical Management) | canales3 | hmm |
| 182 | Asofix (Grupo Tagle) | canales3 | asofix |
| 183 | Syloper | canales3 | syloper |
| 184 | Santa Fe Sistemas (Grupo SFS) | canales3 | sfs |
| 185 | EximIA Solutions (Technology Service SAS) | canales3 | eximia |
| 186 | Human Tech 4.0 (Business Buggers SRL) | canales3 | humantech |
| 187 | Autologica | canales3 | autologica |
| 188 | Kodear | canales3 | kodear |
| 189 | Efficast | canales3 | efficast |
| 190 | Nonlinear Tecnología | canales3 | nonlinear |
| 191 | Datawise | canales3 | datawise |
| 192 | Midas Consultores | canales3 | midas |
| 193 | Merovingian Data | canales3 | merovingian |
| 194 | Quinto Impacto | canales3 | quintoimpacto |
| 195 | Axis Human (Inamika Interactive S.A.) | canales3 | axishuman |
| 196 | Griftin (Área Clave Consultoría Estratégica SRL) | canales3 | griftin |
| 197 | MBM Sistemas | canales3 | mbm |
| 198 | Blackfish Argentina | canales3 | blackfish |
| 199 | Devoo | canales3 | devoo |
| 200 | Sudata | canales3 | sudata |
| 201 | Crenein | canales3 | crenein |
| 202 | iSource | canales3 | isource |
| 203 | Yugoo | canales3 | yugoo |
| 204 | Pipe Tech | canales4 | pipe-tech |
| 205 | TGV | canales4 | tgv |
| 206 | Mutt Data | canales4 | muttdata |
| 207 | Pigmalion Software | canales4 | pigmalion |
| 208 | Tekne Data Labs | canales4 | tekne-data-labs |
| 209 | C&S Informática | canales4 | cys |
| 210 | Appstract | canales4 | appstract |
| 211 | IT Maker | canales4 | it-maker |
| 212 | Big Data Estratégico | canales4 | big-data-estrategico |
| 213 | Cloud Solutions LATAM | canales4 | cloud-solutions-latam |
| 214 | HabSar | canales4 | habsar |
| 215 | Axcelere | canales4 | axcelere |
| 216 | Blueorange Group | canales4 | blueorange |
| 217 | Axioma IT Solutions | canales4 | axioma-it |
| 218 | Hitofusion (Yügo SAS) | canales4 | hitofusion |
| 219 | MG Intelligence | canales4 | mg-intelligence |
| 220 | Chroma Agency | canales4 | chroma |
| 221 | ITBS Business Solutions | canales4 | itbs |
| 222 | Sysmo | canales4 | sysmo |
| 223 | RockingData | canales4 | rockingdata |
| 224 | Accedra | canales4 | accedra |
| 225 | BGlobal Solutions | canales4 | bglobal |
| 226 | PositiveIT | canales4 | positiveit |
| 227 | Zennon BI | canales4 | zennon |
| 228 | GrowIT | canales4 | growit |
| 229 | Quantit | canales4 | quantit |
| 230 | Silogik | canales4 | silogik |
| 231 | Proda Software | canales4 | proda |
| 232 | Datcom Software | canales4 | datcom |
| 233 | Potencia Technologies | canales4 | potencia-tech |
| 234 | GiGa Global | canales4 | giga-global |
| 235 | Global Think Technology | canales4 | global-think |
| 236 | Mindfactory | canales4 | mindfactory |
| 237 | Program Consultores (PGM) | canales4 | program-consultores |
| 238 | Emser | canales4 | emser |
| 239 | DinoCloud | canales4 | dinocloud |
| 240 | Vatrox | canales4 | vatrox |
| 241 | Olpa Group | canales4 | olpa-group |
| 242 | Castelsoft | canales4 | castelsoft |
| 243 | Dynetis | canales4 | dynetis |
| 244 | Glowix / Neos Tech | canales4 | glowix-neos |
| 245 | Psiware | canales4 | psiware |
| 246 | Idear Tech | canales4 | idear-tech |
| 247 | Inteligencia Analítica | canales4 | inteligencia-analitica |
| 248 | Grupo Aicon | canales4 | grupo-aicon |
| 249 | Alchemid | canales4 | alchemid |
| 250 | M3C Software | canales4 | m3c |
| 251 | ERPYCA | canales4 | erpyca |
| 252 | devFactory | canales4 | devfactory |
| 253 | Solutions Hub / AGP & ROD Servicios | canales4 | solutions-hub |
| 254 | Alpardata | canales4 | alpardata |
| 255 | Hexium Software Factory | canales4 | hexium |
| 256 | Corpora | canales4 | corpora |
| 257 | GoodComex (Full Comex SAS) | canales4 | goodcomex |
| 258 | Solution IT (SIT) | canales4 | solution-it |
| 259 | PuntoGap | canales4 | puntogap |
| 260 | Pragmática Consultores | canales4 | pragmatica |
| 261 | DITyC | canales4 | dityc |
| 262 | Patagonian | canales4 | patagonian |
| 263 | Waiki Consultores en Sistemas | canales4 | waiki |
| 264 | Ingenio Solutions | canales4 | ingenio-solutions |
| 265 | Quay | canales4 | quay |
| 266 | Tecopens Consulting | canales4 | tecopens |
| 267 | Grupo Orange | canales4 | grupo-orange |
| 268 | Grupo Mill | canales4 | grupo-mill |
| 272 | NexHub | canales5 | nexhub |
| 273 | Wynges (Líder Gestión ERP) | canales5 | lidergestion |
| 274 | GestorUno | canales5 | gestoruno |
| 275 | Tribot ERP | canales5 | tribot |
| 276 | CG Software | canales5 | cg-software |
| 277 | iCOMM | canales5 | icomm |
| 278 | Prysma Software (MiGestion) | canales5 | prysma |
| 279 | KM44 | canales5 | km44 |
| 280 | Aguazul Sistemas (MyEstudio) | canales5 | myestudio |
| 281 | Estudio Digital | canales5 | estudio-digital |
| 282 | Contala | canales5 | contala |
| 283 | ConsorcioSimple | canales5 | consorciosimple |
| 284 | Kavanagh Group (Kavanagh Cloud) | canales5 | kavanagh |
| 285 | Octopus | canales5 | octopus |
| 286 | JUDICO | canales5 | judico |
| 287 | Estudio360 | canales5 | estudio360 |
| 288 | RivoLegal | canales5 | rivolegal |
| 289 | Themis | canales5 | themis |
| 290 | AgroGi (CampoGi) | canales5 | agrogi |
| 291 | America GIS (AGIS Agro) | canales5 | america-gis |
| 292 | GENUBE | canales6 | genube |
| 293 | EDUCARF | canales6 | educarf |
| 294 | Clínica Online | canales6 | clinica-online |
| 295 | ConsultSmart | canales6 | consultsmart |
| 296 | DocSuite | canales6 | docsuite |
| 297 | POSIT | canales6 | posit |
| 298 | Nikao | canales6 | nikao |
| 299 | Upfit | canales6 | upfit |
| 300 | Gymzoft | canales6 | gymzoft |
| 301 | Gympas | canales6 | gympas |
| 302 | Oliauto | canales6 | oliauto |
| 303 | Frontera Sistemas (Antares 86) | canales6 | frontera-sistemas |
| 304 | Valbará (TMS) | canales6 | valbara |
| 305 | FonteSoft (TMS) | canales6 | fontesoft |
| 306 | CRISTAL+ | canales6 | cristal |
| 307 | Nousaris | canales6 | nousaris |
| 308 | e-Sueldos | canales6 | e-sueldos |
| 309 | Sueldos Net | canales6 | sueldosnet |
| 310 | GestiónClub | canales6 | gestionclub |
| 311 | Onix (SIRF) | canales6 | onix |
| 312 | AlfaBeta (Winfarma) | canales6 | winfarma |
| 313 | SiCoFa | canales6 | sicofa |
| 314 | OpenPlus | canales6 | openplus |
| 315 | Gestión Comercio | canales6 | gestion-comercio |
| 316 | enorden | canales6 | enorden |
| 317 | Creadores de Soft | canales6 | creadores-de-soft |
| 318 | Aturna VET | canales6 | aturna-vet |
| 319 | Denteo | canales6 | denteo |
| 320 | Dentry | canales6 | dentry |
| 321 | Agroconexiones | canales6 | agroconexiones |
| 322 | Legio | canales6 | legio |
| 323 | Sauce Gestión | canales6 | sauce-gestion |
| 324 | Facturarg | canales6 | facturarg |
| 325 | Orion Sistemas | canales6 | orion |
| 326 | Staciona | canales6 | staciona |
| 327 | AdminParking | canales6 | adminparking |
| 328 | Visionsoft | canales6 | visionsoft |
| 329 | Fudo | canales6 | fudo |
| 330 | Maxirest | canales6 | maxirest |
| 331 | ClinIA | canales6 | clinia |
| 332 | iNOTARY | canales6 | inotary |
| 333 | Fixa (Mutual Core) | canales6 | fixa |
| 334 | SINADY | canales6 | sinady |
| 335 | Flota360 | canales6 | flota360 |
| 336 | Power System (idata) | canales6 | powersystem |
| 337 | MeSumo | canales6 | mesumo |
| 338 | ProCurva | canales6 | procurva |
| 339 | Total Stock | canales6 | total-stock |
| 340 | Aumo | canales6 | aumo |
| 341 | Qontabiliza | canales6 | qontabiliza |

## Clics en el link (Google Analytics)

Visitas a la landing con la UTM de cada mail, acumuladas hasta la fecha del dato (Explorar de GA, `utm_campaign` / `utm_content`,
las pasó el usuario). Las dos métricas se asumen **usuarios y sesiones** (a confirmar en GA). Una fila por campaña y contenido: el
primer mail y el seguimiento van por separado y no se suman, porque el mismo usuario puede estar en las dos.

- **Un clic de 1 usuario y 1 sesión puede ser el escáner del correo** (Safe Links de Microsoft y similares abren los links al
  recibir el mail). Varios usuarios o varias sesiones son una señal más firme.
- **No mencionar el clic al contactar.** Sirve para elegir a quién insistir y por qué canal, no como tema del mensaje.
- Al actualizar: filas nuevas con su fecha del dato; no se pisan las anteriores.
- **Dato del 21-oct:** el reporte trae usuarios activos y **eventos** (no sesiones): en esas filas la columna "Sesiones" lleva los eventos (`ev.`), que no se comparan con las sesiones del 15-oct. No trae a COTEL, AMD, Celesol, Sporting ni Mutual Bell (puede ser filtro del reporte). Los que hicieron clic y entraron a una tanda de seguimiento están en [`envios/2026-10-19-seguimientos-ga.md`](envios/2026-10-19-seguimientos-ga.md) (agregados del 21-oct al final).

| # | Empresa | Campaña / contenido | Usuarios | Sesiones | Fecha del dato | Nota |
|---|---|---|---|---|---|---|
| 119 | Consultores en IT | canales2 / consultores-en-it | 7 | 7 | 15-oct | prioridad alta |
| 119 | Consultores en IT | follow_up_canales_2 / consultores-en-it | 2 | 2 | 15-oct | prioridad alta |
| 117 | ARTECH | canales2 / artech | 3 | 3 | 15-oct | prioridad alta |
| 117 | ARTECH | follow_up_canales_2 / artech | 4 | 4 | 15-oct | prioridad alta |
| 137 | Brain Food | canales2 / brainfood | 4 | 4 | 15-oct | prioridad alta |
| 175 | AYI Group | canales3 / ayi | 4 | 7 | 15-oct | charla hecha el 15-oct (seguimiento enviado el mismo día) |
| 94 | EVOL SRL | canales1 / evol | 3 | 3 | 15-oct | el mail figura como no enviado (borrador; salió por LinkedIn, L4, que iba sin UTM): confirmar si el mail salió o si el mensaje de LinkedIn llevaba este link |
| 131 | Infolytics | canales2 / infolytics | 3 | 3 | 15-oct | — |
| 131 | Infolytics | follow_up_canales_2 / infolytics | 1 | 1 | 15-oct | — |
| 133 | Quanam | canales2 / quanam | 3 | 3 | 15-oct | — |
| 133 | Quanam | follow_up_canales_2 / quanam | 1 | 1 | 15-oct | — |
| 128 | Widergy | canales2 / widergy | 3 | 4 | 15-oct | — |
| 154 | Mooving | canales3 / mooving | 3 | 3 | 15-oct | seguimiento enviado el 15-oct |
| 191 | Datawise | canales3 / datawise | 2 | 2 | 15-oct | respondió: no interesa |
| 173 | Puntonet Tech | canales3 / puntonet | 2 | 2 | 15-oct | seguimiento: no salió (Resend), borrador del 21-oct |
| 163 | Tecnom | canales3 / tecnom | 2 | 2 | 15-oct | seguimiento enviado el 15-oct |
| 67 | Mutual TOJU | tanda5 / toju | 2 | 3 | 15-oct | seguimiento enviado el 15-oct |
| 107 | Chatsell | canales1 / chatsell | 1 | 1 | 15-oct | — |
| 104 | Freetech Solutions | canales1 / freetech | 1 | 1 | 15-oct | — |
| 109 | Raptiv | canales1 / raptiv | 1 | 6 | 15-oct | charla hecha |
| 106 | Yoizen | canales1 / yoizen | 1 | 1 | 15-oct | respondió |
| 187 | Autologica | canales3 / autologica | 1 | 1 | 15-oct | prueba de asunto, «Consulta» |
| 198 | Blackfish Argentina | canales3 / blackfish | 1 | 1 | 15-oct | prueba de asunto, «Consulta» |
| 185 | EximIA Solutions | canales3 / eximia | 1 | 1 | 15-oct | prueba de asunto, control |
| 209 | C&S Informática | canales4 / cys | 1 | 1 | 15-oct | enviado el 15-oct |
| 31 | COTEL | follow_up_tanda_3 / cotel | 1 | 2 | 15-oct | — |
| 44 | AMD | tanda4 / amd | 1 | 1 | 15-oct | seguimiento enviado el 15-oct |
| 47 | Mutual Celesol | tanda4 / celesol | 1 | 2 | 15-oct | seguimiento enviado (varias tandas, según el usuario) |
| 72 | Sporting Club Mutual | tanda5 / sporting-corral | 1 | 2 | 15-oct | seguimiento enviado el 15-oct |
| 119 | Consultores en IT | canales2 / consultores-en-it | 7 | 35 ev. | 21-oct | prioridad alta; seguimiento del 14-oct |
| 119 | Consultores en IT | follow_up_canales_2 / consultores-en-it | 2 | 10 ev. | 21-oct | prioridad alta |
| 137 | Brain Food | canales2 / brainfood | 4 | 18 ev. | 21-oct | prioridad alta; seguimiento del 14-oct |
| 175 | AYI Group | canales3 / ayi | 4 | 33 ev. | 21-oct | charla hecha; follow-up propio el 21-oct |
| 175 | AYI Group | canales3 / ayi (medio `organic`) | 2 | 25 ev. | 21-oct | ídem |
| 117 | ARTECH | follow_up_canales_2 / artech | 4 | 22 ev. | 21-oct | prioridad alta |
| 117 | ARTECH | canales2 / artech | 3 | 15 ev. | 21-oct | prioridad alta |
| 94 | EVOL SRL | canales1 / evol | 3 | 12 ev. | 21-oct | mail en borrador: confirmar si salió |
| 131 | Infolytics | canales2 / infolytics | 3 | 17 ev. | 21-oct | — |
| 131 | Infolytics | follow_up_canales_2 / infolytics | 1 | 4 ev. | 21-oct | — |
| 133 | Quanam | canales2 / quanam | 3 | 16 ev. | 21-oct | — |
| 133 | Quanam | follow_up_canales_2 / quanam | 1 | 5 ev. | 21-oct | — |
| 128 | Widergy | canales2 / widergy | 3 | 16 ev. | 21-oct | — |
| 154 | Mooving | canales3 / mooving | 3 | 15 ev. | 21-oct | seguimiento del 15-oct |
| 191 | Datawise | canales3 / datawise | 2 | 11 ev. | 21-oct | no interesa |
| 173 | Puntonet Tech | canales3 / puntonet | 2 | 13 ev. | 21-oct | seguimiento: no salió (Resend), borrador del 21-oct |
| 163 | Tecnom | canales3 / tecnom | 2 | 9 ev. | 21-oct | seguimiento del 15-oct |
| 224 | Accedra | canales4 / accedra | 2 | 10 ev. | 21-oct | seguimiento del 19-oct |
| 224 | Accedra | follow_up_canales_4 / accedra | 2 | 8 ev. | 21-oct | clic en el seguimiento del 19-oct |
| 230 | Silogik | canales4 / silogik | 2 | 8 ev. | 21-oct | seguimiento del 19-oct |
| 230 | Silogik | follow_up_canales_4 / silogik | 2 | 8 ev. | 21-oct | clic en el seguimiento del 19-oct |
| 209 | C&S Informática | canales4 / cys | 2 | 9 ev. | 21-oct | seguimiento del 19-oct |
| 209 | C&S Informática | follow_up_canales_4 / cys | 1 | 4 ev. | 21-oct | clic en el seguimiento del 19-oct |
| 205 | TGV | canales4 / tgv | 1 | 5 ev. | 21-oct | seguimiento del 19-oct |
| 205 | TGV | follow_up_canales_4 / tgv | 1 | 4 ev. | 21-oct | clic en el seguimiento del 19-oct |
| 333 | Fixa (Mutual Core) | canales6 / fixa | 2 | 12 ev. | 21-oct | seguimiento del 19-oct |
| 341 | Qontabiliza | canales6 / qontabiliza | 2 | 8 ev. | 21-oct | seguimiento enviado el 21-oct |
| 67 | Mutual TOJU | tanda5 / toju | 2 | 14 ev. | 21-oct | seguimiento del 15-oct |
| 107 | Chatsell | canales1 / chatsell | 1 | 8 ev. | 21-oct | seguimiento del 14-oct |
| 104 | Freetech Solutions | canales1 / freetech | 1 | 4 ev. | 21-oct | seguimiento del 14-oct |
| 109 | Raptiv | canales1 / raptiv | 1 | 14 ev. | 21-oct | charla hecha |
| 106 | Yoizen | canales1 / yoizen | 1 | 4 ev. | 21-oct | en conversación |
| 187 | Autologica | canales3 / autologica | 1 | 5 ev. | 21-oct | seguimiento enviado el 21-oct |
| 198 | Blackfish Argentina | canales3 / blackfish | 1 | 4 ev. | 21-oct | seguimiento enviado el 21-oct |
| 185 | EximIA Solutions | canales3 / eximia | 1 | 3 ev. | 21-oct | seguimiento enviado el 21-oct |
| 252 | devFactory | canales4 / devfactory | 1 | 5 ev. | 21-oct | seguimiento del 19-oct |
| 241 | Olpa Group | canales4 / olpa-group | 1 | 16 ev. | 21-oct | seguimiento enviado el 21-oct |
| 227 | Zennon BI | canales4 / zennon | 1 | 4 ev. | 21-oct | atendió nuestra llamada el 19-oct, interesado |
| 287 | Estudio360 | canales5 / estudio360 | 1 | 4 ev. | 21-oct | seguimiento del 19-oct |
| 294 | Clínica Online | canales6 / clinica-online | 1 | 9 ev. | 21-oct | seguimiento del 19-oct |
| 319 | Denteo | canales6 / denteo | 1 | 16 ev. | 21-oct | seguimiento del 19-oct |
| 320 | Dentry | canales6 / dentry | 1 | 5 ev. | 21-oct | seguimiento enviado el 21-oct |
| 300 | Gymzoft | canales6 / gymzoft | 1 | 8 ev. | 21-oct | seguimiento del 19-oct |
| 325 | Orion Sistemas | canales6 / orion | 1 | 6 ev. | 21-oct | seguimiento enviado el 21-oct |

Sin contacto atribuible (15-oct): `email` sin campaña (`(not set)`) 5 usuarios (probablemente los 41 mails del 5-oct con el link mal
armado, ver "Links con UTM"); orgánico de Google 4 y de Bing 2; `linkedin.com` 1 (los mensajes L2 a L9 iban sin UTM); referral
`dataindex.pro` 1; directo 238 usuarios y 292 sesiones (incluye visitas propias y pruebas de la demo).
Sin contacto atribuible (21-oct): `email` sin campaña (`(not set)`) 5 usuarios y 28 eventos.

## Conversaciones

Una entrada por charla (llamada, reunión o intercambio de mails con contenido), aunque no termine
en venta. Son los campos de la sección 0 del plan.

Formato:

```
### <fecha> · <empresa> · <persona, cargo>

- Problema: qué llamadas o mensajes hacen hoy a mano.
- Volumen: cuántos por mes.
- Costo actual: quién los hace y cuánto les cuesta.
- Quién decide:
- ¿Pagaría un piloto?:
- Caso de uso: (turnos, cobranza, reclamos, otro)
- Próximo paso:
```

Las tres primeras se cargaron el 9-oct-2026 con lo que contó el usuario; lo que dice "a confirmar" hay que pedírselo.

### ≤9-oct (fecha exacta a confirmar) · Raptiv (#109) · Federico Vara, director

- Resultado: positiva.
- Problema: a confirmar (en su respuesta del 7-oct: usarlo en sus apps).
- Volumen: a confirmar.
- Costo actual: a confirmar.
- Quién decide: a confirmar.
- ¿Pagaría un piloto?: a confirmar.
- Caso de uso: canal (integrador que revende o integra la voz en sus apps); caso final a confirmar.
- Próximo paso: demo enviada a Raptiv o a MINDO (a confirmar a cuál); siguiente paso a confirmar.

### ≤9-oct (fecha exacta a confirmar) · MINDO (#169) · persona a confirmar

- Resultado: positiva. Pyme integradora (agentes de IA para e-commerce en WhatsApp e Instagram, Mar del Plata).
- Problema: a confirmar.
- Volumen: a confirmar.
- Costo actual: a confirmar.
- Quién decide: a confirmar.
- ¿Pagaría un piloto?: a confirmar.
- Caso de uso: canal (integrador); caso final a confirmar.
- Próximo paso: demo enviada a Raptiv o a MINDO (a confirmar a cuál); siguiente paso a confirmar.

### ≤9-oct (fecha exacta a confirmar) · Gimnasio, nombre a confirmar (#270) · persona a confirmar

- Resultado: positiva; gimnasio con 200 alumnos.
- Problema: necesitan agentes para varias cosas (cuáles, a confirmar).
- Volumen: a confirmar.
- Costo actual: a confirmar.
- Quién decide: a confirmar.
- ¿Pagaría un piloto?: a confirmar.
- Caso de uso: otro (gimnasio, varios agentes; detalle a confirmar).
- Próximo paso: armar un prototipo para la venta.

### 15-oct · AYI Group (#175) · Luciano Fuccia, cargo a confirmar

- Cómo llegó: primer mail el 8-oct (`canales3`) y seguimiento el 15-oct (`follow_up_canales_3`), los dos a hi@ayi.group. Luciano llamó tres veces al 0800 de Atentina (lun 13-oct 22:44, 20 s; mar 14-oct 11:08, 17 s; mié 15-oct 12:52, 32 s) y las tres veces cortó cuando el agente le preguntó de qué empresa era. El 15-oct Laureano lo llamó a ese número.
- Resultado: positiva. Van a evaluar el producto como reemplazo de Twilio: voz y telefonía por API para lo que ellos construyen.
- Problema: hoy usan Twilio para voz y telefonía por API; qué construyen con eso y para qué clientes, a confirmar.
- Volumen: a confirmar.
- Costo actual: Twilio; cifra a confirmar.
- Quién decide: a confirmar (cargo de Luciano, a confirmar).
- ¿Pagaría un piloto?: a confirmar.
- Caso de uso: canal, reemplazo de Twilio (voz y telefonía por API); caso final de sus clientes a confirmar.
- Email: luciano.fuccia@ayi.group (persona; lo dio en la charla). Pasa a ser el ★ de AYI y desplaza a la casilla general hi@ayi.group.
- Próximo paso: follow-up el mié 21-oct a luciano.fuccia@ayi.group, en el mismo hilo; borrador en [`envios/2026-10-21-ayi-seguimiento.md`](envios/2026-10-21-ayi-seguimiento.md).

### 19-oct · Zennon BI (#227) · Cristian Ventura, fundador y CEO (a confirmar)

- Cómo llegó: primer mail el 15-oct (`canales4`, asunto «Llamadas de voz») a contacto@zennonbi.com, con clic en el link (GA del 19-oct). El 19-oct Laureano llamó al móvil publicado (+54 9 11 5402-0593); de 15 llamadas a los que hicieron clic, fue el único que atendió.
- Resultado: positiva, interesado. Laureano le pasó para agendar una reunión.
- Problema, volumen, costo actual, quién decide, piloto y caso de uso: a confirmar en la reunión.
- Próximo paso: confirmar la fecha de la reunión.

### 19-oct · Erpwoosync (#269) · Gabriel, cargo a confirmar

- Cómo llegó: por un contacto del usuario, sin envío nuestro; la charla agendada del 9-oct no se hizo y no respondió más. El 19-oct Laureano lo llamó y atendió.
- Resultado: positiva. Laureano le arma una demo de llamadas telefónicas con un número 0810.
- Problema, volumen, costo actual, quién decide y piloto: a confirmar (con la demo).
- Caso de uso: canal (ERP); atención telefónica por 0810 para sus clientes, a confirmar.
- Próximo paso: armar la demo con el 0810 y avisarle.

## Casos de uso que aparecen

Se cuenta en cuántas conversaciones aparece cada caso. Con 3, se justifica construir para él.

| Caso de uso | Conversaciones | Empresas |
|---|---|---|
| Canal: integrador que suma la voz a lo que vende (caso final a confirmar) | 3 | Raptiv, MINDO, AYI Group |
| Canal, subcaso: reemplazo de Twilio (voz y telefonía por API para lo que construyen); no se suma al de arriba | 1 | AYI Group |
| Gimnasio: varios agentes (cuáles, a confirmar) | 1 | Gimnasio (#270, nombre a confirmar) |

## Competidores que aparecen

Empresas contactadas que dicen tener algo parecido o que se superponen con lo nuestro. Sirve para no insistirles y para
ver qué ofrece el mercado local. Lo de cada sitio se leyó el 14-oct-2026.

| Empresa | Qué dijeron o qué se ve | Voz | Fuente |
|---|---|---|---|
| Datawise (#191), CABA y Rosario, oficinas en Uruguay, Chile, Paraguay y Perú | 14-oct: "ya tienen esta solución". Integrador IT; su página de IA ofrece chatbot, reconocimiento de voz, NLP para atención y "agentes de IA" a medida | No publican agente de voz telefónico; el sitio dice "reconocimiento de voz" | respuesta; https://datawise.com.ar/inteligencia-artificial/ |
| Inthegra Software (#271), Córdoba | 14-oct: escribieron ofreciendo integraciones o alianza comercial. Su "AI Chatbot" hace atención y cobranzas por WhatsApp, integrado al CRM | No publican voz: complemento, no competidor directo | https://inthegrasoftware.com/solutions_ai_chatbot.html |
| Yoizen (#106), CABA | Suite de atención omnicanal (Yoizen CX Suite: ySocial, yFlow, ySurvey), WhatsApp BSP y Meta Business Partner; agentes de IA de texto que "integran múltiples motores —ChatGPT, Gemini, LLaMA, Agentforce de Salesforce o modelos propios—". Meta los eligió para el despliegue de las llamadas de WhatsApp en LATAM (2025). Clientes: Metrogas, OSDE, Swiss Medical, Galicia, Claro, Edenor, AMUR (#3). Pasaron el contacto a producto (7-oct) y a Juan Stamati, alianzas (14 o 15-oct) | Llamadas de WhatsApp atendidas por humanos ("escalamiento a llamadas"); no publican agente de voz con IA ni voz telefónica, pero su post del Forum Salud Digital usa #VoiceBots. Leído el 19-oct-2026 | https://yoizen.com/prepara-tu-cx-para-el-mundial-2026-con-whatsapp-y-la-ia-backup/; https://yoizen.com/blog/whatsapp-business-calling-api/; https://www.linkedin.com/company/yoizen/ |
