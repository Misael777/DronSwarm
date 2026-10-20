# Fabricación del motor propio (M6)

Cómo hacer el motor elegido en M2 con la cortadora láser, la impresora 3D y herramientas de mano. Todo se regenera desde el
diseño con `bash motor/run_all.sh`.

| Documento | Qué tiene |
|---|---|
| [planos/ds-i_planos.pdf](planos/ds-i_planos.pdf), [planos/ds-d_planos.pdf](planos/ds-d_planos.pdf) | Planos A3: ensamble en corte con lista de piezas, base, tapa, eje, lámina del estator y anillo del rotor, con cotas y tolerancias |
| [tolerancias.md](tolerancias.md) | Tabla de ajustes, cadena del entrehierro, cadena axial de la precarga y orden de armado |
| [valores.md](valores.md) | Vueltas, alambre, orden de las bobinas, resistencia y Kv esperados de cada motor |
| [../bom/Lista_Materiales_Motor.xlsx](../bom/Lista_Materiales_Motor.xlsx) | Lista de compras y costo de fabricación |
| `cad/exports/motor/<dron>/vista_*.png` | Vistas del ensamble, en corte y explosionado |

## Piezas

| Pieza | Archivo (`cad/exports/motor/<dron>/`) | Cómo se hace | Material |
|---|---|---|---|
| Lámina del estator | `lamina_estator.dxf` | láser de fibra | acero al silicio 0.20 mm (NO20) |
| Anillo del rotor (interior de caras planas) | `anillo_rotor.dxf` | láser de fibra | acero DC01 1.0 mm |
| Base (asientos de rodamiento, tubo del estator, montaje DMI) | `base.stl` | impresora, brida sobre la cama | PETG / ASA / PA-CF |
| Tapa (hélice, agujero en D del eje, pollera del anillo) | `tapa.stl` (ya orientada boca abajo) | impresora | PETG / ASA / PA-CF |
| Eje con 2 ranuras de anillo E y un plano | `eje.stl` (solo para ver; plano M-xx-003) | barra rectificada cortada y ranurada | acero plata h6 |
| Probeta de ajustes | `probeta_ajustes.stl` | impresora | el mismo plástico de las piezas |
| Útil de concentricidad (anillo ↔ tapa) | `util_concentricidad.stl` | impresora | PETG |
| Plantilla de imanes, mandril de apilado, soporte de bobinado | `plantilla_imanes.stl`, `mandril_apilado.stl`, `soporte_bobinado.stl` | impresora | PETG |
| Normalizados: 2 rodamientos ZZ, 2 anillos E DIN 6799, 3 arandelas DIN 988, 1 arandela ondulada DIN 137, 8 insertos roscados, 8 tornillos | — | se compran | ver lista de compras |

La fuente es OpenSCAD: `cad/openscad/motor/` (`motor_lib.scad` + `<dron>_motor_params.scad`, generados por
`motor/fabricacion/gen_cad.py`). Para verlo: `openscad cad/openscad/motor/ds_i_ensamble.scad` y F5.

## Antes de empezar: supuestos a confirmar

- **Láser de fibra** (≥ 20 W corta 0.2 mm; ≥ 50 W corta el acero de 1 mm del rotor). Un láser de CO₂ no corta acero:
  en ese caso se manda a cortar el DXF (≈ US$0.3-1 por lámina) y lo demás se hace igual.
- **Impresora** que imprima PETG con buena precisión dimensional. Para la base y la tapa del DS-D, mejor ASA o PA-CF
  (M5: la base llega a 54 °C; el PETG ablanda a ~70 °C).
- **Sin torno** se puede: las ranuras del eje se hacen girando el eje en el taladro de banco con un disco de corte fino.

## Pasos (tiempos de un motor DS-I / DS-D)

0. **Calibrar la impresora** (una vez). Imprimir `probeta_ajustes.stl` y probar el rodamiento y el eje en cada agujero.
   El agujero marcado **0** debe sostener el rodamiento a presión firme y dejar pasar el eje justo. Si no, corregir
   `HOLE_COMP` en `gen_cad.py` y regenerar. Con eso los asientos, el agujero del eje y los insertos salen a medida.
1. **Cortar las láminas y los anillos** (20 / 37 min, desatendido). Con la compensación de corte configurada en el láser.
   El borde no debe quedar con rebaba ni color azul. Medir con calibre el agujero y el exterior de las primeras piezas
   (planos M-xx-004 y M-xx-005).
2. **Desbarbar y limpiar** (15 / 20 min). Lija 600 sobre vidrio y alcohol isopropílico. Las láminas NO20 vienen
   aisladas en las dos caras: solo se lija el borde.
3. **Apilar el estator** (15 / 20 min + 24 h). En el **mandril de apilado**, con la muesca en la chaveta, una capa muy
   fina de epoxi entre láminas, prensado con la varilla M5. Altura del paquete ±0.1 mm.
4. **Aislar** (20 / 30 min). Barniz en los bordes de los dientes y papel Nomex de 0.08 mm en cada ranura.
5. **Bobinar** (90 / 150 min). Con el **soporte de bobinado** en la morsa. Vueltas, hilos y orden de las bobinas en
   [valores.md](valores.md). Apretado y ordenado: **el relleno de ranura es el riesgo n.º 1 del diseño**.
6. **Conectar las fases** (20 / 25 min) en estrella o triángulo según [valores.md](valores.md). Soldar los cables de
   silicona, aislar con Kapton y termocontraíble y sacarlos por el canal de la base.
7. **Impregnar** (10 / 15 min + curado) con barniz clase H.
8. **Eje** (20 / 25 min). Cortar a medida, chaflanar, hacer las 2 ranuras de anillo E y el plano (plano M-xx-003).
   Verificar que el anillo E calce sin juego.
9. **Imprimir** la base, la tapa y los útiles (1.5 / 4 h, desatendido). Colocar los **insertos roscados** con el soldador
   (4 abajo en la base y 4 arriba en la tapa), perpendiculares. **Escariar** el agujero en D de la tapa a la medida del eje.
10. **Rotor** (45 / 60 min + curado). Pegar los anillos alineados por las muescas. Pegar los imanes en las caras planas
    con la **plantilla de imanes**, alternando N y S (verificar cada uno con la brújula antes de soltarlo). Pegar el
    anillo en la tapa con el **útil de concentricidad**: el perno entra en el agujero de la tapa y la copa centra el anillo.
11. **Ensamblar** (25 / 30 min), en el orden de [tolerancias.md](tolerancias.md):
    1. los rodamientos a presión en la base (morsa, no a golpes), cada uno contra su hombro;
    2. el estator pegado sobre el tubo, con la chaveta y 3 tiras de 0.05 mm para centrarlo (se retiran);
    3. el eje en la tapa con adhesivo retenedor, más la arandela y el anillo E superiores en el rebaje;
    4. la arandela de ajuste y la ondulada sobre el rodamiento superior, y el rotor por los rodamientos;
    5. desde abajo, la arandela de ajuste y el anillo E inferior.
12. **Control de calidad** (20 / 25 min). Ver abajo.

Total: **~4.5 / 6.5 h de mano de obra** por motor (los primeros tardan más) y ~1.8 / 4.6 h de máquina.

## Control de calidad de cada motor

| Prueba | Cómo | Debe dar |
|---|---|---|
| Entrehierro | galga en 4 posiciones, girando a mano | pasa la galga de la mitad del entrehierro ([tolerancias.md](tolerancias.md)) |
| Juego axial y precarga | empujar y tirar del rotor | sin juego perceptible y giro libre; si no, cambiar la arandela de ajuste de 0.1 mm |
| Resistencia fase-fase (las 3 combinaciones) | medidor de 4 hilos, a 20 °C | lo de [valores.md](valores.md), las 3 iguales ± 3 % |
| Aislamiento | multímetro en MΩ entre cualquier cable y el estator | > 20 MΩ (circuito abierto) |
| Giro libre | a mano | sin roces ni tirones (el cogging calculado es ~0.1 % del torque de hover) |
| Polaridad de los imanes | brújula alrededor del rotor | N-S-N-S… sin dos iguales seguidos |
| Kv | rpm sin carga / voltaje (tacómetro óptico o telemetría del ESC) | lo de [valores.md](valores.md) |
| Balanceo | balanceador magnético con la tapa | sin punto pesado; vibración en el banco dentro del criterio del S11 |

Las pruebas de rendimiento (empuje, g/W, temperatura, 10 h de durabilidad) son M8, en el banco del S10.
