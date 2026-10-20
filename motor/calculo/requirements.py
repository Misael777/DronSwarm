"""M0 · Puntos de operación que el motor propio tiene que cumplir → motor/requisitos/puntos_operacion.json

Salen del mismo modelo del dron que usó la selección COTS del S09 (engineering/cots.py): hélice, MTOW con los
componentes reales, batería y aire de altura. El motor comercial elegido es la referencia a superar.

    .venv/bin/python -m motor.calculo.requirements
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from engineering.atmosphere import G0, air
from engineering.cots import MOTORS
from engineering.endurance_table import load_design
from engineering.mission_loads import Propulsion
from engineering.motor import MAX_DUTY, operating_point
from engineering.propeller import PropGeometry

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "motor" / "requisitos" / "puntos_operacion.json"
REPORT = ROOT / "motor" / "requisitos" / "README.md"
SELECTION = ROOT / "engineering" / "data" / "results" / "cots_selection.json"

V_CELL_EMPTY = 3.3              # V por celda Li-ion bajo carga al final de la descarga (diseño: el motor rinde igual)
# Peso de cada punto en el objetivo de eficiencia (fracción del tiempo de vuelo): el dron pasa casi todo en hover
WEIGHTS = {"hover_4500m_0C": 0.55, "hover_5000m_15C": 0.25, "hover_vacio": 0.10, "maniobra_twr15": 0.10}
DMI = {"DS-I": {"mount": "DMI-S: 4×M3 en Ø19/Ø25", "max_diameter_mm": 50, "max_height_mm": 32},
       "DS-D": {"mount": "DMI-L: 4×M4 en Ø35", "max_diameter_mm": 80, "max_height_mm": 45}}


def _point(name: str, op: dict, prop_rpm_max: float, note: str) -> dict:
    omega = op["rpm"] * 2 * math.pi / 60
    return {"name": name, "rpm": round(op["rpm"]), "torque_nm": round(op["torque"], 4), "p_shaft_w": round(op["torque"] * omega, 1),
            "thrust_n": round(op["thrust"], 2), "cots_current_a": round(op["current"], 2),
            "cots_efficiency": round(op["efficiency"], 4), "note": note}


def vehicle_requirements(vehicle: str) -> dict:
    sel = json.loads(SELECTION.read_text())["selected"][vehicle]
    cots = next(m for m in MOTORS if m.name == sel["motor"])
    d, base = load_design(vehicle)
    n = d["rotors"]
    geom = PropGeometry.inches(sel["prop_in"], sel["prop_in"] * d["pitch_ratio"], cd0_scale=base.geom.cd0_scale)
    prop = Propulsion(n, cots.motor(), geom, base.pack, base.avionics_w)
    mtow = sel["mtow_kg"]
    payload = d["masses"].get("carga útil", 0.0)
    pack = base.pack
    a_end, a_hot = air(4500, 0), air(5000, 15)

    pts = []
    h1 = prop.hover(mtow, a_end)
    pts.append(_point("hover_4500m_0C", h1, 0, "hover con MTOW: condición de autonomía del requisito"))
    h2 = prop.hover(mtow, a_hot)
    pts.append(_point("hover_5000m_15C", h2, 0, "hover con MTOW en el caso de diseño (aire caliente y alto)"))
    empty = mtow - payload if payload else mtow * 0.92          # DS-D vuelve sin carga; DS-I con batería semivacía
    h3 = prop.hover(empty, a_end)
    pts.append(_point("hover_vacio", h3, 0, "DS-D de regreso sin la carga" if payload else "DS-I liviano (referencia de carga parcial)"))
    t_hot = prop.table(a_hot)
    v_hot = h2["v_battery"]
    m15 = operating_point(cots.motor(), t_hot, 1.5 * mtow * G0 / n, v_hot)
    pts.append(_point("maniobra_twr15", m15, 0, "empuje = 1.5 × peso: maniobras y viento"))
    m20 = operating_point(cots.motor(), t_hot, 2.0 * mtow * G0 / n, v_hot)
    pts.append(_point("maximo_twr20", m20, 0, "empuje = 2 × peso a 5,000 msnm: requisito de empuje/peso (corto, < 30 s)"))

    v_empty = pack.series * V_CELL_EMPTY
    rpm_need = m20["rpm"]
    return {
        "vehicle": vehicle,
        "rotors": n,
        "mtow_kg": mtow,
        "prop": {"diameter_in": sel["prop_in"], "pitch_in": round(sel["prop_in"] * d["pitch_ratio"], 2),
                 "inertia_note": "inercia de la hélice: engineering/inertia.py"},
        "battery": {"cells_series": pack.series, "v_nominal": round(pack.v_nominal, 1), "v_hover_5000m": round(v_hot, 2),
                    "v_empty_loaded": round(v_empty, 1), "max_duty": MAX_DUTY},
        "points": pts,
        "objective_weights": WEIGHTS,
        "constraints": {
            "rpm_max_twr20": round(rpm_need),
            "kv_min_rpm_per_v": round(rpm_need / (v_empty * MAX_DUTY * 0.92), 1),     # 8 % de caída I·R con batería vacía
            "torque_peak_nm": round(m20["torque"], 3),
            "winding_t_max_c": 120,
            "magnet_t_max_c": 100,
            "ambient_c": 20,
            "air_density_design": round(a_hot.density, 4),
            **DMI[vehicle],
            "erpm_max_esc": 200_000 if vehicle == "DS-I" else 120_000,
        },
        "reference_cots": {"name": cots.name, "kv": cots.kv, "rm_ohm": cots.rm, "i0_a": cots.i0, "i_max_a": cots.i_max,
                           "mass_kg": cots.mass_kg, "cost_usd": cots.cost_usd, "mount": cots.mount,
                           "hover_efficiency_cots_selection": sel["hover_motor_efficiency"]},
        "targets": {"hover_efficiency_min": 0.88, "mass_max_kg": round(cots.mass_kg * 1.10, 3),
                    "material_cost_max_usd": round(cots.cost_usd * 0.30, 1)},
        "check_vs_s09": {"hover_current_a": [round(h1["current"], 2), sel["hover_current_per_motor_a"]],
                         "hover_efficiency": [round(h1["efficiency"], 4), sel["hover_motor_efficiency"]]},
    }


def write_report(res: dict) -> None:
    L = ["# M0 · Requisitos del motor propio", "",
         "> Generado por `motor/calculo/requirements.py` desde el modelo del dron (engineering/, S04-S09). No editar a mano.", "",
         "Lo que tiene que entregar **un** motor en cada condición. La eficiencia del comercial (columna COTS) es la que "
         "hay que superar: es la del modelo del S09, que en M1 se recalibra con datos del fabricante.", ""]
    for v, r in res.items():
        c = r["constraints"]
        L += [f"## {v} · hélice {r['prop']['diameter_in']:g}×{r['prop']['pitch_in']:g}\", MTOW {r['mtow_kg']:.2f} kg, "
              f"{r['battery']['cells_series']}S", "",
              "| Punto | Peso en el objetivo | rpm | Torque | Potencia en el eje | Corriente COTS | Eficiencia COTS |",
              "|---|---|---|---|---|---|---|"]
        for p in r["points"]:
            w = r["objective_weights"].get(p["name"])
            L.append(f"| {p['name']} — {p['note']} | {f'{w:.0%}' if w else 'restricción'} | {p['rpm']:,} | {p['torque_nm']:.3f} N·m | "
                     f"{p['p_shaft_w']:.0f} W | {p['cots_current_a']:.1f} A | {p['cots_efficiency']:.1%} |")
        L += ["", f"- **Restricciones:** {c['rpm_max_twr20']:,} rpm con la batería vacía ({r['battery']['v_empty_loaded']} V) "
              f"⇒ Kv ≥ {c['kv_min_rpm_per_v']} rpm/V; torque pico {c['torque_peak_nm']} N·m; bobinado < {c['winding_t_max_c']} °C; "
              f"imanes < {c['magnet_t_max_c']} °C; montaje {c['mount']}, Ø ≤ {c['max_diameter_mm']} mm, alto ≤ {c['max_height_mm']} mm; "
              f"ESC hasta {c['erpm_max_esc']:,} eRPM.",
              f"- **Metas (G5):** eficiencia ponderada ≥ {r['targets']['hover_efficiency_min']:.0%}; masa ≤ {r['targets']['mass_max_kg'] * 1000:.0f} g; "
              f"materiales ≤ US${r['targets']['material_cost_max_usd']:.0f} por motor.",
              f"- **A superar:** {r['reference_cots']['name']} ({r['reference_cots']['mass_kg'] * 1000:.0f} g, US${r['reference_cots']['cost_usd']}).",
              f"- Verificación contra el S09: corriente en hover {r['check_vs_s09']['hover_current_a'][0]} A "
              f"(S09: {r['check_vs_s09']['hover_current_a'][1]} A).", ""]
    REPORT.write_text("\n".join(L))


def run() -> dict:
    res = {v: vehicle_requirements(v) for v in ("DS-I", "DS-D")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    write_report(res)
    return res


if __name__ == "__main__":
    for v, r in run().items():
        print(v, [(p["name"], p["rpm"], p["torque_nm"], p["p_shaft_w"]) for p in r["points"]], r["check_vs_s09"], r["constraints"]["kv_min_rpm_per_v"])
