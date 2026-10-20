# M3 · Reductores: ¿motor directo o motor rápido con reductor?

> Generado por `motor/reductores/gearbox.py`. No editar a mano.

Para cada reductor y relación se optimizó un motor a la medida con el mismo modelo de M2 (puntos de operación vistos desde el motor: rpm × N y torque ÷ N ÷ eficiencia del engrane, más arrastre). La comparación es del **conjunto** a nivel dron. Autonomía relativa al comercial; eficiencia útil = potencia en la hélice / potencia eléctrica.

## DS-I

| Opción | N | Eficiencia útil | Masa (motor + reductor) | Autonomía | Costo | Motor a | Inercia vista por la hélice | +10 % de rpm en | Juego |
|---|---|---|---|---|---|---|---|---|---|
| Planetario comercial de aeromodelismo (tipo Neu/Hacker, escenario optimista) | 5 | 87.2% | 59 g (43 + 15) | **+5.1 %** | US$88 | 28,670 rpm | ×1.43 la de la hélice | 104 ms | 0.3° |
| Planetario comercial de aeromodelismo (tipo Neu/Hacker, escenario optimista) | 4 | 85.7% | 53 g (37 + 15) | **+4.9 %** | US$90 | 22,936 rpm | ×1.21 la de la hélice | 88 ms | 0.3° |
| Planetario comercial de aeromodelismo (tipo Neu/Hacker, escenario optimista) | 3 | 86.2% | 58 g (43 + 15) | **+4.1 %** | US$90 | 17,202 rpm | ×1.15 la de la hélice | 84 ms | 0.3° |
| **Directo (elegido en M2) · recomendado** | 1 | 88.9% | 80 g (80 + 0) | **+1.7 %** | US$12 | 5,734 rpm | ×1.03 la de la hélice | 75 ms | 0.0° |
| Planetario de 1 etapa (engranajes de acero cortados con láser, apilados) | 5 | 85.2% | 74 g (44 + 30) | **-1.2 %** | US$15 | 28,670 rpm | ×1.45 la de la hélice | 105 ms | 0.4° |
| Planetario de 1 etapa (engranajes de acero cortados con láser, apilados) | 4 | 83.2% | 66 g (37 + 30) | **-1.7 %** | US$16 | 22,936 rpm | ×1.22 la de la hélice | 89 ms | 0.4° |
| Planetario de 1 etapa (engranajes de acero cortados con láser, apilados) | 3 | 83.3% | 71 g (41 + 30) | **-2.6 %** | US$16 | 17,202 rpm | ×1.15 la de la hélice | 83 ms | 0.4° |
| Correa dentada HTD/GT (1 etapa) | 3 | 82.5% | 91 g (41 + 50) | **-8.1 %** | US$15 | 17,202 rpm | ×1.15 la de la hélice | 83 ms | 0.2° |
| Cicloidal de 1 etapa (2 discos a 180°, pines con rodillos) | 8 | 76.8% | 71 g (43 + 28) | **-10.3 %** | US$16 | 45,872 rpm | ×2.16 la de la hélice | 157 ms | 0.1° |
| Correa dentada HTD/GT (1 etapa) | 2 | 82.3% | 101 g (52 + 50) | **-10.6 %** | US$16 | 11,468 rpm | ×1.09 la de la hélice | 79 ms | 0.2° |
| Planetario de 1 etapa impreso (nylon/PA-CF) | 5 | 80.2% | 112 g (48 + 64) | **-15.1 %** | US$11 | 28,670 rpm | ×1.52 la de la hélice | 111 ms | 0.8° |
| Planetario de 1 etapa impreso (nylon/PA-CF) | 4 | 79.9% | 112 g (48 + 64) | **-15.3 %** | US$11 | 22,936 rpm | ×1.35 la de la hélice | 98 ms | 0.8° |
| Planetario de 1 etapa impreso (nylon/PA-CF) | 3 | 78.5% | 109 g (45 + 64) | **-16.2 %** | US$12 | 17,202 rpm | ×1.19 la de la hélice | 86 ms | 0.8° |
| Cicloidal de 1 etapa (2 discos a 180°, pines con rodillos) | 11 | — | — | **no viable**: el motor tendría que girar a 63,074 rpm | — | — | — | — | 0.1° |
| Cicloidal de 1 etapa (2 discos a 180°, pines con rodillos) | 15 | — | — | **no viable**: el motor tendría que girar a 86,010 rpm | — | — | — | — | 0.1° |
| Armónico (strain wave) | 30 | — | — | **no viable**: el motor tendría que girar a 172,020 rpm | — | — | — | — | 0.0° |

**Riesgos por tipo:**

- *Planetario de 1 etapa (engranajes de acero cortados con láser, apilados):* ruido de engrane a 10-30 krpm; engranajes cortados con láser tienen perfil imperfecto (más pérdidas y desgaste); lubricación con polvo de mina.
- *Planetario comercial de aeromodelismo (tipo Neu/Hacker, escenario optimista):* se compra (no se fabrica en casa) y cuesta tanto como el motor comercial; pensado para aviones, no para 1,000 h de hover.
- *Planetario de 1 etapa impreso (nylon/PA-CF):* dientes plásticos se deforman con calor y fatigan: vida de decenas de horas a estos torques.
- *Cicloidal de 1 etapa (2 discos a 180°, pines con rodillos):* excéntrico a 30-60 krpm: vibración y rodamientos muy cargados; relación mínima ~8 lleva el motor a rpm muy altas.
- *Armónico (strain wave):* relación mínima ~30: el motor tendría que girar a 110-170 krpm (imposible para el ESC y los rodamientos); el flexspline se fatiga girando continuo; diseñado para robots lentos y precisos, no para hélices.
- *Correa dentada HTD/GT (1 etapa):* no es coaxial: obliga a rediseñar el extremo del brazo; la correa se estira y hay que tensarla.

## DS-D

| Opción | N | Eficiencia útil | Masa (motor + reductor) | Autonomía | Costo | Motor a | Inercia vista por la hélice | +10 % de rpm en | Juego |
|---|---|---|---|---|---|---|---|---|---|
| Planetario comercial de aeromodelismo (tipo Neu/Hacker, escenario optimista) | 5 | 89.9% | 201 g (131 + 70) | **+7.1 %** | US$167 | 19,380 rpm | ×1.29 la de la hélice | 85 ms | 0.3° |
| Planetario comercial de aeromodelismo (tipo Neu/Hacker, escenario optimista) | 4 | 89.4% | 216 g (146 + 70) | **+5.5 %** | US$168 | 15,504 rpm | ×1.26 la de la hélice | 83 ms | 0.3° |
| Planetario comercial de aeromodelismo (tipo Neu/Hacker, escenario optimista) | 3 | 89.7% | 223 g (154 + 70) | **+5.4 %** | US$172 | 11,628 rpm | ×1.15 la de la hélice | 75 ms | 0.3° |
| **Directo (elegido en M2) · recomendado** | 1 | 90.6% | 241 g (241 + 0) | **+5.3 %** | US$32 | 3,876 rpm | ×1.04 la de la hélice | 68 ms | 0.0° |
| Planetario de 1 etapa (engranajes de acero cortados con láser, apilados) | 5 | 87.4% | 288 g (133 + 154) | **-1.2 %** | US$32 | 19,380 rpm | ×1.31 la de la hélice | 86 ms | 0.4° |
| Planetario de 1 etapa (engranajes de acero cortados con láser, apilados) | 4 | 87.5% | 318 g (164 + 154) | **-2.9 %** | US$32 | 15,504 rpm | ×1.24 la de la hélice | 81 ms | 0.4° |
| Planetario de 1 etapa (engranajes de acero cortados con láser, apilados) | 3 | 86.9% | 311 g (157 + 154) | **-3.2 %** | US$35 | 11,628 rpm | ×1.16 la de la hélice | 76 ms | 0.4° |
| Correa dentada HTD/GT (1 etapa) | 3 | 86.1% | 408 g (154 + 254) | **-9.2 %** | US$32 | 11,628 rpm | ×1.15 la de la hélice | 75 ms | 0.2° |
| Correa dentada HTD/GT (1 etapa) | 2 | 85.9% | 438 g (185 + 254) | **-11.0 %** | US$36 | 7,752 rpm | ×1.09 la de la hélice | 72 ms | 0.2° |
| Planetario de 1 etapa impreso (nylon/PA-CF) | 5 | 82.5% | 557 g (160 + 397) | **-20.0 %** | US$23 | 19,380 rpm | ×1.38 la de la hélice | 90 ms | 0.8° |
| Planetario de 1 etapa impreso (nylon/PA-CF) | 4 | 81.1% | 549 g (151 + 397) | **-21.0 %** | US$25 | 15,504 rpm | ×1.20 la de la hélice | 79 ms | 0.8° |
| Planetario de 1 etapa impreso (nylon/PA-CF) | 3 | 81.7% | 565 g (168 + 397) | **-21.1 %** | US$27 | 11,628 rpm | ×1.18 la de la hélice | 77 ms | 0.8° |
| Cicloidal de 1 etapa (2 discos a 180°, pines con rodillos) | 8 | — | — | **no viable**: ningún motor cumple (eRPM del ESC, temperatura o tamaño) | — | — | — | — | 0.1° |
| Cicloidal de 1 etapa (2 discos a 180°, pines con rodillos) | 11 | — | — | **no viable**: ningún motor cumple (eRPM del ESC, temperatura o tamaño) | — | — | — | — | 0.1° |
| Cicloidal de 1 etapa (2 discos a 180°, pines con rodillos) | 15 | — | — | **no viable**: ningún motor cumple (eRPM del ESC, temperatura o tamaño) | — | — | — | — | 0.1° |
| Armónico (strain wave) | 30 | — | — | **no viable**: el motor tendría que girar a 116,280 rpm | — | — | — | — | 0.0° |

**Riesgos por tipo:**

- *Planetario de 1 etapa (engranajes de acero cortados con láser, apilados):* ruido de engrane a 10-30 krpm; engranajes cortados con láser tienen perfil imperfecto (más pérdidas y desgaste); lubricación con polvo de mina.
- *Planetario comercial de aeromodelismo (tipo Neu/Hacker, escenario optimista):* se compra (no se fabrica en casa) y cuesta tanto como el motor comercial; pensado para aviones, no para 1,000 h de hover.
- *Planetario de 1 etapa impreso (nylon/PA-CF):* dientes plásticos se deforman con calor y fatigan: vida de decenas de horas a estos torques.
- *Cicloidal de 1 etapa (2 discos a 180°, pines con rodillos):* excéntrico a 30-60 krpm: vibración y rodamientos muy cargados; relación mínima ~8 lleva el motor a rpm muy altas.
- *Armónico (strain wave):* relación mínima ~30: el motor tendría que girar a 110-170 krpm (imposible para el ESC y los rodamientos); el flexspline se fatiga girando continuo; diseñado para robots lentos y precisos, no para hélices.
- *Correa dentada HTD/GT (1 etapa):* no es coaxial: obliga a rediseñar el extremo del brazo; la correa se estira y hay que tensarla.

## Conclusión

- **DS-I:** directo +1.7 % de autonomía (US$12). Mejor reductor hecho en casa (planetario de 1 etapa, N = 5): -1.2 %: **pierde por 2.8 puntos**. Un planetario comercial de aeromodelismo, con supuestos optimistas, daría +5.1 % (+3.4 puntos sobre el directo) pero el conjunto costaría US$88 por motor, más que el motor comercial que se quiere reemplazar.
- **DS-D:** directo +5.3 % de autonomía (US$32). Mejor reductor hecho en casa (planetario de 1 etapa, N = 5): -1.2 %: **pierde por 6.5 puntos**. Un planetario comercial de aeromodelismo, con supuestos optimistas, daría +7.1 % (+1.8 puntos sobre el directo) pero el conjunto costaría US$167 por motor, más que el motor comercial que se quiere reemplazar.

**Por qué pierden los reductores hechos en casa:**

- El motor rápido es chico, pero gira a 10-30 krpm: sus pérdidas en el hierro suben con la frecuencia y su eficiencia queda por debajo de la del motor directo, que ya trabaja cerca de su óptimo con la hélice lenta.
- A eso se suma la pérdida del engrane (3-10 %) y el arrastre, y la masa del reductor se come el ahorro del motor.
- **Armónico: descartado.** Su relación mínima (~30) pone el motor a > 100,000 rpm; además pierde 20-25 % y su pieza flexible no está hecha para girar continuo a miles de rpm.
- **Cicloidal:** relación mínima ~8, motor a 30-45 krpm, excéntrico que vibra y eficiencia ~90 %. En el DS-D ningún motor cumple el límite de eRPM del ESC.
- **Planetario impreso:** pierde mucho y no aguanta la vida útil. **Correa:** pesa (poleas, soporte) y no es coaxial.
- **Respuesta del empuje:** la inercia del rotor del motor se multiplica por N². Con reductor, la hélice tarda 10-115 % más en acelerar, lo que vuelve menos firme el control de actitud, sobre todo con viento.

**Decisión propuesta (ADR-014):** motor **directo** en el DS-I y el DS-D. El planetario comercial de aeromodelismo queda anotado como la única variante que podría ganar en autonomía, a revisar si en el futuro aparece uno durable y barato, o para un DS-H con hélices de 30" o más.
