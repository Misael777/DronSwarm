"""S06-02 · Modelo de comunicaciones entre drones y con la estación de tierra.

Cada mensaje pasa por un enlace de radio con:
  - pérdida de trayecto log-distancia + sombreado (desvanecimiento lento, gaussiano en dB),
  - obstrucción opcional (p. ej. la pared del tajo entre dron y estación) como atenuación extra,
  - tasa de pérdida de paquetes (PER) a partir de la relación señal/ruido con una curva logística,
  - latencia = tiempo en el aire (bits / tasa) + acceso al medio (exponencial, crece con la cantidad de nodos) + saltos.

Así el control del enjambre recibe los estados de sus vecinos tarde, a veces nunca, y sin enlace más allá del alcance:
lo mismo que pasará con radios reales. Los valores por defecto son supuestos documentados, no mediciones; se
reemplazan con las pruebas de radio en campo (S14).

    from simulation.common.comms_model import CommsModel, RADIOS
    net = CommsModel(RADIOS["mesh_900"], seed=1)
    net.send(src=0, dst=1, t=10.0, pos_src=(0, 0, 10), pos_dst=(30, 0, 10), payload=estado)
    for msg in net.deliver(t=10.2): ...
"""

from __future__ import annotations

import heapq
import math
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

C_LIGHT = 299_792_458.0
GCS = -1                                   # identificador de la estación de tierra


@dataclass(frozen=True)
class Radio:
    """Parámetros de un enlace. Los presets se basan en hojas de datos de radios comerciales típicos."""

    name: str
    freq_hz: float
    tx_dbm: float
    gain_dbi: float                        # ganancia de cada antena (tx y rx iguales)
    noise_dbm: float                       # piso de ruido en el ancho de banda del canal
    snr50_db: float                        # SNR con 50 % de paquetes perdidos (sensibilidad del módem)
    snr_slope_db: float                    # ancho de la transición de la curva de pérdida
    rate_bps: float                        # tasa efectiva de datos
    path_exp: float = 2.2                  # exponente de pérdida (2 = espacio libre; 2.2-2.7 mina a cielo abierto)
    shadow_db: float = 4.0                 # desviación del sombreado
    mac_ms: float = 4.0                    # demora media de acceso al medio por nodo que comparte el canal
    base_ms: float = 2.0                   # procesamiento fijo en cada extremo

    def per(self, snr_db: float) -> float:
        """Probabilidad de perder un paquete con esa SNR."""
        return 1.0 / (1.0 + math.exp((snr_db - self.snr50_db) / self.snr_slope_db))


RADIOS: dict[str, Radio] = {
    # Malla de telemetría en 900 MHz (clase RFD900x / Microhard): largo alcance, poca tasa
    "mesh_900": Radio("Malla 900 MHz", 915e6, 30.0, 3.0, -110.0, 6.0, 1.5, 64_000, path_exp=2.4, mac_ms=6.0),
    # Wi-Fi/ESP-NOW 2.4 GHz entre drones: más tasa, poco alcance
    "wifi_24": Radio("Wi-Fi 2.4 GHz", 2.44e9, 20.0, 2.0, -95.0, 10.0, 1.5, 1_000_000, path_exp=2.4, mac_ms=1.5),
}


def fspl_db(d_m: float, freq_hz: float) -> float:
    """Pérdida en espacio libre (Friis) a la distancia d."""
    return 20 * math.log10(4 * math.pi * max(d_m, 1e-3) * freq_hz / C_LIGHT)


@dataclass(order=True)
class Message:
    t_arrive: float
    seq: int
    src: int = field(compare=False)
    dst: int = field(compare=False)
    t_sent: float = field(compare=False)
    payload: object = field(compare=False, default=None)

    @property
    def age(self) -> float:
        return self.t_arrive - self.t_sent


@dataclass
class LinkStats:
    sent: int = 0
    delivered: int = 0
    latencies: list[float] = field(default_factory=list)

    @property
    def loss(self) -> float:
        return 1 - self.delivered / self.sent if self.sent else 0.0


class CommsModel:
    """Red de radio simulada: `send` decide si el paquete llega y cuándo; `deliver` entrega los que ya llegaron."""

    def __init__(self, radio: Radio, n_nodes: int = 6, seed: int | None = None, payload_bytes: int = 60,
                 blockage: Callable[[tuple, tuple], float] | None = None, extra_loss: float = 0.0):
        self.radio = radio
        self.n_nodes = n_nodes
        self.rng = np.random.default_rng(seed)
        self.payload_bits = 8 * (payload_bytes + 20)            # + encabezados MAVLink/radio
        self.blockage = blockage                                # (pos_a, pos_b) → atenuación extra en dB
        self.extra_loss = extra_loss                            # pérdida adicional fija (interferencia, ensayos)
        self._queue: list[Message] = []
        self._seq = 0
        self._shadow: dict[tuple[int, int], float] = {}
        self.stats: dict[tuple[int, int], LinkStats] = {}
        self.down: set[int] = set()                             # nodos con la radio caída (inyección de fallas)

    # ------------------------------------------------------------------ física del enlace
    def path_loss_db(self, d_m: float) -> float:
        d0 = 1.0
        return fspl_db(d0, self.radio.freq_hz) + 10 * self.radio.path_exp * math.log10(max(d_m, d0) / d0)

    def snr_db(self, a: int, b: int, pos_a, pos_b) -> float:
        d = math.dist(pos_a, pos_b)
        key = (min(a, b), max(a, b))
        if key not in self._shadow:                             # sombreado fijo por par (cambia lento frente a una misión)
            self._shadow[key] = float(self.rng.normal(0.0, self.radio.shadow_db))
        rx = self.radio.tx_dbm + 2 * self.radio.gain_dbi - self.path_loss_db(d) - self._shadow[key]
        if self.blockage is not None:
            rx -= self.blockage(tuple(pos_a), tuple(pos_b))
        return rx - self.radio.noise_dbm

    def range_m(self, per_max: float = 0.5) -> float:
        """Distancia (sin sombreado ni obstrucción) a la que la pérdida alcanza `per_max`."""
        snr_need = self.radio.snr50_db + self.radio.snr_slope_db * math.log(1 / per_max - 1)
        budget = self.radio.tx_dbm + 2 * self.radio.gain_dbi - self.radio.noise_dbm - snr_need
        return 10 ** ((budget - fspl_db(1.0, self.radio.freq_hz)) / (10 * self.radio.path_exp))

    def latency_s(self) -> float:
        r = self.radio
        air = self.payload_bits / r.rate_bps
        mac = self.rng.exponential(r.mac_ms * self.n_nodes / 6) / 1e3   # más nodos en el canal → más espera
        return 2 * r.base_ms / 1e3 + air + mac

    # ------------------------------------------------------------------ envío y entrega
    def send(self, src: int, dst: int, t: float, pos_src, pos_dst, payload=None) -> bool:
        st = self.stats.setdefault((src, dst), LinkStats())
        st.sent += 1
        if src in self.down or dst in self.down:
            return False
        p_loss = 1 - (1 - self.radio.per(self.snr_db(src, dst, pos_src, pos_dst))) * (1 - self.extra_loss)
        if self.rng.random() < p_loss:
            return False
        lat = self.latency_s()
        self._seq += 1
        heapq.heappush(self._queue, Message(t + lat, self._seq, src, dst, t, payload))
        st.delivered += 1
        st.latencies.append(lat)
        return True

    def broadcast(self, src: int, t: float, positions: dict[int, tuple], payload=None) -> int:
        """Difunde a todos los demás nodos (cada receptor tiene su propio enlace). Devuelve cuántos lo recibirán."""
        return sum(self.send(src, dst, t, positions[src], pos, payload) for dst, pos in positions.items() if dst != src)

    def deliver(self, t: float) -> list[Message]:
        out = []
        while self._queue and self._queue[0].t_arrive <= t:
            out.append(heapq.heappop(self._queue))
        return out

    # ------------------------------------------------------------------ resumen
    def summary(self) -> dict:
        sent = sum(s.sent for s in self.stats.values())
        got = sum(s.delivered for s in self.stats.values())
        lat = [x for s in self.stats.values() for x in s.latencies]
        return {"radio": self.radio.name, "packets_sent": sent, "packet_loss_pct": round(100 * (1 - got / sent), 1) if sent else 0.0,
                "latency_ms_mean": round(1e3 * float(np.mean(lat)), 1) if lat else None,
                "latency_ms_p95": round(1e3 * float(np.percentile(lat, 95)), 1) if lat else None,
                "range_m_50pct": round(self.range_m()), "extra_loss_pct": round(100 * self.extra_loss, 1)}
