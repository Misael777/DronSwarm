# Electrónica propia DronSwarm · plan del subproyecto

> Estado: **aprobado por el usuario** (2026-10-25). ADR-015 en `docs/decisiones.md`. Reemplaza el alcance de electrónica
> de los sprints S20-S22 (diseño en S20; placas, fabricación y banco en S21; vuelos y Gate G6 en S22). Mismo método que el motor propio (`motor/PLAN.md`): requisitos → cálculo → esquema → placa →
> banco → vuelo → gate.

## 1. Objetivo

Bajar el costo del dron fabricando tres placas propias, sin perder rendimiento ni confiabilidad:

| Placa | Reemplaza a | Costo comercial por dron | Meta de materiales por dron |
|---|---|---|---|
| **ESC de nitruro de galio (GaN)**: DS-D 1 placa por motor; DS-I 4 en 1 | APD 120F3 ×6 (DS-D) · ESC 4 en 1 50 A (DS-I) | US$720 · US$80 | ≤ US$300 · ≤ US$80 (o se sigue con el comercial) |
| **Controladora de vuelo** (estándar abierto Pixhawk FMUv6, PX4) | Holybro Pixhawk 6C | US$225 | ≤ US$80 |
| **GNSS RTK** multibanda + magnetómetro | H-RTK F9P (ZED-F9P) | US$250 | ≤ US$130 |

La **cámara** (SIYI A8 mini, US$280) queda **planificada a futuro** (ver §6), fuera de este alcance.

Herramientas: **100 % libres** — esquemas como código con **SKIDL** (Python), placas en **KiCad**, firmware abierto
(**AM32** en los ESC, **PX4** en la controladora). Fabricación de placas y montaje SMD por servicio (JLCPCB/PCBWay) con
lista de materiales y archivos de posición generados por KiCad.

## 2. Decisiones técnicas de partida (se verifican en las fases)

- **ESC GaN**: transistores EPC de 100 V en QFN 3 × 5 mm (EPC2302: 1.8 mΩ, Qg 23 nC, Qrr 0) con driver de medio puente
  para GaN (compuerta máx. +6 V: el driver debe regular 5 V). Microcontrolador **STM32G071** (soportado por **AM32**,
  firmware abierto con DShot y telemetría). Conmutación a 48-96 kHz para reducir el rizado en nuestros motores de baja
  inductancia (M2-M4). El DS-I (6S) se evalúa con GaN de 40-100 V: si el 4 en 1 GaN no es más barato que el comercial,
  se queda el comercial o se hace uno de silicio (decisión de costo, no de orgullo).
- **Controladora**: arquitectura FMUv6 (STM32H743, 2 IMU con aislación de vibración y calefacción, barómetro, FRAM,
  microSD, 2 CAN, UART, salidas DShot). Port de PX4 como placa nueva (el código de PX4 es abierto; la placa también).
- **GNSS RTK**: comparar **Quectel LG290P** (4 bandas, ≈ US$82), **Unicore UM980** (3 bandas, ≈ US$150) y ZED-F9P
  (referencia); antena multibanda, magnetómetro IST8310 y salida UART (o DroneCAN). Verificar el soporte de PX4 (NMEA +
  inyección de RTCM) antes de elegir.
- **Sin sensores Hall** en los motores (AM32 sin sensores, contra-FEM); sensor de corriente en cada ESC (telemetría).

## 3. Fases

| Fase | Qué | Entregable | Hecho cuando |
|---|---|---|---|
| **E0** | Requisitos eléctricos de cada placa desde los motores y el dron | `electronics/requisitos/` | corrientes, tensiones, eRPM y conectores definidos |
| **E1** | ESC: GaN vs silicio (pérdidas, frecuencia, rizado en nuestros motores), selección de piezas | `electronics/informes/E1_*` | ganancia y costo cuantificados; piezas elegidas |
| **E2** | ESC DS-D: esquema (SKIDL → netlist KiCad) | `electronics/skidl/esc_ds_d.py`, `electronics/kicad/esc_ds_d/` | netlist sin errores de ERC |
| **E3** | ESC DS-I 4 en 1: decisión de costo y esquema (**silicio propio**, ADR-016) | `electronics/skidl/esc_ds_i.py` | netlist o ADR de "comercial" |
| **E4** | Controladora FMU: esquema + plan de port de PX4 | `electronics/skidl/fc.py`, `electronics/fc/px4_port.md` | netlist; target de PX4 compila |
| **E5** | GNSS RTK: elección del módulo y esquema | `electronics/skidl/gnss.py` | netlist; soporte PX4 verificado |
| **E6** | Placas en KiCad: ruteo, DRC, Gerbers, BOM y posiciones para montaje | `electronics/kicad/*` | DRC limpio, archivos de fabricación |
| **S20-07** | Packs 21700 + BMS (BQ769x0, DroneCAN) + cargador de campo GaN 1 kW | `electronics/skidl/bms.py`, `charger.py`, `informes/S20-07_*` | netlists con ERC limpio |
| **E7** | Lista de materiales y presupuesto de la electrónica por dron | `electronics/bom/*.xlsx` | costo por placa y por dron vs comercial |
| **E8** | Fabricar, banco (ESC: eficiencia y temperatura vs comercial; FC: HITL; GNSS: precisión RTK), integrar y volar | `electronics/pruebas/` | Gate G6 |

## 4. Criterios del Gate G6 (electrónica)

| Placa | Criterio |
|---|---|
| ESC | eficiencia ≥ comercial − 0.3 puntos en hover (banco, mismo motor; E1 predice +0.5: el beneficio es el costo), temperatura ≤ 85 °C a empuje máximo 60 s a 5,000 msnm (simulado en banco), sin desincronización en 10 h, costo ≤ meta |
| Controladora | PX4 estable, IMU con vibración ≤ la de la Pixhawk 6C en el mismo frame, HITL y vuelo sin regresiones en los tests de S13 |
| GNSS | RTK fijo en ≤ 60 s, error horizontal ≤ 2 cm (estático, 1 h) con la base del proyecto |

## 5. Riesgos

| Riesgo | Mitigación |
|---|---|
| Compuerta GaN (máx. +6 V) dañada por sobretensión o ruido | driver con regulación de 5 V, resistencia de compuerta y ruteo Kelvin; prototipos con límite de corriente |
| Ruteo de potencia GaN (inductancia de lazo) | diseño "vertical" de EPC (condensadores bajo el medio puente), placa de 4 capas, revisión con la nota de aplicación de EPC |
| AM32 con GaN (tiempo muerto, frecuencia) | AM32 permite tiempo muerto y frecuencia configurables; banco antes de volar |
| Port de PX4 | basarse en `px4_fmu-v6c` (misma MCU y sensores compatibles); HITL antes de volar |
| Soporte de PX4 para el GNSS elegido | verificar antes de diseñar (E5); plan B: ZED-F9P en placa propia |
| Montaje SMD de QFN/BGA | montaje por servicio (no a mano) |

## 6. Estado (2026-10-25)

| Placa | Esquema (SKIDL → netlist, ERC) | Firmware | Informe |
|---|---|---|---|
| ESC GaN DS-D | `skidl/esc_ds_d.py` ✅ | AM32 (G0_G) | `informes/E1_esc_gan_vs_si.md` |
| ESC 4 en 1 DS-I (silicio) | `skidl/esc_ds_i.py` ✅ | AM32 (G0_G) | `informes/E3_esc_ds_i.md` |
| Controladora FMU | `skidl/fc.py` ✅ | PX4 `dronswarm_fmu-v1` compila ✅ | `fc/px4_port.md` |
| GNSS RTK LG290P | `skidl/gnss.py` ✅ | NMEA de PX4 | `informes/E5_gnss.md` |
| BMS 6S / 12S | `skidl/bms.py` ✅ | por escribir (DroneCAN BatteryInfo) | `informes/S20-07_baterias.md` |
| Cargador GaN 1 kW | `skidl/charger.py` ✅ | por escribir (CC/CV en HRTIM) | `informes/S20-07_cargador.md` |

Regenerar todo: `bash electronics/build_netlists.sh` · pruebas: `.venv/bin/pytest -q electronics/tests`.

## 7. A futuro (fuera de este alcance)

- **Cámara de inspección propia** (sensor + gimbal + enlace de video): se planifica después del Gate G6, con datos de
  campo de la SIYI A8 mini.
- **Placa de distribución de potencia** integrada al ESC del DS-D.
- Etapa AC-DC propia del cargador (PFC GaN): se compra hecha mientras el volumen no la justifique.
