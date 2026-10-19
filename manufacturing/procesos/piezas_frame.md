# Plan de fabricación de piezas · frames DS-I y DS-D

- Sprint: S08 · Tarea: S08-07 · Fuente CAD: `cad/openscad/{inspection,delivery}/` · Archivos de fabricación: `cad/exports/{inspection,delivery}/`
- Para regenerar todo tras un cambio de diseño: `.venv/bin/python tools/cad/build_frame.py inspection` y `... delivery`
- Fabricación y ensamble del DS-I en detalle: [dfm_dfa_ds-i.md](../../docs/ingenieria/dfm_dfa_ds-i.md) · resistencia: [fea_frames.md](../../docs/ingenieria/fea_frames.md)

## 1. Qué se manda a cada proveedor

| Proveedor | DS-I | DS-D | Archivos |
|---|---|---|---|
| **Corte CNC de carbono** (router con fresa de 2-3 mm) | 2 placas de 3 mm, Ø168 mm | 2 placas de 3 mm, Ø363 mm | `center_plate_top.dxf`, `center_plate_bottom.dxf` (mm, 1:1) |
| **Corte por agua o láser de fibra** (aluminio 6061-T6 de 6 mm) | — | 1 gancho de carga | `payload_release_hook.dxf` + taladro Ø5.3 (perno) |
| **Tubos de carbono enrollado** (compra + corte) | 4 × Ø20×1 × 287 mm, 4 × Ø12×1 × 130 mm | 6 × Ø22×1.5 × 530 mm, 4 × Ø16×1 × 397 mm, 2 × Ø16×1 × 560 mm | lista de corte (sección 3) |
| **Impresión FDM** (PA12-CF y TPU) | 15 + 4 piezas | 24 + 4 piezas | `*.stl` de cada pieza (sección 2) |

La plancha de carbono debe ser **3K twill cuasi-isótropa** (capas a 0/45/90/−45), no unidireccional: las placas trabajan en todas direcciones. Hay que pedir el certificado del espesor y del gramaje.

## 2. Perfiles de impresión

Material: PA12-CF (nailon 12 con fibra de carbono picada) en boquilla endurecida. Se seca 6 h a 80 °C antes de imprimir y se guarda con desecante. La pieza es ~50 % más débil entre capas, así que **la orientación sigue la carga** (FEA).

| Pieza | Dron | Cant. | Orientación en la cama | Perímetros / relleno | Notas |
|---|---|---|---|---|---|
| Bloque de brazo | DS-I | 4 | Cara del extremo (eje del tubo vertical) | 4 / 40 % giroide | Agujero del tubo sin soporte |
| Bloque desmontable | DS-D | 6 | Cara del extremo | 5 / 50 % giroide | Las ranuras de la leva quedan verticales |
| Soporte de motor DMI | ambos | 4 / 6 | Placa DMI sobre la cama | 4 / 40 % | Soporte de árbol bajo el manguito |
| Abrazadera de pata | DS-I | 4 | Casquillo abajo | 5 / 50 % | — |
| Soporte de pata / T del esquí | DS-D | 4 + 4 | Cara plana sobre la cama / casquillo abajo | 5 / 50 % | — |
| Carcasa IP54 | ambos | 1 | Techo sobre la cama | 5 / 30 %, 100 % en la brida | Lijar la brida plana (≤ 0.2 mm). ASA si va pintada de blanco (UV) |
| Bandeja de batería | ambos | 1 | Cara plana | 3 / 30 % | — |
| Cuerpo de liberación | DS-D | 1 | Cara contra la placa sobre la cama | 4 / 40 % | Bujes del perno escariados a Ø5.3 |
| Adaptador de cámara, FPV, luces | — | — | Cara plana | 3 / 30 % | — |
| Pie amortiguador / zapata del esquí | DS-I / DS-D | 4 / 4 | Boca abajo / cara plana | TPU 85A, 2 / 15-20 % giroide | Es el resorte del tren: no subir el relleno |

**Control de calidad por lote:** 1 probeta de tracción (ISO 527-2 tipo 1A) por bobina y por orientación (XY y Z). Criterio: ≥ 45 MPa en XY y ≥ 22 MPa en Z, que es lo que supone el FEA. Si no cumple, se cambia de proveedor o de perfil antes de imprimir las piezas de vuelo.

## 3. Lista de corte de tubos

| Tubo | Dron | Medida | Largo | Cant. | Total |
|---|---|---|---|---|---|
| Brazo | DS-I | Ø20 × 1 | 287 mm | 4 | 1.15 m |
| Pata | DS-I | Ø12 × 1 | 130 mm | 4 | 0.52 m |
| Brazo | DS-D | Ø22 × 1.5 | 530 mm | 6 | 3.18 m |
| Pata | DS-D | Ø16 × 1 | 397 mm | 4 | 1.59 m |
| Esquí | DS-D | Ø16 × 1 | 560 mm | 2 | 1.12 m |

Los tubos se cortan con disco diamantado y plantilla de tope (±0.5 mm), y las puntas se lijan a 90°. Se trabaja con mascarilla P2 porque el polvo de carbono es irritante y conductor.

## 4. Pedido de cotización (para los talleres de Lima)

> Corte CNC de 2 placas de fibra de carbono 3K twill cuasi-isótropa de 3 mm según DXF adjuntos (mm, 1:1). Fresa de
> 2-3 mm, agujeros pasantes cortados (sin taladrar), bordes lijados. Cantidad: 1 juego DS-I (placas Ø168) y 1 juego
> DS-D (placas Ø363). Indicar precio con plancha incluida, plazo y espesor real medido.

> Impresión 3D en PA12-CF de las piezas STL adjuntas, con orientación y perfiles según la tabla. Incluir 2 probetas
> ISO 527-2 1A (XY y Z) del mismo lote. Indicar precio por pieza, plazo y marca del filamento.

## 5. Tiempos y costos estimados (a confirmar con las cotizaciones del S09)

| Rubro | DS-I | DS-D |
|---|---|---|
| Impresión PA12-CF | ≈ 0.33 kg, ≈ 30 h · US$45-70 | ≈ 0.70 kg, ≈ 60 h · US$90-140 |
| Impresión TPU | ≈ 35 g · US$5 | ≈ 40 g · US$6 |
| Corte CNC de placas | US$25-40 | US$70-110 |
| Gancho de aluminio | — | US$15-25 |
| Tubos de carbono | US$30-35 | US$110-140 |
| Tornillería y levas | US$6 | US$35 (6 levas de apriete rápido + M4) |
| **Frame completo** | **≈ US$110-155** | **≈ US$325-455** |
| Presupuesto del S04 (placas + brazos + impresas) | US$105 | US$327 |

Los dos frames pueden quedar hasta ~US$50 (DS-I) y ~US$130 (DS-D) sobre lo presupuestado, sobre todo por la impresión de PA12-CF. Hay dos maneras de bajarlo: imprimir en casa (filamento ~US$60/kg) o pasar los bloques a **inyección** cuando la serie supere ~200 unidades (S20, costo de fabricación en serie).
