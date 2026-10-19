#!/usr/bin/env python3
"""S07-02/03 · S08-01/03 · Construye un frame completo desde OpenSCAD.

1. Lee las posiciones del ensamble (`assembly.scad` anuncia cada pieza con echo "PLACE|…").
2. Exporta cada pieza distinta a STL + STEP sólido (OpenSCAD → CSG → FreeCAD) y las placas a DXF (corte CNC).
3. Arma el ensamble en FreeCAD (tools/cad/fc_assembly.py): .FCStd con una pieza por objeto, STEP, STL e informe
   de interferencias y holgura de hélices.
4. Masas desde el volumen del CAD × densidad del material, comparadas con el presupuesto del S04.

    .venv/bin/python tools/cad/build_frame.py inspection          # DS-I
    .venv/bin/python tools/cad/build_frame.py delivery            # DS-D

El ensamble generado se guarda como `cad/freecad/<grupo>/<dron>_ensamble_generado.FCStd`: nunca se sobrescribe el
ensamble que edita el usuario.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OPENSCAD = os.environ.get("OPENSCAD", str(Path.home() / ".local/opt/openscad/AppRun"))
FREECAD = os.environ.get("FREECADCMD", str(Path.home() / ".local/opt/freecad/AppRun"))

# Densidad efectiva [g/cm³]: impresas con 4 perímetros y 40 % de relleno ≈ 75 % de la densidad del material;
# el TPU de los pies amortiguadores va con 15 % de giroide y 2 perímetros (≈ 30 % de 1.2 g/cm³)
MATERIALS = {"carbono": 1.55, "PA12-CF": 0.85, "TPU": 0.35}
GROUPS = {
    "inspection": {
        "vehicle": "DS-I", "prefix": "ds-i",
        "material": {"center_plate": "carbono", "arm_tube": "carbono", "leg_tube": "carbono", "foot": "TPU"},
        "plates": ["center_plate"],
        "budget": {   # categoría del S04 → piezas del CAD que la componen
            "placas centrales": ["center_plate"], "brazos": ["arm_tube"], "soportes de motor": ["motor_mount"],
            "piezas impresas y tornillería": ["arm_block", "battery_tray", "gimbal_mount"],
            "tren de aterrizaje (equipo fijo)": ["leg_clamp", "leg_tube", "foot"], "carcasa IP54 (equipo fijo)": ["housing"],
        },
        "budget_kg": {"tren de aterrizaje (equipo fijo)": 0.060, "carcasa IP54 (equipo fijo)": 0.120},
    },
    "delivery": {
        "vehicle": "DS-D", "prefix": "ds-d",
        "material": {"center_plate": "carbono", "arm_tube": "carbono", "leg_tube": "carbono", "skid_tube": "carbono",
                     "skid_pad": "TPU", "payload_release_hook": "aluminio"},
        "plates": ["center_plate"],
        "dxf_extra": [("payload_release.scad", "hook")],          # gancho de aluminio: corte por agua o láser
        "budget": {
            "placas centrales": ["center_plate"], "brazos": ["arm_tube"], "soportes de motor": ["motor_mount"],
            "piezas impresas y tornillería": ["arm_socket", "battery_tray", "fpv_mount", "light_mount"],
            "tren de aterrizaje (equipo fijo)": ["gear_mount", "leg_tube", "skid_tube", "skid_tee", "skid_pad"],
            "carcasa IP54 (equipo fijo)": ["housing"], "mecanismo de liberación (equipo fijo)": ["payload_release"],
        },
        "budget_kg": {"tren de aterrizaje (equipo fijo)": 0.250, "carcasa IP54 (equipo fijo)": 0.200,
                      "mecanismo de liberación (equipo fijo)": 0.150},
    },
}
MATERIALS["aluminio"] = 2.70


def material_of(g: dict, pid: str) -> str:
    """Material de una pieza por el prefijo más largo de la tabla del grupo (PA12-CF si no está)."""
    keys = sorted((k for k in g["material"] if pid.startswith(k)), key=len, reverse=True)
    return g["material"][keys[0]] if keys else "PA12-CF"


def placements(group: str) -> list[dict]:
    src = ROOT / "cad/openscad" / group / "assembly.scad"
    with tempfile.TemporaryDirectory() as td:
        out = subprocess.run([OPENSCAD, "-o", f"{td}/a.csg", str(src)], capture_output=True, text=True)
    rows = []
    for line in (out.stdout + out.stderr).splitlines():
        m = re.search(r'ECHO: "PLACE\|(.*)"$', line)
        if not m:
            continue
        name, file, defs, t, r, kind = m.group(1).split("|")
        defs = defs.replace('\\"', '"')
        rows.append({"name": name, "file": file, "defs": defs, "t": json.loads(t), "r": json.loads(r), "kind": kind})
    if not rows:
        raise SystemExit(f"assembly.scad no anunció piezas:\n{out.stderr[-2000:]}")
    return rows


def part_id(file: str, defs: str) -> str:
    base = file.removesuffix(".scad")
    m = re.search(r'which="([^"]+)"', defs)
    return f"{base}_{m.group(1)}" if m else base


def export_part(group: str, file: str, defs: str, out: Path) -> dict:
    src = ROOT / "cad/openscad" / group / file
    pid = part_id(file, defs)
    stl, csg, step = out / f"{pid}.stl", out / f"{pid}.csg", out / f"{pid}.step"
    dargs = ["-D", defs] if defs else []
    for target in (stl, csg):
        r = subprocess.run([OPENSCAD, *dargs, "-o", str(target), str(src)], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"OpenSCAD falló en {file} {defs}:\n{r.stderr[-1500:]}")
    env = dict(os.environ, CSG_IN=str(csg), STEP_OUT=str(step), OPENSCAD_BIN=OPENSCAD)
    r = subprocess.run([FREECAD, "-c", f"exec(open('{ROOT}/tools/cad/csg_to_step.py').read())"], env=env,
                       capture_output=True, text=True)
    res = next((json.loads(line[7:]) for line in r.stdout.splitlines() if line.startswith("RESULT ")), None)
    if res is None:
        raise SystemExit(f"FreeCAD no exportó {pid}:\n{(r.stdout + r.stderr)[-1500:]}")
    csg.unlink(missing_ok=True)
    return {"id": pid, **res}


def export_dxf(group: str, file: str, which: str, out: Path) -> Path:
    dxf = out / f"{file.removesuffix('.scad')}_{which}.dxf"
    subprocess.run([OPENSCAD, "-D", f'which="{which}"', "-D", 'mode="2d"', "-o", str(dxf),
                    str(ROOT / "cad/openscad" / group / file)], check=True, capture_output=True)
    return dxf


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("group", choices=list(GROUPS))
    ap.add_argument("--no-assembly", action="store_true")
    a = ap.parse_args()
    g = GROUPS[a.group]
    out = ROOT / "cad/exports" / a.group
    out.mkdir(parents=True, exist_ok=True)
    rows = placements(a.group)
    uniq = {(r["file"], r["defs"]) for r in rows}
    parts = {}
    for file, defs in sorted(uniq):
        res = export_part(a.group, file, defs, out)
        parts[res["id"]] = res
        print(f"  {res['id']:<24} {'válido' if res['valid'] else 'INVÁLIDO'}  {res['volume_mm3'] / 1000:8.1f} cm³  {res['bbox_mm']}", flush=True)
    dxfs = [str(export_dxf(a.group, f + ".scad", w, out).relative_to(ROOT)) for f in g["plates"] for w in ("top", "bottom")]
    dxfs += [str(export_dxf(a.group, f, w, out).relative_to(ROOT)) for f, w in g.get("dxf_extra", [])]

    # masas por pieza y por categoría del S04
    sizing = json.loads((ROOT / f"engineering/data/results/{g['vehicle'].lower()}_sizing.json").read_text())
    count: dict[str, int] = {}
    for r in rows:
        if r["kind"] == "part":
            pid = part_id(r["file"], r["defs"])
            count[pid] = count.get(pid, 0) + 1
    mass = {}
    for pid, n in count.items():
        mat = material_of(g, pid)
        m1 = parts[pid]["volume_mm3"] / 1000 * MATERIALS[mat] / 1000
        mass[pid] = {"material": mat, "qty": n, "unit_kg": round(m1, 4), "total_kg": round(m1 * n, 4)}
    categories = {}
    for cat, bases in g["budget"].items():
        cad = sum(v["total_kg"] for k, v in mass.items() if any(k.startswith(b) for b in bases))
        budget = sizing["masses"].get(cat, g["budget_kg"].get(cat))
        categories[cat] = {"cad_kg": round(cad, 3), "budget_kg": budget,
                           "delta_pct": round(100 * (cad / budget - 1), 0) if budget else None}
    report = {"vehicle": g["vehicle"], "parts": mass, "categories": categories, "dxf": dxfs,
              "frame_cad_kg": round(sum(v["total_kg"] for v in mass.values()), 3),
              "frame_budget_kg": round(sum(c["budget_kg"] or 0 for c in categories.values()), 3),
              "note": "Masa sin tornillería ni adhesivos (≈ 5-8 % adicional). Impresas a densidad efectiva de 4 perímetros + 40 % de relleno.",
              "placements": {r["name"]: r["t"] for r in rows}}

    prev = out / "masas.json"
    if a.no_assembly and prev.exists():                   # conservar el ensamble de la corrida anterior
        old = json.loads(prev.read_text())
        report.update({k: old[k] for k in ("assembly", "assembly_files") if k in old})
    if not a.no_assembly:
        cfg = {"name": f"{g['prefix']}_ensamble", "fcstd": str(ROOT / f"cad/freecad/{a.group}/{g['prefix']}_ensamble_generado.FCStd"),
               "step": str(out / f"{g['prefix']}_ensamble.step"), "stl": str(out / f"{g['prefix']}_ensamble.stl"),
               "sim_stl": str(out / f"{g['prefix']}_sim.stl"),
               "report": str(out / "interferencias.json"), "ignore_pairs": [],
               "parts": [{"name": r["name"], "step": str(out / f"{part_id(r['file'], r['defs'])}.step"), "t": r["t"], "r": r["r"],
                          "kind": r["kind"],
                          "material": ("prop" if r["name"].startswith("prop") else "ref") if r["kind"] == "ref"
                          else material_of(g, part_id(r["file"], r["defs"]))}
                         for r in rows]}
        Path(cfg["fcstd"]).parent.mkdir(parents=True, exist_ok=True)
        cfg_path = out / "ensamble_config.json"
        cfg_path.write_text(json.dumps(cfg, indent=1))
        r = subprocess.run([FREECAD, "-c", f"exec(open('{ROOT}/tools/cad/fc_assembly.py').read())"],
                           env=dict(os.environ, ASM_JSON=str(cfg_path)), capture_output=True, text=True)
        if "RESULT" not in r.stdout:
            raise SystemExit(f"falló el ensamble:\n{(r.stdout + r.stderr)[-2000:]}")
        cfg_path.unlink()
        report["assembly"] = json.loads((out / "interferencias.json").read_text())
        report["assembly_files"] = [str(Path(cfg[k]).relative_to(ROOT)) for k in ("fcstd", "step", "stl")]
    (out / "masas.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: report[k] for k in ("categories", "frame_cad_kg", "frame_budget_kg")}, indent=2, ensure_ascii=False))
    if "assembly" in report:
        asm = report["assembly"]
        print(f"interferencias: {len(asm['interferences'])} · holgura mínima de hélices: "
              f"{min(p['min_clearance_mm'] for p in asm['prop_clearance'])} mm · caja {asm['bbox_mm']} mm")


if __name__ == "__main__":
    sys.exit(main())
