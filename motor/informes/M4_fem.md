# M4 · Verificación por elementos finitos (2D, no lineal)

> Generado por `motor/fem/analysis.py` (malla gmsh, solver Newton-Raphson propio en `motor/fem/fem2d.py`). No editar a mano.

Sección completa del motor con el hierro no lineal (curvas B-H), imanes con magnetización radial y las bobinas por diente de M2. Corriente senoidal con el mismo torque que la de 6 pasos del ESC.

**Ciclo FEM → cálculo (2 vueltas).** En la 1ª vuelta la FEM dio un Kv 3.5-5.6 % menor que el cálculo de M2 (más flujo: la fuga de 0.92 era conservadora) y la desmagnetización del DS-I quedó en 0.72 (límite 0.7; el circuito simple daba 0.52). Con eso, el DS-I no llegaba a las rpm máximas con la batería vacía. Se calibró el modelo analítico (fuga 0.96, desmagnetización ×1.5), se reconstruyeron los comerciales, se volvió a optimizar (M2) y esta es la 2ª vuelta. El optimizador pasó solo a imanes N48SH.

| Verificación | Criterio | DS-I | DS-D |
|---|---|---|---|
| Malla | — | 11,295 nodos | 14,997 nodos |
| Inducción en el entrehierro (bajo el imán) | ≈ cálculo | 0.93 T (cálculo 0.85) | 1.00 T (cálculo 0.93) |
| Estator en vacío (p95) | ≤ 1.8 T | 1.55 T | 1.66 T |
| Anillo del rotor en vacío (p95) | ≤ 1.8 T | 1.74 T | 1.71 T |
| Estator a corriente máxima (p95) | ≤ 2.0 T | 1.64 T | 1.77 T |
| **Kv** | ± 5 % del cálculo | **324** (cálculo 332, -2.4 %) | **127** (cálculo 127, +0.0 %) |
| Armónicos de la contra-FEM (3°, 5°, 7°) | informativo | 2.5% | 2.2% |
| **Cogging** pico a pico | < 5 % del torque de hover | **0.1 mN·m = 0.1 %** (período 1.15°) | **0.4 mN·m = 0.0 %** (período 1.25°) |
| Torque en hover: FEM / cálculo | 0.95-1.05 | 0.161 / 0.157 N·m = **1.03** | 1.022 / 1.028 N·m = **0.99** |
| Torque a corriente máxima: FEM / cálculo | ≥ 0.90 (saturación) | 0.311 / 0.305 N·m = **1.02** | 1.994 / 2.044 N·m = **0.98** |
| Rizado de torque a corriente máxima | informativo | 0.4 % | 1.6 % |
| **Desmagnetización** (1.5 × Imax, imanes a 100 °C) | < 0.7 de Hcj | **0.54** | **0.55** |

![campo DS-I](M4_campo_ds-i.png)

![campo DS-D](M4_campo_ds-d.png)

## Resultado

- **DS-I: cumple todas las verificaciones.**
- **DS-D: cumple todas las verificaciones.**

## Limitaciones

- 2D: sin flujo de extremo ni cabezas de bobina (con paquetes cortos, el flujo real es algo menor que el 2D: el Kv real puede salir 2-5 % más alto). Se mide en el banco (M8).
- La malla se rehace en cada posición: el cogging tiene ruido numérico del orden de 0.5 % del torque de hover.
- Desmagnetización con el criterio de la rodilla (H < 0.7·Hcj en el 99.5 % del imán), no con un modelo de histéresis.
