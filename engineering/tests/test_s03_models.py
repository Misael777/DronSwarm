"""S03 · Pruebas de los modelos de ingeniería (atmósfera, hélice, motor, batería, misión, validación)."""

import math

import pytest

from engineering import atmosphere as atm
from engineering.battery import CELLS, Pack, capacity_factor
from engineering.design import Infeasible, size_motor
from engineering.mission_loads import Propulsion, delivery_mission, hover_endurance_min
from engineering.motor import Motor, max_thrust_point
from engineering.propeller import PropGeometry, PropTable
from engineering.safety_factors import all_factors, design_cases


# --- S03-01 atmósfera: tabla ISA (ICAO Doc 7488), error < 0.5 % ---
@pytest.mark.parametrize("h, rho_ref, t_ref", [
    (0, 1.2250, 288.15), (1000, 1.1117, 281.65), (2000, 1.0066, 275.15),
    (3000, 0.9093, 268.65), (5000, 0.7364, 255.65), (8000, 0.5258, 236.15),
])
def test_isa_table(h, rho_ref, t_ref):
    a = atm.isa(h)
    assert a.density == pytest.approx(rho_ref, rel=0.005)
    assert a.temperature_k == pytest.approx(t_ref, abs=0.01)


def test_design_case_hot_high_density():
    hot = atm.air(5000, 15)                     # caso de empuje: 5,000 msnm a 15 °C
    assert hot.density == pytest.approx(0.653, rel=0.01)
    assert 1 - hot.sigma == pytest.approx(0.467, abs=0.01)   # ≈ 47 % menos denso que el nivel del mar


# --- S03-02 factores de seguridad ---
def test_safety_factors_within_documented_ranges():
    f = all_factors()
    assert f["thrust_to_weight"] == 2.0 and f["structure"] == 2.5
    assert set(f) >= {"motor_current", "esc_current", "battery_capacity", "flight_time_margin"}


def test_design_cases_have_both_vehicles():
    v = design_cases()["vehicles"]
    assert v["DS-I"]["rotors"] == 4 and v["DS-D"]["rotors"] == 6 and v["DS-D"]["payload_kg"] == 5.0


# --- S03-03 hélice ---
@pytest.fixture(scope="module")
def prop10():
    return PropTable.build(PropGeometry.inches(10, 4.7), atm.isa(0))


def test_prop_coefficients_in_physical_range(prop10):
    c = prop10.coefficients(prop10.max_rpm * 0.6)
    assert 0.08 < c["ct"] < 0.12                     # típico de una 10x4.7
    assert 0.45 < c["figure_of_merit"] < 0.80        # FM < 1 siempre; hélices reales 0.5-0.75


def test_prop_thrust_monotonic_and_density_scaling(prop10):
    assert all(b > a for a, b in zip(prop10.thrust, prop10.thrust[1:]))
    high = PropTable.build(PropGeometry.inches(10, 4.7), atm.air(5000, 15))
    rpm = 6000
    ratio = high.thrust_at(rpm) / prop10.thrust_at(rpm)
    assert ratio == pytest.approx(atm.air(5000, 15).sigma, rel=0.10)   # empuje ∝ ρ a igual rpm


# --- S03-04 motor ---
def test_motor_energy_balance():
    m = Motor.parametric(800, 300, 22.2)
    e = m.electrical(0.15, 6000)
    losses = e["current"] ** 2 * m.rm + e["voltage"] * m.i0
    assert e["p_in"] == pytest.approx(e["p_shaft"] + losses, rel=0.02)
    assert 0.6 < e["efficiency"] < 0.95


def test_max_thrust_respects_current_limit(prop10):
    m = Motor.parametric(2000, 150, 14.8)            # Kv alto: lo limita la corriente, no el voltaje
    mx = max_thrust_point(m, prop10, 14.8)
    assert mx["current"] <= m.i_max * 1.001
    assert mx["limit"] in {"corriente", "voltaje", "punta"}


# --- S03-05 batería ---
def test_pack_energy_and_sag():
    p = Pack(CELLS["P45B"], 6, 2)
    assert p.energy_wh == pytest.approx(6 * 2 * 4.5 * 3.6)
    assert p.voltage_under_load(800) < p.voltage_under_load(100) < p.v_nominal
    assert capacity_factor(20) == 1.0 and capacity_factor(-15) == pytest.approx(0.80, abs=0.01)


# --- S03-06 misión ---
@pytest.fixture(scope="module")
def quad():
    geom = PropGeometry.inches(12, 6)
    pack = Pack(CELLS["P45B"], 6, 2)
    sizing = size_motor(4, geom, pack, atm.air(5000, 15), 2.0, 2.0, 1.3)
    return Propulsion(4, sizing.motor, geom, pack, avionics_w=15)


def test_twr_met_at_design_case(quad):
    mx = quad.max_thrust(atm.air(5000, 15))
    assert mx["total_thrust"] / (2.0 * atm.G0) >= 1.95


def test_hover_less_power_than_max_and_forward_flight(quad):
    a = atm.air(4500, 0)
    h = quad.hover(2.0, a)
    assert 0.3 < h["thrust_fraction"] < 0.6
    assert quad.forward(2.0, a, 8, 0.03)["p_total"] < h["p_total"]   # sustentación por traslación


def test_endurance_and_delivery_mission(quad):
    a = atm.air(4500, 0)
    assert 10 < hover_endurance_min(quad, 2.0, a, 0) < 120
    d = delivery_mission(quad, 1.8, 0.2, a, 1000, 8, 0.03, 0)
    assert d["required_wh"] == pytest.approx(d["energy_wh"] * 1.2)


def test_infeasible_when_prop_too_small():
    with pytest.raises(Infeasible):
        size_motor(4, PropGeometry.inches(5, 3), Pack(CELLS["P45B"], 6, 1), atm.air(5000, 15), 10.0, 2.0, 1.3)


# --- S03-07 validación contra DJI (regresión del estado actual) ---
def test_validation_against_dji():
    from engineering.validation import calibrate
    res = calibrate()
    m4e, m400 = res["cases"]
    assert abs(m4e["error_pct"]) < 1.0                      # calibrado
    assert -15.0 < m400["error_pct"] <= 0.0                 # conservador y acotado (criterio 10 % aún no cumplido)
    assert math.isfinite(res["cd0_scale"])
