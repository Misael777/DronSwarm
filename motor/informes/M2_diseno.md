# M2 · Diseño del motor propio (cálculo analítico y optimización)

> Generado por `motor/calculo/optimize.py` + `report_m2.py`. No editar a mano.

## Resumen

| | Comercial | Propio elegido | Diferencia |
|---|---|---|---|
| **DS-I** | T-Motor MN4006 KV380 | 24N26P, estator Ø43.9×6.2 mm | |
| Eficiencia ponderada (mismo modelo) | 85.9% | 88.9% | **+3.0 puntos** |
| Masa (mismo modelo) | 72 g | 80 g | +7 g |
| Autonomía del dron | — | — | **+1.7 %** |
| Costo | US$75 (compra) | US$12 (materiales) | 17% del comercial |
| **DS-D** | MAD M6C12 EEE KV150 | 36N32P, estator Ø69.7×8.4 mm | |
| Eficiencia ponderada (mismo modelo) | 88.5% | 90.6% | **+2.1 puntos** |
| Masa (mismo modelo) | 288 g | 241 g | -47 g |
| Autonomía del dron | — | — | **+5.3 %** |
| Costo | US$170 (compra) | US$32 (materiales) | 19% del comercial |

**Comparación justa:** el comercial se reconstruye desde su ficha y se evalúa con el mismo modelo que el diseño propio (eficiencia y masa, modelo contra modelo). La ganancia viene de **más cobre por la misma masa** (estator más ancho y corto, bobinado concentrado de alto factor) y de láminas de 0.2 mm a menor inducción.

![compromiso](M2_compromiso.png)

![pérdidas en hover](M2_perdidas_hover.png)

## 1. Validación del modelo

El modelo (`design.py`) reconstruye a los comerciales desde su nombre y su ficha (tamaño del estator, ranuras/polos, diámetro exterior) con vueltas y ranuras plausibles:

| Motor | Geometría supuesta | Kv modelo / ficha | R modelo / ficha | Ø exterior | Masa modelo / real |
|---|---|---|---|---|---|
| MN4006 KV380 | 18N24P, estator Ø40×6 mm, 10 vueltas en estrella | 375 / 380 | 189 / 194 mΩ | 45.4 / 44.35 mm | 72 / 68 g |
| M6C12 KV150 | 24N28P, estator Ø62×12 mm, 5 vueltas en estrella | 152 / 150 | 101 / 90 mΩ | 70.8 / 72 mm | 288 / 257 g |

- **Contra la tabla de banco del MN4006:** error de corriente 2.3 % RMS en las 7 filas (ESC supuesto 95%); corriente en vacío 0.392 A contra 0.3 A de la ficha (el modelo es algo pesimista en hierro).
- **Térmico:** carcasa a fondo 46.4 °C contra 46.0 °C del fabricante (bobinado estimado 77.1 °C).
- Constantes calibradas: hierro ×0.6 sobre catálogo + borde láser, cobre ×1.03 por la conmutación de 6 pasos, conductancia térmica ×26.9 sobre la superficie externa.
- La masa del modelo es 7-13 % alta para los comerciales (campanas de aluminio fino). Por eso la masa se compara modelo contra modelo.

## 2. DS-I

20,478 diseños válidos (de un muestreo aleatorio + 3 rondas de refinamiento). Metas del G5 en términos del modelo: eficiencia ≥ 87.9% (comercial + 2 puntos), masa ≤ 80 g, materiales ≤ US$22.

| | A · máxima autonomía | B · máxima eficiencia con la masa meta | C · el más liviano que cumple |
|---|---|---|---|
| Ranuras / polos | 24N26P (factor 0.949) | 24N26P (factor 0.949) | 24N26P (factor 0.949) |
| Estator | Ø43.3 × 4.8 mm, NO20 | Ø43.9 × 6.2 mm, NO20 | Ø42.9 × 5.5 mm, NO20 |
| Diente / yugo / ranura | 2.83 / 1.41 / 7.4 mm | 2.87 / 1.30 / 5.8 mm | 2.80 / 1.24 / 6.9 mm |
| Bobinado | 17 vueltas/diente, triángulo, 3 × Ø0.25 mm en paralelo (cobre +2 % del diseño) | 8 vueltas/diente, estrella, 1 × Ø0.60 mm (cobre +2 % del diseño) | 15 vueltas/diente, triángulo, 1 × Ø0.45 mm (cobre +2 % del diseño) |
| Imanes | 26 imanes N48SH de 4.6 × 4.8 × 1.0 mm (ancho × largo × espesor, magnetizados en el espesor) | 26 imanes N48SH de 4.6 × 6.2 × 1.0 mm (ancho × largo × espesor, magnetizados en el espesor) | 26 imanes N48SH de 4.5 × 5.5 × 1.0 mm (ancho × largo × espesor, magnetizados en el espesor) |
| Rotor | anillo de acero 1.3 mm, Ø exterior 48.8 mm, alto 15 mm | anillo de acero 1.3 mm, Ø exterior 49.5 mm, alto 16 mm | anillo de acero 1.3 mm, Ø exterior 48.4 mm, alto 15 mm |
| Kv / R (20 °C) | 354 rpm/V / 185 mΩ | 332 rpm/V / 159 mΩ | 357 rpm/V / 162 mΩ |
| Eficiencia hover 4,500 m | 87.2% | 88.9% | 87.9% |
| Eficiencia ponderada | **87.2%** (+1.4) | **88.9%** (+3.0) | **87.9%** (+2.0) |
| Masa | 69 g | 80 g | 73 g |
| Autonomía del dron | **+2.5 %** | **+1.7 %** | **+2.3 %** |
| Materiales | US$12.1 | US$12.5 | US$12.2 |
| Bobinado en maniobra / máximo | 33 / 41 °C | 30 / 35 °C | 31 / 39 °C |
| Corriente máx. / densidad | 11.3 A / 44.5 A/mm² | 10.6 A / 37.5 A/mm² | 11.4 A / 41.4 A/mm² |
| Desmagnetización (< 0.7) | 0.62 | 0.60 | 0.61 |
| Frecuencia eléctrica máx. | 1242 Hz | 1242 Hz | 1242 Hz |

**Elegido: B · máxima eficiencia con la masa meta.**

**Robustez** (puntos de eficiencia que gana sobre el comercial si el modelo se equivoca; el mismo cambio se aplica al comercial cuando corresponde):

| Caso | A | B | C |
|---|---|---|---|
| modelo base | +1.4 | +3.0 | +2.0 |
| hierro pierde lo de catálogo (K_IRON 1.0) | +1.4 | +2.8 | +1.9 |
| entrehierro +0.2 mm (campana con juego) | +0.2 | +2.5 | +1.6 |
| bobinado peor: relleno 0.33 | -1.0 | +1.5 | +0.1 |
| imanes N42SH (más baratos) | +1.2 | +3.0 | +1.3 |
| enfriamiento a la mitad (K_THERMAL/2) | +1.4 (maniobra a 42 °C) | +3.2 (maniobra a 36 °C) | +2.1 (maniobra a 39 °C) |

**Mejor diseño por combinación** (autonomía del dron):

| Ranuras/polos | Autonomía | Eficiencia | Masa | Estator |
|---|---|---|---|---|
| 24N26P | +2.5 % | 87.2% | 69 g | Ø43×4.8 mm |
| 24N22P | +1.8 % | 87.4% | 72 g | Ø43×5.2 mm |
| 24N28P | +1.0 % | 86.1% | 70 g | Ø40×6.8 mm |
| 18N20P | +0.2 % | 87.8% | 81 g | Ø41×6.6 mm |
| 18N16P | -0.2 % | 87.9% | 83 g | Ø37×8.0 mm |
| 18N24P | -3.8 % | 86.7% | 92 g | Ø37×10.5 mm |

**Por acero** (el mejor diseño con cada uno): NO20: +2.5 % de autonomía, 87.2%; M270-35A: -0.2 % de autonomía, 84.8%; NO27: +1.8 % de autonomía, 87.4%.

**Costo de materiales del elegido:** acero eléctrico US$0.61, acero del rotor US$0.04, imanes US$3.90, cobre US$0.23, filamento US$1.20, eje US$1.00, rodamientos US$3.00, varios US$2.50 → **US$12.48**.

**Masa del elegido:** estator (dientes) 21.7 g, estator (yugo) 5.4 g, cobre 9.9 g, imanes 5.7 g, yugo del rotor 12.5 g, tapa impresa 4.0 g, base impresa 10.3 g, eje 2.8 g, rodamientos 3.4 g, tornillos, cables, adhesivo 4.0 g.

## 3. DS-D

20,186 diseños válidos (de un muestreo aleatorio + 3 rondas de refinamiento). Metas del G5 en términos del modelo: eficiencia ≥ 90.5% (comercial + 2 puntos), masa ≤ 317 g, materiales ≤ US$51.

| | A · máxima autonomía | B · máxima eficiencia con la masa meta | C · el más liviano que cumple |
|---|---|---|---|
| Ranuras / polos | 36N32P (factor 0.945) | 36N32P (factor 0.945) | 36N32P (factor 0.945) |
| Estator | Ø69.5 × 7.6 mm, NO20 | Ø71.9 × 11.0 mm, NO20 | Ø69.7 × 8.4 mm, NO20 |
| Diente / yugo / ranura | 3.27 / 1.76 / 9.5 mm | 3.47 / 2.23 / 8.9 mm | 3.30 / 1.78 / 8.8 mm |
| Bobinado | 7 vueltas/diente, estrella, 4 × Ø0.40 mm en paralelo (cobre +2 % del diseño) | 5 vueltas/diente, estrella, 6 × Ø0.38 mm en paralelo (cobre +2 % del diseño) | 6 vueltas/diente, estrella, 7 × Ø0.32 mm en paralelo (cobre +2 % del diseño) |
| Imanes | 32 imanes N48SH de 5.9 × 7.6 × 1.5 mm (ancho × largo × espesor, magnetizados en el espesor) | 32 imanes N48SH de 6.1 × 11.0 × 1.5 mm (ancho × largo × espesor, magnetizados en el espesor) | 32 imanes N48SH de 5.9 × 8.4 × 1.5 mm (ancho × largo × espesor, magnetizados en el espesor) |
| Rotor | anillo de acero 1.8 mm, Ø exterior 77.3 mm, alto 19 mm | anillo de acero 1.8 mm, Ø exterior 79.8 mm, alto 22 mm | anillo de acero 1.8 mm, Ø exterior 77.6 mm, alto 19 mm |
| Kv / R (20 °C) | 121 rpm/V / 138 mΩ | 113 rpm/V / 95 mΩ | 127 rpm/V / 113 mΩ |
| Eficiencia hover 4,500 m | 89.9% | 92.3% | 90.5% |
| Eficiencia ponderada | **89.9%** (+1.5) | **92.3%** (+3.9) | **90.6%** (+2.1) |
| Masa | 227 g | 313 g | 241 g |
| Autonomía del dron | **+5.5 %** | **+2.8 %** | **+5.3 %** |
| Materiales | US$31.7 | US$33.8 | US$32.1 |
| Bobinado en maniobra / máximo | 38 / 51 °C | 29 / 35 °C | 36 / 47 °C |
| Corriente máx. / densidad | 25.9 A / 51.5 A/mm² | 23.9 A / 35.1 A/mm² | 27.2 A / 48.4 A/mm² |
| Desmagnetización (< 0.7) | 0.56 | 0.53 | 0.55 |
| Frecuencia eléctrica máx. | 1034 Hz | 1034 Hz | 1034 Hz |

**Elegido: C · el más liviano que cumple.**

**Robustez** (puntos de eficiencia que gana sobre el comercial si el modelo se equivoca; el mismo cambio se aplica al comercial cuando corresponde):

| Caso | A | B | C |
|---|---|---|---|
| modelo base | +1.5 | +3.9 | +2.1 |
| hierro pierde lo de catálogo (K_IRON 1.0) | +1.6 | +3.6 | +2.1 |
| entrehierro +0.2 mm (campana con juego) | +1.2 | +3.9 | +1.9 |
| bobinado peor: relleno 0.33 | -0.6 | +2.9 | +0.5 |
| imanes N42SH (más baratos) | +0.7 | +3.9 | +1.7 |
| enfriamiento a la mitad (K_THERMAL/2) | +1.6 (maniobra a 51 °C) | +4.2 (maniobra a 37 °C) | +2.2 (maniobra a 48 °C) |

**Mejor diseño por combinación** (autonomía del dron):

| Ranuras/polos | Autonomía | Eficiencia | Masa | Estator |
|---|---|---|---|---|
| 36N32P | +5.5 % | 89.9% | 227 g | Ø69×7.6 mm |
| 36N40P | +5.1 % | 89.4% | 223 g | Ø73×7.4 mm |
| 36N42P | +4.6 % | 89.7% | 237 g | Ø72×8.2 mm |
| 24N28P | +3.5 % | 89.2% | 246 g | Ø69×7.8 mm |
| 24N26P | +2.6 % | 88.6% | 248 g | Ø63×10.2 mm |
| 24N20P | +2.4 % | 91.9% | 311 g | Ø69×10.0 mm |

**Por acero** (el mejor diseño con cada uno): NO27: +4.7 % de autonomía, 90.0%; M270-35A: +3.6 % de autonomía, 87.3%; NO20: +5.5 % de autonomía, 89.9%.

**Costo de materiales del elegido:** acero eléctrico US$1.98, acero del rotor US$0.10, imanes US$14.40, cobre US$0.65, filamento US$3.96, eje US$2.00, rodamientos US$5.00, varios US$4.00 → **US$32.10**.

**Masa del elegido:** estator (dientes) 71.6 g, estator (yugo) 16.5 g, cobre 27.9 g, imanes 18.5 g, yugo del rotor 34.9 g, tapa impresa 13.0 g, base impresa 34.1 g, eje 7.2 g, rodamientos 7.0 g, tornillos, cables, adhesivo 10.0 g.

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
