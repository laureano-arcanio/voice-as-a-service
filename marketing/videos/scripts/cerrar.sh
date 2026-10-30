#!/usr/bin/env bash
# Cierra una versión de un video (marketing/VIDEOS.md, "Versiones"): copia el código, el guion y la locución a
# versiones/v<V>/fuente/ y marca NOTAS.md como "Estado: cerrada (fecha)". Una versión cerrada no se vuelve a
# renderizar; un cambio es una versión nueva. Para reproducirla: copiar fuente/ de vuelta al proyecto.
# Uso: scripts/cerrar.sh <proyecto> <V>
set -euo pipefail
p="${1:?uso: scripts/cerrar.sh <proyecto> <V>}"; v="${2:?falta la versión}"
dir="proyectos/$p/versiones/v$v"
[ -f "$dir/$p-v$v.mp4" ] || { echo "falta el render $dir/$p-v$v.mp4 (make video P=$p V=$v)" >&2; exit 1; }
[ -f "$dir/NOTAS.md" ] || { echo "falta $dir/NOTAS.md" >&2; exit 1; }
if grep -qi '^Estado: cerrada' "$dir/NOTAS.md"; then echo "v$v ya está cerrada"; exit 0; fi
rm -rf "$dir/fuente"; mkdir -p "$dir/fuente"
cp -r "proyectos/$p/src" "proyectos/$p/guion.json" "$dir/fuente/"
# Los videos mudos (landing) no tienen locución; los retratos u otras imágenes del proyecto también se guardan
for x in vo voces; do if [ -d "public/proyectos/$p/$x" ]; then cp -r "public/proyectos/$p/$x" "$dir/fuente/$x"; fi; done
sed -i "s/^Estado: .*/Estado: cerrada ($(date +%d-%m-%Y))/" "$dir/NOTAS.md"
grep -q '^Estado: cerrada' "$dir/NOTAS.md" || { echo "NOTAS.md no tiene la línea 'Estado: ...'" >&2; exit 1; }
echo "v$v cerrada: $dir/fuente/ ($(du -sh "$dir/fuente" | cut -f1))"
