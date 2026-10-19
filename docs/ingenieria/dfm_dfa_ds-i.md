# DFM / DFA · frame del DS-I

- Sprint: S07 · Tarea: S07-06 · Fuente: `cad/openscad/inspection/` · Exportes: `cad/exports/inspection/`
- Masas y ensamble: `cad/exports/inspection/masas.json` (generado por `tools/cad/build_frame.py inspection`)
- FEA: `cad/freecad/inspection/fea/resultados.json` · decisiones: ADR-011

## 1. Piezas por proceso

| Pieza | Cant. | Proceso | Material | Masa c/u | Archivo de fabricación |
|---|---|---|---|---|---|
| Placa central inferior | 1 | Corte CNC | Carbono 3K twill, 3 mm, cuasi-isótropo | 98 g | `center_plate_bottom.dxf` |
| Placa central superior | 1 | Corte CNC | ídem | 102 g | `center_plate_top.dxf` |
| Tubo de brazo Ø20×1 × 287 mm | 4 | Corte de tubo | Carbono enrollado | 27 g | lista de corte (abajo) |
| Tubo de pata Ø12×1 × 130 mm | 4 | Corte de tubo | Carbono enrollado | 7 g | lista de corte |
| Bloque de brazo | 4 | Impresión FDM | PA12-CF | 18 g | `arm_block.stl` |
| Soporte de motor DMI-S | 4 | Impresión FDM | PA12-CF | 15 g | `motor_mount.stl` |
| Abrazadera de pata | 4 | Impresión FDM | PA12-CF | 11 g | `leg_clamp.stl` |
| Pie amortiguador | 4 | Impresión FDM | TPU 85A | 9 g | `foot.stl` |
| Bandeja de batería | 1 | Impresión FDM | PA12-CF | 38 g | `battery_tray.stl` |
| Adaptador de cámara (sup. / inf.) | 1 + 1 | Impresión FDM | PA12-CF | 14 g / 21 g | `gimbal_mount_top.stl`, `gimbal_mount_bottom.stl` |
| Carcasa IP54 | 1 | Impresión FDM | PA12-CF (o ASA si se pinta) | 75 g | `housing.stl` |

**Frame: 0.69 kg** (presupuesto del S04: 0.68 kg) más ~6 % de tornillería. Son 12 piezas distintas y 30 piezas en total.

## 2. Reglas de diseño para fabricar (DFM)

**Corte CNC de carbono.** El DXF trae solo contornos y agujeros, en mm y a escala 1:1. La fresa de 2-3 mm redondea las esquinas interiores. Los agujeros M3 se cortan a Ø3.3 mm, sin taladrado posterior. Hay que lijar y sellar los bordes con epoxi o CA, porque el polvo de carbono es conductor. Tolerancia: ±0.1 mm.

**Impresión FDM.** Ninguna pieza supera 150 mm de lado, así que entran en una impresora de 220 × 220 mm. El PA12-CF se imprime con boquilla endurecida de 0.4-0.6 mm y se seca el filamento 6 h a 80 °C. La pieza es ~50 % más débil entre capas, por eso **la orientación sigue la carga del FEA**:

| Pieza | Orientación en la cama | Por qué | Perfil |
|---|---|---|---|
| Bloque de brazo | Cara del extremo (eje del tubo vertical) | Agujero del tubo sin soportes y capas perpendiculares al tubo | 4 perímetros, 40 % giroide |
| Soporte de motor | Placa DMI sobre la cama | El empuje flexiona la placa en el plano de las capas | 4 perímetros, 40 %, soporte de árbol bajo el manguito |
| Abrazadera de pata | Casquillo hacia abajo | La caída comprime el casquillo en el eje (FS 3.6 en el plano, ≈ 1.8 entre capas) | 5 perímetros, 50 % |
| Carcasa IP54 | Techo sobre la cama | Brida plana arriba (sella mejor), sin soportes dentro | 5 perímetros, 100 % en la brida |
| Pie amortiguador | Boca hacia abajo | Elástico | TPU 85A, 2 perímetros, 15 % giroide |
| Bandeja y adaptador | Cara plana sobre la cama | Sin soportes | 3 perímetros, 30 % |

**Tubos.** Se cortan con disco diamantado y plantilla de tope, con tolerancia de ±0.5 mm. Las puntas se lijan a 90°.

## 3. Reglas de diseño para ensamblar (DFA)

- **Un solo tipo de tornillo:** M3 de cabeza cilíndrica allen (ISO 4762, A2-70) en 3 largos, con tuerca autoblocante M3. Los motores traen sus propios tornillos.
- **Una sola herramienta:** llave allen de 2.5 mm, más una llave de 5.5 mm para las tuercas.
- **Piezas simétricas e intercambiables:** los 4 brazos, bloques, soportes, abrazaderas, patas y pies son iguales. Solo las dos placas son distintas, y no se pueden confundir: la superior lleva el agujero del prensaestopa.
- **Sin pegamento estructural:** todo es atornillado o por apriete, así que cualquier pieza se cambia en campo (HU-12).

| Tornillo | Cant. | Dónde |
|---|---|---|
| M3 × 35 | 20 | Placas + bloques (16) y apriete de los bloques (4) |
| M3 × 12 | 24 | Apriete de soportes de motor (8), abrazaderas de pata (4), pasadores de pata (4) y adaptador de cámara (8, con los amortiguadores) |
| M3 × 10 | 16 | Carcasa (8, con arandela de nylon) y bandeja de batería (4), más controladora (4, sobre ojales de goma) |
| Tuerca autoblocante M3 | 60 | — |

## 4. Secuencia de ensamble (objetivo: 45 min, una persona)

1. Bloques de brazo sobre la placa inferior: 16 × M3×35 desde abajo, todavía sin apretar.
2. Tubos de brazo en los bloques, con el extremo a ras de la cara interior. Placa superior. Apretar las 16 tuercas.
3. Apretar el tornillo de cada bloque sobre su tubo.
4. Abrazaderas de pata a 70 mm del bloque, con la oreja hacia afuera. Insertar las patas y pasar el pasador. Encajar los pies a presión.
5. Soportes de motor en las puntas, con las ranuras DMI a 45°. Motores con sus tornillos y fijador de rosca azul.
6. Pasar los cables de motor por los tubos hasta el espacio entre placas.
7. Bandeja de batería y adaptador de cámara con amortiguadores bajo la placa inferior.
8. Controladora (sobre ojales de goma), ESC, computadora a bordo y radio sobre la placa superior. Prensaestopa M12.
9. Junta de EPDM en el canal de la carcasa. Carcasa con 8 × M3 y arandela de nylon, apretando en cruz.
10. Prueba de hermeticidad: chorro de agua de 30 s por cada lado (método IP54 simplificado). Luego, hélices.

## 5. Tiempos y costos de fabricación (estimados, a cotizar en el S09)

| Proceso | Tiempo | Costo estimado (Lima, 2026) |
|---|---|---|
| Impresión PA12-CF (~0.33 kg, 15 piezas) | ≈ 30 h de máquina | US$45-70 (material + máquina) |
| Impresión TPU (4 pies) | ≈ 4 h | US$5 |
| Corte CNC de 2 placas | 20 min | US$25-40 (incluye la plancha 200 × 200 mm) |
| Tubos de carbono (1.15 m Ø20 + 0.52 m Ø12) | 15 min de corte | US$30-35 |
| Tornillería | — | US$6 |
| Ensamble | 45 min | — |

En el BOM del S04, placas + brazos + impresas suman US$105 (59 + 24 + 21). Con esta tabla, el frame real cuesta ≈ US$110-155, es decir hasta +US$50 sobre el presupuesto (sobre todo por la impresión de PA12-CF). Se confirma con las cotizaciones del S09.
