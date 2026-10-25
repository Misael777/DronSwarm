#!/usr/bin/env python3
"""S21-04 · Banco del ESC: eficiencia del conjunto ESC + motor con el ESC propio contra el comercial (mismo motor y hélice).

Con el mismo motor, la diferencia de eficiencia eléctrica→mecánica entre dos barridos es la diferencia de los ESC.
Usa los CSV crudos de tools/bench/acquire.py (barrido "sweep") y la calibración del banco.

    .venv/bin/python electronics/pruebas/compare_esc.py <barrido_comercial.csv> <barrido_propio.csv> [--hover-n 26]
    # sin hardware: dos barridos simulados con tools/bench/acquire.py sweep --simulate

Criterio del G6 (electronics/PLAN.md §4): eficiencia del propio ≥ comercial − 0.3 puntos en hover (E1 predice +0.5).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bench"))
from benchlib import Calibration, physical, read_raw  # noqa: E402

CRITERION_PTS = -0.3


def efficiency_curve(path: Path, cal: Calibration) -> tuple[np.ndarray, np.ndarray]:
    rows, _ = read_raw(path)
    p = physical(rows, cal)
    p_in = p["v"] * p["i"]
    p_mech = p["torque_nm"] * p["rpm"] * 2 * np.pi / 60
    ok = (p_in > 20) & (p["thrust_n"] > 1)
    return p["thrust_n"][ok], (p_mech[ok] / p_in[ok])


def at_thrust(thrust: np.ndarray, eff: np.ndarray, target: float, band: float = 0.08) -> float:
    sel = np.abs(thrust - target) <= band * target
    if sel.sum() < 3:
        raise SystemExit(f"Pocas muestras cerca de {target:.1f} N: ampliar el barrido")
    return float(np.median(eff[sel]))


def compare(ref: Path, own: Path, hover_n: float) -> dict:
    cal = Calibration.load()
    t_r, e_r = efficiency_curve(ref, cal)
    t_o, e_o = efficiency_curve(own, cal)
    out = {"empuje_hover_n": hover_n, "puntos": []}
    for frac in (0.6, 1.0, 1.5):
        t = hover_n * frac
        er, eo = at_thrust(t_r, e_r, t), at_thrust(t_o, e_o, t)
        out["puntos"].append({"empuje_n": round(t, 1), "eficiencia_comercial": round(er, 4), "eficiencia_propio": round(eo, 4),
                              "diferencia_pts": round((eo - er) * 100, 2)})
    d = out["puntos"][1]["diferencia_pts"]
    out["criterio_pts"] = CRITERION_PTS
    out["cumple"] = d >= CRITERION_PTS
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ref", help="barrido con el ESC comercial (CSV crudo)")
    ap.add_argument("own", help="barrido con el ESC propio (CSV crudo)")
    ap.add_argument("--hover-n", type=float, default=26.0, help="empuje por motor en hover [N]")
    a = ap.parse_args()
    print(json.dumps(compare(Path(a.ref), Path(a.own), a.hover_n), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
