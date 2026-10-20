#!/usr/bin/env python3
"""Presupuesto con motores propios → motor/bom/Presupuesto_Motor_Propio.xlsx

Costo unitario de cada motor (DS-I y DS-D) por escala de producción, y el presupuesto del dron y de la flota de
prototipos reemplazando los motores comerciales por los propios. Todo con fórmulas sobre dos hojas de datos:
  BOM_Motor     ← motor/bom/lista_materiales_motor.csv (gen_bom_motor.py)
  BOM_Prototipo ← manufacturing/bom/bom_prototipo_v1.csv (tools/bom/gen_bom.py)
Los supuestos (mano de obra, contingencia, merma, energía, descuentos por volumen) están en la hoja Supuestos.

    .venv/bin/python motor/bom/gen_presupuesto.py
"""

from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "motor" / "bom"))
from gen_bom_motor import COTS_PRICE, PROCESS, TOOLS  # noqa: E402

from tools.bom.gen_bom_xlsx import BAND_FILL, BOX, GRAY, INPUT_FILL, NAVY, TOTAL_FILL, USD, USD0, font, header, title  # noqa: E402

MOTOR_CSV = ROOT / "motor" / "bom" / "lista_materiales_motor.csv"
PROTO_CSV = ROOT / "manufacturing" / "bom" / "bom_prototipo_v1.csv"
OUT = ROOT / "motor" / "bom" / "Presupuesto_Motor_Propio.xlsx"
COTS_ID = {"DS-I": "I001", "DS-D": "D023"}                          # línea del motor comercial en la BOM del prototipo
ROTORS = {"DS-I": 4, "DS-D": 6}
TIERS = ["1 motor", "Validación", "Flota", "100", "500"]
GROUPS = [("acero", "Acero eléctrico y de rotor (de plancha suelta a compra por kg)", [1.0, 1.0, 0.45, 0.25, 0.20]),
          ("imanes", "Imanes a medida (lote mínimo → pedido grande)", [1.0, 1.0, 1.0, 0.70, 0.50]),
          ("cobre", "Alambre esmaltado", [1.0, 1.0, 1.0, 0.85, 0.75]),
          ("rodamientos", "Rodamientos", [1.0, 1.0, 1.0, 0.80, 0.70]),
          ("otros", "Tornillería, insertos, cables, conectores, filamento", [1.0, 1.0, 1.0, 0.85, 0.75]),
          ("consumibles", "Epoxi, barniz, adhesivos, aislantes", [1.0, 1.0, 1.0, 0.90, 0.80])]
LEARNING = [1.0, 1.0, 0.85, 0.70, 0.60]          # horas de mano de obra relativas (curva de aprendizaje + útiles)


def group_of(r: dict) -> str:
    rid, cat = r["id"], r["categoria"]
    if cat == "consumible":
        return "consumibles"
    if rid[1:] in ("01", "02"):
        return "acero"
    if rid[1:] == "03":
        return "imanes"
    if cat == "bobinado":
        return "cobre"
    if "Rodamiento" in r["descripcion"]:
        return "rodamientos"
    return "otros"


def main() -> None:
    motor_rows = list(csv.DictReader(open(MOTOR_CSV, encoding="utf-8")))
    proto_rows = list(csv.DictReader(open(PROTO_CSV, encoding="utf-8")))
    fleet = {v: next(int(r["cant_total"]) for r in proto_rows if r["id"] == COTS_ID[v]) for v in ("DS-I", "DS-D")}
    wb = Workbook()
    lm = wb.active
    lm.title = "Léeme"
    sup = wb.create_sheet("Supuestos")
    sheets = {v: wb.create_sheet(f"Motor {v}") for v in ("DS-I", "DS-D")}
    comp = wb.create_sheet("Comparación")
    dron = wb.create_sheet("Dron y flota")
    bm = wb.create_sheet("BOM_Motor")
    bp = wb.create_sheet("BOM_Prototipo")

    # ---------------- datos
    mcols = ["id", "motor", "categoria", "grupo", "descripcion", "uso", "unidad", "por_presentacion", "precio"]
    header(bm, 1, mcols)
    for i, r in enumerate(motor_rows):
        vals = [r["id"], r["motor"], r["categoria"], group_of(r), r["descripcion"], float(r["uso"]), r["unidad"], float(r["por_presentacion"]),
                float(r["precio"])]
        for j, v in enumerate(vals):
            bm.cell(2 + i, 1 + j, v).font = font(color="0000FF" if j >= 5 and j != 6 else "000000")
    for col, wdt in zip("ABCDEFGHI", (6, 8, 12, 12, 70, 9, 9, 10, 10)):
        bm.column_dimensions[col].width = wdt
    pcols = ["id", "dron", "categoria", "descripcion", "cant_por_dron", "cant_total", "precio_unit_usd"]
    header(bp, 1, pcols)
    for i, r in enumerate(proto_rows):
        vals = [r["id"], r["dron"], r["categoria"], r["descripcion"], float(r["cant_por_dron"]), float(r["cant_total"]), float(r["precio_unit_usd"])]
        for j, v in enumerate(vals):
            bp.cell(2 + i, 1 + j, v).font = font(color="0000FF" if j >= 4 else "000000")
    for col, wdt in zip("ABCDEFG", (6, 8, 22, 70, 10, 10, 10)):
        bp.column_dimensions[col].width = wdt
    p_last = 1 + len(proto_rows)

    # ---------------- supuestos
    title(sup, "Supuestos del presupuesto", "Celdas amarillas: cambiar libremente. Azules: estimaciones documentadas.")
    for col, wdt in zip("ABCDEFGH", (44, 12, 12, 12, 12, 12, 12, 40)):
        sup.column_dimensions[col].width = wdt
    inputs = [("Mano de obra (US$/h; 0 = no se cuenta)", 0.0, USD, "El usuario fabrica: 0. Para cotizar con un técnico: p. ej. 4-6 US$/h."),
              ("Contingencia sobre el costo", 0.10, "0%", "imprevistos, precios que suben, envíos"),
              ("Merma de fabricación (material desechado o rehecho)", 0.10, "0%", "primeros motores: láminas o bobinas que se rehacen"),
              ("Electricidad (US$/kWh)", 0.20, USD, "tarifa residencial típica"),
              ("Potencia del láser de fibra en uso (kW)", 0.6, "0.0", "láser de 30-50 W con enfriador y extracción"),
              ("Potencia de la impresora (kW)", 0.15, "0.00", "con cama caliente"),
              ("Herramientas (US$, una vez)", f"={sum(t[1] for t in TOOLS)}", USD0, "hoja Herramientas de Lista_Materiales_Motor.xlsx")]
    sup["A4"] = "Generales"
    sup["A4"].font = font(True, NAVY, 11)
    for i, (lab, val, fmt, note) in enumerate(inputs):
        r = 5 + i
        sup.cell(r, 1, lab).font = font()
        c = sup.cell(r, 2, val)
        c.number_format = fmt
        c.fill = INPUT_FILL if i < 6 else BAND_FILL
        c.border = BOX
        sup.cell(r, 8, note).font = font(color=GRAY, size=9)
    SUP = {"labor": "Supuestos!$B$5", "cont": "Supuestos!$B$6", "scrap": "Supuestos!$B$7", "kwh": "Supuestos!$B$8",
           "laser_kw": "Supuestos!$B$9", "printer_kw": "Supuestos!$B$10", "tools": "Supuestos!$B$11"}
    r0 = 14
    sup.cell(r0, 1, "Motores por escala").font = font(True, NAVY, 11)
    header(sup, r0 + 1, ["Escala"] + TIERS)
    for j, v in enumerate(("DS-I", "DS-D")):
        sup.cell(r0 + 2 + j, 1, f"Motores {v}").font = font()
        for t, n in enumerate([1, 2, fleet[v], 100, 500]):
            c = sup.cell(r0 + 2 + j, 2 + t, n)
            c.font = font(color="0000FF")
            c.border = BOX
            c.alignment = Alignment(horizontal="center")
    sup.cell(r0 + 4, 1, "Herramientas amortizadas en (motores de los 2 tipos)").font = font()
    for t in range(len(TIERS)):
        col = get_column_letter(2 + t)
        c = sup.cell(r0 + 4, 2 + t, f"={col}{r0 + 2}+{col}{r0 + 3}")
        c.border = BOX
        c.alignment = Alignment(horizontal="center")
    AMORT_ROW = r0 + 4
    g0 = r0 + 7
    sup.cell(g0, 1, "Precio relativo por volumen (1 = precio de la lista de compras)").font = font(True, NAVY, 11)
    header(sup, g0 + 1, ["Grupo"] + TIERS + ["", "Qué incluye"])
    G_ROW = {}
    for i, (key, desc, factors) in enumerate(GROUPS):
        r = g0 + 2 + i
        sup.cell(r, 1, key).font = font(True)
        for t, f in enumerate(factors):
            c = sup.cell(r, 2 + t, f)
            c.number_format = "0.00"
            c.font = font(color="0000FF")
            c.border = BOX
        sup.cell(r, 8, desc).font = font(color=GRAY, size=9)
        G_ROW[key] = r
    lr = g0 + 3 + len(GROUPS)
    sup.cell(lr, 1, "Horas de mano de obra relativas (aprendizaje)").font = font(True)
    for t, f in enumerate(LEARNING):
        c = sup.cell(lr, 2 + t, f)
        c.number_format = "0.00"
        c.font = font(color="0000FF")
        c.border = BOX
    sup.cell(lr + 2, 1, ("Los descuentos por volumen son estimaciones (acero por kg cortado a medida, imanes en pedido grande, "
                         "rodamientos por caja). Reemplazar con cotizaciones (tarea S17-05).")).font = font(color=GRAY, size=9, italic=True)
    G_RANGE = f"Supuestos!$A${g0 + 2}:$A${g0 + 1 + len(GROUPS)}"

    # ---------------- motor (por escala)
    hours = {"DS-I": sum(p[1] for p in PROCESS if p[3] in ("mano", "láser + mano")) / 60,
             "DS-D": sum(p[2] for p in PROCESS if p[3] in ("mano", "láser + mano")) / 60}
    laser_h = {"DS-I": sum(p[1] for p in PROCESS if "láser" in p[3]) / 60, "DS-D": sum(p[2] for p in PROCESS if "láser" in p[3]) / 60}
    print_h = {"DS-I": sum(p[1] for p in PROCESS if p[3] == "impresora") / 60, "DS-D": sum(p[2] for p in PROCESS if p[3] == "impresora") / 60}
    totals = {}

    def motor_sheet(veh: str, ws) -> dict:
        title(ws, f"Presupuesto por motor · {veh}", f"Costo de UN motor {veh} según la cantidad que se fabrica. Fórmulas sobre "
              "BOM_Motor y Supuestos.")
        cols = ["ID", "Grupo", "Material / concepto", "Uso", "Unidad"] + [f"{t} (US$)" for t in TIERS]
        header(ws, 4, cols)
        ws.row_dimensions[4].height = 30
        for col, wdt in zip("ABCDEFGHIJ", (6, 12, 62, 8, 9, 13, 13, 13, 13, 13)):
            ws.column_dimensions[col].width = wdt
        mine = [i for i, r in enumerate(motor_rows) if r["motor"] in (veh, "común")]
        row = 5
        for n, i in enumerate(mine):
            br = 2 + i
            ws.cell(row, 1, f"=BOM_Motor!A{br}")
            ws.cell(row, 2, f"=BOM_Motor!D{br}")
            ws.cell(row, 3, f"=BOM_Motor!E{br}")
            ws.cell(row, 4, f"=BOM_Motor!F{br}").number_format = "0.###"
            ws.cell(row, 5, f"=BOM_Motor!G{br}")
            for t in range(len(TIERS)):
                fac = f"INDEX(Supuestos!${get_column_letter(2 + t)}${g0 + 2}:${get_column_letter(2 + t)}${g0 + 1 + len(GROUPS)},MATCH(B{row},{G_RANGE},0))"
                c = ws.cell(row, 6 + t, f"=BOM_Motor!F{br}/BOM_Motor!H{br}*BOM_Motor!I{br}*{fac}")
                c.number_format = USD
            for k in range(1, 11):
                ws.cell(row, k).border = BOX
                ws.cell(row, k).font = font(color="008000" if k <= 5 else "000000")
                if n % 2:
                    ws.cell(row, k).fill = BAND_FILL
            ws.cell(row, 3).alignment = Alignment(wrap_text=True, vertical="top")
            row += 1
        last_item = row - 1
        rows_sum = {}

        def line(label, fn, bold=False, fill=None, key=None, note=None):
            nonlocal row
            ws.cell(row, 3, label).font = font(bold)
            for t in range(len(TIERS)):
                c = ws.cell(row, 6 + t, fn(t, get_column_letter(6 + t)))
                c.number_format = USD
                c.font = font(bold)
            for k in range(1, 11):
                ws.cell(row, k).border = BOX
                if fill:
                    ws.cell(row, k).fill = fill
            if note:
                ws.cell(row, 3).comment = Comment(note, "DronSwarm")
            if key:
                rows_sum[key] = row
            row += 1
        line("Materiales y consumibles", lambda t, c: f"=SUM({c}5:{c}{last_item})", True, TOTAL_FILL, "mat")
        line("Merma de fabricación", lambda t, c: f"={c}{rows_sum['mat']}*{SUP['scrap']}", key="scrap")
        line(f"Electricidad (láser {laser_h[veh]:.2f} h, impresora {print_h[veh]:.1f} h)",
             lambda t, c: f"=({laser_h[veh]:.4f}*{SUP['laser_kw']}+{print_h[veh]:.4f}*{SUP['printer_kw']})*{SUP['kwh']}", key="energy")
        line("Herramientas amortizadas", lambda t, c: f"={SUP['tools']}/Supuestos!{get_column_letter(2 + t)}{AMORT_ROW}", key="tools",
             note="Herramientas que se compran una vez, repartidas entre todos los motores de esa escala (de los dos tipos).")
        line(f"Mano de obra ({hours[veh]:.1f} h × aprendizaje × tarifa)",
             lambda t, c: f"={hours[veh]:.4f}*Supuestos!{get_column_letter(2 + t)}{lr}*{SUP['labor']}", key="labor")
        line("Subtotal", lambda t, c: f"=SUM({c}{rows_sum['mat']}:{c}{rows_sum['labor']})", True, key="sub")
        line("Contingencia", lambda t, c: f"={c}{rows_sum['sub']}*{SUP['cont']}", key="cont")
        line("COSTO POR MOTOR", lambda t, c: f"={c}{rows_sum['sub']}+{c}{rows_sum['cont']}", True, TOTAL_FILL, "total")
        line("Motor comercial que reemplaza", lambda t, c: COTS_PRICE[veh], key="cots")
        line("Ahorro por motor", lambda t, c: f"={c}{rows_sum['cots']}-{c}{rows_sum['total']}", True, key="save")
        line("Costo propio / comercial", lambda t, c: f"={c}{rows_sum['total']}/{c}{rows_sum['cots']}", key="ratio")
        for t in range(len(TIERS)):
            ws.cell(rows_sum["ratio"], 6 + t).number_format = "0%"
        ws.freeze_panes = "F5"
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        return rows_sum

    for veh, ws in sheets.items():
        totals[veh] = motor_sheet(veh, ws)

    # ---------------- comparación
    title(comp, "Motor propio vs comercial", "Por motor, por dron y amortización de las herramientas.")
    for col, wdt in zip("ABCDEFGH", (40, 14, 14, 14, 14, 14, 4, 4)):
        comp.column_dimensions[col].width = wdt
    header(comp, 4, ["Concepto"] + TIERS)
    r = 5
    for veh in ("DS-I", "DS-D"):
        rs = totals[veh]
        for lab, key in ((f"{veh} · costo por motor propio", "total"), (f"{veh} · motor comercial", "cots"), (f"{veh} · ahorro por motor", "save")):
            comp.cell(r, 1, lab).font = font(key == "save")
            for t in range(len(TIERS)):
                c = comp.cell(r, 2 + t, f"='Motor {veh}'!{get_column_letter(6 + t)}{rs[key]}")
                c.number_format = USD
                c.border = BOX
            r += 1
        comp.cell(r, 1, f"{veh} · ahorro por dron ({ROTORS[veh]} motores)").font = font(True)
        for t in range(len(TIERS)):
            c = comp.cell(r, 2 + t, f"={get_column_letter(2 + t)}{r - 1}*{ROTORS[veh]}")
            c.number_format = USD0
            c.font = font(True)
            c.border = BOX
            c.fill = TOTAL_FILL
        r += 2
    comp.cell(r, 1, "Motores para pagar las herramientas (al ahorro de la flota)").font = font(True)
    for j, veh in enumerate(("DS-I", "DS-D")):
        c = comp.cell(r + 1 + j, 2, f"=ROUNDUP({SUP['tools']}/('Motor {veh}'!H{totals[veh]['save']}),0)")
        comp.cell(r + 1 + j, 1, f"si fueran solo motores {veh}").font = font()
        c.border = BOX

    # ---------------- dron y flota
    title(dron, "Dron y flota de prototipos con motores propios",
          "BOM del prototipo (S09) con los motores comerciales reemplazados por los propios (escala Flota).")
    for col, wdt in zip("ABCDEF", (52, 18, 18, 18, 14, 4)):
        dron.column_dimensions[col].width = wdt
    header(dron, 4, ["Concepto", "Con motores comerciales", "Con motores propios", "Diferencia", "%"])
    rr = 5
    for veh in ("DS-I", "DS-D"):
        cid = COTS_ID[veh]
        base = f'SUMPRODUCT((BOM_Prototipo!$B$2:$B${p_last}="{veh}")*BOM_Prototipo!$E$2:$E${p_last}*BOM_Prototipo!$G$2:$G${p_last})'
        cots_unit = f'SUMIFS(BOM_Prototipo!$G$2:$G${p_last},BOM_Prototipo!$A$2:$A${p_last},"{cid}")'
        n_rot = f'SUMIFS(BOM_Prototipo!$E$2:$E${p_last},BOM_Prototipo!$A$2:$A${p_last},"{cid}")'
        own = f"'Motor {veh}'!$H${totals[veh]['total']}"
        dron.cell(rr, 1, f"Un {veh} (componentes, sin repuestos)").font = font(True)
        dron.cell(rr, 2, f"={base}")
        dron.cell(rr, 3, f"={base}-{n_rot}*{cots_unit}+{n_rot}*{own}")
        rr_d = rr
        rr += 1
        dron.cell(rr, 1, f"   de los cuales motores ({ROTORS[veh]})").font = font(color=GRAY)
        dron.cell(rr, 2, f"={n_rot}*{cots_unit}")
        dron.cell(rr, 3, f"={n_rot}*{own}")
        for x in (rr_d, rr):
            dron.cell(x, 4, f"=C{x}-B{x}")
            dron.cell(x, 5, f"=IF(B{x}=0,\"\",D{x}/B{x})")
            for k in (2, 3, 4):
                dron.cell(x, k).number_format = USD0
                dron.cell(x, k).border = BOX
            dron.cell(x, 5).number_format = "0%"
        rr += 2
    # flota
    dron.cell(rr, 1, "FLOTA DE PROTOTIPOS (4 DS-I + 2 DS-D, repuestos y equipo de tierra)").font = font(True, NAVY, 11)
    rr += 1
    tot_all = f"SUM(BOM_Prototipo!$F$2:$F${p_last})"
    _ = tot_all
    total_bom = f"SUMPRODUCT(BOM_Prototipo!$F$2:$F${p_last},BOM_Prototipo!$G$2:$G${p_last})"
    lines = []
    for veh in ("DS-I", "DS-D"):
        cid = COTS_ID[veh]
        qty = f'SUMIFS(BOM_Prototipo!$F$2:$F${p_last},BOM_Prototipo!$A$2:$A${p_last},"{cid}")'
        unit = f'SUMIFS(BOM_Prototipo!$G$2:$G${p_last},BOM_Prototipo!$A$2:$A${p_last},"{cid}")'
        lines.append((f"Motores {veh} (flota + repuesto)", f"={qty}*{unit}", f"={qty}*'Motor {veh}'!$H${totals[veh]['total']}"))
    lines.append(("Lote de validación (2 DS-I + 2 DS-D, antes de la flota)", "=0",
                  f"=2*'Motor DS-I'!$G${totals['DS-I']['total']}+2*'Motor DS-D'!$G${totals['DS-D']['total']}"))
    lines.append(("Herramientas del motor (una vez)", "=0", f"={SUP['tools']}"))
    first = rr
    for lab, a, b in lines:
        dron.cell(rr, 1, lab).font = font()
        dron.cell(rr, 2, a)
        dron.cell(rr, 3, b)
        dron.cell(rr, 4, f"=C{rr}-B{rr}")
        for k in (2, 3, 4):
            dron.cell(rr, k).number_format = USD0
            dron.cell(rr, k).border = BOX
        rr += 1
    dron.cell(rr, 1, "Resto de la BOM (sin motores)").font = font()
    motor_lines_cots = f"B{first}+B{first + 1}"
    dron.cell(rr, 2, f"={total_bom}-({motor_lines_cots})")
    dron.cell(rr, 3, f"=B{rr}")
    dron.cell(rr, 4, f"=C{rr}-B{rr}")
    for k in (2, 3, 4):
        dron.cell(rr, k).number_format = USD0
        dron.cell(rr, k).border = BOX
    rr += 1
    dron.cell(rr, 1, "TOTAL FLOTA").font = font(True)
    for k, col in ((2, "B"), (3, "C"), (4, "D")):
        c = dron.cell(rr, k, f"=SUM({col}{first}:{col}{rr - 1})")
        c.number_format = USD0
        c.font = font(True)
        c.fill = TOTAL_FILL
        c.border = BOX
    dron.cell(rr, 5, f"=D{rr}/B{rr}").number_format = "0%"
    dron.cell(rr + 2, 1, ("Los motores propios se usan en la flota solo si pasan el Gate G5 (banco y vuelo, M8). Hasta entonces, "
                          "la flota vuela con los comerciales y este presupuesto es el objetivo.")).font = font(color=GRAY, size=9, italic=True)

    # ---------------- léeme
    title(lm, "Presupuesto con motores propios", f"Generado el {date.today():%d/%m/%Y} por motor/bom/gen_presupuesto.py")
    lm.column_dimensions["B"].width = 24
    lm.column_dimensions["C"].width = 96
    notes = [("Supuestos", "Mano de obra, contingencia, merma, energía y descuentos por volumen. Celdas amarillas para cambiar."),
             ("Motor DS-I / DS-D", "Costo de UN motor en 5 escalas (1, validación, flota, 100, 500): materiales, merma, electricidad, "
              "herramientas amortizadas, mano de obra y contingencia, contra el motor comercial."),
             ("Comparación", "Ahorro por motor y por dron en cada escala; motores para pagar las herramientas."),
             ("Dron y flota", "BOM del prototipo con los motores propios en lugar de los comerciales: costo de un dron y de la flota."),
             ("BOM_Motor, BOM_Prototipo", "Datos de origen (de las listas de compras). No editar: se regeneran."),
             ("Regenerar", "`.venv/bin/python motor/bom/gen_presupuesto.py` (después de gen_bom_motor.py)."),
             ("Precios", "US$ de octubre de 2026, sin envío ni aranceles; estimados hasta tener cotizaciones (S17-05).")]
    for i, (k, v) in enumerate(notes):
        lm.cell(4 + i, 2, k).font = font(True)
        lm.cell(4 + i, 3, v).font = font()
        lm.cell(4 + i, 3).alignment = Alignment(wrap_text=True, vertical="top")
    wb.active = 2
    for s, color in zip(wb.worksheets, ("808080", "C65911", NAVY, NAVY, "548235", "548235", "A6A6A6", "A6A6A6")):
        s.sheet_properties.tabColor = color
    wb.calculation.fullCalcOnLoad = True
    wb.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
