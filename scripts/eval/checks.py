"""Metricas duras de una conversacion (docs/EVAL_LLM_PLAN.md, seccion 4): datos
contra la ficha, resultado, cierre, loops, reglas de voz por regex, largo y
latencia del LLM. Sin juez: deterministas y gratis.
"""
import json
import re
import statistics
import unicodedata
from typing import Any

# Velocidad media de las voces del TTS (tts/finetune/voces.tsv): para pasar
# caracteres a segundos de audio.
CAR_POR_SEGUNDO = 17.0

REGLAS = {
    # El texto va directo al TTS: todo lo que no se dice en voz alta se escucha mal.
    "markdown": re.compile(r"[*#`_]|^\s*[-•]\s|\n\s*\d+[.)]\s", re.M),
    "simbolos": re.compile(r"[\[\]{}<>/@%&$|~^=+()]"),
    "digitos": re.compile(r"\d"),
    # Usted o tuteo en vez de voseo: vistos en el humo ("Disculpe la molestia",
    # "Le comento", "que puedes verificar").
    "usted": re.compile(r"\busted\b|\bdesea\b|\bdisculpe\b|\ble (comento|llamo|llamaba|paso|pido|recordamos|recuerdo)\b|"
                        r"\b(puedes|tienes|quieres|prefieres|necesitas)\b", re.I),
}
SIGLA = re.compile(r"\b[A-ZÁÉÍÓÚÑ]{2,}\b")
FRASE = re.compile(r"[.!?…]+(?:\s|$)")


def plain(text: Any) -> str:
    return unicodedata.normalize("NFKD", str(text).lower()).encode("ascii", "ignore").decode()


def solo_letras_numeros(text: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", plain(text))


def check_valor(esperado: Any, valor: Any) -> str:
    """ok, falta (no guardo un dato dicho) o mal (dato equivocado o inventado).
    esperado: None = tiene que quedar vacio; "*" = cualquier valor no vacio;
    bool o int = igual; texto de cifras = las cifras del valor iguales; otro
    texto = lo contiene (sin tildes ni mayusculas); lista = alguno de ellos."""
    if esperado is None:
        return "ok" if valor is None else "mal"
    if valor is None:
        return "falta"
    if isinstance(esperado, list):
        return "ok" if any(check_valor(e, valor) == "ok" for e in esperado) else "mal"
    if esperado == "*":
        return "ok"
    if isinstance(esperado, bool):
        return "ok" if valor is esperado else "mal"
    if isinstance(esperado, int):
        return "ok" if not isinstance(valor, bool) and str(valor).strip() == str(esperado) else "mal"
    esperado = str(esperado)
    if esperado.isdigit():
        return "ok" if re.sub(r"\D", "", str(valor)) == esperado else "mal"
    return "ok" if solo_letras_numeros(esperado) in solo_letras_numeros(valor) else "mal"


def reglas_rotas(texto: str, checks: dict) -> list[str]:
    """Nombres de las reglas de voz que rompe un mensaje del agente."""
    rotas = []
    if not texto.strip():
        return ["vacio"]
    for nombre, regex in REGLAS.items():
        if regex.search(texto):
            rotas.append(nombre)
    permitidas = {s.upper() for s in checks.get("siglas") or []}
    if any(s not in permitidas for s in SIGLA.findall(texto)):
        rotas.append("siglas")
    if texto.count("?") > 1:
        rotas.append("mas_de_una_pregunta")
    if len(FRASE.findall(texto)) > checks.get("frases_max", 3):
        rotas.append("frases_largas")
    for p in checks.get("prohibido") or []:
        if re.search(p["regex"], texto, re.I):
            rotas.append(f"prohibido: {p['motivo']}")
    return rotas


def _next_objective(msg: dict) -> str | None:
    """En el motor structured, la salida del turno es JSON con next_objective."""
    for tr in msg.get("llm") or []:
        if tr.get("kind") == "turno":
            try:
                return json.loads(tr.get("output") or "").get("next_objective")
            except (ValueError, AttributeError):
                return None
    return None


def _pct(xs: list[float], q: float) -> float | None:
    """Percentil con interpolacion lineal (p50 de [500, 700] = 600)."""
    if not xs:
        return None
    xs = sorted(xs)
    pos = q * (len(xs) - 1)
    lo, hi = int(pos), min(int(pos) + 1, len(xs) - 1)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (pos - lo), 3)


def evaluar(escenario, fields: dict, outcome: str | None, status: str, mensajes: list[dict],
            error: str | None, checks: dict | None = None) -> dict:
    """mensajes: los del estado final (role, text, llm). Devuelve el bloque
    `checks` de la conversacion."""
    checks = checks if checks is not None else escenario.checks
    esperado = escenario.esperado
    datos = {campo: check_valor(exp, fields.get(campo)) for campo, exp in (esperado.get("fields") or {}).items()}
    inventados = [c for c, r in datos.items() if r == "mal" and esperado["fields"].get(c) is None]

    agente = [m for m in mensajes if m.get("role") == "assistant"]
    usuario = [m for m in mensajes if m.get("role") == "user"]
    # El primer mensaje es la apertura del YAML, no del LLM.
    respuestas = agente[1:]
    reglas, repetidas, objetivos = [], 0, []
    anterior = plain(agente[0]["text"]) if agente else ""
    for i, m in enumerate(respuestas, 1):
        for regla in reglas_rotas(m.get("text") or "", checks):
            reglas.append({"turno": i, "regla": regla, "texto": (m.get("text") or "")[:160]})
        actual = plain(m.get("text") or "").strip()
        repetidas += bool(actual) and actual == anterior
        anterior = actual
        objetivos.append(_next_objective(m))
    racha = mejor = 0
    for a, b in zip(objetivos, objetivos[1:]):
        racha = racha + 1 if a and a == b else 0
        mejor = max(mejor, racha)

    largos = [len(m.get("text") or "") for m in respuestas]
    ms_turno = [tr["ms"] for m in respuestas for tr in (m.get("llm") or []) if tr.get("kind") == "turno" and tr.get("ms") is not None]
    ms_extr = [tr["ms"] for m in agente for tr in (m.get("llm") or []) if tr.get("kind", "").startswith("extraccion") and tr.get("ms") is not None]
    termino = status == "completed"
    outcome_ok = (outcome or ("sin_terminar" if not termino else None)) in (esperado.get("outcome") or [])
    por_regla: dict[str, int] = {}
    for r in reglas:
        por_regla[r["regla"]] = por_regla.get(r["regla"], 0) + 1
    n_turnos = len(usuario)
    resumen = {
        "datos": datos,
        "datos_ok": sum(r == "ok" for r in datos.values()),
        "datos_falta": sum(r == "falta" for r in datos.values()),
        "datos_mal": sum(r == "mal" for r in datos.values()),
        "inventados": inventados,
        "outcome": outcome or ("sin_terminar" if not termino else None),
        "outcome_ok": outcome_ok,
        "termino": termino,
        "turnos": n_turnos,
        "repetidas": repetidas,
        "mismo_objetivo": mejor,
        "reglas": reglas,
        "reglas_n": len(reglas),
        "reglas_por_10_turnos": round(10 * len(reglas) / n_turnos, 2) if n_turnos else 0,
        "por_regla": por_regla,
        "largo_medio": round(statistics.mean(largos), 1) if largos else 0,
        "largo_max": max(largos) if largos else 0,
        "audio_max_s": round(max(largos) / CAR_POR_SEGUNDO, 1) if largos else 0,
        "llm_turno_ms": ms_turno,
        "llm_turno_ms_p50": _pct(ms_turno, 0.5), "llm_turno_ms_p95": _pct(ms_turno, 0.95),
        "llm_turno_ms_max": max(ms_turno) if ms_turno else None,
        "llm_extraccion_ms_p50": _pct(ms_extr, 0.5),
        "error": error,
    }
    resumen["problemas"] = puntaje_problemas(resumen)
    return resumen


def puntaje_problemas(c: dict) -> int:
    """Para ordenar las peores conversaciones: cuanto mas alto, peor."""
    return (3 * c["datos_mal"] + c["datos_falta"] + 3 * (not c["outcome_ok"]) + 2 * (not c["termino"])
            + 2 * c["repetidas"] + 2 * (c["mismo_objetivo"] >= 2) + c["reglas_n"] + 5 * bool(c.get("error")))
