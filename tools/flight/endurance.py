#!/usr/bin/env python3
"""S11-06 · Autonomía real contra el modelo, desde un log de PX4 con batería real (.ulg).

Del vuelo de hover (en el aire, velocidad < 0.5 m/s) se mide la potencia media de batería (V·I de battery_status). El
modelo (selección COTS del S09) predice la potencia de hover para la masa real del dron y el aire del lugar (altitud y
temperatura). Criterio del plan: desviación < 10 %. Con la energía útil del pack se proyecta la autonomía hasta la
reserva y se escala a 4,500 msnm.

    .venv/bin/python tools/flight/endurance.py vuelo.ulg --vehicle DS-I --mass 2.45 --site-alt 150 --ambient 20
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def model_hover_power(vehicle: str, mass_kg: float, altitude_m: float, temp_c: float) -> float:
    """Potencia de batería en hover según el modelo con el motor y la hélice elegidos en el S09."""
    from engineering.atmosphere import air
    from engineering.cots import MOTORS
    from engineering.endurance_table import load_design
    from engineering.mission_loads import Propulsion
    from engineering.propeller import PropGeometry

    sel = json.loads((ROOT / "engineering/data/results/cots_selection.json").read_text())["selected"][vehicle]
    d, base = load_design(vehicle)
    motor = next(m for m in MOTORS if m.name == sel["motor"]).motor()
    geom = PropGeometry.inches(sel["prop_in"], sel["prop_in"] * d["pitch_ratio"], cd0_scale=base.geom.cd0_scale)
    prop = Propulsion(d["rotors"], motor, geom, base.pack, base.avionics_w)
    return prop.hover(mass_kg, air(altitude_m, temp_c))["p_total"]


def measured_hover(t: np.ndarray, v: np.ndarray, i: np.ndarray, hovering: np.ndarray) -> dict:
    sel = hovering & (i > 0) & (v > 0)
    if sel.sum() < 20:
        raise ValueError("no hay suficiente tramo de hover con corriente medida")
    p = v[sel] * i[sel]
    return {"hover_s": round(float(np.sum(np.diff(t)[sel[:-1]])), 1), "p_hover_w": round(float(np.median(p)), 1),
            "v_mean": round(float(np.mean(v[sel])), 2), "i_mean": round(float(np.mean(i[sel])), 2)}


def from_ulog(path: Path) -> dict:
    from pyulog import ULog
    u = ULog(str(path))
    get = {d.name: d.data for d in u.data_list}
    bat, lp = get["battery_status"], get["vehicle_local_position"]
    t = bat["timestamp"] / 1e6
    k = np.clip(np.searchsorted(lp["timestamp"] / 1e6, t) - 1, 0, len(lp["timestamp"]) - 1)
    speed = np.sqrt(lp["vx"][k] ** 2 + lp["vy"][k] ** 2 + lp["vz"][k] ** 2)
    alt = -lp["z"][k]
    hovering = (speed < 0.5) & (alt > 2)
    res = measured_hover(t, bat["voltage_v"], bat["current_a"], hovering)
    res["discharged_mah"] = round(float(bat["discharged_mah"][-1]), 0)
    return res


def compare(meas: dict, vehicle: str, mass: float, site_alt: float, ambient: float) -> dict:
    from engineering.atmosphere import air
    from engineering.endurance_table import load_design

    p_model = model_hover_power(vehicle, mass, site_alt, ambient)
    dev = 100 * (meas["p_hover_w"] / p_model - 1)
    _, base = load_design(vehicle)
    e_usable = base.pack.usable_energy_wh(ambient)
    # escalar la potencia medida a 4,500 msnm, 0 °C con la relación del modelo (misma masa)
    p_4500 = meas["p_hover_w"] * model_hover_power(vehicle, mass, 4500, 0) / p_model
    out = {**meas, "vehicle": vehicle, "mass_kg": mass, "site": f"{site_alt:.0f} msnm, {ambient:.0f} °C",
           "air_density": round(air(site_alt, ambient).density, 3), "p_hover_model_w": round(p_model, 1),
           "deviation_pct": round(dev, 1), "ok": abs(dev) < 10,
           "endurance_site_min": round(e_usable * 60 / meas["p_hover_w"], 1),
           "endurance_4500m_min": round(base.pack.usable_energy_wh(0) * 60 / p_4500, 1)}

    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ulg", type=Path)
    ap.add_argument("--vehicle", choices=["DS-I", "DS-D"], required=True)
    ap.add_argument("--mass", type=float, required=True, help="masa real de despegue [kg] (pesada en balanza)")
    ap.add_argument("--site-alt", type=float, required=True)
    ap.add_argument("--ambient", type=float, required=True)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    res = compare(from_ulog(a.ulg), a.vehicle, a.mass, a.site_alt, a.ambient)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if a.out:
        a.out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
