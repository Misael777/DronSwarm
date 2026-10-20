#!/usr/bin/env python3
"""Lista de compras del prototipo v1 en Excel → manufacturing/bom/Lista_de_Compras_Prototipo_v1.xlsx

Lee el BOM (bom_prototipo_v1.csv, de tools/bom/gen_bom.py) y arma un libro para revisar y seguir las compras:
Léeme · Resumen · Compras (todas las líneas) · DS-I y DS-D (lista de armado de un dron).

Las celdas amarillas son del usuario (precio cotizado, proveedor elegido, estado, fechas, inspección, notas) y se
CONSERVAN al regenerar (por ID de ítem). Si el libro aún no existe, se siembran desde seguimiento_compras.csv.

    .venv/bin/python tools/bom/gen_bom_xlsx.py
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[2]
BOM = ROOT / "manufacturing" / "bom" / "bom_prototipo_v1.csv"
TRACK = ROOT / "manufacturing" / "bom" / "seguimiento_compras.csv"
OUT = ROOT / "manufacturing" / "bom" / "Lista_de_Compras_Prototipo_v1.xlsx"

FONT = "Arial"
NAVY, GRAY, LIGHT = "1F3864", "595959", "F2F2F2"
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")             # amarillo suave: lo llena el usuario
HEAD_FILL = PatternFill("solid", fgColor=NAVY)
BAND_FILL = PatternFill("solid", fgColor=LIGHT)
TOTAL_FILL = PatternFill("solid", fgColor="D9E1F2")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
USD = '"US$"#,##0.00;("US$"#,##0.00);"-"'
USD0 = '"US$"#,##0;("US$"#,##0);"-"'
PCT = '0.0%;-0.0%;"-"'
DATE = "dd/mm/yyyy"
STATES = ["Pendiente", "Cotizando", "Pedido", "En tránsito", "Recibido", "Inspeccionado OK", "Rechazado"]
FLEET_TXT = "4 DS-I + 2 DS-D"

# Hoja Compras: (encabezado, ancho, clave). clave: campo del CSV, "=" fórmula, "in:<campo>" celda del usuario
COLS = [
    ("ID", 7, "id"), ("Dron", 8, "dron"), ("Categoría", 16, "categoria"), ("Descripción", 52, "descripcion"),
    ("Cant. por dron", 9, "cant_por_dron"), ("Cant. flota", 9, "cant_flota"), ("Repuestos", 9, "cant_repuesto"),
    ("Cant. total", 9, "=qty"), ("Cant. fase A", 9, "fase_a"),
    ("Precio est. (US$)", 12, "precio_unit_usd"), ("Precio cotizado (US$)", 13, "in:quote"),
    ("Precio usado (US$)", 12, "=price"), ("Total flota (US$)", 13, "=total"), ("Costo fase A (US$)", 12, "=cost_a"),
    ("Costo por dron (US$)", 12, "=per_drone"), ("Fase", 7, "fase"), ("Plazo (sem.)", 8, "plazo_semanas"),
    ("Proveedor 1", 24, "proveedor_1"), ("Proveedor 2", 22, "proveedor_2"), ("Proveedor elegido", 20, "in:supplier"),
    ("Estado", 15, "in:state"), ("Fecha pedido", 12, "in:ordered"), ("Fecha llegada", 12, "in:arrived"),
    ("Inspección de entrada", 13, "in:inspection"), ("Tipo de precio", 11, "=price_kind"),
    ("Fuente del precio", 38, "fuente_precio"), ("Notas", 34, "in:notes"),
]
COL = {key: get_column_letter(i + 1) for i, (_, _, key) in enumerate(COLS)}
INPUT_KEYS = [k for _, _, k in COLS if k.startswith("in:")]
HEAD_ROW, FIRST = 4, 5


def font(bold=False, color="000000", size=10, italic=False):
    return Font(name=FONT, bold=bold, color=color, size=size, italic=italic)


def fase_a_qty(r: dict) -> int:
    """Cantidad que se pide en la fase A (validación): todo lo de fase A; de lo "A+B", lo del banco de empuje."""
    if r["fase"] == "A":
        return int(r["cant_total"])
    if r["fase"] == "A+B" and r["categoria"] == "propulsión":
        d = r["descripcion"]
        if d.startswith("Motor"):
            return 2                                   # 2 motores de cada tipo al banco
        if d.startswith("Hélice"):
            return 2                                   # un par CW/CCW para el banco
        return 1                                       # 1 ESC de cada tipo
    return 0


def saved_inputs() -> dict[str, dict]:
    """Celdas del usuario por ID: del libro existente o, la primera vez, de seguimiento_compras.csv."""
    out: dict[str, dict] = {}
    if OUT.exists():
        ws = load_workbook(OUT)["Compras"]
        heads = {ws.cell(HEAD_ROW, c).value: c for c in range(1, ws.max_column + 1)}
        cols = {k: heads.get(h) for h, _, k in COLS if k in INPUT_KEYS}
        for r in range(FIRST, ws.max_row + 1):
            rid = ws.cell(r, 1).value
            if rid:
                out[rid] = {k: ws.cell(r, c).value for k, c in cols.items() if c}
    elif TRACK.exists():
        for t in csv.DictReader(open(TRACK, encoding="utf-8")):
            out[t["id"]] = {"in:quote": float(t["precio_real_usd"]) if t["precio_real_usd"] else None,
                            "in:supplier": t["proveedor_elegido"] or None, "in:ordered": t["fecha_pedido"] or None,
                            "in:arrived": t["fecha_llegada"] or None, "in:inspection": t["inspeccion_ok"] or None,
                            "in:notes": t["observaciones"] or None}
    return out


def title(ws, text: str, sub: str):
    ws["A1"] = text
    ws["A1"].font = font(True, NAVY, 16)
    ws["A2"] = sub
    ws["A2"].font = font(False, GRAY, 9, italic=True)
    ws.sheet_view.showGridLines = False


def header(ws, row: int, labels: list[str], col0: int = 1):
    for i, h in enumerate(labels):
        c = ws.cell(row, col0 + i, h)
        c.font = font(True, "FFFFFF")
        c.fill = HEAD_FILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BOX


def sheet_compras(wb, rows, inputs) -> int:
    ws = wb.create_sheet("Compras")
    title(ws, "Lista de compras · prototipo v1",
          f"Flota {FLEET_TXT} con repuestos y equipo de tierra. Precios en US$ (2026-10). Celdas amarillas: para llenar.")
    header(ws, HEAD_ROW, [h for h, _, _ in COLS])
    ws.row_dimensions[HEAD_ROW].height = 42
    for i, (_, w, _) in enumerate(COLS):
        ws.column_dimensions[get_column_letter(i + 1)].width = w
    c = COL
    for n, r in enumerate(rows):
        row = FIRST + n
        saved = inputs.get(r["id"], {})
        f = {
            "=qty": f"={c['cant_flota']}{row}+{c['cant_repuesto']}{row}",
            "=price": f'=IF({c["in:quote"]}{row}="",{c["precio_unit_usd"]}{row},{c["in:quote"]}{row})',
            "=total": f"={c['=qty']}{row}*{c['=price']}{row}",
            "=cost_a": f"={c['fase_a']}{row}*{c['=price']}{row}",
            "=per_drone": f'=IF({c["dron"]}{row}="tierra","",{c["cant_por_dron"]}{row}*{c["=price"]}{row})',
            "=price_kind": f'=IF({c["in:quote"]}{row}<>"","Cotizado","{"Estimado" if r["estimado"] == "sí" else "De lista"}")',
        }
        for i, (_, _, key) in enumerate(COLS):
            cell = ws.cell(row, i + 1)
            if key.startswith("="):
                cell.value = f[key]
            elif key.startswith("in:"):
                v = saved.get(key)
                cell.value = "Pendiente" if key == "in:state" and not v else v
                cell.fill = INPUT_FILL
            elif key == "fase_a":
                cell.value = fase_a_qty(r)
                cell.font = font(color="0000FF")
            else:
                v = r[key]
                if key in ("cant_por_dron", "cant_flota", "cant_repuesto", "plazo_semanas"):
                    v = int(v)
                elif key == "precio_unit_usd":
                    v = float(v)
                cell.value = v
                if key in ("cant_por_dron", "cant_flota", "cant_repuesto", "precio_unit_usd", "plazo_semanas"):
                    cell.font = font(color="0000FF")              # dato de entrada del BOM
            if not cell.font or cell.font.name != FONT:
                cell.font = font()
            cell.border = BOX
            cell.alignment = Alignment(vertical="top", wrap_text=key in ("descripcion", "fuente_precio", "in:notes",
                                                                         "proveedor_1", "proveedor_2"))
            if key in ("precio_unit_usd", "in:quote", "=price", "=total", "=cost_a", "=per_drone"):
                cell.number_format = USD
            if key in ("in:ordered", "in:arrived"):
                cell.number_format = DATE
            if key in ("id", "dron", "fase", "=qty", "fase_a", "cant_por_dron", "cant_flota", "cant_repuesto",
                       "plazo_semanas", "in:state", "in:inspection", "=price_kind"):
                cell.alignment = Alignment(horizontal="center", vertical="top")
            if n % 2 and not key.startswith("in:"):
                cell.fill = BAND_FILL
    last = FIRST + len(rows) - 1
    tot = last + 1
    ws.cell(tot, 4, "TOTAL").font = font(True)
    for key in ("=total", "=cost_a"):
        col = c[key]
        ws[f"{col}{tot}"] = f"=SUM({col}{FIRST}:{col}{last})"
        ws[f"{col}{tot}"].number_format = USD0
        ws[f"{col}{tot}"].font = font(True)
    for i in range(1, len(COLS) + 1):
        ws.cell(tot, i).fill = TOTAL_FILL
        ws.cell(tot, i).border = BOX

    rng = lambda key: f"{c[key]}{FIRST}:{c[key]}{last}"  # noqa: E731
    dv = DataValidation(type="list", formula1=f'"{",".join(STATES)}"', allow_blank=True)
    dv.add(rng("in:state"))
    dv2 = DataValidation(type="list", formula1='"OK,Rechazado,Pendiente"', allow_blank=True)
    dv2.add(rng("in:inspection"))
    dv3 = DataValidation(type="decimal", operator="greaterThan", formula1="0", allow_blank=True,
                         error="El precio cotizado debe ser un número mayor que 0 (US$).", showErrorMessage=True)
    dv3.add(rng("in:quote"))
    dv4 = DataValidation(type="date", operator="greaterThan", formula1="44927", allow_blank=True,
                         error="Escribe una fecha (dd/mm/aaaa).", showErrorMessage=True)
    dv4.add(rng("in:ordered"))
    dv4.add(rng("in:arrived"))
    for d in (dv, dv2, dv3, dv4):
        ws.add_data_validation(d)

    st = rng("in:state")
    for state, color in (("Recibido", "C6EFCE"), ("Inspeccionado OK", "A9D08E"), ("Pedido", "DDEBF7"),
                         ("En tránsito", "BDD7EE"), ("Rechazado", "FFC7CE"), ("Cotizando", "FCE4D6")):
        ws.conditional_formatting.add(st, CellIsRule(operator="equal", formula=[f'"{state}"'],
                                                     fill=PatternFill("solid", fgColor=color)))
    ws.conditional_formatting.add(rng("=price_kind"), CellIsRule(operator="equal", formula=['"Estimado"'],
                                                                  font=Font(name=FONT, color="C65911", bold=True)))
    ws.conditional_formatting.add(rng("=price_kind"), CellIsRule(operator="equal", formula=['"Cotizado"'],
                                                                  font=Font(name=FONT, color="548235", bold=True)))
    # cotización más de 20 % por encima de lo estimado → rojo
    q, e = c["in:quote"], c["precio_unit_usd"]
    ws.conditional_formatting.add(rng("in:quote"), FormulaRule(formula=[f'AND({q}{FIRST}<>"",{q}{FIRST}>1.2*{e}{FIRST})'],
                                                                fill=PatternFill("solid", fgColor="FFC7CE"),
                                                                font=Font(name=FONT, color="9C0006", bold=True)))
    ws[f"{q}{HEAD_ROW}"].comment = Comment("Precio unitario real de la cotización o factura. Si queda vacío se usa el "
                                           "estimado. En rojo si supera al estimado en más de 20 %.", "DronSwarm")
    ws[f"{c['fase_a']}{HEAD_ROW}"].comment = Comment("Fase A (validación, pedir ya): baterías, cargadores, banco de empuje, "
                                                     "2 motores, 1 ESC y 1 par de hélices de cada tipo. El resto es fase B, "
                                                     "cuando el banco confirme los motores.", "DronSwarm")
    ws[f"{c['=per_drone']}{HEAD_ROW}"].comment = Comment("Costo de los componentes de UN dron (cant. por dron × precio), "
                                                         "sin repuestos ni equipo de tierra.", "DronSwarm")
    ws.freeze_panes = f"E{FIRST}"
    ws.auto_filter.ref = f"A{HEAD_ROW}:{get_column_letter(len(COLS))}{last}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f"{HEAD_ROW}:{HEAD_ROW}"
    return last


def sheet_drone(wb, veh: str, rows, last: int):
    ws = wb.create_sheet(veh)
    items = [r for r in rows if r["dron"] == veh]
    name = "inspección, cuadricóptero" if veh == "DS-I" else "entrega 5 kg, hexacóptero"
    title(ws, f"{veh} · lista de armado de 1 dron ({name})",
          "Lo necesario para armar una unidad, sin repuestos. Los precios vienen de la hoja Compras (cotizado si hay, si no estimado).")
    heads = ["ID", "Categoría", "Descripción", "Cant.", "Precio unit. (US$)", "Subtotal (US$)", "Tipo de precio", "Estado de compra"]
    widths = [7, 16, 60, 7, 13, 13, 12, 16]
    header(ws, 4, heads)
    ws.row_dimensions[4].height = 30
    for i, w in enumerate(widths):
        ws.column_dimensions[get_column_letter(i + 1)].width = w
    ids = f"Compras!$A${FIRST}:$A${last}"

    def look(key, row):
        return f"=INDEX(Compras!${COL[key]}${FIRST}:${COL[key]}${last},MATCH($A{row},{ids},0))"
    r0 = 5
    for n, r in enumerate(items):
        row = r0 + n
        vals = [r["id"], r["categoria"], r["descripcion"], int(r["cant_por_dron"]), look("=price", row), f"=D{row}*E{row}",
                look("=price_kind", row), look("in:state", row)]
        for i, v in enumerate(vals):
            cell = ws.cell(row, i + 1, v)
            cell.font = font(color="008000" if isinstance(v, str) and v.startswith("=INDEX") else "000000")
            cell.border = BOX
            cell.alignment = Alignment(vertical="top", wrap_text=i == 2, horizontal="center" if i in (0, 3, 6, 7) else None)
            if i in (4, 5):
                cell.number_format = USD
            if n % 2:
                cell.fill = BAND_FILL
    end = r0 + len(items) - 1
    tot = end + 1
    ws.cell(tot, 3, f"TOTAL 1 {veh}").font = font(True)
    ws.cell(tot, 6, f"=SUM(F{r0}:F{end})").number_format = USD0
    ws.cell(tot, 6).font = font(True)
    for i in range(1, 9):
        ws.cell(tot, i).fill = TOTAL_FILL
        ws.cell(tot, i).border = BOX

    k = tot + 2
    ws.cell(k, 2, "Por categoría").font = font(True, NAVY, 11)
    header(ws, k + 1, ["Categoría", "", "Subtotal (US$)"], 2)
    ws.merge_cells(start_row=k + 1, start_column=2, end_row=k + 1, end_column=3)
    cats = list(dict.fromkeys(r["categoria"] for r in items))
    for j, cat in enumerate(cats):
        row = k + 2 + j
        ws.cell(row, 2, cat).font = font()
        ws.cell(row, 4, f'=SUMIFS($F${r0}:$F${end},$B${r0}:$B${end},B{row})').number_format = USD0
        ws.cell(row, 4).font = font()
    ws.freeze_panes = "A5"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def sheet_resumen(ws, rows, last: int, budgets: dict):
    title(ws, "Resumen de compras · prototipo v1",
          f"Generado el {date.today():%d/%m/%Y} desde tools/bom/gen_bom.py. Se actualiza solo al llenar la hoja Compras.")
    for col, w in zip("ABCDEF", (30, 16, 16, 14, 16, 4)):
        ws.column_dimensions[col].width = w
    c = COL
    rg = lambda key: f"Compras!${c[key]}${FIRST}:${c[key]}${last}"  # noqa: E731

    def block(row, text):
        ws.cell(row, 1, text).font = font(True, NAVY, 12)

    def money(cell, formula, bold=False, fmt=USD0):
        ws[cell] = formula
        ws[cell].number_format = fmt
        ws[cell].font = font(bold)
        ws[cell].border = BOX

    # 1. costo por dron
    block(4, "Costo de 1 dron (sin repuestos ni equipo de tierra)")
    header(ws, 5, ["Dron", "Prototipo v1", "Presupuesto S04", "Diferencia"])
    for i, veh in enumerate(("DS-I", "DS-D")):
        r = 6 + i
        ws.cell(r, 1, veh).font = font(True)
        ws.cell(r, 1).border = BOX
        money(f"B{r}", f'=SUMIFS({rg("=per_drone")},{rg("dron")},"{veh}")', True)
        money(f"C{r}", budgets[veh])
        ws[f"C{r}"].font = font(color="0000FF")
        ws[f"C{r}"].comment = Comment("Costo objetivo del modelo paramétrico del S04 (engineering/data/results/"
                                      f"{veh.lower()}_sizing.json, bom_cost_usd).", "DronSwarm")
        money(f"D{r}", f"=IF(C{r}=0,\"\",B{r}/C{r}-1)", fmt=PCT)
    ws["A8"] = ("El prototipo usa componentes de marca a precio unitario; el objetivo del S04 supone volumen, motor y "
                "electrónica propios (S17-S21). El costo de producción se recalcula en el S24.")
    ws["A8"].font = font(color=GRAY, size=9, italic=True)
    ws["A8"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells("A8:E8")
    ws.row_dimensions[8].height = 28

    # 2. flota por categoría
    block(10, f"Flota de prototipos ({FLEET_TXT}), repuestos y equipo de tierra")
    header(ws, 11, ["Categoría", "Total (US$)", "Fase A (US$)", "% del total"])
    cats = list(dict.fromkeys(r["categoria"] for r in rows))
    r = 12
    for cat in cats:
        ws.cell(r, 1, cat).font = font()
        ws.cell(r, 1).border = BOX
        money(f"B{r}", f'=SUMIFS({rg("=total")},{rg("categoria")},A{r})')
        money(f"C{r}", f'=SUMIFS({rg("=cost_a")},{rg("categoria")},A{r})')
        money(f"D{r}", f"=IF($B${12 + len(cats)}=0,\"\",B{r}/$B${12 + len(cats)})", fmt=PCT)
        r += 1
    ws.cell(r, 1, "TOTAL").font = font(True)
    for col in "ABCD":
        ws[f"{col}{r}"].fill = TOTAL_FILL
        ws[f"{col}{r}"].border = BOX
    money(f"B{r}", f"=SUM(B12:B{r - 1})", True)
    money(f"C{r}", f"=SUM(C12:C{r - 1})", True)
    money(f"D{r}", f"=IF(B{r}=0,\"\",B{r}/B{r})", True, PCT)
    total_row = r

    # 3. fases
    r += 2
    block(r, "Por fase de compra")
    header(ws, r + 1, ["Fase", "Monto (US$)", "", "Qué incluye"])
    ws.merge_cells(start_row=r + 1, start_column=4, end_row=r + 1, end_column=5)
    phases = [("A · validación (pedir ya)", f"=C{total_row}", "Baterías, cargadores, banco, 2 motores + 1 ESC + hélices por tipo"),
              ("B · flota", f"=B{total_row}-C{total_row}", "El resto, cuando el banco confirme los motores (S10)")]
    for j, (name, frm, what) in enumerate(phases):
        rr = r + 2 + j
        ws.cell(rr, 1, name).font = font()
        ws.cell(rr, 1).border = BOX
        money(f"B{rr}", frm, True)
        ws.cell(rr, 4, what).font = font(size=9)
        ws.merge_cells(start_row=rr, start_column=4, end_row=rr, end_column=5)

    # 4. avance de compras
    r += 5
    block(r, "Avance de compras")
    header(ws, r + 1, ["Estado", "Ítems", "Monto (US$)", "% del monto"])
    for j, s in enumerate(STATES):
        rr = r + 2 + j
        ws.cell(rr, 1, s).font = font()
        ws.cell(rr, 1).border = BOX
        ws[f"B{rr}"] = f'=COUNTIF({rg("in:state")},A{rr})'
        ws[f"B{rr}"].font = font()
        ws[f"B{rr}"].border = BOX
        ws[f"B{rr}"].alignment = Alignment(horizontal="center")
        money(f"C{rr}", f'=SUMIFS({rg("=total")},{rg("in:state")},A{rr})')
        money(f"D{rr}", f"=IF($B${total_row}=0,\"\",C{rr}/$B${total_row})", fmt=PCT)
    rr = r + 2 + len(STATES)
    ws.cell(rr, 1, "Ítems con precio cotizado").font = font(True)
    ws[f"B{rr}"] = f'=COUNTIF({rg("=price_kind")},"Cotizado")&" de "&COUNTA({rg("id")})'
    ws[f"B{rr}"].font = font(True)
    ws[f"B{rr}"].alignment = Alignment(horizontal="center")
    ws.cell(rr + 1, 1, "Monto aún estimado (US$)").font = font(True)
    money(f"B{rr + 1}", f'=SUMIFS({rg("=total")},{rg("=price_kind")},"Estimado")', True)
    ws.cell(rr + 2, 1, "Plazo más largo (semanas)").font = font(True)
    ws[f"B{rr + 2}"] = f'=MAX({rg("plazo_semanas")})'
    ws[f"B{rr + 2}"].font = font(True)
    ws[f"B{rr + 2}"].alignment = Alignment(horizontal="center")


def sheet_leeme(ws):
    title(ws, "Lista de compras DronSwarm · prototipo v1", "Cómo usar este libro")
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 90
    lines = [
        ("Hojas", None),
        ("Resumen", "Costo por dron, total de la flota por categoría y fase, y avance de compras. Se calcula solo."),
        ("Compras", f"Todas las líneas para la flota de prototipos ({FLEET_TXT}), con repuestos y equipo de tierra. "
                    "Aquí se registran cotizaciones y pedidos. Tiene filtros en el encabezado."),
        ("DS-I / DS-D", "Lista de armado de UNA unidad de cada dron, con su costo. Útil para revisar qué lleva cada uno."),
        ("Colores", None),
        ("Fondo amarillo", "Para llenar: precio cotizado, proveedor elegido, estado, fechas, inspección y notas."),
        ("Texto azul", "Datos de entrada del BOM (cantidades, precio estimado, plazos). Vienen de tools/bom/gen_bom.py."),
        ("Texto verde", "Valores traídos de otra hoja (DS-I / DS-D toman el precio y el estado de Compras)."),
        ("Texto negro", "Fórmulas: no editar."),
        ("Cotización en rojo", "El precio cotizado supera al estimado en más de 20 %: revisar el presupuesto."),
        ("Cómo se usa", None),
        ("1. Cotizar", "Escribe el precio unitario real en «Precio cotizado». Todos los totales pasan a usarlo y el "
                       "tipo de precio cambia de Estimado a Cotizado."),
        ("2. Pedir", "Elige el proveedor, cambia el estado a Pedido y anota la fecha. Primero la fase A (validación)."),
        ("3. Recibir", "Estado Recibido + fecha de llegada; tras la inspección de entrada "
                       "(manufacturing/bom/inspeccion_entrada.md), «Inspeccionado OK» o «Rechazado»."),
        ("Regenerar", "`.venv/bin/python tools/bom/gen_bom_xlsx.py` reconstruye el libro desde el BOM y CONSERVA las "
                      "celdas amarillas (por ID). Si cambia la selección de componentes, primero `tools/bom/gen_bom.py`."),
        ("Notas", None),
        ("Moneda y fecha", "US$, precios de octubre de 2026, sin envío, impuestos ni aranceles de importación."),
        ("Precios estimados", "Los marcados «Estimado» salen de catálogos o del modelo de costo; confirmar con cotización."),
    ]
    r = 4
    for k, v in lines:
        if v is None:
            r += 1
            ws.cell(r, 2, k).font = font(True, NAVY, 12)
        else:
            ws.cell(r, 2, k).font = font(True)
            ws.cell(r, 3, v).font = font()
            ws.cell(r, 3).alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(r, 2).alignment = Alignment(vertical="top")
        if k == "Fondo amarillo":
            ws.cell(r, 2).fill = INPUT_FILL
        elif k == "Texto azul":
            ws.cell(r, 2).font = font(True, "0000FF")
        elif k == "Texto verde":
            ws.cell(r, 2).font = font(True, "008000")
        r += 1


def main():
    rows = list(csv.DictReader(open(BOM, encoding="utf-8")))
    budgets = {v: json.loads((ROOT / f"engineering/data/results/{v.lower()}_sizing.json").read_text())["bom_cost_usd"]
               for v in ("DS-I", "DS-D")}
    inputs = saved_inputs()
    wb = Workbook()
    sheet_leeme(wb.active)
    wb.active.title = "Léeme"
    res = wb.create_sheet("Resumen")
    last = sheet_compras(wb, rows, inputs)
    sheet_drone(wb, "DS-I", rows, last)
    sheet_drone(wb, "DS-D", rows, last)
    sheet_resumen(res, rows, last, budgets)
    wb.active = 1
    for ws in wb.worksheets:
        ws.sheet_properties.tabColor = {"Léeme": "808080", "Resumen": NAVY, "Compras": "C65911"}.get(ws.title, "548235")
    wb.calculation.fullCalcOnLoad = True              # Excel recalcula todo al abrir
    wb.save(OUT)
    kept = sum(1 for v in inputs.values() if any(x not in (None, "", "Pendiente") for x in v.values()))
    print(f"{OUT} ({len(rows)} ítems, {kept} con datos del usuario conservados)")


if __name__ == "__main__":
    main()
