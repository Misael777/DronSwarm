#!/usr/bin/env python3
"""Demo de entrega: despegar, volar al punto de entrega, bajar, "entregar", volver y aterrizar.

Vista previa con el x500 de PX4 y una caja fija (la carga no se suelta todavía: el mecanismo de
liberación y el dron de carga DS-D llegan en S05/S08). Sirve para ver cuánto empuje extra pide la carga.

    python tools/sitl/demo_delivery.py --dist 60 --alt 10 --drop-alt 3
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

from demo_formation import connect, distance_m, first, goto, offset, takeoff


async def run(dist: float, alt: float, drop_alt: float, hold: float) -> dict:
    t0 = time.monotonic()
    d = await connect(0)
    await takeoff(d, alt)
    home = await anext(d.telemetry.home())
    cruise_amsl = home.absolute_altitude_m + alt
    lat, lon = offset(home.latitude_deg, home.longitude_deg, dist, 0)

    print(f"→ volando {dist:.0f} m al punto de entrega", flush=True)
    await goto(d, lat, lon, cruise_amsl)
    print(f"↓ bajando a {drop_alt:.0f} m para entregar", flush=True)
    await d.action.goto_location(lat, lon, home.absolute_altitude_m + drop_alt, float("nan"))
    await first(d.telemetry.position(), lambda p: p.relative_altitude_m <= drop_alt + 0.5, 60)
    print(f"■ entregando ({hold:.0f} s)", flush=True)
    await asyncio.sleep(hold)
    print("↑ subiendo y regresando a la base", flush=True)
    await goto(d, lat, lon, cruise_amsl, tol_m=50)  # subir en el mismo punto
    await first(d.telemetry.position(), lambda p: p.relative_altitude_m >= alt - 1.0, 60)
    await goto(d, home.latitude_deg, home.longitude_deg, cruise_amsl)
    await d.action.land()
    await first(d.telemetry.armed(), lambda a: not a, 120)
    final = await anext(d.telemetry.position())
    err = distance_m(final.latitude_deg, final.longitude_deg, home.latitude_deg, home.longitude_deg)
    print(f"✔ aterrizó a {err:.1f} m de la base", flush=True)
    return {"n": 1, "ok": 1, "dist_m": dist, "duration_s": round(time.monotonic() - t0, 1),
            "landing_error_m": round(err, 2), "passed": True}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=1, help="(compatibilidad con run_gz_multi.sh; siempre 1)")
    ap.add_argument("--dist", type=float, default=60.0, help="distancia al punto de entrega [m]")
    ap.add_argument("--alt", type=float, default=10.0, help="altura de crucero [m]")
    ap.add_argument("--drop-alt", type=float, default=3.0, help="altura de entrega [m]")
    ap.add_argument("--hold", type=float, default=5.0, help="segundos en el punto de entrega")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    res = asyncio.run(run(a.dist, a.alt, a.drop_alt, a.hold))
    print(json.dumps(res, indent=2))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=2) + "\n")


if __name__ == "__main__":
    main()
