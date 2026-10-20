#!/usr/bin/env bash
# Regenera todo el subproyecto del motor en orden (M0 → M7). ~12 min (la FEM y el CAD son lo lento).
#   bash motor/run_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
$PY -m motor.calculo.requirements          # M0
$PY -m motor.calculo.reference             # M1
$PY -m motor.calculo.optimize              # M2 (búsqueda)
$PY -m motor.calculo.report_m2             # M2 (informe, elegidos)
$PY -m motor.reductores.gearbox            # M3
$PY -m motor.fem.analysis                  # M4 (FEM, ~5 min)
$PY -m motor.calculo.m5                    # M5
$PY motor/fabricacion/gen_cad.py           # M6 (CAD → DXF/STL, ~4 min)
$PY motor/bom/gen_bom_motor.py             # M6 (lista de materiales)
$PY motor/fabricacion/gen_valores.py       # M6 (valores de fabricación y control de calidad)
$PY motor/docs/gen_partes.py               # M7 (guía HTML)
echo "motor: todo regenerado"
