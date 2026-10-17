#!/usr/bin/env python3
"""Demo visual: N drones despegan, recorren un cuadrado manteniendo la formación y aterrizan.

Es una vista previa para ver el enjambre en Gazebo; el control de formación de verdad (consenso,
evitación de colisiones) se desarrolla en S06 en control/swarm/.

    python tools/sitl/demo_formation.py --n 4 --side 30 --alt 10
"""

import argparse
import asyncio
import json
import math
import time
from pathlib import Path

from mavsdk_grpc import System
from mavsdk_grpc.action import ActionError

EARTH_R = 6_378_137.0


def offset(lat, lon, north_m, east_m):
    """Desplaza una coordenada (grados) unos metros al norte y al este."""
    dlat = north_m / EARTH_R
    dlon = east_m / (EARTH_R * math.cos(math.radians(lat)))
    return lat + math.degrees(dlat), lon + math.degrees(dlon)


def distance_m(lat1, lon1, lat2, lon2):
    dn = math.radians(lat2 - lat1) * EARTH_R
    de = math.radians(lon2 - lon1) * EARTH_R * math.cos(math.radians(lat1))
    return math.hypot(dn, de)


async def first(stream, pred, timeout):
    async def _run():
        async for v in stream:
            if pred(v):
                return v

    return await asyncio.wait_for(_run(), timeout)


async def connect(i: int) -> System:
    d = System(port=50051 + i)
    await d.connect(system_address=f"udpin://0.0.0.0:{14540 + i}")
    await first(d.core.connection_state(), lambda s: s.is_connected, 90)
    await first(d.telemetry.health(), lambda h: h.is_global_position_ok and h.is_home_position_ok, 180)
    return d


async def takeoff(d: System, alt: float):
    await d.action.set_takeoff_altitude(alt)
    for attempt in range(30):
        try:
            await d.action.arm()
            break
        except ActionError:
            if attempt == 29:
                raise
            await asyncio.sleep(2)
    await d.action.takeoff()
    await first(d.telemetry.position(), lambda p: p.relative_altitude_m >= alt - 1.0, 90)


async def goto(d: System, lat: float, lon: float, alt_amsl: float, tol_m: float = 1.5, timeout: float = 120):
    await d.action.goto_location(lat, lon, alt_amsl, float("nan"))
    await first(d.telemetry.position(), lambda p: distance_m(p.latitude_deg, p.longitude_deg, lat, lon) < tol_m, timeout)


async def run(n: int, side: float, alt: float) -> dict:
    t0 = time.monotonic()
    drones = await asyncio.gather(*(connect(i) for i in range(n)))
    await asyncio.gather(*(takeoff(d, alt) for d in drones))
    starts = [await anext(d.telemetry.position()) for d in drones]

    # Cuadrado: norte, este, sur, oeste. Cada dron mueve su propia posición inicial → la formación se conserva.
    legs = [(side, 0), (side, side), (0, side), (0, 0)]
    for k, (dn, de) in enumerate(legs, start=1):
        await asyncio.gather(*(goto(d, *offset(s.latitude_deg, s.longitude_deg, dn, de), s.absolute_altitude_m)
                               for d, s in zip(drones, starts)))
        print(f"vértice {k}/4 alcanzado por los {n} drones", flush=True)

    await asyncio.gather(*(d.action.land() for d in drones))
    await asyncio.gather(*(first(d.telemetry.armed(), lambda a: not a, 120) for d in drones))
    return {"n": n, "ok": n, "side_m": side, "alt_m": alt, "duration_s": round(time.monotonic() - t0, 1), "passed": True}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--side", type=float, default=30.0, help="lado del cuadrado [m]")
    ap.add_argument("--alt", type=float, default=10.0, help="altura de vuelo [m]")
    ap.add_argument("--hold", type=float, default=0.0, help="(compatibilidad con run_gz_multi.sh; no se usa)")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    res = asyncio.run(run(a.n, a.side, a.alt))
    print(json.dumps(res, indent=2))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=2) + "\n")


if __name__ == "__main__":
    main()
