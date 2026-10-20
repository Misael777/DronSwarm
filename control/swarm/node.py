#!/usr/bin/env python3
"""S13-01 · Nodo del enjambre: corre en la computadora a bordo de CADA dron (en SITL, un proceso por dron).

Habla con su PX4 por MAVSDK (SITL: UDP; dron real: serie TELEM2 de la Pixhawk), difunde su estado a 10 Hz, recibe los
de sus vecinos y la referencia de la estación de tierra (net.py), y comanda velocidad en offboard con el MISMO
`Agent` del S06 (formación por consenso + evitación + protocolo de pérdida de radio).

Seguridad (independiente de la estación de tierra):
  - sin referencia de tierra por 2 s → se detiene (hover); sin ningún mensaje de tierra por 10 s → RTL y el nodo termina;
  - si el nodo muere, PX4 detecta la pérdida de offboard (COM_OF_LOSS_T) y hace su failsafe (COM_OBL_RC_ACT);
  - CMD ABORT de tierra → RTL inmediato (botón "abortar todo" de la HU-08).

    # SITL (lo lanza control/swarm/dist_launch.py):
    .venv/bin/python control/swarm/node.py --id 0 --connect udpin://0.0.0.0:14540
    # dron real (Raspberry Pi):
    python3 control/swarm/node.py --id 3 --connect serial:///dev/ttyAMA0:921600 --origin -9.53,-77.05
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "sitl"))

from control.swarm.avoidance import Obstacle  # noqa: E402
from control.swarm.consensus import NeighborState  # noqa: E402
from control.swarm.net import Bus, Emulation, as_np, enu  # noqa: E402
from control.swarm.swarm import Agent  # noqa: E402

REF_HOLD_S, REF_RTL_S = 2.0, 10.0
RATE_HZ = 10.0


class Node:
    def __init__(self, a):
        self.a = a
        self.id = a.id
        self.origin = tuple(float(x) for x in a.origin.split(","))
        self.bus = Bus(a.id, emulation=Emulation(a.radio, a.loss, a.seed + a.id) if a.emulate else None,
                       transport=a.transport, n_nodes=a.n_nodes)
        self.agent = Agent(a.id)
        self.pos = np.zeros(3)
        self.vel = np.zeros(3)
        self.have_pos = False
        self.ref: dict | None = None
        self.ref_rx = 0.0
        self.ground_rx = 0.0                                  # último mensaje de tierra (cualquiera): vigilancia del enlace
        self.cmd: dict | None = None
        self.radio_down = False
        self.log = {"id": a.id, "events": [], "min_neighbors": None, "ground_timeout": False}

    def event(self, txt: str):
        self.log["events"].append([round(time.time(), 2), txt])
        print(f"[dron {self.id}] {txt}", flush=True)

    async def connect(self):
        from demo_formation import first
        from mavsdk_grpc import System
        self.d = System(port=self.a.grpc_port)
        await self.d.connect(system_address=self.a.connect)
        await first(self.d.core.connection_state(), lambda s: s.is_connected, 90)
        await first(self.d.telemetry.health(), lambda h: h.is_global_position_ok and h.is_home_position_ok, 180)
        await self.d.telemetry.set_rate_position(RATE_HZ)
        await self.d.telemetry.set_rate_position_velocity_ned(RATE_HZ)
        asyncio.ensure_future(self._track())

    async def _track(self):
        async def pos():
            async for p in self.d.telemetry.position():
                x, y = enu(self.origin, p.latitude_deg, p.longitude_deg)
                self.pos = np.array([x, y, p.relative_altitude_m])
                self.have_pos = True
                self.bus.own_pos = tuple(self.pos)

        async def vel():
            async for pv in self.d.telemetry.position_velocity_ned():
                v = pv.velocity
                self.vel = np.array([v.east_m_s, v.north_m_s, -v.down_m_s])

        await asyncio.gather(pos(), vel())

    def pump(self, feed_agent: bool = True):
        """Procesa los mensajes recibidos. Antes del vuelo no se alimenta al Agent: su protocolo de pérdida de radio
        tomaría el silencio del despegue (20-60 s sin leer) como radio caída."""
        if self.radio_down:
            self.bus.poll()                                   # se descartan: la radio está caída
            return
        for m in self.bus.poll():
            if m["src"] == -1:
                self.ground_rx = time.time()
            if m["k"] == "STATE" and feed_agent:
                self.agent.receive(m["src"], NeighborState(as_np(m["pos"]), as_np(m["vel"]), as_np(m["slot"]), m["t"]))
            elif m["k"] == "REF":
                self.ref, self.ref_rx = m, time.time()
            elif m["k"] == "CMD" and m["cmd"] != "WAIT" and m.get("to") in (None, self.id):
                self.cmd = m

    def beat(self):
        """Latido para el watchdog (control/mavsdk_nodes/watchdog.py)."""
        if self.a.heartbeat:
            self.a.heartbeat.write_text(f"{time.time():.3f}\n")

    def broadcast(self, slot):
        if not self.radio_down:
            self.bus.send("STATE", pos=[round(float(x), 3) for x in self.pos], vel=[round(float(x), 3) for x in self.vel],
                          slot=[round(float(x), 3) for x in slot], lost=self.agent.lost, ready=self.have_pos)

    async def run(self):
        from mavsdk_grpc.offboard import OffboardError, VelocityNedYaw

        from control.swarm.sitl_swarm import arm_and_takeoff
        await self.connect()
        slot = np.zeros(2)
        alt = 10.0
        resume = await anext(self.d.telemetry.in_air())
        if resume:                                   # el watchdog reinició el nodo en vuelo: retomar sin despegar
            self.event("reinicio en vuelo: se retoma el control")
        else:
            self.event("conectado a PX4; esperando START de tierra")
            while not (self.cmd and self.cmd["cmd"] in ("START", "ABORT")):      # 1. espera
                self.pump(feed_agent=False)
                self.broadcast(slot)
                self.beat()
                await asyncio.sleep(1 / RATE_HZ)
            if self.cmd["cmd"] == "ABORT":
                return await self.finish("abortado antes de despegar")
            alt = float(self.cmd.get("alt", 10.0))
        t_start = time.time()
        if not resume:
            await arm_and_takeoff(self.d, alt)                                  # 2. despegue
        await self.d.offboard.set_velocity_ned(VelocityNedYaw(0, 0, 0, 0))
        for k in range(5):
            try:
                await self.d.offboard.start()
                break
            except OffboardError:
                if k == 4:
                    raise
                await asyncio.sleep(1)
        self.bus.send("ACK", what="airborne")
        self.event("en el aire, offboard")
        self.agent = Agent(self.id)                                            # tabla de vecinos limpia al empezar
        self.pump(feed_agent=False)                                            # descartar lo acumulado en el despegue
        t_air = time.time()                                                    # el enlace se vigila desde aquí
        n_nb = []
        while True:                                                            # 3. vuelo
            t = time.time()
            if self.a.drop_out is not None and t - t_start >= self.a.drop_out and not self.radio_down:
                self.radio_down = True
                self.event("RADIO CAÍDA (emulada)")
            self.pump()
            if self.cmd and self.cmd["cmd"] in ("LAND", "ABORT"):
                break
            age = t - self.ref_rx if self.ref else 1e9
            if t - max(self.ground_rx, t_air) > REF_RTL_S:
                self.event(f"sin enlace con tierra por {REF_RTL_S:.0f} s → RTL")
                self.log["ground_timeout"] = True
                self.cmd = {"cmd": "ABORT"}
                break
            if self.ref and age <= REF_HOLD_S:
                ref = as_np(self.ref["ref"]) + as_np(self.ref["ref_vel"]) * age
                slot = as_np(self.ref["slots"][self.id])
                obst = [Obstacle(*o) for o in self.ref.get("obstacles", [])]
                v, info = self.agent.command(t, self.pos, self.vel, slot, ref, as_np(self.ref["ref_vel"]),
                                             float(self.ref.get("alt", alt)), obst)
                n_nb.append(info.get("neighbors", 0))
            else:                                                              # sin referencia: quieto a su altura
                v = np.array([0.0, 0.0, float(np.clip(0.8 * (alt - self.pos[2]), -1.5, 1.5))])
            await self.d.offboard.set_velocity_ned(VelocityNedYaw(v[1], v[0], -v[2], 0))
            self.broadcast(slot)
            self.beat()
            await asyncio.sleep(max(0.0, 1 / RATE_HZ - (time.time() - t)))
        self.log["min_neighbors"] = int(min(n_nb)) if n_nb else None
        return await self.finish("ABORT → RTL" if self.cmd["cmd"] == "ABORT" else "LAND")

    async def finish(self, why: str):
        from demo_formation import first
        from mavsdk_grpc.offboard import OffboardError
        self.event(f"fin: {why}")
        try:
            await self.d.offboard.stop()
        except OffboardError:
            pass
        if "ABORT" in why or "RTL" in why:
            await self.d.action.return_to_launch()
        else:
            await self.d.action.land()
        try:
            await first(self.d.telemetry.armed(), lambda a: not a, 300)
            self.bus.send("ACK", what="landed")
            self.event("en tierra")
        except asyncio.TimeoutError:
            self.event("no aterrizó en 300 s")
        self.log.update(sent=self.bus.sent, received=self.bus.received, dropped_by_radio=self.bus.dropped,
                        lost_link=self.agent.lost)
        if self.a.log:
            Path(self.a.log).write_text(json.dumps(self.log, indent=2, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", type=int, required=True)
    ap.add_argument("--connect", help="URL de MAVSDK (por defecto, la de SITL: udpin://0.0.0.0:14540+id)")
    ap.add_argument("--grpc-port", type=int, help="puerto del servidor MAVSDK (por defecto 50051+id)")
    ap.add_argument("--origin", default=None, help="lat,lon del origen del campo (por defecto, el del mundo swarm)")
    ap.add_argument("--emulate", action="store_true", help="SITL: aplicar el modelo de radio al recibir")
    ap.add_argument("--radio", default="mesh_900")
    ap.add_argument("--loss", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--drop-out", type=float, help="SITL: la radio de este dron cae a los N s del despegue")
    ap.add_argument("--log", type=Path)
    ap.add_argument("--transport", choices=["multicast", "local"], default="multicast", help="local = SITL en una máquina")
    ap.add_argument("--n-nodes", type=int, default=0, help="(transporte local) cantidad de drones")
    ap.add_argument("--heartbeat", type=Path, help="archivo de latido para el watchdog (p. ej. /run/dronswarm/node.hb)")
    a = ap.parse_args()
    a.connect = a.connect or f"udpin://0.0.0.0:{14540 + a.id}"
    a.grpc_port = a.grpc_port or 50051 + a.id
    if a.origin is None:
        lay = json.loads((ROOT / "simulation/xtdrone/worlds/swarm_layout.json").read_text())
        a.origin = ",".join(map(str, lay["origin_latlon"]))
    try:
        asyncio.run(Node(a).run())
        code = 0
    except Exception:                                  # los streams de gRPC no dejan terminar al intérprete
        import traceback
        traceback.print_exc()
        code = 2
    sys.stdout.flush()
    os._exit(code)


if __name__ == "__main__":
    main()
