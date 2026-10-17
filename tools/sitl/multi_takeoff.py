#!/usr/bin/env python3
"""Despegue simultáneo de N drones PX4 SITL (uno por instancia) a alturas escalonadas, y aterrizaje.

Cada instancia i de PX4 publica MAVLink en el puerto UDP 14540 + i. Cada dron usa su propio
mavsdk_server (puerto gRPC 50051 + i).

    python tools/sitl/multi_takeoff.py --n 6 --out docs/evidencias/sitl/multi_takeoff.json
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

from mavsdk_grpc import System
from mavsdk_grpc.action import ActionError


async def first(stream, pred, timeout):
    async def _run():
        async for v in stream:
            if pred(v):
                return v

    return await asyncio.wait_for(_run(), timeout)


async def fly(i: int, alt: float, hold_s: float) -> dict:
    drone = System(port=50051 + i)
    await drone.connect(system_address=f"udpin://0.0.0.0:{14540 + i}")
    await first(drone.core.connection_state(), lambda s: s.is_connected, 90)
    await first(drone.telemetry.health(), lambda h: h.is_global_position_ok and h.is_home_position_ok, 180)
    await drone.action.set_takeoff_altitude(alt)
    # PX4 rechaza el armado mientras sus chequeos de prevuelo no terminan; reintentar como lo hace una GCS
    arm_attempts = 0
    while True:
        arm_attempts += 1
        try:
            await drone.action.arm()
            break
        except ActionError as e:
            if arm_attempts >= 30:
                raise RuntimeError(f"dron {i}: armado rechazado {arm_attempts} veces ({e._result.result})") from e
            await asyncio.sleep(2)
    await drone.action.takeoff()
    reached = await first(drone.telemetry.position(), lambda p: p.relative_altitude_m >= alt - 1.0, 90)
    await asyncio.sleep(hold_s)
    await drone.action.land()
    await first(drone.telemetry.armed(), lambda a: not a, 120)
    return {"drone": i, "target_alt_m": alt, "reached_alt_m": round(reached.relative_altitude_m, 2),
            "arm_attempts": arm_attempts, "landed": True}


async def run(n: int, hold_s: float) -> dict:
    t0 = time.monotonic()
    results = await asyncio.gather(*(fly(i, 5.0 + 2.0 * i, hold_s) for i in range(n)), return_exceptions=True)
    ok = [r for r in results if isinstance(r, dict)]
    errors = [repr(r) for r in results if not isinstance(r, dict)]
    return {"n": n, "ok": len(ok), "errors": errors, "duration_s": round(time.monotonic() - t0, 1),
            "drones": ok, "passed": len(ok) == n}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--hold", type=float, default=15.0)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    res = asyncio.run(run(a.n, a.hold))
    print(json.dumps(res, indent=2))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=2) + "\n")
    raise SystemExit(0 if res["passed"] else 1)


if __name__ == "__main__":
    main()
