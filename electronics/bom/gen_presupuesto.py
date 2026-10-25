#!/usr/bin/env python3
"""E7 · Presupuesto de la electrónica propia → electronics/bom/Presupuesto_Electronica.xlsx + bom_<placa>.csv

Lista de piezas de cada placa desde su netlist (electronics/kicad/<placa>/<placa>.net), precios unitarios a 100
unidades (estimados de distribuidor, oct. 2026, en la hoja "Precios": celdas azules editables), PCB por área y montaje
por servicio (hoja "Supuestos"). Resumen por dron contra la electrónica comercial del BOM del prototipo.

    .venv/bin/python electronics/bom/gen_presupuesto.py
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from electronics.netlist import load  # noqa: E402
from tools.bom.gen_bom_xlsx import BAND_FILL, BOX, GRAY, NAVY, TOTAL_FILL, USD, USD0, font, header, title  # noqa: E402

OUT = ROOT / "electronics" / "bom"
BOARDS = {"esc_ds_d": "ESC GaN DS-D (1 por motor)", "esc_ds_i": "ESC 4 en 1 DS-I (silicio)", "fc": "Controladora FMU",
          "gnss": "GNSS RTK LG290P", "bms_ds_i": "BMS 6S (DS-I)", "bms_ds_d": "BMS 12S (DS-D)", "charger": "Cargador GaN 1 kW"}
SIZE_CM2 = {"esc_ds_d": 4 * 7, "esc_ds_i": 6 * 6, "fc": 5.5 * 4.5, "gnss": 4 * 4, "bms_ds_i": 6 * 4, "bms_ds_d": 8 * 4.5, "charger": 10 * 8}
HEAVY_CU = {"esc_ds_d", "esc_ds_i", "charger"}                       # 2 oz en las de potencia
EXTRAS = {"gnss": [("Antena multibanda activa (L1/L2/L5) con cable u.FL", 25.0), ("Caja impresa + tapa transparente a RF", 2.0)],
          "charger": [("Fuente AC-DC 48 V 1 kW (Mean Well RSP-1000-48 o similar)", 190.0), ("Caja, ventilador 12 V, conectores XT60", 25.0)],
          "esc_ds_d": [("Disipador de aluminio + pasta térmica", 1.5)]}
# (patrón sobre "valor|huella", precio US$ a 100 u.) — el primero que coincide
PRICES = [
    (r"^EPC2302\|", 4.00), (r"^LMG1210\|", 3.00), (r"^STM32G071", 1.60), (r"^STM32H743", 9.80), (r"^STM32G0B1", 2.20),
    (r"^STM32G474", 4.50), (r"^LM5164", 1.40), (r"^MCP1703", 0.35), (r"^TLV75533", 0.12), (r"^INA181", 0.35),
    (r"^DRV8300", 0.85), (r"^CSD18503", 0.55), (r"^BSC035N10", 1.20), (r"^IIM-42652", 4.50), (r"^BMI088", 5.50),
    (r"^MS5611", 3.50), (r"^IST8310", 0.80), (r"^24LC64", 0.15), (r"^MB85RS256", 1.60), (r"^TCAN330", 0.90),
    (r"^TPS2116", 0.45), (r"^TPS2561", 0.90), (r"^USBLC6", 0.10), (r"^USB_C_Receptacle", 0.15), (r"^Micro_SD", 0.25),
    (r"^LG290P", 72.00), (r"^BQ7693003", 2.20), (r"^BQ7694003", 3.00), (r"^LM74700", 1.00), (r"^ESD0P2RF", 0.10),
    (r"^TPD1E05", 0.08), (r"^SMAJ", 0.08), (r"^AO340[01]A", 0.03), (r"^2N7002|^BSS123", 0.02), (r"^BZX84", 0.02),
    (r"^BAT54|^PMEG", 0.03), (r"^Buzzer|CPT-9019", 0.40), (r"^8MHz|^16MHz", 0.12), (r"^30A\|", 0.30),
    (r"^10k B3950", 0.03), (r"^verde|^azul|^rojo|^LED_RGB", 0.02), (r"^SW_Push", 0.10),
    (r"\|.*XAL1510", 3.50), (r"\|.*MSS1246", 0.45), (r"^68n\|", 0.02), (r"^600R", 0.01),
    (r"^470u/63V", 0.35), (r"^470u/35V", 0.25), (r"\|.*R_Shunt", 0.35),
    (r"^4\.7u/100V\|", 0.25), (r"^2\.2u/100V\|", 0.15), (r"^2\.2u/50V\|", 0.10), (r"^22u/25V\|", 0.12), (r"\|.*C_1210", 0.10),
    (r"\|.*C_0805", 0.03), (r"\|.*C_0603", 0.008), (r"\|.*C_0402", 0.004), (r"^DNP\|", 0.0),
    (r"\|.*R_1206", 0.008), (r"\|.*R_0603", 0.003), (r"\|.*R_0402", 0.002),
    (r"\|Connector_JST:JST_GH_SM(\d+)", None), (r"\|Connector_JST:JST_SH", 0.12), (r"\|Connector_JST:JST_XH", 0.25),
    (r"\|Connector_PinHeader_1.27mm", 0.05), (r"\|Connector_Coaxial:U.FL", 0.20), (r"\|DronSwarm:Pad_Power|\|TestPoint:", 0.0),
]
ASSUMPTIONS = [("PCB 4 capas 1 oz, US$/cm² (a 100 placas)", 0.07, "JLCPCB/PCBWay, estándar FR-4 1.6 mm"),
               ("Recargo 2 oz cobre exterior (placas de potencia)", 0.40, "fracción sobre el precio de la PCB"),
               ("PCB: costo fijo por placa (US$)", 0.30, "panelizado, prueba eléctrica"),
               ("Montaje: US$ por junta de soldadura", 0.0017, "montaje SMD por servicio"),
               ("Montaje: configuración del pedido (US$)", 25.0, "plantilla + puesta a punto, por pedido"),
               ("Montaje: cargo por pieza no estándar (US$, por pedido)", 3.0, "por cada pieza distinta"),
               ("Placas por pedido", 100, "escala del presupuesto"),
               ("Recubrimiento conformado (US$ por placa, 12S)", 0.60, "obligatorio en 12S a 5,000 msnm (IPC-2221 B4)")]
COMMERCIAL = {"DS-I": [("ESC 4 en 1 50 A comercial", 80.0), ("Pixhawk 6C", 225.0), ("GNSS H-RTK F9P", 250.0)],
              "DS-D": [("6 × ESC APD 120F3", 720.0), ("Pixhawk 6C", 225.0), ("GNSS H-RTK F9P", 250.0)]}
PER_DRONE = {"DS-I": [("esc_ds_i", 1), ("fc", 1), ("gnss", 1), ("bms_ds_i", 1)],
             "DS-D": [("esc_ds_d", 6), ("fc", 1), ("gnss", 1), ("bms_ds_d", 1)]}


def price_of(value: str, fp: str) -> tuple[float, bool]:
    key = f"{value}|{fp}"
    for pat, p in PRICES:
        m = re.search(pat, key)
        if m:
            if p is None:                                              # JST-GH: 0.12 + 0.02 por posición
                return round(0.12 + 0.02 * int(m.group(1)), 2), True
            return p, True
    return 0.05, False


def board_bom(board: str) -> list[dict]:
    parts, nets = load(board)
    pads = Counter(r for nodes in nets.values() for r, _, _ in nodes)
    groups = defaultdict(list)
    for ref, p in parts.items():
        groups[(p["value"], p["footprint"])].append(ref)
    rows = []
    for (val, fp), refs in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        price, known = price_of(val, fp)
        rows.append({"value": val, "footprint": fp, "qty": len(refs), "refs": ",".join(sorted(refs, key=lambda r: (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r) or 0)))),
                     "price": price, "known": known, "joints": sum(max(pads[r], 2) for r in refs)})
    return rows


def main() -> None:
    wb = Workbook()
    res = wb.active
    res.title = "Resumen"
    sup = wb.create_sheet("Supuestos")
    title(sup, "Supuestos de PCB y montaje", "Celdas azules editables; todas las hojas recalculan.")
    header(sup, 4, ["Supuesto", "Valor", "Fuente / nota"])
    for i, (k, v, n) in enumerate(ASSUMPTIONS):
        r = 5 + i
        sup.cell(r, 1, k).border = BOX
        c = sup.cell(r, 2, v)
        c.font = font(color="0000FF")
        c.border = BOX
        sup.cell(r, 3, n).font = font(color=GRAY, size=9, italic=True)
    for col, w in zip("ABC", (52, 12, 50)):
        sup.column_dimensions[col].width = w
    S = {k: f"Supuestos!$B${5 + i}" for i, (k, _, _) in enumerate(ASSUMPTIONS)}
    a_cm2, a_cu, a_fix, a_joint, a_setup, a_ext, a_qty, a_coat = (S[k] for k, _, _ in ASSUMPTIONS)
    totals = {}
    for board, label in BOARDS.items():
        rows = board_bom(board)
        with open(OUT / f"bom_{board}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Comment", "Designator", "Footprint", "Quantity", "Unit price USD (est.)"])
            for r in rows:
                w.writerow([r["value"], r["refs"], r["footprint"], r["qty"], r["price"]])
        ws = wb.create_sheet(board)
        title(ws, f"{label}: lista de materiales", f"Desde electronics/kicad/{board}/{board}.net · precios a 100 u. (estimados)")
        cols = [("Valor / pieza", 30), ("Huella", 44), ("Cant.", 7), ("Referencias", 40), ("Precio unit. (US$)", 12),
                ("Subtotal (US$)", 12), ("Precio", 9)]
        header(ws, 4, [c for c, _ in cols])
        for i, (_, wdt) in enumerate(cols):
            ws.column_dimensions["ABCDEFG"[i]].width = wdt
        first = 5
        for i, r in enumerate(rows):
            row = first + i
            vals = [r["value"], r["footprint"], r["qty"], r["refs"], r["price"], f"=C{row}*E{row}", "lista" if r["known"] else "REVISAR"]
            for j, v in enumerate(vals):
                c = ws.cell(row, j + 1, v)
                c.border = BOX
                c.font = font(color="0000FF" if j == 4 else ("C00000" if v == "REVISAR" else "000000"), size=9)
                if j in (4, 5):
                    c.number_format = USD
                if j == 3:
                    c.alignment = Alignment(wrap_text=True, vertical="top")
                if i % 2:
                    c.fill = BAND_FILL
        last = first + len(rows) - 1
        t = last + 2
        n_unique = len(rows)
        joints = sum(r["joints"] for r in rows)
        extras = EXTRAS.get(board, [])
        lines = [("Componentes", f"=SUM(F{first}:F{last})"),
                 ("PCB", f"={SIZE_CM2[board]}*{a_cm2}*(1+{a_cu if board in HEAVY_CU else 0})+{a_fix}"),
                 ("Montaje (juntas + configuración y piezas no estándar repartidas)", f"={joints}*{a_joint}+({a_setup}+{n_unique}*{a_ext})/{a_qty}"),
                 ("Recubrimiento conformado", f"={a_coat}" if board in ("esc_ds_d", "bms_ds_d", "charger") else "=0")]
        lines += [(k, v) for k, v in extras]
        for i, (k, v) in enumerate(lines):
            ws.cell(t + i, 4, k).font = font(True if i == 0 else False)
            c = ws.cell(t + i, 6, v)
            c.number_format = USD
            if not isinstance(v, str):
                c.font = font(color="0000FF")
        tot = t + len(lines)
        ws.cell(tot, 4, "TOTAL POR PLACA").font = font(True)
        ws[f"F{tot}"] = f"=SUM(F{t}:F{tot - 1})"
        ws[f"F{tot}"].number_format = USD
        ws[f"F{tot}"].font = font(True)
        for col in "DEF":
            ws[f"{col}{tot}"].fill = TOTAL_FILL
        ws.cell(tot + 2, 1, f"{len(rows)} piezas distintas, {sum(r['qty'] for r in rows)} en total, {joints} juntas. "
                f"Área {SIZE_CM2[board]} cm².").font = font(color=GRAY, size=9, italic=True)
        ws.freeze_panes = "A5"
        totals[board] = f"'{board}'!$F${tot}"
    # Resumen por dron
    title(res, "Presupuesto de la electrónica propia", "Por dron, contra la electrónica comercial del prototipo. Precios a 100 placas (estimados).")
    for col, w in zip("ABCDE", (46, 10, 16, 16, 4)):
        res.column_dimensions[col].width = w
    r = 4
    for veh in ("DS-I", "DS-D"):
        res.cell(r, 1, f"{veh} · electrónica propia").font = font(True, NAVY, 12)
        header(res, r + 1, ["Placa", "Cant.", "Por placa (US$)", "Por dron (US$)"])
        s = r + 2
        for i, (b, q) in enumerate(PER_DRONE[veh]):
            row = s + i
            res.cell(row, 1, BOARDS[b]).border = BOX
            res.cell(row, 2, q).border = BOX
            res.cell(row, 3, f"={totals[b]}").number_format = USD
            res.cell(row, 4, f"=B{row}*C{row}").number_format = USD0
        e = s + len(PER_DRONE[veh]) - 1
        res.cell(e + 1, 1, "Total propio (sin BMS)").font = font(True)
        res[f"D{e + 1}"] = f"=SUM(D{s}:D{e})-D{e}"
        res.cell(e + 2, 1, "Total propio (con BMS)").font = font(True)
        res[f"D{e + 2}"] = f"=SUM(D{s}:D{e})"
        c0 = e + 4
        res.cell(c0, 1, "Electrónica comercial que reemplaza").font = font(True)
        for i, (k, v) in enumerate(COMMERCIAL[veh]):
            res.cell(c0 + 1 + i, 1, k)
            res.cell(c0 + 1 + i, 4, v).font = font(color="0000FF")
        ce = c0 + len(COMMERCIAL[veh])
        res.cell(ce + 1, 1, "Total comercial").font = font(True)
        res[f"D{ce + 1}"] = f"=SUM(D{c0 + 1}:D{ce})"
        res.cell(ce + 2, 1, "AHORRO POR DRON (sin BMS, que el comercial no tiene)").font = font(True)
        res[f"D{ce + 2}"] = f"=D{ce + 1}-D{e + 1}"
        res.cell(ce + 3, 1, "Ahorro (%)").font = font(True)
        res[f"D{ce + 3}"] = f"=D{ce + 2}/D{ce + 1}"
        res[f"D{ce + 3}"].number_format = "0%"
        for rr in (e + 1, e + 2, ce + 1, ce + 2):
            res[f"D{rr}"].number_format = USD0
            res[f"D{rr}"].font = font(True)
            for col in "ABCD":
                res[f"{col}{rr}"].fill = TOTAL_FILL
        for rr in range(c0 + 1, ce + 1):
            res[f"D{rr}"].number_format = USD0
        r = ce + 6
    res.cell(r, 1, "Equipo de tierra").font = font(True, NAVY, 12)
    res.cell(r + 1, 1, BOARDS["charger"] + " (con fuente AC-DC)")
    res[f"D{r + 1}"] = f"={totals['charger']}"
    res[f"D{r + 1}"].number_format = USD0
    res.cell(r + 2, 1, "Cargador comercial 1 kW 12S + 6S (T049)")
    res.cell(r + 2, 4, 380.0).font = font(color="0000FF")
    res[f"D{r + 2}"].number_format = USD0
    res.cell(r + 4, 1, ("Precios estimados a 100 unidades (distribuidor, oct. 2026); las filas marcadas REVISAR no tienen precio "
                        "en la tabla. Se reemplazan por cotizaciones reales antes de comprar.")).font = font(color=GRAY, size=9, italic=True)
    wb.calculation.fullCalcOnLoad = True
    wb.save(OUT / "Presupuesto_Electronica.xlsx")
    print(OUT / "Presupuesto_Electronica.xlsx")


if __name__ == "__main__":
    main()
