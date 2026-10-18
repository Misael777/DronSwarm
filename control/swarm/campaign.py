#!/usr/bin/env python3
"""S06 · Campaña Monte Carlo del enjambre en el simulador cinemático: cada condición con N corridas (semillas
distintas: viento, ruido de GNSS, sombreado de radio, pérdidas). Escribe un JSON por condición y un resumen.

    .venv/bin/python -m control.swarm.campaign --runs 200 --out docs/evidencias/simulacion/enjambre_cinematico
"""

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from control.swarm.sim_kinematic import monte_carlo

CONDITIONS = {
    "consenso_nominal": dict(),
    "consenso_perdida_30": dict(loss=0.3),
    "consenso_perdida_50": dict(loss=0.5),
    "consenso_viento_8": dict(wind=8.0),
    "consenso_wifi_24": dict(radio="wifi_24"),
    "caida_radio_en_transito": dict(drop_out=(2, 20.0)),
    "caida_radio_en_cruce": dict(drop_out=(2, 33.0)),
    "lider_seguidor_nominal": dict(mode="leader"),
    "sin_evitacion": dict(avoidance=False),
}


def figures(out: Path):
    """Vista en planta de una corrida nominal y una con caída de radio, y un GIF animado de la nominal."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter

    from control.swarm.sim_kinematic import run_once

    for name, kw in [("nominal", {}), ("caida_radio_en_cruce", {"drop_out": (2, 33.0)})]:
        r = run_once(seed=0, record=True, **kw)
        tr = r["trajectory"]
        fig, ax = plt.subplots(figsize=(6.5, 8))
        for i in range(r["n"]):
            ax.plot([f["pos"][i][0] for f in tr], [f["pos"][i][1] for f in tr], lw=1.1, label=f"dron {i}")
        for o in r["obstacles"]:
            ax.add_patch(plt.Circle((o["x"], o["y"]), o["radius"], color="0.3"))
            ax.annotate("torre", (o["x"] + 1.5, o["y"]), fontsize=8)
        ax.set_aspect("equal")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7, loc="lower right")
        ax.set_xlabel("este [m]")
        ax.set_ylabel("norte [m]")
        ax.set_title(f"Simulador cinemático · {name.replace('_', ' ')}\nseparación mínima {r['min_separation_m']} m · "
                     f"colisiones {r['collisions']}", fontsize=10)
        fig.tight_layout()
        fig.savefig(out / f"trayectorias_{name}.png", dpi=120)
        plt.close(fig)
        if name != "nominal":
            continue
        frames = tr[::3]
        fig, ax = plt.subplots(figsize=(5, 6.5))
        ax.set_xlim(-25, 25)
        ax.set_ylim(-15, 75)
        ax.set_aspect("equal")
        ax.grid(alpha=0.3)
        for o in r["obstacles"]:
            ax.add_patch(plt.Circle((o["x"], o["y"]), o["radius"], color="0.3"))
        dots = ax.scatter([p[0] for p in frames[0]["pos"]], [p[1] for p in frames[0]["pos"]], s=60,
                          c=[f"C{i}" for i in range(r["n"])])
        title = ax.set_title("")

        def draw(f, dots=dots, title=title):
            dots.set_offsets([p[:2] for p in f["pos"]])
            title.set_text(f"t = {f['t']:.0f} s · fase: {f['phase'].replace('_', ' ')}")
            return dots, title

        FuncAnimation(fig, draw, frames=frames, blit=False).save(out / "enjambre_nominal.gif", writer=PillowWriter(fps=12))
        plt.close(fig)


def _job(item):
    name, kw, runs = item
    return name, monte_carlo(runs, **kw)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=200)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=9)
    ap.add_argument("--figures-only", action="store_true", help="solo las figuras (sin repetir las corridas)")
    a = ap.parse_args()
    if a.figures_only:
        figures(a.out)
        return
    a.out.mkdir(parents=True, exist_ok=True)
    summary = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for name, res in ex.map(_job, [(k, v, a.runs) for k, v in CONDITIONS.items()]):
            (a.out / f"{name}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
            summary[name] = {k: res[k] for k in ("runs", "completed", "runs_with_collision", "collisions_total",
                                                 "min_separation_m", "min_obstacle_clearance_m",
                                                 "formation_error_p95_m_median", "duration_s_median",
                                                 "packet_loss_pct_mean", "latency_ms_p95_mean")}
            print(name, summary[name], flush=True)
    (a.out / "resumen.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    figures(a.out)


if __name__ == "__main__":
    main()
