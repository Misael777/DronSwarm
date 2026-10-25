#!/usr/bin/env bash
# Compila PX4 para la controladora DronSwarm FMU v1: copia el target al árbol de PX4 y corre make.
#   bash electronics/fc/build_px4.sh [default|bootloader]      (PX4 en $PX4_DIR, por defecto ~/src/PX4-Autopilot)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PX4_DIR="${PX4_DIR:-$HOME/src/PX4-Autopilot}"
LABEL="${1:-default}"
export PATH="$HOME/.local/opt/gcc-arm-none-eabi-9-2020-q2-update/bin:$HOME/.venvs/px4/bin:$PATH"
rm -rf "$PX4_DIR/boards/dronswarm/fmu-v1"
mkdir -p "$PX4_DIR/boards/dronswarm"
cp -r "$HERE/px4/boards/dronswarm/fmu-v1" "$PX4_DIR/boards/dronswarm/"
make -C "$PX4_DIR" "dronswarm_fmu-v1_${LABEL}"
ls -l "$PX4_DIR/build/dronswarm_fmu-v1_${LABEL}/"*.px4 "$PX4_DIR/build/dronswarm_fmu-v1_${LABEL}/"*.bin 2>/dev/null || true
