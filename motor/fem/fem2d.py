"""M4 · Simulación electromagnética 2D (magnetostática no lineal) del outrunner elegido en M2.

Malla con gmsh (geometría exacta con arcos), solver propio de elementos finitos P1 en numpy/scipy:
    ∇·(ν ∇A) = −J − ∇×(ν_m Br m̂)        A = potencial vector axial, B = (∂A/∂y, −∂A/∂x)
- Hierro (láminas NO20 en el estator, acero común en el anillo del rotor) con su curva B-H (iteración de Picard).
- Imanes con magnetización radial alternada, μr = 1.05, Br según temperatura.
- Torque por el método de Arkkio en el entrehierro; flujo enlazado de cada fase sumando las bobinas por diente.

Limitaciones: 2D (sin efectos de extremo ni cabezas de bobina), la malla se rehace en cada posición del rotor (el
cogging tiene ruido numérico de ~0.5 % del torque de hover), corriente senoidal equivalente a la de 6 pasos.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

from motor.calculo.design import H_TIP, K_STACK, SLOT_OPENING
from motor.calculo.materials import MAGNETS, STEELS
from motor.calculo.winding import layout

MU0 = 4e-7 * math.pi


@dataclass
class Model:
    nodes: np.ndarray           # (n, 2) en metros
    tri: np.ndarray             # (m, 3) índices
    region: np.ndarray          # (m,) código de región
    sub: np.ndarray             # (m,) índice dentro de la región (ranura/imán)
    boundary: np.ndarray        # nodos con A = 0
    params: dict


# códigos de región
AIR, STATOR, ROTOR, MAGNET, COIL, GAP = 0, 1, 2, 3, 4, 5


def _nu_table(steel_key: str):
    bh = STEELS[steel_key].bh
    hs = np.array([h for h, _ in bh[1:]], float)
    bs = np.array([b for _, b in bh[1:]], float)
    return bs, hs


def nu_iron(b: np.ndarray, steel_key: str, stack: float = 1.0) -> np.ndarray:
    """Reluctividad ν = H/B de la curva B-H (extrapolada con pendiente μ0 en saturación). stack < 1: paquete laminado."""
    bs, hs = _nu_table(steel_key)
    b = np.maximum(b / stack, 1e-3)                       # el hierro real lleva el flujo en K_STACK de la sección
    h = np.where(b <= bs[-1], np.interp(b, np.concatenate(([0], bs)), np.concatenate(([0], hs))),
                 hs[-1] + (b - bs[-1]) / MU0)
    return h / b / stack


def nu_of_iron(bi: np.ndarray, m: Model, iron_s: np.ndarray, iron_r: np.ndarray, p: dict) -> np.ndarray:
    """ν del hierro para los elementos de hierro (en el orden de m.region[iron])."""
    iron = iron_s | iron_r
    out = np.empty(iron.sum())
    is_s = iron_s[iron]
    out[is_s] = nu_iron(bi[is_s], p["steel"], K_STACK)
    out[~is_s] = nu_iron(bi[~is_s], p["rotor_steel"])
    return out


def build_mesh(p: dict, rotor_angle: float, fine: float = 1.0) -> Model:
    """Malla de la sección completa con el rotor girado `rotor_angle` [rad mecánicos]."""
    import gmsh
    ns, pp = p["ns"], p["pole_pairs"]
    r_s, r_bore = p["r_s"], p["r_bore"]
    r_t = r_s - H_TIP * 1e3
    r_b = r_t - p["h_slot"]
    w = p["w_tooth"]
    r_mi, r_mo, r_out = p["r_mag_in"], p["r_mag_out"], p["r_out"]
    r_gm = (r_s + r_mi) / 2
    r_air = r_out * 1.25
    b0 = SLOT_OPENING * 1e3
    g = r_mi - r_s
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("motor")
    occ = gmsh.model.occ
    center = occ.addPoint(0, 0, 0)

    def pt(r, a):
        return occ.addPoint(r * math.cos(a), r * math.sin(a), 0)

    def arc(p1, p2):
        return occ.addCircleArc(p1, center, p2)

    def sector(r1, r2, a1, a2, edge1=None, edge2=None):
        """Región entre arcos r1, r2 y bordes; edge = ángulos (a_en_r1, a_en_r2) si el borde no es radial."""
        e1 = edge1 or (a1, a1)
        e2 = edge2 or (a2, a2)
        q1, q2, q3, q4 = pt(r1, e1[0]), pt(r2, e1[1]), pt(r2, e2[1]), pt(r1, e2[0])
        loop = occ.addCurveLoop([occ.addLine(q1, q2), arc(q2, q3), occ.addLine(q3, q4), arc(q4, q1)])
        return occ.addPlaneSurface([loop])

    inputs = []                                           # (dimtag, tipo, índice)
    for k in range(ns):
        phi_k = 2 * math.pi * k / ns
        phi_n = 2 * math.pi * (k + 1) / ns
        phi_s = (phi_k + phi_n) / 2
        left = sector(r_b, r_t, None, None, (phi_k + math.asin(w / 2 / r_b), phi_k + math.asin(w / 2 / r_t)), (phi_s, phi_s))
        right = sector(r_b, r_t, None, None, (phi_s, phi_s), (phi_n - math.asin(w / 2 / r_b), phi_n - math.asin(w / 2 / r_t)))
        opening = sector(r_t, r_s, None, None, (phi_s - math.asin(b0 / 2 / r_t), phi_s - math.asin(b0 / 2 / r_s)),
                         (phi_s + math.asin(b0 / 2 / r_t), phi_s + math.asin(b0 / 2 / r_s)))
        inputs += [((2, left), "slotL", k), ((2, right), "slotR", k), ((2, opening), "open", k)]
    half = p["pole_arc"] * math.pi / (2 * pp)
    for k in range(2 * pp):
        c = rotor_angle + k * math.pi / pp
        inputs.append(((2, sector(r_mi, r_mo, c - half, c + half)), "magnet", k))
    for name, r in (("bore", r_bore), ("stator", r_s), ("gap_in", r_gm), ("gap_out", r_mi), ("magzone", r_mo), ("rotor", r_out),
                    ("air", r_air)):
        inputs.append(((2, occ.addDisk(0, 0, 0, r, r)), name, 0))
    out, out_map = occ.fragment([d for d, _, _ in inputs], [])
    occ.synchronize()
    owner: dict[int, list] = {}
    for (_dt, kind, idx), pieces in zip(inputs, out_map):
        for _, tag in pieces:
            owner.setdefault(tag, []).append((kind, idx))
    order = ["bore", "stator", "gap_in", "gap_out", "magzone", "rotor", "air"]
    cls = {}
    for _, tag in out:
        own = owner[tag]
        kinds = {k for k, _ in own}
        if "slotL" in kinds or "slotR" in kinds:
            kind, idx = next((k, i) for k, i in own if k in ("slotL", "slotR"))
            cls[tag] = (COIL, 2 * idx + (0 if kind == "slotL" else 1))
        elif "open" in kinds:
            cls[tag] = (AIR, -1)
        elif "magnet" in kinds:
            cls[tag] = (MAGNET, next(i for k, i in own if k == "magnet"))
        else:
            smallest = min((k for k in kinds if k in order), key=order.index)
            cls[tag] = {"bore": (AIR, -1), "stator": (STATOR, -1), "gap_in": (GAP, 0), "gap_out": (GAP, 1),
                        "magzone": (AIR, -1), "rotor": (ROTOR, -1), "air": (AIR, -1)}[smallest]
    h_far = max(0.6, r_s / 18) / fine
    h_gap = g / 3 / fine
    f = gmsh.model.mesh.field.add("MathEval")
    gmsh.model.mesh.field.setString(f, "F", f"Min({h_far}, {h_gap} + 0.25*Abs(Sqrt(x*x+y*y) - {r_gm}))")
    gmsh.model.mesh.field.setAsBackgroundMesh(f)
    for opt in ("Mesh.MeshSizeExtendFromBoundary", "Mesh.MeshSizeFromPoints", "Mesh.MeshSizeFromCurvature"):
        gmsh.option.setNumber(opt, 0)
    gmsh.model.mesh.generate(2)
    tags, coords, _ = gmsh.model.mesh.getNodes()
    idx_of = {int(t): i for i, t in enumerate(tags)}
    xy = coords.reshape(-1, 3)[:, :2] * 1e-3
    tris, reg, sub = [], [], []
    for _, tag in out:
        et, _, enodes = gmsh.model.mesh.getElements(2, tag)
        for t, en in zip(et, enodes):
            if t != 2:
                continue
            tri = np.array([idx_of[int(n)] for n in en], int).reshape(-1, 3)
            tris.append(tri)
            reg.append(np.full(len(tri), cls[tag][0]))
            sub.append(np.full(len(tri), cls[tag][1]))
    gmsh.finalize()
    tri = np.vstack(tris)
    r = np.hypot(xy[:, 0], xy[:, 1])
    boundary = np.where(r > r_air * 1e-3 * (1 - 1e-6))[0]
    return Model(xy, tri, np.concatenate(reg), np.concatenate(sub), boundary, p)


def _grad(m: Model):
    x, y = m.nodes[m.tri, 0], m.nodes[m.tri, 1]
    b = np.stack([y[:, 1] - y[:, 2], y[:, 2] - y[:, 0], y[:, 0] - y[:, 1]], 1)
    c = np.stack([x[:, 2] - x[:, 1], x[:, 0] - x[:, 2], x[:, 1] - x[:, 0]], 1)
    area = 0.5 * (b[:, 0] * c[:, 1] - b[:, 1] * c[:, 0])
    return b, c, area


def solve(m: Model, coil_current: np.ndarray | None, t_magnet: float = 20.0, iters: int = 40) -> dict:
    """coil_current[2·ranura + lado] = amper-vueltas (con signo) del lado de bobina. Devuelve A, B por elemento y torque."""
    p = m.params
    b, c, area = _grad(m)
    n = len(m.nodes)
    mag = MAGNETS[p["magnet"]]
    br = mag.br(t_magnet)
    nu0 = 1 / MU0
    nu_m = 1 / (MU0 * mag.mu_rec)
    cx, cy = m.nodes[m.tri].mean(1).T
    rc = np.hypot(cx, cy)
    rhs = np.zeros(n)
    # imanes: magnetización radial, signo alternado por polo
    mm = m.region == MAGNET
    sign = np.where(m.sub[mm] % 2 == 0, 1.0, -1.0)
    mx, my = sign * cx[mm] / rc[mm], sign * cy[mm] / rc[mm]
    np.add.at(rhs, m.tri[mm], (nu_m * br * (mx[:, None] * c[mm] - my[:, None] * b[mm]) / 2))
    # bobinas: densidad de corriente uniforme en cada mitad de ranura
    if coil_current is not None:
        cm = m.region == COIL
        side = m.sub[cm]
        side_area = np.bincount(side, weights=area[cm], minlength=2 * p["ns"])
        j = coil_current[side] / side_area[side]
        np.add.at(rhs, m.tri[cm], (j * area[cm] / 3)[:, None] * np.ones((1, 3)))
    nu_base = np.full(len(m.tri), nu0)
    nu_base[mm] = nu_m
    iron_s, iron_r = m.region == STATOR, m.region == ROTOR
    iron = iron_s | iron_r
    free = np.zeros(n, bool)
    free[np.unique(m.tri)] = True                         # nodos sueltos (punto central auxiliar) fuera de las incógnitas
    free[m.boundary] = False
    se = (b[:, :, None] * b[:, None, :] + c[:, :, None] * c[:, None, :]) / (4 * area[:, None, None])   # rigidez con ν = 1
    rows = np.repeat(m.tri, 3, axis=1).ravel()
    cols = np.tile(m.tri, (1, 3)).ravel()

    def nu_of(bm):
        nu = nu_base.copy()
        nu[iron_s] = nu_iron(bm[iron_s], p["steel"], K_STACK)
        nu[iron_r] = nu_iron(bm[iron_r], p["rotor_steel"])
        return nu

    def fields(a):
        bx = (c * a[m.tri]).sum(1) / (2 * area)
        by = -(b * a[m.tri]).sum(1) / (2 * area)
        return bx, by, np.hypot(bx, by)

    def residual(a, nu):
        ae = a[m.tri]
        r = np.zeros(n)
        np.add.at(r, m.tri, nu[:, None] * np.einsum("eij,ej->ei", se, ae))
        return r - rhs

    # Newton-Raphson con búsqueda de línea. Jacobiano: ν·S + 2·(dν/dB²)·(S·a)(S·a)ᵀ/Δ en el hierro
    a = np.zeros(n)
    bm = np.ones(len(m.tri))
    hist = []
    for it in range(iters):
        nu = nu_of(bm)
        r = residual(a, nu)
        rn = np.linalg.norm(r[free])
        db = 1e-4
        dnu_db2 = np.zeros(len(m.tri))
        bi = np.maximum(bm[iron], 1e-3)
        dnu = (nu_of_iron(bi + db, m, iron_s, iron_r, p) - nu_of_iron(np.maximum(bi - db, 1e-4), m, iron_s, iron_r, p)) / (2 * db)
        dnu_db2[iron] = dnu / (2 * bi)
        sa = np.einsum("eij,ej->ei", se, a[m.tri])
        jac = nu[:, None, None] * se + 2 * dnu_db2[:, None, None] * sa[:, :, None] * sa[:, None, :] / area[:, None, None]
        k = coo_matrix((jac.ravel(), (rows, cols)), shape=(n, n)).tocsr()
        delta = np.zeros(n)
        delta[free] = spsolve(k[free][:, free], -r[free])
        step = 1.0
        for _ in range(12):                               # búsqueda de línea: el residuo tiene que bajar
            a_try = a + step * delta
            bm_try = fields(a_try)[2]
            if np.linalg.norm(residual(a_try, nu_of(bm_try))[free]) < rn or step < 1e-3:
                break
            step /= 2
        a, bm = a_try, bm_try
        rel = step * np.linalg.norm(delta) / max(np.linalg.norm(a), 1e-15)
        hist.append((float(rn), float(rel)))
        if it > 0 and rel < 1e-6:
            break
    bx, by, bm = fields(a)
    # torque de Arkkio en las dos capas del entrehierro
    gm = m.region == GAP
    r1, r2 = p["r_s"] * 1e-3, p["r_mag_in"] * 1e-3
    br_r = (bx[gm] * cx[gm] + by[gm] * cy[gm]) / rc[gm]
    bt = (-bx[gm] * cy[gm] + by[gm] * cx[gm]) / rc[gm]
    torque = p["l_stack"] * np.sum(area[gm] * rc[gm] * br_r * bt) / (MU0 * (r2 - r1))
    return {"a": a, "bx": bx, "by": by, "bmag": bm, "torque": torque, "area": area, "cx": cx, "cy": cy, "iterations": it + 1,
            "br": br, "nu_m": nu_m, "conv": hist}


def coil_sides(p: dict) -> list[tuple[int, int, int]]:
    """(fase 0-2, signo, lado de ranura) para cada lado de bobina. Bobina del diente j: lados en la ranura j−1 (mitad R) y j (mitad L)."""
    lay = layout(p["ns"], p["pole_pairs"])
    out = []
    for j, (ph, sg) in enumerate(lay["coils"]):
        phase = "ABC".index(ph)
        out.append((phase, sg, 2 * j + 0))                       # ranura j, mitad junto al diente j: +
        out.append((phase, -sg, 2 * ((j - 1) % p["ns"]) + 1))      # ranura j−1, mitad junto al diente j: −
    return out


def phase_currents_to_coils(p: dict, i_abc: tuple[float, float, float]) -> np.ndarray:
    cur = np.zeros(2 * p["ns"])
    for phase, sg, side in coil_sides(p):
        cur[side] += sg * p["turns"] * i_abc[phase]
    return cur


def flux_linkage(m: Model, sol: dict) -> np.ndarray:
    """Flujo enlazado de cada fase [Wb] (vueltas en serie por fase: todas las bobinas de la fase en serie)."""
    p = m.params
    cm = m.region == COIL
    side = m.sub[cm]
    a_el = sol["a"][m.tri[cm]].mean(1)
    side_area = np.bincount(side, weights=sol["area"][cm], minlength=2 * p["ns"])
    a_avg = np.bincount(side, weights=a_el * sol["area"][cm], minlength=2 * p["ns"]) / side_area
    lam = np.zeros(3)
    for phase, sg, s in coil_sides(p):
        lam[phase] += sg * p["turns"] * a_avg[s] * p["l_stack"]
    return lam


def params_from(chosen: dict) -> dict:
    d, g = chosen["design"], chosen["geometry"]
    return {"ns": d["ns"], "pole_pairs": d["pole_pairs"], "r_s": d["d_stator"] / 2 * 1e3, "r_bore": g["r_bore"] * 1e3,
            "h_slot": g["h_slot"] * 1e3, "w_tooth": g["w_tooth"] * 1e3, "r_mag_in": g["r_mag_in"] * 1e3, "r_mag_out": g["r_mag_out"] * 1e3,
            "r_out": g["r_out"] * 1e3, "pole_arc": d["pole_arc"], "magnet": d["magnet"], "steel": d["steel"],
            "rotor_steel": d["rotor_steel"], "turns": d["turns"], "delta": d["delta"], "l_stack": d["l_stack"]}
