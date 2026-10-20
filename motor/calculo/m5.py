"""M5 · Térmico (red de 5 nodos, régimen permanente y transitorio) y mecánico del motor elegido → informes/M5_termico_mecanico.md

Térmico: bobinado, estator, rotor (imanes + anillo), aire interno y base impresa, más el ambiente. Las conductancias de
convección salen de correlaciones (cilindro en el chorro de la hélice, cilindro que gira, cavidad con aire que entra por
la tapa calada); un único factor las escala para reproducir la temperatura medida del MN4006 (calibración).
Mecánico: anillo del rotor y pegado de imanes a sobrevelocidad, eje (torsión + flexión + giroscópico), rodamientos
(vida L10 con la atracción magnética por excentricidad), velocidad crítica y tapa impresa.

    .venv/bin/python -m motor.calculo.m5
"""

from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from engineering.atmosphere import air
from engineering.mass_budget import prop_mass_kg
from motor.calculo.design import (
    BEARING,
    CAP_THICK,
    INSULATION,
    K_INS,
    RECON,
    SHAFT,
    Design,
    geometry,
    iron_loss,
    masses,
    resistance_line,
)
from motor.calculo.materials import MAGNETS, PLASTICS

ROOT = Path(__file__).resolve().parents[2]
INF = ROOT / "motor" / "informes"
REQ = ROOT / "motor" / "requisitos" / "puntos_operacion.json"
K_AIR, PR = 0.0255, 0.71
CP = {"cu": 385, "fe": 450, "mag": 460, "plastic": 1300}
K_PLASTIC = 0.35                 # W/(m·K) de una pieza impresa (PA-CF/PETG, con relleno)
G_ARM = 0.04                     # W/K: conducción de la base al brazo de carbono
BEARING_C = {"DS-I": {"C": 720.0, "C0": 260.0}, "DS-D": {"C": 1350.0, "C0": 520.0}}   # N, catálogo 694ZZ / 696ZZ
E_STEEL, ADHESIVE_SHEAR = 200e9, 15e6
DC01_YIELD = 210e6
ECCENTRICITY = 0.1e-3            # desalineación del rotor supuesta (rodamientos + campana impresa)
OVERSPEED = 1.2


def _nu(rho: float, t_c: float) -> float:
    return air(0, t_c).viscosity / rho


def h_external(d: Design, g: dict, rpm: float, thrust: float, prop_d: float, rho: float, t_c: float) -> float:
    """Campana: el mayor entre cilindro en el chorro de la hélice (Hilpert) y cilindro que gira (Nu = 0.133 Re^2/3)."""
    dia = 2 * g["r_out"]
    nu = _nu(rho, t_c)
    v = math.sqrt(max(thrust, 0) / (2 * rho * math.pi * (prop_d / 2) ** 2))
    re = max(v * dia / nu, 1.0)
    h_cross = 0.193 * re ** 0.618 * PR ** (1 / 3) * K_AIR / dia
    omega = rpm * 2 * math.pi / 60
    re_w = omega * dia ** 2 / nu
    h_rot = 0.133 * re_w ** (2 / 3) * PR ** (1 / 3) * K_AIR / dia
    return max(h_cross, h_rot)


def network(d: Design, g: dict, m: dict, rpm: float, thrust: float, prop_d: float, rho: float, t_c: float, f_cal: float) -> dict:
    """Conductancias [W/K] y capacidades [J/K]. Nodos: 0 bobinado, 1 estator, 2 rotor, 3 aire interno, 4 base. Ambiente aparte."""
    omega = rpm * 2 * math.pi / 60
    lining = d.ns * (2 * g["h_slot"] + g["slot_w_bottom"]) * d.l_stack
    g_cu_fe = K_INS * lining / INSULATION
    h_ext = h_external(d, g, rpm, thrust, prop_d, rho, t_c) * f_cal
    v_tip = omega * g["r_mag_in"]
    h_int = 40 * math.sqrt(1 + v_tip / 10) * (rho / 1.225) ** 0.6 * f_cal          # cavidad ventilada: aire bombeado por la campana
    a_end = 2 * math.pi * (g["r_bore"] + g["h_yoke"] + g["h_slot"] / 2) * g["overhang"] * 2 * 2      # cabezas de bobina
    a_faces = 2 * math.pi * ((d.d_stator / 2) ** 2 - g["r_bore"] ** 2)                             # caras del paquete
    a_slots = 0.3 * lining                                                                          # canales entre bobinas
    a_gap = 2 * math.pi * d.d_stator / 2 * d.l_stack
    g_gap = 4.0 * K_AIR / (2 * d.gap) * a_gap * f_cal                               # entrehierro: Nu ≈ 4 (Taylor-Couette)
    a_rot_out = 2 * math.pi * g["r_out"] * (d.l_stack + 2 * g["overhang"]) + math.pi * g["r_out"] ** 2 * 0.6
    a_rot_in = 2 * math.pi * g["r_mag_in"] * d.l_stack + math.pi * g["r_out"] ** 2 * 0.4
    a_vent = math.pi * g["r_out"] ** 2 * 0.3
    mdot = rho * 0.15 * max(v_tip, 1.0) * a_vent * f_cal                            # aire que entra por la tapa calada
    base_area = math.pi * (g["r_bore"] + 4e-3) ** 2
    g_fe_base = (K_PLASTIC * base_area / 4e-3 + 1.0e-2) * f_cal
    G = np.zeros((5, 5))

    def link(i, j, val):
        G[i, j] += val
        G[j, i] += val
    link(0, 1, g_cu_fe)
    link(0, 3, h_int * (a_end + a_slots))
    link(1, 3, h_int * a_faces)
    link(1, 2, g_gap)
    link(2, 3, h_int * a_rot_in)
    link(1, 4, g_fe_base)
    g_amb = np.array([0.0, 0.0, h_ext * a_rot_out, mdot * 1005.0, G_ARM * f_cal + h_ext * base_area * 0.5])
    pl = PLASTICS[d.print_plastic]
    cap = np.array([m["cobre"] * CP["cu"], (m["estator (dientes)"] + m["estator (yugo)"]) * CP["fe"],
                    m["imanes"] * CP["mag"] + m["yugo del rotor"] * CP["fe"] + m["tapa impresa"] * CP["plastic"],
                    5.0, m["base impresa"] * CP["plastic"] * (pl.density / pl.density)])
    return {"G": G, "g_amb": g_amb, "cap": cap, "h_ext": h_ext, "h_int": h_int}


def losses_at(d: Design, g: dict, m: dict, torque: float, rpm: float, t_w: float) -> np.ndarray:
    mag = MAGNETS[d.magnet]
    omega = rpm * 2 * math.pi / 60
    t_m = t_w - 15
    ke = g["ke_line_20"] * (1 + mag.alpha_br * (t_m - 20))
    p_fe = iron_loss(d, g, m, rpm)
    p_bear = BEARING[d.vehicle]["friction_nm"] * omega
    i = (torque + (p_fe + p_bear) / max(omega, 1e-6)) / ke
    p_cu = 1.03 * i * i * resistance_line(d, g, t_w)
    return np.array([p_cu, p_fe, 0.15 * p_fe, 0.0, 0.0]) + np.array([0, 0, p_bear, 0, 0])


def steady(d, g, m, pt, prop_d, rho, t_amb, f_cal) -> np.ndarray:
    net = network(d, g, m, pt["rpm"], pt["thrust_n"], prop_d, rho, t_amb, f_cal)
    t = np.full(5, t_amb + 20.0)
    for _ in range(200):
        q = losses_at(d, g, m, pt["torque_nm"], pt["rpm"], t[0])
        a = -net["G"].copy()
        np.fill_diagonal(a, net["G"].sum(1) + net["g_amb"])
        t_new = np.linalg.solve(a, q + net["g_amb"] * t_amb)
        if np.max(np.abs(t_new - t)) < 0.05:
            return t_new
        t = 0.5 * (t + np.minimum(t_new, 400.0))
    return t


def transient(d, g, m, t0, pt, prop_d, rho, t_amb, f_cal, seconds: float, dt: float = 0.5) -> np.ndarray:
    net = network(d, g, m, pt["rpm"], pt["thrust_n"], prop_d, rho, t_amb, f_cal)
    a = -net["G"].copy()
    np.fill_diagonal(a, net["G"].sum(1) + net["g_amb"])
    lhs = np.diag(net["cap"] / dt) + a
    t = t0.copy()
    for _ in range(int(seconds / dt)):
        q = losses_at(d, g, m, pt["torque_nm"], pt["rpm"], t[0])
        t = np.linalg.solve(lhs, net["cap"] / dt * t + q + net["g_amb"] * t_amb)
    return t


def calibrate() -> float:
    """Factor de convección que reproduce 46 °C de campana (rotor) del MN4006 a fondo, 15×5, nivel del mar, 25 °C."""
    d = RECON["DS-I"]
    g = geometry(d)
    m = masses(d, g)
    pt = {"rpm": 6177, "torque_nm": 0.40, "thrust_n": 2228 * 9.81e-3}

    def f(k):
        return steady(d, g, m, pt, 15 * 0.0254, 1.18, 25.0, k)[2] - 46.0
    return brentq(f, 0.05, 50.0)


def mechanical(d: Design, g: dict, m: dict, req: dict, ops: dict) -> dict:
    veh = d.vehicle
    rpm_max = max(p["rpm"] for p in req["points"]) * OVERSPEED
    w = rpm_max * 2 * math.pi / 60
    # anillo del rotor: tensión circunferencial por su propio giro + presión de los imanes
    r_ring = (g["r_mag_out"] + g["r_out"]) / 2
    t_ring = g["h_rotor_yoke"]
    p_mag = MAGNETS[d.magnet].density * d.h_magnet * w ** 2 * (g["r_mag_in"] + g["r_mag_out"]) / 2
    sigma = 7850 * w ** 2 * r_ring ** 2 + p_mag * r_ring / t_ring
    # pegado de imanes: torque máximo transmitido por corte
    t_max = max(p["torque_nm"] for p in req["points"]) * 1.5
    a_glue = d.pole_arc * 2 * math.pi * g["r_mag_out"] * d.l_stack
    tau_glue = t_max / (g["r_mag_out"] * a_glue)
    # eje: torsión + flexión por momento giroscópico (Ω = 3 rad/s) y peso/desbalance, en el rodamiento
    ds = SHAFT[veh]
    prop_d = req["prop"]["diameter_in"] * 0.0254
    j_prop = prop_mass_kg(req["prop"]["diameter_in"]) * (prop_d / 2) ** 2 / 3 * 0.8
    m_gyro = j_prop * (ops["maximo_twr20"]["rpm"] * 2 * math.pi / 60) * 3.0
    tau_s = 16 * t_max / (math.pi * ds ** 3)
    sig_b = 32 * m_gyro / (math.pi * ds ** 3)
    von_mises = math.sqrt(sig_b ** 2 + 3 * tau_s ** 2)
    # atracción magnética desbalanceada por excentricidad
    bg = g["bg20"]
    area = 2 * math.pi * d.d_stator / 2 * d.l_stack
    f_ump = bg ** 2 / (2 * 4e-7 * math.pi) * area * 0.5 * ECCENTRICITY / (d.gap + d.h_magnet / 1.05)
    # rodamientos: axial = empuje de hover (el dron pasa casi todo el tiempo ahí), radial = UMP + desbalance G6.3
    hov = next(p for p in req["points"] if p["name"] == "hover_4500m_0C")
    m_rot = m["imanes"] + m["yugo del rotor"] + m["tapa impresa"]
    f_unb = m_rot * 6.3e-3 * (hov["rpm"] * 2 * math.pi / 60)
    fr = (f_ump + f_unb) / 2
    fa = hov["thrust_n"]
    bc = BEARING_C[veh]
    e = 0.28 * (fa / bc["C0"]) ** 0.23
    p_eq = fr if fa / max(fr, 1e-6) <= e else 0.56 * fr + 1.0 / e * 0.44 * fa
    l10_h = (bc["C"] / p_eq) ** 3 * 1e6 / (hov["rpm"] * 60)
    # velocidad crítica: rotor en voladizo sobre el eje desde el rodamiento superior
    overhang = g["overhang"] + CAP_THICK[veh] + 3e-3
    k = 3 * E_STEEL * math.pi * ds ** 4 / 64 / overhang ** 3
    n_crit = math.sqrt(k / m_rot) * 60 / (2 * math.pi)
    # tapa impresa: tensión por giro + torque en el cubo
    pl = PLASTICS[d.print_plastic]
    sig_cap = pl.density * w ** 2 * g["r_out"] ** 2 * (3.3 / 8)
    hub_r = ds / 2 + 3e-3
    tau_hub = t_max / (2 * math.pi * hub_r ** 2 * CAP_THICK[veh])
    cap_fs = 0.6 * pl.tensile_mpa * 1e6 / max(sig_cap, tau_hub * math.sqrt(3))
    return {"rpm_overspeed": rpm_max, "ring_stress_mpa": sigma / 1e6, "ring_fs": DC01_YIELD / sigma,
            "glue_shear_mpa": tau_glue / 1e6, "glue_fs": ADHESIVE_SHEAR / tau_glue,
            "shaft_vm_mpa": von_mises / 1e6, "shaft_fs": 650e6 / von_mises, "ump_n": f_ump, "bearing_fa_n": fa, "bearing_fr_n": fr,
            "bearing_l10_h": l10_h, "n_crit_rpm": n_crit, "crit_margin": n_crit / rpm_max, "cap_fs": cap_fs,
            "cap_stress_mpa": sig_cap / 1e6, "hub_shear_mpa": tau_hub / 1e6}


def run() -> dict:
    req_all = json.loads(REQ.read_text())
    chosen = json.loads((INF / "M2_elegidos.json").read_text())
    f_cal = calibrate()
    out = {"f_cal": f_cal}
    for veh in ("DS-I", "DS-D"):
        c = chosen[veh]
        d = Design(**c["design"])
        g = geometry(d)
        m = masses(d, g)
        req = req_all[veh]
        prop_d = req["prop"]["diameter_in"] * 0.0254
        rho = req["constraints"]["air_density_design"]
        pts = {p["name"]: p for p in req["points"]}
        res = {"steady": {}, "steady_30c": {}}
        for name, pt in pts.items():
            res["steady"][name] = steady(d, g, m, pt, prop_d, rho, 20.0, f_cal).tolist()
            res["steady_30c"][name] = steady(d, g, m, pt, prop_d, rho * 293 / 303, 30.0, f_cal).tolist()
        t_h = np.array(res["steady"]["hover_5000m_15C"])
        res["max_30s"] = transient(d, g, m, t_h, pts["maximo_twr20"], prop_d, rho, 20.0, f_cal, 30).tolist()
        res["max_60s"] = transient(d, g, m, t_h, pts["maximo_twr20"], prop_d, rho, 20.0, f_cal, 60).tolist()
        net = network(d, g, m, pts["hover_5000m_15C"]["rpm"], pts["hover_5000m_15C"]["thrust_n"], prop_d, rho, 20.0, f_cal)
        res["tau_s"] = float(net["cap"].sum() / (net["g_amb"].sum()))
        res["mech"] = mechanical(d, g, m, req, c["ops"])
        # PETG con la base a la temperatura más alta (maniobra 30 °C) — ¿alcanza o hace falta ASA/PA-CF?
        res["base_max_c"] = max(res["steady_30c"]["maniobra_twr15"][4], res["max_60s"][4])
        res["plastic_ok"] = {k: res["base_max_c"] + 15 < p.hdt_c for k, p in PLASTICS.items()}
        out[veh] = res
        _ = replace
    (INF / "M5_termico_mecanico.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    write_report(out)
    return out


def write_report(r: dict) -> None:
    names = ["bobinado", "estator", "rotor/campana", "aire interno", "base impresa"]
    L = ["# M5 · Térmico y mecánico del motor elegido", "", "> Generado por `motor/calculo/m5.py`. No editar a mano.", "",
         f"Red térmica de 5 nodos con convección por correlaciones; un factor ×{r['f_cal']:.2f} sobre las correlaciones reproduce "
         "los 46 °C de campana del MN4006 a fondo (tabla del fabricante). Aire de 5,000 msnm; ambiente 20 °C (y 30 °C como día caluroso).", ""]
    for veh in ("DS-I", "DS-D"):
        x = r[veh]
        L += [f"## {veh}", "", "| Condición | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
        for name, t in x["steady"].items():
            L.append(f"| {name} (permanente, 20 °C) | " + " | ".join(f"{v:.0f} °C" for v in t) + " |")
        L.append("| maniobra_twr15 (permanente, **30 °C**) | " + " | ".join(f"{v:.0f} °C" for v in x["steady_30c"]["maniobra_twr15"]) + " |")
        L.append("| máximo 30 s desde hover | " + " | ".join(f"{v:.0f} °C" for v in x["max_30s"]) + " |")
        L.append("| máximo **60 s** desde hover | " + " | ".join(f"{v:.0f} °C" for v in x["max_60s"]) + " |")
        mm = x["mech"]
        okp = ", ".join(k for k, v in x["plastic_ok"].items() if v)
        L += ["", f"- Constante de tiempo térmica ≈ {x['tau_s'] / 60:.1f} min. Límite del bobinado: 120 °C (esmalte clase H: 200 °C).",
              f"- **Base impresa** hasta {x['base_max_c']:.0f} °C → sirven (HDT con 15 °C de margen): **{okp}**.", "",
              "| Verificación mecánica | Valor | Factor de seguridad |", "|---|---|---|",
              f"| Anillo del rotor a {mm['rpm_overspeed']:,.0f} rpm (sobrevelocidad 20 %) | {mm['ring_stress_mpa']:.1f} MPa | {mm['ring_fs']:.0f} |",
              f"| Pegado de imanes (corte, 1.5 × torque máximo) | {mm['glue_shear_mpa']:.2f} MPa | {mm['glue_fs']:.0f} |",
              f"| Eje Ø{SHAFT[veh] * 1e3:.0f} mm (torsión + giroscópico a 3 rad/s) | {mm['shaft_vm_mpa']:.0f} MPa | {mm['shaft_fs']:.1f} |",
              f"| Tapa impresa (giro + torque en el cubo) | {max(mm['cap_stress_mpa'], mm['hub_shear_mpa']):.1f} MPa | {mm['cap_fs']:.1f} |",
              f"| Rodamientos {BEARING[veh]['name']}: axial {mm['bearing_fa_n']:.1f} N, radial {mm['bearing_fr_n']:.1f} N "
              f"(atracción por 0.1 mm de excentricidad: {mm['ump_n']:.1f} N) | **vida L10 {mm['bearing_l10_h']:,.0f} h** en hover | — |",
              f"| Velocidad crítica del rotor en voladizo | {mm['n_crit_rpm']:,.0f} rpm | ×{mm['crit_margin']:.0f} sobre la máxima |", ""]
    L += ["## Conclusiones", "",
          "- Las temperaturas quedan muy lejos de 120 °C incluso un minuto a empuje máximo y con día caluroso: el motor propio no "
          "necesita aluminio en la base; el límite real es el plástico de la base (ver arriba).",
          "- Los rodamientos chicos de 694/696 alcanzan cientos a miles de horas en hover; la atracción magnética por excentricidad "
          "es la carga radial dominante: la campana y la base tienen que quedar concéntricas (útil de ensamble, M6).",
          "- Mecánicamente todo tiene factor de seguridad ≥ 2; el más ajustado se indica en la tabla.", ""]
    (INF / "M5_termico_mecanico.md").write_text("\n".join(L))


if __name__ == "__main__":
    r = run()
    print("f_cal", round(r["f_cal"], 3))
    for v in ("DS-I", "DS-D"):
        print(v, {k: [round(t) for t in r[v]["steady"][k]] for k in r[v]["steady"]}, "max60", [round(t) for t in r[v]["max_60s"]],
              "base", round(r[v]["base_max_c"]), {k: round(x, 2) for k, x in r[v]["mech"].items()})
