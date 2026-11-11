"""Teclas (DTMF) marcadas en la llamada (docs/features/EQUIPO_TELEFONIA.md, "Teclas marcadas").

`Keys` agrupa los digitos seguidos de una misma parte: el que llega antes de GROUP_PAUSE_SECONDS del anterior
sigue el grupo; si no, empieza otro. `KeyLog` lo deja en la conversacion como un solo mensaje "Marcó 123"
(Message.dtmf) que se extiende con cada digito, con un evento call.dtmf por digito y, si hay panel, la linea del
tema `transcript` (con `extend` para que reemplace la anterior del mismo grupo). Los digitos se guardan tal cual.
`AgentKeys` las lleva a la conversacion del agente: el grupo cerrado es un turno del usuario.
"""
import asyncio
import logging
import time
from collections.abc import Callable

from ..conversation.models import Message
from ..services import events

logger = logging.getLogger("agent.dtmf")

# Pausa que corta un grupo: entre digitos de un mismo numero (interno, documento) se tarda menos de 1 s; 3 s da
# margen a quien busca la tecla sin juntar dos respuestas distintas.
GROUP_PAUSE_SECONDS = 3.0


def text(digits: str) -> str:
    """El texto legible del grupo: lo leen exportes, MCP, el resumen de la derivacion y el correo sin cambios."""
    return f"Marcó {digits}"


class Keys:
    """Agrupador de digitos, sin conversacion ni timers. press() devuelve (digitos del grupo, si es grupo nuevo).
    close() cierra el grupo en curso (el siguiente digito abre otro): lo usa quien necesita saber cuando termino de
    marcar, con su propio timer de `pause` segundos desde `last`."""

    def __init__(self, pause: float = GROUP_PAUSE_SECONDS, clock: Callable[[], float] = time.monotonic):
        self.pause = pause
        self.clock = clock
        self.who: object = None
        self.digits = ""
        self.last: float | None = None

    def press(self, who: object, digit: str) -> tuple[str, bool]:
        now = self.clock()
        new = not self.digits or who != self.who or self.last is None or now - self.last >= self.pause
        self.digits = digit if new else self.digits + digit
        self.who, self.last = who, now
        return self.digits, new

    def close(self) -> str:
        digits, self.digits, self.who, self.last = self.digits, "", None, None
        return digits


class KeyLog:
    """Las teclas en la conversacion `conversation_id` (store: el ConversationStore). Un mensaje por grupo: role user
    (quien llama, el contacto) o assistant con `person` (el usuario del panel en la saliente), con el tramo de la
    derivacion en curso (`leg`). Sincronico, sin await: nadie guarda la conversacion entre el get y el save."""

    def __init__(self, *, sessions, store, conversation_id: str, send=None, keys: Keys | None = None):
        self.sessions = sessions
        self.store = store
        self.conversation_id = conversation_id
        self.send = send
        self.keys = keys or Keys()

    def press(self, digit: str, *, role: str = "user", person: str | None = None, leg: str | None = None) -> None:
        try:
            self._press(digit, role, person, leg)
        except Exception:   # una tecla que no se pudo guardar no corta la llamada
            logger.exception("llamada %s: no se pudo registrar la tecla", self.conversation_id)

    def _press(self, digit: str, role: str, person: str | None, leg: str | None) -> None:
        state = self.store.get(self.conversation_id)
        if state is None or not state.client_id:
            return
        digits, new = self.keys.press((role, person, leg), digit)
        last = state.messages[-1] if state.messages else None
        # Una frase en el medio (o el mensaje no es el del grupo) abre otro.
        if not new and not (last is not None and last.dtmf and last.role == role and last.person == person
                            and last.handoff_leg == leg):
            self.keys.close()
            digits, new = self.keys.press((role, person, leg), digit)
        if new:
            state.messages.append(Message(role=role, text=text(digits), dtmf=digits, person=person, handoff_leg=leg))
        else:
            last.dtmf, last.text = digits, text(digits)
        self.store.save(state)
        record(self.sessions, state.client_id, self.conversation_id, digit, person)
        if self.send is not None:
            self.send("transcript", {"role": role, "person": person, "text": text(digits), "dtmf": digits,
                                     "extend": not new})


def record(sessions, client_id: str, conversation_id: str, digit: str, person: str | None = None) -> None:
    """El evento call.dtmf de un digito."""
    with sessions() as s:
        data = {"digit": digit, **({"person": person} if person else {})}
        events.record(s, client_id, "call.dtmf", conversation_id=conversation_id,
                      actor="person" if person else "customer", **data)
        s.commit()


class AgentKeys:
    """Las teclas de quien llama en la conversacion del agente (app/voice/worker.py): on_dtmf es el handler de
    sip_dtmf_received y solo toma las de customer() (el 1 de la persona es de la derivacion). Cada digito deja su evento
    (on_digit); el grupo se cierra `pause` segundos despues del ultimo y on_group(digitos) lo lleva como turno del
    usuario. No hace nada si active() es falso (derivacion en curso: las teclas son de la linea, KeyLog) y un grupo
    que se cierra ahi se descarta. close() cancela el timer sin llamar a on_group (al cortar)."""

    def __init__(self, *, customer: Callable[[], str | None], on_digit: Callable[[str], None],
                 on_group: Callable[[str], None], active: Callable[[], bool], keys: Keys | None = None):
        self.customer = customer
        self.on_digit = on_digit
        self.on_group = on_group
        self.active = active
        self.keys = keys or Keys()
        self._timer: asyncio.TimerHandle | None = None

    def on_dtmf(self, ev) -> None:
        if ev.participant is not None and ev.participant.identity == self.customer():
            self.press(ev.digit)

    def press(self, digit: str) -> None:
        if not self.active():
            return
        try:
            self.on_digit(digit)
        except Exception:   # sin evento, la tecla igual cuenta para el turno
            logger.exception("no se pudo registrar la tecla")
        self.keys.press("customer", digit)
        self._cancel()
        self._timer = asyncio.get_running_loop().call_later(self.keys.pause, self._fire)

    def _fire(self) -> None:
        self._timer = None
        digits = self.keys.close()
        if digits and self.active():
            try:
                self.on_group(digits)
            except Exception:
                logger.exception("no se pudo pasar la tecla al agente")

    def _cancel(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def close(self) -> None:
        self._cancel()
        self.keys.close()
