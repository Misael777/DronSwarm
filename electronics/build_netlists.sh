#!/usr/bin/env bash
# Regenera todas las netlists de KiCad desde los esquemas SKIDL (ERC incluido) → electronics/kicad/<placa>/<placa>.net
#   bash electronics/build_netlists.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
[ -f "$HOME/.local/opt/kicad8/env.sh" ] && source "$HOME/.local/opt/kicad8/env.sh"
: "${KICAD8_SYMBOL_DIR:?falta KICAD8_SYMBOL_DIR (bibliotecas de símbolos de KiCad 8)}"
mkdir -p "$ROOT/electronics/kicad/_build" && cd "$ROOT/electronics/kicad/_build"
run() {
  echo "== $*"
  "$ROOT/.venv/bin/python" "$ROOT/electronics/skidl/$1.py" "${@:2}" 2>&1 | grep -E "^ERC (ERROR|WARNING|INFO)|errors found" || true
}
run esc_ds_d
run esc_ds_i
run fc
run gnss
run bms DS-I
run bms DS-D
run charger
