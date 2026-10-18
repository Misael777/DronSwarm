"""S03-07 · Validación del modelo contra drones reales (fichas DJI del repo).

Método: se calibra UN parámetro (cd0_scale, el arrastre de perfil de la hélice) para que el modelo reproduzca el
tiempo de hover del DJI Matrice 4E, y con ese mismo valor se PREDICE el del Matrice 400 (dron 9× más pesado,
hélice 2.3× más grande). El error en el M400 es la validación independiente; criterio: < 10 %.

Fuentes: docs/referencias/dji/DJI-M4E_ESPECIFICACIÓN_TÉCNICA.pdf y DJI-M400_ESPECIFICACIÓN_TÉCNICA.pdf.
Supuestos donde la ficha no da el dato (marcados en el informe): paso de hélice, consumo de aviónica, motores.

    .venv/bin/python -m engineering.validation
"""

import json
from dataclasses import dataclass, replace
from pathlib import Path

from scipy.optimize import brentq

from . import DATA
from .atmosphere import isa
from .battery import Cell, Pack
from .design import size_motor
from .mission_loads import Propulsion
from .propeller import PropGeometry

ROOT = Path(__file__).resolve().parents[1]
TWR_ASSUMED = 2.0            # DJI no publica el empuje máximo; relación típica de un multirrotor comercial
DISCHARGE_TO_ZERO = 0.95     # las fichas miden del 100 % al 0 %: energía entregable ≈ 95 % de la nominal


@dataclass(frozen=True)
class Reference:
    name: str
    mass_kg: float
    rotors: int
    prop_in: float
    pitch_ratio: float        # supuesto (no publicado)
    energy_wh: float
    series: int
    v_nominal: float
    hover_min: float
    avionics_w: float         # supuesto
    source: str


M4E = Reference("DJI Matrice 4E", 1.219, 4, 10.8, 0.50, 99.5, 4, 14.76, 42.0, 15.0,
                "Ficha M4E: 1,219 g, hélice 10.8\", batería 4S 99.5 Wh, hover 42 min sin viento a nivel del mar")
M400 = Reference("DJI Matrice 400 (con H30T)", 10.67, 4, 25.0, 0.40, 977.0, 13, 48.23, 53.0, 60.0,
                 "Ficha M400: 10,670 g con H30T, hélice 25\", batería 13S 977 Wh, hover 53 min sin viento a nivel del mar")


def predicted_hover_min(ref: Reference, cd0_scale: float) -> dict:
    air = isa(0)
    geom = PropGeometry.inches(ref.prop_in, ref.prop_in * ref.pitch_ratio, cd0_scale=cd0_scale)
    capacity_ah = ref.energy_wh / ref.v_nominal
    cell = Cell(ref.name, capacity_ah, ref.v_nominal / ref.series, 0.0, capacity_ah * 4, 0.002 * 6.7 / capacity_ah, 0.0)
    pack = Pack(cell, ref.series, 1)
    sizing = size_motor(ref.rotors, geom, pack, air, ref.mass_kg, TWR_ASSUMED, 1.3)
    prop = Propulsion(ref.rotors, sizing.motor, geom, pack, avionics_w=ref.avionics_w)
    h = prop.hover(ref.mass_kg, air)
    minutes = ref.energy_wh * DISCHARGE_TO_ZERO * 60 / h["p_total"]
    return {"hover_min": minutes, "hover_power_w": h["p_total"], "w_per_kg": h["p_total"] / ref.mass_kg,
            "figure_of_merit": prop.table(air).coefficients(h["rpm"])["figure_of_merit"],
            "motor_efficiency": h["efficiency"], "kv": sizing.motor.kv}


def calibrate() -> dict:
    f = lambda k: predicted_hover_min(M4E, k)["hover_min"] - M4E.hover_min  # noqa: E731
    k = brentq(f, 0.3, 6.0, xtol=1e-3)
    results = {"cd0_scale": round(k, 3), "cases": []}
    for ref, role in ((M4E, "calibración"), (M400, "validación")):
        base = predicted_hover_min(ref, 1.0)
        cal = predicted_hover_min(ref, k)
        results["cases"].append({
            "name": ref.name, "role": role, "spec_hover_min": ref.hover_min,
            "uncalibrated_min": round(base["hover_min"], 1), "predicted_min": round(cal["hover_min"], 1),
            "error_pct": round(100 * (cal["hover_min"] - ref.hover_min) / ref.hover_min, 1),
            "hover_power_w": round(cal["hover_power_w"]), "w_per_kg": round(cal["w_per_kg"], 1),
            "figure_of_merit": round(cal["figure_of_merit"], 3), "motor_efficiency": round(cal["motor_efficiency"], 3),
            "source": ref.source, "pitch_ratio_assumed": ref.pitch_ratio, "avionics_w_assumed": ref.avionics_w,
        })
    return results


def sensitivity(k: float) -> list[dict]:
    """Cuánto cambia la predicción del M400 si los supuestos no publicados están errados."""
    rows = []
    for label, ref in [
        ("Base", M400),
        ("Paso de hélice 0.35", replace(M400, pitch_ratio=0.35)),
        ("Paso de hélice 0.50", replace(M400, pitch_ratio=0.50)),
        ("Aviónica 30 W", replace(M400, avionics_w=30.0)),
        ("Aviónica 100 W", replace(M400, avionics_w=100.0)),
    ]:
        rows.append({"case": label, "predicted_min": round(predicted_hover_min(ref, k)["hover_min"], 1)})
    return rows


def main():
    res = calibrate()
    res["m400_sensitivity"] = sensitivity(res["cd0_scale"])
    out = DATA / "results" / "validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
