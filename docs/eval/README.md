# Eval de calidad del LLM: resultados y registro

Qué tan bien conversa cada modelo LLM en los agentes más comunes (cobranza, relevamiento, toma de
datos, turnos, venta) con clientes cooperativos, apurados, confusos, hostiles, evasivos y fuera de
guion. Diseño en [`../EVAL_LLM_PLAN.md`](../EVAL_LLM_PLAN.md), código en `scripts/eval/`. Es por
texto: mide el LLM y el motor, no el STT ni el TTS (para eso, la capa de canal `tts-stt`).

## Resultados vigentes

Todavía no hay runs registrados. El primero es la línea base con Qwen3.5-9B w4a16 (EVAL-001).

## Índice

| EVAL | Fecha | Agente LLM | Motor | Cliente / canal | Datos ok | Cierre ok | Reglas / 10 turnos | Juez | LLM p50 |
|---|---|---|---|---|---|---|---|---|---|

## Cómo correrlo

Todo corre en el contenedor `app` contra el `vllm-llm` del stack (o contra otro LLM con
`--llm-base-url`). Las conversaciones se guardan en `scripts/eval/runs/<fecha>_<nombre>/`
(sin versionar).

1. **Sin API externa** (verificar el test, regresión de prompts): el cliente sigue los guiones fijos
   de `scripts/eval/personas/*.yml`.
   ```bash
   make eval-llm ARGS="--humo --cliente guion"          # 1 cooperativo por agente, ~1 min
   make eval-llm ARGS="--cliente guion --reps 3"        # todas las personas con guion
   ```
2. **Con cliente simulado** (la medición): `EVAL_LLM_API_KEY` en `.env` (DeepSeek directo por
   defecto). Con OpenRouter: `EVAL_LLM_BASE_URL=https://openrouter.ai/api/v1` y el modelo con
   prefijo de proveedor, por ejemplo `EVAL_LLM_MODEL=deepseek/deepseek-v3.2`. Cualquier endpoint
   OpenAI-compatible sirve; el pensamiento de Qwen se apaga solo en los endpoints locales.
   ```bash
   make eval-llm ARGS="--reps 3 --juez"                 # ~90 conversaciones + juez, 10-15 min
   make eval-llm ARGS="--agentes cobranza,datos --personas hostil,evasivo --reps 5"
   make eval-llm ARGS="--engine structured"             # el mismo agente con el motor estructurado
   make eval-llm ARGS="--canal stt-sim"                 # errores de STT simulados en el texto
   make eval-llm ARGS="--canal tts-stt --paralelo 4"    # TTS -> tel8k -> Parakeet reales (carga las GPUs)
   ```
3. **Otro modelo local:** levantarlo con su override (por ejemplo `docker-compose.gemma4-e4b.yml`,
   que recrea `vllm-llm`, `app` y `agent`), correr el mismo comando y volver con
   `make up-inference && make up-agent`.
4. **Un modelo por API como agente** (techo de referencia, solo motor `classic`):
   ```bash
   make eval-llm ARGS="--llm-base-url https://api.deepseek.com/v1 --llm-model deepseek-chat --llm-api-key-env EVAL_LLM_API_KEY --nombre deepseek"
   ```
5. **Juez y comparación:**
   ```bash
   make eval-llm-juez RUN=scripts/eval/runs/<run>                          # rúbrica 1-5 -> juez.jsonl
   make eval-llm-juez RUN=scripts/eval/runs/<A> ARGS="--pareado scripts/eval/runs/<B>"   # cuál conversó mejor
   make eval-llm-report RUN=scripts/eval/runs/<A> ARGS="--comparar scripts/eval/runs/<B>"
   ```

`--lista` imprime los escenarios sin correr nada. `--seed` cambia las fichas (nombres, emails,
fechas, puntajes); con la misma semilla, dos runs comparan los mismos escenarios.

## Qué mide

Por conversación (`checks.py`, deterministas): datos ok / faltan / mal contra la ficha (mal con
esperado vacío = inventado), cierre correcto, si terminó, turnos, respuestas repetidas y mismo
objetivo seguido (`structured`), reglas de voz rotas por regex (markdown, símbolos, dígitos,
siglas, usted, más de una pregunta, más de N frases, y las prohibidas de cada agente y persona),
largo de la respuesta en caracteres y segundos de TTS, latencia del LLM por turno y de la
extracción, errores. `problemas` las resume para ordenar las peores.

Con el juez (`juez.py`, LLM externo): coherencia, adherencia (con lista de alucinaciones), manejo
de la persona, naturalidad y cierre, de 1 a 5 con motivo; y repreguntas. Pareado entre dos runs.

## Registrar un run

`EVAL-NNN-<slug>/` con `README.md` (modelo, config, comando, tabla del resumen, hallazgos con
ejemplos de conversaciones), `summary.json` y `report.html` copiados del run. Sumar la fila al
índice de arriba y, si cambia la decisión de modelo, `AGENTS.md`.

## Trampas

- **Emails con punto o cifras:** `app.conversation.workflow.said()` exige que la parte local del
  email dictado esté en lo que dijo el cliente comparando solo letras y números, así que
  "lucia punto fernandez arroba" no valida `lucia.fernandez`. Las fichas usan locales sin punto
  ni cifras para medir el LLM y no esa trampa del motor.
- **El simulador es un LLM:** es más paciente que una persona y no interrumpe. Con temperatura
  0,7 varía entre repeticiones; por eso ≥ 3 repeticiones y la misma semilla entre runs.
- **Juez y agente distintos:** cuando el agente es DeepSeek, decidir con las métricas duras y el
  pareado, no con el puntaje absoluto.
- **`tts-stt` usa las GPUs del stack:** correrlo con el stack libre y `--paralelo` bajo.
