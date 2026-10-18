"""S06-03 · Evitación de colisiones entre drones y contra obstáculos.

Filtro sobre la velocidad deseada (la de la formación o la misión), con tres términos:

1. Repulsión por cercanía: crece rápido al acercarse a la distancia de seguridad `r_safe` (campos potenciales).
2. Predicción del punto de máximo acercamiento (CPA) con la velocidad relativa: si dentro de `horizon_s` segundos
   dos drones pasarían a menos de `r_cpa`, se empujan de costado, ANTES de estar cerca. Todos suman además un sesgo
   hacia su derecha, como en tránsito: en cruces de muchos drones se forma una rotonda sin coordinarse.
3. Se quita la componente de la velocidad deseada que acerca al dron a un vecino o a un obstáculo que ya está
   dentro de la zona de seguridad.

Obstáculos: cilindros verticales (torres de iluminación, postes, antenas) con radio y altura; cada dron los rodea
por el lado en que ya viene (la formación se abre alrededor, como el agua en un poste) y, de frente exacto, por la
derecha. Para la separación vertical: si dos drones están a más de `dz_sep` de altura no se consideran en conflicto.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class AvoidParams:
    r_safe: float = 3.0              # distancia mínima deseada entre centros de drones [m]
    r_infl: float = 7.0              # a partir de aquí empieza la repulsión
    r_cpa: float = 4.0               # acercamiento predicho que se considera conflicto
    horizon_s: float = 5.0
    k_rep: float = 3.0               # [m/s] repulsión máxima por vecino al llegar a r_safe
    k_cpa: float = 4.0               # [m/s]
    margin_obst: float = 2.5         # margen libre alrededor de un obstáculo (además de su radio y del dron)
    k_obst: float = 4.0              # [m/s] repulsión dentro del margen
    look_obst_m: float = 10.0        # distancia a la que empieza a desviarse de un obstáculo en su camino
    dz_sep: float = 4.0
    right_bias: float = 1.0          # sesgo a la derecha en todo conflicto predicho (rotonda espontánea): sin él,
                                     # el cruce de 6 drones por el centro chocaba en ~3 % de las corridas (S06)
    v_max: float = 5.0


@dataclass
class Obstacle:
    x: float
    y: float
    radius: float
    height: float = 1e9


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else np.zeros_like(v)


def _right(v: np.ndarray) -> np.ndarray:
    return np.array([v[1], -v[0]])


def _repel(dist: float, r_safe: float, r_infl: float, k: float) -> float:
    if dist >= r_infl:
        return 0.0
    x = (r_infl - dist) / (r_infl - r_safe)            # 0 en r_infl, 1 en r_safe, > 1 adentro
    return k * x * x


def _steer_obstacles(pos: np.ndarray, v: np.ndarray, obstacles: list[Obstacle], p: AvoidParams):
    """Campo de guiado: si un obstáculo está en el camino, la dirección gira hacia su tangente sin frenar (evita el
    mínimo local de los campos potenciales puros, donde el dron queda trabado de frente al obstáculo)."""
    push, blocked, clear = np.zeros(2), [], np.inf
    speed = float(np.linalg.norm(v))
    for ob in obstacles:
        if pos[2] > ob.height + p.dz_sep / 2:
            continue
        d = pos[:2] - np.array([ob.x, ob.y])
        dist = float(np.linalg.norm(d)) - ob.radius
        clear = min(clear, dist)
        away = _unit(d)
        if dist < p.margin_obst:                          # dentro del margen: repulsión dura
            push += _repel(dist, p.margin_obst * 0.4, p.margin_obst, p.k_obst) * away
            blocked.append(-away)
        if speed < 0.2 or dist > p.look_obst_m:
            continue
        h = v / speed
        if float(h @ -away) <= 0:                         # ya lo dejó atrás
            continue
        lateral = d - float(d @ h) * h                    # distancia lateral al pasar
        if float(np.linalg.norm(lateral)) > ob.radius + p.margin_obst + 1.0:
            continue                                      # pasa holgado
        tangents = (_right(away), -_right(away))
        t = max(tangents, key=lambda u: float(u @ h))     # la tangente que sigue avanzando (el lado en que ya está)
        if abs(float(tangents[0] @ h)) < 0.05:            # de frente exacto: por la derecha
            t = _right(h)
        w = float(np.clip((p.look_obst_m - dist) / (p.look_obst_m - p.margin_obst), 0.0, 1.0))
        v = speed * _unit((1 - w) * h + w * t)
    return v, push, blocked, clear


def avoid(pos: np.ndarray, vel: np.ndarray, v_des: np.ndarray, others: list[tuple[np.ndarray, np.ndarray]],
          obstacles: list[Obstacle], p: AvoidParams) -> tuple[np.ndarray, dict]:
    """Velocidad corregida (3D). `others` = [(pos, vel)] de los demás drones (estimados por radio)."""
    v, push, blocked, obst_clear = _steer_obstacles(pos, v_des[:2].astype(float), obstacles, p)
    closest = np.inf
    for po, vo in others:
        if abs(po[2] - pos[2]) > p.dz_sep:
            continue
        d = pos[:2] - po[:2]
        dist = float(np.linalg.norm(d))
        closest = min(closest, dist)
        away = _unit(d) if dist > 1e-6 else _right(_unit(v_des[:2] + 1e-6))
        push += _repel(dist, p.r_safe, p.r_infl, p.k_rep) * away
        if dist < p.r_safe * 1.3:
            blocked.append(-away)
        # acercamiento predicho
        vr = vel[:2] - vo[:2]
        vr2 = float(vr @ vr)
        if vr2 > 0.04:
            t_cpa = -float(d @ vr) / vr2
            if 0.0 < t_cpa < p.horizon_s:
                miss = d + vr * t_cpa
                m = float(np.linalg.norm(miss))
                if m < p.r_cpa:
                    side = _unit(miss) if m > 0.3 else _right(_unit(vr))     # de frente: por la derecha
                    side = _unit(side + p.right_bias * _right(_unit(vr)))
                    push += p.k_cpa * (1 - m / p.r_cpa) * (1 - t_cpa / p.horizon_s) * side
    v = v + push
    for b in blocked:                                  # no avanzar hacia lo que está demasiado cerca
        toward = float(v @ b)
        if toward > 0:
            v = v - toward * b
    n = float(np.linalg.norm(v))
    if n > p.v_max:
        v *= p.v_max / n
    return np.array([v[0], v[1], v_des[2]]), {"closest_m": closest, "obstacle_clearance_m": obst_clear,
                                              "active": bool(np.linalg.norm(push) > 0.05)}
