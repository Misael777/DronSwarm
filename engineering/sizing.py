"""S04 · Dimensionamiento de DS-I y DS-D por escenarios de requisitos + informe de diseño preliminar.

    .venv/bin/python -m engineering.sizing

Salidas:
    engineering/data/results/validation.json      calibración del modelo (S03-07)
    engineering/data/results/sizing_scenarios.json todos los escenarios con su mejor diseño
    engineering/data/results/ds-i_sizing.json      diseño recomendado DS-I (S04-03)
    engineering/data/results/ds-d_sizing.json      diseño recomendado DS-D (S04-04)
    docs/ingenieria/diseno_preliminar.md           informe (S04-07)
"""

import json
from datetime import date
from pathlib import Path

from . import DATA
from .atmosphere import air
from .optimizer import sweep
from .safety_factors import all_factors, design_cases
from .validation import calibrate

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "ingenieria" / "diseno_preliminar.md"
MTOW_TARGET = {"DS-I": 2.5, "DS-D": 16.0, "DS-H": 30.0}
BOM_TARGET = {"DS-I": 600, "DS-D": 1600, "DS-H": 3000}

SCENARIOS = {
    "DS-I": [
        ("A", "Requisito actual del PRD: ≥ 35 min con batería al final de su vida", {}),
        ("B", "≥ 35 min con batería nueva (a 4,500 msnm, 0 °C, aterrizando con 10 %)", {"endurance_basis": "new"}),
        ("C", "≥ 30 min con batería nueva (el mínimo de targets.md)", {"endurance_basis": "new", "hover_endurance_min": 30}),
        ("D", "C sin RTK ni computadora a bordo (versión base; RTK opcional)",
         {"endurance_basis": "new", "hover_endurance_min": 30, "remove_equipment": ["rtk_module", "companion_computer"]}),
        ("E", "≥ 25 min con batería al final de su vida", {"hover_endurance_min": 25}),
    ],
    "DS-D": [
        ("A", "Requisito actual del PRD: 5 kg, ≥ 25 min con batería al final de su vida", {}),
        ("B", "5 kg, ≥ 25 min con batería nueva", {"endurance_basis": "new"}),
        ("C", "5 kg, ≥ 20 min con batería nueva", {"endurance_basis": "new", "hover_endurance_min": 20}),
        ("D", "4 kg (mínimo de targets.md), ≥ 20 min con batería nueva",
         {"endurance_basis": "new", "hover_endurance_min": 20, "payload_kg": 4.0}),
        ("E", "5 kg, ≥ 15 min con batería nueva (manda la misión de entrega de 3 km)",
         {"endurance_basis": "new", "hover_endurance_min": 15}),
    ],
    "DS-H": [
        ("A", "10 kg, ≥ 15 min en hover con batería nueva + entrega de 3 km", {}),
        ("B", "10 kg, ≥ 20 min en hover con batería nueva", {"hover_endurance_min": 20}),
    ],
}
RECOMMENDED = {"DS-I": "D", "DS-D": "C", "DS-H": "A"}


def summary(d) -> dict:
    p = d.performance
    return {"prop": d.prop, "battery": d.battery, "kv": d.kv, "mtow_kg": d.mtow_kg, "bom_usd": d.bom_cost_usd,
            "endurance_eol_min": p["endurance_eol_min"], "endurance_new_min": p["endurance_new_min"],
            "endurance_cold_min": p["endurance_cold_min"], "endurance_dji_style_min": p["endurance_dji_style_min"],
            "hover_power_w": p["hover_power_w_4500m"]}


def run() -> dict:
    cal = calibrate()
    k = cal["cd0_scale"]
    (DATA / "results").mkdir(parents=True, exist_ok=True)
    (DATA / "results" / "validation.json").write_text(json.dumps(cal, indent=2, ensure_ascii=False) + "\n")
    out = {"date": date.today().isoformat(), "cd0_scale": k, "vehicles": {}}
    for vehicle, scenarios in SCENARIOS.items():
        out["vehicles"][vehicle] = []
        for code, text, ov in scenarios:
            r = sweep(vehicle, k, ov)
            best, light = r.best, r.lightest
            row = {"code": code, "description": text, "overrides": ov, "evaluated": r.evaluated,
                   "feasible": len(r.feasible), "rejected": r.rejected,
                   "best": summary(best) if best else None, "lightest": summary(light) if light else None}
            if best:
                row["best_full"] = best.to_dict()
            print(f"{vehicle} {code}: {len(r.feasible)}/{r.evaluated} factibles"
                  + (f" · mejor {best.prop} {best.battery} {best.mtow_kg} kg US${best.bom_cost_usd}" if best else ""))
            out["vehicles"][vehicle].append(row)
    (DATA / "results" / "sizing_scenarios.json").write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n")
    for vehicle, code in RECOMMENDED.items():
        row = next(r for r in out["vehicles"][vehicle] if r["code"] == code)
        if row.get("best_full"):
            name = vehicle.lower() + "_sizing.json"
            (DATA / "results" / name).write_text(json.dumps({"scenario": code, "description": row["description"],
                                                             **row["best_full"]}, indent=2, ensure_ascii=False) + "\n")
    write_report(out, cal)
    return out


def _fmt(v, nd=1):
    return f"{v:,.{nd}f}" if isinstance(v, (int, float)) else str(v)


def write_report(out: dict, cal: dict) -> None:
    env = design_cases()["environment"]
    sf = all_factors()
    a_thr = air(env["thrust_case"]["altitude_m"], env["thrust_case"]["temperature_c"])
    a_end = air(env["endurance_case"]["altitude_m"], env["endurance_case"]["temperature_c"])
    L = []
    a = L.append
    a("# Informe de diseño preliminar · DS-I, DS-D y DS-H\n")
    a(f"> Generado por `engineering/sizing.py` el {out['date']}. No editar a mano: cambiar `engineering/config/` y "
      "volver a correr `.venv/bin/python -m engineering.sizing`.\n")
    a("**Estado:** dimensionamiento preliminar (S04). Los requisitos son supuestos del PRD pendientes del Gate G0; "
      "este informe muestra que **los requisitos de autonomía del PRD no son alcanzables** y propone alternativas.\n")

    a("## 1. Conclusiones\n")
    for vehicle in ("DS-I", "DS-D", "DS-H"):
        rows = out["vehicles"][vehicle]
        cur = rows[0]
        rec = next(r for r in rows if r["code"] == RECOMMENDED[vehicle])
        b = rec["best"]
        status = "no tiene ninguna solución factible" if not cur["feasible"] else f"tiene {cur['feasible']} soluciones"
        a(f"- **{vehicle}:** el requisito actual del PRD {status}. Escenario recomendado **{rec['code']}** ({rec['description']}): "
          + (f"hélice {b['prop']}, batería {b['battery']}, MTOW {b['mtow_kg']} kg, BOM ≈ US${b['bom_usd']:,.0f} "
             f"(objetivo US${BOM_TARGET[vehicle]:,}), {b['endurance_new_min']} min con batería nueva a 4,500 msnm "
             f"(≈ {b['endurance_dji_style_min']} min medido como DJI)." if b else "sin solución."))
    a("- La autonomía que publica DJI se mide a nivel del mar, con batería nueva y hasta 0 %. El PRD la pedía a 4,500 msnm, "
      "con 10 % de reserva y batería envejecida: ≈ 1.6 veces más exigente. La columna \"estilo DJI\" permite comparar en igualdad.")
    a("- El modelo es conservador: con el DJI M400 predice 13 % menos autonomía que la real (sección 3).\n")

    a("## 2. Casos de diseño y factores de seguridad\n")
    a("| Caso | Altitud | Temperatura | Densidad del aire | vs nivel del mar |")
    a("|---|---|---|---|---|")
    a(f"| Empuje (peor caso) | {a_thr.altitude_m:,.0f} msnm | {a_thr.temperature_c:.0f} °C | {a_thr.density:.3f} kg/m³ | −{100 * (1 - a_thr.sigma):.0f} % |")
    a(f"| Autonomía | {a_end.altitude_m:,.0f} msnm | {a_end.temperature_c:.0f} °C | {a_end.density:.3f} kg/m³ | −{100 * (1 - a_end.sigma):.0f} % |")
    a(f"| Batería en frío | — | {env['cold_case']['temperature_c']} °C | — | capacidad ≈ 80 % |\n")
    a("Factores: " + ", ".join(f"{k} = {v}" for k, v in sf.items()) + ".\n")

    a("## 3. Modelo y validación (S03)\n")
    a("Hélice por BEMT con corrección de Reynolds, motor por circuito equivalente con eficiencia según tamaño, "
      "batería Li-ion 21700 con caída de voltaje y frío. Se calibró un parámetro con el DJI M4E y se verificó con el M400:\n")
    a("| Dron | Rol | Ficha (hover) | Sin calibrar | Modelo calibrado | Error |")
    a("|---|---|---|---|---|---|")
    for c in cal["cases"]:
        a(f"| {c['name']} | {c['role']} | {c['spec_hover_min']} min | {c['uncalibrated_min']} min | {c['predicted_min']} min | {c['error_pct']:+.1f} % |")
    a(f"\nFactor de calibración (arrastre de perfil): {cal['cd0_scale']}. **El criterio de error < 10 % no se cumple en el M400 "
      "(−13 %)**: el modelo subestima la eficiencia de drones grandes. El error es conservador (diseños algo más grandes de lo "
      "necesario, sobre todo el DS-D). Validación definitiva con el banco de empuje en S10.\n")

    a("## 4. Escenarios de requisitos (para decidir en el Gate G0)\n")
    for vehicle in ("DS-I", "DS-D", "DS-H"):
        a(f"### {vehicle} · MTOW objetivo ≤ {MTOW_TARGET[vehicle]} kg · BOM objetivo ≤ US${BOM_TARGET[vehicle]:,}\n")
        a("| Esc. | Requisito | Factibles | Hélice | Batería | MTOW | BOM | Nueva 4,500 m | Fin de vida | Frío −15 °C | Estilo DJI |")
        a("|---|---|---|---|---|---|---|---|---|---|---|")
        for r in out["vehicles"][vehicle]:
            b = r["best"]
            mark = " ★" if r["code"] == RECOMMENDED[vehicle] else ""
            if b:
                a(f"| {r['code']}{mark} | {r['description']} | {r['feasible']}/{r['evaluated']} | {b['prop']} | {b['battery']} | "
                  f"{b['mtow_kg']} kg | US${b['bom_usd']:,.0f} | {b['endurance_new_min']} min | {b['endurance_eol_min']} min | "
                  f"{b['endurance_cold_min']} min | {b['endurance_dji_style_min']} min |")
            else:
                reasons = ", ".join(f"{k} ({v})" for k, v in sorted(r["rejected"].items(), key=lambda kv: -kv[1])[:2])
                a(f"| {r['code']} | {r['description']} | 0/{r['evaluated']} | — | — | — | — | — | — | — | Rechazos: {reasons} |")
        a("\nSe muestra el diseño de menor BOM de cada escenario. ★ = recomendado.\n")

    a("## 5. Diseños recomendados\n")
    for vehicle in ("DS-I", "DS-D", "DS-H"):
        row = next(r for r in out["vehicles"][vehicle] if r["code"] == RECOMMENDED[vehicle])
        d = row.get("best_full")
        if not d:
            continue
        p = d["performance"]
        a(f"### {vehicle} · escenario {row['code']}\n")
        a(f"{row['description']}.\n")
        a("**Requisitos para comprar o fabricar los componentes (entrada de S09 y S17):**\n")
        a("| Componente | Especificación |")
        a("|---|---|")
        a(f"| Hélice | {d['prop']} (relación paso/diámetro {d['pitch_ratio']:.2f}), {d['rotors']} unidades |")
        a(f"| Motor | Kv ≈ {d['kv']:.0f} rpm/V · potencia máx. ≈ {d['motor_p_max_w']:,} W · corriente máx. ≈ {d['motor_i_max_a']} A · "
          f"masa ≈ {1000 * d['masses']['motores'] / d['rotors']:.0f} g |")
        a(f"| ESC | ≥ {d['esc_current_a']:.0f} A por canal |")
        a(f"| Batería | {d['battery']} · {p['battery_energy_wh']:,} Wh · {1000 * d['masses']['batería']:.0f} g |")
        a(f"| Brazos | tubo de carbono {d['arm']['tube']}, {1000 * d['arm']['length_m']:.0f} mm · distancia entre ejes {1000 * d['wheelbase_m']:.0f} mm |")
        a("")
        a("**Desempeño:**\n")
        a("| Métrica | Valor |")
        a("|---|---|")
        a(f"| MTOW | {d['mtow_kg']} kg |")
        a(f"| Empuje máximo a 5,000 msnm y 15 °C | {p['max_thrust_total_kgf_5000m']} kgf (límite: {p['max_thrust_limit']}) |")
        a(f"| Potencia en hover a 4,500 msnm | {p['hover_power_w_4500m']} W ({p['hover_rpm']} rpm, eficiencia de motor {p['hover_motor_efficiency']:.0%}, FM {p['figure_of_merit']}) |")
        a(f"| Autonomía en hover · nueva / fin de vida / frío / estilo DJI | {p['endurance_new_min']} / {p['endurance_eol_min']} / {p['endurance_cold_min']} / {p['endurance_dji_style_min']} min |")
        if "delivery_mission" in p:
            dm = p["delivery_mission"]
            a(f"| Misión de entrega 3 km (ida con carga, vuelta vacío) | {dm['energy_wh']:.0f} Wh + 20 % de reserva = {dm['required_wh']:.0f} Wh · disponibles {dm['available_wh']:.0f} Wh (nueva) |")
        a("")
        a("**Verificaciones:**\n")
        for name, c in d["checks"].items():
            a(f"- {'✔' if c['ok'] else '✘'} {name}: {c['value']}")
        a("")
        a("**Presupuesto de masa y costo:**\n")
        a("| Subsistema | Masa | Costo |")
        a("|---|---|---|")
        for k_, m in d["masses"].items():
            a(f"| {k_} | {1000 * m:,.0f} g | {('US$' + format(d['costs'][k_], ',.0f')) if k_ in d['costs'] else '—'} |")
        a(f"| **Total** | **{1000 * d['mtow_kg']:,.0f} g** | **US${d['bom_cost_usd']:,.0f}** |\n")
        i = d["inertia"]
        a(f"**Inercias (para el SDF de S05):** Ixx = {i['ixx']:.4f}, Iyy = {i['iyy']:.4f}, Izz = {i['izz']:.4f} kg·m²; "
          f"CG {i['cg_m']} m. **Motor en Gazebo:** motorConstant = {d['sdf']['motorConstant']:.3e}, "
          f"momentConstant = {d['sdf']['momentConstant']:.4f}, maxRotVelocity = {d['sdf']['maxRotVelocity']:.0f} rad/s.\n")
        arm = d["arm"]
        a(f"**Brazo:** margen de resistencia {arm['stress_margin']:.1f} (FS 2.5 ya incluido), deflexión {arm['deflection_pct']} % de la longitud, "
          f"frecuencia natural {arm['f_natural_hz']} Hz vs giro 1P {arm['f_1p_hz']} Hz y paso de pala 2P {arm['f_2p_hz']} Hz.\n")

    a("## 6. Decisiones para el Gate G0\n")
    a("1. **Base de la autonomía:** medir los targets con batería nueva (recomendado) o al final de su vida.")
    a("2. **DS-I:** aceptar ≥ 30 min con batería nueva a 4,500 msnm y RTK/computadora como opcionales (escenario D).")
    a("3. **DS-D:** aceptar ≥ 20 min en hover con 5 kg (escenario C); la misión de entrega de 3 km se cumple igual.")
    a("4. **Precio:** con el equipo del PRD, el BOM del DS-I no baja de ≈ US$800; revisar el precio objetivo o la cámara.\n")
    a("## 7. Limitaciones\n")
    a("- Componentes paramétricos (no de catálogo): masa, Rm e I0 del motor siguen relaciones típicas; se reemplazan en S09.")
    a("- Celdas 21700 con datos de ficha y costos estimados 2026, sin cotizar.")
    a("- Hélices modeladas por BEMT, no medidas (las bases UIUC/APC bloquean descargas automáticas): banco de empuje en S10.")
    a("- Masas de estructura simplificadas (placas, tornillería, carcasa); el CAD de S07-S08 las reemplaza.")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Informe: {REPORT}")


if __name__ == "__main__":
    run()
