"""Transferencia atendida de una llamada a una persona del equipo (docs/features/EQUIPO_TELEFONIA.md).

El agente llama a la herramienta transfer_call con el area (app/llm/platform_tools.py) y el worker:

1. Revisa el area (activa, en horario, con miembros), los minutos salientes del plan y los canales de Anura.
2. Le avisa al cliente (mensaje "transfer" del area, si el LLM no dijo nada) y lo deja en espera con musica.
3. Llama a cada miembro, en orden, con el timbre del area. El cliente no lo escucha.
4. Al atender: mira si es un contestador (STT de los primeros segundos y las frases de las campañas) y, en
   paralelo, le pasa el resumen solo a la persona (whisper) y espera el 1. Sin el 1, siguiente miembro.
5. Con el 1, los conecta y se queda escuchando (modo escucha): transcribe y graba cada lado en la
   conversacion, y espera el codigo de vuelta a la IA (return_digits) o que corte alguno.
6. Si nadie atiende o al volver, el agente retoma con el mensaje que corresponda.

Sigue por las rutas del area: `after_hours_area_id` fuera de horario y `no_answer_area_id` si nadie acepto o no se
puede llamar, con la musica sin cortar y el mensaje solo al final. Un area `delivery=whatsapp` no llama: avisa a una
persona, en una tarea propia, que termina aunque el cliente corte. Un area de llamada con `call_template` le manda
ademas un WhatsApp a cada persona, sin demorar el marcado.

`Transfer` es la logica, sin LiveKit; `RoomLine` es el lado de LiveKit (los tests usan un falso). Cada intento
queda en handoff_legs (minutos salientes y canales) y en events (linea de tiempo).
"""
import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
from google.protobuf.duration_pb2 import Duration

from livekit import api, rtc

from ..campaigns.voicemail import VoicemailDetector
from ..config import settings
from ..db import utcnow
from ..models import HandoffArea, HandoffLeg, TeamMember
from ..services import campaign_calls, events, handoff, quota
from ..services.handoff import (  # noqa: F401  (el resumen vive alla; lo usa tambien el texto)
    FALLBACK_SUMMARY,
    SUMMARY_SCHEMA,
    SUMMARY_TIMEOUT,
    summarize,
    summary_messages,
)
from ..whatsapp import team_notify
from .listen import Listener
from .speech_text import to_speech

logger = logging.getLogger("agent.handoff")

# Identidad de la persona en la room: persona-<intento>. El worker no corta la llamada cuando sale una.
PERSON_PREFIX = "persona-"
# Segundos de audio de la persona, desde que atiende, para la deteccion de contestador por STT. El buzon de
# Claro dijo "Bienvenido al buzón de voz Claro" en los primeros 3 s (spike, plan 11.1).
MACHINE_WINDOW_SECONDS = 3.0
# Intentos por llamada (entre todas sus derivaciones): los permisos de las pistas van por identidad.
MAX_ATTEMPTS = 30
# Las pone la derivacion: una variable del pre-call con el mismo nombre no las pisa.
RESERVED_VARS = frozenset({"area", "persona", "cliente", "resumen", "horario"})
# Motivos para seguir por no_answer_area_id, ademas de que nadie acepte.
PASS_ON_REASONS = frozenset({"no_members", "no_channel", "outbound_minutes"})


class CustomerGone(Exception):
    """El cliente corto: se cierra todo."""


@dataclass
class DialResult:
    result: str                 # answered, no_answer, busy, failed
    sip_status: int | None = None
    error: str = ""


class Line(Protocol):
    """El lado telefonico de la transferencia (RoomLine en LiveKit; un falso en los tests).

    events: ("dtmf", identidad, digito), ("left", identidad), ("text", identidad, texto, pcm16k)."""
    events: asyncio.Queue

    async def say(self, text: str, interruptible: bool = False) -> None: ...   # al cliente, con la voz del agente
    async def hold(self, on: bool) -> None: ...                    # musica de espera, solo al cliente
    async def dial(self, identity: str, phone: str, ring_seconds: int) -> DialResult: ...
    async def first_words(self, identity: str, seconds: float) -> str: ...   # STT de lo primero que se oye
    async def whisper(self, identity: str, text: str) -> None: ...  # solo a la persona; vuelve al terminar
    async def stop_whisper(self) -> None: ...
    async def connect(self, identity: str) -> None: ...            # cliente y persona se escuchan
    async def listen(self, identity: str) -> None: ...             # transcribe a los dos (eventos "text")
    async def remove(self, identity: str) -> None: ...
    async def resume(self) -> None: ...                            # vuelve el agente: permisos y entrada de audio


@dataclass
class Outcome:
    """Como termino la transferencia: para el worker y los tests."""
    status: str                 # connected, notified, unavailable, failed
    result: str = ""            # el del ultimo intento, o el motivo si no se intento
    ended: str = ""             # conectada: returned_to_ai, person_hung_up, customer_hung_up, quota
    legs: list[str] = field(default_factory=list)
    member_id: str | None = None   # conectada o avisada: la persona


@dataclass
class TeamRing:
    """Las personas de un numero en una entrante directa (app/voice/direct.py): como un area, sin agente detras
    (sin codigo de vuelta a la IA ni mensajes de vuelta)."""
    name: str
    ring_seconds: int
    id: str | None = None
    return_digits: str = ""
    on_person_hangup: str = "end"
    whatsapp: dict | None = None


@dataclass
class _Step:
    """Un area de la cadena, leida de la base: lo que hace falta sin volver a abrir una sesion."""
    area: HandoffArea | None
    texts: dict
    values: dict
    members: list[TeamMember]
    reason: str | None

    @property
    def notice(self) -> bool:
        return self.area is not None and self.area.delivery == "whatsapp"


def _uses_summary(template_cfg: dict | None) -> bool:
    """Solo se espera el resumen si la plantilla lo lleva."""
    return "resumen" in ((template_cfg or {}).get("params") or [])


class Transfer:
    """Una transferencia de la llamada `conversation_id` a un area. on_message(role, text, person, leg, pcm)
    agrega a la conversacion; hang_up(reason) corta la llamada (el area se despide al cortar la persona).
    get_vars() da las variables del pre-call, leidas en cada area; spawn_notice(coro) corre un aviso en una tarea que
    sobrevive a la derivacion y que el worker espera al cerrar."""

    def __init__(self, *, sessions, line: Line | None, conversation_id: str, client_id: str, areas: list[dict],
                 customer: str, caller: str = "", summary=None, on_message=None, hang_up=None,
                 hold_music: bool = True, confirm_seconds: int | None = None, first_attempt: int = 0,
                 on_connected=None, limit=None, get_vars=None, spawn_notice=None):
        self.sessions = sessions
        self.line = line
        self.conversation_id = conversation_id
        self.client_id = client_id
        self.areas = areas
        self.customer = customer             # identidad del cliente en la room
        self.caller = caller                 # su numero, para {{cliente}}
        self.summary = summary               # corrutina sin argumentos que devuelve el resumen, o None
        self.on_message = on_message or (lambda *a, **k: None)
        self.hang_up = hang_up
        self.on_connected = on_connected     # on_connected(member): la persona quedo conectada con el cliente
        self.hold_music = hold_music
        # limit() -> motivo de corte o None, con la persona conectada: la entrante directa no tiene el
        # quota_watchdog del worker (minutos entrantes y duracion: app/voice/direct.py, TeamCall._limit).
        self.limit = limit
        self.confirm_seconds = settings.handoff_confirm_seconds if confirm_seconds is None else confirm_seconds
        # Intentos de la llamada (la identidad persona-<n> no se repite entre derivaciones de la misma llamada).
        self.attempt = first_attempt
        self._open_leg: str | None = None
        self.get_vars = get_vars
        self.spawn_notice = spawn_notice or self._own_task
        self._tasks: list[asyncio.Task] = []
        self._summary_task: asyncio.Task | None = None
        self._summary_shared = False         # lo espera un aviso: no se cancela al terminar la derivacion
        self._complemented: set[str] = set()   # a quienes ya les salio el WhatsApp de esta derivacion

    # ---------- registro ----------

    def _event(self, type: str, *, area_id: str | None = None, member_id: str | None = None,
               actor: str = "system", **data) -> None:
        with self.sessions() as s:
            events.record(s, self.client_id, type, conversation_id=self.conversation_id, actor=actor,
                          area_id=area_id, team_member_id=member_id, **data)
            s.commit()

    def _new_leg(self, area: HandoffArea | TeamRing, member: TeamMember) -> str:
        with self.sessions() as s:
            leg = HandoffLeg(client_id=self.client_id, conversation_id=self.conversation_id, area_id=area.id,
                             team_member_id=member.id, phone=member.phone)
            s.add(leg)
            s.commit()
            self._open_leg = leg.id
            return leg.id

    def _update_leg(self, leg_id: str, **values) -> HandoffLeg:
        with self.sessions() as s:
            leg = s.get(HandoffLeg, leg_id)
            for k, v in values.items():
                setattr(leg, k, v)
            if values.get("ended_at") is not None:
                self._open_leg = None
                if leg.answered_at:   # Anura cobra desde que atiende, acepte o no
                    leg.billed_seconds = quota.elapsed_seconds((leg.ended_at - leg.answered_at).total_seconds())
            s.commit()
            s.refresh(leg)
            s.expunge(leg)
            return leg

    def close(self) -> None:
        """Al terminar la llamada con un tramo abierto (corto el cliente, se cayo el worker)."""
        if self._open_leg is not None:
            self._update_leg(self._open_leg, ended_at=utcnow())

    # ---------- flujo ----------

    def _variables(self) -> dict:
        """Las del pre-call, sin las reservadas. Una falla aca no frena la derivacion: se oye sin ese dato."""
        if self.get_vars is None:
            return {}
        try:
            return {k: "" if v is None else v for k, v in (self.get_vars() or {}).items() if k not in RESERVED_VARS}
        except Exception:
            logger.exception("derivacion %s: sin variables", self.conversation_id)
            return {}

    def _load(self, area_id: str | None, area_name: str) -> _Step:
        """Lee un area y dice si se puede usar ahora."""
        variables = self._variables()
        with self.sessions() as s:
            area = s.get(HandoffArea, area_id) if area_id else None
            if area is not None and area.client_id != self.client_id:
                area = None
            texts = handoff.messages(area) if area else handoff.DEFAULT_MESSAGES
            values = {**variables, "area": area.name if area else area_name, "cliente": self.caller,
                      "horario": handoff.describe_schedule(area.schedule) if area else ""}
            reason = None
            if area is None or not area.active:
                reason = "unknown_area"
            elif not handoff.is_open(area.schedule):
                reason = "after_hours"
            members = []
            if reason is None and area.delivery != "whatsapp":
                members = handoff.candidates(s, area)
                if not members:
                    reason = "no_members"
                if reason is None:
                    reason = quota.handoff_check(s, self.client_id)
                if reason is None and self.attempt + len(members) > MAX_ATTEMPTS:
                    reason = "too_many_attempts"
            if area is not None:
                s.expunge(area)
                for m in members:
                    s.expunge(m)
        return _Step(area, texts, values, members, reason)

    def _route(self, area: HandoffArea | None, key: str, visited: set[str]) -> tuple[str, str, bool] | None:
        """El area siguiente: (id, nombre, si es de aviso), o None si no hay, ya paso por ella (un ciclo se corta aca)
        o no sirve: inactiva o de otro cliente, aunque la base lo diga."""
        target_id = getattr(area, key) if area is not None else None
        if not target_id or target_id in visited:
            return None
        with self.sessions() as s:
            target = s.get(HandoffArea, target_id)
            if target is None or target.client_id != self.client_id or not target.active:
                logger.warning("derivacion %s: ruta %s ignorada", self.conversation_id, key)
                return None
            return target.id, target.name, target.delivery == "whatsapp"

    def _unavailable(self, step: _Step, name: str) -> None:
        """Quedo sin atender por un motivo: un area de aviso nunca fue un pedido de derivacion (no suma en reportes)."""
        area_id = step.area.id if step.area else None
        logger.info("derivacion %s a %r: no se intenta (%s)", self.conversation_id, name, step.reason)
        if step.notice:
            self._event("handoff.whatsapp_failed", area_id=area_id, reason=step.reason)
        else:
            self._event("handoff.unavailable", area_id=area_id, actor="agent", area=step.values["area"],
                        reason=step.reason)

    def _rerouted(self, step: _Step, route: tuple[str, str, bool], reason: str) -> None:
        """Un pase a otra area de llamada no suma por esta en los reportes. A un area de aviso no es un pase: el
        pedido quedo sin atender y esta area lo cuenta."""
        if not route[2]:
            self._event("handoff.rerouted", area_id=step.area.id, actor="agent", area=step.values["area"],
                        to=route[1], reason=reason)
        elif step.reason is not None:
            self._unavailable(step, step.values["area"])

    async def run(self, area_name: str, *, announced: bool = False) -> Outcome:
        """announced: el LLM ya dijo algo al derivar (no se repite el aviso del area)."""
        snap = handoff.find_area(self.areas, area_name)
        area_id, name = (snap["id"] if snap else None), area_name
        visited: set[str] = set()
        told = announced
        holding = False
        outcome = Outcome("failed")
        try:
            while True:
                step = self._load(area_id, name)
                area, texts, values = step.area, step.texts, step.values
                if area is not None:
                    visited.add(area.id)
                if step.reason is not None:
                    key = ("after_hours_area_id" if step.reason == "after_hours"
                           else "no_answer_area_id" if step.reason in PASS_ON_REASONS else "")
                    route = self._route(area, key, visited) if key else None
                    if route is not None:
                        self._rerouted(step, route, step.reason)
                        area_id, name = route[0], route[1]
                        continue
                    self._unavailable(step, name)
                    if holding:
                        await self._stop_hold(area.id if area else None)
                    await self._back(texts["after_hours" if step.reason == "after_hours" else "no_answer"], values)
                    outcome.status, outcome.result = "unavailable", step.reason
                    return outcome
                if step.notice:
                    notice = await self._until(asyncio.shield(self.spawn_notice(self._notify(area, values))))
                    if notice.ok:
                        if holding:
                            await self._stop_hold(area.id)
                        await self._back(texts["notified"], values | {"persona": self._member_name(notice.member_id)})
                        outcome.status, outcome.result, outcome.member_id = "notified", "notified", notice.member_id
                        return outcome
                    route = self._route(area, "no_answer_area_id", visited)
                    if route is not None:
                        self._rerouted(step, route, "no_answer")
                        area_id, name = route[0], route[1]
                        continue
                    if holding:
                        await self._stop_hold(area.id)
                    await self._back(texts["no_answer"], values)
                    outcome.status, outcome.result = "unavailable", "no_answer"
                    return outcome

                self._event("handoff.requested", area_id=area.id, actor="agent", area=area.name,
                            members=len(step.members))
                if not told:
                    told = True
                    await self._say(handoff.render(texts["transfer"], **values))
                summary = self._shared_summary()
                if self.hold_music and not holding:
                    holding = True
                    await self.line.hold(True)
                    self._event("hold.started", area_id=area.id)
                for member in step.members:
                    result, leg_id, identity = await self._attempt(area, member, texts, values, summary)
                    outcome.legs.append(leg_id)
                    outcome.result = result
                    if result == "confirmed":
                        await self._stop_hold(area.id)
                        outcome.status = "connected"
                        outcome.ended = await self._connected(area, member, leg_id, identity, texts, values)
                        return outcome
                route = self._route(area, "no_answer_area_id", visited)
                if route is not None:
                    self._rerouted(step, route, outcome.result)
                    area_id, name = route[0], route[1]
                    continue
                await self._stop_hold(area.id)
                await self._back(texts["busy" if outcome.result == "busy" else "no_answer"], values)
                return outcome
        finally:
            if self._summary_task is not None and not self._summary_shared:
                self._summary_task.cancel()

    async def notify_only(self, area_name: str) -> team_notify.Notice | None:
        """El cliente ya corto: sale el aviso de un area de aviso, siguiendo sus rutas. Un area de llamada termina aca,
        como si no hubiera derivacion: no hay nadie a quien conectar."""
        snap = handoff.find_area(self.areas, area_name)
        area_id, name = (snap["id"] if snap else None), area_name
        visited: set[str] = set()
        while True:
            step = self._load(area_id, name)
            if not step.notice:
                return None
            visited.add(step.area.id)
            if step.reason is None:
                notice = await self._notify(step.area, step.values)
                if notice.ok:
                    return notice
                route = self._route(step.area, "no_answer_area_id", visited)
            else:
                self._unavailable(step, name)
                route = self._route(step.area, "after_hours_area_id", visited) if step.reason == "after_hours" else None
            if route is None:
                return None
            area_id, name = route[0], route[1]

    def _own_task(self, coro) -> asyncio.Task:
        """Sin worker (entrante directa, tests): la tarea queda referenciada aca."""
        task = asyncio.create_task(coro)
        self._tasks.append(task)
        return task

    def _shared_summary(self) -> asyncio.Task:
        """El resumen de la derivacion: uno solo, para el whisper y las plantillas."""
        if self._summary_task is None:
            self._summary_task = asyncio.create_task(self._summary())
        return self._summary_task

    async def _notify(self, area: HandoffArea, values: dict) -> team_notify.Notice:
        """El aviso de un area: una persona, sin aceptacion. Corre en su tarea."""
        if _uses_summary((area.whatsapp or {}).get("template")):
            self._summary_shared = True
            values = values | {"resumen": await self._shared_summary()}
        return await team_notify.notify_area(self.sessions, self.client_id, area.id, values, self.conversation_id)

    async def _complement(self, area: HandoffArea, member: TeamMember, template_cfg: dict, values: dict,
                          summary: asyncio.Task) -> None:
        if _uses_summary(template_cfg):
            values = values | {"resumen": await summary}
        await team_notify.send(self.sessions, self.client_id, area, member, template_cfg, values, self.conversation_id)

    def _spawn_complement(self, area: HandoffArea | TeamRing, member: TeamMember, values: dict,
                          summary: asyncio.Task) -> None:
        """WhatsApp que acompaña la llamada, una vez por persona. send registra member_not_notified como falla: sin el
        toggle no se lo llama, o quedaria una falla por cada tramo."""
        template_cfg = (area.whatsapp or {}).get("call_template")
        if not template_cfg or not member.whatsapp_notify or member.id in self._complemented:
            return
        self._complemented.add(member.id)
        if _uses_summary(template_cfg):
            self._summary_shared = True
        self.spawn_notice(self._complement(area, member, template_cfg, values, summary))

    def _member_name(self, member_id: str | None) -> str:
        with self.sessions() as s:
            member = s.get(TeamMember, member_id) if member_id else None
            return member.name if member else ""

    async def run_team(self, team: TeamRing, members: list[TeamMember], whisper: str, values: dict) -> Outcome:
        """Entrante directa: las personas en sus celulares, en orden, con el whisper `whisper` y el 1 para atender.
        La musica de espera y lo que pasa si nadie atiende los maneja app/voice/direct.py; al conectar se corta la
        musica. Conectada, termina cuando corta alguno (no hay agente al que volver)."""
        with self.sessions() as s:
            reason = quota.handoff_check(s, self.client_id)
        if reason is None and self.attempt + len(members) > MAX_ATTEMPTS:
            reason = "too_many_attempts"
        if reason is not None:
            logger.info("directa %s: no se llama a los celulares (%s)", self.conversation_id, reason)
            self._event("handoff.unavailable", area=team.name, reason=reason)
            return Outcome("unavailable", reason)
        texts = handoff.DEFAULT_MESSAGES | {"whisper": whisper}
        summary = asyncio.create_task(self._summary())
        outcome = Outcome("failed")
        try:
            for member in members:
                result, leg_id, identity = await self._attempt(team, member, texts, values, summary)
                outcome.legs.append(leg_id)
                outcome.result = result
                if result == "confirmed":
                    if self.hold_music:
                        await self.line.hold(False)
                    outcome.status, outcome.member_id = "connected", member.id
                    outcome.ended = await self._connected(team, member, leg_id, identity, texts, values)
                    return outcome
            return outcome
        finally:
            summary.cancel()

    async def _stop_hold(self, area_id: str | None) -> None:
        if self.hold_music:
            await self.line.hold(False)
            self._event("hold.ended", area_id=area_id)

    async def _summary(self) -> str:
        if self.summary is None:
            return FALLBACK_SUMMARY
        try:
            return (await asyncio.wait_for(self.summary(), SUMMARY_TIMEOUT)).strip() or FALLBACK_SUMMARY
        except Exception:
            logger.exception("derivacion %s: sin resumen para el whisper", self.conversation_id)
            return FALLBACK_SUMMARY

    async def _attempt(self, area: HandoffArea | TeamRing, member: TeamMember, texts: dict, values: dict,
                       summary: asyncio.Task) -> tuple[str, str, str]:
        """Un miembro: (resultado, tramo, identidad). confirmed, no_answer, busy, failed, machine o not_confirmed."""
        self.attempt += 1
        identity = f"{PERSON_PREFIX}{self.attempt}"
        leg_id = self._new_leg(area, member)
        ids = {"area_id": area.id, "member_id": member.id}
        self._event("handoff.dialing", **ids, attempt=self.attempt, person=member.name)
        self._spawn_complement(area, member, values, summary)
        dial = asyncio.create_task(self.line.dial(identity, member.phone, area.ring_seconds))
        try:
            res = await self._until(dial)
        except CustomerGone:
            await self.line.remove(identity)
            self._update_leg(leg_id, result="failed", ended_at=utcnow())
            raise
        if res.result != "answered":
            self._update_leg(leg_id, result=res.result, sip_status=res.sip_status, ended_at=utcnow())
            self._event(f"handoff.{res.result}", **ids, sip_status=res.sip_status, error=res.error[:200])
            return res.result, leg_id, identity
        self._update_leg(leg_id, answered_at=utcnow())
        self._event("handoff.answered", **ids, actor="person")
        try:
            result = await self._confirm(identity, texts, values | {"persona": member.name}, summary)
        except CustomerGone:
            await self.line.remove(identity)
            self._update_leg(leg_id, result="failed", ended_at=utcnow())
            raise
        if result != "confirmed":
            await self.line.remove(identity)
            self._update_leg(leg_id, result=result, ended_at=utcnow())
            self._event(f"handoff.{result}", **ids)
        return result, leg_id, identity

    async def _until(self, task: asyncio.Task):
        """Espera la tarea; si mientras tanto corta el cliente, la cancela y levanta CustomerGone. Los demas
        eventos se descartan (antes de atender no hay DTMF ni voz que importe)."""
        while True:
            get = asyncio.create_task(self.line.events.get())
            done, _ = await asyncio.wait({task, get}, return_when=asyncio.FIRST_COMPLETED)
            if get in done:
                ev = get.result()
                if ev[0] == "left" and ev[1] == self.customer:
                    task.cancel()
                    raise CustomerGone()
            else:
                get.cancel()
            if task in done:
                return task.result()

    async def _confirm(self, identity: str, texts: dict, values: dict, summary: asyncio.Task) -> str:
        """Contestador en paralelo con el whisper; despues del whisper, confirm_seconds para marcar 1."""
        detector = VoicemailDetector()
        machine = asyncio.create_task(self.line.first_words(identity, MACHINE_WINDOW_SECONDS))
        await self.line.listen(identity)
        text = handoff.render(texts["whisper"], **(values | {"resumen": await summary}))
        whisper = asyncio.create_task(self.line.whisper(identity, text))
        deadline: float | None = None
        checked = False
        try:
            while True:
                if deadline is None and whisper.done():
                    deadline = time.monotonic() + self.confirm_seconds
                if not checked and machine.done():
                    checked = True
                    heard = machine.result() if not machine.cancelled() and machine.exception() is None else ""
                    if detector.feed(heard or "", True):
                        logger.info("derivacion %s: contestador (%r)", self.conversation_id, heard)
                        return "machine"
                timeout = 0.2 if deadline is None else max(0.0, deadline - time.monotonic())
                if deadline is not None and timeout == 0:
                    return "not_confirmed"
                try:
                    ev = await asyncio.wait_for(self.line.events.get(), min(timeout, 0.2))
                except asyncio.TimeoutError:
                    continue
                kind, who = ev[0], ev[1]
                if kind == "left" and who == self.customer:
                    raise CustomerGone()
                if who != identity:
                    continue
                if kind == "left":
                    return "not_confirmed"
                if kind == "dtmf":
                    return "confirmed" if ev[2] == "1" else "not_confirmed"
                if kind == "text" and detector.feed(ev[2], True):
                    return "machine"
        finally:
            machine.cancel()
            if not whisper.done():
                await self.line.stop_whisper()
                whisper.cancel()

    async def _connected(self, area: HandoffArea | TeamRing, member: TeamMember, leg_id: str, identity: str,
                         texts: dict, values: dict) -> str:
        """Modo escucha hasta que vuelve la IA o corta alguno. Devuelve como termino."""
        ids = {"area_id": area.id, "member_id": member.id}
        self._event("handoff.confirmed", **ids, actor="person")
        await self.line.connect(identity)
        self._update_leg(leg_id, result="connected", connected_at=utcnow())
        if area.id is not None:
            with self.sessions() as s:
                if (row := s.get(HandoffArea, area.id)) is not None:
                    row.last_member_id = member.id
                    s.commit()
        if self.on_connected is not None:
            self.on_connected(member)
        self._event("handoff.connected", **ids, person=member.name)
        digits = ""
        ended = ""
        next_check = time.monotonic() + settings.quota_check_seconds
        try:
            while not ended:
                try:
                    ev = await asyncio.wait_for(self.line.events.get(), max(0.1, next_check - time.monotonic()))
                except asyncio.TimeoutError:
                    next_check = time.monotonic() + settings.quota_check_seconds
                    with self.sessions() as s:
                        if quota.handoff_check(s, self.client_id) == "outbound_minutes":
                            ended = "quota"
                    if not ended and self.limit is not None:
                        ended = self.limit() or ""
                    continue
                kind, who = ev[0], ev[1]
                if kind == "left" and who == self.customer:
                    ended = "customer_hung_up"
                elif kind == "left" and who == identity:
                    ended = "person_hung_up"
                elif kind == "dtmf" and who == identity and area.return_digits:
                    digits = (digits + ev[2])[-len(area.return_digits):]
                    if digits == area.return_digits:
                        ended = "returned_to_ai"
                elif kind == "text" and who in (identity, self.customer):
                    person = member.name if who == identity else None
                    self.on_message("assistant" if person else "user", ev[2], person=person, leg=leg_id,
                                    pcm=ev[3] if len(ev) > 3 else None)
        finally:
            if ended != "person_hung_up":
                await self.line.remove(identity)
            leg = self._update_leg(leg_id, ended_at=utcnow())
            self._event("handoff.ended", **ids, reason=ended or "worker_stopped", seconds=leg.billed_seconds)
        if ended == "customer_hung_up":
            return ended
        if ended == "returned_to_ai":
            self._event("handoff.returned_to_ai", **ids, actor="person")
        elif ended == "person_hung_up":
            self._event("handoff.person_hung_up", **ids, actor="person")
        if area.id is None:     # entrante directa: no hay agente que vuelva ni se despida
            return ended
        if ended == "person_hung_up" and area.on_person_hangup == "end":
            await self._back(texts["goodbye"], values)
            if self.hang_up is not None:
                await self.hang_up("person_hung_up")
            return ended
        await self._back(texts["resume"], values)
        return ended

    async def _say(self, text: str, interruptible: bool = False) -> None:
        self.on_message("assistant", text)
        await self.line.say(text, interruptible=interruptible)

    async def _back(self, text: str, values: dict) -> None:
        """Vuelve el agente: el texto queda en la conversacion (el LLM lo ve en el turno siguiente). Se puede
        interrumpir: sin interrupciones, LiveKit descarta lo que dice la persona encima (discard_audio_if_uninterruptible)
        y un pedido hecho durante el aviso se perdia."""
        await self.line.resume()
        await self._say(handoff.render(text, **values), interruptible=True)


# ---------- LiveKit ----------

HOLD_SAMPLE_RATE = 48000


class Speaker:
    """Una pista propia del agente; play() la ocupa hasta terminar o hasta stop(). Se corta con una bandera
    entre frames: cancelar la tarea en medio de capture_frame deja el AudioSource en InvalidState (spike)."""

    def __init__(self, name: str, sample_rate: int):
        self.sample_rate = sample_rate
        self.source = rtc.AudioSource(sample_rate, 1)
        self.track = rtc.LocalAudioTrack.create_audio_track(name, self.source)
        self.sid = ""
        self._task: asyncio.Task | None = None
        self._stopping = False

    async def publish(self, room: rtc.Room) -> None:
        pub = await room.local_participant.publish_track(
            self.track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))
        self.sid = pub.sid

    async def _run(self, pcm: bytes, loop: bool) -> None:
        step = self.sample_rate // 100 * 2   # 10 ms de 16 bits
        while not self._stopping:
            for i in range(0, len(pcm) - step + 1, step):
                if self._stopping:
                    return
                await self.source.capture_frame(rtc.AudioFrame(pcm[i:i + step], self.sample_rate, 1, step // 2))
            if not loop:
                break
        if not self._stopping:
            await self.source.wait_for_playout()

    async def play(self, pcm: bytes, loop: bool = False) -> asyncio.Task:
        await self.stop()
        self._stopping = False
        self._task = asyncio.create_task(self._run(pcm, loop))
        return self._task

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._stopping = True
            await self._task
            self.source.clear_queue()


async def _decode(path: str, volume: float) -> bytes:
    from livekit.agents.utils.audio import audio_frames_from_file

    pcm = bytearray()
    async for frame in audio_frames_from_file(path, sample_rate=HOLD_SAMPLE_RATE, num_channels=1):
        pcm.extend(frame.data)
    samples = np.frombuffer(bytes(pcm), dtype=np.int16).astype(np.float32) * volume
    return np.clip(samples, -32768, 32767).astype(np.int16).tobytes()


def hold_music_path(track: str) -> str:
    if track != "default" and (path := settings.hold_music_dir / f"{track}.ogg").is_file():
        return str(path)
    from livekit.agents.voice.background_audio import BuiltinAudioClip

    return BuiltinAudioClip.HOLD_MUSIC.path()


class RoomLine:
    """La transferencia sobre la room de la llamada: la persona entra como participante SIP saliente por el
    trunk de Anura. Pistas por destinatario (set_track_subscription_permissions): la voz del agente y la musica
    solo al cliente, el whisper solo a la persona; cliente y persona no se escuchan (update_subscriptions)
    hasta connect()."""

    def __init__(self, ctx, session, *, customer: str, trunk_id: str, caller_id: str, hold_music,
                 max_call_seconds: int):
        self.ctx = ctx
        self.room: rtc.Room = ctx.room
        self.session = session
        self.customer = customer
        self.trunk_id = trunk_id
        self.caller_id = caller_id
        self.hold_cfg = hold_music
        self.max_call_seconds = max_call_seconds
        self.events: asyncio.Queue = asyncio.Queue()
        self.persons: set[str] = set()
        self.tracks: dict[str, str] = {}          # identidad -> sid de su pista de audio
        # Captura y transcripcion (app/voice/listen.py): cada frase es un evento "text". Guarda el audio de las
        # personas (deteccion de contestador); el del cliente va solo al VAD.
        self.listener = Listener(session.vad, session.stt,
                                 lambda who, text, pcm: self.events.put_nowait(("text", who, text, pcm)))
        self.audio = self.listener.audio          # identidad -> audio a 16 kHz desde que se suscribio
        self.listening = self.listener.listening
        self.tasks: list[asyncio.Task] = []
        self.hold_speaker: Speaker | None = None
        self.whisper_speaker: Speaker | None = None
        self._hold_pcm: bytes | None = None
        self._agent_tracks: list[str] = []
        self._handlers: list[tuple[str, object]] = []
        self._started = False

    # -- eventos de la room --

    def _on_dtmf(self, ev) -> None:
        if ev.participant is not None:
            self.events.put_nowait(("dtmf", ev.participant.identity, ev.digit))

    def _on_left(self, p) -> None:
        self.events.put_nowait(("left", p.identity))

    def _on_published(self, pub, p) -> None:
        if pub.kind == rtc.TrackKind.KIND_AUDIO:
            self.tracks[p.identity] = pub.sid
            if p.identity in self.persons:
                # La persona entra a la room al empezar a sonar: se aisla ya, no al atender (spike, plan 11.1).
                self.tasks.append(asyncio.create_task(self._isolate(p.identity)))

    def _on_joined(self, p) -> None:
        self.events.put_nowait(("joined", p.identity))

    def _on_subscribed(self, track, pub, p) -> None:
        # Todas las pistas de audio remotas: el cliente, las personas y, en las directas, el usuario del panel.
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            self.listener.capture(track, p.identity)

    async def _subscribe(self, who: str, other: str, on: bool) -> None:
        if other in self.tracks:
            await self.ctx.api.room.update_subscriptions(api.UpdateSubscriptionsRequest(
                room=self.room.name, identity=who, track_sids=[self.tracks[other]], subscribe=on))

    async def _isolate(self, identity: str) -> None:
        try:
            await self._subscribe(identity, self.customer, False)
            await self._subscribe(self.customer, identity, False)
        except Exception:
            logger.exception("derivacion: no se pudo aislar a %s", identity)

    # -- Line --

    async def start(self) -> None:
        """Pistas propias y permisos, una vez por llamada (la primera derivacion)."""
        if self._started:
            self._apply_permissions()
            return
        self._started = True
        for p in self.room.remote_participants.values():
            for pub in p.track_publications.values():
                if pub.kind == rtc.TrackKind.KIND_AUDIO:
                    self.tracks[p.identity] = pub.sid
        self._agent_tracks = [pub.sid for pub in self.room.local_participant.track_publications.values()]
        self._handlers = [("sip_dtmf_received", self._on_dtmf), ("participant_disconnected", self._on_left),
                          ("participant_connected", self._on_joined), ("track_published", self._on_published),
                          ("track_subscribed", self._on_subscribed)]
        for event, handler in self._handlers:
            self.room.on(event, handler)
        # El audio del cliente ya estaba suscripto (lo escucha la sesion): se captura aparte para el modo escucha.
        for p in self.room.remote_participants.values():
            if p.identity == self.customer:
                for pub in p.track_publications.values():
                    if pub.track is not None and pub.kind == rtc.TrackKind.KIND_AUDIO:
                        self.listener.capture(pub.track, p.identity)
        self.hold_speaker = Speaker("espera", HOLD_SAMPLE_RATE)
        self.whisper_speaker = Speaker("whisper", self.session.tts.sample_rate)
        await self.hold_speaker.publish(self.room)
        await self.whisper_speaker.publish(self.room)
        self._apply_permissions()

    def _apply_permissions(self) -> None:
        to_customer = [*self._agent_tracks, self.hold_speaker.sid]
        perms = [rtc.ParticipantTrackPermission(participant_identity=self.customer, allow_all=False,
                                                allowed_track_sids=to_customer)]
        # Las identidades de las personas se conocen antes de marcar (persona-<n>).
        perms += [rtc.ParticipantTrackPermission(participant_identity=f"{PERSON_PREFIX}{i}", allow_all=False,
                                                 allowed_track_sids=[self.whisper_speaker.sid])
                  for i in range(1, MAX_ATTEMPTS + 1)]
        self.room.local_participant.set_track_subscription_permissions(
            allow_all_participants=False, participant_permissions=perms)

    async def say(self, text: str, interruptible: bool = False) -> None:
        await self.session.say(text, allow_interruptions=interruptible, add_to_chat_ctx=False).wait_for_playout()

    async def hold(self, on: bool) -> None:
        if not on:
            await self.hold_speaker.stop()
            return
        if self._hold_pcm is None:
            self._hold_pcm = await _decode(hold_music_path(self.hold_cfg.track), self.hold_cfg.volume)
        await self.hold_speaker.play(self._hold_pcm, loop=True)

    async def dial(self, identity: str, phone: str, ring_seconds: int) -> DialResult:
        self.persons.add(identity)
        self.listener.keep.add(identity)
        try:
            await self.ctx.api.sip.create_sip_participant(api.CreateSIPParticipantRequest(
                room_name=self.room.name, sip_trunk_id=self.trunk_id, sip_call_to=phone,
                sip_number=self.caller_id, participant_identity=identity, participant_name="Persona del equipo",
                wait_until_answered=True, ringing_timeout=Duration(seconds=ring_seconds),
                max_call_duration=Duration(seconds=self.max_call_seconds)))
        except asyncio.CancelledError:
            await self.remove(identity)
            raise
        except Exception as e:  # noqa: BLE001 - cualquier falla del tramo es un resultado del intento
            result, status = campaign_calls.classify_error(e)
            if result == "failed" and status is None and "timed out" in str(e).lower():
                result = "no_answer"   # el ringing_timeout de LiveKit: "sip request timed out" (spike)
            if result not in ("no_answer", "busy"):
                result = "failed"
            return DialResult(result, status, str(e))
        # Por si la pista ya estaba publicada antes de marcarla como persona.
        await self._isolate(identity)
        return DialResult("answered")

    async def first_words(self, identity: str, seconds: float) -> str:
        start = len(self.audio.get(identity, b""))
        await asyncio.sleep(seconds)
        return await self.listener.recognize_pcm(bytes(self.audio.get(identity, b""))[start:])

    async def whisper(self, identity: str, text: str) -> None:
        pcm = bytearray()
        async with self.session.tts.synthesize(to_speech(text)) as stream:
            async for chunk in stream:
                pcm.extend(chunk.frame.data)
        await (await self.whisper_speaker.play(bytes(pcm)))

    async def stop_whisper(self) -> None:
        await self.whisper_speaker.stop()

    async def connect(self, identity: str) -> None:
        await self._subscribe(identity, self.customer, True)
        await self._subscribe(self.customer, identity, True)

    async def listen(self, identity: str) -> None:
        self.listening |= {identity, self.customer}

    async def remove(self, identity: str) -> None:
        self.listening.discard(identity)
        self.listening.discard(self.customer)
        if identity not in {p.identity for p in self.room.remote_participants.values()}:
            return
        try:
            await self.ctx.api.room.remove_participant(
                api.RoomParticipantIdentity(room=self.room.name, identity=identity))
        except Exception:  # noqa: BLE001 - ya se habia ido: no hay nada que sacar
            logger.info("derivacion: %s ya no estaba en la room", identity)

    async def settle(self, identity: str, timeout: float) -> None:
        """Salio `identity`: espera (hasta `timeout`) su ultima frase (evento "text")."""
        await self.listener.settle(identity, timeout)

    def detach(self) -> None:
        """Deja de escuchar los eventos de la room (la entrante al equipo que sigue con el agente)."""
        for event, handler in self._handlers:
            with contextlib.suppress(Exception):   # ya no estaba
                self.room.off(event, handler)
        self._handlers = []

    async def resume(self) -> None:
        self.room.local_participant.set_track_subscription_permissions(allow_all_participants=True)
        self.session.input.set_audio_enabled(True)

    async def aclose(self) -> None:
        self.listener.close()
        for task in self.tasks:
            task.cancel()
