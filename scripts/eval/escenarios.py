"""Escenarios del eval: un agente (workflow) x una persona x una repeticion, con
las variables de la ficha ya rellenadas (fichas.py).

Los archivos de personas (scripts/eval/personas/<grupo>.yml) tienen:

  agente: <workflow id>            # y opcional agente_structured: <workflow id>
  checks: {siglas: [...], frases_max: N, prohibido: [{regex, motivo}]}
  personas:
    <nombre>:
      resumen, estilo, ficha, esperado: {fields: {...}, outcome: [...]},
      guion: [...] (opcional), solo_guion: bool, turnos_max: N, prohibido: [...]
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .fichas import generar, rellenar

PERSONAS_DIR = Path(__file__).resolve().parent / "personas"
TURNOS_MAX = 12
FALLBACK_GUION = "¿Cómo? No te entendí."


@dataclass
class Escenario:
    grupo: str
    agente: str
    persona: str
    rep: int
    variables: dict
    resumen: str
    estilo: str
    ficha: dict
    esperado: dict
    checks: dict
    turnos_max: int = TURNOS_MAX
    guion: list[str] | None = None
    solo_guion: bool = False

    @property
    def id(self) -> str:
        return f"{self.grupo}/{self.persona}/{self.rep}"

    @property
    def clave(self) -> tuple[str, str, int]:
        """Para aparear conversaciones entre runs (pareado del juez)."""
        return self.grupo, self.persona, self.rep


def grupos_disponibles() -> list[str]:
    return sorted(p.stem for p in PERSONAS_DIR.glob("*.yml"))


def cargar_grupo(grupo: str) -> dict:
    path = PERSONAS_DIR / f"{grupo}.yml"
    if not path.exists():
        raise KeyError(f"no hay personas para {grupo!r} (hay: {', '.join(grupos_disponibles())})")
    return yaml.safe_load(path.read_text())


def _rellenar(obj: Any, variables: dict) -> Any:
    if isinstance(obj, str):
        return rellenar(obj, variables)
    if isinstance(obj, list):
        return [_rellenar(x, variables) for x in obj]
    if isinstance(obj, dict):
        return {k: _rellenar(v, variables) for k, v in obj.items()}
    return obj


def escenarios(grupos: list[str], reps: int, seed: int, personas: list[str] | None = None,
               engine: str | None = None, turnos_max: int | None = None) -> list[Escenario]:
    """engine: None deja el agente del archivo (classic); "structured" usa
    agente_structured o <agente>_structured."""
    out = []
    for grupo in grupos:
        data = cargar_grupo(grupo)
        agente = data["agente"]
        if engine == "structured":
            agente = data.get("agente_structured") or f"{agente}_structured"
        checks_grupo = data.get("checks") or {}
        for nombre, p in (data.get("personas") or {}).items():
            if personas and nombre not in personas:
                continue
            for rep in range(reps):
                variables = generar(seed, grupo, nombre, rep)
                p_r = _rellenar(p, variables)
                checks = {**checks_grupo, "prohibido": list(checks_grupo.get("prohibido") or []) + list(p_r.get("prohibido") or [])}
                out.append(Escenario(
                    grupo=grupo, agente=agente, persona=nombre, rep=rep, variables=variables,
                    resumen=p_r.get("resumen", ""), estilo=p_r.get("estilo", "").strip(),
                    ficha=p_r.get("ficha") or {}, esperado=p_r.get("esperado") or {"fields": {}, "outcome": []},
                    checks=checks, turnos_max=turnos_max or p_r.get("turnos_max", TURNOS_MAX),
                    guion=p_r.get("guion"), solo_guion=bool(p_r.get("solo_guion")),
                ))
    return out
