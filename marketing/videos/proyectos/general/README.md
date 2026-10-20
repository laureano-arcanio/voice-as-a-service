# Video general de Atentina

- **Pedido (20-oct-2026, Laureano):** un video animado con voces de nuestro TTS que explique el problema, las
  ventajas de Atentina y cómo se usa desde el panel y por API. Arrancó como prueba de concepto de 30 s y creció
  con los pedidos de cambio (historia abajo).
- **Público:** dueños y responsables de atención de empresas (landing, redes, primer contacto). No técnico.
- **Mensaje:** cada llamada sin atender es un cliente que se va con la competencia; Atentina atiende a todos a la
  vez, por cualquier canal, responde al instante y se configura por panel o por API.
- **Formato:** 1920 × 1080, 30 fps, ~60 s. Composición `general` (`src/Video.tsx`).

## Guion (v2)

| Escena | Tiempo | Locución | Qué se ve |
|---|---|---|---|
| `intro` | 0–6,8 s | n5 | Pantalla oscura del cierre (logo, frase de la landing, "Probá la demo", personajes); se funde con la siguiente |
| `problema` | 6,2–11,4 | n1 | Tres clientes (teléfono, WhatsApp, web) contra "Tu línea · Ocupada · 1 a la vez"; "Sin respuesta" y se van a "La competencia" |
| `atentina` | 11,4–16,9 | n2 | La mascota atiende a los tres a la vez, cada uno por su canal; "Las 24 horas" |
| `viaje` | 16,9–24,7 | c1, a1 | Diagrama Cliente → Llamada → Escucha (STT) → Piensa (LLM) ↔ CRM → Responde (TTS) → vuelta; cronómetro hasta 0,90 s |
| `api` | 24,7–38,3 | n3, n3b | El integrador escribe el JSON del agente, `POST /api/v1/agents` → 201; después `GET /api/v1/calls/{id}` y la tarjeta de resultado |
| `salientes` | 38,3–47,3 | n6 | Campaña (contactos, horario, 8 en paralelo, reintentos, WhatsApp si no atiende) y avance por contacto |
| `panel` | 47,3–53,7 | n4 | Dashboard: estadísticas, "En vivo", tabla de conversaciones y detalle con transcripción y datos |
| `cierre` | 53,7–60,5 | n5 | Igual que la intro |

Locución en [`guion.json`](guion.json): narrador `lucas`, la cliente `carolina` y la asistente `valentina`
(elegida por variación de tono: la menos monótona de 14 voces, `scripts/candidatas.py voces`).

## Afirmaciones y de dónde salen

- **0,90 s:** mediana del tiempo de respuesta en llamadas reales desde el 7-oct-2026 (`call_logs.latency`, total =
  fin de la frase + LLM + TTS, 35 turnos; p90 1,49 s). No incluye una consulta a un CRM: en el video la consulta
  entra dentro de ese tiempo.
- **"Inferencia propia · servidores en Argentina":** de la landing.
- **Campañas salientes (escena `salientes`):** implementadas, **sin desplegar** (docs/LLAMADAS_SALIENTES_PLAN.md);
  "hasta 8 a la vez" es el tope provisorio `CALL_CAMPAIGN_MAX_CONCURRENT`, sin medir con Gemma.
- **Ilustrativo:** los números del panel y de la campaña, los contactos y la herramienta `buscar_cliente`.
- **Rutas y JSON:** reales (`POST /api/v1/agents`, `GET /api/v1/calls/{id}`, `POST /api/v1/campaigns`), recortados.

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 20-oct-2026 | 51,5 s | Con intro; ejemplo de turnos | cerrada (sin fuente) |
| [v2](versiones/v2/NOTAS.md) | 20-oct-2026 | 60,5 s | Genérico (sin turnos) y escena de llamadas salientes | borrador |

Antes de v1 hubo cortes que no se guardaron: la prueba de 30 s (5 escenas, voz `sofia`), la de 45 s (varios
clientes contra una línea, CRM de turnos, voz `valentina`, API y panel por separado) y el ajuste del marcador del
viaje (iba y volvía demasiado rápido).
