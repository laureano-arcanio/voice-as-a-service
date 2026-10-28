# Guía de la UI

Cómo hacer cada cosa desde la UI (`http://<host>:8011/`; en este server `http://192.168.1.99:8011/`;
desde internet, `https://app.atentina.com.ar/` cuando se publique). Todo lo que hace la UI también se
puede hacer por la API (`/api/v1/docs`, solo con sesión de admin). La arquitectura está en
[`ARQUITECTURA.md`](ARQUITECTURA.md).

Hay dos roles, y cada uno trabaja en su área ([`ADMIN_SOPORTE_PLAN.md`](ADMIN_SOPORTE_PLAN.md)):
- **Cliente:** usuario de un cliente, que solo ve lo suyo. Su panel (`/`) tiene este menú (los grupos se
  despliegan con un click; arranca abierto el de la pantalla actual):
  - Inicio, Reportes y Conversaciones, sueltos.
  - **Agentes:** Mis agentes, Herramientas, Secretos, Modelos, Playground y Voces.
  - **Canales:** WhatsApp, Llamadas y Campañas.
  - **Organización:** Contactos, Teléfono y Equipo.
  - **Developers:** API keys y Uso de la API.
  - **Cuenta:** Mi cuenta, Plan y Consumos.
- **Admin:** administra la plataforma en `/admin/*` (al iniciar sesión va siempre ahí). Su menú: Inicio,
  Reportes, Conversaciones, Agentes (solo lectura, de todos los clientes), Uso de la API, Clientes, Números,
  Tiers, Cobros y Usuarios. Lo demás (agentes, herramientas, WhatsApp, contactos, campañas, equipo...) no está
  en su menú: para operarlo **entra como el cliente** y ve su panel tal cual (ver [Entrar como un cliente
  (soporte)](#entrar-como-un-cliente-soporte)).

Las pantallas del panel del cliente son las mismas para todos: no tienen selector de cliente ni columnas o
acciones "solo admin". La pestaña **JSON**, el slug y **Ver prompt** del agente los ve todo cliente.

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

## Entrar como un cliente (soporte)

Para dar soporte o trabajar con los agentes de un cliente (también los propios, del cliente `atentina`), el
admin no se loguea con otro usuario: entra al panel del cliente.

- **Cómo entrar:** **Entrar como el cliente** en su ficha (Clientes), o **Abrir como el cliente** en una fila de
  Agentes y en el detalle de una conversación (abre ese agente o esa conversación).
- **Qué se ve:** el panel del cliente tal cual (menú, marca blanca si tiene, y lo que su plan incluye), con la
  marca **soporte** en el encabezado. Se puede hacer todo lo que hace el cliente: crear agentes, herramientas,
  conectar WhatsApp, cargar contactos, lanzar campañas. No queda registro aparte de lo que se hace.
- **Plan, pagos, datos fiscales y perfil:** solo lectura (pagar, cambiar de plan, aceptar condiciones y editar el
  perfil dan 403 `support_read_only`).
- **Salir:** **Volver a administración**, en el encabezado, es la única forma. El cliente activo es **por
  pestaña**: sobrevive a una recarga, y cada pestaña puede estar en otro cliente. Abrir `/admin` en esa pestaña
  lleva al panel del cliente.
- **Vista previa de la marca blanca** (ficha del cliente, pestaña Marca blanca): abre otra pestaña entrando
  como el cliente, con el borrador de la marca.
- **Por API:** el header `X-Atentina-Client: <client_id>` con la sesión del admin.

## Puesta en marcha de un cliente nuevo (admin)

Orden recomendado: **tier → cliente → agente → número → usuario**. Tier, cliente, números y usuarios se hacen
en `/admin`; los agentes, las herramientas, WhatsApp y el resto, **entrando como el cliente** (arriba).

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
| Llamadas directas (teléfono del equipo) | Switch. Prendido, las personas llaman desde el panel (Teléfono) y el equipo puede atender las entrantes de un número, sin el agente. Apagado (el Free), esas pantallas muestran el aviso de plan y las entrantes de un número del equipo van a su agente. La saliente además necesita minutos salientes. En la lista de tiers aparece "con llamadas directas". |

- **Interno (Atentina):** switch para el tier de nuestras cuentas (`tiers.internal`): no se ofrece como plan
  (ni en el registro ni en Plan) y no cuenta en las estadísticas de la plataforma.
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
(el sobre de la fila). Te lleva a la ficha del cliente, con **Entrar como el cliente** arriba a la derecha y
estas pestañas: Consumo y datos, Números, Agentes, Usuarios, Modelos, API keys y Marca blanca.

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
- **Números**, **Agentes**, **Usuarios**, **Modelos**, **API keys** y **Marca blanca**: ver abajo.

### 3. Crear el agente (Agentes)

Entrando como el cliente, **Agentes > Nuevo agente**: nombre, slug (opcional), descripción y **punto de partida** (no se
elige motor: hay uno solo desde el 26-oct-2026): el **asistente básico** (atiende, responde con la
base de conocimiento y, si no puede, toma nombre y contacto) o **en blanco** (un dato y el resultado
por defecto). Te lleva a la pestaña **Conversación** para completarlo.

El detalle del agente tiene pestañas. Cinco de ellas (Conversación, Datos, Herramientas, Voz y canales y
Modelo) editan la misma definición: comparten el borrador y la barra de arriba (versión, estado de la
validación, **Descartar** y **Guardar versión nueva**), así que cambiar de pestaña no pierde nada y guardar
lleva lo de todas. Cada una responde una pregunta: qué dice, qué obtiene, qué puede hacer, cómo suena y
quién piensa. Las ve igual el cliente y el admin que entró como él (ver [Agentes (cliente)](#agentes-cliente)). El
admin, en **Agentes** de `/admin`, ve los de todos los clientes en solo lectura (cliente, nombre, slug, versión, voz
y fecha, con filtros por cliente y archivados); **Abrir como el cliente** lo abre para editarlo.

- **Resumen:** la definición en limpio: agente, idioma, versión, objetivo, apertura, reglas, base de
  conocimiento, datos a obtener (orden, tipo, obligatorio, pregunta sugerida) y resultados.
- **Conversación:** qué dice y cómo. Es lo que arma el prompt.
  - **Agente:** nombre, rol e idioma.
  - **Objetivo y apertura**, **Reglas** (una por regla) y **Base de conocimiento**. La plantilla trae reglas genéricas de comportamiento (una pregunta por turno, no inventar, cuándo cortar), editables. La fecha no se le pasa sola al agente: `{{today}}` y `{{now}}` se pueden usar en el objetivo, las reglas y la base de conocimiento.
  - **Ver prompt** (en la barra): el prompt que arma el motor con lo que está en pantalla, por llamada o por
    WhatsApp. No hay un prompt aparte para editar: sale de la definición.
- **Datos:** qué obtiene.
  - **Datos a obtener:** cada dato con etiqueta, nombre interno, tipo (texto, número, sí o no, opción
    de una lista, email, email o teléfono), si es obligatorio (sí, no o según otro dato), descripción
    y pregunta sugerida. Se ordenan con las flechas. Al renombrar uno, se actualizan las condiciones que lo usan.
  - **Resultados:** etiqueta, ID, si cumple el objetivo, mensaje de cierre y condiciones. Vale el
    primero que se cumple; el último es el de por defecto.
- **Herramientas:** qué puede hacer además de hablar.
  - **Herramientas:** las herramientas del cliente (las de **Herramientas**: llamadas a una API o código), las **vueltas con herramientas por turno** (vacío: 3) con el **mensaje al llegar al tope**, y los **Secretos** que usan sus herramientas: **Del cliente** (cargados en Agentes > Secretos), **Propio** (un valor solo de este agente, que pisa al del cliente) o **Falta** (con **Cargar valor**). **Confirmar antes de ejecutarla** es de cada herramienta: solo agrega a su descripción que pida confirmación; el modelo decide (la plataforma no confirma desde el 26-oct-2026).
  - **Derivación a personas:** las áreas del cliente (de
    **Equipo**, con su horario; si no tiene, un link para crearlas). **Puede pasarle llamadas** habilita cada área
    (hasta 10) y abre **Cuándo pasarla**, el criterio para el agente (vacío = la descripción del área). Un área
    inactiva queda marcada, pero el agente no la ofrece. Con alguna área, **Música de espera** (prendida por
    defecto): tema (**Música de espera estándar** o los que haya en el servidor) y volumen (5 a 100 %). Sin áreas
    marcadas no se guarda nada de esto.
- **Voz y canales:** cómo suena y por dónde atiende.
  - **Voz:** tarjetas con las voces (filtro por mujeres u hombres); al lado, la prueba con la voz elegida, con la apertura como texto (editable). **Pregenerar el audio de la apertura** y **Espera antes de la apertura (ms)**: cómo arranca la llamada. **Grabar audio**: un WAV por mensaje de cada llamada (telefónica o de WhatsApp; el cliente y el agente por separado), localmente en el servidor; con **Avisar que la llamada se graba**, el agente lo dice antes del saludo. **Ventana de contexto en WhatsApp (minutos)**: minutos sin mensaje del contacto para que la próxima conversación arranque en limpio, sin el historial anterior; vacío usa el default del servidor (1440 min = 24 hs).
- **Modelo:** quién piensa.
  - **Tu propio agente:** prendido, contesta el agente del cliente (su endpoint compatible con OpenAI, por una conexión de **Modelos**) y Atentina pone la voz y el teléfono; se ocultan **Herramientas**, **Modelo de lenguaje**, reglas, base de conocimiento y datos ([`AGENTE_EXTERNO_PLAN.md`](AGENTE_EXTERNO_PLAN.md)). Es una opción del agente, no un motor aparte.
  - **Modelo de lenguaje:** el de Atentina o los proveedores del cliente por etapas, con sus parámetros.
- **JSON:** la misma definición en JSON (formato en [`ARQUITECTURA.md`](ARQUITECTURA.md#definición-de-un-agente)), para pegar o editar a mano. Para salir de la pestaña el JSON tiene que parsear: lo escrito pasa al formulario.
- En las cinco pestañas de edición y en JSON:
  - **Validación:** se valida mientras editás; los errores aparecen arriba y, al hacerles click, te
    llevan a la pestaña y al campo (o a esa parte del JSON).
  - **Guardar:** crea una **versión nueva**, o avisa "Sin cambios" si no cambió nada. Las llamadas en
    curso siguen con la versión con que empezaron.
  - `id` y `version` los pone la app (el slug y el número de versión): no hace falta tocarlos.
  - Si salís del agente con cambios sin guardar, avisa.
- **Versiones:** historial con fecha y autor. Podés ver el JSON de cualquier versión, compararla con
  la vigente y **Restaurar**, que guarda esa definición como versión nueva.
- **Probar:** lo mismo que la pantalla **Playground** (abajo), con este agente fijo.
  - **Probar por voz:** elegís la voz y **Probar agente** te lleva a la llamada en el navegador
    (`/calls/<id>/hablar`). Si este agente ya tiene una prueba esperando que alguien se conecte, entra a esa
    en vez de crear otra; si no, la crea. No marca teléfonos ni gasta minutos. Las salientes a un
    teléfono, en **Llamadas**.
  - **Conversación por texto:** chateás con el agente sin voz. Los datos aparecen al terminar la
    conversación; las llamadas a herramientas se ven en la traza de cada respuesta (argumentos, estado,
    tiempo y resultado).
  - **Link para llamar:** lo crea, o lo muestra para copiar o abrir; **Configurar** lleva a la pestaña
    Link para llamar (nombre, imagen, límites, pausar, regenerar).

**Agentes > Playground** (`/probar`): elegís el agente en una tarjeta con su
objetivo (sale de la definición; con más de 6, hay buscador) y abajo lo
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
     después, en la fila del número. Un número asignado arranca atendido por **el equipo, sin personas**
     (columna **Atiende**: "Equipo sin personas"): hasta que se elija quién atiende, las entrantes van al
     agente del número, y sin agente no las atiende nadie. **No lo dejes sin agente ni sin personas.**
3. **Quién atiende:** en la fila de cada número (lápiz de **Editar**, en Números, en la ficha del cliente o
   en Mi cuenta), sección **Quién atiende las entrantes**. Lo puede cambiar el admin o el propio cliente.
   - **El agente:** elegís el agente del cliente que atiende las entrantes a ese número (el selector también
     está directo en la fila). El agente puede derivar al equipo con sus áreas, como siempre.
   - **El equipo** (planes con llamadas directas; en el Free queda deshabilitado y se explica por qué): atienden
     personas, sin agente, y la llamada se graba. Se configura acá mismo:
     - **Personas:** las de Equipo, en el orden en que suenan (**Agregar persona al número**, **Quitar del
       número**); al menos una. Cada una muestra por dónde le puede sonar: su celular, "Solo en el panel"
       (tiene usuario del panel pero no celular), "Solo en el celular" o "No le puede sonar".
     - **Suena primero:** **En su celular** (llama al celular de cada persona, en orden, y si ninguna atiende suena en
       el panel a las que están Disponibles) o **En el panel** (suena a todas las Disponibles a la vez y, si nadie
       atiende, llama a los celulares en orden).
     - **Timbre por persona:** de 5 a 60 s (20 por defecto) antes de pasar a la siguiente.
     - **Horario (opcional):** por día, igual que en las áreas de Equipo.
     - **Si nadie atiende o es fuera de horario:** **Pasa al agente** (el **Agente de respaldo**, que arranca
       sabiendo que nadie del equipo contestó), **Deja un mensaje y graba lo que dice quien llama** o **Dice el
       mensaje y corta**; en estos dos, el **Mensaje** es opcional (vacío usa el de siempre).
   - Con el equipo elegido y el cliente sin las condiciones nuevas aceptadas (ver Problemas frecuentes), la
     entrante va al agente del número.
4. **Liberar:** devuelve el número al inventario, sin cliente ni agente, y sus entrantes dejan de
   atenderse. **Borrar:** solo los libres.

Al **cargar o borrar** números, la app los agrega o quita sola del trunk entrante de LiveKit, en
caliente: no hay que reiniciar nada ni se cortan llamadas.

**Varios números en la misma cuenta de Anura:** cada entrante va al agente del número marcado (Anura
manda el número en la llamada, verificado el 29-sep-2026). Si no llega un número válido, va al número
principal de la cuenta (`ANURA_DID`). Ver [`TELEFONIA_ANURA.md`](TELEFONIA_ANURA.md).

### 4b. WhatsApp (entrando como el cliente)

El cliente conecta sus números solo (ver [WhatsApp (cliente)](#whatsapp-cliente)). Para ver los de un cliente o
conectarle uno, el admin entra como el cliente. El **alta manual**, para números de nuestro portafolio (nuestra
WABA, con `WA_ACCESS_TOKEN`), la hace el admin entrando como el cliente: el botón y la columna **Token** solo
aparecen en soporte. En soporte también se editan, registran y ven las plantillas de esos números.

Conecta un número de WhatsApp Business a un agente del cliente. Responde texto y notas de voz: si el
contacto manda un audio, el agente lo transcribe y contesta con una nota de voz con la voz del agente
(ver [`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md)).

1. **WhatsApp > Alta manual** (en soporte): agente que responde, **Phone number ID** y **WABA ID**
   (de Meta: WhatsApp → Configuración de la API; el ID, no el teléfono), número visible y nombre.
2. **Token:** vacío usa el del system user (`WA_ACCESS_TOKEN`). Uno propio solo para números de otro
   portafolio; no se vuelve a mostrar (la tabla dice "Propio" o "Global").
3. **Editar:** agente por defecto, número visible, nombre y token. El agente nuevo vale para las
   conversaciones nuevas; las en curso siguen con el suyo.
4. **Ruteo por contacto** (menú de la fila): agrega uno o más agentes y, a cada uno, la lista de
   contactos que atiende (el WhatsApp con código de país, ej. `5493511234567`; Enter después de cada
   uno). Esos contactos los atiende ese agente en los mensajes y las llamadas de WhatsApp; los demás,
   el agente por defecto. Se ve debajo del agente ("N reglas por
   contacto").
5. **Desactivar:** los mensajes a ese número dejan de responderse. No hay borrado: las conversaciones
   lo referencian. **Activar** lo vuelve a habilitar.

Si el cliente está desactivado, sus números de WhatsApp tampoco responden.

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
- **Uso de la API** (`Developers > Uso de la API` del cliente y `/admin/inference-requests` del admin): cada pedido a
  la API de inferencia, con fecha, key, tipo, estado, duración y consumo, y los totales del filtro. Filtros: API
  key, tipo, estado, streaming y período; la del admin suma la columna y el filtro de cliente y los datos técnicos.
  Desde la tarjeta de consumo, **Ver los pedidos** abre esta pantalla filtrada por el cliente.
  - **Revocar** la anula en el acto.

## Operación diaria

### Inicio (dashboard)

`/` en el panel del cliente; `/admin` es el de toda la plataforma, con el filtro de cliente y la columna Cliente.

- **Filtros:** cliente (solo en `/admin`), agente y período (última semana, último mes o fechas). Aplican a
  los indicadores y al gráfico. Los días son del huso horario del navegador. **Ver conversaciones**
  lleva al listado con los mismos filtros.
- **Nueva llamada:**
  - **Agente:** los no archivados.
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
  panel del cliente los muestra como "Completas" y "Tiempo de respuesta".
- **Conversaciones por día** (barras) y **Resultado por día** (líneas: % con workflow completo y %
  con objetivo cumplido).
- Para ver más (conversión, mapa de calor por hora, transferencias, campañas), **Reportes** (más abajo).
### Reportes (`/reports` del cliente y `/admin/reports`)

Estadísticas del negocio para decidir: cuánto te consultan, cuántas consultas terminan bien y si el plan
alcanza. En la navegación, debajo de Inicio.

- **Filtros (arriba):** período (últimos 30 días por defecto; los KPIs se comparan con el período anterior),
  agente, canal (llamadas, WhatsApp o web), línea y **Incluir pruebas** (apagado: las llamadas de prueba y del
  Playground quedan fuera). En `/admin/reports` se suma el selector de cliente, con **Todos**.
- **Pestañas:**
  - **Resumen:** consultas por día (llamadas y WhatsApp apiladas) con cuántas terminaron en una
    transferencia, KPIs (conversaciones, % de conversión, % derivadas, minutos, duración media) y el
    consumo de minutos del plan con la proyección a fin de mes.
  - **Llamadas:** por día y modo (con las **Directas** como serie propia), mapa de calor por día y hora, por línea
    y por agente, duración, cómo terminaron y llamantes nuevos o que vuelven. Si el equipo usó el teléfono:
    **Por tipo** (con el agente, directas que hace el equipo y entrantes que atiende el equipo: llamadas,
    minutos y duración media) y **Por usuario** (directas y entrantes atendidas de cada persona). Las del
    equipo cuentan como llamadas y minutos, no en conversión ni resultados.
  - **Resultados:** conversión (completa, parcial o sin datos), resultados por agente, embudo, datos
    capturados por campo y comparación por versión del agente.
  - **Mensajes:** WhatsApp por día y hora, texto o nota de voz, entrega y estado de la cuenta.
  - **Transferencias:** pedidas, atendidas y no atendidas, por área y por persona del equipo.
  - **Campañas:** comparativo, embudo, motivos de no contacto y mejor horario.
  - **Técnico** y **Plataforma** (solo en `/admin/reports`; Plataforma, con cliente en Todos): latencia,
    herramientas, errores y tokens; clientes con alertas ("cerca del cupo" y "inactivo"), negocio y operación.
    No están en el panel del cliente, tampoco entrando como él.
- **Plan:** Resumen y Llamadas están en todos los planes. Resultados, Mensajes, Transferencias y Campañas son
  de los planes con reportes completos: en el Free se ve el aviso con **Mejorar mi plan** y el panel
  atenuado. En `/admin/reports` se ven siempre.
- **Descargar CSV:** cada tabla o gráfico tiene su botón, con los datos tal como se ven con los filtros
  elegidos.
- El panel del cliente no muestra nada técnico (latencia, herramientas, errores internos): eso es de las pestañas de
  `/admin/reports`.

### Conversaciones (`/calls` del cliente y `/admin/calls`)

- Todas las conversaciones (llamadas, API y WhatsApp), con los mismos filtros que el inicio (agente y período; en
  `/admin/calls`, también cliente), en la URL.
- Se puede filtrar por campaña (también en Inicio): los intentos de una campaña de llamadas y las
  conversaciones que abrió la respuesta de un contacto.
- Tabla paginada, filtrable además por estado y origen. Las de WhatsApp no tienen estado ni duración y
  muestran el teléfono del contacto. Cada fila lleva al detalle.
- **Llamadas del equipo** (planes con llamadas directas): el origen **Directa** es la que hace una persona desde
  Teléfono, y **Entrante del equipo** la que atendió una persona en un número del equipo. Sin agente, la columna
  del agente dice "Llamó: Ana" o "Atendió: Ana" (o "Atendió: nadie"), y no tienen datos obtenidos ni resultado.
  Dos filtros más: **Atendió** (todas, agente o equipo) y **Usuario** (quién llamó o atendió); el admin elige
  antes un cliente.
- **Borrar (solo en `/admin/calls`):** cada fila tiene el ícono de borrar a la derecha y las casillas para
  seleccionar varias estilo Gmail (la del encabezado selecciona la página; la barra muestra cuántas
  hay y las borra juntas). Siempre pide confirmación. Se borra la conversación con sus mensajes,
  grabaciones y su consumo del mes; las que tienen una llamada en curso no se pueden borrar.

### Llamadas (`/outbound`)

- El agente llama a un contacto **con un motivo**: por ejemplo, la consulta que la persona dejó en la web
  ("quiero el precio de la BJ30 en plan de ahorro"). El agente arranca por ahí, sin preguntar lo que el
  motivo ya dice.
- **Formulario:** agente, destino (un contacto de la agenda, buscado por nombre o teléfono, o un número
  suelto en formato +549…), número de origen, motivo (hasta 2000 caracteres) y **Llamar**. Con un contacto,
  su nombre, email e ID externo también le llegan al agente (como en una campaña: `{{nombre}}` en la apertura).
- **Modo prueba:** no marca; te conectás por navegador y hacés de contacto. Usa solo el motivo.
- Un número en la lista de bajas de voz del cliente (Contactos, Bajas) no se llama (409).
- **Últimas llamadas:** las 10 salientes más nuevas, con estado, duración y resultado. El resultado sale
  de la definición del agente (por ejemplo, área y urgencia). Si el agente tiene prendido el resumen por
  email, al cortar le llega al equipo, con el motivo.
- El detalle de la llamada muestra el motivo en "Motivo del llamado".
- Acá llama el agente. Para llamar vos, hablando desde el navegador, está **Teléfono** (abajo).

### Teléfono (`/telefono`)

Llamadas **sin agente** ([`LLAMADAS_DIRECTAS_PLAN.md`](LLAMADAS_DIRECTAS_PLAN.md)): hablás vos (o alguien de tu
equipo) desde el navegador, y el contacto ve el número de la empresa. Está en **Organización > Teléfono** en los
planes con llamadas directas; en el Free la pantalla muestra el aviso de plan con **Mejorar mi plan** y queda
atenuada. Toda llamada del equipo **se graba y se transcribe** (queda en Conversaciones); el aviso "Esta llamada
está siendo grabada." es opcional (Mi cuenta). Entrando como el cliente (soporte) no se puede llamar ni atender.

**Llamar**
1. **Sale desde:** el número que ve el contacto. Aparece solo si tu cuenta tiene más de un número; se recuerda
   en este navegador. Sin ningún número asignado hay un aviso y no se puede llamar.
2. Elegí un contacto de la agenda (buscador por nombre o teléfono) y tocá **Llamar**,
   o escribí un número en **O marcá un número** (formato internacional, `+5493515551234`) y **Llamar**.
   A la derecha, el contacto elegido con su nota, su historial (**Últimas llamadas**, las del agente y las
   directas) y **Ver la ficha**. Abajo, **Mis últimas llamadas** (entrantes y salientes tuyas).
3. El navegador pide el micrófono. Usá auriculares: sin ellos la voz del contacto vuelve como eco.
4. **Contacto que pidió no recibir llamadas** (marca "No quiere llamadas"): se puede llamar igual, con una
   confirmación ("Llamar igual"); en el detalle de la llamada queda quién lo confirmó.
5. **Bloqueado** (Contactos, Números bloqueados): el botón queda apagado y el tooltip dice por qué. También se
   apaga si ya estás en una llamada.

**Barra de llamada** (abajo, en todo el panel del cliente; la llamada sigue mientras navegás):
- Estados: Conectando micrófono, Conectando, Llamando, Sonando, En curso (con el tiempo) y, al terminar,
  Terminada (también "no atendió", "ocupado", "falló" o "cortada"), con **Ver la conversación**.
- **Silenciar** / **Activar micrófono**, **Teclado** (para menús tipo "marque 1") y **Transcripción** (las frases
  en vivo, del contacto y tuyas). Si el navegador frena el audio, aparece **Activar el audio**.
- **Cortar** termina la llamada. Al cerrar o recargar la pestaña el navegador avisa; si se recarga igual, la
  barra dice "Tenés una llamada en curso" con **Volver a entrar** (en esa pestaña).
- Al terminar una llamada a un número que no está en la agenda, **Guardar como contacto**.
- Sin llamada, la barra muestra el link a Teléfono y el switch **Disponible**.

**Recibir llamadas en el panel**
- **Disponible** (switch en el encabezado de Teléfono y en la barra): mientras está prendido y el panel abierto,
  te suenan las entrantes de los números atendidos por el equipo donde estés en la lista de personas (ver [Números
  de teléfono](#4-números-de-teléfono-números), **Quién atiende**). Hace falta que tu usuario esté asociado a una
  persona de Equipo.
- Una entrante muestra "Llamada entrante", el número o contacto, la línea a la que llaman y un timbre. **Atender**
  te pasa a la llamada; **Rechazar** la saca solo de tu pantalla. Si la atiende otra persona primero, el aviso
  es "La atendió otra persona".
- Si el número suena primero en el celular, la persona atiende ahí ("marcá 1 para atender") y no hace falta el panel.
- En el celular se puede usar el panel como teléfono con la pestaña abierta y la pantalla encendida: con la
  pantalla bloqueada el navegador puede cortar el micrófono. Para recibir llamadas con el celular apagado o la
  app cerrada, cargá el celular de la persona en Equipo.

**Llamada creada desde la API o el MCP** (por ejemplo, tu agente de IA que pide "llamá a Juan"): la API devuelve un
link `/telefono/llamada/<id>`. Al abrirlo con tu usuario aparece **Entrar a la llamada** (A, Desde): el click da el
permiso del micrófono y la llamada sigue en la barra. Si la abre otro usuario, "La llamada es de otro usuario";
si ya terminó, "La llamada terminó" con el link al detalle. Sin entrar en 2 minutos, la llamada falla
(`user_not_joined`).

### Detalle de una llamada (`/calls/<id>`)

- **Cabecera:** contacto, empresa, origen, número del cliente, fecha, estado, duración, motivo de fin,
  datos obtenidos, resultado, y agente con versión. En una llamada del equipo (sin agente) no hay datos ni
  resultado: en lugar del agente dice **Llamó** o **Atendió** con la persona, la conversación ocupa todo el ancho
  y, si se llamó a un contacto que había pedido no recibir llamadas, un aviso amarillo dice quién lo confirmó.
  Cada frase trae su audio (la grabación es siempre) y el chat rotula "Contacto" o "Quien llamó".
- **Estado:** cada dato a obtener, con su valor, si está pendiente o no aplica, y los valores
  rechazados. Los recién obtenidos se resaltan unos segundos.
- **Conversación:** el chat. Con **Salida del LLM** se despliega lo que devolvió el LLM en cada turno
  (conversación y extracción, con su tiempo y razonamiento); si el agente tiene **Grabar audio**
  prendido, cada mensaje trae el reproductor de su WAV. En una llamada derivada, el tramo con la persona del
  equipo empieza con el separador "Llamada con <persona>", y lo que dijo ella va del lado del agente, en una
  burbuja blanca con borde y su nombre ("Ana Pérez (equipo)").
- **Latencia por turno:** E2E, EOU, STT, endpointing, LLM, TTS y audio, con promedios y máximos.
- En el panel del cliente (también entrando como él), las dos cosas son **Detalle técnico**: el interruptor del
  chat y, al final, una tarjeta plegada con la latencia. En `/admin/calls/<id>` se ven a la vista, con el cliente
  en la cabecera, y **Abrir como el cliente** abre la conversación en su panel.
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
| `person_hangup` | Cortó la persona del equipo (llamada directa o entrante del equipo). |
| `user_not_joined` | Una directa creada por API o MCP: el usuario no entró a la llamada a tiempo. |
| `after_hours`, `team_no_answer` | Entrante de un número del equipo: fuera de horario, o nadie atendió (pasó al respaldo del número). |

### Agentes (cliente)

El usuario de un cliente (o el admin que entró como él) crea y edita sus propios agentes; no ve ni puede tocar los de
otro cliente.

1. **Agentes > Nuevo agente:** nombre, descripción (opcional) y punto de partida (asistente básico o
   en blanco). Te lleva a la pestaña **Conversación**.
2. **Conversación**, **Datos**, **Herramientas**, **Voz y canales** y **Modelo:** las cinco editan la misma
   definición (agente, objetivo y apertura, reglas, base de conocimiento; datos a obtener y resultados;
   herramientas, secretos y derivación; voz, grabación y resumen por email; modelo). Se valida mientras editás y
   **Guardar** crea una versión nueva con lo de todas.
3. **Versiones:** historial con autor; **Restaurar** guarda una anterior como versión nueva.
4. **Probar:** conversación por texto, llamada de prueba o link para llamar, antes de ponerlo a
   atender. También desde **Agentes > Playground** en el menú, o con **Probar** en la lista.
5. Arriba, **Editar** (nombre y descripción), **Archivar/Desarchivar** y **Borrar** (solo si nunca
   tuvo conversaciones ni atiende un número de WhatsApp).
6. Para que atienda: elegilo en **Mi cuenta > Números** o en **WhatsApp**.

La pestaña **JSON**, el slug y **Ver prompt** los ve todo cliente, como el admin. Por API el cliente hace lo
mismo con su API key (`POST /api/v1/agents` sin `client_id`); `engine` ya no existe en la definición
(el de una definición vieja se ignora) y tu propio agente es `external`.

### Modelos (cliente) y Modelo de lenguaje de un agente

Por defecto todos los agentes contestan con el modelo de Atentina, **atentina-conversational-v1** (el
servidor propio: la conversación no sale). Con **BYOK** el cliente trae la clave de su proveedor y elige,
por agente, desde qué turno lo usa ([`BYOK_LLM_PLAN.md`](BYOK_LLM_PLAN.md)).

1. **Modelos > Nueva conexión** (el admin, en la ficha del cliente, pestaña **Modelos**, o entrando como él): proveedor
   (Anthropic, OpenRouter u OpenAI compatible, con su URL base), nombre, API key y modelo por defecto.
   Al guardar se **prueba** sola: dice si la clave y el modelo andan, cuánto tardó y cómo pide el JSON
   ese proveedor. La clave se guarda cifrada y no se vuelve a mostrar (solo `…1234`).
2. En la lista: **Probar** de nuevo, **Editar** (nombre, modelo, o rotar la clave) y **Dar de baja**.
   La columna *Agentes* dice cuántos la usan: al darla de baja pasan a atentina-conversational-v1.
3. **Agente > Modelo > Modelo de lenguaje:** arriba se elige entre **Modelo atentina-conversational-v1**
   (el default) y **Mis proveedores, por etapas**. La segunda opción se habilita cuando el cliente ya cargó
   una conexión; sin ninguna, la sección lo explica con el botón **Cargar una clave**. Volver al modelo de
   Atentina pide confirmación y quita las etapas.
4. **Configurar parámetros del modelo** despliega todos los parámetros del modelo (temperatura, `top_p`,
   `top_k`/`min_p`, razonamiento y su tope, máximo de tokens…) con su **valor por defecto**, el recomendado
   para el modelo. Para cambiarlos: **Cambiar valores** y confirmar (se pregunta una vez por
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

### Herramientas (`/tools`)

Lo que el agente puede hacer durante una conversación ([`TOOLS_PLAN.md`](TOOLS_PLAN.md)): consultar un turno,
crear una reserva, buscar una deuda. Está si el plan incluye
herramientas (`max_tools`); las de código, si incluye `code_tools`.

- **Nueva herramienta > Llamar a una API:** método y URL (con `{variables}` de la ruta) y pestañas
  **Ruta**, **Query**, **Headers**, **Body**, **Autenticación**, **Respuesta** y **Mientras se espera**. Cada parámetro
  lo completa **el agente** (con una descripción: qué dato es) o es un **valor fijo** (puede llevar
  `{{secrets.NOMBRE}}`, `{{call.from}}` y otras variables, del botón **Variables**, que también crea un
  secreto nuevo). El agente solo ve los que completa. **Autenticación:** elegir una **Credencial** del
  cliente o crearla ahí (**Nueva credencial**: Bearer, API key en header o query, Basic u OAuth2 client
  credentials, con su valor); "Configurada en esta herramienta" es la opción avanzada. **Lo que ve el
  agente** muestra la función tal como le llega al modelo, y **Secretos que pide** marca **Cargado** o
  **Falta** (con **Cargar valor**).
- **Nueva herramienta > Escribir código:** una función en JavaScript (`export default async function
  ({ args, secrets, call, vars })`) que arranca con un ejemplo. Al lado: **Parámetros**, **Secretos que
  usa** (llegan en `secrets`), **Hosts permitidos** (la función solo puede llamar a esos dominios) y el
  tiempo máximo.
- **Probar** (los dos tipos): los argumentos como los mandaría el agente; usa los secretos del cliente,
  los valores propios de un agente si se elige uno, o valores solo para la prueba (no se guardan), y el resultado: el pedido enviado (con los secretos
  tachados), la respuesta, lo que recibe el agente y los logs del código. Llama de verdad a la API.
- Para que un agente la use: en el agente, **Herramientas** (la pestaña del agente), elegirla; si le falta
  un secreto, la herramienta dice **Falta X** y se carga ahí (**Cargar valor**: para todos los agentes o
  solo este). Sin sus secretos el agente no se guarda. Cambiar una herramienta rige en todos los agentes
  que la usan; no se puede borrar mientras un agente la use.

### Secretos

**Agentes > Secretos**: lo que usan las herramientas para entrar a los sistemas del cliente.

- **Credenciales:** la autenticación de cada API (nombre, tipo y sus datos, y el valor, que se guarda en un
  secreto). Se crean acá o desde la herramienta; **Editar** cambia todas las herramientas que la usan. No se
  borra mientras una herramienta la use.
- **Secretos:** tokens y claves para todos los agentes, `{{secrets.NOMBRE}}` en una herramienta. Se
  escriben una vez y no se vuelven a mostrar (`••••` y los últimos 4); **Reemplazar valor** los rota en
  todos los agentes. **Falta** marca los que piden las herramientas y no están. **Agentes con otro valor:**
  los que tienen uno propio (se carga en el agente, **Usar otro valor acá**; **Pasar al cliente** lo sube
  para todos).

### Voces

Catálogo de las 41 voces del TTS, con género, WER y velocidad (car/s), filtrable, y la prueba de voz.
La voz por defecto de un agente es `agent.voice` en su definición.

### WhatsApp (cliente)

Conectá tu número de WhatsApp Business para que lo atienda uno de tus agentes, por texto y notas de voz. Se conecta
con **tu propia app de Meta** ([`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md), 5.9); el registro con Facebook (Embedded
Signup) queda oculto mientras `WA_EMBEDDED_SIGNUP=false` (falta el Tech Provider).

1. **Conectar con mi app de Meta:** la ventana trae la guía (crear en tu Business Manager una app tipo Business con
   WhatsApp, pasarla a Live y crear un usuario de sistema con token permanente con `whatsapp_business_messaging`
   y `whatsapp_business_management`) y el formulario: Phone number ID, WABA ID, token, app secret y agente. Al
   guardar, la plataforma valida el número contra tu WABA y suscribe tu app.
2. **Datos del webhook:** el panel te da la **URL del webhook de tu número** y su **verify token** (menú de la fila >
   **Datos del webhook**). Pegalos en tu app de Meta (Webhooks > WhatsApp Business Account) y suscribí `messages`.
3. **Medio de pago:** Meta cobra los mensajes a tu cuenta, no a nosotros. Cargalo en
   [WhatsApp Manager](https://business.facebook.com/wa/manage/home/).
4. **Estado** de cada número (con el badge **App propia**):
   - **Conectado:** responde.
   - **Pendiente:** falló la suscripción o el registro en Meta. Menú > **Reintentar suscripción** o **Reintentar
     registro** (con el PIN si Meta dice que es incorrecto).
   - **Desconectado:** Meta rechazó el acceso (lo quitaste o venció). Menú > **Actualizar token**.
   - **Calidad** (Alta, Media, Baja) y límite de envío, según Meta. **Releer datos de Meta** los actualiza.
5. **Agente:** se cambia en la fila; vale para las conversaciones nuevas.
6. **Ruteo por contacto:** en el menú de la fila, elegí los agentes y cargá los contactos que atiende
   cada uno (mensajes y llamadas de WhatsApp); los demás los atiende el agente por defecto.
7. **Plantillas:** abajo, por número. Lista las de tu cuenta con su estado (En revisión, Aprobada,
   Rechazada con el motivo) y **Nueva plantilla** crea una (nombre en minúsculas y `_`, categoría
   Utilidad o Marketing, cuerpo con `{{1}}`, `{{2}}`… y un ejemplo por variable). Meta la revisa.
8. **Desactivar** deja de responder ese número; **Activar** lo vuelve a habilitar.
9. Con **Embedded Signup** prendido aparece también **Conectar WhatsApp** (ventana de Meta; solo desde
   `https://app.atentina.com.ar`).
10. Un número de **alta manual** (nuestra WABA, que carga el admin entrando como el cliente) no muestra registro,
    datos de Meta ni plantillas al cliente: los maneja el admin.

### Contactos (`/contacts`)

La agenda del cliente: de ahí salen los destinatarios de las campañas. Lo único obligatorio es el teléfono
(único por cliente, se normaliza a formato internacional); nombre, email, ID externo y una nota (texto libre, como la de un contacto del teléfono)
son opcionales.

1. **Nuevo contacto** o **Importar CSV**: encabezado `telefono` (obligatorio), `nombre`, `email`, `id_externo`,
   `notas`; las demás columnas se ignoran. La vista previa muestra las columnas; el resultado, los
   creados, actualizados, archivados e inválidos (con fila y motivo). Un contacto que ya existe se actualiza:
   lo que no viene no se pisa; la nota solo cambia si viene con texto.
2. **No se borran, se archivan.** El filtro Activos / Archivados / Todos muestra el resto. Se archiva uno
   o varios seleccionados. Un archivado no entra en campañas nuevas y se saltea en las
   que tenía pendientes. Recargar su teléfono no lo desarchiva: **Desarchivar** es explícito.
3. **Ficha** (clic en la fila): datos, nota y campañas en que participó o participa.
4. **Tope:** el tier limita los contactos activos de la agenda.
5. **Llamar:** el ícono de teléfono de cada fila y el botón **Llamar** de la ficha hacen una llamada directa
   (hablás vos, desde el navegador; ver [Teléfono](#teléfono-telefono)), saliendo del número que elegiste
   en Teléfono. Apagado, con el motivo en el tooltip, si el plan no la incluye, el número está bloqueado,
   ya estás en una llamada o no tenés número asignado. Que llame un **agente** es otra cosa: **Canales >
   Llamadas** o una campaña.
6. **Números bloqueados** (al final): sus llamadas entrantes, por la línea o por WhatsApp, se cortan sin
   atender y quedan como rechazadas (`blocked_number`). Se cargan acá (teléfono y motivo) o desde el detalle
   de una llamada (**Bloquear número**). No cambian las campañas: para no llamar a alguien están las bajas.

### Equipo (`/team`)

Las personas del cliente a las que el agente les pasa una llamada o un chat, agrupadas en áreas
([`DERIVACIONES_PLAN.md`](DERIVACIONES_PLAN.md)). A qué áreas deriva cada
agente se elige en su definición, **Derivación a personas**.

1. **Personas:** nombre, teléfono (para transferirle llamadas; solo Argentina), WhatsApp (para el puente de
   WhatsApp; único por cliente) y **Usuario del panel** (para que atienda llamadas desde el panel con
   Disponible; cada usuario es de una sola persona). Hace falta al menos uno de los tres: puede ser solo el
   usuario del panel. El tier limita cuántas. Con llamadas directas, la tabla suma **En el panel**: Disponible
   (verde), En una llamada (amarillo), No disponible (gris) o raya si no tiene usuario. Las personas de un
   número del equipo se eligen en Números, **Quién atiende**.
2. **Áreas:** nombre y qué atiende (lo lee el agente para elegir el área), personas en el orden en que se las
   llama (**En orden** o **Rotativa**), timbre por persona (20 s por defecto: el buzón de Claro atiende a los
   ~33 s), horario por día con días cerrados (o **Atiende siempre**), qué hace el agente si la persona corta
   (vuelve con "¿Te puedo ayudar con algo más?" o se despide) y la tecla con la que la persona le devuelve la
   llamada a la IA (2 por defecto; nunca con `*`, que la central de Anura toma como código).
3. **Mensajes:** cada momento (antes de transferir, el aviso a la persona, no atiende, ocupado, fuera de
   horario, vuelta y despedida) tiene un texto por defecto; se cambia por área, con `{{area}}`, `{{persona}}`,
   `{{cliente}}`, `{{resumen}}` y `{{horario}}`.

### Campañas (`/campaigns`)

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
   - **Destinatarios:** contactos elegidos de la agenda o un CSV (que también los carga en la agenda).
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
en la pestaña Consumo y datos de la ficha del cliente. La API no cuenta lo que consumen los agentes integrados (llamadas y WhatsApp).

### Mi cuenta (cliente)

- **Consumo del mes:** llamadas activas, minutos entrantes y salientes, y números, cada uno contra
  su tope.
- **Números:** editás la etiqueta y **quién atiende** cada número: un agente tuyo o el equipo, con sus personas,
  timbre, horario y respaldo (ver [Números de teléfono](#4-números-de-teléfono-números)). Asignar y liberar
  números lo hace el admin.
- **API keys:** crear y revocar.
- **Llamadas del equipo:** switch **Avisar que la llamada se graba**. Las llamadas que hace el equipo desde el
  panel y las que atiende en un número del equipo se graban siempre; con el switch prendido (apagado por
  defecto), al empezar suena "Esta llamada está siendo grabada." Avisar a quien llama y tener su
  consentimiento es responsabilidad de tu empresa. Está atenuada en los planes sin llamadas directas.
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
- **Plan (`/plan`, cliente):** datos para la factura y planes con precio. Entrando como el cliente es de solo lectura. Se pagan con **tarjeta**
  (débito automático de Mercado Pago, se activa en el momento; con uno activo, cambiar de plan no pide la
  tarjeta) o por **transferencia** (ve los datos bancarios y manda el comprobante por email).
- **Lo que el plan no incluye** ([`FUNCIONES_POR_PLAN_PLAN.md`](FUNCIONES_POR_PLAN_PLAN.md)): el cliente ve
  un candado en la navegación (Llamadas, WhatsApp, Contactos, Teléfono, Equipo, Campañas) y, en esa pantalla, un aviso
  con borde amarillo, en qué planes está ("Disponible en los planes Mostrador y Sucursal") y "Mejorar mi plan"; lo de abajo queda atenuado y sin responder. Con plan gratis, "Free"
  al lado de Plan. Sale de los campos del tier (minutos salientes y números, canales de campañas, contactos,
  equipo, links y la casilla **WhatsApp**) y de los ajustes del cliente: un ajuste abre la función. Sin
  salientes, "Nueva llamada" de Inicio y Probar del agente quedan fijos en modo prueba.
- **Ficha del cliente, tarjeta "Plan pago" (admin):** "Registrar pago" activa o renueva el plan por un
  mes; "Rechazar pedido" o "Pasar al gratuito" lo corta.
- **Cobros (`/admin/billing`, admin):** planes pagos y pedidos abiertos, y pagos para facturar ("Marcar facturado").
- **Olvidé mi clave:** link en el ingreso (`/forgot-password`); manda un link nuevo por mail.

### Mi perfil (`/profile` y `/admin/profile`)

Ícono de usuario arriba a la derecha, al lado de "Salir".

En soporte (entrando como un cliente) el perfil es de solo lectura: es el del cliente, no el tuyo; el tuyo está en
`/admin/profile`.

- **Tus datos:** el nombre (sale en los mails).
- **Email de ingreso:** escribís el nuevo y "Mandar código"; el código de 6 dígitos llega al email **actual** y
  con él se confirma el cambio.
- **Clave:** "Mandar código", y con el código del mail elegís la nueva (al menos 10 caracteres).
- El código vale 15 minutos y una sola vez. Al cambiar el email o la clave se cierran las otras sesiones
  abiertas; la de esta pestaña sigue.

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| Las entrantes suenan y cortan ("ocupado") | El número no tiene agente, o está libre; o lo atiende "Equipo sin personas" y no tiene agente. Elegí quién atiende en Números o en la ficha del cliente. Log del agente: `no tiene cliente o agente asignado`. |
| Una entrante escucha "no podemos atender tu llamada" | El tier no deja: tope de simultáneas, de llamadas por hora, día o mes, minutos entrantes agotados o cliente inactivo. Mirá el consumo del cliente. |
| Todas las entrantes van al mismo agente | No llega el número marcado y cae al principal (`ANURA_DID`). Mirar el log de Asterisk (`Entrante de Anura: ... (marcado: ...)`) y que cada número tenga su agente. |
| "Llegaste al límite…" al llamar | Tope del tier. Esperá que terminen llamadas, subí el tier o el tope. |
| Un número nuevo no recibe llamadas | No entró al trunk de LiveKit (ver el log de `app`; se arregla con `make livekit-sip`), o Anura no lo entrega a esta troncal. |
| "Conectar WhatsApp" (Embedded Signup) abre y se cierra, o da error de dominio | Solo con `WA_EMBEDDED_SIGNUP=true`. Se entró por `http://` o por un dominio que no está en la app de Meta: usar `https://app.atentina.com.ar`. |
| Un número de WhatsApp con app propia no recibe mensajes | La URL del webhook y el verify token (**Datos del webhook**) no están pegados en la app de Meta, o falta suscribir `messages`. |
| Un número de WhatsApp queda "Pendiente" | Falló la suscripción o el registro en Meta (ej. PIN de dos pasos incorrecto, 133005): **Reintentar suscripción** o **Reintentar registro** con el PIN correcto. |
| Un admin no encuentra herramientas, WhatsApp o campañas en su menú | Son del panel del cliente: **Entrar como el cliente** desde su ficha. |
| La prueba de voz o el chat por texto dan error | El TTS o el LLM no responden (`make health`). |
| Una conexión de modelos "falló la prueba" | El detalle lo dice: clave inválida, modelo inexistente o URL incorrecta (OpenAI compatible), límite del proveedor o sin conexión. Corregí y volvé a **Probar**. |
| Un agente con modelo propio contesta con el servidor Atentina | El proveedor falló y el agente tiene el respaldo activado: mirá en el detalle de la conversación el motivo (`fallback_reason`). Si la conexión se dio de baja, también. |
| El navegador dice "El micrófono está bloqueado" al llamar o atender | No deja usar el micrófono en la página. Candado de la barra de direcciones, Micrófono, Permitir, y volvé a llamar. Si dice "No encontramos un micrófono" o "El micrófono está en uso", conectá uno o cerrá la otra aplicación que lo usa. |
| "Todas las líneas están ocupadas" al llamar (`no_channel`) | No hay canales libres en la troncal de Anura para marcar. Probá en unos minutos; si es siempre, mirá las llamadas activas (Inicio, En vivo) y el tope de canales de la cuenta de Anura. |
| "Falta aceptar las condiciones nuevas" (`terms_pending`) | Las llamadas directas exigen la versión vigente de las condiciones y la política de privacidad, y el cliente todavía no la aceptó. Un usuario del cliente (no el admin en soporte) las acepta en el aviso **Condiciones del servicio** al entrar al panel. Mientras tanto no se llama, no se atiende y no se puede poner un número en el equipo; las entrantes de un número del equipo van a su agente. |
| "Tu plan no incluye llamadas directas" | El tier no tiene **Llamadas directas** (el Free). **Mejorar mi plan**, o el admin lo prende en Tiers. La saliente además necesita minutos salientes. |
| "No tenés un número para llamar" | El cliente no tiene números asignados: los asigna el admin (Números). |
| No suena el timbre de una entrante en el panel | **Disponible** apagado, o el panel (pestaña) cerrado: solo suena con el panel abierto y Disponible prendido (se apaga solo sin señal de la pestaña por un minuto). Tu usuario tiene que estar en Equipo (**Usuario del panel**) y la persona, en el número (**Quién atiende**, **Suena primero**). Con **En su celular** primero, suena en el celular y recién después en el panel. Si el navegador no deja sonar, queda el aviso en la barra de abajo: hacé un clic en la página una vez. Estando en otra llamada no suena. |
| Una entrante del equipo cae al agente, al mensaje o se corta | Nadie atendió o es fuera de horario (`team_no_answer`, `after_hours`): se aplica **Si nadie atiende o es fuera de horario** del número. También si el número está en el equipo pero sin personas activas con celular o usuario del panel. |
| Se escucha el eco de la propia voz en una llamada del equipo | Usá auriculares. |
