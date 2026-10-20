#!/usr/bin/env bash
# Imprime un documento HTML a PDF con Chrome y lo controla (docs/DOCUMENTOS.md, "Controles").
# Uso: scripts/render.sh <carpeta de la versión> [hojas máximas]
#   Lee <carpeta>/documento.html y escribe <carpeta>/documento.pdf y <carpeta>/vista-N.png (una por hoja).
#   Falla si la versión está cerrada (NOTAS.md: "Estado: cerrada"), si el PDF tiene más hojas que el
#   máximo o si alguna fuente no es de la marca.
set -euo pipefail

dir="${1:?uso: scripts/render.sh <carpeta de la versión> [hojas máximas]}"
max="${2:-}"
html="$dir/documento.html"
pdf="$dir/documento.pdf"
[ -f "$html" ] || { echo "no existe $html" >&2; exit 1; }
# Una versión cerrada no se vuelve a generar: su PDF es el registro (docs/DOCUMENTOS.md)
if grep -qi '^Estado: cerrada' "$dir/NOTAS.md" 2>/dev/null; then
  echo "ERROR: $dir está cerrada: hacé una versión nueva" >&2; exit 1
fi

google-chrome --headless=new --no-sandbox --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$pdf" "file://$(realpath "$html")" 2>/dev/null

hojas=$(pdfinfo "$pdf" | awk '/^Pages:/ {print $2}')
tam=$(pdfinfo "$pdf" | awk -F': *' '/^Page size:/ {print $2}')
echo "$pdf: $hojas hoja(s), $tam"
if [ -n "$max" ] && [ "$hojas" -gt "$max" ]; then
  echo "ERROR: $hojas hojas, el máximo es $max" >&2; exit 1
fi
# Las fuentes de la marca tienen que estar incrustadas (si Chrome no las encontró, cae a una del sistema)
if pdffonts "$pdf" | tail -n +3 | awk '{print $1}' | grep -viqE 'Bricolage|Figtree|PlexMono'; then
  echo "ERROR: hay fuentes que no son de la marca:" >&2; pdffonts "$pdf" >&2; exit 1
fi
rm -f "$dir"/vista-*.png
pdftoppm -r 80 -png "$pdf" "$dir/vista"
ls "$dir"/vista-*.png
