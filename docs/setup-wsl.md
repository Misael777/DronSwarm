# Entorno de desarrollo en WSL2

Máquina de referencia (medida el 2026-10-17): Ubuntu 22.04.2 en WSL2, 14 núcleos, 10 GB de RAM asignados a WSL (`.wslconfig`), GPU NVIDIA visible (`nvidia-smi`).

## Nivel 1 · Sin sudo (ya instalado)

| Componente | Dónde | Para qué |
|---|---|---|
| PX4 v1.15.4 (clon superficial) | `~/src/PX4-Autopilot` | Firmware y SITL |
| Entorno de compilación de PX4 | `~/.venvs/px4` (cmake 3.31, ninja, deps Python) | `make px4_sitl` sin apt |
| Entorno Python del repo | `.venv/` (`uv`) | Cálculos, MAVSDK, pruebas |
| OpenSCAD 2021.01 | `~/.local/opt/openscad/AppRun` | CAD paramétrico (agente) |
| FreeCAD 1.0.2 (incluye CalculiX y gmsh) | `~/.local/opt/freecad/AppRun` | Conversión a STEP en línea de comandos, FEA |

Compilar y probar:

```bash
export PATH=$HOME/.venvs/px4/bin:$PATH
make -C ~/src/PX4-Autopilot px4_sitl          # ≈ 1 min con 14 núcleos
bash tools/sitl/run_sih.sh                     # 1 dron: despegue, hover, aterrizaje
bash tools/sitl/run_sih_multi.sh 6             # 6 drones a la vez + medición de CPU/RAM
```

SIH es el simulador interno de PX4: no tiene gráficos ni Gazebo, pero ejecuta el mismo firmware y responde a los mismos comandos MAVLink. Es el que corre en CI.

## Nivel 2 · Completo (requiere sudo, lo ejecuta el usuario)

```bash
bash tools/setup_wsl.sh          # paquetes base, dependencias de PX4, Gazebo Garden (gz-sim 7), OpenSCAD, entorno Python
bash tools/setup_wsl.sh --ros2   # además ROS 2 Humble + Micro XRCE-DDS Agent
```

Después: `cd ~/src/PX4-Autopilot && make px4_sitl gz_x500` abre Gazebo con un dron (WSLg muestra la ventana en Windows). Sin ventana y con varios drones: `bash tools/sitl/run_gz_multi.sh N`.

**FreeCAD para el usuario:** se recomienda instalar FreeCAD 1.0 en **Windows** y abrir los archivos del repo desde `\\wsl$\Ubuntu-22.04\home\mishaco\DronSwarm\cad\`. Es más fluido que la versión Linux vía WSLg.

## Problemas encontrados y su solución

| Problema | Causa | Solución |
|---|---|---|
| `uv` no instala `Tools/setup/requirements.txt` de PX4 | `matplotlib>=3.0.*` no es una versión válida en PEP 440 | Usar `matplotlib>=3.0` (copia local del archivo) |
| `make px4_sitl` falla en la configuración | cmake 4.x eliminó la compatibilidad con `cmake_minimum_required < 3.5` | Fijar `cmake>=3.24,<4` |
| Falla "Generating git version header" (`IndexError`) | El clon superficial no trae los tags de NuttX | `git -C platforms/nuttx/NuttX/nuttx tag nuttx-11.0.0` (ya lo hace `setup_wsl.sh`) |
| `mavsdk` 4.x rompe `System()` | En 2026 el paquete `mavsdk` pasó a ser el binding nativo, con otra API | Usar `mavsdk-grpc` (`from mavsdk_grpc import System`) |
| OpenSCAD no exporta PNG | Sin OpenGL fuera de pantalla en WSL | `tools/cad/render_stl.py` (matplotlib) |
| `setup_wsl.sh` termina con "ninja: no work to do" y PX4 no tiene `gz_bridge` | El build se configuró antes de instalar Gazebo | `rm -rf build/px4_sitl_default && make px4_sitl` (≈ 3 min) |
| PX4 no coloca el dron en Gazebo ("Service call timed out") | Sin `PX4_GZ_WORLD` PX4 no arranca el servidor de Gazebo | `run_gz_multi.sh` arranca el servidor, espera el reloj del mundo y conecta PX4 con `PX4_GZ_STANDALONE=1` |
| Al fallar, PX4 mata la terminal que lo lanzó | Comparte el grupo de procesos | Lanzar con `setsid` |
| Motor caído: PX4 no lo detecta en SITL y el dron cae (S06) | El puente de Gazebo no reporta corriente ni motor en `esc_status`; el detector de PX4 necesita ambos | Parche `simulation/px4/patches/0001-gz-esc-telemetria.patch` (lo aplica `setup_wsl.sh`; a mano: `git -C ~/src/PX4-Autopilot apply <parche> && make px4_sitl`) |
| Saltos de tiempo y "Yaw estimate error" en PX4 | Un servidor de Gazebo de una corrida anterior seguía vivo con el mismo mundo `default` (mismo reloj) | `run_gz_multi.sh` mata los servidores viejos, con SIGKILL si no responden |
| Un script que espera "a que no haya simulaciones" espera para siempre | `pgrep -f` también ve la línea de comandos del shell que lo contiene | Patrón anclado: `pgrep -f "^bash .*run_gz_multi\.sh"` |
| Docker no responde en WSL | La integración de Docker Desktop con esta distro está desactivada | Activarla en Docker Desktop → Settings → Resources → WSL integration (opcional) |

## Capacidad del PC para simular el enjambre (S01-05, 2026-10-17)

Medido con `tools/sitl/run_gz_multi.sh N`: Gazebo Garden sin ventana, N drones x500 despegando a la vez (5 a 5+2(N-1) m), PX4 v1.15.4.

| Drones | Factor de tiempo real (mediana) | RTF p10 | RAM extra | CPU media | Resultado |
|---|---|---|---|---|---|
| 1 | 0.98 | 0.97 | 180 MB | 0.8 núcleos | 1/1 despegó y aterrizó |
| 3 | 0.99 | 0.98 | 190 MB | 1.9 núcleos | 3/3 |
| 6 | 0.98 | 0.96 | 270 MB | 3.5 núcleos | 6/6 |
| 9 | 0.79 | 0.63 | 370 MB | 4.3 núcleos | 9/9, más lento que el tiempo real |
| 12 | 0.56 | 0.39 | ≈ 0.5 GB | 4.8 núcleos | No terminó en 6 min |

**Conclusión:** el PC simula **6 drones en tiempo real** y 9 a ~80 % de velocidad (válido para probar lógica, no tiempos). El límite no es la RAM (< 1 GB de 10) ni los núcleos (≈ 5 de 14 en uso): es la física de Gazebo, que avanza en un solo hilo. Para enjambres más grandes: SIH (6 drones = 2 núcleos) o reducir la frecuencia de física del mundo. Evidencia: `docs/evidencias/sitl/gz_n*/`.

## GPU (2026-10-17)

La laptop es híbrida: **AMD Radeon integrada + NVIDIA GeForce RTX 3050 Ti Laptop** (4 GB VRAM, Ampere, compute 8.6, CUDA 12.5 en el driver 555.97). WSL expone ambas.

| Uso | Estado | Cómo |
|---|---|---|
| CUDA (IA, visión) | Funciona | PyTorch 2.6 + cu124 en `~/.venvs/gpu` (aparte del repo: ~2.5 GB). Matmul 4096²: CPU 0.27 TFLOPS · GPU fp32 3.4 (12×) · GPU fp16 10.7 (39×) |
| OpenGL (Gazebo: ventana y sensores de cámara/LiDAR) | Funciona **solo forzando la NVIDIA** | `export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA` (ya en `~/.bashrc` y en `setup_wsl.sh`) |
| Física de Gazebo | No usa GPU | Corre en CPU, un hilo: la GPU no sube el límite de ~6 drones en tiempo real |

Por defecto OpenGL elige la **AMD integrada**, y con ella Gazebo se cae (segmentation fault) al renderizar cámaras. Con la NVIDIA: 1 y 3 drones con cámara (`x500_mono_cam`, 640×480 a 30 Hz) vuelan con RTF 0.98, hasta 37 % de GPU y ≈ 0.5 GB de VRAM. Evidencia: `docs/evidencias/sitl/gpu/`.

```bash
MODEL=x500_mono_cam bash tools/sitl/run_gz_multi.sh 3        # drones con cámara en la NVIDIA
~/.venvs/gpu/bin/python -c "import torch; print(torch.cuda.get_device_name(0))"
```

Dónde rinde en el plan: cámaras y LiDAR simulados de las misiones (S05), detección de grietas/idlers con visión artificial (entrenar YOLO pequeño cabe en 4 GB con batch reducido), OpenDroneMap con extracción de características en GPU (S14), y AirSim/Unreal si se usa (4 GB es justo).
