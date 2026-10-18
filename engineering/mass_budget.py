"""S04-01 · Presupuesto de masa y costo con iteración de MTOW, y verificación de requisitos de un diseño.

Ciclo: MTOW → motor (TWR en el caso de empuje) → ESC, hélice, brazos → nueva MTOW, hasta converger (< 1 g).
Criterios de energía: la batería se evalúa al final de su vida útil (capacidad / factor de batería 1.3) a 0 °C;
así la autonomía de un pack nuevo queda ≥ 1.3 × el objetivo (cubre también el margen de autonomía de 1.2).
"""

from dataclasses import asdict, dataclass, field

from .atmosphere import G0, Air
from .battery import Pack
from .design import Infeasible, size_motor
from .inertia import vehicle_inertia
from .mission_loads import Propulsion, delivery_mission
from .propeller import INCH, PropGeometry, PropTable
from .structures import ArmResult, center_plates, select_arm, wheelbase_m

PRINTED_PARTS = {"mass": 0.06, "cost": 15.0}
HARDWARE = {"mass": 0.03, "cost": 6.0}
MOTOR_MOUNT_MASS = 0.015


def prop_mass_kg(d_in: float) -> float:
    return 0.12e-3 * d_in ** 2          # hélice plegable carbono-nylon (11" ≈ 15 g, 22" ≈ 58 g)


def prop_cost(d_in: float) -> float:
    return 0.025 * d_in ** 2            # US$ por hélice (hoja BOM_Costos: par 11" ≈ 6, par 22" ≈ 25)


def esc_mass_kg(current_a: float) -> float:
    return 0.004 + 0.0006 * current_a   # por canal


def esc_cost(current_a: float) -> float:
    return 0.35 * current_a             # US$ por canal (60 A ≈ 21, 80 A ≈ 28)


@dataclass
class Design:
    vehicle: str
    rotors: int
    prop: str
    prop_diameter_in: float
    pitch_ratio: float
    battery: str
    kv: float
    motor_p_max_w: float
    motor_i_max_a: float
    esc_current_a: float
    mtow_kg: float
    masses: dict
    costs: dict
    bom_cost_usd: float
    wheelbase_m: float
    arm: dict
    checks: dict
    performance: dict
    inertia: dict
    sdf: dict = field(default_factory=dict)

    @property
    def feasible(self) -> bool:
        return all(c["ok"] for c in self.checks.values())

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate(vehicle: str, cfg: dict, geom: PropGeometry, pack: Pack, sf: dict, airs: dict[str, Air],
             tables: dict[str, PropTable], drag_area: float, avionics_w: float, battery_temps: dict) -> Design:
    n = cfg["rotors"]
    payload = cfg.get("payload_kg", 0.0)
    fixed_mass = sum(e["mass"] for e in cfg["fixed_equipment"].values())
    fixed_cost = sum(e["cost"] for e in cfg["fixed_equipment"].values())
    d_in = geom.diameter_m / INCH
    wb = wheelbase_m(geom.diameter_m, n)
    plates_mass, plates_cost, plates_dia = center_plates(wb, n)
    arm_len = wb / 2 - plates_dia / 2

    mtow = fixed_mass + payload + pack.mass_kg + 0.5
    for _ in range(40):
        sizing = size_motor(n, geom, pack, airs["thrust"], mtow, sf["thrust_to_weight"], sf["motor_current"],
                            tables["thrust"])
        motor = sizing.motor
        i_esc = motor.i_max * sf["esc_current"]
        tip_mass = motor.mass_kg + prop_mass_kg(d_in) + esc_mass_kg(i_esc) + MOTOR_MOUNT_MASS
        prop_end = Propulsion(n, motor, geom, pack, avionics_w, {})
        prop_end._tables[(round(airs["endurance"].density, 4), round(airs["endurance"].temperature_k, 1))] = tables["endurance"]
        hover_rpm = prop_end.hover(mtow, airs["endurance"])["rpm"]
        try:
            arm: ArmResult = select_arm(arm_len, sizing.thrust_per_rotor_n, tip_mass, hover_rpm, geom.blades, sf["structure"])
        except ValueError as e:
            raise Infeasible(str(e)) from e
        masses = {
            "equipo fijo": fixed_mass, "carga útil": payload, "batería": pack.mass_kg,
            "motores": n * motor.mass_kg, "hélices": n * prop_mass_kg(d_in), "ESC": n * esc_mass_kg(i_esc),
            "brazos": n * arm.mass_kg, "soportes de motor": n * MOTOR_MOUNT_MASS, "placas centrales": plates_mass,
            "piezas impresas y tornillería": PRINTED_PARTS["mass"] + HARDWARE["mass"],
        }
        new_mtow = sum(masses.values())
        if abs(new_mtow - mtow) < 1e-3:
            mtow = new_mtow
            break
        mtow = new_mtow
    else:
        raise Infeasible("la MTOW no converge (el dron crece sin límite)")

    costs = {
        "equipo fijo": fixed_cost, "batería": pack.cost_usd, "motores": n * motor.cost_usd,
        "hélices": n * prop_cost(d_in), "ESC": n * esc_cost(i_esc), "brazos": n * arm.cost_usd,
        "placas centrales": plates_cost, "piezas impresas y tornillería": PRINTED_PARTS["cost"] + HARDWARE["cost"],
    }
    bom = sum(costs.values())

    # --- Desempeño y verificaciones ---
    a_thr, a_end = airs["thrust"], airs["endurance"]
    propulsion = Propulsion(n, motor, geom, pack, avionics_w, {})
    propulsion._tables[(round(a_thr.density, 4), round(a_thr.temperature_k, 1))] = tables["thrust"]
    propulsion._tables[(round(a_end.density, 4), round(a_end.temperature_k, 1))] = tables["endurance"]
    mx_thr = propulsion.max_thrust(a_thr)
    hov = propulsion.hover(mtow, a_end)
    hov_hot = propulsion.hover(mtow, a_thr)
    e_eol = pack.usable_energy_wh(battery_temps["endurance"]) / sf["battery_capacity"]
    e_new = pack.usable_energy_wh(battery_temps["endurance"])
    e_cold = pack.usable_energy_wh(battery_temps["cold"])
    endurance_eol = e_eol * 60 / hov["p_total"]
    endurance_new = e_new * 60 / hov["p_total"]
    basis = cfg.get("endurance_basis", "eol")          # "eol" = batería al final de su vida, "new" = nueva
    endurance_req = endurance_eol if basis == "eol" else endurance_new
    basis_txt = "batería al final de su vida" if basis == "eol" else "batería nueva"
    lo, hi = cfg["hover_throttle_range"]
    twr = mx_thr["total_thrust"] / (mtow * G0)
    checks = {
        "TWR ≥ 2.0 a 5,000 msnm y 15 °C": {"value": round(twr, 2), "ok": twr >= sf["thrust_to_weight"] - 0.02},
        f"Autonomía en hover ≥ {cfg['hover_endurance_min']} min ({basis_txt}, 4,500 msnm, 0 °C)":
            {"value": round(endurance_req, 1), "ok": endurance_req >= cfg["hover_endurance_min"]},
        f"Empuje de hover entre {lo:.0%} y {hi:.0%} del máximo (4,500 msnm)":
            {"value": round(hov["thrust_fraction"], 2), "ok": lo <= hov["thrust_fraction"] <= hi},
        "Corriente de batería dentro del límite de las celdas":
            {"value": round(mx_thr["current_total"], 1), "limit": pack.i_max, "ok": mx_thr["current_total"] <= pack.i_max},
        "Brazos: resistencia (FS 2.5), deflexión y frecuencias": {"value": arm.label, "ok": True},
    }
    if n >= 6:
        motor_out = (n - 2) * mx_thr["thrust"] / (mtow * G0)   # perder un motor anula también su opuesto
        checks[f"Motor caído: {n - 2} rotores sostienen ≥ 1.1 × peso"] = {"value": round(motor_out, 2), "ok": motor_out >= 1.1}
    sea = airs["sea_level"]
    propulsion._tables.setdefault((round(sea.density, 4), round(sea.temperature_k, 1)), tables["sea_level"])
    hov_sea = propulsion.hover(mtow, sea)
    performance = {
        "endurance_dji_style_min": round(pack.energy_wh * 0.95 * 60 / hov_sea["p_total"], 1),
        "hover_power_w_4500m": round(hov["p_total"]), "hover_power_w_5000m_hot": round(hov_hot["p_total"]),
        "hover_rpm": round(hov["rpm"]), "hover_current_a": round(hov["current_total"], 1),
        "hover_motor_efficiency": round(hov["efficiency"], 3),
        "figure_of_merit": round(tables["endurance"].coefficients(hov["rpm"])["figure_of_merit"], 3),
        "endurance_new_min": round(e_new * 60 / hov["p_total"], 1),
        "endurance_eol_min": round(endurance_eol, 1),
        "endurance_cold_min": round(e_cold * 60 / hov["p_total"], 1),
        "max_thrust_total_kgf_5000m": round(mx_thr["total_thrust"] / G0, 2),
        "max_thrust_limit": mx_thr.get("limit"),
        "battery_energy_wh": round(pack.energy_wh, 1),
    }
    if cfg.get("delivery_distance_km"):
        dm = delivery_mission(propulsion, mtow - payload, payload, a_end, cfg["delivery_distance_km"] * 1000,
                              cfg["cruise_speed_ms"], drag_area, battery_temps["endurance"])
        dm_eol_margin = (e_eol if basis == "eol" else e_new) / dm["required_wh"] - 1
        checks[f"Entrega {cfg['delivery_distance_km']:g} km + regreso con 20 % de reserva ({basis_txt})"] = {
            "value": f"{dm_eol_margin:+.0%} de margen", "ok": dm_eol_margin >= 0}
        performance["delivery_mission"] = dm

    inertia = vehicle_inertia(n, wb / 2, tip_mass, arm.mass_kg,
                              fixed_mass + plates_mass + PRINTED_PARTS["mass"] + HARDWARE["mass"],
                              (plates_dia, plates_dia, 0.08), pack.mass_kg, payload)
    # Parámetros para el modelo de motor de Gazebo/PX4 (S05-01): T = kT·ω², Q = kQ·T
    omega_h = hov["rpm"] * 2 * 3.141592653589793 / 60
    sdf = {"motorConstant": hov["thrust"] / omega_h ** 2, "momentConstant": hov["torque"] / hov["thrust"],
           "maxRotVelocity": mx_thr["rpm"] * 2 * 3.141592653589793 / 60, "note": "valores a 4,500 msnm"}

    return Design(
        vehicle=vehicle, rotors=n, prop=geom.label + '"', prop_diameter_in=d_in, pitch_ratio=geom.pitch_ratio,
        battery=pack.label, kv=round(motor.kv), motor_p_max_w=round(motor.i_max * pack.v_nominal),
        motor_i_max_a=round(motor.i_max, 1), esc_current_a=round(i_esc, 1), mtow_kg=round(mtow, 3),
        masses={k: round(v, 3) for k, v in masses.items()}, costs={k: round(v, 1) for k, v in costs.items()},
        bom_cost_usd=round(bom, 1), wheelbase_m=round(wb, 3),
        arm={"tube": arm.label, "length_m": round(arm.length_m, 3), "stress_margin": round(arm.stress_margin, 2),
             "deflection_pct": round(arm.deflection_pct, 2), "f_natural_hz": round(arm.f_natural_hz, 1),
             "f_1p_hz": round(arm.f_1p_hz, 1), "f_2p_hz": round(arm.f_2p_hz, 1)},
        checks=checks, performance=performance, inertia=inertia, sdf=sdf)
