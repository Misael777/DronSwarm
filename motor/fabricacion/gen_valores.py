#!/usr/bin/env python3
"""M6 · Valores de fabricación y control de calidad de cada motor → motor/fabricacion/valores.md (generado).

El README de fabricación explica el proceso; los NÚMEROS (láminas, vueltas, alambre, resistencia y Kv esperados) salen
de aquí para que no queden desactualizados cuando cambia el diseño.

    .venv/bin/python motor/fabricacion/gen_valores.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from motor.calculo.report_m2 import magnet_spec, wire_plan  # noqa: E402

INF = ROOT / "motor" / "informes"
OUT = ROOT / "motor" / "fabricacion" / "valores.md"


def kv_range(kv_fem: float, kv_calc: float) -> str:
    lo, hi = sorted((round(kv_fem), round(kv_calc)))
    return f"**{lo} rpm/V**" if lo == hi else f"**{lo}-{hi} rpm/V** (FEM 2D / cálculo; el real suele quedar más cerca del mayor)"


def main() -> None:
    chosen = json.loads((INF / "M2_elegidos.json").read_text())
    fem = json.loads((INF / "M4_fem.json").read_text())
    cad = json.loads((ROOT / "cad" / "exports" / "motor" / "resumen.json").read_text())
    m5 = json.loads((INF / "M5_termico_mecanico.json").read_text())
    rows = [("Ranuras / polos", lambda c, v: c["label"]),
            ("Estator", lambda c, v: f"Ø{c['design']['d_stator'] * 1e3:.1f} mm × {c['design']['l_stack'] * 1e3:.1f} mm, "
             f"{cad[v]['params']['n_lam']} láminas de 0.20 mm"),
            ("Anillo del rotor", lambda c, v: f"{cad[v]['params']['n_ring']} anillos de 1.0 mm, Ø{2 * cad[v]['params']['r_out']:.1f} mm"),
            ("Imanes", lambda c, v: magnet_spec(c)),
            ("Bobinado", lambda c, v: f"{c['design']['turns']} vueltas por diente, {wire_plan(c['geometry']['a_cond_ideal'])}, "
             f"{'triángulo' if c['design']['delta'] else 'estrella'}"),
            ("Orden de las bobinas (diente 1 → n)", lambda c, v: f"`{c['coils']}` (mayúscula = un sentido, minúscula = el contrario)"),
            ("**Resistencia fase-fase a 20 °C**", lambda c, v: f"**{c['r_line_20_ohm'] * 1e3:.0f} mΩ** (las 3 iguales ± 3 %)"),
            ("**Kv esperado**", lambda c, v: kv_range(fem[v]["bemf"]["kv_fem"], c["kv"])),
            ("Corriente en vacío a 22 V (DS-I) / 44 V (DS-D)", lambda c, v: "se registra en el primer motor (referencia para el resto)"),
            ("Masa esperada", lambda c, v: f"{c['mass']['total'] * 1e3:.0f} g"),
            ("Bobinado a empuje máximo continuo (M5)", lambda c, v: f"{m5[v]['steady']['maximo_twr20'][0]:.0f} °C (límite 120 °C)")]
    L = ["# Valores de fabricación y control de calidad", "",
         "> Generado por `motor/fabricacion/gen_valores.py` desde el diseño (M2), la FEM (M4), M5 y el CAD (M6). No editar a mano.", "",
         "| | DS-I | DS-D |", "|---|---|---|"]
    for label, fn in rows:
        L.append(f"| {label} | " + " | ".join(fn(chosen[v], v) for v in ("DS-I", "DS-D")) + " |")
    OUT.write_text("\n".join(L) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
