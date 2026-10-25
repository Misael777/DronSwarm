"""S20-07 · BMS de los packs propios 21700 → electronics/kicad/bms_ds_i/ (6S, BQ76930) y bms_ds_d/ (12S, BQ76940)

    .venv/bin/python electronics/skidl/bms.py DS-I        (o DS-D; sin argumento: DS-D)

Arquitectura (electronics/informes/S20-07_baterias.md):
  - Monitor TI BQ769x0 (variante 03: REGOUT 3.3 V, I2C 0x08), conexión de celdas según las tablas 9-3 y 9-4 de la hoja
    SLUSBK2I; filtros de entrada Rc 1 k / Cc 1 µF, BAT con 100 Ω / 2 × 4.7 µF, CAPx 1 µF, ALERT 1 MΩ.
  - Balanceo externo ~100 mA por celda: P-MOSFET AO3401A con la compuerta en el nodo del pin VCn (cuando el balanceo
    interno se activa, la caída en Rc ≈ Vcelda/2 lo enciende) y 2 × 18 Ω.
  - Salida de vuelo SIN transistor de corte (un corte en vuelo derriba el dron): fusible en el arnés y aviso a PX4 por
    DroneCAN (BatteryInfo) para aterrizar. El puerto de CARGA sí se corta: 2 MOSFET espalda con espalda (DSG/CHG).
  - Shunt de 4 terminales fuera de la placa (barra en el negativo del pack), con hilos Kelvin a SRP/SRN.
  - MCU STM32G0B1 (FDCAN) con cristal de 8 MHz, alimentado por LM5164 → 3.3 V que se apaga a 2.9 V/celda.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blocks import buck_3v3  # noqa: E402
from common import FP_C0603, FP_C0805, FP_C1210, FP_LED, FP_R1206, C, R, finish, nc, nc_net, rail  # noqa: E402
from skidl import Net, Part, generate_netlist, subcircuit  # noqa: E402

# Pines VC del monitor → nodo de celda (0 = negativo del pack). Tablas 9-3 (BQ76930, 6 celdas) y 9-4 (BQ76940, 12).
CONFIG = {
    "DS-I": {"afe": "BQ76930DBT", "cells": 6, "uvlo": ("1M", "94.2k"), "chg_fets": 1, "ts": 2,
             "vc": {0: 0, 1: 1, 2: 2, 3: 2, 4: 2, 5: 3, "5B": 3, 6: 4, 7: 5, 8: 5, 9: 5, 10: 6}, "x": {"5X": 3}},
    "DS-D": {"afe": "BQ76940DBT", "cells": 12, "uvlo": ("1M", "45.3k"), "chg_fets": 2, "ts": 3,
             "vc": {0: 0, 1: 1, 2: 2, 3: 3, 4: 3, 5: 4, "5B": 4, 6: 5, 7: 6, 8: 7, 9: 7, 10: 8, "10B": 8, 11: 9, 12: 10,
                    13: 11, 14: 11, 15: 12},
             "x": {"5X": 4, "10X": 8}},
}
VEH = sys.argv[1] if len(sys.argv) > 1 else "DS-D"
CFG = CONFIG[VEH]

gnd = rail("GND")           # VSS del monitor = negativo de las celdas (lado SRP del shunt)
v3 = rail("3V3")            # MCU y CAN
cell = [gnd] + [rail(f"CELL{k}") for k in range(1, CFG["cells"] + 1)]  # nodos del arnés de balanceo; CELL0 = GND


@subcircuit
def afe() -> Part:
    u = Part("Battery_Management", CFG["afe"], value=CFG["afe"].replace("DBT", "03DBT"))
    pin_node = {}                                                      # nodo de celda → net del lado del pin (tras Rc)
    for key, node in CFG["vc"].items():
        pin = f"VC{key}"
        if node not in pin_node:
            pn = Net(f"VC_N{node}")
            pin_node[node] = pn
            if node == 0:
                R("1k")[1, 2] += cell[0], pn
            else:
                R("1k")[1, 2] += cell[node], pn                        # Rc
        u[pin] += pin_node[node]
    for k in range(1, CFG["cells"] + 1):                               # Cc entre pines adyacentes
        C("1u/16V", FP_C0603)[1, 2] += pin_node[k], pin_node[k - 1]
    # Balanceo externo de la celda k (entre cell[k-1] y cell[k])
    for k in range(1, CFG["cells"] + 1):
        q = Part("Transistor_FET", "AO3401A")
        q["S"] += cell[k]
        q["G"] += pin_node[k]
        mid, d = Net(f"BAL{k}_M"), Net(f"BAL{k}_D")
        q["D"] += d
        R("18", FP_R1206)[1, 2] += d, mid
        R("18", FP_R1206)[1, 2] += mid, cell[k - 1]
    # Grupos 2 y 3: referencia (VCxX) por el filtro de potencia, CAPx entre CAPx y VCxX, NC a CAPx
    xs = {}
    for xpin, node in CFG["x"].items():
        xn = Net(f"{xpin}_REF")
        R("100")[1, 2] += cell[node], xn
        u[f"VC{xpin}"] += xn
        xs[xpin] = xn
    u["VSS"] += gnd
    u["CAP1"] & C("1u/16V", FP_C0603) & gnd
    if "5X" in xs:
        cap2 = Net("CAP2")
        u["CAP2"] += cap2
        u["NC(CAP2)"] += cap2
        C("1u/16V", FP_C0603)[1, 2] += cap2, xs["5X"]
    if "10X" in xs:
        cap3 = Net("CAP3")
        u["CAP3"] += cap3
        u["NC(CAP3)"] += cap3
        C("1u/16V", FP_C0603)[1, 2] += cap3, xs["10X"]
    # BAT por el filtro de alimentación (Rf 100 Ω, Cf 2 × 4.7 µF)
    bat = Net("AFE_BAT")
    R("100")[1, 2] += cell[-1], bat
    for _ in range(2):
        C("4.7u/100V", FP_C1210)[1, 2] += bat, gnd
    u["BAT"] += bat
    # REGSRC: seguidor de fuente BSS123 (≈ 12 V − Vth) desde el tope del pack
    g, src = Net("REGSRC_G"), rail("REGSRC")                         # salida del seguidor: fuente del LDO interno
    q = Part("Transistor_FET", "BSS123")
    q["D"] += bat
    q["G"] += g
    q["S"] += src
    R("1M")[1, 2] += bat, g
    Part("Diode", "BZX84Cxx", value="BZX84C12")["K", "A"] += g, gnd
    u["REGSRC"] += src
    C("1u/25V", FP_C0603)[1, 2] += src, gnd
    u["REGOUT"] & C("4.7u/10V", FP_C0805) & gnd
    # Termistores 103AT: TS1 → VSS, TS2 → VC5X, TS3 → VC10X (en las celdas, por conector)
    for t, ref in ((1, gnd), (2, xs.get("5X")), (3, xs.get("10X"))):
        if t > CFG["ts"]:
            continue
        tsn = Net(f"TS{t}")
        u[f"TS{t}"] += tsn
        j = Part("Connector_Generic", "Conn_01x02", ref=f"J_NTC{t}", footprint="Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal")
        j[1, 2] += tsn, ref
        C("100n")[1, 2] += tsn, ref
    if "NC" in [p.name for p in u.pins]:
        nc(u, "NC")
    return u


@subcircuit
def sense_and_charge(u: Part) -> tuple:
    """Shunt Kelvin (fuera de la placa) y corte del puerto de carga (MOSFET DSG + CHG espalda con espalda)."""
    srp_k, srn_k, srp, srn = Net("SHUNT_K_P"), Net("SHUNT_K_N"), Net("SRP"), Net("SRN")
    R("100")[1, 2] += srp_k, srp
    R("100")[1, 2] += srn_k, srn
    C("100n")[1, 2] += srp, srn
    u["SRP"] += srp
    u["SRN"] += srn
    pack_n, chg_n, mid = rail("PACK_N"), Net("CHG_N"), Net("CHG_MID")
    j = Part("Connector_Generic", "Conn_01x03", ref="J_SHUNT", footprint="Connector_JST:JST_GH_SM03B-GHS-TB_1x03-1MP_P1.25mm_Horizontal")
    j[1, 2, 3] += srp_k, srn_k, gnd                                    # Kelvin del shunt (lado celdas = SRP)
    for drv, src_net, name in (("DSG", pack_n, "DSG"), ("CHG", chg_n, "CHG")):
        gate = Net(f"{name}_G")
        R("1k")[1, 2] += u[drv], gate
        R("1M")[1, 2] += gate, src_net
        Part("Diode", "BZX84Cxx", value="BZX84C15")["K", "A"] += gate, src_net
        for _ in range(CFG["chg_fets"]):
            q = Part("Transistor_FET", "BSC035N10NS5")
            q["G"] += gate
            q["S"] += src_net
            q["D"] += mid
    for net, ref in ((pack_n, "J_PACKN"), (chg_n, "J_CHGN")):
        Part("Connector_Generic", "Conn_01x01", ref=ref, footprint="DronSwarm:Pad_Power_6x4mm")[1] += net
    return pack_n, chg_n


@subcircuit
def mcu_can(u: Part) -> None:
    buck_3v3(cell[-1], v3, gnd, *CFG["uvlo"])                          # se apaga a ~2.9 V/celda
    m = Part("MCU_ST_STM32G0", "STM32G0B1CBTx")
    m["VDD", "VREF+", "VBAT"] += v3
    m["VSS"] += gnd
    for _ in range(3):
        C("100n")[1, 2] += v3, gnd
    C("4.7u", FP_C0603)[1, 2] += v3, gnd
    nrst = Net("NRST")
    m["PF2"] += nrst
    C("100n")[1, 2] += nrst, gnd
    x = Part("Device", "Crystal_GND24", value="8MHz", footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm")
    x[1, 3] += m["PF0"], m["PF1"]
    x[2, 4] += gnd
    C("10p/C0G")[1, 2] += m["PF0"], gnd
    C("10p/C0G")[1, 2] += m["PF1"], gnd
    # I2C al monitor (PB6 SCL, PB7 SDA) con pull-ups a 3.3 V; ALERT a PB5; arranque del monitor (TS1 alto) desde PB4
    m["PB6"] += u["SCL"]
    m["PB7"] += u["SDA"]
    R("4.7k")[1, 2] += u["SCL"], v3
    R("4.7k")[1, 2] += u["SDA"], v3
    alert = Net("AFE_ALERT")
    u["ALERT"] += alert
    m["PB5"] += alert
    R("1M")[1, 2] += alert, gnd
    boot = Net("AFE_BOOT")
    R("1k")[1, 2] += m["PB4"], boot
    Part("Device", "D_Schottky", value="BAT54", footprint="Diode_SMD:D_SOD-323")["A", "K"] += boot, u["TS1"]
    # DroneCAN: FDCAN1 RX PD0 / TX PD1 → TCAN330
    t = Part("Interface_CAN_LIN", "TCAN330", footprint="Package_TO_SOT_SMD:SOT-23-8")
    t["VCC"] += v3
    t["GND", "S", "SHDN"] += gnd
    C("100n")[1, 2] += v3, gnd
    t["TXD"] += m["PD1"]
    t["RXD"] += m["PD0"]
    j = Part("Connector_Generic", "Conn_01x04", ref="J_CAN", footprint="Connector_JST:JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal")
    j[1, 2, 3, 4] += nc_net(), t["CANH"], t["CANL"], gnd     # pin 1 (5 V) sin usar: el BMS se alimenta del pack
    # Indicador de carga (4 LED) y botón
    for k, pin in enumerate(("PB0", "PB1", "PB2", "PB10"), 1):
        a = Net(f"SOC_LED{k}")
        R("1k")[1, 2] += m[pin], a
        Part("Device", "LED", value="verde", footprint=FP_LED)["A", "K"] += a, gnd
    btn = Part("Switch", "SW_Push", footprint="Button_Switch_SMD:Panasonic_EVQPUL_EVQPUC")
    btn[1, 2] += m["PB12"], gnd
    swd = Part("Connector_Generic", "Conn_01x05", ref="J_SWD", footprint="Connector_PinHeader_1.27mm:PinHeader_1x05_P1.27mm_Vertical")
    swd[1, 2, 3, 4, 5] += v3, m["PA13"], m["PA14"], nrst, gnd
    for pin in m.pins:
        if not pin.is_connected():
            pin += nc_net()


def bms() -> None:
    u = afe()
    sense_and_charge(u)
    mcu_can(u)
    j = Part("Connector_Generic", f"Conn_01x{CFG['cells'] + 1:02d}", ref="J_BAL",
             footprint=f"Connector_JST:JST_XH_B{CFG['cells'] + 1}B-XH-A_1x{CFG['cells'] + 1:02d}_P2.50mm_Vertical")
    for k in range(CFG["cells"] + 1):
        j[k + 1] += cell[k]


bms()
generate_netlist(file_=finish(f"bms_{VEH.lower().replace('-', '_')}"))
