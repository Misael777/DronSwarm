"""S20-07 · Cargador de campo GaN 1 kW (48 V DC → 6S/12S) → electronics/kicad/charger/charger.net

Cálculo y decisión: electronics/informes/S20-07_cargador.md. Etapa reductora-elevadora de 4 interruptores con dos
medios puentes GaN (EPC2302 + LMG1210, los del ESC del DS-D) e inductor XAL1510 de 6.8 µH a 250 kHz. Control digital
STM32G474 (HRTIM: rama A en CHA1/CHA2 = PA8/PA9, rama B en CHC1/CHC2 = PB12/PB13), perfil CC/CV desde el BMS del pack
por DroneCAN (FDCAN1 PA11/PA12). Protecciones: diodo ideal LM74700 + MOSFET en la entrada (polaridad inversa) y en la
salida (sin retroalimentación desde la batería), supresores, fusible de salida 30 A, NTC y ventilador.
Entrada 36-56 V (fuente AC-DC de 48 V o sistema de 48 V); salida 0-55 V, hasta 20 A.

    source ~/.local/opt/kicad8/env.sh
    .venv/bin/python electronics/skidl/charger.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blocks import FP_TVS, buck_12v, current_sense, gan_half_bridge, ldo_3v3, ntc, power_pad  # noqa: E402
from common import FP_C0603, FP_C0805, FP_LED, FP_R0603, C, R, finish, nc_net, rail  # noqa: E402
from skidl import Net, Part, Pin, generate_netlist, subcircuit  # noqa: E402

gnd = rail("GND")
vin_raw, vin = rail("VIN_RAW"), rail("VIN")          # antes y después del diodo ideal de entrada
vout_int, vout = rail("VOUT_INT"), rail("VOUT")      # bus de salida del convertidor y lado batería
in_n, out_n = rail("IN_N"), rail("OUT_N")            # retornos de entrada y salida (lado externo de los shunts)
v12, v3 = rail("12V"), rail("3V3")


@subcircuit
def ideal_diode(anode: Net, cathode: Net, n_fets: int = 1) -> None:
    """LM74700 + MOSFET de 100 V: conduce de ánodo a cátodo, bloquea al revés (hoja SNOSD17: VCAP ≥ 10 × Ciss)."""
    u = Part("Power_Management", "LM74700")
    g = Net(f"IDEAL_G_{cathode.name}")
    u["ANODE", "EN"] += anode
    u["CATHODE"] += cathode
    u["GATE"] += g
    u["GND"] += gnd
    C("220n/16V", FP_C0603)[1, 2] += u["VCAP"], anode
    for _ in range(n_fets):
        q = Part("Transistor_FET", "BSC035N10NS5")
        q["S"] += anode
        q["D"] += cathode
        q["G"] += g


@subcircuit
def sense_divider(src: Net, out: Net) -> None:
    """200 k / 10 k (56 V → 2.67 V) con 100 nF."""
    R("200k", FP_R0603)[1, 2] += src, out
    R("10k")[1, 2] += out, gnd
    C("100n")[1, 2] += out, gnd


@subcircuit
def controller(sig: dict) -> Part:
    m = Part("MCU_ST_STM32G4", "STM32G474CETx")
    for pin in m["VDD"]:
        pin.func = Pin.types.PWRIN
    m["VDD", "VBAT"] += v3
    m["VSS", "VSSA"] += gnd
    for _ in range(3):
        C("100n")[1, 2] += v3, gnd
    C("4.7u", FP_C0603)[1, 2] += v3, gnd
    vdda = rail("VDDA")
    Part("Device", "FerriteBead_Small", value="600R@100MHz", footprint="Inductor_SMD:L_0603_1608Metric")[1, 2] += v3, vdda
    m["VDDA", "VREF+"] += vdda
    C("1u", FP_C0603)[1, 2] += vdda, gnd
    C("100n")[1, 2] += vdda, gnd
    nrst = Net("NRST")
    m["PG10"] += nrst
    C("100n")[1, 2] += nrst, gnd
    R("10k")[1, 2] += m["PB8"], gnd                                    # PB8-BOOT0: arranque desde la flash
    x = Part("Device", "Crystal_GND24", value="8MHz", footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm")
    x[1, 3] += m["PF0"], m["PF1"]
    x[2, 4] += gnd
    C("10p/C0G")[1, 2] += m["PF0"], gnd
    C("10p/C0G")[1, 2] += m["PF1"], gnd
    for pin, net in sig.items():
        m[pin] += net
    swd = Part("Connector_Generic", "Conn_01x05", ref="J_SWD", footprint="Connector_PinHeader_1.27mm:PinHeader_1x05_P1.27mm_Vertical")
    swd[1, 2, 3, 4, 5] += v3, m["PA13"], m["PA14"], nrst, gnd
    return m


def charger() -> None:
    # Entrada: pads, supresor, diodo ideal, bulk
    power_pad(vin_raw, "J_INP", "DronSwarm:Pad_Power_8x5mm")
    power_pad(in_n, "J_INN", "DronSwarm:Pad_Power_8x5mm")
    Part("Diode", "SMAJ58A", footprint=FP_TVS)[1, 2] += vin_raw, in_n
    ideal_diode(vin_raw, vin, 2)
    for _ in range(2):
        Part("Device", "C_Polarized", value="470u/63V", footprint="Capacitor_THT:CP_Radial_D10.0mm_P5.00mm")[1, 2] += vin, gnd
    # Potencia: rama A (entrada), rama B (salida), inductor entre los nodos de conmutación
    sw_a, sw_b = Net("SW_A"), Net("SW_B")
    pwm = {k: Net(f"PWM_{k}") for k in ("A_HI", "A_LO", "B_HI", "B_LO")}
    gan_half_bridge("A", pwm["A_HI"], pwm["A_LO"], sw_a, vin, gnd, v12, 4)
    gan_half_bridge("B", pwm["B_HI"], pwm["B_LO"], sw_b, vout_int, gnd, v12, 4)
    Part("Device", "L", value="6.8u XAL1510-682", footprint="Inductor_SMD:L_Coilcraft_XAL1510-682")[1, 2] += sw_a, sw_b
    for _ in range(2):
        Part("Device", "C_Polarized", value="470u/63V", footprint="Capacitor_THT:CP_Radial_D10.0mm_P5.00mm")[1, 2] += vout_int, gnd
    # Salida: diodo ideal (sin retroalimentación de la batería), fusible, supresor, pads
    vout_d = Net("VOUT_D")
    ideal_diode(vout_int, vout_d, 2)
    Part("Device", "Fuse", value="30A", footprint="Fuse:Fuseholder_Blade_Mini_Keystone_3568")[1, 2] += vout_d, vout
    Part("Diode", "SMAJ58A", footprint=FP_TVS)[1, 2] += vout, out_n
    power_pad(vout, "J_OUTP", "DronSwarm:Pad_Power_8x5mm")
    power_pad(out_n, "J_OUTN", "DronSwarm:Pad_Power_8x5mm")
    # Alimentación auxiliar
    buck_12v(vin, v12, gnd, "1M", "52.3k")                             # arranca a 30.2 V
    ldo_3v3(v12, v3, gnd)
    # Mediciones: corriente de entrada (GND → IN_N) y de salida (OUT_N → GND), INA181A2 (×50, 50 mV/A con 1 mΩ)
    i_in, i_out = Net("I_IN"), Net("I_OUT")
    current_sense(gnd, in_n, i_in, v3, gnd, "1m/3W", "INA181A2")
    current_sense(out_n, gnd, i_out, v3, gnd, "1m/3W", "INA181A2")
    v_in_s, v_out_s, v_bus_s, t_s = Net("VIN_SENSE"), Net("VOUT_SENSE"), Net("VBUS_OUT_SENSE"), Net("TEMP_SENSE")
    sense_divider(vin, v_in_s)
    sense_divider(vout, v_out_s)                                       # tensión de la batería aun con el cargador apagado
    sense_divider(vout_int, v_bus_s)
    ntc(v3, t_s, gnd)
    # Ventilador 12 V (PA6) con diodo de rueda libre
    fan_g, fan_n = Net("FAN_G"), Net("FAN_N")
    q = Part("Transistor_FET", "AO3400A")
    q["G"] += fan_g
    q["S"] += gnd
    q["D"] += fan_n
    R("100k")[1, 2] += fan_g, gnd
    Part("Device", "D_Schottky", value="BAT54", footprint="Diode_SMD:D_SOD-323")["A", "K"] += fan_n, v12
    jf = Part("Connector_Generic", "Conn_01x02", ref="J_FAN", footprint="Connector_JST:JST_GH_SM02B-GHS-TB_1x02-1MP_P1.25mm_Horizontal")
    jf[1, 2] += v12, fan_n
    # CAN al BMS del pack y UART de servicio
    can_tx, can_rx = Net("CAN_TX"), Net("CAN_RX")
    t = Part("Interface_CAN_LIN", "TCAN330", footprint="Package_TO_SOT_SMD:SOT-23-8")
    t["VCC"] += v3
    t["GND", "S", "SHDN"] += gnd
    C("100n")[1, 2] += v3, gnd
    t["TXD"] += can_tx
    t["RXD"] += can_rx
    jc = Part("Connector_Generic", "Conn_01x04", ref="J_CAN", footprint="Connector_JST:JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal")
    jc[1, 2, 3, 4] += nc_net(), t["CANH"], t["CANL"], gnd
    tx, rx = Net("UART_TX"), Net("UART_RX")
    ju = Part("Connector_Generic", "Conn_01x03", ref="J_UART", footprint="Connector_JST:JST_GH_SM03B-GHS-TB_1x03-1MP_P1.25mm_Horizontal")
    ju[1, 2, 3] += gnd, tx, rx
    # Indicadores y botón
    leds = {}
    for name, color in (("LED_FAULT", "rojo"), ("LED_CHG", "verde")):
        a, k = Net(f"{name}_A"), Net(name)
        R("1k")[1, 2] += k, a
        Part("Device", "LED", value=color, footprint=FP_LED)["A", "K"] += a, gnd
        leds[name] = k
    pwr = Part("Device", "LED", value="verde", footprint=FP_LED)
    R("2.2k")[1, 2] += v3, pwr["A"]
    pwr["K"] += gnd
    btn_n = Net("BTN")
    Part("Switch", "SW_Push", footprint="Button_Switch_SMD:Panasonic_EVQPUL_EVQPUC")[1, 2] += btn_n, gnd
    for n in pwm.values():
        R("10k")[1, 2] += n, gnd                                       # transistores apagados con el MCU en reset
    m = controller({"PA8": pwm["A_HI"], "PA9": pwm["A_LO"], "PB12": pwm["B_HI"], "PB13": pwm["B_LO"],
                    "PA0": v_in_s, "PA1": v_out_s, "PA2": i_in, "PA3": i_out, "PA4": v_bus_s, "PB0": t_s,
                    "PA6": fan_g, "PA11": can_rx, "PA12": can_tx, "PB6": tx, "PB7": rx,
                    "PB10": leds["LED_FAULT"], "PB11": leds["LED_CHG"], "PB14": btn_n})
    for pin in m.pins:
        if not pin.is_connected():
            pin += nc_net()
    C("1u", FP_C0805)[1, 2] += v12, gnd


charger()
generate_netlist(file_=finish("charger"))
