"""Arma un ensamble de FreeCAD desde piezas STEP y posiciones (se ejecuta con freecadcmd).

Variables de entorno:
    ASM_JSON   JSON con {"name", "parts": [{name, step, t, r, kind, material}], "fcstd", "step", "stl", "report"}
Salidas: .FCStd con una pieza por objeto (colores por material), STEP del ensamble, STL para imágenes y un
informe JSON de interferencias (volumen común entre sólidos que no deberían tocarse).
"""

import itertools
import json
import os

import FreeCAD
import Mesh
import MeshPart
import Part

cfg = json.load(open(os.environ["ASM_JSON"]))
COLORS = {"carbono": (0.12, 0.12, 0.13), "PA12-CF": (0.30, 0.30, 0.32), "TPU": (0.85, 0.45, 0.10),
          "ref": (0.55, 0.70, 0.90), "prop": (0.80, 0.80, 0.80)}

doc = FreeCAD.newDocument(cfg["name"])
grp_parts = doc.addObject("App::DocumentObjectGroup", "Piezas")
grp_refs = doc.addObject("App::DocumentObjectGroup", "Comerciales_referencia")
cache, placed = {}, []
for p in cfg["parts"]:
    if p["step"] not in cache:
        s = Part.Shape()
        s.read(p["step"])
        cache[p["step"]] = s
    shape = cache[p["step"]].copy()
    rx, ry, rz = p["r"]
    pl = FreeCAD.Placement(FreeCAD.Vector(*p["t"]), FreeCAD.Rotation(rz, ry, rx))   # = rotate([rx, ry, rz]) de OpenSCAD
    shape.Placement = pl
    obj = doc.addObject("Part::Feature", p["name"])
    obj.Shape = shape
    (grp_refs if p["kind"] == "ref" else grp_parts).addObject(obj)
    if hasattr(obj, "ViewObject") and obj.ViewObject:
        obj.ViewObject.ShapeColor = COLORS.get(p["material"], (0.5, 0.5, 0.5))
    placed.append((p, shape))
doc.recompute()
doc.saveAs(cfg["fcstd"])

# Interferencias: volumen común entre pares de sólidos (las piezas que solo se apoyan dan ~0)
ignore = set(tuple(sorted(x)) for x in cfg.get("ignore_pairs", []))
found = []
for (pa, sa), (pb, sb) in itertools.combinations(placed, 2):
    if "prop" in (pa["material"], pb["material"]):
        continue                                          # los discos de hélice se revisan aparte (holgura)
    if not sa.BoundBox.intersect(sb.BoundBox):
        continue
    key = tuple(sorted((pa["name"].rsplit("_", 1)[0] if pa["name"][-1].isdigit() else pa["name"],
                        pb["name"].rsplit("_", 1)[0] if pb["name"][-1].isdigit() else pb["name"])))
    if key in ignore:
        continue
    try:
        v = sa.common(sb).Volume
    except Exception:                                     # noqa: BLE001
        v = -1
    if v > 1.0 or v < 0:
        found.append({"a": pa["name"], "b": pb["name"], "volume_mm3": round(v, 1)})

# Holgura de hélices: disco de cada hélice contra todas las piezas que no son su motor
prop_clear = []
for (pa, sa) in placed:
    if pa["material"] != "prop":
        continue
    best = None
    for (pb, sb) in placed:
        if pb is pa or pb["material"] == "prop" or pb["name"].startswith("motor_"):
            continue
        d = sa.distToShape(sb)[0]
        if best is None or d < best[0]:
            best = (d, pb["name"])
    prop_clear.append({"prop": pa["name"], "min_clearance_mm": round(best[0], 1), "nearest": best[1]})
props = [s for p, s in placed if p["material"] == "prop"]
for (i, a), (j, b) in itertools.combinations(enumerate(props), 2):
    prop_clear.append({"prop": f"prop_{i}↔prop_{j}", "min_clearance_mm": round(a.distToShape(b)[0], 1), "nearest": "hélice vecina"})

compound = Part.makeCompound([s for p, s in placed if p["material"] != "prop"])
compound.exportStep(cfg["step"])
Mesh.export([o for o in doc.Objects if o.TypeId == "Part::Feature" and "prop" not in o.Name], cfg["stl"])
# Malla liviana para el simulador: sin hélices ni caja de carga (en Gazebo son cuerpos aparte), menor resolución
sim = Part.makeCompound([s for p, s in placed if p["material"] != "prop" and not p["name"].startswith("payload_box")])
Mesh.Mesh(MeshPart.meshFromShape(Shape=sim, LinearDeflection=0.8, AngularDeflection=0.6)).write(cfg["sim_stl"])
bb = compound.BoundBox
json.dump({"interferences": found, "prop_clearance": prop_clear,
           "bbox_mm": [round(bb.XLength, 1), round(bb.YLength, 1), round(bb.ZLength, 1)],
           "zmin_mm": round(bb.ZMin, 1), "zmax_mm": round(bb.ZMax, 1)},
          open(cfg["report"], "w"), indent=2, ensure_ascii=False)
print("RESULT " + json.dumps({"interferences": len(found), "parts": len(placed)}))
