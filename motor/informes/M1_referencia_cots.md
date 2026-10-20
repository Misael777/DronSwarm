# M1 · Modelo de referencia de los motores comerciales

> Generado por `motor/calculo/reference.py`. No editar a mano.

El motor propio se diseña con el **mismo** modelo de pérdidas que aquí reproduce a los comerciales. Así la comparación es justa: cualquier error del modelo afecta igual a los dos.

Modelo: pérdidas en cobre I²R (R sube 0.39 %/K) + pérdidas en vacío c1·ω + c2·ω² (hierro, rodamientos, aire), con el imán más débil en caliente (−0.12 %/K). Temperaturas del bobinado supuestas hasta el térmico de M5: hover 55 °C, maniobra 75 °C, maximo 95 °C.

## DS-I · MN4006 KV380 (18N24P, Ø44.35×21 mm, 68 g)

- Ficha: Kv 380, R 194 mΩ, I0 0.3 A a 22 V, Imax 16 A. Fuente: ligpower.com (2026-10-20): ficha y tabla de pruebas del fabricante.
- Calibración: ficha + tabla de banco del fabricante. Kv efectivo 380.0 rpm/V (×1.0), pérdidas en vacío 32% lineales con la velocidad, ESC 92.4%.
- Sensibilidad al Kv efectivo (los datos no lo separan del ESC): eficiencia en hover 84.8% con Kv×1.00 (ajuste 1.5 pt), 83.0% con Kv×1.05 (ajuste 1.45 pt), 81.5% con Kv×1.10 (ajuste 1.41 pt), 80.5% con Kv×1.15 (ajuste 1.39 pt). **La meta usa el valor más alto** (lo conservador).
- **Error contra la tabla del fabricante: 1.5 puntos RMS** (máx. 2.35). La tabla redondea el torque a 0.01 N·m, lo que solo ya mete ±1-3 puntos a carga baja.

| Acelerador | rpm | Torque | Corriente medida | Corriente modelo | Eficiencia sistema medida | Modelo |
|---|---|---|---|---|---|---|
| 50% | 3746 | 0.15 | 3.1 A | 3.07 A | 79.1% | 79.8% |
| 55% | 4089 | 0.18 | 4.1 A | 4.05 A | 78.3% | 79.3% |
| 60% | 4358 | 0.20 | 4.8 A | 4.81 A | 79.2% | 79.0% |
| 65% | 4634 | 0.23 | 5.8 A | 5.93 A | 80.2% | 78.4% |
| 75% | 5215 | 0.29 | 8.3 A | 8.55 A | 79.5% | 77.1% |
| 85% | 5627 | 0.33 | 10.7 A | 10.62 A | 75.7% | 76.3% |
| 100% | 6177 | 0.40 | 15.0 A | 14.54 A | 71.9% | 74.1% |

**En los puntos de operación del dron (motor solo, sin ESC):**

| Punto | rpm | Torque | Bobinado | Corriente | Eficiencia | Pérdidas | Cobre / vacío |
|---|---|---|---|---|---|---|---|
| hover_4500m_0C | 3,821 | 0.152 N·m | 55 °C | 6.4 A | **84.8%** | 11.0 W | 83% / 17% |
| hover_5000m_15C | 4,053 | 0.154 N·m | 55 °C | 6.5 A | **85.2%** | 11.4 W | 82% / 18% |
| hover_vacio | 3,661 | 0.141 N·m | 55 °C | 5.9 A | **85.0%** | 9.6 W | 81% / 19% |
| maniobra_twr15 | 4,965 | 0.226 N·m | 75 °C | 9.7 A | **82.5%** | 24.9 W | 89% / 11% |
| maximo_twr20 | 5,734 | 0.296 N·m | 95 °C | 13.0 A | **79.5%** | 45.8 W | 92% / 8% |

**Eficiencia ponderada del comercial: 84.7%** (pesos de M0); en hover, a superar: **84.8%** (extremo alto de la sensibilidad).

## DS-D · M6C12 KV150 (24N28P, Ø72×33.4 mm, 257 g)

- Ficha: Kv 150, R 90 mΩ, I0 0.67 A a 20 V, Imax 36.18 A. Fuente: openelab.io / rcdrone.top (2026-10-20): ficha de MAD Components; la tabla de pruebas solo está en imagen.
- Calibración: solo ficha (I0 y R); reparto de pérdidas en vacío copiado del MN4006 — se mide en el banco (S10). Kv efectivo 150 rpm/V (×1.0), pérdidas en vacío 35% lineales con la velocidad.
- Sensibilidad al Kv efectivo (los datos no lo separan del ESC): eficiencia en hover 87.3% con Kv×1.00, 86.7% con Kv×1.05, 86.1% con Kv×1.10, 85.4% con Kv×1.15. **La meta usa el valor más alto** (lo conservador).

**En los puntos de operación del dron (motor solo, sin ESC):**

| Punto | rpm | Torque | Bobinado | Corriente | Eficiencia | Pérdidas | Cobre / vacío |
|---|---|---|---|---|---|---|---|
| hover_4500m_0C | 2,581 | 1.013 N·m | 55 °C | 16.9 A | **87.3%** | 39.9 W | 74% / 26% |
| hover_5000m_15C | 2,743 | 1.023 N·m | 55 °C | 17.1 A | **87.6%** | 41.6 W | 72% / 28% |
| hover_vacio | 2,109 | 0.690 N·m | 55 °C | 11.7 A | **87.6%** | 21.5 W | 65% / 35% |
| maniobra_twr15 | 3,357 | 1.507 N·m | 75 °C | 25.6 A | **85.8%** | 88.1 W | 82% / 18% |
| maximo_twr20 | 3,876 | 1.986 N·m | 95 °C | 34.5 A | **83.5%** | 159.1 W | 87% / 13% |

**Eficiencia ponderada del comercial: 87.2%** (pesos de M0); en hover, a superar: **87.3%** (extremo alto de la sensibilidad).

## Qué dice esto para el diseño propio

- **En hover, la mayor parte de las pérdidas es cobre:** 83% en el MN4006 y 74% en el M6C12. Los comerciales son motores livianos con bobinados de resistencia alta para su hélice. **Ahí está el margen del diseño propio:** más cobre (estator más largo o más ancho, mejor relleno de ranura) baja las pérdidas I²R, a cambio de algo de masa. M2 busca el punto óptimo.
- Las pérdidas en vacío (hierro y rodamientos) son la parte menor en hover, pero crecen con la frecuencia: láminas delgadas y no exagerar el número de polos.
- A fondo domina todavía más el cobre: el diseño propio tiene que cuidar la temperatura (M5).
- Se recalibra con el banco propio (S10) cuando lleguen los motores: la tabla del MN4006 es del fabricante y la del M6C12 no existe en texto.

## Hallazgo para el S09 (decisión pendiente del G2)

La ficha real del M6C12 (90 mΩ, 0.67 A, **36.18 A máx.**, 1,725 W) difiere de los valores estimados que usa `engineering/cots.py` (100 mΩ, 0.9 A, 45 A, 1,900 W). El fabricante recomienda hélices de 21-24". Con esos datos:

| Hélice | Autonomía (req. ≥ 20 min) | Empuje/peso a 5,000 msnm | Corriente a fondo |
|---|---|---|---|
| 26" (línea base actual) | 21.9 min | 2.29 | 36.2 A: **justo en el límite** del motor |
| 24" (recomendada por MAD) | 20.6 min | 2.38 | 34.5 A |

La selección automática pasaría a 24". No se cambió: la línea base (26", CAD, SITL, parámetros, BOM) queda hasta la decisión del G2. El motor propio del DS-D se diseña con margen de corriente para cualquiera de las dos.
