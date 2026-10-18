#!/usr/bin/env python3
"""S06 · Métricas de seguridad desde el monitor de Gazebo (posición REAL de cada dron, no la estimada por PX4).

Lee el CSV de simulation/plugins/safety/SwarmMonitorSystem: separación mínima entre drones, distancia libre a los
obstáculos, contactos (colisiones) y la vista en planta de las trayectorias.

    .venv/bin/python -m control.swarm.analyze_monitor carpeta/monitor.csv --out carpeta/seguridad.json --png carpeta/trayectorias.png
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def analyze(path: Path) -> dict:
    tracks: dict[str, list[tuple[float, float, float, float]]] = defaultdict(list)
    pair_min: dict[str, tuple[float, float]] = {}
    obst_min: dict[str, tuple[float, float]] = {}
    contacts = []
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0] == "t":
                continue
            t, kind = float(row[0]), row[1]
            if kind == "#pair":
                d = float(row[3])
                if row[2] not in pair_min or d < pair_min[row[2]][0]:
                    pair_min[row[2]] = (d, t)
            elif kind == "#obst":
                d = float(row[3])
                if row[2] not in obst_min or d < obst_min[row[2]][0]:
                    obst_min[row[2]] = (d, t)
            elif kind == "#contact":
                contacts.append({"t": t, "between": row[2]})
            else:
                tracks[kind].append((t, float(row[2]), float(row[3]), float(row[4])))
    worst_pair = min(pair_min.items(), key=lambda kv: kv[1][0]) if pair_min else None
    worst_obst = min(obst_min.items(), key=lambda kv: kv[1][0]) if obst_min else None
    return {
        "drones": sorted(tracks), "samples": sum(len(v) for v in tracks.values()),
        "collisions": len(contacts), "contacts": contacts,
        "min_separation_m": round(worst_pair[1][0], 2) if worst_pair else None,
        "min_separation_pair": worst_pair[0] if worst_pair else None,
        "min_separation_t_s": round(worst_pair[1][1], 1) if worst_pair else None,
        "min_obstacle_clearance_m": round(worst_obst[1][0], 2) if worst_obst else None,
        "max_altitude_m": round(max(p[3] for v in tracks.values() for p in v), 1) if tracks else None,
        "_tracks": tracks,
    }


def plot(res: dict, png: Path, obstacles: list[dict], title: str = ""):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 8))
    for name, pts in sorted(res["_tracks"].items()):
        ax.plot([p[1] for p in pts], [p[2] for p in pts], lw=1.2, label=name)
        ax.plot(pts[0][1], pts[0][2], "o", ms=4, color=ax.lines[-1].get_color())
    for o in obstacles:
        ax.add_patch(plt.Circle((o["x"], o["y"]), o["radius"], color="0.3"))
        ax.annotate(o["name"].replace("_", " "), (o["x"] + o["radius"] + 1, o["y"]), fontsize=8)
    ax.set_aspect("equal")
    ax.set_xlabel("este [m]")
    ax.set_ylabel("norte [m]")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc="lower right")
    sep = res["min_separation_m"]
    ax.set_title(f"{title}\nseparación mínima {sep} m · colisiones {res['collisions']}", fontsize=10)
    fig.tight_layout()
    fig.savefig(png, dpi=120)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--png", type=Path)
    ap.add_argument("--layout", type=Path, default=Path(__file__).resolve().parents[2] / "simulation/xtdrone/worlds/swarm_layout.json")
    ap.add_argument("--title", default="Enjambre en PX4 + Gazebo (posición real)")
    a = ap.parse_args()
    res = analyze(a.csv)
    if a.png:
        obst = json.loads(a.layout.read_text())["obstacles"] if a.layout.exists() else []
        plot(res, a.png, obst, a.title)
    out = {k: v for k, v in res.items() if not k.startswith("_")}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if a.out:
        a.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
