#!/usr/bin/env bash
# DronSwarm · Consola de pruebas
#
#   ./dronswarm.sh              menú interactivo
#   ./dronswarm.sh demo [N]     demo de formación con ventana (N drones, por defecto 4)
#   ./dronswarm.sh sih          prueba de vuelo sin gráficos + gráfica
#   ./dronswarm.sh tests        lint + pruebas automáticas
#   ./dronswarm.sh estado       diagnóstico del entorno
#
# Los resultados de cada corrida quedan en logs/<prueba>-<fecha>/ (carpeta ignorada por git).
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$REPO/.venv/bin/python"
PX4_DIR="${PX4_DIR:-$HOME/src/PX4-Autopilot}"
BUILD="$PX4_DIR/build/px4_sitl_default"
LOGS="$REPO/logs"
REPORT_URL="https://claude.ai/code/artifact/a7037c35-535a-4140-9774-32aebfa1fe00"
REALTIME_MAX=6   # drones que este PC simula en tiempo real (medido en S01-05)
export MESA_D3D12_DEFAULT_ADAPTER_NAME="${MESA_D3D12_DEFAULT_ADAPTER_NAME:-NVIDIA}"   # ADR-009

TITLE="DronSwarm · Consola de pruebas"
H=22
W=78
export NEWT_COLORS='
root=white,black
window=white,black
border=cyan,black
shadow=black,black
title=brightcyan,black
button=black,cyan
actbutton=white,blue
compactbutton=white,black
listbox=white,black
actlistbox=black,cyan
actsellistbox=black,cyan
sellistbox=white,black
checkbox=white,black
actcheckbox=black,cyan
entry=white,black
label=white,black
textbox=white,black
acttextbox=black,cyan
helpline=black,cyan
roottext=cyan,black'

B=$'\e[1m'; C=$'\e[36m'; G=$'\e[32m'; R=$'\e[31m'; Y=$'\e[33m'; D=$'\e[2m'; N=$'\e[0m'

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

banner() {
    clear
    printf '%s%s' "$C" "$B"
    cat <<'EOF'
   ___                 ___
  |   \ _ _ ___ _ _   / __|_ __ ____ _ _ _ _ __
  | |) | '_/ _ \ ' \  \__ \ V  V / _` | '_| '  \
  |___/|_| \___/_||_| |___/\_/\_/\__,_|_| |_|_|_|
EOF
    printf '%s%s  Drones de bajo costo para minería · enjambre · 5,000 msnm%s\n\n' "$N" "$D" "$N"
}

has_whiptail() { command -v whiptail >/dev/null && [[ -t 0 && -t 1 ]]; }

# whiptail escribe la elección en stderr: se intercambian los descriptores
wt() { whiptail --backtitle "$TITLE" --yes-button "Sí" --no-button "No" --ok-button "Aceptar" --cancel-button "Volver" "$@" 3>&1 1>&2 2>&3; }

msg() { wt --title "$1" --msgbox "$2" "$H" "$W"; }

pause() {
    echo
    read -rp "${D}Presiona Enter para volver al menú…${N}" _
}

new_run_dir() {
    local d
    d="$LOGS/$1-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$d"
    echo "$d"
}

open_in_windows() {
    if command -v explorer.exe >/dev/null && command -v wslpath >/dev/null; then
        explorer.exe "$(wslpath -w "$1")" >/dev/null 2>&1 || true
    else
        echo "Abrir manualmente: $1"
    fi
}

stop_sims() {
    pkill -x px4 2>/dev/null || true
    local p
    for p in $(pgrep -x ruby 2>/dev/null); do
        grep -q "gz" "/proc/$p/cmdline" 2>/dev/null && kill "$p" 2>/dev/null
    done
    sleep 1
    pkill -9 -x px4 2>/dev/null || true
    rm -f /tmp/px4_lock-* /tmp/px4-sock-* 2>/dev/null || true
}

ok()   { printf '  %s✔%s %s\n' "$G" "$N" "$1"; }
fail() { printf '  %s✘%s %s\n' "$R" "$N" "$1"; }

# Encabezado de una prueba en la terminal
header() {
    banner
    printf '%s▶ %s%s\n' "$B" "$1" "$N"
    [[ -n "${2:-}" ]] && printf '%s  %s%s\n' "$D" "$2" "$N"
    printf '%s  Ctrl+C para detener%s\n\n' "$D" "$N"
}

# Resumen legible de los JSON que dejan las pruebas
summarize() {
    "$PY" - "$1" <<'EOF'
import json, os, sys
d = sys.argv[1]
out = []
def load(name):
    p = os.path.join(d, name)
    return json.load(open(p)) if os.path.exists(p) else None
t = load("takeoff.json")
if t:
    out.append(f"Drones que completaron la misión: {t.get('ok')}/{t.get('n')}")
    if t.get("duration_s"):
        out.append(f"Duración de la misión: {t['duration_s']} s")
    for e in t.get("errors", []):
        out.append(f"Error: {e}")
s = load("smoke_test.json")
if s:
    out.append(f"Altura objetivo: {s['target_alt_m']} m · alcanzada: {s['reached_alt_m']} m")
    out.append(f"Error máximo en hover: {s['hold_max_error_m']} m")
    out.append(f"Aterrizó y desarmó: {'sí' if s.get('disarmed') else 'no'}")
r = load("resources.json")
if r:
    rtf = r.get("rtf_median")
    if rtf is not None:
        verdict = "tiempo real" if rtf >= 0.95 else ("más lento que el tiempo real" if rtf >= 0.7 else "muy lento: demasiados drones")
        out.append(f"Velocidad de la simulación: {rtf:.2f} × tiempo real ({verdict})")
    if r.get("cpu_mean_pct") is not None:
        out.append(f"CPU media: {r['cpu_mean_pct'] / 100:.1f} núcleos · RAM extra: {r.get('mem_increase_mb')} MB")
    if r.get("gpu_peak_pct") is not None:
        out.append(f"GPU ({r.get('gpu_adapter')}): pico {r['gpu_peak_pct']:.0f} % · VRAM {r.get('gpu_mem_peak_mb'):.0f} MB")
passed = (t or s or {}).get("passed")
head = "RESULTADO: OK" if passed else ("RESULTADO: FALLÓ" if passed is False else "RESULTADO: sin datos (¿se interrumpió?)")
print(head + "\n\n" + "\n".join(out) + f"\n\nArchivos: {d}")
EOF
}

finish_run() {
    local dir="$1" rc="$2" text
    text="$(summarize "$dir" 2>/dev/null || echo "Sin resumen disponible. Archivos: $dir")"
    echo
    if [[ "$rc" -eq 0 ]]; then printf '%s%s✔ Terminó correctamente%s\n' "$G" "$B" "$N"; else printf '%s%s✘ Terminó con errores (código %s)%s\n' "$R" "$B" "$rc" "$N"; fi
    printf '%s\n' "$text" | sed "1s/.*/${B}&${N}/"
    pause
}

require_px4() {
    if [[ ! -x "$BUILD/bin/px4-gz_bridge" ]]; then
        msg "PX4 no está listo" "PX4 no está compilado con soporte de Gazebo.\n\nEjecuta:\n  bash tools/setup_wsl.sh\no bien:\n  rm -rf $BUILD && make -C $PX4_DIR px4_sitl"
        return 1
    fi
}

choose_drones() {
    local default="${1:-4}"
    wt --title "Número de drones" --radiolist \
        "¿Cuántos drones?\n\nEste PC simula hasta $REALTIME_MAX en tiempo real; más de eso funciona, pero más lento." \
        "$H" "$W" 6 \
        1 "1 dron" "$([[ $default == 1 ]] && echo ON || echo OFF)" \
        2 "2 drones" "$([[ $default == 2 ]] && echo ON || echo OFF)" \
        3 "3 drones" "$([[ $default == 3 ]] && echo ON || echo OFF)" \
        4 "4 drones" "$([[ $default == 4 ]] && echo ON || echo OFF)" \
        6 "6 drones (máximo en tiempo real)" "$([[ $default == 6 ]] && echo ON || echo OFF)" \
        9 "9 drones (≈ 80 % de velocidad)" "$([[ $default == 9 ]] && echo ON || echo OFF)"
}

ask_gui() {
    wt --title "Ventana de Gazebo" --yes-button "Con ventana" --no-button "Sin ventana" \
        --yesno "¿Abrir la ventana 3D de Gazebo?\n\nCon ventana ves los drones (se abre en Windows).\nSin ventana es más rápido y sirve para medir." 12 "$W"
}

# ---------------------------------------------------------------------------
# Acciones
# ---------------------------------------------------------------------------

act_formation() {
    require_px4 || return
    local n="${1:-}" gui=1 dir rc
    if [[ -z "$n" ]]; then
        n="$(choose_drones 4)" || return
        ask_gui || gui=""
    fi
    dir="$(new_run_dir formacion)"
    header "Enjambre en formación · $n drones" "Despegan a 10 m, recorren un cuadrado de 30 m manteniendo la formación y aterrizan (≈ 1.5 min)."
    GUI="$gui" MISSION=formation bash "$REPO/tools/sitl/run_gz_multi.sh" "$n" "$dir" 2>&1 | grep --line-buffered -vE "Warning|^\s*$|^[{}]|^\s+\""
    rc=${PIPESTATUS[0]}
    finish_run "$dir" "$rc"
}

act_takeoff() {
    require_px4 || return
    local n gui=1 dir rc hold
    n="$(choose_drones 6)" || return
    ask_gui || gui=""
    hold="$(wt --title "Tiempo en el aire" --inputbox "Segundos que los drones se quedan en el aire:" 10 "$W" 30)" || return
    dir="$(new_run_dir despegue)"
    header "Despegue simultáneo · $n drones" "Cada dron sube a una altura distinta (5, 7, 9… m), espera ${hold} s y aterriza."
    GUI="$gui" HOLD="$hold" bash "$REPO/tools/sitl/run_gz_multi.sh" "$n" "$dir" 2>&1 | grep --line-buffered -vE "Warning|^\s*$|^[{}]|^\s+\""
    rc=${PIPESTATUS[0]}
    finish_run "$dir" "$rc"
}

act_camera() {
    require_px4 || return
    local n dir rc
    n="$(wt --title "Drones con cámara" --radiolist "¿Cuántos drones con cámara (640×480, 30 Hz)?" 12 "$W" 3 \
        1 "1 dron" ON 2 "2 drones" OFF 3 "3 drones" OFF)" || return
    msg "Cómo ver la cámara" "Cuando se abra Gazebo:\n\n  1. Menú ⋮ (arriba a la derecha)\n  2. Buscar 'Image Display' y agregarlo\n  3. Elegir el tópico /camera\n\nLos drones se quedan 60 s en el aire.\nLa cámara usa la GPU NVIDIA."
    dir="$(new_run_dir camara)"
    header "Drones con cámara · $n" "Render de la cámara en la GPU NVIDIA."
    GUI=1 MODEL=x500_mono_cam HOLD=60 bash "$REPO/tools/sitl/run_gz_multi.sh" "$n" "$dir" 2>&1 | grep --line-buffered -vE "Warning|^\s*$|^[{}]|^\s+\""
    rc=${PIPESTATUS[0]}
    finish_run "$dir" "$rc"
}

act_delivery() {
    require_px4 || return
    local kg gui=1 base load rc1 rc2
    kg="$(wt --title "Entrega con carga" --radiolist \
        "Peso de la caja de carga.\n\nVista previa con el x500 de PX4 (2 kg, empuje máx. ≈ 3.5 kg): la caja va fija; el dron de carga real (5 kg) y el mecanismo que la suelta llegan en S05/S08.\n\nSe hacen 2 vuelos (sin y con carga) para comparar el empuje (≈ 3.5 min)." \
        "$H" "$W" 3 0.3 "0.3 kg" OFF 0.5 "0.5 kg (recomendado)" ON 0.8 "0.8 kg (cerca del límite)" OFF)" || return
    ask_gui || gui=""
    base="$(new_run_dir entrega-sin-carga)"
    header "Entrega · vuelo 1 de 2: sin carga" "Vuela 60 m, baja a 3 m, entrega, vuelve y aterriza."
    GUI="$gui" MISSION=delivery bash "$REPO/tools/sitl/run_gz_multi.sh" 1 "$base" 2>&1 | grep --line-buffered -vE "Warning|^\s*$|^[{}]|^\s+\""
    rc1=${PIPESTATUS[0]}
    load="$(new_run_dir entrega-${kg}kg)"
    header "Entrega · vuelo 2 de 2: con ${kg} kg" "La caja naranja va fija bajo el dron."
    GUI="$gui" MISSION=delivery PAYLOAD_KG="$kg" bash "$REPO/tools/sitl/run_gz_multi.sh" 1 "$load" 2>&1 | grep --line-buffered -vE "Warning|^\s*$|^[{}]|^\s+\""
    rc2=${PIPESTATUS[0]}
    echo
    "$PY" - "$base/drone_0.ulg" "$load/drone_0.ulg" "$kg" "$REPO/tools/sitl" <<'EOF2'
import sys
sys.path.insert(0, sys.argv[4])
from flight_stats import stats
try:
    a, b = stats(sys.argv[1]), stats(sys.argv[2])
except Exception as e:
    print(f"No se pudo comparar: {e}"); raise SystemExit
kg = sys.argv[3]
row = lambda name, x, y: print(f"  {name:<34}{x:>12}{y:>14}")
print(f"\033[1mCOMPARACIÓN\033[0m\n")
row("", "Sin carga", f"Con {kg} kg")
row("Empuje en vuelo estacionario", f"{a['hover_thrust']:.0%}", f"{b['hover_thrust']:.0%}")
row("Margen de empuje restante", f"{a['thrust_margin']:.0%}", f"{b['thrust_margin']:.0%}")
row("Pico de empuje", f"{a['peak_thrust']:.0%}", f"{b['peak_thrust']:.0%}")
print()
if b["peak_thrust"] >= 0.97:
    print("  ⚠ Con carga los motores llegan al tope: sin margen para viento o maniobras.")
print("  Nuestros drones se diseñan con empuje ≥ 2× el peso a 5,000 msnm (S04).")
EOF2
    [[ $rc1 -eq 0 && $rc2 -eq 0 ]] && printf '\n%s✔ Ambos vuelos completaron la entrega%s\n' "$G" "$N" || printf '\n%s✘ Algún vuelo falló (ver %s y %s)%s\n' "$R" "$base" "$load" "$N"
    pause
}

act_engineering() {
    local opt="" tmp
    while true; do
        opt="$(wt --title "Ingeniería · S03 y S04" --default-item "${opt:-informe}" --menu "Cálculos de diseño de DS-I y DS-D:" "$H" "$W" 8 \
            informe "Leer el informe de diseño preliminar (S04)" \
            autonomia "Autonomía según altitud (hover y volando)" \
            validacion "Validación del modelo contra DJI (S03-07)" \
            requisitos "Ver los requisitos usados (design_cases.yaml)" \
            recalcular "Recalcular el dimensionamiento (≈ 2.5 min)" \
            tests "Pruebas de ingeniería" \
            carpeta "Abrir la carpeta de resultados en Windows" \
            volver "Volver")" || return
        case "$opt" in
            informe)
                wt --title "Informe de diseño preliminar" --scrolltext --textbox "$REPO/docs/ingenieria/diseno_preliminar.md" "$H" 110 ;;
            autonomia)
                tmp="$(mktemp)"
                (cd "$REPO" && "$PY" -m engineering.endurance_table) > "$tmp" 2>&1
                wt --title "Autonomía según altitud" --scrolltext --textbox "$tmp" "$H" "$W"
                rm -f "$tmp" ;;
            validacion)
                tmp="$(mktemp)"
                (cd "$REPO" && "$PY" - <<'EOF2'
import json
from engineering.validation import calibrate
r = calibrate()
print("Calibración con el DJI M4E y verificación con el DJI M400")
print("(fichas técnicas en docs/referencias/dji/)\n")
print(f"{'Dron':30s}{'Rol':14s}{'Ficha':>8s}{'Modelo':>9s}{'Error':>8s}")
for c in r["cases"]:
    print(f"{c['name']:30s}{c['role']:14s}{c['spec_hover_min']:>6.0f} m{c['predicted_min']:>7.1f} m{c['error_pct']:>+7.1f}%")
print(f"\nFactor de calibración: {r['cd0_scale']}")
print("Criterio: error < 10 % en el M400. Estado: NO cumplido (-13 %).")
print("El error es conservador: el modelo predice MENOS autonomía que la real,")
print("así que los diseños salen algo más grandes de lo necesario, nunca más débiles.")
print("Validación definitiva: banco de empuje en S10.")
EOF2
                ) > "$tmp" 2>&1
                wt --title "Validación del modelo" --scrolltext --textbox "$tmp" "$H" "$W"
                rm -f "$tmp" ;;
            requisitos)
                wt --title "Requisitos usados (editar en VS Code y recalcular)" --scrolltext --textbox "$REPO/engineering/config/design_cases.yaml" "$H" "$W" ;;
            recalcular)
                header "Recalcular el dimensionamiento" "Calibra el modelo, barre ~1,800 combinaciones por escenario y regenera el informe."
                (cd "$REPO" && "$PY" -m engineering.sizing)
                pause ;;
            tests)
                header "Pruebas de ingeniería"
                (cd "$REPO" && "$REPO/.venv/bin/pytest" -q engineering/tests)
                pause ;;
            carpeta) open_in_windows "$REPO/engineering/data/results" ;;
            volver) return ;;
        esac
    done
}

run_ours() {   # $1 = título, $2 = descripción, resto = variables de entorno para run_gz_multi.sh
    local title="$1" desc="$2" gui=1 dir rc
    shift 2
    require_px4 || return
    ask_gui || gui=""
    dir="$(new_run_dir "nuestros")"
    header "$title" "$desc"
    env GUI="$gui" "$@" bash "$REPO/tools/sitl/run_gz_multi.sh" 1 "$dir" 2>&1 | grep --line-buffered -vE "Warning|^\s*$|^[{}]|^\s+\""
    rc=${PIPESTATUS[0]}
    finish_run "$dir" "$rc"
}

show_swarm_plot() {
    local last
    last="$(ls -td "$LOGS"/nuestros-* 2>/dev/null | head -1)"
    [[ -f "$last/trayectorias.png" ]] && wt --title "Trayectorias" --yesno "¿Abrir la vista en planta de las trayectorias (posición real)?" 8 "$W" \
        && open_in_windows "$last/trayectorias.png"
}

act_ours() {
    local opt="" last
    if [[ ! -f "$REPO/simulation/xtdrone/models/ds_i/model.sdf" ]]; then
        msg "Faltan los modelos" "Genera primero los modelos desde el dimensionamiento:\n\n  .venv/bin/python tools/gen_sdf.py\n  .venv/bin/python tools/gen_coop.py"
        return
    fi
    while true; do
        opt="$(wt --title "Nuestros drones (S05-S06)" --default-item "${opt:-enjambre}" --menu \
            "Modelos generados desde el dimensionamiento del S04 (peso, inercias, motores a 4,500 msnm):" "$H" "$W" 19 \
            enjambre "Enjambre de 6 DS-I: formación en V, torre, círculo, cruce y regreso (S06)" \
            enjambre_dist "Enjambre DISTRIBUIDO: un proceso por dron, como en las computadoras a bordo (S13)" \
            enjambre_radio "Enjambre con radio mala: 30 % de pérdida y un dron que se queda sin radio" \
            sectores "HU-08: 6 drones levantan un área por sectores y 'abortar todo'" \
            montecarlo "Simulador rápido sin Gazebo: 50 corridas del enjambre (≈ 1 min)" \
            falla_motor "Falla: DS-D pierde un motor en vuelo" \
            falla_gps "Falla: pérdida de GNSS" \
            falla_bateria "Falla: batería crítica → retorno a casa" \
            falla_enlace "Falla: pérdida de enlace con la estación → retorno a casa" \
            geocerca "HU-10: geocerca (misión rechazada, el dron no la cruza)" \
            inspeccion "Mina: inspección del tajo (grilla fotogramétrica + órbita de talud)" \
            entrega "Mina: entrega al fondo del tajo con liberación de la caja" \
            viento "Mina: DS-I resistiendo viento de 8 m/s con ráfagas" \
            tamanos "Los 3 tamaños lado a lado: DS-I, DS-D y DS-H" \
            dsd "DS-D: entrega con su caja de 5 kg" \
            dsh "DS-H: entrega con su caja de 10 kg (8 motores)" \
            mixto "Enjambre mixto en formación (2 DS-I + DS-D + DS-H)" \
            coop "Carga cooperativa: 3 DS-D levantan una caja de 10 kg" \
            dsi "DS-I solo: despegue y aterrizaje" \
            volver "Volver")" || return
        case "$opt" in
            inspeccion) run_ours "Inspección del tajo" "DS-I: 5 líneas a 109 m (GSD 3 cm/px, 55 fotos) y una órbita dentro del tajo (≈ 7 min)." \
                            SCENE=mine MODEL=ds_i MISSION=inspection
                        [[ -f "$(ls -td "$LOGS"/nuestros-* | head -1)/inspeccion.png" ]] && wt --title "Recorrido" --yesno "¿Abrir el mapa del recorrido y las fotos en Windows?" 8 "$W" \
                            && open_in_windows "$(ls -td "$LOGS"/nuestros-* | head -1)/inspeccion.png" ;;
            entrega) run_ours "Entrega con liberación" "DS-D lleva una caja de 5 kg colgada al fondo del tajo (170 m, −60 m), la apoya, la suelta y vuelve (≈ 4 min)." \
                         SCENE=delivery ;;
            viento) run_ours "Viento en la mina" "DS-I se mantiene en el aire 30 s con viento de 8 m/s del oeste y ráfagas." \
                        SCENE=mine MODEL=ds_i HOLD=30 ;;
            tamanos) run_ours "Los 3 tamaños" "DS-I (2.7 kg), DS-D (15.6 kg con 5 kg) y DS-H (30 kg con 10 kg) suben a la vez." \
                         MODELS=ds_i,ds_d,ds_h HOLD=30 ;;
            dsd) run_ours "DS-D con 5 kg" "Vuela 60 m, baja a 3 m, entrega, vuelve y aterriza." MODEL=ds_d MISSION=delivery ;;
            dsh) run_ours "DS-H con 10 kg" "Vuela 60 m, baja a 3 m, entrega, vuelve y aterriza." MODEL=ds_h MISSION=delivery ;;
            mixto) run_ours "Enjambre mixto" "Recorren juntos un cuadrado de 30 m." MODELS=ds_i,ds_i,ds_d,ds_h MISSION=formation ;;
            coop)
                msg "Carga cooperativa" "3 DS-D (sin caja propia) levantan juntos una caja de 10 kg colgada de cuerdas de 3.2 m, la trasladan 15 m y aterrizan (≈ 2.5 min).\n\nLas cuerdas se ven como líneas negras en la ventana de Gazebo.\n\nVista previa: cada dron usa su control PX4 normal, así que la carga no se reparte en partes iguales (eso es control cooperativo, v2)."
                run_ours "Carga cooperativa (10 kg)" "Despegue → subida conjunta → traslado → aterrizaje." SCENE=coop ;;
            dsi) run_ours "DS-I" "Despegue, hover y aterrizaje." MODEL=ds_i ;;
            enjambre) run_ours "Enjambre de 6 DS-I" "Consenso + evitación + radio simulada. Forman en V, pasan una torre de iluminación, hacen un círculo, cruzan todos por el centro y vuelven en línea (≈ 5 min)." \
                          SCENE=swarm MODELS=ds_i,ds_i,ds_i,ds_i,ds_i,ds_i
                      show_swarm_plot ;;
            enjambre_dist) run_ours "Enjambre distribuido (6 nodos + tierra)" "Cada dron corre su propio nodo y se comunica por la red con la radio emulada; la tierra solo secuencia las fases (≈ 6 min)." \
                               SCENE=swarm MODELS=ds_i,ds_i,ds_i,ds_i,ds_i,ds_i MISSION=swarm_dist
                           show_swarm_plot ;;
            enjambre_radio) run_ours "Enjambre con radio mala" "30 % de paquetes perdidos y el dron 2 se queda sin radio a los 40 s: se detiene, sube 8 m y los demás lo esquivan (≈ 5 min)." \
                                SCENE=swarm MODELS=ds_i,ds_i,ds_i,ds_i,ds_i,ds_i MISSION_ARGS="--loss 0.3 --drop-out 2:40"
                            show_swarm_plot ;;
            sectores) run_ours "Levantamiento por sectores (HU-08)" "Área de 240 × 180 m en 6 sectores, cada dron en su capa de altura (30-80 m). A los 90 s: abortar todo → los 6 vuelven a casa. Criterio: nunca a menos de 10 m entre drones (≈ 6 min)." \
                          SPACING=12 SPAWN_X=-20 SCENE=swarm MODELS=ds_i,ds_i,ds_i,ds_i,ds_i,ds_i MISSION=sector
                      last="$(ls -td "$LOGS"/nuestros-* | head -1)"
                      [[ -f "$last/sectores.png" ]] && wt --title "Sectores" --yesno "¿Abrir el mapa de sectores y recorridos?" 8 "$W" \
                          && open_in_windows "$last/sectores.png" ;;
            geocerca) run_ours "Geocerca (HU-10)" "Geocerca de 70 × 70 m: una misión que la cruza debe ser rechazada y una orden de salir debe terminar en retorno a casa." \
                          SCENE=swarm MODEL=ds_i MISSION=fault MISSION_ARGS="--case geofence" ;;
            montecarlo)
                header "Simulador rápido del enjambre" "50 corridas con viento, ruido de GNSS y radio simulada; cuenta colisiones con la posición real."
                (cd "$REPO" && "$PY" -m control.swarm.sim_kinematic --runs 50)
                pause ;;
            falla_motor) run_ours "Falla de motor" "DS-D (6 motores) a 20 m y 50 m al este: se apaga un motor; 15 s después se ordena aterrizar." \
                             SCENE=swarm MODEL=ds_d MISSION=fault MISSION_ARGS="--case motor" ;;
            falla_gps) run_ours "Pérdida de GNSS" "DS-I a 20 m y 50 m al este: se pierde el GNSS; PX4 debe aterrizar sin alejarse." \
                           SCENE=swarm MODEL=ds_i MISSION=fault MISSION_ARGS="--case gps" ;;
            falla_bateria) run_ours "Batería crítica" "DS-I a 50 m de casa: la batería cae a 6 %; PX4 debe volver y aterrizar en casa." \
                               SCENE=swarm MODEL=ds_i MISSION=fault MISSION_ARGS="--case battery" ;;
            falla_enlace) run_ours "Pérdida de enlace" "DS-I a 50 m de casa: se corta el enlace con la estación; PX4 debe volver solo." \
                              SCENE=swarm MODEL=ds_i MISSION=fault MISSION_ARGS="--case link" ;;
            volver) return ;;
        esac
    done
}

act_stories() {
    wt --title "Historias de usuario (borrador para el Gate G0)" --scrolltext --textbox "$REPO/docs/requisitos/historias-usuario.md" "$H" "$W"
}

act_manual() {
    require_px4 || return
    msg "Dron manual (consola de PX4)" "Se abre Gazebo con un dron y la consola de PX4 (pxh>).\n\nComandos útiles:\n  commander takeoff     despegar\n  commander land        aterrizar\n  commander status      estado\n  listener vehicle_local_position   posición\n  shutdown              salir y volver al menú"
    header "Dron manual" "Escribe los comandos en el prompt pxh>"
    stop_sims
    (cd "$PX4_DIR" && make px4_sitl gz_x500)
    stop_sims
    pause
}

act_sih() {
    local dir rc
    if [[ ! -x "$BUILD/bin/px4" ]]; then require_px4 || return; fi
    dir="$(new_run_dir sih)"
    header "Prueba de vuelo sin gráficos (SIH)" "Despegue a 10 m, hover de 10 s, aterrizaje; luego la gráfica del vuelo (≈ 1.5 min)."
    bash "$REPO/tools/sitl/run_sih.sh" "$dir" 2>&1 | grep --line-buffered -vE "Warning|^\s*$|^[{}]|^\s+\""
    rc=${PIPESTATUS[0]}
    if [[ -f "$dir/smoke_test.ulg" ]]; then
        "$PY" "$REPO/tools/sitl/plot_flight.py" "$dir/smoke_test.ulg" "$dir/vuelo.png" >/dev/null 2>&1 && \
            printf '\n%sGráfica: %s/vuelo.png%s\n' "$C" "$dir" "$N"
    fi
    finish_run "$dir" "$rc"
    if [[ -f "$dir/vuelo.png" ]] && has_whiptail && wt --title "Gráfica" --yesno "¿Abrir la gráfica del vuelo en Windows?" 8 "$W"; then
        open_in_windows "$dir/vuelo.png"
    fi
}

act_capacity() {
    require_px4 || return
    local n dir rc
    n="$(choose_drones 6)" || return
    dir="$(new_run_dir capacidad)"
    header "Capacidad del PC · $n drones" "Mide velocidad de la simulación, CPU, RAM y GPU sin ventana."
    bash "$REPO/tools/sitl/run_gz_multi.sh" "$n" "$dir" 2>&1 | grep --line-buffered -vE "Warning|^\s*$|^[{}]|^\s+\""
    rc=${PIPESTATUS[0]}
    finish_run "$dir" "$rc"
}

act_tests() {
    header "Pruebas automáticas" "Lint (ruff) + pruebas (pytest)"
    local rc=0
    printf '%sLint%s\n' "$B" "$N"
    "$REPO/.venv/bin/ruff" check "$REPO" || rc=1
    printf '\n%sPruebas%s\n' "$B" "$N"
    (cd "$REPO" && "$REPO/.venv/bin/pytest" -q) || rc=1
    echo
    if [[ $rc -eq 0 ]]; then printf '%s%s✔ Todo pasó%s\n' "$G" "$B" "$N"; else printf '%s%s✘ Hay fallas%s\n' "$R" "$B" "$N"; fi
    pause
}

act_cad_piece() {
    local files=() f items=() choice dir rc
    while IFS= read -r f; do files+=("$f"); done < <(cd "$REPO" && find cad/openscad -name '*.scad' | sort)
    if [[ ${#files[@]} -eq 0 ]]; then msg "CAD" "No hay piezas en cad/openscad/."; return; fi
    for f in "${files[@]}"; do items+=("$f" ""); done
    choice="$(wt --title "CAD · Exportar pieza" --menu "Elige la pieza OpenSCAD a exportar (STL + STEP + FreeCAD):" "$H" "$W" 10 "${items[@]}")" || return
    header "Exportar pieza CAD" "$choice → STL (impresión/simulación) + STEP (FreeCAD) + .FCStd"
    (cd "$REPO" && bash tools/cad/export_scad.sh "$choice" --fcstd) 2>&1 | grep -E '^\{|ERROR|error'
    rc=${PIPESTATUS[0]}
    local name; name="$(basename "${choice%.scad}")"
    dir="$REPO/cad/exports"
    if [[ $rc -eq 0 ]]; then
        "$PY" "$REPO/tools/cad/render_stl.py" "$dir/$name.stl" "$dir/$name.png" --title "$name" >/dev/null 2>&1
        printf '\n%s✔ Exportado:%s\n  %s/%s.stl\n  %s/%s.step\n  %s\n' "$G" "$N" "$dir" "$name" "$dir" "$name" "$(ls "$REPO"/cad/freecad/*/"$name".FCStd 2>/dev/null)"
        pause
        local opt
        opt="$(wt --title "Pieza exportada" --menu "¿Qué quieres abrir?" 14 "$W" 3 \
            imagen "Ver la imagen de la pieza" \
            carpeta "Abrir la carpeta de FreeCAD en Windows" \
            nada "Volver al menú")" || return
        case "$opt" in
            imagen) open_in_windows "$dir/$name.png" ;;
            carpeta) open_in_windows "$(dirname "$(ls "$REPO"/cad/freecad/*/"$name".FCStd | head -1)")" ;;
        esac
    else
        printf '\n%s✘ La exportación falló%s\n' "$R" "$N"
        pause
    fi
}

build_frame_ui() {   # $1 = grupo (inspection|delivery), $2 = nombre
    local g="$1" name="$2" pre rc
    pre="$([[ $g == inspection ]] && echo ds-i || echo ds-d)"
    header "Frame $name" "Piezas STL/STEP, DXF de corte, ensamble de FreeCAD, interferencias y masas (≈ $([[ $g == inspection ]] && echo 2 || echo 5) min)."
    (cd "$REPO" && "$PY" tools/cad/build_frame.py "$g") 2>&1 | grep -vE '^\s+"|^\{|^\}' | tail -25
    rc=${PIPESTATUS[0]}
    if [[ $rc -eq 0 ]]; then
        "$PY" "$REPO/tools/cad/render_stl.py" "$REPO/cad/exports/$g/$pre""_ensamble.stl" "$REPO/cad/exports/$g/$pre""_ensamble.png" --title "$name" >/dev/null 2>&1
        printf '\n%s✔ Ensamble para revisar en FreeCAD:%s cad/freecad/%s/%s_ensamble_generado.FCStd\n' "$G" "$N" "$g" "$pre"
    fi
    pause
}

act_cad() {
    local opt="" g pre
    while true; do
        opt="$(wt --title "CAD y FEA (S07-S08)" --default-item "${opt:-dsi}" --menu "Frames generados desde la spec v1 (OpenSCAD → FreeCAD):" "$H" "$W" 9 \
            dsi "Construir el frame DS-I (≈ 2 min)" \
            dsd "Construir el frame DS-D (≈ 5 min)" \
            fea "Correr el FEA de los dos frames + informe (≈ 9 min)" \
            img "Ver las imágenes de los ensambles" \
            masas "Masas del CAD contra el presupuesto del S04" \
            freecad "Abrir la carpeta de FreeCAD en Windows (ensambles generados)" \
            pieza "Exportar una pieza suelta (STL + STEP + FCStd)" \
            volver "Volver")" || return
        case "$opt" in
            dsi) build_frame_ui inspection "DS-I" ;;
            dsd) build_frame_ui delivery "DS-D" ;;
            fea) header "FEA de los frames" "gmsh + CalculiX: soportes de motor, bloques, tren de aterrizaje, gancho y modal de brazos."
                 (cd "$REPO" && "$PY" tools/fea/run_fea.py inspection && "$PY" tools/fea/run_fea.py delivery && "$PY" tools/fea/fea_report.py)
                 pause ;;
            img) for g in inspection delivery; do pre="$([[ $g == inspection ]] && echo ds-i || echo ds-d)"
                     [[ -f "$REPO/cad/exports/$g/$pre""_ensamble.stl" && ! -f "$REPO/cad/exports/$g/$pre""_ensamble.png" ]] && \
                         "$PY" "$REPO/tools/cad/render_stl.py" "$REPO/cad/exports/$g/$pre""_ensamble.stl" "$REPO/cad/exports/$g/$pre""_ensamble.png" >/dev/null 2>&1
                     [[ -f "$REPO/cad/exports/$g/$pre""_ensamble.png" ]] && open_in_windows "$REPO/cad/exports/$g/$pre""_ensamble.png"; done ;;
            masas) local tmp; tmp="$(mktemp)"
                   (cd "$REPO" && "$PY" - > "$tmp" <<'EOF2'
import json
for g, n in (("inspection", "DS-I"), ("delivery", "DS-D")):
    try:
        d = json.load(open(f"cad/exports/{g}/masas.json"))
    except FileNotFoundError:
        print(f"{n}: falta construir el frame"); continue
    print(f"{n}: frame {d['frame_cad_kg']:.3f} kg en CAD (+6 % tornillería) vs {d['frame_budget_kg']:.3f} kg del S04")
    for k, v in d["categories"].items():
        print(f"   {k:<40} {v['cad_kg']:.3f} kg  (S04 {v['budget_kg']})")
    print()
EOF2
                   ); wt --title "Masas del CAD" --scrolltext --textbox "$tmp" "$H" "$W"; rm -f "$tmp" ;;
            freecad) open_in_windows "$REPO/cad/freecad" ;;
            pieza) act_cad_piece ;;
            volver) return ;;
        esac
    done
}

plan_summary() {
    "$PY" - "$REPO" <<'EOF'
import sys
from pathlib import Path
from openpyxl import load_workbook
repo = Path(sys.argv[1])
ws = load_workbook(repo / "docs/plan/DronSwarm_Plan_de_Trabajo.xlsx")["Tareas"]
sprints, total_h, done_h = {}, 0.0, 0.0
pending = []
for r in range(2, ws.max_row + 1):
    tid, spr, name, hours, state, pct = (ws[f"{c}{r}"].value for c in "ABDIKL")
    if not tid:
        continue
    eff = 1.0 if state == "Hecho" else 0.0 if state in (None, "", "Pendiente") else float(pct or 0)
    s = sprints.setdefault(spr, [0.0, 0.0])
    s[0] += hours; s[1] += hours * eff
    total_h += hours; done_h += hours * eff
    if state in ("En revisión", "Bloqueado", "En curso"):
        pending.append(f"  {tid}  {state:<12} {name[:48]}")
print(f"Avance global: {done_h / total_h:.1%}  ({done_h:.0f} de {total_h:.0f} h)\n")
print("Sprints con avance:")
for spr, (h, d) in sprints.items():
    if d > 0:
        bar = "█" * round(d / h * 20) + "░" * (20 - round(d / h * 20))
        print(f"  {spr}  {bar} {d / h:4.0%}")
print("\nTareas abiertas (en curso, en revisión o bloqueadas):")
print("\n".join(pending) or "  ninguna")
EOF
}

act_plan() {
    local opt
    while true; do
        opt="$(wt --title "Plan de trabajo" --menu "Seguimiento del plan (24 sprints):" "$H" "$W" 6 \
            ver "Ver el avance" \
            actualizar "Actualizar el estado de una tarea" \
            excel "Abrir el Excel en Windows" \
            informe "Ver el enlace del informe de sprints" \
            volver "Volver")" || return
        case "$opt" in
            ver) wt --title "Avance del plan" --scrolltext --msgbox "$(plan_summary 2>&1)" "$H" "$W" ;;
            actualizar) plan_update ;;
            excel) open_in_windows "$REPO/docs/plan/DronSwarm_Plan_de_Trabajo.xlsx" ;;
            informe) msg "Informe de sprints" "Informe S01-S02 (claude.ai):\n\n$REPORT_URL" ;;
            volver) return ;;
        esac
    done
}

plan_update() {
    local tid state hours args
    msg "Antes de actualizar" "Cierra el Excel si lo tienes abierto: el archivo se regenera\n(el progreso registrado se conserva)."
    tid="$(wt --title "Actualizar tarea" --inputbox "ID de la tarea (por ejemplo S01-06):" 10 "$W")" || return
    tid="${tid^^}"
    state="$(wt --title "Estado de $tid" --menu "Nuevo estado:" 15 "$W" 5 \
        "Pendiente" "" "En curso" "" "En revisión" "" "Bloqueado" "" "Hecho" "")" || return
    hours="$(wt --title "Horas reales" --inputbox "Horas reales trabajadas en $tid (vacío = no cambiar):" 10 "$W")" || return
    args="$tid=$state"
    [[ -n "$hours" ]] && args="$args:$hours"
    if out="$("$PY" "$REPO/tools/plan/generar_plan_trabajo.py" --set "$args" 2>&1)"; then
        msg "Tarea actualizada" "$tid → $state\n\n$(echo "$out" | tail -1)"
    else
        msg "No se pudo actualizar" "$out"
    fi
}

status_text() {
    {
        echo "ENTORNO"
        [[ -x "$PY" ]] && ok "Entorno Python del repo (.venv)" || fail "Entorno Python: ejecutar tools/setup_wsl.sh"
        [[ -x "$BUILD/bin/px4" ]] && ok "PX4 $(git -C "$PX4_DIR" describe --tags 2>/dev/null) compilado" || fail "PX4 sin compilar"
        [[ -x "$BUILD/bin/px4-gz_bridge" ]] && ok "PX4 con soporte de Gazebo" || fail "PX4 sin soporte de Gazebo"
        local gzv; gzv="$(gz sim --versions 2>/dev/null | head -1)"
        [[ -n "$gzv" ]] && ok "Gazebo $gzv (Garden)" || fail "Gazebo no instalado"
        echo
        echo "GPU"
        local gpu; gpu="$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null)"
        [[ -n "$gpu" ]] && ok "NVIDIA: $gpu" || fail "GPU NVIDIA no visible"
        [[ "$MESA_D3D12_DEFAULT_ADAPTER_NAME" == "NVIDIA" ]] && ok "OpenGL en la NVIDIA (necesario para cámaras)" || fail "OpenGL no forzado a la NVIDIA"
        [[ -x "$HOME/.venvs/gpu/bin/python" ]] && ok "PyTorch + CUDA en ~/.venvs/gpu" || fail "PyTorch + CUDA no instalado (opcional)"
        echo
        echo "CAD"
        { command -v openscad >/dev/null || [[ -x "$HOME/.local/opt/openscad/AppRun" ]]; } && ok "OpenSCAD" || fail "OpenSCAD no encontrado"
        { command -v freecadcmd >/dev/null || [[ -x "$HOME/.local/opt/freecad/AppRun" ]]; } && ok "FreeCAD (línea de comandos)" || fail "FreeCAD no encontrado"
        echo
        echo "CAPACIDAD MEDIDA (S01-05)"
        echo "  6 drones en tiempo real · 9 al 80 % · 12 al 55 %"
        echo
        echo "PROCESOS"
        local n; n="$(pgrep -xc px4 2>/dev/null || true)"
        [[ "${n:-0}" -gt 0 ]] && echo "  ${n} instancia(s) de PX4 corriendo (usa 'Detener simulaciones')" || echo "  Ninguna simulación corriendo"
    } | sed 's/\x1b\[[0-9;]*m//g'
}

act_status() {
    if has_whiptail; then
        wt --title "Estado del entorno" --scrolltext --msgbox "$(status_text)" "$H" "$W"
    else
        banner; status_text; pause
    fi
}

act_clean() {
    stop_sims
    msg "Listo" "Se detuvieron todas las instancias de PX4 y Gazebo."
}

act_docs() {
    local opt
    opt="$(wt --title "Documentación" --menu "¿Qué abrir?" 16 "$W" 6 \
        probar "Guía: cómo probar (docs/como-probar.md)" \
        entorno "Entorno, GPU y problemas conocidos (docs/setup-wsl.md)" \
        decisiones "Decisiones técnicas (docs/decisiones.md)" \
        requisitos "Requisitos y targets (docs/requisitos/)" \
        evidencias "Carpeta de evidencias" \
        logs "Carpeta con los resultados de esta consola")" || return
    case "$opt" in
        probar) wt --title "Cómo probar" --scrolltext --textbox "$REPO/docs/como-probar.md" "$H" "$W" ;;
        entorno) wt --title "Entorno" --scrolltext --textbox "$REPO/docs/setup-wsl.md" "$H" "$W" ;;
        decisiones) wt --title "Decisiones" --scrolltext --textbox "$REPO/docs/decisiones.md" "$H" "$W" ;;
        requisitos) open_in_windows "$REPO/docs/requisitos" ;;
        evidencias) open_in_windows "$REPO/docs/evidencias" ;;
        logs) mkdir -p "$LOGS"; open_in_windows "$LOGS" ;;
    esac
}

# ---------------------------------------------------------------------------
# Menú principal
# ---------------------------------------------------------------------------

main_menu() {
    local choice=""
    while true; do
        choice="$(wt --title "Menú principal" --cancel-button "Salir" --default-item "${choice:-N}" --menu \
            "Elige qué quieres probar (flechas + Enter):" 26 "$W" 16 \
            "N" "Nuestros drones: enjambre, fallas, mina y carga cooperativa (S05-S06)" \
            "1" "Demo: enjambre en formación con x500 (con ventana 3D)" \
            "2" "Despegue simultáneo de varios drones" \
            "3" "Drones con cámara (usa la GPU)" \
            "C" "Demo: entrega con carga (compara empuje sin/con carga)" \
            "4" "Dron manual con la consola de PX4" \
            "5" "Prueba de vuelo sin gráficos + gráfica" \
            "6" "Medir capacidad del PC" \
            "7" "Pruebas automáticas (lint + tests)" \
            "8" "CAD y FEA: frames DS-I y DS-D, ensambles de FreeCAD, masas (S07-S08)" \
            "9" "Plan de trabajo: avance y actualizar tareas" \
            "H" "Historias de usuario (para revisar)" \
            "I" "Ingeniería: informe, autonomía, validación (S03-S04)" \
            "E" "Estado del entorno" \
            "D" "Documentación y carpetas" \
            "X" "Detener simulaciones colgadas")" || break
        case "$choice" in
            N) act_ours ;;
            1) act_formation ;;
            2) act_takeoff ;;
            3) act_camera ;;
            C) act_delivery ;;
            4) act_manual ;;
            5) act_sih ;;
            6) act_capacity ;;
            7) act_tests ;;
            8) act_cad ;;
            9) act_plan ;;
            H) act_stories ;;
            I) act_engineering ;;
            E) act_status ;;
            D) act_docs ;;
            X) act_clean ;;
        esac
    done
    clear
    printf '%sHasta luego.%s Resultados guardados en %s\n' "$C" "$N" "$LOGS"
}

# Ctrl+C detiene la prueba en curso pero no cierra la consola
trap 'printf "\n%sInterrumpido%s\n" "$Y" "$N"' INT

case "${1:-}" in
    demo) act_formation "${2:-4}" ;;
    sih) act_sih ;;
    tests) act_tests ;;
    estado) banner; status_text ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//' ;;
    "")
        if has_whiptail; then
            main_menu
        else
            echo "Instala whiptail (sudo apt install whiptail) para el menú; mientras tanto: ./dronswarm.sh --help"
        fi
        ;;
    *) echo "Opción desconocida: $1"; sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
