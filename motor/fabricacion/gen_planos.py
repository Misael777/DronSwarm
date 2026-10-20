#!/usr/bin/env python3
"""M6 · Planos de fabricación del motor (PDF, A3 apaisado) → motor/fabricacion/planos/<dron>_planos.pdf

Mismas medidas que el CAD (gen_cad.params/mech). Láminas: ensamble en corte con lista de piezas, base, tapa, eje, lámina del
estator (con detalle de ranura) y anillo del rotor (con detalle de caras planas). Escalas normalizadas elegidas para que cada
vista entre en el área libre. Con PLANOS_PNG=<carpeta> guarda también cada lámina en PNG (revisión).

    .venv/bin/python motor/fabricacion/gen_planos.py
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Circle, Polygon, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "motor" / "fabricacion"))
sys.path.insert(0, str(ROOT))
import gen_cad as G  # noqa: E402

from motor.docs.gen_partes import lamination  # noqa: E402

INF = ROOT / "motor" / "informes"
OUT = ROOT / "motor" / "fabricacion" / "planos"
A3 = (420.0, 297.0)
INK, DIM = "#111111", "#1f4e9c"
THIN, FS = 0.3, 7.0
SCALES = (10, 8, 6, 5, 4, 3, 2.5, 2, 1.5, 1, 0.75, 0.5)
_PNG = {"dir": os.environ.get("PLANOS_PNG"), "n": 0, "veh": ""}


def fit_scale(w: float, h: float, box_w: float, box_h: float) -> float:
    return next((s for s in SCALES if w * s <= box_w and h * s <= box_h), SCALES[-1])


def sheet(title: str, part: str, material: str, qty: str, scale_txt: str, veh: str, notes: list[str]):
    fig = plt.figure(figsize=(A3[0] / 25.4, A3[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A3[0])
    ax.set_ylim(0, A3[1])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((10, 10), A3[0] - 20, A3[1] - 20, fill=False, lw=0.8, color=INK))
    x0, y0, w, h = A3[0] - 190, 10, 180, 42
    ax.add_patch(Rectangle((x0, y0), w, h, fill=False, lw=0.8, color=INK))
    for yy in (y0 + 14, y0 + 28):
        ax.plot([x0, x0 + w], [yy, yy], color=INK, lw=0.5)
    for xx in (x0 + 60, x0 + 120):
        ax.plot([xx, xx], [y0, y0 + 28], color=INK, lw=0.5)
    ax.text(x0 + 3, y0 + 35, f"DronSwarm · Motor {veh} · {title}", fontsize=10, weight="bold", va="center")
    cells = [("Pieza", part), ("Material", material), ("Cantidad", qty), ("Escala", scale_txt),
             ("Tolerancias gen.", "ISO 2768-m / impresas ±0.2"), ("Fecha", f"{date.today():%d/%m/%Y}")]
    for i, (k, v) in enumerate(cells):
        cx, cy = x0 + 3 + (i % 3) * 60, y0 + (21 if i < 3 else 7)
        ax.text(cx, cy + 3, k, fontsize=5.5, color="#666")
        ax.text(cx, cy - 2.5, v, fontsize=7.5)
    ax.text(x0, y0 + h + 2, "Cotas en mm. Generado por motor/fabricacion/gen_planos.py desde el diseño (no editar a mano).",
            fontsize=5.5, color="#666")
    ax.text(15, 55, "NOTAS", fontsize=7, weight="bold")
    for i, n in enumerate(notes):
        ax.text(15, 50 - i * 4.2, n, fontsize=6.3)
    return fig, ax


def save(pdf, fig) -> None:
    pdf.savefig(fig)
    if _PNG["dir"]:
        _PNG["n"] += 1
        fig.savefig(Path(_PNG["dir"]) / f"{_PNG['veh']}_{_PNG['n']}.png", dpi=70)
    plt.close(fig)


class View:
    """Coordenadas de la pieza [mm] → hoja (origen y escala). Las cotas se ubican en coordenadas de la pieza."""

    def __init__(self, ax, ox, oy, s):
        self.ax, self.ox, self.oy, self.s = ax, ox, oy, s

    def P(self, x, y):
        return (self.ox + x * self.s, self.oy + y * self.s)

    def poly(self, pts, fc="none", ec=INK, lw=0.6, hatch=None):
        self.ax.add_patch(Polygon([self.P(*q) for q in pts], closed=True, fc=fc, ec=ec, lw=lw, hatch=hatch))

    def line(self, a, b, color=INK, lw=0.6, ls="-"):
        (x1, y1), (x2, y2) = self.P(*a), self.P(*b)
        self.ax.plot([x1, x2], [y1, y2], color=color, lw=lw, ls=ls)

    def axis(self, a, b):
        self.line(a, b, color="#777", lw=0.35, ls=(0, (8, 2, 1, 2)))

    def circle(self, c, r, color=INK, lw=0.6, ls="-"):
        self.ax.add_patch(Circle(self.P(*c), r * self.s, fill=False, color=color, lw=lw, ls=ls))

    def hdim(self, x1, x2, y_feat1, y_feat2, y_dim, text):
        """Cota horizontal entre x1 y x2; líneas de referencia desde y_feat hasta y_dim (coordenadas de la pieza)."""
        (a, ya), (b, yb), (_, yd) = self.P(x1, y_feat1), self.P(x2, y_feat2), self.P(0, y_dim)
        sgn = 1 if yd >= max(ya, yb) else -1
        for x, y in ((a, ya), (b, yb)):
            self.ax.plot([x, x], [y + sgn * 0.8, yd + sgn * 1.5], color=DIM, lw=THIN)
        self.ax.annotate("", (a, yd), (b, yd), arrowprops=dict(arrowstyle="<|-|>", color=DIM, lw=THIN, mutation_scale=6,
                                                               shrinkA=0, shrinkB=0))
        self.ax.text((a + b) / 2, yd + sgn * 0.8, text, fontsize=FS, color=DIM, ha="center", va="bottom" if sgn > 0 else "top",
                     bbox=dict(fc="white", ec="none", pad=0.3))

    def vdim(self, y1, y2, x_feat1, x_feat2, x_dim, text):
        (xa, a), (xb, b), (xd, _) = self.P(x_feat1, y1), self.P(x_feat2, y2), self.P(x_dim, 0)
        sgn = 1 if xd >= max(xa, xb) else -1
        for x, y in ((xa, a), (xb, b)):
            self.ax.plot([x + sgn * 0.8, xd + sgn * 1.5], [y, y], color=DIM, lw=THIN)
        self.ax.annotate("", (xd, a), (xd, b), arrowprops=dict(arrowstyle="<|-|>", color=DIM, lw=THIN, mutation_scale=6,
                                                               shrinkA=0, shrinkB=0))
        self.ax.text(xd + sgn * 0.9, (a + b) / 2, text, fontsize=FS, color=DIM, rotation=90, ha="left" if sgn > 0 else "right",
                     va="center", bbox=dict(fc="white", ec="none", pad=0.3))

    def note(self, at, text, to):
        """Nota con línea de referencia desde `at` (pieza) desplazada `to` (mm de hoja)."""
        x, y = self.P(*at)
        self.ax.annotate(text, (x, y), (x + to[0], y + to[1]), fontsize=FS, color=DIM, ha="left" if to[0] >= 0 else "right",
                         va="center", arrowprops=dict(arrowstyle="-", color=DIM, lw=THIN),
                         bbox=dict(fc="white", ec="none", pad=0.3))

    def title(self, at, text):
        x, y = self.P(*at)
        self.ax.text(x, y, text, fontsize=8, weight="bold", ha="center")


def hatched(v: View, pts, color):
    v.poly(pts, fc=color, hatch="////", lw=0.6)


def mirror(pts):
    return [(-x, y) for x, y in pts]


# ------------------------------------------------------------------ perfiles (las mismas fórmulas que motor_lib.scad)
def R_seat(m):
    return (m["bearing"]["D"] + G.FITS["bearing_seat"]) / 2


def base_profile(p, m):
    Rs, R_sh = R_seat(m), (m["bearing"]["Da"] - 0.2) / 2
    ch, li, B = G.CHAMFER, G.LEAD_IN, m["bearing"]["B"]
    rf, bt = m["r_flange"], m["base_t"]
    return [(Rs + li, 0), (rf - ch, 0), (rf, ch), (rf, bt - ch), (rf - ch, bt), (m["r_shoulder"], bt), (m["r_shoulder"], m["z_s0"]),
            (m["r_tube"], m["z_s0"]), (m["r_tube"], m["z_tube"] - 0.3), (m["r_tube"] - 0.3, m["z_tube"]), (Rs + li, m["z_tube"]),
            (Rs, m["z_tube"] - li), (Rs, m["z_tube"] - B), (R_sh, m["z_tube"] - B), (R_sh, m["h_low"] + B), (Rs, m["h_low"] + B),
            (Rs, li)]


def cap_geom(p, m):
    r_cap = p["r_out"] + G.FITS["ring_in_skirt"] / 2 + 1.6
    skirt_in = (2 * p["r_out"] + G.FITS["ring_in_skirt"]) / 2
    z_low = m["z_r1"] - (2.0 + m["z_cap"] - m["z_r1"])
    return r_cap, skirt_in, z_low


def cap_profile(p, m):
    ch, li = G.CHAMFER, G.LEAD_IN
    r_cap, skirt_in, z_low = cap_geom(p, m)
    R_rec, Rb = (m["shim"]["D"] + 0.6) / 2, p["shaft"] / 2
    return [(Rb, m["z_sp"]), (m["wave"]["D"] / 2, m["z_sp"]), (m["wave"]["D"] / 2, m["z_cap"]), (p["r_mag_in"] + 0.3, m["z_cap"]),
            (p["r_mag_in"] + 0.3, m["z_r1"]), (skirt_in, m["z_r1"]), (skirt_in, z_low + li), (skirt_in + li, z_low), (r_cap - ch, z_low),
            (r_cap, z_low + ch), (r_cap, m["z_cap"] + p["cap_t"] - ch), (r_cap - ch, m["z_cap"] + p["cap_t"]), (m["r_plateau"], m["z_cap"] + p["cap_t"]),
            (m["r_plateau"], m["z_pt"] - ch), (m["r_plateau"] - ch, m["z_pt"]), (R_rec, m["z_pt"]), (R_rec, m["z_rb"]), (Rb, m["z_rb"])]


def arc(r, a0, a1, n=12):
    return [(r * math.cos(a0 + (a1 - a0) * j / n), r * math.sin(a0 + (a1 - a0) * j / n)) for j in range(n + 1)]


# ------------------------------------------------------------------ 1. ensamble
def sheet_assembly(pdf, veh, p, m):
    r_cap = cap_geom(p, m)[0]
    s = fit_scale(2 * r_cap + 20, m["shaft_top"] + 10, 230, 205)
    notes = ["1. Corte por el eje. Rodamientos en X: aros exteriores contra los hombros de la base; aros interiores apretados entre el",
             "   anillo E inferior y el espigón de la tapa, con precarga de la arandela ondulada (11).",
             "2. Empuje de la hélice: tapa → eje → anillo E inferior → rodamiento inferior → hombro de la base → brazo.",
             "3. Ajustes, cadenas de tolerancias y orden de armado: motor/fabricacion/tolerancias.md. Bobinado y control: valores.md."]
    fig, ax = sheet("Ensamble en corte", f"M-{veh}-000", "—", "1", f"{s:g} : 1", veh, notes)
    v = View(ax, 25 + (r_cap + 6) * s, 85, s)
    b, sh, wv, cl = m["bearing"], m["shim"], m["wave"], m["clip"]
    r_t = p["r_s"] - p["h_tip"]
    r_b = r_t - p["h_slot"]
    for f in (lambda q: q, mirror):
        hatched(v, f(base_profile(p, m)), "#f6d2a8")
        hatched(v, f(cap_profile(p, m)), "#f3b38f")
        for z in (m["h_low"], m["z_tube"] - b["B"]):
            v.poly(f([(b["d"] / 2, z), (b["D"] / 2, z), (b["D"] / 2, z + b["B"]), (b["d"] / 2, z + b["B"])]), fc="#c8ccd0")
            v.circle(f([((b["d"] + b["D"]) / 4, z + b["B"] / 2)])[0], (b["D"] - b["d"]) / 8, lw=0.4)
        v.poly(f([(p["r_bore"], m["z_s0"]), (p["r_s"], m["z_s0"]), (p["r_s"], m["z_s1"]), (p["r_bore"], m["z_s1"])]), fc="#b9bec4", hatch="\\\\\\\\")
        for z0, z1 in ((m["z_s0"] - p["overhang"] + 0.2, m["z_s0"]), (m["z_s1"], m["z_s1"] + p["overhang"] - 0.2)):
            v.poly(f([(r_b + 0.25, z0), (r_t - 0.25, z0), (r_t - 0.25, z1), (r_b + 0.25, z1)]), fc="#d9a066", lw=0.4)
        v.poly(f([(p["r_mag_out"] - p["h_magnet"], m["z_s0"]), (p["r_mag_out"], m["z_s0"]), (p["r_mag_out"], m["z_s1"]),
                  (p["r_mag_out"] - p["h_magnet"], m["z_s1"])]), fc="#c46a8f")
        v.poly(f([(p["r_mag_out"] + 0.05, m["z_r0"]), (p["r_out"], m["z_r0"]), (p["r_out"], m["z_r1"]), (p["r_mag_out"] + 0.05, m["z_r1"])]),
               fc="#666666", hatch="xxxx")
        for z, t, d0, d1, col in ((m["h_low"] - sh["t"], sh["t"], sh["d"], sh["D"], "#999"), (m["z_tube"], sh["t"], sh["d"], sh["D"], "#999"),
                                  (m["z_tube"] + sh["t"], wv["h_work"], wv["d"], wv["D"], "#bbb"), (m["z_rb"], sh["t"], sh["d"], sh["D"], "#999"),
                                  (m["z_g1"], cl["s"], cl["groove_d"], cl["od"], "#555"), (m["z_g2"], cl["s"], cl["groove_d"], cl["od"], "#555")):
            v.poly(f([(d0 / 2, z), (d1 / 2, z), (d1 / 2, z + t), (d0 / 2, z + t)]), fc=col, lw=0.35)
    R = p["shaft"] / 2
    v.poly([(-R, m["shaft_bot"]), (R, m["shaft_bot"]), (R, m["shaft_top"]), (-R, m["shaft_top"])], fc="#eeeeee")
    v.axis((0, -3), (0, m["shaft_top"] + 3))
    items = [("1", "Base", "PETG/ASA/PA-CF", "1", (m["r_flange"] - 1.5, m["base_t"] / 2)),
             ("2", f"Rodamiento {b['name']}", "acero", "2", ((b["d"] + b["D"]) / 4, m["h_low"] + b["B"] / 2)),
             ("3", f"Eje Ø{p['shaft']:.0f} h6", "acero plata", "1", (R * 0.5, m["z_s0"] + 0.5)),
             ("4", "Paquete del estator", f"NO20 0.2 × {p['n_lam']}", "1", ((p["r_bore"] + p["r_s"]) / 2, m["z_s0"] + p["l_stack"] / 2)),
             ("5", "Bobinado", "Cu clase H", "1", ((r_b + r_t) / 2, m["z_s1"] + p["overhang"] / 2)),
             ("6", "Imán", "N48SH", str(p["poles"]), (p["r_mag_out"] - p["h_magnet"] / 2, m["z_s0"] + p["l_stack"] * 0.35)),
             ("7", "Anillo del rotor", f"DC01 1.0 × {p['n_ring']}", "1", ((p["r_mag_out"] + p["r_out"]) / 2, m["z_r0"] + 1.0)),
             ("8", "Tapa del rotor", "PETG/ASA/PA-CF", "1", (r_cap - 0.8, m["z_cap"] + p["cap_t"] / 2)),
             ("9", f"Anillo E {cl['name']}", "acero", "2", (cl["od"] / 2 - 0.3, m["z_g1"] + cl["s"] / 2)),
             ("10", f"Arandela {sh['name']}", "acero", "3", (sh["D"] / 2 - 0.3, m["z_tube"] + sh["t"] / 2)),
             ("11", f"Arandela ondulada {wv['name'].split(' (')[0]}", "acero resorte", "1", (wv["D"] / 2 - 0.3, m["z_tube"] + sh["t"] + wv["h_work"] / 2)),
             ("12", f"Inserto roscado {m['insert']['thread']}", "latón", "8", (p["prop"]["pcd"] / 2, m["z_pt"] - 1.5))]
    col_x = v.P(r_cap, 0)[0] + 16
    order = sorted(items, key=lambda it: it[4][1])
    ys = []
    for it in order:
        y = v.P(*it[4])[1]
        ys.append(max(y, ys[-1] + 7.5) if ys else y - 6)
    shift = max(0.0, ys[-1] - 270)
    ys = [y - shift for y in ys]
    for it, ty in zip(order, ys):
        x, y = v.P(*it[4])
        ax.plot([x, col_x - 3], [y, ty], color=DIM, lw=THIN)
        ax.plot([x], [y], marker="o", ms=1.5, color=DIM)
        ax.add_patch(Circle((col_x, ty), 3, fill=False, color=DIM, lw=0.5))
        ax.text(col_x, ty, it[0], fontsize=6.5, ha="center", va="center", color=DIM)
    tx, ty0 = 300, 280
    ax.text(tx, ty0, "LISTA DE PIEZAS", fontsize=8, weight="bold")
    for j, hdr in enumerate(("N.º", "Descripción", "Material", "Cant.")):
        ax.text(tx + (0, 9, 62, 96)[j], ty0 - 6, hdr, fontsize=6.3, weight="bold")
    for i, it in enumerate(items):
        yy = ty0 - 11 - i * 5
        for j, val in enumerate((it[0], it[1], it[2], it[3])):
            ax.text(tx + (0, 9, 62, 96)[j], yy, val, fontsize=6.0)
    k = 1 / s
    v.hdim(-m["r_flange"], m["r_flange"], 0, 0, -7 * k, f"Ø{2 * m['r_flange']:.1f}")
    v.hdim(-r_cap, r_cap, m["z_pt"], m["z_pt"], m["z_pt"] + 9 * k, f"Ø{2 * r_cap:.1f}")
    v.vdim(0, m["z_pt"], -m["r_flange"], -r_cap, -r_cap - 9 * k, f"{m['z_pt']:.2f} (sin eje)")
    v.note((p["r_s"] + p["gap"] / 2, m["z_s0"] + 0.5), f"entrehierro {p['gap']:.2f}", (-38, -40))
    save(pdf, fig)


# ------------------------------------------------------------------ 2. base
def sheet_base(pdf, veh, p, m):
    b, ins = m["bearing"], m["insert"]
    rf = m["r_flange"]
    s = fit_scale(2 * rf + 40, m["z_tube"] + 30, 205, 200)
    notes = [f"1. Imprimir con la brida sobre la cama; 4 perímetros, relleno ≥ 40 %. Agujeros modelados con hole_comp = {G.HOLE_COMP}.",
             f"2. Asientos de rodamiento Ø{2 * R_seat(m):.2f} +0.05/0: apriete en plástico; calibrar con la probeta de ajustes.",
             f"3. Insertos {ins['thread']} desde abajo en agujeros Ø{ins['hole']} × {ins['depth']} a Ø{p['dmi']['pcd']:.0f} (DMI), con soldador.",
             f"4. Tubo Ø{2 * m['r_tube']:.2f} ±0.05 para el estator (juego para epoxi) con chaveta de {2.0 - G.FITS['key']:.1f} mm.",
             f"5. Chaflanes no indicados {G.CHAMFER} × 45°; entradas de los asientos {G.LEAD_IN} × 45°."]
    fig, ax = sheet("Base", f"M-{veh}-001", "PETG / ASA / PA-CF", "1 por motor", f"{s:g} : 1", veh, notes)
    k = 1 / s
    v = View(ax, 25 + (rf + 22 * k) * s, 95, s)
    pts = base_profile(p, m)
    hatched(v, pts, "#f6d2a8")
    hatched(v, mirror(pts), "#f6d2a8")
    v.axis((0, -2), (0, m["z_tube"] + 3))
    Rs = R_seat(m)
    zt = m["z_tube"]
    v.title((0, zt + 24 * k), "SECCIÓN A-A")
    v.hdim(-Rs, Rs, zt, zt, zt + 6 * k, f"Ø{2 * Rs:.2f} +0.05/0")
    v.hdim(-m["r_tube"], m["r_tube"], zt, zt, zt + 14 * k, f"Ø{2 * m['r_tube']:.2f} ±0.05")
    v.hdim(-Rs, Rs, 0, 0, -6 * k, f"Ø{2 * Rs:.2f} +0.05/0")
    v.hdim(-rf, rf, 0, 0, -14 * k, f"Ø{2 * rf:.1f}")
    zsh = (m["h_low"] + b["B"] + zt - b["B"]) / 2
    v.hdim(-(b["Da"] - 0.2) / 2, (b["Da"] - 0.2) / 2, zsh, zsh, zsh, f"Ø{b['Da'] - 0.2:.1f}")
    for i, (z, xf, label) in enumerate(((m["base_t"], rf, f"{m['base_t']:.1f}"), (m["z_s0"], m["r_shoulder"], f"{m['z_s0']:.2f}"),
                                        (zt, m["r_tube"], f"{zt:.2f}"))):
        v.vdim(0, z, rf, xf, rf + (6 + 8 * i) * k, label)
    v.vdim(0, m["h_low"] + b["B"], -Rs, -Rs, -rf - 6 * k, f"{m['h_low'] + b['B']:.2f}")
    v.vdim(zt - b["B"], zt, -Rs, -Rs, -rf - 14 * k, f"{b['B']:.1f}")
    v.note((rf - G.CHAMFER / 2, m["base_t"] - G.CHAMFER / 2), f"{G.CHAMFER} × 45°", (6, 18))
    s2 = fit_scale(2 * rf + 30, 2 * rf + 30, 160, 190)
    v2 = View(ax, 320, 175, s2)
    v2.title((0, rf + 14 / s2), "VISTA SUPERIOR")
    v2.circle((0, 0), rf)
    v2.circle((0, 0), m["r_shoulder"], lw=0.4)
    v2.circle((0, 0), m["r_tube"], lw=0.4)
    v2.circle((0, 0), Rs)
    v2.circle((0, 0), p["dmi"]["pcd"] / 2, color="#777", lw=0.35, ls=(0, (8, 2, 1, 2)))
    for i in range(p["dmi"]["n"]):
        a = math.radians(45 + 360 / p["dmi"]["n"] * i)
        v2.circle((p["dmi"]["pcd"] / 2 * math.cos(a), p["dmi"]["pcd"] / 2 * math.sin(a)), ins["hole"] / 2, ls="--", lw=0.5)
    w = (3 * m["wire_d"] + 1.0) / 2
    v2.poly([(-m["r_tube"] + 1.5, -w), (-rf, -w), (-rf, w), (-m["r_tube"] + 1.5, w)], lw=0.45)
    v2.poly([(m["r_tube"] - 0.3, -0.95), (m["r_tube"] + 0.7, -0.95), (m["r_tube"] + 0.7, 0.95), (m["r_tube"] - 0.3, 0.95)], lw=0.45)
    v2.line((-rf - 3, 0), (rf + 3, 0), color="#777", lw=0.35, ls=(0, (8, 2, 1, 2)))
    a = math.radians(45)
    v2.note((p["dmi"]["pcd"] / 2 * math.cos(a), p["dmi"]["pcd"] / 2 * math.sin(a)),
            f"4 × inserto {ins['thread']} Ø{ins['hole']} × {ins['depth']} (desde abajo), a Ø{p['dmi']['pcd']:.0f}", (10, 30))
    v2.note((-rf + 1, w), f"canal de cables {2 * w:.1f} × {min(2.5, m['base_t'] - 1.5):.1f}", (-4, 30))
    v2.note((m["r_tube"] + 0.7, -0.95), "chaveta 1.9 × 1.0", (14, -26))
    save(pdf, fig)


# ------------------------------------------------------------------ 3. tapa
def sheet_cap(pdf, veh, p, m):
    ins = m["insert"]
    r_cap, skirt_in, z_low = cap_geom(p, m)
    s = fit_scale(2 * r_cap + 40, m["z_pt"] - z_low + 40, 205, 190)
    notes = ["1. Imprimir boca abajo (cara de la hélice sobre la cama); 4 perímetros, relleno ≥ 40 %.",
             f"2. Agujero en D: imprimir Ø{p['shaft'] - 0.15:.2f} y escariar a Ø{p['shaft']:.0f} H7; pegar el eje con adhesivo retenedor.",
             f"3. Insertos {ins['thread']} de la hélice desde arriba, Ø{ins['hole']} × {ins['depth']} a Ø{p['prop']['pcd']:.0f} (ajustar a la hélice usada).",
             f"4. Pollera Ø{2 * skirt_in:.2f} ±0.05: pegar el anillo del rotor con el útil de concentricidad.",
             f"5. Rebaje superior para arandela + anillo E (quedan al ras). Chaflanes no indicados {G.CHAMFER} × 45°."]
    fig, ax = sheet("Tapa del rotor", f"M-{veh}-002", "PETG / ASA / PA-CF", "1 por motor", f"{s:g} : 1", veh, notes)
    k = 1 / s
    v = View(ax, 25 + (r_cap + 22 * k) * s, 130 - z_low * s, s)
    pts = cap_profile(p, m)
    hatched(v, pts, "#f3b38f")
    hatched(v, mirror(pts), "#f3b38f")
    v.axis((0, m["z_sp"] - 2), (0, m["z_pt"] + 2))
    v.title((0, m["z_pt"] + 20 * k), "SECCIÓN B-B")
    v.hdim(-r_cap, r_cap, m["z_cap"] + p["cap_t"], m["z_cap"] + p["cap_t"], m["z_pt"] + 11 * k, f"Ø{2 * r_cap:.1f}")
    v.hdim(-m["r_plateau"], m["r_plateau"], m["z_pt"], m["z_pt"], m["z_pt"] + 4 * k, f"Ø{2 * m['r_plateau']:.1f}")
    v.hdim(-skirt_in, skirt_in, z_low, z_low, z_low - 6 * k, f"Ø{2 * skirt_in:.2f} ±0.05")
    v.hdim(-p["shaft"] / 2, p["shaft"] / 2, m["z_sp"], m["z_sp"], z_low - 14 * k, f"Ø{p['shaft']:.0f} H7 (en D)")
    v.vdim(z_low, m["z_pt"], r_cap, m["r_plateau"], r_cap + 7 * k, f"{m['z_pt'] - z_low:.2f}")
    v.vdim(m["z_cap"], m["z_pt"], m["r_plateau"], m["r_plateau"], r_cap + 15 * k, f"{m['t_plateau']:.1f}")
    v.vdim(m["z_sp"], m["z_cap"], -m["wave"]["D"] / 2, -m["wave"]["D"] / 2, -r_cap - 7 * k, f"espigón {m['z_cap'] - m['z_sp']:.2f}")
    v.note((-(m["shim"]["D"] + 0.6) / 2, m["z_rb"] + 0.3), f"rebaje Ø{m['shim']['D'] + 0.6:.1f} × {m['z_pt'] - m['z_rb']:.2f}", (-8, 26))
    v.note((p["r_mag_in"] + 0.3, m["z_r1"]), "apoyo del anillo (1 mm sobre los imanes)", (6, -30))
    s2 = fit_scale(2 * r_cap + 30, 2 * r_cap + 30, 160, 190)
    v2 = View(ax, 320, 180, s2)
    v2.title((0, r_cap + 12 / s2), "VISTA SUPERIOR")
    v2.circle((0, 0), r_cap)
    v2.circle((0, 0), m["r_plateau"], lw=0.45)
    v2.circle((0, 0), (m["shim"]["D"] + 0.6) / 2, lw=0.4)
    R = p["shaft"] / 2
    a0 = math.acos((R - m["flat"]) / R)
    v2.poly(arc(R, a0, 2 * math.pi - a0, 40), lw=0.5)
    for i in range(6):
        a_0, a_1 = math.radians(60 * i - 20), math.radians(60 * i + 20)
        v2.poly(arc(m["r_plateau"] + 1.2, a_0, a_1) + arc(p["r_mag_in"] - 1.2, a_1, a_0), lw=0.45)
    for i in range(p["prop"]["n"]):
        a = math.radians(45 + 360 / p["prop"]["n"] * i)
        v2.circle((p["prop"]["pcd"] / 2 * math.cos(a), p["prop"]["pcd"] / 2 * math.sin(a)), ins["hole"] / 2, lw=0.5)
    v2.circle((0, 0), p["prop"]["pcd"] / 2, color="#777", lw=0.35, ls=(0, (8, 2, 1, 2)))
    a = math.radians(45)
    v2.note((p["prop"]["pcd"] / 2 * math.cos(a), p["prop"]["pcd"] / 2 * math.sin(a)),
            f"4 × inserto {ins['thread']} Ø{ins['hole']} × {ins['depth']}, a Ø{p['prop']['pcd']:.0f}", (14, 40))
    v2.note((R - m["flat"], 0), f"agujero en D: Ø{p['shaft']:.0f} H7, plano a {R - m['flat']:.2f}", (24, -44))
    v2.note(((m["r_plateau"] + p["r_mag_in"]) / 2, 0), "6 ventilaciones de 40°", (30, -16))
    save(pdf, fig)


# ------------------------------------------------------------------ 4. eje
def sheet_shaft(pdf, veh, p, m):
    c = m["clip"]
    L = m["shaft_len"]
    s = fit_scale(L + 30, p["shaft"] + 30, 230, 150)
    notes = [f"1. Acero plata (o 4140) rectificado Ø{p['shaft']:.0f} h6 (0/−0.008). Cortar a {L:.2f} ±0.05.",
             f"2. Ranuras para anillo E {c['name']}: Ø{c['groove_d']} h11 × {c['m']} H13. Con torno; sin torno: girar el eje en el taladro de banco",
             "   y ranurar con disco de corte de 0.6 mm con plantilla; verificar con el anillo E (debe calzar sin juego axial).",
             f"3. Plano para el agujero en D de la tapa: profundidad {m['flat']} mm (limar o amolar), sin tocar la zona de los rodamientos.",
             "4. Chaflanes 0.3 × 45° en los extremos. Sin rebabas ni marcas en las zonas de los rodamientos."]
    fig, ax = sheet("Eje", f"M-{veh}-003", "Acero plata h6", "1 por motor", f"{s:g} : 1", veh, notes)
    z0 = m["shaft_bot"]
    v = View(ax, 40, 170, s)
    R, Rg = p["shaft"] / 2, c["groove_d"] / 2
    g1, g2 = m["z_g1"] - z0, m["z_g2"] - z0
    prof = [(0, -R + 0.3), (0.3, -R), (g1, -R), (g1, -Rg), (g1 + c["m"], -Rg), (g1 + c["m"], -R), (g2, -R), (g2, -Rg), (g2 + c["m"], -Rg),
            (g2 + c["m"], -R), (L - 0.3, -R), (L, -R + 0.3), (L, R - 0.3), (L - 0.3, R), (g2 + c["m"], R), (g2 + c["m"], Rg), (g2, Rg),
            (g2, R), (g1 + c["m"], R), (g1 + c["m"], Rg), (g1, Rg), (g1, R), (0.3, R), (0, R - 0.3)]
    v.poly(prof, fc="#eeeeee")
    fz0, fz1 = m["z_sp"] - z0, m["z_rb"] - z0
    v.line((fz0, R - m["flat"]), (fz1, R - m["flat"]), lw=0.8)
    v.axis((-2, 0), (L + 2, 0))
    k = 1 / s
    v.hdim(0, L, -R, -R, -R - 8 * k, f"{L:.2f} ±0.05")
    v.hdim(0, g1, R, R, R + 6 * k, f"{g1:.2f}")
    v.hdim(0, g2, R, R, R + 13 * k, f"{g2:.2f}")
    v.hdim(fz0, fz1, R, R, R + 20 * k, f"plano {fz1 - fz0:.2f}")
    v.vdim(-R, R, L, L, L + 6 * k, f"Ø{p['shaft']:.0f} h6")
    v.vdim(-Rg, Rg, g1 + c["m"] / 2, g1 + c["m"] / 2, -6 * k, f"Ø{c['groove_d']} h11")
    v.note((g2 + c["m"] / 2, -Rg), f"ranura {c['m']} H13 (×2)", (6, -16))
    v.note((L - 0.15, R - 0.15), "0.3 × 45° (ambos extremos)", (10, 12))
    v.note(((fz0 + fz1) / 2, R - m["flat"]), f"plano a {R - m['flat']:.2f} del eje", (-12, 26))
    s3 = fit_scale(p["shaft"] + 6, p["shaft"] + 6, 50, 50)
    v2 = View(ax, 345, 170, s3)
    yy = math.sqrt(R * R - (R - m["flat"]) ** 2)
    a0 = math.acos((R - m["flat"]) / R)
    v2.poly(arc(R, a0, 2 * math.pi - a0, 60) + [(R - m["flat"], -yy)], fc="#eeeeee", hatch="////")
    v2.title((0, R + 8 / s3), f"SECCIÓN C-C ({s3:g}:1)")
    save(pdf, fig)


# ------------------------------------------------------------------ 5. lámina del estator
def sheet_lamination(pdf, veh, p, m, slot0):
    r_s = p["r_s"]
    s = fit_scale(2 * r_s + 30, 2 * r_s + 30, 200, 210)
    notes = [f"1. Acero al silicio no orientado 0.20 mm (NO20), aislado C5. {p['n_lam']} láminas por motor (paquete {p['l_stack']:.2f} ±0.1 mm).",
             "2. Láser de fibra desde lamina_estator.dxf, con compensación de corte; borde sin rebaba ni coloración azul (sube las pérdidas).",
             "3. Esquinas del fondo de ranura R 0.3. Muesca de chaveta 2.0 × 1.2: alinea el paquete y lo traba en el tubo de la base.",
             "4. Apilar en el mandril con epoxi fino y prensar con la varilla M5; desbarbar el contorno antes de aislar."]
    sd = fit_scale(2 * math.pi * r_s / p["ns"] * 1.6, p["h_slot"] + p["h_tip"] + 4, 140, 150)
    fig, ax = sheet("Lámina del estator", f"M-{veh}-004", "NO20 0.20 mm", f"{p['n_lam']} por motor", f"{s:g} : 1 (detalle {sd:g}:1)",
                    veh, notes)
    k = 1 / s
    v = View(ax, 25 + (r_s + 15 * k) * s, 175, s)
    v.poly(lamination(p["ns"], r_s, p["w_tooth"], p["h_slot"]), fc="#e9ebee", lw=0.5)
    v.ax.add_patch(Circle(v.P(0, 0), p["r_bore"] * s, fc="white", ec=INK, lw=0.5))
    v.poly([(p["r_bore"] - 0.01, -1.0), (p["r_bore"] + 1.2, -1.0), (p["r_bore"] + 1.2, 1.0), (p["r_bore"] - 0.01, 1.0)], fc="white", lw=0.5)
    v.axis((-r_s - 3, 0), (r_s + 3, 0))
    v.axis((0, -r_s - 3), (0, r_s + 3))
    v.hdim(-r_s, r_s, 0, 0, -r_s - 8 * k, f"Ø{2 * r_s:.2f} ±0.03")
    v.hdim(-p["r_bore"], p["r_bore"], 0, 0, 0.4 * p["r_bore"], f"Ø{2 * p['r_bore']:.2f} +0.03/0")
    v.note((p["r_bore"] + 1.2, 1.0), "chavetero 2.0 × 1.2", (14, 18))
    ang0 = math.pi / p["ns"]                               # la ranura 0 está centrada en π/ns
    v.circle((r_s * 0.85 * math.cos(ang0), r_s * 0.85 * math.sin(ang0)), 0.32 * r_s, color=DIM, lw=0.4)
    v.note(((r_s * 0.85 + 0.32 * r_s) * math.cos(ang0), (r_s * 0.85 + 0.32 * r_s) * math.sin(ang0)), "DETALLE D", (10, 10))
    r_t = r_s - p["h_tip"]
    r_b = r_t - p["h_slot"]
    ang = math.pi / 2 - ang0                               # gira la ranura 0 hasta quedar vertical
    rot = [(x * math.cos(ang) - y * math.sin(ang), x * math.sin(ang) + y * math.cos(ang)) for x, y in slot0]
    v2 = View(ax, 330, 120 - r_b * sd, sd)
    xs_lim = 2 * math.pi * r_s / p["ns"] * 0.8
    clip = []                                              # la ranura, con la abertura recortada en el diámetro exterior
    for x, y in rot:
        r = math.hypot(x, y)
        clip.append((x * r_s / r, y * r_s / r) if r > r_s else (x, y))
    v2.poly(clip, fc="white", lw=0.7)
    xo = p["b0"] / 2
    for sgn in (-1, 1):                                    # cara exterior de las zapatas a ambos lados de la abertura
        a_in, a_out = math.asin(xo / r_s), math.asin(min(xs_lim / r_s, 0.99))
        pts = [(sgn * r_s * math.sin(a_in + (a_out - a_in) * t / 10), r_s * math.cos(a_in + (a_out - a_in) * t / 10)) for t in range(11)]
        v2.ax.plot([v2.P(*q)[0] for q in pts], [v2.P(*q)[1] for q in pts], color=INK, lw=0.7)
    v2.line((-xs_lim, r_b - 1.5), (xs_lim, r_b - 1.5), color="#999", lw=0.4, ls="--")
    v2.title((0, r_s + 1.6), f"DETALLE D ({sd:g}:1)")
    b0, w = p["b0"], p["w_tooth"]
    v2.hdim(-b0 / 2, b0 / 2, r_s, r_s, r_s + 0.8, f"abertura {b0:.1f}")
    v2.vdim(r_b, r_t, 0, 0, -0.55 * xs_lim, f"ranura {p['h_slot']:.2f}")
    v2.vdim(r_t, r_s, b0 / 2, b0 / 2, 0.55 * xs_lim, f"zapata {p['h_tip']:.1f}")
    v2.note(rot[0], "R 0.3 (2×)", (-22, -14))
    ax.text(*v2.P(-xs_lim, r_b - 2.6), f"Diente de lados paralelos, ancho {w:.2f}. {p['ns']} ranuras a {360 / p['ns']:.2f}°.",
            fontsize=FS, color=DIM)
    save(pdf, fig)


# ------------------------------------------------------------------ 6. anillo del rotor
def sheet_ring(pdf, veh, p, m):
    poles = p["poles"]
    apo = p["r_mag_out"] + 0.05
    rc = apo / math.cos(math.pi / poles)
    s = fit_scale(2 * p["r_out"] + 30, 2 * p["r_out"] + 30, 200, 210)
    sd = 10.0
    notes = [f"1. Acero DC01 1.0 mm. {p['n_ring']} anillos por motor (alto {p['n_ring'] * 1.0:.0f} mm), pegados con epoxi, alineados por las muescas.",
             f"2. Interior de {poles} caras planas (una por imán): distancia entre caras opuestas {2 * apo:.2f} ±0.03.",
             "3. Marca cuadrada = polo 1 (orientación del apilado). Muescas R 0.5 a 180° para la varilla de alineación.",
             f"4. Exterior Ø{2 * p['r_out']:.2f} ±0.03: entra en la pollera de la tapa con juego para epoxi."]
    fig, ax = sheet("Anillo del rotor", f"M-{veh}-005", "DC01 1.0 mm", f"{p['n_ring']} por motor", f"{s:g} : 1 (detalle {sd:g}:1)", veh, notes)
    k = 1 / s
    v = View(ax, 25 + (p["r_out"] + 15 * k) * s, 175, s)
    v.circle((0, 0), p["r_out"])
    half = math.pi / poles
    v.poly([(rc * math.cos(half + 2 * math.pi * j / poles), rc * math.sin(half + 2 * math.pi * j / poles)) for j in range(poles)], lw=0.5)
    for a in (half, half + math.pi):
        v.circle((p["r_out"] * math.cos(a), p["r_out"] * math.sin(a)), 0.5, lw=0.5)
    v.axis((-p["r_out"] - 3, 0), (p["r_out"] + 3, 0))
    v.axis((0, -p["r_out"] - 3), (0, p["r_out"] + 3))
    v.hdim(-p["r_out"], p["r_out"], 0, 0, -p["r_out"] - 8 * k, f"Ø{2 * p['r_out']:.2f} ±0.03")
    v.hdim(-apo, apo, 0, 0, 0.3 * p["r_out"], f"entre caras {2 * apo:.2f} ±0.03")
    v.note((p["r_out"] * math.cos(half), p["r_out"] * math.sin(half)), "muesca R 0.5 (2 × 180°)", (12, 14))
    xs = apo * math.tan(half)
    v2 = View(ax, 330, 160 - apo * sd, sd)
    wall = [(-xs, apo), (xs, apo), (xs + 0.7, apo - 0.7 * math.tan(half) * 0), (xs + 0.7, p["r_out"] - 0.05), (-xs - 0.7, p["r_out"] - 0.05),
            (-xs - 0.7, apo)]
    v2.poly(wall, fc="#dddddd", lw=0.0)
    v2.line((-xs, apo), (xs, apo), lw=0.8)
    v2.line((-xs - 0.7, p["r_out"] - 0.05), (xs + 0.7, p["r_out"] - 0.05), lw=0.8)
    mw = p["magnet_w"]
    v2.poly([(-mw / 2, apo - 0.05 - p["h_magnet"]), (mw / 2, apo - 0.05 - p["h_magnet"]), (mw / 2, apo - 0.05), (-mw / 2, apo - 0.05)],
            fc="#e6b3c8", lw=0.5, hatch="..")
    v2.title((0, p["r_out"] + 1.6), f"DETALLE E ({sd:g}:1): cara plana con su imán")
    v2.hdim(-xs, xs, apo, apo, p["r_out"] + 0.6, f"cara {2 * xs:.2f}")
    v2.hdim(-mw / 2, mw / 2, apo - 0.05 - p["h_magnet"], apo - 0.05 - p["h_magnet"], apo - p["h_magnet"] - 0.9, f"imán {mw:.1f}")
    v2.vdim(apo, p["r_out"], xs + 0.7, xs + 0.7, xs + 1.6, f"pared {p['r_out'] - apo:.2f}")
    v2.note((-mw / 2, apo - 0.05 - p["h_magnet"] / 2), f"imán {p['h_magnet']:.1f} N48SH + 0.05 de epoxi", (-10, -14))
    save(pdf, fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    chosen = json.loads((INF / "M2_elegidos.json").read_text())
    for veh, c in chosen.items():
        p = G.params(veh, c)
        m = G.mech(veh, p, p["h_yoke_g"])
        slot0 = G.slot_polygon(p["ns"], 0, p["r_s"], p["w_tooth"], p["h_slot"], p["b0"])
        path = OUT / f"{veh.lower()}_planos.pdf"
        _PNG.update(veh=veh.lower(), n=0)
        with PdfPages(path) as pdf:
            sheet_assembly(pdf, veh, p, m)
            sheet_base(pdf, veh, p, m)
            sheet_cap(pdf, veh, p, m)
            sheet_shaft(pdf, veh, p, m)
            sheet_lamination(pdf, veh, p, m, slot0)
            sheet_ring(pdf, veh, p, m)
        print(path)


if __name__ == "__main__":
    main()
