#!/usr/bin/env python3
"""M6 · Ajustes, tolerancias y cadenas de cotas del motor → motor/fabricacion/tolerancias.md (generado)

Tabla de ajustes de cada interfaz, cadena radial del entrehierro (que el rotor no roce y el entrehierro no se desparrame) y
cadena axial de la precarga de los rodamientos (que la arandela ondulada absorba las tolerancias de altura).

    .venv/bin/python motor/fabricacion/gen_tolerancias.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "motor" / "fabricacion"))
sys.path.insert(0, str(ROOT))
import gen_cad as G  # noqa: E402

OUT = ROOT / "motor" / "fabricacion" / "tolerancias.md"
INF = ROOT / "motor" / "informes"

# Contribuciones a la excentricidad del entrehierro [mm, radial], con el proceso de M6 y los útiles de concentricidad
RADIAL = [
    ("Juego radial interno de los rodamientos (C0, ×2 rodamientos)", 0.008),
    ("Concentricidad de los 2 asientos de rodamiento (misma impresión, misma pieza)", 0.03),
    ("Tubo de la base respecto de los asientos (misma impresión)", 0.03),
    ("Estator sobre el tubo: mitad del juego para el epoxi (centrado con la chaveta y 3 tiras de 0.05 mm)", 0.05),
    ("Contorno exterior de las láminas (láser de fibra)", 0.03),
    ("Eje en el agujero de la tapa (escariado H7, adhesivo)", 0.01),
    ("Anillo del rotor respecto del agujero de la tapa (útil de concentricidad al pegar)", 0.03),
    ("Caras planas del anillo respecto de su exterior (láser)", 0.02),
    ("Espesor de los imanes (tolerancia de catálogo ±0.05 → radial)", 0.05),
]


def axial_chain(m: dict) -> list[tuple[str, float]]:
    """Tolerancias que cambian la compresión de la arandela ondulada [mm]."""
    return [("Alto del tubo entre hombros de rodamiento (impresión ±0.10)", 0.10),
            ("Ancho de los 2 rodamientos (ISO 492: 0/−0.12 c/u → ±0.06 c/u)", 0.06 * math.sqrt(2)),
            ("Espigón de la tapa hasta la ranura superior (impresión ±0.10)", 0.10),
            ("Posición de las 2 ranuras del eje (torneado ±0.05 c/u)", 0.05 * math.sqrt(2)),
            ("Arandelas de ajuste DIN 988 (±0.02 × 3)", 0.02 * math.sqrt(3))]


def main() -> None:
    chosen = json.loads((INF / "M2_elegidos.json").read_text())
    L = ["# Ajustes y tolerancias del motor", "",
         "> Generado por `motor/fabricacion/gen_tolerancias.py` con las medidas del CAD (`gen_cad.py`). No editar a mano.", "",
         "Generales: piezas cortadas con láser **ISO 2768-m**; piezas impresas **±0.2 mm** salvo indicación; aristas de piezas "
         "impresas con **chaflán 0.5 × 45°**; entradas de asientos de rodamiento con **chaflán 0.4 × 45°**; extremos del eje "
         "**0.3 × 45°**; esquinas del fondo de ranura de las láminas **R 0.3** (no concentra tensiones ni rompe el esmalte).", "",
         f"**Impresión:** los agujeros se modelan con el nominal + `hole_comp` = {G.HOLE_COMP} mm (las impresoras FDM los hacen "
         "más chicos). Antes de imprimir piezas, imprimir `probeta_ajustes.stl`, probar el rodamiento y el eje en cada agujero "
         "y corregir `HOLE_COMP` en `gen_cad.py` hasta que el agujero marcado **0** dé el ajuste de la tabla.", "",
         "**Láser:** los DXF están a la medida nominal. Configurar la compensación de corte (kerf) del láser (≈ 0.02-0.05 mm "
         "con fibra) para que la pieza, no el corte, quede a medida. Verificar con calibre el agujero de la lámina y el "
         "exterior del anillo en las primeras piezas.", ""]
    for veh in ("DS-I", "DS-D"):
        c = chosen[veh]
        p = G.params(veh, c)
        m = G.mech(veh, p, p["h_yoke_g"])
        b, ins = m["bearing"], m["insert"]
        d_tube = 2 * m["r_tube"]
        L += [f"## {veh}", "",
              "| Interfaz | Medida nominal | Pieza | Contraparte | Ajuste resultante | Cómo se logra / controla |",
              "|---|---|---|---|---|---|",
              f"| Aro exterior del rodamiento {b['name']} en la base | Ø{b['D']:.0f} | rodamiento Ø{b['D']:.0f} 0/−0.008 (ISO 492) | "
              f"asiento Ø{b['D'] + G.FITS['bearing_seat']:.2f} +0.05/0 | apriete 0.04-0.06 (plástico: tipo N7) | "
              "probeta de ajustes; entra con morsa y cubos de madera, no a golpes; no debe girar a mano |",
              f"| Eje en el aro interior | Ø{b['d']:.0f} | eje h6 (0/−0.008) | rodamiento Ø{b['d']:.0f} 0/−0.008 | de transición | "
              "fijador de rodamientos (Loctite 641) |",
              f"| Hombros de los rodamientos | Ø{b['Da']:.1f} (máx.) | asiento: hombro Ø{b['Da'] - 0.2:.1f} | apoya solo en el aro exterior | — | "
              "no tocar las tapas ZZ (ISO: D_a máx.) |",
              f"| Eje en la tapa (agujero en D) | Ø{p['shaft']:.0f} con plano a {p['shaft'] / 2 - m['flat']:.2f} del centro | eje h6 | "
              f"tapa: imprimir Ø{p['shaft'] - 0.15:.2f} y **escariar a Ø{p['shaft']:.0f} H7** | deslizante justo | adhesivo retenedor "
              "(Loctite 638); el plano bloquea el giro |",
              f"| Ranuras de anillo E (DIN 6799) | Ø{m['clip']['groove_d']} × {m['clip']['m']} | ranura Ø h11, ancho H13 | "
              f"anillo {m['clip']['name']} | — | torneado o lima en torno manual; borde a ≥ {m['clip']['n']} mm del extremo |",
              f"| Estator sobre el tubo de la base | Ø{2 * p['r_bore']:.2f} | lámina (láser) ±0.03 | tubo Ø{d_tube:.2f} ±0.05 (impreso) | "
              f"juego 0.05-0.18 | epoxi; centrar con la chaveta y 3 tiras de 0.05 mm a 120° (se retiran) |",
              f"| Chaveta en la muesca de las láminas | 2.0 | muesca 2.0 ±0.03 | chaveta {2.0 - G.FITS['key']:.1f} ±0.05 | juego 0.05-0.18 | "
              "solo orientación y antigiro; el epoxi transmite el torque de reacción |",
              f"| Anillo del rotor en la pollera de la tapa | Ø{2 * p['r_out']:.2f} | anillo (láser) ±0.03 | pollera Ø{2 * p['r_out'] + G.FITS['ring_in_skirt']:.2f} "
              f"±0.05 | juego 0.12-0.28 | epoxi con el **útil de concentricidad** (perno en el agujero de la tapa, copa en el anillo) |",
              f"| Imanes en las caras planas del anillo | {p['h_magnet']:.1f} de espesor | imán ±0.05 | cara plana a {p['r_mag_out'] + 0.05:.2f} del centro | "
              "0.05 para el epoxi | plantilla de imanes; epoxi de alta temperatura |",
              f"| Insertos roscados (hélice y DMI) | {ins['thread']} | inserto | agujero Ø{ins['hole']} × {ins['depth']} | según fabricante | "
              "colocar con soldador a 220-240 °C (PETG) y punta de insertos, perpendicular |",
              ""]
        # cadena radial
        rss = math.sqrt(sum(v * v for _, v in RADIAL))
        wc = sum(v for _, v in RADIAL)
        gap = p["gap"]
        L += [f"**Cadena radial del entrehierro** (nominal {gap:.2f} mm, mínimo admisible 50 % = {gap / 2:.2f} mm):", "",
              "| Contribución | Excentricidad [mm] |", "|---|---|"]
        L += [f"| {n} | {v:.3f} |" for n, v in RADIAL]
        L += [f"| **Peor caso (suma)** | **{wc:.2f}** → entrehierro mínimo {gap - wc:.2f} mm "
              f"({'cumple' if gap - wc >= gap / 2 else 'apenas bajo el 50 %: requiere todas las tolerancias al máximo y en la misma dirección; la galga del armado lo detecta'}) |",
              f"| **Estadística (raíz de la suma de cuadrados)** | **{rss:.2f}** → entrehierro mínimo {gap - rss:.2f} mm |", "",
              f"Atracción magnética desbalanceada con la excentricidad estadística: M5 la calcula con 0.10 mm "
              f"({'conservador' if rss <= 0.10 else 'revisar M5 con ' + f'{rss:.2f} mm'}). Control: girar a mano y pasar una galga "
              f"de {gap / 2:.2f} mm por el entrehierro en 4 posiciones antes de cerrar la tapa.", ""]
        ax = axial_chain(m)
        rss_a = math.sqrt(sum(v * v for _, v in ax))
        travel = m["wave"]["h_free"] - m["wave"]["h_work"]
        L += [f"**Cadena axial de la precarga** (arandela ondulada {m['wave']['name']}: libre {m['wave']['h_free']} mm, "
              f"trabajo {m['wave']['h_work']} mm → recorrido útil ±{travel / 2:.2f} mm):", "",
              "| Contribución | ± [mm] |", "|---|---|"] + [f"| {n} | {v:.3f} |" for n, v in ax]
        L += [f"| **Estadística** | **±{rss_a:.2f}** {'≤' if rss_a <= travel / 2 else '>'} ±{travel / 2:.2f} |", "",
              ("La arandela ondulada absorbe la variación esperada." if rss_a <= travel / 2 else
               "La variación puede superar el recorrido de la arandela: ") +
              " Ajuste en el armado: con el anillo E superior colocado, el eje no debe tener juego axial perceptible y el rotor "
              "tiene que girar libre. Si hay juego, agregar una arandela DIN 988 de 0.1 mm bajo el espigón; si frena, quitarla.", ""]
    L += ["## Orden de armado (por qué cada pieza está donde está)", "",
          "1. **Rodamientos en la base** (desde abajo el inferior, desde arriba el superior) contra sus hombros: el empuje de la "
          "hélice tira del rotor hacia arriba y lo resiste el rodamiento inferior contra su hombro.",
          "2. **Estator pegado sobre el tubo**, con la chaveta en la muesca y las 3 tiras de centrado.",
          "3. **Rotor**: anillo + imanes pegados; anillo pegado en la tapa con el útil de concentricidad.",
          "4. **Eje en la tapa** (adhesivo retenedor), arandela + anillo E superiores en el rebaje de la tapa.",
          "5. **Arandela de ajuste + arandela ondulada** sobre el rodamiento superior; bajar el rotor con el eje por los rodamientos.",
          "6. **Arandela de ajuste + anillo E inferior** desde abajo: quedan los aros interiores apretados entre el anillo E inferior "
          "y el espigón de la tapa (disposición en X, precarga por la arandela ondulada).",
          "7. Verificar: giro libre, sin juego axial, galga en el entrehierro, resistencia y aislamiento (valores.md).", ""]
    OUT.write_text("\n".join(L))
    print(OUT)


if __name__ == "__main__":
    main()
