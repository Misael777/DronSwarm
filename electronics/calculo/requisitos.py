"""E0 · Requisitos eléctricos de las placas propias → electronics/requisitos/requisitos.json + README.md

ESC: desde los motores propios elegidos (motor/informes/M2_elegidos.json) y la batería de cada dron; inductancias de los
motores por FEM (imanes apagados, motor/fem). Controladora y GNSS: interfaces del cableado del prototipo
(hardware/wiring.md) y del estándar FMUv6.

    .venv/bin/python -m electronics.calculo.requisitos
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "electronics" / "requisitos"
V_CELL_MAX = 4.2
MARGIN_I = 1.3                  # corriente de diseño del ESC = corriente del motor × 1.3
MARGIN_V = 2.0                  # tensión de los transistores ≥ 2 × tensión máxima del bus (picos de conmutación)


def motor_inductance(veh: str, chosen: dict) -> dict:
    """Inductancia propia y mutua por fase del motor elegido (FEM 2D, imanes sin magnetizar) [H]."""
    from motor.fem.fem2d import build_mesh, flux_linkage, params_from, phase_currents_to_coils, solve
    p = params_from(chosen)
    m = build_mesh(p, 0.0)
    i = 2.0
    lam = flux_linkage(m, solve(m, phase_currents_to_coils(p, (i, 0.0, 0.0)), magnets=False))
    return {"L_phase_h": lam[0] / i, "M_h": lam[1] / i, "L_loop_h": 2 * (lam[0] - lam[1]) / i,
            "note": "FEM 2D sin cabezas de bobina: la real es ~10-25 % mayor"}


def esc_requirements(veh: str, chosen: dict, req: dict) -> dict:
    ops = chosen["ops"]
    bat = req["battery"]
    v_max = bat["cells_series"] * V_CELL_MAX
    i_hover = ops["hover_4500m_0C"]["current"]
    i_cont = ops["maniobra_twr15"]["current"]
    i_peak = ops["maximo_twr20"]["current"]
    rpm_max = max(o["rpm"] for o in ops.values()) * 1.2
    pp = chosen["design"]["pole_pairs"]
    return {
        "motores_por_dron": req["rotors"], "formato": "4 en 1" if veh == "DS-I" else "1 por motor",
        "bus_v_nominal": bat["v_nominal"], "bus_v_max": v_max, "bus_v_min": bat["v_empty_loaded"],
        "transistor_vds_min": round(v_max * MARGIN_V / 10) * 10,                  # ≈ 2× el bus (con supresor de picos)
        "i_hover_a": round(i_hover, 2), "i_continua_a": round(i_cont, 2), "i_pico_30s_a": round(i_peak, 2),
        "i_diseno_continua_a": round(i_cont * MARGIN_I, 1), "i_diseno_pico_a": round(i_peak * MARGIN_I, 1),
        "pares_de_polos": pp, "erpm_max": round(pp * rpm_max), "f_electrica_max_hz": round(pp * rpm_max / 60),
        "p_motor_hover_w": round(ops["hover_4500m_0C"]["p_in"], 1), "p_motor_max_w": round(ops["maximo_twr20"]["p_in"], 1),
        "conexion": "triángulo" if chosen["design"]["delta"] else "estrella",
        "protocolo": "DShot600 bidireccional + telemetría (AM32)", "sensores_hall": False,
        "medicion": ["corriente del bus (telemetría y límite)", "tensión del bus", "temperatura de los transistores (NTC)"],
        "ambiente": "5,000 msnm, −10 a 40 °C, polvo (IP54 en el dron)",
    }


FC = {
    "estandar": "Pixhawk FMUv6 (abierto) · PX4 v1.15",
    "mcu": "STM32H743 (480 MHz, 2 MB flash)",
    "imu": "2 IMU distintas (redundancia), con aislación de vibración y calefacción a 45 °C (frío de altura)",
    "barometro": "1 (con espuma; ventilado dentro de la carcasa IP54)",
    "memoria": "FRAM SPI (parámetros) + microSD (logs)",
    "interfaces": {"UART": ["TELEM1: Raspberry Pi (MAVLink)", "TELEM2: RFD900x", "GPS1: GNSS RTK", "RC: ExpressLRS (CRSF)",
                            "TELEM3: cámara SIYI", "UART5: flujo óptico MTF-01P", "consola de depuración"],
                   "CAN": ["CAN1 (GNSS/ESC futuros)", "CAN2"], "I2C": ["magnetómetro externo", "expansión"],
                   "salidas": "8 DShot/PWM (6 motores DS-D + servo de liberación + luces)", "USB": "USB-C (carga de firmware)"},
    "alimentacion": "5 V desde un BEC/PM redundante (2 entradas), medición de tensión y corriente de la batería (ADC)",
    "tamano": "≤ 50 × 40 mm, montaje 30.5 mm (estándar)",
}
GNSS = {
    "precision": "RTK: ≤ 2 cm horizontal con base propia; multibanda (L1/L2 o L1/L5) para fijar rápido en minas",
    "interfaz": "UART a GPS1 (NMEA/RTCM o protocolo propio soportado por PX4) + I2C del magnetómetro",
    "magnetometro": "IST8310 o LIS3MDL, lejos de los cables de potencia (mástil)",
    "antena": "multibanda (helicoidal o parche con LNA), conector u.FL/SMA",
    "alimentacion": "5 V desde la controladora; LDO 3.3 V de bajo ruido",
    "tamano": "≤ 60 × 60 mm, carcasa impresa con tapa transparente a RF",
}


def run() -> dict:
    chosen = json.loads((ROOT / "motor" / "informes" / "M2_elegidos.json").read_text())
    req = json.loads((ROOT / "motor" / "requisitos" / "puntos_operacion.json").read_text())
    out = {"esc": {}, "motor_inductancia": {}, "fc": FC, "gnss": GNSS}
    for veh in ("DS-I", "DS-D"):
        out["esc"][veh] = esc_requirements(veh, chosen[veh], req[veh])
        out["motor_inductancia"][veh] = motor_inductance(veh, chosen[veh])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "requisitos.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    L = ["# E0 · Requisitos eléctricos de las placas propias", "",
         "> Generado por `electronics/calculo/requisitos.py` desde los motores propios (M2) y el dron. No editar a mano.", "",
         "## ESC", "", "| | DS-I | DS-D |", "|---|---|---|"]
    rows = [("Formato", "formato"), ("Motores por dron", "motores_por_dron"), ("Bus nominal / máx. / mín. [V]", None),
            ("Tensión mínima de los transistores [V]", "transistor_vds_min"), ("Corriente del motor en hover [A]", "i_hover_a"),
            ("Corriente continua (maniobra) [A]", "i_continua_a"), ("Corriente pico 30 s [A]", "i_pico_30s_a"),
            ("Diseño: continua / pico (× 1.3) [A]", None), ("Pares de polos · eRPM máx.", None),
            ("Frecuencia eléctrica máx. [Hz]", "f_electrica_max_hz"), ("Potencia del motor en hover / máx. [W]", None),
            ("Conexión del motor", "conexion"), ("Protocolo", "protocolo")]
    e = out["esc"]
    for label, key in rows:
        if key:
            vals = [str(e[v][key]) for v in ("DS-I", "DS-D")]
        elif label.startswith("Bus"):
            vals = [f"{e[v]['bus_v_nominal']} / {e[v]['bus_v_max']:.1f} / {e[v]['bus_v_min']}" for v in ("DS-I", "DS-D")]
        elif label.startswith("Diseño"):
            vals = [f"{e[v]['i_diseno_continua_a']} / {e[v]['i_diseno_pico_a']}" for v in ("DS-I", "DS-D")]
        elif label.startswith("Pares"):
            vals = [f"{e[v]['pares_de_polos']} · {e[v]['erpm_max']:,}" for v in ("DS-I", "DS-D")]
        else:
            vals = [f"{e[v]['p_motor_hover_w']} / {e[v]['p_motor_max_w']}" for v in ("DS-I", "DS-D")]
        L.append(f"| {label} | " + " | ".join(vals) + " |")
    mi = out["motor_inductancia"]
    L.append("| Inductancia del motor: fase / lazo de 2 fases [µH] (FEM) | " + " | ".join(
        f"{mi[v]['L_phase_h'] * 1e6:.0f} / {mi[v]['L_loop_h'] * 1e6:.0f}" for v in ("DS-I", "DS-D")) + " |")
    L += ["", "Sin sensores Hall (AM32 sin sensores). Medición en cada ESC: " + ", ".join(e["DS-D"]["medicion"]) + ".", "",
          "## Controladora de vuelo", ""]
    for k, v in FC.items():
        L.append(f"- **{k}**: " + (v if isinstance(v, str) else "; ".join(f"{kk}: {', '.join(vv) if isinstance(vv, list) else vv}" for kk, vv in v.items())))
    L += ["", "## GNSS RTK", ""] + [f"- **{k}**: {v}" for k, v in GNSS.items()] + [""]
    (OUT / "README.md").write_text("\n".join(L))
    return out


if __name__ == "__main__":
    r = run()
    print(json.dumps(r["esc"], indent=1, ensure_ascii=False)[:1500])
