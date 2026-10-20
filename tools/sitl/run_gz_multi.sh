#!/usr/bin/env bash
# N drones PX4 (x500) en Gazebo sin ventana: despegue simultáneo + medición de capacidad del PC.
#
#   bash tools/sitl/run_gz_multi.sh 6 [carpeta_de_salida]
#   MODEL=x500_mono_cam bash tools/sitl/run_gz_multi.sh 3     # drones con cámara (render en GPU)
#   GUI=1 HOLD=60 bash tools/sitl/run_gz_multi.sh 6            # con ventana de Gazebo, 60 s en el aire
#   GUI=1 MISSION=formation bash tools/sitl/run_gz_multi.sh 4  # demo: formación recorre un cuadrado de 30 m
#   GUI=1 MISSION=delivery PAYLOAD_KG=0.5 bash tools/sitl/run_gz_multi.sh 1   # entrega con caja de 0.5 kg
#   GUI=1 MODEL=ds_d bash tools/sitl/run_gz_multi.sh 1          # nuestro DS-D (con su caja de 5 kg)
#   GUI=1 MODELS=ds_i,ds_i,ds_d,ds_h MISSION=formation bash tools/sitl/run_gz_multi.sh   # enjambre mixto
#   GUI=1 SCENE=coop bash tools/sitl/run_gz_multi.sh            # 3 DS-D levantan juntos una caja de 10 kg
#   GUI=1 SCENE=swarm bash tools/sitl/run_gz_multi.sh 6         # S06: enjambre de 6 DS-I (formación, cruce, torre)
#   SCENE=swarm MODEL=ds_d MISSION=fault MISSION_ARGS="--case motor" bash tools/sitl/run_gz_multi.sh 1   # fallas
#   SPACING=12 SCENE=swarm MODELS=ds_i,ds_i,ds_i,ds_i,ds_i,ds_i MISSION=sector bash tools/sitl/run_gz_multi.sh  # HU-08
#
# GPU: en laptops híbridas OpenGL usa por defecto la GPU integrada. Este script fuerza la NVIDIA
# (MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA); para probar otra: GPU_ADAPTER=AMD bash ...
#
# Mide el factor de tiempo real (RTF) de Gazebo, CPU y RAM mientras los N drones vuelan.
# RTF ≈ 1.0 = la simulación corre a tiempo real; < 0.8 = el PC ya no da abasto.
set -euo pipefail

N="${1:-1}"
[[ "$N" =~ ^[0-9]+$ ]] || N=1
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
# Servidores de Gazebo que hayan quedado de corridas interrumpidas: dos mundos "default" mezclan los tópicos
# (un servidor viejo con el mismo mundo "default" comparte /world/default/clock con el nuevo: PX4 ve saltos de tiempo)
stale_gz() { for p in $(pgrep -x ruby 2>/dev/null); do grep -q "gz" "/proc/$p/cmdline" 2>/dev/null && echo "$p"; done; }
for p in $(stale_gz); do kill "$p" 2>/dev/null; done
sleep 2
for p in $(stale_gz); do kill -9 "$p" 2>/dev/null; done

[[ -x "$BUILD/bin/px4-gz_bridge" ]] || { echo "PX4 sin soporte de Gazebo: rm -rf $BUILD && make -C $PX4_DIR px4_sitl" >&2; exit 1; }
# shellcheck disable=SC1091
set +u; . "$BUILD/rootfs/gz_env.sh"; set -u   # GZ_SIM_RESOURCE_PATH, PX4_GZ_WORLDS (el archivo de PX4 usa variables sin definir)

# Modelos y airframes propios (DS-I, DS-D, DS-H generados por tools/gen_sdf.py)
export GZ_SIM_RESOURCE_PATH="$REPO/simulation/xtdrone/models:${GZ_SIM_RESOURCE_PATH:-}"
cp -f "$REPO"/simulation/px4/airframes/*_gz_* "$BUILD/etc/init.d-posix/airframes/" 2>/dev/null || true
# Plugins propios de seguridad: falla física de motor (en cada modelo DS) y monitor de separación (mundo swarm)
SAFETY="$REPO/simulation/plugins/safety"
[[ -f "$SAFETY/build/libdronswarm-motor-failure-system.so" ]] || \
    { cmake -S "$SAFETY" -B "$SAFETY/build" >/dev/null && cmake --build "$SAFETY/build" -j >/dev/null; }
export GZ_SIM_SYSTEM_PLUGIN_PATH="$SAFETY/build:${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"

# Carga útil: se genera una variante del x500 con una caja de PAYLOAD_KG kg fija bajo el cuerpo
if [[ -n "${PAYLOAD_KG:-}" ]]; then
    mdir="$OUT/models/x500_payload"
    mkdir -p "$mdir"
    "${PY:-python3}" - "$mdir" "$PAYLOAD_KG" <<'PYEOF'
import sys
d, m = sys.argv[1], float(sys.argv[2])
a, b, c = 0.15, 0.15, 0.08                     # caja de 15 × 15 × 8 cm
ixx, iyy, izz = m * (b*b + c*c) / 12, m * (a*a + c*c) / 12, m * (a*a + b*b) / 12
open(f"{d}/model.config", "w").write("<?xml version='1.0'?><model><name>x500_payload</name><sdf version='1.9'>model.sdf</sdf></model>\n")
open(f"{d}/model.sdf", "w").write(f"""<?xml version='1.0'?>
<sdf version='1.9'>
  <model name='x500_payload'>
    <include merge='true'><uri>x500</uri></include>
    <link name='payload'>
      <pose relative_to='base_link'>0 0 -0.02 0 0 0</pose>
      <inertial><mass>{m}</mass><inertia><ixx>{ixx}</ixx><iyy>{iyy}</iyy><izz>{izz}</izz><ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>
      <visual name='payload_visual'>
        <geometry><box><size>{a} {b} {c}</size></box></geometry>
        <material><ambient>0.9 0.45 0.1 1</ambient><diffuse>0.9 0.45 0.1 1</diffuse></material>
      </visual>
    </link>
    <joint name='payload_joint' type='fixed'><parent>base_link</parent><child>payload</child></joint>
  </model>
</sdf>
""")
PYEOF
    export GZ_SIM_RESOURCE_PATH="$OUT/models:${GZ_SIM_RESOURCE_PATH:-}"
    export MODEL="x500_payload"
fi

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
WORLD_FILE="${WORLD_FILE:-$PX4_GZ_WORLDS/$WORLD.sdf}"
if [[ "${SCENE:-}" == "mine" ]]; then                    # mundo de mina (tools/gen_world.py): tajo, faja, relavera, viento
    WORLD_FILE="$REPO/simulation/xtdrone/worlds/mine.sdf"
fi
if [[ "${SCENE:-}" == "swarm" ]]; then                   # S06: campo plano con torre de iluminación y monitor de separación
    WORLD_FILE="$REPO/simulation/xtdrone/worlds/swarm.sdf"
    export DRONSWARM_MONITOR_CSV="$OUT/monitor.csv"
    [[ "$MODEL" == "x500" ]] && export MODEL="ds_i"
    export MISSION="${MISSION:-swarm}"
fi
if [[ "${SCENE:-}" == "delivery" ]]; then                # mina + DS-D con gancho y caja de 5 kg que se suelta en destino
    WORLD_FILE="$REPO/simulation/xtdrone/worlds/mine_delivery.sdf"
    export GZ_SIM_SYSTEM_PLUGIN_PATH="$REPO/simulation/plugins/tether/build:${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"
    export MODEL="ds_d_hook" MISSION="${MISSION:-release}"
fi
if [[ "${SCENE:-}" == "coop" ]]; then                    # mundo con el plugin de cuerdas (tools/gen_coop.py)
    WORLD_FILE="$REPO/simulation/xtdrone/worlds/coop.sdf"
    export GZ_SIM_SYSTEM_PLUGIN_PATH="$REPO/simulation/plugins/tether/build:${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"
    [[ -f "$REPO/simulation/plugins/tether/build/libdronswarm-tether-system.so" ]] || \
        { cmake -S "$REPO/simulation/plugins/tether" -B "$REPO/simulation/plugins/tether/build" >/dev/null && \
          cmake --build "$REPO/simulation/plugins/tether/build" -j >/dev/null; }
fi
setsid gz sim --verbose=1 -r -s --headless-rendering "$WORLD_FILE" > "$OUT/gz_server.log" 2>&1 &
GZ_PID=$!
for _ in $(seq 1 120); do
    gz topic -l 2>/dev/null | grep -q "^/world/$WORLD/clock" && break
    sleep 1
done
gz topic -l | grep -q "^/world/$WORLD/clock" || { echo "Gazebo no arrancó" >&2; exit 1; }
echo "Gazebo listo (pid $GZ_PID)"

if [[ "${SCENE:-}" == "delivery" ]]; then
    gz service -s "/world/$WORLD/create" --reqtype gz.msgs.EntityFactory --reptype gz.msgs.Boolean --timeout 10000 \
        --req "sdf_filename: \"$REPO/simulation/xtdrone/models/delivery_box/model.sdf\", name: \"delivery_box\"" >/dev/null \
        && echo "Caja de entrega creada bajo el dron"
    sleep 1
fi

# Escena de carga cooperativa (tools/gen_coop.py): la caja con cuerdas se crea ANTES que los drones
POSE_LIST=()
if [[ "${SCENE:-}" == "coop" ]]; then
    layout="$REPO/simulation/xtdrone/models/coop_layout.json"
    MODELS="$("$PY" -c "import json;print(','.join(json.load(open('$layout'))['models']))")"
    IFS=';' read -r -a POSE_LIST <<< "$("$PY" -c "import json;print(';'.join(','.join(str(v) for v in p) for p in json.load(open('$layout'))['poses']))")"
    export MISSION="${MISSION:-coop}"
    LAUNCH_GAP="${LAUNCH_GAP:-5}"           # modelos pesados: dar tiempo a que cada PX4 reciba sus sensores
    gz service -s "/world/$WORLD/create" --reqtype gz.msgs.EntityFactory --reptype gz.msgs.Boolean --timeout 10000 \
        --req "sdf_filename: \"$REPO/simulation/xtdrone/models/coop_payload/model.sdf\", name: \"coop_payload\"" >/dev/null \
        && echo "Caja de carga con cuerdas creada"
    sleep 2
fi
GUI_PID=""
if [[ -n "${GUI:-}" ]]; then
    setsid gz sim -g > "$OUT/gz_gui.log" 2>&1 &
    GUI_PID=$!
    echo "Ventana de Gazebo abierta (se ve en Windows vía WSLg)"
fi

# 2. Una instancia de PX4 por dron, en fila, separados según su tamaño real.
#    MODELS="ds_i,ds_i,ds_d" arma un enjambre mixto (N = cantidad de modelos de la lista).
export MODELS="${MODELS:-}"
IFS=',' read -r -a MODEL_LIST <<< "${MODELS:-}"
if [[ ${#MODEL_LIST[@]} -gt 0 && -n "${MODEL_LIST[0]}" ]]; then N=${#MODEL_LIST[@]}; fi
y_pos=0
for ((i = 0; i < N; i++)); do
    m="${MODEL_LIST[$i]:-$MODEL}"
    read -r width leg_h < <("$PY" - "$REPO/simulation/xtdrone/models/models_summary.json" "$m" <<'PYEOF'
import json, sys
try:
    info = {v["model"]: v for v in json.load(open(sys.argv[1])).values()}.get(sys.argv[2])
except FileNotFoundError:
    info = None
print(f"{max(3.0, info['wheelbase_m'] + 1.5):.2f} {info['leg_height_m'] + 0.05:.2f}" if info else "3.0 0.0")
PYEOF
)
    [[ -n "${SPACING:-}" ]] && width="$SPACING"          # separación fija entre bases (p. ej. 12 m para la HU-08)
    if [[ $i -gt 0 ]]; then y_pos="$(echo "$y_pos + ($prev_width + $width) / 2" | bc -l)"; fi
    prev_width="$width"
    pose="${SPAWN_X:-0},$(printf '%.2f' "$y_pos"),$leg_h"          # SPAWN_X: mover la fila de bases al este/oeste
    [[ -n "${POSE_LIST[$i]:-}" ]] && pose="${POSE_LIST[$i]}"
    autostart=()
    ls "$BUILD/etc/init.d-posix/airframes/"*"_gz_$m" >/dev/null 2>&1 || autostart=(PX4_SYS_AUTOSTART=4001)
    wd="$BUILD/instance_$i"
    # A veces Gazebo tarda en crear el modelo y PX4 aborta ("gz_bridge failed to start and spawn model"):
    # verificar que el dron exista en el mundo y relanzar esa instancia (hasta 3 intentos).
    spawned=0
    for attempt in 1 2 3; do
        rm -rf "$wd" && mkdir -p "$wd"
        rm -f "/tmp/px4_lock-$i" "/tmp/px4-sock-$i"
        (cd "$wd" && env PX4_GZ_STANDALONE=1 PX4_GZ_WORLD="$WORLD" "${autostart[@]}" PX4_SIM_MODEL="gz_$m" \
            PX4_GZ_MODEL_POSE="$pose" setsid "$BUILD/bin/px4" -i "$i" -d "$BUILD/etc" > "$wd/out.log" 2>&1 &)
        for _ in $(seq 1 40); do
            if grep -q "gz_bridge failed" "$wd/out.log" 2>/dev/null; then break; fi
            if gz model --list 2>/dev/null | grep -q -- "- ${m}_$i\$"; then spawned=1; break; fi
            sleep 0.5
        done
        [[ $spawned -eq 1 ]] && break
        echo "  dron $i: no apareció en Gazebo (intento $attempt), relanzando…"
        pkill -f -- "bin/px4 -i $i -d" 2>/dev/null || true
        sleep 2
    done
    [[ $spawned -eq 1 ]] || { echo "  dron $i: no se pudo crear tras 3 intentos" >&2; exit 1; }
    echo "  dron $i: $m en ($pose)"
    sleep "${LAUNCH_GAP:-2}"
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
        echo "topic,${topic:-}" > "$OUT/camera.csv"
        [[ -n "${topic:-}" ]] || exit 0
        for _ in 1 2 3; do
            t0=$(date +%s.%N)
            timeout 30 gz topic -e -t "${topic:-}" -n 20 > /dev/null 2>&1 && \
                echo "fps,$(echo "20 / ($(date +%s.%N) - $t0)" | bc -l)" >> "$OUT/camera.csv"
            sleep 3
        done
    ) &
fi

status=0
mission_script="$REPO/tools/sitl/multi_takeoff.py"
[[ "${MISSION:-}" == "formation" ]] && mission_script="$REPO/tools/sitl/demo_formation.py"
[[ "${MISSION:-}" == "delivery" ]] && mission_script="$REPO/tools/sitl/demo_delivery.py"
[[ "${MISSION:-}" == "coop" ]] && mission_script="$REPO/tools/sitl/demo_coop_lift.py"
[[ "${MISSION:-}" == "inspection" ]] && mission_script="$REPO/control/missions/inspection.py"
[[ "${MISSION:-}" == "release" ]] && mission_script="$REPO/control/missions/delivery.py"
[[ "${MISSION:-}" == "swarm" ]] && mission_script="$REPO/control/swarm/sitl_swarm.py"
[[ "${MISSION:-}" == "fault" ]] && mission_script="$REPO/simulation/xtdrone/scripts/fault_injection.py"
[[ "${MISSION:-}" == "sector" ]] && mission_script="$REPO/control/missions/sector_survey.py"
[[ "${MISSION:-}" == "swarm_dist" ]] && mission_script="$REPO/control/swarm/dist_launch.py"
# MISSION_ARGS: opciones extra de la misión, p. ej. MISSION_ARGS="--loss 0.3 --drop-out 2:40"
# shellcheck disable=SC2086
"$PY" "$mission_script" --n "$N" --hold "${HOLD:-15}" --out "$OUT/takeoff.json" ${MISSION_ARGS:-} || status=$?

# Métricas de seguridad con la posición real (monitor del mundo swarm)
if [[ -s "$OUT/monitor.csv" ]]; then
    (cd "$REPO" && "$PY" -m control.swarm.analyze_monitor "$OUT/monitor.csv" --out "$OUT/seguridad.json" \
        --png "$OUT/trayectorias.png" > /dev/null 2>&1) && "$PY" - "$OUT/seguridad.json" <<'EOF2'
import json, sys
d = json.load(open(sys.argv[1]))
print(f"Seguridad (posición real): separación mínima {d['min_separation_m']} m, colisiones {d['collisions']}, "
      f"torre a {d['min_obstacle_clearance_m']} m")
EOF2
fi

# Logs de vuelo de cada dron (PX4 los cierra al desarmar)
for ((i = 0; i < N; i++)); do
    ulg="$(ls -t "$BUILD/instance_$i"/log/*/*.ulg 2>/dev/null | head -1 || true)"
    [[ -n "$ulg" ]] && cp "$ulg" "$OUT/drone_$i.ulg"
done

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
res["model"] = os.environ.get("MODELS") or os.environ.get("MODEL", "x500")
json.dump(res, open(sys.argv[2], "w"), indent=2)
print(json.dumps(res))
EOF
exit $status
