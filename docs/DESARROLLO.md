# Desarrollo y deploy

| Entorno | Host | Código | Datos |
|---|---|---|---|
| Desarrollo | `192.168.1.99` | Copia de trabajo, cualquier rama | Base propia, sin datos de producción; credenciales en `.env.dev` |
| Producción | server2 (`192.168.1.98`) | Siempre `main`, sin cambios locales | Base y `.env` reales |

**Flujo:** se planifica ([ciclo de `AGENTS.md`](../AGENTS.md#ciclo-de-desarrollo)) → cada tarea se desarrolla, se prueba en el entorno local y se documenta → commit a `main` y push → se despliega con el agente
[`deploy`](../.claude/agents/deploy.md). Nada se prueba por primera vez en producción. Los `make up*` de producción se niegan si
el repo no está en `main` o tiene cambios locales (`solo-principal`).

## Entorno local

`make dev-up` crea `.env.dev` si falta, compila, migra y levanta el stack con el código del repo; al final imprime la URL
y el admin. Volver a verlos: `make dev-login`. Es **http://192.168.1.99:8211** (cualquier equipo de la LAN; `DEV_PORT` en `.env.dev`).

| Comando | Qué hace |
|---|---|
| `make dev-up` | Levanta o actualiza todo. Hace falta tras cambiar `web/`, `requirements.txt` o el `Dockerfile` |
| `make dev-web` | UI con recarga al instante en `:5173`, contra la API local |
| `make dev-restart S=agent` | Toma cambios en el worker de voz. La API (`app/`) se recarga sola |
| `make dev-migrate` | Migraciones y seed |
| `make dev-agents-reference` | Como `make agents-reference` (agentes de `atentina` con la referencia reescrita) sobre la base local: `SLUG=`, `APPLY=1` |
| `make dev-health`, `dev-ps`, `dev-logs S=app`, `dev-psql` | Estado y diagnóstico |
| `make dev-down`, `make dev-reset` | Para el stack; borra base y audios |
| `make test`, `make web-check` | Tests sin modelo real, como siempre |

**Qué corre** (`docker-compose.dev.yml`, proyecto `atentina-dev`): `db`, `migrate`, `app`, `agent`, `tools-runner`,
`tools-egress` y `livekit`, con base, audios, red y LiveKit propios.

**Qué no se puede probar:** teléfono (no hay Asterisk ni SIP; nunca dos Asterisk), WhatsApp, cobros y mails (sin clave, no
se envían: los mails quedan en `make dev-logs S=app`), túnel ni monitoreo. Eso se valida en producción con cuidado.

**Voz en el navegador:** el micrófono exige HTTPS o `localhost`. Desde otro equipo, por la URL de la LAN, la llamada de
prueba no toma el micrófono: abrir un túnel con `ssh -L 8211:127.0.0.1:8211 -L 7880:127.0.0.1:7880 192.168.1.99` y entrar por `http://localhost:8211`.

**Trampas:**
- **La inferencia es la de producción:** `.env.dev` apunta al proxy de server2 (`http://192.168.1.98:8100/{llm,stt,tts}/v1`,
  [`INFRA.md`](INFRA.md), "Servicios"). Lo que se prueba en desarrollo compite con las llamadas: nada de cargas, y
  `make eval-llm`, `mcp-eval` y `stt-eval` fuera de horario. Recrear un modelo en server2 corta también desarrollo (502 en su path).
- **Un pedido al TTS sin `voice` o con `"default"` tumba el TTS de producción** (todo da 500 hasta reiniciar `vllm-tts` en
  server2). El código de la plataforma no lo manda; un `curl` o código a medio hacer sí puede: siempre una voz del catálogo.
  El proxy no lo filtra (riesgo aceptado).
- Un cambio de modelo se prueba con su override y el test de capacidad ([`INFRA.md`](INFRA.md)).
- `.env.dev` no se versiona y no lleva credenciales de producción, salvo `VLLM_API_KEY` (la de server2, copiada del `.env` con
  los nombres de los modelos). Si cambia el modelo del LLM, actualizar `.env.dev.example` y `.env.dev`, o el LLM da 404.
- `make dev-backend` (SQLite, `:8111`) sigue para mirar la UI rápido, pero lee las `LIVEKIT_*` y demás claves del `.env`.

## Deploy

Se le pide al agente `deploy`, diciendo qué se probó. Mira qué cambió entre server2 y `origin/main`, baja el código con
`git pull --ff-only` y corre solo los `make` que hacen falta; lo que corta llamadas pasa por `make calls-active`. La tabla de
qué comando corresponde a cada cambio está en el agente. `make deploy-status` muestra lo desplegado y lo pendiente, sin tocar nada.

Vuelta atrás: `git revert` en `main` y otro deploy, nunca mover server2 a otro commit.

`landing/` se publica aparte: Render compila al llegar el push a la rama que sigue ([`features/LANDING.md`](features/LANDING.md)). Un push con cambios ahí ya es público, sin pasar por el agente.
