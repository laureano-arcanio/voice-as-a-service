# yoizen-tu-propio-agente · v1

Estado: borrador

- **Pedido (26-oct-2026, Laureano, textual):** "Puedes crear en vez de un video, un slide tipo presentación para la
  demo con yoisen sobre cómo integrar sus agentes? 'Tu propio agente'. Es para mostrar en una llamada en vivo."
- **Archivos:** `documento.html` (fuente; se presenta abriéndolo en Chrome: `make slides-abrir`), `documento.pdf`
  (12 páginas de 1920 × 1080, 16:9, fuentes de la marca incrustadas) y `vista-01.png` a `vista-12.png` (una por
  diapositiva, 1920 × 1080).
- **Plantilla nueva:** `plantilla/slides.css` y `plantilla/slides.js` (16:9, navegación con teclado y contador),
  `scripts/render-slides.sh` y los targets `make slides` y `make slides-abrir`. `render.sh` y `base.css` no cambian,
  salvo que los dos scripts corren Chrome sin `DISPLAY` ni D-Bus: con la sesión gráfica del host, Chrome headless se
  colgaba sin imprimir (26-oct-2026).
- **Cambios durante el armado:**
  - la flecha "→" de los rótulos en mono salía con DejaVu Sans Mono (Plex Mono latin no la tiene): los rótulos de 5
    y 6 pasaron a "de Atentina al endpoint de Yoizen" / "del endpoint de Yoizen a Atentina";
  - 3, 6, 7, 8 y 12 desbordaban: títulos más chicos, listas compactas, columna de código al 1,35/0,65, línea de
    `messages = [...]` partida, contacto en dos líneas y títulos de los pasos en claro sobre el fondo oscuro
    (`.dark .step b`);
  - los mensajes del ejemplo HTTP se acortaron para entrar a 23 px.
- **Controles:** `make slides P=yoizen-tu-propio-agente V=1 DIAPOS=12` (12 diapositivas, 1440 × 810 pt, solo
  Bricolage, Figtree y Plex Mono); las 12 vistas revisadas (nada cortado ni tapado, código legible sobre fondo
  oscuro); el texto del PDF se copia (0800, dominios y mail como texto); modo pantalla probado con una captura a
  1280 × 720 (diapositiva centrada y escalada, contador "4 / 12"). Contacto igual al de `site.ts`.

## Notas del presentador

Lo que Laureano puede decir en cada diapositiva y qué objeciones esperar. No van impresas.

1. **Portada.** "Hoy no vengo a venderles la plataforma entera: la vieron el 20. Vengo a mostrarles una sola función
   que publicamos la semana pasada y que es exactamente lo que pidieron: sus bots deciden qué decir, nosotros
   ponemos la voz y el teléfono." Un minuto, y pasar.
2. **El punto de partida.** Repetir en una frase lo que ellos contaron (omnicanal, orquestador, Asterisk en camino) para
   que corrijan si hace falta. Objeción posible: "nosotros queremos construir la voz". Respuesta: "Pueden; esto es
   para tener voicebots en semanas y medir si el negocio existe, sin armar el pipeline."
3. **Quién pone qué.** Marcar que no tocan ni prompt ni modelo de nuestro lado: la conversación es de ellos. Objeción:
   "¿y los datos?" El texto de la conversación y los datos de la llamada viajan a su endpoint; el audio no sale de
   nuestros servidores (política de privacidad, excepción "Agente del cliente").
4. **Un turno.** Contarlo con el dedo sobre el diagrama: la persona habla, nosotros transcribimos y les mandamos todo,
   ellos contestan en streaming, lo decimos a medida que llega. Objeción: "¿cuánto agrega su parte?" No hay número
   publicado para este motor; en nuestro motor propio la mediana es 0,9 s en llamadas reales, y acá la parte de
   ellos se suma. Se mide en la prueba del paso 2.
5. **El pedido.** Lo clave: sin estado de su lado, formato de OpenAI, los datos en headers. "Si su orquestador ya
   expone algo tipo chat completions, es un adaptador chico." Objeción: "nuestro orquestador no habla OpenAI".
   Respuesta: el ejemplo de la diapositiva 8 es ese adaptador.
6. **La respuesta.** Insistir en que el streaming no es opcional: una respuesta JSON entera cuenta como error. Si su
   orquestador no hace streaming, el adaptador puede emitir el texto final en un solo pedazo, pero la latencia la
   pagan completa (diapositiva 10).
7. **Herramientas.** `end_call` elige el resultado que queda en el panel y en el webhook; `transfer_call` pasa a una
   persona de su equipo cargada en Atentina. Objeción: "queremos derivar a nuestro ACD". Hoy la derivación es a
   personas del equipo del cliente en Atentina (teléfono); la conexión SIP con su Asterisk sigue en evaluación.
8. **Endpoint mínimo.** No leer el código: señalar las tres partes resaltadas (prompt + headers, pedido al modelo con
   `tools`, stream tal cual). "Son veinte líneas; lo que vale es lo que ellos ya tienen detrás."
9. **Configurar.** Tres pasos del panel, y que todo sale por API y MCP (lo pidieron: configurar sin depender de
   nosotros). El aviso "Tu agente respondió" de la diapositiva 9 va sin cifra (el 420 ms del ejemplo de la documentación se sacó): no citar
   como dato.
10. **Latencia.** Sin cifras. Lo que pesa es el primer texto; más de un segundo se siente lento; consejo "texto
    primero, herramientas después". Desde Azure EE.UU. la red se suma: la medición del paso 2 lo dice.
11. **Errores.** Mensaje configurado, varios seguidos cortan o pasan al equipo, un turno bueno vuelve a cero. No decir
    que hay respaldo con nuestro modelo: no lo hay (ni hace falta decirlo).
12. **Próximos pasos.** Pedir dos cosas concretas: un endpoint con uno de sus bots y un caso real. Prometer solo lo
    de la propuesta del 20 (piloto; "sin costo" lo dijo Laureano ese día, acá no está escrito).

**Antes de la llamada, saber esto (estado al 26-oct-2026):** el motor está desplegado y la página publicada, pero
**todavía no hubo una llamada real de punta a punta con un endpoint externo** (solo tests con endpoint simulado y
un smoke test del ejemplo). Si piden una demo en vivo del motor `external`, decir que la primera llamada real la
hacemos con su endpoint en el paso 2; la demo en vivo que sí se puede hacer es la del agente propio (0800 o link).
Tampoco está medida la capacidad con el LLM actual: no afirmar "las llamadas a la vez que necesiten".
