"""S07-04 / S08-04 · FEA con gmsh + CalculiX (los binarios vienen dentro de FreeCAD 1.0).

- `solid_static`: pieza sólida desde STEP, tetraedros cuadráticos (C3D10), apoyos y cargas elegidos por geometría
  (funciones sobre las coordenadas de los nodos), esfuerzo de von Mises y desplazamiento.
- `beam_modal`: brazo como viga tubular (B32) empotrada con la masa del motor en la punta: frecuencias propias.

Se usa desde tools/fea/run_fea.py. Unidades: mm, N, MPa, t (toneladas) para la densidad en el análisis modal.
"""

from __future__ import annotations

import math
import os
import re
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

FC = Path(os.environ.get("FREECAD_USR", Path.home() / ".local/opt/freecad/usr"))
GMSH, CCX = FC / "bin/gmsh", FC / "bin/ccx"
ENV = dict(os.environ, LD_LIBRARY_PATH=f"{FC / 'lib'}:{os.environ.get('LD_LIBRARY_PATH', '')}", OMP_NUM_THREADS="4")


@dataclass(frozen=True)
class Material:
    name: str
    e_mpa: float
    nu: float
    rho_t_mm3: float          # densidad en t/mm³ (1 g/cm³ = 1e-9 t/mm³)
    strength_mpa: float       # resistencia de referencia (para el factor de seguridad)


# FDM: módulo y resistencia en el plano de las capas; entre capas la resistencia baja a ~50 % (se informa aparte).
PA12_CF = Material("PA12-CF (FDM, 4 perímetros)", 3500, 0.35, 1.0e-9, 50.0)
CARBON_QI = Material("Carbono cuasi-isótropo (placa)", 45000, 0.30, 1.55e-9, 450.0)
CARBON_TUBE = Material("Carbono enrollado (tubo)", 70000, 0.30, 1.55e-9, 500.0)
ALU_6061 = Material("Aluminio 6061-T6", 69000, 0.33, 2.70e-9, 240.0)


def mesh(step: Path, size: float, work: Path) -> tuple[np.ndarray, dict[int, int], np.ndarray]:
    """Malla de tetraedros cuadráticos. Devuelve (coordenadas, id→fila, conectividad C3D10)."""
    inp = work / "mesh.inp"
    r = subprocess.run([str(GMSH), str(step), "-3", "-order", "2", "-setnumber", "Mesh.SecondOrderLinear", "1",
                        "-clmax", str(size), "-clmin", str(size / 4),
                        "-format", "inp", "-o", str(inp)], env=ENV, capture_output=True, text=True)
    if not inp.exists():
        raise RuntimeError(f"gmsh falló:\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
    nodes, elems, mode = [], [], None
    for line in inp.read_text().splitlines():
        if line.startswith("*"):
            low = line.lower()
            mode = "node" if low.startswith("*node") else ("tet" if "c3d10" in low else None)
            continue
        if not line.strip():
            continue
        vals = [v for v in line.replace(" ", "").split(",") if v]
        if mode == "node":
            nodes.append((int(vals[0]), float(vals[1]), float(vals[2]), float(vals[3])))
        elif mode == "tet":
            elems.append([int(v) for v in vals])
    ids = np.array([n[0] for n in nodes])
    xyz = np.array([n[1:] for n in nodes])
    return xyz, {int(i): k for k, i in enumerate(ids)}, np.array(elems, dtype=int)


def _vm(s):
    sxx, syy, szz, sxy, sxz, syz = s
    return math.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2) + 3 * (sxy ** 2 + sxz ** 2 + syz ** 2))


@dataclass
class StaticResult:
    nodes: int
    elements: int
    vm_max: float
    vm_p995: float            # percentil 99.5: sin los picos numéricos en esquinas de los apoyos
    disp_max_mm: float
    fixed_nodes: int
    loaded_nodes: dict


def solid_static(step: Path, mat: Material, size: float, fix: Callable[[np.ndarray], np.ndarray],
                 loads: list[tuple[str, Callable[[np.ndarray], np.ndarray], tuple[float, float, float]]],
                 keep: Path | None = None) -> StaticResult:
    """fix(xyz) → máscara de nodos empotrados; loads = [(nombre, máscara(xyz), fuerza total [N])] repartida por igual."""
    with tempfile.TemporaryDirectory() as td:
        work = Path(keep) if keep else Path(td)
        work.mkdir(parents=True, exist_ok=True)
        xyz, idx, el = mesh(step, size, work)
        ids = np.array(sorted(idx, key=idx.get))
        fixed = ids[fix(xyz)]
        if len(fixed) < 3:
            raise RuntimeError("apoyo con menos de 3 nodos: revisar la selección")
        deck = ["*HEADING", "DronSwarm FEA", "*NODE, NSET=NALL"]
        deck += [f"{i}, {x:.6f}, {y:.6f}, {z:.6f}" for i, (x, y, z) in zip(ids, xyz)]
        deck.append("*ELEMENT, TYPE=C3D10, ELSET=EALL")
        deck += [", ".join(map(str, e)) for e in el]
        deck += ["*NSET, NSET=FIX"] + [", ".join(map(str, fixed[k:k + 12])) for k in range(0, len(fixed), 12)]
        deck += ["*MATERIAL, NAME=M", "*ELASTIC", f"{mat.e_mpa}, {mat.nu}", "*DENSITY", f"{mat.rho_t_mm3}",
                 "*SOLID SECTION, ELSET=EALL, MATERIAL=M", "*STEP", "*STATIC", "*BOUNDARY", "FIX, 1, 3, 0.0", "*CLOAD"]
        loaded = {}
        for name, sel, f in loads:
            ln = ids[sel(xyz)]
            if len(ln) == 0:
                raise RuntimeError(f"carga '{name}' sin nodos: revisar la selección")
            loaded[name] = int(len(ln))
            for n in ln:
                for dof, comp in enumerate(f, start=1):
                    if comp:
                        deck.append(f"{n}, {dof}, {comp / len(ln):.6e}")
        deck += ["*NODE PRINT, NSET=NALL", "U", "*EL PRINT, ELSET=EALL", "S", "*END STEP"]
        (work / "job.inp").write_text("\n".join(deck) + "\n")
        r = subprocess.run([str(CCX), "job"], cwd=work, env=ENV, capture_output=True, text=True)
        dat = (work / "job.dat")
        if not dat.exists() or "ERROR" in r.stdout:
            raise RuntimeError(f"CalculiX falló:\n{r.stdout[-2000:]}")
        u, s = [], []
        section = None
        for line in dat.read_text().splitlines():
            if "displacements" in line:
                section = "u"
                continue
            if "stresses" in line:
                section = "s"
                continue
            v = line.split()
            if section == "u" and len(v) == 4:
                u.append([float(x) for x in v[1:]])
            elif section == "s" and len(v) == 8:
                s.append(_vm([float(x) for x in v[2:]]))
        vm = np.array(s)
        return StaticResult(len(ids), len(el), float(vm.max()), float(np.percentile(vm, 99.5)),
                            float(np.linalg.norm(np.array(u), axis=1).max()), int(len(fixed)), loaded)


def beam_modal(length_mm: float, od_mm: float, wall_mm: float, mat: Material, tip_mass_kg: float,
               n_el: int = 20, modes: int = 4) -> list[float]:
    """Voladizo tubular (elementos de viga B32R, sección PIPE) con masa puntual en la punta: frecuencias [Hz]."""
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        n_nodes = 2 * n_el + 1
        deck = ["*HEADING", "brazo", "*NODE, NSET=NALL"]
        deck += [f"{i + 1}, {length_mm * i / (n_nodes - 1):.6f}, 0, 0" for i in range(n_nodes)]
        deck.append("*ELEMENT, TYPE=B32R, ELSET=EB")
        deck += [f"{k + 1}, {2 * k + 1}, {2 * k + 2}, {2 * k + 3}" for k in range(n_el)]
        deck += ["*ELEMENT, TYPE=MASS, ELSET=EM", f"{n_el + 1}, {n_nodes}",
                 "*MASS, ELSET=EM", f"{tip_mass_kg / 1000:.6e}",
                 "*MATERIAL, NAME=M", "*ELASTIC", f"{mat.e_mpa}, {mat.nu}", "*DENSITY", f"{mat.rho_t_mm3}",
                 "*BEAM SECTION, ELSET=EB, MATERIAL=M, SECTION=PIPE", f"{od_mm / 2:.4f}, {wall_mm:.4f}", "0, 0, 1",
                 "*BOUNDARY", "1, 1, 6, 0.0", "*STEP", "*FREQUENCY", f"{modes}", "*END STEP"]
        (work / "job.inp").write_text("\n".join(deck) + "\n")
        r = subprocess.run([str(CCX), "job"], cwd=work, env=ENV, capture_output=True, text=True)
        txt = (work / "job.dat").read_text() if (work / "job.dat").exists() else ""
        m = re.search(r"E I G E N V A L U E   O U T P U T(.*?)(?:\n\s*\n\s*\n|P A R T I C I P)", txt, re.S)
        if not m:
            raise RuntimeError(f"CalculiX (modal) falló:\n{r.stdout[-2000:]}")
        freqs = []
        for line in m.group(1).splitlines():
            v = line.split()
            if len(v) >= 4 and v[0].isdigit():
                freqs.append(float(v[3]))      # columna CYCLES/TIME [Hz]
        return freqs
