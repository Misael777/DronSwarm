#!/usr/bin/env python3
"""S06-05 · Spec v1: envolvente de masa, empuje y energía de cada dron + requisitos que heredan las fases siguientes.

Se arma con el dimensionamiento del S04 (engineering/data/results), el cierre cálculo ↔ simulación
(docs/evidencias/simulacion/calculo_vs_sim) y los parámetros del enjambre validados en el S06.

    .venv/bin/python -m engineering.spec_v1          → docs/ingenieria/spec_v1.md
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "engineering" / "data" / "results"
EVID = ROOT / "docs" / "evidencias" / "simulacion"
OUT = ROOT / "docs" / "ingenieria" / "spec_v1.md"
VEHICLES = ["DS-I", "DS-D", "DS-H"]
NOMINAL_CELL_V = 3.6


def load(v: str) -> dict:
    return json.loads((RESULTS / f"{v.lower()}_sizing.json").read_text())


def cells(battery: str) -> int:
    return int(battery.split("S")[0])


def f(v, nd=1):
    return f"{v:,.{nd}f}" if isinstance(v, (int, float)) else str(v)


def envelope_rows(ds: dict[str, dict]) -> list[str]:
    def row(label, fn):
        return f"| {label} | " + " | ".join(fn(ds[v]) for v in VEHICLES) + " |"

    p = lambda d: d["performance"]  # noqa: E731
    return [
        "| | " + " | ".join(f"**{v}** (esc. {ds[v]['scenario']})" for v in VEHICLES) + " |",
        "|---|" + "---|" * len(VEHICLES),
        row("MTOW máximo", lambda d: f"{d['mtow_kg']:.2f} kg"),
        row("Carga útil", lambda d: f"{d['masses'].get('carga útil', 0):.1f} kg"),
        row("Masa vacía (sin carga)", lambda d: f"{d['mtow_kg'] - d['masses'].get('carga útil', 0):.2f} kg"),
        row("Rotores · hélice", lambda d: f"{d['rotors']} · {d['prop']}"),
        row("Empuje máximo a 5,000 msnm, 15 °C", lambda d: f"{p(d)['max_thrust_total_kgf_5000m']:.1f} kgf"),
        row("Relación empuje/peso (mín. 2.0)", lambda d: f"{p(d)['max_thrust_total_kgf_5000m'] / d['mtow_kg']:.2f}"),
        row("Hover en % del empuje máximo (40-65 %)", lambda d: next((f"{c['value'] * 100:.0f} %" for k, c in d["checks"].items() if k.startswith("Empuje de hover")), "—")),
        row("Motor caído: empuje restante / peso", lambda d: next((f"{c['value']:.2f}" for k, c in d["checks"].items() if k.startswith("Motor caído")), "no aplica (4 rotores)")),
        row("Batería · energía", lambda d: f"{d['battery']} · {p(d)['battery_energy_wh']:.0f} Wh"),
        row("Potencia en hover a 4,500 msnm", lambda d: f"{p(d)['hover_power_w_4500m']:,} W"),
        row("Potencia en hover a 5,000 msnm, 15 °C", lambda d: f"{p(d)['hover_power_w_5000m_hot']:,} W"),
        row("Autonomía batería nueva (4,500 msnm, 0 °C)", lambda d: f"{p(d)['endurance_new_min']:.1f} min"),
        row("Autonomía fin de vida (80 %)", lambda d: f"{p(d)['endurance_eol_min']:.1f} min"),
        row("Autonomía en frío (−15 °C)", lambda d: f"{p(d)['endurance_cold_min']:.1f} min"),
        row("Autonomía medida como DJI (referencia)", lambda d: f"{p(d)['endurance_dji_style_min']:.1f} min"),
        row("Corriente de batería en hover", lambda d: f"{p(d)['hover_current_a']:.1f} A"),
        row("Distancia entre ejes (wheelbase)", lambda d: f"{d['wheelbase_m'] * 1000:.0f} mm"),
        row("Brazos", lambda d: f"{d['arm']['tube']} · FS {d['arm']['stress_margin']:.1f}"),
        row("Costo de materiales (BOM)", lambda d: f"US${d['bom_cost_usd']:,.0f}"),
    ]


def motor_rows(ds: dict[str, dict]) -> list[str]:
    def row(label, fn):
        return f"| {label} | " + " | ".join(fn(ds[v]) for v in VEHICLES) + " |"

    p = lambda d: d["performance"]  # noqa: E731
    return [
        "| | " + " | ".join(f"**{v}**" for v in VEHICLES) + " |",
        "|---|" + "---|" * len(VEHICLES),
        row("Constante kv", lambda d: f"{d['kv']} rpm/V"),
        row("Tensión nominal", lambda d: f"{cells(d['battery'])}S · {cells(d['battery']) * NOMINAL_CELL_V:.1f} V"),
        row("rpm sin carga (kv × V nominal)", lambda d: f"{d['kv'] * cells(d['battery']) * NOMINAL_CELL_V:,.0f}"),
        row("rpm en hover (4,500 msnm)", lambda d: f"{p(d)['hover_rpm']:,}"),
        row("Potencia eléctrica en hover por motor", lambda d: f"{p(d)['hover_power_w_4500m'] / d['rotors']:.0f} W"),
        row("Potencia máxima por motor", lambda d: f"{d['motor_p_max_w']:,} W"),
        row("Corriente máxima por motor (FS 1.3)", lambda d: f"{d['motor_i_max_a']:.1f} A"),
        row("Eficiencia del motor en hover (mín.)", lambda d: f"{p(d)['hover_motor_efficiency'] * 100:.0f} %"),
        row("Masa máxima por motor", lambda d: f"{d['masses']['motores'] / d['rotors'] * 1000:.0f} g"),
        row("Costo objetivo por motor (COTS hoy)", lambda d: f"US${d['costs']['motores'] / d['rotors']:.0f}"),
        row("ESC: corriente continua", lambda d: f"{d['esc_current_a']:.1f} A"),
    ]


def sim_rows() -> list[str]:
    rows = ["| Dron | Vuelo | Muestras | rpm medido / calculado | Error rpm | Empuje/peso | Autonomía a las rpm medidas / calculada | ¿Coherente? |",
            "|---|---|---|---|---|---|---|---|"]
    for p in sorted((EVID / "calculo_vs_sim").glob("*.json")):
        r = json.loads(p.read_text())
        rows.append(f"| {r['vehicle']} | {p.stem.split('_', 1)[1]} | {r['hover_samples']} | {r['rpm_hover_measured']:,} / {r['rpm_hover_predicted']:,} | "
                    f"{r['rpm_error_pct']:+.1f} % | {r['thrust_over_weight']:.3f} | {r['endurance_min_at_measured_rpm']} / {r['endurance_min_predicted']} min | "
                    f"{'sí' if r['consistent'] else 'NO'} |")
    return rows


def swarm_rows() -> list[str]:
    path = EVID / "enjambre_cinematico" / "resumen.json"
    if not path.exists():
        return ["(falta la campaña: `.venv/bin/python -m control.swarm.campaign --out docs/evidencias/simulacion/enjambre_cinematico`)"]
    s = json.loads(path.read_text())
    rows = ["| Condición | Corridas | Con colisión | Separación mín. | Torre: distancia libre mín. | Error de formación p95 |",
            "|---|---|---|---|---|---|"]
    for k, r in s.items():
        rows.append(f"| {k.replace('_', ' ')} | {r['runs']} | {r['runs_with_collision']} | {r['min_separation_m']['min']} m | "
                    f"{r['min_obstacle_clearance_m']} m | {r['formation_error_p95_m_median']} m |")
    return rows


def write() -> Path:
    ds = {v: load(v) for v in VEHICLES}
    val = json.loads((RESULTS / "validation.json").read_text()) if (RESULTS / "validation.json").exists() else {}
    m400 = next((r for r in val.get("cases", []) if "400" in r.get("name", "")), None)
    m400_err = f"{m400['error_pct']:+.1f} %" if m400 and "error_pct" in m400 else "−13.4 %"
    lines = [
        "# Spec v1 · DS-I, DS-D y DS-H",
        "",
        f"> Generado por `engineering/spec_v1.py` el {dt.date.today().isoformat()}. No editar a mano: cambiar la fuente "
        "(dimensionamiento, evidencias) y volver a correr `.venv/bin/python -m engineering.spec_v1`.",
        "",
        "**Estado: propuesta para el Gate G1 (PDR).** Se congela cuando se aprueba el G1. Depende de las decisiones del "
        "Gate G0, todavía pendientes: escenarios D (DS-I), C (DS-D) y A (DS-H). Si el G0 elige otros escenarios, esta spec se regenera.",
        "",
        "## 1. Qué significa congelar la spec",
        "",
        "- Desde el G1, **el frame (S07-S09), la selección de componentes comerciales y el prototipo se diseñan contra estos números**: "
        "masa máxima, empuje mínimo y energía mínima. Si una pieza real los excede, se registra el desvío y se decide (no se ajusta la spec en silencio).",
        "- El **motor, la electrónica y las baterías propias (S17 en adelante)** se especifican con la sección 4, corregida con lo que midan el banco de empuje (S10) y los vuelos de prototipo.",
        "- Cambiar la spec requiere un cambio registrado en `docs/decisiones.md` y regenerar este archivo.",
        "",
        "## 2. Envolvente por dron",
        "",
        *envelope_rows(ds),
        "",
        "Casos de diseño: empuje a 5,000 msnm y 15 °C (aire 47 % menos denso que a nivel del mar); autonomía a 4,500 msnm y 0 °C; "
        "frío a −15 °C. Factores de seguridad: empuje/peso 2.0, corriente de motor y ESC 1.3, batería 1.3, estructura 2.5.",
        "",
        "## 3. Cierre del ciclo cálculo ↔ simulación",
        "",
        "Se compara lo que midieron los vuelos en PX4 + Gazebo (rpm reales de los motores en vuelo estacionario) con lo que "
        "predijo el dimensionamiento. Criterio del plan: desviación < 10 %.",
        "",
        *sim_rows(),
        "",
        "**Lectura honesta:** la coincidencia es casi exacta porque el simulador usa las mismas constantes de motor y hélice que "
        "el cálculo. Esto prueba que el modelo del dron en el simulador es **coherente** con el diseño (masas, inercias, "
        "constantes, controlador), no que el diseño sea correcto. Hay dos validaciones independientes:",
        "",
        f"1. Contra drones reales (S03): el modelo predice la autonomía del DJI M400 con {m400_err} de error. Es conservador y no cumple el criterio < 10 %.",
        "2. Contra el banco de empuje (S10) y los vuelos del prototipo (S11-S12): es la validación definitiva y puede corregir esta spec.",
        "",
        "## 4. Requisitos que hereda el motor propio (entrada para S17+)",
        "",
        *motor_rows(ds),
        "",
        "Un motor propio tiene que igualar o superar la eficiencia en hover, no exceder la masa y bajar el costo; la potencia máxima "
        "incluye el margen para empuje/peso 2.0 a 5,000 msnm.",
        "",
        "## 5. Enjambre, comunicaciones y seguridad (validado en S06)",
        "",
        "- **Control de formación:** consenso distribuido (cada dron conoce la ruta de la misión y se ajusta con sus vecinos). "
        "El líder-seguidor queda como alternativa, no como arquitectura principal: con la evitación final no chocó, pero su "
        "error de formación es ~70 % mayor, tarda más y todo el enjambre depende de un solo dron.",
        "- **Evitación:** separación mínima deseada de 3 m entre centros y obstáculos rodeados con 2.5 m libres; predicción del acercamiento a 5 s con sesgo a la derecha.",
        "  Con viento de 8 m/s la distancia libre a la torre bajó a ~1 m (sin contacto): **con viento fuerte, margen de obstáculos de 4 m "
        "y crucero más lento** (acción abierta para el S14, ensayo en campo).",
        "- **Protocolo de pérdida de radio entre drones:** el dron sin noticias por 0.8 s frena, sube 8 m y queda en una capa reservada; "
        "los demás esquivan su última posición conocida durante 20 s. Después actúa el failsafe de PX4 (retorno a casa).",
        "- **Radio:** se diseña para tolerar hasta 30 % de pérdida de paquetes con latencia p95 < 100 ms a 10 Hz por dron; malla de 900 MHz "
        "para enlace con tierra (alcance de diseño, a confirmar en campo en S14).",
        "",
        "Resultados del simulador rápido (cada fila: corridas Monte Carlo con viento, ruido de GNSS y radio simulada):",
        "",
        *swarm_rows(),
        "",
        "La verificación en PX4 + Gazebo (autopiloto real, posición real medida por el monitor del mundo) está en `docs/evidencias/simulacion/`.",
        "",
    ]
    OUT.write_text("\n".join(lines))
    return OUT


if __name__ == "__main__":
    print(write())
