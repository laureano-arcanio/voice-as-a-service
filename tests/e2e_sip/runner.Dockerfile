# Cliente de la prueba SIP de punta a punta (tests/e2e_sip/smoke.py): solo el SDK de LiveKit, con las
# versiones del .venv del repo.
FROM python:3.12-slim-bookworm
RUN pip install --no-cache-dir livekit==1.1.18 livekit-api==1.2.1 livekit-protocol==1.1.27
WORKDIR /e2e
