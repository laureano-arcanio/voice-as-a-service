# Espacio de las grabaciones (MB por minuto de llamada)

Para la grabación completa ([`EQUIPO_TELEFONIA.md`](../features/EQUIPO_TELEFONIA.md#grabación-completa)) y los audios
por frase (`record_audio`). Medido el 11-nov-2026.

## Por formato

ffmpeg sobre frases reales de 16 kHz del entorno local, 169 s; estéreo con dos voces, continuo o alternado (cada lado
habla la mitad, silencio digital el resto: FLAC queda optimista, con ruido de línea sube).

| Formato | Mono | Estéreo (alternada – continua) |
|---|---|---|
| PCM 8 / 16 kHz (16 kHz mono: los audios por frase) | 0,96 / 1,92 | 1,92 / 3,84 |
| G.711 A-law 8 kHz (la troncal) | 0,48 | 0,96 |
| FLAC 8 kHz | 0,62 | 0,63 – 1,22 |
| FLAC 16 kHz | 0,89 | 1,00 – 1,96 |
| Opus 16 / 24 / 32 kbps | 0,12 / 0,18 / 0,22 | 0,12 / 0,17–0,18 / 0,22–0,25 |
| MP3 32 kbps mono / 48 kbps estéreo | 0,24 | 0,36 |

**Lo que usa la grabación completa:** Opus 24 kbps estéreo a partir del crudo de Asterisk (8 kHz, 16 bits, 1,92 MB/min).
Con dos archivos reales de `make e2e-sip` convertidos por `app/services/line_recordings.py`: 32.651 B en 11,0 s y
29.735 B en 9,0 s, **0,18–0,20 MB/min**. El crudo vive en el spool solo hasta que se convierte (segundos).

## Producción (server2, 11-nov-2026)

- Disco de datos `/mnt/storage-server-region-2` (`RECORDINGS_DIR=…/audios`): 687 GB, 4,5 GB usados, **676 GB libres**;
  `/`: 309 GB libres de 466.
- Audios por frase: 130 MB en 720 WAV.
- Minutos de llamada: oct-2026 26 llamadas / 23 min; nov-2026 (1 al 11) 83 / 75 min, ~205 min por mes al ritmo de
  noviembre.
- Los audios por frase dan ~1,3 MB por minuto de llamada (130 MB / 98 min; cota alta: no todas las llamadas graban),
  7 veces Opus 24 estéreo.

## Capacidad

En 676 GB con Opus 24 kbps estéreo (0,18 MB/min): ~3,75 millones de minutos, **~62.600 horas**.

| Volumen mensual (sobre 205 min/mes) | Opus 24 estéreo por mes | Se llena en | G.711 estéreo por mes | Por frase hoy (1,3 MB/min) |
|---|---|---|---|---|
| Actual, ~205 min | 37 MB | siglos | 0,2 GB | 0,27 GB |
| x10, 2.000 min | 0,36 GB | ~150 años | 1,9 GB | 2,6 GB |
| x100, 20.000 min | 3,6 GB | ~15 años | 19 GB | 26 GB (~2 años) |
| x1.000, 200.000 min | 36 GB | ~19 meses | 192 GB (~3,5 meses) | 260 GB (~2,5 meses) |

Supone todas las llamadas grabadas, cada columna sola; los backups del mismo disco (dentro de los 4,5 GB) se suman.

- Opus 24 kbps estéreo: la troncal es de banda angosta (16 kHz no agrega); 12 kbps por canal sobra.
- Sin rotación: se borra con la conversación, sin backup ([`INFRA.md`](../INFRA.md)). La alerta de disco avisa al 85 %
  (`deploy/monitoring/rules.yml`).
- Lo que crece primero son los audios por frase (7 veces más por minuto). Al 50 % del disco, object storage (R2/MinIO)
  o la copia S3 ya implementada.
