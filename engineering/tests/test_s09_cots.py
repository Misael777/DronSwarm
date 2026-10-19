"""S09 · Selección COTS: la elección cumple los requisitos y el BOM es coherente con ella."""

import csv
from pathlib import Path

import pytest

from engineering import cots

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def res():
    return cots.run()


def test_selection_meets_hard_requirements(res):
    for veh in ("DS-I", "DS-D"):
        s = res["selected"][veh]
        assert s["ok"] and all(s["checks"].values())
        assert s["twr_5000m"] >= 1.98
        assert s["endurance_new_min"] >= cots.REQUIREMENTS[veh]["endurance_min"]
        assert s["pack_current_twr2_a"] <= s["pack_limit_a"]


def test_throttle_cap_only_when_needed(res):
    for s in res["selected"].values():
        if s["pack_current_full_a"] <= s["pack_limit_a"]:
            assert s["thr_max_recommended"] == 1.0
        else:
            assert 0.5 <= s["thr_max_recommended"] < 1.0


def test_dsd_esc_has_telemetry():
    esc = next(e for e in cots.ESCS if e.vehicle == "DS-D")
    assert esc.telemetry                                  # requisito del S06 (motor caído)


def test_camera_gsd():
    assert cots.camera_gsd(109) == pytest.approx(4.85, abs=0.1)


def test_bom_uses_selected_motors(res):
    p = ROOT / "manufacturing/bom/bom_prototipo_v1.csv"
    if not p.exists():
        pytest.skip("falta generar el BOM (tools/bom/gen_bom.py)")
    rows = list(csv.DictReader(open(p)))
    for veh in ("DS-I", "DS-D"):
        name = res["selected"][veh]["motor"]
        assert any(name in r["descripcion"] and r["dron"] == veh for r in rows)
    assert all(float(r["total_usd"]) == pytest.approx(float(r["precio_unit_usd"]) * int(r["cant_total"]), abs=0.05) for r in rows)

