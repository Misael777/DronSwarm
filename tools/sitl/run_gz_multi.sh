#!/usr/bin/env bash
# N drones PX4 (x500) en Gazebo sin ventana: despegue simultáneo + medición de capacidad del PC.
#
#   bash tools/sitl/run_gz_multi.sh 6 [carpeta_de_salida]
#   MODEL=x500_mono_cam bash tools/sitl/run_gz_multi.sh 3     # drones con cámara (render en GPU)
#   GUI=1 HOLD=60 bash tools/sitl/run_gz_multi.sh 6            # con ventana de Gazebo, 60 s en el aire
#   GUI=1 MISSION=formation bash tools/sitl/run_gz_multi.sh 4  # demo: formación recorre un cuadrado de 30 m
#
# GPU: en laptops híbridas OpenGL usa por defecto la GPU integrada. Este script fuerza la NVIDIA
# (MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA); para probar otra: GPU_ADAPTER=AMD bash ...
#
# Mide el factor de tiempo real (RTF) de Gazebo, CPU y RAM mientras los N drones vuelan.
# RTF ≈ 1.0 = la simulación corre a tiempo real; < 0.8 = el PC ya no da abasto.
set -euo pipefail

N="${1:-1}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PX4_DIR="${PX4_DIR:-$HOME/src/PX4-Autopilot}"
BUILD="$PX4_DIR/build/px4_sitl_default"
OUT="${2:-$REPO/docs/evidencias/sitl/gz_n$N}"
PY="${PY:-$REPO/.venv/bin/python}"
WORLD="default"
export MODEL="${MODEL:-x500}"
export MESA_D3D12_DEFAULT_ADAPTER_NAME="${GPU_ADAPTER:-NVIDIA}"
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

[[ -x "$BUILD/bin/px4-gz_bridge" ]] || { echo "PX4 sin soporte de Gazebo: rm -rf $BUILD && make -C $PX4_DIR px4_sitl" >&2; exit 1; }
# shellcheck disable=SC1091
set +u; . "$BUILD/rootfs/gz_env.sh"; set -u   # GZ_SIM_RESOURCE_PATH, PX4_GZ_WORLDS (el archivo de PX4 usa variables sin definir)

GZ_PID=""
cleanup() {
    stop_px4
    [[ -n "${GUI_PID:-}" ]] && kill -- -"$GUI_PID" 2>/dev/null || true
    [[ -n "$GZ_PID" ]] && kill -- -"$GZ_PID" 2>/dev/null || true
}
trap cleanup EXIT

mem_used_mb() { free -m | awk '/^Mem:/ {print $3}'; }
base_mem="$(mem_used_mb)"

# 1. Servidor de Gazebo en su propia sesión (para poder apagarlo entero)
setsid gz sim --verbose=1 -r -s --headless-rendering "$PX4_GZ_WORLDS/$WORLD.sdf" > "$OUT/gz_server.log" 2>&1 &
GZ_PID=$!
for _ in $(seq 1 120); do
    gz topic -l 2>/dev/null | grep -q "^/world/$WORLD/clock" && break
    sleep 1
done
gz topic -l | grep -q "^/world/$WORLD/clock" || { echo "Gazebo no arrancó" >&2; exit 1; }
echo "Gazebo listo (pid $GZ_PID)"
GUI_PID=""
if [[ -n "${GUI:-}" ]]; then
    setsid gz sim -g > "$OUT/gz_gui.log" 2>&1 &
    GUI_PID=$!
    echo "Ventana de Gazebo abierta (se ve en Windows vía WSLg)"
fi

# 2. Una instancia de PX4 por dron, separados 3 m en una fila
for ((i = 0; i < N; i++)); do
    wd="$BUILD/instance_$i"
    rm -rf "$wd" && mkdir -p "$wd"
    (cd "$wd" && PX4_GZ_STANDALONE=1 PX4_GZ_WORLD="$WORLD" PX4_SYS_AUTOSTART=4001 PX4_SIM_MODEL="gz_$MODEL" \
        PX4_GZ_MODEL_POSE="0,$((i * 3))" setsid "$BUILD/bin/px4" -i "$i" -d "$BUILD/etc" > "$wd/out.log" 2>&1 &)
    sleep 2
done
echo "$N instancias PX4 lanzadas"

# 3. Muestreo de RTF, RAM y CPU mientras vuelan
samples="$OUT/resources.csv"
echo "t_s,rtf,mem_used_mb,cpu_pct,gpu_pct,gpu_mem_mb" > "$samples"
(
    t=0
    while kill -0 "$GZ_PID" 2>/dev/null; do
        rtf="$(timeout 5 gz topic -e -t "/world/$WORLD/stats" -n 1 2>/dev/null | awk '/real_time_factor/ {print $2; exit}')"
        cpu="$( { ps -C px4 -o %cpu=; ps -s "$GZ_PID" -o %cpu=; } | awk '{s+=$1} END {print s+0}')"
        gpu="$(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits 2>/dev/null | tr -d ' ' || echo ",")"
        echo "$t,${rtf:-},$(mem_used_mb),$cpu,${gpu:-,}" >> "$samples"
        sleep 2; t=$((t + 2))
    done
) &

# 4. Si el modelo tiene cámara: cuadros por segundo reales (reloj de pared) de la cámara del dron 0
if [[ "$MODEL" == *cam* || "$MODEL" == *depth* ]]; then
    (
        sleep 15
        topic="$(gz topic -l | grep -m 1 -E '^/camera$|/image$' || true)"  # los modelos de PX4 publican en /camera (compartido entre drones)
        echo "topic,$topic" > "$OUT/camera.csv"
        for _ in 1 2 3; do
            t0=$(date +%s.%N)
            timeout 30 gz topic -e -t "$topic" -n 20 > /dev/null 2>&1 && \
                echo "fps,$(echo "20 / ($(date +%s.%N) - $t0)" | bc -l)" >> "$OUT/camera.csv"
            sleep 3
        done
    ) &
fi

status=0
mission_script="$REPO/tools/sitl/multi_takeoff.py"
[[ "${MISSION:-}" == "formation" ]] && mission_script="$REPO/tools/sitl/demo_formation.py"
"$PY" "$mission_script" --n "$N" --hold "${HOLD:-15}" --out "$OUT/takeoff.json" || status=$?

"$PY" - "$samples" "$OUT/resources.json" "$N" "$base_mem" <<'EOF'
import csv, json, sys
rows = list(csv.DictReader(open(sys.argv[1])))
rtf = sorted(float(r["rtf"]) for r in rows[3:] if r["rtf"])  # sin las muestras del arranque
mem = [int(r["mem_used_mb"]) for r in rows]
cpu = [float(r["cpu_pct"]) for r in rows]
res = {"drones": int(sys.argv[3]), "samples": len(rows),
       "rtf_median": round(rtf[len(rtf) // 2], 3) if rtf else None, "rtf_p10": round(rtf[len(rtf) // 10], 3) if rtf else None,
       "mem_increase_mb": max(mem) - int(sys.argv[4]) if mem else None,
       "cpu_peak_pct": max(cpu) if cpu else None, "cpu_mean_pct": round(sum(cpu) / len(cpu), 1) if cpu else None}
gpu = [float(r["gpu_pct"]) for r in rows if r.get("gpu_pct")]
gmem = [float(r["gpu_mem_mb"]) for r in rows if r.get("gpu_mem_mb")]
res.update({"gpu_peak_pct": max(gpu) if gpu else None, "gpu_mean_pct": round(sum(gpu) / len(gpu), 1) if gpu else None,
            "gpu_mem_peak_mb": max(gmem) if gmem else None})
import os
cam = os.path.join(os.path.dirname(sys.argv[2]), "camera.csv")
if os.path.exists(cam):
    fps = [float(l.split(",")[1]) for l in open(cam) if l.startswith("fps,")]
    res["camera_fps_mean"] = round(sum(fps) / len(fps), 1) if fps else None
res["gpu_adapter"] = os.environ.get("MESA_D3D12_DEFAULT_ADAPTER_NAME")
res["model"] = os.environ.get("MODEL", "x500")
json.dump(res, open(sys.argv[2], "w"), indent=2)
print(json.dumps(res))
EOF
exit $status
