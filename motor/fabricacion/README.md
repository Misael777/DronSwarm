# Fabricación del motor propio (M6)

Cómo hacer el motor elegido en M2 con la cortadora láser y la impresora 3D. Los archivos se regeneran desde el diseño con
`.venv/bin/python motor/fabricacion/gen_cad.py`:

| Pieza | Archivo (`cad/exports/motor/<dron>/`) | Máquina | Material | Cantidad por motor (DS-I / DS-D) |
|---|---|---|---|---|
| Lámina del estator | `lamina_estator.dxf` | láser de fibra | acero al silicio 0.20 mm (NO20) | ver [valores.md](valores.md) |
| Anillo del rotor | `anillo_rotor.dxf` | láser de fibra | acero DC01 1.0 mm | ver [valores.md](valores.md) |
| Tapa (lleva la hélice y el eje) | `tapa.stl` | impresora | PETG (ASA o PA-CF mejor) | 1 |
| Base (rodamientos + montaje DMI) | `base.stl` | impresora | PETG (ASA o PA-CF mejor) | 1 |
| Plantilla de imanes | `plantilla_imanes.stl` | impresora | PLA/PETG | útil (1 para todos) |
| Mandril de apilado | `mandril_apilado.stl` | impresora | PETG | útil |
| Soporte de bobinado | `soporte_bobinado.stl` | impresora | PETG | útil |
| Ensamble (para ver) | `ensamble.stl` | — | — | — |

**Los números de cada motor** (láminas, vueltas, alambre, orden de las bobinas, resistencia y Kv esperados) están en
[valores.md](valores.md), generado desde el diseño.

La fuente es OpenSCAD: `cad/openscad/motor/` (`motor_lib.scad` + `<dron>_motor_params.scad`, generados). La lista de
materiales y los costos están en [`motor/bom/Lista_Materiales_Motor.xlsx`](../bom/Lista_Materiales_Motor.xlsx).

## Antes de empezar: supuestos a confirmar

- **Láser de fibra** (≥ 20 W corta 0.2 mm; ≥ 50 W corta el acero de 1 mm del rotor). Un láser de CO₂ no corta acero:
  en ese caso se manda a cortar el DXF (≈ US$0.3-1 por lámina) y lo demás se hace igual.
- **Impresora** que imprima PETG con buena precisión dimensional. Para la base y la tapa, ASA o PA-CF dan más margen
  térmico (M5: la base llega a 40-55 °C; PETG ablanda a ~70 °C, justo para el DS-D: mejor ASA o PA-CF ahí).
- **Calibrar los ajustes** con una pieza de prueba: el eje entra a presión en la tapa (`fit_press`), los rodamientos a
  presión en la base, y la plantilla de imanes deja 0.15 mm de juego. Si la impresora da otras medidas, se corrigen
  `FIT` en `gen_cad.py` y se regenera.

## Pasos (tiempos de un motor DS-I / DS-D)

1. **Cortar las láminas** (20 / 37 min, desatendido). Potencia y velocidad bajas con aire comprimido: el borde debe
   quedar sin rebaba ni color azul. Un borde quemado sube las pérdidas en el hierro (M2 ya supone 0.4 mm de borde dañado).
2. **Desbarbar y limpiar** (15 / 20 min). Lija 600 sobre vidrio y alcohol isopropílico. Las láminas NO20 vienen con
   aislante (C5) en las dos caras: no lijar la cara, solo el borde.
3. **Apilar y pegar** (15 / 20 min + 24 h). En el **mandril de apilado**, con la chaveta alineada. Una capa muy fina de
   epoxi entre láminas; prensar con la varilla M5. Medir el alto (debe dar el de [valores.md](valores.md)).
4. **Aislar** (20 / 30 min). Barniz en los bordes de los dientes y una tira de papel Nomex de 0.08 mm en cada ranura.
   Un solo roce del alambre con el hierro deja el motor en cortocircuito.
5. **Bobinar** (90 / 150 min). Con el **soporte de bobinado** en una morsa. Vueltas, hilos en paralelo y orden de las
   bobinas: [valores.md](valores.md) (mayúscula = un sentido, minúscula = el contrario). Bobinar apretado y ordenado: **el relleno de ranura es
   el riesgo n.º 1 del diseño** (M2: con relleno 0.33 en vez de 0.40 la ganancia sobre el comercial cae a la mitad).
6. **Conectar las fases** (20 / 25 min), en triángulo o estrella según [valores.md](valores.md). Soldar los cables de silicona y aislar con Kapton y
   termocontraíble.
7. **Impregnar** (10 / 15 min + curado). Barniz clase H sobre el bobinado: lo fija (no vibra) y mejora la conducción de calor.
8. **Rotor** (15 / 20 min). Pegar los anillos cortados con láser, alineados por la marca, con epoxi.
9. **Imanes** (30 / 40 min + curado). Meter la **plantilla de imanes** en el anillo y pegar cada imán en su lugar,
   **alternando la polaridad** (verificar cada uno con la brújula antes de soltarlo). Pinza no magnética, gafas y guantes:
   los imanes saltan al anillo y se rompen o pellizcan.
10. **Imprimir tapa y base** (1.5 / 4 h, desatendido). 4 paredes, relleno 40 % gyroid o más.
11. **Ensamblar** (20 / 25 min). Rodamientos a presión en la base; estator pegado sobre el tubo de la base (chaveta en la
    muesca); eje por los rodamientos con los anillos E; rotor + tapa (eje a presión en la tapa, prisionero M3 con fijador).
12. **Balancear y control de calidad** (20 / 25 min). Ver abajo.

Total: **~4.3 / 6.2 h de mano de obra** por motor (los primeros tardan más) y ~1.8 / 4.6 h de máquina.

## Control de calidad de cada motor

| Prueba | Cómo | Debe dar |
|---|---|---|
| Resistencia fase-fase (las 3 combinaciones) | medidor de 4 hilos, a 20 °C | lo de [valores.md](valores.md), las 3 iguales ± 3 % |
| Aislamiento | multímetro en MΩ entre cualquier cable y el estator | > 20 MΩ (circuito abierto) |
| Giro libre | a mano | sin roces ni tirones (el cogging calculado es ~0.1 % del torque de hover) |
| Polaridad de imanes | brújula alrededor del rotor | N-S-N-S… sin dos iguales seguidos |
| Corriente en vacío | ESC a 50 % sin hélice, medir corriente | cerca de lo calculado (se registra en `motor/pruebas/`) |
| Kv | rpm sin carga / voltaje (tacómetro óptico o telemetría del ESC) | lo de [valores.md](valores.md) |
| Balanceo | balanceador magnético con la tapa | sin punto pesado; vibración en el banco dentro del criterio del S11 |

Las pruebas de rendimiento (empuje, g/W, temperatura, 10 h de durabilidad) son M8, en el banco del S10.
