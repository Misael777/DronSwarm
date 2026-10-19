#!/usr/bin/env python3
"""S07-04 / S08-04 · Casos de FEA de los frames (gmsh + CalculiX) con cargas derivadas del dimensionamiento.

Cargas de vuelo: empuje máximo de 5,000 msnm escalado a nivel del mar por la densidad (1.225 / 0.653 = 1.88, cota
superior: el motor no llega a tanto) × FS 2.5. Cargas de aterrizaje (accidentales) × FS 1.5:
  DS-I  caída de 1 m sobre 2 patas, la energía la absorbe el pie amortiguador de TPU.
  DS-D  aterrizaje duro a 2 m/s con la carga (5 kg) sobre 2 patas, carrera de 30 mm (zapatas + flexión del esquí).
Gancho de carga (DS-D): caja de 5 kg × 2 (tirón dinámico) × FS 2.5.

Como las cargas ya incluyen el factor de seguridad, el criterio es σ ≤ resistencia (FS calculado ≥ 1). En piezas
impresas se compara contra la resistencia en el plano de las capas; entre capas es ≈ 50 % (ver el informe).

    .venv/bin/python tools/fea/run_fea.py inspection | delivery   →  cad/freecad/<grupo>/fea/resultados.json
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from ccx_fea import ALU_6061, CARBON_TUBE, PA12_CF, beam_modal, solid_static  # noqa: E402

G = 9.81
RHO_RATIO = 1.225 / 0.653
SF_FLIGHT, SF_LAND = 2.5, 1.5
GROUPS = {"inspection": ("DS-I", "ds_i_params.scad", "ds_i_frame.scad"),
          "delivery": ("DS-D", "ds_d_params.scad", "ds_d_frame.scad")}


def scad_vars(*files: Path) -> dict:
    """Asignaciones numéricas simples `nombre = número;` de los .scad (parámetros y geometría derivada)."""
    out = {}
    for f in files:
        for m in re.finditer(r"^(\w+)\s*=\s*(-?[\d.]+)\s*;", f.read_text(), re.M):
            out[m.group(1)] = float(m.group(2))
    return out


def case(title, r, strength, load):
    sf = strength / r.vm_p995
    return {"title": title, "load": load, "nodes": r.nodes, "elements": r.elements,
            "vm_max_mpa": round(r.vm_max, 1), "vm_p995_mpa": round(r.vm_p995, 1), "disp_max_mm": round(r.disp_max_mm, 3),
            "strength_mpa": strength, "safety_factor": round(sf, 2), "ok": sf >= 1.0,
            "fixed_nodes": r.fixed_nodes, "loaded_nodes": r.loaded_nodes}


def analytic(title, load, sigma, strength, required=1.0):
    return {"title": title, "load": load, "stress_mpa": round(sigma, 1), "strength_mpa": strength,
            "safety_factor": round(strength / sigma, 2), "required_sf": required, "ok": strength / sigma >= required}


class Ctx:
    def __init__(self, group: str, size: float):
        veh, pfile, ffile = GROUPS[group]
        src = ROOT / "cad/openscad" / group
        self.group, self.size = group, size
        self.p = scad_vars(src / pfile, src / ffile)
        self.d = json.loads((ROOT / f"engineering/data/results/{veh.lower()}_sizing.json").read_text())
        self.exp = ROOT / "cad/exports" / group
        self.parts = json.loads((self.exp / "masas.json").read_text())["parts"]
        self.n = self.d["rotors"]
        self.t_max = self.d["performance"]["max_thrust_total_kgf_5000m"] * G / self.n * RHO_RATIO
        self.f_design = SF_FLIGHT * self.t_max
        self.tube_d, self.wall = self.p["tube_od"], self.p["tube_wall"]
        self.r_out = self.p["plate_d"] / 2 - 3
        self.lever = self.p["arm_radius"] - self.r_out
        self.inertia = math.pi / 64 * (self.tube_d ** 4 - (self.tube_d - 2 * self.wall) ** 4)
        self.res = {"vehicle": veh, "thrust_max_per_motor_N": round(self.t_max, 1), "design_thrust_N": round(self.f_design, 1),
                    "cases": {}}

    def step(self, name):
        return self.exp / f"{name}.step"


def motor_mount_case(c: Ctx):
    large = c.d["motor_p_max_w"] >= 600
    pd, pt = (56, 6) if large else (36, 4)
    zc = -pt - c.tube_d / 2 - 1
    rb = (c.tube_d + 0.3) / 2

    def bore(x):
        return (np.abs(np.hypot(x[:, 1], x[:, 2] - zc) - rb) < 0.35) & (x[:, 0] < -6)

    def top(x):
        return (x[:, 2] > -0.05) & (np.hypot(x[:, 0], x[:, 1]) < pd / 2)

    r = solid_static(c.step("motor_mount"), PA12_CF, c.size, bore, [("empuje", top, (0, 0, c.f_design))])
    c.res["cases"]["motor_mount"] = case(f"Soporte de motor DMI-{'L' if large else 'S'} (PA12-CF)", r, PA12_CF.strength_mpa,
                                         f"empuje {c.f_design:.0f} N sobre la placa DMI")


def arm_block_case(c: Ctx, part: str, insert: float, clearance: float):
    """Bloque entre placas: empotrado por las dos caras; el tubo apoya arriba en la boca y abajo en el fondo."""
    gap = c.p["plate_gap"]
    zt = gap / 2
    m_root = c.f_design * c.lever
    span = insert - 8
    f_out, f_in = m_root / span + c.f_design, m_root / span
    rb = (c.tube_d + clearance) / 2

    def bore(x):
        return np.abs(np.hypot(x[:, 1], x[:, 2] - zt) - rb) < 0.35

    r = solid_static(c.step(part), PA12_CF, c.size, lambda x: (x[:, 2] < 0.05) | (x[:, 2] > gap - 0.05),
                     [("boca", lambda x: bore(x) & (x[:, 0] > -6) & (x[:, 2] > zt), (0, 0, f_out)),
                      ("fondo", lambda x: bore(x) & (x[:, 0] < -insert + 6) & (x[:, 0] > -insert - 1) & (x[:, 2] < zt), (0, 0, -f_in))])
    c.res["cases"][part] = case(f"Bloque de brazo ({part}, PA12-CF)", r, PA12_CF.strength_mpa,
                                f"momento del brazo {m_root / 1000:.1f} N·m y corte {c.f_design:.0f} N")


def arm_beam_cases(c: Ctx, f_leg: float | None = None, a_leg: float | None = None):
    sig_f = c.f_design * c.lever * (c.tube_d / 2) / c.inertia
    c.res["cases"]["arm_flight"] = analytic("Tubo del brazo en vuelo (analítico)", f"{c.f_design:.0f} N en la punta, {c.lever:.0f} mm",
                                            sig_f, CARBON_TUBE.strength_mpa)
    if f_leg and a_leg:
        sig = f_leg * a_leg * (c.tube_d / 2) / c.inertia
        c.res["cases"]["arm_drop"] = analytic("Tubo del brazo en la caída (analítico)", f"{f_leg:.0f} N a {a_leg:.0f} mm del bloque",
                                              sig, CARBON_TUBE.strength_mpa, SF_LAND)
    tip = c.d["masses"]["motores"] / c.n + c.d["masses"]["hélices"] / c.n + c.parts["motor_mount"]["unit_kg"]
    length = c.lever + 8
    freqs = beam_modal(length, c.tube_d, c.wall, CARBON_TUBE, tip)
    f1p = c.d["performance"]["hover_rpm"] / 60
    f1 = freqs[0]
    sep = min(abs(f1 - f1p) / f1p, abs(f1 - 2 * f1p) / (2 * f1p))
    c.res["cases"]["arm_modal"] = {"title": "Modal del brazo (viga B32R + masa en la punta)", "tip_mass_kg": round(tip, 3),
                                   "length_mm": round(length, 1), "f1_hz": round(f1, 1), "f_1p_hz": round(f1p, 1),
                                   "f_2p_hz": round(2 * f1p, 1), "separation_pct": round(100 * sep, 0),
                                   "note": ("primer modo bajo 1P: se cruza solo al acelerar los motores desde reposo"
                                            if f1 < 0.8 * f1p else "entre 1P y 2P"),
                                   "ok": sep >= 0.20}


def inspection(c: Ctx):
    motor_mount_case(c)
    arm_block_case(c, "arm_block", c.p.get("block_len", 40.0), 0.2)
    # caída de 1 m sobre 2 patas, pie amortiguador de TPU (≈ 30 N/mm)
    foot_k, m = 30.0, c.d["mtow_kg"]
    stroke = math.sqrt(2 * m * G * 1000 / (2 * foot_k))
    f_leg = foot_k * stroke
    fd = SF_LAND * f_leg
    rb, sock_r, od = (c.tube_d + 0.3) / 2, (c.p.get("leg_tube", 12.0) + 0.3) / 2, c.tube_d + 8
    r = solid_static(c.step("leg_clamp"), PA12_CF, c.size,
                     lambda x: np.abs(np.hypot(x[:, 1], x[:, 2]) - rb) < 0.35,
                     [("impacto", lambda x: (np.abs(np.hypot(x[:, 0], x[:, 1]) - sock_r) < 0.35) & (x[:, 2] < -od / 2 - 6),
                       (0.3 * fd, 0, fd))])
    c.res["cases"]["leg_clamp"] = case("Abrazadera de pata (PA12-CF)", r, PA12_CF.strength_mpa,
                                       f"caída de 1 m en 2 patas: {f_leg:.0f} N por pata × {SF_LAND} (+30 % lateral), carrera {stroke:.0f} mm")
    arm_beam_cases(c, f_leg, c.p.get("leg_offset", 70.0))


def delivery(c: Ctx):
    motor_mount_case(c)
    arm_block_case(c, "arm_socket", c.p["tube_insert"], 0.25)
    # aterrizaje duro a 2 m/s con la carga, sobre 2 patas, 30 mm de carrera
    m = c.d["mtow_kg"]
    energy = 0.5 * m * 2.0 ** 2 * 1000                               # N·mm
    stroke = 30.0
    f_leg = 2 * energy / stroke / 2
    fd = SF_LAND * f_leg
    dz = (-c.p["plate_t"] - 6) - (-c.p["leg_h"] + c.p["gear_tube"] / 2 + 6)
    t = math.atan((c.p["skid_y"] - c.p["leg_y_top"]) / dz)
    sock_r = (c.p["gear_tube"] + 0.3) / 2
    axis_o = np.array([0.0, 0.0, -6.0])
    axis_u = np.array([0.0, math.sin(t), -math.cos(t)])               # eje de la pata: hacia abajo y afuera

    def socket(x):
        v = x - axis_o
        along = v @ axis_u
        radial = np.linalg.norm(v - np.outer(along, axis_u), axis=1)
        return (np.abs(radial - sock_r) < 0.35) & (along > 14)

    r = solid_static(c.step("gear_mount"), PA12_CF, c.size, lambda x: x[:, 2] > -0.05,
                     [("aterrizaje", socket, tuple(-fd * axis_u + np.array([0.3 * fd, 0, 0])))])
    c.res["cases"]["gear_mount"] = case("Soporte de pata (PA12-CF)", r, PA12_CF.strength_mpa,
                                        f"aterrizaje a 2 m/s con carga en 2 patas: {f_leg:.0f} N por pata × {SF_LAND} (+30 % lateral)")
    # gancho de carga (aluminio) y cuerpo de liberación (PA12-CF)
    f_hook = c.p.get("payload_kg", 5.0) * G * 2 * SF_FLIGHT
    piv = (-20.0, -52.0)

    def hole(x, cx, cz, r0):
        return np.abs(np.hypot(x[:, 0] - cx, x[:, 2] - cz) - r0) < 0.35

    def latch_face(x):                                               # cara del dedo del gancho contra el pasador
        return (np.abs(x[:, 2] + 50) < 0.05) & (x[:, 0] > -10) & (x[:, 0] < 18)

    r = solid_static(c.step("payload_release_hook"), ALU_6061, c.size * 0.6,
                     lambda x: hole(x, piv[0], piv[1], 5.3 / 2) | latch_face(x),
                     [("anilla", lambda x: hole(x, -12, -71, 9.0) & (x[:, 2] < -71), (0, 0, -f_hook))])
    c.res["cases"]["release_hook"] = case("Gancho de carga (aluminio 6061-T6)", r, ALU_6061.strength_mpa,
                                          f"caja de 5 kg × 2 (tirón) × {SF_FLIGHT} = {f_hook:.0f} N en la anilla")
    r = solid_static(c.step("payload_release_body"), PA12_CF, c.size, lambda x: x[:, 2] > -0.05,
                     [("perno", lambda x: hole(x, piv[0], piv[1], 5.3 / 2), (0, 0, -f_hook))])
    c.res["cases"]["release_body"] = case("Cuerpo de liberación (PA12-CF)", r, PA12_CF.strength_mpa,
                                          f"{f_hook:.0f} N en el perno del gancho")
    arm_beam_cases(c)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("group", choices=list(GROUPS))
    ap.add_argument("--size", type=float, default=1.6, help="tamaño de elemento [mm]")
    a = ap.parse_args()
    c = Ctx(a.group, a.size)
    (inspection if a.group == "inspection" else delivery)(c)
    out = ROOT / "cad/freecad" / a.group / "fea"
    out.mkdir(parents=True, exist_ok=True)
    c.res["materials"] = {"PA12-CF": vars(PA12_CF), "tubo": vars(CARBON_TUBE), "aluminio": vars(ALU_6061)}
    c.res["all_ok"] = all(x["ok"] for x in c.res["cases"].values())
    (out / "resultados.json").write_text(json.dumps(c.res, indent=2, ensure_ascii=False) + "\n")
    for k, x in c.res["cases"].items():
        print(f"{k:<13} {'OK ' if x['ok'] else 'NO '} " + ", ".join(f"{y}={x[y]}" for y in x if y in
              ("vm_p995_mpa", "safety_factor", "disp_max_mm", "stress_mpa", "f1_hz", "separation_pct")))


if __name__ == "__main__":
    main()
