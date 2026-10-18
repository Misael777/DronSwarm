"""Atmósfera estándar internacional (ISA, troposfera) con temperatura real del día.

La presión sigue la ISA con la altitud; la densidad usa la temperatura real (aire caliente en altura = menos
densidad = menos empuje). Válido hasta 11 km.
"""

from dataclasses import dataclass

G0 = 9.80665            # m/s²
R_AIR = 287.05287       # J/(kg·K)
T0 = 288.15             # K, nivel del mar ISA
P0 = 101_325.0          # Pa
LAPSE = 0.0065          # K/m
GAMMA = 1.4
MU_REF, T_MU_REF, S_MU = 1.716e-5, 273.15, 110.4   # Sutherland


@dataclass(frozen=True)
class Air:
    altitude_m: float
    temperature_k: float
    pressure_pa: float
    density: float          # kg/m³
    viscosity: float        # Pa·s
    speed_of_sound: float   # m/s

    @property
    def temperature_c(self) -> float:
        return self.temperature_k - 273.15

    @property
    def sigma(self) -> float:
        """Densidad relativa al nivel del mar ISA."""
        return self.density / isa(0).density


def isa_temperature_k(altitude_m: float) -> float:
    if not 0 <= altitude_m <= 11_000:
        raise ValueError("modelo válido de 0 a 11,000 m")
    return T0 - LAPSE * altitude_m


def isa_pressure_pa(altitude_m: float) -> float:
    return P0 * (isa_temperature_k(altitude_m) / T0) ** (G0 / (R_AIR * LAPSE))


def air(altitude_m: float, temperature_c: float | None = None) -> Air:
    """Aire a una altitud; sin temperatura usa la ISA, con temperatura usa la del día."""
    t = isa_temperature_k(altitude_m) if temperature_c is None else temperature_c + 273.15
    p = isa_pressure_pa(altitude_m)
    rho = p / (R_AIR * t)
    mu = MU_REF * (t / T_MU_REF) ** 1.5 * (T_MU_REF + S_MU) / (t + S_MU)
    return Air(altitude_m, t, p, rho, mu, (GAMMA * R_AIR * t) ** 0.5)


def isa(altitude_m: float) -> Air:
    return air(altitude_m)
