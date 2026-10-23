Estado: borrador

# Primeros pasos v2

## Pedido

> Crea un nuevo video, v2. No utilizes la v1 ni la leas. Crea desde cero.
> Crea un nuevo video sobre como crear un Agente basico como cliente.
> - formato vertical para mobiles
> - Voz por defecto (1 sola)
> - zoom in cuando escriba (sin abusar del recurso)
> - Empieza con gracias por probar Atentina, te cuento como empezar.
> - que explique los pasos a seguir y como hacer una llamada de prueba desde la web.

## Qué cambió

Recreación completa desde cero: no se leyó ni se reutilizó el código, el guion ni los audios de la v1. La v1
quedó cerrada en `versiones/v1/` (y su README se conservó como `versiones/v1/README-v1.md`).

- Vertical 1080 × 1920, 59,7 s, pensado para el celular.
- Una sola voz (`paula`) en las nueve líneas, sin contrapuntos.
- Un único zoom de cámara (10 %) al escribir el nombre del agente.
- El recorrido: Agentes → Nuevo agente → Definición → Guardar → Probar → Modo prueba → link → llamada.
- Pantallas recreadas a mano (no capturas), con los textos y botones reales de la UI.

## Locución

- `paula`, 4 tomas por línea, la más fiel según el STT propio. `ganancia_db: -1.5`.
- Duraciones: t1 3,04 s · t2 3,36 s · t3 5,20 s · t4 7,04 s · t5 3,44 s · t6 4,32 s · t7 4,96 s ·
  t8 6,16 s · t9 4,88 s.
- Se verificó que ninguna línea se pise con la escena siguiente.

## Controles

- Render: 59,7 s, 5,4 MB.
- `make video-revisar`: **−17,0 LUFS** (referencia −16 ± 1,5) y transcripción por tramos.
- `npx tsc --noEmit` sin errores.
- Cuadros de las nueve escenas revisados; sin textos cortados ni superposiciones.

## A revisar antes de mostrarlo afuera

- **De oído:** "a Tentina" es un error del STT con el nombre de la marca (t1 y t9); la toma limpia de t9 dice
  "Atentina". En t3 la revisión mezclada oyó "crea a la gente"; la toma limpia dice "crea el agente" (fidelidad
  1,00), así que es del STT sobre la mezcla.
- **Ilustrativo:** el nombre "Atención al cliente", los textos de rol, objetivo, apertura y base, las fechas de
  las versiones y el diálogo de la llamada. La pantalla de la llamada es una recreación propia: el link real de
  la prueba abre LiveKit Meet, que no se muestra.
- **Funciones:** todas las que aparecen están desplegadas (agentes por cliente, versiones, modo prueba y link).
  No se muestran cifras de latencia ni de capacidad.
