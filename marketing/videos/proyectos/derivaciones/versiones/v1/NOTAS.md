Estado: borrador

# Derivaciones v1

## Pedido

> Crea un video explicativo de como se crean agentes con transferencia de llamadas, equipo, area como se
> configura. corto, que se entienda. utiliza screens de pantalla en cada paso, version mobile. Primero explica
> como funciona con un diagrama, muchos usuarios ->ciclo de agente-> transferencias por areas.

## Qué es

Primera versión. Vertical 1080 × 1920, 79,7 s, 11,3 MB. Cuatro escenas de diagrama (ciclo del agente, áreas,
espera con aviso y conexión con el 1, si nadie atiende) y cinco pasos con capturas reales del panel a 390 px
(Equipo, área, horario y mensajes, Derivación a personas en el agente, guardar) más el resultado (la
conversación con el tramo de la persona). Guion por escena en el README.

## Locución

- `paula` (d1–d3, d5–d9, d11, d12) y `pablo` (d4, d10); 4 tomas por línea, la más fiel según el STT propio
  (todas 0,99–1,00). `ganancia_db: -1.5`. Total de voz: 65,7 s.
- Duraciones: d1 5,68 · d2 7,52 · d3 6,48 · d4 5,76 · d5 4,80 · d6 4,64 · d7 5,44 · d8 5,92 · d9 6,96 ·
  d10 4,96 · d11 4,40 · d12 3,12 s. Ninguna se pisa con la escena siguiente.
- Ortografía normal, sin grafías forzadas.

## Controles

- `npx tsc --noEmit` sin errores.
- Cuadros de las doce escenas revisados (`scratch/videos/derivaciones/stills/`) y hojas de `make video-revisar`
  (`scratch/videos/revision/derivaciones-v1/`): sin textos cortados ni superposiciones.
- **−16,5 LUFS** (referencia −16 ± 1,5).
- Transcripción por tramos: las doce líneas se entienden. El STT oye "crea un área" por "creá un área" (d7),
  "el aviso o la persona" por "el aviso a la persona" (d8) y "de la gente" por "del agente" (d10): confusiones
  del STT habituales; a confirmar de oído.

## A revisar antes de mostrarlo afuera

- **La transferencia no está probada con llamadas reales** (DERIVACIONES_PLAN 13.4): desplegada el 23-oct-2026.
  El video la presenta como función del panel, sin decir que está probada; conviene mostrarlo afuera después de
  la prueba con los dos celulares.
- **La conversación del resultado es ilustrativa** (mock del detalle de la llamada), lo mismo que la empresa,
  las personas, los teléfonos y los horarios.
- **Mobile:** el panel se usa a 390 px, con detalles: las tablas de Personas y Áreas se cortan a la derecha
  (columnas WhatsApp, Horario y Estado fuera de la vista, con scroll horizontal); en Nueva área, "Rotativa"
  queda pegada al borde del control y los campos "hasta" del horario se salen un poco del modal; en el detalle
  de la conversación, la columna de estado de los datos ("Obtenido") se corta. Ninguno impide el paso; quedan
  para `web/`.
- El botón "Guardar versión nueva" no se ve en la captura del guardado (solo el aviso "Versión 2 guardada.").
