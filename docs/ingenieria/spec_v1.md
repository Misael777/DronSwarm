# Spec v1 · DS-I, DS-D y DS-H

> Generado por `engineering/spec_v1.py` el 2026-10-19. No editar a mano: cambiar la fuente (dimensionamiento, evidencias) y volver a correr `.venv/bin/python -m engineering.spec_v1`.

**Estado: propuesta para el Gate G1 (PDR).** Se congela cuando se aprueba el G1. Depende de las decisiones del Gate G0, todavía pendientes: escenarios D (DS-I), C (DS-D) y A (DS-H). Si el G0 elige otros escenarios, esta spec se regenera.

## 1. Qué significa congelar la spec

- Desde el G1, **el frame (S07-S09), la selección de componentes comerciales y el prototipo se diseñan contra estos números**: masa máxima, empuje mínimo y energía mínima. Si una pieza real los excede, se registra el desvío y se decide (no se ajusta la spec en silencio).
- El **motor, la electrónica y las baterías propias (S17 en adelante)** se especifican con la sección 4, corregida con lo que midan el banco de empuje (S10) y los vuelos de prototipo.
- Cambiar la spec requiere un cambio registrado en `docs/decisiones.md` y regenerar este archivo.

## 2. Envolvente por dron

| | **DS-I** (esc. D) | **DS-D** (esc. C) | **DS-H** (esc. A) |
|---|---|---|---|
| MTOW máximo | 2.69 kg | 15.61 kg | 30.26 kg |
| Carga útil | 0.0 kg | 5.0 kg | 10.0 kg |
| Masa vacía (sin carga) | 2.69 kg | 10.61 kg | 20.26 kg |
| Rotores · hélice | 4 · 17x7.7" | 6 · 26x11.7" | 8 · 30x10.5" |
| Empuje máximo a 5,000 msnm, 15 °C | 5.6 kgf | 33.1 kgf | 64.8 kgf |
| Relación empuje/peso (mín. 2.0) | 2.09 | 2.12 | 2.14 |
| Hover en % del empuje máximo (40-65 %) | 44 % | 43 % | 43 % |
| Motor caído: empuje restante / peso | no aplica (4 rotores) | 1.41 | 1.61 |
| Batería · energía | 6S2P 50S · 216 Wh | 12S5P P42A · 907 Wh | 12S8P P42A · 1452 Wh |
| Potencia en hover a 4,500 msnm | 330 W | 2,134 W | 4,229 W |
| Potencia en hover a 5,000 msnm, 15 °C | 352 W | 2,277 W | 4,524 W |
| Autonomía batería nueva (4,500 msnm, 0 °C) | 31.3 min | 20.3 min | 16.4 min |
| Autonomía fin de vida (80 %) | 24.1 min | 15.6 min | 12.6 min |
| Autonomía en frío (−15 °C) | 28.3 min | 18.4 min | 14.8 min |
| Autonomía medida como DJI (referencia) | 47.4 min | 31.3 min | 25.3 min |
| Corriente de batería en hover | 15.8 A | 51.1 A | 102.2 A |
| Distancia entre ejes (wheelbase) | 672 mm | 1453 mm | 2190 mm |
| Brazos | Ø20×1 mm · FS 15.2 | Ø22×1.5 mm · FS 2.3 | Ø30×2 mm · FS 2.8 |
| Costo de materiales (BOM) | US$735 | US$1,627 | US$2,667 |

Casos de diseño: empuje a 5,000 msnm y 15 °C (aire 47 % menos denso que a nivel del mar); autonomía a 4,500 msnm y 0 °C; frío a −15 °C. Factores de seguridad: empuje/peso 2.0, corriente de motor y ESC 1.3, batería 1.3, estructura 2.5.

## 3. Cierre del ciclo cálculo ↔ simulación

Se compara lo que midieron los vuelos en PX4 + Gazebo (rpm reales de los motores en vuelo estacionario) con lo que predijo el dimensionamiento. Criterio del plan: desviación < 10 %.

| Dron | Vuelo | Muestras | rpm medido / calculado | Error rpm | Empuje/peso | Autonomía a las rpm medidas / calculada | ¿Coherente? |
|---|---|---|---|---|---|---|---|
| DS-D | entrega | 107 | 2,626 / 2,628 | -0.1 % | 0.999 | 20.4 / 20.3 min | sí |
| DS-H | circuito | 114 | 2,617 / 2,615 | +0.0 % | 1.001 | 16.4 / 16.4 min | sí |
| DS-I | inspeccion | 6 | 3,175 / 3,127 | +1.6 % | 1.031 | 30.1 / 31.3 min | sí |

**Lectura honesta:** la coincidencia es casi exacta porque el simulador usa las mismas constantes de motor y hélice que el cálculo. Esto prueba que el modelo del dron en el simulador es **coherente** con el diseño (masas, inercias, constantes, controlador), no que el diseño sea correcto. Hay dos validaciones independientes:

1. Contra drones reales (S03): el modelo predice la autonomía del DJI M400 con -13.4 % de error. Es conservador y no cumple el criterio < 10 %.
2. Contra el banco de empuje (S10) y los vuelos del prototipo (S11-S12): es la validación definitiva y puede corregir esta spec.

## 4. Requisitos que hereda el motor propio (entrada para S17+)

| | **DS-I** | **DS-D** | **DS-H** |
|---|---|---|---|
| Constante kv | 278 rpm/V | 116 rpm/V | 120 rpm/V |
| Tensión nominal | 6S · 21.6 V | 12S · 43.2 V | 12S · 43.2 V |
| rpm sin carga (kv × V nominal) | 6,005 | 5,011 | 5,184 |
| rpm en hover (4,500 msnm) | 3,126 | 2,628 | 2,615 |
| Potencia eléctrica en hover por motor | 82 W | 356 W | 529 W |
| Potencia máxima por motor | 296 W | 1,380 W | 2,064 W |
| Corriente máxima por motor (FS 1.3) | 13.7 A | 31.9 A | 47.8 A |
| Eficiencia del motor en hover (mín.) | 84 % | 86 % | 87 % |
| Masa máxima por motor | 74 g | 345 g | 516 g |
| Costo objetivo por motor (COTS hoy) | US$18 | US$56 | US$80 |
| ESC: corriente continua | 17.8 A | 41.5 A | 62.1 A |

Un motor propio tiene que igualar o superar la eficiencia en hover, no exceder la masa y bajar el costo; la potencia máxima incluye el margen para empuje/peso 2.0 a 5,000 msnm.

## 5. Enjambre, comunicaciones y seguridad (validado en S06)

- **Control de formación:** consenso distribuido (cada dron conoce la ruta de la misión y se ajusta con sus vecinos). El líder-seguidor queda como alternativa, no como arquitectura principal: con la evitación final no chocó, pero su error de formación es ~70 % mayor, tarda más y todo el enjambre depende de un solo dron.
- **Evitación:** separación mínima deseada de 3 m entre centros y obstáculos rodeados con 2.5 m libres; predicción del acercamiento a 5 s con sesgo a la derecha.
  Con viento de 8 m/s la distancia libre a la torre bajó a ~1 m (sin contacto): **con viento fuerte, margen de obstáculos de 4 m y crucero más lento** (acción abierta para el S14, ensayo en campo).
- **Protocolo de pérdida de radio entre drones:** el dron sin noticias por 0.8 s frena, sube 8 m y queda en una capa reservada; los demás esquivan su última posición conocida durante 20 s. Después actúa el failsafe de PX4 (retorno a casa).
- **Radio:** se diseña para tolerar hasta 30 % de pérdida de paquetes con latencia p95 < 100 ms a 10 Hz por dron; malla de 900 MHz para enlace con tierra (alcance de diseño, a confirmar en campo en S14).

Resultados del simulador rápido (cada fila: corridas Monte Carlo con viento, ruido de GNSS y radio simulada):

| Condición | Corridas | Con colisión | Separación mín. | Torre: distancia libre mín. | Error de formación p95 |
|---|---|---|---|---|---|
| consenso nominal | 200 | 0 | 1.92 m | 2.67 m | 2.36 m |
| consenso perdida 30 | 200 | 0 | 1.86 m | 2.72 m | 2.36 m |
| consenso perdida 50 | 200 | 0 | 1.77 m | 2.64 m | 2.37 m |
| consenso viento 8 | 200 | 0 | 2.02 m | 0.98 m | 2.5 m |
| consenso wifi 24 | 200 | 0 | 1.92 m | 2.67 m | 2.36 m |
| caida radio en transito | 200 | 0 | 1.43 m | 2.67 m | 2.35 m |
| caida radio en cruce | 200 | 0 | 2.12 m | 2.67 m | 2.35 m |
| lider seguidor nominal | 200 | 0 | 1.31 m | 2.66 m | 4.05 m |
| sin evitacion | 200 | 200 | 0.01 m | -0.04 m | 2.3 m |

La verificación en PX4 + Gazebo (autopiloto real, posición real medida por el monitor del mundo) está en `docs/evidencias/simulacion/`.
