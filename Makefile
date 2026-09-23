# Makefile — AIVA Validate (voice-as-a-service)
#
# Atajos sobre `docker compose`. Stack por defecto (docker-compose.yml):
#   agente:     db + app (dashboard y API :8011) + agent (worker de LiveKit)
#   inferencia: vllm-llm (Qwen3.5-4B) + stt-parakeet (Parakeet TDT 0.6B v3)
#               + vllm-tts (Qwen3-TTS 1.7B, voz fine-tuneada arf_03034)
#   proxy:      nginx en :PROXY_PORT, entrada publica a la inferencia (loadtest)
#   asterisk:   puente SIP Anura <-> LiveKit (docs/TELEFONIA_ANURA.md)
#
# Primera vez: `make setup`, completar .env y `make up` (la primera carga de
# pesos tarda varios minutos). Requiere NVIDIA Container Toolkit
# (scripts/install-nvidia-toolkit.sh). En una PC sin GPU (ej. la del
# loadtest): `make up-agent`, con VLLM_*_BASE_URL apuntando al proxy del host
# GPU (README, "Inferencia remota").
#
# Los targets que aceptan S=<servicio> actuan sobre todos si no se pasa.
# `make help` (o `make` a secas) lista todos los targets.

SHELL := /bin/bash
COMPOSE := docker compose

# UID/GID del build (ver Dockerfile): el contenedor corre como `appuser` con
# este UID/GID. Si no coincide con el dueño de ./storage en el host, el
# contenedor no puede escribir ahi (PermissionError al arrancar). Se exportan
# para que docker compose los use al interpolar ${UID}/${GID} en build.args.
export UID := $(shell id -u)
export GID := $(shell id -g)

AGENT_SERVICES := db app agent
INFERENCE_SERVICES := vllm-llm stt-parakeet vllm-tts

.DEFAULT_GOAL := help

.PHONY: help setup env storage build \
        up up-agent up-inference up-nginx up-pbx down restart ps logs \
        sh mysql health gpu \
        pbx-cli pbx-status livekit-sip \
        test loadtest-audio loadtest loadtest-report stt-eval stt-corpus \
        db-reset clean

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# --- Setup ---------------------------------------------------------------

setup: env storage ## Primera vez: crea .env (desde .env.example) y storage/
	@echo "Completa las claves en .env (LIVEKIT_*, ANURA_*, PUBLIC_HOST) y corre: make up"

env: ## Crea .env desde .env.example si no existe (no pisa uno ya existente)
	@test -f .env && echo ".env ya existe, no se toca" || (cp .env.example .env && echo ".env creado desde .env.example")

storage: ## Crea storage/recordings con el owner correcto (evita error de permisos en el contenedor)
	@mkdir -p storage/recordings

build: storage ## Build de las imagenes propias (app/agent, stt-parakeet, asterisk)
	$(COMPOSE) build

# --- Levantar / bajar ----------------------------------------------------

# URL publica del proxy, desde PUBLIC_HOST y PROXY_PORT del .env.
PUBLIC_URL_SH = host=$$(sed -n 's/^PUBLIC_HOST=//p' .env | tail -1); \
	port=$$(sed -n 's/^PROXY_PORT=//p' .env | tail -1); url="http://$${host:-<PUBLIC_HOST>}:$${port:-8100}"

up: storage ## Levanta todo: agente + inferencia + proxy + asterisk
	$(COMPOSE) up -d --build

up-agent: storage ## Solo db + app + agent, sin la inferencia (--no-deps; usa VLLM_*_BASE_URL del .env)
	$(COMPOSE) up -d --build --wait --no-deps db
	$(COMPOSE) up -d --build --no-deps app agent

up-inference: ## Solo la inferencia: vllm-llm + stt-parakeet + vllm-tts (espera a que esten healthy)
	$(COMPOSE) up -d --build --wait $(INFERENCE_SERVICES)

up-nginx: ## Solo el proxy publico (nginx en :PROXY_PORT) e imprime las URLs
	$(COMPOSE) up -d proxy
	@$(PUBLIC_URL_SH); \
		echo "URLs publicas (Authorization: Bearer \$$VLLM_API_KEY):"; \
		echo "  VLLM_LLM_BASE_URL=$$url/llm/v1"; \
		echo "  VLLM_STT_BASE_URL=$$url/stt/v1"; \
		echo "  VLLM_TTS_BASE_URL=$$url/tts/v1"

up-pbx: ## Solo Asterisk; lo recrea para releer .env y asterisk/conf/ (corta llamadas en curso)
	@for v in ANURA_DOMAIN ANURA_USER ANURA_PASSWORD ANURA_DID LIVEKIT_SIP_HOST LIVEKIT_SIP_PASSWORD; do \
		grep -qE "^$$v=.+" .env || { echo "Falta $$v en .env (ver docs/TELEFONIA_ANURA.md)"; exit 1; }; \
	done
	$(COMPOSE) up -d --build --force-recreate asterisk
	@echo "Asterisk arriba. Estado de la troncal: make pbx-status (el registro con Anura tarda unos segundos)"

down: ## Para y elimina los contenedores (conserva volumenes: MySQL, pesos, voces)
	$(COMPOSE) down

restart: ## Reinicia servicios (no relee .env: para eso, make up). Ej: make restart S=agent
	$(COMPOSE) restart $(S)

ps: ## Estado de los contenedores
	$(COMPOSE) ps

logs: ## Sigue los logs. Ej: make logs S=agent (o S="vllm-tts stt-parakeet")
	$(COMPOSE) logs -f --tail=200 $(S)

# --- Debug ---------------------------------------------------------------

sh: ## Shell en un contenedor (default: agent). Ej: make sh S=app
	$(COMPOSE) exec $(or $(S),agent) bash

mysql: ## Cliente mysql dentro de db, con las credenciales de .env
	$(COMPOSE) exec db sh -c 'mysql -uroot -p"$$MYSQL_ROOT_PASSWORD" "$$MYSQL_DATABASE"'

health: ## Chequea /health de la app (:8011), la inferencia (:8101-8103) y el proxy (:PROXY_PORT)
	@for p in 8011:app 8101:vllm-llm 8102:stt-parakeet 8103:vllm-tts; do \
		curl -sf -o /dev/null -m 3 http://127.0.0.1:$${p%%:*}/health \
			&& echo "$${p##*:} (:$${p%%:*}): OK" \
			|| echo "$${p##*:} (:$${p%%:*}): no responde (make logs S=$${p##*:})"; \
	done; \
	port=$$(sed -n 's/^PROXY_PORT=//p' .env | tail -1); port=$${port:-8100}; \
	code=$$(curl -s -o /dev/null -m 3 -w '%{http_code}' http://127.0.0.1:$$port/llm/v1/models); \
	case $$code in 200|401) echo "proxy (:$$port): OK";; *) echo "proxy (:$$port): no responde (make logs S=proxy)";; esac

gpu: ## Uso actual de VRAM por GPU
	@nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv

# --- Telefonia (docs/TELEFONIA_ANURA.md) ---------------------------------

pbx-cli: ## Consola de Asterisk (ej. `pjsip set logger on` para ver el SIP crudo)
	$(COMPOSE) exec asterisk asterisk -rvvv

pbx-status: ## Registro con Anura, endpoints y llamadas activas en Asterisk
	@$(COMPOSE) exec asterisk asterisk -rx "pjsip show registrations"
	@$(COMPOSE) exec asterisk asterisk -rx "pjsip show contacts"
	@$(COMPOSE) exec asterisk asterisk -rx "core show channels"

livekit-sip: ## Crea/actualiza en LiveKit los trunks SIP + dispatch rule para Anura via Asterisk (idempotente)
	$(COMPOSE) run --rm --no-deps -v $(CURDIR)/scripts:/app/scripts app python -m scripts.livekit_sip_setup

# --- Tests ---------------------------------------------------------------

test: ## Tests del motor conversacional (los que usan el LLM se saltean si vllm-llm no responde)
	$(COMPOSE) run --rm --no-deps -v $(CURDIR)/tests:/app/tests -v $(CURDIR)/pytest.ini:/app/pytest.ini app pytest -q $(ARGS)

# --- Loadtest y eval (docs/experiments/) ---------------------------------

loadtest-audio: ## Genera el corpus de audio del loadtest con vllm-tts (una vez; cachea en scripts/loadtest/audio/)
	$(COMPOSE) run --rm --no-deps -v $(CURDIR)/scripts:/app/scripts agent python -m scripts.loadtest.gen_audio

loadtest: ## Loadtest usuario->agent->usuario (sin telefonia). Ej: make loadtest ARGS="--levels 16,32 --turns 4"
	$(COMPOSE) run --rm --no-deps -v $(CURDIR)/scripts:/app/scripts agent python -m scripts.loadtest.run $(ARGS)

loadtest-report: ## Sirve scripts/loadtest/ en :8099 y abre report.html (carga results/latest.csv)
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

stt-eval: ## WER + latencia de stt-parakeet sobre un corpus. Ej: make stt-eval ARGS="--telephone --audio-dir ..."
	$(COMPOSE) run --rm --no-deps -v $(CURDIR)/scripts:/app/scripts agent python -m scripts.stt_eval $(ARGS)

stt-corpus: ## Arma el corpus de eval de STT con voces argentinas (OpenSLR 61): limpio, telefonico, +ruido, +cortes
	$(COMPOSE) run --rm --no-deps -v $(CURDIR)/scripts:/app/scripts agent python -m scripts.stt_corpus.openslr61 $(ARGS)

# --- Limpieza ------------------------------------------------------------

db-reset: ## PELIGRO: borra la base MySQL (conversaciones) y la vuelve a crear. Conserva pesos y voces
	$(COMPOSE) rm -sf $(AGENT_SERVICES)
	docker volume rm $(notdir $(CURDIR))_mysql_data
	$(MAKE) up-agent

clean: down ## down + elimina las imagenes construidas por este proyecto
	docker image rm -f $(addprefix $(notdir $(CURDIR))-,app agent stt-parakeet asterisk) 2>/dev/null || true
