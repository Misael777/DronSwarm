#!/usr/bin/env python3
"""S06 · Campaña del enjambre en PX4 + Gazebo: N corridas seguidas (NUNCA superpuestas) y un resumen.

Cada corrida usa otra semilla para la radio simulada; algunas con pérdida de paquetes o con un dron que se queda sin
radio. El juez es el monitor del mundo (posición real de Gazebo): `seguridad.json` de cada corrida.

    .venv/bin/python -m control.swarm.sitl_campaign --nominal 14 --loss 3 --dropout 3 --out docs/evidencias/simulacion/enjambre_sitl
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "logs" / "s06-campana"


def idle() -> bool:
    px4 = subprocess.run(["pgrep", "-x", "px4"], capture_output=True).returncode != 0
    # patrón anclado: "-f" también ve la línea de comandos de los shells que contienen este texto
    runs = subprocess.run(["pgrep", "-f", r"^bash .*run_gz_multi\.sh"], capture_output=True).returncode != 0
    return px4 and runs


def run(k: int, name: str, args: str, model: str) -> dict:
    out = RUNS_DIR / f"{k:02d}_{name}"
    out.mkdir(parents=True, exist_ok=True)
    while not idle():                                   # nunca dos simulaciones a la vez
        time.sleep(5)
    env = dict(os.environ, SCENE="swarm", MODELS=",".join([model] * 6), MISSION_ARGS=args)
    t0 = time.monotonic()
    with open(out / "consola.log", "w") as log:
        rc = subprocess.run(["bash", str(ROOT / "tools/sitl/run_gz_multi.sh"), "6", str(out)], env=env, stdout=log,
                            stderr=subprocess.STDOUT, timeout=1500).returncode
    res = {"run": k, "name": name, "args": args, "rc": rc, "wall_s": round(time.monotonic() - t0)}
    for f, keys in [("seguridad.json", ("collisions", "min_separation_m", "min_separation_pair", "min_obstacle_clearance_m")),
                    ("takeoff.json", ("completed", "duration_s", "formation_error_p95_m", "lost_link_agents")),
                    ("resources.json", ("rtf_median",))]:
        p = out / f
        if p.exists():
            d = json.loads(p.read_text())
            res |= {k2: d.get(k2) for k2 in keys}
            if f == "takeoff.json":
                res["packet_loss_pct"] = d.get("comms", {}).get("packet_loss_pct")
    print(json.dumps(res, ensure_ascii=False), flush=True)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nominal", type=int, default=14)
    ap.add_argument("--loss", type=int, default=3, help="corridas con 30 % de pérdida de paquetes")
    ap.add_argument("--dropout", type=int, default=3, help="corridas con un dron que pierde la radio en el cruce")
    ap.add_argument("--model", default="ds_i")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    plan = [("nominal", f"--seed {s}") for s in range(a.nominal)]
    plan += [("perdida30", f"--seed {100 + s} --loss 0.3") for s in range(a.loss)]
    plan += [("caida_radio", f"--seed {200 + s} --drop-out {2 + s}:45") for s in range(a.dropout)]
    results = [run(k, name, args, a.model) for k, (name, args) in enumerate(plan)]
    ok = [r for r in results if r.get("collisions") is not None]
    summary = {
        "runs": len(results), "runs_with_metrics": len(ok), "completed": sum(bool(r.get("completed")) for r in results),
        "runs_with_collision": sum(r["collisions"] > 0 for r in ok), "collisions_total": sum(r["collisions"] for r in ok),
        "min_separation_m": min((r["min_separation_m"] for r in ok if r["min_separation_m"] is not None), default=None),
        "min_obstacle_clearance_m": min((r["min_obstacle_clearance_m"] for r in ok if r["min_obstacle_clearance_m"] is not None), default=None),
        "rtf_median": sorted(r["rtf_median"] for r in ok if r.get("rtf_median"))[len(ok) // 2] if ok else None,
        "model": a.model, "runs_detail": results,
    }
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "resumen.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "runs_detail"}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
