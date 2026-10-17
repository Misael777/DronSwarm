# Diseño mecánico

- `openscad/` — **fuente paramétrica** (.scad). La edita el agente; es texto y se versiona.
- `freecad/` — **ensambles, revisión y planos** (.FCStd). Los usa el usuario.
- `exports/` — generados: STEP/CSG sólidos para FreeCAD, STL/DAE para simulación.
- Exportar con `tools/cad/export_scad.sh`. Ver `docs/cad-flujo.md`.
