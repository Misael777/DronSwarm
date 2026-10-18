# Informe de diseño preliminar · DS-I, DS-D y DS-H

> Generado por `engineering/sizing.py` el 2026-10-17. No editar a mano: cambiar `engineering/config/` y volver a correr `.venv/bin/python -m engineering.sizing`.

**Estado:** dimensionamiento preliminar (S04). Los requisitos son supuestos del PRD pendientes del Gate G0; este informe muestra que **los requisitos de autonomía del PRD no son alcanzables** y propone alternativas.

## 1. Conclusiones

- **DS-I:** el requisito actual del PRD no tiene ninguna solución factible. Escenario recomendado **D** (C sin RTK ni computadora a bordo (versión base; RTK opcional)): hélice 17x7.7", batería 6S2P 50S, MTOW 2.695 kg, BOM ≈ US$735 (objetivo US$600), 31.3 min con batería nueva a 4,500 msnm (≈ 47.4 min medido como DJI).
- **DS-D:** el requisito actual del PRD no tiene ninguna solución factible. Escenario recomendado **C** (5 kg, ≥ 20 min con batería nueva): hélice 26x11.7", batería 12S5P P42A, MTOW 15.61 kg, BOM ≈ US$1,627 (objetivo US$1,600), 20.3 min con batería nueva a 4,500 msnm (≈ 31.3 min medido como DJI).
- **DS-H:** el requisito actual del PRD tiene 10 soluciones. Escenario recomendado **A** (10 kg, ≥ 15 min en hover con batería nueva + entrega de 3 km): hélice 30x10.5", batería 12S8P P42A, MTOW 30.262 kg, BOM ≈ US$2,667 (objetivo US$3,000), 16.4 min con batería nueva a 4,500 msnm (≈ 25.3 min medido como DJI).
- La autonomía que publica DJI se mide a nivel del mar, con batería nueva y hasta 0 %. El PRD la pedía a 4,500 msnm, con 10 % de reserva y batería envejecida: ≈ 1.6 veces más exigente. La columna "estilo DJI" permite comparar en igualdad.
- El modelo es conservador: con el DJI M400 predice 13 % menos autonomía que la real (sección 3).

## 2. Casos de diseño y factores de seguridad

| Caso | Altitud | Temperatura | Densidad del aire | vs nivel del mar |
|---|---|---|---|---|
| Empuje (peor caso) | 5,000 msnm | 15 °C | 0.653 kg/m³ | −47 % |
| Autonomía | 4,500 msnm | 0 °C | 0.736 kg/m³ | −40 % |
| Batería en frío | — | -15 °C | — | capacidad ≈ 80 % |

Factores: thrust_to_weight = 2.0, motor_current = 1.3, esc_current = 1.3, battery_capacity = 1.3, structure = 2.5, flight_time_margin = 1.2.

## 3. Modelo y validación (S03)

Hélice por BEMT con corrección de Reynolds, motor por circuito equivalente con eficiencia según tamaño, batería Li-ion 21700 con caída de voltaje y frío. Se calibró un parámetro con el DJI M4E y se verificó con el M400:

| Dron | Rol | Ficha (hover) | Sin calibrar | Modelo calibrado | Error |
|---|---|---|---|---|---|
| DJI Matrice 4E | calibración | 42.0 min | 47.0 min | 42.0 min | -0.0 % |
| DJI Matrice 400 (con H30T) | validación | 53.0 min | 50.5 min | 45.9 min | -13.4 % |

Factor de calibración (arrastre de perfil): 2.171. **El criterio de error < 10 % no se cumple en el M400 (−13 %)**: el modelo subestima la eficiencia de drones grandes. El error es conservador (diseños algo más grandes de lo necesario, sobre todo el DS-D). Validación definitiva con el banco de empuje en S10.

## 4. Escenarios de requisitos (para decidir en el Gate G0)

### DS-I · MTOW objetivo ≤ 2.5 kg · BOM objetivo ≤ US$600

| Esc. | Requisito | Factibles | Hélice | Batería | MTOW | BOM | Nueva 4,500 m | Fin de vida | Frío −15 °C | Estilo DJI |
|---|---|---|---|---|---|---|---|---|---|---|
| A | Requisito actual del PRD: ≥ 35 min con batería al final de su vida | 0/1296 | — | — | — | — | — | — | — | Rechazos: Autonomía en hover ≥ 35 min (batería al final de su vida, 4,500 msnm, 0 °C) (1007), hélice o estructura insuficiente (219) |
| B | ≥ 35 min con batería nueva (a 4,500 msnm, 0 °C, aterrizando con 10 %) | 62/1296 | 18x6.3" | 6S3P 50S | 3.414 kg | US$1,012 | 35.3 min | 27.2 min | 31.9 min | 54.1 min |
| C | ≥ 30 min con batería nueva (el mínimo de targets.md) | 245/1296 | 18x8.1" | 6S2P 50S | 2.839 kg | US$966 | 30.7 min | 23.6 min | 27.8 min | 46.5 min |
| D ★ | C sin RTK ni computadora a bordo (versión base; RTK opcional) | 303/1296 | 17x7.7" | 6S2P 50S | 2.695 kg | US$735 | 31.3 min | 24.1 min | 28.3 min | 47.4 min |
| E | ≥ 25 min con batería al final de su vida | 143/1296 | 17x5.9" | 6S3P 50S | 3.389 kg | US$1,006 | 33.8 min | 26.0 min | 30.5 min | 51.7 min |

Se muestra el diseño de menor BOM de cada escenario. ★ = recomendado.

### DS-D · MTOW objetivo ≤ 16.0 kg · BOM objetivo ≤ US$1,600

| Esc. | Requisito | Factibles | Hélice | Batería | MTOW | BOM | Nueva 4,500 m | Fin de vida | Frío −15 °C | Estilo DJI |
|---|---|---|---|---|---|---|---|---|---|---|
| A | Requisito actual del PRD: 5 kg, ≥ 25 min con batería al final de su vida | 0/504 | — | — | — | — | — | — | — | Rechazos: Autonomía en hover ≥ 25 min (batería al final de su vida, 4,500 msnm, 0 °C) (367), TWR ≥ 2.0 a 5,000 msnm y 15 °C (106) |
| B | 5 kg, ≥ 25 min con batería nueva | 21/504 | 30x13.5" | 12S6P P45B | 17.336 kg | US$1,875 | 25.9 min | 19.9 min | 23.4 min | 39.9 min |
| C ★ | 5 kg, ≥ 20 min con batería nueva | 102/504 | 26x11.7" | 12S5P P42A | 15.61 kg | US$1,627 | 20.3 min | 15.6 min | 18.4 min | 31.3 min |
| D | 4 kg (mínimo de targets.md), ≥ 20 min con batería nueva | 153/504 | 26x11.7" | 12S4P P42A | 13.183 kg | US$1,497 | 20.7 min | 15.9 min | 18.7 min | 31.8 min |
| E | 5 kg, ≥ 15 min con batería nueva (manda la misión de entrega de 3 km) | 165/504 | 24x10.8" | 12S4P P42A | 14.188 kg | US$1,500 | 17.2 min | 13.3 min | 15.6 min | 26.5 min |

Se muestra el diseño de menor BOM de cada escenario. ★ = recomendado.

### DS-H · MTOW objetivo ≤ 30.0 kg · BOM objetivo ≤ US$3,000

| Esc. | Requisito | Factibles | Hélice | Batería | MTOW | BOM | Nueva 4,500 m | Fin de vida | Frío −15 °C | Estilo DJI |
|---|---|---|---|---|---|---|---|---|---|---|
| A ★ | 10 kg, ≥ 15 min en hover con batería nueva + entrega de 3 km | 10/432 | 30x10.5" | 12S8P P42A | 30.262 kg | US$2,667 | 16.4 min | 12.6 min | 14.8 min | 25.3 min |
| B | 10 kg, ≥ 20 min en hover con batería nueva | 0/432 | — | — | — | — | — | — | — | Rechazos: TWR ≥ 2.0 a 5,000 msnm y 15 °C (238), Autonomía en hover ≥ 20 min (batería nueva, 4,500 msnm, 0 °C) (191) |

Se muestra el diseño de menor BOM de cada escenario. ★ = recomendado.

## 5. Diseños recomendados

### DS-I · escenario D

C sin RTK ni computadora a bordo (versión base; RTK opcional).

**Requisitos para comprar o fabricar los componentes (entrada de S09 y S17):**

| Componente | Especificación |
|---|---|
| Hélice | 17x7.7" (relación paso/diámetro 0.45), 4 unidades |
| Motor | Kv ≈ 278 rpm/V · potencia máx. ≈ 296 W · corriente máx. ≈ 13.7 A · masa ≈ 74 g |
| ESC | ≥ 18 A por canal |
| Batería | 6S2P 50S · 216.0 Wh · 998 g |
| Brazos | tubo de carbono Ø20×1 mm, 252 mm · distancia entre ejes 672 mm |

**Desempeño:**

| Métrica | Valor |
|---|---|
| MTOW | 2.695 kg |
| Empuje máximo a 5,000 msnm y 15 °C | 5.64 kgf (límite: voltaje) |
| Potencia en hover a 4,500 msnm | 330 W (3126 rpm, eficiencia de motor 84%, FM 0.588) |
| Autonomía en hover · nueva / fin de vida / frío / estilo DJI | 31.3 / 24.1 / 28.3 / 47.4 min |

**Verificaciones:**

- ✔ TWR ≥ 2.0 a 5,000 msnm y 15 °C: 2.09
- ✔ Autonomía en hover ≥ 30 min (batería nueva, 4,500 msnm, 0 °C): 31.3
- ✔ Empuje de hover entre 40% y 65% del máximo (4,500 msnm): 0.44
- ✔ Corriente de batería dentro del límite de las celdas: 48.3
- ✔ Brazos: resistencia (FS 2.5), deflexión y frecuencias: Ø20×1 mm

**Presupuesto de masa y costo:**

| Subsistema | Masa | Costo |
|---|---|---|
| equipo fijo | 705 g | US$434 |
| carga útil | 0 g | — |
| batería | 998 g | US$69 |
| motores | 296 g | US$73 |
| hélices | 139 g | US$29 |
| ESC | 59 g | US$25 |
| brazos | 96 g | US$24 |
| soportes de motor | 60 g | — |
| placas centrales | 253 g | US$59 |
| piezas impresas y tornillería | 90 g | US$21 |
| **Total** | **2,695 g** | **US$735** |

**Inercias (para el SDF de S05):** Ixx = 0.0377, Iyy = 0.0386, Izz = 0.0721 kg·m²; CG [-0.0, -0.0, -0.005] m. **Motor en Gazebo:** motorConstant = 6.164e-05, momentConstant = 0.0288, maxRotVelocity = 503 rad/s.

**Brazo:** margen de resistencia 15.2 (FS 2.5 ya incluido), deflexión 0.15 % de la longitud, frecuencia natural 79.0 Hz vs giro 1P 52.1 Hz y paso de pala 2P 104.2 Hz.

### DS-D · escenario C

5 kg, ≥ 20 min con batería nueva.

**Requisitos para comprar o fabricar los componentes (entrada de S09 y S17):**

| Componente | Especificación |
|---|---|
| Hélice | 26x11.7" (relación paso/diámetro 0.45), 6 unidades |
| Motor | Kv ≈ 116 rpm/V · potencia máx. ≈ 1,380 W · corriente máx. ≈ 31.9 A · masa ≈ 345 g |
| ESC | ≥ 42 A por canal |
| Batería | 12S5P P42A · 907.2 Wh · 4734 g |
| Brazos | tubo de carbono Ø22×1.5 mm, 545 mm · distancia entre ejes 1453 mm |

**Desempeño:**

| Métrica | Valor |
|---|---|
| MTOW | 15.61 kg |
| Empuje máximo a 5,000 msnm y 15 °C | 33.08 kgf (límite: voltaje) |
| Potencia en hover a 4,500 msnm | 2134 W (2628 rpm, eficiencia de motor 86%, FM 0.629) |
| Autonomía en hover · nueva / fin de vida / frío / estilo DJI | 20.3 / 15.6 / 18.4 / 31.3 min |
| Misión de entrega 3 km (ida con carga, vuelta vacío) | 282 Wh + 20 % de reserva = 338 Wh · disponibles 723 Wh (nueva) |

**Verificaciones:**

- ✔ TWR ≥ 2.0 a 5,000 msnm y 15 °C: 2.12
- ✔ Autonomía en hover ≥ 20 min (batería nueva, 4,500 msnm, 0 °C): 20.3
- ✔ Empuje de hover entre 40% y 65% del máximo (4,500 msnm): 0.43
- ✔ Corriente de batería dentro del límite de las celdas: 170.4
- ✔ Brazos: resistencia (FS 2.5), deflexión y frecuencias: Ø22×1.5 mm
- ✔ Motor caído: 4 rotores sostienen ≥ 1.1 × peso: 1.41
- ✔ Entrega 3 km + regreso con 20 % de reserva (batería nueva): +114% de margen

**Presupuesto de masa y costo:**

| Subsistema | Masa | Costo |
|---|---|---|
| equipo fijo | 1,095 g | US$519 |
| carga útil | 5,000 g | — |
| batería | 4,734 g | US$255 |
| motores | 2,069 g | US$338 |
| hélices | 487 g | US$101 |
| ESC | 173 g | US$87 |
| brazos | 505 g | US$84 |
| soportes de motor | 90 g | — |
| placas centrales | 1,366 g | US$222 |
| piezas impresas y tornillería | 90 g | US$21 |
| **Total** | **15,610 g** | **US$1,627** |

**Inercias (para el SDF de S05):** Ixx = 1.0846, Iyy = 1.1049, Izz = 1.7319 kg·m²; CG [-0.0, 0.0, -0.0838] m. **Motor en Gazebo:** motorConstant = 3.369e-04, momentConstant = 0.0411, maxRotVelocity = 425 rad/s.

**Brazo:** margen de resistencia 2.3 (FS 2.5 ya incluido), deflexión 1.41 % de la longitud, frecuencia natural 18.5 Hz vs giro 1P 43.8 Hz y paso de pala 2P 87.6 Hz.

### DS-H · escenario A

10 kg, ≥ 15 min en hover con batería nueva + entrega de 3 km.

**Requisitos para comprar o fabricar los componentes (entrada de S09 y S17):**

| Componente | Especificación |
|---|---|
| Hélice | 30x10.5" (relación paso/diámetro 0.35), 8 unidades |
| Motor | Kv ≈ 120 rpm/V · potencia máx. ≈ 2,064 W · corriente máx. ≈ 47.8 A · masa ≈ 516 g |
| ESC | ≥ 62 A por canal |
| Batería | 12S8P P42A · 1,451.5 Wh · 7556 g |
| Brazos | tubo de carbono Ø30×2 mm, 821 mm · distancia entre ejes 2190 mm |

**Desempeño:**

| Métrica | Valor |
|---|---|
| MTOW | 30.262 kg |
| Empuje máximo a 5,000 msnm y 15 °C | 64.85 kgf (límite: voltaje) |
| Potencia en hover a 4,500 msnm | 4229 W (2615 rpm, eficiencia de motor 87%, FM 0.637) |
| Autonomía en hover · nueva / fin de vida / frío / estilo DJI | 16.4 / 12.6 / 14.8 / 25.3 min |
| Misión de entrega 3 km (ida con carga, vuelta vacío) | 695 Wh + 20 % de reserva = 833 Wh · disponibles 1157 Wh (nueva) |

**Verificaciones:**

- ✔ TWR ≥ 2.0 a 5,000 msnm y 15 °C: 2.14
- ✔ Autonomía en hover ≥ 15 min (batería nueva, 4,500 msnm, 0 °C): 16.4
- ✔ Empuje de hover entre 40% y 65% del máximo (4,500 msnm): 0.43
- ✔ Corriente de batería dentro del límite de las celdas: 359.4
- ✔ Brazos: resistencia (FS 2.5), deflexión y frecuencias: Ø30×2 mm
- ✔ Motor caído: 6 rotores sostienen ≥ 1.1 × peso: 1.61
- ✔ Entrega 3 km + regreso con 20 % de reserva (batería nueva): +39% de margen

**Presupuesto de masa y costo:**

| Subsistema | Masa | Costo |
|---|---|---|
| equipo fijo | 1,515 g | US$555 |
| carga útil | 10,000 g | — |
| batería | 7,556 g | US$399 |
| motores | 4,129 g | US$642 |
| hélices | 864 g | US$180 |
| ESC | 330 g | US$174 |
| brazos | 1,850 g | US$210 |
| soportes de motor | 120 g | — |
| placas centrales | 3,808 g | US$486 |
| piezas impresas y tornillería | 90 g | US$21 |
| **Total** | **30,262 g** | **US$2,667** |

**Inercias (para el SDF de S05):** Ixx = 4.2563, Iyy = 4.3299, Izz = 7.6714 kg·m²; CG [-0.0, -0.0, -0.0847] m. **Motor en Gazebo:** motorConstant = 4.946e-04, momentConstant = 0.0426, maxRotVelocity = 426 rad/s.

**Brazo:** margen de resistencia 2.8 (FS 2.5 ya incluido), deflexión 1.38 % de la longitud, frecuencia natural 15.0 Hz vs giro 1P 43.6 Hz y paso de pala 2P 87.2 Hz.

## 6. Decisiones para el Gate G0

1. **Base de la autonomía:** medir los targets con batería nueva (recomendado) o al final de su vida.
2. **DS-I:** aceptar ≥ 30 min con batería nueva a 4,500 msnm y RTK/computadora como opcionales (escenario D).
3. **DS-D:** aceptar ≥ 20 min en hover con 5 kg (escenario C); la misión de entrega de 3 km se cumple igual.
4. **Precio:** con el equipo del PRD, el BOM del DS-I no baja de ≈ US$800; revisar el precio objetivo o la cámara.

## 7. Limitaciones

- Componentes paramétricos (no de catálogo): masa, Rm e I0 del motor siguen relaciones típicas; se reemplazan en S09.
- Celdas 21700 con datos de ficha y costos estimados 2026, sin cotizar.
- Hélices modeladas por BEMT, no medidas (las bases UIUC/APC bloquean descargas automáticas): banco de empuje en S10.
- Masas de estructura simplificadas (placas, tornillería, carcasa); el CAD de S07-S08 las reemplaza.
