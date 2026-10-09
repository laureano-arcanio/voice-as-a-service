# Guía de la UI

Cómo hacer cada cosa desde la UI (`http://<host>:8011/`; en este server `http://192.168.1.99:8011/`;
desde internet, `https://app.atentina.com.ar/` cuando se publique). Todo lo que hace la UI también se
puede hacer por la API (`/api/v1/docs`, solo con sesión de admin). La arquitectura está en
[`ARQUITECTURA.md`](ARQUITECTURA.md).

Hay dos roles:
- **Admin:** opera la plataforma y ve todo. Menú: Inicio, Conversaciones, Agentes, Voces, WhatsApp, Clientes, Números, Tiers y Usuarios.
- **Cliente:** usuario de un cliente, que solo ve lo suyo. Menú: Inicio, Conversaciones, Agentes, Voces, WhatsApp y Mi cuenta.

## Primer ingreso

1. El primer admin lo crea `make migrate` con `ADMIN_EMAIL` y `ADMIN_PASSWORD` de `.env`. Otro admin
   o cambio de clave: `make create-admin EMAIL=...`.
2. Entrar en `/login` con ese email y clave. La sesión dura `AUTH_TOKEN_HOURS` (12 h). Con 5 intentos
   fallidos en 15 min desde la misma IP para el mismo email (o 10 para el email desde cualquier IP, o 20
   desde la IP con cualquier email), el login se bloquea un rato.
3. Arriba a la derecha: Salir. **Salir cierra todas tus sesiones**, también las de otros navegadores;
   cambiar la clave también.

## Puesta en marcha de un cliente nuevo (admin)

Orden recomendado: **tier → cliente → agente → número → usuario**.

### 1. Crear o elegir un tier (Tiers)

**Tiers > Nuevo tier**: nombre, descripción y límites. Un campo vacío significa ilimitado.
Los de la API de inferencia (abajo) arrancan en 0 = el plan no los incluye.

| Campo | Qué limita |
|---|---|
| Llamadas simultáneas | Llamadas en curso a la vez, de cualquier modalidad (incluye pruebas y loadtest). |
| Minutos entrantes por mes | Minutos de llamadas recibidas, por mes calendario (hora de Buenos Aires). |
| Minutos salientes por mes | Minutos de llamadas hechas por el agente. |
| Números | Cantidad de números de teléfono que puede tener asignados el cliente. |

- **Editar:** los cambios rigen en el acto, también para el mes en curso.
- **Bajar el tope de números:** no se puede si algún cliente de ese tier ya tiene más asignados.
- **Borrar:** solo si el tier no tiene clientes.

### 2. Crear el cliente (Clientes)

**Clientes > Nuevo cliente**: nombre, slug (se arma del nombre; minúsculas, números y `_`), tier y el
email de su primer usuario (con el nombre, opcional, para el saludo). Se crea ese usuario, sin clave, y
le llega un email de Atentina con el plan contratado y un link para crear su clave (vale 72 horas y se usa
una sola vez). Si el aviso dice que no se pudo mandar, o el link venció, **Usuarios > Reenviar invitación**
(el sobre de la fila). Te lleva a la ficha del cliente, que tiene cinco pestañas:

- **Consumo y datos:** consumo del mes con selector de mes (llamadas activas contra el tope,
  minutos entrantes y salientes, números usados), y los datos del cliente:
  - **Cambiar el tier:** se rechaza si el tier nuevo permite menos números de los que tiene.
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
  - **Agente:** nombre, rol, idioma y **motor** (Clásico o Estructurado, en tarjetas). La definición es la misma con los dos motores: cambiarlo no toca nada más.
  - **Voz:** tarjetas con las voces (filtro por mujeres u hombres); al lado, la prueba con la voz elegida, con la apertura como texto (editable).
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
- **Probar:**
  - **Nueva llamada** con este agente: de prueba por navegador o saliente.
  - **Conversación por texto:** chateás con el agente sin voz. Con el motor estructurado ves los datos
    que va extrayendo y el próximo objetivo en cada turno; con el clásico (el de por defecto), los datos
    aparecen al terminar la conversación.

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

Después de **cargar o borrar** números hay que correr `make livekit-sip` en el server, para que el
trunk entrante de LiveKit los acepte (la página lo recuerda). Asignar, liberar o cambiar de agente
no lo necesita.

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
3. **Editar:** agente, número visible, nombre y token. El agente nuevo vale para las conversaciones
   nuevas; las en curso siguen con el suyo.
4. **Desactivar:** los mensajes a ese número dejan de responderse. No hay borrado: las conversaciones
   lo referencian. **Activar** lo vuelve a habilitar.

Si el cliente está desactivado, sus números de WhatsApp tampoco responden.

### 5. Usuarios y API keys del cliente

- **Usuarios** (en el menú, o en la pestaña Usuarios de la ficha del cliente) > **Nuevo usuario**:
  - email, nombre, clave (10 caracteres o más) y rol;
  - rol **cliente**: hay que elegir el cliente;
  - rol **admin**: no pertenece a ninguno.

  Desde la tabla se editan el nombre, la clave y el estado activo, y se borra. Desactivar un usuario
  corta su sesión en el acto. Nadie puede desactivarse ni borrarse a sí mismo.
- **API keys** (pestaña **API keys** de la ficha del cliente, o **API** en el menú del cliente) > **Nueva API key**:
  - Se elige el **acceso**: *Llamadas y agentes* (`calls`) y/o los motores de la API de inferencia: *LLM*, *Transcripción (STT)*
    y *Síntesis (TTS)*.
  - La clave se muestra **una sola vez**, con botón para copiarla y ejemplos `curl` de lo que se eligió.
  - Va en `Authorization: Bearer vaas_...`. Con `calls` da acceso a los agentes (también crearlos y editarlos),
    números y llamadas de ese cliente (sus sistemas disparan llamadas con `POST /api/v1/calls`). Con `llm`, `stt` o `tts`
    llama a los motores, dentro de los límites del tier ([`API_INFERENCIA.md`](API_INFERENCIA.md)).
  - La pantalla **API** muestra además el consumo del mes contra el plan (tokens, minutos, pedidos por minuto, y por key),
    la URL base y ejemplos.
  - **Revocar** la anula en el acto.

## Operación diaria (ambos roles)

### Inicio (dashboard)

- **Filtros:** cliente (solo admin), agente y período (última semana, último mes o fechas). Aplican a
  los indicadores y al gráfico. Los días son del huso horario del navegador. **Ver conversaciones**
  lleva al listado con los mismos filtros.
- **Nueva llamada:**
  - **Agente:** los no archivados; el admin los ve agrupados por cliente.
  - **Teléfono** en E.164 para una saliente, o **Modo prueba**: sin teléfono, te conectás por el
    navegador con el link "Conectate acá…", que se muestra una sola vez.
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
- Tabla paginada, filtrable además por estado y origen. Las de WhatsApp no tienen estado ni duración y
  muestran el teléfono del contacto. Cada fila lleva al detalle.

### Detalle de una llamada (`/calls/<id>`)

- **Cabecera:** contacto, empresa, origen, número del cliente, fecha, estado, duración, motivo de fin,
  datos obtenidos, resultado, y agente con versión.
- **Estado:** cada dato a obtener, con su valor, si está pendiente o no aplica, y los valores
  rechazados. Los recién obtenidos se resaltan unos segundos.
- **Conversación:** el chat. Con **Salida del LLM** se despliega lo que devolvió el LLM en cada turno
  (conversación y extracción, con su tiempo y razonamiento).
- **Latencia por turno:** E2E, EOU, STT, endpointing, LLM, TTS y audio, con promedios y máximos.
- El cliente ve las dos cosas como **Detalle técnico**: el interruptor del chat y, al final, una
  tarjeta plegada con la latencia.
- Mientras la llamada sigue, todo se actualiza cada segundo.
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
| `customer_hangup` | Cortó el cliente. |
| `quota_exhausted` | Se acabaron los minutos del mes durante la llamada. |
| `concurrency_limit` | Rechazada: el cliente estaba al tope de llamadas simultáneas. |
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
4. **Probar:** conversación por texto o llamada de prueba, antes de ponerlo a atender.
5. Arriba, **Editar** (nombre y descripción), **Archivar/Desarchivar** y **Borrar** (solo si nunca
   tuvo conversaciones ni atiende un número de WhatsApp).
6. Para que atienda: elegilo en **Mi cuenta > Números** o en **WhatsApp**.

No se muestran el cliente, el slug, el motor, el JSON ni el prompt: son internos. El agente nace con
el motor Clásico; desde la UI lo cambia un admin. Por API el cliente hace lo mismo con su API key
(`POST /api/v1/agents` sin `client_id`); ahí `engine` es un campo más de la definición.

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
5. **Plantillas:** abajo, por número. Lista las de tu cuenta con su estado (En revisión, Aprobada,
   Rechazada con el motivo) y **Nueva plantilla** crea una (nombre en minúsculas y `_`, categoría
   Utilidad o Marketing, cuerpo con `{{1}}`, `{{2}}`… y un ejemplo por variable). Meta la revisa.
6. **Desactivar** deja de responder ese número; **Activar** lo vuelve a habilitar.
7. Un número que cargó un admin con la cuenta de la plataforma (alta manual) no muestra registro, datos de
   Meta ni plantillas al cliente: los maneja el admin.

### Campañas (`/campaigns`, ambos roles)

Mandan una plantilla aprobada de WhatsApp a una lista de contactos; las respuestas las atiende el agente.
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

### Mi cuenta (cliente)

- **Consumo del mes:** llamadas activas, minutos entrantes y salientes, y números, cada uno contra
  su tope.
- **Números:** elegís qué agente tuyo atiende cada número y editás la etiqueta. Asignar y liberar
  números lo hace el admin.
- **API keys:** crear y revocar.

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| Las entrantes suenan y cortan ("ocupado") | El número no tiene agente, o está libre. Elegí el agente en Números o en la ficha del cliente. Log del agente: `no tiene cliente o agente asignado`. |
| Una entrante escucha "no podemos atender tu llamada" | El tier no deja: tope de simultáneas, minutos entrantes agotados o cliente inactivo. Mirá el consumo del cliente. |
| Todas las entrantes van al mismo agente | No llega el número marcado y cae al principal (`ANURA_DID`). Mirar el log de Asterisk (`Entrante de Anura: ... (marcado: ...)`) y que cada número tenga su agente. |
| "Llegaste al límite…" al llamar | Tope del tier. Esperá que terminen llamadas, subí el tier o el tope. |
| Un número nuevo no recibe llamadas | Faltó `make livekit-sip` después de cargarlo, o Anura no lo entrega a esta troncal. |
| "Conectar WhatsApp" abre y se cierra, o da error de dominio | Se entró por `http://` o por un dominio que no está en la app de Meta: usar `https://app.atentina.com.ar`. |
| Un número de WhatsApp queda "Pendiente" | Falló el registro en Meta (ej. PIN de dos pasos incorrecto, 133005): Reintentar registro con el PIN correcto. |
| La prueba de voz o el chat por texto dan error | El TTS o el LLM no responden (`make health`). |
