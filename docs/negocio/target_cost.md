# Costo objetivo (target costing)

- Estado: **Borrador para Gate G0** · Tarea: S02-04
- Método: se parte del precio que el mercado acepta y se resta el margen necesario; lo que queda es el costo máximo permitido, repartido por subsistema.

## 1. Lo que el cliente paga hoy (cotizaciones del repo)

| Concepto | Monto | Fuente |
|---|---|---|
| DJI Matrice 4E (dron, garantía 2 años) | US$4,679 sin IGV | Prizma, cotiz. 275 |
| Kit M4E (dron + 2 baterías + Terra 1 año + D-RTK 3) | US$9,762 con IGV | Prizma, cotiz. 275 |
| Kit M4E alternativo (dron + 5 baterías + D-RTK 3 + trípode + hélices) | US$6,174 (sin capacitación) | `cotizacion_kit_m4e.jpeg` |
| Capacitación | S/ 5,932 ≈ US$1,580 | `cotizacion_capacitacion_dron.jpeg` |
| DJI Matrice 400 (dron, garantía 2 años) | US$8,892 sin IGV | Prizma, cotiz. 276 |
| Kit M400 (dron + 3 baterías + estación + Zenmuse P1 + Terra + D-RTK 3) | US$26,078 con IGV | Prizma, cotiz. 276 |
| DJI Terra Standard (1 año, 1 dispositivo) | US$2,085 | Ambas |

## 2. Precio objetivo y costo permitido

| | DS-I | DS-D |
|---|---|---|
| Precio de venta objetivo (sin IGV) | **US$1,500** (32 % del M4E) | **US$3,500** (39 % del M400) |
| Margen sobre BOM | 60 % | 54 % |
| **BOM máximo** (materiales) | **US$600** | **US$1,600** |
| Mano de obra + overhead + garantía (estimado) | ≈ US$150 | ≈ US$250 |

Con un kit DronSwarm de 6 drones (4 DS-I + 2 DS-D + base RTK + software) a ≈ US$13,500, el cliente paga lo mismo que **1.4 kits M4E** y recibe un enjambre.

## 3. Reparto del BOM objetivo por subsistema

| Subsistema | DS-I objetivo | DS-I estimado hoy | DS-D objetivo | DS-D estimado hoy |
|---|---|---|---|---|
| Estructura | 70 | 87 | 180 | 165 |
| Propulsión (motores, ESC, hélices) | 140 | 150 | 660 | 622 |
| Aviónica (FC, GNSS, computadora, PDB) | 150 | 355 | 340 | 355 |
| Comunicaciones | 50 | 60 | 70 | 60 |
| Carga útil | 110 | 180 | 60 | 45 |
| Energía | 60 | 85 | 260 | 225 |
| Cableado y varios | 20 | 26 | 30 | 26 |
| **Total** | **600** | **≈ 943** | **1,600** | **≈ 1,498** |

> "Estimado hoy" sale de la hoja `BOM_Costos` del Excel: precios de mercado de componentes en 2026, todavía sin cotizar.

## 4. Brecha del DS-I y cómo cerrarla

El DS-I está **≈ US$340 por encima** del objetivo; el DS-D ya entra. Las palancas, en orden de impacto:

| Palanca | Ahorro estimado | Cuándo |
|---|---|---|
| RTK como **opcional** (se cobra aparte) en vez de estándar | US$140 | Decisión G0 |
| Computadora a bordo opcional en DS-I (misiones que solo usan PX4) | US$80 | S09 |
| Controladora integrada propia (FMU + PDB en una placa) | US$60-80 | S20 |
| Cámara + gimbal de menor costo con el mismo GSD | US$40-70 | S09 |
| Compras por volumen (100 u.) | 10-15 % del total | S24 |

Con RTK opcional y computadora opcional, el DS-I base queda en ≈ US$720; con las palancas de S20 y volumen llega a ≈ US$600.

## 5. Decisiones que pide el Gate G0

1. ¿El RTK es opcional en DS-I? (Recomendado: sí; base DS-I sin RTK y versión DS-I RTK.)
2. ¿Se aceptan los precios objetivo de US$1,500 y US$3,500?
