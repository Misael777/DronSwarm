#!/usr/bin/env bash
# Archivos de fabricación de una placa con kicad-cli: Gerber (4 capas), taladros Excellon, posiciones (CPL) y BOM.
#   bash electronics/kicad/fab_outputs.sh <placa>          → electronics/kicad/<placa>/fab/
# Se niega si el DRC tiene errores o conexiones sin rutear (ver <placa>/drc.json).
set -euo pipefail
B="${1:?placa}"
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
[ -f "$HOME/.local/opt/kicad8/env.sh" ] && source "$HOME/.local/opt/kicad8/env.sh"
PCB="$HERE/$B/$B.kicad_pcb"
OUT="$HERE/$B/fab"
kicad-cli pcb drc --format json --severity-error -o "$HERE/$B/drc.json" "$PCB" >/dev/null
python3 - "$HERE/$B/drc.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
e = [v for v in d.get("violations", []) if v.get("severity") == "error"]
u = d.get("unconnected_items", [])
if e or u:
    sys.exit(f"DRC: {len(e)} errores y {len(u)} conexiones sin rutear: no se generan archivos de fabricación")
PY
rm -rf "$OUT" && mkdir -p "$OUT/gerber"
kicad-cli pcb export gerbers --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts \
  --subtract-soldermask -o "$OUT/gerber/" "$PCB" >/dev/null
kicad-cli pcb export drill --format excellon --excellon-separate-th --generate-map --map-format gerberx2 \
  -o "$OUT/gerber/" "$PCB" >/dev/null
kicad-cli pcb export pos --format csv --units mm --side both -o "$OUT/${B}_posiciones.csv" "$PCB" >/dev/null
cp "$HERE/../bom/bom_${B}.csv" "$OUT/${B}_bom.csv" 2>/dev/null || true
(cd "$OUT" && zip -qr "${B}_gerber.zip" gerber)
ls -1 "$OUT"
