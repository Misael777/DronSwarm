"""S07-S08 · Herramientas de CAD y FEA: parámetros desde la spec, materiales, identificadores y análisis modal."""

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "cad"))
sys.path.insert(0, str(ROOT / "tools" / "fea"))
import build_frame  # noqa: E402
import gen_cad_params  # noqa: E402
from ccx_fea import CARBON_TUBE, CCX, beam_modal  # noqa: E402
from run_fea import scad_vars  # noqa: E402


@pytest.mark.parametrize("vehicle", ["DS-I", "DS-D"])
def test_cad_params_follow_sizing(vehicle):
    d = json.loads((ROOT / f"engineering/data/results/{vehicle.lower()}_sizing.json").read_text())
    p = gen_cad_params.build(vehicle)
    assert p["wheelbase"] == pytest.approx(d["wheelbase_m"] * 1000, abs=0.1)
    assert p["plate_d"] == pytest.approx(p["wheelbase"] / 4, abs=0.1)
    assert (p["tube_od"], p["tube_wall"]) == gen_cad_params.tube(d["arm"]["tube"])
    assert p["prop_d"] == pytest.approx(d["prop_diameter_in"] * 25.4, abs=0.1)
    assert p["motor_iface"] == ("L" if d["motor_p_max_w"] >= 600 else "S")


def test_pack_dims_fit_cells():
    lying = gen_cad_params.pack_dims("6S2P 50S")
    standing = gen_cad_params.pack_dims("12S5P P42A")
    assert lying[0] > 6 * 21.4 and lying[2] > 2 * 21.4         # 6 celdas a lo largo, 2 capas
    assert standing[2] > 70.2                                   # celdas de pie


def test_part_ids_and_materials():
    assert build_frame.part_id("center_plate.scad", 'which="top"') == "center_plate_top"
    assert build_frame.part_id("arm_block.scad", "") == "arm_block"
    g = build_frame.GROUPS["delivery"]
    assert build_frame.material_of(g, "payload_release_hook") == "aluminio"
    assert build_frame.material_of(g, "payload_release_body") == "PA12-CF"
    assert build_frame.material_of(g, "center_plate_bottom") == "carbono"


def test_scad_vars_reads_numbers(tmp_path):
    f = tmp_path / "p.scad"
    f.write_text('a = 3;\nb = -1.5;\nname = "x";\nc = a + 1;\n')
    assert scad_vars(f) == {"a": 3.0, "b": -1.5}


@pytest.mark.skipif(not CCX.exists(), reason="requiere CalculiX (FreeCAD en ~/.local/opt)")
def test_beam_modal_matches_analytic():
    f = beam_modal(280, 20, 1.0, CARBON_TUBE, 0.091)[0]
    inertia = math.pi / 64 * (0.02 ** 4 - 0.018 ** 4)
    m = 0.091 + 0.24 * 1550 * math.pi / 4 * (0.02 ** 2 - 0.018 ** 2) * 0.28
    analytic = math.sqrt(3 * 70e9 * inertia / (0.28 ** 3 * m)) / (2 * math.pi)
    assert f == pytest.approx(analytic, rel=0.02)


@pytest.mark.parametrize("group", ["inspection", "delivery"])
def test_frame_exports_are_consistent(group):
    rep = ROOT / f"cad/exports/{group}/masas.json"
    if not rep.exists():
        pytest.skip("falta construir el frame (tools/cad/build_frame.py)")
    r = json.loads(rep.read_text())
    assert r["assembly"]["interferences"] == []
    assert min(p["min_clearance_mm"] for p in r["assembly"]["prop_clearance"]) > 20
    assert r["frame_cad_kg"] * 1.06 <= r["frame_budget_kg"] * 1.10     # ≤ 10 % sobre el presupuesto del S04
