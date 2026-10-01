# Guía de la UI

Cómo hacer cada cosa desde la UI (`http://<host>:8011/`; en este server `http://192.168.1.99:8011/`).
Todo lo que hace la UI también se puede hacer por la API (`/api/v1/docs`). La arquitectura está en
[`ARQUITECTURA.md`](ARQUITECTURA.md).

Hay dos roles:
- **Admin:** opera la plataforma y ve todo. Menú: Inicio, Agentes, Voces, Clientes, Números, Tiers y Usuarios.
- **Cliente:** usuario de un cliente, que solo ve lo suyo. Menú: Inicio, Agentes, Voces y Mi cuenta.

## Primer ingreso

1. El primer admin lo crea `make migrate` con `ADMIN_EMAIL` y `ADMIN_PASSWORD` de `.env`. Otro admin
   o cambio de clave: `make create-admin EMAIL=...`.
2. Entrar en `/login` con ese email y clave. La sesión dura `AUTH_TOKEN_HOURS` (12 h). Después de 10
   intentos fallidos en 5 min desde la misma IP para el mismo email, el login se bloquea un rato.
3. Arriba a la derecha: cambiar tema claro/oscuro y Salir.

## Puesta en marcha de un cliente nuevo (admin)

Orden recomendado: **tier → cliente → agente → número → usuario**.

### 1. Crear o elegir un tier (Tiers)

**Tiers > Nuevo tier**: nombre, descripción y límites. Un campo vacío significa ilimitado.

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

**Clientes > Nuevo cliente**: nombre, slug (se arma del nombre; minúsculas, números y `_`) y tier.
Te lleva a la ficha del cliente, que tiene cinco pestañas:

- **Consumo y datos:** consumo del mes con selector de mes (llamadas activas contra el tope,
  minutos entrantes y salientes, números usados), y los datos del cliente:
  - **Cambiar el tier:** se rechaza si el tier nuevo permite menos números de los que tiene.
  - **Activo:** apagarlo impide hacer y recibir llamadas; las entrantes escuchan un aviso y se cortan.
  - **Borrar:** solo si el cliente no tiene conversaciones; si tiene, desactivalo.
- **Números**, **Agentes**, **Usuarios** y **API keys**: ver abajo.

### 3. Crear el agente (Agentes)

**Agentes > Nuevo agente**: cliente, nombre, slug (opcional), descripción y una **plantilla de partida**
(las de `app/agents/templates/`, con motor, voz y objetivo). Te lleva a la pestaña **Definición**.

El detalle del agente tiene cuatro pestañas:

- **Resumen:** la definición en limpio: agente, idioma, versión, objetivo, apertura, reglas, base de
  conocimiento, datos a obtener (orden, tipo, obligatorio, pregunta sugerida) y resultados.
- **Definición:** el JSON del agente (formato en [`ARQUITECTURA.md`](ARQUITECTURA.md#definición-de-un-agente)).
  - **Validación:** se valida mientras escribís; los errores aparecen abajo y, al hacerles click, el
    cursor va a esa parte del JSON.
  - **Guardar:** crea una **versión nueva**, o avisa "Sin cambios" si no cambió nada. Las llamadas en
    curso siguen con la versión con que empezaron.
  - `id` y `version` los pone la app (el slug y el número de versión): no hace falta tocarlos.
  - Si salís con cambios sin guardar, avisa.
- **Versiones:** historial con fecha y autor. Podés ver el JSON de cualquier versión, compararla con
  la vigente y **Restaurar**, que guarda esa definición como versión nueva.
- **Probar:**
  - **Nueva llamada** con este agente: de prueba por navegador o saliente.
  - **Conversación por texto:** chateás con el agente sin voz y ves los datos que va extrayendo y el
    próximo objetivo.

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

**Limitación actual de Anura:** Anura entrega a Asterisk todas las entrantes de una cuenta por la
misma línea, sin decir qué número se marcó. Para que cada número vaya a su agente, cada número
tiene que estar en una cuenta de Anura distinta (o en una troncal con DID). Ver
[`TELEFONIA_ANURA.md`](TELEFONIA_ANURA.md).

### 4b. WhatsApp (admin)

Conecta un número de WhatsApp Business a un agente del cliente (fase 1: solo texto, ver
[`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md)).

1. **WhatsApp > Conectar número:** cliente, agente que responde, **Phone number ID** y **WABA ID**
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
- **API keys** (pestaña de la ficha del cliente, o Mi cuenta para el cliente) > **Nueva API key**:
  - La clave se muestra **una sola vez**, con botón para copiarla y un ejemplo `curl`.
  - Va en `Authorization: Bearer vaas_...` y da acceso a los agentes, números y llamadas de ese
    cliente (sus sistemas disparan llamadas con `POST /api/v1/calls`).
  - **Revocar** la anula en el acto.

## Operación diaria (ambos roles)

### Inicio (dashboard)

- **Filtros:** cliente (solo admin), agente y período (última semana, último mes o fechas). Aplican a
  los indicadores, al gráfico y a la tabla. Los días son del huso horario del navegador.
- **Nueva llamada:**
  - **Agente:** los no archivados; el admin los ve agrupados por cliente.
  - **Teléfono** en E.164 para una saliente, o **Modo prueba**: sin teléfono, te conectás por el
    navegador con el link "Conectate acá…", que se muestra una sola vez.
  - **Número de origen:** opcional, uno del cliente. Hoy Asterisk sale siempre con el de Anura.
  - **Voz:** la del agente, u otra del catálogo con filtros de género, WER y car/s.
  - **Prueba de voz:** escuchás el texto con la voz elegida, directo contra el TTS, sin llamar.
  - Si el tier no deja (sin lugar o sin minutos), el error dice cuál límite.
- **En vivo:** llamadas pendientes, sonando o en curso, con "Ver en vivo".
- **Indicadores:** conversaciones (con cuántas por WhatsApp), llamadas finalizadas, workflow
  completo, objetivo cumplido, fallidas, rechazadas (por límite), minutos y latencia por turno.
- **Evolución de conversaciones:** barras por día y % con workflow completo y con objetivo cumplido.
- **Conversaciones:** tabla paginada, filtrable por estado y origen (llamadas, API o WhatsApp). Las de
  WhatsApp no tienen estado ni duración y muestran el teléfono del contacto. Cada fila lleva al detalle.

### Detalle de una llamada (`/calls/<id>`)

- **Cabecera:** contacto, empresa, origen, número del cliente, fecha, estado, duración, motivo de fin,
  datos obtenidos, resultado, y agente con versión.
- **Estado:** cada dato a obtener, con su valor, si está pendiente o no aplica, y los valores
  rechazados. Los recién obtenidos se resaltan unos segundos.
- **Conversación:** el chat. Con **Salida del LLM** se despliega lo que devolvió el LLM en cada turno
  (conversación y extracción, con su tiempo y razonamiento).
- **Latencia por turno:** E2E, EOU, STT, endpointing, LLM, TTS y audio, con promedios y máximos.
- Mientras la llamada sigue, todo se actualiza cada segundo.
- **WhatsApp:** en lugar de estado, duración y fin de llamada muestra el último mensaje del contacto y
  los envíos fallidos, con el último error de Meta (131047: pasaron más de 24 h desde el último
  mensaje del contacto, no se puede mandar texto libre). No hay latencia por turno. Mientras la
  conversación está activa se actualiza cada 3 s.

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

### Voces

Catálogo de las 41 voces del TTS, con género, WER y velocidad (car/s), filtrable, y la prueba de voz.
La voz por defecto de un agente es `agent.voice` en su definición.

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
| Todas las entrantes van al mismo agente | Anura manda todos los números de una cuenta por la misma línea (ver Números). |
| "Llegaste al límite…" al llamar | Tope del tier. Esperá que terminen llamadas, subí el tier o el tope. |
| Un número nuevo no recibe llamadas | Faltó `make livekit-sip` después de cargarlo, o Anura no lo entrega a esta troncal. |
| La prueba de voz o el chat por texto dan error | El TTS o el LLM no responden (`make health`). |
