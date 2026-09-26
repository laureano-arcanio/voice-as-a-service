import os

import pytest

from app.conversation.store import ConversationStore
from app.conversation.workflow import load_workflow
from app.db import Base


@pytest.fixture
def workflow():
    return load_workflow("sales_discovery")


@pytest.fixture
def store(tmp_path):
    """SQLite por defecto. Con TEST_DB_DSN (ej. postgresql+psycopg://u:p@host/db) corre
    contra esa base, con el esquema recreado en cada test."""
    dsn = os.getenv("TEST_DB_DSN")
    if not dsn:
        yield ConversationStore(f"sqlite:///{tmp_path}/conversations.db")
        return
    s = ConversationStore(dsn)
    Base.metadata.drop_all(s.engine)
    Base.metadata.create_all(s.engine)
    yield s
    s.engine.dispose()
