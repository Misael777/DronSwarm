"""M1 · Modelo de pérdidas de un motor BLDC, el mismo para el comercial (referencia) y para el propio (M2).

    I = (τ + P_vacío(ω)/ω) / Kt(T_imán)         V = ω / Kv(T_imán) + I · R(T_bobinado)
    P_vacío(ω) = c1·ω + c2·ω²                   (histéresis + rodamientos ∝ ω; corrientes parásitas + aire ∝ ω²)

R es la resistencia "de línea" equivalente en continua (la que da la ficha, entre dos cables), igual que en
engineering/motor.py. El imán caliente debilita el flujo: Kt baja y Kv sube ~0.12 %/K (N52H).
Las pérdidas en vacío se calibran con la corriente en vacío de la ficha y, si hay tabla de banco, se ajustan a ella.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

from scipy.optimize import least_squares

ALPHA_CU = 0.00393
ALPHA_BR = -0.0012


@dataclass(frozen=True)
class MotorModel:
    name: str
    kv: float                   # rpm/V con los imanes a 20 °C
    r20: float                  # Ω (línea, equivalente en continua) a 20 °C
    c1: float                   # W/(rad/s)
    c2: float                   # W/(rad/s)²
    mass_kg: float = 0.0
    i_max: float = 0.0

    @classmethod
    def from_noload(cls, name: str, kv: float, r20: float, i0: float, v0: float, split: float = 0.5,
                    mass_kg: float = 0.0, i_max: float = 0.0) -> MotorModel:
        """Calibra P_vacío con la corriente en vacío I0 medida a V0. split = fracción ∝ ω (histéresis + rodamientos)."""
        omega0 = kv * 2 * math.pi / 60 * (v0 - i0 * r20)
        p0 = v0 * i0 - i0 ** 2 * r20
        return cls(name, kv, r20, split * p0 / omega0, (1 - split) * p0 / omega0 ** 2, mass_kg, i_max)

    def kt(self, t_mag: float = 20.0) -> float:
        return 60 / (2 * math.pi * self.kv) * (1 + ALPHA_BR * (t_mag - 20))

    def r(self, t_wind: float = 20.0) -> float:
        return self.r20 * (1 + ALPHA_CU * (t_wind - 20))

    def p_noload(self, omega: float) -> float:
        return self.c1 * omega + self.c2 * omega ** 2

    def operate(self, torque: float, rpm: float, t_wind: float = 20.0, t_mag: float | None = None) -> dict:
        t_mag = t_wind - 15 if t_mag is None else t_mag            # imanes algo más fríos que el bobinado (rotor ventilado)
        omega = rpm * 2 * math.pi / 60
        kt, r = self.kt(t_mag), self.r(t_wind)
        p_nl = self.p_noload(omega)
        i = (torque + p_nl / max(omega, 1e-6)) / kt
        v = omega * kt + i * r
        p_cu = i * i * r
        p_shaft = torque * omega
        p_in = p_shaft + p_cu + p_nl
        return {"current": i, "voltage": v, "p_in": p_in, "p_shaft": p_shaft, "p_copper": p_cu, "p_noload": p_nl,
                "efficiency": p_shaft / p_in if p_in > 0 else 0.0}

    def winding_temp(self, p_loss: float, t_amb: float, r_th: float) -> float:
        return t_amb + p_loss * r_th


def read_bench(path: Path) -> list[dict]:
    rows = [r for r in csv.reader(open(path)) if r and not r[0].startswith("#")]
    head = rows[0]
    return [dict(zip(head, map(float, r))) for r in rows[1:]]


def fit_to_bench(name: str, kv: float, r20: float, i0: float, v0: float, bench: list[dict], v_supply: float,
                 t_surface_full: float, t_amb: float = 25.0, mass_kg: float = 0.0, i_max: float = 0.0,
                 kv_scale: float = 1.0) -> tuple[MotorModel, dict]:
    """Ajusta el reparto de las pérdidas en vacío y la eficiencia del ESC a la corriente de la fuente medida.

    El Kv se FIJA (por defecto el de la ficha): con torques redondeados, Kv, ESC y pérdidas en vacío se compensan
    entre sí y el ajuste libre no los separa (ver `kv_sensitivity`). Temperatura del bobinado en cada fila: la de
    superficie a fondo escalada con I², más un 30 % entre bobinado y superficie.
    """
    i_full = max(b["current_a"] for b in bench)

    def t_wind(b):
        return t_amb + (t_surface_full - t_amb) * 1.3 * (b["current_a"] / i_full) ** 2

    def model(x):
        split, eta_esc = x
        return MotorModel.from_noload(name, kv * kv_scale, r20, i0, v0, split=split, mass_kg=mass_kg, i_max=i_max), eta_esc

    def residuals(x):
        m, eta = model(x)
        return [(m.operate(b["torque_nm"], b["rpm"], t_wind(b))["p_in"] / eta / v_supply - b["current_a"]) / b["current_a"]
                for b in bench]

    sol = least_squares(residuals, x0=[0.5, 0.95], bounds=([0.05, 0.85], [0.95, 0.99]))
    m, eta = model(sol.x)
    rows = []
    for b in bench:
        op = m.operate(b["torque_nm"], b["rpm"], t_wind(b))
        p_supply = op["p_in"] / eta
        eff_meas = b["torque_nm"] * b["rpm"] * 2 * math.pi / 60 / (b["current_a"] * v_supply)
        rows.append({"throttle": b["throttle"], "rpm": b["rpm"], "torque_nm": b["torque_nm"], "current_meas_a": b["current_a"],
                     "current_model_a": round(p_supply / v_supply, 2), "eff_system_meas": round(eff_meas, 4),
                     "eff_system_model": round(op["p_shaft"] / p_supply, 4), "eff_motor_model": round(op["efficiency"], 4),
                     "t_wind_c": round(t_wind(b), 1)})
    err_pts = [abs(r["eff_system_model"] - r["eff_system_meas"]) * 100 for r in rows]
    info = {"split": round(float(sol.x[0]), 3), "eta_esc": round(float(sol.x[1]), 4), "kv_scale": kv_scale,
            "eff_error_rms_points": round(math.sqrt(sum(e * e for e in err_pts) / len(err_pts)), 2),
            "eff_error_max_points": round(max(err_pts), 2), "rows": rows}
    return m, info
