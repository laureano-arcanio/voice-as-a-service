"""La API falsa de scripts/tools/mock_api.py en un hilo, en un puerto libre de 127.0.0.1 (permitido por
runtime.PRIVATE_HOSTS solo en estos tests)."""
import os
import socket
import threading
import time

import pytest
import uvicorn

from app.tools import runtime
from scripts.tools import mock_api


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def mock_server():
    port = free_port()
    # Con el sandbox de prueba (make e2e-tools), la funcion la llama desde Docker por la IP del host.
    host = "0.0.0.0" if os.getenv("TOOLS_RUNNER_TEST_URL") else "127.0.0.1"
    server = uvicorn.Server(uvicorn.Config(mock_api.app, host=host, port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def mock_api_url(mock_server, monkeypatch):
    monkeypatch.setattr(runtime, "PRIVATE_HOSTS", {"127.0.0.1"})
    mock_api.RECEIVED.clear()
    return mock_server
