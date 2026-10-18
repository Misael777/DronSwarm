"""S06-01/03 · Misión del enjambre y "cerebro" de cada dron (formación + consenso + evitación).

El mismo código corre en el simulador cinemático rápido (`sim_kinematic.py`, cientos de corridas Monte Carlo) y en
PX4 + Gazebo (`sitl_swarm.py`, MAVSDK offboard por velocidad). En el dron real correrá en la computadora a bordo.

Escenario de prueba (ENU, origen = centro de la formación al despegar):
  1. formar en V                      4. cruce antipodal: cada dron va al puesto opuesto del círculo (todos
  2. tránsito 60 m al norte en V,        pasan por el centro a la vez: la prueba más dura para la evitación)
     una torre de iluminación en medio 5. regreso en línea al origen (pasa otra vez junto a la torre)
  3. círculo de 10 m de radio
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from control.swarm import formation
from control.swarm.avoidance import AvoidParams, Obstacle, avoid
from control.swarm.consensus import FormationGains, NeighborState, formation_velocity


@dataclass
class Phase:
    name: str
    shape: str
    size: float
    goal: tuple[float, float]               # centro de la formación al final de la fase
    heading_deg: float                      # rumbo de avance (desde el este, antihorario): 90 = norte
    swap: bool = False                      # cruce antipodal: cada dron al puesto opuesto
    timeout_s: float = 90.0


DEFAULT_PHASES = [
    Phase("formar_v", "v", 6.0, (0.0, 0.0), 90.0, timeout_s=60),
    Phase("transito_v", "v", 6.0, (0.0, 60.0), 90.0, timeout_s=90),
    Phase("circulo", "circulo", 10.0, (0.0, 60.0), 90.0, timeout_s=60),
    Phase("cruce", "circulo", 10.0, (0.0, 60.0), 90.0, swap=True, timeout_s=60),
    Phase("linea_regreso", "linea", 6.0, (0.0, 0.0), -90.0, timeout_s=90),
]
# Torre de iluminación en la ruta (las faenas mineras están llenas de ellas): 1 m de radio, 25 m de alto
DEFAULT_OBSTACLES = [Obstacle(0.0, 32.0, 1.0, 25.0)]


@dataclass
class Scenario:
    n: int
    phases: list[Phase] = field(default_factory=lambda: list(DEFAULT_PHASES))
    obstacles: list[Obstacle] = field(default_factory=lambda: list(DEFAULT_OBSTACLES))
    cruise: float = 4.0                     # velocidad de la referencia [m/s]
    form_tol: float = 1.5                   # error de formación para dar una fase por cumplida [m]
    settle_s: float = 3.0                   # tiempo que debe sostenerse en formación

    def __post_init__(self):
        self.k = -1
        self.ref = np.zeros(2)
        self.slots = np.zeros((self.n, 2))  # puesto (offset en el mundo) de cada dron
        self.t_phase = 0.0
        self.t_ok = None
        self.log: list[dict] = []

    @property
    def phase(self) -> Phase | None:
        return self.phases[self.k] if 0 <= self.k < len(self.phases) else None

    @property
    def done(self) -> bool:
        return self.k >= len(self.phases)

    def start(self, t: float, positions: np.ndarray):
        self.ref = positions[:, :2].mean(axis=0)
        self._next(t, positions)

    def _next(self, t: float, positions: np.ndarray):
        if self.phase is not None:
            self.log[-1].update(t_end=round(t, 1), duration_s=round(t - self.t_phase, 1))
        self.k += 1
        self.t_phase, self.t_ok = t, None
        ph = self.phase
        if ph is None:
            return
        shape = formation.to_world(formation.make(ph.shape, self.n, ph.size), math.radians(ph.heading_deg))
        if ph.swap:                         # el puesto opuesto del círculo en el que está cada uno
            current = np.array([np.argmin(np.linalg.norm(shape - s, axis=1)) for s in self.slots])
            self.slots = shape[(current + self.n // 2) % self.n]
        else:                               # asignación óptima desde donde están ahora (respecto del centro)
            perm = formation.assign(positions[:, :2] - positions[:, :2].mean(axis=0), shape)
            self.slots = shape[perm]
        self.log.append({"phase": ph.name, "t_start": round(t, 1), "timed_out": False})

    def update(self, t: float, dt: float, positions: np.ndarray, alive: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
        """Avanza la referencia; devuelve (ref, ref_vel) del centro de la formación.

        Las fases las secuencia la estación de tierra; `alive` excluye a los drones fuera de la formación (sin enlace,
        con falla) para que el resto pueda seguir."""
        alive = np.ones(len(positions), dtype=bool) if alive is None else alive
        ph = self.phase
        if ph is None:
            return self.ref, np.zeros(2)
        to_goal = np.array(ph.goal) - self.ref
        dist = float(np.linalg.norm(to_goal))
        ref_vel = np.zeros(2)
        # la referencia espera al enjambre: si el centro real se atrasa (obstáculo, viento, un dron lento), frena
        lag = float(np.linalg.norm(positions[alive, :2].mean(axis=0) - self.slots[alive].mean(axis=0) - self.ref))
        speed = self.cruise * float(np.clip(1.5 - lag / 2.0, 0.2, 1.0))
        if dist > 1e-3:
            step = min(dist, speed * dt)
            ref_vel = to_goal / dist * (step / dt)
            self.ref = self.ref + to_goal / dist * step
        err = self.formation_error(positions, alive)
        if dist < 0.5 and err < self.form_tol:
            self.t_ok = self.t_ok if self.t_ok is not None else t
        else:
            self.t_ok = None
        timed_out = t - self.t_phase > ph.timeout_s
        if (self.t_ok is not None and t - self.t_ok >= self.settle_s) or timed_out:
            self.log[-1].update(timed_out=timed_out, form_error_end_m=round(err, 2))
            self._next(t, positions)
        return self.ref, ref_vel

    def formation_error(self, positions: np.ndarray, alive: np.ndarray | None = None) -> float:
        """Error máximo de cada dron respecto de su puesto (ref + slot)."""
        e = np.linalg.norm(positions[:, :2] - (self.ref + self.slots), axis=1)
        return float(e[alive].max() if alive is not None and alive.any() else e.max())


@dataclass
class Agent:
    """Lo que corre en cada dron: estado de los vecinos por radio + formación + evitación.

    Protocolo de pérdida de enlace (lo conocen todos de antemano, así no hace falta comunicarse para aplicarlo):
      - el dron que no recibe nada por `lost_link_s` se detiene y sube `climb_m` a una capa reservada (después el
        autopiloto hace su retorno con la falla de enlace de PX4);
      - los demás tratan la última posición conocida de un vecino mudo como un obstáculo durante `ghost_s`.
    """

    i: int
    mode: str = "consensus"                 # "consensus" | "leader" (dron 0 = líder)
    gains: FormationGains = field(default_factory=FormationGains)
    avoid: AvoidParams = field(default_factory=AvoidParams)
    use_avoidance: bool = True
    lost_link_s: float = 0.8              # a 10 Hz y 5 vecinos, 0.8 s sin nada solo ocurre si la radio cayó
    slow_after_s: float = 0.3             # desde aquí frena en proporción a lo viejo de su información
    climb_m: float = 8.0
    ghost_s: float = 20.0

    def __post_init__(self):
        self.table: dict[int, NeighborState] = {}
        self.last_rx: float | None = None
        self.lost = False

    def receive(self, j: int, state: NeighborState):
        old = self.table.get(j)
        if old is None or state.t_sent >= old.t_sent:      # los mensajes pueden llegar desordenados
            self.table[j] = state
        self.last_rx = state.t_sent if self.last_rx is None else max(self.last_rx, state.t_sent)

    def others(self, t: float) -> list[tuple[np.ndarray, np.ndarray]]:
        out = []
        for n in self.table.values():
            age = t - n.t_sent
            if age <= self.gains.stale_s * 2:
                out.append((n.pos + n.vel * age, n.vel))
            elif age <= self.ghost_s:                        # vecino mudo: frenó donde estaba (protocolo)
                out.append((n.pos + n.vel * (self.lost_link_s + 0.6), np.zeros(3)))
        return out

    def command(self, t: float, pos: np.ndarray, vel: np.ndarray, slot: np.ndarray, ref: np.ndarray,
                ref_vel: np.ndarray, alt: float, obstacles: list[Obstacle]) -> tuple[np.ndarray, dict]:
        if self.last_rx is not None and t - self.last_rx > self.lost_link_s:
            self.lost = True
        if self.lost:                                         # sin radio: detenerse y subir a la capa reservada
            vz = float(np.clip(self.gains.k_alt * (alt + self.climb_m - pos[2]), -self.gains.vz_max, self.gains.vz_max))
            return np.array([0.0, 0.0, vz]), {"lost_link": True, "neighbors": 0}
        follower = self.mode == "leader" and self.i != 0
        v, info = formation_velocity(t, pos, slot, None if follower else ref, ref_vel, self.table, alt, self.gains,
                                     mode=self.mode)
        if self.use_avoidance:
            v, ainfo = avoid(pos, vel, v, self.others(t), obstacles, self.avoid)
            info.update(ainfo)
        if self.last_rx is not None:                          # información vieja = volar más lento
            age = t - self.last_rx
            k = float(np.clip(1 - (age - self.slow_after_s) / (self.lost_link_s - self.slow_after_s), 0.0, 1.0))
            vz = v[2] if k >= 1.0 else self.gains.vz_max * (1 - k)    # sin ver a nadie, escapar hacia arriba
            v = np.array([v[0] * k, v[1] * k, vz])
        return v, info
