#!/usr/bin/env python3
"""S06-01/02/03 · Simulador cinemático rápido del enjambre (Monte Carlo).

Cada dron es un punto con la respuesta de velocidad de un multirotor (primer orden, τ = 0.6 s, aceleración máxima
4 m/s²), viento con ráfagas (proceso de Ornstein-Uhlenbeck) y ruido de GNSS en lo que transmite. Los estados de los
vecinos llegan por el modelo de radio (simulation/common/comms_model.py): con retardo, pérdidas y alcance.

No reemplaza a PX4 + Gazebo (dinámica completa, autopiloto real); sirve para probar cientos de corridas en minutos,
ajustar ganancias y buscar casos raros. La validación final del criterio "0 colisiones en 20 corridas" se hace en
SITL (`sitl_swarm.py`).

    .venv/bin/python -m control.swarm.sim_kinematic --runs 200 --loss 0.2 --out docs/evidencias/simulacion/enjambre
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from control.swarm.avoidance import AvoidParams
from control.swarm.consensus import NeighborState
from control.swarm.swarm import Agent, Scenario
from simulation.common.comms_model import RADIOS, CommsModel

BODY_RADIUS = 0.55                         # DS-I: semieje + radio de hélice 17" (punta a punta 1.1 m)


def run_once(n: int = 6, seed: int = 0, mode: str = "consensus", radio: str = "mesh_900", loss: float = 0.0,
             wind: float = 3.0, gnss_sigma: float = 0.3, avoidance: bool = True, dt: float = 0.05,
             ctrl_hz: float = 10.0, alt: float = 10.0, spawn_spacing: float = 3.0, drop_out: tuple | None = None,
             avoid_params: dict | None = None, record: bool = False) -> dict:
    """Una corrida completa del escenario. drop_out = (dron, t_s): ese dron pierde la radio a esa hora."""
    rng = np.random.default_rng(seed)
    net = CommsModel(RADIOS[radio], n_nodes=n, seed=seed + 1000, extra_loss=loss)
    sc = Scenario(n)
    agents = [Agent(i, mode=mode, use_avoidance=avoidance, avoid=AvoidParams(**(avoid_params or {}))) for i in range(n)]
    pos = np.column_stack([np.zeros(n), (np.arange(n) - (n - 1) / 2) * spawn_spacing, np.full(n, alt)])
    pos[:, :2] += rng.normal(0, 0.2, (n, 2))
    vel = np.zeros((n, 3))
    cmd = np.zeros((n, 3))
    gust = np.zeros(2)
    tau, a_max = 0.6, 4.0
    wind_dir = rng.uniform(0, 2 * math.pi)
    wind_mean = wind * np.array([math.cos(wind_dir), math.sin(wind_dir)])
    t, t_ctrl, t_end = 0.0, 0.0, sum(p.timeout_s for p in sc.phases) + 30
    sc.start(t, pos)
    min_sep, min_obst, collisions, traj = np.inf, np.inf, 0, []
    in_contact: set[tuple[int, int]] = set()
    form_err = []
    while not sc.done and t < t_end:
        # radio: cada dron difunde su estado a 10 Hz
        if t >= t_ctrl:
            meas = pos + np.column_stack([rng.normal(0, gnss_sigma, (n, 2)), rng.normal(0, gnss_sigma / 2, n)])
            positions = {i: tuple(pos[i]) for i in range(n)}
            if drop_out and t >= drop_out[1]:
                net.down.add(drop_out[0])
            for i in range(n):
                st = NeighborState(meas[i].copy(), vel[i].copy(), sc.slots[i].copy(), t, is_leader=(i == 0))
                net.broadcast(i, t, positions, st)
            for m in net.deliver(t):
                agents[m.dst].receive(m.src, m.payload)
            alive = np.array([not a.lost for a in agents])
            ref, ref_vel = sc.update(t, 1 / ctrl_hz, pos, alive)
            for i in range(n):
                cmd[i], _ = agents[i].command(t, meas[i], vel[i], sc.slots[i], ref, ref_vel, alt, sc.obstacles)
            if t - sc.t_phase > 10.0:                              # tramos estables, no justo tras cambiar de forma
                form_err.append(sc.formation_error(pos, alive))
            t_ctrl += 1 / ctrl_hz
        else:
            for m in net.deliver(t):
                agents[m.dst].receive(m.src, m.payload)
        # dinámica
        gust += (-gust / 3.0) * dt + 0.6 * wind * math.sqrt(dt) * rng.normal(0, 1, 2) / 3
        acc = (cmd - vel) / tau
        an = np.linalg.norm(acc[:, :2], axis=1, keepdims=True)
        acc[:, :2] *= np.minimum(1.0, a_max / np.maximum(an, 1e-9))
        vel += acc * dt
        pos += vel * dt
        pos[:, :2] += 0.08 * (wind_mean + gust) * dt          # el viento que el controlador no compensa al instante
        # métricas con la posición REAL
        d = np.linalg.norm(pos[:, None, :] - pos[None, :, :], axis=2)
        iu = np.triu_indices(n, 1)
        min_sep = min(min_sep, float(d[iu].min()))
        for a, b in zip(*iu):
            touching = d[a, b] < 2 * BODY_RADIUS
            if touching and (a, b) not in in_contact:
                collisions += 1
            (in_contact.add if touching else in_contact.discard)((a, b))
        for k, ob in enumerate(sc.obstacles):
            c = np.linalg.norm(pos[:, :2] - np.array([ob.x, ob.y]), axis=1) - ob.radius - BODY_RADIUS
            min_obst = min(min_obst, float(c.min()))
            for i in range(n):                                    # un choque por contacto, no por paso
                if c[i] < 0 and (i, -1 - k) not in in_contact:
                    collisions += 1
                (in_contact.add if c[i] < 0 else in_contact.discard)((i, -1 - k))
        if record and int(t / dt) % 4 == 0:
            traj.append({"t": round(t, 2), "pos": pos.round(2).tolist(), "phase": sc.phase.name if sc.phase else "fin"})
        t += dt
    res = {"seed": seed, "mode": mode, "n": n, "loss_extra": loss, "wind_m_s": wind, "avoidance": avoidance,
           "completed": sc.done, "duration_s": round(t, 1), "min_separation_m": round(min_sep, 2),
           "min_obstacle_clearance_m": round(min_obst, 2), "collisions": collisions,
           "formation_error_p50_m": round(float(np.median(form_err)), 2) if form_err else None,
           "formation_error_p95_m": round(float(np.percentile(form_err, 95)), 2) if form_err else None,
           "phases": sc.log, "comms": net.summary()}
    if record:
        res["trajectory"] = traj
        res["obstacles"] = [vars(o) for o in sc.obstacles]
    return res


def monte_carlo(runs: int, **kw) -> dict:
    rs = [run_once(seed=s, **kw) for s in range(runs)]
    seps = [r["min_separation_m"] for r in rs]
    return {"runs": runs, "config": {k: v for k, v in kw.items() if k != "record"},
            "completed": sum(r["completed"] for r in rs), "collisions_total": sum(r["collisions"] for r in rs),
            "runs_with_collision": sum(r["collisions"] > 0 for r in rs),
            "min_separation_m": {"min": min(seps), "p5": round(float(np.percentile(seps, 5)), 2), "median": round(float(np.median(seps)), 2)},
            "min_obstacle_clearance_m": min(r["min_obstacle_clearance_m"] for r in rs),
            "formation_error_p95_m_median": round(float(np.median([r["formation_error_p95_m"] for r in rs])), 2),
            "duration_s_median": round(float(np.median([r["duration_s"] for r in rs])), 1),
            "packet_loss_pct_mean": round(float(np.mean([r["comms"]["packet_loss_pct"] for r in rs])), 1),
            "latency_ms_p95_mean": round(float(np.mean([r["comms"]["latency_ms_p95"] for r in rs])), 1)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=100)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--mode", choices=["consensus", "leader"], default="consensus")
    ap.add_argument("--radio", choices=list(RADIOS), default="mesh_900")
    ap.add_argument("--loss", type=float, default=0.0, help="pérdida extra de paquetes (0-1)")
    ap.add_argument("--wind", type=float, default=3.0)
    ap.add_argument("--no-avoidance", action="store_true")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    res = monte_carlo(a.runs, n=a.n, mode=a.mode, radio=a.radio, loss=a.loss, wind=a.wind, avoidance=not a.no_avoidance)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
