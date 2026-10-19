"""S10 · Banco de empuje: la cadena adquisición → análisis recupera los parámetros del banco simulado."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bench"))
import analyze  # noqa: E402
from benchlib import Calibration, physical, read_raw  # noqa: E402

MOTOR = "T-Motor MN4006 KV380 (AntiGravity)"


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    d = tmp_path_factory.mktemp("bench")
    out = {}
    for test in ("noload", "sweep"):
        p = d / f"{test}.csv"
        subprocess.run([sys.executable, str(ROOT / "tools/bench/acquire.py"), test, "--simulate", "--motor", MOTOR,
                        "--prop", "15", "--battery", "6S2P", "--out", str(p)], check=True, capture_output=True)
        out[test] = p
    return out


def test_noload_recovers_kv_and_i0(runs):
    rows, _ = read_raw(runs["noload"])
    fit = analyze.noload_fit(analyze.steps(physical(rows, Calibration())))
    assert fit["kv"] == pytest.approx(380, rel=0.02)
    assert fit["i0"] == pytest.approx(0.3, abs=0.1)


def test_sweep_coefficients_are_physical(runs):
    rows, meta = read_raw(runs["sweep"])
    fit = analyze.sweep_fit(analyze.steps(physical(rows, Calibration())), meta.prop_diameter_in * 0.0254, meta.density())
    assert 0.05 < fit["ct"].mean() < 0.2 and 0.02 < fit["cp"].mean() < 0.1
    assert fit["r_eff_ohm"] > 0
    thrusts = [r["thrust_n"] for r in fit["table"]]
    assert thrusts == sorted(thrusts)                        # más throttle, más empuje


def test_altitude_needs_more_rpm(runs):
    rows, meta = read_raw(runs["sweep"])
    d = meta.prop_diameter_in * 0.0254
    fit = analyze.sweep_fit(analyze.steps(physical(rows, Calibration())), d, meta.density())
    low = analyze.at_altitude(fit, 380, d, 1.2, 6.0, 22.0)
    high = analyze.at_altitude(fit, 380, d, 0.74, 6.0, 22.0)
    assert high["rpm"] > low["rpm"] and high["p_bat_w"] > low["p_bat_w"]
