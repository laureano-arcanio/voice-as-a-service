# Guía de la UI

Cómo hacer cada cosa desde la UI (`http://<host>:8011/`; en este server `http://192.168.1.99:8011/`;
desde internet, `https://app.atentina.com.ar/` cuando se publique). Todo lo que hace la UI también se
puede hacer por la API (`/api/v1/docs`, solo con sesión de admin). La arquitectura está en
[`ARQUITECTURA.md`](ARQUITECTURA.md).

Hay dos roles:
- **Cliente:** usuario de un cliente, que solo ve lo suyo. Menú (los grupos se despliegan con un click; arranca
  abierto el de la pantalla actual):
  - Inicio y Conversaciones, sueltos.
  - **Agentes:** Mis agentes, Probar agentes y Voces.
  - **Canales:** WhatsApp, Llamadas y Campañas.
  - **Organización:** Contactos y Equipo.
  - **Configuración:** Modelos y Apps.
  - **Developers:** API keys y Uso de la API.
  - **Cuenta:** Mi cuenta, Plan y Consumos.
- **Admin:** opera la plataforma y ve todo. El mismo menú sin lo que es solo del cliente (Modelos, API keys y
  Cuenta: las API keys de cada cliente están en su ficha), y al final, bajo "Administración": Clientes, Números,
  Tiers, Cobros y Usuarios.

## Primer ingreso

1. El primer admin lo crea `make migrate` con `ADMIN_EMAIL` y `ADMIN_PASSWORD` de `.env`. Otro admin
   o cambio de clave: `make create-admin EMAIL=...`.
2. Entrar en `/login` con ese email y clave. La sesión dura `AUTH_TOKEN_HOURS` (12 h). Con 5 intentos
   fallidos en 15 min desde la misma IP para el mismo email (o 10 para el email desde cualquier IP, o 20
   desde la IP con cualquier email), el login se bloquea un rato.
3. Arriba a la derecha: Salir. **Salir cierra todas tus sesiones**, también las de otros navegadores;
   cambiar la clave también.
4. Un usuario de cliente, la primera vez que entra, ve un pop-up de bienvenida: qué es la plataforma, los
   pasos para empezar y links a los videos de YouTube ("Qué es Atentina" y "Cómo crear y probar agentes",
   en `web/src/features/auth/WelcomeModal.tsx`). Al cerrarlo no vuelve a aparecer en ningún dispositivo
   (`users.welcomed_at`, migración 0027; los que ya habían entrado antes quedan como vistos).

## Puesta en marcha de un cliente nuevo (admin)

Orden recomendado: **tier → cliente → agente → número → usuario**.

### 1. Crear o elegir un tier (Tiers)

**Tiers > Nuevo tier**: nombre, descripción y límites. Un campo vacío significa ilimitado.
Los de la API de inferencia (abajo) arrancan en 0 = el plan no los incluye.

| Campo | Qué limita |
|---|---|
| Llamadas simultáneas | Llamadas en curso a la vez, de cualquier modalidad (incluye pruebas y loadtest). |
| Llamadas por hora, por día y por mes | Cantidad de llamadas (entrantes y salientes juntas) que se pueden empezar en la hora, el día o el mes calendario (hora de Buenos Aires): se renuevan al empezar la hora, a las 00:00 y el día 1. No cuentan las rechazadas por el tier ni las de prueba o loadtest. Son independientes: alcanza con agotar una. |
| Minutos entrantes por mes | Minutos de llamadas recibidas, por mes calendario (hora de Buenos Aires). |
| Minutos salientes por mes | Minutos de llamadas hechas por el agente. |
| Números | Cantidad de números de teléfono que puede tener asignados el cliente. |
| Canales de campañas | Qué campañas puede crear: WhatsApp, llamadas, las dos o ninguna. Los tiers que ya existían quedan con WhatsApp. |
| Campañas por mes | Campañas que puede iniciar en el mes calendario (cuenta al pasar de borrador a programada o en curso; cancelar no devuelve el cupo). |
| Contactos por campaña | Tope de destinatarios de una campaña. |
| Llamadas simultáneas por campaña | Tope de la concurrencia de una campaña de llamadas. |
| Contactos en la agenda | Contactos activos del cliente (los archivados no cuentan). |
| Seguimiento por WhatsApp | Si una campaña de llamadas puede escribirle por WhatsApp a quien no atendió. |
| Personas del equipo | Personas a las que el agente puede derivar una llamada o un chat (Equipo). |

- **Editar:** los cambios rigen en el acto, también para el mes en curso.
- **Bajar el tope de números:** no se puede si algún cliente de ese tier ya tiene más asignados.
- **Sacar un canal de campañas:** las campañas en curso o programadas de ese canal, de los clientes del tier,
  pasan a Pausada con el motivo. Lo mismo al cambiar a un cliente de tier.
- **Borrar:** solo si el tier no tiene clientes.

### 2. Crear el cliente (Clientes)

**Clientes > Nuevo cliente**: nombre, slug (se arma del nombre; minúsculas, números y `_`), tier y el
email de su primer usuario (con el nombre, opcional, para el saludo). Se crea ese usuario, sin clave, y
le llega un email de Atentina con el plan contratado y un link para crear su clave (vale 72 horas y se usa
una sola vez). Si el aviso dice que no se pudo mandar, o el link venció, **Usuarios > Reenviar invitación**
(el sobre de la fila). Te lleva a la ficha del cliente, que tiene cinco pestañas:

- **Consumo y datos:** consumo del mes con selector de mes (llamadas activas contra el tope,
  minutos entrantes y salientes, números usados, y las llamadas de la hora, el día y el mes si el tier tiene tope),
  el **consumo de la API** del mes contra el tier (tokens de
  entrada y salida del LLM, minutos de transcripción y de síntesis, pedidos por minuto y el desglose por key;
  no incluye lo que consumen los agentes integrados), y los datos del cliente:
  - **Cambiar el tier:** se rechaza si el tier nuevo permite menos números de los que tiene. Los ajustes del cliente se conservan.
  - **Ajustes de límites:** para darle algo distinto a un solo cliente sin tocar su tier (que comparten otros) ni
    armar uno nuevo. **Nuevo ajuste**: elegí el límite, si **suma** al del tier (ej. 10 minutos más, una línea más) o lo
    **reemplaza** (un tope propio; vacío = ilimitado), la cantidad, la vigencia (permanente, solo este mes o hasta una
    fecha) y un motivo. El modal muestra cómo queda ("Hoy: 100 min → 110 min"). Rige desde ya y los vencidos dejan de
    aplicar solos. Varios ajustes del mismo límite se suman. En la lista de clientes aparece "Ajustado". Quitar un ajuste
    o bajar un tope de números se rechaza si el cliente ya tiene más números de los que quedarían. El cliente ve el
    límite resultante en su consumo, sin distinguir el origen.
  - **Activo:** apagarlo impide hacer y recibir llamadas; las entrantes escuchan un aviso y se cortan.
  - **Borrar:** solo si el cliente no tiene conversaciones; si tiene, desactivalo.
- **Números**, **Agentes**, **Usuarios** y **API keys**: ver abajo.

### 3. Crear el agente (Agentes)

**Agentes > Nuevo agente**: cliente, nombre, slug (opcional), descripción, **motor** (Clásico, el de
por defecto, o Estructurado; lleva la píldora "interno") y **punto de partida**: el **asistente básico** (atiende, responde con la
base de conocimiento y, si no puede, toma nombre y contacto) o **en blanco** (un dato y el resultado
por defecto). Te lleva a la pestaña **Definición** para completarlo.

El detalle del agente tiene cuatro pestañas:

- **Resumen:** la definición en limpio: agente, idioma, versión, objetivo, apertura, reglas, base de
  conocimiento, datos a obtener (orden, tipo, obligatorio, pregunta sugerida) y resultados.
- **Definición:** un formulario por partes. El cliente ve el mismo, sin motor, **Ver prompt** ni JSON
  (ver [Agentes (cliente)](#agentes-cliente)):
  - **Agente:** nombre, rol, idioma y **motor** (Clásico, Estructurado o Asistente, en tarjetas). La definición es la misma con los dos primeros: cambiarlo no toca nada más. **Asistente** (solo admin) es el asistente personal con las herramientas de las apps del cliente ([`APPS.md`](APPS.md)): oculta Datos a obtener y Resultados (lo que haya queda guardado) y muestra **Herramientas**.
  - **Herramientas** (motor Asistente): un switch por cada app del cliente, con **Todas** o **Elegir** herramientas una por una. Las que borran o envían se confirman con el usuario antes de usarlas.
  - **Voz:** tarjetas con las voces (filtro por mujeres u hombres); al lado, la prueba con la voz elegida, con la apertura como texto (editable). **Grabar audio**: un WAV por mensaje de cada llamada (telefónica o de WhatsApp; el cliente y el agente por separado), localmente en el servidor; con **Avisar que la llamada se graba**, el agente lo dice antes del saludo. **Ventana de contexto en WhatsApp (minutos)**: minutos sin mensaje del contacto para que la próxima conversación arranque en limpio, sin el historial anterior; vacío usa el default del servidor (1440 min = 24 hs).
  - **Derivación a personas** (solo motor Clásico; con otro lo avisa y no se edita): las áreas del cliente (de
    **Equipo**, con su horario; si no tiene, un link para crearlas). **Puede pasarle llamadas** habilita cada área
    (hasta 10) y abre **Cuándo pasarla**, el criterio para el agente (vacío = la descripción del área). Un área
    inactiva queda marcada, pero el agente no la ofrece. Con alguna área, **Música de espera** (prendida por
    defecto): tema (**Música de espera estándar** o los que haya en el servidor) y volumen (5 a 100 %). Sin áreas
    marcadas no se guarda nada de esto.
  - **Objetivo y apertura**, **Reglas** (una por regla) y **Base de conocimiento**.
  - **Datos a obtener:** cada dato con etiqueta, nombre interno, tipo (texto, número, sí o no, opción
    de una lista, email, email o teléfono), si es obligatorio (sí, no o según otro dato), descripción
    y pregunta sugerida. Se ordenan con las flechas. Al renombrar uno, se actualizan las condiciones que lo usan.
  - **Resultados:** etiqueta, ID, si cumple el objetivo, mensaje de cierre y condiciones. Vale el
    primero que se cumple; el último es el de por defecto.
  - **Ver prompt:** el prompt que arma el motor con lo que está en pantalla, por llamada o por
    WhatsApp. No hay un prompt aparte para editar: sale de la definición.
  - **Formulario / JSON:** la misma definición en JSON (formato en [`ARQUITECTURA.md`](ARQUITECTURA.md#definición-de-un-agente)), para pegar o editar a mano.
  - **Validación:** se valida mientras editás; los errores aparecen arriba y, al hacerles click, te
    llevan al campo (o a esa parte del JSON).
  - **Guardar:** crea una **versión nueva**, o avisa "Sin cambios" si no cambió nada. Las llamadas en
    curso siguen con la versión con que empezaron.
  - `id` y `version` los pone la app (el slug y el número de versión): no hace falta tocarlos.
  - Si salís con cambios sin guardar, avisa.
- **Versiones:** historial con fecha y autor. Podés ver el JSON de cualquier versión, compararla con
  la vigente y **Restaurar**, que guarda esa definición como versión nueva.
- **Probar:** lo mismo que la pantalla **Probar agentes** (abajo), con este agente fijo.
  - **Probar por voz:** elegís la voz y **Probar agente** te lleva a la llamada en el navegador
    (`/calls/<id>/hablar`). Si este agente ya tiene una prueba esperando que alguien se conecte, entra a esa
    en vez de crear otra; si no, la crea. No marca teléfonos ni gasta minutos. Las salientes a un
    teléfono, en **Llamadas**.
  - **Conversación por texto:** chateás con el agente sin voz. Con el motor estructurado ves los datos
    que va extrayendo y el próximo objetivo en cada turno; con el clásico (el de por defecto), los datos
    aparecen al terminar la conversación.
  - **Link para llamar:** lo crea, o lo muestra para copiar o abrir; **Configurar** lleva a la pestaña
    Link para llamar (nombre, imagen, límites, pausar, regenerar).

**Agentes > Probar agentes** (`/probar`): elegís el agente en una tarjeta con su
objetivo (sale de la definición; con más de 6, hay buscador; el admin filtra por cliente) y abajo lo
probás igual que en la pestaña Probar. En la lista de Agentes, la columna **Probar** abre esa pantalla con
el agente elegido, y la columna **Link para llamar** muestra la URL del link con el botón para copiarla, o
**Crear link** si el agente todavía no tiene.

Arriba, **Editar** (nombre y descripción), **Archivar/Desarchivar** y **Borrar**:
- Un agente archivado no se puede usar en llamadas nuevas y queda en el historial.
- Borrar solo se puede si el agente nunca tuvo conversaciones; si tuvo, archivalo.
- Agentes > **Incluir archivados** los muestra en la lista.

### 4. Números de teléfono (Números)

Los números los provee Anura. El flujo es: **cargar al inventario → asignar a un cliente → elegir el
agente**.

1. **Números > Cargar números:**
   - Pegás los números, uno por línea o separados por coma, en E.164 o con espacios y guiones
     (`+54 351 700-3976`), con etiqueta y proveedor (default `anura`).
   - La vista previa cuenta válidos, inválidos y repetidos. Al cargar, muestra cuántos entraron y los
     salteados con el motivo.
   - Los números de Anura van como `+54` + 10 dígitos, sin el 9 de celular (ej. `+543517003976`).
2. **Asignar** a un cliente, desde Números o desde la ficha del cliente (pestaña Números > Asignar
   número, que elige entre los libres):
   - Los clientes sin lugar en su tier aparecen deshabilitados.
   - Desde Números se puede elegir el agente en el mismo paso; desde la ficha del cliente se elige
     después, en la fila del número. **No lo dejes sin agente**: un número sin agente corta las
     entrantes.
3. **Agente:** en la fila de cada número, el agente del cliente que atiende las entrantes a ese
   número. Lo puede cambiar el admin o el propio cliente desde Mi cuenta.
4. **Liberar:** devuelve el número al inventario, sin cliente ni agente, y sus entrantes dejan de
   atenderse. **Borrar:** solo los libres.

Al **cargar o borrar** números, la app los agrega o quita sola del trunk entrante de LiveKit, en
caliente: no hay que reiniciar nada ni se cortan llamadas.

**Varios números en la misma cuenta de Anura:** cada entrante va al agente del número marcado (Anura
manda el número en la llamada, verificado el 29-sep-2026). Si no llega un número válido, va al número
principal de la cuenta (`ANURA_DID`). Ver [`TELEFONIA_ANURA.md`](TELEFONIA_ANURA.md).

### 4b. WhatsApp (admin)

El cliente conecta sus números solo (ver [WhatsApp (cliente)](#whatsapp-cliente)); el admin ve todos,
filtra por cliente y también puede usar **Conectar WhatsApp** eligiendo el cliente. El **alta manual**
es para números de nuestro portafolio.

Conecta un número de WhatsApp Business a un agente del cliente. Responde texto y notas de voz: si el
contacto manda un audio, el agente lo transcribe y contesta con una nota de voz con la voz del agente
(ver [`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md)).

1. **WhatsApp > Alta manual:** cliente, agente que responde, **Phone number ID** y **WABA ID**
   (de Meta: WhatsApp → Configuración de la API; el ID, no el teléfono), número visible y nombre.
2. **Token:** vacío usa el del system user (`WA_ACCESS_TOKEN`). Uno propio solo para números de otro
   portafolio; no se vuelve a mostrar (la tabla dice "Propio" o "Global").
3. **Editar:** agente por defecto, número visible, nombre y token. El agente nuevo vale para las
   conversaciones nuevas; las en curso siguen con el suyo.
4. **Ruteo por contacto** (menú de la fila): agrega uno o más agentes y, a cada uno, la lista de
   contactos que atiende (el WhatsApp con código de país, ej. `5493511234567`; Enter después de cada
   uno). Esos contactos los atiende ese agente en los mensajes y las llamadas de WhatsApp; los demás,
   el agente por defecto. Los operadores siguen por encima. Se ve debajo del agente ("N reglas por
   contacto").
5. **Desactivar:** los mensajes a ese número dejan de responderse. No hay borrado: las conversaciones
   lo referencian. **Activar** lo vuelve a habilitar.

Si el cliente está desactivado, sus números de WhatsApp tampoco responden.

**Operadores** (en WhatsApp, solo admin): el dueño de un negocio que le habla a su asistente por un
número compartido. Se carga el número, el contacto (`wa_id`, sin +, como `5493511234567`), el
cliente y un agente de ese cliente. Los mensajes de ese contacto a ese número los atiende el agente
del operador; los demás contactos siguen con el agente del número. Se puede cambiar el agente,
desactivar o borrar.

### 4c. Apps del cliente (Apps)

Las apps son los contenedores de `atentina-apps` ([`APPS.md`](APPS.md)): aparecen solas cuando se
registran con `make register` desde ese repo.

- **Admin:** ve todas y filtra por cliente. Por cada app: versión, estado (Responde, No responde o
  Inválida, con el motivo), cliente, vistas y herramientas (las que borran o envían, resaltadas) y
  último chequeo. Acciones: **Asignar** a un cliente, **Liberar** (vuelve al inventario y revoca sus
  links), **Releer** el manifest (después de una versión nueva) y **Borrar** (solo del inventario).
- **Ambos roles:** **Link a una vista** (elegir la vista y, si hace falta, parámetros como
  `fecha=2026-10-12`): muestra la URL una sola vez, con botón de copiar. **Ver links:** quién los
  creó, cuándo vencen, cuántas veces se abrieron, y revocar.

Para que un dueño use su app: asignarla, crear un agente con motor **Asistente** y la app en
**Herramientas**, y cargarlo como **Operador** del número.

### 5. Usuarios y API keys del cliente

- **Usuarios** (en el menú, o en la pestaña Usuarios de la ficha del cliente) > **Nuevo usuario**:
  - email, nombre, clave (10 caracteres o más) y rol;
  - rol **cliente**: hay que elegir el cliente;
  - rol **admin**: no pertenece a ninguno.

  Desde la tabla se editan el nombre, la clave y el estado activo, y se borra. Desactivar un usuario
  corta su sesión en el acto. Nadie puede desactivarse ni borrarse a sí mismo.
- **API keys** (pestaña **API keys** de la ficha del cliente, o **Developers > API keys** en el menú del cliente) > **Nueva API key**
  (en la ficha del admin, el consumo de la API está en **Consumo y datos**):
  - Se elige el **acceso**: *Llamadas y agentes* (`calls`) y/o los motores de la API de inferencia: *LLM*, *Transcripción (STT)*
    y *Síntesis (TTS)*.
  - La clave se muestra **una sola vez**, con botón para copiarla y ejemplos `curl` de lo que se eligió.
  - Va en `Authorization: Bearer vaas_...`. Con `calls` da acceso a los agentes (también crearlos y editarlos),
    números y llamadas de ese cliente (sus sistemas disparan llamadas con `POST /api/v1/calls`). Con `llm`, `stt` o `tts`
    llama a los motores, dentro de los límites del tier ([`API_INFERENCIA.md`](API_INFERENCIA.md)).
  - La pantalla **API keys** (título "API") muestra además el consumo del mes contra el plan (tokens, minutos, pedidos por minuto, y por key),
    la URL base y ejemplos.
- **Developers > Uso de la API** (admin y cliente): cada pedido a la API de inferencia, con fecha, key, tipo, estado,
  duración y consumo, y los totales del filtro. Filtros: cliente (admin), API key, tipo, estado, streaming y período.
  Desde la tarjeta de consumo, **Ver los pedidos** abre esta pantalla filtrada por el cliente.
  - **Revocar** la anula en el acto.

## Operación diaria (ambos roles)

### Inicio (dashboard)

- **Filtros:** cliente (solo admin), agente y período (última semana, último mes o fechas). Aplican a
  los indicadores y al gráfico. Los días son del huso horario del navegador. **Ver conversaciones**
  lleva al listado con los mismos filtros.
- **Nueva llamada:**
  - **Agente:** los no archivados; el admin los ve agrupados por cliente.
  - **Teléfono** en E.164 para una saliente, o **Modo prueba**: sin teléfono, te conectás por el
    navegador con **Hablar con el agente** (pantalla `/calls/<id>/hablar`, también desde el detalle
    mientras la llamada espera). Si el navegador no tiene permiso del micrófono, primero lo explica y lo
    pide con un clic; si está bloqueado, muestra cómo habilitarlo. Entra con micrófono y audio prendidos
    (si el navegador frena el audio, aparece "Activar el audio").
  - **Número de origen:** opcional, uno del cliente. Es el que ve el destinatario; tiene que ser un
    número de la cuenta de Anura. Sin número de origen, sale con el principal (`ANURA_DID`).
  - **Voz:** la del agente, u otra del catálogo con filtros de género, WER y car/s.
  - **Prueba de voz:** escuchás el texto con la voz elegida, directo contra el TTS, sin llamar. Suena a los ~0,5 s,
    mientras se genera; al terminar queda guardada: repetirla o pausarla es instantáneo.
  - Si el tier no deja (sin lugar o sin minutos), el error dice cuál límite.
- **En vivo:** llamadas pendientes, sonando o en curso, con "Ver en vivo".
- **Indicadores:** conversaciones (con cuántas por WhatsApp), llamadas finalizadas, workflow
  completo, objetivo cumplido, fallidas, rechazadas (por límite), minutos y latencia por turno. El
  cliente los ve como "Completas" y "Tiempo de respuesta".
- **Conversaciones por día** (barras) y **Resultado por día** (líneas: % con workflow completo y %
  con objetivo cumplido).
### Conversaciones (`/calls`)

- Todas las conversaciones (llamadas, API y WhatsApp), con los mismos filtros que el inicio (cliente,
  agente y período), en la URL.
- Se puede filtrar por campaña (también en Inicio): los intentos de una campaña de llamadas y las
  conversaciones que abrió la respuesta de un contacto.
- Tabla paginada, filtrable además por estado y origen. Las de WhatsApp no tienen estado ni duración y
  muestran el teléfono del contacto. Cada fila lleva al detalle.
- **Borrar (solo admin):** cada fila tiene el ícono de borrar a la derecha y las casillas para
  seleccionar varias estilo Gmail (la del encabezado selecciona la página; la barra muestra cuántas
  hay y las borra juntas). Siempre pide confirmación. Se borra la conversación con sus mensajes,
  grabaciones y su consumo del mes; las que tienen una llamada en curso no se pueden borrar.

### Llamadas (`/outbound`, ambos roles)

- El agente llama a un contacto **con un motivo**: por ejemplo, la consulta que la persona dejó en la web
  ("quiero el precio de la BJ30 en plan de ahorro"). El agente arranca por ahí, sin preguntar lo que el
  motivo ya dice.
- **Formulario:** agente, destino (un contacto de la agenda, buscado por nombre o teléfono, o un número
  suelto en formato +549…), número de origen, motivo (hasta 2000 caracteres) y **Llamar**. Con un contacto,
  su nombre y sus atributos también le llegan al agente (como en una campaña: `{{nombre}}` en la apertura).
- **Modo prueba:** no marca; te conectás por navegador y hacés de contacto. Usa solo el motivo.
- Un número en la lista de bajas de voz del cliente (Contactos, Bajas) no se llama (409).
- **Últimas llamadas:** las 10 salientes más nuevas, con estado, duración y resultado. El resultado sale
  de la definición del agente (por ejemplo, área y urgencia). Si el agente tiene prendido el resumen por
  email, al cortar le llega al equipo, con el motivo.
- El detalle de la llamada muestra el motivo en "Motivo del llamado".

### Detalle de una llamada (`/calls/<id>`)

- **Cabecera:** contacto, empresa, origen, número del cliente, fecha, estado, duración, motivo de fin,
  datos obtenidos, resultado, y agente con versión.
- **Estado:** cada dato a obtener, con su valor, si está pendiente o no aplica, y los valores
  rechazados. Los recién obtenidos se resaltan unos segundos.
- **Conversación:** el chat. Con **Salida del LLM** se despliega lo que devolvió el LLM en cada turno
  (conversación y extracción, con su tiempo y razonamiento); si el agente tiene **Grabar audio**
  prendido, cada mensaje trae el reproductor de su WAV. En una llamada derivada, el tramo con la persona del
  equipo empieza con el separador "Llamada con <persona>", y lo que dijo ella va del lado del agente, en una
  burbuja blanca con borde y su nombre ("Ana Pérez (equipo)").
- **Latencia por turno:** E2E, EOU, STT, endpointing, LLM, TTS y audio, con promedios y máximos.
- El cliente ve las dos cosas como **Detalle técnico**: el interruptor del chat y, al final, una
  tarjeta plegada con la latencia.
- Mientras la llamada sigue, todo se actualiza cada segundo.
- **Cortar llamada** (arriba a la derecha, mientras está en curso): cuelga en el momento; termina con
  `hangup_by_user`.
- **Bloquear número** (en las entrantes): las próximas llamadas de ese número a los números del cliente se
  cortan sin atender. Se desbloquea en Contactos, **Números bloqueados**.
- **WhatsApp:** en lugar de estado, duración y fin de llamada muestra el último mensaje del contacto y
  los envíos fallidos, con el último error de Meta (131047: pasaron más de 24 h desde el último
  mensaje del contacto, no se puede mandar texto libre). No hay latencia por turno. Mientras la
  conversación está activa se actualiza cada 3 s.
  - **Cerrar conversación** (arriba a la derecha): el próximo mensaje de ese contacto empieza una
    conversación nueva, con la versión vigente del agente. Sirve después de cambiar el agente: un chat
    sigue con la versión con que empezó hasta 24 h sin mensajes. La cerrada queda en el historial,
    con la píldora "Cerrada".
- **Notas de voz:** en el chat, el mensaje del contacto que llegó como audio lleva el rótulo
  "Transcripción de nota de voz" (se ve el texto que entendió el STT, no el audio), y la respuesta que
  salió como audio, "Enviada como nota de voz". Si la nota de voz falló y salió en texto, no lleva rótulo.
  Si en el mismo turno el contacto escribió y mandó un audio, el mensaje no lleva rótulo y la parte
  transcripta empieza con `[nota de voz transcripta]`.

Motivos de fin frecuentes (`ended_reason`):

| Motivo | Qué pasó |
|---|---|
| `completed` | El agente terminó el workflow y cortó. |
| `off_topic` | El agente cortó porque la llamada no tenía que ver con su objetivo (broma, burla, acoso, número equivocado). Resultado "Fuera de tema". |
| `hangup_by_user` | La cortó alguien desde el panel (**Cortar llamada**) o la API. |
| `blocked_number` | Rechazada sin atender: el número que llama está bloqueado. |
| `customer_hangup` | Cortó el cliente. |
| `quota_exhausted` | Se acabaron los minutos del mes durante la llamada. |
| `concurrency_limit` | Rechazada: el cliente estaba al tope de llamadas simultáneas. |
| `calls_per_hour`, `calls_per_day`, `calls_per_month` | Rechazada: el cliente llegó al tope de llamadas de la hora, el día o el mes. |
| `inbound_minutes`, `outbound_minutes` | Rechazada: sin minutos del mes. |
| `client_inactive` | Rechazada: el cliente está desactivado. |
| `sip_call_failed` | La saliente no se pudo marcar (número, troncal o Anura). |
| `dispatch_failed` | La app no pudo despachar el agente a LiveKit. |
| `test_mode_timeout` | Nadie entró a la llamada de prueba en 5 minutos. |

### Agentes (cliente)

El usuario de un cliente crea y edita sus propios agentes; no ve ni puede tocar los de otro cliente.

1. **Agentes > Nuevo agente:** nombre, descripción (opcional) y punto de partida (asistente básico o
   en blanco). Te lleva a la pestaña **Definición**.
2. **Definición:** agente (nombre, rol, idioma), voz, objetivo y apertura, reglas, base de
   conocimiento, datos a obtener y resultados. Se valida mientras editás y **Guardar** crea una
   versión nueva.
3. **Versiones:** historial con autor; **Restaurar** guarda una anterior como versión nueva.
4. **Probar:** conversación por texto, llamada de prueba o link para llamar, antes de ponerlo a
   atender. También desde **Agentes > Probar agentes** en el menú, o con **Probar** en la lista.
5. Arriba, **Editar** (nombre y descripción), **Archivar/Desarchivar** y **Borrar** (solo si nunca
   tuvo conversaciones ni atiende un número de WhatsApp).
6. Para que atienda: elegilo en **Mi cuenta > Números** o en **WhatsApp**.

No se muestran el cliente, el slug, el motor, el JSON ni el prompt: son internos. El agente nace con
el motor Clásico; desde la UI lo cambia un admin. Por API el cliente hace lo mismo con su API key
(`POST /api/v1/agents` sin `client_id`); ahí `engine` es un campo más de la definición.

### Modelos (cliente) y Modelo de lenguaje de un agente

Por defecto todos los agentes contestan con el modelo de Atentina, **atentina-conversational-v1** (el
servidor propio: la conversación no sale). Con **BYOK** el cliente trae la clave de su proveedor y elige,
por agente, desde qué turno lo usa ([`BYOK_LLM_PLAN.md`](BYOK_LLM_PLAN.md)).

1. **Modelos > Nueva conexión** (el admin, en la ficha del cliente, pestaña **Modelos**): proveedor
   (Anthropic, OpenRouter u OpenAI compatible, con su URL base), nombre, API key y modelo por defecto.
   Al guardar se **prueba** sola: dice si la clave y el modelo andan, cuánto tardó y cómo pide el JSON
   ese proveedor. La clave se guarda cifrada y no se vuelve a mostrar (solo `…1234`).
2. En la lista: **Probar** de nuevo, **Editar** (nombre, modelo, o rotar la clave) y **Dar de baja**.
   La columna *Agentes* dice cuántos la usan: al darla de baja pasan a atentina-conversational-v1.
3. **Agente > Definición > Modelo de lenguaje:** arriba se elige entre **Modelo atentina-conversational-v1**
   (el default) y **Mis proveedores, por etapas**. La segunda opción se habilita cuando el cliente ya cargó
   una conexión; sin ninguna, la sección lo explica con el botón **Cargar una clave**. Volver al modelo de
   Atentina pide confirmación y quita las etapas.
4. **Configurar parámetros del modelo** despliega todos los parámetros del modelo (temperatura, `top_p`,
   `top_k`/`min_p`, razonamiento y su tope, máximo de tokens…) con su **valor por defecto**, el recomendado
   para el modelo y el motor. Para cambiarlos: **Cambiar valores** y confirmar (se pregunta una vez por
   edición). Solo los cambiados van a la definición, marcados como *Cambiado*, y se vuelven al default
   con la flecha o con **Volver todo al default**. Sin default conocido (otro proveedor) dice *Automático*.
5. **Por etapas:** una etapa por tramo de la conversación. *Desde el turno* es el mensaje número N de la
   persona (la apertura no cuenta); la primera empieza siempre en 1 y hay hasta 3. Cada etapa elige quién
   contesta (una conexión o atentina-conversational-v1), su modelo (la lista sale del proveedor; si no la
   da, se escribe) y, en **Parámetros de esta etapa**, los suyos.
6. **Usar atentina-conversational-v1 si el proveedor falla** (activado por defecto): si el proveedor da
   error, ese turno lo contesta el servidor propio. Apagado, el error corta el turno.
7. Las conversaciones con una etapa externa **salen de Atentina**: el editor lo avisa. En el detalle
   de una conversación, cada llamada al modelo muestra proveedor y modelo, y cuándo contestó el respaldo.

### Voces

Catálogo de las 41 voces del TTS, con género, WER y velocidad (car/s), filtrable, y la prueba de voz.
La voz por defecto de un agente es `agent.voice` en su definición.

### WhatsApp (cliente)

Conectá tu número de WhatsApp Business para que lo atienda uno de tus agentes, por texto y notas de voz.
Solo funciona desde `https://app.atentina.com.ar` (Meta exige HTTPS).

1. **Conectar WhatsApp:** elegí el agente y seguí la ventana de Meta: entrás con tu Facebook, elegís o
   creás tu portafolio y tu cuenta de WhatsApp Business, y cargás y verificás el número (SMS o llamada).
   Si el número ya tenía verificación en dos pasos, cargá ese PIN en "El número ya tiene verificación
   en dos pasos". Si el botón está gris, el motivo aparece al lado (falta configurar algo en el server).
2. **Medio de pago:** Meta cobra los mensajes a tu cuenta, no a nosotros. Cargalo en
   [WhatsApp Manager](https://business.facebook.com/wa/manage/home/); sin eso el alta no termina.
3. **Estado** de cada número:
   - **Conectado:** responde.
   - **Pendiente:** falta suscribir o registrar en Meta. Menú > **Reintentar registro** (con el PIN si
     Meta dice que es incorrecto).
   - **Desconectado:** Meta rechazó el acceso (lo quitaste o venció). Volvé a **Conectar WhatsApp** con el
     mismo número.
   - **Calidad** (Alta, Media, Baja) y límite de envío, según Meta. **Releer datos de Meta** los actualiza.
4. **Agente:** se cambia en la fila; vale para las conversaciones nuevas.
5. **Ruteo por contacto:** en el menú de la fila, elegí los agentes y cargá los contactos que atiende
   cada uno (mensajes y llamadas de WhatsApp); los demás los atiende el agente por defecto.
6. **Plantillas:** abajo, por número. Lista las de tu cuenta con su estado (En revisión, Aprobada,
   Rechazada con el motivo) y **Nueva plantilla** crea una (nombre en minúsculas y `_`, categoría
   Utilidad o Marketing, cuerpo con `{{1}}`, `{{2}}`… y un ejemplo por variable). Meta la revisa.
7. **Desactivar** deja de responder ese número; **Activar** lo vuelve a habilitar.
8. Un número que cargó un admin con la cuenta de la plataforma (alta manual) no muestra registro, datos de
   Meta ni plantillas al cliente: los maneja el admin.

### Contactos (`/contacts`, ambos roles)

La agenda del cliente: de ahí salen los destinatarios de las campañas. Lo único obligatorio es el teléfono
(único por cliente, se normaliza a formato internacional); nombre, email, ID externo, etiquetas y datos libres
(`deuda`, `vence`…) son opcionales. El admin elige primero el cliente.

1. **Nuevo contacto** o **Importar CSV**: encabezado `telefono` (obligatorio), `nombre`, `email`, `id_externo`,
   `etiquetas` (separadas por `|` o `;`) y una columna más por cada dato libre. La vista previa muestra las columnas; el resultado, los
   creados, actualizados, archivados e inválidos (con fila y motivo). Un contacto que ya existe se actualiza:
   los datos y las etiquetas se suman, no se pisan.
2. **Etiquetas:** sirven para armar campañas por segmento. Se escriben en minúsculas, sin acentos.
3. **No se borran, se archivan.** El filtro Activos / Archivados / Todos muestra el resto. Se archiva uno,
   varios seleccionados o una etiqueta entera. Un archivado no entra en campañas nuevas y se saltea en las
   que tenía pendientes. Recargar su teléfono no lo desarchiva: **Desarchivar** es explícito.
4. **Ficha** (clic en la fila): datos y campañas en que participó o participa.
5. **Tope:** el tier limita los contactos activos de la agenda.
6. **Números bloqueados** (al final): sus llamadas entrantes, por la línea o por WhatsApp, se cortan sin
   atender y quedan como rechazadas (`blocked_number`). Se cargan acá (teléfono y motivo) o desde el detalle
   de una llamada (**Bloquear número**). No cambian las campañas: para no llamar a alguien están las bajas.

### Equipo (`/team`, ambos roles)

Las personas del cliente a las que el agente les pasa una llamada o un chat, agrupadas en áreas
([`DERIVACIONES_PLAN.md`](DERIVACIONES_PLAN.md)). El admin elige primero el cliente. A qué áreas deriva cada
agente se elige en su definición, **Derivación a personas**.

1. **Personas:** nombre, teléfono (para transferirle llamadas; solo Argentina) y WhatsApp (para el puente de
   WhatsApp; único por cliente). Hace falta uno de los dos. El tier limita cuántas.
2. **Áreas:** nombre y qué atiende (lo lee el agente para elegir el área), personas en el orden en que se las
   llama (**En orden** o **Rotativa**), timbre por persona (20 s por defecto: el buzón de Claro atiende a los
   ~33 s), horario por día con días cerrados (o **Atiende siempre**), qué hace el agente si la persona corta
   (vuelve con "¿Te puedo ayudar con algo más?" o se despide) y la tecla con la que la persona le devuelve la
   llamada a la IA (2 por defecto; nunca con `*`, que la central de Anura toma como código).
3. **Mensajes:** cada momento (antes de transferir, el aviso a la persona, no atiende, ocupado, fuera de
   horario, vuelta y despedida) tiene un texto por defecto; se cambia por área, con `{{area}}`, `{{persona}}`,
   `{{cliente}}`, `{{resumen}}` y `{{horario}}`.

### Campañas (`/campaigns`, ambos roles)

Un lote de contactos al que el agente le escribe por WhatsApp (plantilla) o llama. Las respuestas de
WhatsApp las atiende el agente. La lista filtra por canal y estado. **Nueva campaña** ofrece los canales; el
que el plan no incluye aparece deshabilitado con el motivo. Mientras corre o espera su hora, el detalle se
actualiza cada 5 s.

#### Campaña de WhatsApp

Hace falta un número conectado con su propia cuenta (el cliente) y una plantilla aprobada.

1. **Plantilla:** en WhatsApp > Plantillas > **Nueva plantilla**, categoría Marketing para prospección, con
   botón de enlace (ej. "Probar la demo" → la landing) y el botón "No me interesa". Esperar a que Meta la
   apruebe.
2. **Nueva campaña:** nombre, número que envía, plantilla, agente que responde (vacío: el del número),
   horario (hora de Argentina) y mensajes por minuto. Contactos en CSV con encabezado: `telefono,nombre`
   y una columna más por cada variable de la plantilla (pegado o en archivo). Al crearla muestra cuántos
   entraron y los que quedaron afuera, con el motivo.
3. Queda en **Borrador**: revisar el mensaje y los contactos y usar **Iniciar envío**. **Pausar**,
   **Retomar envío**, **Agregar contactos** (en borrador o pausada) y **Cancelar campaña** (los pendientes
   no se mandan).
4. **Totales:** enviados, entregados, leídos, respondieron, fallidos (con el motivo por contacto) y bajas.
   Cada contacto que respondió tiene **Ver conversación**.
5. **Pausada automáticamente:** Meta pausó la plantilla, frenó el número o rechazó el token. El motivo
   aparece arriba; resolverlo y **Retomar envío**.
6. **Bajas:** quien responde "No me interesa" o "Baja" no recibe más campañas del cliente. Se pueden cargar
   o sacar a mano en la tarjeta **Bajas**.

Meta cobra cada plantilla entregada a la cuenta del número. Conviene escribirles solo a quienes aceptaron
recibir mensajes: muchos bloqueos bajan la calidad del número y su límite de envío.

#### Campaña de llamadas

1. **Nueva campaña > Llamadas:**
   - **Agente que llama**, **número de origen** (uno del cliente: es el que ve el destinatario) y **voz**
     (vacío: la del agente).
   - **Finalidad:** comercial, cobranza, turnos o aviso. Una **comercial** exige marcar "Confirmo que filtré la
     lista contra el Registro No Llame" (Ley 26.951; es responsabilidad del cliente).
   - **Destinatarios:** por etiquetas, contactos elegidos de la agenda o un CSV (que también los carga en la agenda).
   - **Horario:** desde, hasta, días y, opcional, **Inicio programado** y **Termina como máximo**. Fuera de
     horario (o en un feriado de `CAMPAIGN_HOLIDAYS`) no llama.
   - **Llamadas:** de a una, o en paralelo hasta el tope del plan; intentos por contacto, minutos entre intentos
     y en qué resultados se vuelve a llamar (no atendió, ocupado, contestador, falló).
   - **Seguimiento por WhatsApp** (si el plan lo incluye): número, plantilla aprobada, dato de cada `{{n}}`, en
     qué resultados se manda y agente que responde. Se le escribe a quien no atendió tras el último intento.
   - **Webhook:** URL https pública. Si no se carga un secreto se genera y **se muestra una sola vez**.
2. Queda en **Borrador**: **Iniciar**, **Pausar**, **Retomar** y **Cancelar** (los pendientes no se llaman). **Editar** en
   el borrador y la pausada.
3. **Variables:** los datos del contacto se usan en la apertura del agente (`{{nombre}}`, `{{deuda}}`; si falta
   un dato, el texto se acomoda sin él) y los que se llaman como un campo del agente lo cargan ya completo.
4. **Detalle:** barra de avance, ritmo y tiempo estimado; tarjetas por resultado (atendió, no atendió,
   ocupado, contestador, número inválido, rechazó, falló); indicadores (tasa de contacto, objetivo cumplido,
   duración, minutos) y atendidas por hora del día, para elegir el horario; seguimiento; y la tabla de
   contactos, filtrable, con **Ver conversación**. **Descargar reporte** baja el `report.csv`.
5. **Pausada automáticamente:** sin minutos o tope de llamadas del plan, agente archivado, número de origen
   suspendido o 10 intentos seguidos fallidos (Anura o el trunk caídos). El motivo aparece arriba; resolverlo
   y **Retomar**.
6. **Bajas:** un resultado del agente marcado "No volver a llamar" (en el editor del agente) agrega el teléfono
   a las bajas de llamadas; ninguna campaña de llamadas del cliente lo marca más.

El contestador se detecta por lo que dice (frases como "deje su mensaje"): puede equivocarse con un humano.

### Consumos (cliente)

Consumo del mes con selector de mes, contra los límites del plan: llamadas simultáneas, números, minutos
entrantes y salientes, y el consumo de la API de inferencia (tokens de entrada y salida del LLM, minutos de
transcripción y de síntesis, pedidos por minuto y desglose por key). Es la misma información que ve el admin
en la ficha del cliente. La API no cuenta lo que consumen los agentes integrados (llamadas y WhatsApp).

### Mi cuenta (cliente)

- **Consumo del mes:** llamadas activas, minutos entrantes y salientes, y números, cada uno contra
  su tope.
- **Números:** elegís qué agente tuyo atiende cada número y editás la etiqueta. Asignar y liberar
  números lo hace el admin.
- **API keys:** crear y revocar.
- **Resumen de llamadas por email:** prende o apaga, para todos tus agentes, el email que manda Atentina
  después de cada llamada, y elegís a quién le llega (vacío: a los usuarios de la cuenta). Cada agente lo
  prende en su editor, sección Voz ("Resumen por email después de cada llamada"); al prenderlo se agrega el dato
  "Teléfono" si el agente no lo tiene: en las llamadas por teléfono se completa solo con el número de quien llama, y
  por el link para llamar el agente lo pide. El admin lo ve y lo
  edita en la ficha del cliente.

### Plan (cliente) y Cobros (admin)

Registro y cobro por transferencia ([`SUSCRIPCIONES_PLAN.md`](SUSCRIPCIONES_PLAN.md)):

- **Registro:** el cliente se da de alta en `atentina.com.ar/registro` (con su clave) y entra directo al
  panel, en el tier Free (el público con precio 0, que tiene que existir en Tiers). Si eligió un plan pago,
  va a pagarlo con tarjeta (`/plan/pagar`).
- **Tiers que se venden:** en el formulario del tier, "Precio por mes" y "Público". Vacío = no se vende
  por el dashboard; 0 = gratis.
- **Plan (`/plan`, cliente):** datos para la factura y planes con precio. Se pagan con **tarjeta**
  (débito automático de Mercado Pago, se activa en el momento; con uno activo, cambiar de plan no pide la
  tarjeta) o por **transferencia** (ve los datos bancarios y manda el comprobante por email).
- **Lo que el plan no incluye** ([`FUNCIONES_POR_PLAN_PLAN.md`](FUNCIONES_POR_PLAN_PLAN.md)): el cliente ve
  un candado en la navegación (Llamadas, WhatsApp, Contactos, Equipo, Campañas) y, en esa pantalla, un aviso
  con borde amarillo, en qué planes está ("Disponible en los planes Mostrador, Sucursal y Central") y "Mejorar mi plan"; lo de abajo queda atenuado y sin responder. Con plan gratis, "Free"
  al lado de Plan. Sale de los campos del tier (minutos salientes y números, canales de campañas, contactos,
  equipo, links y la casilla **WhatsApp**) y de los ajustes del cliente: un ajuste abre la función. Sin
  salientes, "Nueva llamada" de Inicio y Probar del agente quedan fijos en modo prueba.
- **Ficha del cliente, tarjeta "Plan pago" (admin):** "Registrar pago" activa o renueva el plan por un
  mes; "Rechazar pedido" o "Pasar al gratuito" lo corta.
- **Cobros (`/billing`, admin):** planes pagos y pedidos abiertos, y pagos para facturar ("Marcar facturado").
- **Olvidé mi clave:** link en el ingreso (`/forgot-password`); manda un link nuevo por mail.

### Mi perfil (`/profile`, ambos roles)

Ícono de usuario arriba a la derecha, al lado de "Salir".

- **Tus datos:** el nombre (sale en los mails).
- **Email de ingreso:** escribís el nuevo y "Mandar código"; el código de 6 dígitos llega al email **actual** y
  con él se confirma el cambio.
- **Clave:** "Mandar código", y con el código del mail elegís la nueva (al menos 10 caracteres).
- El código vale 15 minutos y una sola vez. Al cambiar el email o la clave se cierran las otras sesiones
  abiertas; la de esta pestaña sigue.

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| Las entrantes suenan y cortan ("ocupado") | El número no tiene agente, o está libre. Elegí el agente en Números o en la ficha del cliente. Log del agente: `no tiene cliente o agente asignado`. |
| Una entrante escucha "no podemos atender tu llamada" | El tier no deja: tope de simultáneas, de llamadas por hora, día o mes, minutos entrantes agotados o cliente inactivo. Mirá el consumo del cliente. |
| Todas las entrantes van al mismo agente | No llega el número marcado y cae al principal (`ANURA_DID`). Mirar el log de Asterisk (`Entrante de Anura: ... (marcado: ...)`) y que cada número tenga su agente. |
| "Llegaste al límite…" al llamar | Tope del tier. Esperá que terminen llamadas, subí el tier o el tope. |
| Un número nuevo no recibe llamadas | No entró al trunk de LiveKit (ver el log de `app`; se arregla con `make livekit-sip`), o Anura no lo entrega a esta troncal. |
| "Conectar WhatsApp" abre y se cierra, o da error de dominio | Se entró por `http://` o por un dominio que no está en la app de Meta: usar `https://app.atentina.com.ar`. |
| Un número de WhatsApp queda "Pendiente" | Falló el registro en Meta (ej. PIN de dos pasos incorrecto, 133005): Reintentar registro con el PIN correcto. |
| La prueba de voz o el chat por texto dan error | El TTS o el LLM no responden (`make health`). |
| Una conexión de modelos "falló la prueba" | El detalle lo dice: clave inválida, modelo inexistente o URL incorrecta (OpenAI compatible), límite del proveedor o sin conexión. Corregí y volvé a **Probar**. |
| Un agente con modelo propio contesta con el servidor Atentina | El proveedor falló y el agente tiene el respaldo activado: mirá en el detalle de la conversación el motivo (`fallback_reason`). Si la conexión se dio de baja, también. |
