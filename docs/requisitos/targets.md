# Targets de desarrollo vs benchmark DJI

- Estado: **Borrador para Gate G0** · Tarea: S02-03
- Fuentes: fichas técnicas y cotizaciones en [docs/referencias/](../referencias/) (Prizma Drones, cotizaciones 275 y 276 del 13/05/2026).
- **Mínimo** = por debajo no se libera el producto. **Objetivo** = lo que se diseña. Se miden en el sprint indicado y se registran en la hoja `Targets` del Excel.

## DS-I (inspección) vs DJI Matrice 4E

| Parámetro | M4E | Mínimo | Objetivo | Verifica |
|---|---|---|---|---|
| Precio de venta (US$, sin IGV) | 4,679 | ≤ 1,800 | **≤ 1,500** | S24 |
| BOM (US$) | — | ≤ 750 | **≤ 600** | S24 |
| MTOW (kg) | 1.42 | ≤ 3.0 | ≤ 2.5 | S04 |
| Altitud máx. de operación con carga (msnm) | 4,000 | 4,800 | **5,000** | S15 |
| Hover a 4,500 msnm (min) | 42 (nivel del mar) | 30 | **35** | S15 |
| Vuelo en avance (min) | 49 | 35 | 40 | S15 |
| Velocidad máx. (m/s) | 21 | 12 | 15 | S11 |
| Viento (m/s) | 12 | 10 | 12 | S15 |
| Temperatura (°C) | -10 a 40 | -10 a 40 | -15 a 45 | S15 |
| Protección | Sin IP | IP43 | **IP54** | S22 |
| RTK (horizontal) | 1 cm + 1 ppm | 3 cm + 1 ppm | 2 cm + 1 ppm | S15 |
| Cámara | 4/3" 20 MP + 2 tele | 1" 20 MP | 1" 20 MP, gimbal 3 ejes | S09 |
| GSD a 100 m (cm/px) | ≈ 2.7 | 3.5 | 3.0 | S15 |
| Enlace (km, sin obstáculos) | 25 (FCC) / 12 (CE) | 3 | 5 | S15 |
| Batería de repuesto (US$) | 226 | ≤ 120 | ≤ 80 | S24 |
| Ciclos de batería | 200 | 250 | 300 | S21 |

## DS-D (delivery) vs DJI Matrice 400

| Parámetro | M400 | Mínimo | Objetivo | Verifica |
|---|---|---|---|---|
| Precio de venta (US$, sin IGV) | 8,892 | ≤ 4,500 | **≤ 3,500** | S24 |
| BOM (US$) | — | ≤ 2,000 | **≤ 1,600** | S24 |
| MTOW (kg) | 15.8 | ≤ 18 | ≤ 16 | S04 |
| Carga útil a 4,500 msnm (kg) | 6 a nivel del mar (baja con altitud) | 4 | **5** | S15 |
| Hover con carga máx. a 4,500 msnm (min) | 53 (con 1.4 kg, nivel del mar) | 20 | **25** | S15 |
| Redundancia | — | Aterriza con 1 motor caído | Igual | S12 |
| Altitud máx. de operación (msnm) | 7,000 (despegue) | 4,800 | 5,000 | S15 |
| Viento (m/s) | 12 | 10 | 12 | S15 |
| Protección | IP55 | IP43 | IP54 | S22 |
| Enlace (km, sin obstáculos) | 40 (FCC) / 20 (CE) | 5 | 8 | S15 |
| Batería de repuesto (US$) | 1,634 | ≤ 400 | ≤ 300 | S24 |
| Ciclos de batería | 400 | 300 | 400 | S21 |

## Sistema (ambos)

| Parámetro | DJI | Objetivo | Verifica |
|---|---|---|---|
| Software de procesamiento | DJI Terra, US$2,085/año | OpenDroneMap, US$0 | S14 |
| Base RTK | D-RTK 3, US$2,546 | Base propia ≤ US$400 | S24 |
| Enjambre | No nativo | ≥ 6 drones, 1 operador | S16 |
| Ecosistema | Cerrado | PX4 + MAVLink abiertos | S01 |

## Por qué la altura es el diferenciador

El M4E declara 4,000 msnm como altitud máxima **con carga útil**, y el M400 aclara que su carga de 6 kg baja con la altitud. A 5,000 msnm el aire es ≈ 40 % menos denso que a nivel del mar, así que una hélice a las mismas RPM da ≈ 40 % menos empuje. Muchas operaciones peruanas están entre 3,500 y 4,800 msnm. Garantizar el desempeño **medido en la mina** es una promesa que DJI no hace.
