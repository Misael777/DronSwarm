#!/usr/bin/env python3
"""S06-01/02/03 · Enjambre en PX4 + Gazebo: el mismo control del simulador cinemático, ahora con autopilotos reales.

Cada dron recibe órdenes de velocidad por MAVSDK (offboard, 10 Hz). Los estados que cada dron conoce de sus vecinos
pasan por el modelo de radio (retardo, pérdidas, alcance); la posición propia es la que estima PX4 (GNSS + IMU).
La estación de tierra solo secuencia las fases (formar V → tránsito → círculo → cruce → regreso en línea).
El árbitro de colisiones es el monitor del mundo (posición real de Gazebo), no este script.

    SCENE=swarm MODEL=ds_i MISSION=swarm bash tools/sitl/run_gz_multi.sh 6 [carpeta]
    MISSION_ARGS="--loss 0.3 --drop-out 2:40" SCENE=swarm MODEL=ds_i MISSION=swarm bash tools/sitl/run_gz_multi.sh 6
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
from mavsdk_grpc.offboard import OffboardError, VelocityNedYaw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "sitl"))
from demo_formation import EARTH_R, connect, first  # noqa: E402

from control.swarm.avoidance import Obstacle  # noqa: E402
from control.swarm.consensus import NeighborState  # noqa: E402
from control.swarm.swarm import Agent, Scenario  # noqa: E402
from simulation.common.comms_model import RADIOS, CommsModel  # noqa: E402

LAYOUT = ROOT / "simulation" / "xtdrone" / "worlds" / "swarm_layout.json"


def enu(origin: tuple[float, float], lat: float, lon: float) -> tuple[float, float]:
    x = math.radians(lon - origin[1]) * EARTH_R * math.cos(math.radians(origin[0]))
    y = math.radians(lat - origin[0]) * EARTH_R
    return x, y


class Telemetry:
    """Último estado de cada dron (posición ENU en el marco del mundo y velocidad)."""

    def __init__(self, n: int, origin):
        self.origin = origin
        self.pos = np.zeros((n, 3))
        self.vel = np.zeros((n, 3))
        self.ok = np.zeros(n, dtype=bool)

    async def track(self, i: int, d):
        async def _pos():
            async for p in d.telemetry.position():
                x, y = enu(self.origin, p.latitude_deg, p.longitude_deg)
                self.pos[i] = (x, y, p.relative_altitude_m)
                self.ok[i] = True

        async def _vel():
            async for pv in d.telemetry.position_velocity_ned():
                v = pv.velocity
                self.vel[i] = (v.east_m_s, v.north_m_s, -v.down_m_s)

        await asyncio.gather(_pos(), _vel())


async def arm_and_takeoff(d, alt: float, tries: int = 3):
    """Arma y despega; con varias instancias PX4 a veces rechaza el despegue al arrancar: se reintenta."""
    await first(d.telemetry.health(), lambda h: h.is_armable and h.is_local_position_ok, 180)
    await d.action.set_takeoff_altitude(alt)
    for k in range(tries):
        if not await anext(d.telemetry.armed()):        # tras un despegue fallido puede seguir armado
            await first(d.telemetry.health(), lambda h: h.is_armable, 90)
            for attempt in range(30):
                try:
                    await d.action.arm()
                    break
                except Exception:
                    if attempt == 29:
                        raise
                    await asyncio.sleep(2)
        try:
            await d.action.takeoff()
            await first(d.telemetry.position(), lambda p: p.relative_altitude_m >= 2.0, 45)
            return
        except Exception:
            if k == tries - 1:
                raise
            print("   un dron no despegó: reintento", flush=True)
            await asyncio.sleep(12)                    # PX4 lo desarma solo si quedó armado en tierra


async def run(n: int, alt: float, mode: str, radio: str, loss: float, drop_out: tuple[int, float] | None,
              seed: int) -> dict:
    layout = json.loads(LAYOUT.read_text())
    origin = tuple(layout["origin_latlon"])
    drones = await asyncio.gather(*(connect(i) for i in range(n)))
    tel = Telemetry(n, origin)
    for i, d in enumerate(drones):
        await d.telemetry.set_rate_position(10)
        await d.telemetry.set_rate_position_velocity_ned(10)
        asyncio.ensure_future(tel.track(i, d))
    await asyncio.sleep(8)                                       # convergencia del estimador
    print(f"↑ despegue de {n} drones", flush=True)
    await asyncio.gather(*(arm_and_takeoff(d, alt) for d in drones))

    # Offboard por velocidad: hay que enviar una consigna antes de arrancar
    for d in drones:
        await d.offboard.set_velocity_ned(VelocityNedYaw(0, 0, 0, 0))
    for d in drones:
        for attempt in range(5):
            try:
                await d.offboard.start()
                break
            except OffboardError:
                if attempt == 4:
                    raise
                await asyncio.sleep(1)

    origin_m = tel.pos[:, :2].mean(axis=0)                       # el escenario se define respecto del centro inicial
    obstacles = [Obstacle(o["x"] - origin_m[0], o["y"] - origin_m[1], o["radius"], o["height"]) for o in layout["obstacles"]]
    sc = Scenario(n, obstacles=obstacles)
    agents = [Agent(i, mode=mode) for i in range(n)]
    net = CommsModel(RADIOS[radio], n_nodes=n, seed=seed, extra_loss=loss)

    # subir a la altura de trabajo antes de empezar
    print(f"↑ todos a {alt:.0f} m", flush=True)
    t_climb = time.monotonic()
    while (tel.pos[:, 2] < alt - 0.7).any() and time.monotonic() - t_climb < 40:
        await asyncio.gather(*(d.offboard.set_velocity_ned(VelocityNedYaw(0, 0, -1.5 if tel.pos[i, 2] < alt else 0, 0))
                               for i, d in enumerate(drones)))
        await asyncio.sleep(0.1)

    t0 = time.monotonic()
    t = 0.0
    sc.start(t, tel.pos - np.array([*origin_m, 0]))
    form_err, last_phase = [], None
    timeout = sum(p.timeout_s for p in sc.phases) + 60
    while not sc.done and t < timeout:
        t = time.monotonic() - t0
        pos = tel.pos - np.array([*origin_m, 0])                 # marco de la misión
        vel = tel.vel.copy()
        if drop_out and t >= drop_out[1] and drop_out[0] not in net.down:
            net.down.add(drop_out[0])
            print(f"✖ dron {drop_out[0]} pierde la radio (t={t:.0f} s)", flush=True)
        positions = {i: tuple(pos[i]) for i in range(n)}
        for i in range(n):
            st = NeighborState(pos[i].copy(), vel[i].copy(), sc.slots[i].copy(), t, is_leader=(i == 0))
            net.broadcast(i, t, positions, st)
        for m in net.deliver(t + 1e-3):
            agents[m.dst].receive(m.src, m.payload)
        alive = np.array([not a.lost for a in agents])
        ref, ref_vel = sc.update(t, 0.1, pos, alive)
        if sc.phase and sc.phase.name != last_phase:
            last_phase = sc.phase.name
            print(f"→ fase {last_phase} (t={t:.0f} s)", flush=True)
        cmds = []
        for i in range(n):
            v, _ = agents[i].command(t, pos[i], vel[i], sc.slots[i], ref, ref_vel, alt, sc.obstacles)
            cmds.append(drones[i].offboard.set_velocity_ned(VelocityNedYaw(v[1], v[0], -v[2], 0)))
        await asyncio.gather(*cmds)
        if t - sc.t_phase > 10.0:
            form_err.append(sc.formation_error(pos, alive))
        await asyncio.sleep(max(0.0, 0.1 - (time.monotonic() - t0 - t)))

    print("↓ aterrizaje", flush=True)
    for d in drones:
        try:
            await d.offboard.stop()
        except OffboardError:
            pass
    await asyncio.gather(*(d.action.land() for d in drones))
    await asyncio.gather(*(first(d.telemetry.armed(), lambda a: not a, 180) for d in drones))
    res = {"n": n, "ok": n, "mode": mode, "radio": radio, "loss_extra": loss, "drop_out": drop_out,
           "completed": sc.done, "duration_s": round(t, 1), "phases": sc.log,
           "formation_error_p50_m": round(float(np.median(form_err)), 2) if form_err else None,
           "formation_error_p95_m": round(float(np.percentile(form_err, 95)), 2) if form_err else None,
           "lost_link_agents": [a.i for a in agents if a.lost], "comms": net.summary(),
           "mission_origin_world_m": [round(float(v), 2) for v in origin_m]}
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--alt", type=float, default=10.0)
    ap.add_argument("--mode", choices=["consensus", "leader"], default="consensus")
    ap.add_argument("--radio", choices=list(RADIOS), default="mesh_900")
    ap.add_argument("--loss", type=float, default=0.0)
    ap.add_argument("--drop-out", help="dron:segundo — ese dron pierde la radio a esa hora de la misión")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--hold", type=float, default=0.0, help="(compatibilidad con run_gz_multi.sh)")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    drop = tuple(float(x) for x in a.drop_out.split(":")) if a.drop_out else None
    drop = (int(drop[0]), drop[1]) if drop else None
    res = asyncio.run(run(a.n, a.alt, a.mode, a.radio, a.loss, drop, a.seed))
    print(json.dumps({k: v for k, v in res.items() if k != "phases"}, indent=2, ensure_ascii=False))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    os._exit(0 if res["completed"] else 1)        # los streams de gRPC abiertos no dejan terminar al intérprete


if __name__ == "__main__":
    try:
        main()
    except Exception:                                  # sin esto, un error deja colgado el intérprete (streams de gRPC)
        import traceback

        traceback.print_exc()
        sys.stdout.flush()
        os._exit(2)
