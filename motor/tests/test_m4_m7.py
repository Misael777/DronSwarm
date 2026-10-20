import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INF = ROOT / "motor" / "informes"


def test_wire_choice_never_overfills():
    from motor.calculo.design import wire_choice
    for a in (0.06e-6, 0.17e-6, 0.32e-6, 0.9e-6):
        w = wire_choice(a)
        assert w["area_m2"] <= a * 1.02 + 1e-15
        assert w["d_mm"] <= 0.6
    assert wire_choice(0.01e-6)["strands"] == 0          # ni el hilo más fino cabe


def test_fem_reproduces_flux_linkage():
    pytest.importorskip("gmsh")
    from motor.fem.fem2d import build_mesh, flux_linkage, params_from, solve
    chosen = json.loads((INF / "M2_elegidos.json").read_text())["DS-I"]
    p = params_from(chosen)
    m = build_mesh(p, 0.0, fine=0.6)
    s = solve(m, None)
    lam = flux_linkage(m, s)
    assert s["iterations"] < 20                              # Newton converge
    assert abs(sum(lam)) < 0.12 * max(abs(lam))             # balanceadas salvo los armónicos triples (iguales en las 3 fases)
    ke = p["pole_pairs"] * max(abs(lam)) * (1 if p["delta"] else math.sqrt(3))
    kv = 60 / (2 * math.pi * ke)
    assert abs(kv / chosen["kv"] - 1) < 0.12                 # malla gruesa: ±12 % (la fina da < 5 %, M4)


def test_fem_results_pass():
    res = json.loads((INF / "M4_fem.json").read_text())
    for r in res.values():
        assert abs(r["bemf"]["kv_fem"] / r["analytic"]["kv"] - 1) <= 0.05
        assert r["cogging"]["pct_of_hover"] < 5
        assert r["demag_ratio"] < 0.7


def test_thermal_and_mechanics_ok():
    r = json.loads((INF / "M5_termico_mecanico.json").read_text())
    for veh in ("DS-I", "DS-D"):
        assert r[veh]["steady"]["maniobra_twr15"][0] < 120
        assert r[veh]["mech"]["shaft_fs"] >= 2 and r[veh]["mech"]["cap_fs"] >= 2
        assert r[veh]["plastic_ok"]["PETG"]


def test_motor_bom_is_cheaper_than_cots():
    import csv
    rows = list(csv.DictReader(open(ROOT / "motor" / "bom" / "lista_materiales_motor.csv", encoding="utf-8")))
    cost = {v: sum(float(r["uso"]) / float(r["por_presentacion"]) * float(r["precio"]) for r in rows if r["motor"] in (v, "común"))
            for v in ("DS-I", "DS-D")}
    assert cost["DS-I"] < 75 * 0.5 and cost["DS-D"] < 170 * 0.5


def test_cad_exports_exist():
    s = json.loads((ROOT / "cad" / "exports" / "motor" / "resumen.json").read_text())
    for v in s.values():
        for f in v["files"].values():
            assert (ROOT / f).stat().st_size > 1000
