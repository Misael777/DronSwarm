"""S06-01 · Control de formación distribuido: consenso o líder-seguidor.

Cada dron i tiene un puesto d_i en la formación (offset en el mundo) y calcula su propia velocidad con lo que sabe
de sus vecinos por radio (estados con retardo, a veces perdidos). Con ξ_i = p_i − d_i ("dónde estaría el centro de
la formación según el dron i"):

    v_i = v_ref + k_ref·(r − ξ_i) + k_cons·promedio_j(ξ̂_j − ξ_i)

  - Consenso: todos conocen la trayectoria de referencia r(t) de la misión (cargada antes del vuelo, sincronizada
    por la hora del GNSS); el término de consenso mantiene la forma aunque cada uno siga la ruta con error. Si un
    dron cae, los demás siguen sin él.
  - Líder-seguidor: solo el líder sigue la misión; los seguidores toman r = posición del líder recibida por radio.
    Más simple, pero el líder es un punto único de falla: sin noticias del líder, los seguidores se quedan quietos
    (hover) hasta recuperar el enlace o recibir otra orden.

ξ̂_j se extrapola con la velocidad del vecino por la edad del mensaje (compensa la latencia). Mensajes más viejos
que `stale_s` se descartan: el enlace se considera caído.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class NeighborState:
    pos: np.ndarray                  # ENU [m]
    vel: np.ndarray                  # ENU [m/s]
    offset: np.ndarray               # su puesto en la formación (mundo)
    t_sent: float                    # hora en que el vecino midió ese estado
    is_leader: bool = False


@dataclass
class FormationGains:
    k_ref: float = 0.6               # seguimiento de la referencia [1/s]
    k_cons: float = 0.5              # acuerdo con los vecinos [1/s]
    k_alt: float = 0.8               # altura [1/s]
    v_max: float = 5.0               # velocidad horizontal máxima [m/s]
    vz_max: float = 1.5
    stale_s: float = 1.5             # edad máxima de un mensaje para usarlo


def predicted(n: NeighborState, t: float) -> np.ndarray:
    return n.pos + n.vel * max(0.0, t - n.t_sent)


def fresh(neighbors: dict[int, NeighborState], t: float, stale_s: float) -> dict[int, NeighborState]:
    return {j: n for j, n in neighbors.items() if t - n.t_sent <= stale_s}


def saturate(v: np.ndarray, vmax: float) -> np.ndarray:
    s = float(np.linalg.norm(v))
    return v * (vmax / s) if s > vmax else v


def formation_velocity(t: float, pos: np.ndarray, offset: np.ndarray, ref: np.ndarray | None, ref_vel: np.ndarray,
                       neighbors: dict[int, NeighborState], alt_ref: float, g: FormationGains,
                       mode: str = "consensus") -> tuple[np.ndarray, dict]:
    """Velocidad deseada (ENU, 3D) del dron con posición `pos` (3D) y puesto `offset` (2D).

    `ref` es el centro de la formación según la misión (modo consenso o el líder); en líder-seguidor los seguidores
    pasan ref=None y se usa el estado del líder recibido por radio. Devuelve la velocidad y datos de diagnóstico.
    """
    nb = fresh(neighbors, t, g.stale_s)
    xi = pos[:2] - offset
    info = {"neighbors": len(nb), "leader_ok": True}
    if mode == "leader" and ref is None:
        leader = next((n for n in nb.values() if n.is_leader), None)
        if leader is None:                                   # sin líder: mantener posición
            info["leader_ok"] = False
            vz = np.clip(g.k_alt * (alt_ref - pos[2]), -g.vz_max, g.vz_max)
            return np.array([0.0, 0.0, vz]), info
        ref = predicted(leader, t)[:2] - leader.offset
        ref_vel = leader.vel[:2]
    v = np.array(ref_vel[:2], dtype=float) + g.k_ref * (ref[:2] - xi)
    if nb:
        cons = np.mean([predicted(n, t)[:2] - n.offset - xi for n in nb.values()], axis=0)
        v = v + g.k_cons * cons
    v = saturate(v, g.v_max)
    vz = float(np.clip(g.k_alt * (alt_ref - pos[2]), -g.vz_max, g.vz_max))
    return np.array([v[0], v[1], vz]), info
