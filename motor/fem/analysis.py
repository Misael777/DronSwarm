"""M4 · Verificación por elementos finitos de los motores elegidos en M2 → motor/informes/M4_fem.md + figuras + JSON

Para cada dron: campo en vacío (inducción en dientes, yugos e imanes), flujo enlazado en medio período eléctrico
(contra-FEM, Kv y armónicos), cogging en un período de cogging, torque con carga (hover y máximo, corriente en fase
con la contra-FEM) y desmagnetización de los imanes a 100 °C con 1.5 × la corriente máxima.

    .venv/bin/python -m motor.fem.analysis [--fine 1.0]
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from motor.calculo.materials import MAGNETS
from motor.fem.fem2d import (
    COIL,
    GAP,
    MAGNET,
    ROTOR,
    STATOR,
    build_mesh,
    flux_linkage,
    params_from,
    phase_currents_to_coils,
    solve,
)

ROOT = Path(__file__).resolve().parents[2]
INF = ROOT / "motor" / "informes"
T_HOT = 100.0
ITERATION_NOTE = ("**Ciclo FEM → cálculo (2 vueltas).** En la 1ª vuelta la FEM dio un Kv 3.5-5.6 % menor que el cálculo de M2 "
                  "(más flujo: la fuga de 0.92 era conservadora) y la desmagnetización del DS-I quedó en 0.72 (límite 0.7; el "
                  "circuito simple daba 0.52). Con eso, el DS-I no llegaba a las rpm máximas con la batería vacía. Se calibró el "
                  "modelo analítico (fuga 0.96, desmagnetización ×1.5), se reconstruyeron los comerciales, se volvió a optimizar "
                  "(M2) y esta es la 2ª vuelta. El optimizador pasó solo a imanes N48SH.")


def fundamental(theta_e: np.ndarray, lam: np.ndarray) -> tuple[float, float, float]:
    """Amplitud, fase y THD de λ(θe) muestreado en medio período (se completa con λ(θ+π) = −λ(θ))."""
    th = np.concatenate([theta_e, theta_e + math.pi])
    y = np.concatenate([lam, -lam])
    a1 = 2 * np.mean(y * np.cos(th))
    b1 = 2 * np.mean(y * np.sin(th))
    amp = math.hypot(a1, b1)
    harm = [math.hypot(2 * np.mean(y * np.cos(k * th)), 2 * np.mean(y * np.sin(k * th))) for k in (3, 5, 7)]
    return amp, math.atan2(b1, a1), math.sqrt(sum(h * h for h in harm)) / amp


def region_stats(m, s) -> dict:
    out = {}
    for name, r in (("estator", STATOR), ("rotor", ROTOR), ("imanes", MAGNET)):
        sel = m.region == r
        out[name] = {"p95": float(np.percentile(s["bmag"][sel], 95)), "mean": float(s["bmag"][sel].mean())}
    cx, cy = s["cx"], s["cy"]
    rc = np.hypot(cx, cy)
    g = m.region == GAP
    out["entrehierro_p90"] = float(np.percentile(np.abs((s["bx"] * cx + s["by"] * cy) / rc)[g], 90))
    return out


def demag_check(m, s, mag_key: str) -> float:
    """Peor relación (campo desmagnetizante en la dirección de magnetización) / Hcj a T_HOT. Debe ser < 0.7."""
    mag = MAGNETS[mag_key]
    sel = m.region == MAGNET
    sign = np.where(m.sub[sel] % 2 == 0, 1.0, -1.0)
    cx, cy = s["cx"][sel], s["cy"][sel]
    rc = np.hypot(cx, cy)
    bn = (s["bx"][sel] * cx + s["by"][sel] * cy) / rc * sign
    h_n = (bn - mag.br(T_HOT)) / (4e-7 * math.pi * mag.mu_rec)      # A/m, negativo = desmagnetizante
    return float(np.percentile(-h_n, 99.5) / (mag.hcj(T_HOT) * 1e3))


def sine_currents(i_pk: float, theta_e: float, deltas: list[float]) -> tuple:
    """Corriente de cada fase en fase con su contra-FEM (e ∝ −dλ/dθ ⇒ i ∝ sin(θe − δ))."""
    return tuple(i_pk * math.sin(theta_e - d) for d in deltas)


def analyze(veh: str, chosen: dict, fine: float, plots: bool = True) -> dict:
    p = params_from(chosen)
    pp = p["pole_pairs"]
    res = {"vehicle": veh, "label": chosen["label"]}
    # 1. vacío en θ = 0
    m0 = build_mesh(p, 0.0, fine)
    s0 = solve(m0, None)
    res["nodes"] = len(m0.nodes)
    res["noload"] = region_stats(m0, s0)
    res["analytic"] = {"bg20": chosen["geometry"]["bg20"], "b_tooth": chosen["design"]["b_tooth"], "b_yoke": chosen["design"]["b_yoke"],
                       "kv": chosen["kv"]}
    # 2. contra-FEM: medio período eléctrico
    th_m = np.linspace(0, math.pi / pp, 12, endpoint=False)
    lam = []
    for t in th_m:
        m = build_mesh(p, t, fine)
        lam.append(flux_linkage(m, solve(m, None)))
    lam = np.array(lam)
    fits = [fundamental(th_m * pp, lam[:, k]) for k in range(3)]
    amp = float(np.mean([f[0] for f in fits]))
    ke_line = pp * amp * (1 if p["delta"] else math.sqrt(3))
    res["bemf"] = {"lambda_phase_wb": amp, "thd": float(np.mean([f[2] for f in fits])), "kv_fem": 60 / (2 * math.pi * ke_line),
                   "deltas": [f[1] for f in fits], "samples": lam.tolist(), "theta_e": (th_m * pp).tolist()}
    # 3. cogging: un período de cogging
    lcm = math.lcm(p["ns"], 2 * pp)
    th_c = np.linspace(0, 2 * math.pi / lcm, 10, endpoint=False)
    cog = []
    for t in th_c:
        m = build_mesh(p, t, fine * 1.3)
        cog.append(solve(m, None)["torque"])
    cog = np.array(cog)
    hover_t = chosen["ops"]["hover_4500m_0C"]["torque"]
    res["cogging"] = {"pk_pk_nm": float(cog.max() - cog.min()), "pct_of_hover": float((cog.max() - cog.min()) / hover_t * 100),
                      "samples": cog.tolist(), "period_deg": 360 / lcm}
    # 4. torque con carga: hover y máximo, 6 posiciones en 60° eléctricos
    kt_dc = 60 / (2 * math.pi * chosen["kv"])
    res["load"] = {}
    for point in ("hover_4500m_0C", "maximo_twr20"):
        op = chosen["ops"][point]
        i_dc = op["current"]
        i_pk = (math.sqrt(3) / 1.5 if not p["delta"] else 1 / 1.5) * i_dc          # senoidal con el mismo torque que la de 6 pasos
        tq = []
        for t in np.linspace(0, math.pi / 3 / pp, 6, endpoint=False):
            m = build_mesh(p, t, fine)
            cur = phase_currents_to_coils(p, sine_currents(i_pk, t * pp, res["bemf"]["deltas"]))
            s = solve(m, cur)
            tq.append(abs(s["torque"]))
            if point == "maximo_twr20" and t == 0 and plots:
                res["max_fields"] = region_stats(m, s)
                field_plot(m, s, INF / f"M4_campo_{veh.lower()}.png", f"{veh} · {chosen['label']} · corriente máxima ({i_dc:.1f} A)")
        tq = np.array(tq)
        t_analytic = kt_dc * i_dc                                                  # mismo Kt del cálculo (20 °C), sin pérdidas en vacío
        res["load"][point] = {"current_dc_a": i_dc, "torque_fem_nm": float(tq.mean()), "ripple_pct": float((tq.max() - tq.min()) / tq.mean() * 100),
                              "torque_analytic_nm": t_analytic, "ratio": float(tq.mean() / t_analytic)}
    # 5. desmagnetización: 1.5 × corriente máxima, imanes a 100 °C, 4 posiciones
    i_pk = (math.sqrt(3) / 1.5 if not p["delta"] else 1 / 1.5) * chosen["ops"]["maximo_twr20"]["current"] * 1.5
    worst = 0.0
    for t in np.linspace(0, math.pi / pp, 4, endpoint=False):
        m = build_mesh(p, t, fine)
        cur = phase_currents_to_coils(p, sine_currents(-i_pk, t * pp + math.pi / 2, res["bemf"]["deltas"]))   # eje d negativo: lo peor
        s = solve(m, cur, t_magnet=T_HOT)
        worst = max(worst, demag_check(m, s, p["magnet"]))
    res["demag_ratio"] = worst
    return res


def field_plot(m, s, path: Path, title: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.tri import Triangulation
    cmap = LinearSegmentedColormap.from_list("azul", ["#f7f9fc", "#bcd3f2", "#5b9be6", "#2a78d6", "#123f75"])
    tri = Triangulation(m.nodes[:, 0] * 1e3, m.nodes[:, 1] * 1e3, m.tri)
    fig, ax = plt.subplots(figsize=(6.2, 6.2), facecolor="#fcfcfb")
    pc = ax.tripcolor(tri, facecolors=np.clip(s["bmag"], 0, 2.2), cmap=cmap, vmin=0, vmax=2.2)
    ax.tricontour(tri, s["a"], levels=40, colors="#0b0b0b", linewidths=0.35)
    coil = m.region == COIL
    ax.tripcolor(Triangulation(tri.x, tri.y, m.tri[coil]), facecolors=np.ones(coil.sum()), cmap=LinearSegmentedColormap.from_list(
        "cu", ["#eb6834", "#eb6834"]), alpha=0.25)
    r = m.params["r_out"] * 1.12
    ax.set_xlim(-r, r)
    ax.set_ylim(-r, r)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, color="#0b0b0b", fontsize=10, loc="left")
    cb = fig.colorbar(pc, ax=ax, shrink=0.7, pad=0.02)
    cb.set_label("|B| [T]", color="#52514e")
    cb.ax.tick_params(colors="#52514e", labelsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor="#fcfcfb")
    plt.close(fig)


def write_report(res: dict, iteration_note: str = "") -> None:
    L = ["# M4 · Verificación por elementos finitos (2D, no lineal)", "",
         "> Generado por `motor/fem/analysis.py` (malla gmsh, solver Newton-Raphson propio en `motor/fem/fem2d.py`). No editar a mano.", "",
         "Sección completa del motor con el hierro no lineal (curvas B-H), imanes con magnetización radial y las bobinas por diente "
         "de M2. Corriente senoidal con el mismo torque que la de 6 pasos del ESC.", ""]
    if iteration_note:
        L += [iteration_note, ""]
    L += ["| Verificación | Criterio | " + " | ".join(res) + " |", "|---|---|" + "---|" * len(res)]

    def row(label, crit, fn):
        L.append(f"| {label} | {crit} | " + " | ".join(fn(r) for r in res.values()) + " |")
    row("Malla", "—", lambda r: f"{r['nodes']:,} nodos")
    row("Inducción en el entrehierro (bajo el imán)", "≈ cálculo", lambda r: f"{r['noload']['entrehierro_p90']:.2f} T (cálculo {r['analytic']['bg20']:.2f})")
    row("Estator en vacío (p95)", "≤ 1.8 T", lambda r: f"{r['noload']['estator']['p95']:.2f} T")
    row("Anillo del rotor en vacío (p95)", "≤ 1.8 T", lambda r: f"{r['noload']['rotor']['p95']:.2f} T")
    row("Estator a corriente máxima (p95)", "≤ 2.0 T", lambda r: f"{r['max_fields']['estator']['p95']:.2f} T")
    row("**Kv**", "± 5 % del cálculo", lambda r: f"**{r['bemf']['kv_fem']:.0f}** (cálculo {r['analytic']['kv']:.0f}, "
        f"{(r['bemf']['kv_fem'] / r['analytic']['kv'] - 1) * 100:+.1f} %)")
    row("Armónicos de la contra-FEM (3°, 5°, 7°)", "informativo", lambda r: f"{r['bemf']['thd']:.1%}")
    row("**Cogging** pico a pico", "< 5 % del torque de hover", lambda r: f"**{r['cogging']['pk_pk_nm'] * 1e3:.1f} mN·m = "
        f"{r['cogging']['pct_of_hover']:.1f} %** (período {r['cogging']['period_deg']:.2f}°)")
    row("Torque en hover: FEM / cálculo", "0.95-1.05", lambda r: f"{r['load']['hover_4500m_0C']['torque_fem_nm']:.3f} / "
        f"{r['load']['hover_4500m_0C']['torque_analytic_nm']:.3f} N·m = **{r['load']['hover_4500m_0C']['ratio']:.2f}**")
    row("Torque a corriente máxima: FEM / cálculo", "≥ 0.90 (saturación)", lambda r: f"{r['load']['maximo_twr20']['torque_fem_nm']:.3f} / "
        f"{r['load']['maximo_twr20']['torque_analytic_nm']:.3f} N·m = **{r['load']['maximo_twr20']['ratio']:.2f}**")
    row("Rizado de torque a corriente máxima", "informativo", lambda r: f"{r['load']['maximo_twr20']['ripple_pct']:.1f} %")
    row("**Desmagnetización** (1.5 × Imax, imanes a 100 °C)", "< 0.7 de Hcj", lambda r: f"**{r['demag_ratio']:.2f}**")
    L += [""]
    for veh in res:
        L += [f"![campo {veh}](M4_campo_{veh.lower()}.png)", ""]
    ok = {v: (abs(r["bemf"]["kv_fem"] / r["analytic"]["kv"] - 1) <= 0.05 and r["cogging"]["pct_of_hover"] < 5
              and 0.95 <= r["load"]["hover_4500m_0C"]["ratio"] <= 1.05 and r["load"]["maximo_twr20"]["ratio"] >= 0.90
              and r["demag_ratio"] < 0.7) for v, r in res.items()}
    L += ["## Resultado", ""]
    for v, good in ok.items():
        L.append(f"- **{v}: {'cumple todas las verificaciones' if good else 'NO cumple todas las verificaciones (ver tabla)'}.**")
    L += ["", "## Limitaciones", "",
          "- 2D: sin flujo de extremo ni cabezas de bobina (con paquetes cortos, el flujo real es algo menor que el 2D: el Kv real "
          "puede salir 2-5 % más alto). Se mide en el banco (M8).",
          "- La malla se rehace en cada posición: el cogging tiene ruido numérico del orden de 0.5 % del torque de hover.",
          "- Desmagnetización con el criterio de la rodilla (H < 0.7·Hcj en el 99.5 % del imán), no con un modelo de histéresis.", ""]
    (INF / "M4_fem.md").write_text("\n".join(L))


def run(fine: float, note: str = ITERATION_NOTE) -> dict:
    chosen = json.loads((INF / "M2_elegidos.json").read_text())
    res = {veh: analyze(veh, chosen[veh], fine) for veh in ("DS-I", "DS-D")}
    (INF / "M4_fem.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float) + "\n")
    write_report(res, note)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fine", type=float, default=1.0)
    a = ap.parse_args()
    for v, r in run(a.fine).items():
        print(v, json.dumps({k: r[k] for k in ("noload", "cogging", "load", "demag_ratio")}, default=float)[:900],
              "kv_fem", round(r["bemf"]["kv_fem"]), "kv", r["analytic"]["kv"])
