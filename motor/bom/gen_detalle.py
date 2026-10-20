#!/usr/bin/env python3
"""Detalle del costo de los materiales de UN motor → motor/bom/Detalle_Costo_Motor.xlsx

Versión simple para leer: cada material del motor, cuánto lleva, su precio y su peso en el costo; qué hay que comprar para
hacer el primer motor (los materiales vienen en paquetes que alcanzan para muchos); y en qué se va el costo del dron (por
qué el dron baja poco aunque el motor sea barato). Datos: lista_materiales_motor.csv y bom_prototipo_v1.csv.

    .venv/bin/python motor/bom/gen_detalle.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.bom.gen_bom_xlsx import BAND_FILL, BOX, GRAY, NAVY, TOTAL_FILL, USD, USD0, font, header, title  # noqa: E402

MOTOR_CSV = ROOT / "motor" / "bom" / "lista_materiales_motor.csv"
PROTO_CSV = ROOT / "manufacturing" / "bom" / "bom_prototipo_v1.csv"
OUT = ROOT / "motor" / "bom" / "Detalle_Costo_Motor.xlsx"
COTS = {"DS-I": ("T-Motor MN4006 KV380", 75.0, 4), "DS-D": ("MAD M6C12 KV150", 170.0, 6)}
PART = {"estator": "Estator", "rotor": "Rotor", "bobinado": "Bobinado", "mecánica": "Mecánica", "conexión": "Cables",
        "impresión": "Piezas impresas", "consumible": "Consumibles"}
COLS = [("N.º", 5), ("Parte", 13), ("Material", 58), ("Lleva el motor", 10), ("Unidad", 9), ("Precio por unidad (US$)", 11),
        ("Costo en el motor (US$)", 12), ("% del motor", 9), ("", 2), ("Se compra como", 26), ("Precio del paquete (US$)", 11),
        ("Paquetes para el 1.er motor", 10), ("Gasto para el 1.er motor (US$)", 12), ("Alcanza para (motores)", 10)]


def short(desc: str) -> str:
    return desc.split(" (")[0] if len(desc) > 90 else desc


def motor_sheet(wb, veh: str, rows: list[dict]) -> int:
    ws = wb.create_sheet(f"Motor {veh}")
    name, price, n = COTS[veh]
    title(ws, f"Materiales de un motor {veh}", f"Lo que lleva UN motor y cuánto cuesta. Se compara con el {name} (US${price:.0f}).")
    header(ws, 4, [c for c, _ in COLS])
    ws.row_dimensions[4].height = 42
    for i, (_, w) in enumerate(COLS):
        ws.column_dimensions[get_column_letter(i + 1)].width = w
    mine = [r for r in rows if r["motor"] in (veh, "común")]
    first, last = 5, 4 + len(mine)
    for k, r in enumerate(mine):
        row = 5 + k
        uso, per, pk = float(r["uso"]), float(r["por_presentacion"]), float(r["precio"])
        vals = [k + 1, PART.get(r["categoria"], r["categoria"]), short(r["descripcion"]), uso, r["unidad"], f"=K{row}/{per}",
                f"=D{row}*F{row}", f"=G{row}/$G${last + 1}", None, r["presentacion"], pk, f"=ROUNDUP(D{row}/{per},0)",
                f"=L{row}*K{row}", f"=ROUND({per}/D{row},1)"]
        for j, v in enumerate(vals):
            c = ws.cell(row, j + 1, v)
            c.font = font(color="0000FF" if j in (3, 10) else "000000")
            if j != 8:
                c.border = BOX
            c.alignment = Alignment(vertical="top", wrap_text=j in (2, 9), horizontal="center" if j in (0, 3, 4, 11, 13) else None)
            if j in (5, 6, 10, 12):
                c.number_format = USD
            if j == 7:
                c.number_format = "0.0%"
            if k % 2 and j != 8:
                c.fill = BAND_FILL
    tot = last + 1
    ws.cell(tot, 3, "TOTAL DE MATERIALES DE UN MOTOR").font = font(True)
    ws.cell(tot, 7, f"=SUM(G{first}:G{last})").number_format = USD
    ws.cell(tot, 8, f"=SUM(H{first}:H{last})").number_format = "0%"
    ws.cell(tot, 10, "GASTO PARA HACER EL PRIMERO").font = font(True)
    ws.cell(tot, 13, f"=SUM(M{first}:M{last})").number_format = USD0
    for j in (1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14):
        ws.cell(tot, j).fill = TOTAL_FILL
        ws.cell(tot, j).border = BOX
        ws.cell(tot, j).font = font(True)
    s = tot + 2
    lines = [("Material de un motor propio", f"=G{tot}", USD),
             (f"Motor comercial ({name})", price, USD),
             ("El propio cuesta", f"=G{tot}/C{s + 1}", "0%"),
             ("Ahorro por motor", f"=C{s + 1}-C{s}", USD),
             (f"Ahorro por dron ({n} motores)", f"=C{s + 3}*{n}", USD0)]
    ws.cell(s - 1, 2, "Resumen").font = font(True, NAVY, 11)
    for i, (lab, val, fmt) in enumerate(lines):
        ws.cell(s + i, 2, lab).font = font(i in (0, 4))
        ws.merge_cells(start_row=s + i, start_column=2, end_row=s + i, end_column=2)
        c = ws.cell(s + i, 3, val)
        c.number_format = fmt
        c.font = font(i in (0, 4), color="0000FF" if i == 1 else "000000")
        c.border = BOX
    ws.cell(s + 6, 2, ("Los materiales se compran en paquetes (una plancha de acero da para 1-2 motores, un lote de 200 imanes para 7, "
                       "una bobina de alambre para 20…): el primer motor necesita ese gasto, pero los siguientes salen casi solo con "
                       "lo que sobra. Las herramientas (≈ US$115) se compran una vez y están aparte.")).font = font(color=GRAY, size=9, italic=True)
    ws.merge_cells(start_row=s + 6, start_column=2, end_row=s + 6, end_column=13)
    ws.row_dimensions[s + 6].height = 30
    ws.cell(s + 6, 2).alignment = Alignment(wrap_text=True, vertical="top")
    # gráfico: costo por material
    ch = BarChart()
    ch.type = "bar"
    ch.title = f"Costo de cada material en un motor {veh} (US$)"
    ch.style = 10
    ch.y_axis.title = "US$"
    data = Reference(ws, min_col=7, min_row=4, max_row=last)
    cats = Reference(ws, min_col=1, min_row=5, max_row=last)
    ch.add_data(data, titles_from_data=True)
    ch.set_categories(cats)
    ch.legend = None
    ch.height, ch.width = 9, 16
    ch.series[0].graphicalProperties.solidFill = "2A78D6"
    ws.add_chart(ch, f"E{s + 8}")
    ws.freeze_panes = "D5"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    return tot


def drone_sheet(wb, proto: list[dict], tots: dict) -> None:
    ws = wb.create_sheet("Por qué el dron baja poco")
    title(ws, "En qué se va el costo de un dron", "Los motores son una parte del dron: abaratarlos baja ese pedazo, no el resto.")
    for col, w in zip("ABCDEFG", (24, 15, 15, 15, 12, 12, 4)):
        ws.column_dimensions[col].width = w
    r = 4
    for veh in ("DS-I", "DS-D"):
        name, price, n = COTS[veh]
        ws.cell(r, 1, f"Un {veh}").font = font(True, NAVY, 12)
        header(ws, r + 1, ["Categoría", "Con motor comercial (US$)", "Con motor propio (US$)", "Diferencia (US$)", "% del dron (comercial)",
                           "% del dron (propio)"])
        cats = {}
        for p in proto:
            if p["dron"] != veh:
                continue
            cat = "motores" if p["descripcion"].startswith("Motor ") else p["categoria"]
            cats[cat] = cats.get(cat, 0.0) + float(p["cant_por_dron"]) * float(p["precio_unit_usd"])
        start = r + 2
        for i, (cat, val) in enumerate(sorted(cats.items(), key=lambda kv: -kv[1])):
            row = start + i
            ws.cell(row, 1, cat).font = font(cat == "motores")
            ws.cell(row, 2, round(val, 2)).number_format = USD0
            own = f"={n}*'Motor {veh}'!G{tots[veh]}" if cat == "motores" else f"=B{row}"
            ws.cell(row, 3, own).number_format = USD0
            ws.cell(row, 4, f"=C{row}-B{row}").number_format = USD0
            for k in (1, 2, 3, 4, 5, 6):
                ws.cell(row, k).border = BOX
                if cat == "motores":
                    ws.cell(row, k).fill = TOTAL_FILL
        end = start + len(cats) - 1
        tot = end + 1
        ws.cell(tot, 1, "TOTAL DEL DRON").font = font(True)
        for col in "BCD":
            ws[f"{col}{tot}"] = f"=SUM({col}{start}:{col}{end})"
            ws[f"{col}{tot}"].number_format = USD0
            ws[f"{col}{tot}"].font = font(True)
        for row in range(start, end + 1):
            ws.cell(row, 5, f"=B{row}/$B${tot}").number_format = "0%"
            ws.cell(row, 6, f"=C{row}/$C${tot}").number_format = "0%"
        ws.cell(tot, 5, f"=D{tot}/B{tot}").number_format = "0%"
        ws.cell(tot + 1, 1, (f"Los {n} motores pasan de US${n * price:,.0f} a lo que indica la fila «motores»; el resto del dron (aviónica, "
                             "batería, frame, cámara) no cambia.")).font = font(color=GRAY, size=9, italic=True)
        r = tot + 4


def main() -> None:
    rows = list(csv.DictReader(open(MOTOR_CSV, encoding="utf-8")))
    proto = list(csv.DictReader(open(PROTO_CSV, encoding="utf-8")))
    wb = Workbook()
    wb.remove(wb.active)
    tots = {v: motor_sheet(wb, v, rows) for v in ("DS-I", "DS-D")}
    drone_sheet(wb, proto, tots)
    wb.calculation.fullCalcOnLoad = True
    wb.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
