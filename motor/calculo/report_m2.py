"""M2 · Informe de diseño → motor/informes/M2_diseno.md, figuras y M2_elegidos.json (entrada de M3-M6).

    .venv/bin/python -m motor.calculo.report_m2          (después de motor.calculo.optimize)
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from motor.calculo.design import (  # noqa: E402
    K_IRON,
    K_SIX_STEP_CU,
    K_THERMAL,
    RECON,
    calibrate_with_mn4006,
    thermal_calibration,
    wire_choice,
)
from motor.calculo.loss_model import read_bench  # noqa: E402
from motor.calculo.optimize import weighted  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INF = ROOT / "motor" / "informes"
REQ = ROOT / "motor" / "requisitos" / "puntos_operacion.json"
BENCH = ROOT / "motor" / "requisitos" / "datos_cots" / "mn4006_kv380_15x5.csv"

# Paleta de referencia (dataviz): superficie, tinta, neutro de la nube, serie 1 (azul) y serie 2 (naranja)
SURF, INK, INK2, NEUTRAL, BLUE, ORANGE = "#fcfcfb", "#0b0b0b", "#52514e", "#c9c8c2", "#2a78d6", "#eb6834"
LOSS_COLORS = {"cobre": "#2a78d6", "hierro": "#eb6834", "imanes": "#1baf7a", "rodamientos": "#eda100"}

# Elección: el candidato más robusto a un bobinado peor entre los que ganan en autonomía (ver §Robustez)
CHOICE = {"DS-I": "B_max_eficiencia_masa_meta", "DS-D": "C_liviano_que_cumple"}
NAMES = {"A_max_autonomia": "A · máxima autonomía", "B_max_eficiencia_masa_meta": "B · máxima eficiencia con la masa meta",
         "C_liviano_que_cumple": "C · el más liviano que cumple"}


def wire_plan(a_cond_m2: float) -> str:
    """Hilos en paralelo para la sección de cobre de una vuelta (ver design.wire_choice)."""
    w = wire_choice(a_cond_m2)
    extra = f" (cobre {(1 / w['r_factor'] - 1) * 100:+.0f} % del diseño)" if abs(w["r_factor"] - 1) > 0.015 else ""
    return w["label"] + extra


def magnet_spec(c: dict) -> str:
    d, g = c["design"], c["geometry"]
    n_poles = 2 * d["pole_pairs"]
    arc = d["pole_arc"] * 2 * math.pi * g["r_mag_in"] / n_poles
    segs = 2 if d["l_stack"] > 15e-3 else 1
    return (f"{n_poles * segs} imanes {d['magnet']} de {arc * 1e3:.1f} × {d['l_stack'] / segs * 1e3:.1f} × {d['h_magnet'] * 1e3:.1f} mm "
            f"(ancho × largo × espesor, magnetizados en el espesor)")


def fig_tradeoff(res: dict, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), facecolor=SURF)
    for ax, (veh, v) in zip(axes, res["vehicles"].items()):
        ax.set_facecolor(SURF)
        cloud = v["cloud"]
        ax.scatter([c[0] for c in cloud], [100 * (c[2] - 1) for c in cloud], s=6, color=NEUTRAL, lw=0, label="diseños válidos")
        fr = sorted(v["front"], key=lambda f: f["mass_g"])
        ax.scatter([f["mass_g"] for f in fr], [100 * (f["endurance_rel"] - 1) for f in fr], s=18, color=BLUE, lw=0,
                   label="frente de Pareto (autonomía, masa, costo)")
        ref = v["reference"]
        ax.scatter([ref["mass_model_kg"] * 1e3], [0], s=70, marker="D", color=ORANGE, edgecolor=SURF, lw=2, zorder=5, label="comercial")
        ax.annotate(ref["name"].split(" (")[0], (ref["mass_model_kg"] * 1e3, 0), xytext=(8, -14), textcoords="offset points",
                    color=INK2, fontsize=8)
        for k, c in v["candidates"].items():
            x, y = c["mass"]["total"] * 1e3, 100 * (c["endurance_rel"] - 1)
            chosen = k == CHOICE[veh]
            ax.scatter([x], [y], s=90 if chosen else 50, facecolor=SURF, edgecolor=INK, lw=2 if chosen else 1, zorder=6)
            off = {"A": (-12, 8), "B": (9, 6), "C": (9, -14)}[k[0]]
            ax.annotate(k[0] + (" (elegido)" if chosen else ""), (x, y), xytext=off, textcoords="offset points", color=INK, fontsize=9,
                        fontweight="bold" if chosen else "normal", ha="right" if off[0] < 0 else "left")
        ax.axhline(0, color=INK2, lw=0.8, ls=(0, (3, 3)))
        ax.set_ylim(-12, max(100 * (f["endurance_rel"] - 1) for f in fr) + 2.5)    # la zona útil: cerca y por encima del comercial
        ax.set_xlim(ref["mass_model_kg"] * 1e3 * 0.55, ref["mass_model_kg"] * 1e3 * 2.2)
        ax.set_title(f"{veh}", color=INK, fontsize=11, loc="left")
        ax.set_xlabel("masa del motor (modelo) [g]", color=INK2, fontsize=9)
        ax.set_ylabel("autonomía del dron vs comercial [%]", color=INK2, fontsize=9)
        ax.tick_params(colors=INK2, labelsize=8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(NEUTRAL)
        ax.grid(color="#ececea", lw=0.6)
        ax.set_axisbelow(True)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", fontsize=8, frameon=False, ncol=3, labelcolor=INK2)
    fig.savefig(path, dpi=140, facecolor=SURF)
    plt.close(fig)


def hover_losses(res: dict, req_all: dict) -> dict:
    out = {}
    for veh, v in res["vehicles"].items():
        _, ops_ref = weighted(RECON[veh], req_all[veh])
        c = v["candidates"][CHOICE[veh]]
        rows = []
        for name, op in (("comercial", ops_ref["hover_4500m_0C"]), ("propio (elegido)", c["ops"]["hover_4500m_0C"])):
            rows.append((name, {"cobre": op["p_copper"], "hierro": op["p_iron"], "imanes": op["p_magnet"], "rodamientos": op["p_bearing"]}))
        out[veh] = rows
    return out


def fig_losses(losses: dict, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 2.3), facecolor=SURF)
    for ax, (veh, rows) in zip(axes, losses.items()):
        ax.set_facecolor(SURF)
        for i, (_name, parts) in enumerate(rows):
            left = 0.0
            for k, val in parts.items():
                ax.barh(i, val, left=left, height=0.55, color=LOSS_COLORS[k], edgecolor=SURF, lw=2, label=k if i == 0 else None)
                left += val
            ax.text(left + 0.3, i, f"{left:.1f} W", va="center", color=INK, fontsize=9)
        ax.set_yticks(range(len(rows)), [r[0] for r in rows], color=INK, fontsize=9)
        ax.invert_yaxis()
        ax.set_title(f"{veh} · pérdidas por motor en hover (4,500 msnm)", color=INK, fontsize=10, loc="left")
        ax.tick_params(colors=INK2, labelsize=8)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(NEUTRAL)
        ax.set_xlim(0, max(sum(p.values()) for _, p in rows) * 1.25)
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", fontsize=8, frameon=False, ncol=4, labelcolor=INK2)
    fig.savefig(path, dpi=140, facecolor=SURF)
    plt.close(fig)


def main() -> None:
    res = json.loads((INF / "M2_candidatos.json").read_text())
    req_all = json.loads(REQ.read_text())
    fig_tradeoff(res, INF / "M2_compromiso.png")
    losses = hover_losses(res, req_all)
    fig_losses(losses, INF / "M2_perdidas_hover.png")
    cal = calibrate_with_mn4006(read_bench(BENCH))
    th = thermal_calibration()

    chosen = {}
    L = ["# M2 · Diseño del motor propio (cálculo analítico y optimización)", "",
         "> Generado por `motor/calculo/optimize.py` + `report_m2.py`. No editar a mano.", ""]
    # resumen
    L += ["## Resumen", "",
          "| | Comercial | Propio elegido | Diferencia |", "|---|---|---|---|"]
    for veh, v in res["vehicles"].items():
        c, ref = v["candidates"][CHOICE[veh]], v["reference"]
        d = c["design"]
        L += [f"| **{veh}** | {ref['name'].split(' (')[0]} | {c['label']}, estator Ø{d['d_stator'] * 1e3:.1f}×{d['l_stack'] * 1e3:.1f} mm | |",
              f"| Eficiencia ponderada (mismo modelo) | {ref['weighted_efficiency']:.1%} | {c['eta_weighted']:.1%} | **{(c['eta_weighted'] - ref['weighted_efficiency']) * 100:+.1f} puntos** |",
              f"| Masa (mismo modelo) | {ref['mass_model_kg'] * 1e3:.0f} g | {c['mass']['total'] * 1e3:.0f} g | {(c['mass']['total'] - ref['mass_model_kg']) * 1e3:+.0f} g |",
              f"| Autonomía del dron | — | — | **{(c['endurance_rel'] - 1) * 100:+.1f} %** |",
              f"| Costo | US${req_all[veh]['reference_cots']['cost_usd']} (compra) | US${c['cost']['total']:.0f} (materiales) | "
              f"{c['cost']['total'] / req_all[veh]['reference_cots']['cost_usd']:.0%} del comercial |"]
    L += ["", "**Comparación justa:** el comercial se reconstruye desde su ficha y se evalúa con el mismo modelo que el diseño "
          "propio (eficiencia y masa, modelo contra modelo). La ganancia viene de **más cobre por la misma masa** "
          "(estator más ancho y corto, bobinado concentrado de alto factor) y de láminas de 0.2 mm a menor inducción.", "",
          "![compromiso](M2_compromiso.png)", "", "![pérdidas en hover](M2_perdidas_hover.png)", ""]
    # validación
    L += ["## 1. Validación del modelo", "",
          "El modelo (`design.py`) reconstruye a los comerciales desde su nombre y su ficha (tamaño del estator, ranuras/polos, "
          "diámetro exterior) con vueltas y ranuras plausibles:", "",
          "| Motor | Geometría supuesta | Kv modelo / ficha | R modelo / ficha | Ø exterior | Masa modelo / real |", "|---|---|---|---|---|---|"]
    for x in res["cross_check"]:
        L.append(f"| {x['motor']} | {x['geometry']} | {x['kv'][0]} / {x['kv'][1]} | {x['r_mohm'][0]} / {x['r_mohm'][1]} mΩ | "
                 f"{x['d_out_mm'][0]} / {x['d_out_mm'][1]} mm | {x['mass_g'][0]} / {x['mass_g'][1]} g |")
    L += ["", f"- **Contra la tabla de banco del MN4006:** error de corriente {cal['current_error_rms_pct']} % RMS en las 7 filas "
          f"(ESC supuesto {cal['eta_esc_assumed']:.0%}); corriente en vacío {cal['noload_current_model_a']} A contra "
          f"{cal['noload_current_datasheet_a']} A de la ficha (el modelo es algo pesimista en hierro).",
          f"- **Térmico:** carcasa a fondo {th['t_case_model_c']} °C contra {th['t_case_bench_c']} °C del fabricante "
          f"(bobinado estimado {th['t_winding_model_c']} °C).",
          f"- Constantes calibradas: hierro ×{K_IRON} sobre catálogo + borde láser, cobre ×{K_SIX_STEP_CU} por la conmutación "
          f"de 6 pasos, conductancia térmica ×{K_THERMAL} sobre la superficie externa.",
          "- La masa del modelo es 7-13 % alta para los comerciales (campanas de aluminio fino). Por eso la masa se compara "
          "modelo contra modelo.", ""]
    for veh, v in res["vehicles"].items():
        ref, t = v["reference"], v["targets"]
        L += [f"## {'2' if veh == 'DS-I' else '3'}. {veh}", "",
              f"{v['evaluated_valid']:,} diseños válidos (de un muestreo aleatorio + 3 rondas de refinamiento). "
              f"Metas del G5 en términos del modelo: eficiencia ≥ {t['eta_min']:.1%} (comercial + 2 puntos), masa ≤ "
              f"{t['mass_max_kg'] * 1e3:.0f} g, materiales ≤ US${t['cost_max_usd']:.0f}.", "",
              "| | " + " | ".join(NAMES[k] for k in v["candidates"]) + " |", "|---|" + "---|" * len(v["candidates"])]
        cs = list(v["candidates"].items())

        def row(label, fn, cs=cs):
            return f"| {label} | " + " | ".join(fn(c) for _, c in cs) + " |"
        L += [row("Ranuras / polos", lambda c: f"{c['label']} (factor {c['kw']:.3f})"),
              row("Estator", lambda c: f"Ø{c['design']['d_stator'] * 1e3:.1f} × {c['design']['l_stack'] * 1e3:.1f} mm, {c['design']['steel']}"),
              row("Diente / yugo / ranura", lambda c: f"{c['geometry']['w_tooth'] * 1e3:.2f} / {c['geometry']['h_yoke'] * 1e3:.2f} / "
                  f"{c['geometry']['h_slot'] * 1e3:.1f} mm"),
              row("Bobinado", lambda c: f"{c['design']['turns']} vueltas/diente, {'triángulo' if c['design']['delta'] else 'estrella'}, "
                  f"{wire_plan(c['geometry']['a_cond_ideal'])}"),
              row("Imanes", magnet_spec),
              row("Rotor", lambda c: f"anillo de acero {c['geometry']['h_rotor_yoke'] * 1e3:.1f} mm, Ø exterior {c['geometry']['r_out'] * 2e3:.1f} mm, "
                  f"alto {c['height'] * 1e3:.0f} mm"),
              row("Kv / R (20 °C)", lambda c: f"{c['kv']:.0f} rpm/V / {c['r_line_20_ohm'] * 1e3:.0f} mΩ"),
              row("Eficiencia hover 4,500 m", lambda c: f"{c['ops']['hover_4500m_0C']['efficiency']:.1%}"),
              row("Eficiencia ponderada", lambda c, ref=ref: f"**{c['eta_weighted']:.1%}** ({(c['eta_weighted'] - ref['weighted_efficiency']) * 100:+.1f})"),
              row("Masa", lambda c: f"{c['mass']['total'] * 1e3:.0f} g"),
              row("Autonomía del dron", lambda c: f"**{(c['endurance_rel'] - 1) * 100:+.1f} %**"),
              row("Materiales", lambda c: f"US${c['cost']['total']:.1f}"),
              row("Bobinado en maniobra / máximo", lambda c: f"{c['ops']['maniobra_twr15']['t_winding']:.0f} / {c['ops']['maximo_twr20']['t_winding']:.0f} °C"),
              row("Corriente máx. / densidad", lambda c: f"{c['ops']['maximo_twr20']['current']:.1f} A / {c['ops']['maximo_twr20']['current_density']:.1f} A/mm²"),
              row("Desmagnetización (< 0.7)", lambda c: f"{c['demag']:.2f}"),
              row("Frecuencia eléctrica máx.", lambda c: f"{c['ops']['maximo_twr20']['f_electrical']:.0f} Hz")]
        L += ["", f"**Elegido: {NAMES[CHOICE[veh]]}.**", "", "**Robustez** (puntos de eficiencia que gana sobre el comercial si el "
              "modelo se equivoca; el mismo cambio se aplica al comercial cuando corresponde):", "",
              "| Caso | " + " | ".join(k[0] for k, _ in cs) + " |", "|---|" + "---|" * len(cs)]
        cases = [r["case"] for r in v["robustness"][cs[0][0]]]
        for i, case in enumerate(cases):
            def cell(r, case=case):
                txt = f"{r['gain_points']:+.1f}"
                return txt + (f" (maniobra a {r['t_maniobra']:.0f} °C)" if "enfriamiento" in case else "")
            L.append(f"| {case} | " + " | ".join(cell(v["robustness"][k][i]) for k, _ in cs) + " |")
        L += ["", "**Mejor diseño por combinación** (autonomía del dron):", "",
              "| Ranuras/polos | Autonomía | Eficiencia | Masa | Estator |", "|---|---|---|---|---|"]
        for k, b in list(v["best_by_combo"].items())[:6]:
            L.append(f"| {k} | {(b['endurance_rel'] - 1) * 100:+.1f} % | {b['eta']:.1%} | {b['mass_g']:.0f} g | Ø{b['d_mm']:.0f}×{b['l_mm']:.1f} mm |")
        L += ["", "**Por acero** (el mejor diseño con cada uno): " + "; ".join(
            f"{k}: {(b['endurance_rel'] - 1) * 100:+.1f} % de autonomía, {b['eta']:.1%}" for k, b in v["best_by_steel"].items()) + ".", ""]
        c = v["candidates"][CHOICE[veh]]
        L += ["**Costo de materiales del elegido:** " + ", ".join(f"{k} US${x:.2f}" for k, x in c["cost"].items()
                                                                 if k not in ("total", "n_magnets")) + f" → **US${c['cost']['total']:.2f}**.",
              "", "**Masa del elegido:** " + ", ".join(f"{k} {x * 1e3:.1f} g" for k, x in c["mass"].items() if k != "total") + ".", ""]
        chosen[veh] = {**c, "choice": CHOICE[veh], "reference": ref}
    L += ["## 4. Qué se aprende y qué sigue", "",
          "- **Más ranuras y polos ganan** en los dos drones (24N22P en el DS-I, 36N32P en el DS-D): bobinas cortas, factor de "
          "bobinado alto (0.95) y yugos delgados, con frecuencias eléctricas todavía bajas (< 1.2 kHz) para láminas de 0.2 mm.",
          "- **Estatores anchos y cortos** (tipo \"pancake\"): el diámetro está en el límite del montaje. Si el brazo admite un motor "
          "unos milímetros más ancho, se gana más (a revisar con el CAD del frame en M6).",
          "- **El acero de 0.2 mm (NO20) es el mejor**; el de 0.35 mm, más barato y fácil de conseguir, pierde ~1.5 puntos.",
          "- **El riesgo es el bobinado:** con relleno 0.33 en vez de 0.40, la ganancia cae fuerte. El útil de bobinado (M6) y "
          "el hilo en paralelo de 0.4-0.5 mm son parte del diseño, no un detalle.",
          "- **Los imanes quedaron en el espesor mínimo** del rango (1.0 mm en el DS-I, 1.5 mm en el DS-D): son frágiles y se pegan "
          "con la plantilla. El FEM (M4) verifica la desmagnetización en caliente.",
          "- **Densidad de corriente a fondo de 35-45 A/mm²:** alta para un motor industrial, normal en drones (el comercial "
          "reconstruido llega a ~53 A/mm²) porque el motor está en el chorro de la hélice. Es corta (< 30 s) y la temperatura "
          "queda lejos del límite aun con la mitad del enfriamiento calibrado (tabla de robustez). M5 lo confirma.",
          "- **Siguiente:** M3 (¿un reductor mejora esto?) y M4 (FEM 2D de los elegidos: flujo, cogging, contra-FEM y torque).", "",
          "## Limitaciones", "",
          "- Modelo analítico calibrado con **un** motor (MN4006, tabla del fabricante). El M6C12 solo con ficha. El FEM (M4) y el "
          "banco (M8) son la verificación.",
          "- Térmico de régimen permanente simple; la red térmica es M5.",
          "- Costos de materiales con precios de catálogo; las cotizaciones son S17-05.", ""]
    (INF / "M2_diseno.md").write_text("\n".join(L))
    (INF / "M2_elegidos.json").write_text(json.dumps(chosen, indent=1, ensure_ascii=False, default=float) + "\n")
    print(INF / "M2_diseno.md")


if __name__ == "__main__":
    main()
