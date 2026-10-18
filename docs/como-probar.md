# Cómo probar lo que hay hasta ahora

Todo se corre desde una terminal de WSL en la carpeta del repo. Abre una **terminal nueva** (para que cargue la configuración de la GPU de `~/.bashrc`) y entra al repo:

```bash
cd ~/DronSwarm
```

## Lo más fácil: la consola de pruebas

```bash
./dronswarm.sh
```
Menú con todo lo de abajo (flechas + Enter, Esc para volver). Cada prueba muestra su avance, un resumen al final y guarda los resultados en `logs/<prueba>-<fecha>/`. Atajos sin menú: `./dronswarm.sh demo 4`, `./dronswarm.sh sih`, `./dronswarm.sh tests`, `./dronswarm.sh estado`.

Lo más nuevo está en **N · Nuestros drones (S05)**: los modelos reales de DS-I, DS-D y DS-H, el enjambre mixto y la carga cooperativa de 10 kg. A mano:

```bash
GUI=1 MODELS=ds_i,ds_d,ds_h HOLD=30 bash tools/sitl/run_gz_multi.sh          # los 3 tamaños lado a lado
GUI=1 MODEL=ds_d MISSION=delivery bash tools/sitl/run_gz_multi.sh 1          # DS-D entrega con su caja de 5 kg
GUI=1 MODEL=ds_h MISSION=delivery bash tools/sitl/run_gz_multi.sh 1          # DS-H entrega con su caja de 10 kg
GUI=1 MODELS=ds_i,ds_i,ds_d,ds_h MISSION=formation bash tools/sitl/run_gz_multi.sh   # enjambre mixto
GUI=1 SCENE=coop bash tools/sitl/run_gz_multi.sh                             # 3 DS-D levantan juntos 10 kg
GUI=1 SCENE=mine MODEL=ds_i MISSION=inspection bash tools/sitl/run_gz_multi.sh 1   # inspección del tajo (≈ 9 min)
GUI=1 SCENE=delivery bash tools/sitl/run_gz_multi.sh 1                        # entrega al fondo del tajo con liberación
GUI=1 SCENE=mine MODEL=ds_i HOLD=30 bash tools/sitl/run_gz_multi.sh 1          # viento de 8 m/s con ráfagas
```
El mundo de mina (tajo de 6 bancos y 60 m de profundidad, faja transportadora, relavera, túnel, viento y coordenadas
andinas a 4,300 msnm) se genera con `.venv/bin/python tools/gen_world.py --wind 8`. Métricas de un vuelo contra el
cálculo del S04: `.venv/bin/python tools/extract_xtdrone_logs.py logs/.../drone_0.ulg --vehicle DS-D`.
Si cambias el dimensionamiento, regenera los modelos: `.venv/bin/python tools/gen_sdf.py && .venv/bin/python tools/gen_coop.py`.

Los pasos siguientes son los mismos comandos de antes, por si prefieres correrlos a mano.

## 1. Pruebas automáticas (10 s)

```bash
.venv/bin/ruff check . && .venv/bin/pytest -q
```
Esperado: `All checks passed!` y `7 passed`.

## 2. Demo visual: enjambre en formación (≈ 1.5 min)

```bash
GUI=1 MISSION=formation bash tools/sitl/run_gz_multi.sh 4
```
Se abre la ventana de Gazebo en Windows. Los 4 drones despegan a 10 m, recorren un cuadrado de 30 m manteniendo la formación y aterrizan. En la terminal se ve el avance (`vértice 1/4 alcanzado…`). Al terminar, la ventana se cierra sola.

- En Gazebo: rueda del ratón = zoom, clic izquierdo y arrastrar = girar, clic derecho y arrastrar = mover. Los drones aparecen en el centro del mundo.
- Prueba con 6 (`… run_gz_multi.sh 6`): es el máximo que tu PC simula en tiempo real.

## 3. Drones con cámara (≈ 1.5 min)

```bash
GUI=1 MODEL=x500_mono_cam HOLD=60 bash tools/sitl/run_gz_multi.sh 2
```
Para ver la imagen de la cámara en Gazebo: menú ⋮ (arriba a la derecha) → **Image Display** → tópico `/camera`. Requiere la GPU NVIDIA (ya configurada).

## 4. Un dron "a mano", como en la documentación de PX4

```bash
cd ~/src/PX4-Autopilot && make px4_sitl gz_x500
```
Cuando aparezca el prompt `pxh>`, escribe `commander takeoff`, luego `commander land`. Para salir: `shutdown`.

## 5. Prueba de vuelo sin gráficos + gráfica (≈ 1.5 min)

```bash
bash tools/sitl/run_sih.sh
```
Resultado en `docs/evidencias/sitl/smoke_test.json`. Para la gráfica del vuelo:
```bash
.venv/bin/python tools/sitl/plot_flight.py docs/evidencias/sitl/smoke_test.ulg docs/evidencias/sitl/smoke_test.png
```
Los logs de vuelo `.ulg` no se versionan (pesan hasta 120 MB; GitHub admite 100 MB): quedan en tu disco y cada corrida
nueva los genera. Lo que sí se versiona es el `.json` de resultados y las gráficas.
Ábrela desde VS Code o desde Windows en `\\wsl$\Ubuntu-22.04\home\mishaco\DronSwarm\docs\evidencias\sitl\`.

## 6. Capacidad del PC (≈ 1.5 min por corrida)

```bash
bash tools/sitl/run_gz_multi.sh 6      # sin ventana; resultados en docs/evidencias/sitl/gz_n6/resources.json
```

## 7. CAD: OpenSCAD → STEP → FreeCAD

```bash
bash tools/cad/export_scad.sh cad/openscad/common/motor_mount.scad --fcstd
```
Luego, en FreeCAD (Windows): Archivo → Abrir → `\\wsl$\Ubuntu-22.04\home\mishaco\DronSwarm\cad\freecad\common\motor_mount.FCStd`. Para el plano: workbench **TechDraw** → Insertar página → seleccionar la pieza → Insertar vista.

Para cambiar la pieza: edita los parámetros al inicio de `cad/openscad/common/motor_mount.scad` (por ejemplo `tube_d = 25;`) y vuelve a exportar.

## 8. Ingeniería: S03 (modelos) y S04 (dimensionamiento)

En la consola: opción **I · Ingeniería**. A mano:

```bash
.venv/bin/python -m engineering.endurance_table   # autonomía de DS-I y DS-D según altitud (hover y volando)
.venv/bin/python -m engineering.validation        # modelo vs fichas DJI M4E y M400
.venv/bin/python -m engineering.sizing            # recalcula todo (≈ 2.5 min) y regenera el informe
.venv/bin/pytest -q engineering/tests             # 26 pruebas de ingeniería
```

- Informe completo: `docs/ingenieria/diseno_preliminar.md` (ábrelo en VS Code con Ctrl+Shift+V para verlo formateado).
- Requisitos que usa el cálculo: `engineering/config/design_cases.yaml`. Si cambias uno (por ejemplo la autonomía o la carga), recalcula.

## 9. Plan e informe

- Excel de seguimiento: `docs/plan/DronSwarm_Plan_de_Trabajo.xlsx` (hoja Dashboard).
- Informe de los sprints S01-S02: el documento compartido en claude.ai.

## Opcional: mapa y telemetría con QGroundControl

Instala [QGroundControl](https://docs.qgroundcontrol.com/master/en/qgc-user-guide/getting_started/download_and_install.html) en Windows y ábrelo antes de la demo del paso 2: PX4 envía la telemetría a UDP 14550, y con `networkingMode=mirrored` de tu WSL debería conectarse solo y mostrar los drones en el mapa. *No verificado todavía.*

## Si algo falla

| Síntoma | Solución |
|---|---|
| Gazebo se cierra al abrir con cámaras | Terminal sin la variable de GPU: `source ~/.bashrc` o `export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA` |
| "PX4 server already running" | Ya se limpia solo; si persiste: `pkill -x px4; rm -f /tmp/px4_lock-* /tmp/px4-sock-*` |
| La demo se queda esperando | Ctrl+C y repetir; con más de 6 drones la simulación va más lenta que el tiempo real |
| `make px4_sitl gz_x500` sin `gz_bridge` | `rm -rf ~/src/PX4-Autopilot/build/px4_sitl_default && make -C ~/src/PX4-Autopilot px4_sitl` |
