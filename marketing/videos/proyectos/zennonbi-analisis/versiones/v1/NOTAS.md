# zennonbi-analisis · v1

Estado: borrador

- **Archivo:** `zennonbi-analisis-v1.mp4` · 75,6 s · −15,7 LUFS con `"ganancia_db": -1.5`
  (`make video-revisar P=zennonbi-analisis V=1 ARGS="--tramos 0,5.9,17.8,36.9,51.0,64.0,71.8"`).
- **Pedido (22-oct-2026, agente principal por Laureano):** el textual está en el [README](../../README.md). En
  resumen: el PDF `zennonbi-propuesta` v1 en video, "utiliza 2 voces como hicimos en axiom" (paula y lucas).
- **Voces:**
  - `paula` narra todo a 1×, salvo las cuatro líneas de producto.
  - `lucas` dice las cuatro líneas (b1 a b4), un bloque seguido con ~0,7 s de respiro entre tarjetas, como en
    axiomait-analisis. Sin alternancia en el resto. (VIDEOS.md pone a `pablo` como secundario: se siguió el pedido.)
- **Decisiones:**
  - Siete escenas en 75,6 s. La cita de Cristian va dentro de "Lo que ya hacen bien" (con su línea a3), no en una
    escena aparte, para no pasar de ~75 s; el modelo de alianza y el tablero comparten escena.
  - Líneas de producto: las dos destacadas del PDF (Sales/CRM KickStart y Customer Service) más Field Service y
    Customer Insights · Journeys (las que más se apoyan en lo que hay: campañas y WhatsApp); las otras cuatro, en chips
    "Y también". Contact Center queda en chip porque pide derivación a humano, que no existe.
  - "Journeys" no se dice: con lucas salió "SORNAYS"; se dice "Customer Insights" y la tarjeta lleva los dos nombres.
  - a2, a3, a4 y a6 se recortaron después de la primera tanda (iba a ~84 s). a6 decía "Zennon diseña el agente" y el
    STT oía "a la gente": quedó "Zennon lo diseña y lo conecta".
  - El tablero usa las cifras ilustrativas del PDF, rotuladas en la barra ("EJEMPLO CON DATOS ILUSTRATIVOS · UN MES") y
    en el pie.
  - Sin logos de Zennon ni de Microsoft: Dynamics 365, Dataverse, Power Automate, Power BI, Power Pages, Copilot Studio
    y Customer Insights, solo como texto; las cajas son genéricas, no imitan pantallas de Microsoft.
- **Locución** (mejor de 4 tomas; fidelidad con el STT, que escribe los números en cifras):
  - a1 paula "La línea de voz argentina de cada proyecto Dynamics que implementan." (1,00)
  - a2 paula "En Zennon implementan Dynamics desde dos mil dieciocho, con treinta y dos clientes que lo muestran." (0,76
    por las cifras y "Xenon")
  - a3 paula "Con la voz pasa lo mismo: el agente se arma con el conocimiento de cada cliente." (1,00)
  - b1 lucas "Dynamics Sales: el agente llama al lead apenas entra." (1,00)
  - b2 lucas "Customer Service: el número del cliente atiende a toda hora." (1,00)
  - b3 lucas "Field Service: las visitas, confirmadas el día anterior." (1,00)
  - b4 lucas "Customer Insights: un paso de llamada o de WhatsApp en el recorrido." (1,00)
  - a4 paula "Por dentro: Power Automate pide la llamada por ápi, el agente habla con el cliente, y el resultado vuelve a
    Dataverse." (0,99: "Dataverses")
  - a5 paula "Si el cliente llama, atiende el mismo agente y deja el caso. Y Power BI lo mide." (1,00)
  - a6 paula "La alianza: un módulo de voz en cada KickStart. Zennon lo diseña y lo conecta, y el cliente sigue siendo
    de Zennon." (0,97: "Xenon")
  - a7 paula "Atentina pone el número, la voz y el soporte, y cada llamada queda medida." (1,00)
  - a8 paula "Primero, una demo técnica con un Dynamics de prueba. Después, un piloto de treinta días con un caso real."
    (0,94: "demotécnica" y la cifra)
  - a9 paula "¿Agendamos una demo técnica?" (1,00)
- **Pronunciación:** grupo `zennonbi` en `scripts/candidatas.py` (dos tomas por texto), tomas en
  `scratch/videos/candidatas/zennonbi/`: "Zennon" y "Zénon" con paula, "Xenon" 4 de 4 (en el guion, una vez "Zenón");
  "ápi" y "API", bien; "Dataverse", "Detaverses"/"dataverses" con "ápi" y "Dataverse"/"Athers" con "API"; "Power
  Automate" bien salvo "Paolo Automate" (1 de 4); "KickStart" bien; "Power BI", "Power B" en 1 de 2; lucas, "Dynamic
  Sales" y "Customer Service" bien. Sin grafías nuevas; observaciones anotadas en la tabla de VIDEOS.md.
- **Controles:**
  - `npx tsc --noEmit` sin errores.
  - Cuadros de prueba de cada escena (`scratch/videos/zennonbi-analisis/`): se movió el rótulo de la vuelta del
    diagrama (pisaba la curva y el paquete), se acortó el pie del agente (pasaba a dos líneas), el título de la tarjeta
    de Journeys (dos líneas) y el texto de Zennon en la alianza (tocaba el tablero). Hojas en
    `scratch/videos/revision/zennonbi-analisis-v1/`: sin textos cortados ni superposiciones.
  - Transcripción por escena fiel a la locución, salvo "Xenon" (a2, a6), "y la gente se arma" (a3, en la mezcla; la
    toma sola da "el agente"), "Dataverses" (a4) y "demotécnica" (a8).
  - Cada voz termina antes de su corte (0,9–1,6 s de cola por escena).
- **A revisar antes de mandarlo:**
  - Escuchar cómo dice "Zennon" (el STT oye "Xenon"; confirmar cómo lo pronuncian en Zennon: "Zenon", "Zenón" o
    "Sénon"), "Dataverse" (riesgo de "Dataverses"), "el agente" en a3 y el cambio paula → lucas → paula.
  - Funciones mostradas que hoy no existen o no se usaron (zennonbi.md 7.4): conector de Power Automate (lo arma Zennon;
    falta la especificación de la API), resultado que "vuelve" en la entrante y en la saliente suelta (solo hay webhook
    de campañas; hoy, el resumen por email), llamadas salientes y campañas de voz (cero salientes, ningún tier con
    `voice`), "llama al lead apenas entra", "identifica al cliente" contra Dataverse, el paso de Journeys y la demo con
    "suena y la actividad aparece en el lead". Antes de la demo: habilitar `voice` y probar una saliente con números
    propios.
  - Datos ilustrativos: todo el tablero; los KickStart con su contenido son un ejemplo (rotulado).
  - Datos de Zennon leídos el 22-oct-2026: releer el sitio antes de mandarlo (lo siguen cambiando).
