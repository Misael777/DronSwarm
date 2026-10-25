# E5 · GNSS RTK propio: elección del receptor

> Esquema: `electronics/skidl/gnss.py` → `electronics/kicad/gnss/gnss.net`. Precios de módulo a 1-10 unidades, oct. 2026
> (estimados, se cotizan en E7).

## Requisitos (E0)

RTK con error ≤ 2 cm usando la base propia, fijo en ≤ 60 s, multibanda para fijar rápido en minas (paredes de tajo que
tapan cielo), soporte de PX4 sin firmware propio, ≤ US$130 la unidad completa (contra US$250 del H-RTK F9P).

## Comparación

| | Quectel LG290P | Unicore UM980 | u-blox ZED-F9P |
|---|---|---|---|
| Bandas | **L1 / L2 / L5 / L6** (4) | L1 / L2 / L5 (3) | L1 / L2 (2) |
| RTK | sí (≤ 1 cm + 1 ppm) | sí | sí |
| Precio del módulo | **≈ US$82** | ≈ US$150 | ≈ US$200 |
| Protocolo hacia PX4 | NMEA + RTCM entrante | NMEA (o Unicore propio) | UBX (nativo) |
| Soporte en PX4 v1.15 | driver NMEA genérico (`GPS_1_PROTOCOL = 6`) | NMEA genérico | driver UBX completo |
| Unidad completa estimada | **≈ US$120** | ≈ US$190 | ≈ US$240 |

## Verificación del soporte en PX4 (código de v1.15.4)

- `src/drivers/gps/devices/src/nmea.cpp`: la calidad de fijo de GGA se traduce a `fix_type`: 4 (RTK fijo) → **6**,
  5 (RTK flotante) → 5. PX4 ve el RTK fijo igual que con u-blox.
- `src/drivers/gps/gps.cpp`, `GPS::injectData()`: las correcciones RTCM que llegan por MAVLink (`gps_inject_data`) se
  escriben tal cual en el UART, **sin depender del protocolo**. El LG290P acepta RTCM 3 por el mismo UART1.
- Limitaciones del driver NMEA: no configura el receptor (la configuración de 10 Hz, mensajes GGA/RMC/GST y RTCM de
  entrada se graba una vez en la flash del módulo con comandos PQTM, por UART2 desde los pads de prueba) y no reporta
  rumbo ni interferencia. Para el enjambre basta posición RTK.

## Decisión

**LG290P**: único que entra en la meta de costo, con más bandas que el F9P y soporte de PX4 verificado en el código. Plan
B (riesgo del G6): si el driver NMEA no da RTK estable en la prueba de S21, la misma placa se rehace con ZED-F9P (driver
UBX), a ≈ US$240.

## Diseño de la placa

- Módulo LG290P a 3.3 V con LDO de bajo ruido (TLV75533) desde los 5 V del puerto GPS1 de la controladora.
- Antena activa multibanda (con filtro SAW antes del LNA) por u.FL, alimentada desde `VDD_RF` según la figura 17 de la
  guía de hardware de Quectel (10 Ω + 68 nH, bloqueo de DC 100 pF, π de adaptación con 0 Ω y dos sin montar, TVS de RF).
- `V_BCKP` al mismo 3.3 V (arranque en frío al encender: el RTK fija en < 60 s igual; un supercapacitor para arranque en
  caliente queda como opción).
- Magnetómetro IST8310 en el I2C del puerto (bus externo 1 de PX4), lejos de los cables de potencia en el mástil.
- LED de RTK fijo (`RTK_STAT`) y de 1PPS; pads de UART2 y `RESET_N` para configurar o actualizar el módulo.

Fuentes: [guía de hardware LG290P(03) V1.0 (copia de SparkFun)](https://cdn.sparkfun.com/assets/b/1/7/6/3/Quectel_LG290P_03__Hardware_Design_V1.0.pdf),
[especificación LG290P V1.4 (Quectel)](https://www.quectel.com.cn/wp-content/uploads/2024/12/Quectel_LG290P系列_GNSS_模块产品规格书_V1.4.pdf),
[foro de Quectel sobre la documentación](https://forums.quectel.com/t/lg290p-the-new-gnss-module-documentation/34282).
