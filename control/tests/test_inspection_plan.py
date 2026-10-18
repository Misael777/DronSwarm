"""S05-04 · Planificador fotogramétrico de la misión de inspección."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "missions"))
from inspection import Camera, plan_grid  # noqa: E402


def test_gsd_and_height_are_inverse():
    cam = Camera()
    h = cam.height_for_gsd(0.03)
    assert cam.gsd_m(h) == pytest.approx(0.03)
    assert h == pytest.approx(109.4, abs=0.5)          # 1" 20 MP, f 8.8 mm → 3 cm/px a ≈ 109 m


def test_grid_overlaps_and_coverage():
    cam = Camera()
    area = (72, 268, -76, 76)
    plan = plan_grid(area, cam, 0.03, front=0.75, side=0.65)
    across, along = cam.footprint(plan.height_m)
    assert plan.line_spacing_m == pytest.approx(across * 0.35)
    assert plan.photo_spacing_m == pytest.approx(along * 0.25)
    xs = [line[0][0] for line in plan.lines]
    assert min(xs) <= area[0] and max(xs) >= area[1]                 # las líneas cubren el ancho
    assert all(b - a <= plan.line_spacing_m + 1e-6 for a, b in zip(xs, xs[1:]))
    ys = [y for line in plan.lines for _, y in line]
    assert min(ys) < area[2] and max(ys) > area[3]                   # y se extienden más allá del borde


def test_lawnmower_alternates_direction():
    plan = plan_grid((0, 300, 0, 200), Camera(), 0.03)
    directions = [line[1][1] - line[0][1] for line in plan.lines]
    assert all(a * b < 0 for a, b in zip(directions, directions[1:]))
