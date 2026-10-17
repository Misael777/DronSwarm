# PRD · Especificación de requisitos del producto DronSwarm v1.0

- Estado: **Borrador para Gate G0** (aprobación del equipo pendiente)
- Fecha: 2026-10-17 · Tarea: S02-01
- Relacionados: [targets.md](targets.md) · [historias-usuario.md](historias-usuario.md) · [trazabilidad.md](trazabilidad.md) · [../negocio/target_cost.md](../negocio/target_cost.md)

## 1. Propósito

Ofrecer a operaciones mineras una flota de drones de bajo costo, operable en enjambre, que cubra inspección y transporte liviano **en altura (hasta 5,000 msnm)**, a una fracción del precio de DJI Matrice 4E y Matrice 400, sobre un ecosistema abierto (PX4) sin licencias de software.

## 2. Productos

| Código | Producto | Compite con | Rol |
|---|---|---|---|
| **DS-I** | Dron de inspección (quad) | DJI Matrice 4E | Fotogrametría, inspección visual, vigilancia |
| **DS-D** | Dron de delivery (hexa / X8) | DJI Matrice 400 | Transporte de repuestos, herramientas y muestras |
| **DS-GCS** | Estación de tierra + software | DJI Pilot 2 + DJI Terra | Operación del enjambre y procesamiento de datos |

## 3. Usuarios

| Usuario | Necesita |
|---|---|
| Piloto / operador de drones | Planificar y ejecutar misiones de varios drones a la vez con un solo operador |
| Ingeniero de geotecnia / topografía | Modelos 3D, ortofotos y volúmenes precisos y frecuentes |
| Supervisor de mantenimiento | Inspeccionar fajas, idlers e infraestructura sin detener la planta |
| Almacén / logística | Enviar repuestos y herramientas al frente sin camioneta |
| Jefe de seguridad | Menos personal expuesto; operación dentro de las reglas de la mina y del MTC |

## 4. Condiciones de operación (caso de diseño)

| Parámetro | Valor | Nota |
|---|---|---|
| Altitud de operación | 2,500 – **5,000 msnm** | Dimensionar a 5,000 msnm (densidad del aire ≈ 0.74 kg/m³ a 15 °C vs 1.225 a nivel del mar) |
| Temperatura | -15 a 45 °C | Madrugadas bajo cero en altura |
| Viento | 12 m/s sostenido, ráfagas 15 m/s | M4E y M400 declaran 12 m/s |
| Polvo / agua | **IP54** | Polvo de voladura y acarreo; lluvia ligera |
| Iluminación | Diurna | Vuelo nocturno: v2 |
| Entorno GNSS | Tajo abierto con multitrayecto en paredes | GNSS multibanda + RTK |
| Entorno radio | Interferencia media; tajos profundos con sombra de radio | Malla entre drones + relé |

## 5. Misiones (cuantificadas)

| ID | Misión | Producto | Requisito cuantificado |
|---|---|---|---|
| M1 | Levantamiento fotogramétrico de tajo y stockpiles | DS-I | ≥ 60 ha por vuelo a 100 m AGL con GSD ≤ 3 cm/px (traslapes 75/65 %) |
| M2 | Inspección de taludes y bancos | DS-I | Órbita/fachada a 30 m con GSD ≤ 1 cm/px; detección de grietas ≥ 2 cm |
| M3 | Inspección de fajas transportadoras e idlers | DS-I | ≥ 3 km de faja por vuelo, video 4K georreferenciado |
| M4 | Monitoreo de relaves | DS-I | Mapeo mensual de la presa y del espejo de agua con precisión vertical ≤ 5 cm (RTK + puntos de control) |
| M5 | Survey post-voladura | DS-I | Modelo disponible ≤ 30 min después del disparo (referencia Quellaveco: de 1.2 h a 30 min) |
| D1 | Delivery de repuestos y herramientas | DS-D | 5 kg a 3 km (ida) y retorno a 4,500 msnm con 20 % de reserva |
| D2 | Transporte de muestras geológicas | DS-D | 2-5 kg del frente al laboratorio; caja estándar sellada |
| E1 | Operación en enjambre | Ambos | 6 drones coordinados por 1 operador; división automática de área y separación por altitud |

> El cálculo de M1 es preliminar (sensor de 1", 20 MP, focal de 8.8 mm, 10 m/s, 35 min); se confirma en S04 y S15.

## 6. Requisitos funcionales

| ID | Requisito | Prioridad |
|---|---|---|
| RF-01 | Misiones autónomas de grilla, órbita y corredor planificadas desde DS-GCS | Alta |
| RF-02 | Disparo de cámara geoetiquetado con RTK (PPK opcional) | Alta |
| RF-03 | Operación de ≥ 6 drones a la vez por un solo operador | Alta |
| RF-04 | Asignación automática de tareas y separación de rutas entre drones | Alta |
| RF-05 | Evitación de colisiones entre drones y con obstáculos frontales e inferiores | Alta |
| RF-06 | Liberación de carga en vuelo con bloqueo mecánico fail-safe (DS-D) | Alta |
| RF-07 | Failsafes: batería baja, pérdida de enlace, pérdida de GNSS, motor caído (DS-D) → RTL o aterrizaje seguro | Alta |
| RF-08 | Geocerca configurable por la mina | Alta |
| RF-09 | Procesamiento de ortofoto, DEM, nube de puntos y volúmenes sin licencias (OpenDroneMap) | Alta |
| RF-10 | Bitácora de vuelos y exportación de logs por número de serie | Media |
| RF-11 | Abortar global del enjambre desde DS-GCS | Alta |
| RF-12 | Video en vivo para el operador | Media |

## 7. Requisitos no funcionales

| ID | Requisito | Valor | Prioridad |
|---|---|---|---|
| RNF-01 | Precio de venta DS-I | ≤ US$1,500 | Alta |
| RNF-02 | Precio de venta DS-D | ≤ US$3,500 | Alta |
| RNF-03 | Hover DS-I a 4,500 msnm | ≥ 35 min | Alta |
| RNF-04 | Hover DS-D con 5 kg a 4,500 msnm | ≥ 25 min | Alta |
| RNF-05 | Relación empuje/peso a 5,000 msnm | ≥ 2.0 | Alta |
| RNF-06 | Protección | IP54 | Alta |
| RNF-07 | Precisión RTK | ≤ 2 cm + 1 ppm (H) | Alta |
| RNF-08 | Alcance de enlace (sin obstáculos) | DS-I ≥ 5 km · DS-D ≥ 8 km | Media |
| RNF-09 | Tiempo de ensamble por dron (producción) | ≤ 4 h DS-I · ≤ 6 h DS-D | Media |
| RNF-10 | Ciclos de batería | ≥ 300 (DS-I) · ≥ 400 (DS-D) | Media |
| RNF-11 | Seguridad del enlace | Firma MAVLink 2 | Media |
| RNF-12 | Ecosistema | PX4 + MAVLink abiertos, sin bloqueo de proveedor | Alta |

## 8. Fuera de alcance de v1

- Navegación subterránea sin GNSS (VIO/LiDAR) → v2.
- Vuelo nocturno y cámara térmica (útil para idlers calientes) → opción v2.
- Estaciones de carga automáticas (docks) → v2.
- Detección de obstáculos omnidireccional (fase 1 cubre frontal + inferior).

## 9. Preguntas abiertas para el Gate G0

1. ¿Confirmamos **5 kg a 3 km** para DS-D o el cliente objetivo pide otra combinación?
2. ¿La cámara de DS-I debe ser fija (más barata) o intercambiable por térmica/zoom?
3. ¿El RTK es estándar o un opcional que se cobra aparte? Afecta al BOM: ver [target_cost.md](../negocio/target_cost.md).
4. ¿Mina piloto? Fija la altitud real de las pruebas de campo y quién da el permiso.
5. ¿Tamaño del equipo? El plan supone ≈ 80 h por sprint.
