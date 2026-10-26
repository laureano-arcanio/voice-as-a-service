"""Copia los textos legales a la landing (landing/src/data/legal/), que Render compila sola sin ver app/.

`make legal-sync`. tests/test_legal.py falla si la copia quedo vieja.
"""
import json
import pathlib

from . import DOCS, versions

LANDING_DIR = "landing/src/data/legal"


def render() -> dict[str, str]:
    """{path relativo a LANDING_DIR: contenido}: cada version tal cual y el indice."""
    files: dict[str, str] = {}
    index = {}
    for doc in DOCS:
        vs = versions(doc.id)
        for v in vs:
            files[f"{doc.slug}/{v.version}.md"] = v.text
        index[doc.slug] = {"id": doc.id, "title": doc.title, "current": vs[-1].version,
                           "versions": [{"version": v.version, "sha256": v.sha256} for v in vs]}
    files["index.json"] = json.dumps(index, ensure_ascii=False, indent=1) + "\n"
    return files


if __name__ == "__main__":
    out = pathlib.Path(__file__).parents[2] / LANDING_DIR
    for rel, content in render().items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    print(f"{LANDING_DIR}: " + ", ".join(f"{d.slug} {versions(d.id)[-1].version}" for d in DOCS))
