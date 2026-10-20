#!/usr/bin/env python3
"""S13-01 · Enjambre DISTRIBUIDO en SITL: N procesos nodo (uno por dron, como en las computadoras a bordo) + la
estación de tierra, comunicándose por UDP multicast con la radio del S06 emulada en cada receptor.

    SCENE=swarm MODELS=ds_i,ds_i,ds_i,ds_i,ds_i,ds_i MISSION=swarm_dist bash tools/sitl/run_gz_multi.sh
    MISSION_ARGS="--loss 0.3 --drop-out 2:40" ...       # 30 % de pérdida; el dron 2 pierde la radio a los 40 s
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--alt", type=float, default=10.0)
    ap.add_argument("--loss", type=float, default=0.0)
    ap.add_argument("--radio", default="mesh_900")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--drop-out", help="dron:segundo")
    ap.add_argument("--hold", type=float, default=0.0, help="(compatibilidad con run_gz_multi.sh)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    work = a.out.parent
    drop = tuple(a.drop_out.split(":")) if a.drop_out else None
    nodes = []
    for i in range(a.n):
        cmd = [PY, str(ROOT / "control/swarm/node.py"), "--id", str(i), "--emulate", "--radio", a.radio,
               "--loss", str(a.loss), "--seed", str(a.seed), "--log", str(work / f"nodo_{i}.json"),
               "--transport", "local", "--n-nodes", str(a.n)]
        if drop and int(drop[0]) == i:
            cmd += ["--drop-out", drop[1]]
        nodes.append(subprocess.Popen(cmd, stdout=open(work / f"nodo_{i}.log", "w"), stderr=subprocess.STDOUT))
    time.sleep(2)
    gcs_out = work / "tierra.json"
    rc = subprocess.run([PY, str(ROOT / "control/swarm/gcs.py"), "--n", str(a.n), "--alt", str(a.alt), "--out", str(gcs_out),
                         "--transport", "local"],
                        timeout=1800).returncode
    for p in nodes:
        try:
            p.wait(timeout=300)
        except subprocess.TimeoutExpired:
            p.kill()
    res = json.loads(gcs_out.read_text()) if gcs_out.exists() else {"completed": False}
    logs = [json.loads((work / f"nodo_{i}.json").read_text()) for i in range(a.n) if (work / f"nodo_{i}.json").exists()]
    sent = sum(x["sent"] for x in logs)
    res.update({"ok": len(res.get("landed", [])), "distributed": True, "nodes_with_log": len(logs),
                "radio": {"model": a.radio, "extra_loss": a.loss, "packets_sent": sent,
                          "dropped_by_radio": sum(x["dropped_by_radio"] for x in logs)},
                "nodes": [{k: x.get(k) for k in ("id", "lost_link", "min_neighbors", "dropped_by_radio", "ground_timeout")}
                          for x in logs],
                "drop_out": a.drop_out})
    a.out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k not in ("phases", "nodes")}, indent=2, ensure_ascii=False))
    sys.stdout.flush()
    # nadie se fue a RTL por falta de tierra (salvo el dron al que se le cortó la radio a propósito: eso debe hacer)
    flew = len(logs) == a.n and not any(x.get("ground_timeout") for x in logs if not drop or x["id"] != int(drop[0]))
    res["passed"] = bool(res.get("completed") and rc == 0 and flew and res["ok"] == a.n)
    a.out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    os._exit(0 if res["passed"] else 1)


if __name__ == "__main__":
    main()
