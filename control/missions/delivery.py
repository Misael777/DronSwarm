#!/usr/bin/env python3
"""S05-05 · Misión de entrega con liberación de carga (DS-D con gancho, escena SCENE=delivery).

Despegue con la caja colgada → crucero a 15 m sobre la base → descenso al punto de entrega hasta apoyar la caja →
se suelta el gancho → ascenso → regreso → aterrizaje. Se verifica con la posición real de la caja en Gazebo.

En el dron real la orden de soltar será un servo (acción de PX4); en simulación es el tópico /tether/0/release.

    python control/missions/delivery.py --out resultados/entrega.json
"""

import argparse
import asyncio
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "sitl"))
sys.path.insert(0, str(ROOT / "control" / "missions"))
from demo_formation import connect, first  # noqa: E402
from inspection import enu_to_latlon, latlon_to_enu  # noqa: E402

BOX_HALF = 0.11
ROPE = 0.5
HOOK_BELOW_BASE = 0.08


def box_position() -> tuple[float, float, float] | None:
    try:
        out = subprocess.run(["gz", "topic", "-e", "-t", "/world/default/pose/info", "-n", "1"], capture_output=True,
                             text=True, timeout=10).stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    m = re.search(r'name: "delivery_box".*?position \{\s*(?:x: ([-\d.e]+)\s*)?(?:y: ([-\d.e]+)\s*)?(?:z: ([-\d.e]+))?', out, flags=re.S)
    if not m:
        return None
    x, y, z = (float(v) if v else 0.0 for v in m.groups())
    return x, y, z + BOX_HALF


def release_hook() -> bool:
    r = subprocess.run(["gz", "topic", "-t", "/tether/0/release", "-m", "gz.msgs.Boolean", "-p", "data: true"],
                       capture_output=True, text=True, timeout=10)
    return r.returncode == 0


async def run(target: tuple[float, float, float], cruise: float, speed: float) -> dict:
    d = await connect(0)
    await d.param.set_param_float("MPC_XY_CRUISE", speed)
    await d.param.set_param_float("MPC_Z_VEL_MAX_DN", 1.5)
    home = await anext(d.telemetry.home())
    await asyncio.sleep(10)                                  # convergencia del estimador antes de armar
    await first(d.telemetry.health(), lambda h: h.is_armable and h.is_local_position_ok, 120)
    t0 = time.monotonic()
    start_box = box_position()
    for attempt in range(30):
        try:
            await d.action.arm()
            break
        except Exception:
            if attempt == 29:
                raise
            await asyncio.sleep(2)
    await d.action.takeoff()
    await first(d.telemetry.position(), lambda p: p.relative_altitude_m >= 1.5, 120)
    up = box_position()
    print(f"↑ despegue con la caja colgada (caja a {up[2] if up else float('nan'):.2f} m)", flush=True)

    tx, ty, tz = target
    lat, lon = enu_to_latlon(home, tx, ty)
    cruise_abs = home.absolute_altitude_m + cruise
    print(f"→ crucero a {cruise:.0f} m hacia el punto de entrega ({math.hypot(tx, ty):.0f} m, fondo del tajo a {tz:.0f} m)", flush=True)
    await d.action.goto_location(home.latitude_deg, home.longitude_deg, cruise_abs, float("nan"))
    await first(d.telemetry.position(), lambda p: p.relative_altitude_m >= cruise - 1, 120)
    await d.action.goto_location(lat, lon, cruise_abs, float("nan"))
    await first(d.telemetry.position(), lambda p: math.hypot(*(a - b for a, b in zip(latlon_to_enu(home, p.latitude_deg, p.longitude_deg), (tx, ty)))) < 2, 300)

    # Bajar hasta que la caja quede a ~0.3 m del suelo: base del dron = suelo + caja + cuerda + gancho + 0.3
    drop_alt = tz + 2 * BOX_HALF + ROPE + HOOK_BELOW_BASE + 0.3
    print(f"↓ descenso hasta apoyar la caja (dron a {drop_alt:.1f} m relativo a la base)", flush=True)
    await d.action.goto_location(lat, lon, home.absolute_altitude_m + drop_alt, float("nan"))
    await first(d.telemetry.position(), lambda p: p.relative_altitude_m <= drop_alt + 0.5, 240)
    await asyncio.sleep(5)
    print("■ gancho liberado", flush=True)
    released = release_hook()
    await asyncio.sleep(4)
    dropped = box_position()

    print("↑ ascenso y regreso a la base", flush=True)
    await d.action.goto_location(lat, lon, cruise_abs, float("nan"))
    await first(d.telemetry.position(), lambda p: p.relative_altitude_m >= cruise - 2, 240)
    await d.action.goto_location(home.latitude_deg, home.longitude_deg, cruise_abs, float("nan"))
    await first(d.telemetry.position(), lambda p: math.hypot(*latlon_to_enu(home, p.latitude_deg, p.longitude_deg)) < 2, 300)
    await d.action.land()
    await first(d.telemetry.armed(), lambda a: not a, 180)
    final_box = box_position()

    err = math.hypot(final_box[0] - tx, final_box[1] - ty) if final_box else None
    on_ground = final_box is not None and abs(final_box[2] - (tz + BOX_HALF)) < 0.3
    res = {"n": 1, "ok": 1, "released": released, "box_start": start_box, "box_after_release": dropped,
           "box_final": final_box, "delivery_error_m": round(err, 2) if err is not None else None,
           "box_on_ground_at_target": on_ground, "duration_s": round(time.monotonic() - t0)}
    res["passed"] = bool(released and on_ground and err is not None and err < 3)
    print(f"✔ caja entregada a {err:.1f} m del punto objetivo, en el suelo" if res["passed"]
          else "✘ la entrega no cumplió (ver box_final)", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cruise", type=float, default=15.0, help="altura de crucero sobre la base [m]")
    ap.add_argument("--speed", type=float, default=6.0)
    ap.add_argument("--n", type=int, default=1, help="(compatibilidad con run_gz_multi.sh)")
    ap.add_argument("--hold", type=float, default=0.0, help="(compatibilidad con run_gz_multi.sh)")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    layout = json.loads((ROOT / "simulation/xtdrone/worlds/mine_layout.json").read_text())
    res = asyncio.run(run(tuple(layout["delivery"]["target"]), a.cruise, a.speed))
    print(json.dumps(res, indent=2))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=2) + "\n")
    raise SystemExit(0 if res["passed"] else 1)


if __name__ == "__main__":
    main()
