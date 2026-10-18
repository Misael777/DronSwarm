"""Modelo de hélice por teoría de elemento de pala con momento (BEMT), estático y en ascenso axial.

Geometría genérica de hélice de multirrotor: torsión de paso constante (β = atan(P / 2πr)) y cuerda con máximo a
media pala (c/R: 0.12 en la raíz, 0.18 a 0.45R, 0.08 en la punta), típica de hélices APC/T-Motor.
Perfil: sustentación lineal con pérdida, arrastre parabólico con corrección por Reynolds (Re ↓ en altura → Cd ↑).

LIMITACIÓN: es un modelo, no una medición. Se calibra con datos reales (fichas DJI en S03-07, banco de
empuje en S10). Si hay datos medidos (CSV rpm, ct, cp como los de UIUC), `PropTable.from_csv` los usa.
"""

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from .atmosphere import Air

INCH = 0.0254

# Perfil equivalente de hélice de multirrotor (Re 5·10⁴ – 3·10⁵)
CL_ALPHA = 5.7                  # 1/rad (≈ 0.9 · 2π)
ALPHA_0 = math.radians(-5.0)    # perfil con curvatura: ajustado para CT ≈ 0.10 en una 10x4.7 (valor típico)
CL_MAX = 1.2
CD0_REF = 0.014                 # a Re = 1·10⁵
RE_REF = 1.0e5
RE_EXP_LOW = -0.5               # Cd0 ∝ Re^-0.5 bajo Re_crit (régimen de bajo Reynolds, burbujas laminares)
RE_EXP_HIGH = -0.2              # Cd0 ∝ Re^-0.2 sobre Re_crit (capa límite turbulenta)
RE_CRIT = 2.0e5
K_CD = 0.02                     # arrastre inducido por sustentación del perfil


@dataclass(frozen=True)
class PropGeometry:
    diameter_m: float
    pitch_m: float
    blades: int = 2
    chord_root: float = 0.12    # c/R en la raíz del perfil
    chord_peak: float = 0.18    # c/R máximo, a chord_peak_at · R
    chord_peak_at: float = 0.45
    chord_tip: float = 0.08     # c/R en la punta
    hub_ratio: float = 0.15
    cd0_scale: float = 1.0      # calibración (S03-07): multiplica Cd0

    @classmethod
    def inches(cls, diameter_in: float, pitch_in: float, **kw) -> "PropGeometry":
        return cls(diameter_in * INCH, pitch_in * INCH, **kw)

    @property
    def radius(self) -> float:
        return self.diameter_m / 2

    @property
    def pitch_ratio(self) -> float:
        return self.pitch_m / self.diameter_m

    @property
    def disk_area(self) -> float:
        return math.pi * self.radius ** 2

    @property
    def label(self) -> str:
        return f"{self.diameter_m / INCH:.0f}x{self.pitch_m / INCH:.1f}"


def _airfoil(alpha: float, reynolds: float, cd0_scale: float) -> tuple[float, float]:
    cl = max(-CL_MAX, min(CL_MAX, CL_ALPHA * (alpha - ALPHA_0)))
    re = max(reynolds, 1e4)
    if re <= RE_CRIT:
        re_factor = (re / RE_REF) ** RE_EXP_LOW
    else:
        re_factor = (RE_CRIT / RE_REF) ** RE_EXP_LOW * (re / RE_CRIT) ** RE_EXP_HIGH
    cd0 = CD0_REF * cd0_scale * re_factor
    stalled = abs(CL_ALPHA * (alpha - ALPHA_0)) > CL_MAX
    cd = cd0 + K_CD * cl * cl + (0.5 * math.sin(abs(alpha)) if stalled else 0.0)
    return cl, cd


def _element_loads(v: float, r: float, beta: float, chord: float, ut: float, v_axial: float,
                   geom: PropGeometry, air: Air) -> tuple[float, float, float]:
    """Empuje y torque por unidad de radio (elemento de pala) y empuje por momento, para inducida v."""
    rho, b, big_r = air.density, geom.blades, geom.radius
    ua = v_axial + v
    phi = math.atan2(ua, ut)
    w2 = ua * ua + ut * ut
    cl, cd = _airfoil(beta - phi, rho * math.sqrt(w2) * chord / air.viscosity, geom.cd0_scale)
    q = 0.5 * rho * w2 * b * chord
    f = b / 2 * (big_r - r) / (r * max(math.sin(phi), 1e-6))
    tip_loss = 2 / math.pi * math.acos(min(1.0, math.exp(-f)))
    dt_be = q * (cl * math.cos(phi) - cd * math.sin(phi))
    dq_be = q * (cl * math.sin(phi) + cd * math.cos(phi)) * r
    dt_mom = 4 * math.pi * r * rho * ua * v * tip_loss
    return dt_be, dq_be, dt_mom


def _momentum_residual(v: float, *args) -> float:
    dt_be, _, dt_mom = _element_loads(v, *args)
    return dt_mom - dt_be


def bemt(geom: PropGeometry, rpm: float, air: Air, v_axial: float = 0.0, n_elem: int = 30) -> tuple[float, float]:
    """Empuje [N] y torque [N·m] de una hélice a rpm, con velocidad axial v_axial [m/s] (0 = estático)."""
    omega = rpm * 2 * math.pi / 60
    big_r = geom.radius
    r_hub = geom.hub_ratio * big_r
    edges = np.linspace(r_hub, big_r, n_elem + 1)
    thrust = torque = 0.0
    for r0, r1 in zip(edges[:-1], edges[1:]):
        r, dr = 0.5 * (r0 + r1), r1 - r0
        beta = math.atan(geom.pitch_m / (2 * math.pi * r))
        chord = big_r * float(np.interp(r / big_r, [geom.hub_ratio, geom.chord_peak_at, 1.0],
                                        [geom.chord_root, geom.chord_peak, geom.chord_tip]))
        ut = omega * r
        args = (r, beta, chord, ut, v_axial, geom, air)
        if _momentum_residual(0.0, *args) * _momentum_residual(ut, *args) < 0:
            v = brentq(_momentum_residual, 0.0, ut, args=args, xtol=1e-6)
        else:
            v = 0.0
        dt, dq, _ = _element_loads(v, *args)
        thrust += dt * dr
        torque += dq * dr
    return thrust, torque


@dataclass
class PropTable:
    """Empuje y torque precalculados vs rpm para una geometría y un aire dados (interpolación rápida)."""

    geom: PropGeometry
    air: Air
    rpm: np.ndarray = field(repr=False)
    thrust: np.ndarray = field(repr=False)
    torque: np.ndarray = field(repr=False)
    source: str = "BEMT"

    @classmethod
    def build(cls, geom: PropGeometry, air: Air, rpm_max: float | None = None, n: int = 24) -> "PropTable":
        tip_mach_limit = 0.6                       # más allá: ruido y pérdidas de compresibilidad
        if rpm_max is None:
            rpm_max = tip_mach_limit * air.speed_of_sound / geom.radius * 60 / (2 * math.pi)
        rpm = np.linspace(rpm_max * 0.05, rpm_max, n)
        tq = np.array([bemt(geom, x, air) for x in rpm])
        return cls(geom, air, rpm, tq[:, 0], tq[:, 1])

    @classmethod
    def from_csv(cls, geom: PropGeometry, air: Air, path: Path) -> "PropTable":
        """Datos medidos con columnas rpm, ct, cp (definición n = rev/s, como UIUC)."""
        rows = list(csv.DictReader(open(path)))
        rpm = np.array([float(r["rpm"]) for r in rows])
        n = rpm / 60
        ct = np.array([float(r["ct"]) for r in rows])
        cp = np.array([float(r["cp"]) for r in rows])
        d, rho = geom.diameter_m, air.density
        thrust = ct * rho * n ** 2 * d ** 4
        torque = cp * rho * n ** 3 * d ** 5 / (2 * math.pi * n)
        return cls(geom, air, rpm, thrust, torque, source=f"medido: {path.name}")

    @property
    def max_rpm(self) -> float:
        return float(self.rpm[-1])

    def thrust_at(self, rpm: float) -> float:
        return float(np.interp(rpm, self.rpm, self.thrust))

    def torque_at(self, rpm: float) -> float:
        return float(np.interp(rpm, self.rpm, self.torque))

    def rpm_for_thrust(self, thrust_n: float) -> float:
        if thrust_n > self.thrust[-1]:
            raise ValueError(f"{self.geom.label}: {thrust_n:.1f} N supera el límite de punta ({self.thrust[-1]:.1f} N)")
        return float(np.interp(thrust_n, self.thrust, self.rpm))

    def coefficients(self, rpm: float) -> dict:
        n = rpm / 60
        d, rho = self.geom.diameter_m, self.air.density
        t, q = self.thrust_at(rpm), self.torque_at(rpm)
        ct = t / (rho * n ** 2 * d ** 4)
        cp = q * 2 * math.pi * n / (rho * n ** 3 * d ** 5)
        fm = math.sqrt(2 / math.pi) * ct ** 1.5 / cp
        return {"ct": ct, "cp": cp, "figure_of_merit": fm}


def ideal_induced_velocity(thrust_n: float, air: Air, geom: PropGeometry) -> float:
    """Velocidad inducida en hover según la teoría de momento: v_h = √(T / 2ρA)."""
    return math.sqrt(thrust_n / (2 * air.density * geom.disk_area))
