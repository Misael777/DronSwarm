"""S20-07 · Cargador de campo GaN (48 V DC → packs 6S y 12S, 1 kW) → electronics/informes/S20-07_cargador.{md,json}

Etapa reductora-elevadora de 4 interruptores (dos medios puentes y un inductor). Con VIN > VOUT trabaja como reductor
(rama A conmuta, alto de la rama B siempre encendido); con VIN < VOUT como elevador (alto de A encendido, rama B conmuta).
Pérdidas de conmutación con el modelo de E1 (esc_perdidas: tiempos de conmutación por carga de compuerta, E_oss, Q_rr,
tiempo muerto, compuerta) y conducción con la corriente eficaz del inductor (I² + ΔI²/12).

Puntos de operación: carga del DS-I (6S2P Samsung 50S, 12 A = 1.2 C de las celdas) y del DS-D (12S5P Molicel P42A,
20 A ≈ 1 C), con 48 V de entrada (fuente AC-DC o sistema de 48 V del vehículo/campamento).

    .venv/bin/python -m electronics.calculo.cargador
"""

from __future__ import annotations

import json

from electronics.calculo.esc_perdidas import EPC2302, OUT, R_DRIVER, SI_100V, Switch

V_IN = 48.0
POINTS = {"DS-I 6S a 3.9 V/celda": (23.4, 12.0), "DS-I 6S fin (CV 4.2 V)": (25.2, 12.0),
          "DS-D 12S a 3.9 V/celda": (46.8, 20.0), "DS-D 12S fin (CV 4.2 V)": (50.4, 20.0)}
# Inductor y frecuencia por tecnología (Coilcraft XAL1510: DCR y pérdida de núcleo estimadas de la ficha, a confirmar)
STAGE = {"GaN": {"f": 250e3, "L": 6.8e-6, "dcr": 4.5e-3, "core_w": 0.9, "sw": EPC2302, "inductor": "XAL1510-682"},
         "Si": {"f": 100e3, "L": 15e-6, "dcr": 8.0e-3, "core_w": 0.6, "sw": SI_100V, "inductor": "XAL1510-153"}}
R_SHUNTS = 2 * 1.0e-3            # shunts de entrada y salida
P_FIXED_W = 3.0                  # control, drivers, ventilador
COMMERCIAL = {"precio_usd": 380.0, "eficiencia": 0.88, "nota": "cargador de hobby 1 kW 12S + 6S del BOM (T049); eficiencia típica de catálogo"}


def leg_switching(sw: Switch, v: float, i: float, f: float) -> float:
    ig = (sw.v_drv - sw.v_plateau) / (sw.rg_int + R_DRIVER[sw.tech])
    t_sw = (sw.qgd + (sw.qgs - sw.qgth)) / ig
    return (v * i * t_sw * f + 0.5 * sw.coss_er * v * v * f + sw.qrr * v * f + 2 * sw.t_dead * f * i * sw.vsd
            + 2 * sw.qg * sw.v_drv * f)


def stage_losses(tech: str, v_in: float, v_out: float, i_out: float) -> dict:
    s = STAGE[tech]
    sw, f, L = s["sw"], s["f"], s["L"]
    rds = sw.rds_25 * sw.k_t
    if v_in >= v_out:                                                  # reductor
        d = v_out / v_in
        il = i_out
        di = v_out * (1 - d) / (L * f)
        i_rms2 = il * il + di * di / 12
        p_cond = i_rms2 * rds * (1 + 1)                                # un transistor de A (alto o bajo) + alto de B
        p_sw = leg_switching(sw, v_in, il, f)
        mode = f"reductor D = {d:.2f}"
    else:                                                              # elevador
        d = 1 - v_in / v_out
        il = i_out / (1 - d)
        di = v_in * d / (L * f)
        i_rms2 = il * il + di * di / 12
        p_cond = i_rms2 * rds * 2
        p_sw = leg_switching(sw, v_out, il, f)
        mode = f"elevador D = {d:.2f}"
    p_l = i_rms2 * s["dcr"] + s["core_w"]
    p_sh = i_out * i_out * 1.0e-3 + (v_out * i_out / v_in) ** 2 * 1.0e-3
    p_out = v_out * i_out
    tot = p_cond + p_sw + p_l + p_sh + P_FIXED_W
    return {"modo": mode, "i_inductor_a": round(il, 2), "rizado_a": round(di, 2), "p_out_w": round(p_out, 1),
            "p_conduccion_w": round(p_cond, 2), "p_conmutacion_w": round(p_sw, 2), "p_inductor_w": round(p_l, 2),
            "p_shunts_w": round(p_sh, 2), "p_fija_w": P_FIXED_W, "p_total_w": round(tot, 2), "eficiencia": p_out / (p_out + tot)}


def run() -> dict:
    res = {"v_in": V_IN, "etapas": {t: {k: (v if not isinstance(v, Switch) else v.name) for k, v in s.items()} for t, s in STAGE.items()},
           "puntos": {}, "comercial": COMMERCIAL}
    for name, (vo, io) in POINTS.items():
        res["puntos"][name] = {t: stage_losses(t, V_IN, vo, io) for t in STAGE}
    psu_eff = 0.93                                                     # fuente AC-DC 48 V 1 kW (clase Mean Well RSP-1000-48)
    dsd = res["puntos"]["DS-D 12S a 3.9 V/celda"]
    res["cadena_ac"] = {"fuente_ac_dc": psu_eff, "gan": round(psu_eff * dsd["GaN"]["eficiencia"], 4),
                        "si": round(psu_eff * dsd["Si"]["eficiencia"], 4), "comercial": COMMERCIAL["eficiencia"]}
    res["costo"] = {"placa_dc_dc_usd": 48.0, "fuente_ac_dc_48v_1kw_usd": 190.0, "caja_ventilador_conectores_usd": 25.0,
                    "nota": "materiales estimados a 10 unidades; la placa se detalla en E7"}
    res["costo"]["total_usd"] = round(sum(v for k, v in res["costo"].items() if k.endswith("_usd")), 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "S20-07_cargador.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    write_report(res)
    return res


def write_report(res: dict) -> None:
    g, s = STAGE["GaN"], STAGE["Si"]
    L = ["# S20-07 · Cargador de campo con nitruro de galio (GaN)", "",
         "> Generado por `electronics/calculo/cargador.py`. Esquema: `electronics/skidl/charger.py`.", "",
         f"Entrada {res['v_in']:.0f} V DC (fuente AC-DC de 1 kW o sistema de 48 V del vehículo/campamento); salida 0-55 V, "
         "hasta 20 A, perfil CC/CV leído del BMS del pack por DroneCAN. Etapa reductora-elevadora de 4 interruptores con los "
         "mismos medios puentes GaN del ESC del DS-D (EPC2302 + LMG1210) y control digital STM32G474 (HRTIM).", "",
         f"| Punto | Modo | P salida | Pérdidas GaN ({g['f'] / 1e3:.0f} kHz, {g['L'] * 1e6:.1f} µH) | Ef. GaN | "
         f"Pérdidas Si ({s['f'] / 1e3:.0f} kHz, {s['L'] * 1e6:.0f} µH) | Ef. Si |", "|---|---|---|---|---|---|---|"]
    for name, r in res["puntos"].items():
        L.append(f"| {name} | {r['GaN']['modo']} | {r['GaN']['p_out_w']:.0f} W | {r['GaN']['p_total_w']:.1f} W | "
                 f"{r['GaN']['eficiencia'] * 100:.1f} % | {r['Si']['p_total_w']:.1f} W | {r['Si']['eficiencia'] * 100:.1f} % |")
    c = res["cadena_ac"]
    k = res["costo"]
    L += ["", "## Qué aporta el GaN aquí", "",
          f"- **Calor y tamaño:** a 1 kW la etapa GaN pierde ~{res['puntos']['DS-D 12S a 3.9 V/celda']['GaN']['p_total_w']:.0f} W "
          f"contra ~{res['puntos']['DS-D 12S a 3.9 V/celda']['Si']['p_total_w']:.0f} W de silicio, con un inductor de "
          f"{g['L'] * 1e6:.1f} µH en vez de {s['L'] * 1e6:.0f} µH (2.5 × la frecuencia): disipador y caja más chicos, se puede "
          "sellar contra el polvo de mina con un ventilador pequeño.",
          f"- **Cadena desde la red (AC → pack):** fuente AC-DC ({c['fuente_ac_dc'] * 100:.0f} %) × etapa GaN = "
          f"**{c['gan'] * 100:.1f} %**, contra {c['si'] * 100:.1f} % con silicio y ~{c['comercial'] * 100:.0f} % del "
          "cargador comercial.",
          "- **Campo:** con 48 V de un vehículo o banco solar carga sin inversor (un inversor + cargador pierde 8-12 % más).",
          "", "## Costo estimado", "",
          f"- Placa DC-DC GaN: US${k['placa_dc_dc_usd']:.0f} · fuente AC-DC 48 V 1 kW: US${k['fuente_ac_dc_48v_1kw_usd']:.0f} · "
          f"caja, ventilador y conectores: US${k['caja_ventilador_conectores_usd']:.0f}",
          f"- **Total ≈ US${k['total_usd']:.0f}** contra US${res['comercial']['precio_usd']:.0f} del cargador comercial "
          "(que además no lee el BMS). La fuente AC-DC se compra hecha: diseñar la etapa de red (PFC, aislamiento, "
          "certificación eléctrica) no se justifica para este volumen.", "",
          "## Dentro del pack no se usa GaN", "",
          "El BMS no conmuta potencia: sus transistores (puerto de carga) están siempre encendidos o apagados, y solo "
          "conducen. Ahí cuenta la resistencia de conducción y el precio, no la velocidad de conmutación; un MOSFET de "
          "silicio de 100 V y 3.5 mΩ cuesta menos que un GaN equivalente y pierde lo mismo. El GaN va donde se conmuta: "
          "ESC del DS-D y cargador.", ""]
    (OUT / "S20-07_cargador.md").write_text("\n".join(L))


if __name__ == "__main__":
    r = run()
    for name, p in r["puntos"].items():
        print(name, {t: (x["modo"], x["p_total_w"], round(x["eficiencia"] * 100, 2)) for t, x in p.items()})
    print(r["cadena_ac"], r["costo"]["total_usd"])
