#!/usr/bin/env python3
"""Métricas de empuje de un log de PX4 (.ulg): empuje en vuelo estacionario/crucero y margen restante.

    python tools/sitl/flight_stats.py logs/entrega-.../drone_0.ulg
"""

import argparse
import json
from pathlib import Path

import numpy as np
from pyulog import ULog


def topic(ulog: ULog, name: str):
    for d in ulog.data_list:
        if d.name == name:
            return d.data
    return None


def stats(path: Path) -> dict:
    ulog = ULog(str(path))
    pos = topic(ulog, "vehicle_local_position")
    thr = topic(ulog, "vehicle_thrust_setpoint")
    alt = -pos["z"]
    cruise = alt.max() * 0.8
    # Tramos estables: sobre el 80 % de la altura máxima y casi sin velocidad vertical
    stable = (alt > cruise) & (np.abs(pos["vz"]) < 0.3)
    thrust = -thr["xyz[2]"]
    # cada muestra de empuje toma el estado de la muestra de posición más cercana anterior
    idx = np.clip(np.searchsorted(pos["timestamp"], thr["timestamp"]) - 1, 0, len(stable) - 1)
    sel = stable[idx]
    hover = float(np.median(thrust[sel])) if sel.any() else float("nan")
    return {
        "max_alt_m": round(float(alt.max()), 2),
        "hover_thrust": round(hover, 3),
        "thrust_margin": round(1 - hover, 3),
        "peak_thrust": round(float(thrust.max()), 3),
        "flight_s": round(float((pos["timestamp"][-1] - pos["timestamp"][0]) / 1e6), 1),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ulg", type=Path)
    print(json.dumps(stats(ap.parse_args().ulg), indent=2))


if __name__ == "__main__":
    main()
