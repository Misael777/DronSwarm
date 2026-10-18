"""S04-05 · Inercias y centro de gravedad con masas concentradas (para el SDF de Gazebo en S05)."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PointMass:
    name: str
    mass: float
    x: float
    y: float
    z: float
    box: tuple[float, float, float] = (0.0, 0.0, 0.0)   # dimensiones si no es puntual (inercia propia)


def rotor_positions(n_rotors: int, arm_radius: float) -> list[tuple[float, float]]:
    offset = math.pi / n_rotors if n_rotors == 4 else 0.0       # quad en X, hexa con un brazo al frente
    return [(arm_radius * math.cos(offset + 2 * math.pi * i / n_rotors),
             arm_radius * math.sin(offset + 2 * math.pi * i / n_rotors)) for i in range(n_rotors)]


def compute(masses: list[PointMass]) -> dict:
    m = sum(p.mass for p in masses)
    cg = [sum(p.mass * getattr(p, ax) for p in masses) / m for ax in "xyz"]
    ixx = iyy = izz = 0.0
    for p in masses:
        dx, dy, dz = p.x - cg[0], p.y - cg[1], p.z - cg[2]
        a, b, c = p.box
        ixx += p.mass * (dy * dy + dz * dz) + p.mass * (b * b + c * c) / 12
        iyy += p.mass * (dx * dx + dz * dz) + p.mass * (a * a + c * c) / 12
        izz += p.mass * (dx * dx + dy * dy) + p.mass * (a * a + b * b) / 12
    return {"mass_kg": m, "cg_m": [round(v, 4) for v in cg], "ixx": ixx, "iyy": iyy, "izz": izz}


def vehicle_inertia(n_rotors: int, arm_radius: float, tip_mass: float, arm_mass: float, body_mass: float,
                    body_box: tuple[float, float, float], battery_mass: float, payload_mass: float) -> dict:
    pts = [PointMass("cuerpo", body_mass, 0, 0, 0, body_box),
           PointMass("batería", battery_mass, 0, 0, -0.03, (body_box[0] * 0.8, body_box[1] * 0.5, 0.05))]
    for i, (x, y) in enumerate(rotor_positions(n_rotors, arm_radius)):
        pts.append(PointMass(f"rotor {i + 1}", tip_mass, x, y, 0.03))
        pts.append(PointMass(f"brazo {i + 1}", arm_mass, x / 2, y / 2, 0.0))
    if payload_mass > 0:
        pts.append(PointMass("carga", payload_mass, 0, 0, -0.25, (0.30, 0.30, 0.20)))
    return compute(pts)
