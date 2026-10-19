"""Convierte un .csg de OpenSCAD en un sólido STEP con FreeCAD (se ejecuta con freecadcmd).

Variables de entorno:
    CSG_IN    ruta del .csg de entrada
    STEP_OUT  ruta del .step de salida
    FCSTD_OUT (opcional) guarda también un documento FreeCAD con la pieza
    OPENSCAD_BIN binario de OpenSCAD (FreeCAD lo llama para hull/minkowski)

Imprime un JSON con volumen, número de sólidos y validez para verificar la exportación.
"""

import json
import os

import FreeCAD
import importCSG
import Part

src, dst, fcstd = os.environ["CSG_IN"], os.environ["STEP_OUT"], os.environ.get("FCSTD_OUT")
FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/OpenSCAD").SetString("openscadexecutable", os.environ["OPENSCAD_BIN"])

doc = FreeCAD.newDocument("export")
importCSG.insert(src, doc.Name)
doc.recompute()

roots = [o for o in doc.Objects if hasattr(o, "Shape") and not o.InList and not o.Shape.isNull()]
shape = roots[0].Shape if len(roots) == 1 else Part.makeCompound([o.Shape for o in roots])
if not shape.Solids:
    raise SystemExit("ERROR: la exportación no produjo sólidos")
if len(shape.Solids) > 1:          # el importador deja los operandos de union() como sólidos superpuestos
    fused = shape.Solids[0].multiFuse(shape.Solids[1:])
    if fused.isValid() and fused.Solids:
        shape = fused
refined = shape.removeSplitter()  # une caras coplanares; a veces deja la B-rep inválida
if refined.isValid():
    shape = refined
if not shape.isValid():
    raise SystemExit("ERROR: el sólido exportado no es válido")
shape.exportStep(dst)

if fcstd:
    out = FreeCAD.newDocument("pieza")
    feat = out.addObject("Part::Feature", os.path.splitext(os.path.basename(dst))[0])
    feat.Shape = shape
    out.recompute()
    out.saveAs(fcstd)

bb = shape.BoundBox
print("RESULT " + json.dumps({
    "step": dst,
    "valid": shape.isValid(),
    "solids": len(shape.Solids),
    "faces": len(shape.Faces),
    "volume_mm3": round(shape.Volume, 1),
    "center_of_mass_mm": [round(c, 2) for c in (shape.CenterOfMass if hasattr(shape, "CenterOfMass") else shape.BoundBox.Center)],
    "bbox_mm": [round(bb.XLength, 2), round(bb.YLength, 2), round(bb.ZLength, 2)],
}))
