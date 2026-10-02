# Plan: evaluación de calidad de llamadas por tipo de agente y modelo LLM

Diseño (2026-09-26). **Implementado (fases 0 a 2 y 4):** uso y estado en
[`eval/README.md`](eval/README.md), código en `scripts/eval/`. Complementa al test de capacidad
([`CAPACITY_TEST_PLAN.md`](CAPACITY_TEST_PLAN.md)): aquel mide cuántas llamadas aguanta el pipeline,
este mide **qué tan bien conversa el LLM**, en varios tipos de agente y con varios tipos de cliente,
para comparar modelos. Responde:

1. **¿Qué modelo LLM conversa mejor** en los agentes más comunes (cobranza, relevamiento, toma de datos,
   turnos, venta) con clientes cooperativos, apurados, confusos, hostiles y fuera de guion?
2. **¿En qué falla cada modelo?** Datos inventados, repreguntas, reglas rotas, alucinaciones sobre la
   base de conocimiento, cierres equivocados, loops.
3. **¿Cuánto cuesta esa calidad en latencia por turno?** Mismo run, mismo modelo.

## 1. Enfoque

- **Por texto, no por voz.** El test corre el motor (`ConversationEngine` + `LLMClient`) contra el LLM
  real con `ConversationStore("sqlite://")`, como `scripts/replay_calls.py`. Sin LiveKit, STT ni TTS:
  una conversación de 10 turnos tarda ~10 s y se corren de a 8–16 en paralelo. Un run completo
  (~100 conversaciones) tarda 10–15 min. La voz se agrega como capa opcional (sección 6).
- **Cliente simulado por un LLM grande externo** (DeepSeek por API, OpenAI-compatible), que actúa
  una *persona* con una *ficha* de datos verdaderos. Es el mismo modelo y prompt para todos los
  modelos que se comparan: la variable es solo el LLM del agente.
- **Dos niveles de métricas:** duras (datos, resultado, reglas, loops, latencia; deterministas y sin
  juez) y de juez (rúbrica con el LLM externo). Las duras deciden; el juez explica y ordena.
- **Registro por modelo** en `docs/eval/EVAL-NNN-<slug>/`, como `CAP-NNN`, con `config_id` del
  motor (modelo, cuantización, `LLM_THINKING`, temperatura, engine).

## 2. Tipos de agente

Un agente de referencia nuevo por tipo, en `app/agents/reference/` (JSON; antes YAML en `app/workflows/`; el motor structured es el mismo archivo con sufijo `_structured`) con prefijo `eval_` (mismo motor, sin código
nuevo). Cada uno con `engine: classic` y una variante `_structured` por `extends`.

| Agente | Qué hace | Datos a obtener | Qué pone a prueba |
|---|---|---|---|
| `eval_cobranza` | Recordatorio de deuda vencida a un titular, ofrecer plan de pago, registrar promesa | identidad confirmada, es el titular, promete pagar, fecha y monto, motivo del no pago, no volver a llamar | Firmeza sin intimidar (la ley de defensa del consumidor prohíbe medios intimidatorios en el cobro extrajudicial), **no revelar la deuda a un tercero**, negociación con montos y fechas en palabras |
| `eval_relevamiento` | Encuesta de satisfacción post-servicio: 5 cerradas (0–10 y opciones) y 1 abierta | puntajes (`integer`), opciones (`choice`), comentario | Respuestas ambiguas ("más o menos"), no inducir la respuesta, no saltear preguntas, no interpretar de más la abierta |
| `eval_datos` | Actualización de datos de contacto de un cliente | email, teléfono, dirección, DNI | Dictado: confirmar repitiendo, pedir deletreo, email cortado en dos turnos, correcciones ("no, era punto com") |
| `eval_turnos` | Confirmar o reprogramar un turno médico | confirma, nueva fecha y hora, motivo, cancela | Fechas relativas ("el jueves que viene"), no prometer horarios que no están en la base, información de preparación del estudio |
| `demo_booking_classic` | El de venta vigente (ya existe) | los actuales | Base de referencia con llamadas reales; objeciones y preguntas fuera de la base |

Con eso hay 5 agentes: saliente de cobro, saliente de encuesta, saliente o entrante de datos,
saliente de turnos y saliente de venta. Atención al cliente entrante con derivación queda para una
segunda tanda.

## 3. Tipos de cliente (personas)

Cada agente tiene 6 personas. Una persona es: **estilo** (cómo habla y reacciona), **ficha** (los
datos verdaderos que sabe, y cuáles no va a dar) y **esperado** (campos finales con `None` donde el
agente no debe inventar, y el `outcome` correcto). Las fichas se generan con nombres, emails,
montos y fechas al azar por repetición, para que el modelo no pueda memorizar.

| Persona | Estilo | Qué mide |
|---|---|---|
| Cooperativo | Contesta lo que le preguntan, a veces da dos datos juntos | Piso: todo tiene que salir bien |
| Apurado | Respuestas mínimas ("sí", "no", "dale"), apura, corta si el agente se extiende | Brevedad, no repreguntar, cierre rápido |
| Confuso | No entiende, pide repetir, contesta otra pregunta, se va de tema | Reformular sin enojarse, volver al objetivo, no dar por respondido lo que no se respondió |
| Hostil | Se queja, cuestiona la legitimidad, insulta suave, amenaza con cortar | Tono, no discutir, respetar "no me llamen más" |
| Evasivo | No da datos, pregunta precios o cosas fuera de la base, cambia de opinión | Alucinaciones, "lo confirma un asesor", último valor dicho gana |
| Fuera de guion | Número equivocado, tercero que atiende, buzón de voz | No revelar información, cerrar bien, no seguir el guion con una máquina |

Más una **capa de canal** que se aplica sobre cualquier persona, como `stt_corpus/channel.py`
degrada el audio:

- `texto`: sin ruido (default, gratis).
- `stt-sim`: perturbaciones textuales de los errores medidos del STT: pérdida de tildes, homófonos
  ("Villa Belgrano" → "Villa de grano", "running" → "rolling"), email dictado partido en dos turnos,
  dígitos en palabras.
- `tts-stt`: el turno del cliente pasa por `vllm-tts` (una voz distinta a la del agente) → `tel8k`
  → `stt-parakeet`. Es el STT real, con ~0,4 s más por turno. Carga las GPUs en uso: correr cuando
  el stack esté libre.

## 4. Métricas

### Duras (por conversación, sin juez)

| Métrica | Cómo | Fuente |
|---|---|---|
| Datos ok / faltan / mal (inventados) | Campos extraídos contra la ficha, como `check()` de `replay_transcripts.py` | estado final |
| Resultado correcto | `outcome` contra el esperado de la persona | estado final |
| Terminó | El agente cerró (`[FIN]` o `completed`) antes del tope de turnos | traza |
| Turnos hasta cerrar | Eficiencia; también turnos después de tener todos los datos | traza |
| Repreguntas | Veces que pide un dato que el cliente ya dio (en `structured`, por `next_objective`; en `classic`, el juez) | traza |
| Loops | Respuestas iguales a la anterior; mismo objetivo 3+ turnos seguidos | traza |
| Reglas de voz rotas | Regex: markdown, símbolos, dígitos, siglas no permitidas, "usted", más de una pregunta por turno, más de 2 frases, precios o montos donde no corresponde | texto del agente |
| Largo de respuesta | Caracteres por turno → segundos de audio a ~17 car/s (`voces.tsv`): 200 caracteres son ~12 s de TTS | texto del agente |
| Latencia LLM | ms por turno de conversación y de extracción, p50 / p95 | traza `llm` del mensaje |
| Fallas de formato | JSON inválido (`structured`), `[FIN]` sin despedida, respuesta vacía | traza |

### Juez (LLM externo, rúbrica 1–5 con justificación, salida JSON)

Ve la definición del agente (reglas y base de conocimiento), la ficha de la persona y el transcript.

| Dimensión | Pregunta |
|---|---|
| Coherencia | ¿Responde a lo que dijo el cliente y recuerda lo que ya sabe? |
| Adherencia | ¿Cumple las reglas del workflow y dice solo lo que está en la base? Lista las afirmaciones que no están (alucinaciones) |
| Manejo de la persona | ¿Resolvió la objeción, la confusión o la hostilidad como pide el workflow? |
| Naturalidad | ¿Suena a una persona de Córdoba hablando por teléfono, con voseo, sin folleto? |
| Cierre | ¿Cerró en el momento correcto, con el mensaje correcto? |

Además del puntaje absoluto, un **modo pareado**: mismo escenario, dos modelos, el juez elige cuál
conversó mejor, con el orden al azar. Es más confiable que el puntaje absoluto para decidir entre dos.

**Calibración:** antes de confiar en el juez, el usuario califica ~20 conversaciones a ciegas con la
misma rúbrica y se mide el acuerdo. Si no acuerdan en una dimensión, se ajusta la rúbrica o esa
dimensión sale del criterio de decisión.

**Sesgo:** el juez no es el mismo modelo que el agente evaluado. Cuando DeepSeek sea el agente (techo
de referencia), decide con las métricas duras y el pareado.

### Criterio de decisión (propuesta, a ajustar con la línea base)

Un modelo es apto si, sobre todos los agentes y personas:

- datos ok ≥ 95 %, inventados ≤ 1 %, resultado correcto ≥ 90 %;
- 0 loops y ≤ 1 regla de voz rota cada 10 turnos;
- 0 revelaciones de deuda a terceros y 0 promesas fuera de la base (cobranza y turnos);
- juez ≥ 4 en cada dimensión, en el promedio de cada agente;
- y entre los aptos, gana el de menor latencia p50 por turno.

## 5. Modelos a comparar

| Modelo | Cómo se levanta | Por qué |
|---|---|---|
| Qwen3.5-9B w4a16 (vigente) | config actual | Línea base (EVAL-001) |
| Gemma 4 E4B QAT w4a16 | `docker-compose.gemma4-e4b.yml` (ya existe) | Alternativa del mismo tamaño |
| Qwen3.5-4B | override nuevo | El anterior; cuanto se pierde por bajar de tamaño |
| Qwen3.5-9B con pensamiento (`LLM_THINKING=true`, 128 tokens) | solo `.env` | Si el pensamiento corto mejora las personas difíciles a costa de ~0,8 s |
| DeepSeek por API como agente | `--llm-base-url` y `--llm-model` del script | Techo: cuánta calidad se deja por correr local. Solo `classic`: la API no soporta `json_schema` estricto |

Además, con el modelo vigente: `classic` contra `structured` con el mismo test, que hoy solo se
comparó con 3 llamadas reales.

Cada modelo local se levanta con su override (`make up-inference` para volver), se corre el test y se
registra `EVAL-NNN`. Cambiar el modelo obliga a recrear `vllm-llm`, `app` y `agent` (el nombre tiene
que coincidir); el test corre en el contenedor `app` con `docker compose run`, como `eval-motor`.

## 6. Código

```text
scripts/eval/
  run.py           corre agentes × personas × repeticiones contra el motor, en paralelo (asyncio,
                   8–16 conversaciones a la vez); guarda transcripts y trazas en runs/<ts>/conversaciones.jsonl
  simulador.py     el cliente: LLM externo con persona + ficha, salida JSON {"dice": ..., "corta": bool};
                   capas de canal (texto, stt-sim, tts-stt)
  checks.py        métricas duras
  juez.py          rúbrica absoluta y pareado; runs/<ts>/juez.jsonl
  analyze.py       summary.json y report.html: tabla modelo × agente × persona, peores conversaciones
                   con su transcript, comparación entre runs
  personas/*.yml   estilo, ficha (con campos al azar) y esperado, por agente
  guiones/*.yml    guiones fijos por objetivo (como replay_calls.py), regresión gratis y determinista
  runs/            no versionado
app/agents/reference/eval_*.json
docs/eval/README.md, EVAL-NNN-<slug>/
```

- **Dos modos de cliente:** `--cliente guion` (respuestas fijas por objetivo, sin API externa, para
  regresión y para el CI de prompts) y `--cliente simulado` (LLM externo, cobertura de reacciones).
- **Configuración en `.env`:** `EVAL_LLM_BASE_URL`, `EVAL_LLM_API_KEY`, `EVAL_LLM_MODEL` para el
  simulador y el juez (OpenAI-compatible; DeepSeek, o el propio `vllm-llm` para una prueba de humo
  sin costo). El agente usa las `VLLM_LLM_*` salvo `--llm-base-url` / `--llm-model`.
- **Make:** `make eval-llm ARGS="--reps 3 --agentes cobranza,datos"`, `make eval-llm-juez RUN=...`,
  `make eval-llm-report RUN=...`.
- **Reproducibilidad:** semilla para las fichas, mismo simulador y prompts en todos los runs, ≥ 3
  repeticiones por escenario (el agente muestrea con temperatura 0,7 y el simulador también varía).
  Los prompts del simulador y del juez llevan versión, que queda en `run.json`.
- **Costo estimado por run completo:** 5 agentes × 6 personas × 3 repeticiones = 90 conversaciones,
  ~900 turnos: ~900 llamadas al simulador (~1,5k tokens de entrada cada una) y 90 al juez (~3k).
  Del orden de 1,5 M de tokens de entrada en DeepSeek: centavos de dólar según la tarifa vigente.
  Tiempo: 10–15 min con 12 conversaciones en paralelo.

## 7. Fases

| Fase | Entrega | Cómo se valida |
|---|---|---|
| 0. Escenarios (medio día) | 4 workflows `eval_*`, 6 personas por agente con fichas, rúbrica | Una conversación a mano por agente con el modelo vigente, revisada por el usuario |
| 1. Test con métricas duras | `run.py`, `simulador.py` (canal `texto`), `checks.py`, `analyze.py` | EVAL-001 con Qwen3.5-9B: línea base; los peores casos revisados a mano |
| 2. Juez | `juez.py`, absoluto y pareado | Calibración con ~20 conversaciones calificadas por el usuario |
| 3. Comparación | EVAL-002 a 005: Gemma 4 E4B, Qwen3.5-4B, 9B con pensamiento, DeepSeek como techo; `classic` vs `structured` | Tabla comparativa en `docs/eval/README.md` y decisión de modelo |
| 4. Canal | `stt-sim` y `tts-stt` | Cuánto cae cada modelo con errores de STT; los casos de dictado |
| 5. Voz (opcional) | Los 10 peores escenarios reproducidos por voz con el caller del loadtest | El efecto del endpointing y del STT real sobre esos casos |

Las fases 1 a 3 alcanzan para elegir modelo. La 4 y la 5 dicen cuánto de lo que falla es del LLM y
cuánto del canal.

## 8. Límites

- Un cliente simulado por LLM es más paciente y más consistente que una persona real: reacciona a lo
  que le dicen pero no interrumpe ni habla encima. Los casos de interrupción los cubre el agente de
  voz (`CONTINUATION_WINDOW`), no este test.
- Las métricas duras miden lo que el workflow declara; el juez, lo demás. Ninguna reemplaza escuchar
  llamadas reales: las peores conversaciones de cada run son la lista de lo que hay que escuchar.
- La latencia acá es solo del LLM con poca carga. La capacidad sigue siendo tema de `CAP-NNN`.
