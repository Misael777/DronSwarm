"""E3 · ESC 4 en 1 de silicio del DS-I (6S) → electronics/kicad/esc_ds_i/esc_ds_i.net

Decisión en electronics/informes/E3_esc_ds_i.md: silicio propio (~US$43) en vez de GaN (US$159) o comercial (US$80).
4 canales independientes, cada uno con STM32G071 (AM32, G0_G), driver trifásico DRV8300DPW (bootstrap integrado,
tiempo muerto fijo, hoja SLVSFG5D), 6 × CSD18503Q5A (40 V, 4.3 mΩ) y shunt propio (corriente por motor). Comunes: buck
LM5164 → 12 V (compuertas), LDO 3.3 V, supresor, condensadores del bus y conector JST-GH de 6 pines (GND, TLM, S1-S4).

    source ~/.local/opt/kicad8/env.sh
    .venv/bin/python electronics/skidl/esc_ds_i.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blocks import FP_TVS, am32_mcu, bemf_sense, buck_12v, current_sense, ldo_3v3, ntc, power_pad, signal_input  # noqa: E402
from common import FP_C0603, FP_C0805, FP_C1210, FP_R0603, C, R, finish, rail  # noqa: E402
from dsparts import DRV8300DPW  # noqa: E402
from skidl import Net, Part, generate_netlist, subcircuit  # noqa: E402

vbus = rail("VBUS")         # batería 6S: 19.8-25.2 V
gnd = rail("GND")
v12 = rail("12V")           # GVDD de los DRV8300
v3 = rail("3V3")            # 4 MCU + amplificadores


@subcircuit
def power_stage(k: int, pwm: dict, phases: dict, pgnd: Net) -> None:
    """DRV8300DPW (no invertido, bootstrap integrado) + 6 × CSD18503Q5A; fuentes bajas a la tierra de potencia del canal."""
    drv = DRV8300DPW()
    drv["GVDD"] += v12
    drv["GND"] += gnd
    C("10u/25V", FP_C0805)[1, 2] += v12, gnd                         # ≥ 10 µF en GVDD (hoja de datos)
    C("100n")[1, 2] += v12, gnd
    for ph in "ABC":
        q_hi = Part("Transistor_FET", "CSD18503Q5A")
        q_lo = Part("Transistor_FET", "CSD18503Q5A")
        q_hi["D"] += vbus
        q_hi["S"] += phases[ph]
        q_lo["D"] += phases[ph]
        q_lo["S"] += pgnd
        gh, gl = Net(f"GH{ph}{k}"), Net(f"GL{ph}{k}")
        drv[f"GH{ph}"] & R("4.7") & gh & q_hi["G"]
        drv[f"GL{ph}"] & R("4.7") & gl & q_lo["G"]
        R("10k")[1, 2] += gh, phases[ph]
        R("10k")[1, 2] += gl, pgnd
        drv[f"SH{ph}"] += phases[ph]
        C("100n/25V", FP_C0603)[1, 2] += drv[f"BST{ph}"], phases[ph]   # bootstrap (diodo integrado en la versión D)
        drv[f"INH{ph}"] += pwm[ph][0]
        drv[f"INL{ph}"] += pwm[ph][1]
        for _ in range(2):
            C("2.2u/50V", FP_C1210)[1, 2] += vbus, pgnd                # desacople pegado a cada medio puente
        power_pad(phases[ph], f"J_M{k}{ph}", "DronSwarm:Pad_Power_4x3mm")


@subcircuit
def channel(k: int, dshot_pad: Net, tlm_bus: Net) -> None:
    """Un ESC completo (un motor)."""
    phases = {ph: Net(f"M{k}_{ph}") for ph in "ABC"}
    pwm = {ph: (Net(f"PWM{k}_{ph}_HI"), Net(f"PWM{k}_{ph}_LO")) for ph in "ABC"}
    bemf = {ph: Net(f"BEMF{k}_{ph}") for ph in "ABC"}
    pgnd = Net(f"PGND{k}")
    power_stage(k, pwm, phases, pgnd)
    neutral = Net(f"BEMF{k}_N")
    bemf_sense(phases, bemf, neutral, gnd, "20k", "2.2k", "750")       # 25.2 V → 2.50 V
    vsense, isense, tsense = Net(f"VBUS_SENSE{k}"), Net(f"ISENSE{k}"), Net(f"TEMP{k}")
    R("100k", FP_R0603)[1, 2] += vbus, vsense                          # 25.2 V → 2.29 V
    R("10k")[1, 2] += vsense, gnd
    C("100n")[1, 2] += vsense, gnd
    current_sense(pgnd, gnd, isense, v3, gnd, "1m/2W", "INA181A3")     # 100 mV/A: 0-30 A en 0-3 V
    ntc(v3, tsense, gnd)
    dshot, tlm = Net(f"DSHOT{k}"), Net(f"TLM{k}")
    signal_input(dshot, dshot_pad, gnd)
    R("100")[1, 2] += tlm, tlm_bus                                     # telemetría compartida (responde por turno)
    am32_mcu(v3, gnd, pwm, bemf, neutral, vsense, isense, dshot, tlm, tsense)


def esc4() -> None:
    Part("Diode", "SMAJ26A", footprint=FP_TVS)[1, 2] += vbus, gnd      # 26 V de trabajo (> 25.2 V), < 40 V de los FET
    for _ in range(2):
        Part("Device", "C_Polarized", value="470u/35V", footprint="Capacitor_THT:CP_Radial_D8.0mm_P3.50mm")[1, 2] += vbus, gnd
    buck_12v(vbus, v12, gnd, "470k", "47k")                            # arranca a 16.5 V (6S a 2.75 V/celda)
    ldo_3v3(v12, v3, gnd)
    tlm_pad = Net("TLM_OUT")
    Part("Power_Protection", "TPD1E05U06DPY")["I/O", "GND"] += tlm_pad, gnd
    sig = [Net(f"S{k}_IN") for k in range(1, 5)]
    for k in range(1, 5):
        channel(k, sig[k - 1], tlm_pad)
    j = Part("Connector_Generic", "Conn_01x06", ref="J_SIG",
             footprint="Connector_JST:JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal")
    j[1, 2, 3, 4, 5, 6] += gnd, tlm_pad, *sig
    C("100n/50V", FP_C0603)[1, 2] += vbus, gnd
    power_pad(vbus, "J_BATP", "DronSwarm:Pad_Power_6x4mm")
    power_pad(gnd, "J_BATN", "DronSwarm:Pad_Power_6x4mm")


esc4()
generate_netlist(file_=finish("esc_ds_i"))
