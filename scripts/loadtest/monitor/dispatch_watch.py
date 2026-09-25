"""Vigia de despachos de LiveKit durante un loadtest (solo lectura).

Corre dentro del contenedor agent (tiene livekit-api y las credenciales):
  docker exec -i voice-as-a-service-agent-1 python - < scripts/loadtest/monitor/dispatch_watch.py > $RUN/dispatch_watch.jsonl
Cortar: matar el docker exec y el proceso "python -" del contenedor (no tiene kill:
usar os.kill desde python).

Cada 3 s toma las llamadas de loadtest de los ultimos 90 s (app /api/calls) y,
para las que todavia no tienen un job corriendo, lista el dispatch de su room:
estado de cada job (JS_PENDING/RUNNING/...), error y worker. A los ~8 s sin job
lista una vez los participantes de la room. Escribe una linea JSON por cambio.
"""
import asyncio
import datetime
import json
import os
import time

import httpx
from livekit import api
from livekit.protocol import agent as lkagent

APP = "http://app:8011"
POLL_S, TRACK_S, PARTS_AT_S = 3.0, 90.0, 8.0


def emit(**kw):
    print(json.dumps({"ts": round(time.time(), 1), **kw}), flush=True)


async def main():
    last, done, parts_done = {}, set(), set()
    async with api.LiveKitAPI(os.environ["LIVEKIT_URL"], os.environ["LIVEKIT_API_KEY"],
                              os.environ["LIVEKIT_API_SECRET"]) as lk, httpx.AsyncClient(timeout=5) as http:
        emit(event="start")
        while True:
            try:
                calls = (await http.get(f"{APP}/api/calls", params={"limit": 100})).json()
            except Exception as e:  # noqa: BLE001
                emit(event="app_error", error=str(e)[:200])
                await asyncio.sleep(POLL_S)
                continue
            now = time.time()
            for c in calls:
                if c.get("mode") != "loadtest":
                    continue
                room = "call-" + c["id"]
                age = now - datetime.datetime.fromisoformat(c["created_at"].replace("Z", "+00:00")).timestamp()
                if room in done or age > TRACK_S or age < 0:
                    if room not in done and age > TRACK_S and room in last:
                        emit(event="gave_up", room=room, age=round(age, 1), status=c["status"])
                        done.add(room)
                    continue
                try:
                    ds = await lk.agent_dispatch.list_dispatch(room)
                    jobs = [{"status": lkagent.JobStatus.Name(j.state.status), "error": j.state.error,
                             "worker": j.state.worker_id} for d in ds for j in d.state.jobs]
                    snap = {"dispatches": len(ds), "jobs": jobs}
                except Exception as e:  # noqa: BLE001
                    snap = {"api_error": str(e)[:200]}
                if snap != last.get(room):
                    emit(event="dispatch", room=room, age=round(age, 1), status=c["status"], **snap)
                    last[room] = snap
                if any(j["status"] in ("JS_RUNNING", "JS_SUCCESS") for j in snap.get("jobs", [])):
                    done.add(room)
                elif age >= PARTS_AT_S and room not in parts_done:
                    parts_done.add(room)
                    try:
                        ps = (await lk.room.list_participants(api.ListParticipantsRequest(room=room))).participants
                        emit(event="participants", room=room, age=round(age, 1), ids=[p.identity for p in ps])
                    except Exception as e:  # noqa: BLE001
                        emit(event="participants", room=room, age=round(age, 1), api_error=str(e)[:200])
            await asyncio.sleep(POLL_S)


asyncio.run(main())
