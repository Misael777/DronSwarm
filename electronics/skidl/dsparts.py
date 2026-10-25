"""Piezas que no están en las bibliotecas estándar de KiCad 8, definidas para SKIDL (pines de la hoja de datos del fabricante).

Las huellas `DronSwarm:*` se dibujan en E6 (`electronics/kicad/DronSwarm.pretty`) con el patrón de soldadura del fabricante.
La numeración de pines de cada pieza la fija esta definición; la huella usa los mismos números (varias islas pueden
compartir número, p. ej. la fuente del EPC2302).
"""

from __future__ import annotations

from skidl import SKIDL, TEMPLATE, Part, Pin

PIN = Pin.types

# EPC2302: GaN 100 V, 1.8 mΩ, QFN 3 × 5 mm con tapa expuesta (conectada a la fuente). Hoja de datos EPC2302 (2026).
EPC2302 = Part(
    name="EPC2302", tool=SKIDL, dest=TEMPLATE, ref_prefix="Q", footprint="DronSwarm:EPC2302_QFN-3x5mm",
    description="eGaN FET 100 V 1.8 mOhm, Qg 23 nC, Qrr 0, compuerta máx. +6/-4 V",
    pins=[Pin(num="1", name="G", func=PIN.INPUT), Pin(num="2", name="S", func=PIN.PASSIVE), Pin(num="3", name="D", func=PIN.PASSIVE)],
)

# LMG1210 (TI): driver de medio puente para GaN, 200 V, LDO interno de 5 V, tiempo muerto ajustable. WQFN-19 (RVR).
# Pines según la tabla "Pin Functions" de la hoja de datos SNOSD12D: los pines duplicados (VSS, HS, NC) se listan todos.
LMG1210 = Part(
    name="LMG1210", tool=SKIDL, dest=TEMPLATE, ref_prefix="U", footprint="DronSwarm:TI_WQFN-19_RVR_3.5x4.5mm",
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
