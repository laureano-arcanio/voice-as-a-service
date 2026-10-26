#!/usr/bin/env bash
# Imprime una presentación (plantilla/slides.css, 16:9) a PDF con Chrome y la controla (docs/DOCUMENTOS.md,
# "Presentaciones"). Hermano de render.sh, que es para documentos A4.
# Uso: scripts/render-slides.sh <carpeta de la versión> [diapositivas máximas]
#   Lee <carpeta>/documento.html y escribe <carpeta>/documento.pdf (una página 1920 × 1080 por diapositiva) y
#   <carpeta>/vista-N.png (una por diapositiva, a 96 dpi: 1920 × 1080 px).
#   Falla si la versión está cerrada (NOTAS.md: "Estado: cerrada"), si hay más diapositivas que el máximo, si
#   alguna página no es 16:9 o si alguna fuente no es de la marca.
set -euo pipefail

dir="${1:?uso: scripts/render-slides.sh <carpeta de la versión> [diapositivas máximas]}"
max="${2:-}"
html="$dir/documento.html"
pdf="$dir/documento.pdf"
[ -f "$html" ] || { echo "no existe $html" >&2; exit 1; }
if grep -qi '^Estado: cerrada' "$dir/NOTAS.md" 2>/dev/null; then
  echo "ERROR: $dir está cerrada: hacé una versión nueva" >&2; exit 1
fi

# Sin DISPLAY ni D-Bus: con la sesión gráfica del host, Chrome headless se cuelga sin imprimir (26-oct-2026).
# slides.js corre con defer antes de load, así que el contador ya está puesto al imprimir.
timeout 90 env -u DISPLAY -u WAYLAND_DISPLAY -u DBUS_SESSION_BUS_ADDRESS google-chrome --headless=new --no-sandbox --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$pdf" "file://$(realpath "$html")" 2>/dev/null

n=$(pdfinfo "$pdf" | awk '/^Pages:/ {print $2}')
tam=$(pdfinfo "$pdf" | awk -F': *' '/^Page size:/ {print $2}')
echo "$pdf: $n diapositiva(s), $tam"
if [ -n "$max" ] && [ "$n" -gt "$max" ]; then
  echo "ERROR: $n diapositivas, el máximo es $max" >&2; exit 1
fi
# 1920 × 1080 px a 96 dpi son 1440 × 810 pt: si una diapositiva desborda, Chrome agrega páginas y cambia el tamaño
case "$tam" in 1440\ x\ 810\ pts*) ;; *) echo "ERROR: las páginas no son 16:9 (1440 x 810 pts): $tam" >&2; exit 1;; esac
if pdffonts "$pdf" | tail -n +3 | awk '{print $1}' | grep -viqE 'Bricolage|Figtree|PlexMono'; then
  echo "ERROR: hay fuentes que no son de la marca:" >&2; pdffonts "$pdf" >&2; exit 1
fi
rm -f "$dir"/vista-*.png
pdftoppm -r 96 -png "$pdf" "$dir/vista"
ls "$dir"/vista-*.png
