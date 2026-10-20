#!/usr/bin/env python3
"""S13-01 · Estación de tierra del enjambre: secuencia la misión y difunde la referencia. NO controla los drones.

Escucha los STATE de los nodos, corre el `Scenario` del S06 (formar V → tránsito con torre → círculo → cruce →
regreso en línea) y difunde a 10 Hz la referencia en el marco del mundo: centro de la formación, su velocidad, el
puesto de cada dron y los obstáculos. Cada nodo decide su propia velocidad.

    .venv/bin/python control/swarm/gcs.py --n 6 --alt 10 --out resultado.json
    Ctrl+C = ABORTAR TODO (los drones hacen RTL)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import signal
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from control.swarm.avoidance import Obstacle  # noqa: E402
from control.swarm.net import Bus  # noqa: E402
from control.swarm.swarm import Scenario  # noqa: E402

RATE_HZ = 10.0
STALE_S = 3.0


async def run(n: int, alt: float, timeout_ready: float, layout: Path, transport: str = "multicast") -> dict:
    bus = Bus(-1, transport=transport, n_nodes=n)
    lay = json.loads(layout.read_text())
    states: dict[int, dict] = {}
    acks: dict[str, set] = {"airborne": set(), "landed": set()}
    abort = {"flag": False}
    signal.signal(signal.SIGINT, lambda *_: abort.update(flag=True))
    signal.signal(signal.SIGTERM, lambda *_: abort.update(flag=True))

    def pump():
        for m in bus.poll():
            if m["k"] == "STATE":
                states[m["src"]] = {**m, "rx": time.time()}
            elif m["k"] == "ACK":
                acks.setdefault(m["what"], set()).add(m["src"])

    print(f"[tierra] esperando a {n} drones…", flush=True)
    t0 = time.time()
    while len([s for s in states.values() if s.get("ready")]) < n:
        pump()
        if time.time() - t0 > timeout_ready:
            raise SystemExit(f"solo {len(states)} de {n} drones listos")
        await asyncio.sleep(0.2)
    print("[tierra] START", flush=True)
    for _ in range(5):
        bus.send("CMD", cmd="START", alt=alt)
        await asyncio.sleep(0.1)
    while len(acks["airborne"]) < n and not abort["flag"]:            # los que ya despegaron esperan en hover
        pump()
        bus.send("CMD", cmd="WAIT")                                   # latido: el enlace con tierra sigue vivo
        await asyncio.sleep(0.5)
    # todos a la altura de trabajo antes de empezar (los nodos suben solos con la referencia)
    pos = np.array([states[i]["pos"] for i in range(n)])
    origin = pos[:, :2].mean(axis=0)
    obst_w = [Obstacle(o["x"], o["y"], o["radius"], o["height"]) for o in lay["obstacles"]]
    sc = Scenario(n, obstacles=[Obstacle(o.x - origin[0], o.y - origin[1], o.radius, o.height) for o in obst_w])
    sc.start(0.0, pos - np.array([*origin, 0]))
    t_start, last_phase, form_err = time.time(), None, []
    timeout = sum(p.timeout_s for p in sc.phases) + 60
    while not sc.done and not abort["flag"] and time.time() - t_start < timeout:
        t = time.time() - t_start
        pump()
        now = time.time()
        alive = np.array([i in states and now - states[i]["rx"] < STALE_S and not states[i].get("lost") for i in range(n)])
        pos = np.array([states[i]["pos"] for i in range(n)]) - np.array([*origin, 0])
        ref, ref_vel = sc.update(t, 1 / RATE_HZ, pos, alive)
        if sc.phase and sc.phase.name != last_phase:
            last_phase = sc.phase.name
            print(f"[tierra] fase {last_phase} (t={t:.0f} s)", flush=True)
        bus.send("REF", phase=sc.phase.name if sc.phase else "fin", ref=[*(ref + origin).round(3).tolist()],
                 ref_vel=[*np.asarray(ref_vel).round(3).tolist()], slots=sc.slots.round(3).tolist(), alt=alt,
                 obstacles=[[o.x, o.y, o.radius, o.height] for o in obst_w])
        if t - sc.t_phase > 10.0:
            form_err.append(sc.formation_error(pos, alive))
        await asyncio.sleep(max(0.0, 1 / RATE_HZ - (time.time() - now)))
    cmd = "ABORT" if abort["flag"] else "LAND"
    print(f"[tierra] {cmd}", flush=True)
    t_end = time.time()
    while len(acks["landed"]) < len([1 for i in range(n) if i in states]) and time.time() - t_end < 240:
        bus.send("CMD", cmd=cmd)
        pump()
        await asyncio.sleep(0.5)
    res = {"n": n, "completed": sc.done, "aborted": abort["flag"], "duration_s": round(t_end - t_start, 1),
           "phases": sc.log, "formation_error_p50_m": round(float(np.median(form_err)), 2) if form_err else None,
           "formation_error_p95_m": round(float(np.percentile(form_err, 95)), 2) if form_err else None,
           "landed": sorted(acks["landed"]), "lost_link": sorted(i for i, s in states.items() if s.get("lost"))}
    bus.close()
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--alt", type=float, default=10.0)
    ap.add_argument("--ready-timeout", type=float, default=300)
    ap.add_argument("--layout", type=Path, default=ROOT / "simulation/xtdrone/worlds/swarm_layout.json")
    ap.add_argument("--transport", choices=["multicast", "local"], default="multicast")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    res = asyncio.run(run(a.n, a.alt, a.ready_timeout, a.layout, a.transport))
    print(json.dumps({k: v for k, v in res.items() if k != "phases"}, indent=2, ensure_ascii=False))
    if a.out:
        a.out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
