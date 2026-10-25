"""E2 · ESC GaN del DS-D (1 por motor, 12S) → electronics/kicad/esc_ds_d/esc_ds_d.net

3 medios puentes EPC2302 + LMG1210, STM32G071 con AM32 (grupo de pines HARDWARE_GROUP_G0_G), contra-FEM por
comparadores, shunt en el negativo de la batería, buck LM5164 50 V → 12 V (diseño de referencia de la hoja de datos
SNVSAU4D, fig. 7-1) y LDO MCP1703 12 V → 3.3 V. Requisitos: electronics/requisitos/requisitos.json (DS-D).

    source ~/.local/opt/kicad8/env.sh
    .venv/bin/python electronics/skidl/esc_ds_d.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blocks import FP_TVS, am32_mcu, bemf_sense, buck_12v, current_sense, gan_half_bridge, ldo_3v3, ntc, power_pad, signal_input  # noqa: E402
from common import FP_R0603, C, R, finish, rail  # noqa: E402
from skidl import Net, Part, generate_netlist  # noqa: E402

# Rieles críticos
vbus = rail("VBUS")         # batería 12S: 39.6-50.4 V
bat_n = rail("BAT_N")       # negativo de la batería (lado del shunt)
gnd = rail("GND")           # tierra única de potencia y lógica (lado de la placa del shunt)
v12 = rail("12V")           # alimentación de los drivers LMG1210
v3 = rail("3V3")            # MCU, amplificador de corriente


def esc() -> None:
    # Bus: supresor (58 V de trabajo, ~93 V de recorte < 100 V del GaN) y electrolíticos
    Part("Diode", "SMAJ58A", footprint=FP_TVS)[1, 2] += vbus, gnd
    for _ in range(2):
        Part("Device", "C_Polarized", value="470u/63V", footprint="Capacitor_THT:CP_Radial_D10.0mm_P5.00mm")[1, 2] += vbus, gnd
    buck_12v(vbus, v12, gnd, "1M", "47k")                              # arranca a 33.4 V (12S a 2.8 V/celda)
    ldo_3v3(v12, v3, gnd)

    phases = {ph: Net(f"PHASE_{ph}") for ph in "ABC"}
    pwm = {ph: (Net(f"PWM_{ph}_HI"), Net(f"PWM_{ph}_LO")) for ph in "ABC"}
    bemf = {ph: Net(f"BEMF_{ph}") for ph in "ABC"}
    for ph in "ABC":
        gan_half_bridge(ph, *pwm[ph], phases[ph], vbus, gnd, v12)
        power_pad(phases[ph], f"J_{ph}")
    neutral = Net("BEMF_N")
    bemf_sense(phases, bemf, neutral, gnd, "47k", "2.7k", "910")       # 50.4 V → 2.74 V

    vsense, isense, tsense = Net("VBUS_SENSE"), Net("ISENSE"), Net("TEMP_SENSE")
    R("100k", FP_R0603)[1, 2] += vbus, vsense                         # 50.4 V → 2.45 V
    R("5.1k")[1, 2] += vsense, gnd
    C("100n")[1, 2] += vsense, gnd
    current_sense(gnd, bat_n, isense, v3, gnd, "0.5m/3W", "INA181A3")  # 50 mV/A: 0-60 A en 0-3 V
    ntc(v3, tsense, gnd)

    dshot, tlm, dshot_pad, tlm_pad = Net("DSHOT"), Net("TLM"), Net("DSHOT_IN"), Net("TLM_OUT")
    signal_input(dshot, dshot_pad, gnd)
    signal_input(tlm, tlm_pad, gnd)
    am32_mcu(v3, gnd, pwm, bemf, neutral, vsense, isense, dshot, tlm, tsense)
    j_sig = Part("Connector_Generic", "Conn_01x03", ref="J_SIG",
                 footprint="Connector_JST:JST_GH_SM03B-GHS-TB_1x03-1MP_P1.25mm_Horizontal")
    j_sig[1, 2, 3] += dshot_pad, tlm_pad, gnd
    power_pad(vbus, "J_BATP", "DronSwarm:Pad_Power_8x5mm")
    power_pad(bat_n, "J_BATN", "DronSwarm:Pad_Power_8x5mm")


esc()
generate_netlist(file_=finish("esc_ds_d"))
