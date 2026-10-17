#!/usr/bin/env bash
# Instala el entorno de simulación de DronSwarm en WSL2 (Ubuntu 22.04).
#
#   bash tools/setup_wsl.sh            # PX4 v1.15 + Gazebo Garden (gz-sim 7) + entorno Python del repo
#   bash tools/setup_wsl.sh --ros2     # además ROS 2 Humble + Micro XRCE-DDS Agent
#
# Requiere sudo (pide la contraseña una vez). Es idempotente: se puede volver a ejecutar.
# Versiones fijadas: ver docs/decisiones.md (ADR-002).
set -euo pipefail

PX4_VERSION="v1.15.4"
PX4_DIR="${PX4_DIR:-$HOME/src/PX4-Autopilot}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WITH_ROS2=0
[[ "${1:-}" == "--ros2" ]] && WITH_ROS2=1

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }

# --- 0. Verificaciones -------------------------------------------------------
. /etc/os-release
if [[ "${VERSION_ID}" != "22.04" ]]; then
    echo "Este script es para Ubuntu 22.04 (encontrado: ${PRETTY_NAME})." >&2
    exit 1
fi
sudo -v

# --- 1. Paquetes base --------------------------------------------------------
log "Paquetes base"
sudo apt-get update
sudo apt-get install -y git git-lfs curl wget build-essential cmake ninja-build \
    python3-pip python3-venv libfuse2 openscad

# --- 2. PX4 + Gazebo Garden (gz-sim 7) -------------------------------------------------
if [[ ! -d "$PX4_DIR/.git" ]]; then
    log "Clonando PX4 $PX4_VERSION en $PX4_DIR"
    mkdir -p "$(dirname "$PX4_DIR")"
    git clone --depth 1 --branch "$PX4_VERSION" --recurse-submodules --shallow-submodules \
        https://github.com/PX4/PX4-Autopilot.git "$PX4_DIR"
fi
# El clon superficial no trae los tags de NuttX y el generador de versión de PX4 los necesita
git -C "$PX4_DIR/platforms/nuttx/NuttX/nuttx" tag nuttx-11.0.0 2>/dev/null || true

log "Dependencias de PX4 (incluye Gazebo Garden (gz-sim 7))"
bash "$PX4_DIR/Tools/setup/ubuntu.sh" --no-nuttx

log "Compilando PX4 SITL"
make -C "$PX4_DIR" px4_sitl

# --- 3. ROS 2 Humble (opcional) ----------------------------------------------
if [[ $WITH_ROS2 -eq 1 ]]; then
    log "ROS 2 Humble"
    if [[ ! -f /etc/apt/sources.list.d/ros2.list ]]; then
        sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
            -o /usr/share/keyrings/ros-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu jammy main" | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null
        sudo apt-get update
    fi
    sudo apt-get install -y ros-humble-ros-base ros-dev-tools
    if ! command -v MicroXRCEAgent >/dev/null; then
        log "Micro XRCE-DDS Agent (puente PX4 ↔ ROS 2)"
        tmp="$(mktemp -d)"
        git clone --depth 1 --branch v2.4.2 https://github.com/eProsima/Micro-XRCE-DDS-Agent.git "$tmp/agent"
        cmake -S "$tmp/agent" -B "$tmp/agent/build"
        cmake --build "$tmp/agent/build" -j"$(nproc)"
        sudo cmake --install "$tmp/agent/build"
        sudo ldconfig
    fi
    grep -q "ros/humble/setup.bash" ~/.bashrc || echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
fi

# --- 4. GPU ------------------------------------------------------------------
# En laptops híbridas OpenGL usa la GPU integrada por defecto; con ella Gazebo se cae al renderizar
# cámaras. Forzar la NVIDIA (WSL la expone vía D3D12).
if nvidia-smi >/dev/null 2>&1 && ! grep -q MESA_D3D12_DEFAULT_ADAPTER_NAME ~/.bashrc; then
    printf '\n# DronSwarm: OpenGL en la GPU NVIDIA\nexport MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA\n' >> ~/.bashrc
fi

# --- 5. Entorno Python del repo ----------------------------------------------
log "Entorno Python del repo"
if ! command -v uv >/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
cd "$REPO_DIR"
[[ -d .venv ]] || uv venv .venv
uv pip install --python .venv/bin/python -r pyproject.toml --extra dev
git lfs install --local

log "Listo. Prueba rápida:"
echo "  cd $PX4_DIR && make px4_sitl gz_x500        # un dron en Gazebo"
echo "  bash $REPO_DIR/tools/sitl/run_sih.sh        # PX4 sin Gazebo + prueba de despegue/aterrizaje"
