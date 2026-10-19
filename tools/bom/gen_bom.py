#!/usr/bin/env python3
"""S09-06 · BOM del prototipo v1 (flota de 4 DS-I + 2 DS-D) → manufacturing/bom/bom_prototipo_v1.csv + resumen.

Toma motores, ESC y aviónica de la selección COTS (engineering/data/results/cots_selection.json) y agrega frame
(estimados de manufacturing/procesos/piezas_frame.md), baterías, cableado, repuestos y equipo de tierra.

Compra en dos fases:
  A · validación: 2 motores de cada tipo + 1 ESC + hélices para medir en el banco (S10) los datos estimados
      ANTES de comprar la flota. Las baterías se piden también en esta fase: son lo de mayor plazo (envío de
      mercancía peligrosa).
  B · flota: el resto, cuando el banco confirme los motores.

    .venv/bin/python tools/bom/gen_bom.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from engineering.mass_budget import prop_cost  # noqa: E402

OUT = ROOT / "manufacturing" / "bom" / "bom_prototipo_v1.csv"
SUMMARY = ROOT / "manufacturing" / "bom" / "bom_prototipo_v1.md"
FLEET = {"DS-I": 4, "DS-D": 2}
COLS = ["id", "dron", "categoria", "descripcion", "cant_por_dron", "cant_flota", "cant_repuesto", "cant_total",
        "precio_unit_usd", "total_usd", "fase", "plazo_semanas", "proveedor_1", "proveedor_2", "fuente_precio", "estimado"]


def main():
    sel = json.loads((ROOT / "engineering/data/results/cots_selection.json").read_text())
    motors = {m["name"]: m for m in sel["motors"]}
    escs = {e["vehicle"]: e for e in sel["escs"]}
    rows = []

    def add(dron, cat, desc, per, price, phase, weeks, p1, p2, src, est, spare=0, fleet=None):
        n_fleet = (FLEET[dron] if dron in FLEET else 1) * per if fleet is None else fleet
        total = n_fleet + spare
        rows.append({"id": f"{'I' if dron == 'DS-I' else 'D' if dron == 'DS-D' else 'T'}{len(rows) + 1:03d}", "dron": dron,
                     "categoria": cat, "descripcion": desc, "cant_por_dron": per, "cant_flota": n_fleet, "cant_repuesto": spare,
                     "cant_total": total, "precio_unit_usd": round(price, 2), "total_usd": round(round(price, 2) * total, 2), "fase": phase,
                     "plazo_semanas": weeks, "proveedor_1": p1, "proveedor_2": p2, "fuente_precio": src, "estimado": "sí" if est else "no"})

    for veh in ("DS-I", "DS-D"):
        s = sel["selected"][veh]
        m = motors[s["motor"]]
        n = 6 if veh == "DS-D" else 4
        e = escs[veh]
        # propulsión: la fase A compra 2 motores para el banco; el resto en la fase B
        add(veh, "propulsión", f"Motor {m['name']} (fase A: 2 para el banco)", n, m["cost_usd"], "A+B", 4,
            "distribuidor oficial T-Motor / MAD", "tienda UAV (EE. UU./UE)", m["source"], "cost_usd" in m["estimated"], spare=1)
        if veh == "DS-I":
            add(veh, "propulsión", f"{e['name']} (1 placa por dron)", 1, 80, "A+B", 3, "Holybro / iFlight", "tienda FPV",
                e["source"], True, spare=1)
        else:
            add(veh, "propulsión", e["name"], n, e["cost_usd"], "A+B", 6, "Advanced Power Drives (distribuidor)", "GetFPV / RaceDayQuads",
                e["source"], True, spare=1)
        pin = s["prop_in"]
        add(veh, "propulsión", f"Hélice plegable {pin:g}\" (pares CW/CCW)", n, prop_cost(pin), "A+B", 3, "T-Motor / MAD",
            "Hobbywing / genérica de carbono", "modelo de costo del S04 (verificar)", True, spare=n * 2)
        # aviónica
        for it in sel["avionics"][veh]:
            add(veh, "aviónica", f"{it['role']}: {it['name']}", 1, it["cost_usd"], "B", 3,
                "distribuidor oficial", "tienda UAV", it["source"], it["estimated"])
        # batería: 2 por dron (rotación en campo)
        if veh == "DS-I":
            add(veh, "batería", "Pack Li-ion 6S2P Samsung 50S (21700, 10 Ah, XT90-S), armado local", 2, 95, "A", 6,
                "armador de packs en Lima (celdas de distribuidor autorizado)", "pack comercial 6S2P 21700", "estimado: 12 celdas × US$5.5 + armado", True)
        else:
            add(veh, "batería", "Pack Li-ion 12S5P Molicel P42A (21700, 21 Ah, AS150U), armado local", 2, 390, "A", 6,
                "armador de packs en Lima (celdas de distribuidor autorizado)", "LiPo 12S 22 Ah comercial", "estimado: 60 celdas × US$5 + armado", True)
        # frame y kits
        frame = ({"Impresión PA12-CF (15 piezas)": 58, "Impresión TPU (4 pies)": 5, "Corte CNC de 2 placas de carbono 3 mm": 32,
                  "Tubos de carbono (Ø20 y Ø12)": 32, "Tornillería M3 + tuercas autoblocantes": 6,
                  "Kit IP54 (junta EPDM, prensaestopa M12, ventila ePTFE)": 15, "Amortiguadores de cámara (4)": 8,
                  "Kit de cableado (12 AWG, XT90-S, JST-GH, malla, ferritas)": 25, "BEC 5 V / 5 A": 12}
                 if veh == "DS-I" else
                 {"Impresión PA12-CF (24 piezas)": 115, "Impresión TPU (4 zapatas)": 6, "Corte CNC de 2 placas de carbono 3 mm": 90,
                  "Gancho de aluminio 6061 (corte por agua)": 20, "Tubos de carbono (Ø22×1.5 y Ø16)": 125,
                  "6 levas de apriete rápido + tornillería M4": 35, "Kit IP54 (junta EPDM, prensaestopa M16, ventila ePTFE)": 18,
                  "Kit de cableado (6 AWG, AS150U, 6 XT60, barra de cobre, JST-GH)": 70, "Reguladores 5 V / 12 V / 7.4 V": 25})
        for desc, price in frame.items():
            add(veh, "frame y kits", desc, 1, price, "B", 2, "taller local (Lima)", "segundo taller local",
                "manufacturing/procesos/piezas_frame.md (estimado)", True, spare=1 if "Impresión" in desc else 0)

    # equipo de tierra y banco
    for desc, price, phase, weeks, src in [
        ("Radiocontrol RadioMaster TX16S + módulo ExpressLRS 900 MHz", 250, "B", 3, "estimado"),
        ("RFD900x de tierra + antena 6 dBi + mástil 6 m", 200, "B", 3, "estimado"),
        ("Cargador 1 kW 12S (para DS-D) ×1 y cargador 6S ×1", 380, "A", 3, "plan: 2 × US$120 (subestimado para 12S)"),
        ("Bolsas y caja de transporte ignífugas para baterías", 90, "A", 2, "estimado"),
        ("Banco de empuje: celda de carga 20 kg + 2 celdas 5 kg (torque), HX711, sensor óptico de rpm, sensor de corriente/voltaje, ESP32", 180, "A", 2,
         "hardware/test_bench/ (S10)"),
        ("Fuente de laboratorio o batería de banco 12S + multímetro de pinza DC", 150, "A", 2, "estimado"),
    ]:
        add("tierra", "equipo de tierra y banco", desc, 1, price, phase, weeks, "tienda local / importación", "—", src, True, fleet=1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    write_summary(rows, sel)
    track = OUT.parent / "seguimiento_compras.csv"
    if not track.exists():                       # planilla del usuario: se crea una vez y nunca se sobrescribe
        with open(track, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "descripcion", "cant_total", "fase", "proveedor_elegido", "precio_real_usd", "fecha_pedido",
                        "fecha_estimada", "fecha_llegada", "inspeccion_ok", "observaciones"])
            for r in rows:
                w.writerow([r["id"], r["descripcion"], r["cant_total"], r["fase"], "", "", "", "", "", "", ""])
    print(OUT)


def write_summary(rows, sel):
    def tot(filt):
        return sum(r["total_usd"] for r in rows if filt(r))

    per_drone = {v: sum(r["precio_unit_usd"] * r["cant_por_dron"] for r in rows if r["dron"] == v) for v in ("DS-I", "DS-D")}
    budget = {"DS-I": json.loads((ROOT / "engineering/data/results/ds-i_sizing.json").read_text())["bom_cost_usd"],
              "DS-D": json.loads((ROOT / "engineering/data/results/ds-d_sizing.json").read_text())["bom_cost_usd"]}
    phase_a = tot(lambda r: r["fase"] == "A") + sum(r["precio_unit_usd"] * (2 if "Motor" in r["descripcion"] else 1)
                                                  for r in rows if r["fase"] == "A+B" and r["categoria"] == "propulsión"
                                                  and ("Motor" in r["descripcion"] or "ESC" in r["descripcion"] or "APD" in r["descripcion"]))
    cats = {}
    for r in rows:
        cats[r["categoria"]] = cats.get(r["categoria"], 0) + r["total_usd"]
    L = ["# BOM del prototipo v1 · resumen", "",
         "> Generado por `tools/bom/gen_bom.py` desde la selección COTS. Detalle línea por línea en `bom_prototipo_v1.csv` "
         "(cantidades, precios, fase de compra, plazos, 2 proveedores por ítem). Los precios marcados como estimados se "
         "reemplazan con las cotizaciones del S10.", "",
         "## Costo por dron (sin repuestos ni equipo de tierra)", "",
         "| | Prototipo v1 (componentes de marca, compra unitaria) | Presupuesto del S04 | Diferencia |", "|---|---|---|---|",
         *[f"| {v} | US${per_drone[v]:,.0f} | US${budget[v]:,.0f} | {per_drone[v] / budget[v] - 1:+.0%} |" for v in ("DS-I", "DS-D")],
         "", "## Flota de prototipos (4 DS-I + 2 DS-D), repuestos y equipo", "",
         "| Categoría | Total |", "|---|---|", *[f"| {k} | US${v:,.0f} |" for k, v in cats.items()],
         f"| **Total** | **US${sum(cats.values()):,.0f}** |", "",
         f"**Fase A (validación, pedir ya):** ≈ US${phase_a:,.0f}. Incluye baterías, cargadores, banco de empuje, 2 motores de cada tipo, "
         "1 ESC de cada tipo y hélices. **Fase B (flota):** el resto, cuando el banco confirme los motores (S10).", "",
         "## Por qué el prototipo cuesta más que el objetivo", "",
         "- **Motores de marca a precio unitario:** US$75-170 cada uno, contra US$18-56 del modelo paramétrico del S04, que "
         "suponía precio de fábrica en volumen. Este es el hueco que cierra el motor propio (S17-S19).",
         "- **Aviónica de desarrollo:** Pixhawk 6C, GNSS RTK multibanda, computadora a bordo y una radio por dron. En "
         "producción, el DS-I base no lleva RTK ni computadora (escenario D) y la controladora puede ser propia (S20-S21).",
         "- **Frame en servicios por pieza:** imprimir en casa y cortar placas por lote baja ~40 % el costo del frame.",
         "- El costo de producción se recalcula en el S24 con volumen de 100 unidades, motor y electrónica propios.", ""]
    SUMMARY.write_text("\n".join(L))


if __name__ == "__main__":
    main()
