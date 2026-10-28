# Evals de calidad

Qué tan bien conversa un LLM como agente: por tipo de agente, con clientes difíciles y, aparte, con
herramientas y con el MCP. Complementa al test de capacidad ([`../capacity/`](../capacity/README.md)), que mide
cuántas llamadas aguanta el pipeline.

**Los evals informan, no bloquean** (`AGENTS.md`, "Reglas de desarrollo"): miden y reportan qué falla y siempre
terminan en 0. Los escenarios, personas y agentes `eval_*` no se ajustan para que pase un modelo; una
expectativa se corrige solo si estaba mal escrita, y se anota por qué. Que el código ande lo prueba `make test`
con LLM falso.

## Targets

| Target | Qué mide | LLM | Código |
|---|---|---|---|
| `make eval-llm` | Conversación por tipo de agente × persona (este doc) | `vllm-llm` o `--llm-base-url` | `scripts/eval/run.py` |
| `make eval-llm-juez RUN=...` | Rúbrica del juez sobre un run; `--pareado <otro run>` | `EVAL_LLM_*` | `scripts/eval/juez.py` |
| `make eval-llm-report RUN=...` | `summary.json` y `report.html`; `--comparar <otro run>` | - | `scripts/eval/analyze.py` |
| `make eval-tools [LLM=openrouter] [REPS=3]` | Llamadas a herramientas: cuál, argumentos, de más, uso del resultado, latencia | `local` u `openrouter` | `scripts/tools/eval.py` (agente `eval_tools`, API falsa) |
| `make mcp-eval [MODELS=...]` | Si el modelo elige bien entre las herramientas del MCP | OpenRouter (gasta tokens) | `scripts/mcp/eval_tools.py`, detalle en `scratch/mcp-eval/` |
| `make eval-motor` / `make eval-llamadas` | Escenarios y llamadas reales repetidas contra el motor | `vllm-llm` | `scripts/replay_calls.py`, `scripts/replay_transcripts.py` (**rotos**, ver Pendientes) |

## Agentes y personas (`make eval-llm`)

Por texto: corre el motor (`ConversationEngine` + `LLMClient`) con `ConversationStore("sqlite://")`, sin
LiveKit, STT ni TTS, en el contenedor `app`. Un run completo (5 agentes × 6 personas × 3 repeticiones, ~90
conversaciones) tarda 10–15 min. Corridas en `scripts/eval/runs/<fecha>_<nombre>/` (sin versionar).

| Grupo (`personas/<grupo>.yml`) | Agente (`app/agents/reference/`) | Qué pone a prueba |
|---|---|---|
| `cobranza` | `eval_cobranza` | Firmeza sin intimidar, no revelar la deuda a un tercero, montos y fechas |
| `relevamiento` | `eval_relevamiento` | Encuesta 0–10 y opciones: respuestas ambiguas, no inducir, no saltear |
| `datos` | `eval_datos` | Dictado de email, teléfono, dirección y DNI; correcciones |
| `turnos` | `eval_turnos` | Fechas relativas, no prometer horarios fuera de la base |
| `demo_booking` | `demo_booking` | Venta: objeciones y preguntas fuera de la base |

Personas por agente: **cooperativo** (piso), **apurado** (brevedad), **confuso** (reformular, volver al
objetivo), **hostil** (tono, respetar "no me llamen más"), **evasivo** (alucinaciones, último valor dicho gana),
**fuera de guion** (número equivocado, tercero, buzón). Cada una trae ficha (datos verdaderos, al azar por
`--seed`) y esperado (campos, con `null` donde no hay que inventar, y `outcome` aceptables).

- **Cliente** (`--cliente`): `simulado` (default; LLM externo con persona + ficha, `scripts/eval/simulador.py`,
  `EVAL_LLM_BASE_URL`/`EVAL_LLM_API_KEY`/`EVAL_LLM_MODEL` en `.env`, DeepSeek por defecto) o `guion` (respuestas
  fijas de `personas/*.yml`, sin API externa).
- **Canal** (`--canal`): `texto`; `stt-sim` (errores de STT simulados en el texto); `tts-stt` (el turno pasa por
  `vllm-tts` → tel8k → `stt-parakeet` reales: carga las GPUs del stack).

## Métricas

**Duras** (`checks.py`, deterministas): datos ok / faltan / mal contra la ficha (mal con esperado vacío =
inventado), resultado correcto, si terminó (`end_call`), turnos, respuestas repetidas, reglas de voz rotas
(markdown, símbolos, dígitos, siglas, usted, más de una pregunta, más de N frases y las prohibidas del agente),
largo en caracteres y segundos de TTS (17 car/s), latencia del LLM por turno y de la extracción (p50/p95),
errores. `problemas` las pondera para ordenar las peores conversaciones.

**Juez** (`juez.py`, LLM externo): coherencia, adherencia (con lista de alucinaciones), manejo de la persona,
naturalidad y cierre, de 1 a 5 con motivo, más repreguntas. El **pareado** (mismo escenario, dos runs, orden al
azar) decide mejor que el puntaje absoluto.

**Criterio de referencia** para decir que un modelo es apto (sobre todos los agentes y personas): datos ok ≥ 95 %,
inventados ≤ 1 %, resultado correcto ≥ 90 %; 0 loops y ≤ 1 regla de voz rota cada 10 turnos; 0 revelaciones de
deuda a terceros y 0 promesas fuera de la base; juez ≥ 4 por dimensión. Entre los aptos, gana el de menor latencia
p50 por turno. Es un criterio para decidir, no una compuerta.

## Cómo correrlo

```bash
make eval-llm ARGS="--humo --cliente guion"                  # 1 cooperativo por agente, sin API, ~1 min
make eval-llm ARGS="--reps 3 --juez"                         # la medición: ~90 conversaciones + juez
make eval-llm ARGS="--agentes cobranza,datos --personas hostil,evasivo --reps 5"
make eval-llm ARGS="--canal tts-stt --paralelo 4"            # STT y TTS reales, con el stack libre
make eval-llm ARGS="--llm-base-url https://api.deepseek.com/v1 --llm-model deepseek-chat --llm-api-key-env EVAL_LLM_API_KEY --nombre deepseek"
make eval-llm-juez RUN=scripts/eval/runs/<A> ARGS="--pareado scripts/eval/runs/<B>"
make eval-llm-report RUN=scripts/eval/runs/<A> ARGS="--comparar scripts/eval/runs/<B>"
```

- `--lista` imprime los escenarios sin correr. Misma `--seed` entre runs = mismos escenarios.
- **Otro modelo local:** levantarlo con su override (por ejemplo `docker-compose.gemma4-e4b.yml`; el nombre del
  modelo tiene que coincidir en `vllm-llm`, `app` y `agent`), correr el mismo comando y volver con
  `make up-inference && make up-agent` (confirmar antes: recrea servicios en vivo).
- Con OpenRouter como simulador: `EVAL_LLM_BASE_URL=https://openrouter.ai/api/v1` y el modelo con prefijo de
  proveedor (`deepseek/deepseek-v3.2`).

## Registro

Todavía no hay ningún `EVAL-NNN`: ningún modelo está validado con el eval. El primero (EVAL-001) es la línea base
con Gemma 4 26B-A4B (LLM vigente).

Registrar un run: `docs/eval/EVAL-NNN-<slug>/` con `README.md` (modelo, config, comando, tabla del resumen,
hallazgos con ejemplos), `summary.json` y `report.html` copiados del run; sumar la fila abajo y, si cambia la
decisión de modelo, `AGENTS.md`.

| EVAL | Fecha | LLM del agente | Cliente / canal | Datos ok | Resultado ok | Reglas / 10 turnos | Juez | LLM p50 |
|---|---|---|---|---|---|---|---|---|

## Trampas

- **Dígitos:** el texto para el TTS lo normaliza `app/voice/speech_text.py`, así que la regla `digitos` cuenta como
  rota una respuesta que en voz sale bien.
- **Emails:** se guarda lo que extrae el modelo; las fichas usan partes locales sin punto ni cifras.
- **El simulador es un LLM:** más paciente que una persona, no interrumpe; varía con temperatura 0,7. Por eso ≥ 3
  repeticiones y la misma semilla.
- **Juez y agente distintos:** si el agente es el mismo modelo que el juez (DeepSeek), decidir con las métricas
  duras y el pareado.
- **Latencia:** es la del LLM con poca carga; la capacidad es tema de `CAP-NNN`.

## Pendientes

- EVAL-001 con Gemma 4 26B y calibrar el juez contra ~20 conversaciones calificadas a mano.
- `make eval-motor` y `make eval-llamadas` están rotos: `scripts/replay_calls.py` y `scripts/replay_transcripts.py`
  leen `turn.next_objective`, que ya no existe en `AgentTurn` (`app/conversation/models.py`).
- `scripts/eval/run.py` todavía escribe `"engine": "classic"` en `run.json` (lo muestra `analyze.py`).
- Sin eval de herramientas con el LLM propio todavía (`make eval-tools` con `LLM=local`).
