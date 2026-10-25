# E8 · Fabricación, banco e integración de la electrónica propia (S21-S22)

> Procedimientos para cuando haya placas. Criterios del Gate G6: `electronics/PLAN.md` §4. Cada prueba deja su registro
> en esta carpeta (`<placa>_<fecha>.md` + datos crudos) y se resume en `docs/revisiones/G6_componentes.md`.

## S21-03 · Fabricar y montar

1. **Antes de pedir** (por placa): DRC limpio en KiCad, revisión humana del ruteo de potencia y RF (ver
   `electronics/kicad/README.md`), huellas propias contra la hoja de datos impresa a 1:1.
2. Generar los archivos de fabricación: `bash electronics/kicad/fab_outputs.sh <placa>` (Gerber, taladros, BOM y
   posiciones en `electronics/kicad/<placa>/fab/`).
3. Pedido por servicio (JLCPCB/PCBWay): 4 capas, 1.6 mm, cobre exterior 2 oz en ESC y cargador, acabado ENIG (LGA y QFN
   de paso fino), montaje SMD por una cara (la otra a mano o segundo pedido de montaje), 5 placas por diseño para el
   prototipo. **Es un pedido con costo: lo hace el usuario**; el presupuesto a 100 u. está en
   `electronics/bom/Presupuesto_Electronica.xlsx` (el de 5 u. es ~3 × por la configuración).
4. Recepción: inspección visual (puentes en QFN/LGA, polaridad de electrolíticos y diodos), resistencia de los rieles a
   GND antes de energizar (> 1 kΩ), primer encendido con fuente limitada a 100 mA.
5. Placas de 12S (ESC DS-D, BMS DS-D, cargador): **recubrimiento conformado** después de probar (IPC-2221 B4: a 5,000 msnm
   sin recubrimiento la separación de 51-100 V pediría 1.5 mm).

## S21-04 · Banco del ESC

| Paso | Cómo | Pasa si |
|---|---|---|
| Energizar sin motor | fuente 12S limitada a 0.5 A | 12 V y 3.3 V correctos; consumo < 60 mA |
| Firmware | AM32 por SWD (`J_SWD`), objetivo G071 (grupo G0_G); luego por el puerto de señal | AM32 responde al configurador |
| Tiempo muerto y frecuencia | GaN: 48 kHz, tiempo muerto mínimo; silicio: 24 kHz; osciloscopio en las fases | sin solape, sobreimpulso < 20 % del bus |
| Sin carga | motor propio sin hélice, 10-100 % | arranque sin desincronización |
| Barrido con hélice | `tools/bench/acquire.py sweep --esc "propio GaN"` y otro con el comercial, mismo motor | ver abajo |
| Comparación | `.venv/bin/python electronics/pruebas/compare_esc.py comercial.csv propio.csv --hover-n <N>` | eficiencia ≥ comercial − 0.3 puntos en hover |
| Térmica | `acquire.py hover` 60 s a empuje máximo, aire a la densidad de 5,000 m (banco S10) | transistores ≤ 85 °C (NTC del ESC) |
| Resistencia | 10 h de ciclos (`acquire.py hover` en bucle) | sin desincronización ni reinicio |

## S21-05 · Controladora: puesta en marcha y HITL

1. Rieles (5 V, 3.3 V, 3.3 V de sensores) con fuente limitada; corriente en reposo < 250 mA.
2. Bootloader por SWD (`J_DEBUG`): `bash electronics/fc/build_px4.sh bootloader` y grabar `dronswarm_fmu-v1_bootloader.bin`.
3. Firmware por USB (QGroundControl o `make dronswarm_fmu-v1_default upload`).
4. Consola (`J_DEBUG`, USART3): `ver all`, `listener sensor_accel` / `sensor_gyro` (dos IMU), `ms5611 status`,
   `ist8310 status`, `mtd status` (FRAM), `sd_bench`, `uavcan status`, `dshot status`.
5. Calefacción de IMU: `SENS_EN_THERMAL`, temperatura estable a 45 °C desde 0 °C.
6. HITL: `tools/sitl` en modo HITL y los tests de S13 (`.venv/bin/pytest -q control/tests`) contra la placa.
7. Vibración: misma prueba de vuelo atado que con la Pixhawk 6C; criterio: vibración ≤ la de la 6C.

## S21-06 · GNSS RTK

1. Configurar el LG290P una vez por UART2 (pads `TP_TXD2`/`TP_RXD2`): 10 Hz, GGA + RMC + GST, RTCM 3 de entrada por UART1,
   460800 bps; guardar en flash.
2. PX4: `GPS_1_PROTOCOL = 6`, `SER_GPS1_BAUD = 460800`; base RTK del proyecto por QGroundControl.
3. Estático 1 h sobre un punto medido: tiempo a RTK fijo (≤ 60 s) y error horizontal (≤ 2 cm, percentil 95).
4. Dinámico: vuelo de inspección de S12 comparando con el H-RTK F9P en el mismo dron.

## S21-07 · Integración

Motor (si G5 aprueba), ESC, controladora, GNSS y packs propios en un DS-I y un DS-D; cableado según
`hardware/wiring.md` actualizado; parámetros en `hardware/px4_params/`. BMS: `UAVCAN_ENABLE = 3`, `UAVCAN_SUB_BAT = 1`,
lectura de celdas en QGroundControl. Prueba en tierra completa antes del primer vuelo (S22-01).
