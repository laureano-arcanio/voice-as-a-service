# axiomait-analisis · v1

Estado: borrador

- **Archivo:** `axiomait-analisis-v1.mp4` · 77,4 s · −15,5 LUFS con `"ganancia_db": -1.5`
  (`make video-revisar P=axiomait-analisis V=1 ARGS="--tramos 0,6.1,13.0,30.3,41.4,50.2,66.0,73.6"`).
- **Pedido (22-oct-2026, agente principal por Laureano):** el textual está en el [README](../../README.md). En
  resumen: el PDF `axiomait-propuesta` v1 en video, técnico y overview del producto, con paula y lucas, y "explicá que
  las voces pueden sonar mejor, dependiendo de la configuración y ajustando la latencia deseada".
- **Voces:**
  - `paula` narra todo a 1×, salvo las cuatro líneas de Axioma.
  - `lucas` dice las cuatro líneas (b1 a b4), un bloque seguido con ~0,7 s de respiro entre tarjetas: el contrapunto
    "lo que ya venden ustedes". Sin alternancia en el resto.
- **Decisiones:**
  - Duración 77,4 s, algo por encima de los ~75 pedidos: lucas es lento (~3,5 s por línea corta) y la escena de voces
    lleva tres líneas para la explicación pedida. Ya se recortaron a4, a5, a7 y a9 y se sacó la línea de paula que
    abría `lineas` ("Y el teléfono encaja en cada línea que ya venden."): el título de la escena la reemplaza.
  - El largo de cada escena sale de la locución (`timeline.ts`), y cada tarjeta entra con su palabra (`en()`).
  - "Lo que ya hacen bien" usa las cuatro cifras del PDF; "Atentina, en cuatro datos" va en la portada.
  - Sin logo ni marca de Axioma: su nombre va escrito. Google, Clutch, Odoo y Bureau Veritas, solo como texto.
- **Locución** (mejor de 4 tomas; fidelidad con el STT, que escribe los números en cifras):
  - a1 paula "Sumen voz a lo que ya venden: Odoo, agentes de IA y turnos." (0,94: "odú")
  - a2 paula "En Axioma ya entregaron más de cien proyectos, con clientes que se quedan, y cinco estrellas en sus
    reseñas." (0,92 por las cifras; "Axioma" bien en la toma, "En Acción" en el video mezclado)
  - b1 lucas "Odoo y CRM: llamar a cada lead a tiempo." (0,98: "Odo")
  - b2 lucas "Agentes de IA: el mismo agente, también por teléfono." (1,00)
  - b3 lucas "TodoTurnos: una llamada para confirmar el turno." (1,00)
  - b4 lucas "Soporte Odoo: un primer nivel, a toda hora." (1,00)
  - a4 paula "Por dentro: una llamada, un WhatsApp o el navegador llegan al mismo agente, que escucha, decide y habla,
    en Argentina. Todo queda en el panel y sale por ápi." (1,00)
  - a5 paula "Lo que pidieron: el CRM crea la campaña por ápi, con la hora. El agente llama, califica y agenda, y un
    webhook devuelve el resultado." (1,00)
  - a6 paula "Son cuarenta y una voces argentinas, y pueden sonar mejor: depende de la configuración y de la latencia que
    elijan." (0,92 por las cifras)
  - a7 paula "Con menos espera, responde antes. Con más, suena más fluida." (1,00)
  - a8 paula "Natural, pero honesto: el agente no niega ser una IA." (1,00)
  - a9 paula "Pueden probarlo hoy, sin hablar con nadie. Después, una demo técnica y un piloto de treinta días con sus
    leads." (1,00)
  - a10 paula "¿Agendamos una demo técnica?" (1,00)
- **Pronunciación:** grupo `axiomait` en `scripts/candidatas.py` (dos tomas por texto), tomas en
  `scratch/videos/candidatas/axiomait/`: "Axioma" con paula, "Acción Maya" y "Axioma"; "Odoo ... webhook ... CRM" con
  paula, "Odo/Workhook/Crm" y todo bien; lucas, "Odou y cierreme" y "Odo y CRM"; "TodoTurnos", "Todo turnos" (2 de 2).
  Sin grafías nuevas; observaciones anotadas en la tabla de VIDEOS.md.
- **Controles:**
  - `npx tsc --noEmit` sin errores.
  - Cuadros de prueba de cada escena (`scratch/videos/axiomait-analisis/`): se achicaron tres títulos que pasaban a
    dos líneas y pisaban las tarjetas, se ensancharon los canales, se acortó la banda de inferencia y una palanca, y
    se separaron los nodos del llamador para que entren los rótulos de las flechas. Hojas en
    `scratch/videos/revision/axiomait-analisis-v1/`: sin textos cortados ni superposiciones.
  - Transcripción por escena fiel a la locución, salvo "odú" (a1), "En Acción" (a2), "Odo" (b1, b4), "al mismo gente"
    (a4) y "no niega hacer una IA" (a8) en la mezcla con música; las tomas sueltas dan "Axioma", "agente" y "ser".
  - Cada voz termina antes de su corte (0,9–1,6 s de cola por escena).
- **A revisar antes de mandarlo:**
  - Escuchar "Axioma" en a2 (riesgo de "Acción"), "Odoo" en a1, b1 y b4 ("odú"/"Odo"), "CRM" y "webhook" (a5), "ápi"
    (a4, a5) y el cambio paula → lucas → paula.
  - Funciones mostradas que no están en uso: campañas de voz programadas con webhook (código desplegado, ningún tier
    con el canal `voice`, cero campañas y cero salientes); la demo técnica con campaña necesita antes habilitar `voice`
    y una prueba con números propios (axiomait.md 7.4). Voz a medida: se ofrece, requiere reentrenar.
  - La escala "responde antes ↔ suena más fluida" es conceptual (la espera de fin de turno, 0,4 a 1 s en
    `app/voice/worker.py`); no es un control con ese nombre en el panel.
  - Cifras: 0,87 s y 1,17 s son de una sola llamada (6 turnos); datos de Axioma leídos el 22-oct-2026; los dos JSON
    son ilustrativos (rotulados).
