#!/usr/bin/env python3
"""S05-01 · Genera los modelos de Gazebo (SDF) y los airframes de PX4 de DS-I, DS-D y DS-H desde el S04.

Entradas: engineering/data/results/ds-*_sizing.json (masa, inercias, constantes de motor, hélice, geometría).
Salidas:
    simulation/xtdrone/models/<modelo>/model.sdf + model.config   (Gazebo)
    simulation/px4/airframes/<id>_gz_<modelo>                      (PX4: rotores, mezcla, hover)

Las constantes de motor (empuje = kT·ω²) se calcularon con el aire de 4,500 msnm a 0 °C: en la simulación el dron
"vuela en la mina" aunque Gazebo no modele la densidad del aire. Los sensores (IMU, barómetro, GNSS) se copian del
x500 de PX4 para tener el mismo ruido que el resto de la simulación.

    .venv/bin/python tools/gen_sdf.py
"""

import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engineering.inertia import vehicle_inertia  # noqa: E402

RESULTS = ROOT / "engineering" / "data" / "results"
MODELS = ROOT / "simulation" / "xtdrone" / "models"
AIRFRAMES = ROOT / "simulation" / "px4" / "airframes"
PX4_DIR = Path.home() / "src" / "PX4-Autopilot"

VEHICLES = {
    # vehículo: (modelo, id de airframe, color RGB, altura de patas [m], motor (radio, alto) [m], caja de carga [m])
    "DS-I": ("ds_i", 22001, (0.15, 0.35, 0.65), 0.16, (0.022, 0.030), None),
    "DS-D": ("ds_d", 22002, (0.95, 0.70, 0.10), 0.42, (0.040, 0.040), (0.40, 0.30, 0.22)),
    "DS-H": ("ds_h", 22003, (0.80, 0.20, 0.15), 0.52, (0.050, 0.045), (0.50, 0.40, 0.28)),
}
ROTOR_MASS = 0.02
# Máscaras de colisión: 0x01 = drones y cajas, 0x02 = cuerdas. El suelo choca con todo; las cuerdas no chocan con
# los drones (el gancho está soldado al dron y la física no tolera que además se toquen).
DRONE_MASK = "<surface><contact><collide_bitmask>0x01</collide_bitmask></contact></surface>"
X500_DRAG = 8.06428e-05          # rotorDragCoefficient del x500 (hélice de 10")


def sensors_block() -> str:
    """Sensores del x500 de PX4 (barómetro, IMU, GNSS) para reutilizar su modelo de ruido."""
    base = (PX4_DIR / "Tools/simulation/gz/models/x500_base/model.sdf").read_text()
    return "\n".join(re.findall(r"(\s*<sensor name=.*?</sensor>)", base, flags=re.S))


def box_inertia(m: float, a: float, b: float, c: float) -> str:
    return (f"<inertia><ixx>{m * (b * b + c * c) / 12:.6g}</ixx><iyy>{m * (a * a + c * c) / 12:.6g}</iyy>"
            f"<izz>{m * (a * a + b * b) / 12:.6g}</izz><ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia>")


def rotor_xy(n: int, radius: float) -> list[tuple[float, float]]:
    offset = math.pi / n if n == 4 else 0.0
    return [(radius * math.cos(offset + 2 * math.pi * i / n), radius * math.sin(offset + 2 * math.pi * i / n)) for i in range(n)]


def material(rgb, alpha=1.0) -> str:
    r, g, b = rgb
    return (f"<material><ambient>{r} {g} {b} {alpha}</ambient><diffuse>{r} {g} {b} {alpha}</diffuse>"
            f"<specular>0.1 0.1 0.1 1</specular></material>")


def build(vehicle: str, design: dict, with_payload: bool = True, name_suffix: str = "", extra_plugins: str = "") -> tuple[str, dict]:
    model, _, color, leg_h, (motor_r, motor_h), payload_box = VEHICLES[vehicle]
    name = model + name_suffix
    n = design["rotors"]
    radius = design["wheelbase_m"] / 2
    prop_r = design["prop_diameter_in"] * 0.0254 / 2
    payload_kg = design["masses"].get("carga útil", 0.0)
    has_payload = with_payload and payload_kg > 0 and payload_box is not None
    body_mass = design["mtow_kg"] - payload_kg - n * ROTOR_MASS
    # Inercia del dron sin la carga (la caja es un link aparte): restar su aporte (caja bajo el CG)
    plate = 0.25 * design["wheelbase_m"]
    body_box = (plate, plate, 0.10)
    sdf = design["sdf"]
    z_rot = 0.05

    v = []   # visuales del cuerpo
    v.append(f'<visual name="body"><geometry><box><size>{plate:.3f} {plate:.3f} 0.08</size></box></geometry>{material(color)}</visual>')
    v.append(f'<visual name="canopy"><pose>0 0 0.06 0 0 0</pose><geometry><cylinder><radius>{plate * 0.35:.3f}</radius>'
             f'<length>0.05</length></cylinder></geometry>{material((0.15, 0.15, 0.15))}</visual>')
    for k, (x, y) in enumerate(rotor_xy(n, radius)):
        yaw = math.atan2(y, x)
        arm_len = radius - plate / 2 + motor_r
        cx, cy = (plate / 2 + arm_len / 2) * math.cos(yaw), (plate / 2 + arm_len / 2) * math.sin(yaw)
        tube = design["arm"]["tube"]
        od = float(re.search(r"Ø(\d+)", tube).group(1)) / 1000
        v.append(f'<visual name="arm_{k}"><pose>{cx:.4f} {cy:.4f} 0 0 1.5708 {yaw:.4f}</pose><geometry><cylinder>'
                 f'<radius>{od / 2:.4f}</radius><length>{arm_len:.4f}</length></cylinder></geometry>{material((0.1, 0.1, 0.1))}</visual>')
        v.append(f'<visual name="motor_{k}"><pose>{x:.4f} {y:.4f} {z_rot - motor_h / 2 - 0.005:.4f} 0 0 0</pose><geometry><cylinder>'
                 f'<radius>{motor_r}</radius><length>{motor_h}</length></cylinder></geometry>{material((0.3, 0.3, 0.32))}</visual>')
    feet = []
    for k, (sx, sy) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
        lx, ly = sx * plate * 0.45, sy * plate * 0.45
        v.append(f'<visual name="leg_{k}"><pose>{lx:.3f} {ly:.3f} {-leg_h / 2:.3f} 0 0 0</pose><geometry><cylinder>'
                 f'<radius>0.008</radius><length>{leg_h:.3f}</length></cylinder></geometry>{material((0.1, 0.1, 0.1))}</visual>')
        feet.append(f'<collision name="foot_{k}"><pose>{lx:.3f} {ly:.3f} {-leg_h + 0.015:.3f} 0 0 0</pose><geometry><sphere>'
                    f'<radius>0.015</radius></sphere></geometry>{DRONE_MASK}</collision>')

    rotors, joints, plugins = [], [], []
    for k, (x, y) in enumerate(rotor_xy(n, radius)):
        ccw = k % 2 == 0
        rotors.append(f"""
    <link name="rotor_{k}">
      <pose>{x:.4f} {y:.4f} {z_rot:.3f} 0 0 0</pose>
      <inertial><mass>{ROTOR_MASS}</mass>{box_inertia(ROTOR_MASS, 2 * prop_r, 0.02, 0.005)}</inertial>
      <visual name="rotor_{k}_disc"><geometry><cylinder><radius>{prop_r:.4f}</radius><length>0.004</length></cylinder></geometry>
        {material((0.2, 0.2, 0.2) if ccw else (0.35, 0.35, 0.35), 0.45)}</visual>
      <visual name="rotor_{k}_blade"><geometry><box><size>{2 * prop_r:.4f} {0.08 * prop_r:.4f} 0.006</size></box></geometry>
        {material((0.05, 0.05, 0.05))}</visual>
    </link>""")
        joints.append(f"""
    <joint name="rotor_{k}_joint" type="revolute">
      <parent>base_link</parent><child>rotor_{k}</child>
      <axis><xyz>0 0 1</xyz><limit><lower>-1e+16</lower><upper>1e+16</upper></limit></axis>
    </joint>""")
        scale = (design["prop_diameter_in"] / 10) ** 2
        tc = 0.0125 * max(1.0, design["prop_diameter_in"] / 10)
        plugins.append(f"""
    <plugin filename="gz-sim-multicopter-motor-model-system" name="gz::sim::systems::MulticopterMotorModel">
      <jointName>rotor_{k}_joint</jointName>
      <linkName>rotor_{k}</linkName>
      <turningDirection>{'ccw' if ccw else 'cw'}</turningDirection>
      <timeConstantUp>{tc:.4f}</timeConstantUp>
      <timeConstantDown>{2 * tc:.4f}</timeConstantDown>
      <maxRotVelocity>{sdf['maxRotVelocity']:.1f}</maxRotVelocity>
      <motorConstant>{sdf['motorConstant']:.6e}</motorConstant>
      <momentConstant>{sdf['momentConstant']:.5f}</momentConstant>
      <commandSubTopic>command/motor_speed</commandSubTopic>
      <motorNumber>{k}</motorNumber>
      <rotorDragCoefficient>{X500_DRAG * scale:.6e}</rotorDragCoefficient>
      <rollingMomentCoefficient>1e-06</rollingMomentCoefficient>
      <rotorVelocitySlowdownSim>10</rotorVelocitySlowdownSim>
      <motorType>velocity</motorType>
    </plugin>""")

    payload = ""
    if has_payload:
        a, b, c = payload_box
        pz = -leg_h + c / 2 + 0.03
        payload = f"""
    <link name="payload">
      <pose>0 0 {pz:.3f} 0 0 0</pose>
      <inertial><mass>{payload_kg}</mass>{box_inertia(payload_kg, a, b, c)}</inertial>
      <visual name="payload_box"><geometry><box><size>{a} {b} {c}</size></box></geometry>{material((0.9, 0.45, 0.1))}</visual>
      <visual name="payload_label"><pose>0 0 {c / 2 + 0.001:.3f} 0 0 0</pose><geometry><box><size>{a * 0.6:.3f} {b * 0.3:.3f} 0.002</size></box></geometry>
        {material((0.95, 0.95, 0.95))}</visual>
    </link>
    <joint name="payload_joint" type="fixed"><parent>base_link</parent><child>payload</child></joint>"""


    mass_total = body_mass + (payload_kg if has_payload else 0.0) + n * ROTOR_MASS
    # Inercia del cuerpo SIN la carga (la caja es un link aparte), con el mismo modelo de masas del S04
    ms = design["masses"]
    tip = (ms["motores"] + ms["hélices"] + ms["ESC"] + ms["soportes de motor"]) / n
    body = ms["equipo fijo"] + ms["placas centrales"] + ms["piezas impresas y tornillería"]
    bi = vehicle_inertia(n, radius, tip, ms["brazos"] / n, body, body_box, ms["batería"], 0.0)
    body_inertia = (f"<inertia><ixx>{bi['ixx']:.6g}</ixx><iyy>{bi['iyy']:.6g}</iyy><izz>{bi['izz']:.6g}</izz>"
                    f"<ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia>")
    text = f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- Generado por tools/gen_sdf.py desde engineering/data/results ({vehicle}). No editar a mano. -->
<sdf version="1.9">
  <model name="{name}">
    <link name="base_link">
      <enable_wind>true</enable_wind>
      <inertial><mass>{body_mass:.4f}</mass>{body_inertia}</inertial>
      <collision name="body_collision"><geometry><box><size>{plate:.3f} {plate:.3f} 0.08</size></box></geometry>{DRONE_MASK}</collision>
      {''.join(feet)}
      {''.join(v)}
{sensors_block()}
    </link>{''.join(rotors)}{''.join(joints)}{payload}{''.join(plugins)}{extra_plugins}
  </model>
</sdf>
"""
    info = {"model": name, "mass_kg": round(mass_total, 3), "rotors": n, "leg_height_m": leg_h,
            "payload_kg": payload_kg if has_payload else 0.0, "wheelbase_m": design["wheelbase_m"]}
    return text, info


def airframe(vehicle: str, design: dict, model_name: str, af_id: int) -> str:
    n = design["rotors"]
    sdf = design["sdf"]
    radius = design["wheelbase_m"] / 2
    w_max = sdf["maxRotVelocity"]
    hover = design["performance"]["hover_rpm"] * 2 * math.pi / 60
    lines = [
        "#!/bin/sh",
        f"# @name DronSwarm {vehicle} (generado por tools/gen_sdf.py)",
        f"# @type {'Quadrotor' if n == 4 else 'Hexarotor' if n == 6 else 'Octorotor'}",
        "",
        ". ${R}etc/init.d/rc.mc_defaults",
        "",
        "PX4_SIMULATOR=${PX4_SIMULATOR:=gz}",
        "PX4_GZ_WORLD=${PX4_GZ_WORLD:=default}",
        f"PX4_SIM_MODEL=${{PX4_SIM_MODEL:={model_name}}}",
        "",
        "param set-default SIM_GZ_EN 1",
        "param set-default SENS_EN_GPSSIM 1",
        "param set-default SENS_EN_BAROSIM 0",
        "param set-default SENS_EN_MAGSIM 1",
        "",
        "param set-default CA_AIRFRAME 0",
        f"param set-default CA_ROTOR_COUNT {n}",
    ]
    for k, (x, y) in enumerate(rotor_xy(n, radius)):
        km = sdf["momentConstant"] if k % 2 == 0 else -sdf["momentConstant"]
        lines += [f"param set-default CA_ROTOR{k}_PX {x:.4f}", f"param set-default CA_ROTOR{k}_PY {-y:.4f}",
                  f"param set-default CA_ROTOR{k}_KM {km:.4f}"]
    for k in range(n):
        lines += [f"param set-default SIM_GZ_EC_FUNC{k + 1} {101 + k}",
                  f"param set-default SIM_GZ_EC_MIN{k + 1} {0.15 * w_max:.0f}",
                  f"param set-default SIM_GZ_EC_MAX{k + 1} {w_max:.0f}"]
    lines += ["", f"param set-default MPC_THR_HOVER {min(0.8, max(0.3, hover / w_max)):.2f}"]
    if n >= 6:   # drones grandes: más lentos en giro, ganancias de actitud más suaves
        lines += ["param set-default MPC_TILTMAX_AIR 30", "param set-default MPC_ACC_HOR 2.0",
                  "param set-default MPC_XY_VEL_MAX 8"]
    return "\n".join(lines) + "\n"


def main():
    MODELS.mkdir(parents=True, exist_ok=True)
    AIRFRAMES.mkdir(parents=True, exist_ok=True)
    summary = {}
    for vehicle, (model, af_id, *_rest) in VEHICLES.items():
        path = RESULTS / f"{vehicle.lower()}_sizing.json"
        if not path.exists():
            print(f"{vehicle}: falta {path.name} (correr engineering.sizing)")
            continue
        design = json.loads(path.read_text())
        sdf_text, info = build(vehicle, design)
        d = MODELS / model
        d.mkdir(exist_ok=True)
        (d / "model.sdf").write_text(sdf_text)
        (d / "model.config").write_text(f"<?xml version='1.0'?>\n<model><name>{model}</name><version>1.0</version>"
                                        f"<sdf version='1.9'>model.sdf</sdf><description>DronSwarm {vehicle}</description></model>\n")
        af = AIRFRAMES / f"{af_id}_gz_{model}"
        af.write_text(airframe(vehicle, design, model, af_id))
        af.chmod(0o755)
        summary[vehicle] = info
        print(f"{vehicle}: {d / 'model.sdf'} · {af.name} · {info}")
    (MODELS / "models_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
