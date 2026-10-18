#!/usr/bin/env python3
"""Demo de carga cooperativa: N drones (escena de tools/gen_coop.py) levantan juntos una caja con cuerdas.

Secuencia: despegue simultáneo lento → la cuerda se tensa y la caja sube → traslado de `--dist` m en formación
→ descenso hasta apoyar la caja → aterrizaje. La altura y posición de la caja se leen de Gazebo (verdad física),
no de los drones.

Es una vista previa: cada dron usa su controlador PX4 normal y "siente" la cuerda como una perturbación. Un control
cooperativo de verdad (repartir la carga, amortiguar el péndulo) es trabajo de la fase v2.

    python tools/sitl/demo_coop_lift.py --n 3 --alt 5 --dist 15
"""

import argparse
import asyncio
import json
import re
import subprocess
import time
from pathlib import Path

from demo_formation import connect, first, offset
from mavsdk_grpc.action import ActionError

WORLD = "default"
BOX_HALF_HEIGHT = 0.15          # el origen del modelo está en la base de la caja; se reporta su centro


def box_position() -> tuple[float, float, float] | None:
    """Centro de la caja en el mundo, leído del tópico de poses que Gazebo publica en continuo."""
    try:
        out = subprocess.run(["gz", "topic", "-e", "-t", f"/world/{WORLD}/pose/info", "-n", "1"], capture_output=True,
                             text=True, timeout=10).stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    m = re.search(r'name: "coop_payload".*?position \{\s*(?:x: ([-\d.e]+)\s*)?(?:y: ([-\d.e]+)\s*)?(?:z: ([-\d.e]+))?',
                  out, flags=re.S)
    if not m:
        return None
    x, y, z = (float(v) if v else 0.0 for v in m.groups())   # protobuf omite los campos en cero
    return x, y, z + BOX_HALF_HEIGHT


async def lift_off(d):
    """Armar (con reintentos) y despegar a la altura por defecto; las cuerdas aún están flojas."""
    for attempt in range(30):
        try:
            await d.action.arm()
            break
        except ActionError:
            if attempt == 29:
                raise
            await asyncio.sleep(2)
    await d.action.takeoff()
    await first(d.telemetry.position(), lambda p: p.relative_altitude_m >= 1.5, 120)


async def climb_together(drones, alt: float):
    """Subir todos a la vez a la misma altura con una orden de posición explícita: la carga se reparte."""
    homes = [await anext(d.telemetry.home()) for d in drones]
    here = [await anext(d.telemetry.position()) for d in drones]
    await asyncio.gather(*(d.action.goto_location(p.latitude_deg, p.longitude_deg, h.absolute_altitude_m + alt, float("nan"))
                           for d, h, p in zip(drones, homes, here)))
    await asyncio.gather(*(first(d.telemetry.position(), lambda q: q.relative_altitude_m >= alt - 0.6, 180) for d in drones))


async def watch_box(samples: list, stop: asyncio.Event):
    while not stop.is_set():
        p = await asyncio.to_thread(box_position)
        if p:
            samples.append((time.monotonic(), *p))
        await asyncio.sleep(1.0)


async def run(n: int, alt: float, dist: float, speed: float) -> dict:
    t0 = time.monotonic()
    drones = await asyncio.wait_for(asyncio.gather(*(connect(i) for i in range(n))), 240)
    samples: list = []
    stop = asyncio.Event()
    watcher = asyncio.create_task(watch_box(samples, stop))
    start_box = box_position()

    for d in drones:                                      # velocidad de crucero baja: la caja cuelga como péndulo
        await d.param.set_param_float("MPC_XY_VEL_MAX", max(speed, 2.0))
        await d.param.set_param_float("MPC_XY_CRUISE", speed)
        await d.param.set_param_float("MPC_Z_VEL_MAX_UP", 1.0)   # subida lenta: la cuerda se tensa sin tirón
    # Que el estimador (EKF) converja antes de armar: si no, PX4 puede perder la posición al despegar ("blind land")
    print("… esperando que los estimadores de los drones converjan", flush=True)
    await asyncio.sleep(15)
    await asyncio.gather(*(first(d.telemetry.health(), lambda h: h.is_armable and h.is_local_position_ok
                                 and h.is_global_position_ok, 120) for d in drones))
    print(f"↑ despegue simultáneo de {n} drones (cuerdas flojas)", flush=True)
    await asyncio.gather(*(lift_off(d) for d in drones))
    print(f"↑ subida conjunta a {alt:.0f} m: las cuerdas se tensan y la caja sube", flush=True)
    await climb_together(drones, alt)
    await asyncio.sleep(6)                                  # que se amortigüe el péndulo
    lifted = box_position()
    if lifted:
        print(f"  caja a {lifted[2]:.2f} m del suelo", flush=True)

    starts = [await anext(d.telemetry.position()) for d in drones]
    print(f"→ traslado en formación {dist:.0f} m al norte a {speed:.1f} m/s", flush=True)
    await asyncio.gather(*(d.action.goto_location(*offset(s.latitude_deg, s.longitude_deg, dist, 0), s.absolute_altitude_m,
                                                  float("nan")) for d, s in zip(drones, starts)))
    await asyncio.sleep(dist / speed + 8)
    moved = box_position()
    if moved:
        print(f"  caja a {moved[2]:.2f} m del suelo, desplazada {moved[0] - (start_box or (0, 0, 0))[0]:.1f} m (este) "
              f"y {moved[1] - (start_box or (0, 0, 0))[1]:.1f} m (norte)", flush=True)

    print("↓ aterrizaje simultáneo (la caja toca el suelo primero)", flush=True)
    await asyncio.gather(*(d.action.land() for d in drones))
    await asyncio.gather(*(first(d.telemetry.armed(), lambda a: not a, 180) for d in drones))
    stop.set()
    await watcher
    end_box = box_position()

    max_z = max((s[3] for s in samples), default=0.0)
    north = (end_box[1] - start_box[1]) if (end_box and start_box) else None
    res = {"n": n, "ok": n, "payload_lifted": max_z > (start_box[2] if start_box else 0.15) + 0.5,
           "box_max_height_m": round(max_z, 2), "box_moved_north_m": round(north, 1) if north is not None else None,
           "duration_s": round(time.monotonic() - t0, 1)}
    res["passed"] = bool(res["payload_lifted"] and north is not None and north > 0.7 * dist)
    print(f"✔ caja levantada hasta {max_z:.2f} m y trasladada {res['box_moved_north_m']} m" if res["passed"]
          else "✘ la caja no se levantó o no se trasladó como se esperaba", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--alt", type=float, default=5.0)
    ap.add_argument("--dist", type=float, default=15.0)
    ap.add_argument("--speed", type=float, default=1.5)
    ap.add_argument("--hold", type=float, default=0.0, help="(compatibilidad con run_gz_multi.sh)")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    res = asyncio.run(run(a.n, a.alt, a.dist, a.speed))
    print(json.dumps(res, indent=2))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=2) + "\n")
    raise SystemExit(0 if res["passed"] else 1)


if __name__ == "__main__":
    main()
