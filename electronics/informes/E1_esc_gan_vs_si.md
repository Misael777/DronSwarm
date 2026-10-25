# E1 · ESC: nitruro de galio vs silicio en nuestros motores

> Generado por `electronics/calculo/esc_perdidas.py`. No editar a mano.

Pérdidas de UN ESC (6 pasos con rectificación síncrona, como AM32) a la corriente de cada punto, más la pérdida extra en el cobre del motor por el rizado de corriente del PWM (inductancia del motor por FEM). Tensión del bus nominal.

## DS-I (×4 motores · inductancia del lazo 80 µH)

| Transistor | f PWM | Punto | Corriente | Conducción | Conmutación | C_oss | Q_rr | Tiempo muerto | Compuerta | **Pérdida ESC** | Eficiencia ESC | Rizado ΔI | Cobre por rizado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Si | 24 kHz | hover | 5.5 A | 0.11 | 0.03 | 0.01 | 0.02 | 0.04 | 0.022 | **0.23 W** | 99.7% | 2.6 A | 0.10 W |
| Si | 24 kHz | maniobra | 8.1 A | 0.25 | 0.04 | 0.01 | 0.02 | 0.06 | 0.022 | **0.40 W** | 99.7% | 1.9 A | 0.05 W |
| Si | 24 kHz | maximo | 10.6 A | 0.43 | 0.05 | 0.01 | 0.02 | 0.08 | 0.022 | **0.61 W** | 99.7% | 0.9 A | 0.01 W |
| Si | 48 kHz | hover | 5.5 A | 0.11 | 0.05 | 0.02 | 0.04 | 0.08 | 0.043 | **0.35 W** | 99.5% | 1.3 A | 0.03 W |
| Si | 48 kHz | maniobra | 8.1 A | 0.25 | 0.08 | 0.02 | 0.04 | 0.12 | 0.043 | **0.55 W** | 99.6% | 0.9 A | 0.01 W |
| Si | 48 kHz | maximo | 10.6 A | 0.43 | 0.10 | 0.02 | 0.04 | 0.16 | 0.043 | **0.79 W** | 99.6% | 0.5 A | 0.00 W |
| Si | 96 kHz | hover | 5.5 A | 0.11 | 0.10 | 0.04 | 0.07 | 0.17 | 0.086 | **0.58 W** | 99.2% | 0.7 A | 0.01 W |
| Si | 96 kHz | maniobra | 8.1 A | 0.25 | 0.15 | 0.04 | 0.07 | 0.25 | 0.086 | **0.84 W** | 99.4% | 0.5 A | 0.00 W |
| Si | 96 kHz | maximo | 10.6 A | 0.43 | 0.20 | 0.04 | 0.07 | 0.33 | 0.086 | **1.15 W** | 99.4% | 0.2 A | 0.00 W |
| GaN | 24 kHz | hover | 5.5 A | 0.14 | 0.01 | 0.01 | 0.00 | 0.01 | 0.006 | **0.18 W** | 99.7% | 2.6 A | 0.10 W |
| GaN | 24 kHz | maniobra | 8.1 A | 0.32 | 0.02 | 0.01 | 0.00 | 0.01 | 0.006 | **0.36 W** | 99.7% | 1.9 A | 0.05 W |
| GaN | 24 kHz | maximo | 10.6 A | 0.55 | 0.02 | 0.01 | 0.00 | 0.01 | 0.006 | **0.59 W** | 99.7% | 0.9 A | 0.01 W |
| GaN | 48 kHz | hover | 5.5 A | 0.14 | 0.02 | 0.01 | 0.00 | 0.02 | 0.011 | **0.21 W** | 99.7% | 1.3 A | 0.03 W |
| GaN | 48 kHz | maniobra | 8.1 A | 0.32 | 0.03 | 0.01 | 0.00 | 0.02 | 0.011 | **0.40 W** | 99.7% | 0.9 A | 0.01 W |
| GaN | 48 kHz | maximo | 10.6 A | 0.55 | 0.04 | 0.01 | 0.00 | 0.03 | 0.011 | **0.64 W** | 99.7% | 0.5 A | 0.00 W |
| GaN | 96 kHz | hover | 5.5 A | 0.14 | 0.04 | 0.03 | 0.00 | 0.03 | 0.022 | **0.27 W** | 99.6% | 0.7 A | 0.01 W |
| GaN | 96 kHz | maniobra | 8.1 A | 0.32 | 0.06 | 0.03 | 0.00 | 0.05 | 0.022 | **0.48 W** | 99.6% | 0.5 A | 0.00 W |
| GaN | 96 kHz | maximo | 10.6 A | 0.55 | 0.08 | 0.03 | 0.00 | 0.06 | 0.022 | **0.74 W** | 99.6% | 0.2 A | 0.00 W |

**Mejor frecuencia en hover:** silicio a 24 kHz (99.7%), GaN a 48 kHz (99.7%). **Ahorro en el dron: 0.4 W en hover = 0.1 % de la potencia → ≈ +0.1 % de autonomía.**

## DS-D (×6 motores · inductancia del lazo 98 µH)

| Transistor | f PWM | Punto | Corriente | Conducción | Conmutación | C_oss | Q_rr | Tiempo muerto | Compuerta | **Pérdida ESC** | Eficiencia ESC | Rizado ΔI | Cobre por rizado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Si | 24 kHz | hover | 13.7 A | 2.10 | 0.21 | 0.02 | 0.06 | 0.14 | 0.025 | **2.56 W** | 99.2% | 4.4 A | 0.21 W |
| Si | 24 kHz | maniobra | 20.5 A | 4.69 | 0.31 | 0.02 | 0.06 | 0.21 | 0.025 | **5.32 W** | 99.1% | 3.8 A | 0.16 W |
| Si | 24 kHz | maximo | 27.2 A | 8.31 | 0.42 | 0.02 | 0.06 | 0.28 | 0.025 | **9.11 W** | 99.0% | 2.9 A | 0.09 W |
| Si | 48 kHz | hover | 13.7 A | 2.10 | 0.42 | 0.04 | 0.12 | 0.28 | 0.050 | **3.02 W** | 99.0% | 2.2 A | 0.05 W |
| Si | 48 kHz | maniobra | 20.5 A | 4.69 | 0.63 | 0.04 | 0.12 | 0.42 | 0.050 | **5.95 W** | 99.0% | 1.9 A | 0.04 W |
| Si | 48 kHz | maximo | 27.2 A | 8.31 | 0.84 | 0.04 | 0.12 | 0.56 | 0.050 | **9.92 W** | 98.9% | 1.4 A | 0.02 W |
| Si | 96 kHz | hover | 13.7 A | 2.10 | 0.84 | 0.08 | 0.24 | 0.56 | 0.100 | **3.93 W** | 98.7% | 1.1 A | 0.01 W |
| Si | 96 kHz | maniobra | 20.5 A | 4.69 | 1.26 | 0.08 | 0.24 | 0.83 | 0.100 | **7.21 W** | 98.8% | 1.0 A | 0.01 W |
| Si | 96 kHz | maximo | 27.2 A | 8.31 | 1.67 | 0.08 | 0.24 | 1.11 | 0.100 | **11.52 W** | 98.8% | 0.7 A | 0.01 W |
| GaN | 24 kHz | hover | 13.7 A | 0.91 | 0.05 | 0.03 | 0.00 | 0.02 | 0.006 | **1.02 W** | 99.7% | 4.4 A | 0.21 W |
| GaN | 24 kHz | maniobra | 20.5 A | 2.03 | 0.08 | 0.03 | 0.00 | 0.03 | 0.006 | **2.18 W** | 99.6% | 3.8 A | 0.16 W |
| GaN | 24 kHz | maximo | 27.2 A | 3.61 | 0.11 | 0.03 | 0.00 | 0.04 | 0.006 | **3.79 W** | 99.6% | 2.9 A | 0.09 W |
| GaN | 48 kHz | hover | 13.7 A | 0.91 | 0.11 | 0.06 | 0.00 | 0.04 | 0.011 | **1.12 W** | 99.6% | 2.2 A | 0.05 W |
| GaN | 48 kHz | maniobra | 20.5 A | 2.03 | 0.16 | 0.06 | 0.00 | 0.06 | 0.011 | **2.32 W** | 99.6% | 1.9 A | 0.04 W |
| GaN | 48 kHz | maximo | 27.2 A | 3.61 | 0.21 | 0.06 | 0.00 | 0.08 | 0.011 | **3.96 W** | 99.6% | 1.4 A | 0.02 W |
| GaN | 96 kHz | hover | 13.7 A | 0.91 | 0.22 | 0.11 | 0.00 | 0.08 | 0.022 | **1.34 W** | 99.6% | 1.1 A | 0.01 W |
| GaN | 96 kHz | maniobra | 20.5 A | 2.03 | 0.32 | 0.11 | 0.00 | 0.12 | 0.022 | **2.61 W** | 99.6% | 1.0 A | 0.01 W |
| GaN | 96 kHz | maximo | 27.2 A | 3.61 | 0.43 | 0.11 | 0.00 | 0.16 | 0.022 | **4.32 W** | 99.5% | 0.7 A | 0.01 W |

**Mejor frecuencia en hover:** silicio a 24 kHz (99.2%), GaN a 48 kHz (99.6%). **Ahorro en el dron: 9.6 W en hover = 0.5 % de la potencia → ≈ +0.5 % de autonomía.**

## Costo de los transistores

| Dron | Silicio (6 por ESC) | GaN (6 por ESC) | Diferencia por dron |
|---|---|---|---|
| DS-I | 24 × US$0.50 = US$12 | 24 × US$4.00 = US$96 | +US$84 |
| DS-D | 36 × US$1.20 = US$43 | 36 × US$4.00 = US$144 | +US$101 |

## Conclusión

- **Con nuestros motores (poca corriente), un ESC de silicio bien diseñado ya es ~99 % eficiente en los transistores.** El GaN gana poco en energía: ≈ +0.5 % de autonomía en el DS-D y ≈ +0.1 % en el DS-I (la estimación genérica de "95 % → 98 %" incluía pérdidas que no dependen del transistor: medición de corriente, cobre de la placa, conectores y la fuente del microcontrolador).
- **El ahorro de dinero viene de fabricar el ESC propio, no del GaN**: el GaN cuesta más por transistor.
- **Lo que el GaN sí da**: menos calor (placa más chica, sin disipador, mejor a 5,000 msnm con aire poco denso), 48-96 kHz para bajar el rizado en nuestros motores de baja inductancia (calienta menos imanes y hierro: se mide en el banco) y margen para un motor más exigente en el futuro.
- **Recomendación:** DS-D con GaN (el sobrecosto es chico frente al ESC comercial de US$120 y el calor importa a 12S); DS-I: decidir en E3 entre silicio propio y el comercial (el GaN no se paga en 6S con 5 A por motor).

## Lectura

- **El silicio pierde sobre todo en la conmutación, la recuperación del diodo (Q_rr) y el tiempo muerto**; crecen con la frecuencia. Por eso los ESC de silicio se quedan en 24-48 kHz.
- **El GaN conmuta en pocos nanosegundos, no tiene Q_rr y usa tiempos muertos de ~15 ns**: puede ir a 48-96 kHz con poca pérdida, y además tiene la mitad de resistencia.
- **El rizado en nuestros motores** (baja inductancia) cae a la mitad cada vez que se duplica la frecuencia; la pérdida en el cobre que causa es chica, pero el rizado también calienta los imanes y el hierro (no modelado: se mide en el banco).
- Los datos del silicio son de la clase de transistor de los ESC comerciales; se reemplazan por la pieza real del APD 120F3 cuando se mida en el banco.

## Fuentes

- GaN: hoja de datos EPC2302 (Rds máx. 1.8 mΩ, Qg 23 nC, Qgd 2.3 nC, Qoss 85 nC, Qrr 0); V_SD en tiempo muerto ≈ 2 V a corriente de trabajo; precio estimado a 100 u.
- Silicio: valores típicos de la clase (100 V, ~3.5 mΩ, TO/PQFN 5×6); aproximados / valores típicos de la clase (40 V, ~1.2 mΩ, PQFN 3×3/5×6); aproximados
