"""Mapa de dependencias de los tests: que archivos de app/, migrations/, crm/ y scripts/
ejecuta cada archivo de tests/, con sys.monitoring (3.12, ~2 % de sobrecosto, medido).

Solo hace algo con TEST_MAPA=<ruta> (make test la pasa cuando corre la suite completa,
sin ARGS): el mapa se reescribe en cada corrida completa, asi no envejece. Los archivos
de `scripts/` lo leen (scripts/dev/tests_afectados.py). Con xdist, cada worker deja su
parte en config.workeroutput y el controlador junta y escribe; en serie escribe directo.
Escritura atomica (temporal + os.replace): puede haber otra sesion leyendo el mapa.

Limitacion conocida: el codigo a nivel de modulo (clases de app/models/, constantes,
Settings) corre al importar, durante la coleccion, y no queda atribuido a ningun test;
por eso archivo sin tests en el mapa => suite completa (lo decide tests_afectados.py).
"""
import datetime
import json
import os
import sys
import time
from collections import defaultdict

import pytest

MON = sys.monitoring
TOOL_ID = 5

SEGUIDOS = ("app", "migrations", "crm", "scripts")

deps = defaultdict(set)     # archivo de test -> fuentes que ejecuta
secs = defaultdict(float)   # archivo de test -> segundos
_cur = [None]
_partes = []                # partes que mandan los workers (solo controlador)


def _activo() -> bool:
    return bool(os.getenv("TEST_MAPA"))


_root = ""
_track = ()


def pytest_configure(config):
    if not _activo():
        return
    global _root, _track
    _root = os.path.abspath(os.getcwd())
    _track = tuple(os.path.join(_root, d) + os.sep for d in SEGUIDOS)
    MON.use_tool_id(TOOL_ID, "mapa")
    MON.register_callback(TOOL_ID, MON.events.PY_START, _on_start)
    MON.set_events(TOOL_ID, MON.events.PY_START)


def _on_start(code, offset, _disable=sys.monitoring.DISABLE):
    # El callback puede disparar durante el shutdown del interprete, cuando los globals
    # del modulo ya son None; DISABLE viaja en el default del argumento (no en un global).
    try:
        f = code.co_filename
        if _track and f.startswith(_track) and _cur[0]:
            deps[_cur[0]].add(os.path.relpath(f, _root))
    except Exception:
        pass
    return _disable


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    if not _activo():
        yield
        return
    _cur[0] = item.nodeid.split("::")[0]
    MON.restart_events()            # re-habilita lo DISABLE: cada test registra lo suyo
    t = time.perf_counter()
    yield
    secs[_cur[0]] += time.perf_counter() - t


def pytest_testnodedown(node, error):
    """Con xdist: cada worker manda lo suyo por workeroutput al terminar."""
    parte = node.workeroutput.get("mapa")
    if parte:
        _partes.append(parte)


def pytest_sessionfinish(session, exitstatus=0):
    if not _activo():
        return
    if hasattr(session.config, "workerinput"):      # worker: le manda su parte al controlador
        session.config.workeroutput["mapa"] = _datos()
        return
    # Controlador o corrida en serie: junta (las de los workers + la propia, vacia) y escribe.
    _escribir(_datos(), _partes)


def pytest_unconfigure(config):
    if _activo():
        MON.free_tool_id(TOOL_ID)


def _datos():
    out = {}
    for t in set(deps) | set(secs):
        out[t] = {"deps": sorted(deps[t]), "secs": round(secs[t], 2)}
    return out


def _juntar(partes):
    j_deps: dict[str, set] = defaultdict(set)
    j_secs: dict[str, float] = defaultdict(float)
    for parte in partes:
        for t, d in parte.items():
            j_deps[t].update(d["deps"])
            j_secs[t] += d["secs"]
    return j_deps, j_secs


def _escribir(propia, partes):
    j_deps, j_secs = _juntar(partes + [propia])
    fuentes: dict[str, list] = defaultdict(list)
    for t, d in j_deps.items():
        for f in d:
            fuentes[f].append(t)
    mapa = {
        "generado": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "commit": os.getenv("TEST_MAPA_COMMIT", ""),
        "segundos": {t: round(j_secs[t], 2) for t in sorted(j_secs)},
        "fuentes": {f: sorted(ts) for f, ts in sorted(fuentes.items())},
    }
    ruta = os.environ["TEST_MAPA"]
    tmp = ruta + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(mapa, fh, indent=1)
    os.replace(tmp, ruta)
