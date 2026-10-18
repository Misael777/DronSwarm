"""Modelo de motor BLDC (circuito equivalente) y punto de operación motor–hélice.

    ω = Kv · (V − I·Rm)        Q = Kt · (I − I0)        Kt = 1 / Kv  [unidades SI]

Para el dimensionamiento se usa un motor *paramétrico*: dados Kv y la potencia máxima que debe entregar,
estima Rm, I0, masa y costo con relaciones típicas de motores outrunner de multirrotor. La selección de un
motor comercial concreto se hace en S09 con estos requisitos; el motor propio, en S17.
"""

import math
from dataclasses import dataclass

from scipy.optimize import brentq

from .propeller import PropTable

ESC_EFFICIENCY = 0.95
MAX_DUTY = 0.97                    # fracción útil del voltaje de batería con el ESC a fondo

# Relaciones paramétricas (outrunners de multirrotor 22xx-62xx); se reemplazan por datos de catálogo en S09
SPECIFIC_POWER_W_PER_KG = 4000     # potencia máxima / masa
# I²Rm / potencia a corriente máxima: los motores chicos pierden proporcionalmente más (≈ 12 % a 100 W, 7 % a 1 kW)
def copper_loss_fraction(p_max_w: float) -> float:
    return min(0.15, max(0.04, 0.12 * (p_max_w / 100.0) ** -0.25))

NO_LOAD_CURRENT_FRAC = 0.04        # I0 / Imax
COST_BASE, COST_PER_GRAM = 8.0, 0.14   # US$ (ajustado a la hoja Costo_Motor: 28xx ≈ 23, 62xx ≈ 63)


@dataclass(frozen=True)
class Motor:
    kv: float            # rpm/V
    rm: float            # Ω
    i0: float            # A
    i_max: float         # A
    mass_kg: float
    cost_usd: float
    name: str = "paramétrico"

    @property
    def kv_rad(self) -> float:
        return self.kv * 2 * math.pi / 60

    @property
    def kt(self) -> float:
        return 1 / self.kv_rad

    @classmethod
    def parametric(cls, kv: float, p_max_w: float, v_nominal: float) -> "Motor":
        i_max = p_max_w / v_nominal
        mass = p_max_w / SPECIFIC_POWER_W_PER_KG
        return cls(kv=kv, rm=copper_loss_fraction(p_max_w) * p_max_w / i_max ** 2, i0=NO_LOAD_CURRENT_FRAC * i_max,
                   i_max=i_max, mass_kg=mass, cost_usd=COST_BASE + COST_PER_GRAM * mass * 1000)

    def electrical(self, torque_nm: float, rpm: float) -> dict:
        """Corriente, voltaje, potencia de entrada y eficiencia para entregar torque a rpm."""
        omega = rpm * 2 * math.pi / 60
        current = torque_nm / self.kt + self.i0
        voltage = omega / self.kv_rad + current * self.rm
        p_in = voltage * current
        return {"current": current, "voltage": voltage, "p_in": p_in, "p_shaft": torque_nm * omega,
                "efficiency": torque_nm * omega / p_in if p_in > 0 else 0.0}


def operating_point(motor: Motor, prop: PropTable, thrust_n: float, v_battery: float) -> dict:
    """Punto de operación para un empuje dado: rpm, corriente, throttle y potencia desde la batería."""
    rpm = prop.rpm_for_thrust(thrust_n)
    e = motor.electrical(prop.torque_at(rpm), rpm)
    p_batt = e["p_in"] / ESC_EFFICIENCY
    return {"thrust": thrust_n, "rpm": rpm, "torque": prop.torque_at(rpm), **e,
            "throttle": e["voltage"] / (v_battery * MAX_DUTY), "p_battery": p_batt}


def max_thrust_point(motor: Motor, prop: PropTable, v_battery: float) -> dict:
    """Empuje máximo: el menor rpm entre (a) voltaje pedido = voltaje disponible con el ESC a fondo,
    (b) corriente = corriente máxima del motor, (c) límite de velocidad de punta de la hélice."""
    v_avail = v_battery * MAX_DUTY
    lo, hi = prop.rpm[0], prop.max_rpm

    def volt_res(rpm):
        return motor.electrical(prop.torque_at(rpm), rpm)["voltage"] - v_avail

    def curr_res(rpm):
        return motor.electrical(prop.torque_at(rpm), rpm)["current"] - motor.i_max

    if volt_res(lo) > 0 or curr_res(lo) > 0:
        return {"thrust": 0.0, "rpm": 0.0, "current": 0.0, "p_battery": 0.0, "limit": "ninguno"}
    candidates = {"punta": hi}
    if volt_res(hi) > 0:
        candidates["voltaje"] = brentq(volt_res, lo, hi, xtol=1.0)
    if curr_res(hi) > 0:
        candidates["corriente"] = brentq(curr_res, lo, hi, xtol=1.0)
    limit, rpm = min(candidates.items(), key=lambda kv: kv[1])
    e = motor.electrical(prop.torque_at(rpm), rpm)
    return {"thrust": prop.thrust_at(rpm), "rpm": rpm, **e, "p_battery": e["p_in"] / ESC_EFFICIENCY, "limit": limit}


def kv_for_rpm(rpm: float, torque_nm: float, v_battery: float, p_max_w: float, v_nominal: float) -> float:
    """Kv mínimo para que un motor paramétrico alcance rpm con ese torque al voltaje disponible."""
    v_avail = v_battery * MAX_DUTY
    kv = rpm / v_avail
    for _ in range(30):             # Rm depende de Kv vía la corriente: punto fijo
        m = Motor.parametric(kv, p_max_w, v_nominal)
        drop = (torque_nm / m.kt + m.i0) * m.rm
        new_kv = rpm / max(v_avail - drop, 0.3 * v_avail)
        if abs(new_kv - kv) < 0.5:
            break
        kv = new_kv
    return kv
