# Flujo CAD: OpenSCAD → STEP → FreeCAD

Decisión: [ADR-003](decisiones.md). OpenSCAD es la fuente que edita el agente; FreeCAD es la herramienta del usuario.

```text
cad/openscad/<grupo>/<pieza>.scad     ← fuente paramétrica (agente, versionada en git)
        │  tools/cad/export_scad.sh
        ├──► cad/exports/<pieza>.stl   ← impresión 3D y simulación (malla)
        ├──► cad/exports/<pieza>.csg   ← intermedio
        └──► cad/exports/<pieza>.step  ← sólido B-rep para FreeCAD (planos, ensambles)
                         │
cad/freecad/<grupo>/*.FCStd           ← ensambles, revisión, TechDraw (usuario)
```

## Uso

```bash
bash tools/cad/export_scad.sh cad/openscad/common/motor_mount.scad          # STL + STEP
bash tools/cad/export_scad.sh cad/openscad/common/motor_mount.scad --fcstd  # además un .FCStd con la pieza
python tools/cad/render_stl.py cad/exports/motor_mount.stl salida.png      # imagen para informes
```

El script imprime un resumen y falla si el STEP no es un sólido válido:

```json
{"valid": true, "solids": 1, "faces": 42, "volume_mm3": 13033.5, "bbox_mm": [59.0, 42.0, 32.0]}
```

## En FreeCAD (usuario)

1. **Archivo → Importar** el `.step` de `cad/exports/` (o abrir el `.FCStd`).
2. Para ensamblar: workbench **Assembly** (FreeCAD 1.0) → insertar las piezas STEP → restricciones.
3. Para planos: workbench **TechDraw** → vista de la pieza → cotas. Funciona porque el STEP tiene caras y aristas reales.
4. Si cambia una medida, no editar el STEP: pedir el cambio en el `.scad` y re-exportar; luego en FreeCAD **Recargar** el STEP.

## Frames completos (S07-S08)

```bash
.venv/bin/python tools/cad/gen_cad_params.py            # parámetros desde la spec v1 → cad/openscad/<grupo>/*_params.scad
.venv/bin/python tools/cad/build_frame.py inspection    # DS-I: piezas, DXF, ensamble, interferencias, masas (~2 min)
.venv/bin/python tools/cad/build_frame.py delivery      # DS-D (~5 min)
.venv/bin/python tools/fea/run_fea.py inspection        # FEA con gmsh + CalculiX → cad/freecad/<grupo>/fea/
.venv/bin/python tools/fea/fea_report.py                # informe → docs/ingenieria/fea_frames.md
.venv/bin/python tools/gen_sdf.py                       # simulación con la malla y las masas del CAD
```

- Cada pieza está en su propio sistema de coordenadas. `assembly.scad` la posiciona y la anuncia con
  `echo("PLACE|…")`, y `build_frame.py` arma en FreeCAD el ensamble con los STEP:
  `cad/freecad/<grupo>/<dron>_ensamble_generado.FCStd`, con una pieza por objeto y los componentes comerciales en
  un grupo aparte.
- **El ensamble generado se sobrescribe en cada corrida.** Para revisar, anotar o acotar, guardarlo con otro nombre:
  `ds-i_ensamble.FCStd` es el archivo del usuario y el agente no lo toca.
- Salidas en `cad/exports/<grupo>/`: STL y STEP por pieza, DXF de corte, ensamble STEP/STL, `masas.json` (masa por
  pieza y por categoría contra el S04, interferencias, holgura de hélices) y `<dron>_sim.stl` (malla para Gazebo).

## Reglas de diseño en OpenSCAD

| Regla | Motivo |
|---|---|
| Parámetros arriba del archivo, con unidades (mm) y comentarios | Personalizador de OpenSCAD y lectura del agente |
| Una pieza fabricable por archivo; los ensambles van aparte | Cada pieza exporta su propio STEP y plano |
| **Evitar `hull()` y `minkowski()` en piezas que necesitan planos**; usar primitivas y `linear_extrude`/`rotate_extrude` de perfiles 2D | FreeCAD convierte `hull`/`minkowski` en mallas trianguladas: el sólido deja de tener caras acotables |
| `$fn` ≥ 64 en agujeros funcionales | Agujeros redondos en STL e impresión |
| **Sin booleanas 2D para el STEP:** formas redondeadas con cubos y cilindros (`rbox`), y DXF con `projection()` o un modo `2d` aparte | El importador CSG de FreeCAD devuelve formas nulas con `union()` 2D dentro de `linear_extrude` |
| **Cada grupo de agujeros, hijo directo del `difference()`** con su propio `translate` | El importador falla si varios operandos cuelgan de una sola transformación |
| Holguras de impresión como parámetro (no fijas en la geometría) | Ajuste por material/impresora |

## Verificación (S01-06, 2026-10-17)

Pieza de prueba `cad/openscad/common/motor_mount.scad` (soporte de motor para tubo Ø20 mm, patrón de motor 16 × 19 mm M3):

- STL: 2,818 triángulos. STEP: 1 sólido válido, 42 caras, 13,033 mm³, caja 59 × 42 × 32 mm.
- Hallazgos: (1) FreeCAD necesita la ruta de OpenSCAD para importar `hull`, lo que daba un STEP vacío; (2) `removeSplitter()` puede invalidar el sólido, así que solo se aplica si el resultado sigue siendo válido.
- Pendiente del usuario: abrir el STEP/FCStd en FreeCAD (Windows) y generar un plano de prueba en TechDraw.
