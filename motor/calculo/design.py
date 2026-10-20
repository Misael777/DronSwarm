"""M2 · Modelo analítico de un outrunner de flujo radial con bobinado concentrado (una bobina por diente).

Entrada: geometría y materiales (`Design`). Salida: Kv, resistencia, masa, costo de materiales y, en cada punto de
operación, corriente, pérdidas (cobre, hierro, imanes, rodamientos), eficiencia y temperatura del bobinado.

Corte (de adentro hacia afuera):  eje · rodamientos · tubo de la base · yugo del estator · ranuras con cobre ·
zapatas de los dientes · ENTREHIERRO g · imanes · yugo del rotor (anillo de acero) · campana.

Supuestos principales (los verifica el FEM de M4 y el banco de M8):
- Inducción en el entrehierro por circuito magnético con coeficiente de Carter y fuga del 8 %.
- Kv por la fuerza contraelectromotriz fundamental de línea (como mide un ESC: rpm en vacío / V de batería).
- Pérdidas en el hierro con la inducción de vacío (la reacción de armadura es chica en estos motores), corregidas por
  el borde cortado con láser y un factor de calibración K_IRON ajustado con el MN4006 (ver `calibrate_with_mn4006`).
- Pérdidas por corrientes parásitas en los imanes: 15 % de las del estator (bobinado concentrado), con imanes segmentados.
- Térmico de régimen permanente con la convección del chorro de la hélice, calibrado con la temperatura del MN4006
  a fondo (M5 lo reemplaza por una red térmica).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from motor.calculo.materials import COPPER, MAGNETS, PLASTICS, STEELS, laser_cut_factor
from motor.calculo.winding import layout

MU0 = 4e-7 * math.pi
K_LEAK = 0.92                   # fuga de flujo de los imanes
K_STACK = 0.95                  # factor de apilado de las láminas (aislante + adhesivo)
# Factor de calibración de las pérdidas en el hierro (catálogo × borde láser × este factor), ajustado con el MN4006
# reconstruido contra su tabla de banco y su corriente en vacío (calibrate_with_mn4006): da ~0.5. Se usa 0.6 y el
# informe de M2 muestra también el caso pesimista 1.0. Se mide con el anillo de prueba de láminas (M8).
K_IRON = 0.6
K_MAGNET_EDDY = 0.15            # pérdidas en imanes / pérdidas en el hierro del estator
K_SIX_STEP_CU = 1.03            # cobre: corriente de 6 pasos vs continua equivalente (ajustado con el MN4006)
H_TIP = 0.8e-3                  # altura de la zapata del diente
SLOT_OPENING = 1.6e-3           # abertura de ranura (pasa el alambre al bobinar a mano)
INSULATION = 0.15e-3            # papel/esmalte entre cobre y hierro
K_INS = 0.25                    # W/(m·K) del aislamiento impregnado
ROTOR_YOKE_B = 1.5              # T en el anillo de acero común del rotor
BELL_WALL = 0.0                 # el anillo del rotor ES la pared de la campana (sin pared extra)
CAP_THICK = {"DS-I": 3.0e-3, "DS-D": 4.0e-3}       # tapa impresa (PA12-CF) que lleva la hélice
BASE_THICK = {"DS-I": 4.0e-3, "DS-D": 5.0e-3}
SHAFT = {"DS-I": 4e-3, "DS-D": 6e-3}
BEARING = {"DS-I": {"name": "694ZZ (4×11×4)", "od": 11e-3, "mass": 0.0017, "cost": 1.5, "friction_nm": 4e-4},
           "DS-D": {"name": "696ZZ (6×15×5)", "od": 15e-3, "mass": 0.0035, "cost": 2.5, "friction_nm": 1.2e-3}}
HUB_WALL = 1.5e-3               # tubo de la base alrededor de los rodamientos
FIXED_MASS = {"DS-I": 0.004, "DS-D": 0.010}       # tornillos, cables de salida, conectores, adhesivo
FIXED_COST = {"DS-I": 2.5, "DS-D": 4.0}           # tornillos, conectores, epoxi, barniz, termocontraíble
STEEL_SHEET_WASTE = 2.5         # chapa comprada / chapa en la pieza (anidado de piezas redondas)
MAGNET_PIECE_COST = {"DS-I": 0.15, "DS-D": 0.45}  # mínimo por imán (compra de 100-500 piezas)
# Conductancia térmica efectiva / convección externa de la campana. Calibrada con el MN4006: a fondo con hélice 15×5
# a nivel del mar su superficie llega a 46 °C (25 °C de ambiente); K_THERMAL se resuelve para reproducirlo. El aire que circula por
# dentro del estator y la conducción al brazo multiplican por ~30 lo que daría solo la superficie externa. Ver
# `thermal_calibration()`; M5 lo reemplaza por una red térmica.
K_THERMAL = 29.3
T_RUNAWAY = 400.0               # tope numérico: por encima, el diseño ya está descartado


@dataclass(frozen=True)
class Design:
    vehicle: str
    ns: int
    pole_pairs: int
    d_stator: float             # diámetro exterior del estator [m]
    l_stack: float              # largo del paquete de láminas [m]
    gap: float                  # entrehierro mecánico [m]
    h_magnet: float             # espesor del imán [m]
    slot_depth_frac: float      # profundidad de ranura / radio del estator
    b_tooth: float              # inducción de diseño en el diente [T]
    b_yoke: float               # inducción de diseño en el yugo del estator [T]
    turns: int                  # vueltas por diente
    delta: bool                 # conexión triángulo (si no, estrella)
    steel: str = "NO20"
    magnet: str = "N52H"
    fill: float = 0.40          # relleno de ranura con bobinado a mano
    pole_arc: float = 0.85      # fracción del polo cubierta por imán
    rotor_steel: str = "DC01"
    print_plastic: str = "PA12-CF"


def geometry(d: Design) -> dict | None:
    """Dimensiones derivadas y flujo. None si la geometría no cierra (ranura negativa, etc.)."""
    w = layout(d.ns, d.pole_pairs)
    if w is None:
        return None
    mag = MAGNETS[d.magnet]
    r_s = d.d_stator / 2
    tau_s = 2 * math.pi * r_s / d.ns                               # paso de ranura en el entrehierro
    g_eff = d.gap + d.h_magnet / mag.mu_rec
    ratio = SLOT_OPENING / g_eff
    gamma = ratio ** 2 / (5 + ratio)
    k_carter = tau_s / (tau_s - gamma * g_eff)
    bg20 = K_LEAK * mag.br20 / (1 + mag.mu_rec * k_carter * d.gap / d.h_magnet)
    # diente y yugo dimensionados por flujo
    w_tooth = bg20 * tau_s / (d.b_tooth * K_STACK)
    tau_p = math.pi * d.d_stator / (2 * d.pole_pairs)
    phi_pole = d.pole_arc * bg20 * tau_p * d.l_stack
    h_yoke = phi_pole / 2 / (d.b_yoke * K_STACK * d.l_stack)
    h_slot = d.slot_depth_frac * r_s
    r_slot_top = r_s - H_TIP
    r_slot_bottom = r_slot_top - h_slot
    r_bore = r_slot_bottom - h_yoke
    a_slot = (math.pi * (r_slot_top ** 2 - r_slot_bottom ** 2) - d.ns * w_tooth * h_slot) / d.ns
    slot_w_bottom = 2 * math.pi * r_slot_bottom / d.ns - w_tooth
    if a_slot <= 0 or slot_w_bottom <= 0.5e-3 or r_bore <= 0 or w_tooth <= 0:
        return None
    # rotor
    r_mag_in = r_s + d.gap
    r_mag_out = r_mag_in + d.h_magnet
    h_ry = max(1.0e-3, phi_pole / 2 / (ROTOR_YOKE_B * d.l_stack))
    r_out = r_mag_out + h_ry + BELL_WALL
    # bobinado
    a_cond = d.fill * a_slot / (2 * d.turns)                       # sección de cobre de una vuelta
    coil_thick = a_slot * d.fill / (2 * max(h_slot, 1e-4)) + INSULATION
    l_turn = 2 * d.l_stack + 2 * w_tooth + math.pi * coil_thick + 4 * INSULATION
    overhang = coil_thick + 1.0e-3                                 # cabeza de bobina sobre el paquete, por lado
    n_series = d.ns * d.turns / 3                                  # vueltas en serie por fase
    b1 = 4 / math.pi * bg20 * math.sin(d.pole_arc * math.pi / 2)
    phi1 = 2 / math.pi * b1 * tau_p * d.l_stack * K_STACK
    lam = w["kw"] * n_series * phi1                                # enlace de flujo de fase (pico), imán a 20 °C
    ke_line = d.pole_pairs * lam * (1 if d.delta else math.sqrt(3))  # V·s/rad (pico de línea)
    kv = 60 / (2 * math.pi * ke_line)
    return {"winding": w, "k_carter": k_carter, "bg20": bg20, "w_tooth": w_tooth, "h_yoke": h_yoke, "h_slot": h_slot,
            "r_bore": r_bore, "a_slot": a_slot, "r_mag_in": r_mag_in, "r_mag_out": r_mag_out, "h_rotor_yoke": h_ry, "r_out": r_out,
            "a_cond": a_cond, "l_turn": l_turn, "overhang": overhang, "n_series": n_series, "ke_line_20": ke_line, "kv": kv,
            "phi_pole": phi_pole, "tau_p": tau_p, "slot_w_bottom": slot_w_bottom}


def resistance_line(d: Design, g: dict, t_c: float = 20.0) -> float:
    r_phase = COPPER.rho(t_c) * g["n_series"] * g["l_turn"] / g["a_cond"]
    return (2 / 3) * r_phase if d.delta else 2 * r_phase


def masses(d: Design, g: dict) -> dict:
    steel = STEELS[d.steel]
    r_s = d.d_stator / 2
    teeth = d.ns * g["w_tooth"] * g["h_slot"] * d.l_stack
    tips = (2 * math.pi * r_s - d.ns * SLOT_OPENING) * H_TIP * d.l_stack
    yoke = math.pi * ((g["r_bore"] + g["h_yoke"]) ** 2 - g["r_bore"] ** 2) * d.l_stack
    m_teeth = (teeth + tips) * steel.density * K_STACK
    m_yoke = yoke * steel.density * K_STACK
    m_cu = d.ns * d.turns * g["a_cond"] * g["l_turn"] * COPPER.density
    m_mag = d.pole_arc * math.pi * (g["r_mag_out"] ** 2 - g["r_mag_in"] ** 2) * d.l_stack * MAGNETS[d.magnet].density
    m_ry = math.pi * (g["r_out"] ** 2 - g["r_mag_out"] ** 2) * (d.l_stack + 2e-3) * STEELS[d.rotor_steel].density
    pl = PLASTICS[d.print_plastic]
    cap = math.pi * g["r_out"] ** 2 * CAP_THICK[d.vehicle] * pl.density * 0.6         # tapa con rayos (60 % lleno)
    base = math.pi * (g["r_bore"] + 4e-3) ** 2 * BASE_THICK[d.vehicle] * pl.density
    hub = math.pi * (g["r_bore"] ** 2 - (BEARING[d.vehicle]["od"] / 2) ** 2) * (d.l_stack + 2 * g["overhang"]) * pl.density
    shaft_len = d.l_stack + 2 * g["overhang"] + CAP_THICK[d.vehicle] + BASE_THICK[d.vehicle] + 12e-3
    m_shaft = math.pi * (SHAFT[d.vehicle] / 2) ** 2 * shaft_len * 7850
    m_bear = 2 * BEARING[d.vehicle]["mass"]
    parts = {"estator (dientes)": m_teeth, "estator (yugo)": m_yoke, "cobre": m_cu, "imanes": m_mag, "yugo del rotor": m_ry,
             "tapa impresa": cap, "base impresa": base + max(hub, 0), "eje": m_shaft, "rodamientos": m_bear,
             "tornillos, cables, adhesivo": FIXED_MASS[d.vehicle]}
    parts["total"] = sum(parts.values())
    return parts


def material_cost(d: Design, g: dict, m: dict) -> dict:
    steel = STEELS[d.steel]
    n_mag = 2 * d.pole_pairs * (2 if d.l_stack > 15e-3 else 1)    # imanes largos en 2 piezas (segmentado)
    c = {"acero eléctrico": (m["estator (dientes)"] + m["estator (yugo)"]) * STEEL_SHEET_WASTE * steel.price_usd_kg,
         "acero del rotor": m["yugo del rotor"] * STEEL_SHEET_WASTE * STEELS[d.rotor_steel].price_usd_kg,
         "imanes": max(m["imanes"] * MAGNETS[d.magnet].price_usd_kg * 1.3, n_mag * MAGNET_PIECE_COST[d.vehicle]),
         "cobre": m["cobre"] * 1.3 * COPPER.price_usd_kg,
         "filamento": (m["tapa impresa"] + m["base impresa"]) * 1.2 * PLASTICS[d.print_plastic].price_usd_kg,
         "eje": 1.0 if d.vehicle == "DS-I" else 2.0,
         "rodamientos": 2 * BEARING[d.vehicle]["cost"],
         "varios": FIXED_COST[d.vehicle]}
    c["total"] = sum(c.values())
    c["n_magnets"] = n_mag
    return c


def iron_loss(d: Design, g: dict, m: dict, rpm: float) -> float:
    steel = STEELS[d.steel]
    f = d.pole_pairs * rpm / 60
    p_t = m["estator (dientes)"] * steel.loss_w_per_kg(d.b_tooth, f) * laser_cut_factor(g["w_tooth"] * 1e3)
    p_y = m["estator (yugo)"] * steel.loss_w_per_kg(d.b_yoke, f) * laser_cut_factor(g["h_yoke"] * 1e3, both_edges=False)
    return (p_t + p_y) * K_IRON


def convection_h(v: float, density: float) -> float:
    """Coeficiente de convección forzada [W/(m²·K)] sobre la campana (aire a v m/s, densidad de altura)."""
    return 12.0 * math.sqrt(max(v, 0.5)) * (density / 1.225) ** 0.6


def operate(d: Design, g: dict, m: dict, torque: float, rpm: float, thrust_n: float, prop_d_m: float, density: float,
            t_amb: float = 20.0, iters: int = 6) -> dict:
    """Punto de operación con temperatura de régimen permanente acoplada (R y el imán dependen de la temperatura)."""
    mag = MAGNETS[d.magnet]
    omega = rpm * 2 * math.pi / 60
    # aire sobre el motor: velocidad inducida de la hélice (teoría de momento) + giro de la campana
    v_ind = math.sqrt(max(thrust_n, 0) / (2 * density * math.pi * (prop_d_m / 2) ** 2))
    v_air = math.hypot(v_ind, 0.3 * omega * g["r_out"])
    height = d.l_stack + 2 * g["overhang"] + CAP_THICK[d.vehicle]
    area = 2 * math.pi * g["r_out"] * height + math.pi * g["r_out"] ** 2
    r_conv = 1 / (convection_h(v_air, density) * area * K_THERMAL)
    lining = d.ns * (2 * g["h_slot"] + g["slot_w_bottom"]) * d.l_stack
    r_ins = INSULATION / (K_INS * lining)
    p_fe = iron_loss(d, g, m, rpm)
    p_mag = K_MAGNET_EDDY * p_fe
    p_bear = BEARING[d.vehicle]["friction_nm"] * omega
    t_w = t_amb + 30
    for _ in range(iters * 4):
        t_m = min(t_w - 15, T_RUNAWAY)
        ke = g["ke_line_20"] * (1 + mag.alpha_br * (t_m - 20))
        p_nl = p_fe * (1 + mag.alpha_br * (t_m - 20)) ** 2 + p_mag + p_bear
        i = (torque + p_nl / max(omega, 1e-6)) / ke
        r = resistance_line(d, g, min(t_w, T_RUNAWAY))
        p_cu = K_SIX_STEP_CU * i * i * r
        t_case = t_amb + (p_cu + p_nl) * r_conv
        t_w_new = min(t_case + p_cu * r_ins, T_RUNAWAY)
        if abs(t_w_new - t_w) < 0.2:
            t_w = t_w_new
            break
        t_w = t_w + 0.6 * (t_w_new - t_w)                          # amortiguado: R y el imán dependen de T
    v_line = omega * ke + i * r
    p_shaft = torque * omega
    p_in = p_shaft + p_cu + p_nl
    return {"rpm": rpm, "torque": torque, "current": i, "voltage": v_line, "p_in": p_in, "p_shaft": p_shaft,
            "p_copper": p_cu, "p_iron": p_fe, "p_magnet": p_mag, "p_bearing": p_bear, "efficiency": p_shaft / p_in,
            "t_winding": t_w, "t_case": t_case, "t_magnet": t_w - 15, "current_density": i / g["a_cond"] / 1e6 * (1 / math.sqrt(3) if d.delta else 1),
            "f_electrical": d.pole_pairs * rpm / 60}


def demag_margin(d: Design, g: dict, i_peak: float, t_mag: float) -> float:
    """Campo inverso máximo de la armadura en el imán / coercitividad intrínseca a esa temperatura (debe ser < 0.7)."""
    mag = MAGNETS[d.magnet]
    i_coil = i_peak / (math.sqrt(3) if d.delta else 1)
    h_rev = d.turns * i_coil * 1.5 / (2 * (d.h_magnet + mag.mu_rec * d.gap))      # ×1.5: pico de corriente en conmutación
    h_magnet = mag.br(t_mag) / (MU0 * mag.mu_rec) * (d.gap / (d.h_magnet + d.gap))  # campo propio de trabajo (desmagnetizante)
    return (h_rev + h_magnet) / (mag.hcj(t_mag) * 1e3)


def summary(d: Design) -> dict:
    g = geometry(d)
    if g is None:
        return {"design": asdict(d), "valid": False}
    m = masses(d, g)
    return {"design": asdict(d), "valid": True, "geometry": g, "mass": m, "cost": material_cost(d, g, m),
            "r_line_20": resistance_line(d, g, 20.0)}


# MN4006 reconstruido desde su ficha (18N24P, estator 40×6 mm, Ø44.35 mm, Kv 380, 194 mΩ): láminas de 0.2 mm, dientes a 1.9 T
MN4006_RECON = Design("DS-I", 18, 12, 40e-3, 6e-3, 0.3e-3, 1.0e-3, 0.30, 1.9, 1.5, 10, False, steel="NO20", fill=0.42)
# M6C12 reconstruido (24N28P, estator 62×12 mm, Ø72 mm, Kv 150, 90 mΩ). Sin tabla de banco: solo ficha.
M6C12_RECON = Design("DS-D", 24, 14, 62e-3, 12e-3, 0.4e-3, 2.0e-3, 0.25, 1.75, 1.5, 5, False, steel="NO20", fill=0.42)
RECON = {"DS-I": MN4006_RECON, "DS-D": M6C12_RECON}


def calibrate_with_mn4006(bench: list[dict], eta_esc: float = 0.95) -> dict:
    """Error del modelo (con las constantes actuales) contra la tabla de banco y la corriente en vacío del MN4006."""
    d = MN4006_RECON
    g = geometry(d)
    m = masses(d, g)
    rows = []
    for b in bench:
        op = operate(d, g, m, b["torque_nm"], b["rpm"], b["thrust_g"] * 9.81e-3, 15 * 0.0254, 1.20, 25.0)
        rows.append({"throttle": b["throttle"], "current_model_a": round(op["p_in"] / eta_esc / 24, 2), "current_meas_a": b["current_a"]})
    err = [(r["current_model_a"] - r["current_meas_a"]) / r["current_meas_a"] for r in rows]
    nl = operate(d, g, m, 0.0, 380 * 21.9, 0.0, 15 * 0.0254, 1.20, 25.0)
    return {"rows": rows, "current_error_rms_pct": round(100 * math.sqrt(sum(e * e for e in err) / len(err)), 1),
            "noload_current_model_a": round(nl["current"], 3), "noload_current_datasheet_a": 0.3, "eta_esc_assumed": eta_esc}


def thermal_calibration() -> dict:
    """Temperatura de superficie del MN4006 reconstruido a fondo (15×5, nivel del mar) contra los 46 °C del fabricante."""
    d = MN4006_RECON
    g = geometry(d)
    m = masses(d, g)
    op = operate(d, g, m, 0.40, 6177, 2228 * 9.81e-3, 15 * 0.0254, 1.20, 25.0)
    return {"t_case_model_c": round(op["t_case"], 1), "t_case_bench_c": 46.0, "t_winding_model_c": round(op["t_winding"], 1),
            "losses_w": round(op["p_in"] - op["p_shaft"], 1)}
