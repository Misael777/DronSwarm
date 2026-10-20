# M0 · Requisitos del motor propio

> Generado por `motor/calculo/requirements.py` desde el modelo del dron (engineering/, S04-S09). No editar a mano.

Lo que tiene que entregar **un** motor en cada condición. La eficiencia del comercial (columna COTS) es la que hay que superar: es la del modelo del S09, que en M1 se recalibra con datos del fabricante.

## DS-I · hélice 15×6.75", MTOW 2.43 kg, 6S

| Punto | Peso en el objetivo | rpm | Torque | Potencia en el eje | Corriente COTS | Eficiencia COTS |
|---|---|---|---|---|---|---|
| hover_4500m_0C — hover con MTOW: condición de autonomía del requisito | 55% | 3,821 | 0.152 N·m | 61 W | 6.4 A | 84.9% |
| hover_5000m_15C — hover con MTOW en el caso de diseño (aire caliente y alto) | 25% | 4,053 | 0.154 N·m | 65 W | 6.4 A | 85.4% |
| hover_vacio — DS-I liviano (referencia de carga parcial) | 10% | 3,661 | 0.141 N·m | 54 W | 5.9 A | 84.8% |
| maniobra_twr15 — empuje = 1.5 × peso: maniobras y viento | 10% | 4,965 | 0.226 N·m | 117 W | 9.3 A | 85.0% |
| maximo_twr20 — empuje = 2 × peso a 5,000 msnm: requisito de empuje/peso (corto, < 30 s) | restricción | 5,734 | 0.296 N·m | 178 W | 12.1 A | 84.4% |

- **Restricciones:** 5,734 rpm con la batería vacía (19.8 V) ⇒ Kv ≥ 324.5 rpm/V; torque pico 0.296 N·m; bobinado < 120 °C; imanes < 100 °C; montaje DMI-S: 4×M3 en Ø19/Ø25, Ø ≤ 50 mm, alto ≤ 32 mm; ESC hasta 200,000 eRPM.
- **Metas (G5):** eficiencia ponderada ≥ 88%; masa ≤ 75 g; materiales ≤ US$22 por motor.
- **A superar:** T-Motor MN4006 KV380 (AntiGravity) (68 g, US$75).
- Verificación contra el S09: corriente en hover 6.36 A (S09: 6.4 A).

## DS-D · hélice 26×11.7", MTOW 15.07 kg, 12S

| Punto | Peso en el objetivo | rpm | Torque | Potencia en el eje | Corriente COTS | Eficiencia COTS |
|---|---|---|---|---|---|---|
| hover_4500m_0C — hover con MTOW: condición de autonomía del requisito | 55% | 2,581 | 1.013 N·m | 274 W | 16.8 A | 86.2% |
| hover_5000m_15C — hover con MTOW en el caso de diseño (aire caliente y alto) | 25% | 2,743 | 1.023 N·m | 294 W | 17.0 A | 86.7% |
| hover_vacio — DS-D de regreso sin la carga | 10% | 2,109 | 0.690 N·m | 152 W | 11.7 A | 85.2% |
| maniobra_twr15 — empuje = 1.5 × peso: maniobras y viento | 10% | 3,357 | 1.507 N·m | 530 W | 24.6 A | 86.8% |
| maximo_twr20 — empuje = 2 × peso a 5,000 msnm: requisito de empuje/peso (corto, < 30 s) | restricción | 3,876 | 1.986 N·m | 806 W | 32.1 A | 86.5% |

- **Restricciones:** 3,876 rpm con la batería vacía (39.6 V) ⇒ Kv ≥ 109.7 rpm/V; torque pico 1.986 N·m; bobinado < 120 °C; imanes < 100 °C; montaje DMI-L: 4×M4 en Ø35, Ø ≤ 80 mm, alto ≤ 45 mm; ESC hasta 120,000 eRPM.
- **Metas (G5):** eficiencia ponderada ≥ 88%; masa ≤ 283 g; materiales ≤ US$51 por motor.
- **A superar:** MAD M6C12 EEE KV150 (257 g, US$170).
- Verificación contra el S09: corriente en hover 16.82 A (S09: 16.8 A).
