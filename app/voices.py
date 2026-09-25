"""Catalogo de voces del TTS (tts/finetune/voces.tsv): nombre, genero y metricas medidas
del checkpoint servido, para filtrar al elegir voz (docs/TTS_FINETUNE.md).

- wer: WER de frases de dominio, en % (Qwen3-ASR sobre el audio generado).
- car_s: caracteres por segundo (velocidad del habla).
"""
import csv
from dataclasses import asdict, dataclass
from functools import cache

from . import config

CATALOG = config.BASE_DIR / "tts" / "finetune" / "voces.tsv"


@dataclass(frozen=True)
class Voice:
    nombre: str
    genero: str
    wer: float | None
    car_s: float | None


@cache
def catalog() -> dict[str, Voice]:
    if not CATALOG.exists():
        return {}
    with open(CATALOG, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    num = lambda v: float(v) if v else None
    return {r["nombre"]: Voice(r["nombre"], r["genero"], num(r.get("wer")), num(r.get("car_s"))) for r in rows}


def search(genero: str | None = None, wer_max: float | None = None,
           car_min: float | None = None, car_max: float | None = None) -> list[dict]:
    """Voces que cumplen los filtros, de menor a mayor WER. Una voz sin la metrica no pasa ese filtro."""
    def ok(v: Voice) -> bool:
        return ((genero is None or v.genero == genero)
                and (wer_max is None or (v.wer is not None and v.wer <= wer_max))
                and (car_min is None or (v.car_s is not None and v.car_s >= car_min))
                and (car_max is None or (v.car_s is not None and v.car_s <= car_max)))
    voices = [v for v in catalog().values() if ok(v)]
    voices.sort(key=lambda v: (v.wer is None, v.wer, v.nombre))
    return [asdict(v) for v in voices]
