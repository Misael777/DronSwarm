# Ajustes y tolerancias del motor

> Generado por `motor/fabricacion/gen_tolerancias.py` con las medidas del CAD (`gen_cad.py`). No editar a mano.

Generales: piezas cortadas con láser **ISO 2768-m**; piezas impresas **±0.2 mm** salvo indicación; aristas de piezas impresas con **chaflán 0.5 × 45°**; entradas de asientos de rodamiento con **chaflán 0.4 × 45°**; extremos del eje **0.3 × 45°**; esquinas del fondo de ranura de las láminas **R 0.3** (no concentra tensiones ni rompe el esmalte).

**Impresión:** los agujeros se modelan con el nominal + `hole_comp` = 0.15 mm (las impresoras FDM los hacen más chicos). Antes de imprimir piezas, imprimir `probeta_ajustes.stl`, probar el rodamiento y el eje en cada agujero y corregir `HOLE_COMP` en `gen_cad.py` hasta que el agujero marcado **0** dé el ajuste de la tabla.

**Láser:** los DXF están a la medida nominal. Configurar la compensación de corte (kerf) del láser (≈ 0.02-0.05 mm con fibra) para que la pieza, no el corte, quede a medida. Verificar con calibre el agujero de la lámina y el exterior del anillo en las primeras piezas.

## DS-I

| Interfaz | Medida nominal | Pieza | Contraparte | Ajuste resultante | Cómo se logra / controla |
|---|---|---|---|---|---|
| Aro exterior del rodamiento 694ZZ en la base | Ø11 | rodamiento Ø11 0/−0.008 (ISO 492) | asiento Ø10.95 +0.05/0 | apriete 0.04-0.06 (plástico: tipo N7) | probeta de ajustes; entra con morsa y cubos de madera, no a golpes; no debe girar a mano |
| Eje en el aro interior | Ø4 | eje h6 (0/−0.008) | rodamiento Ø4 0/−0.008 | de transición | fijador de rodamientos (Loctite 641) |
| Hombros de los rodamientos | Ø9.6 (máx.) | asiento: hombro Ø9.4 | apoya solo en el aro exterior | — | no tocar las tapas ZZ (ISO: D_a máx.) |
| Eje en la tapa (agujero en D) | Ø4 con plano a 1.70 del centro | eje h6 | tapa: imprimir Ø3.85 y **escariar a Ø4 H7** | deslizante justo | adhesivo retenedor (Loctite 638); el plano bloquea el giro |
| Ranuras de anillo E (DIN 6799) | Ø3.2 × 0.64 | ranura Ø h11, ancho H13 | anillo DIN 6799-3.2 | — | torneado o lima en torno manual; borde a ≥ 1.0 mm del extremo |
| Estator sobre el tubo de la base | Ø28.07 | lámina (láser) ±0.03 | tubo Ø27.97 ±0.05 (impreso) | juego 0.05-0.18 | epoxi; centrar con la chaveta y 3 tiras de 0.05 mm a 120° (se retiran) |
| Chaveta en la muesca de las láminas | 2.0 | muesca 2.0 ±0.03 | chaveta 1.9 ±0.05 | juego 0.05-0.18 | solo orientación y antigiro; el epoxi transmite el torque de reacción |
| Anillo del rotor en la pollera de la tapa | Ø49.82 | anillo (láser) ±0.03 | pollera Ø50.02 ±0.05 | juego 0.12-0.28 | epoxi con el **útil de concentricidad** (perno en el agujero de la tapa, copa en el anillo) |
| Imanes en las caras planas del anillo | 1.0 de espesor | imán ±0.05 | cara plana a 23.51 del centro | 0.05 para el epoxi | plantilla de imanes; epoxi de alta temperatura |
| Insertos roscados (hélice y DMI) | M3 | inserto | agujero Ø4.0 × 4.2 | según fabricante | colocar con soldador a 220-240 °C (PETG) y punta de insertos, perpendicular |

**Cadena radial del entrehierro** (nominal 0.50 mm, mínimo admisible 50 % = 0.25 mm):

| Contribución | Excentricidad [mm] |
|---|---|
| Juego radial interno de los rodamientos (C0, ×2 rodamientos) | 0.008 |
| Concentricidad de los 2 asientos de rodamiento (misma impresión, misma pieza) | 0.030 |
| Tubo de la base respecto de los asientos (misma impresión) | 0.030 |
| Estator sobre el tubo: mitad del juego para el epoxi (centrado con la chaveta y 3 tiras de 0.05 mm) | 0.050 |
| Contorno exterior de las láminas (láser de fibra) | 0.030 |
| Eje en el agujero de la tapa (escariado H7, adhesivo) | 0.010 |
| Anillo del rotor respecto del agujero de la tapa (útil de concentricidad al pegar) | 0.030 |
| Caras planas del anillo respecto de su exterior (láser) | 0.020 |
| Espesor de los imanes (tolerancia de catálogo ±0.05 → radial) | 0.050 |
| **Peor caso (suma)** | **0.26** → entrehierro mínimo 0.24 mm (apenas bajo el 50 %: requiere todas las tolerancias al máximo y en la misma dirección; la galga del armado lo detecta) |
| **Estadística (raíz de la suma de cuadrados)** | **0.10** → entrehierro mínimo 0.40 mm |

Atracción magnética desbalanceada con la excentricidad estadística: M5 la calcula con 0.10 mm (conservador). Control: girar a mano y pasar una galga de 0.25 mm por el entrehierro en 4 posiciones antes de cerrar la tapa.

**Cadena axial de la precarga** (arandela ondulada DIN 137 B4 (ondulada): libre 1.0 mm, trabajo 0.6 mm → recorrido útil ±0.20 mm):

| Contribución | ± [mm] |
|---|---|
| Alto del tubo entre hombros de rodamiento (impresión ±0.10) | 0.100 |
| Ancho de los 2 rodamientos (ISO 492: 0/−0.12 c/u → ±0.06 c/u) | 0.085 |
| Espigón de la tapa hasta la ranura superior (impresión ±0.10) | 0.100 |
| Posición de las 2 ranuras del eje (torneado ±0.05 c/u) | 0.071 |
| Arandelas de ajuste DIN 988 (±0.02 × 3) | 0.035 |
| **Estadística** | **±0.18** ≤ ±0.20 |

La arandela ondulada absorbe la variación esperada. Ajuste en el armado: con el anillo E superior colocado, el eje no debe tener juego axial perceptible y el rotor tiene que girar libre. Si hay juego, agregar una arandela DIN 988 de 0.1 mm bajo el espigón; si frena, quitarla.

## DS-D

| Interfaz | Medida nominal | Pieza | Contraparte | Ajuste resultante | Cómo se logra / controla |
|---|---|---|---|---|---|
| Aro exterior del rodamiento 696ZZ en la base | Ø15 | rodamiento Ø15 0/−0.008 (ISO 492) | asiento Ø14.95 +0.05/0 | apriete 0.04-0.06 (plástico: tipo N7) | probeta de ajustes; entra con morsa y cubos de madera, no a golpes; no debe girar a mano |
| Eje en el aro interior | Ø6 | eje h6 (0/−0.008) | rodamiento Ø6 0/−0.008 | de transición | fijador de rodamientos (Loctite 641) |
| Hombros de los rodamientos | Ø13.4 (máx.) | asiento: hombro Ø13.2 | apoya solo en el aro exterior | — | no tocar las tapas ZZ (ISO: D_a máx.) |
| Eje en la tapa (agujero en D) | Ø6 con plano a 2.50 del centro | eje h6 | tapa: imprimir Ø5.85 y **escariar a Ø6 H7** | deslizante justo | adhesivo retenedor (Loctite 638); el plano bloquea el giro |
| Ranuras de anillo E (DIN 6799) | Ø5.0 × 0.74 | ranura Ø h11, ancho H13 | anillo DIN 6799-5 | — | torneado o lima en torno manual; borde a ≥ 1.2 mm del extremo |
| Estator sobre el tubo de la base | Ø46.94 | lámina (láser) ±0.03 | tubo Ø46.84 ±0.05 (impreso) | juego 0.05-0.18 | epoxi; centrar con la chaveta y 3 tiras de 0.05 mm a 120° (se retiran) |
| Chaveta en la muesca de las láminas | 2.0 | muesca 2.0 ±0.03 | chaveta 1.9 ±0.05 | juego 0.05-0.18 | solo orientación y antigiro; el epoxi transmite el torque de reacción |
| Anillo del rotor en la pollera de la tapa | Ø77.93 | anillo (láser) ±0.03 | pollera Ø78.13 ±0.05 | juego 0.12-0.28 | epoxi con el **útil de concentricidad** (perno en el agujero de la tapa, copa en el anillo) |
| Imanes en las caras planas del anillo | 1.5 de espesor | imán ±0.05 | cara plana a 37.04 del centro | 0.05 para el epoxi | plantilla de imanes; epoxi de alta temperatura |
| Insertos roscados (hélice y DMI) | M4 | inserto | agujero Ø5.6 × 5.0 | según fabricante | colocar con soldador a 220-240 °C (PETG) y punta de insertos, perpendicular |

**Cadena radial del entrehierro** (nominal 0.60 mm, mínimo admisible 50 % = 0.30 mm):

| Contribución | Excentricidad [mm] |
|---|---|
| Juego radial interno de los rodamientos (C0, ×2 rodamientos) | 0.008 |
| Concentricidad de los 2 asientos de rodamiento (misma impresión, misma pieza) | 0.030 |
| Tubo de la base respecto de los asientos (misma impresión) | 0.030 |
| Estator sobre el tubo: mitad del juego para el epoxi (centrado con la chaveta y 3 tiras de 0.05 mm) | 0.050 |
| Contorno exterior de las láminas (láser de fibra) | 0.030 |
| Eje en el agujero de la tapa (escariado H7, adhesivo) | 0.010 |
| Anillo del rotor respecto del agujero de la tapa (útil de concentricidad al pegar) | 0.030 |
| Caras planas del anillo respecto de su exterior (láser) | 0.020 |
| Espesor de los imanes (tolerancia de catálogo ±0.05 → radial) | 0.050 |
| **Peor caso (suma)** | **0.26** → entrehierro mínimo 0.34 mm (cumple) |
| **Estadística (raíz de la suma de cuadrados)** | **0.10** → entrehierro mínimo 0.50 mm |

Atracción magnética desbalanceada con la excentricidad estadística: M5 la calcula con 0.10 mm (conservador). Control: girar a mano y pasar una galga de 0.30 mm por el entrehierro en 4 posiciones antes de cerrar la tapa.

**Cadena axial de la precarga** (arandela ondulada DIN 137 B6 (ondulada): libre 1.3 mm, trabajo 0.8 mm → recorrido útil ±0.25 mm):

| Contribución | ± [mm] |
|---|---|
| Alto del tubo entre hombros de rodamiento (impresión ±0.10) | 0.100 |
| Ancho de los 2 rodamientos (ISO 492: 0/−0.12 c/u → ±0.06 c/u) | 0.085 |
| Espigón de la tapa hasta la ranura superior (impresión ±0.10) | 0.100 |
| Posición de las 2 ranuras del eje (torneado ±0.05 c/u) | 0.071 |
| Arandelas de ajuste DIN 988 (±0.02 × 3) | 0.035 |
| **Estadística** | **±0.18** ≤ ±0.25 |

La arandela ondulada absorbe la variación esperada. Ajuste en el armado: con el anillo E superior colocado, el eje no debe tener juego axial perceptible y el rotor tiene que girar libre. Si hay juego, agregar una arandela DIN 988 de 0.1 mm bajo el espigón; si frena, quitarla.

## Orden de armado (por qué cada pieza está donde está)

1. **Rodamientos en la base** (desde abajo el inferior, desde arriba el superior) contra sus hombros: el empuje de la hélice tira del rotor hacia arriba y lo resiste el rodamiento inferior contra su hombro.
2. **Estator pegado sobre el tubo**, con la chaveta en la muesca y las 3 tiras de centrado.
3. **Rotor**: anillo + imanes pegados; anillo pegado en la tapa con el útil de concentricidad.
4. **Eje en la tapa** (adhesivo retenedor), arandela + anillo E superiores en el rebaje de la tapa.
5. **Arandela de ajuste + arandela ondulada** sobre el rodamiento superior; bajar el rotor con el eje por los rodamientos.
6. **Arandela de ajuste + anillo E inferior** desde abajo: quedan los aros interiores apretados entre el anillo E inferior y el espigón de la tapa (disposición en X, precarga por la arandela ondulada).
7. Verificar: giro libre, sin juego axial, galga en el entrehierro, resistencia y aislamiento (valores.md).
