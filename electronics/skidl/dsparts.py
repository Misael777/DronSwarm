"""Piezas que no están en las bibliotecas estándar de KiCad 8, definidas para SKIDL (pines de la hoja de datos del fabricante).

Las huellas `DronSwarm:*` se dibujan en E6 (`electronics/kicad/DronSwarm.pretty`) con el patrón de soldadura del fabricante.
La numeración de pines de cada pieza la fija esta definición; la huella usa los mismos números (varias islas pueden
compartir número, p. ej. la fuente del EPC2302).
"""

from __future__ import annotations

from skidl import SKIDL, TEMPLATE, Part, Pin

PIN = Pin.types

# EPC2302: GaN 100 V, 1.8 mΩ, QFN 3 × 5 mm. 7 terminales según la hoja de datos EPC2302 (2026), pág. 11:
# 1 compuerta, 2/4/6 fuente, 3/5/7 drenador (la tapa expuesta va a la fuente internamente y no se usa como contacto).
EPC2302 = Part(
    name="EPC2302", tool=SKIDL, dest=TEMPLATE, ref_prefix="Q", footprint="DronSwarm:EPC2302_QFN-3x5mm",
    description="eGaN FET 100 V 1.8 mOhm, Qg 23 nC, Qrr 0, compuerta máx. +6/-4 V",
    pins=[Pin(num="1", name="G", func=PIN.INPUT)] + [Pin(num=str(n), name="S" if n % 2 == 0 else "D", func=PIN.PASSIVE)
                                                     for n in range(2, 8)],
)

# LMG1210 (TI): driver de medio puente para GaN, 200 V, LDO interno de 5 V, tiempo muerto ajustable. WQFN-19 (RVR).
# Pines según la tabla "Pin Functions" de la hoja de datos SNOSD12D: los pines duplicados (VSS, HS, NC) se listan todos.
LMG1210 = Part(
    name="LMG1210", tool=SKIDL, dest=TEMPLATE, ref_prefix="U", footprint="DronSwarm:TI_WQFN-19_RVR0019A_4x3mm",
    description="Driver de medio puente GaN 200 V, 5 V regulados, entradas independientes (IIM) o PWM",
    pins=[
        Pin(num="1", name="NC", func=PIN.NOCONNECT), Pin(num="2", name="VIN", func=PIN.PWRIN),
        Pin(num="3", name="VSS", func=PIN.PWRIN), Pin(num="4", name="VDD", func=PIN.PWROUT),
        Pin(num="5", name="DHL", func=PIN.INPUT), Pin(num="6", name="DLH", func=PIN.INPUT),
        Pin(num="7", name="VSS", func=PIN.PWRIN), Pin(num="8", name="LO", func=PIN.OUTPUT),
        Pin(num="9", name="HS", func=PIN.PASSIVE), Pin(num="10", name="HO", func=PIN.OUTPUT),
        Pin(num="11", name="NC", func=PIN.NOCONNECT), Pin(num="12", name="HB", func=PIN.PASSIVE),
        Pin(num="13", name="HS", func=PIN.PASSIVE), Pin(num="14", name="NC1", func=PIN.PASSIVE),
        Pin(num="15", name="NC", func=PIN.NOCONNECT), Pin(num="16", name="HS", func=PIN.PASSIVE),
        Pin(num="17", name="BST", func=PIN.PASSIVE), Pin(num="18", name="EN/HI", func=PIN.INPUT),
        Pin(num="19", name="PWM/LI", func=PIN.INPUT), Pin(num="20", name="EP_VSS", func=PIN.PWRIN),
        Pin(num="21", name="EP_HS", func=PIN.PASSIVE),
    ],
)

# DRV8300DPW (TI): driver trifásico de MOSFET 100 V, bootstrap integrado, salidas no invertidas, tiempo muerto fijo.
# TSSOP-20 (PW). Pines según la tabla 6-2 de la hoja de datos SLVSFG5D.
DRV8300DPW = Part(
    name="DRV8300DPW", tool=SKIDL, dest=TEMPLATE, ref_prefix="U", footprint="Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
    description="Driver trifásico 100 V para MOSFET N, bootstrap integrado, GVDD 5-20 V",
    pins=[
        Pin(num="1", name="INHA", func=PIN.INPUT), Pin(num="2", name="INHB", func=PIN.INPUT),
        Pin(num="3", name="INHC", func=PIN.INPUT), Pin(num="4", name="INLA", func=PIN.INPUT),
        Pin(num="5", name="INLB", func=PIN.INPUT), Pin(num="6", name="INLC", func=PIN.INPUT),
        Pin(num="7", name="GVDD", func=PIN.PWRIN), Pin(num="8", name="GND", func=PIN.PWRIN),
        Pin(num="9", name="GLC", func=PIN.OUTPUT), Pin(num="10", name="GLB", func=PIN.OUTPUT),
        Pin(num="11", name="GLA", func=PIN.OUTPUT), Pin(num="12", name="SHC", func=PIN.PASSIVE),
        Pin(num="13", name="GHC", func=PIN.OUTPUT), Pin(num="14", name="BSTC", func=PIN.PASSIVE),
        Pin(num="15", name="SHB", func=PIN.PASSIVE), Pin(num="16", name="GHB", func=PIN.OUTPUT),
        Pin(num="17", name="BSTB", func=PIN.PASSIVE), Pin(num="18", name="SHA", func=PIN.PASSIVE),
        Pin(num="19", name="GHA", func=PIN.OUTPUT), Pin(num="20", name="BSTA", func=PIN.PASSIVE),
    ],
)

# BMI088 (Bosch): IMU de 6 ejes (acelerómetro + giróscopo separados) para vibración alta. LGA-16 3 × 4.5 mm, paso 0.5 mm.
# Pines según la tabla 14 de la hoja de datos BST-BMI088-DS000-19 (rev. 1.9, ene. 2024).
BMI088 = Part(
    name="BMI088", tool=SKIDL, dest=TEMPLATE, ref_prefix="U", footprint="DronSwarm:Bosch_LGA-16_3x4.5mm_P0.5mm",
    description="IMU 6 ejes, acelerómetro ±24 g y giróscopo ±2000 °/s, SPI/I2C",
    pins=[
        Pin(num="1", name="INT2", func=PIN.OUTPUT), Pin(num="2", name="NC", func=PIN.PASSIVE),
        Pin(num="3", name="VDD", func=PIN.PWRIN), Pin(num="4", name="GNDA", func=PIN.PWRIN),
        Pin(num="5", name="CSB2", func=PIN.INPUT), Pin(num="6", name="GNDIO", func=PIN.PWRIN),
        Pin(num="7", name="PS", func=PIN.INPUT), Pin(num="8", name="SCK", func=PIN.INPUT),
        Pin(num="9", name="SDI", func=PIN.BIDIR), Pin(num="10", name="SDO2", func=PIN.TRISTATE),
        Pin(num="11", name="VDDIO", func=PIN.PWRIN), Pin(num="12", name="INT3", func=PIN.OUTPUT),
        Pin(num="13", name="INT4", func=PIN.OUTPUT), Pin(num="14", name="CSB1", func=PIN.INPUT),
        Pin(num="15", name="SDO1", func=PIN.TRISTATE), Pin(num="16", name="INT1", func=PIN.OUTPUT),
    ],
)

# Quectel LG290P(03): GNSS RTK de 4 bandas (L1/L2/L5/L6), LGA-79 12.2 × 16.0 mm. Pines según la tabla 6 de
# "LG290P(03) Hardware Design" V1.0 (2024-08-21). RESERVED (1, 2, 5, 17) deben quedar sin conectar.
_LG290P_PINS = {1: "RESERVED", 2: "RESERVED", 3: "1PPS", 4: "EVENT", 5: "RESERVED", 6: "TXD2", 7: "RXD2", 8: "RESET_N",
                9: "VDD_RF", 10: "GND", 11: "RF_IN", 12: "GND", 13: "GND", 14: "RTK_STAT/ANT_ON", 15: "RXD3", 16: "TXD3",
                17: "RESERVED", 18: "I2C_SDA", 19: "I2C_SCL", 20: "TXD1", 21: "RXD1", 22: "V_BCKP", 23: "VCC"}
_LG290P_FUNC = {"RESERVED": PIN.NOCONNECT, "GND": PIN.PWRIN, "VCC": PIN.PWRIN, "V_BCKP": PIN.PWRIN, "VDD_RF": PIN.PWROUT,
                "RF_IN": PIN.PASSIVE, "I2C_SDA": PIN.BIDIR}
LG290P = Part(
    name="LG290P", tool=SKIDL, dest=TEMPLATE, ref_prefix="U", footprint="DronSwarm:Quectel_LG290P_LGA-79_12.2x16mm",
    description="Módulo GNSS RTK 4 bandas, 3 UART + I2C, NMEA/RTCM, 3.3 V",
    pins=[Pin(num=str(n), name=_LG290P_PINS.get(n, "GND"),
              func=_LG290P_FUNC.get(_LG290P_PINS.get(n, "GND"), PIN.INPUT if _LG290P_PINS.get(n, "").startswith(("RX", "RESET", "EVENT", "I2C_SCL")) else PIN.OUTPUT))
          for n in range(1, 80)],
)
