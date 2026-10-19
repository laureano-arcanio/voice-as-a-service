# Revisión de arquitectura para la segunda etapa

10-oct-2026. **Análisis y recomendaciones; no implementado.**

Se interpreta «segunda etapa» como la redundancia de las secciones 2 y 3 de
[`arquitectura-diagramas.html`](arquitectura-diagramas.html): dos servidores y entrada
por relay, o telefonía en un VPS. Se contrastó con [`ARQUITECTURA.md`](ARQUITECTURA.md),
[`PRODUCCION.md`](PRODUCCION.md), capacidad y código local. El repositorio tiene
cambios de otras sesiones, incluido billing sin desplegar según su plan; el código
local no acredita por sí solo el estado de producción. No se ejecutaron pruebas de
carga, llamadas ni fallos, ni se modificaron servicios.

## Decisión recomendada

Conservar la app como monolito modular, la inferencia junto al worker de voz y un
único primario de PostgreSQL. Separar los procesos HTTP de los trabajos durables.
Preparar primero la recuperación del trabajo y la admisión por capacidad; después
activar dos servidores. No hace falta introducir Kubernetes ni dividir el negocio
en microservicios para resolver los problemas encontrados.

Para la entrada de voz, **preferir provisionalmente la variante con Asterisk,
LiveKit, SIP y Redis en un VPS**: permite compartir el despacho y evita construir
un balanceador de dos instalaciones independientes de telefonía. La elección queda
sujeta a pruebas de Anura, Meta, WebRTC y latencia por las dos conexiones. Sigue
habiendo inferencia propia; el audio sí transita por la nube. Un VPS único conserva
un punto único de fallo y no equivale a alta disponibilidad integral.

## Mejoras prioritarias

### 1. Persistir WhatsApp antes de confirmar recepción — bloqueante para activo-activo

En [`webhook.py`](../app/whatsapp/webhook.py), `receive` devuelve 200 después de
agendar tareas, antes de asegurar persistencia. Además, el servicio conserva el
texto pendiente, debounce y locks en memoria. El dedupe por `wamid` evita algunos
duplicados, pero no recupera un mensaje confirmado y perdido, ni serializa mensajes
distintos del mismo contacto atendidos por procesos diferentes.

Propuesta: una bandeja de entrada durable en PostgreSQL; validar firma y guardar el
evento antes del 200. Un worker reclama trabajo con transacciones cortas y una
concesión de procesamiento con vencimiento. Serializar por cuenta y contacto;
persistir el plazo del debounce y los datos necesarios para retomar. No mantener
una transacción abierta mientras responde el LLM. Usar una generación de la
concesión o versión de conversación para rechazar escrituras de un worker vencido:
[`ConversationStore`](../app/conversation/store.py) hoy reemplaza el estado sin ese control.

**Aceptación:** reiniciar después del 200 conserva el mensaje; dos instancias no
procesan simultáneamente el mismo hilo; repetir un evento no agrega otro turno.

### 2. Separar campañas, barridos y notificaciones del proceso HTTP — bloqueante

[`main.py`](../app/main.py) inicia los barridos de WhatsApp, campañas y billing por
cada instancia. [`CampaignSender._send`](../app/whatsapp/sender.py) lee `pending` y
luego escribe `sending` sin una toma exclusiva: dos procesos pueden enviar el mismo
destinatario. `recover()` marca como fallidos todos los `sending`, incluso uno que
otra instancia siga atendiendo. Su ritmo de envío también es local a cada proceso.

En el código nuevo de billing, `tick()` lee suscripciones sin reclamar trabajo
exclusivo y devuelve mails para enviarlos después del commit. Ser idempotente al
ejecutar en secuencia no demuestra seguridad bajo concurrencia; además existe una
ventana de pérdida entre commit y envío.

Propuesta: proceso de trabajos separado, primero con un único ejecutor elegido y
recuperable; después, si hace falta, varios consumidores con reclamación atómica
(`FOR UPDATE SKIP LOCKED` o actualización condicional), vencimiento y reintentos
acotados. Guardar las notificaciones pendientes en la misma transacción del cambio
de negocio (outbox), con clave única por evento. Compartir el presupuesto de envío.
Se puede empezar usando PostgreSQL, sin añadir otro sistema de colas.

**Aceptación:** arrancar B no invalida trabajo vivo de A; correr dos ejecutores no
duplica un envío ni una transición. Si el proveedor pudo aceptar una petición cuyo
resultado se perdió, registrar resultado incierto y conciliar: no prometer entrega
exactamente una vez ni reenviar ciegamente.

### 3. Admitir carga por servidor y por recurso — bloqueante para vender capacidad

[`quota.admit`](../app/services/quota.py) protege los límites del cliente con lock
de fila, una buena base para varias apps conectadas al mismo primario. No protege
la capacidad total de las GPUs. [`worker.py`](../app/voice/worker.py) no configura
una función de carga propia. La documentación de LiveKit permite personalizar la
carga; el criterio predeterminado se basa en CPU, insuficiente para este reparto
de GPU ([LiveKit](https://docs.livekit.io/agents/server/options/)). Validar los hooks
en la versión 1.8.x fijada por el proyecto antes de implementar.

Propuesta: cupos atómicos por nodo, incluyendo llamadas en admisión, señales de
salud y carga de LLM/STT/TTS, y retiro del nodo cuando no esté listo. Compartir ese
presupuesto con WhatsApp, previews y API de inferencia: todos usan los mismos
motores. Dar prioridad al audio de llamadas y limitar o posponer trabajo de fondo.
El anuncio de disponibilidad a LiveKit ayuda al reparto; no sustituye una reserva
atómica ante llegadas simultáneas. Definir rechazo o espera máxima si no hay lugar.

**Aceptación:** medir Gemma con carga mixta y con un nodo caído. Reemplazar los ~32 y
~64 del diagrama por capacidades pendientes de medir. Para dos nodos, el presupuesto
N+1 no supera la capacidad utilizable del menor, descontando carga auxiliar y margen.

### 4. Completar el diseño de PostgreSQL antes del failover automático — bloqueante

La propuesta enumera «Patroni o pg_auto_failover + testigo», pero son arquitecturas
diferentes: Patroni se apoya en un almacén distribuido de coordinación; pg_auto_failover
tiene un monitor y procesos keeper. Hay que elegir y diseñar el conjunto, no tratar
al tercer servidor como una solución genérica ([Patroni](https://patroni.readthedocs.io/en/latest/faq.html),
[pg_auto_failover](https://pg-auto-failover.readthedocs.io/en/main/architecture.html)).

Definir pérdida máxima de datos aceptable (RPO), tiempo de recuperación (RTO), modo
de réplica, exclusión del primario anterior, conexión al nuevo primario y reintegro
del nodo recuperado. La réplica asíncrona puede perder commits; la síncrona estricta
puede detener escrituras al perder la réplica. Dos nodos de datos y un testigo no
eliminan esa elección ([modos de Patroni](https://patroni.readthedocs.io/en/latest/replication_modes.html)).

`pool_pre_ping` en [`db.py`](../app/db.py) descarta conexiones rotas, pero no resuelve
por sí solo el cambio de primario ni el resultado incierto de una transacción.
Configurar descubrimiento del primario y reintentar solo operaciones idempotentes.
Si se usa watchdog del host para aislar el primario, considerar que reiniciaría
también inferencia y otros proyectos ([watchdog](https://patroni.readthedocs.io/en/latest/watchdog.html)).

**Aceptación:** probar caída del primario, réplica atrasada, partición A–B, pérdida
del coordinador y retorno del primario viejo. Nunca dos primarios escribiendo.
El modo manual sigue siendo una transición válida si su RTO se acepta explícitamente;
activo-activo de HTTP no obliga técnicamente a promoción automática de la base.

### 5. Medir disponibilidad del servicio, además del contenedor — bloqueante

[`/health`](../app/main.py) devuelve siempre `ok`. No demuestra que puedan atenderse
llamadas. Dos conectores cloudflared aportan redundancia del túnel; para dirigir
por salud de cada origen hace falta un mecanismo adicional
([Cloudflare](https://developers.cloudflare.com/tunnel/concepts/routing/)).

Separar liveness del proceso y readiness por función: API con primario accesible;
voz con worker conectado y motores listos; mensajería con entrada durable disponible.
Medir periódicamente los motores con solicitudes pequeñas, voz TTS válida, tiempo
límite y frecuencia controlada; servir el último resultado desde los checks, sin
cargar las GPUs en cada sondeo. Registrar backlog, edad del trabajo, latencia por
etapa, saturación, lag de réplica y conectividad. Monitoreo externo y alertas con
responsable. No retirar dashboard sano solo porque falló TTS.

### 6. Recuperar y reconciliar llamadas — antes de automatizar reintentos

En [`calls.py`](../app/services/calls.py) se confirma la llamada en la base antes
del dispatch externo. Una interrupción entre ambos puede dejarla pendiente. En el
worker, el cierre se guarda en `finalize`; una caída abrupta no garantiza ejecutarlo.

Añadir clave de idempotencia al inicio, intención de despacho durable, identificación
del nodo/room/job y reconciliación de estados con LiveKit. Un timeout de despacho no
prueba que no hubo despacho: consultar antes de repetir. Reconciliar duración y
resultado al perder el worker; no convertir automáticamente una llamada interrumpida
en una nueva llamada al cliente.

Distinguir tres garantías: aceptar llamadas nuevas tras una caída, conservar datos
y mantener llamadas en curso. La propuesta permite trabajar sobre las dos primeras;
no demuestra la tercera. LiveKit aloja cada room en un nodo: replicar Redis no migra
por sí solo esa sesión ([LiveKit distribuido](https://docs.livekit.io/transport/self-hosting/distributed/)).

### 7. Límites compartidos, restauración y despliegue reproducible — parte de la etapa

- Pasar los límites de login, demo, previews e inferencia de
  [`RateLimiter`](../app/services/ratelimit.py) a un mecanismo compartido y atómico.
  La API de inferencia comprueba saldo y registra al terminar: varios pedidos pueden
  gastar el mismo saldo disponible. Añadir reservas y conciliación, o documentar y
  acotar el exceso tolerado. No confundir ese problema con el lock ya existente de llamadas.
- Activar backup externo cifrado, con retención y restauración verificada. La réplica
  también replica borrados. Para un RPO menor al dump diario, evaluar backup base más
  archivado WAL/PITR ([PostgreSQL 16](https://www.postgresql.org/docs/16/continuous-archiving.html)).
  Incluir manifiesto de modelos, checkpoint de TTS, secretos y configuración SIP;
  versionar artefactos críticos para que una sincronización no sea su única copia.
- Fijar imágenes y revisiones de modelos; el LLM aún usa `latest`. Ejecutar migraciones
  una sola vez por despliegue y mantener compatibilidad entre versiones durante el corte.
  Drenar llamadas antes de detener workers, con tiempos de gracia acordes a su duración
  ([despliegue LiveKit](https://docs.livekit.io/deploy/custom/deployments/)).
- Persistir Redis de LiveKit y reconciliar trunks/reglas desde configuración. En el
  VPS, probar certificados, SRTP, candidatos ICE y TURN para redes restringidas.
  Restaurar un Redis no recupera audio ni procesos que ya se perdieron.

## Secuencia de implementación y pruebas de aceptación

| Entrega | Alcance | Condición de cierre |
|---|---|---|
| 2A: recuperación en un servidor | Inbox/outbox, trabajos separados, idempotencia, readiness, backups y cupos | Reinicios no pierden trabajo confirmado; restauración aislada exitosa; capacidad Gemma medida |
| 2B: segundo servidor | Misma versión/modelos, réplica, límites compartidos, apps habilitadas tras resolver concurrencia, entrada de voz elegida | Dos procesos no duplican efectos; un nodo atiende la carga comprometida; voz bidireccional por ambos enlaces |
| 2C: recuperación automática | Coordinación y aislamiento de base, ruteo por salud, conciliación y drenaje | Matriz de fallos ejecutada en entorno aislado, con RPO/RTO observados y vuelta atrás documentada |

Para validar 2B/2C: cubrir pérdida de fibra, worker, TTS con contenedor vivo, app con
túnel vivo, primario, coordinador y VPS. Registrar separadamente llamadas nuevas,
llamadas en curso, mensajes confirmados y escrituras. Repetir bajo carga mixta y
reservar capacidad para la recuperación del backlog. Son pruebas propuestas, no realizadas.

## Correcciones necesarias en la propuesta

- Retirar la capacidad numérica heredada de Qwen del diseño vigente con Gemma.
- Cambiar «si cae A, todo sigue por B» por garantías y tiempos por componente;
  distinguir conexión A del servidor A. No afirmar continuidad de sesiones existentes.
- Explicitar la recuperación del VPS o relay: segunda instancia preparada, configuración,
  certificados, reglas, ruteo y ensayo de corte. Si se pospone, declarar el riesgo aceptado.
- El relay de dos LiveKit independientes necesita un diseño de afinidad de room,
  señalización y medios/ICE; reenviar los mismos puertos hacia ambos no lo resuelve.
- No dar por equivalente la latencia de relay y VPS: depende del trayecto y del codec;
  los ~6 Mbps calculados para G.711 tampoco validan automáticamente el tramo WebRTC.
- Corregir la 5060 Ti todavía mencionada en la capacidad de WhatsApp de ARQUITECTURA;
  integrar billing cuando se cierre ese trabajo y separar estado desplegado de propuesta.

La compra del segundo servidor mejora el aislamiento ante fallos de hardware. La
segunda etapa queda completa cuando la aplicación también sabe recuperar el trabajo,
mantener un único escritor y admitir solo la carga que el nodo superviviente soporta.
