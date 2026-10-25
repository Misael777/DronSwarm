"""S20-07 · Packs de batería propios 21700 → electronics/informes/S20-07_baterias.{md,json}

Configuración, corrientes por celda, conexiones (níquel / cobre-níquel), fusible y cable, masa y costo de materiales de
los packs DS-I (6S2P Samsung 50S) y DS-D (12S5P Molicel P42A). Celdas: engineering/battery.py; corrientes: requisitos
de los ESC (electronics/requisitos/requisitos.json, motores propios). BMS: electronics/skidl/bms.py.

    .venv/bin/python -m electronics.calculo.baterias
"""

from __future__ import annotations

import json

from electronics.calculo.esc_perdidas import OUT, REQ
from engineering.battery import CELLS

RHO_NI, RHO_CU = 6.99e-8, 1.72e-8          # Ω·m a 20 °C (níquel puro, cobre)
J_MAX = 10.0                                # A/mm² de diseño para conexiones de celdas (régimen continuo, sin ventilación)
PACKS = {
    "DS-I": {"cell": "50S", "s": 6, "p": 2, "link": [("níquel puro", 0.15, 8.0, 2)], "fuse_a": 60, "awg": 10,
             "connector": "XT90-S (antichispa)", "charge_a": 12.0},
    "DS-D": {"cell": "P42A", "s": 12, "p": 5, "link": [("cobre", 0.20, 10.0, 1), ("níquel puro", 0.15, 10.0, 1)],
             "fuse_a": 200, "awg": 6, "connector": "AS150U (antichispa)", "charge_a": 20.0},
}
AWG_MM2 = {6: 13.3, 8: 8.37, 10: 5.26}
PRICES = {"BMS (placa propia, materiales)": {"DS-I": 22.0, "DS-D": 30.0}, "Shunt de barra 4 terminales": {"DS-I": 4.0, "DS-D": 9.0},
          "Fusible + porta": {"DS-I": 4.0, "DS-D": 12.0}, "Conectores (descarga, carga XT30/XT60, balanceo)": {"DS-I": 6.0, "DS-D": 11.0},
          "Níquel / cobre, papel aislante, cinta Kapton": {"DS-I": 3.0, "DS-D": 12.0},
          "Caja impresa (ASA) + espuma + termocontraíble": {"DS-I": 4.0, "DS-D": 10.0}, "Cable de silicona": {"DS-I": 2.0, "DS-D": 6.0}}


def link_resistance(layers: list, length_mm: float) -> tuple[float, float]:
    """Resistencia de una conexión serie (entre dos grupos en paralelo) y sección total. Cada capa: (material, e, ancho, n)."""
    g = 0.0
    area = 0.0
    for mat, t, w, n in layers:
        a = t * w * n * 1e-6
        rho = RHO_CU if mat == "cobre" else RHO_NI
        g += a / (rho * length_mm * 1e-3)
        area += t * w * n
    return 1 / g, area


def run() -> dict:
    req = json.loads(REQ.read_text())["esc"]
    out = {}
    for veh, pk in PACKS.items():
        c = CELLS[pk["cell"]]
        n_mot = req[veh]["motores_por_dron"]
        i_hover, i_peak = n_mot * req[veh]["i_hover_a"], n_mot * req[veh]["i_pico_30s_a"]
        r_link, area = link_resistance(pk["link"], 22.0)                  # tramo entre celdas vecinas (paso 22 mm)
        i_link_peak = i_peak / pk["p"]
        cells = pk["s"] * pk["p"]
        mass_cells = cells * c.mass_kg
        mass = mass_cells * 1.12 + 0.03
        r_pack = pk["s"] * c.r_internal / pk["p"]
        cost_cells = cells * c.cost_usd
        cost = cost_cells + sum(v[veh] for v in PRICES.values())
        out[veh] = {
            "configuracion": f"{pk['s']}S{pk['p']}P {c.name}", "celdas": cells, "v_nominal": pk["s"] * c.v_nominal,
            "v_max": pk["s"] * 4.2, "capacidad_ah": pk["p"] * c.capacity_ah, "energia_wh": round(pk["s"] * pk["p"] * c.energy_wh, 0),
            "masa_kg": round(mass, 2), "wh_kg": round(pk["s"] * pk["p"] * c.energy_wh / mass, 0),
            "i_hover_a": round(i_hover, 1), "i_pico_a": round(i_peak, 1),
            "i_celda_hover_a": round(i_hover / pk["p"], 1), "i_celda_pico_a": round(i_peak / pk["p"], 1), "i_celda_max_a": c.i_max_cont,
            "margen_pico": round(c.i_max_cont / (i_peak / pk["p"]), 2),
            "caida_pack_pico_v": round(i_peak * r_pack, 2), "perdida_pack_hover_w": round(i_hover ** 2 * r_pack, 1),
            "conexion": " + ".join(f"{mat} {t} × {w} mm ×{n}" for mat, t, w, n in pk["link"]), "conexion_mm2": round(area, 2),
            "densidad_pico_a_mm2": round(i_link_peak / area, 1), "densidad_hover_a_mm2": round(i_hover / pk["p"] / area, 1),
            "r_conexion_mohm": round(r_link * 1e3, 2),
            "fusible_a": pk["fuse_a"], "cable": f"{pk['awg']} AWG silicona ({AWG_MM2[pk['awg']]} mm²)",
            "densidad_cable_hover_a_mm2": round(i_hover / AWG_MM2[pk["awg"]], 1), "conector": pk["connector"],
            "carga_a": pk["charge_a"], "carga_c": round(pk["charge_a"] / (pk["p"] * c.capacity_ah), 2),
            "costo_celdas_usd": round(cost_cells, 2), "costo_total_usd": round(cost, 2),
            "costo_detalle": {k: v[veh] for k, v in PRICES.items()},
        }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "S20-07_baterias.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    write_report(out)
    return out


def write_report(r: dict) -> None:
    rows = [("Configuración", "configuracion"), ("Celdas", "celdas"), ("Tensión nominal / máx. [V]", None), ("Capacidad [Ah]", "capacidad_ah"),
            ("Energía [Wh]", "energia_wh"), ("Masa estimada [kg]", "masa_kg"), ("Energía específica [Wh/kg]", "wh_kg"),
            ("Corriente del dron: hover / pico 30 s [A]", None), ("Por celda: hover / pico / máx. de la celda [A]", None),
            ("Margen de la celda en el pico", "margen_pico"), ("Caída de tensión del pack en el pico [V]", "caida_pack_pico_v"),
            ("Pérdida interna en hover [W]", "perdida_pack_hover_w"), ("Conexión entre grupos", "conexion"),
            ("Densidad en la conexión: hover / pico [A/mm²]", None), ("Fusible principal [A]", "fusible_a"), ("Cable", "cable"),
            ("Conector de vuelo", "conector"), ("Carga [A] (C)", None), ("Costo de materiales [US$]", "costo_total_usd")]
    L = ["# S20-07 · Packs de batería propios 21700 y BMS", "",
         "> Generado por `electronics/calculo/baterias.py`. BMS: `electronics/skidl/bms.py` (netlists `bms_ds_i`, `bms_ds_d`). "
         "Cargador: `S20-07_cargador.md`.", "", "| | DS-I | DS-D |", "|---|---|---|"]
    for label, key in rows:
        if key:
            vals = [str(r[v][key]) for v in ("DS-I", "DS-D")]
        elif label.startswith("Tensión"):
            vals = [f"{r[v]['v_nominal']:.1f} / {r[v]['v_max']:.1f}" for v in r]
        elif label.startswith("Corriente"):
            vals = [f"{r[v]['i_hover_a']} / {r[v]['i_pico_a']}" for v in r]
        elif label.startswith("Por celda"):
            vals = [f"{r[v]['i_celda_hover_a']} / {r[v]['i_celda_pico_a']} / {r[v]['i_celda_max_a']:.0f}" for v in r]
        elif label.startswith("Densidad"):
            vals = [f"{r[v]['densidad_hover_a_mm2']} / {r[v]['densidad_pico_a_mm2']}" for v in r]
        else:
            vals = [f"{r[v]['carga_a']:.0f} ({r[v]['carga_c']} C)" for v in r]
        L.append(f"| {label} | " + " | ".join(vals) + " |")
    L += ["", "## Decisiones", "",
          "- **Salida de vuelo sin transistor de corte.** Un BMS que corta en vuelo derriba el dron. El BMS mide y avisa "
          "a PX4 por DroneCAN (BatteryInfo: tensión de cada celda, corriente, temperatura, estado de carga); PX4 hace RTL "
          "o aterriza. La protección contra cortocircuito es el fusible principal. El puerto de **carga** sí se corta "
          "(MOSFET CHG/DSG del BQ769x0) por sobretensión, sobretemperatura o falla.",
          "- **Balanceo externo de ~100 mA** (P-MOSFET por celda): el interno del BQ76930/40 es de pocos mA y no alcanza "
          "para 10-21 Ah.",
          "- **Conexiones:** en el DS-I alcanza níquel puro doble; en el DS-D la corriente de pico (≈ 33 A por celda) pide "
          "cobre de 0.2 mm bajo el níquel (sándwich soldado por puntos), como se previó en el S09.",
          "- **Shunt de barra fuera de la placa**, con hilos Kelvin: la corriente de vuelo no pasa por el BMS.",
          "- **GaN no:** el BMS no conmuta potencia (ver `S20-07_cargador.md`); el GaN va en el cargador.",
          f"- **Calor del pack del DS-D:** {r['DS-D']['perdida_pack_hover_w']:.0f} W en hover "
          f"({r['DS-D']['perdida_pack_hover_w'] / r['DS-D']['celdas']:.1f} W por celda) por la resistencia interna. Con el "
          "aire de 5,000 msnm (~50 % de densidad) el pack necesita canales de aire entre filas y toma de aire de las "
          "hélices; las NTC del BMS limitan la potencia vía PX4 por encima de 55 °C.",
          f"- **Margen del DS-I en el pico:** {r['DS-I']['margen_pico']} × la corriente máxima de la 50S. Alcanza para 30 s, "
          "pero si el banco muestra calentamiento se pasa a P45B (45 A) con el mismo armado.", "",
          "## Proceso de armado (soldadura por puntos)", "",
          "1. Recepción: celdas de distribuidor autorizado con 2 cotizaciones; medir tensión y resistencia interna (1 kHz) "
          "de cada celda; formar grupos en paralelo con ΔV ≤ 10 mV y ΔR ≤ 5 %.",
          "2. Portaceldas impresos (ASA, resistente a 80 °C) y aisladores de papel de pescado en el polo positivo.",
          "3. Soldadura por puntos (soldadora de condensador, banco S21): 2 puntos dobles por celda y capa; probar "
          "arrancando una tira de prueba en cada sesión.",
          "4. En el DS-D, cobre de 0.2 mm abajo y níquel encima (el níquel suelda al cobre y a la celda).",
          "5. Arnés de balanceo con fusible de hilo (o resistencia 0 Ω de 1206) en cada toma; NTC pegadas al centro del pack.",
          "6. BMS, shunt, fusible y conectores; prueba: tensiones por celda en el BMS, balanceo, corte del puerto de carga, "
          "lectura en PX4 por DroneCAN.",
          "7. Caja con espuma, termocontraíble y etiqueta (Wh, número de serie, fecha). Primer ciclo completo en el banco.", "",
          "## Costo de materiales por pack", "", "| Ítem | DS-I | DS-D |", "|---|---|---|",
          f"| Celdas | US${r['DS-I']['costo_celdas_usd']:.0f} | US${r['DS-D']['costo_celdas_usd']:.0f} |"]
    for k in PRICES:
        L.append(f"| {k} | US${r['DS-I']['costo_detalle'][k]:.0f} | US${r['DS-D']['costo_detalle'][k]:.0f} |")
    L += [f"| **Total** | **US${r['DS-I']['costo_total_usd']:.0f}** | **US${r['DS-D']['costo_total_usd']:.0f}** |", "",
          "Precios estimados (celdas: engineering/battery.py; resto a 10 unidades), se cotizan en E7.", ""]
    (OUT / "S20-07_baterias.md").write_text("\n".join(L))


if __name__ == "__main__":
    for veh, x in run().items():
        print(veh, {k: x[k] for k in ("configuracion", "energia_wh", "masa_kg", "i_celda_pico_a", "margen_pico", "densidad_pico_a_mm2",
                                       "densidad_hover_a_mm2", "densidad_cable_hover_a_mm2", "costo_total_usd")})
