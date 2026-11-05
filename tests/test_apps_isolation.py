"""Las apps de apps/ son aparte: la plataforma no las importa ni las mete en su imagen."""
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize("package", ["app", "crm"])
def test_la_plataforma_no_importa_registros(package):
    files = sorted((ROOT / package).rglob("*.py"))
    assert files, f"sin archivos en {package}/"
    culprits = [str(f) for f in files if _imported_roots(f) & {"registros", "apps"}]
    assert not culprits


def test_la_imagen_de_la_plataforma_no_lleva_apps():
    copies = [line for line in (ROOT / "Dockerfile").read_text().splitlines() if line.strip().upper().startswith("COPY")]
    assert copies
    # Tampoco un COPY de todo el contexto, que se llevaría apps/ salvo por .dockerignore.
    assert not [line for line in copies if "apps" in line or line.split()[1:2] == ["."]]
    assert "apps/" in (ROOT / ".dockerignore").read_text().splitlines()
