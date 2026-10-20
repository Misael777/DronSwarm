"""Bobinado concentrado de doble capa (una bobina por diente): combinaciones ranuras/polos válidas y factor de bobinado.

Método de la estrella de ranuras: la bobina del diente k tiene su fuerza electromotriz a k·p·360°/Ns eléctricos. Se
reparte en las 3 fases por sectores de 60° (con su polaridad), y el factor de distribución es |Σ fasores| / n.
El factor de paso de una bobina que abarca un diente es sin(p·π/Ns).
"""

from __future__ import annotations

import cmath
import math
from functools import cache


@cache
def layout(ns: int, pole_pairs: int) -> dict | None:
    """Fases y polaridad de cada bobina, y factor de bobinado. None si la combinación no es trifásica balanceada."""
    if ns % 3 or 2 * pole_pairs == ns:
        return None
    t = math.gcd(ns, pole_pairs)
    if (ns // t) % 3:                                   # condición de simetría trifásica
        return None
    alpha = 2 * math.pi * pole_pairs / ns
    phases = {0: [], 1: [], 2: []}
    coils = []
    for k in range(ns):
        ang = round(math.degrees(k * alpha), 6) % 360     # sin ruido de redondeo: los bordes de sector caen siempre igual
        sector = int(((ang + 30) % 360) // 60)          # 0: +A, 1: −C, 2: +B, 3: −A, 4: +C, 5: −B
        phase, sign = {0: (0, 1), 1: (2, -1), 2: (1, 1), 3: (0, -1), 4: (2, 1), 5: (1, -1)}[sector]
        phasor = sign * cmath.exp(1j * k * alpha)
        phases[phase].append(phasor)
        coils.append(("ABC"[phase], sign))
    if len({len(v) for v in phases.values()}) != 1:
        return None
    kd = abs(sum(phases[0])) / len(phases[0])
    kp = abs(math.sin(pole_pairs * math.pi / ns))
    return {"ns": ns, "poles": 2 * pole_pairs, "kw": kd * kp, "kd": kd, "kp": kp, "coils": coils,
            "cogging_lcm": math.lcm(ns, 2 * pole_pairs), "periodicity": t,
            "label": f"{ns}N{2 * pole_pairs}P"}


# Combinaciones habituales en outrunners de multirrotor (factor de bobinado alto y cogging bajo)
COMBOS = [(12, 7), (12, 5), (18, 8), (18, 10), (18, 12), (24, 11), (24, 13), (24, 14), (24, 10), (36, 16), (36, 20), (36, 21)]


def valid_combos(min_kw: float = 0.86) -> list[dict]:
    out = []
    for ns, p in COMBOS:
        w = layout(ns, p)
        if w and w["kw"] >= min_kw:
            out.append(w)
    return out
