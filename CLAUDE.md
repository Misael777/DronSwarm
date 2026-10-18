# DronSwarm · Guía para el agente

Drones de bajo costo para minería (DS-I inspección vs DJI M4E; DS-D delivery vs DJI M400), operados en enjambre. Caso de diseño: **5,000 msnm**.

## Antes de trabajar
1. Leer el progreso real en `docs/plan/DronSwarm_Plan_de_Trabajo.xlsx` (hoja `Tareas`: ID, Estado, % avance) y el alcance en `docs/plan/PLAN_DE_TRABAJO.md`.
2. Convenciones: `docs/guia-estructura-repo.md`. Decisiones: `docs/decisiones.md` (no contradecir un ADR aceptado sin proponer otro).
3. Respetar dependencias entre tareas y los Gates (G0-G7).

## Reglas
- Docs en español; código e identificadores en inglés.
- Control siempre vía PX4/MAVLink (`mavsdk_grpc`), nunca APIs propias del simulador.
- CAD: la fuente es OpenSCAD (`cad/openscad/`); FreeCAD (`cad/freecad/`) es del usuario: no sobrescribir `.FCStd` sin avisar. Exportar con `tools/cad/export_scad.sh`; evitar `hull`/`minkowski` en piezas con planos.
- Commits con el ID de tarea: `[S01-04] ...`.
- Plan: editar `tools/plan/plan_data.py` y regenerar con `tools/plan/generar_plan_trabajo.py` (conserva el progreso del Excel).

## Comandos
```bash
./dronswarm.sh                                          # consola de pruebas del usuario (menú whiptail)
.venv/bin/ruff check . && .venv/bin/pytest -q          # lint + tests
export PATH=$HOME/.venvs/px4/bin:$PATH                  # toolchain de PX4 sin sudo
bash tools/sitl/run_sih.sh                              # prueba de humo PX4 SITL (SIH)
bash tools/sitl/run_sih_multi.sh 6                      # 6 drones + medición de recursos
bash tools/sitl/run_gz_multi.sh 6                       # 6 drones en Gazebo (máx. ~6 en tiempo real)
MODEL=x500_mono_cam bash tools/sitl/run_gz_multi.sh 3   # con cámara (OpenGL en la NVIDIA, ADR-009)
SCENE=swarm MODELS=ds_i,ds_i,ds_i,ds_i,ds_i,ds_i bash tools/sitl/run_gz_multi.sh   # enjambre S06 + monitor de colisiones
SCENE=swarm MODEL=ds_d MISSION=fault MISSION_ARGS="--case motor" bash tools/sitl/run_gz_multi.sh 1   # fallas: motor|gps|battery|link
.venv/bin/python -m control.swarm.campaign --runs 200 --out <dir>   # Monte Carlo del enjambre (simulador cinemático)
.venv/bin/python -m engineering.spec_v1                 # spec v1 (docs/ingenieria/spec_v1.md)
~/.venvs/gpu/bin/python                                 # PyTorch + CUDA (RTX 3050 Ti, 4 GB)
bash tools/cad/export_scad.sh <pieza.scad> [--fcstd]    # OpenSCAD → STL + STEP
```
