"""S11 · Herramientas de análisis de vuelo real (vibración, autonomía) y parámetros de PX4."""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "flight"))
sys.path.insert(0, str(ROOT / "tools" / "px4"))
sys.path.insert(0, str(ROOT / "tools"))
import endurance  # noqa: E402
import gen_params  # noqa: E402
import gen_sdf  # noqa: E402


def test_measured_hover_uses_only_hover_with_current():
    t = np.arange(0, 100, 0.1)
    v = np.full_like(t, 22.0)
    i = np.where(t > 10, 15.0, 0.0)
    hov = (t > 20) & (t < 80)
    m = endurance.measured_hover(t, v, i, hov)
    assert m["p_hover_w"] == pytest.approx(330.0) and m["hover_s"] == pytest.approx(60, abs=0.5)


def test_model_power_grows_with_altitude_and_mass():
    p_sea = endurance.model_hover_power("DS-I", 2.4, 0, 15)
    p_alt = endurance.model_hover_power("DS-I", 2.4, 4500, 0)
    p_heavy = endurance.model_hover_power("DS-I", 2.7, 4500, 0)
    assert p_alt > p_sea and p_heavy > p_alt


def test_compare_flags_deviation():
    p = endurance.model_hover_power("DS-I", 2.4, 150, 20)
    ok = endurance.compare({"p_hover_w": p * 1.05}, "DS-I", 2.4, 150, 20)
    bad = endurance.compare({"p_hover_w": p * 1.20}, "DS-I", 2.4, 150, 20)
    assert ok["ok"] and not bad["ok"] and ok["endurance_4500m_min"] < ok["endurance_site_min"]


@pytest.mark.parametrize("vehicle", ["DS-I", "DS-D"])
def test_px4_params_match_sitl_geometry(vehicle):
    import json
    p = {name: v for name, v, _ in gen_params.params(vehicle)}
    d = json.loads((ROOT / f"engineering/data/results/{vehicle.lower()}_sizing.json").read_text())
    sitl = {ln.split()[2]: float(ln.split()[3]) for ln in gen_sdf.airframe(vehicle, d, "x", 0).splitlines()
            if ln.startswith("param set-default CA_ROTOR") and "COUNT" not in ln}
    assert all(p[k] == pytest.approx(v) for k, v in sitl.items())
    assert p["CA_ROTOR_COUNT"] == d["rotors"] and 0.5 <= p["MPC_THR_MAX"] <= 1.0
    if vehicle == "DS-D":
        assert p["CA_FAILURE_MODE"] == 1 and p["MC_AIRMODE"] == 1
