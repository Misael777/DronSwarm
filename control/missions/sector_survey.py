#!/usr/bin/env python3
"""S06-06 · HU-08: un piloto controla 6 drones que levantan un área dividida en sectores.

Criterios de aceptación de la HU-08: el sistema asigna sectores, separa altitudes, no hay conflictos de distancia
< 10 m entre drones y el operador puede abortar todo con un botón.

  1. El área (240 × 180 m) se divide en 6 sectores; la asignación minimiza el recorrido desde cada base (húngaro).
  2. Cada dron vuela su grilla en su propia capa de altura (30, 40, … 80 m): 10 m de separación vertical.
  3. A mitad del levantamiento se aprieta "abortar todo": los 6 vuelven a casa (RTL) a su capa y aterrizan.
  4. Juez: monitor del mundo (posición real) → separación mínima 3D en vuelo ≥ 10 m y cada uno en su base.

    SPACING=12 SPAWN_X=-20 SCENE=swarm MODELS=ds_i,ds_i,ds_i,ds_i,ds_i,ds_i MISSION=sector bash tools/sitl/run_gz_multi.sh
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from mavsdk_grpc.mission import MissionItem, MissionPlan

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "sitl"))
from demo_formation import connect, first, offset  # noqa: E402

from control.swarm import formation  # noqa: E402
from control.swarm.analyze_monitor import analyze  # noqa: E402

LAYOUT = ROOT / "simulation" / "xtdrone" / "worlds" / "swarm_layout.json"
AREA = (40.0, 280.0, -40.0, 140.0)        # xmin, xmax (este), ymin, ymax (norte) en el marco del mundo [m]
LAYER0, LAYER_STEP = 30.0, 10.0
LINE_SPACING = 30.0
SPEED = 8.0
MIN_SEP = 10.0


def sectors(n: int, area=AREA) -> list[tuple[float, float, float, float]]:
    cols = math.ceil(n / 2)
    xmin, xmax, ymin, ymax = area
    w, h = (xmax - xmin) / cols, (ymax - ymin) / 2
    return [(xmin + c * w, xmin + (c + 1) * w, ymin + r * h, ymin + (r + 1) * h) for r in range(2) for c in range(cols)][:n]


def lawnmower(sec, spacing=LINE_SPACING) -> list[tuple[float, float]]:
    xmin, xmax, ymin, ymax = sec
    xs = np.arange(xmin + spacing / 2, xmax, spacing)
    pts = []
    for k, x in enumerate(xs):
        pts += [(x, ymin + 5), (x, ymax - 5)] if k % 2 == 0 else [(x, ymax - 5), (x, ymin + 5)]
    return pts


def item(lat, lon, alt):
    return MissionItem(lat, lon, alt, SPEED, True, float("nan"), float("nan"), MissionItem.CameraAction.NONE,
                       float("nan"), float("nan"), 3.0, float("nan"), float("nan"), MissionItem.VehicleAction.NONE)


async def run(n: int, abort_after: float, monitor: Path) -> dict:
    drones = await asyncio.gather(*(connect(i) for i in range(n)))
    homes = [await anext(d.telemetry.home()) for d in drones]
    lat0, lon0 = json.loads(LAYOUT.read_text())["origin_latlon"]       # origen del mundo de Gazebo

    def to_xy(h):
        dn = math.radians(h.latitude_deg - lat0) * 6_378_137.0
        de = math.radians(h.longitude_deg - lon0) * 6_378_137.0 * math.cos(math.radians(lat0))
        return de, dn
    home_xy = np.array([to_xy(h) for h in homes])
    secs = sectors(n)
    centers = np.array([((s[0] + s[1]) / 2, (s[2] + s[3]) / 2) for s in secs])
    perm = formation.assign(home_xy, centers)           # sector de cada dron (minimiza el recorrido)
    # cada uno en su capa (10 m entre capas): cualquier cruce de rutas tiene ≥ 10 m de separación vertical
    layers = {i: LAYER0 + LAYER_STEP * rank for rank, i in enumerate(np.argsort(-np.linalg.norm(centers[perm] - home_xy, axis=1)))}

    for i, d in enumerate(drones):
        alt = layers[i]
        await d.param.set_param_float("RTL_RETURN_ALT", alt)         # el regreso también va por su capa
        await d.param.set_param_float("RTL_DESCEND_ALT", min(alt, 30.0))
        await d.param.set_param_float("MIS_TAKEOFF_ALT", alt)
        pts = lawnmower(secs[perm[i]])
        h = homes[i]
        items = [item(h.latitude_deg, h.longitude_deg, alt)]          # primero sube en vertical sobre su base
        for x, y in pts:
            lat, lon = offset(lat0, lon0, y, x)
            items.append(item(lat, lon, alt))
        await d.mission.set_return_to_launch_after_mission(True)
        await d.mission.upload_mission(MissionPlan(items))
    print("Sectores asignados: " + ", ".join(f"dron {i} → sector {perm[i]} a {layers[i]:.0f} m" for i in range(n)), flush=True)
    await asyncio.sleep(8)
    await asyncio.gather(*(first(d.telemetry.health(), lambda hh: hh.is_armable and hh.is_local_position_ok, 180) for d in drones))

    async def go(d):
        for attempt in range(30):
            try:
                await d.action.arm()
                break
            except Exception:
                if attempt == 29:
                    raise
                await asyncio.sleep(2)
        await d.mission.start_mission()

    await asyncio.gather(*(go(d) for d in drones))
    t0 = time.monotonic()
    print(f"↑ levantamiento en marcha; 'abortar todo' en {abort_after:.0f} s", flush=True)
    await asyncio.sleep(abort_after)
    print("■ ABORTAR TODO: los 6 vuelven a casa", flush=True)
    t_abort = time.monotonic()
    await asyncio.gather(*(d.action.return_to_launch() for d in drones))
    await asyncio.gather(*(first(d.telemetry.armed(), lambda a: not a, 600) for d in drones))
    t_landed = time.monotonic()
    await asyncio.sleep(2)

    m = analyze(monitor) if monitor.exists() else None
    landed_ok = []
    if m:
        for i in range(n):
            pts = m["_tracks"].get(f"{os.environ.get('MODEL', 'ds_i')}_{i}") or []
            if pts:
                landed_ok.append(math.hypot(pts[-1][1] - home_xy[i][0], pts[-1][2] - home_xy[i][1]) < 3.0 and pts[-1][3] < 1.0)
        plot(m, secs, perm, layers, monitor.parent / "sectores.png")
    res = {"n": n, "ok": n, "sectors": [list(map(float, s)) for s in secs], "assignment": [int(p) for p in perm],
           "layers_m": [layers[i] for i in range(n)], "abort_after_s": abort_after,
           "abort_to_all_landed_s": round(t_landed - t_abort, 1), "flight_s": round(t_landed - t0, 1),
           "min_separation_3d_m": m["min_separation_m"] if m else None, "min_separation_pair": m["min_separation_pair"] if m else None,
           "collisions": m["collisions"] if m else None, "all_landed_at_home": bool(landed_ok) and all(landed_ok)}
    res["passed"] = bool(m and res["min_separation_3d_m"] >= MIN_SEP and res["all_landed_at_home"] and res["collisions"] == 0)
    print(("✔" if res["passed"] else "✘") + f" separación mínima {res['min_separation_3d_m']} m (criterio ≥ {MIN_SEP:.0f} m), "
          f"todos en casa {res['abort_to_all_landed_s']} s después de abortar", flush=True)
    return res


def plot(m: dict, secs, perm, layers, png: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 7))
    for k, s in enumerate(secs):
        ax.add_patch(plt.Rectangle((s[0], s[2]), s[1] - s[0], s[3] - s[2], fill=False, ls="--", color="0.5"))
        ax.annotate(f"sector {k}", (s[0] + 3, s[3] - 8), fontsize=8, color="0.4")
    for name, pts in sorted(m["_tracks"].items()):
        i = int(name.rsplit("_", 1)[1])
        ax.plot([p[1] for p in pts], [p[2] for p in pts], lw=1.1, label=f"dron {i} · sector {perm[i]} · {layers[i]:.0f} m")
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc="upper left")
    ax.set_xlabel("este [m]")
    ax.set_ylabel("norte [m]")
    ax.set_title(f"HU-08 · levantamiento por sectores y 'abortar todo'\nseparación mínima 3D {m['min_separation_m']} m "
                 f"(criterio ≥ {MIN_SEP:.0f} m)", fontsize=10)
    fig.tight_layout()
    fig.savefig(png, dpi=120)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--abort-after", type=float, default=90.0, help="segundos de levantamiento antes de abortar")
    ap.add_argument("--hold", type=float, default=0.0, help="(compatibilidad con run_gz_multi.sh)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    res = asyncio.run(run(a.n, a.abort_after, a.out.parent / "monitor.csv"))
    print(json.dumps(res, indent=2, ensure_ascii=False))
    a.out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    os._exit(0 if res["passed"] else 1)           # los streams de gRPC abiertos no dejan terminar al intérprete


if __name__ == "__main__":
    try:
        main()
    except Exception:                                  # sin esto, un error deja colgado el intérprete (streams de gRPC)
        import traceback

        traceback.print_exc()
        sys.stdout.flush()
        os._exit(2)
