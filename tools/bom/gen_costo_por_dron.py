#!/usr/bin/env python3
"""Costo de UN dron (DS-I y DS-D), componente por componente → manufacturing/bom/Costo_por_Dron.xlsx

Desde la BOM del prototipo (bom_prototipo_v1.csv, cantidades por dron) con dos columnas: con motores comerciales y con
motores propios (material de un motor propio: motor/bom/lista_materiales_motor.csv). Sin repuestos ni equipo de tierra.

    .venv/bin/python tools/bom/gen_costo_por_dron.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.bom.gen_bom_xlsx import BAND_FILL, BOX, GRAY, NAVY, TOTAL_FILL, USD, USD0, font, header, title  # noqa: E402

PROTO = ROOT / "manufacturing" / "bom" / "bom_prototipo_v1.csv"
MOTOR = ROOT / "motor" / "bom" / "lista_materiales_motor.csv"
OUT = ROOT / "manufacturing" / "bom" / "Costo_por_Dron.xlsx"
NAMES = {"DS-I": "DS-I · inspección (cuadricóptero, 4 motores)", "DS-D": "DS-D · entrega 5 kg (hexacóptero, 6 motores)"}


def own_motor_cost(veh: str) -> float:
    rows = list(csv.DictReader(open(MOTOR, encoding="utf-8")))
    return round(sum(float(r["uso"]) / float(r["por_presentacion"]) * float(r["precio"]) for r in rows if r["motor"] in (veh, "común")), 2)


def drone_sheet(wb, veh: str, rows: list[dict], own: float) -> tuple[int, int]:
    ws = wb.create_sheet(veh)
    title(ws, f"Costo de un {NAMES[veh]}", "Componentes de UN dron (sin repuestos ni equipo de tierra). Precios de compra unitaria, oct. 2026.")
    cols = [("Categoría", 13), ("Componente", 64), ("Cantidad en el dron", 10), ("Precio unitario (US$)", 12),
            ("Con motores comerciales (US$)", 14), ("Con motores propios (US$)", 14)]
    header(ws, 4, [c for c, _ in cols])
    ws.row_dimensions[4].height = 42
    for i, (_, w) in enumerate(cols):
        ws.column_dimensions["ABCDEF"[i]].width = w
    mine = sorted([r for r in rows if r["dron"] == veh], key=lambda r: (r["categoria"], -float(r["cant_por_dron"]) * float(r["precio_unit_usd"])))
    first = 5
    for k, r in enumerate(mine):
        row = first + k
        is_motor = r["descripcion"].startswith("Motor ")
        desc = r["descripcion"].replace(" (fase A: 2 para el banco)", "").replace(" (fase A: 2 para el banco)", "")
        vals = [r["categoria"], desc, float(r["cant_por_dron"]), float(r["precio_unit_usd"]), f"=C{row}*D{row}",
                f"=C{row}*{own}" if is_motor else f"=E{row}"]
        for j, v in enumerate(vals):
            c = ws.cell(row, j + 1, v)
            c.border = BOX
            c.font = font(is_motor, color="0000FF" if j in (2, 3) else "000000")
            if j >= 3:
                c.number_format = USD
            if j == 2:
                c.alignment = Alignment(horizontal="center")
            if j == 1:
                c.alignment = Alignment(wrap_text=True, vertical="top")
            if is_motor:
                c.fill = TOTAL_FILL
            elif k % 2:
                c.fill = BAND_FILL
        if is_motor:
            ws.cell(row, 6).comment = Comment(f"Material de un motor propio {veh}: US${own:.2f} (motor/bom/Detalle_Costo_Motor.xlsx).", "DronSwarm")
    last = first + len(mine) - 1
    tot = last + 1
    ws.cell(tot, 2, f"TOTAL DE UN {veh}").font = font(True)
    for col in "EF":
        ws[f"{col}{tot}"] = f"=SUM({col}{first}:{col}{last})"
        ws[f"{col}{tot}"].number_format = USD0
        ws[f"{col}{tot}"].font = font(True)
    for col in "ABCDEF":
        ws[f"{col}{tot}"].fill = TOTAL_FILL
        ws[f"{col}{tot}"].border = BOX
    ws.cell(tot + 1, 2, "Ahorro con motores propios").font = font(True)
    ws.cell(tot + 1, 6, f"=E{tot}-F{tot}").number_format = USD0
    ws.cell(tot + 1, 6).font = font(True)
    ws.cell(tot + 3, 2, ("Fila resaltada = motores. Los precios de impresión y corte del frame son de servicio; con la impresora "
                         "propia baja a solo el filamento.")).font = font(color=GRAY, size=9, italic=True)
    ws.freeze_panes = "C5"
    return first, last


def main() -> None:
    rows = list(csv.DictReader(open(PROTO, encoding="utf-8")))
    wb = Workbook()
    res = wb.active
    res.title = "Resumen"
    rng = {}
    own = {v: own_motor_cost(v) for v in ("DS-I", "DS-D")}
    for veh in ("DS-I", "DS-D"):
        rng[veh] = drone_sheet(wb, veh, rows, own[veh])
    title(res, "Costo por dron", "Un dron completo, por categoría. Detalle componente por componente en las hojas DS-I y DS-D.")
    for col, w in zip("ABCDEF", (24, 16, 16, 16, 14, 4)):
        res.column_dimensions[col].width = w
    r = 4
    cats = ["aviónica", "propulsión", "batería", "frame y kits"]
    for veh in ("DS-I", "DS-D"):
        f, lst = rng[veh]
        sh = f"'{veh}'"                                   # nombre de hoja con guion: va entre comillas en las fórmulas
        res.cell(r, 1, NAMES[veh]).font = font(True, NAVY, 12)
        header(res, r + 1, ["Categoría", "Motores comerciales", "Motores propios", "Diferencia", "% (comerciales)"])
        s = r + 2
        items = [("motores", f'=SUMIFS({sh}!$E${f}:$E${lst},{sh}!$B${f}:$B${lst},"Motor *")',
                  f'=SUMIFS({sh}!$F${f}:$F${lst},{sh}!$B${f}:$B${lst},"Motor *")')]
        for cat in cats:
            extra_e = f'-SUMIFS({sh}!$E${f}:$E${lst},{sh}!$B${f}:$B${lst},"Motor *")' if cat == "propulsión" else ""
            extra_f = f'-SUMIFS({sh}!$F${f}:$F${lst},{sh}!$B${f}:$B${lst},"Motor *")' if cat == "propulsión" else ""
            label = "ESC y hélices" if cat == "propulsión" else cat
            items.append((label, f'=SUMIFS({sh}!$E${f}:$E${lst},{sh}!$A${f}:$A${lst},"{cat}"){extra_e}',
                          f'=SUMIFS({sh}!$F${f}:$F${lst},{sh}!$A${f}:$A${lst},"{cat}"){extra_f}'))
        for i, (lab, e, fo) in enumerate(items):
            row = s + i
            res.cell(row, 1, lab).font = font(lab == "motores")
            res.cell(row, 2, e).number_format = USD0
            res.cell(row, 3, fo).number_format = USD0
            res.cell(row, 4, f"=C{row}-B{row}").number_format = USD0
            for k in (1, 2, 3, 4, 5):
                res.cell(row, k).border = BOX
                if lab == "motores":
                    res.cell(row, k).fill = TOTAL_FILL
        e_ = s + len(items) - 1
        t = e_ + 1
        res.cell(t, 1, "TOTAL DEL DRON").font = font(True)
        for col in "BCD":
            res[f"{col}{t}"] = f"=SUM({col}{s}:{col}{e_})"
            res[f"{col}{t}"].number_format = USD0
            res[f"{col}{t}"].font = font(True)
            res[f"{col}{t}"].border = BOX
        for row in range(s, e_ + 1):
            res.cell(row, 5, f"=B{row}/$B${t}").number_format = "0%"
        res.cell(t, 5, f"=D{t}/B{t}").number_format = "0%"
        r = t + 3
    res.cell(r, 1, ("Un dron, sin repuestos ni equipo de tierra (radiocontrol, cargadores, banco). La flota de prototipos "
                    "(4 DS-I + 2 DS-D + repuestos + tierra) está en Lista_de_Compras_Prototipo_v1.xlsx.")).font = font(color=GRAY, size=9, italic=True)
    wb.calculation.fullCalcOnLoad = True
    wb.save(OUT)
    print(OUT, own)


if __name__ == "__main__":
    main()
