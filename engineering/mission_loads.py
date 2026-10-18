"""Potencia en vuelo y energía de misión.

- Hover: punto de operación motor–hélice con el voltaje real de la batería bajo carga.
- Crucero: teoría de momento con avance (Glauert) + pérdidas de perfil (1 + 4.65 μ²) + arrastre del cuerpo.
- Misiones: autonomía en hover y misión de entrega (ida con carga, entrega, vuelta vacío, reserva).
"""

import math
from dataclasses import dataclass, field

from .atmosphere import G0, Air
from .battery import Pack
from .motor import ESC_EFFICIENCY, Motor, max_thrust_point, operating_point
from .propeller import PropGeometry, PropTable, ideal_induced_velocity

INDUCED_KAPPA = 1.15          # pérdidas inducidas no ideales en avance
PROFILE_ADVANCE = 4.65        # factor de potencia de perfil en avance (rotor convencional)


@dataclass
class Propulsion:
    n_rotors: int
    motor: Motor
    geom: PropGeometry
    pack: Pack
    avionics_w: float = 15.0
    _tables: dict = field(default_factory=dict, repr=False)

    def table(self, air: Air) -> PropTable:
        key = round(air.density, 4), round(air.temperature_k, 1)
        if key not in self._tables:
            self._tables[key] = PropTable.build(self.geom, air)
        return self._tables[key]

    def hover(self, mass_kg: float, air: Air) -> dict:
        """Hover: potencia de batería total, throttle y fracción de empuje máximo."""
        prop = self.table(air)
        thrust = mass_kg * G0 / self.n_rotors
        v = self.pack.v_nominal
        for _ in range(5):                       # el voltaje cae con la corriente: iterar
            op = operating_point(self.motor, prop, thrust, v)
            p_total = self.n_rotors * op["p_battery"] + self.avionics_w
            v = self.pack.voltage_under_load(p_total)
        tmax = self.max_thrust(air)
        return {**op, "p_total": p_total, "v_battery": v, "thrust_fraction": thrust / tmax["thrust"],
                "current_total": p_total / v}

    def max_thrust(self, air: Air) -> dict:
        prop = self.table(air)
        v = self.pack.v_nominal
        for _ in range(5):
            mx = max_thrust_point(self.motor, prop, v)
            v = self.pack.voltage_under_load(self.n_rotors * mx["p_battery"] + self.avionics_w)
        return {**mx, "v_battery": v, "total_thrust": mx["thrust"] * self.n_rotors,
                "current_total": self.n_rotors * mx["p_battery"] / v}

    def forward(self, mass_kg: float, air: Air, speed_ms: float, drag_area_m2: float) -> dict:
        """Potencia de batería en crucero horizontal a speed_ms."""
        prop = self.table(air)
        weight = mass_kg * G0
        drag = 0.5 * air.density * speed_ms ** 2 * drag_area_m2
        thrust = math.hypot(weight, drag) / self.n_rotors
        tilt = math.atan2(drag, weight)
        hov = operating_point(self.motor, prop, thrust, self.pack.v_nominal)
        v_h = ideal_induced_velocity(thrust, air, self.geom)
        vi = v_h
        for _ in range(60):
            vi = v_h ** 2 / math.hypot(speed_ms * math.cos(tilt), speed_ms * math.sin(tilt) + vi)
        omega = hov["rpm"] * 2 * math.pi / 60
        mu = speed_ms * math.cos(tilt) / (omega * self.geom.radius)
        p_profile = max(hov["p_shaft"] - INDUCED_KAPPA * thrust * v_h, 0.0)
        p_shaft = INDUCED_KAPPA * thrust * (vi + speed_ms * math.sin(tilt)) + p_profile * (1 + PROFILE_ADVANCE * mu ** 2)
        e = self.motor.electrical(p_shaft / omega, hov["rpm"])
        p_total = self.n_rotors * e["p_in"] / ESC_EFFICIENCY + self.avionics_w
        return {"p_total": p_total, "speed": speed_ms, "tilt_deg": math.degrees(tilt), "mu": mu}


def hover_endurance_min(prop: Propulsion, mass_kg: float, air: Air, battery_temp_c: float) -> float:
    return prop.pack.usable_energy_wh(battery_temp_c) * 60 / prop.hover(mass_kg, air)["p_total"]


def delivery_mission(prop: Propulsion, empty_mass_kg: float, payload_kg: float, air: Air, distance_m: float,
                     speed_ms: float, drag_area_m2: float, battery_temp_c: float, reserve: float = 0.20) -> dict:
    """Ida con carga, ascenso/descenso, 60 s de entrega en hover, vuelta vacío. Energía vs disponible."""
    loaded, empty = empty_mass_kg + payload_kg, empty_mass_kg
    t_cruise = distance_m / speed_ms
    segments = [
        ("ascenso 30 m", 15.0, prop.hover(loaded, air)["p_total"] * 1.15),
        ("ida con carga", t_cruise, prop.forward(loaded, air, speed_ms, drag_area_m2)["p_total"]),
        ("entrega (hover)", 60.0, prop.hover(loaded, air)["p_total"]),
        ("vuelta vacío", t_cruise, prop.forward(empty, air, speed_ms, drag_area_m2)["p_total"]),
        ("descenso y aterrizaje", 30.0, prop.hover(empty, air)["p_total"]),
    ]
    energy = sum(t * p for _, t, p in segments) / 3600
    available = prop.pack.usable_energy_wh(battery_temp_c)
    return {"segments": [{"name": n, "time_s": round(t), "power_w": round(p)} for n, t, p in segments],
            "energy_wh": energy, "required_wh": energy * (1 + reserve), "available_wh": available,
            "margin": available / (energy * (1 + reserve)) - 1}
