#!/usr/bin/env python3
"""S05-06 · Métricas de vuelo desde logs de PX4 (.ulg) comparadas con el dimensionamiento del S04.

Del tramo de vuelo estacionario (altura > 2 m, velocidad vertical < 0.3 m/s) mide las rpm reales de los motores y
verifica que empuje = peso con las constantes del modelo. Luego estima potencia y autonomía con el modelo del S03 a
esas rpm y lo compara con lo que predijo el S04. (La batería simulada de PX4 se descarga por tiempo, no por consumo:
por eso la potencia se estima desde las rpm medidas y no desde la batería simulada.)

    .venv/bin/python tools/extract_xtdrone_logs.py logs/.../drone_0.ulg --vehicle DS-D
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from pyulog import ULog

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engineering.atmosphere import G0, air  # noqa: E402
from engineering.endurance_table import load_design  # noqa: E402

MODELS = ROOT / "simulation" / "xtdrone" / "models"


def topic(ulog: ULog, name: str):
    for d in ulog.data_list:
        if d.name == name:
            return d.data
    return None


def hover_metrics(path: Path, n_rotors: int) -> dict:
    u = ULog(str(path))
    pos, out = topic(u, "vehicle_local_position"), topic(u, "actuator_outputs")
    alt, vz = -pos["z"], pos["vz"]
    stable = (alt > 2.0) & (np.abs(vz) < 0.3) & (np.hypot(pos["vx"], pos["vy"]) < 0.5)
    idx = np.clip(np.searchsorted(pos["timestamp"], out["timestamp"]) - 1, 0, len(stable) - 1)
    sel = stable[idx]
    if not sel.any():
        raise ValueError("el log no tiene tramo de vuelo estacionario")
    omegas = np.vstack([out[f"output[{k}]"][sel] for k in range(n_rotors)])
    hte = topic(u, "hover_thrust_estimate")
    return {"samples": int(sel.sum()), "omega_mean_rad_s": float(np.median(omegas)),
            "omega_per_motor": [round(float(np.median(o)), 1) for o in omegas],
            "px4_hover_thrust_estimate": round(float(np.median(hte["hover_thrust"])), 3) if hte is not None else None}


def compare(path: Path, vehicle: str, with_payload: bool = True) -> dict:
    design, prop = load_design(vehicle)
    sdf_info = json.loads((MODELS / "models_summary.json").read_text())[vehicle]
    sdf = design["sdf"]
    n = design["rotors"]
    m = hover_metrics(path, n)
    payload = design["masses"].get("carga útil", 0.0)
    mass = sdf_info["mass_kg"] if with_payload else sdf_info["mass_kg"] - payload
    thrust_sim = n * sdf["motorConstant"] * m["omega_mean_rad_s"] ** 2
    a = air(4500, 0)                                     # las constantes del modelo son de 4,500 msnm, 0 °C
    pred = prop.hover(mass, a)
    rpm_meas = m["omega_mean_rad_s"] * 60 / (2 * math.pi)
    # potencia a las rpm medidas, con el modelo de hélice y motor del S03
    table = prop.table(a)
    e = prop.motor.electrical(table.torque_at(rpm_meas), rpm_meas)
    p_meas = n * e["p_in"] / 0.95 + prop.avionics_w
    energy = prop.pack.usable_energy_wh(0)
    res = {
        "vehicle": vehicle, "log": path.name, "mass_kg": round(mass, 2), "hover_samples": m["samples"],
        "rpm_hover_measured": round(rpm_meas), "rpm_hover_predicted": round(pred["rpm"]),
        "rpm_error_pct": round(100 * (rpm_meas - pred["rpm"]) / pred["rpm"], 1),
        "thrust_over_weight": round(thrust_sim / (mass * G0), 3),
        "power_w_at_measured_rpm": round(p_meas), "power_w_predicted": round(pred["p_total"]),
        "endurance_min_at_measured_rpm": round(energy * 60 / p_meas, 1),
        "endurance_min_predicted": round(energy * 60 / pred["p_total"], 1),
        "motor_spread_pct": round(100 * (max(m["omega_per_motor"]) - min(m["omega_per_motor"])) / m["omega_mean_rad_s"], 1),
        "px4_hover_thrust_estimate": m["px4_hover_thrust_estimate"],
    }
    res["consistent"] = abs(res["rpm_error_pct"]) < 5 and abs(res["thrust_over_weight"] - 1) < 0.05
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ulg", type=Path)
    ap.add_argument("--vehicle", required=True, choices=["DS-I", "DS-D", "DS-H"])
    ap.add_argument("--no-payload", action="store_true", help="el vuelo fue sin la caja de carga")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    res = compare(a.ulg, a.vehicle, not a.no_payload)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if a.out:
        a.out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
