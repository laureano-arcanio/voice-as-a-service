#!/usr/bin/env bash
# Cierra una versión de un documento (docs/DOCUMENTOS.md, "Versiones"): copia la hoja de estilos de la
# plantilla a fuente/ y marca NOTAS.md como "Estado: cerrada (fecha)". El PDF queda como registro y no se
# vuelve a generar; un cambio es una versión nueva.
# Uso: scripts/cerrar.sh <carpeta de la versión>
set -euo pipefail
dir="${1:?uso: scripts/cerrar.sh <carpeta de la versión>}"
[ -f "$dir/documento.pdf" ] || { echo "falta $dir/documento.pdf (make doc)" >&2; exit 1; }
[ -f "$dir/NOTAS.md" ] || { echo "falta $dir/NOTAS.md" >&2; exit 1; }
if grep -qi '^Estado: cerrada' "$dir/NOTAS.md"; then echo "$dir ya está cerrada"; exit 0; fi
mkdir -p "$dir/fuente"
# Una presentación (plantilla/slides.css) guarda slides.css y slides.js; un documento A4, base.css
if grep -q "slides.css" "$dir/documento.html"; then cp plantilla/slides.css plantilla/slides.js "$dir/fuente/"; else cp plantilla/base.css "$dir/fuente/"; fi
sed -i "s/^Estado: .*/Estado: cerrada ($(date +%d-%m-%Y))/" "$dir/NOTAS.md"
grep -q '^Estado: cerrada' "$dir/NOTAS.md" || { echo "NOTAS.md no tiene la línea 'Estado: ...'" >&2; exit 1; }
echo "$dir cerrada"
