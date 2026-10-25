# E0 · Requisitos eléctricos de las placas propias

> Generado por `electronics/calculo/requisitos.py` desde los motores propios (M2) y el dron. No editar a mano.

## ESC

| | DS-I | DS-D |
|---|---|---|
| Formato | 4 en 1 | 1 por motor |
| Motores por dron | 4 | 6 |
| Bus nominal / máx. / mín. [V] | 21.6 / 25.2 / 19.8 | 43.2 / 50.4 / 39.6 |
| Tensión mínima de los transistores [V] | 50 | 100 |
| Corriente del motor en hover [A] | 5.46 | 13.7 |
| Corriente continua (maniobra) [A] | 8.07 | 20.46 |
| Corriente pico 30 s [A] | 10.6 | 27.24 |
| Diseño: continua / pico (× 1.3) [A] | 10.5 / 13.8 | 26.6 / 35.4 |
| Pares de polos · eRPM máx. | 13 · 89,450 | 16 · 74,419 |
| Frecuencia eléctrica máx. [Hz] | 1491 | 1240 |
| Potencia del motor en hover / máx. [W] | 68.6 / 202.6 | 302.6 / 912.9 |
| Conexión del motor | estrella | estrella |
| Protocolo | DShot600 bidireccional + telemetría (AM32) | DShot600 bidireccional + telemetría (AM32) |
| Inductancia del motor: fase / lazo de 2 fases [µH] (FEM) | 34 / 70 | 40 / 85 |

Sin sensores Hall (AM32 sin sensores). Medición en cada ESC: corriente del bus (telemetría y límite), tensión del bus, temperatura de los transistores (NTC).

## Controladora de vuelo

- **estandar**: Pixhawk FMUv6 (abierto) · PX4 v1.15
- **mcu**: STM32H743 (480 MHz, 2 MB flash)
- **imu**: 2 IMU distintas (redundancia), con aislación de vibración y calefacción a 45 °C (frío de altura)
- **barometro**: 1 (con espuma; ventilado dentro de la carcasa IP54)
- **memoria**: FRAM SPI (parámetros) + microSD (logs)
- **interfaces**: UART: TELEM1: Raspberry Pi (MAVLink), TELEM2: RFD900x, GPS1: GNSS RTK, RC: ExpressLRS (CRSF), TELEM3: cámara SIYI, UART5: flujo óptico MTF-01P, consola de depuración; CAN: CAN1 (GNSS/ESC futuros), CAN2; I2C: magnetómetro externo, expansión; salidas: 8 DShot/PWM (6 motores DS-D + servo de liberación + luces); USB: USB-C (carga de firmware)
- **alimentacion**: 5 V desde un BEC/PM redundante (2 entradas), medición de tensión y corriente de la batería (ADC)
- **tamano**: ≤ 50 × 40 mm, montaje 30.5 mm (estándar)

## GNSS RTK

- **precision**: RTK: ≤ 2 cm horizontal con base propia; multibanda (L1/L2 o L1/L5) para fijar rápido en minas
- **interfaz**: UART a GPS1 (NMEA/RTCM o protocolo propio soportado por PX4) + I2C del magnetómetro
- **magnetometro**: IST8310 o LIS3MDL, lejos de los cables de potencia (mástil)
- **antena**: multibanda (helicoidal o parche con LNA), conector u.FL/SMA
- **alimentacion**: 5 V desde la controladora; LDO 3.3 V de bajo ruido
- **tamano**: ≤ 60 × 60 mm, carcasa impresa con tapa transparente a RF
