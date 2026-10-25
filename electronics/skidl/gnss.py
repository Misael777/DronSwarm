"""E5 · GNSS RTK DronSwarm (Quectel LG290P + magnetómetro IST8310) → electronics/kicad/gnss/gnss.net

Elección en electronics/informes/E5_gnss.md: LG290P (4 bandas) con el driver NMEA genérico de PX4 v1.15
(GPS_1_PROTOCOL = 6: GGA calidad 4 → RTK fijo; RTCM inyectado por el mismo UART). Antena activa multibanda por u.FL
alimentada desde VDD_RF según la figura 17 de "LG290P(03) Hardware Design" V1.0. Conector JST-GH 6 compatible con el
puerto GPS1 de la controladora (5 V, TX, RX, SCL, SDA, GND).

    source ~/.local/opt/kicad8/env.sh
    .venv/bin/python electronics/skidl/gnss.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FP_C0603, FP_C0805, FP_LED, FP_TP, C, R, finish, nc, rail  # noqa: E402
from dsparts import LG290P  # noqa: E402
from skidl import Net, Part, Pin, generate_netlist, subcircuit  # noqa: E402

gnd = rail("GND")
v5 = rail("5V")             # desde la controladora (puerto GPS1)
v3 = rail("3V3_GNSS")       # LDO de bajo ruido para el receptor


@subcircuit
def supply() -> None:
    ldo = Part("Regulator_Linear", "TLV75533PDBV")
    ldo["IN", "EN"] += v5
    ldo["OUT"] += v3
    ldo["GND"] += gnd
    nc(ldo, "NC")
    C("1u", FP_C0603)[1, 2] += v5, gnd
    C("10u/10V", FP_C0805)[1, 2] += v3, gnd
    C("100n")[1, 2] += v3, gnd
    C("100p/C0G")[1, 2] += v3, gnd                                   # desacople de RF cerca de VCC


@subcircuit
def antenna(rf_in: Net, vdd_rf: Net) -> None:
    """Antena activa: alimentación por VDD_RF → 10 Ω → 68 nH; bloqueo de DC 100 pF; π de adaptación (0 Ω, sin montar)."""
    j = Part("Connector", "Conn_Coaxial", ref="J_ANT", footprint="Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical")
    ant, feed, pi = Net("ANT_LINE"), Net("ANT_FEED"), Net("RF_PI")
    j[1] += ant
    j[2] += gnd
    Part("Device", "D_TVS", value="ESD0P2RF-02LS", footprint="Diode_SMD:D_0402_1005Metric")[1, 2] += ant, gnd
    R("10")[1, 2] += vdd_rf, feed                                      # R2
    Part("Device", "L", value="68n", footprint="Inductor_SMD:L_0402_1005Metric")[1, 2] += feed, ant   # L1
    C("100p/C0G")[1, 2] += feed, gnd                                   # C4
    C("100n")[1, 2] += feed, gnd                                       # C5
    C("100p/C0G")[1, 2] += ant, pi                                     # C1: bloqueo de DC hacia el módulo
    R("0")[1, 2] += pi, rf_in                                          # R1 del π
    C("DNP")[1, 2] += pi, gnd                                          # C2 (sin montar)
    C("DNP")[1, 2] += rf_in, gnd                                       # C3 (sin montar)


def gnss() -> None:
    supply()
    u = LG290P()
    for pin in u["GND"]:
        pin.func = Pin.types.PASSIVE                                   # 59 pines de GND del mismo módulo
    u["GND"] += gnd
    for pin in u["RESERVED"]:
        nc(u, pin.num)
    u["VCC", "V_BCKP"] += v3                                           # V_BCKP siempre alimentado mientras haya 5 V
    vdd_rf = Net("VDD_RF")
    for pin in u["VDD_RF"]:
        pin.func = Pin.types.PASSIVE
    u["VDD_RF"] += vdd_rf
    rf = Net("RF_IN")
    u["RF_IN"] += rf
    antenna(rf, vdd_rf)

    # UART1 a la controladora (TX del módulo → RX de la FC): 22 Ω en serie
    tx_fc, rx_fc = Net("GPS_TX"), Net("GPS_RX")
    R("22")[1, 2] += u["TXD1"], tx_fc
    R("22")[1, 2] += rx_fc, u["RXD1"]
    # Magnetómetro IST8310 en el I2C del puerto (externo para PX4, bus 1), lejos de los cables de potencia
    scl, sda = Net("I2C_SCL"), Net("I2C_SDA")
    mag = Part("Sensor_Magnetic", "IST8310")
    mag["AVDD", "DVDD", "~{RST}"] += v3
    mag["VSS", "CAD0", "CAD1"] += gnd                                  # dirección 0x0C
    mag["SCL"] += scl
    mag["SDA"] += sda
    C("1u", FP_C0603)[1, 2] += mag["C1"], gnd
    C("100n")[1, 2] += mag["VPP"], gnd
    C("100n")[1, 2] += v3, gnd
    nc(mag, "DRDY", "NC")
    R("2.2k")[1, 2] += scl, v3
    R("2.2k")[1, 2] += sda, v3
    j = Part("Connector_Generic", "Conn_01x06", ref="J_GPS",
             footprint="Connector_JST:JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal")
    j[1, 2, 3, 4, 5, 6] += v5, rx_fc, tx_fc, scl, sda, gnd             # pin 2 = TX de la FC, pin 3 = RX de la FC

    # Indicadores: RTK fijo (RTK_STAT alto) y 1PPS; pads de prueba de UART2 (configuración/RTCM) y RESET_N
    for sig, color in (("RTK_STAT/ANT_ON", "verde"), ("1PPS", "azul")):
        a = Net(f"LED_{sig.split('/')[0]}")
        R("1k")[1, 2] += u[sig], a
        Part("Device", "LED", value=color, footprint=FP_LED)["A", "K"] += a, gnd
    for sig in ("TXD2", "RXD2", "RESET_N"):
        Part("Connector", "TestPoint", ref=f"TP_{sig}", footprint=FP_TP)[1] += u[sig]
    nc(u, "TXD3", "RXD3", "EVENT", "I2C_SDA", "I2C_SCL")


gnss()
generate_netlist(file_=finish("gnss"))
