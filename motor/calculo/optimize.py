"""M2 · Optimización del motor directo → motor/informes/M2_diseno.md + M2_candidatos.json + figuras

1. Validación: el modelo de design.py reconstruye los comerciales desde su geometría (Kv, R, masa).
2. Búsqueda: muestreo aleatorio + refinamiento local alrededor de los mejores, por dron. Las vueltas por diente no se
   sortean: se toma el MÁXIMO que todavía llega al empuje máximo (2 × peso a 5,000 msnm) con la batería vacía, así
   la corriente (y las pérdidas del ESC y la batería) es la mínima posible.
3. Objetivo principal: autonomía relativa del dron = (η ponderada / η comercial) × (MTOW comercial / MTOW nuevo)^1.5
   (la potencia de hover crece con el peso^1.5). Así un motor más eficiente pero más pesado no gana por error.
   El comercial se evalúa con el MISMO modelo (reconstruido desde su ficha): eficiencia y masa, modelo contra modelo.
4. Restricciones: temperatura (maniobra continua < 120 °C, máximo de 30 s), desmagnetización, eRPM del ESC, diámetro y
   alto del montaje DMI, dientes fabricables con láser (≥ 1.5 mm) y hueco para rodamientos.

    .venv/bin/python -m motor.calculo.optimize [--samples 20000]
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import asdict, replace
from pathlib import Path

import motor.calculo.design as model
from motor.calculo.design import (
    BEARING,
    CAP_THICK,
    HUB_WALL,
    RECON,
    Design,
    demag_margin,
    geometry,
    masses,
    material_cost,
    operate,
    resistance_line,
)

ROOT = Path(__file__).resolve().parents[2]
REQ = ROOT / "motor" / "requisitos" / "puntos_operacion.json"
OUT_DIR = ROOT / "motor" / "informes"
DATA = ROOT / "motor" / "requisitos" / "datos_cots" / "fichas.json"

GAP = {"DS-I": 0.5e-3, "DS-D": 0.6e-3}          # entrehierro fabricable en casa (láminas apiladas + campana impresa)
MIN_TOOTH = 1.5e-3                              # diente más angosto que se corta y apila sin deformarse
RANGES = {
    "DS-I": {"d": (28e-3, 46e-3), "l": (4e-3, 22e-3), "hm": (1.0e-3, 3.0e-3), "combos": [(12, 7), (12, 5), (18, 8), (18, 10),
                                                                                         (18, 12), (24, 11), (24, 13), (24, 14)]},
    "DS-D": {"d": (48e-3, 74e-3), "l": (6e-3, 32e-3), "hm": (1.5e-3, 4.0e-3), "combos": [(18, 8), (18, 10), (24, 11), (24, 13),
                                                                                         (24, 14), (24, 10), (36, 16), (36, 20),
                                                                                         (36, 21)]},
}
STEEL_OPTS = ["NO20", "NO27", "M270-35A"]
MAGNET_OPTS = ["N52H", "N48SH"]
T_MAG_WORST = 100.0


def max_turns(d: Design, g: dict, pmax: dict, v_avail: float) -> int:
    """Máximo de vueltas que entrega el punto máximo con la batería vacía (bobinado a 95 °C, imán a 80 °C)."""
    omega = pmax["rpm"] * 2 * math.pi / 60
    ke1 = g["ke_line_20"] / d.turns * (1 - 0.0012 * 60)
    r1 = resistance_line(d, g, 95.0) / d.turns ** 2
    torque = pmax["torque_nm"] * 1.03                               # pérdidas en vacío
    per_turn = omega * ke1 + torque * r1 / ke1 * 1.08
    return int(v_avail * 0.97 / per_turn)


def evaluate(d: Design, req: dict, ref: dict) -> dict | None:
    g = geometry(d)
    if g is None or g["w_tooth"] < MIN_TOOTH:
        return None
    c = req["constraints"]
    pts = {p["name"]: p for p in req["points"]}
    v_avail = req["battery"]["v_empty_loaded"] * req["battery"]["max_duty"]
    n = max_turns(d, g, pts["maximo_twr20"], v_avail)
    if n < 1:
        return None
    d = replace(d, turns=n)
    g = geometry(d)
    if g is None:
        return None
    m = masses(d, g)
    height = d.l_stack + 2 * g["overhang"] + CAP_THICK[d.vehicle] + 4e-3
    if 2 * g["r_out"] > c["max_diameter_mm"] * 1e-3 or height > c["max_height_mm"] * 1e-3:
        return None
    if g["r_bore"] < BEARING[d.vehicle]["od"] / 2 + HUB_WALL:
        return None
    if d.pole_pairs * pts["maximo_twr20"]["rpm"] > c["erpm_max_esc"]:
        return None
    dens = c["air_density_design"]
    prop_d = req["prop"]["diameter_in"] * 0.0254
    ops = {k: operate(d, g, m, p["torque_nm"], p["rpm"], p["thrust_n"], prop_d, dens, c["ambient_c"]) for k, p in pts.items()}
    if ops["maniobra_twr15"]["t_winding"] > c["winding_t_max_c"]:
        return None
    # máximo: corto (< 30 s). Se exige que su régimen permanente no pase de 180 °C (la constante térmica es de minutos)
    if ops["maximo_twr20"]["t_winding"] > 180 or ops["maximo_twr20"]["voltage"] > v_avail * 1.001:
        return None
    dm = demag_margin(d, g, ops["maximo_twr20"]["current"], T_MAG_WORST)
    if dm > 0.7:
        return None
    w = req["objective_weights"]
    # eficiencia útil: potencia en la hélice / potencia eléctrica (con reductor, p_useful_w < potencia en el eje del motor)
    eff = {k: pts[k].get("p_useful_w", ops[k]["p_shaft"]) / ops[k]["p_in"] for k in ops}
    eta = sum(w[k] * eff[k] for k in w) / sum(w.values())
    n_rot = req["rotors"]
    extra = req.get("extra_mass_kg", 0.0)                                        # reductor (M3)
    mtow_new = req["mtow_kg"] + n_rot * (m["total"] + extra - ref["mass_model_kg"])     # masa: modelo contra modelo
    endurance_rel = eta / ref["weighted_efficiency"] * (req["mtow_kg"] / mtow_new) ** 1.5
    cost = material_cost(d, g, m)
    return {"design": d, "geometry": g, "mass": m, "cost": cost, "ops": ops, "eff_useful": eff, "eta_weighted": eta, "endurance_rel": endurance_rel,
            "mtow_new": mtow_new, "demag": dm, "height": height, "r_line_20": resistance_line(d, g, 20)}


def random_design(veh: str, rng: random.Random, r: dict | None = None) -> Design:
    r = r or RANGES[veh]
    ns, p = rng.choice(r["combos"])
    return Design(veh, ns, p, rng.uniform(*r["d"]), rng.uniform(*r["l"]), GAP[veh], rng.uniform(*r["hm"]),
                  rng.uniform(0.15, 0.42), rng.uniform(1.35, 1.8), rng.uniform(1.2, 1.6), 1, rng.random() < 0.5,
                  steel=rng.choice(STEEL_OPTS), magnet=rng.choice(MAGNET_OPTS))


def perturb(d: Design, rng: random.Random, s: float, r: dict | None = None) -> Design:
    r = r or RANGES[d.vehicle]

    def j(x, lo, hi):
        return min(hi, max(lo, x * (1 + rng.gauss(0, s))))
    return replace(d, d_stator=j(d.d_stator, *r["d"]), l_stack=j(d.l_stack, *r["l"]), h_magnet=j(d.h_magnet, *r["hm"]),
                   slot_depth_frac=j(d.slot_depth_frac, 0.15, 0.42), b_tooth=j(d.b_tooth, 1.35, 1.8), b_yoke=j(d.b_yoke, 1.2, 1.6))


def search(veh: str, req: dict, ref: dict, samples: int, seed: int = 1) -> list[dict]:
    rng = random.Random(seed)
    ranges = req.get("ranges")
    out = []
    for _ in range(samples):
        e = evaluate(random_design(veh, rng, ranges), req, ref)
        if e:
            out.append(e)
    # refinamiento: 3 rondas alrededor de los 40 mejores en autonomía y de los 40 más livianos con buena autonomía
    for s in (0.10, 0.05, 0.02):
        seeds = sorted(out, key=lambda e: -e["endurance_rel"])[:40]
        seeds += sorted([e for e in out if e["endurance_rel"] > 1.0], key=lambda e: e["mass"]["total"])[:40]
        for e0 in seeds:
            for _ in range(samples // 400):
                e = evaluate(perturb(e0["design"], rng, s, ranges), req, ref)
                if e:
                    out.append(e)
    return out


def pareto(rows: list[dict]) -> list[dict]:
    """Frente no dominado: más autonomía, menos masa, menos costo."""
    rows = sorted(rows, key=lambda e: -e["endurance_rel"])
    front = []
    for e in rows:
        if not any(f["endurance_rel"] >= e["endurance_rel"] and f["mass"]["total"] <= e["mass"]["total"]
                   and f["cost"]["total"] <= e["cost"]["total"] for f in front):
            front.append(e)
    return front


def targets(req: dict, ref: dict) -> dict:
    """Metas del G5 en términos del modelo: +2 puntos de eficiencia, masa ≤ comercial + 10 %, materiales ≤ 30 %."""
    return {"eta_min": ref["weighted_efficiency"] + 0.02, "mass_max_kg": ref["mass_model_kg"] * 1.10,
            "cost_max_usd": req["targets"]["material_cost_max_usd"]}


def pick_candidates(rows: list[dict], req: dict, ref: dict) -> dict:
    t = targets(req, ref)
    ok_cost = [e for e in rows if e["cost"]["total"] <= t["cost_max_usd"]]
    pool = ok_cost or rows
    best = max(pool, key=lambda e: e["endurance_rel"])
    light = [e for e in pool if e["mass"]["total"] <= t["mass_max_kg"] and e["eta_weighted"] >= t["eta_min"]]
    eff = [e for e in pool if e["mass"]["total"] <= t["mass_max_kg"]]
    out = {"A_max_autonomia": best}
    if eff:
        out["B_max_eficiencia_masa_meta"] = max(eff, key=lambda e: e["eta_weighted"])
    if light:
        out["C_liviano_que_cumple"] = min(light, key=lambda e: e["mass"]["total"])
    return out


def as_json(e: dict) -> dict:
    g = {k: v for k, v in e["geometry"].items() if k != "winding"}
    w = e["geometry"]["winding"]
    return {"design": asdict(e["design"]), "label": w["label"], "kw": w["kw"], "cogging_lcm": w["cogging_lcm"],
            "coils": "".join(c[0] if c[1] > 0 else c[0].lower() for c in w["coils"]),
            "geometry": g, "kv": g["kv"], "r_line_20_ohm": e["r_line_20"], "mass": e["mass"], "cost": e["cost"],
            "eta_weighted": e["eta_weighted"], "endurance_rel": e["endurance_rel"], "mtow_new": e["mtow_new"], "demag": e["demag"],
            "height": e["height"], "ops": e["ops"]}


def cross_check() -> list[dict]:
    """El modelo reconstruye a los comerciales (geometría plausible desde nombre y ficha)."""
    f = json.loads(DATA.read_text())
    cases = [("MN4006 KV380", RECON["DS-I"]), ("M6C12 KV150", RECON["DS-D"])]
    out = []
    for name, d in cases:
        g = geometry(d)
        m = masses(d, g)
        fd = f[name]
        out.append({"motor": name, "geometry": f"{d.ns}N{2 * d.pole_pairs}P, estator Ø{d.d_stator * 1e3:.0f}×{d.l_stack * 1e3:.0f} mm, "
                    f"{d.turns} vueltas en estrella", "kv": [round(g["kv"]), fd["kv"]],
                    "r_mohm": [round(resistance_line(d, g) * 1e3), round(fd["r_line_ohm"] * 1e3)],
                    "d_out_mm": [round(2 * g["r_out"] * 1e3, 1), fd["outer_d_mm"]], "mass_g": [round(m["total"] * 1e3), round(fd["mass_kg"] * 1e3)]})
    return out


def weighted(d: Design, req: dict) -> tuple[float, dict]:
    g = geometry(d)
    m = masses(d, g)
    c = req["constraints"]
    ops = {p["name"]: operate(d, g, m, p["torque_nm"], p["rpm"], p["thrust_n"], req["prop"]["diameter_in"] * 0.0254,
                              c["air_density_design"], c["ambient_c"]) for p in req["points"]}
    w = req["objective_weights"]
    return sum(w[k] * ops[k]["efficiency"] for k in w) / sum(w.values()), ops


def reference(veh: str, req: dict) -> dict:
    """Comercial reconstruido evaluado con el mismo modelo (y, como dato, su eficiencia de M1)."""
    d = RECON[veh]
    eta, ops = weighted(d, req)
    g = geometry(d)
    m1 = json.loads((OUT_DIR / "M1_referencia_cots.json").read_text())[veh]["weighted_efficiency"]
    return {"name": req["reference_cots"]["name"], "weighted_efficiency": eta, "mass_model_kg": masses(d, g)["total"],
            "mass_real_kg": req["reference_cots"]["mass_kg"], "m1_weighted_efficiency": m1,
            "hover_efficiency": ops["hover_4500m_0C"]["efficiency"], "kv": g["kv"], "r_line_20": resistance_line(d, g)}


def robustness(e: dict, req: dict, ref_design: Design) -> list[dict]:
    """¿Sigue ganando si el modelo es optimista? Mismo cambio aplicado al candidato y al comercial reconstruido."""
    d0 = e["design"]
    cases = [("modelo base", {}, {}),
             ("hierro pierde lo de catálogo (K_IRON 1.0)", {"K_IRON": 1.0}, {}),
             ("entrehierro +0.2 mm (campana con juego)", {}, {"gap": d0.gap + 0.2e-3}),
             ("bobinado peor: relleno 0.33", {}, {"fill": 0.33}),
             ("imanes N42SH (más baratos)", {}, {"magnet": "N42SH"}),
             ("enfriamiento a la mitad (K_THERMAL/2)", {"K_THERMAL": model.K_THERMAL / 2}, {})]
    out = []
    saved = {k: getattr(model, k) for k in ("K_IRON", "K_THERMAL")}
    for label, consts, changes in cases:
        for k, v in consts.items():
            setattr(model, k, v)
        try:
            dc = replace(d0, **changes)
            eta_c, ops = weighted(dc, req)
            eta_r, _ = weighted(ref_design, req)
            out.append({"case": label, "eta": eta_c, "eta_cots": eta_r, "gain_points": (eta_c - eta_r) * 100,
                        "t_maniobra": ops["maniobra_twr15"]["t_winding"],
                        "reaches_max": ops["maximo_twr20"]["voltage"] <= req["battery"]["v_empty_loaded"] * req["battery"]["max_duty"]})
        finally:
            for k, v in saved.items():
                setattr(model, k, v)
    return out


def run(samples: int) -> dict:
    req_all = json.loads(REQ.read_text())
    res = {"cross_check": cross_check(), "vehicles": {}}
    for veh in ("DS-I", "DS-D"):
        req = req_all[veh]
        ref = reference(veh, req)
        rows = search(veh, req, ref, samples)
        front = pareto(rows)
        cands = pick_candidates(rows, req, ref)
        by_combo, by_steel = {}, {}
        for e in rows:
            k = e["geometry"]["winding"]["label"]
            if k not in by_combo or e["endurance_rel"] > by_combo[k]["endurance_rel"]:
                by_combo[k] = e
            s = e["design"].steel
            if s not in by_steel or e["endurance_rel"] > by_steel[s]["endurance_rel"]:
                by_steel[s] = e
        res["vehicles"][veh] = {
            "evaluated_valid": len(rows), "reference": ref, "targets": targets(req, ref), "mtow_kg": req["mtow_kg"],
            "robustness": {k: robustness(e, req, RECON[veh]) for k, e in cands.items()},
            "candidates": {k: as_json(e) for k, e in cands.items()},
            "best_by_combo": {k: {"endurance_rel": e["endurance_rel"], "eta": e["eta_weighted"], "mass_g": e["mass"]["total"] * 1e3,
                                  "cost": e["cost"]["total"], "d_mm": e["design"].d_stator * 1e3, "l_mm": e["design"].l_stack * 1e3}
                              for k, e in sorted(by_combo.items(), key=lambda kv: -kv[1]["endurance_rel"])},
            "best_by_steel": {k: {"endurance_rel": e["endurance_rel"], "eta": e["eta_weighted"], "mass_g": e["mass"]["total"] * 1e3,
                                  "cost": e["cost"]["total"]} for k, e in by_steel.items()},
            "front": [{"endurance_rel": e["endurance_rel"], "eta": e["eta_weighted"], "mass_g": e["mass"]["total"] * 1e3,
                       "cost": e["cost"]["total"], "label": e["geometry"]["winding"]["label"]} for e in front],
            "cloud": [[round(e["mass"]["total"] * 1e3, 1), round(e["eta_weighted"], 4), round(e["endurance_rel"], 4),
                       round(e["cost"]["total"], 1)] for e in rows[:: max(1, len(rows) // 4000)]],
        }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "M2_candidatos.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float) + "\n")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=40000)
    a = ap.parse_args()
    r = run(a.samples)
    for v, x in r["vehicles"].items():
        print(v, x["evaluated_valid"], {k: (round(y, 4) if isinstance(y, float) else y) for k, y in x["reference"].items()}, x["targets"])
        for k, c in x["candidates"].items():
            d = c["design"]
            print(f"  {k}: {c['label']} Ø{d['d_stator'] * 1e3:.1f}×{d['l_stack'] * 1e3:.1f} hm={d['h_magnet'] * 1e3:.2f} N={d['turns']}"
                  f"{'Δ' if d['delta'] else 'Y'} {d['steel']} {d['magnet']} kv={c['kv']:.0f} R={c['r_line_20_ohm'] * 1e3:.0f}mΩ "
                  f"η={c['eta_weighted']:.3f} m={c['mass']['total'] * 1e3:.0f}g US${c['cost']['total']:.1f} aut={c['endurance_rel']:.3f} "
                  f"Tman={c['ops']['maniobra_twr15']['t_winding']:.0f}°C Tmax={c['ops']['maximo_twr20']['t_winding']:.0f}°C "
                  f"hoverη={c['ops']['hover_4500m_0C']['efficiency']:.3f} Øout={c['geometry']['r_out'] * 2e3:.1f}")
        print("  por combo:", {k: (round(b["endurance_rel"], 3), round(b["mass_g"])) for k, b in x["best_by_combo"].items()})
        print("  por acero:", {k: (round(b["endurance_rel"], 3), round(b["eta"], 3)) for k, b in x["best_by_steel"].items()})
        for k, rb in x["robustness"].items():
            print("  robustez", k, [(r["case"][:22], round(r["gain_points"], 2), r["reaches_max"]) for r in rb])
    print(r["cross_check"])
