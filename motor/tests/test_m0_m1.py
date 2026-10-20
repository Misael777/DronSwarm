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


def test_winding_factors_match_literature():
    from motor.calculo.winding import layout
    for ns, p, kw in ((12, 7, 0.933), (18, 8, 0.945), (18, 12, 0.866), (24, 11, 0.949), (24, 14, 0.933)):
        assert abs(layout(ns, p)["kw"] - kw) < 0.001
    assert layout(12, 6) is None


def test_design_model_reconstructs_cots():
    from motor.calculo.design import RECON, geometry, masses, resistance_line
    for d, kv, r, m in ((RECON["DS-I"], 380, 0.194, 0.068), (RECON["DS-D"], 150, 0.090, 0.257)):
        g = geometry(d)
        assert abs(g["kv"] - kv) / kv < 0.05
        assert abs(resistance_line(d, g) - r) / r < 0.10
        assert 0.95 < masses(d, g)["total"] / m < 1.20       # el modelo es algo pesado (campanas de aluminio fino)


def test_design_model_matches_mn4006_bench():
    from pathlib import Path

    from motor.calculo.design import calibrate_with_mn4006, thermal_calibration
    from motor.calculo.loss_model import read_bench
    bench = read_bench(Path(__file__).resolve().parents[1] / "requisitos" / "datos_cots" / "mn4006_kv380_15x5.csv")
    assert calibrate_with_mn4006(bench)["current_error_rms_pct"] < 3.0
    assert abs(thermal_calibration()["t_case_model_c"] - 46.0) < 2.0


def test_chosen_designs_beat_cots():
    import json
    from pathlib import Path
    chosen = json.loads((Path(__file__).resolve().parents[1] / "informes" / "M2_elegidos.json").read_text())
    for c in chosen.values():
        assert c["eta_weighted"] - c["reference"]["weighted_efficiency"] >= 0.02
        assert c["endurance_rel"] > 1.0
        assert c["ops"]["maniobra_twr15"]["t_winding"] < 120


def test_direct_drive_beats_home_built_gearboxes():
    import json
    from pathlib import Path
    res = json.loads((Path(__file__).resolve().parents[1] / "informes" / "M3_reductores.json").read_text())
    for v in res.values():
        direct = next(x for x in v["rows"] if x["type"] == "directo")
        home = [x for x in v["rows"] if x["feasible"] and x["type"] not in ("directo", "planetario_aero")]
        assert all(x["endurance_rel"] < direct["endurance_rel"] for x in home)
        assert not any(x["feasible"] for x in v["rows"] if x["type"] == "armonico")
