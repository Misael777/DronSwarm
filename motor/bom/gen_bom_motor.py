#!/usr/bin/env python3
"""M6 · Lista de compras y costo de fabricación del motor propio → motor/bom/Lista_Materiales_Motor.xlsx + .csv

Cantidades desde el diseño elegido (informes/M2_elegidos.json) y el CAD (cad/exports/motor/resumen.json). El corte láser y
la impresión 3D son en casa: solo se costea el material (y, si se quiere, la mano de obra con una tarifa por hora).
Las compras van en presentaciones reales (plancha, bobina, paquete): el libro calcula cuántas comprar para cada
escenario (1 motor, validación, flota) y el costo de material CONSUMIDO por motor.

Celdas amarillas (precio cotizado, proveedor elegido, notas) se conservan al regenerar, por ID.

    .venv/bin/python motor/bom/gen_bom_motor.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from motor.calculo.design import SHAFT, wire_choice  # noqa: E402
from tools.bom.gen_bom_xlsx import BAND_FILL, BOX, FONT, GRAY, INPUT_FILL, NAVY, TOTAL_FILL, USD, USD0, font, header, title  # noqa: E402

INF = ROOT / "motor" / "informes"
CAD = ROOT / "cad" / "exports" / "motor" / "resumen.json"
OUT_X = ROOT / "motor" / "bom" / "Lista_Materiales_Motor.xlsx"
OUT_C = ROOT / "motor" / "bom" / "lista_materiales_motor.csv"
SHEET_MM = 300                   # plancha de 300 × 300 mm
COTS_PRICE = {"DS-I": 75.0, "DS-D": 170.0}
SCEN = {"validacion": {"DS-I": 2, "DS-D": 2}, "flota": {"DS-I": 18, "DS-D": 14}}     # flota: 4×4 + 2 y 2×6 + 2 de repuesto


def per_sheet(od_mm: float, kerf: float = 2.5) -> int:
    n = int(SHEET_MM // (od_mm + kerf))
    return n * n


def wire_m(c: dict, strands: int) -> float:
    d, g = c["design"], c["geometry"]
    return round(d["ns"] * d["turns"] * g["l_turn"] * strands * 1.2 + 0.6, 1)          # +20 % de sobrante y salidas


def rows_for(veh: str, c: dict, p: dict) -> list[dict]:
    d, g = c["design"], c["geometry"]
    small = veh == "DS-I"
    pre = "I" if small else "D"
    od_lam = 2 * p["r_s"]
    od_ring = 2 * p["r_out"]
    n_mag = 2 * d["pole_pairs"]
    wire = wire_choice(g["a_cond_ideal"])
    strands = wire["strands"]
    wl = wire_m(c, strands)
    shaft_len = round(p["l_stack"] + 2 * p["overhang"] + p["cap_t"] + p["base_t"] + 12, 0)
    mag_dims = f"{p['magnet_w']:.1f} × {p['l_stack']:.1f} × {p['h_magnet']:.1f} mm"
    filament_g = round((c["mass"]["tapa impresa"] + c["mass"]["base impresa"]) * 1e3 * 1.15, 0)
    R = []

    def add(cat, desc, use, unit, pres, per_pres, price, supplier, weeks, src, est=True):
        R.append({"id": f"{pre}{len(R) + 1:02d}", "motor": veh, "categoria": cat, "descripcion": desc, "uso": use, "unidad": unit,
                  "presentacion": pres, "por_presentacion": per_pres, "precio": price, "proveedor": supplier, "plazo": weeks,
                  "fuente": src, "estimado": est})
    lam_ps = per_sheet(od_lam)
    add("estator", f"Acero al silicio no orientado 0.20 mm (NO20: B20AT1500 / 20JNEH1200), aislado C5. Láminas Ø{od_lam:.1f} mm, "
        f"{d['ns']} ranuras (cad/exports/motor/{veh.lower()}/lamina_estator.dxf)", p["n_lam"], "láminas",
        f"plancha 300×300 mm ({lam_ps} láminas)", lam_ps, 15.0, "AliExpress / distribuidor de acero eléctrico", 3,
        "estimado. Referencias 2026: RS UK, plancha 0.30 mm 300×300 a £26 (minorista); mayorista China 0.5 mm ≈ US$0.6/kg. "
        "Para la flota, cotizar 10-25 kg de 0.2 mm cortado a 300×300: puede bajar a US$1-3 por plancha")
    ring_ps = per_sheet(od_ring)
    add("rotor", f"Acero laminado en frío DC01/SPCC 1.0 mm. Anillos Ø{od_ring:.1f}/Ø{2 * p['r_mag_out']:.1f} mm "
        f"(anillo_rotor.dxf); se apilan {p['n_ring']}", p["n_ring"], "anillos", f"plancha 300×300 mm ({ring_ps} anillos)", ring_ps,
        4.0, "ferretería industrial local", 1, "estimado: chapa negra 1 mm")
    add("rotor", f"Imán de neodimio N48SH (150 °C), bloque {mag_dims} (ancho × largo × espesor), magnetizado en el espesor, "
        "níquel-cobre-níquel", n_mag + 1, "imanes", "lote de 200 piezas a medida", 200, 28.0 if small else 70.0,
        "fabricante de imanes (Ningbo/Hangzhou) o AliExpress a medida", 4, "estimado: US$0.12-0.35 por pieza; pedido mínimo 100-500")
    m_per_spool = round(0.25 / (8960 * math.pi * (wire["d_mm"] * 1e-3) ** 2 / 4))
    add("bobinado", f"Alambre esmaltado clase H (200 °C, poliéster-imida + poliamida-imida) Ø{wire['d_mm']:.2f} mm; {strands} hilos en "
        f"paralelo, {d['turns']} vueltas por diente, {'triángulo' if d['delta'] else 'estrella'}", wl, "m",
        f"bobina de 250 g (≈ {m_per_spool} m)", m_per_spool, 12.0, f"AliExpress / Amazon (magnet wire {wire['d_mm']:.2f} mm 200C)", 2,
        "estimado")
    brg = "694ZZ (4×11×4 mm)" if small else "696ZZ (6×15×5 mm)"
    add("mecánica", f"Rodamiento {brg}, preferible ABEC-5 / marca (EZO, NSK) para el lote final", 2, "u", "paquete de 10", 10,
        8.0 if small else 10.0, "AliExpress / tienda de rodamientos", 2, "estimado: genérico; EZO ≈ US$4-6 c/u")
    add("mecánica", f"Eje de acero plata (o 4140) Ø{SHAFT[veh] * 1e3:.0f} mm h6, cortado a {shaft_len:.0f} mm, con ranuras para anillo E",
        shaft_len, "mm", "barra de 330 mm", 330, 3.0 if small else 4.0, "ferretería industrial / AliExpress", 2, "estimado")
    add("mecánica", f"Anillo de retención E DIN 6799 para eje Ø{SHAFT[veh] * 1e3:.0f} mm", 2, "u", "paquete de 100", 100, 3.0,
        "ferretería", 1, "estimado")
    add("mecánica", "Prisionero M3×4 (fija la tapa al eje)", 1, "u", "paquete de 50", 50, 3.0, "ferretería", 1, "estimado")
    add("mecánica", f"Tornillos {'M3×8' if small else 'M4×10'} cabeza allen (hélice ×4 y base al soporte DMI ×4)", 8, "u",
        "paquete de 100", 100, 4.0 if small else 5.0, "ferretería", 1, "estimado")
    add("conexión", f"Cable de silicona {'18' if small else '14'} AWG (3 fases × 10 cm)", 0.3, "m", "juego de 3 m (3 colores)", 3,
        6.0 if small else 8.0, "tienda de RC / AliExpress", 2, "estimado")
    add("conexión", f"Conector bala {'3.5' if small else '5.5'} mm (macho, lado motor)", 3, "u", "10 pares", 10, 5.0 if small else 7.0,
        "tienda de RC", 2, "estimado")
    add("impresión", f"Filamento PETG para tapa y base (ASA o PA-CF para más margen térmico, ver M5); {filament_g:.0f} g por motor",
        filament_g, "g", "bobina de 1 kg", 1000, 20.0, "local", 1, "estimado")
    return R


COMMON = [
    ("consumible", "Epoxi estructural de alta temperatura (p. ej. JB Weld Original, 2 × 57 g): apilado de láminas, anillos e imanes", 4,
     "g", "kit de 114 g", 114, 9.0, "ferretería", 1),
    ("consumible", "Barniz de impregnación clase H para bobinados (p. ej. Elantas / Electrolube) 100 ml", 3, "ml", "frasco de 100 ml",
     100, 12.0, "electrónica industrial", 2),
    ("consumible", "Papel aislante Nomex 410 de 0.08 mm (forro de ranuras)", 0.08, "hoja A4", "hoja A4", 1, 3.0, "AliExpress", 3),
    ("consumible", "Cinta Kapton 10 mm (aislar salidas y cruces)", 0.4, "m", "rollo de 33 m", 33, 4.0, "electrónica", 1),
    ("consumible", "Termocontraíble surtido", 4, "piezas", "surtido de 120 piezas", 120, 5.0, "electrónica", 1),
    ("consumible", "Fijador de roscas de resistencia media (azul) 10 ml", 0.05, "ml", "frasco de 10 ml", 10, 5.0, "ferretería", 1),
    ("consumible", "Alcohol isopropílico (limpiar láminas antes de pegar) 500 ml", 10, "ml", "botella de 500 ml", 500, 5.0, "farmacia", 1),
]
TOOLS = [
    ("Medidor de miliohmios de 4 hilos (resistencia fase-fase; control de calidad)", 35.0, "opcional pero recomendado"),
    ("Pinza no magnética (titanio o plástico) para manipular imanes", 5.0, "imprescindible: los imanes saltan y se rompen"),
    ("Varilla roscada M5 de 100 mm + tuercas y arandelas (prensa del mandril de apilado)", 3.0, ""),
    ("Desbarbador / lima fina y lija 400-600 (bordes de láminas cortadas con láser)", 8.0, ""),
    ("Balanceador magnético de hélices (sirve para balancear el rotor con la tapa)", 12.0, ""),
    ("Gafas de seguridad y guantes de nitrilo (epoxi, barniz, imanes)", 8.0, "imprescindible"),
    ("Brújula o visor de campo magnético (verificar la polaridad alternada de los imanes)", 3.0, "imprescindible"),
]
PROCESS = [
    ("Cortar las láminas del estator (láser de fibra, desatendido)", 20, 37, "láser"),
    ("Desbarbar y limpiar las láminas con alcohol", 15, 20, "mano"),
    ("Apilar en el mandril con la chaveta, pegar con epoxi fino y prensar; curar 24 h", 15, 20, "mano"),
    ("Aislar el estator: barniz en los bordes y papel Nomex en las ranuras", 20, 30, "mano"),
    ("Bobinar los dientes con el soporte de bobinado (orden de fases en el CAD: variable 'coils')", 90, 150, "mano"),
    ("Conectar las fases (triángulo/estrella), soldar los cables y aislar", 20, 25, "mano"),
    ("Impregnar el bobinado con barniz y curar", 10, 15, "mano"),
    ("Cortar y apilar los anillos del rotor; pegar con epoxi", 15, 20, "láser + mano"),
    ("Pegar los imanes con la plantilla, polaridad alternada (verificar con la brújula); curar", 30, 40, "mano"),
    ("Imprimir tapa y base (desatendido)", 90, 240, "impresora"),
    ("Ensamblar: rodamientos en la base, estator al tubo, eje, tapa y anillos E", 20, 25, "mano"),
    ("Balancear el rotor y control de calidad: R fase-fase, I0 y Kv con el ESC, giro sin roces", 20, 25, "mano"),
]

COLS = [("ID", 6), ("Motor", 8), ("Categoría", 12), ("Descripción / especificación", 58), ("Uso por motor", 10), ("Unidad", 9),
        ("Presentación de compra", 24), ("Cantidad por presentación", 11), ("Precio por presentación est. (US$)", 12),
        ("Precio cotizado (US$)", 12), ("Precio usado (US$)", 11), ("Material consumido por motor (US$)", 13),
        ("Validación: presentaciones", 12), ("Validación: costo (US$)", 12), ("Flota: presentaciones", 11), ("Flota: costo (US$)", 12),
        ("Proveedor sugerido", 26), ("Proveedor elegido", 18), ("Plazo (sem.)", 8), ("Fuente del precio", 30), ("Notas", 26)]
C = {h: get_column_letter(i + 1) for i, (h, _) in enumerate(COLS)}
INPUTS = ("Precio cotizado (US$)", "Proveedor elegido", "Notas")
HEAD, FIRST = 4, 5


def saved() -> dict:
    if not OUT_X.exists():
        return {}
    ws = load_workbook(OUT_X)["Materiales"]
    heads = {ws.cell(HEAD, k).value: k for k in range(1, ws.max_column + 1)}
    out = {}
    for r in range(FIRST, ws.max_row + 1):
        rid = ws.cell(r, 1).value
        if rid:
            out[rid] = {h: ws.cell(r, heads[h]).value for h in INPUTS if h in heads}
    return out


def build(rows: list[dict]) -> None:
    keep = saved()
    wb = Workbook()
    lm = wb.active
    lm.title = "Léeme"
    res = wb.create_sheet("Resumen")
    ws = wb.create_sheet("Materiales")
    tl = wb.create_sheet("Herramientas")
    pr = wb.create_sheet("Proceso")

    # --- Resumen: entradas de escenarios
    title(res, "Motor propio · costo de fabricación", f"Generado el {date.today():%d/%m/%Y} desde el diseño de M2 y el CAD de M6. "
          "Celdas azules: cantidades de motores; amarillas: tarifa de mano de obra.")
    for col, wdt in zip("ABCDEF", (36, 16, 16, 16, 16, 4)):
        res.column_dimensions[col].width = wdt
    header(res, 4, ["Escenario", "DS-I (motores)", "DS-D (motores)"])
    scen_rows = {"uno": 5, "validacion": 6, "flota": 7}
    labels = {"uno": "1 motor", "validacion": "Validación (primeros prototipos)", "flota": f"Flota ({4} DS-I × 4 + 2 · {2} DS-D × 6 + 2)"}
    for k, r in scen_rows.items():
        res.cell(r, 1, labels[k]).font = font()
        for j, veh in enumerate(("DS-I", "DS-D")):
            v = 1 if k == "uno" else SCEN[k][veh]
            cell = res.cell(r, 2 + j, v)
            cell.font = font(color="0000FF")
            cell.alignment = Alignment(horizontal="center")
            cell.border = BOX
    res["A9"] = "Mano de obra (US$/h, 0 = no se cuenta)"
    res["A9"].font = font(True)
    res["B9"] = 0
    res["B9"].fill = INPUT_FILL
    res["B9"].number_format = USD
    n_i_val, n_d_val, n_i_fl, n_d_fl = "Resumen!$B$6", "Resumen!$C$6", "Resumen!$B$7", "Resumen!$C$7"

    # --- Materiales
    title(ws, "Lista de materiales del motor propio", "Corte láser e impresión en casa: solo material. Las compras se calculan en "
          "presentaciones enteras. Celdas amarillas: para llenar.")
    header(ws, HEAD, [h for h, _ in COLS])
    ws.row_dimensions[HEAD].height = 48
    for i, (_, wdt) in enumerate(COLS):
        ws.column_dimensions[get_column_letter(i + 1)].width = wdt
    for n, r in enumerate(rows):
        row = FIRST + n
        keepr = keep.get(r["id"], {})
        q = f"{C['Precio cotizado (US$)']}{row}"
        nval = (f"IF({C['Motor']}{row}=\"DS-I\",{n_i_val},IF({C['Motor']}{row}=\"DS-D\",{n_d_val},{n_i_val}+{n_d_val}))")
        nfl = (f"IF({C['Motor']}{row}=\"DS-I\",{n_i_fl},IF({C['Motor']}{row}=\"DS-D\",{n_d_fl},{n_i_fl}+{n_d_fl}))")
        use, per, price_used = f"{C['Uso por motor']}{row}", f"{C['Cantidad por presentación']}{row}", f"{C['Precio usado (US$)']}{row}"
        vals = {"ID": r["id"], "Motor": r["motor"], "Categoría": r["categoria"], "Descripción / especificación": r["descripcion"],
                "Uso por motor": r["uso"], "Unidad": r["unidad"], "Presentación de compra": r["presentacion"],
                "Cantidad por presentación": r["por_presentacion"], "Precio por presentación est. (US$)": r["precio"],
                "Precio cotizado (US$)": keepr.get("Precio cotizado (US$)"),
                "Precio usado (US$)": f'=IF({q}="",{C["Precio por presentación est. (US$)"]}{row},{q})',
                "Material consumido por motor (US$)": f"={use}/{per}*{price_used}",
                "Validación: presentaciones": f"=ROUNDUP({use}*{nval}/{per},0)",
                "Validación: costo (US$)": f"={C['Validación: presentaciones']}{row}*{price_used}",
                "Flota: presentaciones": f"=ROUNDUP({use}*{nfl}/{per},0)",
                "Flota: costo (US$)": f"={C['Flota: presentaciones']}{row}*{price_used}",
                "Proveedor sugerido": r["proveedor"], "Proveedor elegido": keepr.get("Proveedor elegido"), "Plazo (sem.)": r["plazo"],
                "Fuente del precio": r["fuente"] + (" (estimado: cotizar)" if r["estimado"] else ""), "Notas": keepr.get("Notas")}
        for i, (h, _) in enumerate(COLS):
            cell = ws.cell(row, i + 1, vals[h])
            cell.font = font(color="0000FF" if h in ("Uso por motor", "Cantidad por presentación", "Precio por presentación est. (US$)")
                             else "000000")
            cell.border = BOX
            cell.alignment = Alignment(vertical="top", wrap_text=h in ("Descripción / especificación", "Presentación de compra",
                                                                         "Proveedor sugerido", "Fuente del precio", "Notas"),
                                       horizontal="center" if h in ("ID", "Motor", "Uso por motor", "Unidad", "Cantidad por presentación",
                                                                    "Plazo (sem.)", "Validación: presentaciones", "Flota: presentaciones")
                                       else None)
            if "US$" in h:
                cell.number_format = USD
            if h in INPUTS:
                cell.fill = INPUT_FILL
            elif n % 2:
                cell.fill = BAND_FILL
    last = FIRST + len(rows) - 1
    tot = last + 1
    ws.cell(tot, 4, "TOTAL").font = font(True)
    for h in ("Validación: costo (US$)", "Flota: costo (US$)"):
        col = C[h]
        ws[f"{col}{tot}"] = f"=SUM({col}{FIRST}:{col}{last})"
        ws[f"{col}{tot}"].number_format = USD0
        ws[f"{col}{tot}"].font = font(True)
    for i in range(1, len(COLS) + 1):
        ws.cell(tot, i).fill = TOTAL_FILL
        ws.cell(tot, i).border = BOX
    ws.freeze_panes = f"E{FIRST}"
    ws.auto_filter.ref = f"A{HEAD}:{get_column_letter(len(COLS))}{last}"
    dv = DataValidation(type="decimal", operator="greaterThan", formula1="0", allow_blank=True, showErrorMessage=True,
                        error="Precio de la presentación en US$ (> 0).")
    dv.add(f"{C['Precio cotizado (US$)']}{FIRST}:{C['Precio cotizado (US$)']}{last}")
    ws.add_data_validation(dv)
    ws[f"{C['Material consumido por motor (US$)']}{HEAD}"].comment = Comment(
        "Uso por motor ÷ cantidad por presentación × precio: lo que cuesta el material que efectivamente se usa en un motor. "
        "Lo que se compra depende del escenario (presentaciones enteras).", "DronSwarm")
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    # --- Herramientas (una vez)
    title(tl, "Herramientas y útiles (se compran una vez)", "Los útiles impresos (mandril, plantilla, soporte de bobinado) salen del CAD de M6.")
    header(tl, 4, ["Herramienta", "Precio est. (US$)", "Comentario"])
    for col, wdt in zip("ABC", (70, 14, 44)):
        tl.column_dimensions[col].width = wdt
    for i, (name, price, note) in enumerate(TOOLS):
        r = 5 + i
        tl.cell(r, 1, name).font = font()
        tl.cell(r, 2, price).font = font(color="0000FF")
        tl.cell(r, 2).number_format = USD
        tl.cell(r, 3, note).font = font(color=GRAY)
        for k in (1, 2, 3):
            tl.cell(r, k).border = BOX
    t_tot = 5 + len(TOOLS)
    tl.cell(t_tot, 1, "TOTAL").font = font(True)
    tl.cell(t_tot, 2, f"=SUM(B5:B{t_tot - 1})").number_format = USD0
    tl.cell(t_tot, 2).font = font(True)

    # --- Proceso
    title(pr, "Proceso de fabricación por motor", "Tiempos estimados de un motor (los primeros tardan más). Ver motor/fabricacion/README.md.")
    header(pr, 4, ["Paso", "DS-I (min)", "DS-D (min)", "Equipo"])
    for col, wdt in zip("ABCD", (78, 11, 11, 14)):
        pr.column_dimensions[col].width = wdt
    for i, (step, ti, td, eq) in enumerate(PROCESS):
        r = 5 + i
        pr.cell(r, 1, f"{i + 1}. {step}").font = font()
        pr.cell(r, 2, ti).font = font(color="0000FF")
        pr.cell(r, 3, td).font = font(color="0000FF")
        pr.cell(r, 4, eq).font = font(color=GRAY)
        for k in (1, 2, 3, 4):
            pr.cell(r, k).border = BOX
    p_last = 4 + len(PROCESS)
    pr.cell(p_last + 1, 1, "Mano de obra (solo pasos a mano), horas").font = font(True)
    for col in "BC":
        pr[f"{col}{p_last + 1}"] = f'=SUMIFS({col}5:{col}{p_last},$D$5:$D${p_last},"mano")/60+SUMIFS({col}5:{col}{p_last},$D$5:$D${p_last},"láser + mano")/60'
        pr[f"{col}{p_last + 1}"].number_format = "0.0"
        pr[f"{col}{p_last + 1}"].font = font(True)
    pr.cell(p_last + 2, 1, "Tiempo de máquina (láser + impresora), horas").font = font(True)
    for col in "BC":
        pr[f"{col}{p_last + 2}"] = f'=SUMIFS({col}5:{col}{p_last},$D$5:$D${p_last},"láser")/60+SUMIFS({col}5:{col}{p_last},$D$5:$D${p_last},"impresora")/60'
        pr[f"{col}{p_last + 2}"].number_format = "0.0"
    labor_i, labor_d = f"Proceso!$B${p_last + 1}", f"Proceso!$C${p_last + 1}"

    # --- Resumen: costos
    mat = "Materiales!"
    rng = lambda h: f"{mat}${C[h]}${FIRST}:${C[h]}${last}"  # noqa: E731
    res["A11"] = "Costo de un motor"
    res["A11"].font = font(True, NAVY, 12)
    header(res, 12, ["Concepto", "DS-I", "DS-D"])
    lines = [("Material consumido (propio)", lambda v: f'=SUMIFS({rng("Material consumido por motor (US$)")},{rng("Motor")},"{v}")'
              f'+SUMIFS({rng("Material consumido por motor (US$)")},{rng("Motor")},"común")'),
             ("Mano de obra (horas × tarifa)", lambda v: f"={labor_i if v == 'DS-I' else labor_d}*$B$9"),
             ("Costo de fabricación por motor", lambda v: f"=SUM({'B' if v == 'DS-I' else 'C'}13:{'B' if v == 'DS-I' else 'C'}14)"),
             ("Motor comercial que reemplaza (compra)", lambda v: COTS_PRICE[v]),
             ("Ahorro por motor", lambda v: f"={'B' if v == 'DS-I' else 'C'}16-{'B' if v == 'DS-I' else 'C'}15"),
             ("Ahorro por dron (4 o 6 motores)", lambda v: f"={'B' if v == 'DS-I' else 'C'}17*{4 if v == 'DS-I' else 6}")]
    for i, (lab, fn) in enumerate(lines):
        r = 13 + i
        res.cell(r, 1, lab).font = font(True if i in (2, 4, 5) else False)
        for j, v in enumerate(("DS-I", "DS-D")):
            cell = res.cell(r, 2 + j, fn(v))
            cell.number_format = USD
            cell.font = font(True if i in (2, 4, 5) else False, color="0000FF" if i == 3 else "000000")
            cell.border = BOX
        res.cell(r, 1).border = BOX
    res.cell(16, 2).comment = Comment("Precio de compra unitario de la BOM del prototipo (manufacturing/bom/).", "DronSwarm")
    res["A20"] = "Desembolso por escenario (compras en presentaciones enteras)"
    res["A20"].font = font(True, NAVY, 12)
    header(res, 21, ["Escenario", "Materiales (US$)", "Herramientas (US$)", "Total (US$)"])
    for i, (lab, col) in enumerate((("Validación", "Validación: costo (US$)"), ("Flota", "Flota: costo (US$)"))):
        r = 22 + i
        res.cell(r, 1, lab).font = font()
        res.cell(r, 2, f"=SUM({rng(col)})").number_format = USD0
        res.cell(r, 3, f"=Herramientas!B{t_tot}" if i == 0 else 0).number_format = USD0
        res.cell(r, 4, f"=B{r}+C{r}").number_format = USD0
        res.cell(r, 4).font = font(True)
        for k in (1, 2, 3, 4):
            res.cell(r, k).border = BOX
    res["A25"] = ("Las herramientas se compran una sola vez (con la validación). Los imanes a medida suelen tener un pedido mínimo: "
                  "el lote de 200 alcanza para la validación y buena parte de la flota.")
    res["A25"].font = font(color=GRAY, size=9, italic=True)
    res["A25"].alignment = Alignment(wrap_text=True, vertical="top")
    res.merge_cells("A25:D25")
    res.row_dimensions[25].height = 30

    # --- Léeme
    title(lm, "Motor propio DronSwarm · lista de materiales y costo", "Cómo usar este libro")
    lm.column_dimensions["A"].width = 4
    lm.column_dimensions["B"].width = 24
    lm.column_dimensions["C"].width = 92
    notes = [("Resumen", "Costo de fabricación de un motor (material consumido + mano de obra opcional), ahorro contra el comercial y "
              "desembolso de cada escenario."),
             ("Materiales", "Cada material con su uso por motor y su presentación de compra. El libro calcula cuántas presentaciones "
              "comprar en cada escenario. Filtros en el encabezado."),
             ("Herramientas", "Lo que se compra una vez. Los útiles impresos salen del CAD."),
             ("Proceso", "Pasos y tiempos de fabricación por motor."),
             ("Fondo amarillo", "Para llenar: precio cotizado (por presentación), proveedor elegido, notas, tarifa de mano de obra."),
             ("Texto azul", "Datos de entrada (cantidades, precios estimados, motores por escenario): se pueden cambiar."),
             ("Regenerar", "`.venv/bin/python motor/bom/gen_bom_motor.py` (después de M2/M6) conserva las celdas amarillas por ID."),
             ("Precios", "US$ de octubre de 2026, compra chica, sin envío ni aranceles. Todos estimados: cotizar."),
             ("Supuestos", "Láser de fibra (corta acero de 0.2-1 mm). Si es de CO₂, las láminas se mandan a cortar: sumar el servicio "
              "(≈ US$0.3-1 por lámina). Impresión en PETG (ASA o PA-CF dan más margen térmico).")]
    for i, (k, v) in enumerate(notes):
        lm.cell(4 + i, 2, k).font = font(True)
        lm.cell(4 + i, 3, v).font = font()
        lm.cell(4 + i, 3).alignment = Alignment(wrap_text=True, vertical="top")
        lm.cell(4 + i, 2).alignment = Alignment(vertical="top")
        if k == "Fondo amarillo":
            lm.cell(4 + i, 2).fill = INPUT_FILL
        if k == "Texto azul":
            lm.cell(4 + i, 2).font = Font(name=FONT, bold=True, color="0000FF")
    wb.active = 1
    for s, color in zip(wb.worksheets, ("808080", NAVY, "C65911", "548235", "548235")):
        s.sheet_properties.tabColor = color
    wb.calculation.fullCalcOnLoad = True
    wb.save(OUT_X)


def main() -> None:
    chosen = json.loads((INF / "M2_elegidos.json").read_text())
    cad = json.loads(CAD.read_text())
    rows = []
    for veh in ("DS-I", "DS-D"):
        rows += rows_for(veh, chosen[veh], cad[veh]["params"])
    for i, (cat, desc, use, unit, pres, per, price, sup, wk) in enumerate(COMMON):
        rows.append({"id": f"C{i + 1:02d}", "motor": "común", "categoria": cat, "descripcion": desc, "uso": use, "unidad": unit,
                     "presentacion": pres, "por_presentacion": per, "precio": price, "proveedor": sup, "plazo": wk,
                     "fuente": "estimado", "estimado": True})
    with open(OUT_C, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    build(rows)
    per_motor = {v: sum(r["uso"] / r["por_presentacion"] * r["precio"] for r in rows if r["motor"] in (v, "común")) for v in ("DS-I", "DS-D")}
    print(OUT_X, {k: round(x, 2) for k, x in per_motor.items()})


if __name__ == "__main__":
    main()
