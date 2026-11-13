"""Derivacion por WhatsApp de texto: rotacion por plantillas, toque del boton, entrega al operador y reenvio de lo que
escribe la persona (docs/features/WHATSAPP.md).

El estado vive en wa_threads, fuera de store.save. Cada transicion es un UPDATE ... WHERE: si afecta 0 filas, ese camino
no hace nada. En `sending` y `delivering`, handoff_deadline es tambien el dueño del paso: quien lo renueva sigue, y a
quien se lo cambiaron (un toque, una retoma del barrido) deja de enviar.

- sending: enviando la siguiente plantilla. Si vence, el barrido retoma el avance.
- waiting: esperando el toque del tramo vigente. Si vence, el tramo queda no_answer y avanza.
- delivering: alguien toco; entrega en curso. Si vence, el barrido la retoma.
- accepted: el operador tiene los datos. El deadline es el fin del reenvio; el barrido no lo mira.
- closed: rotacion terminada. El toque vale hasta el deadline.

Cada intento es un tramo en handoff_legs con su wamid, nacido ya cerrado (ended_at): no ocupa canal ni descuenta minutos.

La derivacion queda escrita (reserve, en `sending`) antes de responderle a la persona: si `app` muere despues, el barrido
la retoma. Hay una sola rotacion viva por contacto y cuenta: otra derivacion se ignora y queda en handoff.ignored.

Un `sending` o `delivering` vencido es un paso abandonado: el envio de la plantilla tiene tope (team_notify.SEND_DEADLINE)
menor al lease. Los tramos que quedaron sin wamid pasan a `interrupted` y esa persona se vuelve a intentar; un wamid que
llega tarde deja el tramo como enviado y tocable. Tras MAX_RETAKES retomas seguidas se cierra y se libera al contacto.

Si falla una entrega, antes de seguir con la siguiente persona le toca a quien toco y perdio, y despues al tramo que ese
toque desplazo si sigue vigente (_delivery_failed).

Lo que se le dice a la persona se agrega a su conversacion bajo el lock de sus turnos (service.contact_lock). Un turno
ya tiene ese lock: por eso la rotacion arranca en su propia tarea.

Sin telefonos ni textos en los logs ni en los eventos.
"""
from __future__ import annotations

import asyncio
import datetime
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..conversation import variables, workflows
from ..conversation.models import AgentTurn, ConversationState, Message
from ..db import utcnow
from ..llm.prompt import render_conversation
from ..models import (
    ConversationRow,
    HandoffArea,
    HandoffLeg,
    TeamMember,
    WaMessage,
    WaThread,
)
from ..services import events, handoff, wa_routing
from . import store, team_notify

if TYPE_CHECKING:
    from .service import AccountInfo, WhatsAppService

logger = logging.getLogger(__name__)

# Tiempos del plan, sin medir: lo que puede tardar un paso antes de que el barrido lo retome.
SENDING_LEASE = datetime.timedelta(seconds=30)
DELIVERY_LEASE = datetime.timedelta(seconds=20)
MAX_DELIVERY_TRIES = 3
# Retomas seguidas de un paso abandonado, sin medir: un reinicio suma como maximo 1 por rotacion.
MAX_RETAKES = 5
# Corta una cadena larga: las rutas pueden formar ciclos largos (services/handoff._route_target).
MAX_HOPS = 10
POST_CALL_POLL_SECONDS = 0.05
BATCH = 100
# Las pone la derivacion: una variable del pre-call con el mismo nombre no las pisa.
RESERVED_VARS = frozenset({"area", "persona", "cliente", "resumen", "horario"})
VALUE_MAX_CHARS = 500
NO_MEMBER_NAME = "la persona que tomó tu pedido"
NO_AREA_NAME = "el equipo"


def active_relay_id(s: Session, account_id: str, wa_id: str, now: datetime.datetime) -> str | None:
    """La conversacion cuyo reenvio al operador sigue vigente, la mas reciente. Sin mirar closed_at: si el barrido
    cerro el hilo por wa_session_minutes, el reenvio sigue."""
    return s.scalar(select(WaThread.conversation_id).where(
        WaThread.account_id == account_id, WaThread.wa_id == wa_id, WaThread.handoff_status == "accepted",
        WaThread.handoff_deadline > now).order_by(WaThread.created_at.desc()).limit(1))


def stop_relay(s: Session, conversation_id: str) -> None:
    """Cerrar conversacion: termina el reenvio. Una rotacion en curso sigue, porque una emergencia se deriva siempre y
    un deadline adelantado dispararia el barrido. Sin commit."""
    s.execute(update(WaThread).where(WaThread.conversation_id == conversation_id, WaThread.handoff_status == "accepted")
              .values(handoff_deadline=utcnow()))


@dataclass(frozen=True)
class Booking:
    """Resultado de reserve. lease: None si no gano. text_area_id: de que area hablarle a la persona, la viva si no gano
    y la pedida si gano; None si ya no existe."""
    lease: datetime.datetime | None
    text_area_id: str | None


@dataclass
class _Step:
    """Un area de la cadena, leida de la base."""
    area: HandoffArea | None
    members: list[TeamMember] = field(default_factory=list)     # los que faltan en esta rotacion
    tried: bool = False                                         # ya tuvo tramos en esta rotacion
    used_areas: set[str] = field(default_factory=set)


class TextHandoffs:
    def __init__(self, service: WhatsAppService):
        self.service = service
        self.sessions = service.sessions
        self.engine = service.engine

    # --- Lecturas y transiciones ---

    def _thread(self, conversation_id: str) -> WaThread | None:
        with self.sessions() as s:
            thread = s.get(WaThread, conversation_id)
            if thread is not None:
                s.expunge(thread)
            return thread

    def _move(self, conversation_id: str, *where, **values) -> bool:
        """Una transicion. True si la gano este camino."""
        with self.sessions() as s:
            done = s.execute(update(WaThread).where(WaThread.conversation_id == conversation_id, *where)
                             .values(**values)).rowcount
            s.commit()
        return bool(done)

    def _renew(self, thread: WaThread, status: str, lease: datetime.datetime,
               length: datetime.timedelta) -> datetime.datetime | None:
        """Sigue siendo dueño del paso: el deadline nuevo, o None si ya lo tomo otro."""
        fresh = utcnow() + length
        won = self._move(thread.conversation_id, WaThread.handoff_status == status, WaThread.handoff_deadline == lease,
                         handoff_deadline=fresh)
        return fresh if won else None

    def _event(self, thread: WaThread, type: str, *, area_id: str | None = None, member_id: str | None = None,
               actor: str = "system", **data) -> None:
        with self.sessions() as s:
            events.record(s, thread.client_id, type, conversation_id=thread.conversation_id, actor=actor,
                          area_id=area_id, team_member_id=member_id, channel="whatsapp", **data)
            s.commit()

    def _update_leg(self, leg_id: str | None, **values) -> None:
        if not leg_id:
            return
        with self.sessions() as s:
            s.execute(update(HandoffLeg).where(HandoffLeg.id == leg_id).values(**values))
            s.commit()

    def _leg_info(self, thread: WaThread) -> tuple[HandoffLeg | None, TeamMember | None, HandoffArea | None]:
        """El tramo vigente, su persona y el area, de la base. Cualquiera puede ya no estar."""
        with self.sessions() as s:
            leg = s.get(HandoffLeg, thread.handoff_leg_id) if thread.handoff_leg_id else None
            member = s.get(TeamMember, leg.team_member_id) if leg is not None and leg.team_member_id else None
            area = s.get(HandoffArea, thread.handoff_area_id) if thread.handoff_area_id else None
            if area is not None and area.client_id != thread.client_id:
                area = None
            for row in (leg, member, area):
                if row is not None:
                    s.expunge(row)
            return leg, member, area

    # --- Valores de mensajes y plantillas ---

    def _variables(self, conversation_id: str) -> dict:
        """Las de la conversacion (ocultas incluidas: van al equipo, no al LLM) sin las reservadas, y las del
        sistema."""
        state = self.engine.store.get(conversation_id)
        values = variables.message_values(state, self.engine.workflow(state) if state is not None else None)
        return {k: "" if v is None else v for k, v in values.items() if k not in RESERVED_VARS}

    def _template_values(self, thread: WaThread, *, contact: bool) -> dict:
        """Para los params de una plantilla. contact: el aviso, que lleva el telefono; en la rotacion no sale antes de
        aceptar, y por eso tampoco el nombre que escribio la persona en su perfil."""
        values = self._variables(thread.conversation_id)
        if contact:
            values["cliente"] = f"+{thread.wa_id}"
            values["nombre"] = values.get("nombre") or thread.contact_name or ""
        return values

    def _texts(self, thread: WaThread, area: HandoffArea | None, member: TeamMember | None = None, *,
               contact: bool = True, **extra) -> tuple[dict, dict]:
        """Los mensajes del area y sus valores. Una variable muy larga no ocupa el texto entero. contact=False: para los
        mensajes de antes de aceptar (handoff.PRE_ACCEPT_MESSAGES), sin datos de la persona ni variables del pre-call."""
        texts = handoff.messages(area) if area else handoff.DEFAULT_MESSAGES
        safe = {"area": area.name if area else NO_AREA_NAME, "persona": member.name if member else NO_MEMBER_NAME,
                "horario": handoff.describe_schedule(area.schedule) if area else ""}
        if not contact:
            return texts, safe
        values = {k: str(v)[:VALUE_MAX_CHARS] for k, v in self._variables(thread.conversation_id).items()}
        return texts, values | safe | {"cliente": f"+{thread.wa_id}",
                                       "nombre": values.get("nombre") or thread.contact_name or "-", **extra}

    async def _summary(self, conversation_id: str, timeout: float | None = None) -> str:
        """El resumen de la conversacion, con tope y respaldo. No lanza."""
        try:
            state = self.engine.store.get(conversation_id)
            workflow = self.engine.workflow(state)
            llm = self.engine.llms.for_turn(workflow, 1 + sum(m.role == "user" for m in state.messages), state.client_id)
            conversation = render_conversation(state)
        except Exception:
            logger.exception("derivacion %s: sin resumen", conversation_id)
            return handoff.FALLBACK_SUMMARY
        return await handoff.safe_summary(llm, conversation, timeout)

    # --- Mensajes a la persona ---

    def _append(self, conversation_id: str, role: str, text: str, voice_note: bool = False) -> None:
        """Sin await: no se intercala con la extraccion, que relee y guarda el estado. Un aviso del agente seguido de
        otro va en el mismo mensaje, como en voz."""
        state = self.engine.store.get(conversation_id)
        if state is None:
            return
        last = state.messages[-1] if state.messages else None
        if role == "assistant" and last is not None and last.role == "assistant":
            last.text = f"{last.text} {text}".strip()
        else:
            state.messages.append(Message(role=role, text=text, voice_note=voice_note))
        self.engine.store.save(state)

    async def _say(self, thread: WaThread, text: str) -> None:
        """A la persona, por la cuenta del hilo, en su formato. Queda en la conversacion. Si no sale, queda registrado."""
        self._append(thread.conversation_id, "assistant", text)
        with self.sessions() as s:
            info = self.service.account_info(s, thread.account_id, thread.client_id)
        if info is None:
            logger.warning("derivacion %s: la cuenta del hilo no puede enviar", thread.conversation_id)
            return
        graph = self.service._graph(info.token)
        state = self.engine.store.get(thread.conversation_id)
        if (thread.handoff_voice_note and state is not None and len(text) <= settings.wa_audio_max_reply_chars
                and await self.service._send_audio(graph, info, thread.wa_id, state, text)):
            self.engine.mark_voice_note(thread.conversation_id)
            return
        await self.service._send(graph, info, thread.wa_id, thread.conversation_id, text)

    async def _tell(self, thread: WaThread, text: str, *, locked: bool = False) -> None:
        if locked:
            await self._say(thread, text)
            return
        with self.sessions() as s:
            info = self.service.account_info(s, thread.account_id, thread.client_id)
        if info is None:
            await self._say(thread, text)
            return
        async with self.service.contact_lock(info.phone_number_id, thread.wa_id):
            await self._say(thread, text)

    # --- Arranque ---

    def transfer_area(self, state: ConversationState, turn: AgentTurn) -> dict | None:
        """El area del transfer_call de este turno, en cualquier estado: si se despacha o se ignora lo decide reserve."""
        if not turn.handoff:
            return None
        area = handoff.find_area(state.progress.handoff_areas, turn.handoff)
        if area is None:
            logger.warning("derivacion %s: area desconocida", state.conversation_id)
        return area

    def transfer_text(self, conversation_id: str, area_id: str | None) -> str:
        """El modelo derivo sin escribir nada: el aviso del area, tambien en la conversacion. No lanza: la persona recibe
        una respuesta aunque la base no conteste."""
        try:
            thread = self._thread(conversation_id)
            with self.sessions() as s:
                row = s.get(HandoffArea, area_id) if area_id else None
                if row is not None and row.client_id != thread.client_id:
                    row = None
                if row is not None:
                    s.expunge(row)
            texts, values = self._texts(thread, row)
            text = handoff.render(texts["transfer"], **values)
            self._append(conversation_id, "assistant", text)
            return text
        except Exception:
            logger.exception("derivacion %s: sin aviso del area", conversation_id)
            return handoff.render(handoff.DEFAULT_MESSAGES["transfer"], area=NO_AREA_NAME)

    def reserve(self, conversation_id: str, area: dict, voice_note: bool) -> Booking:
        """Deja la derivacion escrita, en `sending`, antes de responderle a la persona. No lanza: una derivacion que no se
        pudo escribir no le saca la respuesta a la persona. Si se borro el area en el medio, reserva sin area y termina en
        no_answer. Sin await: el turno sigue sin que nada se intercale."""
        try:
            try:
                return self._book(conversation_id, area, area["id"], voice_note)
            except IntegrityError:
                # La transaccion entera se deshizo: el reintento rehace tambien el vencimiento de los `closed`.
                logger.warning("derivacion %s: el area ya no existe", conversation_id)
                return self._book(conversation_id, area, None, voice_note)
        except Exception:
            logger.exception("derivacion %s: no se pudo reservar", conversation_id)
            return Booking(None, area["id"])

    def _book(self, conversation_id: str, area: dict, area_id: str | None, voice_note: bool) -> Booking:
        """Una transaccion: vence los `closed` de otras conversaciones del contacto, mira si hay otra rotacion viva y
        escribe la propia. Si no gano, nada de eso queda: el toque tardio de otra conversacion sigue valiendo."""
        now = utcnow()
        with self.sessions() as s:
            thread = s.get(WaThread, conversation_id)
            if thread is None:
                logger.warning("derivacion %s: sin hilo", conversation_id)
                return Booking(None, area_id)
            client_id, own_status, own_area = thread.client_id, thread.handoff_status, thread.handoff_area_id
            if area_id is not None:
                row = s.get(HandoffArea, area_id)
                if row is None or row.client_id != client_id:
                    area_id = None
            contact = (WaThread.account_id == thread.account_id, WaThread.wa_id == thread.wa_id,
                       WaThread.conversation_id != conversation_id)
            s.execute(update(WaThread).where(*contact, WaThread.handoff_status == "closed",
                                             WaThread.handoff_deadline > now).values(handoff_deadline=now))
            other = s.execute(select(WaThread.conversation_id, WaThread.handoff_status, WaThread.handoff_area_id).where(
                *contact, or_(WaThread.handoff_status.in_(("sending", "waiting", "delivering")),
                              and_(WaThread.handoff_status == "accepted", WaThread.handoff_deadline > now)))
                .order_by(WaThread.created_at.desc()).limit(1)).first()
            if other is None:
                lease = now + SENDING_LEASE
                won = s.execute(update(WaThread).where(
                    WaThread.conversation_id == conversation_id,
                    or_(WaThread.handoff_status.is_(None), WaThread.handoff_status == "closed",
                        and_(WaThread.handoff_status == "accepted", WaThread.handoff_deadline <= now)))
                    .values(handoff_status="sending", handoff_area_id=area_id, handoff_leg_id=None,
                            handoff_started_at=now, handoff_closed_at=None, handoff_deadline=lease,
                            handoff_voice_note=voice_note, handoff_delivery_tries=0, handoff_retakes=0)).rowcount
                if won:
                    s.commit()
                    return Booking(lease, area_id)
            s.rollback()
            other_id, live_status, live_area = other if other is not None else (None, own_status, own_area)
            live = s.get(HandoffArea, live_area) if live_area else None
            logger.info("derivacion %s: transfer_call ignorado (%s)", conversation_id, live_status)
            events.record(s, client_id, "handoff.ignored", conversation_id=conversation_id, actor="agent",
                          area_id=area_id, channel="whatsapp", area=area.get("name"),
                          live_area=live.name if live is not None else "", live_status=live_status,
                          other_conversation=other_id)
            s.commit()
            return Booking(None, live_area)

    def start(self, conversation_id: str, lease: datetime.datetime) -> None:
        """Con la reserva ganada, despues de responder: en su tarea, porque el que llama tiene el lock del contacto y un
        fin de cadena le escribe."""
        self.service._spawn(self._advance(conversation_id, lease))

    # --- Rotacion ---

    def _load_step(self, thread: WaThread, area_id: str | None) -> _Step:
        with self.sessions() as s:
            area = s.get(HandoffArea, area_id) if area_id else None
            if area is None or area.client_id != thread.client_id or not area.active:
                return _Step(None)
            legs = s.execute(select(HandoffLeg.team_member_id, HandoffLeg.area_id, HandoffLeg.result, HandoffLeg.wamid)
                             .where(HandoffLeg.conversation_id == thread.conversation_id,
                                    HandoffLeg.created_at >= thread.handoff_started_at)).all()
            # Nadie sabe si le llego un envio interrumpido, y sin wamid no pudo tocar: se le vuelve a intentar.
            tried = {leg.team_member_id for leg in legs if leg.result != "interrupted" or leg.wamid}
            members = [m for m in handoff.candidates(s, area) if m.whatsapp_notify and m.id not in tried]
            step = _Step(area, members, any(leg.area_id == area.id for leg in legs),
                         {leg.area_id for leg in legs if leg.area_id})
            s.expunge(area)
            for member in members:
                s.expunge(member)
            return step

    def _route(self, thread: WaThread, area: HandoffArea, key: str, visited: set[str], hops: int) -> HandoffArea | None:
        """El area siguiente, o None si no hay, ya paso por ella en este avance, se llego al tope o no sirve. Otra vuelta
        por un area ya usada no repite a nadie: los tramos de la rotacion quedan afuera."""
        target_id = getattr(area, key)
        if not target_id or target_id in visited or hops >= MAX_HOPS:
            return None
        with self.sessions() as s:
            target = s.get(HandoffArea, target_id)
            if target is None or target.client_id != thread.client_id or not target.active:
                logger.warning("derivacion %s: ruta %s ignorada", thread.conversation_id, key)
                return None
            s.expunge(target)
            return target

    async def _advance(self, conversation_id: str, lease: datetime.datetime) -> None:
        """Con el avance ganado: la siguiente plantilla, el aviso o el fin de la cadena."""
        thread = self._thread(conversation_id)
        if thread is None or thread.handoff_status != "sending" or thread.handoff_deadline != lease:
            return
        visited: set[str] = set()
        area_id = thread.handoff_area_id
        last: HandoffArea | None = None
        reason = "no_answer"
        while True:
            step = self._load_step(thread, area_id)
            area = step.area
            if area is None:
                await self._end_chain(thread, lease, last, "no_answer")
                return
            last = area
            visited.add(area.id)
            if not handoff.is_open(area.schedule):
                reason, key = "after_hours", "after_hours_area_id"
            elif area.delivery == "whatsapp":
                reason, key = "no_answer", "no_answer_area_id"
                lease = self._renew(thread, "sending", lease, SENDING_LEASE)
                if lease is None:
                    return
                notice, lease = await self._notify(thread, area, lease)
                if lease is None:
                    return
                if notice.ok:
                    await self._end_chain(thread, lease, area, "notified")
                    return
            else:
                key = "no_answer_area_id"
                finished, lease = await self._send_next(thread, step, lease)
                if finished or lease is None:
                    return
                reason = "no_answer" if step.tried or step.members else "no_members"
            target = self._route(thread, area, key, visited, len(visited | step.used_areas))
            if target is None:
                if not step.tried and area.delivery != "whatsapp" and reason != "no_answer":
                    self._event(thread, "handoff.unavailable", area_id=area.id, actor="agent", area=area.name,
                                reason=reason)
                await self._end_chain(thread, lease, area, "after_hours" if reason == "after_hours" else "no_answer")
                return
            self._passed(thread, step, target, reason)
            area_id = target.id

    def _passed(self, thread: WaThread, step: _Step, target: HandoffArea, reason: str) -> None:
        """Un pase a otra area de llamada no suma por esta en los reportes. A un area de aviso no es un pase: el pedido
        quedo sin atender y esta area lo cuenta."""
        area = step.area
        if target.delivery != "whatsapp":
            self._event(thread, "handoff.rerouted", area_id=area.id, actor="agent", area=area.name, to=target.name,
                        reason=reason)
        elif not step.tried and area.delivery != "whatsapp":
            self._event(thread, "handoff.unavailable", area_id=area.id, actor="agent", area=area.name, reason=reason)

    async def _notify(self, thread: WaThread, area: HandoffArea,
                      lease: datetime.datetime) -> tuple[team_notify.Notice, datetime.datetime | None]:
        """(resultado, lease vigente). El lease se renueva antes de cada persona: con Meta lento, una retoma del barrido
        no le manda el aviso a una segunda persona a la vez que este camino."""
        current = lease

        def still_mine() -> bool:
            nonlocal current
            current = self._renew(thread, "sending", current, SENDING_LEASE)
            return current is not None

        values = self._template_values(thread, contact=True)
        if "resumen" in ((area.whatsapp or {}).get("template") or {}).get("params", []):
            values["resumen"] = await self._summary(thread.conversation_id)
        notice = await team_notify.notify_area(self.sessions, thread.client_id, area.id, values, thread.conversation_id,
                                               graph_factory=self.service._graph, before_send=still_mine)
        return notice, current

    async def _send_next(self, thread: WaThread, step: _Step,
                         lease: datetime.datetime) -> tuple[bool, datetime.datetime | None]:
        """La plantilla a la siguiente persona del area. Rechazada: prueba con la otra. (salio, lease vigente)."""
        area = step.area
        template_cfg = (area.whatsapp or {}).get("template")
        if not template_cfg:
            return False, lease     # sin plantilla: se saltea
        values = self._template_values(thread, contact=False)
        if "resumen" in template_cfg.get("params", []) and step.members:
            values["resumen"] = await self._summary(thread.conversation_id)
        requested = step.tried
        for member in step.members:
            lease = self._renew(thread, "sending", lease, SENDING_LEASE)
            if lease is None:
                return True, None
            if not requested:
                requested = True
                self._event(thread, "handoff.requested", area_id=area.id, actor="agent", area=area.name,
                            members=len(step.members))
            ok, leg_id, error = await self._send_template(thread, area, member, template_cfg, values)
            if ok:
                wait = (area.whatsapp or {}).get("wait_seconds") or handoff.WAIT_SECONDS_DEFAULT
                self._move(thread.conversation_id, WaThread.handoff_status == "sending",
                           WaThread.handoff_deadline == lease, handoff_status="waiting", handoff_area_id=area.id,
                           handoff_leg_id=leg_id, handoff_retakes=0,
                           handoff_deadline=utcnow() + datetime.timedelta(seconds=wait))
                return True, lease
            if error and error.get("reason") in team_notify.ACCOUNT_REASONS:
                break
        return False, lease

    def _open_leg(self, thread: WaThread, area: HandoffArea, member: TeamMember) -> str | None:
        """Relee a la persona y crea su tramo. None: no se le envia, porque se fue (inactiva o borrada, tambien si la
        borran antes del insert: la FK lo rechaza) o porque no se pudo leer."""
        try:
            with self.sessions() as s:
                if not s.scalar(select(TeamMember.active).where(TeamMember.id == member.id)):
                    return None
                leg = HandoffLeg(client_id=thread.client_id, conversation_id=thread.conversation_id, area_id=area.id,
                                 team_member_id=member.id, phone=member.phone, result="whatsapp_sent",
                                 ended_at=utcnow(), billed_seconds=0)
                s.add(leg)
                s.commit()
                return leg.id
        except IntegrityError:
            logger.info("derivacion %s: la persona o el area ya no existe", thread.conversation_id)
            return None
        except Exception:
            logger.exception("derivacion %s: no se pudo releer a una persona", thread.conversation_id)
            team_notify._record_failure(self.sessions, thread.client_id, area.id, member.id, thread.conversation_id,
                                        {"reason": "internal"})
            return None

    async def _send_template(self, thread: WaThread, area: HandoffArea, member: TeamMember, template_cfg: dict,
                             values: dict) -> tuple[bool, str | None, dict | None]:
        """Un intento: el tramo se crea antes del envio. (salio, id del tramo, error). Sin tramo (_open_leg) no se envia y
        no hay error: sigue la siguiente. Sin wamid no se puede aceptar: es como si no hubiera salido. Con wamid queda
        enviado y tocable, aunque una retoma lo haya marcado interrupted."""
        leg_id = self._open_leg(thread, area, member)
        if leg_id is None:
            return False, None, None
        # Sin await hasta el envio: lo que la plantilla lleva no le llega a quien se fue.
        self._event(thread, "handoff.dialing", area_id=area.id, member_id=member.id, person=member.name)
        ok, wamid, error = await team_notify.send(self.sessions, thread.client_id, area, member, template_cfg, values,
                                                  thread.conversation_id, graph_factory=self.service._graph)
        if ok and wamid:
            self._update_leg(leg_id, result="whatsapp_sent", wamid=wamid)
            return True, leg_id, None
        self._update_leg(leg_id, result="failed")
        if ok:
            self._event(thread, "handoff.whatsapp_failed", area_id=area.id, member_id=member.id, reason="no_wamid")
        return False, leg_id, error

    async def _end_chain(self, thread: WaThread, lease: datetime.datetime, area: HandoffArea | None, key: str) -> None:
        now = utcnow()
        late = datetime.timedelta(minutes=settings.wa_handoff_late_minutes)
        if not self._move(thread.conversation_id, WaThread.handoff_status == "sending",
                          WaThread.handoff_deadline == lease, handoff_status="closed", handoff_closed_at=now,
                          handoff_deadline=now + late, handoff_delivery_tries=0, handoff_retakes=0):
            return
        texts, values = self._texts(thread, area)
        await self._tell(thread, handoff.render(texts[key], **values))

    # --- Barrido ---

    async def sweep(self) -> int:
        """Lo vencido de la rotacion, cada uno en su tarea y sin esperarlo: un envio lento o una persona con un turno en
        curso no frenan a los demas. Cada _resume mueve el deadline antes de su primer await, asi que el barrido siguiente
        no lo vuelve a tomar hasta que venza ese lease. Las fallas las registra service._done."""
        now = utcnow()
        with self.sessions() as s:
            rows = s.execute(select(WaThread.conversation_id, WaThread.handoff_status, WaThread.handoff_deadline,
                                    WaThread.handoff_leg_id)
                             .where(WaThread.handoff_status.in_(("sending", "waiting", "delivering")),
                                    WaThread.handoff_deadline <= now)
                             .order_by(WaThread.handoff_deadline).limit(BATCH)).all()
        for row in rows:
            self.service._spawn(self._resume(*row))
        return len(rows)

    async def _resume(self, conversation_id: str, status: str, deadline: datetime.datetime, leg_id: str | None) -> None:
        now = utcnow()
        where = (WaThread.handoff_status == status, WaThread.handoff_deadline == deadline)
        lease = now + (DELIVERY_LEASE if status == "delivering" else SENDING_LEASE)
        values = {"handoff_deadline": lease}
        if status != "delivering":
            values["handoff_status"] = "sending"
        if status != "waiting":     # paso abandonado; un waiting vencido es el camino normal
            values["handoff_retakes"] = WaThread.handoff_retakes + 1
        if not self._move(conversation_id, *where, **values):
            return
        if status == "waiting":
            await self._leg_expired(conversation_id, leg_id)
            await self._advance(conversation_id, lease)
            return
        thread = self._thread(conversation_id)
        if thread is None:
            return
        self._interrupt_legs(thread)
        if thread.handoff_retakes >= MAX_RETAKES:
            await self._retakes_exhausted(thread, lease)
        elif status == "delivering":
            await self._deliver(conversation_id, lease)
        else:
            await self._advance(conversation_id, lease)

    def _interrupt_legs(self, thread: WaThread) -> None:
        """Los envios que quedaron sin respuesta de Meta. `failed` no entra: ese lo escribio alguien que tuvo respuesta,
        y un rechazo no se reintenta."""
        with self.sessions() as s:
            s.execute(update(HandoffLeg).where(HandoffLeg.conversation_id == thread.conversation_id,
                                               HandoffLeg.created_at >= thread.handoff_started_at,
                                               HandoffLeg.wamid.is_(None), HandoffLeg.result == "whatsapp_sent")
                      .values(result="interrupted"))
            s.commit()

    async def _retakes_exhausted(self, thread: WaThread, lease: datetime.datetime) -> None:
        """Una fila que no termina nunca no le ocupa la rotacion al contacto para siempre."""
        logger.error("derivacion %s: %d retomas en %s, se corta", thread.conversation_id, thread.handoff_retakes,
                     thread.handoff_status)
        if thread.handoff_status == "delivering":
            await self._delivery_failed(thread, lease, "retakes_exhausted")
            return
        _, _, area = self._leg_info(thread)
        self._event(thread, "handoff.whatsapp_failed", area_id=area.id if area else None, reason="retakes_exhausted")
        await self._end_chain(thread, lease, area, "no_answer")

    async def _leg_expired(self, conversation_id: str, leg_id: str | None) -> None:
        thread = self._thread(conversation_id)
        with self.sessions() as s:
            leg = s.get(HandoffLeg, leg_id) if leg_id else None
            ids = (leg.area_id, leg.team_member_id) if leg is not None else (None, None)
        self._update_leg(leg_id, result="no_answer")
        if thread is not None and leg_id:
            self._event(thread, "handoff.no_answer", area_id=ids[0], member_id=ids[1])

    # --- Toque ---

    async def on_tap(self, info: AccountInfo, wa_id: str, wamid: str, msg: dict) -> bool:
        """Toque del boton de una plantilla. True si era de una rotacion y quedo atendido aca; False sigue como cualquier
        boton (los de campaña). Otro numero, cuenta o cliente no tiene efecto sobre la rotacion."""
        context = msg.get("context")
        context_id = context.get("id") if isinstance(context, dict) else None
        if not isinstance(context_id, str) or not context_id:
            return False
        with self.sessions() as s:
            leg = s.scalar(select(HandoffLeg).where(HandoffLeg.wamid == context_id))
            if (leg is None or leg.client_id != info.client_id or not wa_routing.same_number(leg.phone, wa_id)
                    or not self._sent_by(s, leg, info.id)):
                return False
            leg_id, conversation_id, created_at, area_id = leg.id, leg.conversation_id, leg.created_at, leg.area_id
            member_id = leg.team_member_id
        await self.service._mark_read(self.service._graph(info.token), info, wamid)
        with self.sessions() as s:
            store.set_inbound(s, [wamid], status="answered")
            s.commit()
        now = utcnow()
        lease = now + DELIVERY_LEASE
        won = self._move(
            conversation_id, WaThread.handoff_started_at <= created_at,
            or_(WaThread.handoff_status.in_(("waiting", "sending")),
                and_(WaThread.handoff_status == "closed", WaThread.handoff_deadline > now)),
            handoff_status="delivering", handoff_leg_id=leg_id, handoff_area_id=area_id, handoff_deadline=lease,
            handoff_delivery_tries=0, handoff_retakes=0)
        if not won:
            await self._tap_answer(info, wa_id, conversation_id, leg_id, created_at, member_id)
            return True
        self._update_leg(leg_id, answered_at=now)
        thread = self._thread(conversation_id)
        self._event(thread, "handoff.confirmed", area_id=area_id, member_id=member_id, actor="person")
        await self._deliver(conversation_id, lease)
        return True

    @staticmethod
    def _sent_by(s: Session, leg: HandoffLeg, account_id: str) -> bool:
        """El toque llega por la cuenta que envio la plantilla."""
        sent = s.scalar(select(WaMessage.account_id).where(WaMessage.wamid == leg.wamid))
        if sent is not None:
            return sent == account_id
        area = s.get(HandoffArea, leg.area_id) if leg.area_id else None
        return area is not None and (area.whatsapp or {}).get("account_id") == account_id

    async def _tap_answer(self, info: AccountInfo, wa_id: str, conversation_id: str, leg_id: str,
                          created_at: datetime.datetime, member_id: str | None) -> None:
        """No la tomo este toque: se le responde, fuera de la conversacion. Si perdio contra otro operador de la rotacion,
        queda registrado: recibe la entrega si la del otro falla (_delivery_failed). Un desactivado o borrado no recibe nada."""
        thread = self._thread(conversation_id)
        if thread is None:
            return
        _, member, area = self._leg_info(thread)
        same_rotation = thread.handoff_started_at is not None and created_at >= thread.handoff_started_at
        taken = thread.handoff_status == "delivering" or (
            thread.handoff_status == "accepted" and thread.handoff_deadline > utcnow())
        own = member is not None and member.id == member_id
        texts, values = self._texts(thread, area, member, contact=False)
        # El tramo de un miembro borrado queda sin team_member_id.
        if not same_rotation or not taken or member_id is None or (own and not member.active):
            body = handoff.render(texts["tap_closed"], **values)
        elif not own:
            self._mark_lost_tap(leg_id)
            body = handoff.render(texts["tap_taken"], **values)
        elif thread.handoff_status == "delivering":
            body = handoff.render(texts["tap_wait"], **values)
        else:
            body = await self._contact_text(thread, area, member)
            # Se pudo ir durante el resumen: sin await hasta el envio.
            _, member, _ = self._leg_info(thread)
            if member is None or not member.active:
                body = handoff.render(texts["tap_closed"], **values)
        await self.service.send_team(info, wa_routing.digits(wa_id), None, body, "team_notice")

    def _mark_lost_tap(self, leg_id: str) -> None:
        with self.sessions() as s:
            s.execute(update(HandoffLeg).where(HandoffLeg.id == leg_id, HandoffLeg.answered_at.is_(None))
                      .values(answered_at=utcnow()))
            s.commit()

    # --- Entrega al operador ---

    async def _deliver(self, conversation_id: str, lease: datetime.datetime) -> None:
        """En orden: (a) acuse sin datos, (b) post-call, (c) contacto, (d) aceptada. El barrido la retoma si vence: con
        tries=0 repite desde (a), porque un mensaje repetido es inofensivo; si no, solo (c)."""
        thread = self._thread(conversation_id)
        if thread is None or thread.handoff_status != "delivering":
            return
        leg, member, area = self._leg_info(thread)
        with self.sessions() as s:
            info = self.service.account_info(s, (area.whatsapp or {}).get("account_id") if area else None,
                                             thread.client_id)
        if leg is None or member is None or not member.active or area is None or info is None:
            await self._delivery_failed(thread, lease, "no_route")
            return
        number = wa_routing.digits(leg.phone)
        texts, values = self._texts(thread, area, member, contact=False)
        if thread.handoff_delivery_tries == 0:
            if not await self.service.send_team(info, number, conversation_id,
                                                handoff.render(texts["operator_ack"], **values), "team_notice"):
                await self._delivery_failed(thread, lease, "ack_rejected")
                return
            lease = self._renew(thread, "delivering", lease, DELIVERY_LEASE)
            if lease is None:
                return
            summary = asyncio.ensure_future(self._summary(conversation_id, settings.post_call_wait_seconds))
            await self._post_call_step(thread)
            contact = await self._contact_text(thread, area, member, await summary)
        else:
            contact = await self._contact_text(thread, area, member)
        lease = self._renew(thread, "delivering", lease, DELIVERY_LEASE)
        if lease is None:
            return
        # Se pudo ir durante el post-call o el resumen: sin await hasta el envio. Un post-call ya hecho no se deshace ni
        # se repite con el operador siguiente (_post_call_step).
        _, member, _ = self._leg_info(thread)
        if member is None or not member.active:
            await self._delivery_failed(thread, lease, "no_route")
            return
        if not await self.service.send_team(info, number, conversation_id, contact, "team_notice"):
            tries = thread.handoff_delivery_tries + 1
            if tries >= MAX_DELIVERY_TRIES:
                await self._delivery_failed(thread, lease, "contact_rejected")
            else:
                self._move(conversation_id, WaThread.handoff_status == "delivering", WaThread.handoff_deadline == lease,
                           handoff_delivery_tries=tries, handoff_deadline=utcnow() + DELIVERY_LEASE)
            return
        await self._accepted(thread, lease, leg, member, area)

    async def _accepted(self, thread: WaThread, lease: datetime.datetime, leg: HandoffLeg, member: TeamMember | None,
                        area: HandoffArea) -> None:
        """(d) El operador tiene los datos: arranca el reenvio."""
        now = utcnow()
        if not self._move(thread.conversation_id, WaThread.handoff_status == "delivering",
                          WaThread.handoff_deadline == lease, handoff_status="accepted", handoff_delivery_tries=0,
                          handoff_retakes=0,
                          handoff_deadline=now + datetime.timedelta(hours=settings.wa_handoff_relay_hours)):
            return
        self._update_leg(leg.id, result="connected", connected_at=now)
        with self.sessions() as s:
            if (row := s.get(HandoffArea, area.id)) is not None and member is not None:
                row.last_member_id = member.id
                s.commit()
        self._event(thread, "handoff.connected", area_id=area.id, member_id=member.id if member else None,
                    person=member.name if member else "")
        texts, values = self._texts(thread, area, member)
        await self._tell(thread, handoff.render(texts["accepted"], **values))

    def _post_call_tool(self, conversation_id: str):
        """El post-call del agente de la conversacion, o None."""
        state = self.engine.store.get(conversation_id)
        try:
            workflow = self.engine.workflow(state) if state is not None else None
        except KeyError:
            return None
        return workflow.workflows.post_call if workflow is not None and workflow.workflows else None

    async def _post_call_step(self, thread: WaThread) -> None:
        """(b) Corre el post-call o consulta el que ya corre, hasta POST_CALL_WAIT_SECONDS. Si falla o vence, sigue en el
        loop y se entrega igual. Una espera de reintento no se adelanta, y lo ya terminado no se repite."""
        conversation_id = thread.conversation_id
        if self._post_call_tool(conversation_id) is None:
            return
        loop = asyncio.get_running_loop()
        until = loop.time() + settings.post_call_wait_seconds
        with self.sessions() as s:
            row = s.get(ConversationRow, conversation_id)
            status, attempts = row.post_call_status, row.post_call_attempts
            if status is None or status == "armed" or (status == "pending" and attempts == 0):
                seen = (ConversationRow.post_call_status.is_(None) if status is None
                        else ConversationRow.post_call_status == status)
                s.execute(update(ConversationRow).where(ConversationRow.id == conversation_id, seen)
                          .values(post_call_status="pending", post_call_next_at=utcnow()))
                s.commit()
                run = True
            else:
                run = False
                if status != "running":
                    return
        if run:
            # El post-call usa {{fields.x}} y {{call.summary}}: el análisis corre antes, dentro de la misma espera. Si
            # vence, el post-call corre igual con lo que haya y la entrega sigue.
            await self.engine.analyze(conversation_id, max(until - loop.time(), 0))
            # No se cancela al vencer la espera: termina en su tarea y deja su resultado en la base.
            task = self.service._spawn(workflows.run_post_call(self.sessions, self.engine, conversation_id,
                                                               actor=f"wa:{thread.wa_id}"))
            done, _ = await asyncio.wait([task], timeout=max(until - loop.time(), 0))
            if not done or task.cancelled() or task.exception() is not None or task.result() is not None:
                return
        # Lo esta corriendo otro (el loop, o una aceptacion anterior).
        while loop.time() < until:
            with self.sessions() as s:
                if s.get(ConversationRow, conversation_id).post_call_status != "running":
                    return
            await asyncio.sleep(POST_CALL_POLL_SECONDS)

    async def _contact_text(self, thread: WaThread, area: HandoffArea | None, member: TeamMember | None,
                            summary: str | None = None) -> str:
        """(c) Un solo texto, armado siempre desde la base: la nota del post-call, o su falla, mas el contacto. Si no
        entra, se recorta la nota: el telefono llega siempre."""
        conversation_id = thread.conversation_id
        if summary is None:
            summary = await self._summary(conversation_id, settings.post_call_wait_seconds)
        texts, values = self._texts(thread, area, member, resumen=summary)
        with self.sessions() as s:
            row = s.get(ConversationRow, conversation_id)
            note, status = row.post_call_note, row.post_call_status
        if not note and self._post_call_tool(conversation_id) is not None and status != "done":
            note = handoff.render(texts["post_call_failed"], **values)
        contact = handoff.render(texts["operator_contact"], **values)
        limit = settings.wa_max_reply_chars
        if note:
            contact = f"{note[:max(limit - len(contact) - 2, 0)]}\n\n{contact}"
        return contact[:limit]

    async def _delivery_failed(self, thread: WaThread, lease: datetime.datetime, reason: str) -> None:
        """A quien le toca ahora, en orden: otro operador que ya toco y perdio; sin hora de cierre, el tramo que este toque
        desplazo, si sigue vigente; si no, la rotacion sigue con la siguiente persona. Si ya habia terminado, vuelve a
        `closed` con su mismo tope, sin repetirle el mensaje a la persona. El reenvio termina porque deja de estar
        `accepted`. Cada falla deja su tramo en `failed`: no hay bucle. Un post-call `done` no se repite."""
        where = (WaThread.handoff_status.in_(("delivering", "accepted")), WaThread.handoff_deadline == lease)
        conversation_id = thread.conversation_id
        reset = {"handoff_delivery_tries": 0, "handoff_retakes": 0}
        tapped = self._other_leg(thread, HandoffLeg.answered_at.is_not(None),
                                 HandoffLeg.result.not_in(("failed", "connected")), order=HandoffLeg.answered_at)
        shifted = None
        if tapped is None and thread.handoff_closed_at is None:
            shifted = self._other_leg(thread, HandoffLeg.answered_at.is_(None), HandoffLeg.result == "whatsapp_sent",
                                      HandoffLeg.wamid.is_not(None), order=HandoffLeg.created_at.desc())
        until = self._leg_until(shifted) if shifted is not None else None
        fresh = None
        if tapped is not None:
            fresh = utcnow() + DELIVERY_LEASE
            values = {"handoff_status": "delivering", "handoff_leg_id": tapped.id, "handoff_area_id": tapped.area_id,
                      "handoff_deadline": fresh}
        elif until is not None and until > utcnow():
            values = {"handoff_status": "waiting", "handoff_leg_id": shifted.id, "handoff_area_id": shifted.area_id,
                      "handoff_deadline": until}
        elif thread.handoff_closed_at is None:
            fresh = utcnow() + SENDING_LEASE
            values = {"handoff_status": "sending", "handoff_deadline": fresh}
            if shifted is not None and shifted.area_id:
                values["handoff_area_id"] = shifted.area_id
        else:
            late = datetime.timedelta(minutes=settings.wa_handoff_late_minutes)
            values = {"handoff_status": "closed", "handoff_deadline": thread.handoff_closed_at + late}
        if not self._move(conversation_id, *where, **values, **reset):
            return
        self._update_leg(thread.handoff_leg_id, result="failed", connected_at=None)
        self._event(thread, "handoff.whatsapp_failed", area_id=thread.handoff_area_id, reason=reason)
        if tapped is not None:
            self._event(thread, "handoff.confirmed", area_id=tapped.area_id, member_id=tapped.team_member_id,
                        actor="person")
            await self._deliver(conversation_id, fresh)
        elif fresh is not None:
            if shifted is not None:
                await self._leg_expired(conversation_id, shifted.id)
            await self._advance(conversation_id, fresh)

    def _other_leg(self, thread: WaThread, *where, order):
        """El primer tramo de esta rotacion, sin contar el vigente, que cumple where."""
        with self.sessions() as s:
            return s.execute(select(HandoffLeg.id, HandoffLeg.area_id, HandoffLeg.team_member_id, HandoffLeg.created_at)
                             .where(HandoffLeg.conversation_id == thread.conversation_id,
                                    HandoffLeg.created_at >= thread.handoff_started_at,
                                    HandoffLeg.id != thread.handoff_leg_id, *where)
                             .order_by(order).limit(1)).first()

    def _leg_until(self, leg) -> datetime.datetime | None:
        """Hasta cuando espera el toque de un tramo; None si su area ya no existe."""
        with self.sessions() as s:
            area = s.get(HandoffArea, leg.area_id) if leg.area_id else None
            if area is None:
                return None
            wait = (area.whatsapp or {}).get("wait_seconds") or handoff.WAIT_SECONDS_DEFAULT
            return leg.created_at + datetime.timedelta(seconds=wait)

    # --- Reenvio ---

    async def relay(self, conversation_id: str, conversation_text: str, relay_text: str, voice_note: bool) -> None:
        """Lo que escribe la persona, al operador y a la conversacion, sin el modelo. Corre bajo el lock del contacto."""
        thread = self._thread(conversation_id)
        self._append(conversation_id, "user", conversation_text, voice_note)
        leg, member, area = self._leg_info(thread)
        with self.sessions() as s:
            info = self.service.account_info(s, (area.whatsapp or {}).get("account_id") if area else None,
                                             thread.client_id)
        if leg is None or member is None or not member.active or info is None:
            await self._relay_failed(thread, "no_route", locked=True)
            return
        header = " · ".join(x for x in (thread.contact_name, f"+{thread.wa_id}") if x)
        body = f"*{header}*\n{relay_text}"[:settings.wa_max_reply_chars]
        if not await self.service.send_team(info, wa_routing.digits(leg.phone), conversation_id, body, "team_relay"):
            await self._relay_failed(thread, "rejected", locked=True)

    async def _relay_failed(self, thread: WaThread, reason: str, *, locked: bool = False) -> None:
        """Termina el reenvio: el siguiente mensaje va a la IA, que puede derivar otra vez. La persona se entera."""
        now = utcnow()
        if not self._move(thread.conversation_id, WaThread.handoff_status == "accepted",
                          WaThread.handoff_deadline > now, handoff_deadline=now):
            return
        leg, member, area = self._leg_info(thread)
        self._event(thread, "handoff.relay_failed", area_id=area.id if area else None,
                    member_id=leg.team_member_id if leg is not None else None, reason=reason)
        texts, values = self._texts(thread, area, member)
        await self._tell(thread, handoff.render(texts["relay_failed"], **values), locked=locked)

    # --- Status failed de Meta ---

    async def on_failed(self, account_id: str, wamid: str) -> None:
        """Una plantilla o un texto al equipo que Meta no pudo entregar. El mensaje tiene que ser de esta cuenta."""
        with self.sessions() as s:
            msg = s.scalar(select(WaMessage).where(WaMessage.wamid == wamid))
            if msg is None or msg.account_id != account_id or msg.direction != "out":
                return
            kind, conversation_id, number, created_at = msg.type, msg.conversation_id, msg.wa_id, msg.created_at
            leg = s.scalar(select(HandoffLeg).where(HandoffLeg.wamid == wamid))
            leg_id, leg_client = (leg.id, leg.client_id) if leg is not None else (None, None)
        if leg_id:
            await self._template_failed(conversation_id, leg_id, leg_client)
        elif conversation_id and kind == "team_relay":
            thread = self._thread(conversation_id)
            if thread is not None:
                await self._relay_failed(thread, "failed")
        elif conversation_id and kind == "team_notice":
            await self._notice_failed(conversation_id, number, created_at)

    async def _template_failed(self, conversation_id: str | None, leg_id: str, client_id: str) -> None:
        thread = self._thread(conversation_id) if conversation_id else None
        if thread is None or thread.client_id != client_id:
            return
        lease = utcnow() + SENDING_LEASE
        if not self._move(conversation_id, WaThread.handoff_status == "waiting", WaThread.handoff_leg_id == leg_id,
                          handoff_status="sending", handoff_deadline=lease):
            self._update_leg_if_unanswered(leg_id)
            return
        self._update_leg(leg_id, result="failed")
        await self._advance(conversation_id, lease)

    def _update_leg_if_unanswered(self, leg_id: str) -> None:
        with self.sessions() as s:
            s.execute(update(HandoffLeg).where(HandoffLeg.id == leg_id, HandoffLeg.answered_at.is_(None))
                      .values(result="failed"))
            s.commit()

    async def _notice_failed(self, conversation_id: str, number: str, created_at: datetime.datetime) -> None:
        """(a) o (c) sin entregar: solo si es del operador de esta entrega y de despues de su toque. Un failed despues del
        post-call no deshace el cobro ni el accepted ya dicho. Con `accepted`, un reenvio ya cerrado no se reabre, y un
        envio posterior a ese numero que no fallo quiere decir que el operador tiene los datos."""
        thread = self._thread(conversation_id)
        if thread is None or thread.handoff_status not in ("delivering", "accepted"):
            return
        accepted = thread.handoff_status == "accepted"
        if accepted and thread.handoff_deadline <= utcnow():
            return
        leg, _, _ = self._leg_info(thread)
        if (leg is None or leg.answered_at is None or created_at < leg.answered_at
                or not wa_routing.same_number(leg.phone, number)):
            return
        if accepted and self._later_notice(conversation_id, number, created_at):
            return
        await self._delivery_failed(thread, thread.handoff_deadline, "failed")

    def _later_notice(self, conversation_id: str, number: str, created_at: datetime.datetime) -> bool:
        with self.sessions() as s:
            sent = s.scalars(select(WaMessage.wa_id).where(
                WaMessage.conversation_id == conversation_id, WaMessage.direction == "out",
                WaMessage.type == "team_notice", WaMessage.status != "failed", WaMessage.created_at > created_at))
            return any(wa_routing.same_number(other, number) for other in sent)
