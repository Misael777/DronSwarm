#!/usr/bin/env python3
"""S09-04 · Presupuesto de enlace de las radios del prototipo → docs/ingenieria/radio_link_budget.md

Para cada enlace: potencia + ganancias − pérdida en espacio libre − pérdidas extra contra la sensibilidad del
receptor (hoja de datos) → margen a 2, 5 y 8 km; alcance teórico con 10 dB de margen; radio de la primera zona de
Fresnel y altura de antena para despejar el 60 % sobre terreno plano.

    .venv/bin/python tools/radio_link_budget.py
"""

from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "ingenieria" / "radio_link_budget.md"
C = 299_792_458.0
EXTRA_LOSS_DB = 6.0          # cables, conectores, polarización, cuerpo del dron
FADE_MARGIN_DB = 10.0        # margen mínimo para el alcance de diseño

# (nombre, uso, frecuencia [Hz], Tx [dBm], ganancia Tx [dBi], ganancia Rx [dBi], sensibilidad [dBm], tasa, fuente)
LINKS = [
    ("ExpressLRS 900 MHz", "control RC (piloto → dron)", 915e6, 30, 2, 2, -112, "100 Hz (LoRa)",
     "documentación ExpressLRS: −112 dBm a 100 Hz"),
    ("RFD900x", "telemetría MAVLink GCS ↔ enjambre (multipunto)", 915e6, 30, 3, 3, -121, "64 kbit/s",
     "hoja de datos RFDesign: −121 dBm a 64 kbit/s"),
    ("ESP-NOW (ESP32-S3, modo LR)", "estados entre drones (consenso, evitación)", 2.44e9, 20, 2, 2, -98, "250 kbit/s",
     "hoja de datos Espressif (modo Long Range)"),
    ("Video 2.4 GHz (clase SIYI HM30)", "video HD en vivo del dron de inspección (opcional)", 2.44e9, 27, 5, 9, -95,
     "≈ 8 Mbit/s", "estimado de enlaces de video COFDM/Wi-Fi de largo alcance"),
]


def fspl(d_m: float, f: float) -> float:
    return 20 * math.log10(4 * math.pi * d_m * f / C)


def margin(link, d_m: float) -> float:
    _, _, f, tx, gt, gr, sens, *_ = link
    return tx + gt + gr - fspl(d_m, f) - EXTRA_LOSS_DB - sens


def range_m(link) -> float:
    _, _, f, tx, gt, gr, sens, *_ = link
    budget = tx + gt + gr - EXTRA_LOSS_DB - sens - FADE_MARGIN_DB
    return 10 ** (budget / 20) * C / (4 * math.pi * f)


def fresnel_r(d_m: float, f: float) -> float:
    lam = C / f
    return math.sqrt(lam * (d_m / 2) * (d_m / 2) / d_m)


def main():
    rows = ["| Enlace | Uso | Frecuencia | Margen a 2 km | 5 km | 8 km | Alcance (10 dB de margen) | Fresnel a 8 km (60 %) |",
            "|---|---|---|---|---|---|---|---|"]
    for lk in LINKS:
        r8 = fresnel_r(8000, lk[2])
        rows.append(f"| {lk[0]} | {lk[1]} | {lk[2] / 1e6:.0f} MHz | {margin(lk, 2000):.0f} dB | {margin(lk, 5000):.0f} dB | "
                    f"{margin(lk, 8000):.0f} dB | {range_m(lk) / 1000:.0f} km | {0.6 * r8:.0f} m |")
    src = [f"- {lk[0]}: {lk[8]} (Tx {lk[3]} dBm, antenas {lk[4]}/{lk[5]} dBi, sensibilidad {lk[6]} dBm a {lk[7]})" for lk in LINKS]
    # caso del tajo: estación en el borde, dron en el fondo a 60 m bajo el borde
    pit = []
    for dist in (100, 170, 300):
        ang = math.degrees(math.atan(60 / dist))
        pit.append(f"| {dist} m | {ang:.0f}° | " + ("despejada si la antena está en el borde mismo del talud" if ang > 25 else
                   "la pared del tajo corta la línea de vista: usar un dron repetidor o bajar la estación a un banco") + " |")
    lines = [
        "# Presupuesto de enlace de radio · prototipos",
        "",
        "> Generado por `tools/radio_link_budget.py`. Espacio libre más 6 dB de pérdidas fijas (cables, polarización, "
        "cuerpo del dron); el alcance de diseño deja 10 dB de margen para desvanecimiento. **Es teórico**: se mide en "
        "campo en el S14 (RSSI y pérdida de paquetes contra distancia).",
        "",
        "## 1. Enlaces y márgenes",
        "",
        *rows,
        "",
        "Target del PRD: 5-8 km. **El control RC y la telemetría en 900 MHz llegan con margen.** Sus alcances de 80-290 km "
        "son solo de espacio libre: en la práctica los limitan la línea de vista y la curvatura de la Tierra (~15 km a 10 m "
        "de altura). El enlace entre drones (ESP-NOW) llega a ~2 km teóricos, ~1 km reales, y basta: los vecinos de una "
        "formación están a menos de 50 m (S06). "
        "Más lejos, los estados viajan por la malla de 900 MHz. El video en vivo es el enlace más justo: va solo en el "
        "dron que inspecciona, y el resto graba a bordo.",
        "",
        "## 2. Línea de vista: el problema real es el tajo, no la distancia",
        "",
        "A 8 km, la primera zona de Fresnel en 900 MHz mide ~26 m de radio, y despejar su 60 % pide ~15 m sobre el "
        "terreno a mitad de camino. La estación de tierra va en alto, en el borde del tajo o sobre un mástil de 6-10 m, "
        "y el dron vuela a 30 m o más. Dentro del tajo, la pared corta la señal cuando el dron baja:",
        "",
        "| Distancia horizontal al dron (60 m bajo el borde) | Ángulo de bajada | Línea de vista |",
        "|---|---|---|",
        *pit,
        "",
        "Medidas de diseño:",
        "- Estación en el borde del talud, del lado de la zona de trabajo. Antena de 900 MHz de 6-9 dBi en un mástil.",
        "- **Dron repetidor:** un DS-I en hover sobre el borde reenvía la telemetría y el video. La malla multipunto del "
        "RFD900x lo permite sin otro hardware.",
        "- Si se pierde el enlace, el failsafe de PX4 hace RTL (verificado en SITL, S06). El protocolo entre drones (ADR-010) "
        "evita choques mientras tanto.",
        "- Muchas minas grandes tienen **LTE privada**. Un módem LTE en la computadora a bordo daría video y telemetría "
        "redundantes; se evalúa con la mina piloto (S15).",
        "",
        "## 3. Datos de entrada",
        "",
        *src,
        "",
        "## 4. Regulación (a confirmar en el S22)",
        "",
        "- 902-928 MHz y 2.4 GHz son bandas de uso libre en el Perú dentro de los límites de potencia del MTC. Hay que "
        "confirmar si 1 W (30 dBm) con antenas de 3-9 dBi entra en el límite de PIRE, o reducir la potencia.",
        "- Los equipos se compran en su versión FCC/CE (por ejemplo, RFD900ux-US) para facilitar la homologación.",
        "",
    ]
    OUT.write_text("\n".join(lines))
    print(OUT)


if __name__ == "__main__":
    main()
