# M3 · Reductores: ¿motor directo o motor rápido con reductor?

> Generado por `motor/reductores/gearbox.py`. No editar a mano.

Para cada reductor y relación se optimizó un motor a la medida con el mismo modelo de M2 (puntos de operación vistos desde el motor: rpm × N y torque ÷ N ÷ eficiencia del engrane, más arrastre). La comparación es del **conjunto** a nivel dron. Autonomía relativa al comercial; eficiencia útil = potencia en la hélice / potencia eléctrica.

## DS-I

| Opción | N | Eficiencia útil | Masa (motor + reductor) | Autonomía | Costo | Motor a | Inercia vista por la hélice | +10 % de rpm en | Juego |
|---|---|---|---|---|---|---|---|---|---|
| Planetario comercial de aeromodelismo (tipo Neu/Hacker, escenario optimista) | 5 | 86.5% | 54 g (39 + 15) | **+6.3 %** | US$89 | 28,670 rpm | ×1.35 la de la hélice | 98 ms | 0.3° |
| Planetario comercial de aeromodelismo (tipo Neu/Hacker, escenario optimista) | 4 | 85.6% | 52 g (37 + 15) | **+6.0 %** | US$90 | 22,936 rpm | ×1.18 la de la hélice | 86 ms | 0.3° |
| Planetario comercial de aeromodelismo (tipo Neu/Hacker, escenario optimista) | 3 | 86.4% | 58 g (43 + 15) | **+5.2 %** | US$90 | 17,202 rpm | ×1.16 la de la hélice | 84 ms | 0.3° |
| **Directo (elegido en M2) · recomendado** | 1 | 89.3% | 80 g (80 + 0) | **+3.1 %** | US$12 | 5,734 rpm | ×1.03 la de la hélice | 75 ms | 0.0° |
| Planetario de 1 etapa (engranajes de acero cortados con láser, apilados) | 5 | 84.0% | 69 g (39 + 30) | **-0.3 %** | US$15 | 28,670 rpm | ×1.36 la de la hélice | 98 ms | 0.4° |
| Planetario de 1 etapa (engranajes de acero cortados con láser, apilados) | 4 | 85.2% | 75 g (46 + 30) | **-0.5 %** | US$15 | 22,936 rpm | ×1.31 la de la hélice | 95 ms | 0.4° |
| Planetario de 1 etapa (engranajes de acero cortados con láser, apilados) | 3 | 83.9% | 73 g (43 + 30) | **-1.3 %** | US$16 | 17,202 rpm | ×1.15 la de la hélice | 84 ms | 0.4° |
| Correa dentada HTD/GT (1 etapa) | 3 | 83.1% | 92 g (43 + 50) | **-6.9 %** | US$15 | 17,202 rpm | ×1.15 la de la hélice | 84 ms | 0.2° |
| Correa dentada HTD/GT (1 etapa) | 2 | 82.5% | 100 g (51 + 50) | **-9.3 %** | US$16 | 11,468 rpm | ×1.10 la de la hélice | 80 ms | 0.2° |
| Cicloidal de 1 etapa (2 discos a 180°, pines con rodillos) | 8 | 76.8% | 72 g (45 + 28) | **-9.6 %** | US$16 | 45,872 rpm | ×2.23 la de la hélice | 162 ms | 0.1° |
| Planetario de 1 etapa impreso (nylon/PA-CF) | 5 | 78.9% | 104 g (41 + 64) | **-14.1 %** | US$11 | 28,670 rpm | ×1.39 la de la hélice | 101 ms | 0.8° |
| Planetario de 1 etapa impreso (nylon/PA-CF) | 4 | 80.3% | 114 g (51 + 64) | **-14.5 %** | US$11 | 22,936 rpm | ×1.38 la de la hélice | 100 ms | 0.8° |
| Planetario de 1 etapa impreso (nylon/PA-CF) | 3 | 78.5% | 107 g (43 + 64) | **-15.1 %** | US$12 | 17,202 rpm | ×1.16 la de la hélice | 84 ms | 0.8° |
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
| Planetario comercial de aeromodelismo (tipo Neu/Hacker, escenario optimista) | 5 | 90.9% | 206 g (137 + 70) | **+8.1 %** | US$168 | 19,380 rpm | ×1.33 la de la hélice | 87 ms | 0.3° |
| Planetario comercial de aeromodelismo (tipo Neu/Hacker, escenario optimista) | 4 | 90.0% | 209 g (139 + 70) | **+6.8 %** | US$168 | 15,504 rpm | ×1.21 la de la hélice | 80 ms | 0.3° |
| Planetario comercial de aeromodelismo (tipo Neu/Hacker, escenario optimista) | 3 | 89.9% | 218 g (148 + 70) | **+6.1 %** | US$172 | 11,628 rpm | ×1.13 la de la hélice | 74 ms | 0.3° |
| **Directo (elegido en M2) · recomendado** | 1 | 90.6% | 237 g (237 + 0) | **+5.7 %** | US$32 | 3,876 rpm | ×1.04 la de la hélice | 68 ms | 0.0° |
| Planetario de 1 etapa (engranajes de acero cortados con láser, apilados) | 5 | 88.2% | 294 g (140 + 154) | **-0.6 %** | US$32 | 19,380 rpm | ×1.39 la de la hélice | 91 ms | 0.4° |
| Planetario de 1 etapa (engranajes de acero cortados con láser, apilados) | 4 | 87.8% | 304 g (150 + 154) | **-1.6 %** | US$32 | 15,504 rpm | ×1.26 la de la hélice | 82 ms | 0.4° |
| Planetario de 1 etapa (engranajes de acero cortados con láser, apilados) | 3 | 87.2% | 299 g (145 + 154) | **-2.0 %** | US$35 | 11,628 rpm | ×1.11 la de la hélice | 73 ms | 0.4° |
| Correa dentada HTD/GT (1 etapa) | 3 | 86.3% | 399 g (145 + 254) | **-8.4 %** | US$31 | 11,628 rpm | ×1.11 la de la hélice | 73 ms | 0.2° |
| Correa dentada HTD/GT (1 etapa) | 2 | 85.6% | 423 g (169 + 254) | **-10.5 %** | US$35 | 7,752 rpm | ×1.06 la de la hélice | 70 ms | 0.2° |
| Planetario de 1 etapa impreso (nylon/PA-CF) | 5 | 82.8% | 549 g (152 + 397) | **-19.2 %** | US$23 | 19,380 rpm | ×1.38 la de la hélice | 91 ms | 0.8° |
| Planetario de 1 etapa impreso (nylon/PA-CF) | 4 | 82.2% | 554 g (157 + 397) | **-20.1 %** | US$23 | 15,504 rpm | ×1.25 la de la hélice | 82 ms | 0.8° |
| Planetario de 1 etapa impreso (nylon/PA-CF) | 3 | 81.7% | 558 g (161 + 397) | **-20.7 %** | US$27 | 11,628 rpm | ×1.17 la de la hélice | 77 ms | 0.8° |
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

- **DS-I:** directo +3.1 % de autonomía (US$12). Mejor reductor hecho en casa (planetario de 1 etapa, N = 5): -0.3 %: **pierde por 3.3 puntos**. Un planetario comercial de aeromodelismo, con supuestos optimistas, daría +6.3 % (+3.3 puntos sobre el directo) pero el conjunto costaría US$89 por motor, más que el motor comercial que se quiere reemplazar.
- **DS-D:** directo +5.7 % de autonomía (US$32). Mejor reductor hecho en casa (planetario de 1 etapa, N = 5): -0.6 %: **pierde por 6.3 puntos**. Un planetario comercial de aeromodelismo, con supuestos optimistas, daría +8.1 % (+2.4 puntos sobre el directo) pero el conjunto costaría US$168 por motor, más que el motor comercial que se quiere reemplazar.

**Por qué pierden los reductores hechos en casa:**

- El motor rápido es chico, pero gira a 10-30 krpm: sus pérdidas en el hierro suben con la frecuencia y su eficiencia queda por debajo de la del motor directo, que ya trabaja cerca de su óptimo con la hélice lenta.
- A eso se suma la pérdida del engrane (3-10 %) y el arrastre, y la masa del reductor se come el ahorro del motor.
- **Armónico: descartado.** Su relación mínima (~30) pone el motor a > 100,000 rpm; además pierde 20-25 % y su pieza flexible no está hecha para girar continuo a miles de rpm.
- **Cicloidal:** relación mínima ~8, motor a 30-45 krpm, excéntrico que vibra y eficiencia ~90 %. En el DS-D ningún motor cumple el límite de eRPM del ESC.
- **Planetario impreso:** pierde mucho y no aguanta la vida útil. **Correa:** pesa (poleas, soporte) y no es coaxial.
- **Respuesta del empuje:** la inercia del rotor del motor se multiplica por N². Con reductor, la hélice tarda 10-115 % más en acelerar, lo que vuelve menos firme el control de actitud, sobre todo con viento.

**Decisión propuesta (ADR-014):** motor **directo** en el DS-I y el DS-D. El planetario comercial de aeromodelismo queda anotado como la única variante que podría ganar en autonomía, a revisar si en el futuro aparece uno durable y barato, o para un DS-H con hélices de 30" o más.
