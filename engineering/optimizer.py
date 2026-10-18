"""S04-02 · Optimizador de configuración: barrido hélice × paso × celdas × tipo de celda × paralelo.

Para cada combinación se itera la MTOW y se verifican los requisitos (mass_budget.evaluate). Entre los diseños
factibles se elige el de menor costo de materiales (BOM); en empate, el más liviano.
"""

from dataclasses import dataclass

from .atmosphere import air
from .battery import CELLS, Pack
from .design import Infeasible
from .mass_budget import Design, evaluate
from .propeller import PropGeometry, PropTable
from .safety_factors import all_factors, design_cases

PITCH_RATIOS = (0.35, 0.45, 0.55)
MAX_PARALLEL = 8
AVIONICS_W = {"DS-I": 20.0, "DS-D": 25.0, "DS-H": 30.0}     # FC, GNSS/RTK, radio, computadora, cámara/gimbal


@dataclass
class SweepResult:
    vehicle: str
    evaluated: int
    feasible: list[Design]
    rejected: dict[str, int]                   # motivo → cantidad

    @property
    def best(self) -> Design | None:
        return min(self.feasible, key=lambda d: (d.bom_cost_usd, d.mtow_kg)) if self.feasible else None

    @property
    def lightest(self) -> Design | None:
        return min(self.feasible, key=lambda d: d.mtow_kg) if self.feasible else None


def sweep(vehicle: str, cd0_scale: float, overrides: dict | None = None, verbose: bool = False) -> SweepResult:
    """Barrido completo. overrides cambia requisitos del vehículo (escenarios para el Gate G0)."""
    cases = design_cases()
    cfg = {**cases["vehicles"][vehicle], **(overrides or {})}
    if overrides and "remove_equipment" in overrides:
        cfg["fixed_equipment"] = {k: v for k, v in cfg["fixed_equipment"].items() if k not in overrides["remove_equipment"]}
    env = cases["environment"]
    airs = {"thrust": air(env["thrust_case"]["altitude_m"], env["thrust_case"]["temperature_c"]),
            "endurance": air(env["endurance_case"]["altitude_m"], env["endurance_case"]["temperature_c"]),
            "sea_level": air(env["sea_level"]["altitude_m"], env["sea_level"]["temperature_c"])}
    temps = {"endurance": env["endurance_case"]["temperature_c"], "cold": env["cold_case"]["temperature_c"]}
    sf = all_factors()
    feasible, rejected, evaluated = [], {}, 0
    for d_in in cfg["prop_diameter_in"]:
        for pr in PITCH_RATIOS:
            geom = PropGeometry.inches(d_in, d_in * pr, cd0_scale=cd0_scale)
            tables = {k: PropTable.build(geom, a) for k, a in airs.items()}  # empuje, autonomía, nivel del mar
            for series in cfg["cells_series"]:
                for cell_key in CELLS:
                    for parallel in range(1, MAX_PARALLEL + 1):
                        evaluated += 1
                        pack = Pack(CELLS[cell_key], series, parallel)
                        try:
                            d = evaluate(vehicle, cfg, geom, pack, sf, airs, tables, cases["drag_area_m2"][vehicle],
                                         AVIONICS_W[vehicle], temps)
                        except Infeasible as e:
                            reason = "hélice o estructura insuficiente" if "punta" in str(e) or "tubo" in str(e) else "MTOW no converge"
                            rejected[reason] = rejected.get(reason, 0) + 1
                            continue
                        if d.feasible:
                            feasible.append(d)
                        else:
                            for name, c in d.checks.items():
                                if not c["ok"]:
                                    rejected[name] = rejected.get(name, 0) + 1
                                    break
    if verbose:
        print(f"{vehicle}: {evaluated} combinaciones, {len(feasible)} factibles")
    return SweepResult(vehicle, evaluated, feasible, rejected)
