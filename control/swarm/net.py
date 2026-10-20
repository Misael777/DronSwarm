"""S13-01 · Red del enjambre en hardware: mensajes entre drones y con la estación de tierra.

Transporte: UDP multicast (JSON compacto). Funciona igual en SITL (todo en la misma máquina) y en la flota real (las
computadoras a bordo en la misma red: malla Wi-Fi/ESP-NOW puenteada a IP, o LTE privada de la mina).
En SITL, cada receptor puede aplicar el modelo de radio del S06 (pérdida por distancia + pérdida extra + latencia), para
probar lo mismo que en la simulación cinemática pero con los procesos reales.

Mensajes ("k" = tipo):
  STATE  dron → todos   10 Hz   posición/velocidad ENU (marco de la misión), puesto en la formación, flags
  REF    tierra → todos 10 Hz   fase, referencia del centro y su velocidad, puestos de todos, obstáculos
  CMD    tierra → todos         START (despegar), LAND, ABORT (todos a RTL: el botón de la HU-08)
                                WAIT (latido mientras los demás despegan)
  ACK    dron → tierra          confirmaciones (despegó, aterrizó, error)
Los tiempos ("t") son de reloj de pared sincronizado: en la flota, chrony con la hora del GNSS en cada computadora a bordo.
"""

from __future__ import annotations

import json
import math
import socket
import struct
import time
from dataclasses import dataclass, field

import numpy as np

GROUP, PORT = "239.255.42.99", 14660
LOCAL_BASE = 14701                      # transporte local (SITL): tierra 14700, dron i → 14701 + i


@dataclass
class Emulation:
    """Radio simulada en el receptor (solo SITL)."""
    radio: str = "mesh_900"
    extra_loss: float = 0.0
    seed: int = 0
    model: object = field(default=None, init=False)

    def __post_init__(self):
        from simulation.common.comms_model import RADIOS, CommsModel
        self.model = CommsModel(RADIOS[self.radio], seed=self.seed, extra_loss=self.extra_loss)

    def delivered(self, src: int, dst: int, pos_src, pos_dst) -> tuple[bool, float]:
        """(llega, latencia [s]) para un paquete entre dos nodos con posiciones conocidas."""
        m = self.model
        if src in m.down or dst in m.down:
            return False, 0.0
        p_loss = 1 - (1 - m.radio.per(m.snr_db(src, dst, pos_src, pos_dst))) * (1 - m.extra_loss)
        if m.rng.random() < p_loss:
            return False, 0.0
        return True, m.latency_s()


class Bus:
    """Envío y recepción no bloqueantes. `node` = id del dron (−1 = estación de tierra).

    transport = "multicast": la flota real (todas las computadoras en la red del enjambre).
    transport = "local": SITL en una sola máquina, sin depender de la red: cada nodo escucha en 127.0.0.1 en el puerto
    LOCAL_BASE + id (la tierra en LOCAL_BASE − 1) y envía una copia a cada uno de los otros `n_nodes`.
    """

    def __init__(self, node: int, group: str = GROUP, port: int = PORT, iface: str = "0.0.0.0", ttl: int = 1,
                 emulation: Emulation | None = None, transport: str = "multicast", n_nodes: int = 0,
                 local_base: int = LOCAL_BASE):
        self.node = node
        self.transport = transport
        self.tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        if transport == "local":
            self.peers = [("127.0.0.1", local_base + k) for k in range(-1, n_nodes) if k != node]
            self.rx.bind(("127.0.0.1", local_base + node))
        else:
            self.peers = [(group, port)]
            self.tx.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
            self.tx.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
            self.rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                self.rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            self.rx.bind(("", port))
            mreq = struct.pack("4s4s", socket.inet_aton(group), socket.inet_aton(iface))
            self.rx.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self.rx.setblocking(False)
        self.emu = emulation
        self.own_pos: tuple | None = None          # para la emulación de la radio
        self._delayed: list[tuple[float, dict]] = []
        self.sent = self.received = self.dropped = self.send_errors = 0

    def send(self, kind: str, **payload):
        msg = {"k": kind, "src": self.node, "t": time.time(), **payload}
        data = json.dumps(msg, separators=(",", ":")).encode()
        for peer in self.peers:
            try:
                self.tx.sendto(data, peer)
            except OSError:                        # red caída (p. ej. sin ruta): se cuenta, no se cae el nodo
                self.send_errors += 1
        self.sent += 1

    def poll(self) -> list[dict]:
        """Mensajes recibidos de otros nodos (sin los propios), ya con la radio emulada si corresponde."""
        now = time.time()
        out = []
        while True:
            try:
                data, _ = self.rx.recvfrom(65536)
            except BlockingIOError:
                break
            msg = json.loads(data)
            if msg.get("src") == self.node:
                continue
            if self.emu is not None and msg["k"] == "STATE" and self.own_pos is not None and self.node >= 0:
                ok, lat = self.emu.delivered(msg["src"], self.node, msg["pos"], self.own_pos)
                if not ok:
                    self.dropped += 1
                    continue
                self._delayed.append((now + lat, msg))
                continue
            out.append(msg)
        keep = []
        for due, m in self._delayed:
            (out if due <= now else keep).append(m if due <= now else (due, m))
        self._delayed = keep
        self.received += len(out)
        return out

    def close(self):
        self.tx.close()
        self.rx.close()


def enu(origin: tuple[float, float], lat: float, lon: float) -> tuple[float, float]:
    r = 6_378_137.0
    return (math.radians(lon - origin[1]) * r * math.cos(math.radians(origin[0])), math.radians(lat - origin[0]) * r)


def as_np(v) -> np.ndarray:
    return np.asarray(v, dtype=float)
