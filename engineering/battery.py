"""Modelo de batería Li-ion de celdas 21700: energía útil, caída de voltaje, límite de corriente y frío.

Valores de celdas tomados de fichas de fabricante (a verificar al cotizar en S09); costo estimado 2026.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Cell:
    name: str
    capacity_ah: float
    v_nominal: float
    mass_kg: float
    i_max_cont: float      # A, descarga continua
    r_internal: float      # Ω
    cost_usd: float

    @property
    def energy_wh(self) -> float:
        return self.capacity_ah * self.v_nominal

    @property
    def specific_energy(self) -> float:
        return self.energy_wh / self.mass_kg


CELLS = {
    "P45B": Cell("Molicel INR21700-P45B", 4.5, 3.6, 0.070, 45.0, 0.010, 5.0),
    "P42A": Cell("Molicel INR21700-P42A", 4.2, 3.6, 0.070, 45.0, 0.012, 4.0),
    "50S": Cell("Samsung INR21700-50S", 5.0, 3.6, 0.072, 25.0, 0.014, 4.5),
}

PACK_MASS_OVERHEAD = 0.12      # niquelado, aislamiento, caja: fracción sobre la masa de celdas
BMS_MASS, BMS_COST = 0.030, 15.0
DEPTH_OF_DISCHARGE = 0.90      # se aterriza con ≥ 10 % de carga


def capacity_factor(temperature_c: float) -> float:
    """Capacidad disponible vs temperatura de la celda (Li-ion a descarga moderada)."""
    return min(1.0, max(0.70, 1.0 - 0.0057 * (20 - temperature_c)))   # 1.0 a 20 °C, ≈ 0.80 a -15 °C


@dataclass(frozen=True)
class Pack:
    cell: Cell
    series: int
    parallel: int

    @property
    def cells(self) -> int:
        return self.series * self.parallel

    @property
    def v_nominal(self) -> float:
        return self.series * self.cell.v_nominal

    @property
    def energy_wh(self) -> float:
        return self.cells * self.cell.energy_wh

    @property
    def mass_kg(self) -> float:
        return self.cells * self.cell.mass_kg * (1 + PACK_MASS_OVERHEAD) + BMS_MASS

    @property
    def cost_usd(self) -> float:
        return self.cells * self.cell.cost_usd + BMS_COST

    @property
    def i_max(self) -> float:
        return self.parallel * self.cell.i_max_cont

    @property
    def r_internal(self) -> float:
        return self.series * self.cell.r_internal / self.parallel

    def voltage_under_load(self, power_w: float, soc_voltage_per_cell: float | None = None) -> float:
        """Voltaje en bornes a una potencia dada (resuelve V = E − I·R con I = P/V)."""
        e = self.series * (soc_voltage_per_cell or self.cell.v_nominal)
        disc = e * e - 4 * self.r_internal * power_w
        if disc <= 0:
            return e / 2      # potencia por encima de la máxima transferible
        return (e + math.sqrt(disc)) / 2

    def usable_energy_wh(self, temperature_c: float = 20.0) -> float:
        return self.energy_wh * DEPTH_OF_DISCHARGE * capacity_factor(temperature_c)

    @property
    def label(self) -> str:
        return f"{self.series}S{self.parallel}P {self.cell.name.split('-')[-1]}"
