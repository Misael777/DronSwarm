#!/usr/bin/env python3
"""M6 · CAD del motor desde el diseño elegido (M2) → cad/openscad/motor/<dron>_motor_params.scad + exportes.

Escribe los parámetros y los contornos EXACTOS de la lámina (los mismos de la FEM de M4) y exporta con OpenSCAD:
  DXF (cortadora láser):  lámina del estator, anillo del rotor
  STL (impresora 3D):     tapa (lleva la hélice), base (rodamientos + montaje DMI), plantilla de imanes, mandril de
                          apilado, soporte de bobinado; y el ensamble completo para ver.
Salidas en cad/exports/motor/<dron>/.

    .venv/bin/python motor/fabricacion/gen_cad.py
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from motor.calculo.design import BASE_THICK, BEARING, CAP_THICK, H_TIP, SHAFT, SLOT_OPENING  # noqa: E402
from motor.docs.gen_partes import halves  # noqa: E402

SCAD_DIR = ROOT / "cad" / "openscad" / "motor"
OUT = ROOT / "cad" / "exports" / "motor"
INF = ROOT / "motor" / "informes"
ROTOR_SHEET_MM = 1.0             # chapa de acero común para los anillos del rotor
STATOR_SHEET_MM = 0.2
FIT = {"press": -0.03, "slide": 0.10, "print_clear": 0.20}       # ajustes [mm] (la impresora agranda/achica: calibrar)

# ---- Normalizados (verificar contra el catálogo del proveedor elegido) ----
BRG = {"DS-I": {"name": "694ZZ", "d": 4.0, "D": 11.0, "B": 4.0, "Da": 9.6, "da": 5.4, "r": 0.15},     # ISO 15, hombros ISO
       "DS-D": {"name": "696ZZ", "d": 6.0, "D": 15.0, "B": 5.0, "Da": 13.4, "da": 7.6, "r": 0.2}}
CLIP = {"DS-I": {"name": "DIN 6799-3.2", "groove_d": 3.2, "m": 0.64, "s": 0.6, "od": 7.3, "n": 1.0},   # anillo E (eje 4-5 mm)
        "DS-D": {"name": "DIN 6799-5", "groove_d": 5.0, "m": 0.74, "s": 0.7, "od": 11.3, "n": 1.2}}    # (eje 6-8 mm)
SHIM = {"DS-I": {"name": "DIN 988 4×8×0.3", "d": 4.0, "D": 8.0, "t": 0.3},                          # arandela de ajuste
        "DS-D": {"name": "DIN 988 6×12×0.5", "d": 6.0, "D": 12.0, "t": 0.5}}
WAVE = {"DS-I": {"name": "DIN 137 B4 (ondulada)", "d": 4.3, "D": 9.0, "h_free": 1.0, "h_work": 0.6},  # precarga de rodamientos
        "DS-D": {"name": "DIN 137 B6 (ondulada)", "d": 6.4, "D": 11.0, "h_free": 1.3, "h_work": 0.8}}
INSERT = {"DS-I": {"name": "inserto roscado M3 × 3 (corto)", "thread": "M3", "hole": 4.0, "depth": 4.2, "clear": 3.4, "head_d": 5.5},
          "DS-D": {"name": "inserto roscado M4 × 4 (corto)", "thread": "M4", "hole": 5.6, "depth": 5.0, "clear": 4.5, "head_d": 7.0}}
FLAT = {"DS-I": 0.3, "DS-D": 0.5}                 # plano del eje (bloqueo de giro de la tapa en el agujero en D)
WIRE_D = {"DS-I": 1.7, "DS-D": 2.7}               # cable de silicona 18 / 14 AWG con aislante [mm]
CLEAR_END_TURNS = 0.8                             # aire entre cabezas de bobina y piezas impresas [mm]
CHAMFER = 0.5                                     # chaflán de aristas de piezas impresas [mm]
LEAD_IN = 0.4                                     # chaflán de entrada de asientos de rodamiento [mm]
# Ajustes de diseño (medida nominal del agujero = nominal de la pieza + ajuste). La impresora suma HOLE_COMP: calibrar con
# la probeta de ajustes (probeta_ajustes.stl) y cambiar HOLE_COMP; las medidas nominales de los planos NO cambian.
FITS = {"bearing_seat": -0.05,   # aro exterior en plástico: apriete ligero (tipo N7 para plástico)
        "stator_on_tube": 0.10,  # estator sobre el tubo: juego para el epoxi
        "ring_in_skirt": 0.20,   # anillo del rotor en la pollera de la tapa: juego para el epoxi
        "shaft_in_cap": 0.00,    # eje en la tapa: agujero en D escariado a medida + adhesivo retenedor
        "key": 0.10}             # chaveta del tubo en la muesca de las láminas
HOLE_COMP = 0.15                 # FDM: los agujeros salen más chicos (se suma al diámetro de todo agujero impreso)


def mech(veh: str, p: dict, g_h_yoke: float) -> dict:
    """Alturas (z = 0 en la cara de montaje de la base) y medidas mecánicas derivadas [mm]."""
    b, c, sh, w, ins = BRG[veh], CLIP[veh], SHIM[veh], WAVE[veh], INSERT[veh]
    base_t = max(p["base_t"], ins["depth"] + 1.2)
    h_low = sh["t"] + c["m"] + c["n"] + 0.4                        # espacio bajo el rodamiento inferior: arandela + anillo E
    z_s0 = base_t + p["overhang"] + CLEAR_END_TURNS               # cara inferior del paquete del estator
    z_s1 = z_s0 + p["l_stack"]
    z_tube = z_s1                                                  # el tubo termina a ras del estator
    z_g1 = h_low - sh["t"] - c["m"]                                # ranura inferior (cara de abajo)
    shaft_bot = z_g1 - c["n"]
    z_sp = z_tube + sh["t"] + w["h_work"]                          # cara inferior del espigón de la tapa
    z_cap = z_s1 + p["overhang"] + CLEAR_END_TURNS
    t_plateau = max(p["cap_t"], ins["depth"] + 1.0)
    z_pt = z_cap + t_plateau                                       # cara superior (apoyo de la hélice)
    recess = sh["t"] + c["s"] + 0.3                                # rebaje para arandela + anillo E superiores (quedan al ras)
    z_rb = z_pt - recess
    z_g2 = z_rb + sh["t"]                                          # ranura superior (cara de abajo)
    shaft_top = z_g2 + c["m"] + c["n"]
    z_r0, z_r1 = z_s0 - 1.0, z_s1 + 1.0                            # anillo del rotor (L + 2 mm, centrado)
    return {"bearing": b, "clip": c, "shim": sh, "wave": w, "insert": ins, "base_t": base_t, "h_low": h_low,
            "z_s0": z_s0, "z_s1": z_s1, "z_tube": z_tube, "z_g1": z_g1, "z_g2": z_g2, "shaft_bot": shaft_bot, "shaft_top": shaft_top,
            "shaft_len": shaft_top - shaft_bot, "z_sp": z_sp, "z_cap": z_cap, "t_plateau": t_plateau, "z_pt": z_pt, "z_rb": z_rb,
            "z_r0": z_r0, "z_r1": z_r1, "flat": FLAT[veh], "wire_d": WIRE_D[veh], "h_yoke": g_h_yoke,
            "r_tube": p["r_bore"] - FITS["stator_on_tube"] / 2, "r_shoulder": p["r_bore"] + 0.6 * g_h_yoke,
            "r_flange": max(p["r_bore"] + 5, p["dmi"]["pcd"] / 2 + ins["hole"] / 2 + 3),
            "r_plateau": p["prop"]["pcd"] / 2 + ins["hole"] / 2 + 2.5}
DMI = {"DS-I": {"bolt": 3.2, "pcd": 25.0, "n": 4}, "DS-D": {"bolt": 4.2, "pcd": 35.0, "n": 4}}
PROP_MOUNT = {"DS-I": {"bolt": 3.2, "pcd": 16.0, "n": 4}, "DS-D": {"bolt": 4.2, "pcd": 25.0, "n": 4}}   # ajustar a la hélice


def slot_polygon(ns: int, k: int, r_s: float, w: float, h_slot: float, b0: float, n_arc: int = 6) -> list[tuple[float, float]]:
    """Contorno de la ranura k (cobre + abertura) en mm, igual que en motor/fem/fem2d.py."""
    r_t = r_s - H_TIP * 1e3
    r_b = r_t - h_slot
    phi_k = 2 * math.pi * k / ns
    phi_n = 2 * math.pi * (k + 1) / ns
    phi_s = (phi_k + phi_n) / 2

    def p(r, a):
        return (round(r * math.cos(a), 4), round(r * math.sin(a), 4))
    a_b1, a_t1 = phi_k + math.asin(w / 2 / r_b), phi_k + math.asin(w / 2 / r_t)
    a_b2, a_t2 = phi_n - math.asin(w / 2 / r_b), phi_n - math.asin(w / 2 / r_t)
    o_t1, o_t2 = phi_s - math.asin(b0 / 2 / r_t), phi_s + math.asin(b0 / 2 / r_t)
    o_s1, o_s2 = phi_s - math.asin(b0 / 2 / (r_s + 0.5)), phi_s + math.asin(b0 / 2 / (r_s + 0.5))
    pts = [p(r_b, a_b1), p(r_t, a_t1)]
    pts += [p(r_t, a_t1 + (o_t1 - a_t1) * i / n_arc) for i in range(1, n_arc + 1)]
    pts += [p(r_s + 0.5, o_s1), p(r_s + 0.5, o_s2)]
    pts += [p(r_t, o_t2 + (a_t2 - o_t2) * i / n_arc) for i in range(0, n_arc)]
    pts += [p(r_t, a_t2), p(r_b, a_b2)]
    pts += [p(r_b, a_b2 + (a_b1 - a_b2) * i / (3 * n_arc)) for i in range(1, 3 * n_arc)]
    k2 = 2 + n_arc + 2 + n_arc + 1                        # índice de la esquina (r_b, a_b2)
    return round_corner(round_corner(pts, k2), 0)


def round_corner(pts: list, i: int, r: float = 0.3, n: int = 4) -> list:
    """Reemplaza el vértice i por un arco aproximado (Bézier cuadrática tangente a los dos lados, a distancia r)."""
    p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]

    def towards(a, b, dist):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        k = min(dist, L / 2) / L
        return (a[0] + dx * k, a[1] + dy * k)
    a, b = towards(p1, p0, r), towards(p1, p2, r)
    arc = [tuple(round((1 - t) ** 2 * a[c] + 2 * t * (1 - t) * p1[c] + t ** 2 * b[c], 4) for c in (0, 1))
           for t in [k / n for k in range(n + 1)]]
    return pts[:i] + arc + pts[i + 1:]


def params(veh: str, c: dict) -> dict:
    d, g = c["design"], c["geometry"]
    mm = 1e3
    n_lam = round(d["l_stack"] * mm / STATOR_SHEET_MM * 0.95)       # factor de apilado 0.95
    n_ring = math.ceil((d["l_stack"] * mm + 2) / ROTOR_SHEET_MM)
    return {"veh": veh, "ns": d["ns"], "poles": 2 * d["pole_pairs"], "r_s": d["d_stator"] / 2 * mm, "l_stack": d["l_stack"] * mm,
            "r_bore": g["r_bore"] * mm, "w_tooth": g["w_tooth"] * mm, "h_slot": g["h_slot"] * mm, "h_tip": H_TIP * mm,
            "b0": SLOT_OPENING * mm, "gap": d["gap"] * mm, "r_mag_in": g["r_mag_in"] * mm, "r_mag_out": g["r_mag_out"] * mm,
            "r_out": (g["r_out"] + g["r_mag_out"] * (1 / math.cos(math.pi / (2 * d["pole_pairs"])) - 1)) * mm, "h_magnet": d["h_magnet"] * mm, "pole_arc": d["pole_arc"], "overhang": g["overhang"] * mm,
            "turns": d["turns"], "delta": d["delta"], "coils": c["coils"],
            "shaft": SHAFT[veh] * mm, "bearing_od": BEARING[veh]["od"] * mm, "bearing_w": 4.0 if veh == "DS-I" else 5.0,
            "cap_t": CAP_THICK[veh] * mm, "base_t": BASE_THICK[veh] * mm, "n_lam": n_lam, "n_ring": n_ring,
            "ring_sheet": ROTOR_SHEET_MM, "magnet_w": d["pole_arc"] * 2 * math.pi * g["r_mag_in"] * mm / (2 * d["pole_pairs"]),
            "dmi": DMI[veh], "prop": PROP_MOUNT[veh], "h_yoke_g": g["h_yoke"] * mm}


def write_params(p: dict, path: Path) -> None:
    slots = [slot_polygon(p["ns"], k, p["r_s"], p["w_tooth"], p["h_slot"], p["b0"]) for k in range(p["ns"])]
    L = [f"// GENERADO por motor/fabricacion/gen_cad.py desde motor/informes/M2_elegidos.json ({p['veh']}). No editar a mano.",
         f"// Estator {p['ns']} ranuras, rotor {p['poles']} polos, {p['turns']} vueltas/diente en {'triángulo' if p['delta'] else 'estrella'}. Unidades: mm.",
         ""]
    for k, v in p.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool) and k not in ("base_t",):
            L.append(f"{k} = {round(v, 4)};")
    m = p["mech"]
    L.append("// --- mecánica (gen_cad.mech) ---")
    for k, v in m.items():
        if isinstance(v, dict):
            pre = {"bearing": "brg", "clip": "clip", "shim": "shim", "wave": "wave", "insert": "ins"}[k]
            for kk, vv in v.items():
                if isinstance(vv, (int, float)):
                    L.append(f"{pre}_{kk} = {round(vv, 4)};")
        elif isinstance(v, (int, float)):
            L.append(f"{k} = {round(v, 4)};")
    for k, v in FITS.items():
        L.append(f"fit_{k} = {v};")
    L += [f"hole_comp = {HOLE_COMP}; chamfer = {CHAMFER}; lead_in = {LEAD_IN};", "key_w = 2.0; key_depth = 1.2;",
          f"wire_ch_w = {round(3 * m['wire_d'] + 1.0, 2)}; wire_ch_d = {round(min(2.5, m['base_t'] - 1.5), 2)};",
          f"skirt_l = {round(2.0 + m['z_cap'] - m['z_r1'], 3)};"]
    L += [f"delta = {'true' if p['delta'] else 'false'};",
          f"dmi_bolt = {p['dmi']['bolt']}; dmi_pcd = {p['dmi']['pcd']}; dmi_n = {p['dmi']['n']};",
          f"prop_bolt = {p['prop']['bolt']}; prop_pcd = {p['prop']['pcd']}; prop_n = {p['prop']['n']};",
          f"fit_press = {FIT['press']}; fit_slide = {FIT['slide']}; print_clear = {FIT['print_clear']};",
          f'coils = "{p["coils"]}";   // fase de cada diente (mayúscula +, minúscula −)', "",
          "slots = ["] + [f"  {[list(q) for q in s]}," for s in slots] + ["];", "",
          "halves = ["] + [f"  {h}," for h in halves(p["ns"], p["r_s"], p["w_tooth"], p["h_slot"])] + ["];", ""]
    path.write_text("\n".join(L))


LIB = r"""// Biblioteca mecánica del motor DronSwarm (M6). Medidas de <dron>_motor_params.scad (generado). Unidades: mm.
// z = 0 en la cara de montaje de la base. Sin hull/minkowski (CLAUDE.md): perfiles de revolución, polígonos y extrusiones.
// Ajustes y cadena de tolerancias: motor/fabricacion/tolerancias.md. Agujeros impresos: nominal + hole_comp (calibrar).
$fn = 120;
r_t = r_s - h_tip;  r_b = r_t - h_slot;
function hd(d) = d + hole_comp;                           // diámetro a modelar para un agujero impreso
R_seat = hd(brg_D + fit_bearing_seat) / 2;
R_sh = (brg_Da - 0.2) / 2;
R_bore_cap = hd(shaft + fit_shaft_in_cap) / 2;
R_skirt_in = hd(2 * r_out + fit_ring_in_skirt) / 2;
r_cap = r_out + fit_ring_in_skirt / 2 + 1.6;
R_sp = wave_D / 2;
R_rec = hd(shim_D + 0.6) / 2;
half_pitch = 180 / ns;
pole_half = 180 / poles;

// ===================== LÁSER (DXF) =====================
module stator_lamination_2d() {           // 0.20 mm NO20. Esquinas de ranura con radio 0.3 (incluido en "slots")
    difference() {
        circle(r = r_s);
        circle(r = r_bore);
        for (s = slots) polygon(s);
        translate([r_bore - 0.01, -key_w / 2]) square([key_depth, key_w]);              // muesca de chaveta
    }
}
module rotor_ring_2d() {                  // 1.0 mm DC01. Interior poligonal: una cara plana por imán (asiento y ubicación)
    apo = r_mag_out + 0.05;                                                           // 0.05: juego para el epoxi
    difference() {
        circle(r = r_out);
        rotate(pole_half) circle(r = apo / cos(pole_half), $fn = poles);              // caras planas centradas en los polos
        for (a = [0, 180]) rotate(a + pole_half) translate([r_out, 0]) circle(r = 0.5, $fn = 24);   // muescas de alineación
        rotate(pole_half) translate([r_out - 0.6, -0.4]) square([0.8, 0.8]);          // marca del polo 1 (orientación)
    }
}

// ===================== PERFILES DE REVOLUCIÓN =====================
module base_body() {
    ch = chamfer;
    rotate_extrude() polygon([
        [R_seat + lead_in, 0], [r_flange - ch, 0], [r_flange, ch], [r_flange, base_t - ch], [r_flange - ch, base_t],
        [r_shoulder, base_t], [r_shoulder, z_s0], [r_tube, z_s0], [r_tube, z_tube - 0.3], [r_tube - 0.3, z_tube],
        [R_seat + lead_in, z_tube], [R_seat, z_tube - lead_in], [R_seat, z_tube - brg_B], [R_sh, z_tube - brg_B],
        [R_sh, h_low + brg_B], [R_seat, h_low + brg_B], [R_seat, lead_in]]);
}
module base() {                           // PETG/ASA/PA-CF. Imprimir con la brida sobre la cama
    difference() {
        union() {
            base_body();
            for (a = [0]) rotate(a) translate([r_tube - 0.3, -(key_w - fit_key) / 2, z_s0])   // chaveta del estator
                cube([key_depth - 0.2 + 0.3, key_w - fit_key, z_tube - z_s0 - 0.5]);
        }
        for (i = [0 : dmi_n - 1]) rotate(360 / dmi_n * i + 45)                         // insertos roscados desde abajo
            translate([dmi_pcd / 2, 0, -0.01]) cylinder(d = hd(ins_hole), h = ins_depth);
        for (i = [0 : dmi_n - 1]) rotate(360 / dmi_n * i + 45)
            translate([dmi_pcd / 2, 0, -0.01]) cylinder(d1 = hd(ins_hole) + 0.8, d2 = hd(ins_hole), h = 0.4);
        // canal de los 3 cables de fase, con chaflán en los bordes
        rotate(180) translate([r_tube - 1.5, -wire_ch_w / 2, base_t - wire_ch_d]) cube([r_flange, wire_ch_w, wire_ch_d + 1]);
        rotate(180) for (sgn = [-1, 1]) translate([r_tube - 1.5, sgn * wire_ch_w / 2, base_t]) rotate([45 * sgn, 0, 0])
            translate([0, -0.4, -0.4]) cube([r_flange, 0.8, 0.8]);
        if (r_tube - R_sh > 7) for (i = [0 : 5]) rotate(30 + 60 * i)                    // alivianado (DS-D)
            translate([(r_tube + R_sh) / 2, 0, base_t + 1.0]) cylinder(d = r_tube - R_sh - 3.0, h = z_tube);
    }
}

module cap_body() {
    ch = chamfer;
    rotate_extrude() polygon([
        [R_bore_cap, z_sp], [R_sp, z_sp], [R_sp, z_cap], [r_mag_in + 0.3, z_cap], [r_mag_in + 0.3, z_r1],
        [R_skirt_in, z_r1], [R_skirt_in, z_r1 - skirt_l + lead_in], [R_skirt_in + lead_in, z_r1 - skirt_l],
        [r_cap - ch, z_r1 - skirt_l], [r_cap, z_r1 - skirt_l + ch], [r_cap, z_cap + cap_t - ch], [r_cap - ch, z_cap + cap_t],
        [r_plateau, z_cap + cap_t], [r_plateau, z_pt - ch], [r_plateau - ch, z_pt], [R_rec, z_pt], [R_rec, z_rb],
        [R_bore_cap, z_rb]]);
}
module cap() {                            // tapa: hélice + eje (agujero en D) + anillo del rotor. Imprimir boca abajo
    difference() {
        union() {
            cap_body();
            // plano del agujero en D: bloquea el giro de la tapa sobre el eje
            intersection() {
                translate([0, 0, z_sp]) cylinder(r = R_bore_cap + 0.01, h = z_rb - z_sp);
                translate([shaft / 2 - flat + hole_comp / 2, -10, z_sp]) cube([10, 20, z_rb - z_sp]);
            }
        }
        for (i = [0 : prop_n - 1]) rotate(360 / prop_n * i + 45)                     // insertos de la hélice (desde arriba)
            translate([prop_pcd / 2, 0, z_pt - ins_depth]) cylinder(d = hd(ins_hole), h = ins_depth + 0.01);
        for (i = [0 : prop_n - 1]) rotate(360 / prop_n * i + 45)
            translate([prop_pcd / 2, 0, z_pt - 0.4]) cylinder(d1 = hd(ins_hole), d2 = hd(ins_hole) + 0.8, h = 0.41);
        for (i = [0 : 5]) rotate(60 * i)                                                // ventilación
            translate([0, 0, z_cap - 0.01]) linear_extrude(cap_t + 0.02) polygon(concat(
                [for (a = [-20 : 5 : 20]) [(r_plateau + 1.2) * cos(a), (r_plateau + 1.2) * sin(a)]],
                [for (a = [20 : -5 : -20]) [(r_mag_in - 1.2) * cos(a), (r_mag_in - 1.2) * sin(a)]]));
    }
}

module shaft_part() {                     // acero plata h6, ranuras DIN 6799, plano para la tapa, chaflanes 0.3 × 45°
    R = shaft / 2; Rg = clip_groove_d / 2; c0 = 0.3;
    difference() {
        rotate_extrude($fn = 64) polygon([
            [0, shaft_bot], [R - c0, shaft_bot], [R, shaft_bot + c0], [R, z_g1], [Rg, z_g1], [Rg, z_g1 + clip_m], [R, z_g1 + clip_m],
            [R, z_g2], [Rg, z_g2], [Rg, z_g2 + clip_m], [R, z_g2 + clip_m], [R, shaft_top - c0], [R - c0, shaft_top], [0, shaft_top]]);
        translate([R - flat, -R - 1, z_sp]) cube([R, 2 * R + 2, z_rb - z_sp]);
    }
}

// ===================== NORMALIZADOS (para el ensamble) =====================
module bearing_part() {                   // rodamiento rígido de bolas con tapas ZZ
    t = (brg_D - brg_d) / 2;
    rotate_extrude($fn = 64) {
        translate([brg_d / 2, 0]) square([t * 0.32, brg_B]);
        translate([brg_D / 2 - t * 0.32, 0]) square([t * 0.32, brg_B]);
        translate([brg_d / 2 + t * 0.32, 0.15]) square([t * 0.36, 0.25]);
        translate([brg_d / 2 + t * 0.32, brg_B - 0.4]) square([t * 0.36, 0.25]);
    }
}
module washer(d, D, t) { linear_extrude(t) difference() { circle(d = D, $fn = 48); circle(d = d, $fn = 32); } }
module e_clip() {
    linear_extrude(clip_s) difference() {
        circle(d = clip_od, $fn = 48); circle(d = clip_groove_d, $fn = 32);
        polygon([[0, 0], [clip_od, -clip_od * 0.45], [clip_od, clip_od * 0.45]]);
    }
}
module insert_part() { color("#c9a227") cylinder(d = ins_hole + 0.2, h = ins_depth - 1.0, $fn = 24); }

// ===================== BOBINADO Y ROTOR (para el ensamble) =====================
module coil_end(j) {
    phi = 360 * j / ns;
    intersection() {
        difference() { circle(r = r_t - 0.25); circle(r = r_b + 0.25); }
        polygon([[0, 0], [2 * r_s * cos(phi - half_pitch * 0.98), 2 * r_s * sin(phi - half_pitch * 0.98)],
                 [2 * r_s * cos(phi), 2 * r_s * sin(phi)], [2 * r_s * cos(phi + half_pitch * 0.98), 2 * r_s * sin(phi + half_pitch * 0.98)]]);
    }
}
module winding() {
    for (j = [0 : ns - 1]) {
        ph = coils[j];
        col = (ph == "A" || ph == "a") ? "#2a78d6" : (ph == "B" || ph == "b") ? "#eb6834" : "#1baf7a";
        color(col) {
            translate([0, 0, z_s0]) linear_extrude(l_stack) offset(r = -0.12) {
                polygon(halves[2 * j]); polygon(halves[2 * ((j - 1 + ns) % ns) + 1]);
            }
            translate([0, 0, z_s0 - overhang + 0.2]) linear_extrude(overhang - 0.2) offset(r = -0.12) coil_end(j);
            translate([0, 0, z_s1]) linear_extrude(overhang - 0.2) offset(r = -0.12) coil_end(j);
        }
    }
}
module magnets() {                        // bloques planos apoyados en las caras del anillo poligonal
    for (k = [0 : poles - 1]) rotate(360 * k / poles)
        color(k % 2 == 0 ? "#d55181" : "#6250d6")
            translate([r_mag_out - h_magnet, -magnet_w / 2, z_s0]) cube([h_magnet, magnet_w, l_stack]);
}

// ===================== ÚTILES (impresos) =====================
module magnet_jig() {                     // peine: centra cada imán en su cara plana (polaridad alternada: ver brújula)
    rib = 2 * (r_mag_out - h_magnet) * tan(pole_half) - magnet_w;
    difference() {
        union() {
            cylinder(r = r_mag_out - h_magnet - 0.15, h = l_stack + 4);
            for (i = [0 : poles - 1]) rotate(360 / poles * (i + 0.5))
                translate([r_mag_out - h_magnet - 0.5, -max(rib - 0.15, 0.5) / 2, 0]) cube([h_magnet + 0.3, max(rib - 0.15, 0.5), l_stack + 4]);
        }
        translate([0, 0, -1]) cylinder(r = r_mag_out - h_magnet - 3, h = l_stack + 6);
    }
}
module ring_glue_jig() {                  // concentricidad: centra el anillo (por su exterior) con el eje de la tapa (por el agujero)
    h = z_r1 - z_r0 - 1;
    difference() {
        union() { cylinder(r = r_out + 3, h = 3); cylinder(r = r_out + 3, h = 3 + h); }
        translate([0, 0, 3]) cylinder(r = hd(2 * r_out + 0.05) / 2, h = h + 1);       // copa: aloja el anillo
    }
    cylinder(d = shaft - 0.02, h = 3 + h + (z_pt - z_r1) + 6);                         // perno: entra en el agujero de la tapa
}
module stack_mandrel() {                  // apilado de láminas: chaveta + varilla M5 para prensar
    difference() {
        union() {
            cylinder(r = r_bore - 0.05, h = l_stack + 10);
            translate([r_bore - 0.3, -(key_w - fit_key) / 2, 0]) cube([key_depth - 0.2 + 0.3, key_w - fit_key, l_stack + 10]);
            cylinder(r = r_s + 3, h = 3);
        }
        translate([0, 0, -1]) cylinder(d = hd(5.0), h = l_stack + 12);
    }
}
module winding_holder() {                 // sujeta el estator por el agujero y la chaveta; mango para la morsa
    union() {
        cylinder(r = r_bore - 0.1, h = l_stack + 2);
        translate([r_bore - 0.4, -(key_w - fit_key) / 2, 0]) cube([key_depth - 0.2 + 0.4, key_w - fit_key, l_stack + 2]);
        translate([0, 0, -40]) cylinder(r = 7, h = 40);
    }
}
module fit_coupon() {                     // probeta de ajustes: imprimir y probar rodamiento, eje e inserto; elegir hole_comp
    offs = [-0.10, -0.05, 0.00, 0.05, 0.10, 0.15];
    difference() {
        translate([0, 0, 0]) cube([len(offs) * (brg_D + 5) + 4, 2 * (brg_D + 6), 6]);
        for (i = [0 : len(offs) - 1]) {
            x = 2 + (brg_D + 5) * (i + 0.5);
            translate([x, brg_D / 2 + 4, -0.1]) cylinder(d = brg_D + fit_bearing_seat + offs[i], h = 6.2);
            translate([x, 1.5 * brg_D + 8, -0.1]) cylinder(d = shaft + offs[i], h = 6.2);
            translate([x - 1.5, 0.6, 5.4]) linear_extrude(0.7) text(str(offs[i] * 100), size = 2.2, halign = "center");
        }
    }
}

// ===================== ENSAMBLE =====================
module stator_stack() { color("#9aa0a6") translate([0, 0, z_s0]) linear_extrude(l_stack) stator_lamination_2d(); }
module rotor_ring() { color("#4a4a4a") translate([0, 0, z_r0]) linear_extrude(z_r1 - z_r0) rotor_ring_2d(); }
module keep_half() { translate([-200, -400, -50]) cube([400, 400, 400]); }      // conserva y < 0 (corte por el plano XZ)
module show(col, cut) {                   // cada pieza se corta y se pasa a malla por separado: el corte se ve con colores
    if (cut) color(col) render(convexity = 8) intersection() { children(); keep_half(); }
    else color(col) children();
}
module assembly(explode = 0, cut = false) {
    e = explode;
    show("#f2a65a", cut) base();
    for (i = [0 : dmi_n - 1]) show("#c9a227", cut) rotate(360 / dmi_n * i + 45) translate([dmi_pcd / 2, 0, 0.6 - e * 0.3]) insert_part();
    show("#c0c4c8", cut) translate([0, 0, h_low - e * 0.6]) bearing_part();
    show("#c0c4c8", cut) translate([0, 0, z_tube - brg_B + e * 0.2]) bearing_part();
    show("#8a8f94", cut) translate([0, 0, h_low - shim_t - e * 0.8]) washer(shim_d, shim_D, shim_t);
    show("#5f6368", cut) translate([0, 0, z_g1 - e * 1.0]) e_clip();
    show("#9aa0a6", cut) translate([0, 0, e * 0.6]) stator_stack();
    translate([0, 0, e * 0.6]) if (cut) render(convexity = 8) intersection() { winding(); keep_half(); } else winding();
    show("#8a8f94", cut) translate([0, 0, z_tube + e * 1.0]) washer(shim_d, shim_D, shim_t);
    show("#b0b4b8", cut) translate([0, 0, z_tube + shim_t + e * 1.1]) washer(wave_d, wave_D, wave_h_work);
    show("#3a3a3a", cut) translate([0, 0, e * 1.6]) rotor_ring();
    translate([0, 0, e * 1.6]) if (cut) render(convexity = 8) intersection() { magnets(); keep_half(); } else magnets();
    show("#eb6834", cut) translate([0, 0, e * 1.6]) cap();
    for (i = [0 : prop_n - 1]) show("#c9a227", cut) translate([0, 0, e * 1.6]) rotate(360 / prop_n * i + 45)
        translate([prop_pcd / 2, 0, z_pt - ins_depth + 0.2]) insert_part();
    show("#8a8f94", cut) translate([0, 0, z_rb + e * 2.0]) washer(shim_d, shim_D, shim_t);
    show("#5f6368", cut) translate([0, 0, z_g2 + e * 2.1]) e_clip();
    show("#d9d9d9", cut) translate([0, 0, e * 0.3]) shaft_part();
}
"""

PARTS = {"lamina_estator": ("stator_lamination_2d();", "dxf"), "anillo_rotor": ("rotor_ring_2d();", "dxf"),
         "tapa": ("rotate([180, 0, 0]) cap();", "stl"), "base": ("base();", "stl"), "eje": ("shaft_part();", "stl"),
         "plantilla_imanes": ("magnet_jig();", "stl"), "util_concentricidad": ("ring_glue_jig();", "stl"),
         "mandril_apilado": ("stack_mandrel();", "stl"), "soporte_bobinado": ("winding_holder();", "stl"),
         "probeta_ajustes": ("fit_coupon();", "stl"), "ensamble": ("assembly();", "stl")}
RENDERS = {"ensamble": ("assembly();", "0,0,12,60,0,30,{d}"), "corte": ("assembly(cut = true);", "0,0,12,90,0,180,{c}"),
           "explosionado": ("assembly(explode = 12, cut = true);", "0,0,30,80,0,160,{d}")}


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--veh", help="DS-I o DS-D (por defecto los dos)")
    ap.add_argument("--parts", help="piezas separadas por coma (por defecto todas)")
    ap.add_argument("--no-renders", action="store_true")
    a = ap.parse_args()
    chosen = json.loads((INF / "M2_elegidos.json").read_text())
    SCAD_DIR.mkdir(parents=True, exist_ok=True)
    (SCAD_DIR / "motor_lib.scad").write_text(LIB)
    old = json.loads((OUT / "resumen.json").read_text()) if (OUT / "resumen.json").exists() else {}
    summary = dict(old)
    only = set(a.parts.split(",")) if a.parts else None
    for veh, c in chosen.items():
        if a.veh and veh != a.veh:
            continue
        key = veh.lower().replace("-", "_")
        p = params(veh, c)
        p["mech"] = mech(veh, p, p["h_yoke_g"])
        write_params(p, SCAD_DIR / f"{key}_motor_params.scad")
        out = OUT / veh.lower()
        out.mkdir(parents=True, exist_ok=True)
        files = dict(old.get(veh, {}).get("files", {}))
        for part, (call, ext) in PARTS.items():
            if only and part not in only:
                continue
            scad = SCAD_DIR / f"{key}_{part}.scad"
            scad.write_text(f"// {veh} · {part} (M6). Generado por motor/fabricacion/gen_cad.py\n"
                            f"include <{key}_motor_params.scad>\ninclude <motor_lib.scad>\n{call}\n")
            dst = out / f"{part}.{ext}"
            r = subprocess.run(["openscad", "-o", str(dst), str(scad)], capture_output=True, text=True, timeout=1800)
            if r.returncode != 0 or not dst.exists() or "WARNING" in r.stderr and "undefined" in r.stderr:
                raise SystemExit(f"OpenSCAD falló en {scad.name}:\n{r.stderr[-2500:]}")
            files[part] = str(dst.relative_to(ROOT))
        if not a.no_renders and (not only or "renders" in only):
            dia = 2.6 * p["r_out"]
            for name, (call, cam) in RENDERS.items():
                scad = SCAD_DIR / f"{key}_vista_{name}.scad"
                scad.write_text(f"include <{key}_motor_params.scad>\ninclude <motor_lib.scad>\n{call}\n")
                dst = out / f"vista_{name}.png"
                ortho = ["--projection=o"] if name == "corte" else []
                subprocess.run(["openscad", "-o", str(dst), "--imgsize=1600,1100", f"--camera={cam.format(d=round(dia * 3.2), c=round(dia * 1.25))}",
                                "--colorscheme=Tomorrow", *ortho, str(scad)], capture_output=True, text=True, timeout=1800)
                files[f"vista_{name}"] = str(dst.relative_to(ROOT))
        summary[veh] = {"params": {k: v for k, v in p.items() if k not in ("dmi", "prop")}, "files": files}
        print(veh, "→", out)
    (OUT / "resumen.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
