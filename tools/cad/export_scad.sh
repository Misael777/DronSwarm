#!/usr/bin/env bash
# Exporta una pieza OpenSCAD a STL (impresión/simulación) y STEP sólido (FreeCAD, planos).
#
#   bash tools/cad/export_scad.sh cad/openscad/common/motor_mount.scad [--fcstd]
#
# Salidas en cad/exports/<nombre>.{stl,csg,step}; con --fcstd también cad/freecad/<carpeta>/<nombre>.FCStd
# Binarios: usa OPENSCAD / FREECADCMD si están definidos; si no, los del sistema o los AppImage en ~/.local/opt.
set -euo pipefail

SCAD="${1:?uso: export_scad.sh archivo.scad [--fcstd]}"
WITH_FCSTD=0
[[ "${2:-}" == "--fcstd" ]] && WITH_FCSTD=1

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
find_bin() {
    local var="$1" sys="$2" local_path="$3"
    if [[ -n "${!var:-}" ]]; then echo "${!var}"
    elif command -v "$sys" >/dev/null; then command -v "$sys"
    elif [[ -x "$local_path" ]]; then echo "$local_path"
    else echo "No se encontró $sys (define $var)" >&2; exit 1
    fi
}
OPENSCAD_BIN="$(find_bin OPENSCAD openscad "$HOME/.local/opt/openscad/AppRun")"
FREECAD_BIN="$(find_bin FREECADCMD freecadcmd "$HOME/.local/opt/freecad/AppRun")"

name="$(basename "${SCAD%.scad}")"
group="$(basename "$(dirname "$SCAD")")"
out="$REPO/cad/exports"
mkdir -p "$out"

"$OPENSCAD_BIN" -o "$out/$name.stl" "$SCAD"
"$OPENSCAD_BIN" -o "$out/$name.csg" "$SCAD"

export CSG_IN="$out/$name.csg" STEP_OUT="$out/$name.step" OPENSCAD_BIN
if [[ $WITH_FCSTD -eq 1 ]]; then
    mkdir -p "$REPO/cad/freecad/$group"
    export FCSTD_OUT="$REPO/cad/freecad/$group/$name.FCStd"
fi
# El AppImage de FreeCAD necesita "-c" para ejecutar un script; freecadcmd del sistema lo acepta igual.
result="$("$FREECAD_BIN" -c "exec(open('$REPO/tools/cad/csg_to_step.py').read())" 2>&1 | grep -E '^(RESULT|ERROR)' || true)"
echo "${result#RESULT }"
[[ "$result" == RESULT* ]]
