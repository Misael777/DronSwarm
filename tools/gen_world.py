#!/usr/bin/env python3
"""S05-02/03 · Mundo de mina para Gazebo: tajo abierto con bancos, faja transportadora, relavera, túnel y viento.

El tajo se genera como malla (OBJ) desde un perfil paramétrico de bancos: no depende de un DEM externo. Cuando
haya mina piloto, el mismo generador puede leer su DEM real (pendiente: --dem).

    .venv/bin/python tools/gen_world.py --wind 8 --wind-dir 270

Salidas:
    simulation/xtdrone/models/mine_terrain/   terreno con el tajo (malla visual + colisión)
    simulation/xtdrone/models/mine_conveyor/  faja transportadora elevada con polines
    simulation/xtdrone/models/mine_tailings/  relavera con dique
    simulation/xtdrone/models/mine_tunnel/    túnel de concreto
    simulation/xtdrone/worlds/mine.sdf        mundo "default" de PX4 con todo lo anterior, viento y coordenadas andinas
    simulation/xtdrone/worlds/mine_layout.json  puntos de interés para las misiones
    simulation/xtdrone/worlds/swarm.sdf       S06: campo plano con torre de iluminación y monitor de separación
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gen_sdf  # noqa: E402

MODELS = gen_sdf.MODELS
WORLDS = ROOT / "simulation" / "xtdrone" / "worlds"

# Geometría del tajo (m)
PIT_CENTER = (170.0, 0.0)
PIT_BOTTOM_R = 30.0          # radio del fondo (eje x)
PIT_ASPECT = 0.78            # semieje y / semieje x
BENCH_H = 10.0
BENCHES = 6
FACE_ANGLE = 65.0            # ángulo del talud de banco [°]
BERM_W = 8.0
EXTENT = 480.0               # lado del terreno modelado
GRID = 3.0                   # resolución de la malla


def pit_profile(r: np.ndarray) -> np.ndarray:
    """Cota z(r) del tajo: fondo plano, bancos (talud + berma) hasta la superficie z = 0."""
    face = BENCH_H / math.tan(math.radians(FACE_ANGLE))
    z = np.full_like(r, -BENCH_H * BENCHES)
    r0 = PIT_BOTTOM_R
    for k in range(BENCHES):
        z_base = -BENCH_H * (BENCHES - k)
        rising = (r > r0) & (r <= r0 + face)
        z = np.where(rising, z_base + BENCH_H * (r - r0) / face, z)
        z = np.where(r > r0 + face, z_base + BENCH_H, z)
        r0 += face + BERM_W
    return z


def terrain_mesh(path: Path) -> dict:
    n = int(EXTENT / GRID) + 1
    xs = np.linspace(-EXTENT / 2 + PIT_CENTER[0] - 60, EXTENT / 2 + PIT_CENTER[0] - 60, n)
    ys = np.linspace(-EXTENT / 2, EXTENT / 2, n)
    gx, gy = np.meshgrid(xs, ys, indexing="ij")
    r = np.hypot(gx - PIT_CENTER[0], (gy - PIT_CENTER[1]) / PIT_ASPECT)
    gz = pit_profile(r)
    # normales por gradiente (sombreado correcto en Gazebo)
    dzdx, dzdy = np.gradient(gz, GRID, GRID)
    normals = np.dstack([-dzdx, -dzdy, np.ones_like(gz)])
    normals /= np.linalg.norm(normals, axis=2, keepdims=True)
    lines = ["# Terreno de mina generado por tools/gen_world.py", "o mine_terrain"]
    for i in range(n):
        for j in range(n):
            lines.append(f"v {gx[i, j]:.2f} {gy[i, j]:.2f} {gz[i, j]:.2f}")
    for i in range(n):
        for j in range(n):
            nx, ny, nz = normals[i, j]
            lines.append(f"vn {nx:.4f} {ny:.4f} {nz:.4f}")
    for i in range(n - 1):
        for j in range(n - 1):
            a = i * n + j + 1
            b, c, d = a + n, a + n + 1, a + 1
            lines.append(f"f {a}//{a} {b}//{b} {c}//{c}")
            lines.append(f"f {a}//{a} {c}//{c} {d}//{d}")
    path.write_text("\n".join(lines) + "\n")
    return {"vertices": n * n, "triangles": 2 * (n - 1) ** 2, "x_range": [float(xs[0]), float(xs[-1])],
            "pit_depth_m": BENCH_H * BENCHES, "pit_top_radius_m": float(r[gz > -0.01].min()) if (gz > -0.01).any() else None}


def static_model(name: str, body: str) -> None:
    d = MODELS / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.sdf").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- Generado por tools/gen_world.py -->
<sdf version="1.9">
  <model name="{name}">
    <static>true</static>{body}
  </model>
</sdf>
""")
    (d / "model.config").write_text(f"<?xml version='1.0'?>\n<model><name>{name}</name><sdf version='1.9'>model.sdf</sdf></model>\n")


def box(name, pose, size, rgb, collide=True):
    mat = gen_sdf.material(rgb)
    geo = f"<geometry><box><size>{size[0]} {size[1]} {size[2]}</size></box></geometry>"
    col = f'<collision name="{name}_c">{geo}</collision>' if collide else ""
    return f'\n    <link name="{name}"><pose>{pose}</pose>{col}<visual name="{name}_v">{geo}{mat}</visual></link>'


def conveyor(start=(120.0, 90.0), end=(-60.0, 90.0), height=3.0) -> dict:
    (x0, y0), (x1, y1) = start, end
    length = math.hypot(x1 - x0, y1 - y0)
    yaw = math.atan2(y1 - y0, x1 - x0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = [box("belt", f"{cx} {cy} {height} 0 0 {yaw:.4f}", (length, 1.2, 0.08), (0.08, 0.08, 0.08)),
             box("frame", f"{cx} {cy} {height - 0.35} 0 0 {yaw:.4f}", (length, 1.6, 0.5), (0.85, 0.65, 0.1))]
    n_supports = int(length // 12)
    for k in range(n_supports + 1):
        t = k / n_supports
        sx, sy = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
        parts.append(box(f"support_{k}", f"{sx:.2f} {sy:.2f} {(height - 0.6) / 2:.2f} 0 0 {yaw:.4f}", (0.3, 1.4, height - 0.6), (0.5, 0.5, 0.5)))
    # polines (idlers): cilindros visuales cada 3 m, lo que se inspecciona en HU-03
    n_idlers = int(length // 3)
    for k in range(n_idlers):
        t = (k + 0.5) / n_idlers
        sx, sy = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
        parts.append(f'\n    <link name="idler_{k}"><pose>{sx:.2f} {sy:.2f} {height - 0.12:.2f} 1.5708 0 {yaw + 1.5708:.4f}</pose>'
                     f'<visual name="idler_{k}_v"><geometry><cylinder><radius>0.08</radius><length>1.3</length></cylinder></geometry>'
                     f'{gen_sdf.material((0.6, 0.6, 0.62))}</visual></link>')
    static_model("mine_conveyor", "".join(parts))
    return {"start": list(start), "end": list(end), "height_m": height, "length_m": round(length, 1), "idlers": n_idlers}


def tailings(center=(-150.0, -130.0), radius=50.0) -> dict:
    cx, cy = center
    parts = [f'\n    <link name="pond"><pose>{cx} {cy} 0.6 0 0 0</pose><visual name="pond_v"><geometry><cylinder>'
             f'<radius>{radius}</radius><length>0.1</length></cylinder></geometry>{gen_sdf.material((0.35, 0.55, 0.6))}</visual></link>']
    n = 32
    seg = 2 * math.pi * (radius + 4) / n * 1.05
    for k in range(n):
        a = 2 * math.pi * k / n
        parts.append(box(f"dam_{k}", f"{cx + (radius + 4) * math.cos(a):.2f} {cy + (radius + 4) * math.sin(a):.2f} 2 0 0 {a + math.pi / 2:.4f}",
                         (seg, 8, 4), (0.55, 0.45, 0.35)))
    static_model("mine_tailings", "".join(parts))
    return {"center": list(center), "radius_m": radius}


def tunnel(center=(-80.0, -40.0), length=40.0, inner=6.0, wall=0.6) -> dict:
    cx, cy = center
    o = inner + 2 * wall
    c = (0.65, 0.65, 0.65)
    parts = [box("roof", f"{cx} {cy} {inner + wall / 2} 0 0 0", (length, o, wall), c),
             box("wall_l", f"{cx} {cy + (inner + wall) / 2} {inner / 2} 0 0 0", (length, wall, inner), c),
             box("wall_r", f"{cx} {cy - (inner + wall) / 2} {inner / 2} 0 0 0", (length, wall, inner), c)]
    static_model("mine_tunnel", "".join(parts))
    return {"center": list(center), "length_m": length, "inner_m": inner}


def world(wind: float, wind_dir_deg: float, scale: float, extra_plugins: str = "") -> str:
    src = (gen_sdf.PX4_DIR / "Tools/simulation/gz/worlds/default.sdf").read_text()
    src = re.sub(r'<model name="ground_plane">.*?</model>', "", src, flags=re.S)        # el terreno reemplaza al plano
    # de dónde sopla → hacia dónde va (convención meteorológica)
    to = math.radians((wind_dir_deg + 180) % 360)
    wx, wy = wind * math.sin(to), wind * math.cos(to)                                  # x = este, y = norte (ENU)
    includes = "".join(f"\n    <include><uri>model://{m}</uri></include>"
                       for m in ("mine_terrain", "mine_conveyor", "mine_tailings", "mine_tunnel"))
    wind_block = f"""
    <wind><linear_velocity>{wx:.2f} {wy:.2f} 0</linear_velocity></wind>
    <plugin filename="gz-sim-wind-effects-system" name="gz::sim::systems::WindEffects">
      <force_approximation_scaling_factor>{scale}</force_approximation_scaling_factor>
      <horizontal>
        <magnitude><time_for_rise>10</time_for_rise>
          <sin><amplitude_percent>0.25</amplitude_percent><period>12</period></sin>
          <noise type="gaussian"><mean>0</mean><stddev>0.08</stddev></noise></magnitude>
        <direction><time_for_rise>30</time_for_rise>
          <sin><amplitude>10</amplitude><period>40</period></sin>
          <noise type="gaussian"><mean>0</mean><stddev>0.03</stddev></noise></direction>
      </horizontal>
      <vertical><noise type="gaussian"><mean>0</mean><stddev>0.05</stddev></noise></vertical>
    </plugin>""" if wind > 0 else ""
    src = src.replace("</world>", f"{includes}{wind_block}{extra_plugins}\n  </world>")
    # Ubicación referencial: Andes peruanos a 4,300 msnm (GPS y altitud de PX4)
    src = re.sub(r"<latitude_deg>.*?</latitude_deg>", "<latitude_deg>-9.5300</latitude_deg>", src)
    src = re.sub(r"<longitude_deg>.*?</longitude_deg>", "<longitude_deg>-77.0500</longitude_deg>", src)
    src = re.sub(r"<elevation>.*?</elevation>", "<elevation>4300</elevation>", src)
    return src


def delivery_scene(wind: float, wind_dir: float, scale: float, payload_kg: float = 5.0, rope: float = 0.5) -> dict:
    """S05-05 · DS-D con gancho y caja colgada de una cuerda corta que se suelta en destino (/tether/0/release)."""
    design = json.loads((gen_sdf.RESULTS / "ds-d_sizing.json").read_text())
    text, _ = gen_sdf.build("DS-D", design, with_payload=False, name_suffix="_hook")
    md = MODELS / "ds_d_hook"
    md.mkdir(exist_ok=True)
    (md / "model.sdf").write_text(text)
    (md / "model.config").write_text("<?xml version='1.0'?>\n<model><name>ds_d_hook</name><sdf version='1.9'>model.sdf</sdf></model>\n")
    af = gen_sdf.AIRFRAMES / "22030_gz_ds_d_hook"
    af.write_text((gen_sdf.AIRFRAMES / "22002_gz_ds_d").read_text().replace("PX4_SIM_MODEL:=ds_d}", "PX4_SIM_MODEL:=ds_d_hook}"))
    af.chmod(0o755)
    a, b, c = 0.30, 0.24, 0.22                    # cabe entre las patas del DS-D
    bd = MODELS / "delivery_box"
    bd.mkdir(exist_ok=True)
    (bd / "model.sdf").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<sdf version="1.9">
  <model name="delivery_box">
    <link name="box">
      <pose>0 0 {c / 2} 0 0 0</pose>
      <inertial><mass>{payload_kg}</mass>{gen_sdf.box_inertia(payload_kg, a, b, c)}</inertial>
      <collision name="c"><geometry><box><size>{a} {b} {c}</size></box></geometry>{gen_sdf.DRONE_MASK}</collision>
      <visual name="v"><geometry><box><size>{a} {b} {c}</size></box></geometry>{gen_sdf.material((0.9, 0.45, 0.1))}</visual>
    </link>
  </model>
</sdf>
""")
    (bd / "model.config").write_text("<?xml version='1.0'?>\n<model><name>delivery_box</name><sdf version='1.9'>model.sdf</sdf></model>\n")
    plugin = f"""
    <plugin filename="dronswarm-tether-system" name="dronswarm::TetherSystem">
      <stiffness>6000</stiffness>
      <damping>120</damping>
      <tether>
        <a model="ds_d_hook_0" link="base_link" offset="0 0 -0.08"/>
        <b model="delivery_box" link="box" offset="0 0 {c / 2}"/>
        <length>{rope}</length>
      </tether>
    </plugin>"""
    (WORLDS / "mine_delivery.sdf").write_text(world(wind, wind_dir, scale, plugin))
    return {"payload_kg": payload_kg, "rope_m": rope, "box": [a, b, c]}


TOWER = {"name": "torre_iluminacion", "x": 0.0, "y": 40.0, "radius": 1.0, "height": 25.0}


def monitor_plugin(obstacles: list[dict]) -> str:
    """Monitor de separación (simulation/plugins/safety): radios de colisión de cada tipo de dron y obstáculos."""
    summary = json.loads((MODELS / "models_summary.json").read_text())
    vehicles = "".join(f'\n      <vehicle prefix="{v["model"]}" radius="{v["radius_m"]}"/>' for v in summary.values())
    vehicles += '\n      <vehicle prefix="x500" radius="0.38"/>'
    obst = "".join(f'\n      <obstacle name="{o["name"]}" x="{o["x"]}" y="{o["y"]}" radius="{o["radius"]}" height="{o["height"]}"/>'
                   for o in obstacles)
    return f"""
    <plugin filename="dronswarm-swarm-monitor-system" name="dronswarm::SwarmMonitorSystem">{vehicles}{obst}
    </plugin>"""


def swarm_scene(wind: float, wind_dir_deg: float, scale: float) -> dict:
    """S06 · Campo de pruebas del enjambre: suelo plano a 4,300 msnm, una torre de iluminación en la ruta y el monitor."""
    t = TOWER
    static_model(t["name"], f"""
    <link name="mast">
      <pose>0 0 {t["height"] / 2} 0 0 0</pose>
      <collision name="c"><geometry><cylinder><radius>{t["radius"]}</radius><length>{t["height"]}</length></cylinder></geometry></collision>
      <visual name="v"><geometry><cylinder><radius>{t["radius"]}</radius><length>{t["height"]}</length></cylinder></geometry>
        {gen_sdf.material((0.75, 0.75, 0.72))}</visual>
    </link>
    <link name="lamps">
      <pose>0 0 {t["height"] + 0.6} 0 0 0</pose>
      <visual name="v"><geometry><box><size>4 1.2 1.2</size></box></geometry>{gen_sdf.material((0.95, 0.85, 0.2))}</visual>
    </link>""")
    src = world(wind, wind_dir_deg, scale, monitor_plugin([t]) + f"""
    <include><uri>model://{t["name"]}</uri><pose>{t["x"]} {t["y"]} 0 0 0 0</pose></include>""")
    src = src.replace("".join(f"\n    <include><uri>model://{m}</uri></include>"
                              for m in ("mine_terrain", "mine_conveyor", "mine_tailings", "mine_tunnel")), "")
    ground = re.search(r'<model name="ground_plane">.*?</model>',
                       (gen_sdf.PX4_DIR / "Tools/simulation/gz/worlds/default.sdf").read_text(), flags=re.S).group(0)
    src = src.replace("  </world>", f"    {ground}\n  </world>")
    (WORLDS / "swarm.sdf").write_text(src)
    m = re.search(r"<latitude_deg>(.*?)</latitude_deg>.*?<longitude_deg>(.*?)</longitude_deg>", src, flags=re.S)
    return {"origin_latlon": [float(m.group(1)), float(m.group(2))], "obstacles": [t], "wind_ms": wind}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wind", type=float, default=0.0, help="viento medio [m/s] (con ráfagas de ±25 %)")
    ap.add_argument("--wind-dir", type=float, default=270.0, help="de dónde sopla [°], 270 = del oeste")
    ap.add_argument("--wind-scale", type=float, default=0.04,
                    help="factor de fuerza de WindEffects; 0.04 ≈ arrastre ½ρV²·CdA de DS-I/DS-D a 4,500 msnm")
    ap.add_argument("--swarm-wind", type=float, default=4.0, help="viento del campo de pruebas del enjambre [m/s]")
    a = ap.parse_args()

    MODELS.mkdir(parents=True, exist_ok=True)
    td = MODELS / "mine_terrain"
    (td / "meshes").mkdir(parents=True, exist_ok=True)
    stats = terrain_mesh(td / "meshes" / "terrain.obj")
    rock = gen_sdf.material((0.55, 0.47, 0.40))
    static_model("mine_terrain", f"""
    <link name="terrain">
      <collision name="terrain_c"><geometry><mesh><uri>meshes/terrain.obj</uri></mesh></geometry></collision>
      <visual name="terrain_v"><geometry><mesh><uri>meshes/terrain.obj</uri></mesh></geometry>{rock}</visual>
    </link>""")
    layout = {
        "pit": {"center": list(PIT_CENTER), "bottom_z": -BENCH_H * BENCHES, "benches": BENCHES, "bench_h_m": BENCH_H,
                "face_angle_deg": FACE_ANGLE, "berm_m": BERM_W, "aspect": PIT_ASPECT, **stats},
        "conveyor": conveyor(), "tailings": tailings(), "tunnel": tunnel(),
        "base": [0.0, 0.0, 0.0], "wind_ms": a.wind, "wind_from_deg": a.wind_dir,
        "location": "referencial: Andes peruanos, 4,300 msnm",
    }
    WORLDS.mkdir(parents=True, exist_ok=True)
    (WORLDS / "mine.sdf").write_text(world(a.wind, a.wind_dir, a.wind_scale))
    layout["delivery"] = delivery_scene(a.wind, a.wind_dir, a.wind_scale)
    layout["delivery"]["target"] = [PIT_CENTER[0], PIT_CENTER[1], -BENCH_H * BENCHES]   # fondo del tajo
    (WORLDS / "mine_layout.json").write_text(json.dumps(layout, indent=2, ensure_ascii=False) + "\n")
    swarm = swarm_scene(a.swarm_wind, a.wind_dir, a.wind_scale)
    (WORLDS / "swarm_layout.json").write_text(json.dumps(swarm, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: layout[k] for k in ("pit", "conveyor", "wind_ms")}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
