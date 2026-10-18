"""S06-01 · Geometría de formaciones del enjambre.

Las formaciones son desplazamientos (offsets) en el marco de la formación: x hacia adelante, y hacia la izquierda,
en metros. `to_world` los gira según el rumbo de avance. Marco del mundo: ENU (x este, y norte, z arriba).

Al cambiar de formación, `assign` reparte los puestos minimizando la distancia total que recorren los drones
(algoritmo húngaro): menos cruces entre drones y transiciones más cortas.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import linear_sum_assignment


def _centered(off: np.ndarray) -> np.ndarray:
    return off - off.mean(axis=0)


def line(n: int, spacing: float) -> np.ndarray:
    """En línea de frente (abreast): todos lado a lado, perpendiculares al avance."""
    y = (np.arange(n) - (n - 1) / 2) * spacing
    return np.column_stack([np.zeros(n), y])


def column(n: int, spacing: float) -> np.ndarray:
    """En columna: uno detrás de otro (pasos estrechos, rampas del tajo)."""
    x = -(np.arange(n) - (n - 1) / 2) * spacing
    return np.column_stack([x, np.zeros(n)])


def wedge(n: int, spacing: float, angle_deg: float = 45.0) -> np.ndarray:
    """En V: el primero adelante y los demás alternando atrás-izquierda / atrás-derecha."""
    a = math.radians(angle_deg)
    pts = [(0.0, 0.0)]
    for k in range(1, n):
        rank, side = (k + 1) // 2, (1 if k % 2 else -1)
        pts.append((-rank * spacing * math.cos(a), side * rank * spacing * math.sin(a)))
    return _centered(np.array(pts))


def circle(n: int, radius: float) -> np.ndarray:
    th = 2 * math.pi * np.arange(n) / n
    return np.column_stack([radius * np.cos(th), radius * np.sin(th)])


def grid(n: int, spacing: float) -> np.ndarray:
    cols = math.ceil(math.sqrt(n))
    pts = [((k // cols) * -spacing, (k % cols) * spacing) for k in range(n)]
    return _centered(np.array(pts, dtype=float))


SHAPES = {"linea": line, "columna": column, "v": wedge, "circulo": circle, "grilla": grid}


def make(shape: str, n: int, size: float) -> np.ndarray:
    """size = separación entre vecinos (o radio para el círculo)."""
    return SHAPES[shape](n, size)


def to_world(offsets: np.ndarray, heading_rad: float) -> np.ndarray:
    """Gira los offsets de la formación al marco ENU; heading = dirección de avance medida desde el este."""
    c, s = math.cos(heading_rad), math.sin(heading_rad)
    return offsets @ np.array([[c, s], [-s, c]])


def assign(positions: np.ndarray, slots: np.ndarray) -> np.ndarray:
    """Puesto de cada dron: perm[i] = índice del slot para el dron i (minimiza la suma de distancias al cuadrado)."""
    cost = ((positions[:, None, :2] - slots[None, :, :2]) ** 2).sum(axis=2)
    rows, cols = linear_sum_assignment(cost)
    perm = np.empty(len(positions), dtype=int)
    perm[rows] = cols
    return perm


def min_spacing(offsets: np.ndarray) -> float:
    d = np.linalg.norm(offsets[:, None, :] - offsets[None, :, :], axis=2)
    return float(d[~np.eye(len(offsets), dtype=bool)].min())
