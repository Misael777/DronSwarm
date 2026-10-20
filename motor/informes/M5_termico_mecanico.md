# M5 · Térmico y mecánico del motor elegido

> Generado por `motor/calculo/m5.py`. No editar a mano.

Red térmica de 5 nodos con convección por correlaciones; un factor ×4.32 sobre las correlaciones reproduce los 46 °C de campana del MN4006 a fondo (tabla del fabricante). Aire de 5,000 msnm; ambiente 20 °C (y 30 °C como día caluroso).

## DS-I

| Condición | bobinado | estator | rotor/campana | aire interno | base impresa |
|---|---|---|---|---|---|
| hover_4500m_0C (permanente, 20 °C) | 30 °C | 28 °C | 23 °C | 22 °C | 25 °C |
| hover_5000m_15C (permanente, 20 °C) | 30 °C | 29 °C | 23 °C | 22 °C | 25 °C |
| hover_vacio (permanente, 20 °C) | 28 °C | 28 °C | 23 °C | 22 °C | 24 °C |
| maniobra_twr15 (permanente, 20 °C) | 39 °C | 36 °C | 25 °C | 23 °C | 29 °C |
| maximo_twr20 (permanente, 20 °C) | 51 °C | 46 °C | 27 °C | 24 °C | 34 °C |
| maniobra_twr15 (permanente, **30 °C**) | 50 °C | 47 °C | 35 °C | 33 °C | 40 °C |
| máximo 30 s desde hover | 46 °C | 41 °C | 25 °C | 23 °C | 29 °C |
| máximo **60 s** desde hover | 49 °C | 44 °C | 27 °C | 24 °C | 32 °C |

- Constante de tiempo térmica ≈ 0.2 min. Límite del bobinado: 120 °C (esmalte clase H: 200 °C).
- **Base impresa** hasta 40 °C → sirven (HDT con 15 °C de margen): **PLA, PETG, ASA, PA12-CF, PC**.

| Verificación mecánica | Valor | Factor de seguridad |
|---|---|---|
| Anillo del rotor a 6,881 rpm (sobrevelocidad 20 %) | 4.0 MPa | 52 |
| Pegado de imanes (corte, 1.5 × torque máximo) | 0.02 MPa | 615 |
| Eje Ø4 mm (torsión + giroscópico a 3 rad/s) | 97 MPa | 6.7 |
| Tapa impresa (giro + torque en el cubo) | 0.9 MPa | 25.7 |
| Rodamientos 694ZZ (4×11×4): axial 6.0 N, radial 4.3 N (atracción por 0.1 mm de excentricidad: 8.5 N) | **vida L10 107,740 h** en hover | — |
| Velocidad crítica del rotor en voladizo | 269,356 rpm | ×39 sobre la máxima |

## DS-D

| Condición | bobinado | estator | rotor/campana | aire interno | base impresa |
|---|---|---|---|---|---|
| hover_4500m_0C (permanente, 20 °C) | 38 °C | 36 °C | 25 °C | 23 °C | 31 °C |
| hover_5000m_15C (permanente, 20 °C) | 38 °C | 37 °C | 25 °C | 23 °C | 31 °C |
| hover_vacio (permanente, 20 °C) | 29 °C | 29 °C | 23 °C | 22 °C | 26 °C |
| maniobra_twr15 (permanente, 20 °C) | 59 °C | 54 °C | 29 °C | 25 °C | 42 °C |
| maximo_twr20 (permanente, 20 °C) | 96 °C | 87 °C | 37 °C | 30 °C | 62 °C |
| maniobra_twr15 (permanente, **30 °C**) | 72 °C | 68 °C | 40 °C | 36 °C | 54 °C |
| máximo 30 s desde hover | 69 °C | 60 °C | 28 °C | 26 °C | 37 °C |
| máximo **60 s** desde hover | 80 °C | 71 °C | 32 °C | 27 °C | 45 °C |

- Constante de tiempo térmica ≈ 0.3 min. Límite del bobinado: 120 °C (esmalte clase H: 200 °C).
- **Base impresa** hasta 54 °C → sirven (HDT con 15 °C de margen): **PETG, ASA, PA12-CF, PC**.

| Verificación mecánica | Valor | Factor de seguridad |
|---|---|---|
| Anillo del rotor a 4,651 rpm (sobrevelocidad 20 %) | 4.7 MPa | 44 |
| Pegado de imanes (corte, 1.5 × torque máximo) | 0.05 MPa | 308 |
| Eje Ø6 mm (torsión + giroscópico a 3 rad/s) | 182 MPa | 3.6 |
| Tapa impresa (giro + torque en el cubo) | 3.3 MPa | 7.4 |
| Rodamientos 696ZZ (6×15×5): axial 24.6 N, radial 7.7 N (atracción por 0.1 mm de excentricidad: 15.3 N) | **vida L10 28,427 h** en hover | — |
| Velocidad crítica del rotor en voladizo | 290,892 rpm | ×63 sobre la máxima |

## Conclusiones

- Las temperaturas quedan muy lejos de 120 °C incluso un minuto a empuje máximo y con día caluroso: el motor propio no necesita aluminio en la base; el límite real es el plástico de la base (ver arriba).
- Los rodamientos chicos de 694/696 alcanzan cientos a miles de horas en hover; la atracción magnética por excentricidad es la carga radial dominante: la campana y la base tienen que quedar concéntricas (útil de ensamble, M6).
- Mecánicamente todo tiene factor de seguridad ≥ 2; el más ajustado se indica en la tabla.
