# E4 · Port de PX4 a la controladora DronSwarm FMU v1

> Target `dronswarm_fmu-v1` en `electronics/fc/px4/boards/dronswarm/fmu-v1/`, derivado de la placa de referencia abierta
> `px4_fmu-v6c` (PX4 v1.15.4, commit `99c4040`). Esquema: `electronics/skidl/fc.py` → `electronics/kicad/fc/fc.net`.

## Resultado

| Target | Estado | Flash | Tamaño | SHA-256 (16) |
|---|---|---|---|---|
| `dronswarm_fmu-v1_default` | **compila sin advertencias** | 97.1 % de 1920 KB | 1.80 MB (`.px4`) | `ef6d79ad7d60c3ed` |
| `dronswarm_fmu-v1_bootloader` | compila | — | 46 KB (`.bin`) | `5e7cbcb93b1f8cf8` |

```bash
bash electronics/fc/build_px4.sh            # firmware (copia el target al árbol de PX4 y corre make)
bash electronics/fc/build_px4.sh bootloader # bootloader (se graba una vez por SWD)
```

Toolchain sin sudo: `gcc-arm-none-eabi-9-2020-q2-update` (la versión que pide PX4 v1.15) en `~/.local/opt/` y el entorno
`~/.venvs/px4` (con `setuptools<70`, que trae `pkg_resources` para el compilador de DSDL de DroneCAN).

## Qué cambia respecto de fmu-v6c

El esquema copia la asignación de pines de fmu-v6c **sin coprocesador PX4IO**, así que el port es corto:

| Archivo | Cambio | Por qué |
|---|---|---|
| `src/board_config.h` | sin PX4IO: `RC_SERIAL_PORT "/dev/ttyS4"` (USART6) | el RC (CRSF/ELRS) entra por UART al H743; 8 salidas DShot directas |
| `src/board_config.h` | sin versionado de hardware (PE12, PC0, PC1 libres) | una sola placa; v6c distingue 7 variantes |
| `src/board_config.h` | `VDD_5V_PERIPH_EN` y `VDD_5V_HIPOWER_EN` activos en alto | el TPS2561 tiene EN activo alto (v6c usa interruptores activos en bajo) |
| `src/spi.cpp` | SPI1: BMI088 (acel. PC15/PE4, giro PC14/PE5) + **IIM-42652** (PC13/PE6); alimentación por PB2. SPI2: FRAM (PD4) | IMU industrial (−40/+105 °C) en vez de ICM-42688-P; sin tabla por versión |
| `src/init.c`, `src/CMakeLists.txt` | sin `board_determine_hw_info()` ni `manifest.c` | consecuencia de quitar el versionado |
| `init/rc.board_sensors` | arranca `bmi088`, `iim42652`, `ms5611` e `ist8310` (I2C4) + `ist8310` externo (GPS1) | sensores de esta placa y del GNSS DronSwarm |
| `default.px4board` | − PX4IO, − BMI055, − ICM42688P, + IIM42652, + `rc_input` | libera flash (97.1 % contra 99.8 % de v6c) |
| `firmware.prototype`, `src/hw_config.h` | `board_id` 6110 | **provisorio**: registrar un ID propio en PX4 antes de producir, para que QGroundControl no cargue firmware de otra placa |
| `nuttx-config/*/defconfig` | ruta de la placa | — |

Puertos (iguales a v6c): GPS1 = `/dev/ttyS0` (USART1), TELEM3 = `ttyS1` (USART2), consola = `ttyS2` (USART3),
TELEM2 = `ttyS3` (UART5), RC = `ttyS4` (USART6), TELEM1 = `ttyS5` (UART7), GPS2 = `ttyS6` (UART8).

## Parámetros de PX4 para el dron

| Parámetro | Valor | Motivo |
|---|---|---|
| `RC_INPUT_PROTO` / `RC_PORT_CONFIG` | CRSF en `RC` | receptor ExpressLRS |
| `GPS_1_CONFIG` = GPS1, `GPS_1_PROTOCOL` = **6 (NMEA)** | GNSS DronSwarm (LG290P), ver `electronics/informes/E5_gnss.md` |
| `SER_GPS1_BAUD` | 460800 | NMEA a 10 Hz + RTCM |
| `UAVCAN_ENABLE` = 3, `UAVCAN_SUB_BAT` = 1 | BMS propio por DroneCAN | estado del pack por celda |
| `SENS_EN_THERMAL` / `SENS_IMU_TEMP` | 45 °C | calefactor de las IMU (PB9) para el frío de altura |
| `DSHOT_CONFIG` = 600, `DSHOT_BIDIR_EN` = 1 | ESC propios (AM32) | RPM para el filtro de muesca dinámico |

## Pendiente (E8, con la placa)

- Grabar el bootloader por SWD (`J_DEBUG`), luego el firmware por USB desde QGroundControl.
- Verificar sensores (`listener sensor_accel`, `sensor_gyro`, `ms5611 status`), FRAM (`mtd status`), microSD (`sd_bench`),
  CAN (`uavcan status`), salidas DShot y los dos puertos de alimentación.
- HITL y los tests de S13 sin regresiones (criterio del G6).
