#!/usr/bin/env python3
"""Prueba de humo de PX4 SITL vía MAVSDK: armar, despegar, mantener, aterrizar.

Criterio de aceptación (S01-04): el dron alcanza la altura objetivo (±1 m) y aterriza desarmado.
Funciona igual con SIH (sin Gazebo), Gazebo o un dron real, porque solo habla MAVLink con PX4.

    python tools/sitl/smoke_test.py --url udpin://0.0.0.0:14540 --alt 10
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from mavsdk_grpc import System


async def wait_for(predicate_stream, predicate, timeout):
    async def _run():
        async for value in predicate_stream:
            if predicate(value):
                return value

    return await asyncio.wait_for(_run(), timeout)


async def run(url: str, alt: float, hold_s: float) -> dict:
    drone = System()
    t0 = time.monotonic()
    await drone.connect(system_address=url)
    await wait_for(drone.core.connection_state(), lambda s: s.is_connected, 60)
    await wait_for(drone.telemetry.health(), lambda h: h.is_global_position_ok and h.is_home_position_ok, 120)

    await drone.action.set_takeoff_altitude(alt)
    await drone.action.arm()
    await drone.action.takeoff()

    reached = await wait_for(drone.telemetry.position(), lambda p: p.relative_altitude_m >= alt - 1.0, 60)
    t_takeoff = time.monotonic() - t0

    await asyncio.sleep(3.0)  # estabilización: el error de hover se mide sin el final del ascenso
    samples = []
    end = time.monotonic() + hold_s
    async for p in drone.telemetry.position():
        samples.append(p.relative_altitude_m)
        if time.monotonic() > end:
            break

    battery = await anext(drone.telemetry.battery())
    await drone.action.land()
    await wait_for(drone.telemetry.armed(), lambda armed: not armed, 90)
    final = await anext(drone.telemetry.position())

    hold_err = max(abs(a - alt) for a in samples) if samples else float("nan")
    return {
        "url": url,
        "target_alt_m": alt,
        "reached_alt_m": round(reached.relative_altitude_m, 2),
        "time_to_altitude_s": round(t_takeoff, 1),
        "hold_samples": len(samples),
        "hold_max_error_m": round(hold_err, 2),
        "battery_remaining_pct": round(battery.remaining_percent * 100, 1)
        if battery.remaining_percent <= 1 else round(battery.remaining_percent, 1),
        "landed_alt_m": round(final.relative_altitude_m, 2),
        "disarmed": True,
        "passed": abs(reached.relative_altitude_m - alt) <= 1.0 and hold_err <= 1.0 and abs(final.relative_altitude_m) <= 0.5,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="udpin://0.0.0.0:14540")
    ap.add_argument("--alt", type=float, default=10.0)
    ap.add_argument("--hold", type=float, default=10.0, help="segundos manteniendo altura")
    ap.add_argument("--out", type=Path, help="guardar resultado en JSON")
    args = ap.parse_args()

    result = asyncio.run(run(args.url, args.alt, args.hold))
    print(json.dumps(result, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
