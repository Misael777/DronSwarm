"""E6 · Biblioteca de huellas propias DronSwarm.pretty (piezas que no trae KiCad), desde las hojas de datos.

Se ejecuta con el Python del sistema y el módulo pcbnew de KiCad 8 (la sintaxis la escribe KiCad):
    source ~/.local/opt/kicad8/env.sh && /usr/bin/python3 electronics/kicad/gen_footprints.py

Fuentes (cotas en mm, vista superior; KiCad usa y hacia abajo):
  EPC2302   hoja de datos EPC2302 (2026), "Recommended copper drawing", "Recommended land pattern" (máscara definida por
            soldadura) y "Recommended stencil drawing", págs. 11-12.
  BMI088    BST-BMI088-DS000-19, fig. 11 "Landing pattern recommendation".
  LG290P    LG290P(03) Hardware Design V1.0, fig. 18 "Recommended Footprint".
  Pad_Power pads de soldadura de cables de potencia (diseño propio).
PENDIENTE: LMG1210 (TI, WQFN-19 "RVR0019A", 4 × 3 mm). La hoja SNOSD12D no trae el dibujo mecánico; bajar el plano desde
la página del producto en ti.com ("Package | Pins" → dibujo del encapsulado) antes de rutear el ESC del DS-D y el cargador.
"""

from __future__ import annotations

from pathlib import Path

import pcbnew

LIB = Path(__file__).resolve().parent / "DronSwarm.pretty"
MM = pcbnew.FromMM


def new_fp(name: str, descr: str) -> pcbnew.FOOTPRINT:
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID("DronSwarm", name))
    fp.SetLibDescription(descr)
    fp.SetAttributes(pcbnew.FP_SMD)
    fp.Reference().SetText("REF**")
    fp.Value().SetText(name)
    fp.Value().SetLayer(pcbnew.F_Fab)
    return fp


def pad(fp, num: str, x: float, y: float, w: float, h: float, layers: tuple, shape=pcbnew.PAD_SHAPE_ROUNDRECT,
        rr: float = 0.05, mask_margin: float | None = None) -> pcbnew.PAD:
    p = pcbnew.PAD(fp)
    p.SetNumber(num)
    p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    p.SetShape(shape)
    p.SetSize(pcbnew.VECTOR2I(MM(w), MM(h)))
    p.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    ls = pcbnew.LSET()
    for layer in layers:
        ls.AddLayer(layer)
    p.SetLayerSet(ls)
    if shape == pcbnew.PAD_SHAPE_ROUNDRECT:
        p.SetRoundRectRadiusRatio(min(0.5, rr / min(w, h)))
    if mask_margin is not None:
        p.SetLocalSolderMaskMargin(MM(mask_margin))
    fp.Add(p)
    return p


def rect(fp, layer, x0, y0, x1, y1, width=0.1):
    for (a, b), (c, d) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        s = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(MM(a), MM(b)))
        s.SetEnd(pcbnew.VECTOR2I(MM(c), MM(d)))
        s.SetLayer(layer)
        s.SetWidth(MM(width))
        fp.Add(s)


def frame(fp, w, h, court=0.25, silk_pin1=None):
    rect(fp, pcbnew.F_Fab, -w / 2, -h / 2, w / 2, h / 2)
    rect(fp, pcbnew.F_CrtYd, -w / 2 - court, -h / 2 - court, w / 2 + court, h / 2 + court, 0.05)
    if silk_pin1:
        c = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_CIRCLE)
        c.SetCenter(pcbnew.VECTOR2I(MM(silk_pin1[0]), MM(silk_pin1[1])))
        c.SetEnd(pcbnew.VECTOR2I(MM(silk_pin1[0] + 0.15), MM(silk_pin1[1])))
        c.SetLayer(pcbnew.F_SilkS)
        c.SetWidth(MM(0.12))
        fp.Add(c)
    fp.Reference().SetPosition(pcbnew.VECTOR2I(0, MM(-h / 2 - 1.0)))
    fp.Value().SetPosition(pcbnew.VECTOR2I(0, MM(h / 2 + 1.0)))


def epc2302():
    """Cobre según "copper drawing" (sin máscara propia), aberturas de máscara y de pasta como pads de apertura."""
    fp = new_fp("EPC2302_QFN-3x5mm", "EPC2302 eGaN FET 100 V, QFN 3 × 5 mm, 7 terminales (1 G, 2/4/6 S, 3/5/7 D). "
                "Máscara definida por soldadura según la hoja de datos EPC2302 págs. 11-12")
    cu = (pcbnew.F_Cu,)
    # (número, x, y, ancho, alto): cuerpo de 5 mm a lo largo de x
    copper = [("1", -2.352, -1.23, 1.102, 1.14), ("2", -2.352, 0.67, 1.102, 2.26), ("3", -1.275, 0, 0.65, 3.6),
              ("4", -0.425, 0, 0.65, 3.6), ("5", 0.425, 0, 0.65, 3.6), ("6", 1.275, 0, 0.65, 3.6), ("7", 2.352, 0, 1.102, 3.6)]
    for n, x, y, w, h in copper:
        pad(fp, n, x, y, w, h, cu, rr=0.05, mask_margin=-1.0)      # la abertura de máscara la dan los pads de abajo
    # Aberturas de máscara ("land pattern"): tiras y lengüetas laterales 0.725 × 0.37
    mask = [(-2.175, -1.2075, 0.40, 0.985), (-2.175, 0.65, 0.40, 2.10), (-1.275, 0, 0.30, 3.40), (-0.425, 0, 0.30, 3.40),
            (0.425, 0, 0.30, 3.40), (1.275, 0, 0.30, 3.40), (2.175, 0, 0.40, 3.40)]
    for y in (-0.975,):
        mask.append((-2.338 - 0.0, y, 0.725, 0.37))
    for y in (-0.225, 0.325, 0.975):
        mask.append((-2.338, y, 0.725, 0.37))
    for y in (-0.975, -0.325, 0.325, 0.975):
        mask.append((2.338, y, 0.725, 0.37))
    for x, y, w, h in mask:
        pad(fp, "", x, y, w, h, (pcbnew.F_Mask,), rr=0.05)
    # Pasta ("stencil drawing", 100 µm)
    paste = [(-2.090, -0.975 - 0.0, 0.54, 1.035), (-2.090, -0.040, 0.535, 0.973), (-2.090, 1.000, 0.535, 0.973)]
    for x in (-1.275, -0.425, 0.425, 1.275):
        paste += [(x, -0.900, 0.40, 1.60), (x, 0.900, 0.40, 1.60)]
    paste += [(2.143, -0.900, 0.435, 1.60), (2.143, 0.900, 0.435, 1.60)]
    for y in (-1.182 + 0.207, -0.265, 0.365, 1.0):                   # lengüetas izquierdas 0.25 × 0.45
        paste.append((-2.665, y, 0.25, 0.45))
    for y in (-0.975, -0.325, 0.325, 0.975):
        paste.append((2.665, y, 0.25, 0.45))
    for x, y, w, h in paste:
        pad(fp, "", x, y, w, h, (pcbnew.F_Paste,), rr=0.05)
    frame(fp, 5.0, 3.0, silk_pin1=(-2.9, -1.9))
    return fp


def bmi088():
    fp = new_fp("Bosch_LGA-16_3x4.5mm_P0.5mm", "BMI088 LGA-16 3 × 4.5 mm (BST-BMI088-DS000-19, fig. 11). Sin vías ni pistas "
                "bajo el sensor en la capa superior")
    layers = (pcbnew.F_Cu, pcbnew.F_Paste, pcbnew.F_Mask)
    x = 0.925 + 0.675 / 2                                             # borde interior a 0.925 del centro
    for k in range(7):
        y = -1.5 + 0.5 * k
        pad(fp, str(1 + k), x, y, 0.675, 0.25, layers, rr=0.03)       # derecha: 1 (arriba) → 7
        pad(fp, str(15 - k), -x, y, 0.675, 0.25, layers, rr=0.03)     # izquierda: 15 (arriba) → 9
    yc = 1.675 + 0.675 / 2
    pad(fp, "8", 0, yc, 0.25, 0.675, layers, rr=0.03)
    pad(fp, "16", 0, -yc, 0.25, 0.675, layers, rr=0.03)
    frame(fp, 3.0, 4.5, silk_pin1=(1.9, -2.6))
    return fp


def lg290p():
    fp = new_fp("Quectel_LG290P_LGA-79_12.2x16mm", "Quectel LG290P(03) LGA-79 12.2 × 16 mm (Hardware Design V1.0, fig. 18). "
                "Dejar 3 mm libres alrededor del módulo")
    layers = (pcbnew.F_Cu, pcbnew.F_Paste, pcbnew.F_Mask)
    W, H = 12.2, 16.0
    ys = [1.0 + 1.1 * k for k in range(7)] + [10.6 + 1.1 * k for k in range(5)]
    for k, yt in enumerate(ys):
        y = yt - H / 2
        pad(fp, str(1 + k), 1.05 - W / 2, y, 1.5, 0.8, layers, rr=0.1)  # izquierda: 1 (arriba) → 12
        pad(fp, str(24 - k), W / 2 - 1.05, y, 1.5, 0.8, layers, rr=0.1) # derecha: 24 (arriba) → 13
    n = 25
    for r in range(11):
        for c in range(5):
            x, y = 3.3 + 1.4 * c - W / 2, 1.0 + 1.4 * r - H / 2
            shape = pcbnew.PAD_SHAPE_CIRCLE if (r == 0 and c == 0) else pcbnew.PAD_SHAPE_RECT
            pad(fp, str(n), x, y, 1.0, 1.0, layers, shape=shape)       # malla interior: GND (25-79)
            n += 1
    frame(fp, W, H, court=3.0, silk_pin1=(-W / 2 - 0.6, 1.0 - H / 2))
    return fp


def power_pad(w: float, h: float):
    fp = new_fp(f"Pad_Power_{w:g}x{h:g}mm", f"Pad de potencia {w} × {h} mm para soldar cable, sin pasta")
    pad(fp, "1", 0, 0, w, h, (pcbnew.F_Cu, pcbnew.F_Mask), rr=0.3)
    frame(fp, w, h)
    return fp


def main() -> None:
    LIB.mkdir(parents=True, exist_ok=True)
    io = pcbnew.PCB_IO_KICAD_SEXPR()
    for fp in (epc2302(), bmi088(), lg290p(), power_pad(4, 3), power_pad(6, 4), power_pad(8, 5)):
        io.FootprintSave(str(LIB), fp)
        print("ok", fp.GetFPID().GetLibItemName())


if __name__ == "__main__":
    main()
