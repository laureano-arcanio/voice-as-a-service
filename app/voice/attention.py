"""Atención del turno en voz (`turn_attention` en la definición, docs/features/ATENCION_TURNO.md).

`AttentionWatchdog` lleva la ventana de silencio de una llamada: si la persona no responde después
del turno del agente, repite la última pregunta, insiste y cierra con aviso — `hang_up("no_response")`
o derivación al área configurada. Sin LiveKit: el worker le pasa `say`/`end`/`transfer`/`busy` y lo
arma desde los ganchos que saben quién habló (fin de la apertura, done-callback del speech de un
turno, vuelta de una derivación fallida). `on_agent_state` no llama nada: los avisos pasan por
`say`, que dispara los mismos eventos de estado que una respuesta real, y con eventos crudos la
secuencia se rompe o loopea.

Mientras suena un aviso propio ignora arm/disarm (su voz no reinicia la ventana); un `reset`
(voz, tecla o transcripción de la persona) nunca se ignora: cancela hasta el cierre en vuelo.
"""
import asyncio
import logging

from ..config import settings

logger = logging.getLogger("agent.attention")

# Un evento vencido con el turno ocupado (herramienta, derivación, respuesta o corte en curso)
# espera esto y vuelve a mirar: se difiere, no se pierde.
BUSY_POLL_SECONDS = 0.25


class AttentionWatchdog:
    """Ventana de silencio de una llamada: una sola tarea asyncio y un token de generación (`gen`)
    que invalida lo agendado, para que un aviso cancelado no salga tarde.

    `say(text, allow_interruptions=)` habla y devuelve un handle con `wait_for_playout`; `end()`
    corta (`hang_up("no_response")`); `transfer(area_id)` pasa al área configurada; `busy()` dice si
    hay un turno, derivación o corte en curso. `sleep` inyectable para los tests. `question()` da la
    última pregunta del primer aviso y `second()` el texto de insistencia (con/sin áreas de
    derivación); sin ellos, los textos de la plataforma (`app/config.py`).
    """

    def __init__(self, cfg, say, end, transfer, busy, sleep=asyncio.sleep, *, question=None, second=None):
        self.cfg = cfg
        self.say = say
        self.end = end
        self.transfer = transfer
        self.busy = busy
        self.sleep = sleep
        self.question = question
        self.second = second
        self.gen = 0                    # invalida la ventana en curso
        self.task: asyncio.Task | None = None
        self.said = 0                    # avisos dichos en la ventana (los del STT cuentan)
        self._speaking = 0              # >0: el watchdog está diciendo su propio aviso

    def arm(self) -> None:
        """Ventana nueva: el agente terminó de hablar (apertura, respuesta, vuelta de una derivación
        fallida). Se ignora mientras suena un aviso propio: su voz no re-arma."""
        if self._speaking:
            return
        self._start()

    def disarm(self) -> None:
        """Turno o derivación en curso: sin ventana hasta el próximo arm/reset."""
        if self._speaking:
            return
        self._stop()

    def reset(self) -> None:
        """Entrada real de la persona (voz, tecla, transcripción con texto): ventana nueva sin
        importar qué estaba sonando; un cierre agendado o en vuelo se cancela."""
        self._start()

    def close(self) -> None:
        """Al cortar la llamada (finalize): apaga la ventana, incluso en medio de un aviso."""
        self._stop()

    async def on_transcription_timeout(self) -> None:
        """El VAD oyó voz y el STT no devolvió texto: pedir que repita. Consume presupuesto de
        avisos y NO toca la ventana ni el deadline: una línea ruidosa no loopea el pedido ni
        atrasa el cierre; solo la entrada real resetea."""
        if self.task is None or self._speaking or self.busy() or self.said >= self.cfg.reminder_max:
            return
        self.said += 1
        await self._speak(settings.voice_no_response_stt, allow_interruptions=True)

    # --- interna ---------------------------------------------------------------------------------

    def _start(self) -> None:
        self.said = 0
        gen = self._stop()
        self.task = asyncio.create_task(self._window(gen))

    def _stop(self) -> int:
        self.gen += 1
        task, self.task = self.task, None
        if task is not None and task is not asyncio.current_task():
            task.cancel()
        return self.gen

    async def _window(self, gen: int) -> None:
        cfg = self.cfg
        first = cfg.reminder_after_ms / 1000
        gap = cfg.reminder_gap_ms / 1000
        end_at = cfg.end_after_ms / 1000
        next_at = first            # próximo aviso de esta ventana, absoluto desde su arranque
        elapsed = 0.0              # lo corrido, esperas de busy incluidas: los deadlines no se corren
        try:
            while True:
                target = end_at if self.said >= cfg.reminder_max else min(next_at, end_at)
                if target - elapsed > 0:
                    await self.sleep(target - elapsed)
                if gen != self.gen:
                    return
                elapsed = target
                while self.busy():
                    if gen != self.gen:
                        return
                    await self.sleep(BUSY_POLL_SECONDS)
                    elapsed += BUSY_POLL_SECONDS
                    if gen != self.gen:
                        return
                if elapsed >= end_at:
                    await self._close(gen)
                    return
                await self._remind()
                if gen != self.gen:
                    return         # la persona habló durante el aviso
                next_at += gap
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("watchdog de silencio: error inesperado")

    async def _remind(self) -> None:
        # El primer aviso de la ventana repite la última pregunta; los demás insisten.
        text = self._first_text() if self.said == 0 else self._second_text()
        self.said += 1
        await self._speak(text, allow_interruptions=True)

    async def _close(self, gen: int) -> None:
        await self._speak(self.cfg.end_text or settings.voice_no_response_end, allow_interruptions=False)
        if gen != self.gen:
            return                 # la persona habló durante el aviso de cierre: no se corta
        if self.cfg.on_end == "transfer":
            await self.transfer(self.cfg.on_end_area_id)
        else:
            await self.end()

    async def _speak(self, text: str, *, allow_interruptions: bool) -> None:
        self._speaking += 1
        try:
            handle = self.say(text, allow_interruptions=allow_interruptions)
            await handle.wait_for_playout()
        except Exception:
            # Sin TTS no hay aviso, pero el cierre igual llega (patrón de say_end_and_hang_up).
            logger.exception("watchdog de silencio: no se pudo decir %r", text[:80])
        finally:
            # Vuelve a 0 con el aviso sonado, si el say falló o si la tarea se canceló a mitad
            # (un reset con la persona hablando): con el contador arriba, arm/disarm quedaban
            # ignorados por el resto de la llamada y la ventana nunca volvía a anclarse al fin
            # de una respuesta real.
            self._speaking -= 1

    def _first_text(self) -> str:
        if self.cfg.reminder_text:
            return self.cfg.reminder_text
        prefix = settings.voice_no_response_reminder
        if self.question is None:
            return prefix
        question = (self.question() or "").strip()
        return f"{prefix} {question}" if question else prefix

    def _second_text(self) -> str:
        return self.second() if self.second is not None else settings.voice_no_response_second
