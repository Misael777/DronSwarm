"""Dimensionamiento del motor para una hélice, una batería y una relación empuje/peso objetivo."""

import math
from dataclasses import dataclass

from .atmosphere import G0, Air
from .battery import Pack
from .motor import ESC_EFFICIENCY, Motor, kv_for_rpm
from .propeller import PropGeometry, PropTable

KV_MARGIN = 1.03              # margen sobre el Kv mínimo (tolerancia de fabricación del motor)
EFFICIENCY_GUESS = 0.80       # eficiencia del motor en empuje máximo (primera estimación)


class Infeasible(ValueError):
    """La combinación no puede cumplir el requisito (p. ej. la hélice no da el empuje antes del límite de punta)."""


@dataclass(frozen=True)
class MotorSizing:
    motor: Motor
    rpm_max_thrust: float
    thrust_per_rotor_n: float
    p_battery_max_w: float      # potencia de batería total en empuje máximo (sin factor de seguridad)
    current_max_a: float        # corriente de batería total en empuje máximo


def size_motor(n_rotors: int, geom: PropGeometry, pack: Pack, air_thrust: Air, mass_kg: float,
               twr: float, current_sf: float, table: PropTable | None = None) -> MotorSizing:
    """Motor paramétrico que entrega twr × peso en el aire del caso de empuje, con factor de corriente."""
    prop = table or PropTable.build(geom, air_thrust)
    thrust = twr * mass_kg * G0 / n_rotors
    try:
        rpm = prop.rpm_for_thrust(thrust)
    except ValueError as e:
        raise Infeasible(str(e)) from e
    torque = prop.torque_at(rpm)
    p_shaft = torque * rpm * 2 * math.pi / 60
    p_motor = p_shaft / EFFICIENCY_GUESS
    p_max = p_motor * current_sf                      # potencia nominal máxima del motor
    p_batt = n_rotors * p_motor / ESC_EFFICIENCY
    v = pack.voltage_under_load(p_batt)
    kv = kv_for_rpm(rpm, torque, v, p_max, pack.v_nominal) * KV_MARGIN
    motor = Motor.parametric(kv, p_max, pack.v_nominal)
    e = motor.electrical(torque, rpm)                 # recalcular con el motor ya definido
    p_batt = n_rotors * e["p_in"] / ESC_EFFICIENCY
    return MotorSizing(motor, rpm, thrust, p_batt, p_batt / pack.voltage_under_load(p_batt))
