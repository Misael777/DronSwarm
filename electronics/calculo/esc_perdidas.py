"""E1 · ESC: pérdidas con nitruro de galio (GaN) vs silicio y rizado en nuestros motores → electronics/informes/E1_*

Modelo de un ESC trifásico con conmutación de 6 pasos y rectificación síncrona (como AM32): en cada instante conducen
2 fases; una rama conmuta con PWM a la frecuencia f.
  conducción   P = 2 · I² · Rds(T)                         (siempre 2 transistores en serie en el camino)
  conmutación  P = V · I · t_sw · f                         (encendido + apagado de la rama que conmuta)
  salida       P = E_oss · f                                (carga de C_oss en cada encendido "duro")
  recuperación P = Q_rr · V · f                             (solo silicio: el diodo del cuerpo; GaN Q_rr = 0)
  tiempo muerto P = 2 · t_muerto · f · I · V_SD              (conducción inversa en los tiempos muertos)
  compuerta    P = 2 · Q_g · V_drv · f                      (la rama que conmuta)
  t_sw = Q_sw / I_g,  Q_sw = Q_gd + (Q_gs − Q_g(th)),  I_g = (V_drv − V_plateau) / (R_g,int + R_g,ext + R_driver)
Rizado de corriente en el motor (PWM sobre el lazo de 2 fases): ΔI = V·D·(1−D)/(L_lazo·f) → pérdida extra en el cobre.

Datos: EPC2302 de su hoja de datos (EPC, 2026); MOSFET de silicio: valores típicos de la clase usada en ESC comerciales
de 12S/120 A (100 V, ~3.5 mΩ) y 6S (40 V, ~1.2 mΩ), aproximados — se reemplazan por la pieza del ESC comercial medido.

    .venv/bin/python -m electronics.calculo.esc_perdidas
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQ = ROOT / "electronics" / "requisitos" / "requisitos.json"
OUT = ROOT / "electronics" / "informes"
F_SW = (24e3, 48e3, 96e3)


@dataclass(frozen=True)
class Switch:
    name: str
    tech: str
    rds_25: float          # Ω (máx. de la hoja)
    k_t: float             # Rds(T_trabajo)/Rds(25 °C) a ~80 °C de unión
    qg: float              # C (total, a V_drv)
    qgs: float
    qgd: float
    qgth: float
    coss_er: float         # F (equivalente en energía)
    qrr: float             # C
    vsd: float             # V (conducción inversa en tiempo muerto)
    rg_int: float          # Ω
    v_drv: float           # V
    v_plateau: float       # V
    t_dead: float          # s
    price_usd: float       # unidad, compra de 100
    source: str


EPC2302 = Switch("EPC2302 (GaN 100 V, QFN 3×5)", "GaN", 1.8e-3, 1.35, 23e-9, 8.9e-9, 2.3e-9, 6.3e-9, 1300e-12, 0.0, 2.0, 0.5,
                 5.0, 2.5, 15e-9, 4.0, "hoja de datos EPC2302 (Rds máx. 1.8 mΩ, Qg 23 nC, Qgd 2.3 nC, Qoss 85 nC, Qrr 0); "
                 "V_SD en tiempo muerto ≈ 2 V a corriente de trabajo; precio estimado a 100 u.")
SI_100V = Switch("MOSFET de silicio 100 V (clase de ESC 12S 120 A)", "Si", 3.5e-3, 1.6, 52e-9, 17e-9, 10e-9, 7e-9, 1000e-12, 60e-9, 0.85,
                 1.2, 10.0, 4.5, 250e-9, 1.2, "valores típicos de la clase (100 V, ~3.5 mΩ, TO/PQFN 5×6); aproximados")
SI_40V = Switch("MOSFET de silicio 40 V (clase de ESC 6S 4 en 1)", "Si", 1.2e-3, 1.6, 45e-9, 12e-9, 8e-9, 6e-9, 1800e-12, 35e-9, 0.8, 1.0,
                10.0, 4.0, 200e-9, 0.5, "valores típicos de la clase (40 V, ~1.2 mΩ, PQFN 3×3/5×6); aproximados")
R_DRIVER = {"GaN": 0.5 + 1.0, "Si": 1.0 + 2.0}       # resistencia del driver + compuerta externa [Ω]


def esc_losses(sw: Switch, v: float, i: float, f: float) -> dict:
    rds = sw.rds_25 * sw.k_t
    p_cond = 2 * i * i * rds
    ig = (sw.v_drv - sw.v_plateau) / (sw.rg_int + R_DRIVER[sw.tech])
    t_sw = (sw.qgd + (sw.qgs - sw.qgth)) / ig
    p_sw = v * i * t_sw * f
    p_oss = 0.5 * sw.coss_er * v * v * f
    p_rr = sw.qrr * v * f
    p_dead = 2 * sw.t_dead * f * i * sw.vsd
    p_gate = 2 * sw.qg * sw.v_drv * f
    tot = p_cond + p_sw + p_oss + p_rr + p_dead + p_gate
    return {"cond": p_cond, "sw": p_sw, "oss": p_oss, "rr": p_rr, "dead": p_dead, "gate": p_gate, "total": tot, "t_sw_ns": t_sw * 1e9}


def ripple_loss(v: float, duty: float, l_loop: float, f: float, r_loop: float) -> dict:
    di = v * duty * (1 - duty) / (l_loop * f)
    i_rms = di / (2 * 3 ** 0.5)
    return {"di_pp_a": di, "p_cu_w": i_rms * i_rms * r_loop}


def run() -> dict:
    req = json.loads(REQ.read_text())
    chosen = json.loads((ROOT / "motor" / "informes" / "M2_elegidos.json").read_text())
    res = {}
    for veh in ("DS-I", "DS-D"):
        e = req["esc"][veh]
        lind = req["motor_inductancia"][veh]["L_loop_h"] * 1.15          # +15 % por cabezas de bobina
        r_loop = chosen[veh]["r_line_20_ohm"] * 1.15                     # caliente (~60 °C)
        si = SI_40V if veh == "DS-I" else SI_100V
        v = e["bus_v_nominal"] * 0.97
        pts = {"hover": (e["i_hover_a"], e["p_motor_hover_w"], chosen[veh]["ops"]["hover_4500m_0C"]["voltage"]),
               "maniobra": (e["i_continua_a"], chosen[veh]["ops"]["maniobra_twr15"]["p_in"], chosen[veh]["ops"]["maniobra_twr15"]["voltage"]),
               "maximo": (e["i_pico_30s_a"], e["p_motor_max_w"], chosen[veh]["ops"]["maximo_twr20"]["voltage"])}
        rows = []
        for sw in (si, EPC2302):
            for f in F_SW:
                for name, (i, p_motor, v_motor) in pts.items():
                    lo = esc_losses(sw, v, i, f)
                    rp = ripple_loss(v, min(v_motor / v, 0.95), lind, f, r_loop)
                    rows.append({"switch": sw.name, "tech": sw.tech, "f_khz": f / 1e3, "point": name, "i_a": i, "p_motor_w": p_motor,
                                 **{k: round(x, 3) for k, x in lo.items()}, "eff_esc": p_motor / (p_motor + lo["total"]),
                                 "ripple_di_a": round(rp["di_pp_a"], 2), "ripple_cu_w": round(rp["p_cu_w"], 3),
                                 "loss_esc_plus_ripple_w": round(lo["total"] + rp["p_cu_w"], 3)})
        hover = [r for r in rows if r["point"] == "hover"]
        best = {t: min((r for r in hover if r["tech"] == t), key=lambda r: r["loss_esc_plus_ripple_w"]) for t in ("Si", "GaN")}
        n = e["motores_por_dron"]
        p_total = n * e["p_motor_hover_w"]
        gain_w = n * (best["Si"]["loss_esc_plus_ripple_w"] - best["GaN"]["loss_esc_plus_ripple_w"])
        res[veh] = {"rows": rows, "best": best, "n": n, "gain_w_drone": gain_w,
                    "gain_pct_hover_power": gain_w / (p_total + n * best["Si"]["loss_esc_plus_ripple_w"]) * 100,
                    "L_loop_uH": lind * 1e6, "si": si.name, "si_source": si.source, "gan_source": EPC2302.source}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "E1_esc_gan_vs_si.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float) + "\n")
    write_report(res)
    return res


def write_report(res: dict) -> None:
    L = ["# E1 · ESC: nitruro de galio vs silicio en nuestros motores", "",
         "> Generado por `electronics/calculo/esc_perdidas.py`. No editar a mano.", "",
         "Pérdidas de UN ESC (6 pasos con rectificación síncrona, como AM32) a la corriente de cada punto, más la pérdida "
         "extra en el cobre del motor por el rizado de corriente del PWM (inductancia del motor por FEM). Tensión del bus "
         "nominal.", ""]
    for veh, r in res.items():
        L += [f"## {veh} (×{r['n']} motores · inductancia del lazo {r['L_loop_uH']:.0f} µH)", "",
              "| Transistor | f PWM | Punto | Corriente | Conducción | Conmutación | C_oss | Q_rr | Tiempo muerto | Compuerta | **Pérdida ESC** | Eficiencia ESC | Rizado ΔI | Cobre por rizado |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for x in r["rows"]:
            L.append(f"| {x['tech']} | {x['f_khz']:.0f} kHz | {x['point']} | {x['i_a']:.1f} A | {x['cond']:.2f} | {x['sw']:.2f} | {x['oss']:.2f} | "
                     f"{x['rr']:.2f} | {x['dead']:.2f} | {x['gate']:.3f} | **{x['total']:.2f} W** | {x['eff_esc']:.1%} | {x['ripple_di_a']:.1f} A | "
                     f"{x['ripple_cu_w']:.2f} W |")
        b = r["best"]
        L += ["", f"**Mejor frecuencia en hover:** silicio a {b['Si']['f_khz']:.0f} kHz ({b['Si']['eff_esc']:.1%}), GaN a {b['GaN']['f_khz']:.0f} kHz "
              f"({b['GaN']['eff_esc']:.1%}). **Ahorro en el dron: {r['gain_w_drone']:.1f} W en hover = {r['gain_pct_hover_power']:.1f} % de la potencia "
              f"→ ≈ +{r['gain_pct_hover_power']:.1f} % de autonomía.**", ""]
    L += ["## Costo de los transistores", "", "| Dron | Silicio (6 por ESC) | GaN (6 por ESC) | Diferencia por dron |", "|---|---|---|---|"]
    for veh, r in res.items():
        si = SI_40V if veh == "DS-I" else SI_100V
        n_sw = 6 * r["n"]
        L.append(f"| {veh} | {n_sw} × US${si.price_usd:.2f} = US${n_sw * si.price_usd:.0f} | {n_sw} × US${EPC2302.price_usd:.2f} = "
                 f"US${n_sw * EPC2302.price_usd:.0f} | +US${n_sw * (EPC2302.price_usd - si.price_usd):.0f} |")
    L += ["", "## Conclusión", "",
          "- **Con nuestros motores (poca corriente), un ESC de silicio bien diseñado ya es ~99 % eficiente en los transistores.** "
          "El GaN gana poco en energía: ≈ +0.5 % de autonomía en el DS-D y ≈ +0.1 % en el DS-I (la estimación genérica de "
          "\"95 % → 98 %\" incluía pérdidas que no dependen del transistor: medición de corriente, cobre de la placa, "
          "conectores y la fuente del microcontrolador).",
          "- **El ahorro de dinero viene de fabricar el ESC propio, no del GaN**: el GaN cuesta más por transistor.",
          "- **Lo que el GaN sí da**: menos calor (placa más chica, sin disipador, mejor a 5,000 msnm con aire poco denso), "
          "48-96 kHz para bajar el rizado en nuestros motores de baja inductancia (calienta menos imanes y hierro: se mide en "
          "el banco) y margen para un motor más exigente en el futuro.",
          "- **Recomendación:** DS-D con GaN (el sobrecosto es chico frente al ESC comercial de US$120 y el calor importa a 12S); "
          "DS-I: decidir en E3 entre silicio propio y el comercial (el GaN no se paga en 6S con 5 A por motor).", ""]
    L += ["## Lectura", "",
          "- **El silicio pierde sobre todo en la conmutación, la recuperación del diodo (Q_rr) y el tiempo muerto**; crecen con la "
          "frecuencia. Por eso los ESC de silicio se quedan en 24-48 kHz.",
          "- **El GaN conmuta en pocos nanosegundos, no tiene Q_rr y usa tiempos muertos de ~15 ns**: puede ir a 48-96 kHz con poca "
          "pérdida, y además tiene la mitad de resistencia.",
          "- **El rizado en nuestros motores** (baja inductancia) cae a la mitad cada vez que se duplica la frecuencia; la pérdida en el "
          "cobre que causa es chica, pero el rizado también calienta los imanes y el hierro (no modelado: se mide en el banco).",
          "- Los datos del silicio son de la clase de transistor de los ESC comerciales; se reemplazan por la pieza real del APD 120F3 "
          "cuando se mida en el banco.", "",
          "## Fuentes", "", f"- GaN: {EPC2302_SOURCE}", f"- Silicio: {res['DS-D']['si_source']} / {res['DS-I']['si_source']}", ""]
    (OUT / "E1_esc_gan_vs_si.md").write_text("\n".join(L))


EPC2302_SOURCE = EPC2302.source

if __name__ == "__main__":
    r = run()
    for veh, x in r.items():
        print(veh, {t: (b["f_khz"], round(b["total"], 2), round(b["eff_esc"], 4), b["ripple_cu_w"]) for t, b in x["best"].items()},
              "ahorro W", round(x["gain_w_drone"], 1), "%", round(x["gain_pct_hover_power"], 2))
