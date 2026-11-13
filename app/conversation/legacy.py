"""Conversión de una definición de agente vieja (objective, conversation, knowledge, fields, completion) a la
actual (prompt, first_message, analysis). Puro dict -> dict y solo stdlib.

CONGELADO: no se edita. Lo importa la migración 0057, que reescribe con esto las definiciones guardadas; un
cambio acá cambiaría lo que hace una migración ya aplicada. Lo aplica también Workflow al leer una definición
vieja (tests y pedidos por API en la forma vieja). No busca igual comportamiento: arma un prompt con títulos con
lo que decía cada sección."""
import copy
import json

OLD_KEYS = ("objective", "conversation", "knowledge", "fields", "completion")


def is_legacy(data: dict) -> bool:
    return isinstance(data, dict) and "prompt" not in data and any(k in data for k in ("objective", "conversation",
                                                                                       "completion"))


def _d(value) -> dict:
    """Una seccion que tendria que ser un objeto; mal formada, vacia (la validacion de Workflow dira que falta)."""
    return value if isinstance(value, dict) else {}


def _list(value) -> list:
    return value if isinstance(value, list) else []


def _text(value) -> str:
    return " ".join(str(value or "").split())


def _condition(when: dict) -> str:
    return " y ".join(f"{k} = {json.dumps(v, ensure_ascii=False)}" for k, v in when.items())


def _ordered_fields(fields: dict) -> list[tuple[str, dict]]:
    items = [(n, f) for n, f in _d(fields).items() if isinstance(f, dict)]
    return sorted(items, key=lambda kv: kv[1].get("priority", 0) if isinstance(kv[1].get("priority"), int) else 0)


def _prompt(data: dict) -> str:
    agent = _d(data.get("agent"))
    name, role, language = _text(agent.get("name")), _text(agent.get("role")), _text(agent.get("language"))
    identity = f"Sos {name}" + (f", {role}" if role else "") + "." + (f" Idioma: {language}." if language else "")
    sections = [f"# Identidad\n{identity}"]
    objective = str(_d(data.get("objective")).get("description") or "").strip()
    if objective:
        sections.append(f"# Objetivo\n{objective}")
    lines = []
    for fname, spec in _ordered_fields(data.get("fields")):
        need = ("obligatorio" if spec.get("required") else
                f"obligatorio si {_condition(spec['required_if'])}" if isinstance(spec.get("required_if"), dict)
                and spec["required_if"] else "opcional")
        description = _text(spec.get("description")).rstrip(".")
        line = f"- {fname} ({need}): {description}."
        if _list(spec.get("options")):
            line += f" Opciones: {', '.join(str(o) for o in spec['options'])}."
        if _text(spec.get("question")):
            line += f" Pregunta sugerida: {_text(spec['question'])}"
        lines.append(line)
    if lines:
        sections.append("# Datos a pedir\n" + "\n".join(lines))
    rules = [r for r in _list(_d(data.get("conversation")).get("rules")) if _text(r)]
    if rules:
        sections.append("# Cómo conversar\n" + "\n".join(f"- {str(r).strip()}" for r in rules))
    knowledge = str(data.get("knowledge") or "").strip()
    if knowledge:
        sections.append(f"# Información\n{knowledge}")
    closings = []
    for o in _list(_d(data.get("completion")).get("outcomes")):
        if not isinstance(o, dict):
            continue
        when = _d(o.get("when"))
        cond = f" (si {_condition(when)})" if when else " (en cualquier otro caso)"
        closings.append(f"- {_text(o.get('label') or o.get('id'))}{cond}: {_text(o.get('message'))}")
    if closings:
        sections.append("# Cierres\n" + "\n".join(closings))
    return "\n\n".join(sections)


def _analysis(data: dict) -> dict | None:
    fields = []
    for fname, spec in _ordered_fields(data.get("fields")):
        ftype = spec.get("type") or "string"
        fields.append({"name": fname, "type": "string" if ftype == "digits" else ftype,
                       **({"label": spec["label"]} if spec.get("label") else {}),
                       "description": str(spec.get("description") or ""),
                       **({"options": list(spec["options"])} if _list(spec.get("options")) else {})})
    outcomes = []
    for o in _list(_d(data.get("completion")).get("outcomes")):
        if isinstance(o, dict) and o.get("id"):
            outcomes.append({"id": o["id"], "label": o.get("label") or o["id"], "when": dict(_d(o.get("when"))),
                             "goal": bool(o.get("goal")), "no_contact": bool(o.get("no_contact"))})
    if not fields and not outcomes:
        return None
    return {"summary": True, "instructions": "", "fields": fields, "outcomes": outcomes}


def upgrade(data: dict) -> dict:
    """La definición vieja en la forma actual. Lo que no es de la forma vieja pasa igual."""
    if not is_legacy(data):
        return data
    out = {k: copy.deepcopy(v) for k, v in data.items() if k not in OLD_KEYS}
    if isinstance(data.get("agent"), dict):
        out["agent"] = {k: v for k, v in data["agent"].items() if k != "role"}
    out["prompt"] = _prompt(data)
    conversation = _d(data.get("conversation"))
    out["first_message"] = str(conversation.get("opening") or "")
    if "opening_audio" in conversation:
        out["first_message_audio"] = bool(conversation["opening_audio"])
    if "opening_delay_ms" in conversation:
        out["first_message_delay_ms"] = conversation["opening_delay_ms"]
    if (analysis := _analysis(data)) is not None:
        out["analysis"] = analysis
    return out
