"""S13-02 · Asignación de tareas del enjambre y separación de rutas por altitud.

- `hungarian`: asignación óptima 1 a 1 (tantas tareas como drones o menos), minimiza el costo total.
- `auction`: subasta secuencial para más tareas que drones. En cada ronda, cada dron puja con el costo de agregar la
  tarea al final de su ruta, y gana la puja más baja. Es descentralizable: cada dron calcula su puja con lo que sabe.
- Costo = energía estimada (tránsito + trabajo) [Wh]; ∞ si el dron no tiene la capacidad (cámara, carga) o si la
  energía no alcanza con la reserva.
- `altitude_layers`: rutas de tránsito que se cruzan o pasan a < 10 m reciben capas distintas (30, 40, 50… m),
  como en la HU-08; las que no se cruzan comparten capa.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linear_sum_assignment

INF = 1e9


@dataclass
class Drone:
    id: int
    kind: str                         # "DS-I" | "DS-D"
    pos: tuple[float, float]
    energy_wh: float                  # energía útil restante
    cruise_wh_per_km: float           # consumo en crucero
    payload_kg: float = 0.0           # capacidad de carga
    camera: bool = False
    reserve: float = 0.25             # fracción que no se usa (umbral de RTL)


@dataclass
class Task:
    id: str
    kind: str                         # "survey" | "inspect" | "deliver"
    start: tuple[float, float]
    end: tuple[float, float] | None = None
    work_wh: float = 0.0              # energía del trabajo en sí (grilla, hover de entrega…)
    payload_kg: float = 0.0
    needs_camera: bool = False

    @property
    def finish(self) -> tuple[float, float]:
        return self.end or self.start


@dataclass
class Plan:
    assignment: dict[int, list[str]] = field(default_factory=dict)
    cost_wh: dict[int, float] = field(default_factory=dict)
    unassigned: list[str] = field(default_factory=list)


def _dist_km(a, b) -> float:
    return math.dist(a, b) / 1000


def capable(d: Drone, t: Task) -> bool:
    return (not t.needs_camera or d.camera) and d.payload_kg >= t.payload_kg


def task_cost(d: Drone, t: Task, from_pos: tuple[float, float], spent_wh: float = 0.0) -> float:
    """Energía para ir desde from_pos, hacer la tarea y volver a la base; ∞ si no puede."""
    if not capable(d, t):
        return INF
    go = _dist_km(from_pos, t.start) * d.cruise_wh_per_km
    back = _dist_km(t.finish, d.pos) * d.cruise_wh_per_km
    total = spent_wh + go + t.work_wh + back
    if total > d.energy_wh * (1 - d.reserve):
        return INF
    return go + t.work_wh


def hungarian(drones: list[Drone], tasks: list[Task]) -> Plan:
    cost = np.full((len(drones), len(tasks)), INF)
    for i, d in enumerate(drones):
        for j, t in enumerate(tasks):
            cost[i, j] = task_cost(d, t, d.pos)
    rows, cols = linear_sum_assignment(np.minimum(cost, INF))
    plan = Plan()
    for i, j in zip(rows, cols):
        if cost[i, j] < INF:
            plan.assignment.setdefault(drones[i].id, []).append(tasks[j].id)
            plan.cost_wh[drones[i].id] = round(float(cost[i, j]), 1)
    done = {t for ts in plan.assignment.values() for t in ts}
    plan.unassigned = [t.id for t in tasks if t.id not in done]
    return plan


def auction(drones: list[Drone], tasks: list[Task]) -> Plan:
    plan = Plan()
    last = {d.id: d.pos for d in drones}
    spent = {d.id: 0.0 for d in drones}
    pending = list(tasks)
    while pending:
        best = None
        for t in pending:
            for d in drones:
                c = task_cost(d, t, last[d.id], spent[d.id])
                if c < INF and (best is None or c < best[0]):
                    best = (c, d, t)
        if best is None:
            break
        c, d, t = best
        plan.assignment.setdefault(d.id, []).append(t.id)
        spent[d.id] += c
        plan.cost_wh[d.id] = round(spent[d.id], 1)
        last[d.id] = t.finish
        pending.remove(t)
    plan.unassigned = [t.id for t in pending]
    return plan


def _seg_dist(p1, p2, q1, q2) -> float:
    """Distancia mínima entre dos segmentos 2D."""
    def pt_seg(p, a, b):
        a, b, p = np.asarray(a, float), np.asarray(b, float), np.asarray(p, float)
        ab = b - a
        t = 0.0 if not ab.any() else float(np.clip((p - a) @ ab / (ab @ ab), 0, 1))
        return float(np.linalg.norm(p - (a + t * ab)))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    d1, d2 = cross(q1, q2, p1), cross(q1, q2, p2)
    d3, d4 = cross(p1, p2, q1), cross(p1, p2, q2)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    return min(pt_seg(p1, q1, q2), pt_seg(p2, q1, q2), pt_seg(q1, p1, p2), pt_seg(q2, p1, p2))


def altitude_layers(routes: dict[int, tuple[tuple, tuple]], base: float = 30.0, step: float = 10.0,
                    min_sep: float = 10.0) -> dict[int, float]:
    """Capas por coloreo de un grafo: dos rutas en conflicto (se cruzan o pasan a < min_sep) no comparten capa."""
    ids = list(routes)
    conflict = {i: set() for i in ids}
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            i, j = ids[a], ids[b]
            if _seg_dist(*routes[i], *routes[j]) < min_sep:
                conflict[i].add(j)
                conflict[j].add(i)
    layer: dict[int, int] = {}
    for i in sorted(ids, key=lambda k: -len(conflict[k])):            # los más conflictivos primero
        used = {layer[j] for j in conflict[i] if j in layer}
        layer[i] = next(k for k in range(len(ids)) if k not in used)
    return {i: base + step * k for i, k in layer.items()}
