# Makefile — AIVA Validate (voice-as-a-service)
#
# Atajos sobre `docker compose` para levantar el stack: db + app + agent +
# vllm-llm/vllm-stt/vllm-tts (inferencia local sobre GPU, ver docker-compose.yml
# y README.md). Uso tipico:
#   make setup   -> primera vez: crea .env desde .env.example y storage/
#                   (completar LIVEKIT_* en .env antes de seguir, ver README)
#   make up      -> build + levanta los 6 servicios en background. La primera
#                   vez tarda varios minutos (descarga de pesos + carga en
#                   GPU) -- app y agent esperan a que los vllm-* esten
#                   healthy antes de arrancar. Requiere NVIDIA Container
#                   Toolkit instalado (ver scripts/install-nvidia-toolkit.sh).
#   make up-remote -> PC sin GPU: levanta solo db+app+agent, apuntando la
#                   inferencia a los vLLM de otro host (ej. via ngrok, ver
#                   seccion "Inferencia remota" del README).
#   make logs    -> sigue los logs de los 6 servicios
#   make tunnel  -> opcional: expone los 3 vllm-* en internet via ngrok
#                   (perfil `ngrok` de compose, ver .env.example)
#   make health  -> chequea que la app responda en :8011
#   make gpu     -> uso actual de VRAM por GPU
#   make down    -> para y elimina contenedores (conserva los datos de MySQL)
#
# `make help` (o `make` a secas) lista todos los targets disponibles.

SHELL := /bin/bash
COMPOSE := docker compose

# UID/GID del build (ver Dockerfile): el contenedor corre como `appuser` con
# este UID/GID. Si no coincide con el dueño de ./storage en el host, el
# contenedor no puede escribir ahi (PermissionError al arrancar). Se exportan
# para que docker compose los use al interpolar ${UID}/${GID} en build.args.
export UID := $(shell id -u)
export GID := $(shell id -g)

.DEFAULT_GOAL := help

.PHONY: help setup env storage \
        build rebuild up up-remote start stop down re \
        restart restart-app restart-agent restart-llm restart-stt restart-tts \
        ps logs logs-app logs-agent logs-db logs-llm logs-stt logs-tts \
        tunnel logs-tunnel \
        sh-app sh-agent mysql \
        health health-vllm open gpu \
        loadtest-audio loadtest loadtest-report \
        db-reset clean fclean

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: env storage ## Primera vez: crea .env (desde .env.example) y storage/
	@echo "Completa las claves en .env (LIVEKIT_*) y corre: make up (LLM/STT/TTS corren locales via vLLM, sin API keys)"

env: ## Crea .env desde .env.example si no existe (no pisa uno ya existente)
	@test -f .env && echo ".env ya existe, no se toca" || (cp .env.example .env && echo ".env creado desde .env.example")

storage: ## Crea storage/recordings con el owner correcto (evita error de permisos en el contenedor)
	@mkdir -p storage/recordings
	@echo "storage/recordings listo (owner: $$(id -un):$$(id -gn))"

build: storage ## Build de las imagenes app/agent con tu UID/GID de host
	$(COMPOSE) build

rebuild: storage ## Build sin cache (usar si un cambio no se refleja)
	$(COMPOSE) build --no-cache

up: storage ## Build (si hace falta) + levanta los 6 servicios en background (1ra vez tarda, ver arriba)
	$(COMPOSE) up -d --build

up-remote: storage ## PC sin GPU: levanta db+app+agent (--no-deps; la inferencia va a VLLM_*_BASE_URL, ver README)
	$(COMPOSE) up -d --build --wait --no-deps db
	$(COMPOSE) up -d --build --no-deps app agent

start: ## Arranca contenedores ya creados, sin rebuild
	$(COMPOSE) start

stop: ## Para los contenedores sin eliminarlos
	$(COMPOSE) stop

down: ## Para y elimina contenedores + red (conserva el volumen de MySQL)
	$(COMPOSE) down

re: down up ## down + up (reinicio completo de contenedores; conserva datos)

restart: ## Reinicia app y agent (util tras cambiar .env o codigo)
	$(COMPOSE) restart app agent

restart-app: ## Reinicia solo app
	$(COMPOSE) restart app

restart-agent: ## Reinicia solo agent (worker LiveKit)
	$(COMPOSE) restart agent

restart-llm: ## Reinicia solo vllm-llm (no relee cambios de .env -- para eso hace falta `make up`)
	$(COMPOSE) restart vllm-llm

restart-stt: ## Reinicia solo vllm-stt
	$(COMPOSE) restart vllm-stt

restart-tts: ## Reinicia solo vllm-tts
	$(COMPOSE) restart vllm-tts

ps: ## Estado de los 6 contenedores del proyecto
	$(COMPOSE) ps

logs: ## Sigue los logs de los 6 servicios
	$(COMPOSE) logs -f --tail=100

logs-app: ## Sigue los logs solo de app
	$(COMPOSE) logs -f --tail=200 app

logs-agent: ## Sigue los logs solo de agent (worker LiveKit)
	$(COMPOSE) logs -f --tail=200 agent

logs-db: ## Sigue los logs solo de db (MySQL)
	$(COMPOSE) logs -f --tail=200 db

logs-llm: ## Sigue los logs solo de vllm-llm
	$(COMPOSE) logs -f --tail=200 vllm-llm

logs-stt: ## Sigue los logs solo de vllm-stt
	$(COMPOSE) logs -f --tail=200 vllm-stt

logs-tts: ## Sigue los logs solo de vllm-tts
	$(COMPOSE) logs -f --tail=200 vllm-tts

tunnel: ## Expone los 3 vllm-* via ngrok (perfil opt-in; requiere NGROK_* en .env, ver .env.example)
	@grep -qE '^NGROK_AUTHTOKEN=.+' .env || { echo "Falta NGROK_AUTHTOKEN en .env (ver .env.example)"; exit 1; }
	@grep -qE '^NGROK_DOMAIN=.+' .env || { echo "Falta NGROK_DOMAIN en .env (ver .env.example)"; exit 1; }
	$(COMPOSE) --profile ngrok up -d ngrok-llm ngrok-stt ngrok-tts
	@dom=$$(sed -n 's/^NGROK_DOMAIN=//p' .env | tail -1); \
		echo "Agentes ngrok arriba. URLs publicas (api_key: VLLM_API_KEY):"; \
		echo "  LLM: https://$$dom/llm/v1"; \
		echo "  STT: https://$$dom/stt/v1"; \
		echo "  TTS: https://$$dom/tts/v1"

logs-tunnel: ## Sigue los logs de los 3 agentes ngrok
	$(COMPOSE) logs -f --tail=200 ngrok-llm ngrok-stt ngrok-tts

sh-app: ## Shell dentro del contenedor app
	$(COMPOSE) exec app bash

sh-agent: ## Shell dentro del contenedor agent
	$(COMPOSE) exec agent bash

mysql: ## Cliente mysql dentro de db, con las credenciales de .env
	$(COMPOSE) exec db sh -c 'mysql -uroot -p"$$MYSQL_ROOT_PASSWORD" "$$MYSQL_DATABASE"'

health: ## Chequea GET /health en localhost:8011
	@curl -sf http://127.0.0.1:8011/health && echo || echo "app no responde en :8011 (revisa 'make ps' / 'make logs-app')"

health-vllm: ## Chequea /v1/models en los 3 servicios vllm-* (localhost:8101/8102/8103)
	@for p in 8101:vllm-llm 8102:vllm-stt 8103:vllm-tts; do \
		port=$${p%%:*}; name=$${p##*:}; \
		curl -sf http://127.0.0.1:$$port/v1/models >/dev/null \
			&& echo "$$name (:$$port): OK" \
			|| echo "$$name (:$$port): no responde (revisa 'make ps' / 'make logs-$${name#vllm-}')"; \
	done

open: ## Abre el dashboard en el navegador por defecto (Linux)
	@xdg-open http://127.0.0.1:8011 >/dev/null 2>&1 || echo "Abri http://127.0.0.1:8011 manualmente"

gpu: ## Uso actual de VRAM por GPU (requiere nvidia-smi en el host)
	@nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv

loadtest-audio: ## Genera el corpus de audio del load test con el propio vllm-tts (una sola vez, cachea en scripts/loadtest/audio/)
	$(COMPOSE) run --rm --no-deps -v $(CURDIR)/scripts:/app/scripts agent python -m scripts.loadtest.gen_audio

loadtest: ## Load test usuario->agent->usuario (sin telefonia). Ej: make loadtest ARGS="--levels 1,2,4,8 --turns 3"
	$(COMPOSE) run --rm --no-deps -v $(CURDIR)/scripts:/app/scripts agent python -m scripts.loadtest.run $(ARGS)

loadtest-report: ## Sirve scripts/loadtest/ en :8099 y abre report.html (asi el auto-load de results/latest.csv funciona; file:// directo tambien sirve, pero hay que elegir el CSV a mano)
	@# El ?t= es necesario: con la URL pelada, xdg-open solo ENFOCA la pestana
	@# que ya estaba abierta en vez de recargarla, y el reporte sigue mostrando
	@# el run anterior (tryAutoload corre una sola vez, al cargar la pagina).
	@url="http://127.0.0.1:8099/report.html?t=$$(date +%s)"; \
	if ss -ltn 2>/dev/null | grep -q ':8099 '; then \
		echo "ya hay un servidor en :8099, lo reuso"; \
		xdg-open "$$url" >/dev/null 2>&1 || echo "Abri: $$url"; \
	else \
		( sleep 1 && xdg-open "$$url" >/dev/null 2>&1 || echo "Abri: $$url" ) & \
		cd scripts/loadtest && python3 -m http.server 8099; \
	fi

db-reset: ## PELIGRO: borra el volumen de MySQL (todas las llamadas y config quedan en blanco) y vuelve a levantar
	$(COMPOSE) down -v
	$(MAKE) up

clean: down ## down + elimina las imagenes construidas por este proyecto
	docker image rm -f voice-as-a-service-app voice-as-a-service-agent 2>/dev/null || true

fclean: ## PELIGRO: down -v + elimina imagenes locales del proyecto (borra datos y contenedores)
	$(COMPOSE) down -v --rmi local
