"""S04-06 · Brazos de tubo de carbono como vigas en voladizo: resistencia, deflexión y frecuencia natural.

- Carga: empuje máximo del rotor en la punta × factor de seguridad estructural (2.5).
- Frecuencia natural (voladizo con masa en la punta): debe alejarse ≥ 20 % de 1P (giro) y 2P (paso de pala) en hover.
Propiedades de tubo de carbono enrollado (roll-wrapped), conservadoras; se confirman con proveedor en S07.
"""

import math
from dataclasses import dataclass

E_CARBON = 70e9            # Pa, módulo axial (pultruido llega a ~120 GPa)
SIGMA_ULT = 500e6          # Pa, resistencia a flexión
RHO_CARBON = 1600.0        # kg/m³
MAX_DEFLECTION = 0.015     # deflexión máxima de servicio / longitud
FREQ_SEPARATION = 0.20     # separación mínima de 1P y 2P en hover
MIN_OD_MM = 16             # regla de robustez: golpes, aterrizajes duros y abrazadera de motor estándar
# Nota: en drones grandes la frecuencia del brazo suele quedar bajo 1P (se cruza solo al acelerar); el análisis
# modal con FEA en S07-S08 confirma que no haya resonancia en hover.

# Tubos estándar (diámetro exterior mm, pared mm)
TUBES = [(12, 1.0), (14, 1.0), (16, 1.0), (16, 1.5), (18, 1.5), (20, 1.0), (20, 1.5), (22, 1.5),
         (25, 1.5), (25, 2.0), (28, 2.0), (30, 2.0), (32, 2.0), (35, 2.0), (40, 2.0)]


def tube_cost_per_m(od_mm: float) -> float:
    """US$/m (estimado 2026; hoja BOM_Costos: Ø20 ≈ 24 US$/m)."""
    return 8 + 0.8 * od_mm


@dataclass(frozen=True)
class ArmResult:
    od_mm: float
    wall_mm: float
    length_m: float
    mass_kg: float
    cost_usd: float
    stress_mpa: float
    stress_margin: float         # σ_ult / σ_diseño − 1
    deflection_pct: float
    f_natural_hz: float
    f_1p_hz: float
    f_2p_hz: float

    @property
    def label(self) -> str:
        return f"Ø{self.od_mm:g}×{self.wall_mm:g} mm"


def check_arm(od_mm: float, wall_mm: float, length_m: float, thrust_max_n: float, tip_mass_kg: float,
              hover_rpm: float, blades: int, sf: float) -> ArmResult:
    do, di = od_mm / 1000, (od_mm - 2 * wall_mm) / 1000
    inertia = math.pi / 64 * (do ** 4 - di ** 4)
    area = math.pi / 4 * (do ** 2 - di ** 2)
    m_arm = RHO_CARBON * area * length_m
    stress = sf * thrust_max_n * length_m * (do / 2) / inertia
    deflection = thrust_max_n * length_m ** 3 / (3 * E_CARBON * inertia)
    f_n = math.sqrt(3 * E_CARBON * inertia / (length_m ** 3 * (tip_mass_kg + 0.24 * m_arm))) / (2 * math.pi)
    return ArmResult(od_mm, wall_mm, length_m, m_arm, tube_cost_per_m(od_mm) * length_m, stress / 1e6,
                     SIGMA_ULT / stress - 1, 100 * deflection / length_m, f_n, hover_rpm / 60, blades * hover_rpm / 60)


def arm_ok(a: ArmResult) -> bool:
    sep = lambda f: abs(a.f_natural_hz - f) / f >= FREQ_SEPARATION  # noqa: E731
    return a.stress_margin >= 0 and a.deflection_pct <= 100 * MAX_DEFLECTION and sep(a.f_1p_hz) and sep(a.f_2p_hz)


def select_arm(length_m: float, thrust_max_n: float, tip_mass_kg: float, hover_rpm: float, blades: int, sf: float) -> ArmResult:
    """El tubo estándar más liviano que cumple resistencia, deflexión y separación de frecuencias."""
    results = [check_arm(od, w, length_m, thrust_max_n, tip_mass_kg, hover_rpm, blades, sf)
               for od, w in TUBES if od >= MIN_OD_MM]
    ok = [a for a in results if arm_ok(a)]
    if not ok:
        raise ValueError(f"ningún tubo estándar sirve para L={length_m:.2f} m, T={thrust_max_n:.0f} N")
    return min(ok, key=lambda a: a.mass_kg)


def wheelbase_m(prop_diameter_m: float, rotors: int, clearance: float = 0.10) -> float:
    """Distancia diagonal entre motores para que las hélices vecinas no se toquen (con holgura)."""
    spacing = prop_diameter_m * (1 + clearance)
    if rotors == 4:
        return spacing * math.sqrt(2)          # quad X: vecinos a 90°
    if rotors == 6:
        return 2 * spacing                     # hexa: vecinos a 60° → separación = radio
    if rotors == 8:
        return spacing / math.sin(math.pi / 8)  # octo: vecinos a 45° → separación = 2R·sin(22.5°)
    raise ValueError("solo 4, 6 u 8 rotores")


def center_plates(wheelbase: float, rotors: int) -> tuple[float, float, float]:
    """Masa [kg], costo [US$] y diámetro [m] de las dos placas centrales de carbono más tornillería."""
    dia = 0.25 * wheelbase
    thickness = {4: 0.003, 6: 0.004, 8: 0.005}[rotors]
    area = 2 * math.pi / 4 * dia ** 2
    mass = area * thickness * RHO_CARBON + 0.04
    return mass, 15 + 1000 * area, dia
