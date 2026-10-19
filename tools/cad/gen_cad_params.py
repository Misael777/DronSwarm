#!/usr/bin/env python3
"""S07-02 / S08-01 · Parámetros del CAD desde el dimensionamiento (spec v1).

Escribe `cad/openscad/<grupo>/<dron>_params.scad` con los números del S04 (distancia entre ejes, tubos, hélices,
batería, alturas) y las medidas de referencia de los componentes comerciales. Así el frame queda atado a la spec:
si cambia el dimensionamiento, se regenera este archivo y se re-exportan las piezas.

    .venv/bin/python tools/cad/gen_cad_params.py

Las medidas de componentes (controladora, cámara, celdas) son de hojas de datos típicas: se confirman con la
selección de componentes del S09.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "engineering" / "data" / "results"
CAD = ROOT / "cad" / "openscad"
CELL_D, CELL_L = 21.4, 70.2                      # celda 21700 [mm]

# Disposición de celdas del pack: (a lo largo, a lo ancho, de pie) → medidas exteriores con envoltura
PACK_LAYOUT = {"6S2P": (6, 2, False), "12S5P": (10, 6, True), "12S8P": (12, 8, True)}

VEHICLES = {
    "DS-I": {"group": "inspection", "file": "ds_i_params.scad", "leg_h": 160, "fold": False,
             "extra": {"gimbal_box": [90, 70, 105], "gimbal_damper_pitch": [60, 50]}},
    "DS-D": {"group": "delivery", "file": "ds_d_params.scad", "leg_h": 420, "fold": True,
             "extra": {"payload_box": [300, 240, 220], "payload_kg": 5.0}},
}


def tube(label: str) -> tuple[float, float]:
    m = re.match(r"Ø([\d.]+)×([\d.]+)", label)
    return float(m.group(1)), float(m.group(2))


def pack_dims(battery: str) -> list[float]:
    cfg = battery.split()[0]
    n_long, n_wide, standing = PACK_LAYOUT[cfg]
    wrap = 3.0
    if standing:
        return [round(n_long * CELL_D + 2 * wrap, 1), round(n_wide * CELL_D + 2 * wrap, 1), round(CELL_L + 2 * wrap, 1)]
    # acostadas: n_long lado a lado, n_wide capas en altura, el eje de la celda a lo ancho
    return [round(n_long * CELL_D + 2 * wrap, 1), round(CELL_L + 2 * wrap, 1), round(n_wide * CELL_D + 2 * wrap, 1)]


def scad_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(scad_value(x) for x in v) + "]"
    if isinstance(v, str):
        return f'"{v}"'
    return f"{v:g}" if isinstance(v, float) else str(v)


def build(vehicle: str) -> dict:
    d = json.loads((RESULTS / f"{vehicle.lower()}_sizing.json").read_text())
    od, wall = tube(d["arm"]["tube"])
    n = d["rotors"]
    wb = d["wheelbase_m"] * 1000
    plate_d = 0.25 * wb
    # Espesor de placa del CAD (S08): el momento del brazo llega a las placas como fuerza en su plano; con 3 mm el
    # aplastamiento en los agujeros M4 del DS-D es ≈ 60 MPa (carbono ≈ 300 MPa). El S04 había supuesto 4 mm.
    plate_t = {4: 3.0, 6: 3.0, 8: 4.0}[n]
    motor_pattern = "S" if d["motor_p_max_w"] < 600 else "L"
    v = VEHICLES[vehicle]
    p = {
        "vehicle": vehicle, "rotors": n, "wheelbase": round(wb, 1), "arm_radius": round(wb / 2, 1),
        "prop_d": round(d["prop_diameter_in"] * 25.4, 1), "tube_od": od, "tube_wall": wall,
        "arm_len": round(d["arm"]["length_m"] * 1000, 1), "plate_d": round(plate_d, 1), "plate_t": plate_t,
        "plate_gap": round(od + 2 * 3.0, 1),                        # separación entre placas = abrazadera del tubo
        "motor_iface": motor_pattern, "battery_dims": pack_dims(d["battery"]), "battery": d["battery"],
        "leg_h": v["leg_h"], "fold_arms": v["fold"], "mtow_kg": d["mtow_kg"],
        "motor_mass_kg": round(d["masses"]["motores"] / n, 3), "fc_pattern": 30.5,
    }
    p.update(v["extra"])
    return p


def write(vehicle: str) -> Path:
    v = VEHICLES[vehicle]
    p = build(vehicle)
    lines = [f"// {vehicle} · parámetros generados por tools/cad/gen_cad_params.py el {dt.date.today().isoformat()}",
             "// desde engineering/data/results (spec v1). No editar a mano: regenerar. Unidades: mm, kg.", ""]
    lines += [f"{k} = {scad_value(val)};" for k, val in p.items()]
    out = CAD / v["group"] / v["file"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    return out


if __name__ == "__main__":
    for veh in VEHICLES:
        print(write(veh))
