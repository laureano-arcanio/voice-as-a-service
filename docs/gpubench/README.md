# gpubench — memoria y PCIe de una GPU

Mide la velocidad de la memoria de la GPU y de las transferencias host↔GPU, como % de la
especificación. Sirve para comparar GPUs, slots y risers con números reproducibles.

- Código: [`scripts/gpubench/`](../../scripts/gpubench/) (`gpubench.cu` + lanzador `gpubench.py`).
- Requisitos: `nvcc` y `nvidia-smi` (nada de Python extra). Compila solo la primera vez, en `scratch/gpubench/`.

## Cómo correrlo

1. **Dejar la GPU sin carga.** Ver `nvidia-smi`: si `vllm-*` o `stt-parakeet` la usan, los números salen bajos
   (el script avisa si ve procesos). Parar la inferencia solo si el usuario lo confirma (`make up-inference` la vuelve a levantar).
2. Anotar los límites vigentes (los de la 3090 en AGENTS.md: `-pl`, `-lgc`, `-lmc`), porque cambian el resultado.
3. Correr, guardando el JSON con nombre `AAAA-MM-DD-<gpu>-<detalle>.json` en `docs/gpubench/`:

```bash
make gpubench                                  # todas las GPUs
make gpubench ARGS="--gpu 0 --iters 20 --out docs/gpubench/2026-09-28-5060ti-x4.json"
```

Opciones: `--gpu N` (índice de `nvidia-smi`, repetible), `--iters` (corridas por medición, mediana; default 10),
`--size-mb` (transferencias PCIe, 256), `--mem-mb` (buffer de memoria, 1024; baja solo si no hay libre), `--rebuild`.
Para otra máquina: copiar `scripts/gpubench/` y correr `python3 scripts/gpubench/gpubench.py`.

## Qué mide y cómo leerlo

| Bloque | Medición | Referencia (100 %) |
|---|---|---|
| Memoria | lectura, escritura y copia con kernels; `cudaMemcpy` D2D. Buffer 1 GiB (mayor que el L2) | bus (bits) × reloj de memoria máx. × 2 / 8 |
| PCIe | H2D, D2H y ambos a la vez; pinned y pageable; barrido 4 KiB–256 MiB | GB/s por carril de la generación × ancho, por sentido |
| Latencia | pedido de 4 B en cada sentido y kernel vacío (µs) | — |

- **Memoria:** una lectura sana da ~90–95 % de la especificación; escritura y copia ~85–90 %. Si el reporte trae
  "especificación (reloj visto)", la memoria corrió a menos reloj que el máximo (bajo carga CUDA las GeForce pueden
  quedar en P2): comparar contra esa línea para separar "reloj bajo" de "memoria lenta".
- **PCIe:** un enlace bien armado llega a ~85–90 % con memoria pinned. El pageable rinde menos (copia intermedia en la CPU).
  Mirar la línea "PCIe … gen X xN en uso": si es menor que el máximo de la GPU, el slot o el riser limita.
  La suma de ambos sentidos se compara contra el doble de la especificación.
- **Relojes/potencia vistos:** si la potencia toca el límite o el SM está bajo lo esperado, el resultado está limitado por eso.

## Trampas

- El índice de `--gpu` es el de `nvidia-smi` (orden por bus PCI); el script fuerza `CUDA_DEVICE_ORDER=PCI_BUS_ID`.
- nvcc 12.0 no compila nativo para Blackwell (`sm_120`, hace falta CUDA ≥ 12.8): se incluye PTX de `compute_90` y el
  driver lo compila al vuelo. Con un toolkit nuevo se puede agregar `-gencode arch=compute_120,code=sm_120` en `build()`.
- Las GPUs sin ventilación o calientes bajan el reloj: comparar corridas a temperatura parecida (el JSON la trae).
- Otros procesos en la GPU (el escritorio dibuja en la 3090) restan un poco.

## Mediciones

Cada corrida guardada en este directorio (JSON con hw, relojes vistos y todos los números).

| Fecha | Archivo | Notas |
|---|---|---|
| 2026-09-28 | [`2026-09-28-5060ti-3090.json`](2026-09-28-5060ti-3090.json) | Server de validación, sin carga. 3090 con 280 W / mem 9501. 3090: lectura mediana 755 GB/s (mejor 888 = 95 %; con 10 corridas la mediana había dado 887; potencia en el tope de 280 W y el escritorio dibujando, así que mirar el "mejor" como techo y repetir si la mediana difiere mucho), PCIe gen4 x16 26,7 GB/s (85 %). 5060 Ti: lectura 214 GB/s (48 % del máx., 95 % del reloj visto: memoria a 7001 de 14001 MHz), PCIe gen3 x4 3,3 / 3,6 GB/s (84 / 91 %). |
| 2026-09-28 | [`2026-09-28-5060ti-x4.json`](2026-09-28-5060ti-x4.json) | 5060 Ti, gen3 x4, sin carga, 20 corridas, 69 W y 36 °C. Memoria a pleno reloj (13801 MHz): lectura 426 GB/s (95 %), escritura 423 (94 %), copia 382 (85 %). PCIe pinned H2D 3,31 / D2H 3,57 GB/s (84 / 91 %). Latencia 6,2 µs. La corrida anterior había quedado con la memoria a 7001 MHz (48 %): mirar siempre el reloj visto. |
| 2026-09-28 | [`2026-09-28-3090-350w.json`](2026-09-28-3090-350w.json) | 3090 sin límites (350 W), gen4 x16, 20 corridas, 311 W y 73 °C. Lectura 884 GB/s (94 %), escritura 788 (84 %), copia 756 (81 %). PCIe pinned 26,7 / 26,3 GB/s (85 / 84 %), pageable ~14 GB/s (~44 %). Latencia 4,3 µs. |
| 2026-09-28 | [`2026-09-28-3090-280w.json`](2026-09-28-3090-280w.json) | 3090 con los límites de AGENTS.md (280 W, mem 9501), 280 W y 66 °C. Igual que sin límites: lectura 882 GB/s (94 %), escritura 787 (84 %), copia 740 (79 %), PCIe pinned 26,7 / 26,3 GB/s. Memoria y PCIe casi no dependen del tope de potencia. |

## Valores de referencia para otras placas

Una placa sana en un slot bien armado, medida con 20 corridas y sin carga:

| Bloque | Esperable (% de la especificación) | Vistos |
|---|---|---|
| Lectura | 94–95 % | 3090: 94 %, 5060 Ti: 95 % |
| Escritura | 84–94 % | 3090: 84 %, 5060 Ti: 94 % |
| Copia (R+W) | 79–86 % | 3090: 79–81 %, 5060 Ti: 85 % |
| PCIe pinned H2D / D2H | 84 % / 84–91 % | 3090 x16: 85 / 84 %, 5060 Ti x4: 84 / 91 % |
| PCIe pageable | ~44 % en x16, ~84–90 % en x4 | 3090: 40–45 %, 5060 Ti: 84–90 % |
| Latencia 4 B | 4–6 µs | 3090: 4,3 µs, 5060 Ti: 6,2 µs |

- Por debajo de estos valores, mirar primero el reloj de memoria visto, el enlace PCIe en uso y la temperatura.
- En la 3090 la mediana de escritura y copia queda por debajo del mejor (escritorio y temperatura): comparar con el "mejor".
