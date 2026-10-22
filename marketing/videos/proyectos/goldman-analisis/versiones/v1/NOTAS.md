# goldman-analisis · v1

Estado: cerrada (21-10-2026)

- **Archivo:** `goldman-analisis-v1.mp4` · 58,9 s · −15,4 LUFS (`make video-revisar P=goldman-analisis V=1
  ARGS="--tramos 0,4.9,14.8,20.3,32.6,41.7,53.7"`).
- **Pedido (21-oct-2026, Laureano, textual):** "hagamos otro video, similar pero que siga el formato del PDF. Con la
  introducción, qué hacen bien y qué observamos. Corto, 60 segundos." Con las reglas nuevas: logo en lugar del robot,
  tilde en la tónica en la locución, probar "aire", "En Isaías Goldman...", cierre "antes del pico de consultas", sin
  la marca de Goldman.
- **Qué es:** primera versión. Estructura del PDF `goldman-propuesta` v1: portada, lo que ya hacen bien (y la cita de
  Isaías), lo que observamos, lo que dicen sus clientes, la propuesta con el panel, y el piloto.
- **Locución** (`lucas`, mejor de 4 tomas; fidelidad entre paréntesis, baja solo por cifras que el STT escribe en
  números):
  - a1 "Que cada consulta tenga respuesta, y que ustedes las vean todas." (1,00)
  - a2 "En Isaías Goldman ya hicieron lo difícil. Treinta años en el rubro, unas cincuenta personas, y empresas como
    Arcor, Georgálos y Mostaza." (1,00)
  - a3 "Como dijo Isaías Goldman: nos gusta hacer cosas donde podemos responder." (1,00)
  - a4 "Lo que observamos: un solo número para todo. Doscientos sesenta y seis productos, ninguno con precio. Ciento
    veintiuna horas por semana, cerrado. Y en noviembre, arranca la temporada." (0,84: "266", "121")
  - a5 "Sus clientes los valoran, y lo que piden es poder comunicarse: un llamado que se devuelva, un presupuesto a
    tiempo, un aviso." (1,00)
  - a6 "Proponemos un especialista de guardia en el cero ochocientos, el WhatsApp y la web, que deriva a su equipo. Y
    un panel. Hoy, la atención se mide en reseñas. Con el panel, cada día." (1,00; la primera tanda dio "Cero 200" y
    se regeneró)
  - a7 "Empecemos un piloto en noviembre, antes del pico de consultas." (1,00)
  - La primera versión del guion daba 65 s de voz: se sacaron las reseñas de la locución (quedan en pantalla), la
    segunda frase de la intro, "de la semana" y "clasífica".
- **Grafías probadas** (`scripts/candidatas.py goldman-analisis`, dos tomas por texto, en
  `scratch/videos/candidatas/goldman-analisis/`): `Georgalos` (1 de 2 salió "Jorgalos"), `Yeorgalos` ("Sheorgalos",
  "Yorgalos") y `Georgálos` (2 de 2 bien): elegida `Georgálos`. `aire` / `áire`: el STT transcribe igual las dos; no
  quedó en la locución. "En Isaías Goldman ya hicieron lo difícil." bien en 2 de 2. Cifras ("mil seiscientas setenta y
  una", "ciento veintiuna de las ciento sesenta y ocho") bien.
- **Controles:** `npx tsc --noEmit` sin errores; cuadros de cada escena (`scratch/videos/goldman-analisis/`) y hojas
  (`scratch/videos/revision/goldman-analisis-v1/`): sin textos cortados ni superposiciones (se corrigieron dos títulos
  en dos líneas y el bloque de horas). Transcripción por escena fiel al guion.
- **A revisar antes de mandarlo:**
  - Escuchar `Georgálos` (que no suene "Georgalós" ni raro) y "Goldman".
  - Funciones de la oferta que no están construidas: derivación de la llamada, relay de WhatsApp, chat web, métricas
    del panel por canal, tipo, horario y persona; el 0800/0810 de ellos, a dar de alta con Anura.
  - Panel con números ilustrativos (lo dice en pantalla).
  - Las citas de reseñas son textuales (con sus faltas: "atencion", "via"), como en el PDF.
