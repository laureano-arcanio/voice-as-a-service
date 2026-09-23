import pytest

from app.conversation.store import ConversationStore
from app.conversation.workflow import load_workflow


@pytest.fixture
def workflow():
    return load_workflow("sales_discovery")


@pytest.fixture
def store(tmp_path):
    return ConversationStore(f"sqlite:///{tmp_path}/conversations.db")
