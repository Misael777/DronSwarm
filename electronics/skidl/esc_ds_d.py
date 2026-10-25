"""E2 · ESC GaN del DS-D (1 por motor, 12S) → electronics/kicad/esc_ds_d/esc_ds_d.net

3 medios puentes EPC2302 + LMG1210, STM32G071 con AM32 (grupo de pines HARDWARE_GROUP_G0_G), contra-FEM por
comparadores, shunt en el negativo de la batería, buck LM5164 50 V → 12 V (diseño de referencia de la hoja de datos
SNVSAU4D, fig. 7-1) y LDO MCP1703 12 V → 3.3 V. Requisitos: electronics/requisitos/requisitos.json (DS-D).

    export KICAD8_SYMBOL_DIR=$HOME/.local/share/kicad-libs/kicad-symbols
    .venv/bin/python electronics/skidl/esc_ds_d.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from skidl import ERC, KICAD8, POWER, Net, Part, generate_netlist, set_default_tool, subcircuit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from dsparts import EPC2302, LMG1210  # noqa: E402

set_default_tool(KICAD8)
OUT = HERE.parents[0] / "kicad" / "esc_ds_d"
OUT.mkdir(parents=True, exist_ok=True)

FP_R = "Resistor_SMD:R_0402_1005Metric"
FP_R0603 = "Resistor_SMD:R_0603_1608Metric"
FP_C = "Capacitor_SMD:C_0402_1005Metric"
FP_C0603 = "Capacitor_SMD:C_0603_1608Metric"
FP_C1210 = "Capacitor_SMD:C_1210_3225Metric"


def R(value: str, fp: str = FP_R) -> Part:
    return Part("Device", "R", value=value, footprint=fp)


def C(value: str, fp: str = FP_C) -> Part:
    return Part("Device", "C", value=value, footprint=fp)


# Rieles críticos
vbus = Net("VBUS")          # batería 12S: 39.6-50.4 V
bat_n = Net("BAT_N")        # negativo de la batería (lado del shunt)
gnd = Net("GND")            # tierra única de potencia y lógica (lado de la placa del shunt)
v12 = Net("12V")            # alimentación de los drivers LMG1210
v3 = Net("3V3")             # MCU, amplificador de corriente
for n in (vbus, bat_n, gnd, v12, v3):
    n.drive = POWER         # rieles alimentados (batería, buck, LDO) para el ERC


@subcircuit
def half_bridge(name: str, hi_in: Net, lo_in: Net, sw: Net) -> None:
    """Medio puente GaN: 2 × EPC2302 + LMG1210 en modo IIM (entradas independientes; el tiempo muerto lo pone AM32)."""
    drv = LMG1210()
    q_hi, q_lo = EPC2302(), EPC2302()
    q_hi["D"] += vbus
    q_hi["S"] += sw
    q_lo["D"] += sw
    q_lo["S"] += gnd
    # Compuertas: resistencia serie (ajuste de dV/dt en banco) y 10 k a la fuente (apagado sin driver)
    g_hi, g_lo = Net(f"G{name}_HI"), Net(f"G{name}_LO")
    r_ghi, r_glo = R("2.2"), R("2.2")
    drv["HO"] & r_ghi & g_hi & q_hi["G"]
    drv["LO"] & r_glo & g_lo & q_lo["G"]
    R("10k")[1, 2] += g_hi, sw
    R("10k")[1, 2] += g_lo, gnd
    # Alimentación del driver: VIN 12 V, VDD 5 V (regulador interno), bootstrap HB-HS
    vdd = Net(f"VDD5_{name}")
    drv["VIN"] += v12
    drv["VDD"] += vdd
    drv["BST"] += vdd
    drv["VSS", "EP_VSS"] += gnd
    drv["HS", "EP_HS"] += sw
    drv["NC1"] += sw
    C("1u", FP_C0603)[1, 2] += v12, gnd
    C("1u", FP_C0603)[1, 2] += vdd, gnd
    C("100n")[1, 2] += vdd, gnd
    C("100n", FP_C0603)[1, 2] += drv["HB"], sw
    # Modo IIM: DLH a VDD y DHL a VSS (hoja de datos LMG1210, tabla de modos)
    drv["DLH"] += vdd
    drv["DHL"] += gnd
    drv["EN/HI"] += hi_in
    drv["PWM/LI"] += lo_in
    # Desacople del bus pegado al medio puente (lazo de potencia "vertical" de EPC)
    for _ in range(3):
        C("2.2u/100V", FP_C1210)[1, 2] += vbus, gnd
    C("100n/100V", FP_C0603)[1, 2] += vbus, gnd


@subcircuit
def bemf_divider(sw: Net, out: Net) -> None:
    """Contra-FEM de una fase al comparador: 47 k / 2.7 k (50.4 V → 2.74 V) y 1 nF de filtro."""
    R("47k")[1, 2] += sw, out
    R("2.7k")[1, 2] += out, gnd
    C("1n")[1, 2] += out, gnd


@subcircuit
def power_supply() -> None:
    """Supresor + bus, buck LM5164 VBUS → 12 V (300 kHz) y LDO 12 V → 3.3 V."""
    Part("Diode", "SMAJ58A")[1, 2] += vbus, gnd                       # 58 V de trabajo, ~93 V de recorte (< 100 V del GaN)
    for _ in range(2):
        Part("Device", "C_Polarized", value="470u/63V", footprint="Capacitor_THT:CP_Radial_D10.0mm_P5.00mm")[1, 2] += vbus, gnd
    buck = Part("Regulator_Switching", "LM5164DDA")
    sw12 = Net("SW12")
    buck["VIN"] += vbus
    buck["GND", "EP"] += gnd
    for _ in range(2):
        C("2.2u/100V", FP_C1210)[1, 2] += vbus, gnd
    # UVLO: arranca a 1.5 V × (1 + 1M/47k) = 33.4 V (12S a 2.8 V/celda)
    en = Net("BUCK_EN")
    R("1M", FP_R0603)[1, 2] += vbus, en
    R("47k")[1, 2] += en, gnd
    buck["EN/UVLO"] += en
    R("100k")[1, 2] += buck["RON"], gnd                                # R_RON = 12 V × 2500 / 300 kHz = 100 k
    C("2.2n/50V")[1, 2] += buck["BST"], sw12
    buck["SW"] += sw12
    Part("Device", "L", value="68u", footprint="Inductor_SMD:L_Coilcraft_MSS1246")[1, 2] += sw12, v12
    for _ in range(2):
        C("22u/25V", FP_C1210)[1, 2] += v12, gnd
    # Realimentación: 12 V = 1.2 V × (1 + 453k / 49.9k); rizado tipo 3 (RA, CA, CB) según la hoja de datos
    fb, ra = Net("BUCK_FB"), Net("BUCK_RA")
    R("453k")[1, 2] += v12, fb
    R("49.9k")[1, 2] += fb, gnd
    R("453k", FP_R0603)[1, 2] += sw12, ra
    C("3.3n")[1, 2] += ra, v12
    C("56p/C0G")[1, 2] += ra, fb
    buck["FB"] += fb
    buck["PGOOD"] += Net("BUCK_PG")                                     # sin uso: pad de prueba
    Part("Connector", "TestPoint", footprint="TestPoint:TestPoint_Pad_D1.0mm")[1] += buck["PGOOD"]
    ldo = Part("Regulator_Linear", "MCP1703Ax-330xxTT")                # 16 V máx. de entrada, 250 mA
    ldo["VI"] += v12
    ldo["VO"] += v3
    ldo["GND"] += gnd
    C("1u", FP_C0603)[1, 2] += v12, gnd
    C("1u", FP_C0603)[1, 2] += v3, gnd


@subcircuit
def current_sense(out: Net) -> None:
    """Shunt Kelvin 0.5 mΩ en el negativo + INA181A3 (×100): 50 mV/A, 0-60 A en 0-3 V."""
    sh = Part("Device", "R_Shunt", value="0.5m/3W", footprint="Resistor_SMD:R_Shunt_Vishay_WSK2512_6332Metric_T1.19mm")
    sh[1] += gnd                                                       # lado de la placa (fuerza)
    sh[4] += bat_n                                                     # lado de la batería (fuerza)
    sense_p, sense_n = Net("ISENSE_P"), Net("ISENSE_N")
    amp = Part("Amplifier_Current", "INA181", value="INA181A3", footprint="Package_TO_SOT_SMD:SOT-23-6")
    R("10")[1, 2] += sh[2], sense_p                                    # Kelvin del lado de la placa
    R("10")[1, 2] += sh[3], sense_n                                    # Kelvin del lado de la batería
    C("100n")[1, 2] += sense_p, sense_n
    amp["+"] += sense_p
    amp["-"] += sense_n
    amp["REF"] += gnd
    amp["GND"] += gnd
    amp["V+"] += v3
    C("100n")[1, 2] += v3, gnd
    R("1k")[1, 2] += amp[1], out                                      # filtro 1.6 kHz hacia el ADC
    C("100n")[1, 2] += out, gnd


@subcircuit
def signal_input(pin_net: Net, pad_net: Net) -> None:
    """Entrada externa con 100 Ω en serie y TVS de 5 V contra ESD."""
    R("100")[1, 2] += pad_net, pin_net
    Part("Power_Protection", "TPD1E05U06DPY")["I/O", "GND"] += pad_net, gnd


def esc() -> None:
    mcu = Part("MCU_ST_STM32G0", "STM32G071KBUxN")
    mcu["VDD"] += v3
    mcu["VSS"] += gnd                                                  # pin 5 y pad expuesto 33
    C("100n")[1, 2] += v3, gnd
    C("4.7u", FP_C0603)[1, 2] += v3, gnd
    nrst = Net("NRST")
    mcu["PF2"] += nrst
    C("100n")[1, 2] += nrst, gnd

    power_supply()

    # Fases (AM32 G0_G): A = PA10/PB15, B = PA9/PB0, C = PA8/PA7 (TIM1 CHx / CHxN)
    phases = {"A": ("PA10/UCPD1_DBCC2", "PB15", "PB7"), "B": ("PA9/UCPD1_DBCC1", "PB0", "PA2"), "C": ("PA8", "PA7", "PA0")}
    sw_nets = {}
    for ph, (hi, lo, bemf) in phases.items():
        sw = Net(f"PHASE_{ph}")
        sw_nets[ph] = sw
        hi_n, lo_n = Net(f"PWM_{ph}_HI"), Net(f"PWM_{ph}_LO")
        mcu[hi] += hi_n
        mcu[lo] += lo_n
        R("10k")[1, 2] += hi_n, gnd                                    # transistores apagados con el MCU en reset
        R("10k")[1, 2] += lo_n, gnd
        half_bridge(ph, hi_n, lo_n, sw)
        b = Net(f"BEMF_{ph}")
        bemf_divider(sw, b)
        mcu[bemf] += b
        Part("Connector_Generic", "Conn_01x01", ref=f"J_{ph}", footprint="DronSwarm:Pad_Power_6x4mm")[1] += sw

    # Neutro virtual: 3 × 47 k desde las fases y 910 Ω a GND (misma relación que los divisores de fase)
    neutral = Net("BEMF_N")
    for sw in sw_nets.values():
        R("47k")[1, 2] += sw, neutral
    R("910")[1, 2] += neutral, gnd
    C("3.3n")[1, 2] += neutral, gnd
    mcu["PA1"] += neutral                                              # COMP1 INP
    mcu["PA3"] += neutral                                              # COMP2 INP

    # Tensión del bus: 100 k / 5.1 k (50.4 V → 2.45 V)
    vsense = Net("VBUS_SENSE")
    R("100k", FP_R0603)[1, 2] += vbus, vsense
    R("5.1k")[1, 2] += vsense, gnd
    C("100n")[1, 2] += vsense, gnd
    mcu["PA5"] += vsense

    isense = Net("ISENSE")
    current_sense(isense)
    mcu["PA4"] += isense

    # Temperatura de los transistores: NTC 10 k (B3950) junto al medio puente, a PB1 (ADC; AM32 usa el sensor interno,
    # el NTC queda para el banco y una versión futura del firmware)
    tsense = Net("TEMP_SENSE")
    R("10k")[1, 2] += v3, tsense
    Part("Device", "Thermistor_NTC", value="10k B3950", footprint=FP_R)[1, 2] += tsense, gnd
    C("100n")[1, 2] += tsense, gnd
    mcu["PB1"] += tsense

    # Señales: DShot bidireccional (PA6, TIM3 CH1) y telemetría (PB6, USART1 TX)
    dshot, tlm = Net("DSHOT"), Net("TLM")
    dshot_pad, tlm_pad = Net("DSHOT_IN"), Net("TLM_OUT")
    signal_input(dshot, dshot_pad)
    signal_input(tlm, tlm_pad)
    mcu["PA6"] += dshot
    mcu["PB6"] += tlm
    j_sig = Part("Connector_Generic", "Conn_01x03", ref="J_SIG",
                 footprint="Connector_JST:JST_GH_SM03B-GHS-TB_1x03-1MP_P1.25mm_Horizontal")
    j_sig[1, 2, 3] += dshot_pad, tlm_pad, gnd

    # LED de estado (PB8)
    led_a = Net("LED_A")
    R("1k")[1, 2] += mcu["PB8"], led_a
    Part("Device", "LED", value="verde", footprint="LED_SMD:LED_0603_1608Metric")["A", "K"] += led_a, gnd

    # SWD: 3V3, SWDIO, SWCLK, NRST, GND (pads de 1.27 mm)
    j_swd = Part("Connector_Generic", "Conn_01x05", ref="J_SWD",
                 footprint="Connector_PinHeader_1.27mm:PinHeader_1x05_P1.27mm_Vertical")
    j_swd[1, 2, 3, 4, 5] += v3, mcu["PA13"], mcu["PA14"], nrst, gnd

    # Potencia: pads de la batería
    Part("Connector_Generic", "Conn_01x01", ref="J_BATP", footprint="DronSwarm:Pad_Power_8x5mm")[1] += vbus
    Part("Connector_Generic", "Conn_01x01", ref="J_BATN", footprint="DronSwarm:Pad_Power_8x5mm")[1] += bat_n

    # Pines sin uso
    for p in ("PB9", "PC14", "PC15", "PC6", "PA9/PA11", "PA10/PA12", "PD0", "PD1", "PD2", "PD3"):
        mcu[p] += Net(f"NC_{p.replace('/', '_')}", do_erc=False)


esc()
for i, part in enumerate(default_circuit.parts):  # noqa: F821 · etiquetas deterministas: KiCad reconoce las piezas al regenerar
    part.tag = f"p{i:03d}"
ERC()
generate_netlist(file_=str(OUT / "esc_ds_d.net"))
