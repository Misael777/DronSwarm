# E6 · Placas en KiCad

> Flujo: esquema SKIDL → netlist (`electronics/build_netlists.sh`) → placa (`make_boards.py`) → ruteo (`route_boards.py`,
> Freerouting) → DRC (`kicad-cli`) → fabricación (`fab_outputs.sh`, se niega si el DRC no está limpio).
> Abrir cada placa con KiCad 8: `electronics/kicad/<placa>/<placa>.kicad_pro` (la biblioteca `DronSwarm` se carga sola).

## Estado (2026-10-26)

| Placa | Piezas | Contorno actual · meta [mm] | Estado | Falta |
|---|---|---|---|---|
| GNSS (`gnss`) | 32 | 40 × 40 · 40 × 40 | **ruteada**: 0 errores de DRC, 1 conexión de 3V3 por cerrar; RF en microcinta de 0.36 mm ruteada a mano por script | cerrar 1 conexión, revisión humana, Gerber |
| BMS 6S (`bms_ds_i`) | 105 | 60 × 51 · 60 × 40 | colocada, nets asignadas | ruteo manual (el autorruteador dejó 27 pendientes) |
| BMS 12S (`bms_ds_d`) | 141 | 80 × 46 · 80 × 45 | colocada, nets asignadas | ruteo manual (el autorruteador no terminó en 1 h) |
| Controladora (`fc`) | 165 | 55 × 73 · 55 × 45 | colocada en dos caras, nets asignadas | colocación densa con conectores al borde y ruteo manual |
| ESC 4 en 1 DS-I (`esc_ds_i`) | 335 | 60 × 88 · 60 × 60 | colocada, nets asignadas | colocación de potencia (transistores en dos caras) y ruteo manual |
| ESC GaN DS-D (`esc_ds_d`) | 115 | 40 × 70 · 40 × 70 | colocada; **faltan las 3 huellas del LMG1210** | plano RVR0019A de TI, colocación del lazo GaN, ruteo manual |
| Cargador GaN (`charger`) | 131 | 100 × 80 · 100 × 80 | colocada; **faltan las 2 huellas del LMG1210** | ídem |

La colocación automática agrupa por subcircuito y pone los pasivos chicos abajo, pero **no está optimizada**: es el
punto de partida para colocar a mano en KiCad. El ruteo automático sirve para placas chicas de señal (GNSS); en las de
potencia y en las densas no converge y además no conviene: el lazo de conmutación se rutea a mano.

## Biblioteca `DronSwarm.pretty` (`gen_footprints.py`, desde las hojas de datos)

| Huella | Fuente |
|---|---|
| `EPC2302_QFN-3x5mm` | EPC2302: cobre, aberturas de máscara (máscara definida por soldadura) y esténcil, págs. 11-12 |
| `Bosch_LGA-16_3x4.5mm_P0.5mm` | BMI088, fig. 11 |
| `Quectel_LG290P_LGA-79_12.2x16mm` | LG290P(03) Hardware Design, fig. 18 (cortesía de 3 mm alrededor del módulo, como pide Quectel) |
| `Pad_Power_4x3mm`, `6x4mm`, `8x5mm` | pads para soldar cables de potencia |
| **`TI_WQFN-19_RVR0019A_4x3mm`** | **PENDIENTE**: la hoja SNOSD12D del LMG1210 no trae el dibujo mecánico; bajar el plano RVR0019A desde la página del producto en ti.com y agregarlo a `gen_footprints.py` |

## Reglas de las placas

- 4 capas: señal / GND (In1) / alimentación (In2) / señal. Clase **Potencia** 1.0 mm; **RF50** 0.36 mm (GNSS).
- **Placas de 12S a 5,000 msnm** (ESC DS-D, BMS DS-D, cargador): IPC-2221 pide 1.5 mm entre conductores de 51-100 V
  sin recubrimiento por encima de 3,050 m (B3); con **recubrimiento conformado** (B4) bastan 0.13 mm → el recubrimiento
  es obligatorio y está en el presupuesto.
- Lazo de potencia GaN (ESC DS-D, cargador): diseño "vertical" de EPC, con los condensadores de 2.2 µF en la cara
  opuesta, directamente bajo el medio puente, y retorno por In1 (nota de aplicación de EPC sobre el ruteo de GaN).

## Revisión humana antes de fabricar (cada placa)

1. DRC limpio y 0 conexiones pendientes; `bash electronics/kicad/fab_outputs.sh <placa>`.
2. Huellas propias impresas a 1:1 sobre la pieza real.
3. Potencia: ancho de pistas por corriente (IPC-2152), vías térmicas bajo transistores y LDO.
4. RF (GNSS): microcinta de 50 Ω con el stack real del fabricante, plano de GND continuo bajo la línea.
5. Distancias de 12S y recubrimiento conformado anotados en el plano de fabricación.
