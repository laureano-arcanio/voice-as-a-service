"""Llamadas directas en el worker (docs/LLAMADAS_DIRECTAS_PLAN.md, 4, 5 y 13): el equipo habla, sin agente ni LLM.

- Saliente (`run_outbound`, metadata `direct`): espera a que el usuario del panel entre a la room
  (`user-<id>`), marca al contacto sin esperar a que atienda (para mostrar dialing/ringing/active en el panel
  por el tema `call_status`) y, al atender, los deja hablando: cada frase de cada uno es un mensaje con su WAV
  (tema `transcript`). Termina cuando sale cualquiera, por el tope de duracion o sin minutos.
- Entrante al equipo (`run_inbound_team`, InboundCall.team de services/calls.start_inbound): musica de espera
  al que llama y suenan las personas del numero segun ring_first: en sus celulares, en orden (Transfer.run_team
  de la derivacion: whisper con la linea y quien llama, 1 para atender) y en el panel (services/direct_calls
  .ring_panel: el primero que atiende entra a la room). Si nadie atiende o esta fuera de horario, el respaldo
  del numero: el agente (sigue el worker con el agente en la misma room), un mensaje y grabar lo que dice el que
  llama (voicemail) o un mensaje y cortar.

`Outbound` y `TeamCall` son la logica, sin LiveKit; `OutboundRoom` y `TeamRoom` el lado de LiveKit (los tests
usan falsos). Las directas graban siempre, sin mirar record_audio (plan, 2).
"""
import asyncio
import contextlib
import json
import logging
import time
import wave
from pathlib import Path
from types import SimpleNamespace
from typing import Protocol

from google.protobuf.duration_pb2 import Duration
from sqlalchemy import func, select

from livekit import api, rtc

from ..config import settings
from ..conversation import recordings
from ..conversation.models import Message
from ..db import utcnow
from ..models import CallRing, CallRow, CallStatus, Client
from ..services import calls as call_service
from ..services import campaign_calls, direct_calls, events
from ..services import handoff as handoff_service
from . import handoff as transfer
from .listen import Listener
from .speech_text import to_speech

logger = logging.getLogger("agent.direct")

CONTACT = "contact"                 # identidad del contacto en la saliente (plan, 13)
# Timbre al contacto en la saliente: lo que suena un celular antes de ir al buzon del operador.
RING_SECONDS = 40
# Margen sobre el timbre por si LiveKit no avisa que se vencio (el contacto nunca sale de la room).
RING_MARGIN_SECONDS = 10
# Motivos con que el usuario corta la saliente antes de que atiendan: la llamada queda cancelada, no fallida.
CANCELLED_REASONS = ("hangup_by_user", "person_hangup")
# El que llama a un numero del equipo y nadie atiende (respaldo voicemail): cuanto se graba como mucho.
VOICEMAIL_SECONDS = 120
# Atendio en el panel (answer) pero su navegador todavia no entro a la room: cuanto mas se lo espera.
PANEL_JOIN_GRACE_SECONDS = 10
# El usuario del panel salio de la room en medio de la llamada (recargo la pagina, se corto la red): cuanto se lo
# espera a que vuelva a entrar ("Volver a entrar", POST /direct-calls/{id}/join) antes de cortar.
PANEL_REJOIN_GRACE_SECONDS = 30
# Salio el otro: cuanto se espera el STT de su ultima frase antes de cerrar.
SETTLE_SECONDS = 3
# Cada cuanto se mira la base mientras suena en el panel (atendio alguien, rechazaron todos).
PANEL_POLL_SECONDS = 0.5
END_SAY_TIMEOUT = 15
RECORDING_NOTICE = "Esta llamada está siendo grabada."
TEAM_WHISPER = "Llamada a {{linea}} de {{cliente}}. Marcá 1 para atender."
FALLBACK_MESSAGES = {
    "voicemail": "Ahora no podemos atenderte. Dejá tu mensaje y te llamamos.",
    "hangup": "Ahora no podemos atenderte. Por favor, volvé a llamar más tarde.",
}


# ---------- conversacion ----------

class CallLog:
    """Lo que se habla en una directa: cada frase es un Message con su WAV (Message.recording) y va al panel por el
    tema `transcript`. Lo del contacto o el que llama, role=user; lo del usuario o la persona, assistant con person."""

    def __init__(self, store, conversation_id: str, send=None):
        self.store = store
        self.conversation_id = conversation_id
        self.send = send or (lambda topic, data: None)

    def add(self, role: str, text: str, person: str | None = None, leg: str | None = None,
            pcm: bytes | None = None) -> None:
        seq = recordings.append_recording(self.conversation_id, pcm) if pcm else None
        state = self.store.get(self.conversation_id)
        if state is None:
            return
        state.messages.append(Message(role=role, text=text, person=person, handoff_leg=leg, recording=seq))
        self.store.save(state)
        self.send("transcript", {"role": role, "person": person, "text": text})

    def close(self) -> None:
        state = self.store.get(self.conversation_id)
        if state is not None and state.status != "completed":
            state.status = "completed"
            self.store.save(state)


async def settle(line, log: CallLog, parties: dict[str, tuple[str, str | None, str]], who: str) -> None:
    """Salio `who`: lo ultimo que dijo (la frase que el STT todavia transcribe) entra igual a la conversacion."""
    try:
        await line.settle(who, SETTLE_SECONDS)
    except Exception:
        logger.exception("ultima frase de %s", who)
    while not line.events.empty():
        ev = line.events.get_nowait()
        if ev[0] == "text" and ev[1] in parties:
            role, person, _ = parties[ev[1]]
            log.add(role, ev[2], person=person, pcm=ev[3] if len(ev) > 3 else None)


async def talk(line, log: CallLog, parties: dict[str, tuple[str, str | None, str]], *, sessions, conversation_id: str,
               deadline: float, rejoin: str | None = None, away_until: float | None = None) -> str:
    """Dos personas hablando: transcribe y graba hasta que sale alguna (su motivo, de `parties`: identidad ->
    (role, person, motivo al salir)), se cierra la room, se pasa el tope de duracion o el cliente se queda sin
    minutos (quota_watchdog del worker). Al cortar por tope, avisa con QUOTA_END_MESSAGE.

    `rejoin`: el usuario del panel. Si sale, se lo espera PANEL_REJOIN_GRACE_SECONDS a que vuelva a entrar con la
    misma identidad (recargo la pagina) y recien ahi se corta con su motivo; `away_until`, si ya habia salido."""
    next_check = time.monotonic() + settings.quota_check_seconds
    while True:
        now = time.monotonic()
        if away_until is not None and now >= away_until:
            logger.info("directa %s: el usuario del panel no volvio a entrar", conversation_id)
            return parties[rejoin][2]
        if now >= deadline:
            reason = "max_duration"
        elif now >= next_check:
            next_check = now + settings.quota_check_seconds
            with sessions() as s:
                remaining = call_service.call_remaining_seconds(s, conversation_id)
            reason = "quota_exhausted" if remaining is not None and remaining <= 0 else ""
        else:
            reason = ""
        if reason:
            logger.info("directa %s: se corta (%s)", conversation_id, reason)
            with contextlib.suppress(Exception):
                await asyncio.wait_for(line.say(settings.quota_end_message), END_SAY_TIMEOUT)
            return reason
        try:
            wake = min(deadline, next_check, away_until if away_until is not None else deadline)
            ev = await asyncio.wait_for(line.events.get(), max(0.05, wake - now))
        except asyncio.TimeoutError:
            continue
        kind, who = ev[0], ev[1]
        if kind == "closed":
            return "room_closed"
        if who not in parties:
            continue
        role, person, left_reason = parties[who]
        if who == rejoin and kind in ("left", "joined"):
            away_until = now + PANEL_REJOIN_GRACE_SECONDS if kind == "left" else None
            continue
        if kind == "left":
            await settle(line, log, parties, who)
            return left_reason
        if kind == "text":
            log.add(role, ev[2], person=person, pcm=ev[3] if len(ev) > 3 else None)


def _update_call(sessions, conversation_id: str, **values) -> None:
    with sessions() as s:
        call_service.update_call(s, conversation_id, **values)


def _finish_call(sessions, conversation_id: str, reason: str, started: float | None, **values) -> None:
    """Cierra la llamada como el worker (finalize): un motivo ya puesto (cortada desde la API) gana."""
    with sessions() as s:
        call = s.get(CallRow, conversation_id)
        if call is None or call.status not in (CallStatus.pendiente, CallStatus.sonando, CallStatus.en_curso):
            return
        call_service.update_call(s, conversation_id, ended_reason=(call.ended_reason or reason or "")[:128],
                                 ended_at=utcnow(), duration_seconds=int(time.time() - started) if started else 0,
                                 **values)


# ---------- saliente ----------

class OutboundLine(Protocol):
    """El lado de LiveKit de la saliente (OutboundRoom; un falso en los tests).

    events: ("joined", identidad), ("left", identidad, motivo SIP: busy, no_answer, failed o ""),
    ("sip", identidad, sip.callStatus), ("text", identidad, texto, pcm16k), ("closed", "")."""
    events: asyncio.Queue

    async def wait_for(self, identity: str, timeout: float) -> bool: ...
    async def dial(self, identity: str, phone: str, caller_id: str, ring_seconds: int,
                   max_seconds: int) -> transfer.DialResult: ...   # "dialing": marcando, sin esperar
    def send(self, topic: str, data: dict) -> None: ...            # datos al panel (publish_data)
    async def notice(self) -> None: ...                            # aviso de grabacion, a los dos
    async def say(self, text: str) -> None: ...
    async def listen(self, identities: set[str]) -> None: ...
    async def settle(self, identity: str, timeout: float) -> None: ...   # salio: espera su ultima frase
    async def remove(self, identity: str) -> None: ...


class Outbound:
    """Una saliente directa (metadata de services/direct_calls.prepare_direct_call). run() devuelve el resultado:
    completed (atendio), no_answer, busy o failed."""

    def __init__(self, *, sessions, store, line: OutboundLine, metadata: dict):
        self.sessions = sessions
        self.line = line
        self.conversation_id = metadata["conversation_id"]
        self.phone = metadata["phone"]
        self.from_number = metadata.get("from_number") or ""
        self.user = metadata["user_identity"]
        self.user_name = metadata.get("user_name") or "Equipo"
        self.max_seconds = int(metadata.get("max_duration_seconds") or settings.call_max_duration_seconds)
        self.join_timeout = metadata.get("join_timeout_seconds") or direct_calls.JOIN_TIMEOUT_PANEL
        self.recording_notice = bool(metadata.get("recording_notice"))
        self.log = CallLog(store, self.conversation_id, line.send)
        self.started: float | None = None
        self.away_until: float | None = None    # el usuario salio mientras sonaba: hasta cuando se lo espera
        self.done = False

    def _status(self, state: str, **extra) -> None:
        self.line.send("call_status", {"state": state, **extra})

    def _fail(self, result: str, reason: str, error: str = "", sip_status: int | None = None) -> str:
        """No llego a hablar: fallida, con el motivo (no_answer, busy, sip_call_failed, user_not_joined...). Si la
        corto el usuario antes de que atiendan (hangup_by_user o person_hangup), queda cancelada: no fallo nada."""
        self.done = True
        with self.sessions() as s:
            call = s.get(CallRow, self.conversation_id)
            reason = (call.ended_reason if call is not None and call.ended_reason else reason)[:128]
            status = CallStatus.cancelada if reason in CANCELLED_REASONS else CallStatus.fallida
            call_service.update_call(s, self.conversation_id, status=status, ended_reason=reason,
                                     error=error[:2000], ended_at=utcnow(), sip_status=sip_status)
        self.log.close()
        self._status("ended", result=result)
        return result

    def finish(self, reason: str) -> str:
        """Hablaron: finalizada, con minutos desde que atendio el contacto."""
        self.done = True
        _finish_call(self.sessions, self.conversation_id, reason, self.started, status=CallStatus.finalizada)
        self.log.close()
        self._status("ended", result="completed")
        return "completed"

    def close(self, reason: str = "worker_stopped") -> None:
        """Al cerrarse el job sin terminar (se cayo el worker, se cerro la room): que no quede activa."""
        if self.done:
            return
        if self.started is not None:
            self.finish(reason)
        else:
            self._fail("failed", reason)

    async def run(self) -> str:
        self._status("joining")
        if not await self.line.wait_for(self.user, self.join_timeout):
            logger.info("directa %s: el usuario no entro en %s s", self.conversation_id, self.join_timeout)
            return self._fail("failed", "user_not_joined", f"El usuario no entró a la llamada ({self.join_timeout} s)")
        self._status("dialing")
        res = await self.line.dial(CONTACT, self.phone, self.from_number, RING_SECONDS, self.max_seconds)
        if res.result != "dialing":
            logger.info("directa %s: no se pudo marcar (%s, SIP %s)", self.conversation_id, res.result, res.sip_status)
            return self._fail(res.result, "sip_call_failed" if res.result == "failed" else res.result, res.error,
                              res.sip_status)
        missed = await self._ringing()
        if missed is not None:
            await self.line.remove(CONTACT)
            return self._fail(*missed)
        self.started = time.time()
        _update_call(self.sessions, self.conversation_id, status=CallStatus.en_curso, started_at=utcnow())
        self._status("active")
        # Antes del aviso: lo que dicen mientras suena tambien se graba y transcribe.
        await self.line.listen({self.user, CONTACT})
        if self.recording_notice:
            try:
                await self.line.notice()
            except Exception:
                logger.exception("directa %s: no se pudo pasar el aviso de grabacion", self.conversation_id)
        reason = await talk(self.line, self.log, {CONTACT: ("user", None, "customer_hangup"),
                                                  self.user: ("assistant", self.user_name, "person_hangup")},
                            sessions=self.sessions, conversation_id=self.conversation_id,
                            deadline=time.monotonic() + self.max_seconds, rejoin=self.user,
                            away_until=self.away_until)
        return self.finish(reason)

    async def _ringing(self) -> tuple[str, str] | None:
        """Hasta que atiende el contacto (None) o no: (resultado, motivo)."""
        deadline = time.monotonic() + RING_SECONDS + RING_MARGIN_SECONDS
        rang = False
        while True:
            now = time.monotonic()
            if self.away_until is not None and now >= self.away_until:
                return "no_answer", "person_hangup"      # el usuario salio y no volvio antes de que atiendan
            timeout = min(deadline, self.away_until or deadline) - now
            if timeout <= 0:
                return "no_answer", "no_answer"
            try:
                ev = await asyncio.wait_for(self.line.events.get(), timeout)
            except asyncio.TimeoutError:
                continue
            kind, who = ev[0], ev[1]
            if kind == "closed":
                return "no_answer", "room_closed"
            if who == self.user and kind in ("left", "joined"):
                # Recargo la pagina mientras suena: se lo espera a que vuelva a entrar.
                self.away_until = now + PANEL_REJOIN_GRACE_SECONDS if kind == "left" else None
                continue
            if who != CONTACT:
                continue
            if kind == "sip" and ev[2] == "active":
                return None
            if kind == "sip" and ev[2] == "ringing" and not rang:
                rang = True
                self._status("ringing")
            elif kind == "left":
                result = ev[2] if len(ev) > 2 and ev[2] in ("busy", "no_answer") else "failed"
                return result, "sip_call_failed" if result == "failed" else result


# ---------- entrante al equipo ----------

class TeamCall:
    """Una entrante a un numero que atiende el equipo (route: calls.TeamRoute). La linea es la de la derivacion
    (transfer.Line, con los eventos "joined" y "closed"). to_agent() pasa la conversacion al agente del numero (el
    respaldo agent) y dice si se pudo. run() devuelve answered, agent, voicemail, hangup o customer_hung_up; reason,
    el motivo con que termina la llamada."""

    def __init__(self, *, sessions, store, line, conversation_id: str, client_id: str, route, customer: str,
                 caller: str = "", notice: bool = False, to_agent=None, confirm_seconds: int | None = None):
        self.sessions = sessions
        self.line = line
        self.conversation_id = conversation_id
        self.client_id = client_id
        self.route = route
        self.customer = customer
        self.caller = caller
        self.notice = notice
        self.to_agent = to_agent
        self.confirm_seconds = confirm_seconds
        self.log = CallLog(store, conversation_id, line.send)     # transcript al panel del que atiende
        self.transfer: transfer.Transfer | None = None
        self.attempts = 0
        self.reason = ""
        # El tope de duracion cuenta desde que entro la llamada (en_curso), no desde que atiende alguien.
        self.deadline = time.monotonic() + settings.call_max_duration_seconds

    def _event(self, type: str, **data) -> None:
        with self.sessions() as s:
            events.record(s, self.client_id, type, conversation_id=self.conversation_id, **data)
            s.commit()

    async def run(self) -> str:
        if self.notice:
            await self.line.say(RECORDING_NOTICE)
        if not handoff_service.is_open(self.route.schedule):
            logger.info("directa %s: fuera de horario, respaldo %s", self.conversation_id, self.route.fallback)
            return await self._fallback("after_hours")
        await self.line.hold(True)
        self._event("hold.started")
        try:
            order = ("phone", "panel") if self.route.ring_first == "phone" else ("panel", "phone")
            for where in order:
                ended = await (self._phones() if where == "phone" else self._panel())
                if ended is not None:
                    self.reason = ended
                    return "answered"
        except transfer.CustomerGone:
            self.reason = "customer_hangup"
            return "customer_hung_up"
        finally:
            await self.line.hold(False)
            self._event("hold.ended")
            with self.sessions() as s:
                direct_calls.cancel_rings(s, self.conversation_id)
        return await self._fallback("team_no_answer")

    # -- celulares --

    async def _phones(self) -> str | None:
        people = [SimpleNamespace(id=p.member_id, name=p.name, phone=p.phone, user_id=p.user_id)
                  for p in self.route.members if p.phone]
        if not people:
            return None
        tr = self.transfer = transfer.Transfer(
            sessions=self.sessions, line=self.line, conversation_id=self.conversation_id, client_id=self.client_id,
            areas=[], customer=self.customer, caller=self.caller, on_message=self.log.add,
            confirm_seconds=self.confirm_seconds, first_attempt=self.attempts, on_connected=self._phone_connected,
            limit=self._limit)
        try:
            outcome = await tr.run_team(transfer.TeamRing(name=self.route.number_label or "la línea",
                                                          ring_seconds=self.route.ring_seconds),
                                        people, TEAM_WHISPER,
                                        {"linea": self.route.number_label or "la línea", "cliente": self.caller})
        finally:
            self.attempts = tr.attempt
            self.transfer = None
        logger.info("directa %s: celulares %s (%s)", self.conversation_id, outcome.status,
                    outcome.ended or outcome.result)
        if outcome.status != "connected":
            return None
        return {"customer_hung_up": "customer_hangup", "person_hung_up": "person_hangup",
                "quota": "quota_exhausted"}.get(outcome.ended, outcome.ended or "worker_stopped")

    def _limit(self) -> str | None:
        """Hablando por el celular: el corte por minutos entrantes y por duracion (en el panel lo hace talk; la
        entrante al equipo no tiene el quota_watchdog del worker)."""
        if time.monotonic() >= self.deadline:
            return "max_duration"
        with self.sessions() as s:
            remaining = call_service.call_remaining_seconds(s, self.conversation_id)
        return "quota" if remaining is not None and remaining <= 0 else None

    def _phone_connected(self, member) -> None:
        """Atendio en su celular: si tiene usuario del panel, la llamada queda a su nombre (y ocupado)."""
        if member.user_id:
            _update_call(self.sessions, self.conversation_id, user_id=member.user_id)

    # -- panel --

    async def _panel(self) -> str | None:
        names = {p.user_id: p.name for p in self.route.members if p.user_id}
        if not names:
            return None
        with self.sessions() as s:
            rung = direct_calls.ring_panel(s, self.conversation_id, list(names))
        if not rung:
            logger.info("directa %s: nadie Disponible en el panel", self.conversation_id)
            return None
        logger.info("directa %s: suena en el panel de %s usuarios", self.conversation_id, len(rung))
        by_identity = {direct_calls.user_identity(u): u for u in rung}
        deadline = time.monotonic() + self.route.ring_seconds
        next_poll = 0.0
        graced = False
        identity = None
        while identity is None:
            now = time.monotonic()
            if now >= next_poll:
                next_poll = now + PANEL_POLL_SECONDS
                with self.sessions() as s:
                    answered = direct_calls.answered_user(s, self.conversation_id)
                    ringing = s.scalar(select(func.count()).select_from(CallRing).where(
                        CallRing.conversation_id == self.conversation_id, CallRing.status == "ringing"))
                if answered is None and not ringing:
                    break       # rechazaron todos
                if now >= deadline:
                    if answered is None or graced:
                        break
                    graced, deadline = True, now + PANEL_JOIN_GRACE_SECONDS   # atendio y su navegador esta entrando
            try:
                ev = await asyncio.wait_for(self.line.events.get(), max(0.05, min(next_poll, deadline) - now))
            except asyncio.TimeoutError:
                continue
            kind, who = ev[0], ev[1]
            if kind == "left" and who == self.customer:
                raise transfer.CustomerGone()
            if kind == "joined" and who in by_identity:
                with self.sessions() as s:
                    if direct_calls.answered_user(s, self.conversation_id) == by_identity[who]:
                        identity = who
        with self.sessions() as s:
            direct_calls.cancel_rings(s, self.conversation_id)
            # Despues de apagar los timbres nadie mas atiende (answer exige el timbre sonando): pudo atender
            # alguien justo antes, sin que lo viera el ultimo sondeo.
            answered = direct_calls.answered_user(s, self.conversation_id)
        if identity is None and answered in by_identity.values() and not graced:
            identity = await self._wait_join(direct_calls.user_identity(answered), PANEL_JOIN_GRACE_SECONDS)
        if identity is None:
            if answered is not None:
                # Atendio y su navegador no entro: la llamada no queda a su nombre (ni el ocupado), y si entra
                # tarde con el token de answer, se lo saca (no escucha lo que sigue).
                with self.sessions() as s:
                    direct_calls.release_answer(s, self.conversation_id)
                await self.line.block(direct_calls.user_identity(answered))
            return None
        await self.line.hold(False)
        name = names[by_identity[identity]]
        logger.info("directa %s: atendio %s en el panel", self.conversation_id, name)
        await self.line.listen(identity)
        ended = await talk(self.line, self.log, {self.customer: ("user", None, "customer_hangup"),
                                                 identity: ("assistant", name, "person_hangup")},
                           sessions=self.sessions, conversation_id=self.conversation_id, deadline=self.deadline,
                           rejoin=identity)
        if ended != "person_hangup":
            await self.line.remove(identity)
        return ended

    async def _wait_join(self, identity: str, seconds: float) -> str | None:
        """Espera a que entre a la room el usuario que atendio en el panel; None si no entra a tiempo."""
        deadline = time.monotonic() + seconds
        while (timeout := deadline - time.monotonic()) > 0:
            try:
                ev = await asyncio.wait_for(self.line.events.get(), timeout)
            except asyncio.TimeoutError:
                break
            if ev[0] == "left" and ev[1] == self.customer:
                raise transfer.CustomerGone()
            if ev[0] == "joined" and ev[1] == identity:
                return identity
        return None

    # -- respaldo --

    async def _fallback(self, why: str) -> str:
        fallback = self.route.fallback
        if fallback == "agent":
            if self.to_agent is not None and self.to_agent():
                self.reason = why
                self._event("team.fallback", fallback="agent", reason=why)
                return "agent"
            fallback = "voicemail"      # el agente del numero no esta (archivado): se toma el mensaje
        self._event("team.fallback", fallback=fallback, reason=why)
        text = (self.route.fallback_message or "").strip() or FALLBACK_MESSAGES[fallback]
        await self.line.resume()
        self.log.add("assistant", text)
        await self.line.say(text)
        self.reason = why
        if fallback == "hangup":
            return "hangup"
        await self.line.listen(self.customer)
        deadline = time.monotonic() + VOICEMAIL_SECONDS
        while (timeout := deadline - time.monotonic()) > 0:
            try:
                ev = await asyncio.wait_for(self.line.events.get(), timeout)
            except asyncio.TimeoutError:
                break
            if ev[0] == "closed":
                break
            if ev[0] == "left" and ev[1] == self.customer:
                await settle(self.line, self.log, {self.customer: ("user", None, "")}, self.customer)
                break
            if ev[0] == "text" and ev[1] == self.customer:
                self.log.add("user", ev[2], pcm=ev[3] if len(ev) > 3 else None)
        return "voicemail"

    def close(self) -> None:
        if self.transfer is not None:
            self.transfer.close()
        self.log.close()


# ---------- LiveKit ----------

def stt_client(vad):
    from livekit.plugins import openai

    return openai.STT(model=settings.vllm_stt_model, language="es", base_url=settings.vllm_stt_base_url,
                      api_key=settings.vllm_api_key, use_realtime=False, vad=vad)


def tts_client(voice: str):
    from livekit.plugins import openai

    return openai.TTS(model=settings.vllm_tts_model, voice=voice, base_url=settings.vllm_tts_base_url,
                      api_key=settings.vllm_api_key, response_format="pcm")


class Voice:
    """Lo que las directas usan de una AgentSession, sin LLM ni turnos: VAD y STT para transcribir, TTS y una
    pista propia para hablar. RoomLine la usa como su `session` (say, tts, vad, stt, input)."""

    def __init__(self, vad, stt, tts):
        self.vad, self.stt, self.tts = vad, stt, tts
        self.speaker = transfer.Speaker("voz", tts.sample_rate)
        self.input = SimpleNamespace(set_audio_enabled=lambda on: None)   # no hay turnos que pausar

    @classmethod
    def build(cls, voice: str) -> "Voice":
        from livekit.plugins import silero

        vad = silero.VAD.load(min_silence_duration=0.3, min_speech_duration=0.2)   # como build_session
        return cls(vad, stt_client(vad), tts_client(voice))

    async def publish(self, room: rtc.Room) -> None:
        await self.speaker.publish(room)

    async def synthesize(self, text: str) -> bytes:
        pcm = bytearray()
        async with self.tts.synthesize(to_speech(text)) as stream:
            async for chunk in stream:
                pcm.extend(chunk.frame.data)
        return bytes(pcm)

    async def play(self, pcm: bytes) -> None:
        await (await self.speaker.play(pcm))

    async def _say(self, text: str) -> None:
        await self.play(await self.synthesize(text))

    def say(self, text: str, **_):
        """Como AgentSession.say para RoomLine: devuelve algo con wait_for_playout()."""
        task = asyncio.ensure_future(self._say(text))
        return SimpleNamespace(wait_for_playout=lambda: task)

    async def aclose(self) -> None:
        await self.speaker.stop()


def notice_path(voice: str) -> Path:
    return settings.notice_audio_dir / f"{voice}.wav"


async def notice_pcm(voice: Voice, voice_name: str) -> bytes:
    """El aviso de grabacion con esa voz: el WAV de storage/notices/<voz>.wav, o se sintetiza y se guarda la
    primera vez (al cambiar el checkpoint del TTS, borrar storage/notices/, como las aperturas)."""
    path = notice_path(voice_name)
    try:
        with wave.open(str(path), "rb") as w:
            if w.getframerate() == voice.tts.sample_rate:
                return w.readframes(w.getnframes())
    except (FileNotFoundError, wave.Error, EOFError):
        pass
    pcm = await voice.synthesize(RECORDING_NOTICE)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with wave.open(str(tmp), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(voice.tts.sample_rate)
            w.writeframes(pcm)
        tmp.replace(path)
    except OSError:
        logger.exception("no se pudo guardar el aviso de grabacion %s", path)
    return pcm


def _left_reason(p) -> str:
    """Por que salio un participante SIP antes de atender: busy (rechazo), no_answer (no atendio a tiempo) o
    failed; "" si corto (o no es SIP)."""
    reason = p.disconnect_reason
    if reason == rtc.DisconnectReason.USER_REJECTED:
        return "busy"
    if reason == rtc.DisconnectReason.USER_UNAVAILABLE:
        return "no_answer"
    if reason == rtc.DisconnectReason.SIP_TRUNK_FAILURE:
        return "failed"
    return ""


class _DataSender:
    """publish_data al panel sin esperar (los callbacks de la conversacion son sincronicos)."""

    def __init__(self, room: rtc.Room):
        self.room = room
        self.tasks: set[asyncio.Task] = set()

    def send(self, topic: str, data: dict) -> None:
        task = asyncio.create_task(self._send(topic, data))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def _send(self, topic: str, data: dict) -> None:
        try:
            await self.room.local_participant.publish_data(json.dumps(data, ensure_ascii=False), reliable=True,
                                                           topic=topic)
        except Exception:
            logger.exception("publish_data %s", topic)


class OutboundRoom:
    """La saliente sobre la room: el usuario del panel ya esta (o entra), el contacto entra como participante SIP
    por el trunk de Anura. Se escuchan entre ellos sin permisos especiales; la pista "voz" (el aviso) va a los dos."""

    def __init__(self, ctx, voice: Voice, *, trunk_id: str, voice_name: str):
        self.ctx = ctx
        self.room: rtc.Room = ctx.room
        self.voice = voice
        self.voice_name = voice_name
        self.trunk_id = trunk_id
        self.events: asyncio.Queue = asyncio.Queue()
        self.listener = Listener(voice.vad, voice.stt,
                                 lambda who, text, pcm: self.events.put_nowait(("text", who, text, pcm)))
        self.data = _DataSender(self.room)
        self.send = self.data.send

    async def start(self) -> None:
        room = self.room
        room.on("participant_connected", self._on_joined)
        room.on("participant_disconnected", lambda p: self.events.put_nowait(("left", p.identity, _left_reason(p))))
        room.on("participant_attributes_changed", self._on_attributes)
        room.on("track_subscribed", self._on_subscribed)
        room.on("disconnected", lambda *_: self.events.put_nowait(("closed", "")))
        for p in room.remote_participants.values():
            for pub in p.track_publications.values():
                if pub.track is not None and pub.kind == rtc.TrackKind.KIND_AUDIO:
                    self.listener.capture(pub.track, p.identity)
        await self.voice.publish(room)

    def _on_joined(self, p) -> None:
        self.events.put_nowait(("joined", p.identity))
        if status := p.attributes.get("sip.callStatus"):
            self.events.put_nowait(("sip", p.identity, status))

    def _on_attributes(self, changed: dict, p) -> None:
        if "sip.callStatus" in changed:
            self.events.put_nowait(("sip", p.identity, changed["sip.callStatus"]))

    def _on_subscribed(self, track, pub, p) -> None:
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            self.listener.capture(track, p.identity)

    async def wait_for(self, identity: str, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while identity not in self.room.remote_participants:
            # Cortada antes de que entre (POST /calls/{id}/hangup borra la room): no se espera el resto.
            if time.monotonic() > deadline or not self.room.isconnected():
                return False
            await asyncio.sleep(0.2)
        return True

    async def dial(self, identity: str, phone: str, caller_id: str, ring_seconds: int,
                   max_seconds: int) -> transfer.DialResult:
        try:
            await self.ctx.api.sip.create_sip_participant(api.CreateSIPParticipantRequest(
                room_name=self.room.name, sip_trunk_id=self.trunk_id, sip_call_to=phone, sip_number=caller_id,
                participant_identity=identity, participant_name="Contacto", wait_until_answered=False,
                ringing_timeout=Duration(seconds=ring_seconds), max_call_duration=Duration(seconds=max_seconds)))
        except Exception as e:  # noqa: BLE001 - cualquier falla al marcar es un resultado
            result, status = campaign_calls.classify_error(e)
            return transfer.DialResult(result if result in ("no_answer", "busy") else "failed", status, str(e))
        return transfer.DialResult("dialing")

    async def notice(self) -> None:
        await self.voice.play(await notice_pcm(self.voice, self.voice_name))

    async def say(self, text: str) -> None:
        await self.voice.say(text).wait_for_playout()

    async def listen(self, identities: set[str]) -> None:
        self.listener.listening |= identities

    async def settle(self, identity: str, timeout: float) -> None:
        await self.listener.settle(identity, timeout)

    async def remove(self, identity: str) -> None:
        if identity not in self.room.remote_participants:
            return
        try:
            await self.ctx.api.room.remove_participant(api.RoomParticipantIdentity(room=self.room.name,
                                                                                   identity=identity))
        except Exception:  # noqa: BLE001 - ya se habia ido
            logger.info("directa: %s ya no estaba en la room", identity)

    async def aclose(self) -> None:
        self.listener.close()
        await self.voice.aclose()


class TeamRoom(transfer.RoomLine):
    """La entrante al equipo: la RoomLine de la derivacion con la Voice como sesion, mas los datos al panel (tema
    `transcript`), el cierre de la room como evento y los usuarios del panel que ya no pueden entrar (block)."""

    def __init__(self, ctx, voice: Voice, *, customer: str, trunk_id: str, caller_id: str, voice_name: str):
        super().__init__(ctx, voice, customer=customer, trunk_id=trunk_id, caller_id=caller_id,
                         hold_music=SimpleNamespace(track="default", volume=0.3),
                         max_call_seconds=settings.call_max_duration_seconds)
        self.voice_name = voice_name
        self.data = _DataSender(self.room)
        self.send = self.data.send
        self.blocked: set[str] = set()
        self._kicks: set[asyncio.Task] = set()
        self.room.on("disconnected", self._on_closed)
        # Sigue despues de aclose (respaldo al agente): un usuario soltado no entra en ningun momento.
        self.room.on("participant_connected", self._on_blocked_join)

    def _on_closed(self, *_) -> None:
        self.events.put_nowait(("closed", ""))

    def _on_blocked_join(self, p) -> None:
        if p.identity in self.blocked:
            task = asyncio.create_task(self._kick(p.identity))
            self._kicks.add(task)
            task.add_done_callback(self._kicks.discard)

    async def _kick(self, identity: str) -> None:
        if identity not in self.room.remote_participants:
            return
        try:
            await self.ctx.api.room.remove_participant(api.RoomParticipantIdentity(room=self.room.name,
                                                                                   identity=identity))
        except Exception:  # noqa: BLE001 - ya se habia ido
            logger.info("directa: %s ya no estaba en la room", identity)

    async def block(self, identity: str) -> None:
        """Atendio en el panel y no entro a tiempo: si esta (o entra despues con su token), se lo saca."""
        self.blocked.add(identity)
        await self._kick(identity)

    async def start(self) -> None:
        await self.session.publish(self.room)    # antes: RoomLine toma las pistas propias como las del "agente"
        await super().start()

    async def aclose(self) -> None:
        await super().aclose()
        # Sin los handlers de la espera: con el respaldo al agente, la room sigue con el worker.
        self.detach()
        with contextlib.suppress(Exception):
            self.room.off("disconnected", self._on_closed)
        await self.session.aclose()


async def _abort(ctx, sessions, conversation_id: str, error: Exception, reason: str) -> None:
    """No se pudo ni empezar (antes de la room de la directa): fallida con worker_error y se corta."""
    with sessions() as s:
        call_service.update_call(s, conversation_id, status=CallStatus.fallida, ended_reason="worker_error",
                                 error=str(error)[:2000], ended_at=utcnow())
    with contextlib.suppress(Exception):
        await ctx.delete_room()
    ctx.shutdown(reason=reason)


async def run_outbound(ctx, metadata: dict, *, sessions, store, trunk_id) -> None:
    """La saliente directa entera: corre Outbound sobre la room y corta (borra la room) al terminar."""
    conversation_id = metadata["conversation_id"]
    voice_name = metadata.get("voice") or settings.vllm_tts_voice
    _update_call(sessions, conversation_id, status=CallStatus.sonando, room=ctx.room.name)
    try:
        voice = Voice.build(voice_name)
        line = OutboundRoom(ctx, voice, trunk_id=await trunk_id(), voice_name=voice_name)
    except Exception as e:
        # Sin trunk saliente (make livekit-sip) o sin VAD: que la llamada no quede activa.
        logger.exception("directa %s: no se pudo preparar la saliente", conversation_id)
        await _abort(ctx, sessions, conversation_id, e, "direct_failed")
        return
    out = Outbound(sessions=sessions, store=store, line=line, metadata=metadata)

    async def on_shutdown():
        out.close()

    ctx.add_shutdown_callback(on_shutdown)
    result = "failed"
    try:
        await line.start()
        result = await out.run()
    except Exception:
        logger.exception("directa %s: fallo la saliente", conversation_id)
        out.close("worker_error")
    finally:
        out.close()
        await asyncio.sleep(0.5)        # que salga el ultimo call_status
        await line.aclose()
        with contextlib.suppress(Exception):
            await ctx.delete_room()
        ctx.shutdown(reason=f"direct_{result}")


async def run_inbound_team(ctx, inbound, *, customer: str, caller: str, dialed: str, sessions, store,
                           to_agent, trunk_id) -> tuple[float, int] | None:
    """La entrante al equipo. Devuelve None si la llamada termino (ya cortada) o, con el respaldo agent, el momento
    en que empezo (time.time(): los minutos cuentan desde ahi) y los intentos a celulares (persona-<n> no se
    repite en una derivacion del agente): el worker sigue con el agente en la misma room."""
    conversation_id = inbound.conversation_id
    route = inbound.team
    with sessions() as s:
        client = s.get(Client, inbound.client_id)
        notice = bool(client and client.direct_recording_notice)
    voice_name = settings.vllm_tts_voice
    _update_call(sessions, conversation_id, status=CallStatus.sonando, room=ctx.room.name)
    try:
        voice = Voice.build(voice_name)
        line = TeamRoom(ctx, voice, customer=customer, trunk_id=await trunk_id(), caller_id=dialed or "",
                        voice_name=voice_name)
    except Exception as e:
        logger.exception("directa %s: no se pudo preparar la entrante al equipo", conversation_id)
        await _abort(ctx, sessions, conversation_id, e, "direct_team_failed")
        return None
    started = time.time()
    _update_call(sessions, conversation_id, status=CallStatus.en_curso, started_at=utcnow())
    team = TeamCall(sessions=sessions, store=store, line=line, conversation_id=conversation_id,
                    client_id=inbound.client_id, route=route, customer=customer, caller=caller, notice=notice,
                    to_agent=to_agent)
    finished = {"done": False}

    def close(reason: str = "worker_stopped") -> None:
        if finished["done"]:
            return
        finished["done"] = True
        team.close()
        _finish_call(sessions, conversation_id, team.reason or reason, started, status=CallStatus.finalizada)

    async def on_shutdown():
        close()

    ctx.add_shutdown_callback(on_shutdown)
    result = "failed"
    try:
        await line.start()
        result = await team.run()
    except Exception:
        logger.exception("directa %s: fallo la entrante al equipo", conversation_id)
        result = "failed"
    if result == "agent":
        # El agente sigue en la misma room: sin las pistas ni los permisos de la espera.
        finished["done"] = True
        await line.resume()
        await line.aclose()
        for sid in (line.hold_speaker.sid, line.whisper_speaker.sid, voice.speaker.sid):
            with contextlib.suppress(Exception):
                await ctx.room.local_participant.unpublish_track(sid)
        logger.info("directa %s: nadie atendio, respaldo al agente", conversation_id)
        return started, team.attempts
    close("worker_error" if result == "failed" else "")
    await line.aclose()
    with contextlib.suppress(Exception):
        await ctx.delete_room()
    ctx.shutdown(reason=f"direct_team_{result}")
    return None
