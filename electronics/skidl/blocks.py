"""Bloques de circuito compartidos por los ESC (DS-D GaN y DS-I silicio) y otras placas.

Cada bloque es un `@subcircuit` con las nets que recibe; los valores salen de las hojas de datos citadas.
"""

from __future__ import annotations

from common import FP_C0603, FP_C1210, FP_LED, FP_R, FP_R0603, FP_TP, C, R, nc
from dsparts import EPC2302, LMG1210
from skidl import Net, Part, subcircuit

FP_TVS = "Diode_SMD:D_SMA"           # la serie SMAJ es DO-214AC (SMA); la biblioteca de KiCad trae D_SMB por defecto


@subcircuit
def lm5164(vin: Net, vout: Net, gnd: Net, uvlo_top: str, uvlo_bot: str, rfb1: str, rfb2: str, rron: str, l_out: str,
           ra: str, ca: str, cb: str, cout: str) -> None:
    """LM5164 (6-100 V, 1 A, COT) con rizado tipo 3. Ecuaciones de la hoja de datos SNVSAU4D:
    VOUT = 1.2 V × (1 + RFB1/RFB2) (ec. 10) · RRON[kΩ] = VOUT × 2500 / FSW[kHz] (ec. 15) · CA ≥ 10/(FSW·RFB1‖RFB2) (ec. 24)
    · RA·CA ≤ tON·(VIN − VOUT)/20 mV (ec. 25) · CB ≥ t_settling/(3·RFB1) (ec. 26) · arranque a 1.5 V × (1 + top/bot)."""
    buck = Part("Regulator_Switching", "LM5164DDA")
    sw = Net("SW_BUCK")
    buck["VIN"] += vin
    buck["GND", "EP"] += gnd
    for _ in range(2):
        C("2.2u/100V", FP_C1210)[1, 2] += vin, gnd
    en = Net("BUCK_EN")
    R(uvlo_top, FP_R0603)[1, 2] += vin, en
    R(uvlo_bot)[1, 2] += en, gnd
    buck["EN/UVLO"] += en
    R(rron)[1, 2] += buck["RON"], gnd
    C("2.2n/50V")[1, 2] += buck["BST"], sw
    buck["SW"] += sw
    Part("Device", "L", value=l_out, footprint="Inductor_SMD:L_Coilcraft_MSS1246-XXX")[1, 2] += sw, vout
    for _ in range(2):
        C(cout, FP_C1210)[1, 2] += vout, gnd
    fb, ran = Net("BUCK_FB"), Net("BUCK_RA")
    R(rfb1)[1, 2] += vout, fb
    R(rfb2)[1, 2] += fb, gnd
    R(ra, FP_R0603)[1, 2] += sw, ran
    C(ca)[1, 2] += ran, vout
    C(cb)[1, 2] += ran, fb
    buck["FB"] += fb
    Part("Connector", "TestPoint", footprint=FP_TP)[1] += buck["PGOOD"]  # sin uso: pad de prueba


def buck_12v(vin: Net, v12: Net, gnd: Net, uvlo_top: str, uvlo_bot: str) -> None:
    """VIN → 12 V, 1 A, 300 kHz: diseño de referencia de TI (SNVSAU4D, fig. 7-1 y tabla 7-1)."""
    lm5164(vin, v12, gnd, uvlo_top, uvlo_bot, "453k", "49.9k", "100k", "68u", "453k", "3.3n", "56p/C0G", "22u/25V")


def buck_3v3(vin: Net, v3: Net, gnd: Net, uvlo_top: str, uvlo_bot: str) -> None:
    """VIN (16-50 V) → 3.3 V, 300 kHz: RFB 174k/100k (3.29 V), RRON 27.4k, 47 µH, RA 140k, CA 3.3 nF, CB 150 pF."""
    lm5164(vin, v3, gnd, uvlo_top, uvlo_bot, "174k", "100k", "27.4k", "47u", "140k", "3.3n", "150p/C0G", "22u/10V")


@subcircuit
def ldo_3v3(vin: Net, v3: Net, gnd: Net) -> None:
    """MCP1703 (16 V máx. de entrada, 250 mA) → 3.3 V."""
    ldo = Part("Regulator_Linear", "MCP1703Ax-330xxTT")
    ldo["VI"] += vin
    ldo["VO"] += v3
    ldo["GND"] += gnd
    C("1u", FP_C0603)[1, 2] += vin, gnd
    C("1u", FP_C0603)[1, 2] += v3, gnd


@subcircuit
def gan_half_bridge(name: str, hi_in: Net, lo_in: Net, sw: Net, vbus: Net, gnd: Net, v12: Net, n_bus_caps: int = 3) -> None:
    """Medio puente GaN: 2 × EPC2302 + LMG1210 en modo IIM (entradas independientes; el tiempo muerto lo pone el MCU)."""
    drv = LMG1210()
    q_hi, q_lo = EPC2302(), EPC2302()
    q_hi["D"] += vbus
    q_hi["S"] += sw
    q_lo["D"] += sw
    q_lo["S"] += gnd
    # Compuertas: resistencia serie (ajuste de dV/dt en banco) y 10 k a la fuente (apagado sin driver)
    g_hi, g_lo = Net(f"G{name}_HI"), Net(f"G{name}_LO")
    drv["HO"] & R("2.2") & g_hi & q_hi["G"]
    drv["LO"] & R("2.2") & g_lo & q_lo["G"]
    R("10k")[1, 2] += g_hi, sw
    R("10k")[1, 2] += g_lo, gnd
    # Alimentación del driver: VIN 12 V, VDD 5 V (regulador interno), bootstrap HB-HS
    vdd = Net(f"VDD5_{name}")
    drv["VIN"] += v12
    drv["VDD", "BST"] += vdd
    drv["VSS", "EP_VSS"] += gnd
    drv["HS", "EP_HS", "NC1"] += sw
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
    for _ in range(n_bus_caps):
        C("2.2u/100V", FP_C1210)[1, 2] += vbus, gnd
    C("100n/100V", FP_C0603)[1, 2] += vbus, gnd


@subcircuit
def signal_input(pin_net: Net, pad_net: Net, gnd: Net) -> None:
    """Entrada/salida externa con 100 Ω en serie y TVS de 5 V contra ESD."""
    R("100")[1, 2] += pad_net, pin_net
    Part("Power_Protection", "TPD1E05U06DPY")["I/O", "GND"] += pad_net, gnd


@subcircuit
def bemf_sense(phases: dict, out: dict, neutral: Net, gnd: Net, r_top: str, r_bot: str, r_neutral: str) -> None:
    """Contra-FEM de las 3 fases (r_top / r_bot + 1 nF) y neutro virtual (3 × r_top + r_neutral + 3.3 nF).

    r_neutral = r_top / (3/k − 3) con k = r_bot / (r_top + r_bot): el neutro queda con la misma relación que las fases.
    """
    for ph, sw in phases.items():
        R(r_top)[1, 2] += sw, out[ph]
        R(r_bot)[1, 2] += out[ph], gnd
        C("1n")[1, 2] += out[ph], gnd
        R(r_top)[1, 2] += sw, neutral
    R(r_neutral)[1, 2] += neutral, gnd
    C("3.3n")[1, 2] += neutral, gnd


@subcircuit
def current_sense(hi: Net, lo: Net, out: Net, v3: Net, gnd: Net, shunt: str, gain: str) -> None:
    """Shunt Kelvin de 4 terminales entre `hi` y `lo` (la corriente va de hi a lo) + INA181 → ADC (filtro 1.6 kHz)."""
    sh = Part("Device", "R_Shunt", value=shunt, footprint="Resistor_SMD:R_Shunt_Vishay_WSK2512_6332Metric_T1.19mm")
    sh[1] += hi
    sh[4] += lo
    sp, sn = Net("ISENSE_P"), Net("ISENSE_N")
    amp = Part("Amplifier_Current", "INA181", value=gain, footprint="Package_TO_SOT_SMD:SOT-23-6")
    R("10")[1, 2] += sh[2], sp
    R("10")[1, 2] += sh[3], sn
    C("100n")[1, 2] += sp, sn
    amp["+"] += sp
    amp["-"] += sn
    amp["REF", "GND"] += gnd
    amp["V+"] += v3
    C("100n")[1, 2] += v3, gnd
    R("1k")[1, 2] += amp[1], out
    C("100n")[1, 2] += out, gnd


# AM32, grupo HARDWARE_GROUP_G0_G (STM32G071 de 32 pines, variante N): fase → (alto TIM1 CHx, bajo CHxN, comparador)
AM32_G0G = {"A": ("PA10/UCPD1_DBCC2", "PB15", "PB7"), "B": ("PA9/UCPD1_DBCC1", "PB0", "PA2"), "C": ("PA8", "PA7", "PA0")}


@subcircuit
def am32_mcu(v3: Net, gnd: Net, pwm: dict, bemf: dict, neutral: Net, vsense: Net, isense: Net, dshot: Net, tlm: Net,
             tsense: Net | None = None) -> Part:
    """STM32G071KBU con AM32 (G0_G): desacople, reset, LED de estado (PB8), pads SWD y pines sin uso."""
    mcu = Part("MCU_ST_STM32G0", "STM32G071KBUxN")
    mcu["VDD"] += v3
    mcu["VSS"] += gnd                                                  # pin 5 y pad expuesto 33
    C("100n")[1, 2] += v3, gnd
    C("4.7u", FP_C0603)[1, 2] += v3, gnd
    nrst = Net("NRST")
    mcu["PF2"] += nrst
    C("100n")[1, 2] += nrst, gnd
    for ph, (hi, lo, cmp_pin) in AM32_G0G.items():
        mcu[hi] += pwm[ph][0]
        mcu[lo] += pwm[ph][1]
        R("10k")[1, 2] += pwm[ph][0], gnd                              # transistores apagados con el MCU en reset
        R("10k")[1, 2] += pwm[ph][1], gnd
        mcu[cmp_pin] += bemf[ph]
    mcu["PA1", "PA3"] += neutral                                       # entradas + de COMP1 y COMP2
    mcu["PA5"] += vsense
    mcu["PA4"] += isense
    mcu["PA6"] += dshot                                                # TIM3 CH1: DShot bidireccional
    mcu["PB6"] += tlm                                                  # USART1 TX: telemetría
    led = Net("LED_A")
    R("1k")[1, 2] += mcu["PB8"], led
    Part("Device", "LED", value="verde", footprint=FP_LED)["A", "K"] += led, gnd
    swd = Part("Connector_Generic", "Conn_01x05", footprint="Connector_PinHeader_1.27mm:PinHeader_1x05_P1.27mm_Vertical")
    swd[1, 2, 3, 4, 5] += v3, mcu["PA13"], mcu["PA14"], nrst, gnd
    if tsense is not None:
        mcu["PB1"] += tsense                                          # NTC (AM32 usa el sensor interno; queda para banco)
    else:
        nc(mcu, "PB1")
    nc(mcu, "PB9", "PC14", "PC15", "PC6", "PA9/PA11", "PA10/PA12", "PD0", "PD1", "PD2", "PD3")
    return mcu


@subcircuit
def ntc(v3: Net, out: Net, gnd: Net) -> None:
    """NTC 10 k B3950 junto a los transistores, divisor con 10 k a 3.3 V."""
    R("10k")[1, 2] += v3, out
    Part("Device", "Thermistor_NTC", value="10k B3950", footprint=FP_R)[1, 2] += out, gnd
    C("100n")[1, 2] += out, gnd


def power_pad(net: Net, ref: str, fp: str = "DronSwarm:Pad_Power_6x4mm") -> None:
    Part("Connector_Generic", "Conn_01x01", ref=ref, footprint=fp)[1] += net
