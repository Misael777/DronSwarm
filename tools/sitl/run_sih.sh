#!/usr/bin/env bash
# PX4 SITL con el simulador interno SIH (sin Gazebo) + prueba de humo MAVSDK.
# Sirve para CI y para máquinas sin entorno gráfico.
#
#   bash tools/sitl/run_sih.sh [carpeta_de_salida]
#
# PX4_DIR (por defecto ~/src/PX4-Autopilot) debe estar compilado con `make px4_sitl`.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PX4_DIR="${PX4_DIR:-$HOME/src/PX4-Autopilot}"
OUT="${1:-$REPO/docs/evidencias/sitl}"
PY="${PY:-$REPO/.venv/bin/python}"
ROOTFS="$PX4_DIR/build/px4_sitl_default/rootfs"

[[ -x "$PX4_DIR/build/px4_sitl_default/bin/px4" ]] || { echo "Compila PX4 primero: make -C $PX4_DIR px4_sitl" >&2; exit 1; }
mkdir -p "$OUT"
# Detiene todas las instancias de PX4 y espera a que terminen (SIGKILL tras 10 s): una corrida
# siguiente que arranca mientras la anterior se cierra encuentra el bloqueo tomado ("server already running")
stop_px4() {
    pkill -x px4 2>/dev/null || true
    for _ in $(seq 1 20); do pgrep -x px4 >/dev/null || break; sleep 0.5; done
    pkill -9 -x px4 2>/dev/null || true
    rm -f /tmp/px4_lock-* /tmp/px4-sock-*
}
stop_px4

# Arranque limpio: sin parámetros ni logs de corridas anteriores
rm -f "$ROOTFS"/parameters*.bson "$ROOTFS"/dataman
(cd "$ROOTFS" && PX4_SIM_MODEL=sihsim_quadx PX4_SIMULATOR=sihsim \
    "$PX4_DIR/build/px4_sitl_default/bin/px4" -d > "$OUT/px4_console.log" 2>&1) &
PX4_PID=$!
trap stop_px4 EXIT

echo "PX4 SIH arrancando (pid $PX4_PID)…"
status=0
"$PY" "$REPO/tools/sitl/smoke_test.py" --url udpin://0.0.0.0:14540 --alt 10 --hold 10 --out "$OUT/smoke_test.json" || status=$?

ulog="$(ls -t "$ROOTFS"/log/*/*.ulg 2>/dev/null | head -1 || true)"
[[ -n "$ulog" ]] && cp "$ulog" "$OUT/smoke_test.ulg" && echo "Log de vuelo: $OUT/smoke_test.ulg"
exit $status
