"""S05-01 · Modelos de Gazebo y airframes de PX4 generados desde el dimensionamiento del S04."""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import gen_sdf  # noqa: E402

PX4_OK = (gen_sdf.PX4_DIR / "Tools/simulation/gz/models/x500_base/model.sdf").exists()
pytestmark = pytest.mark.skipif(not PX4_OK, reason="requiere PX4 en ~/src/PX4-Autopilot (sensores del x500)")


@pytest.mark.parametrize("vehicle", ["DS-I", "DS-D", "DS-H"])
def test_model_matches_sizing(vehicle, tmp_path):
    path = gen_sdf.RESULTS / f"{vehicle.lower()}_sizing.json"
    if not path.exists():
        pytest.skip("falta el dimensionamiento (python -m engineering.sizing)")
    design = json.loads(path.read_text())
    sdf, info = gen_sdf.build(vehicle, design)
    n = design["rotors"]
    assert sdf.count("MulticopterMotorModel") == n
    assert info["mass_kg"] == pytest.approx(design["mtow_kg"], rel=0.01)       # la masa del modelo es la del S04
    assert sdf.count("<turningDirection>ccw") == sdf.count("<turningDirection>cw") == n // 2
    af = gen_sdf.airframe(vehicle, design, info["model"], 22000)
    assert f"CA_ROTOR_COUNT {n}" in af
    assert len(re.findall(r"CA_ROTOR\d+_KM -", af)) == n // 2                   # mitad de los rotores gira al revés
    if shutil.which("gz"):
        f = tmp_path / "model.sdf"
        f.write_text(sdf)
        out = subprocess.run(["gz", "sdf", "-k", str(f)], capture_output=True, text=True)
        assert "Valid" in out.stdout + out.stderr
