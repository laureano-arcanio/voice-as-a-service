# Fine-tuning de Qwen3-TTS (una voz)

Cómo entrenar una voz propia sobre `Qwen3-TTS-12Hz-1.7B-Base` (o 0.6B), evaluarla y servirla
en `vllm-tts`. Lo sigue el agente [`tts-finetune`](../.claude/agents/tts-finetune.md).

Primera voz entrenada: `arf_03034` (OpenSLR 61, mujer, español argentino), sep-2026.

## Qué produce

Un checkpoint tipo `custom_voice`: la voz queda dentro del modelo y se pide por nombre
(`voice="arf_03034"`), sin audio de referencia. vLLM-Omni v0.28.0, la versión de `vllm-tts`,
lo sirve tal cual.

Frente al clon zero-shot (checkpoint Base + audio de referencia, como `sofia_ar`), con
32 frases y 2 semillas:

| | Clon zero-shot | Fine-tuning (lr 2e-6, época 5) |
|---|---|---|
| Similitud de voz (grabación real: 0,992) | 0,977 | 0,991 |
| WER, frases de dominio | ~1% | ~3% |
| Caracteres/s (grabación real: 18,1) | 15–16 | 17–18 |

La similitud la mide el mismo speaker encoder que da el embedding del checkpoint, así que
favorece al fine-tuning. La mayoría de los errores del WER es voseo que el ASR pasa a tuteo
("podés" → "puedes") y aparece igual en todos los modelos.

## Archivos

| Qué | Dónde |
|---|---|
| Código (versionado) | `tts/finetune/` |
| Datos, checkpoints, audios (no versionado) | `tts/finetune/work/` |
| Entorno | `tts/finetune/Dockerfile`: imagen de [mozi1924/Qwen3-TTS-EasyFinetuning](https://github.com/mozi1924/Qwen3-TTS-EasyFinetuning) fijada por digest, más `num2words` |
| Servir | `docker-compose.tts-ft.yml` (`TTS_FT_CKPT`, `TTS_FT_VOICE`) |

`tts/finetune/run.sh` corre cualquier comando en el entorno. La primera vez construye
la imagen `voice-tts-ft` (base de 25 GB). Monta:

| Host | Contenedor |
|---|---|
| `tts/finetune/` | `/code` (solo lectura, en `PYTHONPATH`) |
| `tts/finetune/work/` | `/work` |
| Volumen `voice-as-a-service_hf_cache` | `/hf` (offline: los modelos tienen que estar descargados) |
| `$OPENSLR_DIR/es_ar_{female,male}` (default `~/Downloads`) | `/src/...` |

Variables: `GPU=0|1|none` (default 0), `NET=host` para llegar a `vllm-tts` en 127.0.0.1.

Estructura de `work/`:
```
work/data/<voz>/            wav24k/, train_raw.jsonl, eval.jsonl, ref.wav, ref.txt, train_with_codes.jsonl
work/runs/<voz>/<corrida>/  checkpoint-epoch-N/, train_log.jsonl
work/eval/<voz>/eval/       <sistema>_s<semilla>/  (32 frases: 8 de eval + 24 de dominio)
work/eval/<voz>/llamada/    <sistema>_s<semilla>/  (28 oraciones de una llamada real)
```

| Script | Qué hace |
|---|---|
| `voice_minutes.py` | Minutos por voz de OpenSLR 61, brutos y con voz, para elegir la voz |
| `prep.py` | Limpia y recorta el audio, lo pasa a 24 kHz y separa train/eval y `ref.wav` |
| `prepare_data.py` | Pasa el audio a códigos del tokenizer de 12 Hz |
| `train.py` | Entrenamiento (SFT) con las correcciones y el optimizador de abajo |
| `gen.py` | Genera los sets `eval` y `llamada` con un checkpoint, o con el clon zero-shot |
| `score.py` | WER (Qwen3-ASR-1.7B), similitud de voz y caracteres/s |
| `pauses.py` | Pausas en el set `llamada` y página A/B para escuchar |
| `served_check.py` | Las mismas pausas contra `vllm-tts` levantado |

## Antes de empezar

1. **Tomar la GPU.** El stack se usa en vivo y puede haber otras sesiones: mirar `docker ps`,
   `nvidia-smi` y `git status`.
   - Entrenar el 1.7B necesita **17 GB**, así que hay que parar el servicio de esa GPU y
     **confirmarlo con el usuario antes**.
   - En este server: `docker stop voice-as-a-service-vllm-tts-1` libra la GPU 0.
   - Generar y evaluar necesita unos 5 GB y entra al lado de `vllm-tts`.
   - El 0.6B entrena con 7,2 GB.
2. **Modelos en el HF cache.** Hacen falta `Qwen/Qwen3-TTS-12Hz-1.7B-Base` (o `-0.6B-Base`)
   y `Qwen/Qwen3-ASR-1.7B`. Ya están si `vllm-tts` y `vllm-stt` corrieron alguna vez. Si falta
   alguno, bajarlo con `huggingface-cli download` en un contenedor con el volumen montado.
3. **Datos.** OpenSLR 61 descomprimido en `~/Downloads/es_ar_female` y `es_ar_male`
   (`line_index.tsv` + wav a 48 kHz, licencia CC BY-SA 4.0).

## Paso a paso

Todo desde `tts/finetune/`. Ejemplo con `VOZ=arf_03034`.

### 1. Elegir la voz

```bash
GPU=none ./run.sh python /code/voice_minutes.py
```

Mirar la columna **con voz**, no los minutos brutos: los clips de OpenSLR traen entre 20% y
50% de silencio. Las 41 voces completas tienen entre 5,6 y 8,9 min con voz (la mayor es
`arf_02121`). Tres voces tienen solo ~1 min y no sirven. Lo recomendado es tener 10 min o
más; con 6 min alcanzó.

### 2. Preparar los datos (CPU, ~15 s)

```bash
GPU=none ./run.sh python /code/prep.py --speaker $VOZ
```

- La transcripción sale del TSV del dataset, no de ASR: es el texto leído, con puntuación y
  números en palabras.
- Separa 8 frases de eval (semilla fija) y elige `ref.wav`, el clip de train más cercano a 6 s.
- **Revisar la última línea:** "clips de train con pausa interna >0,7 s" tiene que dar 0 o 1.
  Si da más, escuchar esos clips antes de entrenar (ver [Trampas](#trampas)).

### 3. Tokenizar (GPU, ~1 min)

```bash
./run.sh python /code/prepare_data.py --device cuda:0 --batch_size 16 \
  --input_jsonl /work/data/$VOZ/train_raw.jsonl --output_jsonl /work/data/$VOZ/train_with_codes.jsonl
```

Control: `len(audio_codes)` es ~12,5 × duración en segundos, con 16 códigos por frame.

### 4. Entrenar (GPU, ~3 min cada 10 épocas con 1.7B)

```bash
./run.sh python /code/train.py --sr --speaker_name $VOZ \
  --train_jsonl /work/data/$VOZ/train_with_codes.jsonl \
  --lr 2e-6 --num_epochs 10 --save_epochs 2,5,9 --output_model_path /work/runs/$VOZ/lr2e-6
```

- Con **`--sr` siempre**; sin él, casi no entrena (ver [Trampas](#trampas)).
- Otra configuración que vale comparar:
  `--lr 1e-5 --warmup_steps 10 --num_epochs 3 --save_epochs 2 --output_model_path /work/runs/$VOZ/lr1e-5`.
- Para 0.6B: `--init_model_path Qwen/Qwen3-TTS-12Hz-0.6B-Base`.
- Batch 2 × acumulación 4. Cada checkpoint ocupa 4,3 GB.
- Loss medio por época (arf_03034, 6,2 min de voz):

  | Época | lr 2e-6 | lr 1e-5 |
  |---|---|---|
  | 0 | 2,81 | 2,86 |
  | 2 | 1,93 | 1,43 |
  | 5 | 1,34 | — |
  | 9 | 1,02 | — |

  Con datos v1, lr 1e-5 bajaba a 0,30 en la época 9 y **sobreajustaba**: palabras trabadas y
  WER de dominio de 7,7%. No pasar de loss ~1 sin evaluar.
- Si cambian el optimizador o la versión de `qwen-tts`: `--probe 10` corta a los 10 steps e
  informa qué porcentaje de pesos cambió. Con `--sr` da ~20%; si da menos de 5%, los
  updates se están redondeando a cero.

### 5. Generar y evaluar (GPU ~5 GB, ~3 min por set y semilla)

Para cada checkpoint candidato, 2 semillas del set `eval` y 3 del set `llamada`:

```bash
C=/work/runs/$VOZ/lr2e-6/checkpoint-epoch-5; L=lr2e-6_ep5
for s in 0 1; do ./run.sh python /code/gen.py --model $C --speaker $VOZ --data /work/data/$VOZ \
  --set eval --seed $s --out /work/eval/$VOZ/eval/${L}_s$s; done
for s in 0 1 2; do ./run.sh python /code/gen.py --model $C --speaker $VOZ --data /work/data/$VOZ \
  --set llamada --seed $s --out /work/eval/$VOZ/llamada/${L}_s$s; done
```

Referencia, el clon zero-shot de la misma voz:
`gen.py --model Qwen/Qwen3-TTS-12Hz-1.7B-Base --mode clone --data /work/data/$VOZ ... --out .../clone_s$s`.

```bash
./run.sh python /code/score.py --data /work/data/$VOZ --out /work/eval/$VOZ/eval/score.json \
  --dirs $(cd work/eval/$VOZ/eval && for d in *_s*; do echo -n "$d=/work/eval/$VOZ/eval/$d "; done)
GPU=none ./run.sh python /code/pauses.py --root /work/eval/$VOZ/llamada --a <antes> --b lr2e-6_ep5
```

`pauses.py` con `--a/--b` arma `work/eval/$VOZ/llamada/ab_<a>_vs_<b>/index.html`, con los
turnos completos y las peores pausas lado a lado, para que el usuario escuche.

### 6. Criterios de aceptación

Valores medidos en arf_03034. Un checkpoint que falla cualquiera de estos no se sirve:

| Métrica | Umbral | Medido (lr 2e-6, ép. 5) |
|---|---|---|
| Pausas internas >0,7 s (set `llamada`, 84 oraciones) | ≤ 1 | 1 |
| Silencio entre oraciones >1 s | 0 | 0 (máx 0,80 s) |
| WER dominio (promedio de 2 semillas) | ≤ 4% | 3,3% |
| Similitud de voz | ≥ 0,985 | 0,991 |
| Caracteres/s dominio | 14–19 | 17,6 |

Entre los checkpoints que pasan, elegir el de menor WER y velocidad más cercana a la
grabación real. La elección final es del usuario, escuchando la página A/B y en una llamada.

### 7. Servir y verificar

```bash
cd ../..   # raíz del repo
TTS_FT_CKPT=./tts/finetune/work/runs/$VOZ/lr2e-6/checkpoint-epoch-5 TTS_FT_VOICE=$VOZ \
docker compose -f docker-compose.yml -f docker-compose.parakeet.yml -f docker-compose.tts-ft.yml \
  --profile stt-eval up -d --wait vllm-llm stt-parakeet vllm-tts agent
```

- El log de `vllm-tts` tiene que decir `Loaded 1 supported speakers: ['<voz>']`.
- Si la voz es la misma que la servida, alcanza con recrear `vllm-tts`.
- Para volver a `sofia_ar`: el mismo comando sin `-f docker-compose.tts-ft.yml`.

Verificación sobre lo servido (sin GPU):

```bash
cd tts/finetune
VLLM_API_KEY=$(grep ^VLLM_API_KEY= ../../.env | cut -d= -f2-) NET=host GPU=none \
  ./run.sh python /code/served_check.py --voice $VOZ --model $VOZ-ft
```

Con arf_03034 da 0/84 pausas >0,7 s, máximo 0,42 s. En llamada, el primer audio llega en
0,04–0,08 s por oración.

## Trampas

Todas medidas en arf_03034. No repetirlas.

1. **El click de fin de grabación de OpenSLR.** Muchos clips terminan con un click 2–3 s
   después de la última palabra, por ejemplo "¿Qué es un atasco?": se habla de 0,1 a 1,2 s y
   el click está en 3,8 s. Un recorte simple (`librosa.effects.trim`) toma el click como voz.
   - Con ese recorte, 36 de 135 clips quedaban con 1–3 s de silencio (68 s de 7,5 min).
   - El modelo aprendió a quedarse callado ~2 s, sobre todo después de las preguntas.
   - El usuario lo notó en la llamada. En el set `llamada` daba 7/84 pausas de hasta 2,0 s
     con lr 2e-6 y 27/84 con lr 1e-5.
   - `prep.py` descarta ruidos cortos (<150 ms) aislados (>300 ms) en los bordes y acorta las
     pausas internas a 0,3 s.
   - **Lección:** el loss y el WER no detectan esto. Hay que medir pausas en frases de una
     llamada y escuchar.
2. **bf16 + AdamW no entrena.** Con pesos bf16 y lr 2e-6, el update es menor que medio ulp y
   se redondea a cero. Con la receta pública (`sft_12hz.py` oficial y la imagen de mozi),
   10 steps cambian solo el **4,7%** de los pesos, aunque el loss baje. `train.py --sr` usa
   AdamW con redondeo estocástico: 22,8%. También congela el embedding de texto (311 M
   params) y el speaker encoder.
3. **Bugs del script oficial** (`QwenLM/Qwen3-TTS/finetuning/sft_12hz.py`, sep-2026):
   - Falta `text_projection` al entrenar: el modelo genera ruido (issue #39).
   - Doble shift de labels: la voz se acelera época a época (issue #179, abierto; la imagen
     de mozi también lo tiene).
   - El sub-talker tiene el mismo doble shift dentro de `qwen_tts` 0.1.1. El parche del fork
     zhyuan11 está malformado, así que `train.py` recalcula ese loss directamente.
4. **24 kHz obligatorio.** `dataset.py` hace `assert sr == 24000` para el audio de referencia.
   OpenSLR viene a 48 kHz y `prep.py` lo convierte.
5. **Idioma.** El entrenamiento usa el prefijo sin idioma. Generar con `language="Auto"`
   (default en `gen.py` y lo que manda el agente).
6. **Volumen de voces separado.** `docker-compose.tts-ft.yml` usa `vllm_tts_speakers_ft`.
   Con el volumen de siempre, vLLM-Omni restauraría `sofia_ar` (voz clonada, task Base)
   sobre un checkpoint `custom_voice`.
7. **Un solo speaker por checkpoint.** El entrenamiento oficial es de una voz; el nombre se
   guarda en minúsculas (`spk_id` 3000 en `config.json`).
