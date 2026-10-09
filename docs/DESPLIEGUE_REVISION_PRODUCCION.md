# Despliegue de la revisión de producción (rama `produccion-multicliente`)

Guía de punta a punta para desplegar los cambios de la revisión del 7-oct-2026 (H01 a H14 y extras;
qué hace cada uno en [`revision-produccion-2026-10-07-respuesta.md`](revision-produccion-2026-10-07-respuesta.md)
y en [`PRODUCCION.md`](PRODUCCION.md), 3.1). Pensada para una ventana de fin de semana.

**Corte esperado:** ~5–10 min sin voz (se recrean la inferencia, LiveKit, su Redis y Asterisk: se cortan
las llamadas en curso) y ~1 min sin dashboard ni webhook. Meta reintenta los webhooks que no reciben 200,
así que los mensajes de WhatsApp de ese minuto llegan después. Referencia medida: el reinicio del host
del 8-oct dejó el stack listo, con el TTS caliente, en ~2 min; un cambio de reparto de GPU, ~4 min.

**Qué cambia en el despliegue:**

| Pieza | Cambio | Efecto |
|---|---|---|
| Base | Migración 0009 (columnas nuevas, FK compuesta número↔agente) | `lock_timeout` de 5 s: si choca con un lock, falla sin cambios a medias |
| Imágenes propias (`app`, `agent`, `stt-parakeet`, `asterisk`) | Build con bases por digest y `requirements.lock` | Se compilan; el resto ya está en el host con el digest fijado (verificado el 9-oct) |
| Resto de servicios | Imagen fijada por digest (la misma que corre) | Compose los recrea igual, porque cambió la referencia |
| `livekit-redis` | Persistencia (AOF) en el volumen nuevo `livekit_redis_data` | Arranca vacío: hay que recargar los trunks (`make livekit-sip`) |
| `app` | Escucha en `127.0.0.1:8011` (`APP_BIND`) | Desde la LAN ya no se llega; el túnel tiene que apuntar a `127.0.0.1:8011` |
| `proxy` | Lista blanca de rutas | El resto da 404 |
| Asterisk | Dialplan con `L()` (techo de 3600 s); DID de WhatsApp desconocido y caller ID inválido, cortados | Se recrea |
| cron | `healthcheck.sh`, `backup.sh` y `restore-test.sh` nuevos | Cron corre los scripts del árbol: quedan activos apenas el árbol está en la rama |

## 0. Antes del fin de semana (sin corte)

1. **Rama al día con `main`.** Si `main` avanzó (otras sesiones), traerlo a la rama y resolver los conflictos ahora:

   ```bash
   git switch produccion-multicliente
   git merge main
   .venv/bin/python -m pytest -q        # 480 passed / 13 skipped el 9-oct
   git switch main
   ```

   Si hay otras sesiones trabajando en el árbol, hacerlo cuando no haya cambios sin commitear (`git status`).
2. **Cloudflare (panel, lo hace el usuario).** En el túnel, cambiar el servicio de cada ruta (`api.`,
   `rtc.` no, `wa.`, `app.`) de `http://localhost:8011` a `http://127.0.0.1:8011`. Anda igual con el bind
   actual (`0.0.0.0`) y evita que `localhost` resuelva a `::1`, que deja de escuchar. Probar el dashboard y
   la demo después del cambio.
3. **Router (lo hace el usuario).** Confirmar si el 8100 está reenviado. Si no se usa el modo remoto,
   quitarlo.
4. **Chequeos de solo lectura en la base de producción:**

   ```bash
   docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
   -- 1. Tiene que dar 0 filas: la 0009 se niega a migrar si hay números ruteados a un agente de otro cliente
   SELECT p.e164 FROM phone_numbers p JOIN agents a ON a.id = p.agent_id
    WHERE p.client_id IS NULL OR p.client_id <> a.client_id;
   -- 2. Agentes con knowledge de más de 24.000 caracteres: siguen andando, pero la próxima edición da 422
   SELECT slug, length(definition->>'knowledge') AS chars FROM agents
    WHERE length(definition->>'knowledge') > 24000;
   -- 3. Clientes sin número propio: después del despliegue no pueden hacer salientes (409 no_caller_id)
   SELECT c.slug FROM clients c LEFT JOIN phone_numbers p ON p.client_id = c.id
    WHERE p.id IS NULL;
   SQL
   ```

   El `restore-test` del 8-oct no encontró números cruzados (consulta 1).

5. **Avisar a los clientes** de los cambios de comportamiento:
   - sin número propio no hay salientes;
   - los límites por hora se comparten entre todos los usuarios y API keys del cliente;
   - hay un tope de 10 API keys activas;
   - `/stats` sin fechas cuenta los últimos 30 días;
   - las llamadas se cortan al máximo del tier (900 s si el tier no fija otro).
6. **Elegir la ventana:** sin llamadas en curso ni campañas de WhatsApp programadas (Campañas, en la UI).

## 1. Preparación (sin corte)

```bash
cd ~/voice-as-a-service
git status                                  # sin cambios ajenos sin commitear
git switch produccion-multicliente
make backup                                 # base, .env, storage/, certificado SIP, checkpoint TTS
make restore-test                           # restaura el dump nuevo en un Postgres desechable y migra a 0009
make build                                  # compila app/agent, stt-parakeet y asterisk; lo que corre no se toca
```

- `restore-test` es la prueba en seco de la migración sobre los datos de hoy. Si falla, no seguir.
- Si `make build` falla por un rango que no admite la versión del lock, no seguir: volver a `main`
  (`git switch main`), sin corte.
- Desde el `git switch`, cron ya corre el `healthcheck.sh` nuevo. Hasta que se recree `app`, pausa el
  chequeo de trunks: el script es más nuevo que la imagen en uso.

## 2. Despliegue (con corte)

```bash
make migrate                                # 0009 + seed; la app vieja sigue andando con el esquema nuevo
docker compose up -d --wait --wait-timeout 900
docker compose -f docker-compose.tunnel.yml up -d tunnel
make livekit-sip                            # trunks en el Redis nuevo, con max_call_duration
make up-pbx                                 # Asterisk con el dialplan nuevo (si `up` ya lo recreó, lo recrea otra vez: sin efecto)
```

- **`make migrate`:** si falla por `LockNotAvailable` (lock de la app vieja), reintentar; si insiste, `docker
  compose stop app agent` y reintentar. Comprobar que quedó en 0009:

  ```bash
  docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tc "SELECT version_num FROM alembic_version"'
  ```

- **`docker compose up`** recrea `db` (unos segundos), la inferencia (minutos), `proxy`, LiveKit, `app`,
  `agent`, `stt-parakeet` y `asterisk`. El orden de la GPU lo da `depends_on`. `app` y `agent` esperan
  hasta 30 s a que terminen los turnos o llamadas en curso (`stop_grace_period`). Si no llega a healthy
  en 15 min, ver `docker compose ps` y `make logs S=<servicio>`.
- **Calentar el TTS**, como `deploy/boot.sh`: sin esto, la primera llamada no recibe el saludo.

  ```bash
  set -a; . ./.env; set +a
  curl -sf -o /dev/null --max-time 120 http://127.0.0.1:8103/v1/audio/speech \
    -H "Authorization: Bearer $VLLM_API_KEY" -H "Content-Type: application/json" \
    -d "{\"model\":\"$VLLM_TTS_MODEL\",\"voice\":\"$VLLM_TTS_VOICE\",\"input\":\"Hola, te habla el agente.\",\"response_format\":\"wav\"}" \
    && echo "TTS caliente"
  ```

## 3. Verificación

**Técnica:**

```bash
docker compose ps                           # todo healthy, también agent (healthcheck nuevo en :8081)
curl -s 127.0.0.1:8011/health/ready         # {"ok":true,...}; solo responde a pedidos locales
make ops-health                             # "ok todo bien", con el chequeo de trunks activo
make pbx-status                             # registro con Anura
```

- **Desde la laptop**, `curl --max-time 3 http://192.168.1.99:8011/health` tiene que fallar: la app ya no
  escucha en la LAN.
- **Desde afuera**, el dashboard tiene que abrir por `https://app.atentina.com.ar` y la demo por la landing.

**Funcional** (con el cliente `atentina` o uno de prueba):

| Prueba | Esperado |
|---|---|
| Llamar a la línea propia (`ANURA_DID`) | Atiende el agente, con saludo |
| Saliente desde la UI, de un cliente con número | Sale con el caller ID del cliente |
| Saliente de un cliente sin número | Mensaje "Asigná un número al cliente para hacer salientes", sin llamada |
| Tier de prueba con duración máxima de 1 min y una entrante a su número | Se corta al minuto |
| Mensaje de WhatsApp a la línea | Responde el agente |
| Mensaje de WhatsApp y, dentro de los 2 s, `docker compose stop app`; después `docker compose start app` | La respuesta llega igual (la recuperación toma el mensaje guardado, en unos minutos) |
| Desactivar un cliente de prueba | El cliente ve el banner "Cuenta en solo lectura"; conversación de texto, preview de voz y API key nueva dan 403 `client_inactive` |
| Llamada de prueba desde la UI, y en el medio `docker compose kill agent` (después `docker compose up -d agent`) | En 1–3 min la llamada queda cerrada (`room_gone`) y deja de ocupar cupo |

Si todo anda, cerrar la rama (punto 5). Si algo crítico falla, volver atrás (punto 4).

## 4. Vuelta atrás

**Antes de `make migrate`:** `git switch main`. Nada que deshacer: los builds nuevos no corren.

**Después de migrar o recrear**, en este orden. Hay que bajar la base **con el código de la rama**, porque
el downgrade de la 0009 solo está ahí:

```bash
docker compose run --rm --no-deps migrate alembic downgrade 0008
git switch main
make build
docker compose up -d --wait --wait-timeout 900
docker compose -f docker-compose.tunnel.yml up -d tunnel
make livekit-sip
make up-pbx
# calentar el TTS (punto 2)
```

- El downgrade borra las columnas nuevas: cuerpos de mensajes de WhatsApp guardados, claves de
  idempotencia, versiones y la retención cargada. No toca conversaciones ni llamadas.
- En `main`, `livekit-redis` vuelve a no persistir. El volumen `livekit_redis_data` queda sin uso; se borra con
  `docker volume rm voice-as-a-service_livekit_redis_data`.
- Si la base quedó dañada: restaurar el dump del punto 1, como en [`MIGRACION_SERVER.md`](MIGRACION_SERVER.md), 4.2.
- La rama queda intacta para reintentar.
- **Las rutas del túnel quedan en `127.0.0.1:8011`:** andan igual con `main`.

## 5. Cerrar la rama

```bash
git switch main
git merge --no-ff produccion-multicliente   # sin conflictos si se hizo el punto 0.1
git push origin main
git branch -d produccion-multicliente
```

El árbol sigue con el mismo contenido que corre: el merge no cambia archivos.

Después, actualizar [`PRODUCCION.md`](PRODUCCION.md), 3.1 (desplegado el `<fecha>`, con lo observado en
la verificación) y el aviso del inicio de las reglas en [`AGENTS.md`](../AGENTS.md).

## 6. Después del despliegue (de a uno, con su verificación)

Los cambios de `.env` van con el diff enmascarado contra el backup antes de reiniciar.

1. **Alertas.** `ALERT_NTFY_TOPIC` (app ntfy en el celular) y `HEALTHCHECKS_PING_URL` (healthchecks.io,
   avisa si el chequeo deja de correr). Sin reinicio: `healthcheck.sh` lee `.env` en cada corrida. Probar
   con `make ops-health` y un fallo inducido (por ejemplo `docker compose stop proxy`; después `start`).
2. **Copia externa del backup.** `rclone config` en el host (R2 o B2), clave pública GPG importada, y en
   `.env`: `RCLONE_REMOTE` y `BACKUP_GPG_RECIPIENT`. Correr `make backup` y comprobar el archivo
   remoto. La clave privada GPG va **fuera del host**: sin ella el backup externo no sirve.
3. **Cookie segura.** `AUTH_COOKIE_SECURE=true` y `docker compose up -d app`. Probar el login por
   `app.atentina.com.ar`. Por la LAN ya no hace falta: la app no escucha ahí.
4. **CSP que bloquea.** La CSP no tiene `report-uri`: los "reportes" son los avisos de la consola del
   navegador. Recorrer el dashboard (incluido Embedded Signup de WhatsApp) con la consola abierta. Si no
   aparecen violaciones, `CSP_REPORT_ONLY=false` y `docker compose up -d app`, y repetir el recorrido.
5. **Retención.** Cargar `retention_days` en los tiers desde la UI. Hoy ninguno tiene: no se borra nada.
6. **Capacidad.** Correr un CAP con Gemma ([`capacity/README.md`](capacity/README.md)) y fijar con el
   resultado:
   - `MAX_CONCURRENT_CALLS_GLOBAL` (20, provisional);
   - `INBOUND_RESERVE_CALLS`;
   - `WA_MAX_CONCURRENT_TURNS`, `API_MAX_CONCURRENT_TURNS` y `TTS_PREVIEW_MAX_CONCURRENT`;
   - `LLM_TURN_DEADLINE_SECONDS`.

   Para el test desde la laptop: `APP_BIND=0.0.0.0` y `MAX_CONCURRENT_CALLS_GLOBAL=200`, `make up-agent`,
   y al terminar sacarlos y volver a `make up-agent`.
7. **Pendiente, sin código:** auth SIP por número para WhatsApp Calling de terceros (hoy un solo auth
   global, el de Atentina).
