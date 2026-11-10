# v1

Estado: cerrada (07-11-2026)

- **Pedido:** el del README (7-nov-2026): video de la propuesta del PDF v2, 60 a 90 s, paula y gonzalo en partes iguales, sin
  jerga, en blanco con intro y cierre.
- **Qué cambió:** primera versión.
- **Locución:** `make video-voces P=laestrella-propuesta TOMAS=4` con el TTS y el STT de server2 (`TTS_URL` y `STT_URL` al
  proxy `http://192.168.1.98:8100/{tts,stt}/v1`: el TTS local de .99 está parado). Fidelidad de las tomas elegidas: 0,91 a
  1,00; las bajas son por cómo escribe el STT números ("24", "0800", "10") y "atendida" → "tendida" (a12, a confirmar de
  oído). a9 y a10 se reescribieron una vez ("llega" → "se suma"; "Atiende el agente" sonaba "Atiende la gente").
  Voz: paula 37,0 s, gonzalo 33,6 s (52 / 48 %). `ganancia_db` −2,2 aplicada a las tomas elegidas (sin ajuste, −14,0 LUFS).
- **Controles:** 82,2 s; −16,3 LUFS; cuadros de cada escena y hojas cada 2 s (`scratch/videos/revision/laestrella-propuesta-v1/`)
  sin textos cortados ni superpuestos; transcripción por escena igual al guion.
- **A revisar antes de mostrarlo:** "+90 años" (89 en ene-2024), la lista de las 6 sucursales, el plazo de 10 días, el
  teléfono IP (equipo y quién lo instala), y que la etapa 1 (entrante al equipo) no tiene llamadas reales todavía. Las
  barras de la escena de datos son ilustrativas.
