#!/usr/bin/env python3
"""S10-03/04/05 · Análisis del banco de empuje.

Entrada: CSV crudos de acquire.py (noload y sweep del mismo motor + hélice). Salida:
  - Kv e I0 (ensayo sin hélice); resistencia efectiva motor + ESC + cables (ajuste de pérdidas P_bat − P_mec = a + b·I²)
  - Curvas por escalón: empuje, torque, rpm, corriente, potencia, eficiencia, g/W; CT y CP de la hélice
  - Corrección a la altura de trabajo (4,500 msnm, 0 °C y 5,000 msnm, 15 °C): rpm, corriente y potencia de hover,
    empuje máximo y empuje/peso, contra lo que predijo la selección COTS (S09)
  - engineering/data/motors/<id>.json (Kv, I0, Rm medidos) y engineering/data/props/<id>.csv (rpm, ct, cp, formato
    de PropTable.from_csv) → los usan la selección COTS, el dimensionamiento y el SDF
  - Sección del informe docs/ingenieria/motor_cots_report.md

    .venv/bin/python tools/bench/analyze.py --noload data/bench/…noload….csv --sweep data/bench/…sweep….csv --vehicle DS-D
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchlib import ROOT, Calibration, physical, read_raw  # noqa: E402

MOTORS_DIR = ROOT / "engineering" / "data" / "motors"
PROPS_DIR = ROOT / "engineering" / "data" / "props"
REPORT = ROOT / "docs" / "ingenieria" / "motor_cots_report.md"
G0 = 9.80665
INCH = 0.0254


def steps(phys: dict, avg_s: float = 2.0) -> list[dict]:
    """Promedio de los últimos avg_s segundos de cada escalón de throttle."""
    thr, t = phys["throttle_us"], phys["t"]
    out = []
    for us in np.unique(thr):
        idx = np.where(thr == us)[0]
        if len(idx) < 10:
            continue
        sel = idx[t[idx] >= t[idx].max() - avg_s]
        out.append({"throttle_us": int(us), **{k: float(np.mean(phys[k][sel])) for k in ("thrust_n", "torque_nm", "rpm", "v", "i", "motor_temp")}})
    return out


MAX_DUTY = 0.97          # misma convención que engineering/motor.py: voltaje útil del ESC a fondo


def noload_fit(st: list[dict]) -> dict:
    """Kv con el escalón a fondo sin hélice: Kv = rpm / (V · duty máx.) (sin carga la caída I·R es despreciable).
    I0 = corriente del motor sin carga ≈ corriente de batería / duty en ese escalón."""
    pts = [s for s in st if s["rpm"] > 500]
    full = max(pts, key=lambda s: s["throttle_us"])
    kv = full["rpm"] / (full["v"] * MAX_DUTY)
    i0 = full["i"] / MAX_DUTY
    return {"kv": round(kv, 1), "i0": round(i0, 3)}


def sweep_fit(st: list[dict], diameter_m: float, rho: float) -> dict:
    pts = [s for s in st if s["rpm"] > 300 and s["thrust_n"] > 0.2]
    rpm = np.array([s["rpm"] for s in pts])
    n = rpm / 60
    T = np.array([s["thrust_n"] for s in pts])
    Q = np.array([s["torque_nm"] for s in pts])
    V = np.array([s["v"] for s in pts])
    current = np.array([s["i"] for s in pts])
    p_mech = Q * 2 * math.pi * n
    p_bat = V * current
    ct = T / (rho * n ** 2 * diameter_m ** 4)
    cp = p_mech / (rho * n ** 3 * diameter_m ** 5)
    # pérdidas eléctricas: P_bat − P_mec = a + b·I²  (a ≈ pérdidas sin carga, b = R efectiva motor + ESC + cables)
    A = np.column_stack([np.ones_like(current), current ** 2])
    (a, b), *_ = np.linalg.lstsq(A, p_bat - p_mech, rcond=None)
    table = [{"throttle_us": s["throttle_us"], "rpm": round(s["rpm"]), "thrust_n": round(s["thrust_n"], 2),
              "thrust_g": round(s["thrust_n"] / G0 * 1000), "torque_nm": round(s["torque_nm"], 4), "v": round(s["v"], 2),
              "i": round(s["i"], 2), "p_bat_w": round(s["v"] * s["i"], 1),
              "p_mech_w": round(s["torque_nm"] * 2 * math.pi * s["rpm"] / 60, 1),
              "g_per_w": round(s["thrust_n"] / G0 * 1000 / max(s["v"] * s["i"], 1e-6), 2),
              "eff": round(s["torque_nm"] * 2 * math.pi * s["rpm"] / 60 / max(s["v"] * s["i"], 1e-6), 3),
              "motor_temp": round(s["motor_temp"], 1)} for s in pts]
    return {"rpm": rpm, "ct": ct, "cp": cp, "loss_a_w": float(a), "r_eff_ohm": float(b), "table": table,
            "rpm_max": float(rpm.max()), "v_mean": float(V.mean())}


def at_altitude(fit: dict, kv: float, diameter_m: float, rho: float, thrust_n: float, v_bus: float) -> dict:
    """Hover a otra densidad: rpm para el empuje pedido (CT medido), potencia mecánica (CP) y corriente de batería."""
    ct = float(np.interp(fit["rpm_max"] * 0.6, fit["rpm"], fit["ct"]))
    for _ in range(5):                                          # CT varía poco con las rpm: dos vueltas bastan
        n = math.sqrt(thrust_n / (ct * rho * diameter_m ** 4))
        ct = float(np.interp(n * 60, fit["rpm"], fit["ct"]))
        cp = float(np.interp(n * 60, fit["rpm"], fit["cp"]))
    p_mech = cp * rho * n ** 3 * diameter_m ** 5
    # P_bat = P_mec + a + b·I², con P_bat = V·I → b·I² − V·I + (P_mec + a) = 0
    a, b = fit["loss_a_w"], fit["r_eff_ohm"]
    disc = v_bus ** 2 - 4 * b * (p_mech + a)
    i = (v_bus - math.sqrt(max(disc, 0))) / (2 * b) if b > 1e-6 else (p_mech + a) / v_bus
    # empuje máximo: las rpm a fondo suben algo con menos carga; se toman las medidas (conservador)
    t_max = float(np.interp(fit["rpm_max"], fit["rpm"], fit["ct"])) * rho * (fit["rpm_max"] / 60) ** 2 * diameter_m ** 4
    return {"rpm": round(n * 60), "p_mech_w": round(p_mech, 1), "current_a": round(i, 2), "p_bat_w": round(i * v_bus, 1),
            "t_max_n": round(t_max, 1)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--noload", type=Path, required=True)
    ap.add_argument("--sweep", type=Path, required=True)
    ap.add_argument("--vehicle", choices=["DS-I", "DS-D"], required=True)
    ap.add_argument("--calibration", type=Path)
    a = ap.parse_args()
    cal = Calibration.load(a.calibration)
    rows_nl, meta_nl = read_raw(a.noload)
    rows_sw, meta = read_raw(a.sweep)
    nl = noload_fit(steps(physical(rows_nl, cal)))
    d = meta.prop_diameter_in * INCH
    rho = meta.density()
    fit = sweep_fit(steps(physical(rows_sw, cal)), d, rho)

    from engineering.atmosphere import air
    sel = json.loads((ROOT / "engineering/data/results/cots_selection.json").read_text())["selected"][a.vehicle]
    n_rot = 6 if a.vehicle == "DS-D" else 4
    hover_thrust = sel["mtow_kg"] * G0 / n_rot
    alt = {}
    for label, (h, tc) in {"4,500 msnm, 0 °C": (4500, 0), "5,000 msnm, 15 °C": (5000, 15)}.items():
        alt[label] = at_altitude(fit, nl["kv"], d, air(h, tc).density, hover_thrust, fit["v_mean"])
    twr = alt["5,000 msnm, 15 °C"]["t_max_n"] / hover_thrust
    cat = next(m for m in json.loads((ROOT / "engineering/data/results/cots_selection.json").read_text())["motors"]
               if m["name"] == meta.motor)
    res = {"motor": meta.motor, "prop": meta.prop, "vehicle": a.vehicle, "date": dt.date.today().isoformat(),
           "simulated": "simulado" in meta.notes, "site_density": round(rho, 4),
           "kv_measured": nl["kv"], "kv_catalog": cat["kv"], "kv_error_pct": round(100 * (nl["kv"] / cat["kv"] - 1), 1),
           "i0_measured": nl["i0"], "r_eff_ohm": round(fit["r_eff_ohm"], 4), "loss_a_w": round(fit["loss_a_w"], 1),
           "ct_mean": round(float(np.mean(fit["ct"])), 4), "cp_mean": round(float(np.mean(fit["cp"])), 4),
           "altitude": alt, "twr_5000m_per_motor": round(twr, 2),
           "hover_p_bat_model_w": sel["hover_p_battery_per_motor_w"], "table": fit["table"]}
    res["checks"] = {"Kv dentro de ±5 % del catálogo": abs(res["kv_error_pct"]) <= 5,
                     "potencia de hover ≤ modelo + 10 %": alt["4,500 msnm, 0 °C"]["p_bat_w"] <= 1.10 * sel["hover_p_battery_per_motor_w"],
                     "empuje/peso ≥ 2.0 a 5,000 msnm": twr >= 2.0,
                     "temperatura máx. del barrido ≤ 80 °C": max(r["motor_temp"] for r in fit["table"]) <= 80}
    slug = "".join(ch if ch.isalnum() else "_" for ch in f"{meta.motor}_{meta.prop}")[:60]
    MOTORS_DIR.mkdir(parents=True, exist_ok=True)
    PROPS_DIR.mkdir(parents=True, exist_ok=True)
    if not res["simulated"]:          # los datos simulados no reemplazan al catálogo
        (MOTORS_DIR / f"{slug}.json").write_text(json.dumps({"name": meta.motor, "kv": nl["kv"], "i0": nl["i0"],
                                                             "rm": round(fit["r_eff_ohm"], 4), "source": f"banco {res['date']}"},
                                                            indent=2, ensure_ascii=False) + "\n")
        with open(PROPS_DIR / f"{slug}.csv", "w") as f:
            f.write("rpm,ct,cp\n" + "".join(f"{r:.0f},{c:.5f},{p:.5f}\n" for r, c, p in zip(fit["rpm"], fit["ct"], fit["cp"])))
    out = a.sweep.parent / f"{slug}_resultado.json"
    out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    # una corrida simulada no toca el informe oficial: el suyo va junto a los datos
    write_report_section(res, a.sweep.parent / "motor_cots_report_simulado.md" if res["simulated"] else REPORT)
    print(json.dumps({k: v for k, v in res.items() if k != "table"}, indent=2, ensure_ascii=False))


def write_report_section(res: dict, report: Path = REPORT):
    """Agrega o reemplaza la sección del motor en el informe del S10."""
    head = f"## {res['motor']} · hélice {res['prop']} ({res['vehicle']})"
    t = res["table"]
    alt = res["altitude"]
    body = [head, "",
            f"- Ensayo del {res['date']}{' — **SIMULADO con el modelo, no es una medición**' if res['simulated'] else ''}; "
            f"densidad del aire en el banco {res['site_density']} kg/m³.",
            f"- Kv medido **{res['kv_measured']}** rpm/V (catálogo {res['kv_catalog']}, {res['kv_error_pct']:+.1f} %); "
            f"I0 {res['i0_measured']} A; resistencia efectiva motor + ESC + cables {res['r_eff_ohm']} Ω.",
            f"- Hélice: CT medio {res['ct_mean']}, CP medio {res['cp_mean']}.", "",
            "| Throttle | rpm | Empuje | Corriente | P batería | g/W | Eficiencia | Temp. |", "|---|---|---|---|---|---|---|---|"]
    body += [f"| {r['throttle_us']} µs | {r['rpm']:,} | {r['thrust_g']:,} g | {r['i']} A | {r['p_bat_w']} W | {r['g_per_w']} | "
             f"{r['eff']:.0%} | {r['motor_temp']} °C |" for r in t[:: max(1, len(t) // 10)]]
    body += ["", "| Altura | rpm de hover | Corriente de batería por motor | P batería por motor | Empuje máx. por motor |", "|---|---|---|---|---|"]
    body += [f"| {k} | {v['rpm']:,} | {v['current_a']} A | {v['p_bat_w']} W (modelo S09: {res['hover_p_bat_model_w']} W) | "
             f"{v['t_max_n'] / G0:.2f} kgf |" for k, v in alt.items()]
    body += ["", f"Empuje/peso a 5,000 msnm: **{res['twr_5000m_per_motor']}**.", "",
             "| Criterio | Resultado |", "|---|---|", *[f"| {k} | {'✅' if v else '❌'} |" for k, v in res["checks"].items()], ""]
    txt = report.read_text() if report.exists() else (
        "# Informe de motores COTS en el banco (S10-03/04/05)\n\n"
        "> Generado por `tools/bench/analyze.py`. Cada sección es un motor + hélice. Las corridas SIMULADAS solo prueban "
        "la cadena de análisis: el informe real lo producen los ensayos del S10.\n\n")
    if head in txt:
        start = txt.index(head)
        nxt = txt.find("\n## ", start + 1)
        txt = txt[:start] + "\n".join(body) + ("\n" + txt[nxt + 1:] if nxt != -1 else "")
    else:
        txt = txt.rstrip() + "\n\n" + "\n".join(body)
    report.write_text(txt)


if __name__ == "__main__":
    main()
