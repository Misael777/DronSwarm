#!/usr/bin/env python3
"""Genera la escena de carga cooperativa: N drones DS-D levantan juntos una caja colgada de cuerdas.

Las cuerdas las simula el plugin propio `simulation/plugins/tether` (resorte-amortiguador que solo tira, aplicado
como fuerzas en cada paso de física). No se usan uniones entre modelos: con ellas el solver DART se vuelve
inestable (cadena dron 10 kg ↔ gancho liviano ↔ caja 10 kg).

Salidas:
    simulation/xtdrone/models/coop_payload/      la caja (cuerpo libre)
    simulation/xtdrone/models/ds_d_coop/         DS-D sin caja propia
    simulation/px4/airframes/22029_gz_ds_d_coop  mismo airframe que el DS-D
    simulation/xtdrone/worlds/coop.sdf           mundo default de PX4 + plugin de cuerdas
    simulation/xtdrone/models/coop_layout.json   posiciones de los drones (las usa el lanzador)

    .venv/bin/python tools/gen_coop.py --drones 3 --payload 10
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gen_sdf  # noqa: E402

MODELS = gen_sdf.MODELS
WORLDS = ROOT / "simulation" / "xtdrone" / "worlds"
BOX = (0.50, 0.40, 0.30)                 # caja de carga [m]
HOOK_OFFSET = (0.0, 0.0, -0.08)          # gancho bajo el cuerpo del dron (en su base_link)


def payload_model(payload_kg: float) -> str:
    a, b, c = BOX
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- Generado por tools/gen_coop.py: caja de {payload_kg} kg para carga cooperativa. -->
<sdf version="1.9">
  <model name="coop_payload">
    <link name="box">
      <pose>0 0 {c / 2:.3f} 0 0 0</pose>
      <inertial><mass>{payload_kg}</mass>{gen_sdf.box_inertia(payload_kg, a, b, c)}</inertial>
      <collision name="box_collision"><geometry><box><size>{a} {b} {c}</size></box></geometry>{gen_sdf.DRONE_MASK}</collision>
      <visual name="box_visual"><geometry><box><size>{a} {b} {c}</size></box></geometry>{gen_sdf.material((0.9, 0.45, 0.1))}</visual>
      <visual name="box_band"><pose>0 0 {c / 2 + 0.001:.3f} 0 0 0</pose><geometry><box><size>{a * 0.7:.2f} {b * 0.25:.2f} 0.002</size></box></geometry>
        {gen_sdf.material((0.95, 0.95, 0.95))}</visual>
    </link>
  </model>
</sdf>
"""


def world_with_tethers(n: int, radius: float, rope: float, stiffness: float, damping: float) -> tuple[str, list]:
    src = (gen_sdf.PX4_DIR / "Tools/simulation/gz/worlds/default.sdf").read_text()
    a, b, c = BOX
    tethers, positions = [], []
    for k in range(n):
        ang = math.pi / 2 + 2 * math.pi * k / n
        anchor = (0.4 * a * math.cos(ang), 0.4 * b * math.sin(ang), c / 2)     # en la cara superior de la caja
        positions.append((radius * math.cos(ang), radius * math.sin(ang)))
        tethers.append(f"""
      <tether>
        <a model="ds_d_coop_{k}" link="base_link" offset="{HOOK_OFFSET[0]} {HOOK_OFFSET[1]} {HOOK_OFFSET[2]}"/>
        <b model="coop_payload" link="box" offset="{anchor[0]:.3f} {anchor[1]:.3f} {anchor[2]:.3f}"/>
        <length>{rope}</length>
      </tether>""")
    plugin = f"""
    <plugin filename="dronswarm-tether-system" name="dronswarm::TetherSystem">
      <stiffness>{stiffness}</stiffness>
      <damping>{damping}</damping>{''.join(tethers)}
    </plugin>
"""
    out = re.sub(r'(<world name="default">)', lambda m: m.group(1) + plugin, src, count=1)
    return out, positions


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drones", type=int, default=3)
    ap.add_argument("--payload", type=float, default=10.0, help="masa de la caja [kg]")
    ap.add_argument("--radius", type=float, default=2.0, help="radio del círculo de drones [m]")
    ap.add_argument("--rope", type=float, default=3.2, help="largo de cada cuerda [m]")
    ap.add_argument("--stiffness", type=float, default=4000.0, help="rigidez de la cuerda [N/m]")
    ap.add_argument("--damping", type=float, default=80.0, help="amortiguamiento de la cuerda [N·s/m]")
    a = ap.parse_args()

    design = json.loads((gen_sdf.RESULTS / "ds-d_sizing.json").read_text())
    spawn_z = gen_sdf.VEHICLES["DS-D"][3] + 0.05

    d = MODELS / "coop_payload"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.sdf").write_text(payload_model(a.payload))
    (d / "model.config").write_text("<?xml version='1.0'?>\n<model><name>coop_payload</name><sdf version='1.9'>model.sdf</sdf></model>\n")

    text, _ = gen_sdf.build("DS-D", design, with_payload=False, name_suffix="_coop")
    md = MODELS / "ds_d_coop"
    md.mkdir(exist_ok=True)
    (md / "model.sdf").write_text(text)
    (md / "model.config").write_text("<?xml version='1.0'?>\n<model><name>ds_d_coop</name><sdf version='1.9'>model.sdf</sdf></model>\n")
    base_af = (gen_sdf.AIRFRAMES / "22002_gz_ds_d").read_text()
    af = gen_sdf.AIRFRAMES / "22029_gz_ds_d_coop"
    af.write_text(base_af.replace("PX4_SIM_MODEL:=ds_d}", "PX4_SIM_MODEL:=ds_d_coop}"))
    af.chmod(0o755)

    world, positions = world_with_tethers(a.drones, a.radius, a.rope, a.stiffness, a.damping)
    WORLDS.mkdir(parents=True, exist_ok=True)
    (WORLDS / "coop.sdf").write_text(world)

    layout = {"models": ["ds_d_coop"] * a.drones,
              "poses": [[round(x, 3), round(y, 3), round(spawn_z, 3)] for x, y in positions],
              "payload_kg": a.payload, "rope_m": a.rope, "radius_m": a.radius,
              "load_per_drone_kg": round(a.payload / a.drones, 2)}
    (MODELS / "coop_layout.json").write_text(json.dumps(layout, indent=2) + "\n")
    # Limpiar la versión anterior (cadena de eslabones + ganchos soldados)
    for old in MODELS.glob("ds_d_lift_*"):
        for f in old.iterdir():
            f.unlink()
        old.rmdir()
    for old in gen_sdf.AIRFRAMES.glob("2202[0-8]_gz_ds_d_lift_*"):
        old.unlink()
    print(json.dumps(layout, indent=2))


if __name__ == "__main__":
    main()
