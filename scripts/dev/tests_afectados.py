#!/usr/bin/env python3
"""Que tests correr despues de un cambio: los afectados, o `todo` (suite completa).

Lo llama `make test-afectados`. El mapa lo escribe `make test` en cada corrida completa
(tests/mapa_plugin.py con TEST_MAPA) y vive en scratch/ del checkout principal: lo busca
con git rev-parse --git-common-dir, asi tambien funciona desde un worktree (scratch/wt-*).

Reglas:
- Suite completa (`todo`) si cambio algo central (tests/conftest.py, tests/helpers.py,
  pytest.ini, requirements.txt, app/models/**, app/db.py, app/config.py, migrations/env.py);
  o un .py que no esta en el mapa; o no hay mapa; o lo elegido pasa del 60 % del tiempo
  de la suite (el mapa guarda los segundos por archivo); o la seleccion quedo vacia.
- Si no: los archivos de test del diff (cambiados o nuevos); los que el mapa asocia a
  cada .py cambiado; para lo que no es Python, los archivos de test cuyo texto menciona
  la ruta o el nombre del archivo; para migrations/versions/NNNN_*.py, ademas
  tests/test_migration_NNNN.py si existe.

Salida: la lista de archivos de test separados por espacio, o la palabra `todo`.
--listar imprime la lista con el motivo de cada uno (para el technical-leader), sin correr
nada. --web imprime los archivos de web/src del mismo diff (los usa make web-afectados).
--contar cuenta los tests de la lista que recibe (para decidir serie vs paralelo).

Corre en el host con el python3 del sistema; no importa nada de app/.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

CENTRAL = {
    "tests/conftest.py",
    "tests/helpers.py",
    "pytest.ini",
    "requirements.txt",
    "app/db.py",
    "app/config.py",
    "migrations/env.py",
}

UMBRAL_TIEMPO = 0.60
RE_TEST = re.compile(r"^\s*(?:async )?def test_", re.M)


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.stdout.strip()


def cambiados(base: str | None) -> set[str]:
    """El diff contra `base` mas los cambios sin commitear y sin trackear."""
    arch = set()
    if base:
        arch |= set(git("diff", "--name-only", base).splitlines())
    arch |= set(git("diff", "--name-only").splitlines())
    arch |= set(git("ls-files", "--others", "--exclude-standard").splitlines())
    return {a for a in arch if a}


def base_defecto() -> str | None:
    mb = git("merge-base", "main", "HEAD")
    return mb or None


def ruta_mapa() -> Path:
    """scratch/ del checkout principal (en un worktree, git-common-dir apunta al .git principal)."""
    common = git("rev-parse", "--git-common-dir")
    p = Path(common)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.parent / "scratch" / "test-mapa.json"


def tests_del_repo() -> list[Path]:
    return sorted(Path("tests").rglob("test_*.py"))


def textos() -> dict[str, str]:
    return {str(p): p.read_text(errors="replace") for p in tests_del_repo()}


def migracion_num(ruta: str) -> str | None:
    m = re.match(r"migrations/versions/(\d+)_.*\.py$", ruta)
    return m.group(1) if m else None


def elegir(
    cambiados: set[str], mapa: dict | None, textos_map: dict[str, str] | None = None
) -> tuple[list[str], str | None, dict[str, list[str]]]:
    """Devuelve (tests, motivo_de_todo, test->motivos). motivo_de_todo no es None => suite completa.

    textos_map: texto de cada archivo de test; si es None, se lee tests/ (los usa la
    regla de "menciona" para lo que no es Python)."""
    if textos_map is None:
        textos_map = textos()
    motivos: dict[str, list[str]] = defaultdict(list)

    def agregar(t: str, m: str) -> None:
        motivos[t].append(m)

    central: list[str] = []
    sin_mapa_py: list[str] = []
    migra_sin_test: list[str] = []
    for f in sorted(cambiados):
        if f in CENTRAL or f.startswith("app/models/"):
            central.append(f)
            continue
        if f.startswith("tests/"):
            if f.endswith(".py"):
                agregar(f, "test del diff")
            continue
        n = migracion_num(f)
        if n is not None:
            t = f"tests/test_migration_{n}.py"
            con_mapa = (mapa or {}).get("fuentes", {}).get(f)
            if Path(t).exists():
                agregar(t, f"migracion {f}")
            if con_mapa:
                for t in con_mapa:
                    agregar(t, f"ejecuta {f}")
            elif not Path(t).exists():
                migra_sin_test.append(f)
            continue
        if f.endswith(".py"):
            if mapa and mapa["fuentes"].get(f):
                for t in mapa["fuentes"][f]:
                    agregar(t, f"ejecuta {f}")
            else:
                sin_mapa_py.append(f)
            continue
        # Lo que no es Python (json de referencia, docs, compose, Dockerfile): los tests que lo mencionan.
        base = Path(f).name
        for t, txt in textos_map.items():
            if f in txt or base in txt:
                agregar(t, f"menciona {f}")

    if mapa is None:
        return [], "no hay mapa (corre make test una vez)", {}
    if central:
        return [], f"central: {', '.join(central)}", {}
    if sin_mapa_py:
        return [], f".py fuera del mapa: {', '.join(sin_mapa_py)}", {}
    if migra_sin_test:
        return [], f"migracion sin test_migration_NNNN: {', '.join(migra_sin_test)}", {}
    if not motivos:
        return [], "la seleccion quedo vacia (corre la suite por las dudas)", {}
    total = sum(mapa["segundos"].values())
    elegido = sum(mapa["segundos"].get(t, 0.0) for t in motivos)
    if total and elegido / total > UMBRAL_TIEMPO:
        return [], f"la seleccion es el {elegido / total:.0%} del tiempo de la suite", {}
    return sorted(motivos), None, dict(motivos)


def contar(tests: list[str]) -> int:
    n = 0
    for t in tests:
        p = Path(t)
        if p.exists():
            n += len(RE_TEST.findall(p.read_text(errors="replace")))
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", help="ref contra la que mirar el diff (default: merge-base con main)")
    ap.add_argument("--archivos", help="lista de archivos separados por espacio, en vez del diff")
    ap.add_argument("--listar", action="store_true", help="imprime la lista con el motivo, sin correr nada")
    ap.add_argument("--web", action="store_true", help="imprime los archivos de web/src del mismo diff")
    ap.add_argument("--contar", action="store_true", help="cuenta los tests de la lista recibida")
    args = ap.parse_args()

    base = args.base or base_defecto()
    if args.contar:
        print(contar((args.archivos or "").split()))
        return
    if args.web:
        arch = sorted(a for a in cambiados(base) if a.startswith("web/src/"))
        print(" ".join(arch))
        return
    lista = set((args.archivos or "").split()) if args.archivos else cambiados(base)
    tests, motivo_todo, motivos = elegir(lista, _cargar_mapa())
    if motivo_todo:
        print(f"todo: {motivo_todo}" if args.listar else "todo")
        return
    if args.listar:
        for t in tests:
            print(f"{t}: {motivos[t][0]}")
        return
    print(" ".join(tests))


def _cargar_mapa() -> dict | None:
    ruta = ruta_mapa()
    try:
        return json.loads(ruta.read_text())
    except (OSError, ValueError):
        return None


if __name__ == "__main__":
    sys.exit(main())
