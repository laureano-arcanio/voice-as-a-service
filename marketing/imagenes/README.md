# API de imágenes (Qwen-Image-2.1 en vLLM-Omni)

Servicio de imágenes fijas del entorno de desarrollo (`192.168.1.99:8210`), no de producción. Lo usa el agente
[`videos`](../../.claude/agents/videos.md) para generar assets de las escenas
([`marketing/VIDEOS.md`](../VIDEOS.md)); el cliente es `marketing/videos/scripts/imagen.py`.
Imagen `vllm/vllm-omni:v0.32.0` + `vllm-gguf-plugin 0.0.5` + `bitsandbytes 0.49.2`
(derivada: `atentina/vllm-omni-qwen21:0.32.0`, ver `Dockerfile`).

## Reparto de memoria

| Componente | bf16 | Cuantizado | Cómo |
|---|---:|---:|---|
| DiT `QwenImage21Transformer2DModel` | 14,2 GB | 4,6 GB | GGUF Q4_K_M |
| Text encoder `Qwen3-VL-8B` | 17,5 GB | 4,5 GB | BitsAndBytes NF4 online |
| VAE | 1,35 GB | 1,35 GB | bf16 |

Pico medido con `nvidia-smi`: **10,5 GB** a 1024x1024, 20 pasos (el escritorio usa ~1,6 GB).
Una imagen 1024x1024/20 pasos tarda **25 s** (RTX 3090).

## Qué se probó y por qué quedó así

- **GGUF solo cubre el DiT.** El text encoder se queda en bf16 si no se cuantiza aparte:
  17,5 + 4,6 + 1,35 GB no entra y el arranque muere por OOM.
- **FP8 online del text encoder (`fp8_per_tensor`) no sirve en Ampere.** Entra en memoria
  (8,4 GB) pero en sm_86 vLLM usa el path Marlin weight-only y la imagen sale ruido.
  Medido con la misma semilla y el mismo DiT: ruido con FP8, imagen correcta con NF4.
- **BitsAndBytes NF4** es lo que entra y se ve bien. Necesita el `--diffusion-offload-config`
  de `text_encoder`: con `load_device=cpu` el loader cuantiza capa por capa y la devuelve a
  host; sin eso el encoder bf16 (17,5 GB) queda residente y revienta antes de cuantizar.
- **GGUF: hace falta un repo con layout diffusers.** `azukivc/Qwen-Image-2.1-GGUF`
  (`qwen-image-2.1-Q4_K_M.gguf`, 4,6 GB) trae `img_mlp.gate_layer/proj/out`,
  `attn.to_q/to_k/to_v`, `txt_in.*`, `modulation.1`, sin prefijo. El GGUF de
  `unsloth/Qwen-Image-2.1-GGUF` usa layout ComfyUI (`model.diffusion_model.*`,
  `img_mlp.gate_up`) y no carga: el adapter `QwenImageDiffusionGGUFAdapter` no remapea.
- **`--enforce-eager` es obligatorio.** Con `torch.compile` el dummy run falla al trazar
  con fake tensors (`split` sobre el qkv).

## Parches propios (`patches.py`)

1. `vllm-gguf-plugin 0.0.5` solo entiende un `quantization_config` plano; se le hace
   resolver el slice `transformer` de un `ComponentQuantizationConfig` para poder mezclar
   GGUF (DiT) con otro método (text encoder).
2. `DiffusionGGUFLinearMethod.apply` concatena los shards QKV con `torch.cat(result, axis=1)`:
   en tensores 3-D eso concatena sobre los tokens (3102 = 3x1034) y no sobre el hidden.
   Se reimplementa con `dim=-1`.
3. Entrada de arranque (`entrypoint.py`) que aplica los parches antes del CLI de vLLM-Omni.

## Uso

```bash
make imagenes-up                              # arranca el server en :8210
make imagenes-down                            # lo apaga
curl -s localhost:8210/v1/images/generations -H 'Content-Type: application/json' -d '{
  "model":"/models/Qwen-Image-2.1",
  "prompt":"a red apple on a white table, photo",
  "size":"1024x1024","n":1,"response_format":"b64_json",
  "num_inference_steps":20,"seed":42}'
```

## Datos en disco

- `/home/laureano/Models/Qwen-Image-2.1` — base del DiT, text encoder, VAE, scheduler,
  processor y tokenizer (~19 GB). `transformer/qwen-image-2.1-Q4_K_M.gguf` es un symlink al GGUF.
- `/home/laureano/Models/Qwen-Image-2.1-GGUF-azukivc/qwen-image-2.1-Q4_K_M.gguf`.
- No hace falta bajar `transformer/*.safetensors` (los 14,2 GB bf16): el GGUF los reemplaza.
- La imagen Docker derivada se construye con `make imagenes-build`
  (`vllm/vllm-omni:v0.32.0` + `vllm-gguf-plugin` + `bitsandbytes`).

## Concurrencia y optimización (medido, 19-nov-2026)

`max_num_seqs` por defecto en vLLM-Omni es **1**: las peticiones concurrentes se serializan.
Con `--max-num-seqs N` se batchean solo las peticiones *compatibles* (mismo tamaño).

| Caso | Tiempo total | Por imagen | Pico GPU |
|---|---:|---:|---:|
| 1 x 1024², 20 pasos | 26,1 s | 26,1 s | 12,6 GB |
| 4 x 1024², 20 pasos (concurrentes) | 97,8 s | 24,5 s | 19,7 GB |
| 6 x 1024², 20 pasos | OOM en el decode del VAE | — | 22,9 GB |
| 6 x 1024², 20 pasos + `--vae-use-tiling` | 172,7 s | 28,8 s | 18,3 GB |
| 1 x 512², 20 pasos | 7,9 s | 7,9 s | — |
| 8 x 512², 20 pasos (concurrentes) | 66,7 s | 8,3 s | 18,7 GB |
| 1 x 1024², 8 pasos | 12,7 s | 12,7 s | — |

Conclusiones:

- A 1024² la GPU ya está saturada con una petición: batchear 4 mejora el throughput solo ~6 %
  (26 → 24,5 s/imagen) y multiplica la latencia percibida (98 s). Para uso interactivo, dejar
  `--max-num-seqs 1`–`2` y tamaño 512².
- A 512² sí hay ganancia: 8 concurrentes rinden 8,3 s/imagen (vs 7,9 s una sola), es decir
  concurrencia casi gratis. `--max-num-seqs 8` ahí.
- El decode del VAE es el pico de memoria, no el denoise: 6 pedidos de 1024² mueren por OOM
  (pico 22,9 GB) y entran con `--vae-use-tiling` (pico 18,3 GB, 172,7 s). Sirve como válvula de
  memoria, no para ganar velocidad (a 1024² conviene 4 sin tiling: 24,5 s/imagen).
- Si el cliente no manda `num_inference_steps`, el default es **50** (~65 s a 1024²).
- `--enforce-eager` no cuesta velocidad (26,1 vs 27,4 s sin él): `torch.compile` no aporta acá.
- La caché de embeddings de prompt (`{"0":{"enable_prompt_embed_cache":true}}`) no cambió los
  tiempos porque el cuello es el denoise, no el text encoder.
- Palanca grande pendiente: variante Turbo/Lightning (4–8 pasos) o cambiar GGUF por una
  cuantización con kernels nativos (elimina el dequant por paso); hoy los GGUF Turbo públicos
  vienen con layout ComfyUI y no cargan en este adapter.

## Banco de pruebas (`bench/`)

`bench/prompt.txt` es el prompt estándar para comparar configuraciones y modelos: barista
sirviendo latte art, delantal con la palabra "ATENTINA" bordada, vapor, ventana al atardecer.
Ejercita lo que suele romperse: texto chico, manos, materiales y luz.

```bash
make imagenes-bench                            # 512x512, 12 pasos
make imagenes-bench SIZE=1024x1024 PASOS=20    # otra config
python3 marketing/imagenes/bench/bench.py --size 512x512 --steps 12 --seed 1234 --tag otra
# otro server o modelo:
python3 marketing/imagenes/bench/bench.py --url http://host:8210/v1/images/generations --model /models/Otro
```

Guarda la imagen en `scratch/imagenes-bench/img/<tag>.png` y agrega una fila a
`scratch/imagenes-bench/results.csv` (`wall_s`, `gen_ms`, `step_ms`, `peak_mb`).

| 512² | 8 pasos | 12 pasos | 20 pasos |
|---|---:|---:|---:|
| wall | 3,46 s | 5,64 s | 8,03 s |
| ms/paso | 428 | 466 | 400 |

| 1024² | 12 pasos | 20 pasos |
|---|---:|---:|
| wall | 18,22 s | 28,36 s |
| ms/paso | 1.510 | 1.413 |

Con este prompt, 12 pasos a 512² no muestra artefactos (texto y manos correctos) y 8 pasos
sigue siendo usable, un poco más blando.
