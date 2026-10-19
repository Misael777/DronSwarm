# Carga progresiva y liberación en vuelo · DS-D (S12-04)

Cajas de prueba con arena embolsada: 1.25 / 2.5 / 3.75 / 5.0 / 5.5 kg (25 / 50 / 75 / 100 / 110 %). Cada caja en la
caja estándar de 300 × 240 × 220 mm con anilla.

| Paso | Carga | Vuelo | Criterio | Throttle de hover | Corriente de hover | Liberación | ¿Cumple? |
|---|---|---|---|---|---|---|---|
| 1 | 1.25 kg | Hover 60 s a 5 m + tramo de 50 m | Estable, sin oscilación de la carga | | | — | |
| 2 | 2.5 kg | ídem | ídem | | | — | |
| 3 | 3.75 kg | ídem | ídem | | | — | |
| 4 | 5.0 kg | ídem + autonomía hasta el 25 % | Potencia ± 10 % del modelo | | | — | |
| 5 | 5.5 kg (110 %) | Solo hover de 60 s a 3 m | Throttle de hover ≤ 75 %; ninguna corriente de ESC sobre 40 A | | | — | |
| 6 | 5.0 kg | Bajar hasta apoyar la caja y liberar desde QGC (Gripper) | Abre a la primera; el dron no salta más de 1 m al soltar | | | | |
| 7 | 5.0 kg | **Liberación en vuelo** a 1.5 m sobre una colchoneta (prueba de contingencia) | El dron recupera la altura en < 2 s, sin oscilación | | | | |
| 8 | 5.0 kg | Cortar la energía del servo con la caja colgada (desconectar su regulador) | **La caja NO se suelta** (a prueba de fallas) | | | | |

Seguridad: nadie bajo el dron con carga; la zona de caída se marca con conos (radio de 5 m).
