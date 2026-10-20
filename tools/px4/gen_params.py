#!/usr/bin/env python3
"""S11-02 / S12-02 · Parámetros de PX4 1.15 para los prototipos reales → hardware/px4_params/ds-i.params, ds-d.params

Formato de QGroundControl (Parámetros → Herramientas → Cargar desde archivo). La geometría de rotores es la misma del
airframe de SITL ya validado (tools/gen_sdf.py); el resto sale de la selección COTS (S09) y de lo aprendido en S06.
Antes de volar se revisa todo en QGC (ver hardware/px4_params/README.md): un parámetro con nombre equivocado se
ignora sin aviso.

    .venv/bin/python tools/px4/gen_params.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import gen_sdf  # noqa: E402

OUT = ROOT / "hardware" / "px4_params"
FLOAT, INT = 9, 6
# Puertos de la Pixhawk 6C (boards/px4/fmu-v6c): TELEM1 = RFD900x, TELEM2 = Raspberry Pi, TELEM3 = telemetría de ESC,
# GPS1 = F9P + brújula, GPS2 = flujo óptico MTF-01P (MAVLink); RC por SBUS en RC IN (receptor ExpressLRS en modo SBUS)
PORT = {"TELEM1": 101, "TELEM2": 102, "TELEM3": 103, "GPS1": 201, "GPS2": 202}


def params(vehicle: str) -> list[tuple[str, float | int, str]]:
    d = json.loads((ROOT / f"engineering/data/results/{vehicle.lower()}_sizing.json").read_text())
    sel = json.loads((ROOT / "engineering/data/results/cots_selection.json").read_text())["selected"][vehicle]
    n = d["rotors"]
    cells = int(d["battery"].split("S")[0])
    parallel = int(d["battery"].split("S")[1].split("P")[0])
    cap_mah = parallel * (5000 if "50S" in d["battery"] else 4200)
    p: list[tuple[str, float | int, str]] = []

    def add(name, value, why=""):
        p.append((name, value, why))

    add("SYS_AUTOSTART", 4001 if n == 4 else 6001, "multirrotor genérico; la geometría real va en CA_*")
    add("CA_AIRFRAME", 0, "multirrotor")
    add("CA_ROTOR_COUNT", n, "")
    for line in gen_sdf.airframe(vehicle, d, "x", 0).splitlines():
        if line.startswith("param set-default CA_ROTOR") and "COUNT" not in line:
            _, _, name, value = line.split()
            add(name, float(value), "geometría del airframe de SITL (validado en S05-S08)")
    # salidas: motores por DShot600 en las salidas FMU (AUX) de la 6C, telemetría del ESC por UART
    add("PWM_AUX_TIM0", -3, "DShot600 en el grupo de timers de los motores (verificar en QGC → Actuadores)")
    if n > 4:
        add("PWM_AUX_TIM1", -3, "")
    for k in range(n):
        add(f"PWM_AUX_FUNC{k + 1}", 101 + k, f"motor {k + 1}")
    add("DSHOT_TEL_CFG", PORT["TELEM3"], "telemetría de ESC (rpm, corriente, temperatura) → filtro notch y detección de motor caído")
    add("MOT_POLE_COUNT", 28, "polos del motor: VERIFICAR con la ficha (afecta las rpm del filtro notch)")
    add("IMU_GYRO_DNF_EN", 1, "filtro notch dinámico con las rpm del ESC")
    add("IMU_GYRO_DNF_HMC", 3, "armónicos del filtro notch")
    # radios y computadora a bordo
    add("MAV_0_CONFIG", PORT["TELEM1"], "RFD900x (estación de tierra)")
    add("MAV_1_CONFIG", PORT["TELEM2"], "Raspberry Pi 5 (control del enjambre por MAVSDK)")
    add("MAV_1_MODE", 2, "onboard")
    add("SER_TEL2_BAUD", 921600, "")
    add("MAV_2_CONFIG", PORT["GPS2"], "flujo óptico + lidar MTF-01P (MAVLink)")
    add("SER_GPS2_BAUD", 115200, "")
    add("RC_INPUT_PROTO", -1, "detección automática (SBUS del receptor ExpressLRS)")
    # GNSS, flujo óptico y estimador
    add("GPS_1_CONFIG", PORT["GPS1"], "u-blox F9P")
    add("GPS_1_GNSS", 0, "todas las constelaciones")
    add("EKF2_OF_CTRL", 1, "fusiona flujo óptico: sostiene posición sin GNSS (hallazgo del S06)")
    add("EKF2_RNG_CTRL", 1, "telémetro cerca del suelo")
    add("SENS_FLOW_MAXHGT", 8.0, "alcance útil del lidar del MTF-01P")
    add("COM_POSCTL_NAVL", 2, "sin posición: aterrizar")
    # batería Li-ion y umbrales mineros (S06)
    add("BAT1_N_CELLS", cells, "")
    add("BAT1_V_EMPTY", 3.2, "Li-ion bajo carga (corte de celda 2.5-3.0 V)")
    add("BAT1_V_CHARGED", 4.15, "")
    add("BAT1_CAPACITY", float(cap_mah), "")
    add("BAT_LOW_THR", 0.35, "umbrales mineros: el regreso desde lejos necesita margen (S06)")
    add("BAT_CRIT_THR", 0.25, "")
    add("BAT_EMERGEN_THR", 0.10, "")
    add("COM_LOW_BAT_ACT", 3, "RTL en crítico, aterrizar en emergencia")
    # failsafes y geocerca (S06)
    add("NAV_DLL_ACT", 2, "pérdida de enlace con la estación → RTL")
    add("COM_DL_LOSS_T", 10, "")
    add("NAV_RCL_ACT", 2, "pérdida de RC → RTL (en misión automática no corta la misión: COM_RCL_EXCEPT)")
    add("COM_RCL_EXCEPT", 4, "la misión sigue si se pierde el RC")
    add("GF_ACTION", 3, "geocerca → RTL (HU-10)")
    add("GF_PREDICT", 1, "frena antes del límite")
    add("GF_MAX_HOR_DIST", 2000.0, "límite por defecto: la mina carga su propia geocerca")
    add("GF_MAX_VER_DIST", 150.0, "")
    add("RTL_RETURN_ALT", 40.0, "sobre los taludes y torres de iluminación")
    add("RTL_DESCEND_ALT", 15.0, "")
    # envolvente y empuje (S09)
    add("MPC_THR_MAX", sel["thr_max_recommended"], "no pasar la corriente continua del pack (S09)")
    add("MPC_THR_HOVER", round(min(0.6, max(0.3, sel["hover_thrust_fraction"] + 0.05)), 2),
        "estimado; el estimador de hover lo ajusta en vuelo (MPC_USE_HTE)")
    add("MPC_XY_VEL_MAX", 15.0 if vehicle == "DS-I" else 10.0, "envolvente del target (DS-I ≥ 15 m/s)")
    add("MPC_XY_CRUISE", 10.0 if vehicle == "DS-I" else 8.0, "")
    add("MPC_TILTMAX_AIR", 35.0 if vehicle == "DS-I" else 30.0, "")
    add("COM_OF_LOSS_T", 1.0, "1 s sin órdenes del nodo de enjambre = pérdida de offboard")
    add("COM_OBL_RC_ACT", 5, "pérdida de offboard → Hold: el watchdog reinicia el nodo y éste retoma (S13-05)")
    add("SDLOG_PROFILE", 3, "logs con estimador y alta frecuencia (análisis de vibración y autonomía)")
    if vehicle == "DS-D":
        add("CA_FAILURE_MODE", 1, "motor caído: lo saca de la asignación (requiere telemetría de corriente, S06)")
        add("COM_ACT_FAIL_ACT", 2, "motor caído → aterrizar")
        add("FD_ACT_EN", 1, "")
        add("MC_AIRMODE", 1, "airmode roll/pitch: sin él el hexa cae con un motor menos (verificado en SITL)")
        add("PD_GRIPPER_EN", 1, "mecanismo de liberación (servo)")
        add("PD_GRIPPER_TYPE", 0, "servo; asignar la función 'Gripper' a AUX 7 en QGC → Actuadores")
    return p


def write(vehicle: str) -> Path:
    path = OUT / f"{vehicle.lower()}.params"
    lines = [f"# DronSwarm {vehicle} · PX4 1.15 · Pixhawk 6C · generado por tools/px4/gen_params.py",
             "# Cargar en QGroundControl: Parámetros → Herramientas → Cargar desde archivo. Revisar hardware/px4_params/README.md",
             "# Vehicle-Id\tComponent-Id\tName\tValue\tType"]
    for name, value, why in params(vehicle):
        t = INT if isinstance(value, int) else FLOAT
        v = f"{value}" if t == INT else f"{float(value):.6f}"
        if why:                                    # QGC salta las líneas con '#'; no admite comentarios al final
            lines.append(f"# {name}: {why}")
        lines.append(f"1\t1\t{name}\t{v}\t{t}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return path


if __name__ == "__main__":
    for v in ("DS-I", "DS-D"):
        print(write(v))
