# Selección de componentes comerciales (COTS) · prototipos DS-I y DS-D

> Generado por `engineering/cots.py` el 2026-10-19. Catálogo y criterios en el código; para recalcular: `.venv/bin/python -m engineering.cots`.

Cada motor del catálogo se evalúa con el **mismo modelo del dimensionamiento** (hélice BEMT, motor por circuito equivalente, batería Li-ion, aire a 4,500-5,000 msnm), con la masa real de motor, hélice, ESC, aviónica y frame (CAD). Requisitos que descartan una opción: empuje/peso ≥ 2.0 a 5,000 msnm, autonomía del escenario (DS-I ≥ 30 min, DS-D ≥ 20 min con 5 kg), corriente dentro del motor y del pack, y ESC con telemetría. Las guías de diseño se informan como observaciones. Lo marcado *estimado* se mide en el banco del S10.

## 1. Resultado

| | DS-I | DS-D |
|---|---|---|
| Motor | T-Motor MN4006 KV380 (AntiGravity) | MAD M6C12 EEE KV150 |
| Hélice | 15" (el frame admite hasta 17") | 26" |
| ESC | ESC 4 en 1 BLHeli32/AM32 6S 50 A con telemetría DShot bidireccional | APD 120F3[X] V2 12S 120 A (BLHeli32, telemetría DShot) |
| MTOW con componentes reales | 2.43 kg (S04: 2.69) | 15.07 kg (S04: 15.61) |
| Autonomía, batería nueva, 4,500 msnm | 32.1 min (S04: 31.3) | 21.4 min con 5 kg (S04: 20.3) |
| Empuje/peso a 5,000 msnm | 2.27 | 2.77 |
| Corriente del pack: a fondo / con empuje 2 × peso / límite | 55 / 49 / 50 A | 262 / 193 / 225 A |
| `MPC_THR_MAX` de PX4 (protege la batería) | 0.91 | 0.86 |
| Propulsión (motores + hélices + ESC) | US$402 (S04: US$127) | US$1841 (S04: US$526) |

**Lectura:** los dos prototipos cumplen sus escenarios con componentes que se compran hoy. El DS-I sale más liviano que lo dimensionado (la cámara real pesa 95 g contra 300 g supuestos) y gana autonomía. **El costo sube:** los motores de marca cuestan 3-4 veces lo que suponía el modelo paramétrico del S04, y la aviónica real ~US$500 más por dron (sección 4). Es el principal argumento para el motor y la electrónica propios (S17-S21).

## 2. Motores y hélices evaluados

| Dron | Motor | Hélice | MTOW | Autonomía | Empuje/peso | Hover | Corriente máx./motor | Propulsión | ¿Cumple? | Observaciones |
|---|---|---|---|---|---|---|---|---|---|---|
| DS-I | T-Motor MN4006 KV380 (AntiGravity) | 15" | 2.43 kg | 32.1 min | 2.27 | 41% | 13.6 A | US$402 | ✅ | a fondo el pack daría 55 A (límite 50 A): limitar con MPC_THR_MAX = 0.91; datos estimados: cost_usd (se miden en el S10) |
| DS-I | T-Motor MN4006 KV380 (AntiGravity) | 16" | 2.45 kg | 33.2 min | 2.51 | 39% | 16.0 A | US$406 | ❌ el pack entrega la corriente para empuje/peso 2.0 | a fondo el pack daría 65 A (límite 50 A): limitar con MPC_THR_MAX = 0.77; hover al 39% del empuje máximo (guía 40-65 %): motor holgado, margen extra en altura; hélice de 16" fuera del rango del fabricante (12-15"): verificar temperatura en el banco (S10); a fondo llega al límite de corriente del motor: el empuje máximo lo fija la corriente; datos estimados: cost_usd (se miden en el S10) |
| DS-I | T-Motor MN4006 KV380 (AntiGravity) | 17" | 2.46 kg | 34.1 min | 2.34 | 42% | 16.0 A | US$409 | ❌ el pack entrega la corriente para empuje/peso 2.0 | a fondo el pack daría 65 A (límite 50 A): limitar con MPC_THR_MAX = 0.77; hélice de 17" fuera del rango del fabricante (12-15"): verificar temperatura en el banco (S10); a fondo llega al límite de corriente del motor: el empuje máximo lo fija la corriente; datos estimados: cost_usd (se miden en el S10) |
| DS-I | T-Motor MN4014 KV330 | 15" | 2.85 kg | 26.6 min | 1.84 | 49% | 11.6 A | US$522 | ❌ empuje/peso ≥ 2.0 a 5,000 msnm; autonomía ≥ 30 min (batería nueva, 4,500 msnm); el pack entrega la corriente para empuje/peso 2.0 | datos estimados: i0, cost_usd (se miden en el S10) |
| DS-I | T-Motor MN4014 KV330 | 16" | 2.86 kg | 28.0 min | 2.2 | 41% | 14.5 A | US$526 | ❌ autonomía ≥ 30 min (batería nueva, 4,500 msnm); el pack entrega la corriente para empuje/peso 2.0 | a fondo el pack daría 59 A (límite 50 A): limitar con MPC_THR_MAX = 0.85; datos estimados: i0, cost_usd (se miden en el S10) |
| DS-I | T-Motor MN4014 KV330 | 17" | 2.88 kg | 29.3 min | 2.59 | 35% | 18.0 A | US$529 | ❌ autonomía ≥ 30 min (batería nueva, 4,500 msnm); el pack entrega la corriente para empuje/peso 2.0 | a fondo el pack daría 73 A (límite 50 A): limitar con MPC_THR_MAX = 0.69; hover al 35% del empuje máximo (guía 40-65 %): motor holgado, margen extra en altura; datos estimados: i0, cost_usd (se miden en el S10) |
| DS-D | T-Motor U8 Lite KV100 | 24" | 14.88 kg | 20.5 min | 1.35 | 67% | 13.7 A | US$2786 | ❌ empuje/peso ≥ 2.0 a 5,000 msnm | hover al 67% del empuje máximo (guía 40-65 %): poco margen; hélice de 24" fuera del rango del fabricante (27-28"): verificar temperatura en el banco (S10) |
| DS-D | T-Motor U8 Lite KV100 | 26" | 14.96 kg | 21.9 min | 1.7 | 54% | 18.4 A | US$2801 | ❌ empuje/peso ≥ 2.0 a 5,000 msnm | hélice de 26" fuera del rango del fabricante (27-28"): verificar temperatura en el banco (S10) |
| DS-D | MAD M6C12 EEE KV150 | 24" | 15.00 kg | 20.2 min | 2.39 | 38% | 34.9 A | US$1826 | ✅ | hover al 38% del empuje máximo (guía 40-65 %): motor holgado, margen extra en altura; datos estimados: rm, i0, i_max, cost_usd, p_max_w (se miden en el S10) |
| DS-D | MAD M6C12 EEE KV150 | 26" | 15.07 kg | 21.4 min | 2.77 | 35% | 43.6 A | US$1841 | ✅ | a fondo el pack daría 262 A (límite 225 A): limitar con MPC_THR_MAX = 0.86; hover al 35% del empuje máximo (guía 40-65 %): motor holgado, margen extra en altura; datos estimados: rm, i0, i_max, cost_usd, p_max_w (se miden en el S10) |
| DS-D | T-Motor MN6007II KV160 | 24" | 14.38 kg | 19.8 min | 1.65 | 60% | 25.0 A | US$1706 | ❌ empuje/peso ≥ 2.0 a 5,000 msnm; autonomía ≥ 20 min (batería nueva, 4,500 msnm) | hélice de 24" fuera del rango del fabricante (21-22"): verificar temperatura en el banco (S10); a fondo llega al límite de corriente del motor: el empuje máximo lo fija la corriente; datos estimados: i0, i_max, cost_usd, p_max_w (se miden en el S10) |
| DS-D | T-Motor MN6007II KV160 | 26" | 14.46 kg | 20.4 min | 1.51 | 66% | 25.0 A | US$1721 | ❌ empuje/peso ≥ 2.0 a 5,000 msnm | hover al 66% del empuje máximo (guía 40-65 %): poco margen; hélice de 26" fuera del rango del fabricante (21-22"): verificar temperatura en el banco (S10); a fondo llega al límite de corriente del motor: el empuje máximo lo fija la corriente; datos estimados: i0, i_max, cost_usd, p_max_w (se miden en el S10) |

Descartados antes de evaluar: **Hobbywing X6 Plus G2** (motor + ESC CAN integrado, a prueba de agua): ~750 g y ~US$310 por brazo, y monta en tubo de 30 mm. Es una buena opción para una versión agrícola, pero no para este peso.

## 3. ESC

| Dron | ESC | Corriente | Telemetría | Por qué |
|---|---|---|---|---|
| DS-I | ESC 4 en 1 BLHeli32/AM32 6S 50 A con telemetría DShot bidireccional | 50 A | sí | 4 en 1, liviano; la telemetría da rpm para el filtro notch dinámico |
| DS-D | APD 120F3[X] V2 12S 120 A (BLHeli32, telemetría DShot) | 120 A | sí | **telemetría de corriente obligatoria** para detectar un motor caído (S06); 12S con margen sobre 45 A |

## 4. Aviónica y equipo por dron

### DS-I

| Función | Componente | Masa | Precio | Fuente |
|---|---|---|---|---|
| controladora | Holybro Pixhawk 6C (caja de plástico) | 60 g | US$225 | pyrodrone.com (2026-10): US$224.99 |
| GNSS | u-blox ZED-F9P multibanda, RTK, con brújula (clase Holybro H-RTK F9P Ultralight) | 40 g | US$250 * | estimado: módulos F9P US$200-300 |
| computadora a bordo | Raspberry Pi 5 4 GB + disipador + caja | 60 g | US$80 | precio de lista Raspberry Pi |
| radio de tierra | RFDesign RFD900x (malla/multipunto 900 MHz) | 15 g | US$140 | unmannedtechshop.co.uk (2026-10): £219.95 el par |
| radio entre drones | Módulo ESP32-S3 (ESP-NOW 2.4 GHz) en la computadora a bordo | 5 g | US$10 | precio de lista |
| receptor RC | ExpressLRS 900 MHz (clase RadioMaster BR3) | 5 g | US$25 * | estimado |
| flujo óptico + telémetro | MicoAir MTF-01P (flujo óptico + lidar 8 m, MAVLink) | 5 g | US$40 * | estimado; requisito del S06 (pérdida de GNSS) |
| módulo de potencia | Holybro PM02 V3 (2-12S, sensado de V/I) | 30 g | US$30 * | estimado |
| cámara + gimbal | SIYI A8 mini (1/1.7" 8 MP, gimbal 3 ejes, 4K) | 95 g | US$280 | irlock.com / siyi.biz (2026-10): 95 g, US$190-330 |

Contra el presupuesto del S04: **-220 g y +485 US$** por dron (`*` = precio estimado).

### DS-D

| Función | Componente | Masa | Precio | Fuente |
|---|---|---|---|---|
| controladora | Holybro Pixhawk 6C (caja de plástico) | 60 g | US$225 | pyrodrone.com (2026-10): US$224.99 |
| GNSS | u-blox ZED-F9P multibanda, RTK, con brújula (clase Holybro H-RTK F9P Ultralight) | 40 g | US$250 * | estimado: módulos F9P US$200-300 |
| computadora a bordo | Raspberry Pi 5 4 GB + disipador + caja | 60 g | US$80 | precio de lista Raspberry Pi |
| radio de tierra | RFDesign RFD900x (malla/multipunto 900 MHz) | 15 g | US$140 | unmannedtechshop.co.uk (2026-10): £219.95 el par |
| radio entre drones | Módulo ESP32-S3 (ESP-NOW 2.4 GHz) en la computadora a bordo | 5 g | US$10 | precio de lista |
| receptor RC | ExpressLRS 900 MHz (clase RadioMaster BR3) | 5 g | US$25 * | estimado |
| flujo óptico + telémetro | MicoAir MTF-01P (flujo óptico + lidar 8 m, MAVLink) | 5 g | US$40 * | estimado; requisito del S06 (pérdida de GNSS) |
| módulo de potencia | Sensor Hall 200 A (clase Mauch HS-200) + regulador 5.3 V | 45 g | US$90 * | estimado |
| cámara FPV | Cámara FPV analógica/digital 19 mm | 10 g | US$30 * | estimado |
| servo de liberación | Servo estándar de engranajes metálicos 20 kg·cm + micro-interruptor | 60 g | US$35 * | estimado |
| luces anticolisión | 4 LED de alta luminosidad (rojo, verde, 2 blancas destellantes) | 30 g | US$30 * | estimado |

Contra el presupuesto del S04: **+40 g y +515 US$** por dron (`*` = precio estimado).

## 5. Cámara y resolución del levantamiento (HU-01)

La SIYI A8 mini (1/1.7", 8 MP, gimbal de 3 ejes, 95 g, compatible con PX4) da **4.8 cm/px a 109 m**. Para los 3 cm/px de la HU-01 hay que volar a **67 m**: más líneas de grilla, ~60 % más tiempo de vuelo por hectárea. Sirve para inspección (zoom, video 4K, seguimiento) y para levantamientos de hasta ~35-40 ha por vuelo.

Opción para la HU-01 completa (60 ha en un vuelo): una cámara de 1" a 20 MP en montaje fijo (~130-300 g, US$700-1,000). Es una **decisión del G2**: la A8 mini para el prototipo y una carga de mapeo como accesorio en el S13.

## 6. Baterías

| | DS-I | DS-D |
|---|---|---|
| Configuración | 6S2P 50S | 12S5P P42A |
| Energía nominal | 216 Wh | 907 Wh |
| Corriente continua del pack | 50 A | 225 A |
| Fabricación | Armador de packs local con celdas de distribuidor oficial (soldadura por puntos, níquel 0.15 mm) | ídem, con barra de cobre en las series de alta corriente |
| Conector | XT90-S antichispa | AS150U antichispa |
| Alternativa comercial | Pack Li-ion 21700 6S2P 10 Ah de catálogo para drones | LiPo 12S 22 Ah de catálogo (≈ 25 % más pesado por Wh) |

Sin BMS de corte en vuelo: un BMS que desconecta en el aire tira el dron. Lleva conector de balanceo, y la protección es la alarma de batería de PX4 más los umbrales mineros del S06 (aviso 35 %, RTL 25 %, aterrizaje 10 %). Las celdas se compran a distribuidores autorizados, con 2 cotizaciones: hay muchas falsificaciones de 21700.

## 7. Fuentes consultadas (2026-10)

- [T-Motor MN4006 KV380](https://www.getfpv.com/tiger-motor-mn4006-380kv-antigravity-2-black-motors.html)
- [T-Motor MN4006 KV380 (Robotshop)](https://ca.robotshop.com/products/tmotor-uav-brushless-motor-antigravity-mn4006-kv380-2x)
- [T-Motor MN4014 KV330](https://store.tmotor.com/product/mn4014-kv330-motor-navigator-type.html)
- [T-Motor U8 Lite KV100](https://www.ligpower.com/product/u8-lite-kv100-u-efficiency.html)
- [T-Motor U8 Lite KV100 (precio)](https://irlock.com/products/t-motor-u8-lite-efficiency-type-uav-motor-kv100-net)
- [MAD M6C12 EEE KV150](https://openelab.io/nl/products/mad-m6c12-eee-kv150-motor)
- [T-Motor MN6007II](https://www.unmannedtechshop.co.uk/products/t-motor-mn6007-ii-vtol-uav-motor-kv160-kv320)
- [Hobbywing X6 Plus G2 (descartado)](https://www.hobbywing.com/en/products/x6-plus-g2)
- [APD 120F3[X] V2](https://www.getfpv.com/apd-f-series-120f3-x-v2-120a-12s-50v-blheli-32-esc.html)
- [SIYI A8 mini](https://siyi.biz/en/product/tri-axis-single-camera-gimbal/a8-mini/)
- [Pixhawk 6C (precio)](https://pyrodrone.com/collections/all-inventory/brand_holybro)
- [RFD900x (precio)](https://www.unmannedtechshop.co.uk/collections/wireless-telemetry?page=2)
