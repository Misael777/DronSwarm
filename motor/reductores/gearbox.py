"""M3 · Estudio de reductores: motor directo vs motor rápido + reductor → motor/informes/M3_reductores.md

Para cada tipo y relación N se optimiza un motor a la medida (mismo optimizador y modelo de M2) para los puntos de
operación vistos desde el motor: rpm × N y torque / (N · η_engrane) + arrastre. Luego se compara el CONJUNTO a nivel dron:
eficiencia útil (en la hélice), masa total (motor + reductor), autonomía, costo, inercia vista por la hélice
(respuesta del empuje → control de actitud), juego y riesgos de vida útil.

Parámetros de reductores: valores típicos de catálogo y literatura para reductores chicos (1-50 N·m). Son supuestos
de primer orden; si un reductor queda cerca del directo, se mide un prototipo en el banco antes de decidir.

    .venv/bin/python -m motor.reductores.gearbox [--samples 6000]
"""

from __future__ import annotations

import argparse
import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path

from engineering.mass_budget import prop_mass_kg
from motor.calculo.design import RECON, geometry, masses
from motor.calculo.optimize import RANGES, reference, search

ROOT = Path(__file__).resolve().parents[2]
REQ = ROOT / "motor" / "requisitos" / "puntos_operacion.json"
INF = ROOT / "motor" / "informes"


@dataclass(frozen=True)
class GearType:
    key: str
    name: str
    ratios: tuple
    eta_mesh: float             # eficiencia del engrane a carga nominal
    drag_frac: float            # torque de arrastre en vacío / torque nominal de salida (sellos, rodamientos, aceite/grasa)
    torque_density: float       # N·m de salida (pico) por kg de reductor, tamaños chicos
    m0: dict                    # masa fija: carcasa, rodamiento del eje de salida (por dron)
    cost: dict                  # US$ de materiales por reductor (hecho en casa) o compra
    backlash_deg: float
    coaxial: bool
    risks: str


GEARS = [
    GearType("planetario", "Planetario de 1 etapa (engranajes de acero cortados con láser, apilados)", (3, 4, 5), 0.97, 0.02, 25.0,
             {"DS-I": 0.012, "DS-D": 0.035}, {"DS-I": 6.0, "DS-D": 14.0}, 0.4, True,
             "ruido de engrane a 10-30 krpm; engranajes cortados con láser tienen perfil imperfecto (más pérdidas y desgaste); "
             "lubricación con polvo de mina"),
    GearType("planetario_aero", "Planetario comercial de aeromodelismo (tipo Neu/Hacker, escenario optimista)", (3, 4, 5), 0.98, 0.01,
             60.0, {"DS-I": 0.008, "DS-D": 0.020}, {"DS-I": 80.0, "DS-D": 150.0}, 0.3, True,
             "se compra (no se fabrica en casa) y cuesta tanto como el motor comercial; pensado para aviones, no para 1,000 h de hover"),
    GearType("planetario_impreso", "Planetario de 1 etapa impreso (nylon/PA-CF)", (3, 4, 5), 0.92, 0.03, 8.0,
             {"DS-I": 0.008, "DS-D": 0.025}, {"DS-I": 2.0, "DS-D": 5.0}, 0.8, True,
             "dientes plásticos se deforman con calor y fatigan: vida de decenas de horas a estos torques"),
    GearType("cicloidal", "Cicloidal de 1 etapa (2 discos a 180°, pines con rodillos)", (8, 11, 15), 0.90, 0.04, 35.0,
             {"DS-I": 0.015, "DS-D": 0.040}, {"DS-I": 8.0, "DS-D": 18.0}, 0.1, True,
             "excéntrico a 30-60 krpm: vibración y rodamientos muy cargados; relación mínima ~8 lleva el motor a rpm muy altas"),
    GearType("armonico", "Armónico (strain wave)", (30,), 0.75, 0.05, 40.0,
             {"DS-I": 0.020, "DS-D": 0.045}, {"DS-I": 120.0, "DS-D": 250.0}, 0.0, True,
             "relación mínima ~30: el motor tendría que girar a 110-170 krpm (imposible para el ESC y los rodamientos); el "
             "flexspline se fatiga girando continuo; diseñado para robots lentos y precisos, no para hélices"),
    GearType("correa", "Correa dentada HTD/GT (1 etapa)", (2, 3), 0.96, 0.02, 15.0,
             {"DS-I": 0.020, "DS-D": 0.055}, {"DS-I": 5.0, "DS-D": 10.0}, 0.2, False,
             "no es coaxial: obliga a rediseñar el extremo del brazo; la correa se estira y hay que tensarla"),
]


def geared_requirements(req: dict, gear: GearType, n: int) -> dict:
    """Puntos de operación vistos desde el motor, con la potencia útil (en la hélice) guardada para la eficiencia."""
    r = copy.deepcopy(req)
    t_peak = max(p["torque_nm"] for p in req["points"])
    drag_in = gear.drag_frac * t_peak / n
    for p in r["points"]:
        p["p_useful_w"] = p["p_shaft_w"]
        p["rpm"] = p["rpm"] * n
        p["torque_nm"] = p["torque_nm"] / (n * gear.eta_mesh) + drag_in
    r["constraints"]["rpm_max_twr20"] *= n
    r["extra_mass_kg"] = gear.m0[req["vehicle"]] + t_peak * 1.5 / gear.torque_density     # pico con FS 1.5
    base = RANGES[req["vehicle"]]
    r["ranges"] = {**base, "d": (base["d"][0] * 0.45, base["d"][1]), "l": (2e-3, base["l"][1]),
                   "hm": (1.0e-3, base["hm"][1]), "combos": [(9, 4), (12, 5), (12, 7), (18, 8), (24, 11)]}    # pocos polos: eRPM
    return r


def rotor_inertia(e: dict) -> float:
    """Inercia de la parte que gira del motor (imanes + anillo + tapa + eje), aproximada como anillos [kg·m²]."""
    g, m = e["geometry"], e["mass"]
    r_ring = (g["r_mag_in"] + g["r_out"]) / 2
    return (m["imanes"] + m["yugo del rotor"]) * r_ring ** 2 + m["tapa impresa"] * g["r_out"] ** 2 / 2


def prop_inertia(diameter_in: float) -> float:
    r = diameter_in * 0.0254 / 2
    return prop_mass_kg(diameter_in) * r ** 2 / 3 * 0.8                         # pala ≈ varilla que se afina


def response_time(j_total: float, req: dict) -> float:
    """Tiempo para subir 10 % las rpm desde hover con el torque sobrante (máximo − hover) [s]. ∝ inercia total."""
    pts = {x["name"]: x for x in req["points"]}
    omega = pts["hover_4500m_0C"]["rpm"] * 2 * math.pi / 60
    t_extra = pts["maximo_twr20"]["torque_nm"] - pts["hover_4500m_0C"]["torque_nm"]
    return 0.1 * omega * j_total / t_extra


def run(samples: int) -> dict:
    req_all = json.loads(REQ.read_text())
    m2 = json.loads((INF / "M2_elegidos.json").read_text())
    out = {}
    for veh in ("DS-I", "DS-D"):
        req = req_all[veh]
        ref = reference(veh, req)
        j_prop = prop_inertia(req["prop"]["diameter_in"])
        # referencia directa: el elegido de M2 y el comercial
        d2 = m2[veh]
        rows = [{"type": "directo", "name": "Directo (elegido en M2)", "ratio": 1, "eta": d2["eta_weighted"],
                 "mass_total_g": d2["mass"]["total"] * 1e3, "motor_mass_g": d2["mass"]["total"] * 1e3, "gear_mass_g": 0.0,
                 "endurance_rel": d2["endurance_rel"], "cost": d2["cost"]["total"], "backlash_deg": 0.0, "coaxial": True,
                 "motor_rpm_max": max(p["rpm"] for p in d2["ops"].values()),
                 "j_reflected_ratio": None, "tau_ms": None, "risks": "—", "feasible": True}]
        rc = RECON[veh]
        g_c = geometry(rc)
        j_cots = rotor_inertia({"geometry": g_c, "mass": masses(rc, g_c)})
        rows[0]["tau_ms"] = response_time(j_prop + j_cots, req) * 1e3      # referencia aproximada: rotor como el comercial
        rows[0]["j_reflected_ratio"] = j_cots / j_prop
        for gear in GEARS:
            for n in gear.ratios:
                r = geared_requirements(req, gear, n)
                rpm_max = r["constraints"]["rpm_max_twr20"]
                if rpm_max > 60_000:                                         # rodamientos chicos y ESC: límite práctico
                    rows.append({"type": gear.key, "name": gear.name, "ratio": n, "feasible": False,
                                 "why": f"el motor tendría que girar a {rpm_max:,.0f} rpm", "risks": gear.risks,
                                 "backlash_deg": gear.backlash_deg, "coaxial": gear.coaxial})
                    continue
                res = search(veh, r, ref, samples, seed=7)
                if not res:
                    rows.append({"type": gear.key, "name": gear.name, "ratio": n, "feasible": False,
                                 "why": "ningún motor cumple (eRPM del ESC, temperatura o tamaño)", "risks": gear.risks,
                                 "backlash_deg": gear.backlash_deg, "coaxial": gear.coaxial})
                    continue
                best = max(res, key=lambda e: e["endurance_rel"])
                gear_mass = r["extra_mass_kg"]
                j_ref = rotor_inertia(best) * n ** 2
                rows.append({"type": gear.key, "name": gear.name, "ratio": n, "feasible": True, "eta": best["eta_weighted"],
                             "mass_total_g": (best["mass"]["total"] + gear_mass) * 1e3, "motor_mass_g": best["mass"]["total"] * 1e3,
                             "gear_mass_g": gear_mass * 1e3, "endurance_rel": best["endurance_rel"],
                             "cost": best["cost"]["total"] + gear.cost[veh], "backlash_deg": gear.backlash_deg, "coaxial": gear.coaxial,
                             "motor_rpm_max": rpm_max, "motor": f"{best['geometry']['winding']['label']} Ø{best['design'].d_stator * 1e3:.0f}×"
                             f"{best['design'].l_stack * 1e3:.1f} mm, Kv {best['geometry']['kv']:.0f}",
                             "j_reflected_ratio": j_ref / j_prop, "tau_ms": response_time(j_prop + j_ref, req) * 1e3, "risks": gear.risks})
        feas = [x for x in rows if x["feasible"]]
        out[veh] = {"rows": rows, "best": max(feas, key=lambda x: x["endurance_rel"]), "j_prop": j_prop, "reference": ref}
    return out


def write_report(res: dict) -> None:
    L = ["# M3 · Reductores: ¿motor directo o motor rápido con reductor?", "",
         "> Generado por `motor/reductores/gearbox.py`. No editar a mano.", "",
         "Para cada reductor y relación se optimizó un motor a la medida con el mismo modelo de M2 (puntos de operación vistos "
         "desde el motor: rpm × N y torque ÷ N ÷ eficiencia del engrane, más arrastre). La comparación es del **conjunto** a nivel "
         "dron. Autonomía relativa al comercial; eficiencia útil = potencia en la hélice / potencia eléctrica.", ""]
    for veh, v in res.items():
        L += [f"## {veh}", "",
              "| Opción | N | Eficiencia útil | Masa (motor + reductor) | Autonomía | Costo | Motor a | Inercia vista por la hélice | +10 % de rpm en | Juego |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for x in sorted(v["rows"], key=lambda x: (not x["feasible"], -x.get("endurance_rel", 0))):
            if not x["feasible"]:
                L.append(f"| {x['name']} | {x['ratio']} | — | — | **no viable**: {x['why']} | — | — | — | — | {x['backlash_deg']}° |")
                continue
            rec = x["type"] == "directo"                                      # recomendado (ver conclusión)
            L.append(f"| {'**' if rec else ''}{x['name']}{' · recomendado**' if rec else ''} | {x['ratio']} | {x['eta']:.1%} | "
                     f"{x['mass_total_g']:.0f} g ({x['motor_mass_g']:.0f} + {x['gear_mass_g']:.0f}) | **{(x['endurance_rel'] - 1) * 100:+.1f} %** | "
                     f"US${x['cost']:.0f} | {x['motor_rpm_max']:,.0f} rpm | ×{1 + x['j_reflected_ratio']:.2f} la de la hélice | "
                     f"{x['tau_ms']:.0f} ms | {x['backlash_deg']}° |")
        L += ["", "**Riesgos por tipo:**", ""]
        seen = set()
        for x in v["rows"]:
            if x["type"] not in seen and x["type"] != "directo":
                seen.add(x["type"])
                L.append(f"- *{x['name']}:* {x['risks']}.")
        L.append("")
    L += ["## Conclusión", ""]
    for veh, v in res.items():
        direct = next(x for x in v["rows"] if x["type"] == "directo")
        home = [x for x in v["rows"] if x["feasible"] and x["type"] not in ("directo", "planetario_aero")]
        aero = [x for x in v["rows"] if x["feasible"] and x["type"] == "planetario_aero"]
        bh = max(home, key=lambda x: x["endurance_rel"])
        line = (f"- **{veh}:** directo {(direct['endurance_rel'] - 1) * 100:+.1f} % de autonomía (US${direct['cost']:.0f}). "
                f"Mejor reductor hecho en casa ({bh['name'].split(' (')[0].lower()}, N = {bh['ratio']}): "
                f"{(bh['endurance_rel'] - 1) * 100:+.1f} %: **pierde por {(direct['endurance_rel'] - bh['endurance_rel']) * 100:.1f} puntos**.")
        if aero:
            ba = max(aero, key=lambda x: x["endurance_rel"])
            line += (f" Un planetario comercial de aeromodelismo, con supuestos optimistas, daría {(ba['endurance_rel'] - 1) * 100:+.1f} % "
                     f"({(ba['endurance_rel'] - direct['endurance_rel']) * 100:+.1f} puntos sobre el directo) pero el conjunto costaría "
                     f"US${ba['cost']:.0f} por motor, más que el motor comercial que se quiere reemplazar.")
        L.append(line)
    L += ["", "**Por qué pierden los reductores hechos en casa:**", "",
          "- El motor rápido es chico, pero gira a 10-30 krpm: sus pérdidas en el hierro suben con la frecuencia y su eficiencia "
          "queda por debajo de la del motor directo, que ya trabaja cerca de su óptimo con la hélice lenta.",
          "- A eso se suma la pérdida del engrane (3-10 %) y el arrastre, y la masa del reductor se come el ahorro del motor.",
          "- **Armónico: descartado.** Su relación mínima (~30) pone el motor a > 100,000 rpm; además pierde 20-25 % y su pieza "
          "flexible no está hecha para girar continuo a miles de rpm.",
          "- **Cicloidal:** relación mínima ~8, motor a 30-45 krpm, excéntrico que vibra y eficiencia ~90 %. En el DS-D ningún "
          "motor cumple el límite de eRPM del ESC.",
          "- **Planetario impreso:** pierde mucho y no aguanta la vida útil. **Correa:** pesa (poleas, soporte) y no es coaxial.",
          "- **Respuesta del empuje:** la inercia del rotor del motor se multiplica por N². Con reductor, la hélice tarda 10-115 % "
          "más en acelerar, lo que vuelve menos firme el control de actitud, sobre todo con viento.",
          "",
          "**Decisión propuesta (ADR-014):** motor **directo** en el DS-I y el DS-D. El planetario comercial de aeromodelismo queda "
          "anotado como la única variante que podría ganar en autonomía, a revisar si en el futuro aparece uno durable y barato, o "
          "para un DS-H con hélices de 30\" o más.", ""]
    (INF / "M3_reductores.md").write_text("\n".join(L))
    (INF / "M3_reductores.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=6000)
    a = ap.parse_args()
    r = run(a.samples)
    write_report(r)
    for veh, v in r.items():
        for x in v["rows"]:
            if x["feasible"]:
                print(veh, x["name"][:24], x["ratio"], f"η={x['eta']:.3f} m={x['mass_total_g']:.0f}g aut={x['endurance_rel']:.3f} "
                      f"US${x['cost']:.0f} τ={x['tau_ms']:.0f}ms J×{1 + x['j_reflected_ratio']:.2f} {x.get('motor', '')}")
            else:
                print(veh, x["name"][:24], x["ratio"], "NO:", x["why"])
