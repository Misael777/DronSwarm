"""S04 · Pruebas del dimensionamiento: estructura, inercia, presupuesto de masa y verificaciones."""

import math

import pytest

from engineering.atmosphere import air
from engineering.battery import CELLS, Pack
from engineering.inertia import PointMass, compute, rotor_positions
from engineering.mass_budget import evaluate
from engineering.propeller import PropGeometry, PropTable
from engineering.safety_factors import all_factors, design_cases
from engineering.structures import MIN_OD_MM, check_arm, select_arm, wheelbase_m

CD0_SCALE = 2.17      # valor de la calibración con el DJI M4E (validation.json)


def test_cantilever_stress_matches_hand_calc():
    # Ø20×1.5 mm, 0.25 m, 20 N en la punta, FS 2.5 → σ = M·c/I
    a = check_arm(20, 1.5, 0.25, 20.0, 0.1, 5000, 2, 2.5)
    inertia = math.pi / 64 * (0.020 ** 4 - 0.017 ** 4)
    sigma = 2.5 * 20 * 0.25 * 0.010 / inertia / 1e6
    assert a.stress_mpa == pytest.approx(sigma, rel=1e-6)


def test_select_arm_respects_minimum_diameter_and_criteria():
    a = select_arm(0.25, 15.0, 0.12, 4000, 2, 2.5)
    assert a.od_mm >= MIN_OD_MM and a.stress_margin >= 0 and a.deflection_pct <= 1.5


def test_wheelbase_props_do_not_touch():
    d = 0.4064                                    # 16"
    assert wheelbase_m(d, 4) / math.sqrt(2) >= d * 1.1 - 1e-9     # vecinos en quad X
    assert wheelbase_m(d, 6) / 2 >= d * 1.1 - 1e-9                # vecinos en hexa


def test_inertia_of_symmetric_quad():
    pts = [PointMass("c", 1.0, 0, 0, 0)] + [PointMass(f"m{i}", 0.1, x, y, 0) for i, (x, y) in enumerate(rotor_positions(4, 0.3))]
    r = compute(pts)
    assert r["cg_m"] == [0.0, 0.0, 0.0]
    assert r["ixx"] == pytest.approx(r["iyy"]) and r["izz"] == pytest.approx(4 * 0.1 * 0.3 ** 2)


@pytest.fixture(scope="module")
def ds_i_design():
    cases = design_cases()
    cfg = dict(cases["vehicles"]["DS-I"])          # escenario D recomendado: versión base sin RTK ni computadora
    cfg["fixed_equipment"] = {k: v for k, v in cfg["fixed_equipment"].items() if k not in ("rtk_module", "companion_computer")}
    cfg["endurance_basis"], cfg["hover_endurance_min"] = "new", 30
    env = cases["environment"]
    airs = {"thrust": air(env["thrust_case"]["altitude_m"], env["thrust_case"]["temperature_c"]),
            "endurance": air(env["endurance_case"]["altitude_m"], env["endurance_case"]["temperature_c"]),
            "sea_level": air(0, 15)}
    geom = PropGeometry.inches(17, 7.7, cd0_scale=CD0_SCALE)
    tables = {k: PropTable.build(geom, a) for k, a in airs.items()}
    return evaluate("DS-I", cfg, geom, Pack(CELLS["50S"], 6, 2), all_factors(), airs, tables,
                    cases["drag_area_m2"]["DS-I"], 20.0, {"endurance": 0, "cold": -15})


def test_mass_budget_converges_and_adds_up(ds_i_design):
    d = ds_i_design
    assert sum(d.masses.values()) == pytest.approx(d.mtow_kg, abs=0.002)
    assert sum(d.costs.values()) == pytest.approx(d.bom_cost_usd, abs=0.5)
    assert 2.0 < d.mtow_kg < 3.5


def test_recommended_ds_i_passes_all_checks(ds_i_design):
    failed = [name for name, c in ds_i_design.checks.items() if not c["ok"]]
    assert not failed, failed


def test_endurance_metrics_are_ordered(ds_i_design):
    p = ds_i_design.performance
    # fin de vida < frío < nueva a 4,500 m < estilo DJI (nivel del mar, hasta 0 %)
    assert p["endurance_eol_min"] < p["endurance_cold_min"] < p["endurance_new_min"] < p["endurance_dji_style_min"]
