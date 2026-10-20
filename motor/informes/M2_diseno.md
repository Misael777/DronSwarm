# M2 · Diseño del motor propio (cálculo analítico y optimización)

> Generado por `motor/calculo/optimize.py` + `report_m2.py`. No editar a mano.

## Resumen

| | Comercial | Propio elegido | Diferencia |
|---|---|---|---|
| **DS-I** | T-Motor MN4006 KV380 | 24N22P, estator Ø43.1×6.0 mm | |
| Eficiencia ponderada (mismo modelo) | 85.2% | 89.3% | **+4.1 puntos** |
| Masa (mismo modelo) | 73 g | 80 g | +7 g |
| Autonomía del dron | — | — | **+3.1 %** |
| Costo | US$75 (compra) | US$12 (materiales) | 16% del comercial |
| **DS-D** | MAD M6C12 EEE KV150 | 36N32P, estator Ø70.8×7.7 mm | |
| Eficiencia ponderada (mismo modelo) | 88.6% | 90.6% | **+2.0 puntos** |
| Masa (mismo modelo) | 291 g | 237 g | -54 g |
| Autonomía del dron | — | — | **+5.7 %** |
| Costo | US$170 (compra) | US$32 (materiales) | 19% del comercial |

**Comparación justa:** el comercial se reconstruye desde su ficha y se evalúa con el mismo modelo que el diseño propio (eficiencia y masa, modelo contra modelo). La ganancia viene de **más cobre por la misma masa** (estator más ancho y corto, bobinado concentrado de alto factor) y de láminas de 0.2 mm a menor inducción.

![compromiso](M2_compromiso.png)

![pérdidas en hover](M2_perdidas_hover.png)

## 1. Validación del modelo

El modelo (`design.py`) reconstruye a los comerciales desde su nombre y su ficha (tamaño del estator, ranuras/polos, diámetro exterior) con vueltas y ranuras plausibles:

| Motor | Geometría supuesta | Kv modelo / ficha | R modelo / ficha | Ø exterior | Masa modelo / real |
|---|---|---|---|---|---|
| MN4006 KV380 | 18N24P, estator Ø40×6 mm, 10 vueltas en estrella | 380 / 380 | 197 / 194 mΩ | 45.5 / 44.35 mm | 73 / 68 g |
| M6C12 KV150 | 24N28P, estator Ø62×12 mm, 5 vueltas en estrella | 156 / 150 | 97 / 90 mΩ | 71.1 / 72 mm | 291 / 257 g |

- **Contra la tabla de banco del MN4006:** error de corriente 1.9 % RMS en las 7 filas (ESC supuesto 95%); corriente en vacío 0.4 A contra 0.3 A de la ficha (el modelo es algo pesimista en hierro).
- **Térmico:** carcasa a fondo 46.0 °C contra 46.0 °C del fabricante (bobinado estimado 77.5 °C).
- Constantes calibradas: hierro ×0.6 sobre catálogo + borde láser, cobre ×1.03 por la conmutación de 6 pasos, conductancia térmica ×29.3 sobre la superficie externa.
- La masa del modelo es 7-13 % alta para los comerciales (campanas de aluminio fino). Por eso la masa se compara modelo contra modelo.

## 2. DS-I

22,882 diseños válidos (de un muestreo aleatorio + 3 rondas de refinamiento). Metas del G5 en términos del modelo: eficiencia ≥ 87.2% (comercial + 2 puntos), masa ≤ 80 g, materiales ≤ US$22.

| | A · máxima autonomía | B · máxima eficiencia con la masa meta | C · el más liviano que cumple |
|---|---|---|---|
| Ranuras / polos | 24N22P (factor 0.949) | 24N22P (factor 0.949) | 24N26P (factor 0.949) |
| Estator | Ø41.6 × 5.7 mm, NO20 | Ø43.1 × 6.0 mm, NO20 | Ø42.7 × 5.2 mm, NO20 |
| Diente / yugo / ranura | 2.69 / 1.41 / 6.6 mm | 2.82 / 1.47 / 6.7 mm | 2.67 / 1.52 / 6.6 mm |
| Bobinado | 15 vueltas/diente, triángulo, 2 × Ø0.3 mm en paralelo | 14 vueltas/diente, triángulo, 2 × Ø0.3 mm en paralelo | 17 vueltas/diente, triángulo, 2 × Ø0.3 mm en paralelo |
| Imanes | 22 imanes N52H de 5.2 × 5.7 × 1.0 mm (ancho × largo × espesor, magnetizados en el espesor) | 22 imanes N52H de 5.4 × 6.0 × 1.0 mm (ancho × largo × espesor, magnetizados en el espesor) | 26 imanes N48SH de 4.5 × 5.2 × 1.0 mm (ancho × largo × espesor, magnetizados en el espesor) |
| Rotor | anillo de acero 1.4 mm, Ø exterior 47.4 mm, alto 16 mm | anillo de acero 1.5 mm, Ø exterior 49.1 mm, alto 16 mm | anillo de acero 1.2 mm, Ø exterior 48.0 mm, alto 15 mm |
| Kv / R (20 °C) | 354 rpm/V / 177 mΩ | 347 rpm/V / 153 mΩ | 349 rpm/V / 195 mΩ |
| Eficiencia hover 4,500 m | 88.2% | 89.3% | 87.2% |
| Eficiencia ponderada | **88.2%** (+3.0) | **89.3%** (+4.1) | **87.2%** (+2.0) |
| Masa | 73 g | 80 g | 69 g |
| Autonomía del dron | **+3.5 %** | **+3.1 %** | **+3.5 %** |
| Materiales | US$11.5 | US$11.7 | US$12.1 |
| Bobinado en maniobra / máximo | 31 / 39 °C | 29 / 34 °C | 33 / 41 °C |
| Corriente máx. / densidad | 11.3 A / 44.2 A/mm² | 11.0 A / 38.3 A/mm² | 11.2 A / 44.9 A/mm² |
| Desmagnetización (< 0.7) | 0.53 | 0.52 | 0.41 |
| Frecuencia eléctrica máx. | 1051 Hz | 1051 Hz | 1242 Hz |

**Elegido: B · máxima eficiencia con la masa meta.**

**Robustez** (puntos de eficiencia que gana sobre el comercial si el modelo se equivoca; el mismo cambio se aplica al comercial cuando corresponde):

| Caso | A | B | C |
|---|---|---|---|
| modelo base | +3.0 | +4.1 | +2.0 |
| hierro pierde lo de catálogo (K_IRON 1.0) | +3.4 | +4.3 | +2.2 |
| entrehierro +0.2 mm (campana con juego) | +2.7 | +4.0 | +1.7 |
| bobinado peor: relleno 0.33 | +1.4 | +2.7 | +0.3 |
| imanes N42SH (más baratos) | +2.9 | +4.1 | +1.9 |
| enfriamiento a la mitad (K_THERMAL/2) | +3.1 (maniobra a 39 °C) | +4.3 (maniobra a 35 °C) | +2.2 (maniobra a 41 °C) |

**Mejor diseño por combinación** (autonomía del dron):

| Ranuras/polos | Autonomía | Eficiencia | Masa | Estator |
|---|---|---|---|---|
| 24N22P | +3.5 % | 88.2% | 73 g | Ø42×5.7 mm |
| 24N26P | +3.5 % | 87.6% | 71 g | Ø43×5.2 mm |
| 24N28P | +2.3 % | 86.8% | 71 g | Ø41×6.3 mm |
| 18N20P | +1.8 % | 86.6% | 72 g | Ø40×5.8 mm |
| 18N16P | +1.2 % | 87.2% | 77 g | Ø42×5.5 mm |
| 18N24P | -2.0 % | 82.5% | 68 g | Ø40×5.5 mm |

**Por acero** (el mejor diseño con cada uno): NO20: +3.5 % de autonomía, 88.2%; M270-35A: +1.9 % de autonomía, 86.7%; NO27: +3.0 % de autonomía, 87.3%.

**Costo de materiales del elegido:** acero eléctrico US$0.64, acero del rotor US$0.04, imanes US$3.30, cobre US$0.23, filamento US$1.01, eje US$1.00, rodamientos US$3.00, varios US$2.50 → **US$11.72**.

**Masa del elegido:** estator (dientes) 23.0 g, estator (yugo) 5.3 g, cobre 9.9 g, imanes 5.5 g, yugo del rotor 13.9 g, tapa impresa 3.9 g, base impresa 8.1 g, eje 2.8 g, rodamientos 3.4 g, tornillos, cables, adhesivo 4.0 g.

## 3. DS-D

22,088 diseños válidos (de un muestreo aleatorio + 3 rondas de refinamiento). Metas del G5 en términos del modelo: eficiencia ≥ 90.6% (comercial + 2 puntos), masa ≤ 320 g, materiales ≤ US$51.

| | A · máxima autonomía | B · máxima eficiencia con la masa meta | C · el más liviano que cumple |
|---|---|---|---|
| Ranuras / polos | 36N32P (factor 0.945) | 36N32P (factor 0.945) | 36N32P (factor 0.945) |
| Estator | Ø71.4 × 7.2 mm, NO20 | Ø72.0 × 10.6 mm, NO20 | Ø70.8 × 7.7 mm, NO20 |
| Diente / yugo / ranura | 3.22 / 2.17 / 10.2 mm | 3.28 / 2.02 / 10.4 mm | 3.20 / 2.17 / 10.2 mm |
| Bobinado | 8 vueltas/diente, estrella, 4 × Ø0.4 mm en paralelo | 9 vueltas/diente, triángulo, 6 × Ø0.3 mm en paralelo | 13 vueltas/diente, triángulo, 4 × Ø0.3 mm en paralelo |
| Imanes | 32 imanes N48SH de 6.1 × 7.2 × 1.5 mm (ancho × largo × espesor, magnetizados en el espesor) | 32 imanes N48SH de 6.1 × 10.6 × 1.5 mm (ancho × largo × espesor, magnetizados en el espesor) | 32 imanes N48SH de 6.0 × 7.7 × 1.5 mm (ancho × largo × espesor, magnetizados en el espesor) |
| Rotor | anillo de acero 1.8 mm, Ø exterior 79.1 mm, alto 18 mm | anillo de acero 1.8 mm, Ø exterior 79.7 mm, alto 22 mm | anillo de acero 1.7 mm, Ø exterior 78.5 mm, alto 19 mm |
| Kv / R (20 °C) | 114 rpm/V / 152 mΩ | 118 rpm/V / 83 mΩ | 115 rpm/V / 141 mΩ |
| Eficiencia hover 4,500 m | 90.2% | 92.4% | 90.5% |
| Eficiencia ponderada | **90.2%** (+1.7) | **92.4%** (+3.9) | **90.6%** (+2.0) |
| Masa | 230 g | 309 g | 237 g |
| Autonomía del dron | **+5.8 %** | **+3.2 %** | **+5.7 %** |
| Materiales | US$31.7 | US$33.5 | US$31.9 |
| Bobinado en maniobra / máximo | 36 / 47 °C | 28 / 33 °C | 35 / 45 °C |
| Corriente máx. / densidad | 24.3 A / 48.2 A/mm² | 24.9 A / 31.8 A/mm² | 24.5 A / 46.2 A/mm² |
| Desmagnetización (< 0.7) | 0.38 | 0.35 | 0.38 |
| Frecuencia eléctrica máx. | 1034 Hz | 1034 Hz | 1034 Hz |

**Elegido: C · el más liviano que cumple.**

**Robustez** (puntos de eficiencia que gana sobre el comercial si el modelo se equivoca; el mismo cambio se aplica al comercial cuando corresponde):

| Caso | A | B | C |
|---|---|---|---|
| modelo base | +1.7 | +3.9 | +2.0 |
| hierro pierde lo de catálogo (K_IRON 1.0) | +1.8 | +3.4 | +2.1 |
| entrehierro +0.2 mm (campana con juego) | +1.6 | +3.9 | +1.9 |
| bobinado peor: relleno 0.33 | +0.2 | +3.0 | +0.6 |
| imanes N42SH (más baratos) | +1.6 | +3.9 | +2.0 |
| enfriamiento a la mitad (K_THERMAL/2) | +1.8 (maniobra a 47 °C) | +4.1 (maniobra a 35 °C) | +2.2 (maniobra a 46 °C) |

**Mejor diseño por combinación** (autonomía del dron):

| Ranuras/polos | Autonomía | Eficiencia | Masa | Estator |
|---|---|---|---|---|
| 36N32P | +5.8 % | 90.2% | 230 g | Ø71×7.2 mm |
| 36N40P | +5.4 % | 89.3% | 218 g | Ø72×7.1 mm |
| 36N42P | +5.0 % | 89.3% | 225 g | Ø72×7.5 mm |
| 24N28P | +3.7 % | 90.5% | 267 g | Ø69×8.9 mm |
| 24N22P | +3.4 % | 90.7% | 275 g | Ø70×8.4 mm |
| 24N26P | +3.1 % | 90.8% | 281 g | Ø67×10.7 mm |

**Por acero** (el mejor diseño con cada uno): NO20: +5.8 % de autonomía, 90.2%; NO27: +4.7 % de autonomía, 89.9%; M270-35A: +4.4 % de autonomía, 88.7%.

**Costo de materiales del elegido:** acero eléctrico US$2.03, acero del rotor US$0.10, imanes US$14.40, cobre US$0.72, filamento US$3.61, eje US$2.00, rodamientos US$5.00, varios US$4.00 → **US$31.85**.

**Masa del elegido:** estator (dientes) 72.4 g, estator (yugo) 17.7 g, cobre 30.8 g, imanes 16.9 g, yugo del rotor 31.9 g, tapa impresa 13.4 g, base impresa 29.6 g, eje 7.0 g, rodamientos 7.0 g, tornillos, cables, adhesivo 10.0 g.

## 4. Qué se aprende y qué sigue

- **Más ranuras y polos ganan** en los dos drones (24N22P en el DS-I, 36N32P en el DS-D): bobinas cortas, factor de bobinado alto (0.95) y yugos delgados, con frecuencias eléctricas todavía bajas (< 1.2 kHz) para láminas de 0.2 mm.
- **Estatores anchos y cortos** (tipo "pancake"): el diámetro está en el límite del montaje. Si el brazo admite un motor unos milímetros más ancho, se gana más (a revisar con el CAD del frame en M6).
- **El acero de 0.2 mm (NO20) es el mejor**; el de 0.35 mm, más barato y fácil de conseguir, pierde ~1.5 puntos.
- **El riesgo es el bobinado:** con relleno 0.33 en vez de 0.40, la ganancia cae fuerte. El útil de bobinado (M6) y el hilo en paralelo de 0.4-0.5 mm son parte del diseño, no un detalle.
- **Los imanes quedaron en el espesor mínimo** del rango (1.0 mm en el DS-I, 1.5 mm en el DS-D): son frágiles y se pegan con la plantilla. El FEM (M4) verifica la desmagnetización en caliente.
- **Densidad de corriente a fondo de 35-45 A/mm²:** alta para un motor industrial, normal en drones (el comercial reconstruido llega a ~53 A/mm²) porque el motor está en el chorro de la hélice. Es corta (< 30 s) y la temperatura queda lejos del límite aun con la mitad del enfriamiento calibrado (tabla de robustez). M5 lo confirma.
- **Siguiente:** M3 (¿un reductor mejora esto?) y M4 (FEM 2D de los elegidos: flujo, cogging, contra-FEM y torque).

## Limitaciones

- Modelo analítico calibrado con **un** motor (MN4006, tabla del fabricante). El M6C12 solo con ficha. El FEM (M4) y el banco (M8) son la verificación.
- Térmico de régimen permanente simple; la red térmica es M5.
- Costos de materiales con precios de catálogo; las cotizaciones son S17-05.
