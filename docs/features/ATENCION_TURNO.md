# Atención del turno en voz

Tres capas para que una llamada no quede muda cuando la persona no responde: el **watchdog de
silencio** (avisos y corte con aviso), la **repetición** (`repeat_last_reply`) y el
**pedido de repetición por STT vacío**. Se activa por agente con el bloque `turn_attention` en la
definición (una versión nueva; sin migración). Origen: la llamada
`675cd4bc-153f-4ac0-952e-bfd690183b05` (La Estrella, 21-nov-2026, 128 s muda tras el primer turno).

Estado: implementado en `development`, sin deploy todavía.

## Configuración

En la raíz de la definición del agente (`app/conversation/models.py`, `TurnAttention`; sin el
bloque o `enabled: false`, apagado y sin cambios en el comportamiento):

```json
"turn_attention": {
  "enabled": true,
  "reminder_after_ms": 7000,
  "reminder_max": 2,
  "reminder_gap_ms": 7000,
  "end_after_ms": 30000,
  "stt_retry": true,
  "transcription_timeout_ms": 3000,
  "repeat_last_reply": true,
  "reminder_text": "",
  "end_text": "",
  "on_end": "hang_up",
  "on_end_area_id": ""
}
```

| Campo | Default | Rango | Qué hace |
|---|---|---|---|
| `enabled` | `false` | bool | Prende el watchdog y la repetición |
| `reminder_after_ms` | `7000` | 3000–30000 | Primer aviso desde que el agente deja de hablar |
| `reminder_max` | `2` | 0–5 | Avisos por ventana; `0` = solo cierre |
| `reminder_gap_ms` | `7000` | 3000–30000 | Espera entre avisos |
| `end_after_ms` | `30000` | 15000–120000, ≥ `reminder_after_ms` | Cierre desde que el agente deja de hablar |
| `stt_retry` | `true` | bool | VAD con voz y sin transcripción → pedir que repita |
| `transcription_timeout_ms` | `3000` | 1000–10000 | Cuánto esperar antes de ese pedido (solo con `stt_retry`) |
| `repeat_last_reply` | `true` | bool | Ofrece la herramienta de repetición |
| `reminder_text` | `""` | ≤ 300 | Texto del primer aviso; vacío = plataforma |
| `end_text` | `""` | ≤ 300 | Texto del cierre; vacío = plataforma |
| `on_end` | `"hang_up"` | `hang_up` / `transfer` | Qué hace al vencer `end_after_ms` |
| `on_end_area_id` | `""` | UUID de un área de `handoff.areas` | Solo con `transfer`; vacío = primera área |

Validación al guardar (`Workflow._consistent`): con avisos (`reminder_max > 0`),
`end_after_ms >= reminder_after_ms` (con `reminder_max: 0` puede cerrar antes del primer aviso:
cierra sin avisar); `on_end=transfer` exige `handoff.areas` no vacío y, si se setea,
`on_end_area_id` debe estar entre esas áreas. No aplica a WhatsApp de texto; las llamadas de
WhatsApp (voz) sí lo usan.

Plantillas: las 6 de `app/agents/templates/*.json` y los de referencia de la landing (`landing_*`)
nacen con el preset transaccional 7/2/7/30, `on_end: hang_up` y `enabled: true` (el bloque es
inerte en WhatsApp): un agente creado de una plantilla ya trae la función prendida. Los agentes ya
existentes en la base no cambian hasta guardar una versión nueva.

Textos de plataforma (`app/config.py`, como `quota_end_message`); el texto del agente gana. No son
instrucciones del modelo: es protocolo del canal.

| Setting | Default |
|---|---|
| `VOICE_NO_RESPONSE_REMINDER` | `"¿Me escuchás? Te repito:"` (se le agrega la última pregunta) |
| `VOICE_NO_RESPONSE_SECOND` | `"Sigo acá. ¿Querés que te pase con una persona?"` (con áreas) |
| `VOICE_NO_RESPONSE_SECOND_NO_AREAS` | `"Sigo acá. ¿Me repetís lo que necesitás?"` (sin áreas) |
| `VOICE_NO_RESPONSE_END` | `"No te escucho bien. Podés volver a llamarnos o escribirnos por WhatsApp. ¡Gracias!"` |
| `VOICE_NO_RESPONSE_STT` | `"No te escuché, ¿podés repetir?"` |

## Flujo (watchdog de silencio)

`app/voice/attention.py` (`AttentionWatchdog`), integrado en `app/voice/worker.py`. Con 7/2/7/30:

```
el agente termina de hablar
  +7 s   → "¿Me escuchás? Te repito: <última pregunta>"
  +14 s  → "Sigo acá. ¿Querés que te pase con una persona?"   (sin áreas: "... ¿Me repetís lo que necesitás?")
  +30 s  → "No te escucho bien. ..." y hang_up("no_response")
```

- **Dueño de la ventana:** los deadlines son absolutos desde que el agente deja de hablar. Solo
  arman ventana los ganchos que saben quién habló: el fin del `say` de la apertura
  (`add_done_callback` del `SpeechHandle`), el done-callback del speech de un turno real
  (`llm_node`) y la vuelta del agente después de una derivación (`run_transfer`): cuando `Transfer.run`
  termina con el mensaje de vuelta ya sonado (persona que cortó con `on_person_hangup=resume`, código
  de vuelta a la IA, nadie atendió, avisado por WhatsApp, fuera de horario) o tras el aviso de una
  derivación que falló. No arma si quien llamó cortó (`customer_hung_up`, `CustomerGone`) ni si la
  llamada se está cerrando (`on_person_hangup=end`, cualquier `hang_up`). `on_agent_state` no
  llama nada: los avisos del propio watchdog pasan por `session.say` y disparan los mismos eventos
  de estado que una respuesta real; con eventos crudos la secuencia loopea. Mientras suena un aviso
  propio, `arm`/`disarm` se ignoran (su voz no reinicia la ventana).
- **`reset()`** (voz del usuario por VAD, transcripción final con texto, tecla marcada): cancela lo
  agendado, pone el contador a cero y arranca ventana nueva. Nunca se ignora: si la persona habla
  durante un aviso, este se corta (`allow_interruptions=True`) y si habla durante el aviso de
  cierre, se cancela el corte.
- **`disarm()`** al empezar un turno real (`llm_node`) y al empezar `run_transfer`: mientras la
  persona del equipo habla con quien llamó no hay avisos.
- **Presupuesto de avisos por ventana:** los pedidos del STT cuentan como avisos. Un evento de STT
  no toca la ventana ni el deadline: una línea ruidosa no loopea "¿podés repetir?" ni atrasa el
  cierre; solo la entrada real resetea.
- **`busy()`** (turno en curso, derivación, corte empezado, speech en vuelo): un evento vencido se
  difiere y dispara al desocuparse; el cierre nunca se pierde y no se corre del deadline.
- **Cierre:** `say` sin interrupciones y después `hang_up("no_response")`; con `on_end=transfer`,
  resuelve `on_end_area_id` (vacía = la primera) contra `progress.handoff_areas` y llama a
  `run_transfer(announced=True)`; sin área resoluble (la desactivaron), `hang_up("no_response")`.
- Todos los `say` del watchdog van con `add_to_chat_ctx=False` (como el aviso de cuota) y no
  disparan `on_completed`.
- **LiveKit:** con `enabled`, `user_away_timeout=None` (nada escucha el evento `away`; el watchdog
  propio es el único dueño) y, con `stt_retry`, `transcription_timeout` en la sesión → evento
  `user_transcription_timeout`. En el loadtest no se crea (metadata `loadtest`, como `handoff`).
- **Grabación (`record_audio`):** los `say` del watchdog suspenden el tee del agente
  (`agent._rec_suspend`): su audio no se graba ni pisa el WAV del turno pendiente.
- **"La última pregunta"** del primer aviso: el último `Message` assistant con `person` y
  `handoff_leg` en `None` (las piernas y avisos de derivación no cuentan); fallback el saludo.

## `no_response`

`ended_reason` nuevo (familia `max_duration`/`quota_exhausted`: corta el sistema, no el LLM). El
detalle y los reportes lo muestran como **Sin respuesta**, "finalizada por el sistema"
([REPORTES.md](REPORTES.md)). `finalize` lo respeta como cualquier corte ya puesto; las campañas
hoy cierran un intento conectado con `no_response` como atendido (pendiente, abajo).

## Repetición (`repeat_last_reply`)

Para "¿cómo?", "no te escuché" o un pedido de repetición: el modelo llama a la herramienta de plataforma
`repeat_last_reply` (sin parámetros) y la última respuesta suena **tal cual**, sin volver a saludar ni
inventar. Se ofrece solo en voz y solo si el agente tiene `turn_attention` activo con
`repeat_last_reply: true` (una definición vieja sin el bloque, o el switch apagado, no cambia nada;
WhatsApp nunca la recibe).

Descripción que ve el modelo: "Cuando la persona pide que repitas, dice que no escuchó o contesta con
una duda, repetí la última respuesta tal cual. No escribas texto en este turno: llamá a esta herramienta
y nada más."

Flujo (los dos motores, clásico y `external`):

1. **Oferta:** `platform_tools.tools_for` la agrega después de `end_call` (`app/llm/client.py`,
   `anthropic_client.py` y `llm/external.py`: el agente propio la recibe igual, con sus
   herramientas). La vista previa del editor no la ofrece; como es solo voz, probarla en una
   llamada real.
2. **Corte:** con `turn.repeat = True` los clientes cortan la vuelta de herramientas: no se vuelve a
   llamar al LLM después de la repetición.
3. **Sustitución:** si el modelo no escribió texto, el motor (`_use_last_reply`,
   `app/conversation/engine.py`) pone la **última respuesta del agente** como respuesta del turno. La
   regla es la misma que la "última pregunta" del primer aviso: el último `Message` assistant con
   `person` y `handoff_leg` en `None` (las piernas y los avisos de derivación no cuentan), fallback el
   saludo. Si el modelo escribió texto antes de la herramienta, se respeta: no se agrega la anterior y
   no se duplica el audio.
4. **Voz:** `llm_node` (`app/voice/worker.py`) empuja esa respuesta al stream del TTS si no salió
   texto del LLM; si el modelo habló, no agrega nada. Es un turno real del agente: la ventana de
   silencio se arma con el done-callback de siempre y `settle_last_reply` lo puede deshacer como a
   cualquier turno (la interrumpió la persona → el turno siguiente recibe todo).
5. **Registro:** el turno no completa ni dispara la extracción (`repeat` no toca el status) y queda
   marcado en el mensaje (`Message.repeat`, en el JSON del store). El historial del LLM no guarda la
   llamada: un turno repetido se ve como `[user, assistant con la respuesta repetida]`, sin
   `tool_calls` — el filtro por `platform_tools.NAMES` ya la excluye de las herramientas del cliente.
   `Message.repeat` **no** se expone en la API del panel (`MessageOut`): el panel no muestra nada
   distinto para estos mensajes, así que vive solo en el store; el contador `repeat_count` y el evento
   `turn.repeat` (P2) son la vía para reportearlo.

Si el agente del cliente (external) no la usa, no cambia nada; si tiene una herramienta propia con el
mismo nombre, queda reservada por la plataforma (la oferta es de la plataforma y `apply` la maneja).

Tests: `tests/test_platform_tools.py` (oferta por canal/config, `apply`, corte en `converse`),
`tests/test_engine.py` (sustitución, texto del modelo respetado, piernas excluidas, sin extracción,
historial, retracción), `tests/test_external_agent.py` (el agente propio la recibe y no queda mudo),
`tests/test_llm_anthropic.py` (corte en el cliente Anthropic) y `tests/test_voice.py`
(`llm_node` empuja el texto si no hubo streaming, no duplica si hubo).

## STT vacío

Con `stt_retry`, `AgentSession(transcription_timeout=transcription_timeout_ms/1000)`: si el VAD
detectó voz y el STT no devolvió texto dentro del timeout, `user_transcription_timeout` → el
watchdog dice `voice_no_response_stt` y consume presupuesto de avisos (ver arriba). Con
`transcription_timeout_ms >= reminder_after_ms` es válido pero compite con el primer aviso: el
default lo deja antes (3 s contra 7 s).

## Pruebas locales

`make dev-up`, un agente de prueba con el bloque y **tiempos cortos** para no esperar 30 s por
escenario: `reminder_after_ms: 3000, reminder_max: 2, reminder_gap_ms: 3000, end_after_ms: 15000`
(el mínimo). Llamar al número del agente y:

1. Llamada muda: aviso a los 3 s, insistencia a los 6, cierre a los 15 con `no_response`.
2. Pausa de 2 s y hablar: sin avisos.
3. Hablar durante un aviso: se corta y sigue el turno.
4. Marcar una tecla: ventana nueva.
5. Con `on_end: "transfer"` y un área: a los 15 s pasa al área.
6. Con `record_audio`: los WAV de los turnos siguen correctos y el aviso no queda grabado.
7. Responder "¿cómo?" a una pregunta del agente: repite la última respuesta tal cual, sin saludar de
   nuevo; si el agente ya habló en ese turno, no se duplica.

Tests del repo: `AttentionWatchdog` con `sleep` falso (`tests/test_voice.py`, `test_attention_*`), el
`entrypoint` real con el arnes (`tests/test_voice_wiring.py`, `test_mute_call_*`,
`test_dtmf_restarts_*`, `test_transcription_timeout_*`) y la repetición (`test_repeat_*` en
`tests/test_engine.py`, `tests/test_external_agent.py` y `tests/test_platform_tools.py`;
`test_llm_node_*` en `tests/test_voice.py`).

## Puesta en marcha

1. Probar en local con tiempos cortos (arriba) antes de tocar un agente real.
2. Activar por agente guardando una versión nueva con el bloque (panel, sección **Si la persona
   no responde**, o `PUT /api/v1/agents/{agent_id}/definition`); las llamadas en curso siguen con
   la versión con la que empezaron.
3. Vuelta atrás: guardar otra versión con `"enabled": false`; no hace falta tocar código ni
   reiniciar nada.
4. En producción, medir del reporte de llamadas el motivo **Sin respuesta** y ajustar los tiempos
   con esos datos; los contadores por llamada (`no_response_count`, `repeat_count`) son el P2 de
   observabilidad.

## Pendientes

- **RTP (P2):** diagnóstico de microcortes (`rtpqos` en Asterisk o `core show channel`) y
  correlación con llamadas con `no_response`; plan aparte.
- **Campañas (decisión abierta):** hoy un intento conectado con `no_response` cierra como
  atendido; falta decidir si se reintenta como `no_contact`.
- **Observabilidad (P2):** `no_response_count`, `repeat_count` y los eventos `turn.no_response` /
  `turn.repeat` (todo tipo nuevo se registra en `services/events.TYPES` antes de usarse); reporte
  de calidad por número/cliente (% de llamadas con `no_response` o repetición, silencio medio por
  turno).
