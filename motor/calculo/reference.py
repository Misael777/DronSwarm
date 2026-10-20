"""M1 · Modelo de referencia de los motores comerciales → motor/informes/M1_referencia_cots.md + JSON

Calibra el modelo de pérdidas (loss_model.py) con la ficha y, si existe, con la tabla de banco del fabricante, y
calcula la eficiencia y el reparto de pérdidas de cada comercial en los puntos de operación de M0. Ese es el número
que el motor propio tiene que superar. Cuando haya datos del banco propio (S10, tools/bench) se agregan aquí.

    .venv/bin/python -m motor.calculo.reference
"""

from __future__ import annotations

import json
from pathlib import Path

from motor.calculo.loss_model import MotorModel, fit_to_bench, read_bench

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "motor" / "requisitos" / "datos_cots"
REQ = ROOT / "motor" / "requisitos" / "puntos_operacion.json"
OUT_JSON = ROOT / "motor" / "informes" / "M1_referencia_cots.json"
OUT_MD = ROOT / "motor" / "informes" / "M1_referencia_cots.md"
COTS_OF = {"DS-I": "MN4006 KV380", "DS-D": "M6C12 KV150"}
T_WIND = {"hover": 55.0, "maniobra": 75.0, "maximo": 95.0}      # supuesto hasta el térmico de M5 (ambiente 20 °C)
DEFAULT_SPLIT = 0.35            # sin tabla: reparto ajustado en el MN4006 con su Kv de ficha


def t_wind_for(point: str) -> float:
    return next(v for k, v in T_WIND.items() if point.startswith(k))


def build(vehicle: str) -> tuple[MotorModel, dict]:
    f = json.loads((DATA / "fichas.json").read_text())[COTS_OF[vehicle]]
    if f.get("bench_csv"):
        m, info = fit_to_bench(COTS_OF[vehicle], f["kv"], f["r_line_ohm"], f["i0_a"], f["i0_at_v"], read_bench(DATA / f["bench_csv"]),
                               f["bench_v"], f["bench_surface_t_full_c"], mass_kg=f["mass_kg"], i_max=f["i_max_a"])
        info["calibration"] = "ficha + tabla de banco del fabricante"
    else:
        m = MotorModel.from_noload(COTS_OF[vehicle], f["kv"], f["r_line_ohm"], f["i0_a"], f["i0_at_v"],
                                   split=DEFAULT_SPLIT, mass_kg=f["mass_kg"], i_max=f["i_max_a"])
        info = {"split": DEFAULT_SPLIT, "eta_esc": None, "kv_scale": 1.0, "rows": [],
                "calibration": "solo ficha (I0 y R); reparto de pérdidas en vacío copiado del MN4006 — se mide en el banco (S10)"}
    info["datasheet"] = f
    info["kv_sensitivity"] = kv_sensitivity(vehicle, f)
    return m, info


def kv_sensitivity(vehicle: str, f: dict) -> list[dict]:
    """Eficiencia en hover si el Kv efectivo fuera mayor que el de la ficha (adelanto de fase del ESC, tolerancia)."""
    req = json.loads(REQ.read_text())[vehicle]
    hov = next(p for p in req["points"] if p["name"] == "hover_4500m_0C")
    out = []
    for k in (1.0, 1.05, 1.10, 1.15):
        if f.get("bench_csv"):
            m, fit = fit_to_bench("s", f["kv"], f["r_line_ohm"], f["i0_a"], f["i0_at_v"], read_bench(DATA / f["bench_csv"]),
                                  f["bench_v"], f["bench_surface_t_full_c"], kv_scale=k)
            err = fit["eff_error_rms_points"]
        else:
            m, err = MotorModel.from_noload("s", f["kv"] * k, f["r_line_ohm"], f["i0_a"], f["i0_at_v"], split=DEFAULT_SPLIT), None
        out.append({"kv_scale": k, "hover_efficiency": round(m.operate(hov["torque_nm"], hov["rpm"], T_WIND["hover"])["efficiency"], 4),
                    "fit_error_rms_points": err})
    return out


def evaluate(vehicle: str, m: MotorModel, req: dict) -> dict:
    out, wsum, wtot = [], 0.0, 0.0
    weights = req["objective_weights"]
    for p in req["points"]:
        tw = t_wind_for(p["name"])
        op = m.operate(p["torque_nm"], p["rpm"], tw)
        loss = op["p_in"] - op["p_shaft"]
        out.append({"point": p["name"], "rpm": p["rpm"], "torque_nm": p["torque_nm"], "t_wind_c": tw,
                    "current_a": round(op["current"], 2), "voltage_v": round(op["voltage"], 2), "efficiency": round(op["efficiency"], 4),
                    "p_loss_w": round(loss, 1), "copper_share": round(op["p_copper"] / loss, 3), "noload_share": round(op["p_noload"] / loss, 3),
                    "within_i_max": op["current"] <= m.i_max})
        if p["name"] in weights:
            wsum += weights[p["name"]] * op["efficiency"]
            wtot += weights[p["name"]]
    return {"points": out, "weighted_efficiency": round(wsum / wtot, 4)}


def run() -> dict:
    req = json.loads(REQ.read_text())
    res = {}
    for v in ("DS-I", "DS-D"):
        m, info = build(v)
        ev = evaluate(v, m, req[v])
        res[v] = {"model": {"name": m.name, "kv_effective": round(m.kv, 1), "r20_ohm": m.r20, "c1": m.c1, "c2": m.c2,
                            "mass_kg": m.mass_kg, "i_max_a": m.i_max}, "fit": info, **ev}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=float) + "\n")
    write_report(res)
    return res


def write_report(res: dict) -> None:
    L = ["# M1 · Modelo de referencia de los motores comerciales", "",
         "> Generado por `motor/calculo/reference.py`. No editar a mano.", "",
         "El motor propio se diseña con el **mismo** modelo de pérdidas que aquí reproduce a los comerciales. Así la "
         "comparación es justa: cualquier error del modelo afecta igual a los dos.", "",
         "Modelo: pérdidas en cobre I²R (R sube 0.39 %/K) + pérdidas en vacío c1·ω + c2·ω² (hierro, rodamientos, aire), "
         "con el imán más débil en caliente (−0.12 %/K). Temperaturas del bobinado supuestas hasta el térmico de M5: "
         + ", ".join(f"{k} {v:.0f} °C" for k, v in T_WIND.items()) + ".", ""]
    for v, r in res.items():
        f, fit, mo = r["fit"]["datasheet"], r["fit"], r["model"]
        L += [f"## {v} · {mo['name']} ({f['configuration']}, Ø{f['outer_d_mm']}×{f['height_mm']} mm, {f['mass_kg'] * 1000:.0f} g)", "",
              f"- Ficha: Kv {f['kv']}, R {f['r_line_ohm'] * 1000:.0f} mΩ, I0 {f['i0_a']} A a {f['i0_at_v']} V, Imax {f['i_max_a']} A. Fuente: {f['source']}.",
              f"- Calibración: {fit['calibration']}. Kv efectivo {mo['kv_effective']} rpm/V (×{fit['kv_scale']}), "
              f"pérdidas en vacío {fit['split']:.0%} lineales con la velocidad"
              + (f", ESC {fit['eta_esc']:.1%}." if fit["eta_esc"] else "."),
              "- Sensibilidad al Kv efectivo (los datos no lo separan del ESC): eficiencia en hover "
              + ", ".join(f"{s['hover_efficiency']:.1%} con Kv×{s['kv_scale']:.2f}"
                          + (f" (ajuste {s['fit_error_rms_points']} pt)" if s["fit_error_rms_points"] is not None else "")
                          for s in fit["kv_sensitivity"]) + ". **La meta usa el valor más alto** (lo conservador)."]
        if fit["rows"]:
            L += [f"- **Error contra la tabla del fabricante: {fit['eff_error_rms_points']} puntos RMS** (máx. {fit['eff_error_max_points']}). "
                  "La tabla redondea el torque a 0.01 N·m, lo que solo ya mete ±1-3 puntos a carga baja.", "",
                  "| Acelerador | rpm | Torque | Corriente medida | Corriente modelo | Eficiencia sistema medida | Modelo |", "|---|---|---|---|---|---|---|"]
            for row in fit["rows"]:
                L.append(f"| {row['throttle']:.0%} | {row['rpm']:.0f} | {row['torque_nm']:.2f} | {row['current_meas_a']:.1f} A | "
                         f"{row['current_model_a']:.2f} A | {row['eff_system_meas']:.1%} | {row['eff_system_model']:.1%} |")
        L += ["", "**En los puntos de operación del dron (motor solo, sin ESC):**", "",
              "| Punto | rpm | Torque | Bobinado | Corriente | Eficiencia | Pérdidas | Cobre / vacío |", "|---|---|---|---|---|---|---|---|"]
        for p in r["points"]:
            warn = "" if p["within_i_max"] else " ⚠ > Imax"
            L.append(f"| {p['point']} | {p['rpm']:,} | {p['torque_nm']:.3f} N·m | {p['t_wind_c']:.0f} °C | {p['current_a']:.1f} A{warn} | "
                     f"**{p['efficiency']:.1%}** | {p['p_loss_w']:.1f} W | {p['copper_share']:.0%} / {p['noload_share']:.0%} |")
        top = max(s["hover_efficiency"] for s in fit["kv_sensitivity"])
        L += ["", f"**Eficiencia ponderada del comercial: {r['weighted_efficiency']:.1%}** (pesos de M0); en hover, a superar: "
              f"**{top:.1%}** (extremo alto de la sensibilidad).", ""]
    di, dd = (res[v]["points"][0] for v in ("DS-I", "DS-D"))
    L += ["## Qué dice esto para el diseño propio", "",
          f"- **En hover, la mayor parte de las pérdidas es cobre:** {di['copper_share']:.0%} en el MN4006 y {dd['copper_share']:.0%} en "
          "el M6C12. Los comerciales son motores livianos con bobinados de resistencia alta para su hélice. "
          "**Ahí está el margen del diseño propio:** más cobre (estator más largo o más ancho, mejor relleno de ranura) "
          "baja las pérdidas I²R, a cambio de algo de masa. M2 busca el punto óptimo.",
          "- Las pérdidas en vacío (hierro y rodamientos) son la parte menor en hover, pero crecen con la frecuencia: "
          "láminas delgadas y no exagerar el número de polos.",
          "- A fondo domina todavía más el cobre: el diseño propio tiene que cuidar la temperatura (M5).",
          "- Se recalibra con el banco propio (S10) cuando lleguen los motores: la tabla del MN4006 es del fabricante "
          "y la del M6C12 no existe en texto.", "",
          "## Hallazgo para el S09 (decisión pendiente del G2)", "",
          "La ficha real del M6C12 (90 mΩ, 0.67 A, **36.18 A máx.**, 1,725 W) difiere de los valores estimados que usa "
          "`engineering/cots.py` (100 mΩ, 0.9 A, 45 A, 1,900 W). El fabricante recomienda hélices de 21-24\". Con esos datos:",
          "",
          "| Hélice | Autonomía (req. ≥ 20 min) | Empuje/peso a 5,000 msnm | Corriente a fondo |", "|---|---|---|---|",
          "| 26\" (línea base actual) | 21.9 min | 2.29 | 36.2 A: **justo en el límite** del motor |",
          "| 24\" (recomendada por MAD) | 20.6 min | 2.38 | 34.5 A |",
          "",
          "La selección automática pasaría a 24\". No se cambió: la línea base (26\", CAD, SITL, parámetros, BOM) queda "
          "hasta la decisión del G2. El motor propio del DS-D se diseña con margen de corriente para cualquiera de las dos.", ""]
    OUT_MD.write_text("\n".join(L))


if __name__ == "__main__":
    for v, r in run().items():
        print(v, r["model"]["kv_effective"], r["fit"].get("eff_error_rms_points"), r["weighted_efficiency"],
              [(p["point"], p["efficiency"], p["current_a"], p["copper_share"]) for p in r["points"]])
