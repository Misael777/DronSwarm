#!/usr/bin/env python3
"""Genera el plan de trabajo de DronSwarm:

- docs/plan/DronSwarm_Plan_de_Trabajo.xlsx  (seguimiento de progreso, para el equipo)
- docs/plan/PLAN_DE_TRABAJO.md              (guía técnica para el agente de IA)

Uso:
    python tools/plan/generar_plan_trabajo.py                          # regenera ambos conservando el progreso
    python tools/plan/generar_plan_trabajo.py --set S01-01=Hecho:4     # Estado[:horas reales]
    python tools/plan/generar_plan_trabajo.py --set "S01-04=En curso:12:0.6"   # Estado:horas:%avance
    python tools/plan/generar_plan_trabajo.py --note "S01-05=texto"    # nota de una tarea
    python tools/plan/generar_plan_trabajo.py --reset                  # Excel desde cero (BORRA el progreso)

El progreso son las celdas editables (amarillas) del Excel: se leen antes de regenerar y se vuelven a
escribir en la fila con la misma clave (ID de tarea, Gate, parámetro, componente...). No editar el Excel
con openpyxl directamente: openpyxl no conserva los gráficos al guardar.
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule, DataBarRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.properties import CalcProperties
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_data as D  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "docs" / "plan"
XLSX = OUT_DIR / "DronSwarm_Plan_de_Trabajo.xlsx"
MD = OUT_DIR / "PLAN_DE_TRABAJO.md"

MAX_ROW = 400  # rango de tareas usado en las fórmulas (deja espacio para agregar tareas)
N_SPR = len(D.SPRINTS)
SPR_LAST = N_SPR + 1

FONT = "Arial"
C_PRIMARY = "1A365D"
C_HEADER = "2C5282"
C_ALT = "EBF8FF"
C_INPUT = "FFF9C4"
BLUE = "0000FF"
GREEN = "008000"

THIN = Side(style="thin", color="A0AEC0")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)

STATES = ["Pendiente", "En curso", "En revisión", "Bloqueado", "Hecho"]


def phase_label(code):
    return f"{code} - {dict(D.PHASES)[code]}"


def font(**kw):
    kw.setdefault("name", FONT)
    kw.setdefault("size", 10)
    return Font(**kw)


def put(ws, ref, value, *, bold=False, color=None, fill=None, fmt=None, align=WRAP, border=True, size=10):
    c = ws[ref]
    c.value = value
    c.font = font(bold=bold, color=color, size=size)
    if fill:
        c.fill = PatternFill("solid", fgColor=fill)
    if fmt:
        c.number_format = fmt
    if align:
        c.alignment = align
    if border:
        c.border = BORDER
    return c


def inp(ws, ref, value, fmt=None):
    """Celda de entrada: texto azul sobre fondo amarillo."""
    return put(ws, ref, value, color=BLUE, fill=C_INPUT, fmt=fmt)


def header(ws, row, titles, widths=None):
    for i, t in enumerate(titles, start=1):
        c = ws.cell(row=row, column=i, value=t)
        c.font = font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=C_HEADER)
        c.alignment = CENTER
        c.border = BORDER
    if widths:
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
    ws.row_dimensions[row].height = 32


def title(ws, text, sub=None):
    put(ws, "A1", text, bold=True, color=C_PRIMARY, size=14, border=False, align=None)
    if sub:
        put(ws, "A2", sub, color="4A5568", border=False, align=None)


def band(ws, row, ncols):
    if row % 2 == 1:
        for col in range(1, ncols + 1):
            c = ws.cell(row=row, column=col)
            if c.fill is None or c.fill.fgColor.rgb in (None, "00000000"):
                c.fill = PatternFill("solid", fgColor=C_ALT)


def list_validation(ws, values, rng):
    dv = DataValidation(type="list", formula1='"' + ",".join(values) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(rng)


# ---------------------------------------------------------------------------
# Hojas
# ---------------------------------------------------------------------------

def sheet_instrucciones(wb):
    ws = wb.active
    ws.title = "Instrucciones"
    title(ws, f"{D.PROJECT} · Plan de trabajo por sprints", "Del diseño a la fabricación: drones de inspección (DS-I) y delivery (DS-D) para minería")
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 100
    rows = [
        ("Objetivo", "Llegar a un producto de calidad y de bajo costo, con planos, manuales de fabricación y ensamble, BOM, costos (incluida la fabricación de motores) y presupuestos, para competir con DJI M4E y M400."),
        ("Cómo usar", "1) En 'Tareas' actualiza Estado, % avance, Horas reales y Fecha fin real. 2) 'Sprints' y 'Dashboard' se calculan solos. 3) En 'Hitos' registra la decisión de cada Gate. 4) En las hojas de costos reemplaza estimaciones por costos reales cuando compres."),
        ("Celdas editables", "Fondo amarillo + texto azul = dato que tú ingresas o supuesto que puedes cambiar."),
        ("Celdas calculadas", "Texto negro = fórmula. No escribir encima."),
        ("Vínculos", "Texto verde = valor traído de otra hoja."),
        ("Estados de tarea", "Pendiente → En curso → En revisión → Hecho. 'Bloqueado' si algo externo impide avanzar (anota el motivo en Notas)."),
        ("Avance efectivo", "Hecho = 100 %, Pendiente = 0 %; en otros estados se usa el % avance que ingreses. El avance de sprint y fase se pondera por horas estimadas."),
        ("Ejemplo", "Tarea S01-04 en curso a la mitad: Estado = 'En curso', % avance = 50 %, Horas reales = 9. Al terminar: Estado = 'Hecho', Fecha fin real = la fecha del día."),
        ("Avance esperado", "Fracción del tiempo del sprint transcurrida a hoy. Desviación = avance real − esperado; en rojo si va más de 15 puntos atrasado."),
        ("Fechas", "Se calculan desde 'Fecha de inicio Sprint 1' y 'Duración del sprint' en el Dashboard. Cambia esos valores y todo el calendario se mueve."),
        ("Costos", "Valores en USD estimados (precios de mercado de componentes, 2026) a validar con cotizaciones reales en los sprints indicados. Benchmarks DJI: fichas técnicas y cotizaciones Prizma Drones del 13/05/2026 en el repo."),
        ("Fuente", "Este Excel lo genera tools/plan/generar_plan_trabajo.py. Al regenerarlo se conservan las celdas amarillas (el progreso); solo --reset lo borra."),
    ]
    for i, (k, v) in enumerate(rows, start=4):
        put(ws, f"A{i}", k, bold=True)
        put(ws, f"B{i}", v)
        ws.row_dimensions[i].height = 42
    put(ws, "A17", "Ejemplo editable", bold=True)
    inp(ws, "B17", "Celda de entrada (así se ven)")


def sheet_dashboard(wb):
    ws = wb.create_sheet("Dashboard")
    title(ws, f"{D.PROJECT} · Dashboard de progreso", "Se actualiza automáticamente con la hoja Tareas")
    for col, w in zip("ABCDEFGHIJ", [2, 36, 18, 2, 40, 12, 12, 10, 10, 2]):
        ws.column_dimensions[col].width = w

    put(ws, "B3", "Parámetros", bold=True, color=C_PRIMARY, border=False, align=None)
    put(ws, "B4", "Fecha de inicio Sprint 1")
    inp(ws, "C4", date(*D.START_DATE), fmt="DD/MM/YYYY")
    put(ws, "B5", "Duración del sprint (días)")
    inp(ws, "C5", D.SPRINT_DAYS)
    put(ws, "B6", "Capacidad del equipo (h/sprint)")
    inp(ws, "C6", D.CAPACITY_H)
    ws["C6"].comment = Comment("Supuesto: ~1 persona a tiempo completo. Ajustar al equipo real.", "Plan")
    put(ws, "B7", "Tipo de cambio (PEN por USD)")
    inp(ws, "C7", 3.75, fmt="0.00")
    ws["C7"].comment = Comment("Supuesto. Actualizar con el tipo de cambio SBS del día.", "Plan")

    put(ws, "B9", "Indicadores", bold=True, color=C_PRIMARY, border=False, align=None)
    r = MAX_ROW
    kpis = [
        ("Avance global (ponderado por horas)", f"=IFERROR(SUMPRODUCT(Tareas!$I$2:$I${r},Tareas!$M$2:$M${r})/SUM(Tareas!$I$2:$I${r}),0)", "0.0%"),
        ("Avance esperado a hoy", f"=IFERROR(SUMPRODUCT(Sprints!$G$2:$G${SPR_LAST},Sprints!$N$2:$N${SPR_LAST})/SUM(Sprints!$G$2:$G${SPR_LAST}),0)", "0.0%"),
        ("Desviación (real − esperado)", "=C10-C11", "+0.0%;-0.0%;0.0%"),
        ("Sprint actual", f'=IF(TODAY()<Sprints!$E$2,"Aún no inicia",IF(TODAY()>Sprints!$F${SPR_LAST},"Plan finalizado",INDEX(Sprints!$A$2:$A${SPR_LAST},MATCH(TODAY(),Sprints!$E$2:$E${SPR_LAST},1))))', None),
        ("Tareas totales", f"=COUNTA(Tareas!$A$2:$A${r})", "0"),
        ("Tareas hechas", f'=COUNTIF(Tareas!$K$2:$K${r},"Hecho")', "0"),
        ("Tareas en curso / en revisión", f'=COUNTIF(Tareas!$K$2:$K${r},"En curso")+COUNTIF(Tareas!$K$2:$K${r},"En revisión")', "0"),
        ("Tareas bloqueadas", f'=COUNTIF(Tareas!$K$2:$K${r},"Bloqueado")', "0"),
        ("Tareas atrasadas", f'=COUNTIF(Tareas!$R$2:$R${r},"Atrasada")', "0"),
        ("Horas planificadas", f"=SUM(Tareas!$I$2:$I${r})", "#,##0"),
        ("Horas reales", f"=SUM(Tareas!$N$2:$N${r})", "#,##0"),
        ("Fin planificado del plan", f"=MAX(Sprints!$F$2:$F${SPR_LAST})", "DD/MM/YYYY"),
        ("Costo BOM DS-I (USD)", "=BOM_Costos!I_TOTAL", "$#,##0"),
        ("Costo BOM DS-D (USD)", "=BOM_Costos!J_TOTAL", "$#,##0"),
        ("Presupuesto del proyecto (USD)", "=Presupuesto!G_TOTAL", "$#,##0"),
    ]
    for i, (label, f, fmt) in enumerate(kpis, start=10):
        put(ws, f"B{i}", label)
        green = "!" in f and "Tareas" not in f and "Sprints" not in f
        put(ws, f"C{i}", f, fmt=fmt, color=GREEN if green else None, bold=i in (10, 13))
    ws.conditional_formatting.add("C12", CellIsRule(operator="lessThan", formula=["-0.15"], font=Font(name=FONT, color="C53030", bold=True)))

    put(ws, "E9", "Avance por fase", bold=True, color=C_PRIMARY, border=False, align=None)
    for col, t in zip("EFGHI", ["Fase", "Horas", "% avance", "Tareas", "Hechas"]):
        put(ws, f"{col}10", t, bold=True, color="FFFFFF", fill=C_HEADER, align=CENTER)
    for i, (code, _) in enumerate(D.PHASES, start=11):
        put(ws, f"E{i}", phase_label(code))
        put(ws, f"F{i}", f"=SUMIFS(Tareas!$I$2:$I${r},Tareas!$C$2:$C${r},E{i})", fmt="#,##0")
        put(ws, f"G{i}", f"=IFERROR(SUMPRODUCT((Tareas!$C$2:$C${r}=E{i})*Tareas!$I$2:$I${r}*Tareas!$M$2:$M${r})/F{i},0)", fmt="0%")
        put(ws, f"H{i}", f"=COUNTIF(Tareas!$C$2:$C${r},E{i})", fmt="0")
        put(ws, f"I{i}", f'=COUNTIFS(Tareas!$C$2:$C${r},E{i},Tareas!$K$2:$K${r},"Hecho")', fmt="0")
    last = 10 + len(D.PHASES)
    ws.conditional_formatting.add(f"G11:G{last}", DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1, color="38A169"))

    chart = BarChart()
    chart.type = "col"
    chart.title = "Avance por sprint: real vs esperado"
    chart.y_axis.title = "Avance"
    chart.y_axis.scaling.min = 0
    chart.y_axis.scaling.max = 1
    chart.y_axis.numFmt = "0%"
    sp = wb["Sprints"]
    data = Reference(sp, min_col=13, max_col=14, min_row=1, max_row=SPR_LAST)
    cats = Reference(sp, min_col=1, min_row=2, max_row=SPR_LAST)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.height, chart.width = 8, 26
    ws.add_chart(chart, "B27")
    ws.freeze_panes = "A3"
    return ws


def sheet_sprints(wb):
    ws = wb.create_sheet("Sprints")
    header(ws, 1, ["Sprint", "Nombre", "Fase", "Objetivo", "Inicio", "Fin", "Horas plan", "Horas reales",
                   "Carga vs capacidad", "Tareas", "Hechas", "Bloqueadas", "% avance", "% esperado",
                   "Desviación", "Estado", "Gate"],
           [8, 36, 26, 50, 11, 11, 9, 9, 10, 7, 7, 9, 9, 10, 10, 13, 6])
    r = MAX_ROW
    for n, s in enumerate(D.SPRINTS, start=1):
        i = n + 1
        put(ws, f"A{i}", s["id"], bold=True, align=CENTER)
        put(ws, f"B{i}", s["name"])
        put(ws, f"C{i}", phase_label(s["phase"]))
        put(ws, f"D{i}", s["goal"])
        put(ws, f"E{i}", f"=Dashboard!$C$4+{n - 1}*Dashboard!$C$5", fmt="DD/MM/YY", color=GREEN, align=CENTER)
        put(ws, f"F{i}", f"=E{i}+Dashboard!$C$5-1", fmt="DD/MM/YY", align=CENTER)
        put(ws, f"G{i}", f"=SUMIFS(Tareas!$I$2:$I${r},Tareas!$B$2:$B${r},A{i})", fmt="0")
        put(ws, f"H{i}", f"=SUMIFS(Tareas!$N$2:$N${r},Tareas!$B$2:$B${r},A{i})", fmt="0")
        put(ws, f"I{i}", f"=IFERROR(G{i}/Dashboard!$C$6,0)", fmt="0%")
        put(ws, f"J{i}", f"=COUNTIF(Tareas!$B$2:$B${r},A{i})", fmt="0")
        put(ws, f"K{i}", f'=COUNTIFS(Tareas!$B$2:$B${r},A{i},Tareas!$K$2:$K${r},"Hecho")', fmt="0")
        put(ws, f"L{i}", f'=COUNTIFS(Tareas!$B$2:$B${r},A{i},Tareas!$K$2:$K${r},"Bloqueado")', fmt="0")
        put(ws, f"M{i}", f"=IFERROR(SUMPRODUCT((Tareas!$B$2:$B${r}=A{i})*Tareas!$I$2:$I${r}*Tareas!$M$2:$M${r})/G{i},0)", fmt="0%")
        put(ws, f"N{i}", f"=MAX(0,MIN(1,(TODAY()-E{i}+1)/(F{i}-E{i}+1)))", fmt="0%")
        put(ws, f"O{i}", f"=M{i}-N{i}", fmt="+0%;-0%;0%")
        put(ws, f"P{i}", f'=IF(M{i}>=1,"Completado",IF(L{i}>0,"Con bloqueos",IF(AND(TODAY()>F{i},M{i}<1),"Atrasado",IF(M{i}>0,"En curso","No iniciado"))))', align=CENTER)
        put(ws, f"Q{i}", s["gate"] or "", bold=True, align=CENTER)
        band(ws, i, 17)
    ws.conditional_formatting.add(f"O2:O{SPR_LAST}", CellIsRule(operator="lessThan", formula=["-0.15"], font=Font(name=FONT, color="C53030", bold=True)))
    ws.conditional_formatting.add(f"I2:I{SPR_LAST}", CellIsRule(operator="greaterThan", formula=["1"], font=Font(name=FONT, color="C53030", bold=True)))
    ws.conditional_formatting.add(f"M2:M{SPR_LAST}", DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1, color="38A169"))
    for txt, color in [("Completado", "C6F6D5"), ("Atrasado", "FED7D7"), ("Con bloqueos", "FEEBC8"), ("En curso", "BEE3F8")]:
        ws.conditional_formatting.add(f"P2:P{SPR_LAST}", FormulaRule(formula=[f'$P2="{txt}"'], fill=PatternFill("solid", fgColor=color)))
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:Q{SPR_LAST}"


def sheet_tareas(wb):
    ws = wb.create_sheet("Tareas")
    header(ws, 1, ["ID", "Sprint", "Fase", "Tarea", "Detalle técnico / criterio de aceptación", "Entregable (ruta en repo)",
                   "Prioridad", "Depende de", "Horas est.", "Responsable", "Estado", "% avance", "Avance efectivo",
                   "Horas reales", "Fecha fin real", "Notas", "Fin planificado", "Alerta"],
           [8, 7, 22, 34, 60, 34, 9, 14, 8, 14, 12, 9, 9, 9, 11, 28, 11, 10])
    i = 1
    for s in D.SPRINTS:
        for k, (name, detail, deliv, prio, hours, deps) in enumerate(s["tasks"], start=1):
            i += 1
            tid = f"{s['id']}-{k:02d}"
            put(ws, f"A{i}", tid, bold=True)
            put(ws, f"B{i}", s["id"], align=CENTER)
            put(ws, f"C{i}", phase_label(s["phase"]))
            put(ws, f"D{i}", name)
            put(ws, f"E{i}", detail)
            put(ws, f"F{i}", deliv)
            put(ws, f"G{i}", prio, align=CENTER)
            put(ws, f"H{i}", deps)
            put(ws, f"I{i}", hours, fmt="0", align=CENTER)
            inp(ws, f"J{i}", None)
            inp(ws, f"K{i}", "Pendiente")
            inp(ws, f"L{i}", 0, fmt="0%")
            put(ws, f"M{i}", f'=IF(K{i}="Hecho",1,IF(OR(K{i}="Pendiente",K{i}=""),0,L{i}))', fmt="0%", align=CENTER)
            inp(ws, f"N{i}", None, fmt="0")
            inp(ws, f"O{i}", None, fmt="DD/MM/YY")
            inp(ws, f"P{i}", None)
            put(ws, f"Q{i}", f"=IFERROR(INDEX(Sprints!$F$2:$F${SPR_LAST},MATCH(B{i},Sprints!$A$2:$A${SPR_LAST},0)),\"\")", fmt="DD/MM/YY", color=GREEN, align=CENTER)
            put(ws, f"R{i}", f'=IF(AND(K{i}<>"Hecho",Q{i}<>"",TODAY()>Q{i}),"Atrasada","")', align=CENTER)
    last = i
    list_validation(ws, STATES, f"K2:K{MAX_ROW}")
    list_validation(ws, ["Alta", "Media", "Baja"], f"G2:G{MAX_ROW}")
    dv = DataValidation(type="decimal", operator="between", formula1="0", formula2="1", allow_blank=True,
                        error="Ingresa un porcentaje entre 0 % y 100 %", showErrorMessage=True)
    ws.add_data_validation(dv)
    dv.add(f"L2:L{MAX_ROW}")
    colors = {"Hecho": "C6F6D5", "En curso": "BEE3F8", "En revisión": "E9D8FD", "Bloqueado": "FED7D7"}
    for txt, color in colors.items():
        ws.conditional_formatting.add(f"A2:I{MAX_ROW}", FormulaRule(formula=[f'$K2="{txt}"'], fill=PatternFill("solid", fgColor=color)))
    ws.conditional_formatting.add(f"R2:R{MAX_ROW}", FormulaRule(formula=['$R2="Atrasada"'], font=Font(name=FONT, color="C53030", bold=True)))
    ws.freeze_panes = "E2"
    ws.auto_filter.ref = f"A1:R{last}"


def sheet_hitos(wb):
    ws = wb.create_sheet("Hitos")
    title(ws, "Hitos y Gates de revisión", "Un Gate no se aprueba si sus criterios no se cumplen con evidencia")
    header(ws, 4, ["Gate", "Nombre", "Sprint", "Fecha plan", "Criterios de aprobación", "Avance del sprint",
                   "Decisión", "Fecha revisión", "Observaciones"],
           [7, 30, 8, 11, 70, 11, 22, 12, 40])
    for n, (g, name, spr, crit) in enumerate(D.GATES, start=5):
        put(ws, f"A{n}", g, bold=True, align=CENTER)
        put(ws, f"B{n}", name)
        put(ws, f"C{n}", spr, align=CENTER)
        put(ws, f"D{n}", f"=IFERROR(INDEX(Sprints!$F$2:$F${SPR_LAST},MATCH(C{n},Sprints!$A$2:$A${SPR_LAST},0)),\"\")", fmt="DD/MM/YY", color=GREEN, align=CENTER)
        put(ws, f"E{n}", crit)
        put(ws, f"F{n}", f"=IFERROR(INDEX(Sprints!$M$2:$M${SPR_LAST},MATCH(C{n},Sprints!$A$2:$A${SPR_LAST},0)),0)", fmt="0%", color=GREEN, align=CENTER)
        inp(ws, f"G{n}", "Pendiente")
        inp(ws, f"H{n}", None, fmt="DD/MM/YY")
        inp(ws, f"I{n}", None)
        ws.row_dimensions[n].height = 45
    end = 4 + len(D.GATES)
    list_validation(ws, ["Pendiente", "Aprobado", "Aprobado con observaciones", "Rechazado"], f"G5:G{end}")
    for txt, color in [("Aprobado", "C6F6D5"), ("Aprobado con observaciones", "FEFCBF"), ("Rechazado", "FED7D7")]:
        ws.conditional_formatting.add(f"A5:F{end}", FormulaRule(formula=[f'$G5="{txt}"'], fill=PatternFill("solid", fgColor=color)))


def sheet_entregables(wb):
    ws = wb.create_sheet("Entregables")
    title(ws, "Entregables del proyecto", "El estado se toma de la tarea que lo produce")
    header(ws, 4, ["ID", "Entregable", "Tipo", "Ruta en el repo", "Tarea", "Sprint", "Fecha plan", "Estado"],
           [6, 46, 13, 42, 9, 8, 11, 13])
    for n, (name, kind, path, task) in enumerate(D.DELIVERABLES, start=5):
        put(ws, f"A{n}", f"E{n - 4:02d}", bold=True)
        put(ws, f"B{n}", name)
        put(ws, f"C{n}", kind, align=CENTER)
        put(ws, f"D{n}", path)
        put(ws, f"E{n}", task, align=CENTER)
        put(ws, f"F{n}", f"=LEFT(E{n},3)", align=CENTER)
        put(ws, f"G{n}", f"=IFERROR(INDEX(Sprints!$F$2:$F${SPR_LAST},MATCH(F{n},Sprints!$A$2:$A${SPR_LAST},0)),\"\")", fmt="DD/MM/YY", color=GREEN, align=CENTER)
        put(ws, f"H{n}", f"=IFERROR(INDEX(Tareas!$K$2:$K${MAX_ROW},MATCH(E{n},Tareas!$A$2:$A${MAX_ROW},0)),\"\")", color=GREEN, align=CENTER)
    end = 4 + len(D.DELIVERABLES)
    for txt, color in [("Hecho", "C6F6D5"), ("En curso", "BEE3F8"), ("En revisión", "E9D8FD"), ("Bloqueado", "FED7D7")]:
        ws.conditional_formatting.add(f"A5:H{end}", FormulaRule(formula=[f'$H5="{txt}"'], fill=PatternFill("solid", fgColor=color)))
    ws.auto_filter.ref = f"A4:H{end}"
    ws.freeze_panes = "C5"


def sheet_targets(wb):
    ws = wb.create_sheet("Targets")
    title(ws, "Targets de desarrollo vs benchmark DJI",
          "Fuente: fichas técnicas DJI M4E y M400 (Prizma Drones) y cotizaciones 275/276 del 13/05/2026 en el repo")
    header(ws, 4, ["Parámetro", "Unidad", "DJI M4E", "DJI M400", "Target DS-I", "Target DS-D", "Justificación",
                   "Sprint verif.", "Medido DS-I", "Medido DS-D", "¿Cumple?"],
           [34, 9, 22, 22, 18, 18, 46, 9, 13, 13, 11])
    for n, row in enumerate(D.TARGETS, start=5):
        for col, v in zip("ABCDEFGH", row):
            put(ws, f"{col}{n}", v, bold=col == "A", align=CENTER if col in "BH" else WRAP)
        for col in "IJ":
            inp(ws, f"{col}{n}", None)
        inp(ws, f"K{n}", "Pendiente")
        band(ws, n, 8)
    end = 4 + len(D.TARGETS)
    list_validation(ws, ["Pendiente", "Sí", "Parcial", "No"], f"K5:K{end}")
    for txt, color in [("Sí", "C6F6D5"), ("Parcial", "FEFCBF"), ("No", "FED7D7")]:
        ws.conditional_formatting.add(f"K5:K{end}", FormulaRule(formula=[f'$K5="{txt}"'], fill=PatternFill("solid", fgColor=color)))

    q = end + 3
    put(ws, f"A{q - 1}", "Cotizaciones de referencia (lo que el cliente paga hoy)", bold=True, color=C_PRIMARY, border=False, align=None)
    for col, t in zip("ABCDEG", ["Concepto", "Moneda", "Monto", "Monto USD", "Proveedor", "Nota"]):
        put(ws, f"{col}{q}", t, bold=True, color="FFFFFF", fill=C_HEADER, align=CENTER)
    put(ws, f"F{q}", "", fill=C_HEADER)
    for k, (concept, vendor, cur, amount, note) in enumerate(D.BENCHMARK_QUOTES, start=q + 1):
        put(ws, f"A{k}", concept)
        put(ws, f"B{k}", cur, align=CENTER)
        put(ws, f"C{k}", amount, color=BLUE, fmt="#,##0.00")
        put(ws, f"D{k}", f'=IF(B{k}="PEN",C{k}/Dashboard!$C$7,C{k})', fmt="$#,##0", color=GREEN)
        put(ws, f"E{k}", vendor)
        put(ws, f"G{k}", note)
    ws.freeze_panes = "B5"


def sheet_motor(wb):
    ws = wb.create_sheet("Costo_Motor")
    title(ws, "Costo de fabricación del motor propio (por unidad, lote ≈ 100 u.)",
          "Estimación preliminar en USD; validar con cotizaciones en S17 y con tiempos reales en S19")
    header(ws, 4, ["Componente", "Cant. DS-I", "Costo unit. DS-I", "Subtotal DS-I", "Cant. DS-D", "Costo unit. DS-D", "Subtotal DS-D"],
           [42, 11, 14, 14, 11, 14, 14])
    first = 5
    for n, (name, qi, ci, qd, cd) in enumerate(D.MOTOR_COST, start=first):
        put(ws, f"A{n}", name)
        inp(ws, f"B{n}", qi, fmt="0")
        inp(ws, f"C{n}", ci, fmt="$#,##0.00")
        put(ws, f"D{n}", f"=B{n}*C{n}", fmt="$#,##0.00")
        inp(ws, f"E{n}", qd, fmt="0")
        inp(ws, f"F{n}", cd, fmt="$#,##0.00")
        put(ws, f"G{n}", f"=E{n}*F{n}", fmt="$#,##0.00")
    last = first + len(D.MOTOR_COST) - 1
    r = last + 1
    rows = [
        ("Subtotal materiales", f"=SUM(D{first}:D{last})", f"=SUM(G{first}:G{last})", "$#,##0.00", False),
        ("Merma / scrap (%)", 0.05, 0.05, "0%", True),
        ("Horas de mano de obra por motor", D.MOTOR_LABOR_H[0], D.MOTOR_LABOR_H[1], "0.00", True),
        ("Tarifa de mano de obra (USD/h)", 4.0, 4.0, "$#,##0.00", True),
        ("Overhead de taller (%)", 0.10, 0.10, "0%", True),
        ("Costo total por motor", None, None, "$#,##0.00", False),
        ("Precio de motor comercial equivalente (OEM)", D.MOTOR_OEM_PRICE[0], D.MOTOR_OEM_PRICE[1], "$#,##0.00", True),
        ("Ahorro por motor (OEM − propio)", None, None, "$#,##0.00", False),
        ("Motores por dron", 4, 6, "0", True),
        ("Ahorro por dron", None, None, "$#,##0.00", False),
    ]
    idx = {}
    for k, (label, vi, vd, fmt, is_input) in enumerate(rows, start=r):
        idx[label] = k
        put(ws, f"A{k}", label, bold=not is_input)
        for col, v in (("D", vi), ("G", vd)):
            if is_input:
                inp(ws, f"{col}{k}", v, fmt=fmt)
            elif v is not None:
                put(ws, f"{col}{k}", v, fmt=fmt, bold=True)
    s, m, h, t, o = (idx[x] for x in ["Subtotal materiales", "Merma / scrap (%)", "Horas de mano de obra por motor",
                                       "Tarifa de mano de obra (USD/h)", "Overhead de taller (%)"])
    tot, oem, sav, per, savd = (idx[x] for x in ["Costo total por motor", "Precio de motor comercial equivalente (OEM)",
                                                 "Ahorro por motor (OEM − propio)", "Motores por dron", "Ahorro por dron"])
    for col in "DG":
        put(ws, f"{col}{tot}", f"=({col}{s}*(1+{col}{m})+{col}{h}*{col}{t})*(1+{col}{o})", fmt="$#,##0.00", bold=True, fill="C6F6D5")
        put(ws, f"{col}{sav}", f"={col}{oem}-{col}{tot}", fmt="$#,##0.00;[Red]-$#,##0.00", bold=True)
        put(ws, f"{col}{savd}", f"={col}{sav}*{col}{per}", fmt="$#,##0.00;[Red]-$#,##0.00", bold=True)
    ws[f"D{t}"].comment = Comment("Supuesto: técnico en Perú ≈ S/ 15/h. Ajustar.", "Plan")
    ws[f"D{oem}"].comment = Comment("Supuesto: precio de mercado de un motor OEM chino equivalente. Validar en S17-05.", "Plan")
    note = tot + 6
    put(ws, f"A{note}", "Nota: a bajo volumen el motor propio rara vez es más barato que un OEM chino; su valor está en el control del diseño "
                        "(rendimiento en altura, sellado al polvo) y en el costo a escala. La decisión se toma con datos en el Gate G5 (S19).",
        border=False)
    ws.merge_cells(f"A{note}:G{note}")
    ws.row_dimensions[note].height = 45
    return f"D{tot}", f"G{tot}"


def sheet_bom(wb, motor_cells):
    ws = wb.create_sheet("BOM_Costos")
    title(ws, "BOM preliminar y costo unitario por modelo (USD)",
          "Costo usado = real si existe, si no el estimado. Se vuelve BOM final en S21")
    header(ws, 4, ["Categoría", "Componente", "Especificación", "Cant. DS-I", "Cant. DS-D", "Costo unit. estimado",
                   "Costo unit. real", "Costo unit. usado", "Subtotal DS-I", "Subtotal DS-D"],
           [14, 38, 28, 10, 10, 13, 13, 13, 13, 13])
    first = 5
    for n, (cat, comp, spec, qi, qd, cost) in enumerate(D.BOM, start=first):
        put(ws, f"A{n}", cat)
        put(ws, f"B{n}", comp)
        put(ws, f"C{n}", spec)
        inp(ws, f"D{n}", qi, fmt="0")
        inp(ws, f"E{n}", qd, fmt="0")
        if cost is None:
            ref = motor_cells[0] if "DS-I" in comp else motor_cells[1]
            put(ws, f"F{n}", f"=Costo_Motor!{ref}", fmt="$#,##0.00", color=GREEN)
        else:
            inp(ws, f"F{n}", cost, fmt="$#,##0.00")
        inp(ws, f"G{n}", None, fmt="$#,##0.00")
        put(ws, f"H{n}", f"=IF(G{n}>0,G{n},F{n})", fmt="$#,##0.00")
        put(ws, f"I{n}", f"=D{n}*H{n}", fmt="$#,##0.00")
        put(ws, f"J{n}", f"=E{n}*H{n}", fmt="$#,##0.00")
    last = first + len(D.BOM) - 1
    t = last + 1
    put(ws, f"B{t}", "TOTAL BOM por dron", bold=True)
    put(ws, f"I{t}", f"=SUM(I{first}:I{last})", fmt="$#,##0", bold=True, fill="C6F6D5")
    put(ws, f"J{t}", f"=SUM(J{first}:J{last})", fmt="$#,##0", bold=True, fill="C6F6D5")
    rows = [
        ("BOM objetivo (target)", 600, 1600, True, "$#,##0"),
        ("Diferencia vs objetivo", f"=I{t + 1}-I{t}", f"=J{t + 1}-J{t}", False, "$#,##0;[Red]-$#,##0"),
        ("Precio del dron DJI equivalente (sin IGV)", 4679, 8892, True, "$#,##0"),
        ("BOM como % del precio DJI", f"=IFERROR(I{t}/I{t + 3},0)", f"=IFERROR(J{t}/J{t + 3},0)", False, "0%"),
        ("Precio de venta objetivo", 1500, 3500, True, "$#,##0"),
        ("Margen bruto sobre BOM", f"=IFERROR(1-I{t}/I{t + 5},0)", f"=IFERROR(1-J{t}/J{t + 5},0)", False, "0%"),
    ]
    for k, (label, vi, vd, is_input, fmt) in enumerate(rows, start=t + 1):
        put(ws, f"B{k}", label, bold=True)
        for col, v in (("I", vi), ("J", vd)):
            (inp if is_input else lambda w, ref, val, fmt=None: put(w, ref, val, fmt=fmt, bold=True))(ws, f"{col}{k}", v, fmt=fmt)
    ws[f"I{t + 3}"].comment = Comment("DJI Matrice 4E, cotización Prizma Drones 275 (13/05/2026), sin IGV.", "Plan")
    ws[f"J{t + 3}"].comment = Comment("DJI Matrice 400, cotización Prizma Drones 276 (13/05/2026), sin IGV.", "Plan")
    ws.freeze_panes = "C5"
    return f"I{t}", f"J{t}"


def sheet_presupuesto(wb, bom_cells):
    ws = wb.create_sheet("Presupuesto")
    title(ws, "Presupuesto del proyecto de desarrollo (USD)", "Equipos, prototipos y servicios hasta el release de fabricación")
    header(ws, 4, ["Categoría", "Ítem", "Cant.", "Costo unit. estimado", "Costo unit. real", "Costo unit. usado", "Subtotal", "Sprint compra", "Nota"],
           [12, 46, 7, 14, 14, 14, 13, 10, 40])
    first = 5
    for n, (cat, item, qty, cost, spr) in enumerate(D.PROJECT_BUDGET, start=first):
        put(ws, f"A{n}", cat)
        put(ws, f"B{n}", item)
        inp(ws, f"C{n}", qty, fmt="0")
        note = ""
        if cost == "BOM_DSI":
            put(ws, f"D{n}", f"=BOM_Costos!{bom_cells[0]}", fmt="$#,##0", color=GREEN)
            note = "Costo BOM DS-I (hoja BOM_Costos)"
        elif cost == "BOM_DSD":
            put(ws, f"D{n}", f"=BOM_Costos!{bom_cells[1]}", fmt="$#,##0", color=GREEN)
            note = "Costo BOM DS-D (hoja BOM_Costos)"
        elif cost == "TRAINING":
            put(ws, f"D{n}", "=5932.24/Dashboard!$C$7", fmt="$#,##0", color=GREEN)
            note = "S/ 5,932.24 según cotizacion_capacitacion_dron.jpeg"
        else:
            inp(ws, f"D{n}", cost, fmt="$#,##0")
            note = "Estimación de mercado; validar al comprar"
        inp(ws, f"E{n}", None, fmt="$#,##0")
        put(ws, f"F{n}", f"=IF(E{n}>0,E{n},D{n})", fmt="$#,##0")
        put(ws, f"G{n}", f"=C{n}*F{n}", fmt="$#,##0")
        put(ws, f"H{n}", spr, align=CENTER)
        put(ws, f"I{n}", note)
    last = first + len(D.PROJECT_BUDGET) - 1
    s = last + 1
    put(ws, f"B{s}", "Subtotal", bold=True)
    put(ws, f"G{s}", f"=SUM(G{first}:G{last})", fmt="$#,##0", bold=True)
    put(ws, f"B{s + 1}", "Contingencia (%)", bold=True)
    inp(ws, f"F{s + 1}", 0.15, fmt="0%")
    put(ws, f"G{s + 1}", f"=G{s}*F{s + 1}", fmt="$#,##0")
    put(ws, f"B{s + 2}", "TOTAL PRESUPUESTO DE DESARROLLO", bold=True)
    put(ws, f"G{s + 2}", f"=G{s}+G{s + 1}", fmt="$#,##0", bold=True, fill="C6F6D5")
    put(ws, f"B{s + 4}", "Por categoría", bold=True, color=C_PRIMARY, border=False)
    for k, cat in enumerate(["Equipos", "Prototipos", "Servicios"], start=s + 5):
        put(ws, f"B{k}", cat)
        put(ws, f"G{k}", f'=SUMIFS(G{first}:G{last},A{first}:A{last},B{k})', fmt="$#,##0")
    ws.freeze_panes = "C5"
    return f"G{s + 2}"


def sheet_riesgos(wb):
    ws = wb.create_sheet("Riesgos")
    title(ws, "Registro de riesgos", "Severidad = Probabilidad × Impacto (1-5). Alto ≥ 15, Medio ≥ 8")
    header(ws, 4, ["ID", "Riesgo", "Probabilidad", "Impacto", "Severidad", "Nivel", "Mitigación", "Sprint", "Responsable", "Estado"],
           [6, 52, 11, 9, 10, 9, 52, 8, 14, 11])
    for n, (risk, p, i, mit, spr) in enumerate(D.RISKS, start=5):
        put(ws, f"A{n}", f"R{n - 4:02d}", bold=True)
        put(ws, f"B{n}", risk)
        inp(ws, f"C{n}", p, fmt="0")
        inp(ws, f"D{n}", i, fmt="0")
        put(ws, f"E{n}", f"=C{n}*D{n}", fmt="0", align=CENTER)
        put(ws, f"F{n}", f'=IF(E{n}>=15,"Alto",IF(E{n}>=8,"Medio","Bajo"))', align=CENTER)
        put(ws, f"G{n}", mit)
        put(ws, f"H{n}", spr, align=CENTER)
        inp(ws, f"I{n}", None)
        inp(ws, f"J{n}", "Abierto")
    end = 4 + len(D.RISKS)
    dv = DataValidation(type="whole", operator="between", formula1="1", formula2="5", allow_blank=False)
    ws.add_data_validation(dv)
    dv.add(f"C5:D{end}")
    list_validation(ws, ["Abierto", "Mitigado", "Cerrado"], f"J5:J{end}")
    for txt, color in [("Alto", "FED7D7"), ("Medio", "FEFCBF"), ("Bajo", "C6F6D5")]:
        ws.conditional_formatting.add(f"F5:F{end}", FormulaRule(formula=[f'$F5="{txt}"'], fill=PatternFill("solid", fgColor=color)))


def sheet_evaluacion(wb):
    ws = wb.create_sheet("Evaluacion")
    title(ws, "Evaluación del estado actual del proyecto", "Puntos fuertes y oportunidades de mejora (octubre 2026)")
    for col, w in zip("ABCDE", [6, 34, 70, 34, 10]):
        ws.column_dimensions[col].width = w
    put(ws, "A4", "Puntos fuertes", bold=True, color="276749", border=False, align=None, size=12)
    for col, t in zip("ABC", ["#", "Aspecto", "Detalle"]):
        put(ws, f"{col}5", t, bold=True, color="FFFFFF", fill="276749", align=CENTER)
    r = 6
    for k, (a, d) in enumerate(D.STRENGTHS, start=1):
        put(ws, f"A{r}", k, align=CENTER)
        put(ws, f"B{r}", a, bold=True)
        put(ws, f"C{r}", d)
        r += 1
    r += 1
    put(ws, f"A{r}", "Oportunidades de mejora", bold=True, color="C05621", border=False, align=None, size=12)
    r += 1
    for col, t in zip("ABCDE", ["#", "Problema", "Impacto", "Acción", "Sprint"]):
        put(ws, f"{col}{r}", t, bold=True, color="FFFFFF", fill="C05621", align=CENTER)
    r += 1
    for k, (p, imp, act, spr) in enumerate(D.IMPROVEMENTS, start=1):
        put(ws, f"A{r}", k, align=CENTER)
        put(ws, f"B{r}", p, bold=True)
        put(ws, f"C{r}", imp)
        put(ws, f"D{r}", act)
        put(ws, f"E{r}", spr, align=CENTER)
        r += 1


# Columna que identifica cada fila al conservar el progreso (por defecto la A)
KEY_COLUMN = {"Riesgos": "B", "BOM_Costos": "B", "Presupuesto": "B", "Dashboard": "B"}
SKIP_SHEETS = {"Instrucciones"}


def _is_input(cell):
    return cell.fill is not None and str(cell.fill.fgColor.rgb).upper().endswith(C_INPUT)


def collect_inputs(path):
    """{(hoja, clave, columna): valor} de todas las celdas editables del Excel existente."""
    saved = {}
    wb = load_workbook(path)
    for ws in wb.worksheets:
        if ws.title in SKIP_SHEETS:
            continue
        key_col = KEY_COLUMN.get(ws.title, "A")
        for row in ws.iter_rows():
            for c in row:
                if _is_input(c):
                    key = ws[f"{key_col}{c.row}"].value
                    if key not in (None, ""):
                        saved[(ws.title, str(key), c.column_letter)] = c.value
    return saved


def apply_inputs(wb, saved):
    applied = 0
    for ws in wb.worksheets:
        key_col = KEY_COLUMN.get(ws.title, "A")
        for row in ws.iter_rows():
            for c in row:
                if _is_input(c):
                    k = (ws.title, str(ws[f"{key_col}{c.row}"].value), c.column_letter)
                    if k in saved:
                        c.value = saved[k]
                        applied += 1
    return applied


def apply_updates(wb, updates):
    """--set ID=Estado[:horas[:avance]] → columnas K (estado), N (horas), L (% avance), O (fecha fin)."""
    ws = wb["Tareas"]
    rows = {ws[f"A{r}"].value: r for r in range(2, ws.max_row + 1)}
    for upd in updates:
        tid, _, rest = upd.partition("=")
        parts = rest.split(":")
        if tid not in rows or parts[0] not in STATES:
            raise SystemExit(f"--set inválido: {upd!r} (ID existente y estado en {STATES})")
        r = rows[tid]
        ws[f"K{r}"].value = parts[0]
        if len(parts) > 1 and parts[1]:
            ws[f"N{r}"].value = float(parts[1])
        if len(parts) > 2 and parts[2]:
            ws[f"L{r}"].value = float(parts[2])
        if parts[0] == "Hecho":
            ws[f"L{r}"].value = 1
            if ws[f"O{r}"].value is None:
                ws[f"O{r}"].value = datetime.combine(date.today(), datetime.min.time())


def apply_notes(wb, notes):
    """--note ID=texto → columna P (Notas) de la tarea."""
    ws = wb["Tareas"]
    rows = {ws[f"A{r}"].value: r for r in range(2, ws.max_row + 1)}
    for note in notes:
        tid, _, text = note.partition("=")
        if tid not in rows:
            raise SystemExit(f"--note inválido: {note!r} (ID inexistente)")
        ws[f"P{rows[tid]}"].value = text


def build_xlsx(path, saved=None, updates=(), notes=()):
    wb = Workbook()
    sheet_instrucciones(wb)
    # Sprints y Tareas deben existir antes del gráfico del Dashboard
    dash_placeholder = wb.create_sheet("Dashboard")
    sheet_sprints(wb)
    sheet_tareas(wb)
    sheet_hitos(wb)
    sheet_entregables(wb)
    sheet_targets(wb)
    motor_cells = sheet_motor(wb)
    bom_cells = sheet_bom(wb, motor_cells)
    budget_cell = sheet_presupuesto(wb, bom_cells)
    sheet_riesgos(wb)
    sheet_evaluacion(wb)

    wb.remove(dash_placeholder)
    ws = sheet_dashboard(wb)
    wb.move_sheet(ws, offset=-(len(wb.sheetnames) - 2))
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str):
                c.value = (c.value.replace("BOM_Costos!I_TOTAL", f"BOM_Costos!{bom_cells[0]}")
                                  .replace("BOM_Costos!J_TOTAL", f"BOM_Costos!{bom_cells[1]}")
                                  .replace("Presupuesto!G_TOTAL", f"Presupuesto!{budget_cell}"))
    applied = apply_inputs(wb, saved) if saved else 0
    apply_updates(wb, updates)
    apply_notes(wb, notes)
    wb.active = 1
    wb.calculation = CalcProperties(fullCalcOnLoad=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return applied


# ---------------------------------------------------------------------------
# Markdown para el agente
# ---------------------------------------------------------------------------

def build_md(path):
    start = date(*D.START_DATE)
    total_h = sum(t[4] for s in D.SPRINTS for t in s["tasks"])
    n_tasks = sum(len(s["tasks"]) for s in D.SPRINTS)
    L = []
    a = L.append
    a(f"# {D.PROJECT} · Plan de trabajo (guía para el agente)\n")
    a("> Generado por `tools/plan/generar_plan_trabajo.py` desde `tools/plan/plan_data.py`. "
      "No editar a mano: cambiar `plan_data.py` y regenerar.\n")
    a("## Cómo usar este documento\n")
    a("- **Fuente de verdad del progreso:** `docs/plan/DronSwarm_Plan_de_Trabajo.xlsx`, hoja `Tareas` "
      "(columnas `ID`, `Estado`, `% avance`). Leerla con pandas antes de proponer trabajo: "
      "`pd.read_excel(xlsx, sheet_name='Tareas')`.")
    a("- **Fuente de verdad del alcance:** este archivo (IDs `Sxx-yy` idénticos a los del Excel).")
    a("- Al terminar una tarea: crear el entregable en la ruta indicada, referenciar el ID en el commit "
      "(`[S03-04] modelo de motor BLDC`) y pedir al usuario que marque `Hecho` en el Excel (no sobrescribir el Excel).")
    a("- Respetar dependencias (`Depende de`). No empezar un sprint cuyo Gate previo no esté aprobado sin avisar.")
    a("- Convenciones del repo: ver `docs/guia-estructura-repo.md` (capas separadas, control vía PX4, "
      "docs en español y código en inglés, decisiones en `docs/decisiones.md`).\n")
    a("## Objetivo del producto\n")
    a("Dos drones de bajo costo para minería, operables en enjambre, con paquete de fabricación completo "
      "(planos, manuales de fabricación y ensamble, BOM, costeo incluido el motor propio, presupuestos):\n")
    a("- **DS-I (inspección):** compite con DJI Matrice 4E. Precio objetivo ≤ US$1,500 y BOM ≤ US$600.")
    a("- **DS-D (delivery):** compite con DJI Matrice 400. Precio objetivo ≤ US$3,500, BOM ≤ US$1,600, 5 kg a 4,500 msnm.")
    a("- **Diferenciadores:** operación garantizada a ≥ 5,000 msnm, IP54, enjambre nativo, ecosistema abierto (PX4), "
      "procesamiento sin licencias (OpenDroneMap vs DJI Terra a US$2,085/año), baterías y base RTK propias.")
    a("- **Caso de diseño:** 5,000 msnm, -15 a 45 °C, viento 12 m/s. Todo dimensionamiento se verifica en ese caso, no a nivel del mar.\n")
    a("## Estrategia de desarrollo\n")
    a("1. Definir, calcular y simular (F0-F3).")
    a("2. Diseño mecánico: el agente escribe la fuente paramétrica en OpenSCAD (`cad/openscad/`); el usuario revisa, "
      "ensambla, exporta y hace planos en FreeCAD (`cad/freecad/`). Exportar sólidos (CSG/STEP), no solo STL, para que FreeCAD pueda dibujar planos.")
    a("3. Prototipos con componentes comerciales (COTS) → software → validación de campo (F5-F7).")
    a("4. Con datos de campo se congelan las specs (Gate G4) y recién entonces se diseñan motor, electrónica y baterías propias, "
      "calidad y regulación (F8-F10). Cada componente propio debe superar al COTS (Gates G5 y G6).")
    a("5. Paquete de fabricación y comercial (F11).\n")
    a("## Targets (benchmark de las fichas DJI del repo)\n")
    a("| Parámetro | Unidad | DJI M4E | DJI M400 | Target DS-I | Target DS-D | Verifica |")
    a("|---|---|---|---|---|---|---|")
    for p, u, m4, m400, ti, td, _j, spr in D.TARGETS:
        a(f"| {p} | {u} | {m4} | {m400} | {ti} | {td} | {spr} |")
    a("")
    a("Cotizaciones de referencia: " + "; ".join(
        f"{c} = {cur} {amt:,.2f} ({v})" for c, v, cur, amt, _n in D.BENCHMARK_QUOTES) + ".\n")
    a("## Resumen del plan\n")
    end = start + timedelta(days=D.SPRINT_DAYS * N_SPR - 1)
    a(f"- {N_SPR} sprints de {D.SPRINT_DAYS} días: {start:%d/%m/%Y} → {end:%d/%m/%Y}.")
    a(f"- {n_tasks} tareas técnicas, {total_h} h estimadas (capacidad supuesta: {D.CAPACITY_H} h/sprint).\n")
    a("| Sprint | Fechas | Fase | Nombre | Horas | Gate |")
    a("|---|---|---|---|---|---|")
    for n, s in enumerate(D.SPRINTS):
        st = start + timedelta(days=D.SPRINT_DAYS * n)
        en = st + timedelta(days=D.SPRINT_DAYS - 1)
        h = sum(t[4] for t in s["tasks"])
        a(f"| {s['id']} | {st:%d/%m}–{en:%d/%m/%y} | {phase_label(s['phase'])} | {s['name']} | {h} | {s['gate'] or ''} |")
    a("")
    a("## Gates de revisión\n")
    a("| Gate | Nombre | Sprint | Criterio de aprobación |")
    a("|---|---|---|---|")
    for g, name, spr, crit in D.GATES:
        a(f"| {g} | {name} | {spr} | {crit} |")
    a("")
    a("## Sprints y tareas\n")
    for s in D.SPRINTS:
        gate = f" · Gate {s['gate']}" if s["gate"] else ""
        a(f"### {s['id']} · {s['name']}{gate}\n")
        a(f"**Fase:** {phase_label(s['phase'])} · **Objetivo:** {s['goal']}\n")
        a("| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |")
        a("|---|---|---|---|---|---|---|")
        for k, (name, detail, deliv, prio, hours, deps) in enumerate(s["tasks"], start=1):
            a(f"| {s['id']}-{k:02d} | {name} | {detail} | `{deliv}` | {prio} | {hours} | {deps or '-'} |")
        a("")
    a("## Entregables finales\n")
    for name, kind, p, task in D.DELIVERABLES:
        a(f"- **{name}** ({kind}) → `{p}` · tarea {task}")
    a("")
    a("## Riesgos principales\n")
    for risk, p, i, mit, spr in sorted(D.RISKS, key=lambda r: -r[1] * r[2]):
        a(f"- **[{p * i}]** {risk} → {mit} ({spr})")
    a("")
    a("## Evaluación del estado inicial\n")
    a("**Puntos fuertes:**\n")
    for asp, det in D.STRENGTHS:
        a(f"- **{asp}:** {det}")
    a("\n**Mejoras (y dónde se atienden):**\n")
    for prob, imp, act, spr in D.IMPROVEMENTS:
        a(f"- **{prob}:** {imp} → {act} ({spr})")
    a("")
    a("## Supuestos a validar\n")
    a("- Costos del BOM y del motor son estimaciones de mercado 2026 en USD; se reemplazan por cotizaciones reales (S09, S17, S24).")
    a("- Capacidad de 80 h/sprint (≈ 1 persona a tiempo completo); si el equipo es mayor, se pueden paralelizar F6 con F5 y F8 con F9.")
    a("- v1 cubre minería a tajo abierto; navegación subterránea sin GNSS queda para v2.")
    a("- La decisión de fabricar el motor se toma con datos en el Gate G5; si el propio no gana, el producto sale con el motor COTS.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", action="append", default=[], metavar="ID=Estado[:horas[:avance]]",
                    help="actualizar una tarea (se puede repetir)")
    ap.add_argument("--note", action="append", default=[], metavar="ID=texto", help="nota de una tarea (se puede repetir)")
    ap.add_argument("--reset", action="store_true", help="generar el Excel desde cero (BORRA el progreso registrado)")
    args = ap.parse_args()
    build_md(MD)
    print(f"MD generado: {MD}")
    saved = collect_inputs(XLSX) if XLSX.exists() and not args.reset else None
    applied = build_xlsx(XLSX, saved, args.set, args.note)
    print(f"Excel generado: {XLSX} ({applied} celdas de progreso conservadas, {len(args.set)} tareas actualizadas)")


if __name__ == "__main__":
    main()
