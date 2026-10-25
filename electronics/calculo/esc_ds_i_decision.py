"""E3 · ESC 4 en 1 del DS-I: GaN propio vs silicio propio vs comercial → electronics/informes/E3_esc_ds_i.{md,json}

Pérdidas con el modelo de E1 (esc_perdidas.esc_losses) y la pieza de silicio real elegida (CSD18503Q5A, hoja de datos TI
SLPS402); costo de materiales por placa 4 en 1 a 100 unidades (precios estimados de distribuidor, oct. 2026, marcados
como estimados hasta cotizar en E7).

    .venv/bin/python -m electronics.calculo.esc_ds_i_decision
"""

from __future__ import annotations

import json

from electronics.calculo.esc_perdidas import EPC2302, OUT, REQ, Switch, esc_losses

CSD18503 = Switch("CSD18503Q5A (Si 40 V, SON 5×6)", "Si", 4.3e-3, 1.5, 27e-9, 4.5e-9, 4.3e-9, 3.8e-9, 600e-12, 52e-9, 0.8, 1.2,
                  12.0, 3.2, 200e-9, 0.55, "hoja de datos TI SLPS402 (Rds máx. 4.3 mΩ a 10 V, Qg 27 nC, Qgd 4.3 nC, Qrr 52 nC, "
                  "Coss 510 pF); V_plateau de la curva de carga de compuerta; tiempo muerto fijo del DRV8300 (~200 ns)")
COMMERCIAL_USD = 80.0                              # ESC 4 en 1 50 A 6S del prototipo (bom_prototipo_v1.csv)
F_SW = {"Si": 24e3, "GaN": 48e3}                   # óptimos de E1 para cada tecnología

# Materiales de UN canal (un motor) y de la placa, US$ a 100 unidades (estimados)
CHANNEL = {
    "Si": [("CSD18503Q5A ×6", 6 * 0.55), ("DRV8300DPW (driver trifásico, bootstrap integrado)", 0.85),
           ("STM32G071KBU6N", 1.60), ("Shunt 1 mΩ 2512 + INA181A3", 0.25 + 0.35), ("Pasivos (divisores, desacople, filtros)", 0.90)],
    "GaN": [("EPC2302 ×6", 6 * 4.00), ("LMG1210 ×3", 3 * 3.00), ("STM32G071KBU6N", 1.60),
            ("Shunt 1 mΩ 2512 + INA181A3", 0.25 + 0.35), ("Pasivos (divisores, desacople, bootstrap)", 1.20)],
}
BOARD = [("LM5164 + inductor (12 V para los drivers)", 1.40 + 0.45), ("MCP1703 3.3 V", 0.35), ("Condensadores del bus (2 × 470 µF 35 V + MLCC)", 1.30),
         ("TVS SMAJ26A + ESD de señales", 0.30 + 4 * 0.10), ("Conectores (JST-GH 6 pines, pads)", 0.60),
         ("PCB 4 capas 2 oz 50 × 50 mm", 3.00), ("Montaje SMD por servicio (por placa)", 6.00)]


def run() -> dict:
    req = json.loads(REQ.read_text())["esc"]["DS-I"]
    v = req["bus_v_nominal"] * 0.97
    n = req["motores_por_dron"]
    res = {"opciones": {}, "comercial_usd": COMMERCIAL_USD}
    for tech, sw in (("Si", CSD18503), ("GaN", EPC2302)):
        ch = sum(p for _, p in CHANNEL[tech])
        board = sum(p for _, p in BOARD)
        cost = n * ch + board
        loss = {pt: esc_losses(sw, v, req[k], F_SW[tech])["total"] for pt, k in
                (("hover", "i_hover_a"), ("maniobra", "i_continua_a"), ("pico", "i_pico_30s_a"))}
        res["opciones"][tech] = {"switch": sw.name, "f_khz": F_SW[tech] / 1e3, "costo_canal_usd": round(ch, 2),
                                 "costo_placa_usd": round(cost, 2), "perdida_w_por_motor": {k: round(x, 2) for k, x in loss.items()},
                                 "perdida_hover_dron_w": round(n * loss["hover"], 2),
                                 "eficiencia_hover": req["p_motor_hover_w"] / (req["p_motor_hover_w"] + loss["hover"]),
                                 "detalle_canal": CHANNEL[tech]}
    si, gan = res["opciones"]["Si"], res["opciones"]["GaN"]
    p_hover = n * req["p_motor_hover_w"]
    res["gan_vs_si"] = {"ahorro_w": round(si["perdida_hover_dron_w"] - gan["perdida_hover_dron_w"], 2),
                        "ahorro_pct": round((si["perdida_hover_dron_w"] - gan["perdida_hover_dron_w"]) / p_hover * 100, 2),
                        "sobrecosto_usd": round(gan["costo_placa_usd"] - si["costo_placa_usd"], 2)}
    res["decision"] = ("Silicio propio" if si["costo_placa_usd"] < COMMERCIAL_USD and si["costo_placa_usd"] < gan["costo_placa_usd"]
                       else "Comercial")
    res["detalle_placa"] = BOARD
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "E3_esc_ds_i.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    write_report(res, req)
    return res


def write_report(res: dict, req: dict) -> None:
    si, gan = res["opciones"]["Si"], res["opciones"]["GaN"]
    g = res["gan_vs_si"]
    L = ["# E3 · ESC 4 en 1 del DS-I: ¿GaN, silicio propio o comercial?", "",
         "> Generado por `electronics/calculo/esc_ds_i_decision.py`. Precios de materiales estimados a 100 unidades "
         "(se cotizan en E7).", "",
         f"Requisitos (E0): bus 6S {req['bus_v_nominal']} V (máx. {req['bus_v_max']:.1f} V), {req['i_hover_a']} A por motor en "
         f"hover, {req['i_diseno_continua_a']} A continuos y {req['i_diseno_pico_a']} A de pico de diseño, 4 motores.", "",
         "| | Silicio propio | GaN propio | Comercial |", "|---|---|---|---|",
         f"| Transistor | {si['switch']} | {gan['switch']} | 40 V (no publicado) |",
         f"| Conmutación | {si['f_khz']:.0f} kHz | {gan['f_khz']:.0f} kHz | 24-48 kHz |",
         f"| Pérdida por motor: hover / maniobra / pico [W] | {' / '.join(str(x) for x in si['perdida_w_por_motor'].values())} | "
         f"{' / '.join(str(x) for x in gan['perdida_w_por_motor'].values())} | — |",
         f"| Eficiencia del ESC en hover | {si['eficiencia_hover'] * 100:.2f} % | {gan['eficiencia_hover'] * 100:.2f} % | — |",
         f"| Costo de materiales de la placa 4 en 1 | **US${si['costo_placa_usd']:.0f}** | US${gan['costo_placa_usd']:.0f} | "
         f"US${res['comercial_usd']:.0f} |", "",
         f"**GaN contra silicio en el DS-I:** ahorra {g['ahorro_w']} W en hover ({g['ahorro_pct']} % de la potencia) y cuesta "
         f"US${g['sobrecosto_usd']:.0f} más por dron. No se justifica: con 6S y ~5 A por motor el silicio ya está por encima "
         "del 99 %.", "",
         f"**Decisión: {res['decision']}.** El 4 en 1 de silicio propio cuesta ~US${si['costo_placa_usd']:.0f} contra "
         f"US${res['comercial_usd']:.0f} del comercial, usa el mismo firmware (AM32, STM32G071) y la misma estructura que el "
         "ESC del DS-D (medición de corriente por motor, contra-FEM, protecciones), y permite ajustar la conmutación a "
         "nuestros motores de baja inductancia. El GaN queda para el DS-D (E1/E2) y el cargador.", "",
         "## Materiales por canal (silicio)", ""] + [f"- {k}: US${p:.2f}" for k, p in si["detalle_canal"]] + [
         "", "## Materiales comunes de la placa", ""] + [f"- {k}: US${p:.2f}" for k, p in res["detalle_placa"]] + [""]
    (OUT / "E3_esc_ds_i.md").write_text("\n".join(L))


if __name__ == "__main__":
    r = run()
    print(json.dumps({k: v for k, v in r.items() if k != "opciones"}, ensure_ascii=False)[:600])
    for t, o in r["opciones"].items():
        print(t, o["costo_placa_usd"], o["perdida_w_por_motor"], round(o["eficiencia_hover"] * 100, 2))
