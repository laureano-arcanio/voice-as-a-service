"""El motor: el LLM de conversacion decide la respuesta y el fin; la extraccion saca los
datos en segundo plano al terminar; la app valida y guarda."""
import asyncio

from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn, TurnMedia

from .helpers import BASE, FakeLLM, start_with, turn_and_extract


async def test_start_conversation(store, workflow):
    engine = ConversationEngine(FakeLLM(), store)
    state, opening = engine.start_conversation("sales_discovery")
    assert opening == workflow.conversation.opening
    assert set(state.fields) == set(workflow.fields)
    assert all(v is None for v in state.fields.values())
    assert store.get(state.conversation_id).messages[0].text == opening


async def test_start_without_opening(store):
    """WhatsApp entrante: el cliente escribe primero, sin apertura."""
    engine = ConversationEngine(FakeLLM(AgentTurn(assistant_message="¡Hola! ¿Empresa?")),
                                store)
    state, opening = engine.start_conversation("sales_discovery", channel="whatsapp", opening=False)
    assert opening == "" and state.messages == []
    saved = store.get(state.conversation_id)
    assert saved.channel == "whatsapp" and saved.messages == []
    state, _ = await engine.process_turn(state.conversation_id, "Hola, soy Juan")
    assert [m.role for m in state.messages] == ["user", "assistant"]
    assert store.get(state.conversation_id).channel == "whatsapp"


async def test_start_with_given_opening(store):
    engine = ConversationEngine(FakeLLM(), store)
    state, opening = engine.start_conversation("sales_discovery", opening="Hola Juan, te escribo por tu cuota.")
    assert opening == state.messages[0].text == "Hola Juan, te escribo por tu cuota."
    assert state.channel == "voice"


async def test_data_comes_from_the_extraction(store):
    llm = FakeLLM(AgentTurn(assistant_message="Gracias, te escribimos.", status="completed"),
                  extractions=[{"contact_name": "Juan", "company_name": "Acme", "company_activity": "Logística",
                                "employee_count": 80}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine)
    state, turn = await turn_and_extract(engine, cid, "Soy Juan de Acme, hacemos logística y somos unas 80 personas.")
    assert turn.status == "completed"
    assert state.fields["employee_count"] == 80
    assert [m.role for m in state.messages] == ["assistant", "user", "assistant"]


async def test_the_turn_returns_before_the_extraction(store):
    """La respuesta sale sin esperar los datos; solo se extrae al terminar."""
    gate = asyncio.Event()

    class SlowExtraction(FakeLLM):
        async def extract(self, workflow, state):
            await gate.wait()
            return await super().extract(workflow, state)

    llm = SlowExtraction(AgentTurn(assistant_message="¿Empresa?"),
                         AgentTurn(assistant_message="Gracias.", status="completed"),
                         extractions=[{"contact_name": "Juan", "company_name": "Acme"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine)
    await engine.process_turn(cid, "Juan.")
    assert llm.extract_calls == [] and cid not in engine.extractions
    state, _ = await engine.process_turn(cid, "Acme.")
    assert state.fields["contact_name"] is None
    gate.set()
    await engine.wait_extraction(cid)
    state = store.get(cid)
    assert state.fields["contact_name"] == "Juan" and state.fields["company_name"] == "Acme"


async def test_the_llm_message_is_said_as_is(store):
    message = "Entendido, Juan. ¿Dónde trabaja el personal?"
    engine = ConversationEngine(FakeLLM(AgentTurn(assistant_message=message)), store)
    cid = start_with(engine)
    _, turn = await engine.process_turn(cid, "Hola.")
    assert turn.assistant_message == message


async def test_invented_and_invalid_fields_are_dropped_and_reported(store):
    llm = FakeLLM(AgentTurn(assistant_message="Gracias.", status="completed"),
                  extractions=[{"random_field": "foo", "employee_count": "bastantes"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, contact_name="Juan", company_name="Acme", company_activity="Logística")
    state, _ = await turn_and_extract(engine, cid, "Somos bastantes.")
    assert "random_field" not in state.fields and state.fields["employee_count"] is None
    assert state.progress.rejected == {"employee_count": "bastantes"}


async def test_the_llm_decides_when_it_ends(store):
    """Aunque falten datos: la app no pisa la decision (el dashboard muestra lo que falta)."""
    llm = FakeLLM(AgentTurn(assistant_message="Chau.", status="completed"),
                  extractions=[{"contact_name": "Juan"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine)
    state, turn = await turn_and_extract(engine, cid, "Juan, no me interesa, chau.")
    assert turn.status == "completed" and state.status == "completed"
    assert turn.assistant_message == "Chau."
    assert state.progress.outcome == "no_demo"


async def test_outcome_is_recorded_after_the_extraction(store):
    llm = FakeLLM(AgentTurn(assistant_message="Listo.", status="completed"),
                  extractions=[{"wants_demo": True, "email": "juan@acme.com"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, **BASE)
    state, _ = await turn_and_extract(engine, cid, "Sí, a juan arroba acme punto com.")
    assert state.fields["email"] == "juan@acme.com" and state.progress.outcome == "demo"


async def test_goal_with_missing_data_is_incomplete(store):
    """80ac0e22: pidio el link y corto sin dar el resto; contaba como objetivo cumplido."""
    llm = FakeLLM(AgentTurn(assistant_message="Chau.", status="completed"),
                  extractions=[{"wants_demo": True}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, **BASE)
    state, _ = await turn_and_extract(engine, cid, "Sí, pero ahora tengo que cortar.")
    assert state.progress.outcome == "incompleta"


async def test_extracted_email_is_stored_if_valid(store):
    """Se guarda lo que extrae el modelo, validado solo por el tipo del campo: no se revisa si el usuario lo
    dijo (eso lo mide un eval, no la plataforma)."""
    llm = FakeLLM(AgentTurn(assistant_message="Gracias.", status="completed"),
                  extractions=[{"email": "info@browix.com"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, **BASE, wants_demo=True)
    state, _ = await turn_and_extract(engine, cid, "Escribime a")
    assert state.fields["email"] == "info@browix.com" and state.progress.rejected == {}
    llm = FakeLLM(AgentTurn(assistant_message="Gracias.", status="completed"),
                  extractions=[{"email": "info arroba browix punto com"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, **BASE, wants_demo=True)
    state, _ = await turn_and_extract(engine, cid, "info arroba browix punto com")
    assert state.fields["email"] is None and state.progress.rejected == {"email": "info arroba browix punto com"}


async def test_llm_output_is_stored_per_turn(store):
    llm = FakeLLM(AgentTurn(assistant_message="Gracias.", status="completed"),
                  extractions=[{"contact_name": "Juan"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine)
    state, _ = await turn_and_extract(engine, cid, "Juan.")
    reply = state.messages[-1]
    assert [c["kind"] for c in reply.llm] == ["turno", "extraccion"]
    assert reply.llm[0]["input"] == "Juan." and '"contact_name": "Juan"' in reply.llm[1]["output"]


async def test_the_extraction_sees_the_whole_conversation(store):
    """La extraccion ve toda la conversacion, la despedida del agente incluida."""
    class Spy(FakeLLM):
        async def extract(self, workflow, state):
            self.seen = [m.text for m in state.messages]
            return await super().extract(workflow, state)

    llm = Spy(AgentTurn(assistant_message="Chau.", status="completed"))
    engine = ConversationEngine(llm, store)
    cid = start_with(engine)
    await turn_and_extract(engine, cid, "Juan.")
    assert llm.seen[-2:] == ["Juan.", "Chau."]


async def test_retract_last_turn(store):
    llm = FakeLLM(AgentTurn(assistant_message="Gracias.", status="completed"),
                  extractions=[{"attendance_process": "sin control"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, contact_name="Juan")
    before = store.get(cid)
    await turn_and_extract(engine, cid, "no tenemos un control claro")
    assert engine.retract_last_turn(cid)
    after = store.get(cid)
    assert after.fields == before.fields and after.messages == before.messages
    assert not engine.retract_last_turn(cid)


async def test_retract_cancels_the_pending_extraction(store):
    gate = asyncio.Event()

    class SlowExtraction(FakeLLM):
        async def extract(self, workflow, state):
            await gate.wait()
            return await super().extract(workflow, state)

    llm = SlowExtraction(AgentTurn(assistant_message="Gracias.", status="completed"),
                         extractions=[{"attendance_process": "sin control"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, contact_name="Juan")
    await engine.process_turn(cid, "no tenemos")
    assert engine.retract_last_turn(cid)
    gate.set()
    await engine.wait_extraction(cid)
    await asyncio.sleep(0)
    assert store.get(cid).fields["attendance_process"] is None



async def test_voice_note_turn_reaches_the_llm_and_is_not_saved(store):
    """media (WhatsApp) llega al LLM en el estado del turno; se guarda que el mensaje
    del usuario fue audio, no la modalidad del turno."""
    seen = []

    class Spy(FakeLLM):
        async def converse(self, workflow, state, user_message, on_message=None):
            seen.append(state.media)
            return await super().converse(workflow, state, user_message, on_message)

    llm = Spy(AgentTurn(assistant_message="¿Empresa?"),
              AgentTurn(assistant_message="¿Rubro?"))
    engine = ConversationEngine(llm, store)
    state, _ = engine.start_conversation("sales_discovery", channel="whatsapp", opening=False)
    cid = state.conversation_id
    media = TurnMedia(user_voice_note=True, reply_voice_note=True)
    state, _ = await engine.process_turn(cid, "Soy Juan.", media=media)
    await engine.process_turn(cid, "Acme.")
    assert seen == [media, TurnMedia()]
    saved = store.get(cid)
    assert [(m.role, m.voice_note) for m in saved.messages] == [
        ("user", True), ("assistant", False), ("user", False), ("assistant", False)]
    assert saved.media == TurnMedia() and "media" not in saved.model_dump()


async def test_mark_voice_note_marks_the_last_reply(store):
    llm = FakeLLM(AgentTurn(assistant_message="¿Empresa?"))
    engine = ConversationEngine(llm, store)
    cid = start_with(engine)
    await engine.process_turn(cid, "Juan.")
    assert engine.mark_voice_note(cid)
    messages = store.get(cid).messages
    assert [m.voice_note for m in messages] == [False, False, True]
    assert not engine.mark_voice_note("no-existe")
