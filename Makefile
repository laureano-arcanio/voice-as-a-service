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
#                   inferencia a los vLLM de otro host (ej. via `make proxy`, ver
#                   seccion "Inferencia remota" del README).
#   make logs    -> sigue los logs de los 6 servicios
#   make proxy   -> opcional: expone los vllm-* en internet por la IP fija
#                   (nginx en :PROXY_PORT, perfil `proxy`, ver .env.example)
#   make stt-eval-up STT=... + make stt-eval -> opcional: levanta UN STT
#                   candidato (Parakeet o Whisper Turbo, perfil `stt-eval`) y
#                   lo compara contra vllm-stt (WER + latencia)
#   make servers-qwen | servers-whisper | servers-parakeet -> este host como
#                   server de inferencia del loadtest remoto, con ese STT
#   make pbx     -> opcional: Asterisk con la troncal de Anura (perfil `pbx`);
#                   despues `make livekit-sip` (ver docs/TELEFONIA_ANURA.md)
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
        proxy logs-proxy \
        stt-eval-up stt-eval-down stt-eval stt-corpus stt-corpus-entities logs-stt-eval \
        tts-cosyvoice-up tts-cosyvoice-down logs-tts-cosyvoice \
        servers-qwen servers-whisper servers-parakeet \
        pbx restart-pbx logs-pbx pbx-cli pbx-status livekit-sip \
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

# URL publica del proxy, desde PUBLIC_HOST y PROXY_PORT del .env.
define check_public_env
	@grep -qE '^PUBLIC_HOST=.+' .env || { echo "Falta PUBLIC_HOST en .env (ver .env.example)"; exit 1; }
endef
PUBLIC_URL_SH = host=$$(sed -n 's/^PUBLIC_HOST=//p' .env | tail -1); \
	port=$$(sed -n 's/^PROXY_PORT=//p' .env | tail -1); url="http://$$host:$${port:-8100}"

proxy: ## Expone los vllm-* en internet por la IP fija (nginx en :PROXY_PORT, perfil opt-in; requiere PUBLIC_HOST en .env)
	$(check_public_env)
	$(COMPOSE) --profile proxy up -d proxy
	@$(PUBLIC_URL_SH); \
		echo "Proxy arriba. URLs publicas (api_key: VLLM_API_KEY):"; \
		echo "  LLM: $$url/llm/v1"; \
		echo "  STT: $$url/stt/v1"; \
		echo "  TTS: $$url/tts/v1"

logs-proxy: ## Sigue los logs del proxy
	$(COMPOSE) --profile proxy logs -f --tail=200 proxy

STT_EVAL_SERVICES := stt-parakeet stt-whisper

stt-eval-up: ## Levanta UN STT candidato en la GPU 0 y baja el otro (de a uno). Ej: make stt-eval-up STT=stt-parakeet (o stt-whisper)
	@case "$(STT)" in stt-parakeet|stt-whisper) ;; *) echo "Uso: make stt-eval-up STT=stt-parakeet|stt-whisper (de a uno)"; exit 1;; esac
	$(COMPOSE) --profile stt-eval rm -sf $(filter-out $(STT),$(STT_EVAL_SERVICES))
	$(COMPOSE) --profile stt-eval up -d --build --wait $(STT)
	@echo "$(STT) arriba. Comparar contra vllm-stt: make stt-eval"

stt-eval-down: ## Para y elimina el STT candidato que este arriba (libera su VRAM)
	$(COMPOSE) --profile stt-eval rm -sf $(STT_EVAL_SERVICES)

stt-eval: ## WER + latencia de vllm-stt vs el candidato levantado, sobre el corpus del load test. Ej: make stt-eval ARGS="--telephone --runs 5"
	$(COMPOSE) run --rm --no-deps -v $(CURDIR)/scripts:/app/scripts agent python -m scripts.stt_eval $(ARGS)

stt-corpus: ## Arma el corpus de eval de STT con voces argentinas (OpenSLR 61, H/M): limpio, telefonico, +ruido, +micro cortes. Ej: make stt-corpus ARGS="--snr 5"
	$(COMPOSE) run --rm --no-deps -v $(CURDIR)/scripts:/app/scripts agent python -m scripts.stt_corpus.openslr61 $(ARGS)

tts-cosyvoice-up: ## Levanta CosyVoice 3 (TTS candidato para generar el corpus; perfil tts-eval, GPU TTS_EVAL_GPU)
	$(COMPOSE) --profile tts-eval up -d --wait tts-cosyvoice
	@echo "tts-cosyvoice arriba en :8107. Generar con: make stt-corpus-entities ARGS=\"--tts-url http://tts-cosyvoice:8000/v1 --force\""

tts-cosyvoice-down: ## Para y elimina CosyVoice 3 (libera su VRAM)
	$(COMPOSE) --profile tts-eval rm -sf tts-cosyvoice

logs-tts-cosyvoice: ## Sigue los logs de CosyVoice 3
	$(COMPOSE) --profile tts-eval logs -f --tail=200 tts-cosyvoice

stt-corpus-entities: ## Corpus de datos dictados (100 emails, direcciones, telefonos y DNI; voces de OpenSLR 61 clonadas con vllm-tts), en las mismas variantes. Requiere vllm-tts arriba
	$(COMPOSE) run --rm --no-deps -v $(CURDIR)/scripts:/app/scripts agent python -m scripts.stt_corpus.entities $(ARGS)

logs-stt-eval: ## Sigue los logs del STT candidato levantado
	$(COMPOSE) --profile stt-eval logs -f --tail=200 $(STT_EVAL_SERVICES)

# --- Server de inferencia para el loadtest remoto, un STT por vez ----------
# Dejan en este host LLM + TTS + el STT elegido + el proxy publico, y paran
# app/agent: el loadtest corre en otra PC (`make up-remote`) y, si usa el
# mismo proyecto de LiveKit y LIVEKIT_AGENT_NAME, LiveKit repartiria las
# llamadas entre los dos agentes. Los candidatos van en la GPU 1 en lugar de
# vllm-stt (docker-compose.stt-candidates.yml). Al final imprimen lo que va en
# el .env de la PC del loadtest. Volver al uso normal (app/agent aca):
# `make servers-qwen && make up`. Runbook: docs/experiments/README.md.

# $(1) = path del proxy (stt, stt-whisper...), $(2) = modelo
define print_remote_stt_env
	@$(PUBLIC_URL_SH); \
		echo "Listo. En el .env de la PC del loadtest (y recrear su agent):"; \
		echo "  VLLM_STT_BASE_URL=$$url/$(1)/v1"; \
		echo "  VLLM_STT_MODEL=$(2)"
endef

# $(1) = servicio candidato, $(2) = modelo
define servers_stt_candidate
	$(check_public_env)
	$(COMPOSE) --profile stt-eval rm -sf $(filter-out $(1),$(STT_EVAL_SERVICES))
	$(COMPOSE) stop app agent vllm-stt
	$(COMPOSE) -f docker-compose.yml -f docker-compose.stt-candidates.yml \
		--profile stt-eval --profile proxy up -d --build --wait vllm-llm vllm-tts $(1) proxy
	$(call print_remote_stt_env,$(1),$(2))
endef

servers-qwen: ## Loadtest remoto: LLM + TTS + STT vigente (Qwen3-ASR) + proxy; para app/agent aca
	$(check_public_env)
	$(COMPOSE) --profile stt-eval rm -sf $(STT_EVAL_SERVICES)
	$(COMPOSE) stop app agent
	$(COMPOSE) --profile proxy up -d --wait vllm-llm vllm-stt vllm-tts proxy
	$(call print_remote_stt_env,stt,Qwen/Qwen3-ASR-1.7B)

servers-whisper: ## Loadtest remoto: LLM + TTS + Whisper Large v3 Turbo (GPU 1, sin vllm-stt) + proxy; para app/agent aca
	$(call servers_stt_candidate,stt-whisper,openai/whisper-large-v3-turbo)

servers-parakeet: ## Loadtest remoto: LLM + TTS + Parakeet TDT 0.6B v3 (GPU 1, sin vllm-stt) + proxy; para app/agent aca
	$(call servers_stt_candidate,stt-parakeet,nvidia/parakeet-tdt-0.6b-v3)

pbx: ## Levanta Asterisk con la troncal de Anura (perfil opt-in; requiere ANURA_*/LIVEKIT_SIP_* en .env, ver docs/TELEFONIA_ANURA.md)
	@for v in ANURA_DOMAIN ANURA_USER ANURA_PASSWORD ANURA_DID LIVEKIT_SIP_HOST LIVEKIT_SIP_PASSWORD; do \
		grep -qE "^$$v=.+" .env || { echo "Falta $$v en .env (ver docs/TELEFONIA_ANURA.md)"; exit 1; }; \
	done
	$(COMPOSE) --profile pbx up -d --build asterisk
	@echo "Asterisk arriba. Estado de la troncal: make pbx-status (el registro con Anura tarda unos segundos)"

restart-pbx: ## Reinicia Asterisk (rebuild si cambio la imagen, re-renderiza asterisk/conf/ y relee .env)
	$(COMPOSE) --profile pbx up -d --build --force-recreate asterisk

logs-pbx: ## Sigue los logs de Asterisk
	$(COMPOSE) --profile pbx logs -f --tail=200 asterisk

pbx-cli: ## Consola de Asterisk (ej. `pjsip set logger on` para ver el SIP crudo)
	$(COMPOSE) --profile pbx exec asterisk asterisk -rvvv

pbx-status: ## Registro con Anura, endpoints y llamadas activas en Asterisk
	@$(COMPOSE) --profile pbx exec asterisk asterisk -rx "pjsip show registrations"
	@$(COMPOSE) --profile pbx exec asterisk asterisk -rx "pjsip show contacts"
	@$(COMPOSE) --profile pbx exec asterisk asterisk -rx "core show channels"

livekit-sip: ## Crea/actualiza en LiveKit los trunks SIP + dispatch rule para Anura via Asterisk (idempotente)
	$(COMPOSE) run --rm --no-deps -v $(CURDIR)/scripts:/app/scripts app python -m scripts.livekit_sip_setup

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
	docker image rm -f voice-as-a-service-app voice-as-a-service-agent voice-as-a-service-asterisk 2>/dev/null || true

fclean: ## PELIGRO: down -v + elimina imagenes locales del proyecto (borra datos y contenedores)
	$(COMPOSE) down -v --rmi local
