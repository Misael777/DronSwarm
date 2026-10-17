#!/usr/bin/env bash
# Lanza N instancias de PX4 SIH, mide CPU/RAM mientras N drones despegan a la vez, y apaga todo.
#
#   bash tools/sitl/run_sih_multi.sh 6 [carpeta_de_salida]
set -euo pipefail

N="${1:-6}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PX4_DIR="${PX4_DIR:-$HOME/src/PX4-Autopilot}"
OUT="${2:-$REPO/docs/evidencias/sitl}"
PY="${PY:-$REPO/.venv/bin/python}"
BUILD="$PX4_DIR/build/px4_sitl_default"
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
trap stop_px4 EXIT

mem_used_mb() { free -m | awk '/^Mem:/ {print $3}'; }
base_mem="$(mem_used_mb)"

for ((i = 0; i < N; i++)); do
    wd="$BUILD/instance_$i"
    rm -rf "$wd" && mkdir -p "$wd"
    (cd "$wd" && PX4_SIM_MODEL=sihsim_quadx PX4_SIMULATOR=sihsim \
        "$BUILD/bin/px4" -i "$i" -d "$BUILD/etc" > "$wd/out.log" 2>&1) &
done
echo "$N instancias PX4 SIH lanzadas"

# Muestreo de recursos en segundo plano mientras vuelan
samples="$OUT/multi_resources.csv"
echo "t_s,mem_used_mb,px4_cpu_pct" > "$samples"
(
    t=0
    while pgrep -x px4 >/dev/null; do
        cpu="$(ps -C px4 -o %cpu= | awk '{s+=$1} END {print s+0}')"
        echo "$t,$(mem_used_mb),$cpu" >> "$samples"
        sleep 2; t=$((t + 2))
    done
) &

status=0
"$PY" "$REPO/tools/sitl/multi_takeoff.py" --n "$N" --out "$OUT/multi_takeoff.json" || status=$?

peak_mem="$(awk -F, 'NR>1 && $2>m {m=$2} END {print m}' "$samples")"
peak_cpu="$(awk -F, 'NR>1 && $3>m {m=$3} END {print m}' "$samples")"
cat > "$OUT/multi_resources.json" <<EOF
{"instances": $N, "baseline_mem_mb": $base_mem, "peak_mem_mb": $peak_mem,
 "px4_mem_increase_mb": $((peak_mem - base_mem)), "peak_px4_cpu_pct": $peak_cpu,
 "cpu_cores": $(nproc), "total_mem_mb": $(free -m | awk '/^Mem:/ {print $2}')}
EOF
cat "$OUT/multi_resources.json"
exit $status
