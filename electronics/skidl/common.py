"""Utilidades comunes de los esquemas SKIDL: huellas por defecto, R/C, rieles de alimentación y salida de la netlist.

Cada placa (`esc_ds_d.py`, `esc_ds_i.py`, `fc.py`, `gnss.py`, `bms.py`, `charger.py`) importa este módulo y termina con
`finish(<nombre>)` (ERC + etiquetas deterministas) seguido de `generate_netlist(...)`.
"""

from __future__ import annotations

import builtins
from pathlib import Path

from skidl import ERC, KICAD8, POWER, Net, Part, set_default_tool

set_default_tool(KICAD8)
KICAD_DIR = Path(__file__).resolve().parents[1] / "kicad"

FP_R = "Resistor_SMD:R_0402_1005Metric"
FP_R0603 = "Resistor_SMD:R_0603_1608Metric"
FP_R1206 = "Resistor_SMD:R_1206_3216Metric"
FP_C = "Capacitor_SMD:C_0402_1005Metric"
FP_C0603 = "Capacitor_SMD:C_0603_1608Metric"
FP_C0805 = "Capacitor_SMD:C_0805_2012Metric"
FP_C1210 = "Capacitor_SMD:C_1210_3225Metric"
FP_LED = "LED_SMD:LED_0603_1608Metric"
FP_TP = "TestPoint:TestPoint_Pad_D1.0mm"


def R(value: str, fp: str = FP_R) -> Part:
    return Part("Device", "R", value=value, footprint=fp)


def C(value: str, fp: str = FP_C) -> Part:
    return Part("Device", "C", value=value, footprint=fp)


def rail(name: str) -> Net:
    """Riel de alimentación (marcado como fuente para el ERC)."""
    n = Net(name)
    n.drive = POWER
    return n


def nc_net() -> Net:
    """Net de "sin conexión" de SKIDL (builtin del circuito activo)."""
    return builtins.NC


def nc(part: Part, *pins: str) -> None:
    """Pines sin uso: marcados como sin conexión (el ERC los acepta)."""
    for p in pins:
        part[p] += nc_net()


def out_dir(board: str) -> Path:
    d = KICAD_DIR / board
    d.mkdir(parents=True, exist_ok=True)
    return d


def finish(board: str) -> str:
    """Etiquetas deterministas (KiCad reconoce las piezas al regenerar) + ERC. Devuelve la ruta de la netlist."""
    for i, part in enumerate(default_circuit.parts):  # noqa: F821 (builtin de SKIDL)
        part.tag = f"p{i:03d}"
    ERC()
    return str(out_dir(board) / f"{board}.net")
