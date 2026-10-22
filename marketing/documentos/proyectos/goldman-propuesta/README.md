# Propuesta para Isaías Goldman SA

- **Pedido (21-oct-2026, Laureano, textual):** "Un PDF con el análisis observado de su problema actual, fáctico pero con
  lenguaje amable. La solución propuesta. Y cómo se pondría en marcha."
- **Destinatario:** Isaías Goldman (presidente y fundador), y sus hijos Jonatan (director comercial) y Carolina
  (directora). Isaías Miguel Goldman SA, Córdoba: aires, calefacción y refrigeración; venta a público, instaladores y
  empresas, instalación, service y cursos. En "ustedes" (empresa familiar), con un saludo a Isaías.
- **Contexto:** Laureano habló por teléfono con Isaías y él pidió que le cuenten la oferta. Base de conocimiento:
  [`docs/mercado/demos/isaiasgoldman.md`](../../../../docs/mercado/demos/isaiasgoldman.md) (partes 0, 2, 4, 5 y 7).
  Video relacionado en curso: `marketing/videos/proyectos/goldman/`.
- **Objetivo:** que acepten una reunión de relevamiento y un piloto de 30 días desde noviembre.
- **Formato:** A4, 4 a 6 hojas (salió en 5). `make doc P=goldman-propuesta V=<n> HOJAS=6`.
- **Indicación del pedido:** es material de venta: todo se presenta como la oferta, sin decir qué está construido y
  qué no (ver "A validar"). Sin precios. Sin logo ni marca de Goldman.

## Estructura (v1)

1. **Quiénes son y lo que observamos:** h1 "Que cada consulta tenga respuesta, y que ustedes las vean todas", lo que
   hacen bien (cuatro cifras), la cita de Isaías ("Nos gusta hacer cosas donde podemos responder") y cuatro hechos:
   un solo número, 266 productos sin precio, 121 de 168 horas cerrado y la temporada de noviembre con la competencia.
2. **Lo que dicen sus clientes:** cinco momentos con citas textuales sin nombres (llamado, presupuesto, precio, visita,
   mostrador), lo que tienen en común, lo positivo de las reseñas y por qué importa ahora.
3. **La solución:** el especialista de guardia en tres canales (línea 0800/0810, WhatsApp, chat web, cada uno con su
   pase a una persona), un solo precio y criterio, y el diagrama (clientes → canales → agente que clasifica → su
   equipo; todo → panel).
4. **El panel:** mock con datos ilustrativos (consultas, primera respuesta, fuera de horario, resueltas/derivadas,
   presupuestos, turnos, reclamos, por canal, por tipo, derivaciones por persona y demora) y la tabla "lo observado →
   qué lo resuelve".
5. **Puesta en marcha:** piloto de 30 días desde noviembre (aires hogar + posventa), seis pasos, quién hace qué, fases
   posteriores, nota de precio y pie de contacto.

## Afirmaciones y de dónde salen (todas leídas el 21-oct-2026, salvo la prensa)

- **"30 años", "desde los 90", tres generaciones:** banner "30 años" del sitio; fundación 1990-1992 (InfoNegocios 2018
  y 2019); "tercera generación" (Jonatan, InfoNegocios 2021).
- **4.500 m² y ~50 personas:** InfoNegocios 2018 y 2021.
- **1.671 reseñas, 4,2:** ficha de Google Maps.
- **Arcor, Georgalos, Mostaza:** carrusel de clientes del sitio.
- **Citas:** "Nos gusta hacer cosas donde podemos responder" (Isaías, InfoNegocios 10-may-2018); "Nuestro fuerte es el
  postventa" (Jonatan, InfoNegocios 12-abr-2021).
- **Un solo número (351 386 2886):** sitio, Maps, Facebook, Linktree. Existe otro fijo (351 589 0033) solo en una
  respuesta a una reseña: por eso dice "el teléfono y el WhatsApp del sitio, de Google...".
- **266 productos sin precio, "Consultar precio" → formulario por email:** sitemap y fichas de Tiendanube.
- **121 de 168 horas cerrado:** horario de Google Maps (lu a vie 8:30-13 y 14:30-18:30, sáb 8:30-13): 47 h abiertas.
  El sitio no publica horario.
- **Temporada de noviembre a febrero; precios que suben antes del verano:** base de conocimiento, parte 4.2.
- **Competencia "a un clic", "algunos ya muestran el precio":** Climatización Polar publica precios en su Tiendanube
  (parte 4.1). No se nombra quién.
- **Citas de reseñas:** `scratch/prospectos/isaiasgoldman/raw/google-maps-resenas.txt`, textuales y sin nombre;
  antigüedad relativa al 21-oct-2026. "Excelente atención" y elogios al curso: reseñas de 5 estrellas del último año.
- **Voz con acento argentino:** diferencial de Atentina (TTS propio, 41 voces).
- **Panel:** todas las cifras son **ilustrativas** y están rotuladas así en el documento y debajo del mock.

## A validar antes de mandarlo

- **Funciones presentadas como oferta que hoy no están desplegadas** (base de conocimiento, parte 7.4): transferencia
  de la llamada a un vendedor, relay de WhatsApp al vendedor o soporte, chat en la web con contexto de la página, y
  parte de las métricas del panel (por tipo de consulta, por canal con chat web, fuera de horario, derivaciones por
  persona y su demora, presupuestos/turnos/reclamos como contadores). Confirmación de visitas el día anterior: campañas
  de WhatsApp desplegadas, de llamadas sin desplegar. Agenda real de técnicos y registro de casos con estado: falta
  (app por cliente).
- **Promesas comerciales:** piloto de 30 días desde noviembre, revisión semanal y precio a acordar en la reunión
  (vienen del pedido de Laureano). "Ajuste semanal y soporte durante el piloto": a confirmar.
- **Línea 0800 o 0810:** costo por minuto y plazo de alta con Anura sin verificar.
- **Número de WhatsApp:** pasar el 351 386 2886 a la API hace que deje de andar en la app del celular; el documento
  solo dice que se elige en la reunión.
- **Chat web en Tiendanube:** sin verificar que su plan permita insertar un script; el documento dice que se suma
  "cuando su web esté lista".
- **Lista de precios y stock:** para 266 productos que cambian cada mes hace falta integración (fase "Integración").

## Versiones

| Versión | Fecha | Qué cambió | Estado |
|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 21-oct-2026 | Primera versión | borrador |
