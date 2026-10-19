#!/usr/bin/env python3
"""S07-04 / S08-04 · Informe de FEA de los frames → docs/ingenieria/fea_frames.md (desde los resultados JSON).

    .venv/bin/python tools/fea/fea_report.py
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/ingenieria/fea_frames.md"


def rows(res: dict) -> list[str]:
    out = ["| Caso | Carga de diseño | Resultado | FS | Estado |", "|---|---|---|---|---|"]
    for c in res["cases"].values():
        if "vm_p995_mpa" in c:
            result = (f"von Mises {c['vm_p995_mpa']} MPa (p99.5; pico {c['vm_max_mpa']}), desplazamiento máx. "
                      f"{c['disp_max_mm']} mm, {c['elements']:,} elementos")
            sf = f"{c['safety_factor']} (sobre {c['strength_mpa']:g} MPa)"
        elif "f1_hz" in c:
            result = (f"1.er modo {c['f1_hz']} Hz; 1P = {c['f_1p_hz']} Hz, 2P = {c['f_2p_hz']} Hz; separación "
                      f"{c['separation_pct']:g} % ({c['note']})")
            sf = "—"
        else:
            result = f"σ = {c['stress_mpa']} MPa"
            sf = f"{c['safety_factor']} (mín. {c['required_sf']})"
        load = c.get("load", f"motor + soporte + hélice = {c.get('tip_mass_kg')} kg en la punta, {c.get('length_mm')} mm")
        out.append(f"| {c['title']} | {load} | {result} | {sf} | {'✅' if c['ok'] else '❌'} |")
    return out


def main():
    lines = ["# FEA de los frames · DS-I y DS-D", "",
             f"> Generado por `tools/fea/fea_report.py` el {dt.date.today().isoformat()} desde "
             "`cad/freecad/<grupo>/fea/resultados.json`. Para recalcular: `.venv/bin/python tools/fea/run_fea.py inspection|delivery`.",
             "",
             "## Método", "",
             "- **Sólidos:** STEP del CAD, mallado con gmsh en tetraedros cuadráticos (C3D10) de ~1.6 mm y resuelto con "
             "CalculiX 2.22 (ambos incluidos en FreeCAD 1.0). Los apoyos y las cargas se eligen por geometría: "
             "superficie del agujero del tubo, caras contra las placas, etc.",
             "- **Brazos:** viga tubular (elementos B32R, sección PIPE) con la masa del motor, el soporte y la hélice en la "
             "punta. El análisis modal se verificó contra la fórmula analítica: 82.2 Hz contra 82.1 Hz.",
             "- **Cargas de vuelo:** empuje máximo a 5,000 msnm escalado a nivel del mar por la densidad del aire (×1.88, "
             "cota superior) y multiplicado por FS 2.5. **Cargas de aterrizaje** (accidentales) × FS 1.5. Como las cargas ya incluyen "
             "el factor, el criterio es FS calculado ≥ 1.",
             "- **Esfuerzo informado:** percentil 99.5 de von Mises. El pico absoluto aparece en las esquinas de los apoyos "
             "(singularidad numérica) y se reporta aparte.",
             "- **Piezas impresas (PA12-CF):** se comparan contra 50 MPa, la resistencia en el plano de las capas. Entre "
             "capas es ~50 %, por eso las piezas se orientan en la impresora según la carga (`dfm_dfa_ds-i.md` y "
             "`manufacturing/procesos/piezas_frame.md`).", ""]
    for group, name in (("inspection", "DS-I"), ("delivery", "DS-D")):
        p = ROOT / f"cad/freecad/{group}/fea/resultados.json"
        if not p.exists():
            continue
        res = json.loads(p.read_text())
        lines += [f"## {name}", "",
                  f"Empuje máximo por motor a nivel del mar: {res['thrust_max_per_motor_N']} N → carga de diseño "
                  f"{res['design_thrust_N']} N.", "", *rows(res), ""]
    lines += ["## Hallazgos de diseño", "",
              "- **Tren del DS-I:** con un pie macizo de TPU 95A el tren queda casi rígido (≈ 750 N/mm) y una caída de 1 m "
              "daría ≈ 4.5 kN por pata. Se rediseñó como pie amortiguador de TPU 85A con giroide al 15 % (≈ 30 N/mm, 30 mm "
              "de carrera): ≈ 0.9 kN por pata. Las patas se alargaron para que la cámara no toque el suelo con el pie "
              "comprimido.",
              "- **Soportes de motor del DS-I:** FS ≈ 36, sobredimensionados. Se acortó el manguito (34 → 26 mm) por masa. "
              "La forma la manda la rigidez y la impresión, no la resistencia.",
              "- **DS-D:** la bisagra plegable de aluminio del primer diseño pesaba 250 g por brazo. Con brazos desmontables "
              "(ADR-012), el bloque impreso resiste el momento del brazo con FS 2.6.",
              "- **Bloque de brazo del DS-D:** el percentil 99.5 da FS 2.6, pero el pico local llega a ~170 MPa en el borde "
              "de la boca, donde la carga del tubo entra concentrada en la malla (singularidad de contacto). En la pieza "
              "real el tubo aplasta un poco el PA12 y reparte la carga. Si el prototipo muestra desgaste u ovalización en "
              "la boca, la solución es un buje de aluminio de 1 mm (≈ 8 g por brazo).",
              "- **Modo del brazo del DS-D:** 18 Hz, bajo 1P (44 Hz) con 58 % de separación. Es normal en drones grandes: "
              "se cruza solo al arrancar los motores. Se verifica con el acelerómetro en el banco (S10).",
              "- **Pendiente:** el FEA no reemplaza los ensayos. En el S10 vienen el banco de empuje, la carga estática del "
              "gancho a 2.5 × 5 kg y la caída de 1 m del DS-I con piezas impresas reales, porque la resistencia del PA12-CF "
              "depende del perfil de impresión.", ""]
    OUT.write_text("\n".join(lines))
    print(OUT)


if __name__ == "__main__":
    main()
