# experto-analisis · v2

Estado: borrador

- **Archivo:** `experto-analisis-v2.mp4` · 58,3 s · −16,3 LUFS (`make video-revisar P=experto-analisis V=2
  ARGS="--tramos 0,5.4,13.8,19.8,35.7,48.3,54.3"`).
- **Pedido (11-nov-2026, el usuario, por el coordinador, textual):** "quita la frase de con esta última quintuplicamos
  nuestra capacidad productiva, no tiene sentido en el contexto. Si hay algo mejor, alguna reseña que pueda mencionar,
  si no, no lo ponemos." El coordinador propuso la reseña que usa el PDF v2, sin nombre y en la voz de gonzalo.
- **Qué cambió respecto de v1 (cerrada antes de tocar el código):** solo la escena `cita`. Ahora es "LO QUE DICEN SUS
  CLIENTES": cinco estrellas y la reseña palabra por palabra, "**Gran asesoramiento** para quienes justamente no somos
  expertos.", con "Un cliente, en una reseña de 5 estrellas en Google Maps" y la línea "En Carlos Paz, cuatro de las
  cinco reseñas de 5 estrellas que muestra Google nombran a la misma vendedora." En pantalla va sin el "!" del original
  (regla de no usar signos de exclamación en pantalla). El resto, igual que v1; los "8 canales" de la tarjeta quedan.
- **Locución nueva:** a3 gonzalo "Lo dicen sus clientes: gran asesoramiento, para quienes justamente no somos expertos."
  (4,48 s; mejor de 4 tomas, fidelidad 1,00; TTS y STT de server2 por el proxy, como en v1). El resto de la locución es
  la de v1.
- **Controles:** `npx tsc --noEmit` sin errores; cuadro de la escena (`scratch/videos/experto-analisis-v1/v2-f579.png`)
  y hojas (`scratch/videos/revision/experto-analisis-v2/`) sin textos cortados; transcripción por escena igual al guion;
  la cola de a3 transcrita sola da "para quienes justamente no somos expertos" completa; a3 termina 0,9 s antes del
  corte de escena.
- **A revisar antes de mandarlo:** escuchar si a3 suena natural (el STT la oye bien; la decisión es de oído). a2 ya dice
  "un asesoramiento que sus clientes recomiendan", y la reseña lo retoma: funciona como remate, pero se puede cortar el
  final de a2 si suena repetido. Lo demás, como en v1: funciones sin desplegar o sin probar (derivación por WhatsApp,
  número propio de WhatsApp, desvío del 0800, métricas del panel por asesor y sucursal), panel ilustrativo y 7 u 8 canales
  en el PDF.
