# Servidor de inferencia 3 GPUs: guía de hardware

Resumen de la investigación (septiembre 2026) para armar un segundo server con
3 × RTX 5060 Ti 16 GB: un modelo por GPU (STT, LLM, TTS), una instancia de vLLM
por modelo, sin tensor parallel, ~32 conversaciones concurrentes.

## 1. Idea central

**Sin tensor parallel, el PCIe casi no importa.** Por el bus solo viajan IDs de
tokens y audio: alrededor de 1 MB/s con 32 conversaciones. El ancho del slot solo
afecta cuánto tarda en cargar el modelo al arrancar.

Prueba real: en el server actual (2 × RTX 3090, B550M Pro SE), el LLM corre en
un slot Gen3 x4 detrás del chipset y llega al performance buscado.

Lo que sí importa para el tiempo al primer token:

1. **La GPU** (cómputo de prefill y ancho de banda de memoria).
2. **La CPU** (scheduler y tokenización de vLLM; ~7 procesos ocupados con 3 instancias).

## 2. Velocidades de referencia PCIe

Ancho de banda útil por dirección, en GB/s:

| Lanes | Gen3 | Gen4 |
|---|---|---|
| x1 | 1.0 | 2.0 |
| x4 | 3.9 | 7.9 |
| x8 | 7.9 | 15.8 |
| x16 | 15.8 | 31.5 |

- Regla práctica: **Gen4 xN = Gen3 x2N**.
- Cargar un modelo de 8 GB tarda ~8 s en Gen3 x1 y menos de 1 s en Gen4 x16.
- Tráfico real de este proyecto: ~0.001 GB/s. Hasta Gen3 x1 sobra en estado estable.
- La 5060 Ti es eléctricamente x8 (Gen5). Un slot x16 completo no le suma nada.

## 3. Placas AM4 revisadas

Todas las B550 económicas tienen la **misma topología**: un slot x16 desde la CPU,
un slot x4 desde el chipset, slots x1 y un M.2 directo a la CPU. El chipset B550
es solo Gen3, y su enlace con la CPU (Gen3 x4) lo comparten todos sus dispositivos.

| Placa | Formato | Slot CPU | Slot chipset | M.2 CPU | Notas |
|---|---|---|---|---|---|
| ASRock B550M Pro SE (server actual) | micro-ATX | Gen4 x16 | Gen3 x4 + x1 | Gen4 x4 | Venía con el slot principal forzado a Gen3 en la BIOS |
| Gigabyte B550M DS3H AC R2 | micro-ATX | Gen4 x16 | Gen3 x4 + x1 | Gen4 x4 | La más barata. Poco espacio físico. Alimentación del procesador modesta |
| MSI B550-A PRO | ATX | Gen4 x16 | Gen3 x4 + 2 × x1 | Gen4 x4 | Usar el M.2_2 deshabilita el slot x4 |
| ASRock B550 Pro4 | ATX | Gen4 x16 | Gen3 x4 + 2 × x1 | Gen4 x4 | Equivalente a la MSI |
| Gigabyte B550 UD WiFi6E | ATX | Gen4 x16 | 4 × Gen3 x1 (**sin slot x4**) | Gen4 x4 | Venex $189.999 efectivo. Trae un 2º M.2 del chipset (Gen3 x4). VRM 10+3. Solo HDMI |

**Gigabyte B550 UD WiFi6E (y su gemela B550 UD AC):** a diferencia de las otras, no
tiene slot físico x4. El enlace x4 del chipset sale por el segundo M.2 (M2B_SB,
Gen3 x4), así que el ancho de banda total es el mismo, pero cambia el armado:

- Solo 1 GPU va montada directo. Las otras 2 van por adaptador M.2 a PCIe x4
  (M2A_CPU y M2B_SB), y el sistema tiene que ir en SSD SATA (tiene 4 puertos).
- Alternativa para la 3ª GPU: slot x1 con riser (Gen3 x1, ~8 s más de carga del modelo).
- El manual no documenta que se compartan lanes entre los M.2 y los x1. Verificar
  después de armar que los 3 enlaces aparezcan con `nvidia-smi -q | grep -A3 "Link Width"`.
- Es la más barata de las ATX revisadas. Conviene si igual se arma en frame abierto
  con risers. Si se quieren 2 GPUs montadas directo, sirve más la MSI o la ASRock.

Referencia AM5 (precios Venex, efectivo):

| Placa | Precio | Comentario |
|---|---|---|
| ASRock B650 Pro RS WiFi | $294.990 | La mejor topología: x16 y x4 directos a la CPU, más M.2 Gen5 de CPU |
| ASUS Prime B840-Plus WiFi | $299.999 | 4 slots largos, pero el x4 baja a x1 al ocupar otro slot del chipset |

AM5 se descartó por costo: el procesador y la DDR5 encarecen mucho el conjunto.

## 4. Cómo elegir la placa

No mirar la generación PCIe. Mirar esto, en orden:

1. **¿Entran físicamente las GPUs?** Cada 5060 Ti ocupa 2 slots (elegir modelos de
   2 slots exactos, muchos son de 2.5). En ATX entran 2 montadas directo; la
   tercera va por riser o adaptador M.2.
2. **¿Quedan los 3 enlaces activos a la vez?** Leer en el manual las notas de
   lanes compartidos (ej.: un M.2 que apaga un slot).
3. **¿Hay un M.2 directo a la CPU libre?** Con un adaptador M.2 a PCIe x4 se
   convierte en un slot x4 de CPU para la tercera GPU.
4. **Salida de video en el panel trasero**, si se usa un procesador con video integrado.
5. Guiarse por la ficha del fabricante. Las publicaciones de las tiendas tienen errores.

Distribución recomendada en cualquier B550:

| GPU | Conexión | Enlace |
|---|---|---|
| GPU 1 (LLM) | Slot x16 | CPU, x16 |
| GPU 2 | M.2 de CPU + adaptador | CPU, x4 |
| GPU 3 | Slot x4 | Chipset, Gen3 x4 |
| Sistema | SSD SATA | Deja libre el M.2 de la CPU |

## 5. Detalles que ayudan a decidir

**Procesador (AM4, todos 8 núcleos / 16 hilos):**

| CPU | Cache L3 | PCIe | Video | Comentario |
|---|---|---|---|---|
| Ryzen 7 5700X | 32 MB | Gen4 | No | El ya validado en el server actual |
| Ryzen 7 5700G | 16 MB | Gen3 | **Sí** | BIOS y consola sin depender de las GPUs; toda la VRAM para vLLM |
| Ryzen 7 5700 | 16 MB | Gen3 | No | Mismo silicio que el 5700G, sin video. Solo si es claramente más barato |

- Gen3 en la CPU no afecta a este proyecto.
- La duda del 5700G / 5700 es la cache de 16 MB (estimado: 5 a 10% menos en el
  trabajo de CPU de vLLM). Se resuelve midiendo, ver sección 6.

**Risers:**

- Alimentación por PCIe de 6 pines. **Nunca por SATA**: la GPU toma hasta 75 W del slot.
- Los risers de minería por USB fallan a Gen4. Forzar Gen3 en la BIOS para ese slot.
- Mejor opción: riser de cinta certificado Gen4, o adaptador M.2 / OCuLink.
- Verificar después de armar: `nvidia-smi -q | grep -i -A2 replay` y
  `sudo dmesg | grep -iE 'aer|xid'`.

**GPU (el riesgo real del proyecto):**

| | RTX 3090 | RTX 5060 Ti 16 GB |
|---|---|---|
| Ancho de banda de memoria | 936 GB/s | 448 GB/s |
| VRAM | 24 GB | 16 GB |
| FP8 nativo | No | Sí |

- STT y TTS van a andar igual o mejor (hoy comparten una 3090).
- La incógnita es el LLM a concurrencia 32. Mitigación: pesos en FP8, prefix
  caching y ajustar `--max-num-batched-tokens`.
- **Comprar primero una sola 5060 Ti y correr el benchmark del LLM antes de comprar las tres.**

**Otros:**

- RAM: 32 GB alcanzan (hoy se usan 21 GB con escritorio incluido).
- Fuente: 850 W de buena calidad, con cables PCIe para 3 GPUs más los risers.
- Evitar placas de minería y kits X99 con Xeon: CPU lenta, que empeora el tiempo al primer token.
- Revisar en la BIOS que el slot principal no esté forzado a Gen3.

## 6. Prueba pendiente antes de comprar

Correr la carga a concurrencia 32 contra el server actual (puerto 8011) desde
otra máquina, y registrar:

```bash
mpstat -P ALL 1          # por núcleo: importa si uno llega a 100%
pidstat -u -r -h 1       # CPU y RAM por proceso
nvidia-smi dmon -s ut    # uso de GPU y tráfico PCIe real (MB/s)
docker stats             # CPU y RAM por contenedor
```

Para simular una CPU más débil: bajar la frecuencia 10%
(`sudo cpupower frequency-set -u 4.1GHz`) y limitar los contenedores a 6 núcleos
(`docker update --cpuset-cpus 0-5,8-13 <contenedor>`). Si el p95 del tiempo al
primer token no cambia, el 5700G es seguro.

Como la 3090 es más rápida que la 5060 Ti, la CPU medida acá es una cota superior.

## 7. Conclusión: mejor relación calidad / performance / costo

| Componente | Elección |
|---|---|
| Placa | **B550 ATX** (MSI B550-A PRO o ASRock B550 Pro4; Gigabyte B550 UD WiFi6E si se arma todo con risers) |
| CPU | **Ryzen 7 5700G** si la prueba de carga da margen; si no, 5700X |
| RAM | 32 GB DDR4-3200 (2 × 16) |
| Disco | SSD SATA para el sistema |
| 3ª GPU | Adaptador M.2 a PCIe x4 con alimentación de 6 pines |
| Fuente | 850 W |
| Gabinete | Frame abierto |

Por qué:

- Es la misma clase de hardware ya validada en el server actual, al menor costo.
- Gastar más en placa (Gen4 / Gen5, x8/x8, AM5) **no mejora** el tiempo al primer
  token en este uso. Esa plata rinde más en una GPU más fuerte para el LLM, si hiciera falta.
- ATX en lugar de micro-ATX cuesta casi lo mismo y permite montar 2 GPUs directo con aire entre ellas.
- El video integrado del 5700G simplifica el diagnóstico en un armado con risers.

Orden de pasos: (1) prueba de carga en el server actual, (2) comprar una 5060 Ti
y validar el LLM en FP8, (3) comprar el resto.
