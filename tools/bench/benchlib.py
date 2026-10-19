"""S10 · Lógica común del banco de empuje: formato de datos, calibración y simulador del banco.

El simulador produce lo mismo que el firmware (hardware/test_bench/firmware/bench/bench.ino) a partir del modelo de
ingeniería (motor por circuito equivalente + hélice BEMT). Sirve para probar el análisis de punta a punta sin
hardware y para los tests; NO reemplaza al ensayo.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
DATA = ROOT / "data" / "bench"
RAW_COLS = ["t_ms", "throttle_us", "thrust_raw", "torque_a_raw", "torque_b_raw", "rpm", "v_bus", "i_bus", "esc_v",
            "esc_i", "esc_erpm", "esc_temp", "motor_temp"]


@dataclass
class Calibration:
    thrust_n_per_count: float = 1e-4        # N por cuenta del HX711 (se mide con masa patrón)
    torque_a_n_per_count: float = 1e-4
    torque_b_n_per_count: float = 1e-4
    torque_arm_m: float = 0.040              # distancia de cada celda de torque al eje
    lever_ratio: float = 1.0                 # palanca de la celda de empuje
    current_scale: float = 1.0

    @classmethod
    def load(cls, path: Path | None = None) -> Calibration:
        p = path or DATA / "calibracion.json"
        return cls(**json.loads(p.read_text())) if p.exists() else cls()

    def save(self, path: Path | None = None):
        p = path or DATA / "calibracion.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=2) + "\n")


@dataclass
class Meta:
    """Datos del ensayo (van junto al CSV crudo)."""
    motor: str
    prop: str
    prop_diameter_in: float
    esc: str
    battery: str
    test: str                                # noload | sweep | hover
    site_altitude_m: float
    ambient_c: float
    pressure_hpa: float | None = None
    vehicle: str | None = None
    notes: str = ""

    def density(self) -> float:
        from engineering.atmosphere import air
        if self.pressure_hpa:
            return self.pressure_hpa * 100 / (287.05 * (self.ambient_c + 273.15))
        return air(self.site_altitude_m, self.ambient_c).density


def physical(rows: list[dict], cal: Calibration) -> dict[str, np.ndarray]:
    """Convierte las columnas crudas a unidades físicas."""
    a = {k: np.array([float(r[k]) for r in rows]) for k in RAW_COLS}
    return {
        "t": a["t_ms"] / 1000, "throttle_us": a["throttle_us"],
        "thrust_n": a["thrust_raw"] * cal.thrust_n_per_count * cal.lever_ratio,
        "torque_nm": (a["torque_a_raw"] * cal.torque_a_n_per_count - a["torque_b_raw"] * cal.torque_b_n_per_count) * cal.torque_arm_m,
        "rpm": a["rpm"], "v": a["v_bus"], "i": a["i_bus"] * cal.current_scale, "motor_temp": a["motor_temp"],
    }


def write_raw(path: Path, rows: list[dict], meta: Meta):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RAW_COLS)
        w.writeheader()
        w.writerows(rows)
    path.with_suffix(".json").write_text(json.dumps(asdict(meta), indent=2, ensure_ascii=False) + "\n")


def read_raw(path: Path) -> tuple[list[dict], Meta]:
    rows = list(csv.DictReader(open(path)))
    return rows, Meta(**json.loads(path.with_suffix(".json").read_text()))


# ------------------------------------------------------------------------------------------ simulador del banco
class SimBench:
    """Banco virtual: motor COTS del catálogo + hélice BEMT a la densidad del sitio, con ruido de sensores."""

    def __init__(self, motor_name: str, prop_in: float, pitch_ratio: float, v_bus: float, site_alt: float = 150,
                 ambient_c: float = 20, seed: int = 0, no_prop: bool = False, true_overrides: dict | None = None):
        from engineering.atmosphere import air
        from engineering.cots import MOTORS
        from engineering.propeller import PropGeometry, PropTable

        cat = next(m for m in MOTORS if m.name == motor_name)
        self.true = {"kv": cat.kv, "rm": cat.rm, "i0": cat.i0, **(true_overrides or {})}
        self.v = v_bus
        self.no_prop = no_prop
        self.air = air(site_alt, ambient_c)
        geom = PropGeometry.inches(prop_in, prop_in * pitch_ratio, cd0_scale=2.171)
        self.prop = None if no_prop else PropTable.build(geom, self.air)
        self.rng = np.random.default_rng(seed)
        self.cal = Calibration()
        self.temp = ambient_c

    def _state(self, duty: float) -> tuple[float, float, float, float]:
        """(rpm, empuje, torque, corriente de batería) para un duty del ESC."""
        from scipy.optimize import brentq
        kv, rm, i0 = self.true["kv"], self.true["rm"], self.true["i0"]
        kt = 60 / (2 * math.pi * kv)
        vm = duty * self.v * 0.97
        if vm < 0.5:
            return 0.0, 0.0, 0.0, 0.0
        if self.prop is None:
            rpm = kv * (vm - i0 * rm)
            return rpm, 0.0, 0.0, vm * i0 / self.v / 0.95

        def f(rpm):
            q = self.prop.torque_at(rpm)
            return rpm / kv + (q / kt + i0) * rm - vm
        hi = min(kv * vm, self.prop.max_rpm * 0.999)
        if f(hi) < 0:                                     # sin carga suficiente: se usa el máximo de la tabla
            rpm = hi
        else:
            rpm = brentq(f, 1.0, hi)
        q = self.prop.torque_at(rpm)
        i_m = q / kt + i0
        return rpm, self.prop.thrust_at(rpm), q, vm * i_m / 0.95 / self.v

    def sample(self, t_ms: int, throttle_us: int) -> dict:
        duty = (throttle_us - 1000) / 1000
        rpm, thr, q, i = self._state(duty)
        i_m = i * self.v * 0.95 / max(duty * self.v * 0.97, 1e-3) if duty > 0 else 0.0     # corriente del motor
        heat_cap, cool = 150.0, 3.0                       # J/K y W/K: motor de ~250 g con flujo de la hélice
        self.temp += (i_m * i_m * self.true["rm"] - cool * (self.temp - 20)) * 0.02 / heat_cap
        n = self.rng.normal
        c = self.cal
        return {"t_ms": t_ms, "throttle_us": throttle_us,
                "thrust_raw": int((thr + n(0, 0.02)) / c.thrust_n_per_count),
                "torque_a_raw": int((q / 2 / c.torque_arm_m + n(0, 0.01)) / c.torque_a_n_per_count),
                "torque_b_raw": int((-q / 2 / c.torque_arm_m + n(0, 0.01)) / c.torque_b_n_per_count),
                "rpm": round(rpm * (1 + n(0, 0.003))), "v_bus": round(self.v - 0.01 * i + n(0, 0.02), 3),
                "i_bus": round(i + n(0, 0.03), 3), "esc_v": 0, "esc_i": 0, "esc_erpm": 0, "esc_temp": 0,
                "motor_temp": round(self.temp, 1)}
