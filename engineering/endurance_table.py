"""Autonomía del diseño recomendado según altitud y modo de vuelo (hover / crucero a 10 m/s).

Batería nueva, aterrizando con 10 % de reserva. Lee engineering/data/results/ds-*_sizing.json.

    .venv/bin/python -m engineering.endurance_table
"""

import json

from . import DATA
from .atmosphere import air
from .battery import CELLS, Pack, capacity_factor
from .mission_loads import Propulsion
from .motor import Motor
from .propeller import PropGeometry

CONDITIONS = [(0, 15, "Nivel del mar, 15 °C"), (2500, 10, "Mina a 2,500 msnm, 10 °C"),
              (3500, 5, "Mina a 3,500 msnm, 5 °C"), (4500, 0, "Mina a 4,500 msnm, 0 °C"),
              (5000, -5, "Mina a 5,000 msnm, −5 °C")]
CELL_BY_SUFFIX = {"P45B": "P45B", "P42A": "P42A", "50S": "50S"}


def load_design(vehicle: str) -> tuple[dict, Propulsion]:
    d = json.loads((DATA / "results" / f"{vehicle.lower()}_sizing.json").read_text())
    cal = json.loads((DATA / "results" / "validation.json").read_text())["cd0_scale"]
    series = int(d["battery"].split("S")[0])
    parallel = int(d["battery"].split("S")[1].split("P")[0])
    pack = Pack(CELLS[CELL_BY_SUFFIX[d["battery"].split()[-1]]], series, parallel)
    geom = PropGeometry.inches(d["prop_diameter_in"], d["prop_diameter_in"] * d["pitch_ratio"], cd0_scale=cal)
    motor = Motor.parametric(d["kv"], d["motor_i_max_a"] * pack.v_nominal, pack.v_nominal)
    return d, Propulsion(d["rotors"], motor, geom, pack, avionics_w=20 if vehicle == "DS-I" else 25)


def table(vehicle: str, payload_kg: float | None = None) -> list[dict]:
    d, prop = load_design(vehicle)
    payload_design = d["masses"].get("carga útil", 0.0)
    mass = d["mtow_kg"] - payload_design + (payload_design if payload_kg is None else payload_kg)
    rows = []
    for alt, t, label in CONDITIONS:
        a = air(alt, t)
        energy = prop.pack.energy_wh * 0.9 * capacity_factor(t)
        rows.append({"condition": label, "mass_kg": round(mass, 2),
                     "hover_min": round(energy * 60 / prop.hover(mass, a)["p_total"]),
                     "cruise_min": round(energy * 60 / prop.forward(mass, a, 10, 0.03 if vehicle == "DS-I" else 0.12)["p_total"])})
    return rows


def main():
    for vehicle, payloads in (("DS-I", [None]), ("DS-D", [None, 0.0])):
        for pl in payloads:
            rows = table(vehicle, pl)
            what = "" if pl is None else (" (sin carga)" if pl == 0 else f" ({pl} kg)")
            if vehicle == "DS-D" and pl is None:
                what = " (con 5 kg de carga)"
            print(f"\n{vehicle}{what} · {rows[0]['mass_kg']} kg · batería nueva, aterrizando con 10 %")
            print(f"  {'Condición':30s} {'Quieto (hover)':>15s} {'Volando 10 m/s':>15s}")
            for r in rows:
                print(f"  {r['condition']:30s} {r['hover_min']:11d} min {r['cruise_min']:11d} min")


if __name__ == "__main__":
    main()
