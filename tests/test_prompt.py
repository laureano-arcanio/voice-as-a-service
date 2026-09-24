from app.conversation.models import Message
from app.conversation.workflow import load_workflow
from app.llm.prompt import build_user_prompt

from .test_workflow import state_with


def test_prompt_has_whole_conversation_before_state():
    wf = load_workflow("berlin_signup")
    state = state_with(wf, wants_pitch=True)
    state.messages = [Message(role="assistant", text="¿Qué actividad te gustaría hacer?"),
                      Message(role="user", text="Calistenia."),
                      Message(role="assistant", text="¿Por qué zona te queda cómodo entrenar?")]
    prompt = build_user_prompt(wf, state, "Nueva Córdoba.")
    assert "usuario: Calistenia." in prompt
    assert prompt.index("CONVERSATION:") < prompt.index("CURRENT STATE:") < prompt.index("NEW USER MESSAGE:")
