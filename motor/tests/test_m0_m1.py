import json
import math

from motor.calculo.loss_model import MotorModel
from motor.calculo.materials import STEELS, laser_cut_factor
from motor.calculo.reference import REQ, build


def test_steel_loss_fit_matches_catalog():
    for s in STEELS.values():
        assert math.isclose(s.loss_w_per_kg(1.0, 50), s.p10_50, rel_tol=1e-6)
        assert math.isclose(s.loss_w_per_kg(1.0, 400), s.p10_400, rel_tol=1e-6)


def test_laser_factor_grows_for_narrow_teeth():
    assert laser_cut_factor(10) < laser_cut_factor(2) < 1.6 + 1e-9


def test_noload_calibration_reproduces_i0():
    m = MotorModel.from_noload("x", 380, 0.194, 0.3, 22)
    rpm = 380 * (22 - 0.3 * 0.194)
    op = m.operate(0.0, rpm, t_wind=20, t_mag=20)
    assert math.isclose(op["current"], 0.3, rel_tol=0.01)


def test_requirements_match_s09():
    req = json.loads(REQ.read_text())
    for v in ("DS-I", "DS-D"):
        ours, s09 = req[v]["check_vs_s09"]["hover_current_a"]
        assert abs(ours - s09) / s09 < 0.02


def test_mn4006_reference_within_two_points():
    _, info = build("DS-I")
    assert info["eff_error_rms_points"] <= 2.0
