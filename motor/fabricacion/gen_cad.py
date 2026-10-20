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

SCAD_DIR = ROOT / "cad" / "openscad" / "motor"
OUT = ROOT / "cad" / "exports" / "motor"
INF = ROOT / "motor" / "informes"
ROTOR_SHEET_MM = 1.0             # chapa de acero común para los anillos del rotor
STATOR_SHEET_MM = 0.2
FIT = {"press": -0.03, "slide": 0.10, "print_clear": 0.20}       # ajustes [mm] (la impresora agranda/achica: calibrar)
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
    return pts


def params(veh: str, c: dict) -> dict:
    d, g = c["design"], c["geometry"]
    mm = 1e3
    n_lam = round(d["l_stack"] * mm / STATOR_SHEET_MM * 0.95)       # factor de apilado 0.95
    n_ring = math.ceil((d["l_stack"] * mm + 2) / ROTOR_SHEET_MM)
    return {"veh": veh, "ns": d["ns"], "poles": 2 * d["pole_pairs"], "r_s": d["d_stator"] / 2 * mm, "l_stack": d["l_stack"] * mm,
            "r_bore": g["r_bore"] * mm, "w_tooth": g["w_tooth"] * mm, "h_slot": g["h_slot"] * mm, "h_tip": H_TIP * mm,
            "b0": SLOT_OPENING * mm, "gap": d["gap"] * mm, "r_mag_in": g["r_mag_in"] * mm, "r_mag_out": g["r_mag_out"] * mm,
            "r_out": g["r_out"] * mm, "h_magnet": d["h_magnet"] * mm, "pole_arc": d["pole_arc"], "overhang": g["overhang"] * mm,
            "turns": d["turns"], "delta": d["delta"], "coils": c["coils"],
            "shaft": SHAFT[veh] * mm, "bearing_od": BEARING[veh]["od"] * mm, "bearing_w": 4.0 if veh == "DS-I" else 5.0,
            "cap_t": CAP_THICK[veh] * mm, "base_t": BASE_THICK[veh] * mm, "n_lam": n_lam, "n_ring": n_ring,
            "ring_sheet": ROTOR_SHEET_MM, "magnet_w": d["pole_arc"] * 2 * math.pi * g["r_mag_in"] * mm / (2 * d["pole_pairs"]),
            "dmi": DMI[veh], "prop": PROP_MOUNT[veh]}


def write_params(p: dict, path: Path) -> None:
    slots = [slot_polygon(p["ns"], k, p["r_s"], p["w_tooth"], p["h_slot"], p["b0"]) for k in range(p["ns"])]
    L = [f"// GENERADO por motor/fabricacion/gen_cad.py desde motor/informes/M2_elegidos.json ({p['veh']}). No editar a mano.",
         f"// Estator {p['ns']} ranuras, rotor {p['poles']} polos, {p['turns']} vueltas/diente en {'triángulo' if p['delta'] else 'estrella'}. Unidades: mm.",
         ""]
    for k, v in p.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            L.append(f"{k} = {round(v, 4)};")
    L += [f"delta = {'true' if p['delta'] else 'false'};",
          f"dmi_bolt = {p['dmi']['bolt']}; dmi_pcd = {p['dmi']['pcd']}; dmi_n = {p['dmi']['n']};",
          f"prop_bolt = {p['prop']['bolt']}; prop_pcd = {p['prop']['pcd']}; prop_n = {p['prop']['n']};",
          f"fit_press = {FIT['press']}; fit_slide = {FIT['slide']}; print_clear = {FIT['print_clear']};",
          f'coils = "{p["coils"]}";   // fase de cada diente (mayúscula +, minúscula −)', "",
          "slots = ["] + [f"  {[list(q) for q in s]}," for s in slots] + ["];", ""]
    path.write_text("\n".join(L))


LIB = r'''// Biblioteca del motor DronSwarm (M6). Las medidas vienen de <dron>_motor_params.scad (generado). Unidades: mm.
// Sin hull/minkowski (CLAUDE.md): todo con cilindros, polígonos y extrusiones.
$fn = 160;

// ---------- láser ----------
module stator_lamination_2d() {           // lámina del estator: 0.2 mm de acero al silicio (NO20)
    difference() {
        circle(r = r_s);
        circle(r = r_bore);
        for (s = slots) polygon(s);
        translate([r_bore - 0.01, -1.0]) square([1.2, 2.0]);                 // chaveta: alinea las láminas y fija al tubo
    }
}
module rotor_ring_2d() {                  // anillo del rotor: acero común 1 mm, se apilan n_ring
    difference() {
        circle(r = r_out);
        circle(r = r_mag_out + fit_slide / 2);
        translate([r_mag_out, -0.75]) square([0.8, 1.5]);                     // marca de orientación (polo 1)
    }
}

// ---------- impresas ----------
module cap() {                            // tapa: lleva la hélice y el eje; el anillo del rotor entra 2 mm en la ranura
    hub_r = shaft / 2 + 3.5;
    difference() {
        union() {
            cylinder(r = r_out + 1.2, h = cap_t);
            translate([0, 0, -2]) difference() {                                 // pollera que abraza el anillo
                cylinder(r = r_out + 1.2, h = 2);
                translate([0, 0, -0.1]) cylinder(r = r_out + print_clear / 2, h = 2.2);
            }
            cylinder(r = hub_r, h = cap_t + 4);                                  // cubo del eje
        }
        translate([0, 0, -1]) cylinder(d = shaft + fit_press, h = cap_t + 6);   // eje a presión
        translate([0, 0, cap_t + 2]) rotate([0, 90, 0]) cylinder(d = 2.6, h = hub_r + 1);   // prisionero M3
        for (i = [0 : prop_n - 1]) rotate(360 / prop_n * i + 45)
            translate([prop_pcd / 2, 0, -1]) cylinder(d = prop_bolt, h = cap_t + 6);
        for (i = [0 : prop_n - 1]) rotate(360 / prop_n * i)                      // ventilación entre los tornillos de la hélice
            translate([0, 0, -1]) linear_extrude(cap_t + 2)
                polygon([[ (hub_r + 2) * cos(-14), (hub_r + 2) * sin(-14)], [ (r_mag_in - 3) * cos(-18), (r_mag_in - 3) * sin(-18)],
                         [ (r_mag_in - 3) * cos(18), (r_mag_in - 3) * sin(18)], [ (hub_r + 2) * cos(14), (hub_r + 2) * sin(14)]]);
    }
}

module base() {                           // base: tubo con los 2 rodamientos, sostiene el estator, se atornilla al DMI
    tube_h = l_stack + 2 * overhang + 1;
    difference() {
        union() {
            cylinder(r = max(r_bore + 5, dmi_pcd / 2 + 4), h = base_t);
            cylinder(r = r_bore + fit_press / 2, h = base_t + tube_h);               // el estator se pega sobre el tubo
            translate([r_bore - 0.2, -0.9, base_t]) cube([1.0, 1.8, tube_h]);        // chaveta (entra en la muesca de las láminas)
        }
        translate([0, 0, -1]) cylinder(d = bearing_od + fit_press, h = bearing_w + 1);                  // rodamiento inferior
        translate([0, 0, base_t + tube_h - bearing_w]) cylinder(d = bearing_od + fit_press, h = bearing_w + 1); // superior
        translate([0, 0, -1]) cylinder(d = shaft + 1.0, h = base_t + tube_h + 2);
        for (i = [0 : dmi_n - 1]) rotate(360 / dmi_n * i + 45) translate([dmi_pcd / 2, 0, -1]) cylinder(d = dmi_bolt, h = base_t + 2);
        translate([r_bore - 4, -2, -1]) cube([6, 4, base_t + 2]);                 // salida de los 3 cables de fase
    }
}

module magnet_jig() {                     // peine: se mete dentro del anillo y deja cada imán en su lugar (paso de polo exacto)
    rib = 2 * PI * r_mag_in / poles - magnet_w;      // espacio entre imanes en el diámetro interior
    difference() {
        union() {
            cylinder(r = r_mag_in - 0.15, h = l_stack + 4);
            for (i = [0 : poles - 1]) rotate(360 / poles * (i + 0.5))
                translate([r_mag_in - 0.5, -max(rib, 0.6) / 2, 0]) cube([h_magnet + 0.3, max(rib, 0.6) - 0.15, l_stack + 4]);
        }
        translate([0, 0, -1]) cylinder(r = r_mag_in - 3, h = l_stack + 6);
    }
}

module stack_mandrel() {                  // mandril de apilado: alinea las láminas por el agujero y la chaveta mientras cura el adhesivo
    difference() {
        union() {
            cylinder(r = r_bore - 0.05, h = l_stack + 10);
            translate([r_bore - 0.3, -0.9, 0]) cube([1.0, 1.8, l_stack + 10]);
            cylinder(r = r_s + 3, h = 3);
        }
        translate([0, 0, -1]) cylinder(d = 5.5, h = l_stack + 12);                // varilla roscada M5 para prensar
    }
}

module winding_holder() {                 // soporte para bobinar a mano: sujeta el estator por el agujero, con mango
    union() {
        cylinder(r = r_bore - 0.1, h = l_stack + 2);
        translate([r_bore - 0.4, -0.85, 0]) cube([1.0, 1.7, l_stack + 2]);
        translate([0, 0, -40]) cylinder(r = 7, h = 40);
    }
}

// ---------- ensamble (para ver) ----------
module assembly() {
    color("#b0b0b0") translate([0, 0, base_t + overhang]) linear_extrude(l_stack) stator_lamination_2d();
    color("#b87333") for (s = slots) translate([0, 0, base_t + 0.5]) linear_extrude(l_stack + 2 * overhang - 1) offset(r = -0.35) polygon(s);
    color("#4a4a4a") translate([0, 0, base_t + overhang - 1]) linear_extrude(l_stack + 2) rotor_ring_2d();
    color("#2a78d6") for (i = [0 : poles - 1]) rotate(360 / poles * i)
        translate([0, 0, base_t + overhang]) rotate_extrude(angle = 360 / poles * pole_arc)
            translate([r_mag_in, 0]) square([h_magnet, l_stack]);
    color("#eb6834") translate([0, 0, base_t + 2 * overhang + l_stack + 1]) cap();
    color("#eb6834", 0.9) base();
    color("#dddddd") translate([0, 0, -6]) cylinder(d = shaft, h = base_t + 2 * overhang + l_stack + cap_t + 14);
}
'''

PARTS = {"lamina_estator": ("stator_lamination_2d();", "dxf"), "anillo_rotor": ("rotor_ring_2d();", "dxf"),
         "tapa": ("cap();", "stl"), "base": ("base();", "stl"), "plantilla_imanes": ("magnet_jig();", "stl"),
         "mandril_apilado": ("stack_mandrel();", "stl"), "soporte_bobinado": ("winding_holder();", "stl"),
         "ensamble": ("assembly();", "stl")}


def main() -> None:
    chosen = json.loads((INF / "M2_elegidos.json").read_text())
    SCAD_DIR.mkdir(parents=True, exist_ok=True)
    (SCAD_DIR / "motor_lib.scad").write_text(LIB)
    summary = {}
    for veh, c in chosen.items():
        key = veh.lower().replace("-", "_")
        p = params(veh, c)
        write_params(p, SCAD_DIR / f"{key}_motor_params.scad")
        out = OUT / veh.lower()
        out.mkdir(parents=True, exist_ok=True)
        files = {}
        for part, (call, ext) in PARTS.items():
            scad = SCAD_DIR / f"{key}_{part}.scad"
            scad.write_text(f"// {veh} · {part} (M6). Generado por motor/fabricacion/gen_cad.py\n"
                            f"include <{key}_motor_params.scad>\ninclude <motor_lib.scad>\n{call}\n")
            dst = out / f"{part}.{ext}"
            r = subprocess.run(["openscad", "-o", str(dst), str(scad)], capture_output=True, text=True, timeout=900)
            if r.returncode != 0 or not dst.exists():
                raise SystemExit(f"OpenSCAD falló en {scad.name}:\n{r.stderr[-2000:]}")
            files[part] = str(dst.relative_to(ROOT))
        summary[veh] = {"params": {k: v for k, v in p.items() if k not in ("dmi", "prop")}, "files": files}
        print(veh, "→", out)
    (OUT / "resumen.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
