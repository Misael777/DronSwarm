"""Lectura mínima de netlists de KiCad (formato S-expression "D"): piezas y nets con sus nodos (ref, pin)."""

from __future__ import annotations

import re
from pathlib import Path

KICAD = Path(__file__).resolve().parent / "kicad"


def load(board: str) -> tuple[dict, dict]:
    """Devuelve (parts, nets): parts[ref] = {value, footprint, pins: {num: name}}; nets[name] = {(ref, pin), ...}."""
    text = (KICAD / board / f"{board}.net").read_text()
    parts = {}
    comps = text[text.index("(components"):text.index("(libparts")] if "(libparts" in text else text
    for m in re.finditer(r'\(comp\s+\(ref "([^"]+)"\)\s+\(value "([^"]*)"\)(?:.*?\(footprint "([^"]*)"\))?', comps, re.S):
        parts[m.group(1)] = {"value": m.group(2), "footprint": m.group(3) or ""}
    nets = {}
    body = text[text.index("(nets"):]
    for blk in re.split(r"\(net\s*\n\s*\(code", body)[1:]:
        name = re.search(r'\(name "([^"]*)"\)', blk).group(1)
        nodes = set()
        for nm in re.finditer(r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)(?:\s+\(pinfunction "([^"]*)"\))?', blk):
            nodes.add((nm.group(1), nm.group(2), nm.group(3) or ""))
        nets[name] = nodes
    return parts, nets


def net_of(nets: dict, ref: str, pin_name: str) -> str | None:
    """Nombre de la net conectada al pin (por nombre de función) de una pieza."""
    for name, nodes in nets.items():
        if any(r == ref and f == pin_name for r, _, f in nodes):
            return name
    return None


def refs_by_value(parts: dict, value_prefix: str) -> list[str]:
    return sorted(r for r, p in parts.items() if p["value"].startswith(value_prefix))
