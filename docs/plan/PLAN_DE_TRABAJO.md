# DronSwarm · Plan de trabajo (guía para el agente)

> Generado por `tools/plan/generar_plan_trabajo.py` desde `tools/plan/plan_data.py`. No editar a mano: cambiar `plan_data.py` y regenerar.

## Cómo usar este documento

- **Fuente de verdad del progreso:** `docs/plan/DronSwarm_Plan_de_Trabajo.xlsx`, hoja `Tareas` (columnas `ID`, `Estado`, `% avance`). Leerla con pandas antes de proponer trabajo: `pd.read_excel(xlsx, sheet_name='Tareas')`.
- **Fuente de verdad del alcance:** este archivo (IDs `Sxx-yy` idénticos a los del Excel).
- Al terminar una tarea: crear el entregable en la ruta indicada, referenciar el ID en el commit (`[S03-04] modelo de motor BLDC`) y pedir al usuario que marque `Hecho` en el Excel (no sobrescribir el Excel).
- Respetar dependencias (`Depende de`). No empezar un sprint cuyo Gate previo no esté aprobado sin avisar.
- Convenciones del repo: ver `docs/guia-estructura-repo.md` (capas separadas, control vía PX4, docs en español y código en inglés, decisiones en `docs/decisiones.md`).

## Objetivo del producto

Dos drones de bajo costo para minería, operables en enjambre, con paquete de fabricación completo (planos, manuales de fabricación y ensamble, BOM, costeo incluido el motor propio, presupuestos):

- **DS-I (inspección):** compite con DJI Matrice 4E. Precio objetivo ≤ US$1,500 y BOM ≤ US$600.
- **DS-D (delivery):** compite con DJI Matrice 400. Precio objetivo ≤ US$3,500, BOM ≤ US$1,600, 5 kg a 4,500 msnm.
- **Diferenciadores:** operación garantizada a ≥ 5,000 msnm, IP54, enjambre nativo, ecosistema abierto (PX4), procesamiento sin licencias (OpenDroneMap vs DJI Terra a US$2,085/año), baterías y base RTK propias.
- **Caso de diseño:** 5,000 msnm, -15 a 45 °C, viento 12 m/s. Todo dimensionamiento se verifica en ese caso, no a nivel del mar.

## Estrategia de desarrollo

1. Definir, calcular y simular (F0-F3).
2. Diseño mecánico: el agente escribe la fuente paramétrica en OpenSCAD (`cad/openscad/`); el usuario revisa, ensambla, exporta y hace planos en FreeCAD (`cad/freecad/`). Exportar sólidos (CSG/STEP), no solo STL, para que FreeCAD pueda dibujar planos.
3. Prototipos con componentes comerciales (COTS) → software → validación de campo (F5-F7).
4. Con datos de campo se congelan las specs (Gate G4) y recién entonces se diseñan motor, electrónica y baterías propias, calidad y regulación (F8-F10). Cada componente propio debe superar al COTS (Gates G5 y G6).
5. Paquete de fabricación y comercial (F11).

## Targets (benchmark de las fichas DJI del repo)

| Parámetro | Unidad | DJI M4E | DJI M400 | Target DS-I | Target DS-D | Verifica |
|---|---|---|---|---|---|---|
| Rol en el mercado | - | Inspección / mapeo | Carga pesada / plataforma | DS-I (inspección) | DS-D (delivery) | S02 |
| Precio dron (cotización Prizma, sin IGV) | US$ | 4,679 | 8,892 | ≤ 1,500 | ≤ 3,500 | S24 |
| Precio kit completo con IGV (cotización) | US$ | 9,762 | 26,078 | ≤ 3,000 | ≤ 7,000 | S24 |
| BOM objetivo (costo de materiales) | US$ | - | - | ≤ 600 | ≤ 1,600 | S24 |
| Peso de despegue / MTOW | kg | 1.22 / 1.42 | 9.74 / 15.8 | ≤ 2.5 MTOW | ≤ 16 MTOW | S04 |
| Carga útil máxima | kg | 0.2 | 6 (a nivel del mar) | 0.5 (cámara/sensor) | ≥ 5 a 4,500 msnm | S15 |
| Altitud máxima de operación con carga | msnm | 4,000 | 7,000 (despegue) | ≥ 5,000 | ≥ 5,000 | S15 |
| Tiempo de vuelo estacionario | min | 42 | 53 (con 1.4 kg) | ≥ 35 a 4,500 msnm | ≥ 25 con 5 kg | S15 |
| Tiempo de vuelo en avance | min | 49 | 59 | ≥ 40 | ≥ 30 (sin carga) | S15 |
| Velocidad horizontal máxima | m/s | 21 | 25 | ≥ 15 | ≥ 15 | S11 |
| Resistencia al viento | m/s | 12 | 12 | ≥ 12 | ≥ 12 | S15 |
| Temperatura de operación | °C | -10 a 40 | -20 a 50 | -15 a 45 | -15 a 45 | S15 |
| Protección IP | - | Sin IP | IP55 | IP54 | IP54 | S22 |
| Precisión de posicionamiento RTK | cm | 1 + 1 ppm (H) | 1 + 1 ppm (H) | ≤ 2 + 1 ppm | ≤ 2 + 1 ppm | S15 |
| Precisión de hover sin RTK | m | ±0.5 (GNSS) | ±0.5 (GNSS) | ±0.5 | ±0.5 | S11 |
| Cámara de inspección | - | 4/3" 20 MP + 2 tele 48 MP, gimbal 3 ejes | Zenmuse P1 45 MP (opcional) | ≥ 20 MP, gimbal 3 ejes | Cámara FPV + payload | S09 |
| Detección de obstáculos | - | Visión omnidireccional + IR | Visión + LiDAR + radar mmWave | Frontal + inferior (fase 1) | Frontal + inferior + radar (fase 2) | S13 |
| Alcance del enlace (sin interferencias) | km | 25 (FCC) / 12 (CE) | 40 (FCC) / 20 (CE) | ≥ 5 | ≥ 8 | S15 |
| Latencia del video | ms | 130 | - | ≤ 200 | ≤ 200 | S14 |
| Batería: química / energía | Wh | Li-ion 4S 99.5 | Li-ion 13S 977 | Li-ion 6S ≈ 200 | Li-ion 12S ≈ 580 | S20 |
| Batería: ciclos de vida | ciclos | 200 | 400 | ≥ 300 | ≥ 400 | S21 |
| Precio de batería de repuesto | US$ | 226 | 1,634 | ≤ 80 | ≤ 300 | S24 |
| Software de procesamiento | US$/año | 2,085 (DJI Terra) | 2,085 (DJI Terra) | 0 (OpenDroneMap) | 0 (OpenDroneMap) | S14 |
| Estación RTK base | US$ | 2,546 (D-RTK 3) | 2,546 (D-RTK 3) | ≤ 400 | ≤ 400 | S24 |
| Enjambre / multi-dron | - | No nativo | No nativo | ≥ 6 drones coordinados | ≥ 6 drones coordinados | S16 |
| Ecosistema abierto | - | Cerrado (DJI) | Cerrado (DJI) | PX4 + MAVLink abierto | PX4 + MAVLink abierto | S01 |

Cotizaciones de referencia: Kit M4E (dron + 2 baterías + Terra 1 año + D-RTK 3) = USD 9,762.00 (Prizma Drones (cotiz. 275, 13/05/2026)); Kit M400 (dron + 3 baterías + BS100 + Zenmuse P1 + Terra + D-RTK 3) = USD 26,078.00 (Prizma Drones (cotiz. 276, 13/05/2026)); Kit M4E (dron + 5 baterías + D-RTK 3 + trípode + 8 pares de hélices) = USD 6,174.25 (Otro proveedor (docs/referencias/cotizaciones/cotizacion_kit_m4e.jpeg)); Capacitación en uso de dron = PEN 5,932.24 (Otro proveedor (docs/referencias/cotizaciones/cotizacion_capacitacion_dron.jpeg)).

## Resumen del plan

- 24 sprints de 14 días: 19/10/2026 → 19/09/2027.
- 151 tareas técnicas, 1284 h estimadas (capacidad supuesta: 80 h/sprint).

| Sprint | Fechas | Fase | Nombre | Horas | Gate |
|---|---|---|---|---|---|
| S01 | 19/10–01/11/26 | F0 - Fundaciones | Fundaciones del repositorio y entorno | 47 |  |
| S02 | 02/11–15/11/26 | F1 - Requisitos, targets y negocio | Requisitos cuantificados, targets y costo objetivo | 38 | G0 |
| S03 | 16/11–29/11/26 | F2 - Ingeniería de cálculo | Librería de cálculo de ingeniería (núcleo) | 55 |  |
| S04 | 30/11–13/12/26 | F2 - Ingeniería de cálculo | Dimensionamiento y optimización de costo | 60 |  |
| S05 | 14/12–27/12/26 | F3 - Simulación y validación virtual | Modelos de simulación y misiones individuales | 72 |  |
| S06 | 28/12–10/01/27 | F3 - Simulación y validación virtual | Enjambre, fallos y cierre del ciclo (PDR) | 59 | G1 |
| S07 | 11/01–24/01/27 | F4 - Diseño mecánico (OpenSCAD + FreeCAD) | Frame del dron de inspección (DS-I) | 54 |  |
| S08 | 25/01–07/02/27 | F4 - Diseño mecánico (OpenSCAD + FreeCAD) | Frame del dron de delivery (DS-D) y mecanismos | 56 |  |
| S09 | 08/02–21/02/27 | F5 - Prototipos con componentes comerciales | Selección de componentes comerciales y CDR de prototipo | 42 | G2 |
| S10 | 22/02–07/03/27 | F5 - Prototipos con componentes comerciales | Compras, banco de pruebas y fabricación de piezas | 50 |  |
| S11 | 08/03–21/03/27 | F5 - Prototipos con componentes comerciales | Prototipo DS-I: ensamble y primer vuelo | 42 |  |
| S12 | 22/03–04/04/27 | F5 - Prototipos con componentes comerciales | Prototipo DS-D y flota para enjambre | 67 | G3 |
| S13 | 05/04–18/04/27 | F6 - Software: enjambre y estación de tierra | Enjambre en hardware y misiones reales | 64 |  |
| S14 | 19/04–02/05/27 | F6 - Software: enjambre y estación de tierra | Estación de tierra (app) y procesamiento de datos | 62 |  |
| S15 | 03/05–16/05/27 | F7 - Validación de campo y specs finales | Pruebas de campo en altura | 46 |  |
| S16 | 17/05–30/05/27 | F7 - Validación de campo y specs finales | Enjambre real, confiabilidad y especificaciones finales | 55 | G4 |
| S17 | 31/05–13/06/27 | F8 - Motor propio | Motor propio: diseño electromagnético | 52 |  |
| S18 | 14/06–27/06/27 | F8 - Motor propio | Motor propio: CAD, planos y proceso de fabricación | 48 |  |
| S19 | 28/06–11/07/27 | F8 - Motor propio | Motor propio: prototipos, pruebas y decisión | 51 | G5 |
| S20 | 12/07–25/07/27 | F9 - Electrónica y baterías propias | Electrónica y baterías propias: diseño | 64 |  |
| S21 | 26/07–08/08/27 | F9 - Electrónica y baterías propias | Electrónica y baterías propias: fabricación e integración | 45 | G6 |
| S22 | 09/08–22/08/27 | F10 - Calidad y regulación | Calidad y regulación | 38 |  |
| S23 | 23/08–05/09/27 | F11 - Paquete de fabricación y comercial | Planos y manuales de fabricación y ensamble | 80 |  |
| S24 | 06/09–19/09/27 | F11 - Paquete de fabricación y comercial | BOM final, costeo y presupuestos (Release) | 37 | G7 |

## Gates de revisión

| Gate | Nombre | Sprint | Criterio de aprobación |
|---|---|---|---|
| G0 | Requisitos congelados | S02 | PRD v1.0, targets y costo objetivo aprobados; trazabilidad completa. |
| G1 | PDR – Diseño preliminar | S06 | Dimensionamiento cumple targets a 5,000 msnm; simulación de las historias de usuario y del enjambre satisfactoria (< 10 % desviación). |
| G2 | CDR – Prototipo con componentes comerciales | S09 | Frame (OpenSCAD + ensamble FreeCAD), FEA con FS ≥ 2, componentes COTS y cableado revisados; BOM de prototipo aprobado. |
| G3 | Prototipos validados en vuelo | S12 | DS-I y DS-D vuelan estables; carga 110 %; motor caído controlado; autonomía ±10 % del modelo. |
| G4 | Validación de campo y specs congeladas | S16 | Targets de prioridad Alta cumplidos en altura; enjambre de 6 en campo; specs de motor, electrónica y baterías congeladas. |
| G5 | Decisión make-vs-buy del motor | S19 | Motor propio ≥ 95 % de la eficiencia del COTS y menor costo a 100 unidades, o el producto sale con COTS. |
| G6 | Componentes propios validados | S21 | PCB, baterías y (si aplica) motor propios no peores que COTS en más de 5 % y dentro del costo objetivo. |
| G7 | Release de fabricación | S24 | Planos Rev A, manuales, ATP, BOM final, costeo, presupuestos y expediente regulatorio aprobados. |

## Sprints y tareas

### S01 · Fundaciones del repositorio y entorno

**Fase:** F0 - Fundaciones · **Objetivo:** Repo estructurado, entorno PX4 SITL + XTDrone + OpenSCAD/FreeCAD funcionando en WSL y CI básico.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S01-01 | Crear estructura del monorepo | Carpetas de la guía + cad/openscad/ (fuente) + cad/freecad/ (ensambles) + electronics/ + manufacturing/, con README por carpeta. | `README.md, */README.md` | Alta | 4 | - |
| S01-02 | Configurar .gitignore, Git LFS y ordenar documentos | LFS para PDF/STL/STEP/JPEG/FCStd. Mover fichas DJI a docs/referencias/dji/ y cotizaciones a docs/referencias/cotizaciones/. | `.gitignore, .gitattributes, docs/referencias/` | Alta | 3 | S01-01 |
| S01-03 | Definir licencia y política de propiedad intelectual | Decidir qué se publica (software) y qué es propietario (frame, motor, PCB). Registrar ADR-001. | `LICENSE, docs/decisiones.md` | Media | 3 | - |
| S01-04 | Entorno WSL2 + PX4 SITL reproducible | Script idempotente con versiones fijadas (Ubuntu/ROS/Gazebo/PX4 compatibles con XTDrone). Criterio: un dron despega y aterriza en SITL. | `tools/setup_wsl.sh, docs/setup-wsl.md` | Alta | 16 | - |
| S01-05 | Instalar XTDrone y medir capacidad del PC | Lanzar formación demo de 6 drones; registrar factor de tiempo real, CPU y RAM. Definir el máximo de drones simulables. | `docs/setup-wsl.md (sección límites)` | Alta | 8 | S01-04 |
| S01-06 | Cadena CAD OpenSCAD → FreeCAD | OpenSCAD CLI para el agente; FreeCAD (workbench OpenSCAD + Assembly) para el usuario. Pieza de prueba: .scad → CSG/STEP sólido → ensamble y plano en FreeCAD. | `tools/cad/export_scad.sh, docs/cad-flujo.md` | Alta | 6 | S01-01 |
| S01-07 | Entorno Python, linters y CI | pyproject/requirements, ruff, pytest; GitHub Actions corre lint + tests en cada push. | `.github/workflows/ci.yml` | Media | 4 | S01-01 |
| S01-08 | Registro de decisiones y limpieza del flujo | Plantilla ADR; registrar decisiones del PDF y el rol de cada CAD (OpenSCAD = fuente del agente, FreeCAD = revisión/ensamble/exportación del usuario); corregir ruta fija /home/workdir del generador del PDF. | `docs/decisiones.md, generar_flujo_drones_mineria.py` | Media | 3 | S01-01 |

### S02 · Requisitos cuantificados, targets y costo objetivo · Gate G0

**Fase:** F1 - Requisitos, targets y negocio · **Objetivo:** PRD v1.0 congelado con targets medibles frente a M4E y M400 y costo objetivo por modelo.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S02-01 | PRD: misiones y condiciones de operación cuantificadas | Inspección (ha/vuelo, GSD, autonomía) y delivery (kg, km); 3,500-5,000 msnm, -15 a 45 °C, viento 12 m/s, IP54. | `docs/requisitos/PRD.md` | Alta | 12 | - |
| S02-02 | Historias de usuario con criterios de aceptación | Formato Dado/Cuando/Entonces, prioridad MoSCoW, ligadas a misiones de taludes, fajas, relaves, post-voladura y delivery. | `docs/requisitos/historias-usuario.md` | Alta | 8 | S02-01 |
| S02-03 | Formalizar tabla de targets vs DJI | Validar la hoja Targets (M4E/M400 de las fichas del repo) y definir umbral mínimo y objetivo por parámetro. | `docs/requisitos/targets.md` | Alta | 6 | S02-01 |
| S02-04 | Costo objetivo (target costing) | Precio de venta objetivo vs cotizaciones (kit M4E US$9,762; kit M400 US$26,078) → BOM máxima por subsistema. | `docs/negocio/target_cost.md` | Alta | 6 | S02-03 |
| S02-05 | Matriz de trazabilidad requisito → verificación | Cada requisito con método (cálculo, simulación, banco, campo) y sprint de verificación. | `docs/requisitos/trazabilidad.md` | Media | 4 | S02-01 |
| S02-06 | Gate G0: congelar requisitos v1.0 | Revisión formal; cambios posteriores solo vía control de cambios. Tag git req-v1.0. | `docs/decisiones.md` | Alta | 2 | S02-05 |

### S03 · Librería de cálculo de ingeniería (núcleo)

**Fase:** F2 - Ingeniería de cálculo · **Objetivo:** Módulos Python probados para atmósfera, hélices, motores, baterías y energía de misión.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S03-01 | Modelo de atmósfera ISA con altitud y temperatura | Densidad vs altitud/temperatura; error < 0.5 % frente a tablas ISA; caso de diseño 5,000 msnm y 15 °C. | `engineering/atmosphere.py` | Alta | 4 | - |
| S03-02 | Factores de seguridad centralizados | Configuración YAML con los factores del PDF (empuje 1.8-2.5, corriente 1.3-1.5, estructura 2-3...). | `engineering/safety_factors.py` | Alta | 3 | - |
| S03-03 | Base de datos y modelo de hélices | Curvas CT/CP vs RPM (datos públicos UIUC/fabricantes), interpolación y corrección por densidad. | `engineering/propeller.py, engineering/data/propellers/` | Alta | 12 | S03-01 |
| S03-04 | Modelo de motor BLDC | Kv, Rm, I0, Kt → corriente, eficiencia y temperatura; punto de operación motor-hélice; base de datos de motores comerciales. | `engineering/motor.py, engineering/data/motors/` | Alta | 12 | S03-03 |
| S03-05 | Modelo de batería Li-ion | Energía útil, caída de voltaje, C-rate, corrección por frío y envejecimiento; packs 21700 vs LiPo. | `engineering/battery.py` | Alta | 8 | - |
| S03-06 | Energía de misión y autonomía | Perfil de misión (despegue, crucero, hover, viento, reserva) → energía y tiempo de vuelo. | `engineering/mission_loads.py` | Alta | 8 | S03-04, S03-05 |
| S03-07 | Tests y validación contra un dron conocido | pytest + notebook: el modelo reproduce un dron de referencia y eCalc con error < 10 %. | `engineering/tests/, engineering/notebooks/` | Alta | 8 | S03-06 |

### S04 · Dimensionamiento y optimización de costo

**Fase:** F2 - Ingeniería de cálculo · **Objetivo:** Especificación de DS-I y DS-D que cumple los targets al menor costo, con requisitos de motor y batería.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S04-01 | Presupuesto de masa con iteración de MTOW | Masa por subsistema; iteración hasta converger el MTOW. | `engineering/mass_budget.py` | Alta | 6 | S03-07 |
| S04-02 | Optimizador de configuración por costo | Barrido motor × hélice × celdas × batería sobre catálogo comercial; TWR ≥ 2 a 5,000 msnm, throttle de hover 45-60 %; minimiza costo y masa. | `engineering/optimizer.py` | Alta | 16 | S04-01 |
| S04-03 | Dimensionar DS-I (inspección, quad) | Requisitos de motor (empuje, Kv, potencia), hélice, ESC y batería; autonomía a 4,500 msnm vs target ≥ 35 min. | `engineering/data/results/ds-i_sizing.json` | Alta | 6 | S04-02 |
| S04-04 | Dimensionar DS-D (delivery, hexa/X8 con redundancia) | 5 kg de carga a 4,500 msnm; vuelo con motor caído; target ≥ 25 min con carga. | `engineering/data/results/ds-d_sizing.json` | Alta | 8 | S04-02 |
| S04-05 | Inercias y centro de gravedad preliminares | Modelo de masas puntuales → Ixx, Iyy, Izz y CG para el SDF. | `engineering/inertia.py` | Media | 6 | S04-03, S04-04 |
| S04-06 | Análisis estructural preliminar de brazos | Viga en voladizo, flexión, FS 2-3, frecuencia natural alejada de la frecuencia de paso de pala. | `engineering/structures.py` | Alta | 8 | S04-03 |
| S04-07 | Informe de diseño preliminar autogenerado | Informe generado desde Python con especificaciones, márgenes y comparación con los targets. | `docs/ingenieria/diseno_preliminar.md` | Alta | 4 | S04-06 |
| S04-08 | Dimensionar DS-H (carga pesada, 10 kg, octo) | Pedido del usuario (2026-10-17): un solo dron que lleve 10 kg a 4,500 msnm; 8 rotores con tolerancia a motor caído. | `engineering/data/results/ds-h_sizing.json` | Media | 6 | S04-02 |

### S05 · Modelos de simulación y misiones individuales

**Fase:** F3 - Simulación y validación virtual · **Objetivo:** DS-I y DS-D vuelan en XTDrone, en un mundo minero, con física de altura.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S05-01 | Generador de SDF desde resultados de ingeniería | Masa, inercias, CT/CQ, constantes de motor y tiempos de respuesta → SDF de DS-I y DS-D. | `tools/gen_sdf.py, simulation/xtdrone/models/` | Alta | 12 | S04-05 |
| S05-02 | Mundos de mina a tajo abierto y subterráneo | Bancos y taludes desde un DEM, faja transportadora, relavera y un túnel simple. | `simulation/xtdrone/worlds/` | Alta | 12 | - |
| S05-03 | Física de altura y viento | Densidad de 4,500 msnm en el modelo de motor; plugin de viento con ráfagas. | `simulation/xtdrone/config/` | Alta | 6 | S05-01 |
| S05-04 | Misión de inspección autónoma | Grilla fotogramétrica + órbita de talud vía MAVSDK con cámara simulada. | `control/missions/inspection.py` | Alta | 10 | S05-02 |
| S05-05 | Misión de delivery con carga | Punto a punto, carga de 5 kg, liberación en destino y retorno. | `control/missions/delivery.py` | Alta | 8 | S05-02 |
| S05-06 | Pipeline de logs ulog → métricas | pyulog + pandas: corriente, empuje, throttle y tiempo de vuelo comparados con el cálculo. | `tools/extract_xtdrone_logs.py` | Alta | 8 | S05-04 |
| S05-07 | Carga cooperativa: 3 DS-D levantan una caja de 10 kg | Pedido del usuario. Plugin de cuerdas propio (resorte-amortiguador que solo tira) y misión de subida conjunta, traslado y aterrizaje. Reparto de carga real (control cooperativo) queda para v2. | `simulation/plugins/tether/, tools/gen_coop.py, tools/sitl/demo_coop_lift.py` | Media | 16 | S05-01 |

### S06 · Enjambre, fallos y cierre del ciclo (PDR) · Gate G1

**Fase:** F3 - Simulación y validación virtual · **Objetivo:** Enjambre de 6-9 drones simulado con fallos; spec v1 congelada.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S06-01 | Enjambre en formación (6-9 drones) | Leader-follower y consenso, código portable (MAVSDK/ROS) en control/swarm/. | `control/swarm/formation.py, control/swarm/consensus.py` | Alta | 16 | S05-04 |
| S06-02 | Modelo realista de comunicaciones | Latencia, pérdida de paquetes y alcance entre drones y estación de tierra. | `simulation/common/comms_model.py` | Alta | 8 | S06-01 |
| S06-03 | Evitación de colisiones | Entre drones y contra obstáculos (campos potenciales u ORCA); 0 colisiones en 20 corridas. | `control/swarm/avoidance.py` | Alta | 12 | S06-01 |
| S06-04 | Inyección de fallos y failsafes | Motor caído (DS-D), pérdida de GNSS, batería baja, pérdida de enlace → RTL o aterrizaje seguro. | `simulation/xtdrone/scripts/fault_injection.py` | Alta | 10 | S05-05 |
| S06-05 | Cerrar ciclo cálculo ↔ simulación | Desviación < 10 % entre modelo y simulación; congelar spec v1 (envolvente de masa, empuje y energía). | `docs/ingenieria/diseno_preliminar.md (v1)` | Alta | 6 | S06-04 |
| S06-06 | Evidencia de historias de usuario simuladas | Videos y métricas por historia, para clientes e inversionistas. | `docs/evidencias/simulacion/` | Media | 4 | S06-05 |
| S06-07 | Gate G1: revisión de diseño preliminar (PDR) | Revisión formal de requisitos, dimensionamiento y simulación; acta con acciones. | `docs/revisiones/PDR.md` | Alta | 3 | S06-06 |

### S07 · Frame del dron de inspección (DS-I)

**Fase:** F4 - Diseño mecánico (OpenSCAD + FreeCAD) · **Objetivo:** Frame DS-I paramétrico en OpenSCAD, ensamblado y revisado en FreeCAD, validado por FEA.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S07-01 | Arquitectura del frame DS-I | Quad X, brazos de tubo de carbono, placas CNC, piezas PA12-CF; brazos plegables sí/no (ADR). Interfaz de motor estándar (patrón de montaje) para cambiar a motor propio después. | `docs/decisiones.md (ADR frame DS-I)` | Alta | 6 | S06-05 |
| S07-02 | Modelo paramétrico en OpenSCAD (agente) | Variables: distancia entre ejes, diámetro de tubo, bahía de batería, montaje de gimbal y de motor. Una pieza por archivo + archivo de ensamble. | `cad/openscad/inspection/` | Alta | 16 | S07-01 |
| S07-03 | Ensamble y revisión en FreeCAD (usuario) | Importar sólidos (CSG/STEP) al workbench Assembly, verificar interferencias y holguras, renders; exportar STEP del ensamble. | `cad/freecad/inspection/ds-i_ensamble.FCStd` | Alta | 6 | S07-02 |
| S07-04 | FEA y análisis modal (FreeCAD FEM / CalculiX) | Empuje máx × FS y caída de 1 m; primer modo alejado de las RPM de hover. | `cad/freecad/inspection/fea/` | Alta | 10 | S07-03 |
| S07-05 | Carcasa de electrónica IP54 y aislamiento de vibraciones | Sellos, ventilación filtrada, amortiguación de FC y cámara. | `cad/openscad/inspection/housing.scad` | Alta | 8 | S07-02 |
| S07-06 | DFM / DFA | Mínimo de piezas, un solo tipo de tornillo, impresión sin soportes, tiempo de ensamble objetivo. | `docs/ingenieria/dfm_dfa_ds-i.md` | Media | 4 | S07-03 |
| S07-07 | Exportar geometría y re-simular DS-I | STL/DAE → SDF actualizado con masas reales del CAD; repetir misión de inspección. | `cad/exports/, simulation/xtdrone/models/inspection_drone/` | Alta | 4 | S07-04 |

### S08 · Frame del dron de delivery (DS-D) y mecanismos

**Fase:** F4 - Diseño mecánico (OpenSCAD + FreeCAD) · **Objetivo:** Frame DS-D y mecanismo de carga en OpenSCAD, ensamblados en FreeCAD y listos para fabricar.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S08-01 | Frame DS-D paramétrico en OpenSCAD (agente) | Hexa o X8 coaxial según S04, brazos plegables, tren de aterrizaje, interfaz de motor estándar. | `cad/openscad/delivery/` | Alta | 16 | S06-05 |
| S08-02 | Mecanismo de carga y liberación | Servo + gancho o winch con bloqueo mecánico fail-safe; caja de carga estándar. | `cad/openscad/delivery/payload_release.scad` | Alta | 10 | S08-01 |
| S08-03 | Ensamble y revisión en FreeCAD (usuario) | Ensamble completo DS-D con mecanismo de carga; interferencias, plegado de brazos; exportar STEP. | `cad/freecad/delivery/ds-d_ensamble.FCStd` | Alta | 6 | S08-02 |
| S08-04 | FEA y análisis modal de DS-D | Carga máxima × FS y aterrizaje duro con carga. | `cad/freecad/delivery/fea/` | Alta | 8 | S08-03 |
| S08-05 | Montaje de cámara FPV y protecciones | Soporte de FPV, protección opcional de hélices y luces anticolisión. | `cad/openscad/delivery/` | Media | 4 | S08-01 |
| S08-06 | Re-validar DS-D y enjambre en simulación | Geometría real exportada; misión delivery + enjambre mixto. | `simulation/xtdrone/models/delivery_drone/` | Alta | 6 | S08-04 |
| S08-07 | Plan de fabricación de piezas | Perfiles de impresión 3D, DXF para corte CNC de carbono, servicios locales cotizados. | `manufacturing/procesos/piezas_frame.md` | Alta | 6 | S08-03 |

### S09 · Selección de componentes comerciales y CDR de prototipo · Gate G2

**Fase:** F5 - Prototipos con componentes comerciales · **Objetivo:** Prototipo definido con componentes comerciales (COTS) y liberado para compra.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S09-01 | Seleccionar motor, hélice y ESC comerciales | Desde el optimizador (S04) sobre catálogo comercial; cotizar 2 proveedores por ítem. | `docs/ingenieria/seleccion_cots.md` | Alta | 8 | S06-05 |
| S09-02 | Seleccionar aviónica comercial | Controladora estándar Pixhawk, GNSS multibanda + RTK, computadora a bordo, cámara + gimbal. | `docs/ingenieria/seleccion_cots.md` | Alta | 6 | S09-01 |
| S09-03 | Seleccionar baterías comerciales | Packs Li-ion comerciales 6S (DS-I) y 12S (DS-D) que cumplan energía y C-rate del dimensionamiento. | `docs/ingenieria/seleccion_cots.md` | Alta | 4 | S09-01 |
| S09-04 | Enlaces de radio y presupuesto de enlace | RC (ELRS), telemetría en malla para enjambre, video; alcance target ≥ 5-8 km. | `docs/ingenieria/radio_link_budget.md` | Alta | 8 | S09-02 |
| S09-05 | Diagrama de cableado del prototipo | Calibres AWG, conectores, separación GNSS-potencia (EMI), power budget. | `hardware/wiring.md` | Alta | 8 | S09-02 |
| S09-06 | BOM de prototipo y pedido de largo plazo | BOM v1 COTS con proveedores; pedir primero lo de mayor plazo de importación. | `manufacturing/bom/bom_prototipo_v1.csv` | Alta | 4 | S09-05 |
| S09-07 | Gate G2: revisión de diseño crítico del prototipo (CDR) | Frame + componentes COTS + cableado revisados; liberación para comprar y fabricar. | `docs/revisiones/CDR_prototipo.md` | Alta | 4 | S09-06 |

### S10 · Compras, banco de pruebas y fabricación de piezas

**Fase:** F5 - Prototipos con componentes comerciales · **Objetivo:** Banco de empuje operativo, motores comerciales caracterizados y piezas de frame fabricadas.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S10-01 | Órdenes de compra y seguimiento | Seguimiento de plazos y aduanas; inspección de entrada de componentes. | `manufacturing/bom/bom_prototipo_v1.csv` | Alta | 4 | S09-07 |
| S10-02 | Banco de empuje y torque | Celda de carga + HX711 + torque + RPM + V/I; adquisición en Python (o banco comercial). | `hardware/test_bench/` | Alta | 16 | - |
| S10-03 | Caracterizar motores comerciales | Kv, empuje/consumo vs throttle, g/W, temperatura en hover de 10 min; base de comparación para el motor propio. | `docs/ingenieria/motor_cots_report.md` | Alta | 10 | S10-02 |
| S10-04 | Corrección por densidad del aire | Extrapolar a 4,500-5,000 msnm; verificar margen de empuje en altura. | `docs/ingenieria/motor_cots_report.md` | Alta | 4 | S10-03 |
| S10-05 | Actualizar modelos con datos medidos | CT, CQ y constantes de motor reales en Python y en el SDF. | `engineering/data/motors/, simulation/xtdrone/models/` | Alta | 4 | S10-03 |
| S10-06 | Fabricar piezas de frame, lote 1 | Impresión 3D + corte CNC de carbono para DS-I y DS-D. | `hardware/prototipos/frames/` | Alta | 12 | S08-07 |

### S11 · Prototipo DS-I: ensamble y primer vuelo

**Fase:** F5 - Prototipos con componentes comerciales · **Objetivo:** DS-I #1 vuela estable con autotune y autonomía medida.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S11-01 | Ensamble de DS-I #1 con borrador de manual | Registrar tiempos, dificultades y mejoras para el manual de ensamble. | `manufacturing/manuales/borrador_ensamble_ds-i.md` | Alta | 12 | S10-06 |
| S11-02 | Configuración de PX4 | Airframe, geometría de actuadores, batería, failsafes y geocerca. | `hardware/px4_params/ds-i.params` | Alta | 6 | S11-01 |
| S11-03 | Calibraciones y HITL | IMU, brújula, ESC y RC; prueba HITL de misión. | `hardware/calibration.md` | Alta | 6 | S11-02 |
| S11-04 | Primer vuelo atado y análisis de vibración | Hover atado; FFT de logs; filtros notch dinámicos. | `docs/evidencias/vuelos/ds-i/` | Alta | 6 | S11-03 |
| S11-05 | Autotune y envolvente de vuelo | Ajuste PID/autotune; velocidad ≥ 15 m/s; hover ±0.5 m. | `hardware/px4_params/ds-i.params` | Alta | 8 | S11-04 |
| S11-06 | Autonomía real vs calculada | Hover hasta reserva; desviación < 10 % frente al modelo. | `docs/evidencias/vuelos/ds-i/autonomia.md` | Alta | 4 | S11-05 |

### S12 · Prototipo DS-D y flota para enjambre · Gate G3

**Fase:** F5 - Prototipos con componentes comerciales · **Objetivo:** DS-D #1 vuela con carga y la flota de prototipos del enjambre está ensamblada.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S12-01 | Ensamble de DS-D #1 | Con borrador de manual; registrar tiempos. | `manufacturing/manuales/borrador_ensamble_ds-d.md` | Alta | 14 | S10-06 |
| S12-02 | Configuración de PX4 y calibraciones de DS-D | Airframe hexa/X8, actuadores, failsafes, mecanismo de liberación. | `hardware/px4_params/ds-d.params` | Alta | 6 | S12-01 |
| S12-03 | Primer vuelo y autotune de DS-D | Hover, autotune y envolvente sin carga. | `docs/evidencias/vuelos/ds-d/` | Alta | 8 | S12-02 |
| S12-04 | Pruebas de carga progresiva | 25/50/75/100/110 % de carga y liberación en vuelo. | `docs/evidencias/vuelos/ds-d/carga.md` | Alta | 8 | S12-03 |
| S12-05 | Prueba controlada de motor caído | Corte de un motor a altura segura; aterrizaje controlado. | `docs/evidencias/vuelos/ds-d/motor_out.md` | Alta | 4 | S12-03 |
| S12-06 | Ensamblar flota para enjambre | Total de 6 unidades (mezcla DS-I/DS-D) listas para campo. | `hardware/prototipos/flota.md` | Alta | 24 | S11-06 |
| S12-07 | Gate G3: prototipos validados en vuelo | Acta con resultados vs targets y no conformidades. | `docs/revisiones/G3_prototipos.md` | Alta | 3 | S12-05 |

### S13 · Enjambre en hardware y misiones reales

**Fase:** F6 - Software: enjambre y estación de tierra · **Objetivo:** El mismo código de enjambre de simulación corre en la flota real.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S13-01 | Portar control de enjambre a hardware | Mismo código MAVSDK de simulación; secuencia SITL → HITL → real. | `control/swarm/` | Alta | 12 | S12-06 |
| S13-02 | Gestor de enjambre y asignación de tareas | Asignación (subastas o método húngaro), separación de rutas por altitud. | `control/swarm/task_allocation.py` | Alta | 16 | S13-01 |
| S13-03 | Misión de inspección real | Planificador de grilla y órbita de talud, disparo de cámara geoetiquetado con RTK. | `control/missions/inspection.py` | Alta | 12 | S13-01 |
| S13-04 | Misión de delivery real | Ruta, aproximación, liberación, confirmación y retorno. | `control/missions/delivery.py` | Alta | 8 | S13-01 |
| S13-05 | Servicios de la computadora a bordo | Telemetría, cola de comandos y watchdog; firma MAVLink 2 activada. | `control/mavsdk_nodes/` | Alta | 8 | S13-01 |
| S13-06 | Pruebas de regresión SITL en CI | Las misiones clave corren automáticamente en cada cambio. | `.github/workflows/sitl.yml` | Media | 8 | S13-03 |

### S14 · Estación de tierra (app) y procesamiento de datos

**Fase:** F6 - Software: enjambre y estación de tierra · **Objetivo:** App MVP para operar el enjambre y procesar datos sin DJI Terra.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S14-01 | Backend multi-vehículo | FastAPI + MAVSDK, telemetría por WebSocket, registro de vuelos. | `app/backend/` | Alta | 16 | S13-05 |
| S14-02 | Frontend de operador | Mapa (Leaflet/Cesium), estado de flota, baterías y alarmas. | `app/frontend/` | Alta | 16 | S14-01 |
| S14-03 | Planificación y lanzamiento de misiones de enjambre | Planificador en la UI con confirmaciones de seguridad y abortar global. | `app/frontend/, app/backend/` | Alta | 12 | S14-02 |
| S14-04 | Procesamiento con OpenDroneMap | Ortofoto, DEM, nube de puntos y volúmenes de stockpile (sustituye DJI Terra, US$2,085/año). | `app/processing/` | Alta | 12 | S13-03 |
| S14-05 | Usuarios, roles y bitácora | Autenticación, roles (piloto, supervisor) y logbook exportable. | `app/backend/` | Media | 6 | S14-01 |

### S15 · Pruebas de campo en altura

**Fase:** F7 - Validación de campo y specs finales · **Objetivo:** Targets de desempeño verificados en condiciones reales de mina.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S15-01 | Plan de pruebas de campo y permisos mínimos | Análisis de riesgos (ATS), registro MTC de los prototipos y permiso de la mina para volar; checklist. | `docs/evidencias/campo/plan.md` | Alta | 6 | S12-07 |
| S15-02 | Vuelos individuales a ≥ 3,500 msnm | TWR, throttle de hover, temperatura de motores y autonomía vs targets. | `docs/evidencias/campo/altura.md` | Alta | 12 | S15-01 |
| S15-03 | Pruebas de viento, frío y polvo | Viento ≥ 12 m/s, madrugada bajo cero, inspección de sellos después. | `docs/evidencias/campo/ambiental.md` | Alta | 8 | S15-02 |
| S15-04 | Misión de inspección real + ODM | Precisión vs puntos de control RTK; GSD vs target. | `docs/evidencias/campo/inspeccion.md` | Alta | 10 | S14-04 |
| S15-05 | Misión de delivery real con 5 kg | Carga completa en altura; tiempo de vuelo con carga vs target ≥ 25 min. | `docs/evidencias/campo/delivery.md` | Alta | 6 | S15-02 |
| S15-06 | Informe de pruebas y no conformidades | Cada target: cumple / no cumple con evidencia; lista de acciones. | `docs/evidencias/campo/informe.md` | Alta | 4 | S15-05 |

### S16 · Enjambre real, confiabilidad y especificaciones finales · Gate G4

**Fase:** F7 - Validación de campo y specs finales · **Objetivo:** Enjambre de 6 en campo y especificaciones de motor, electrónica y baterías congeladas con datos reales.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S16-01 | Enjambre real de 3 → 6 drones | Formación, evitación y asignación de tareas en campo. | `docs/evidencias/campo/enjambre.md` | Alta | 12 | S15-06 |
| S16-02 | Campaña de confiabilidad de 50 h | Horas acumuladas de vuelo, registro de fallas, MTBF preliminar, ciclos de batería. | `docs/calidad/confiabilidad.md` | Alta | 20 | S15-06 |
| S16-03 | Cambios de ingeniería del frame (ECO) | Correcciones en OpenSCAD tras campo; actualizar ensambles FreeCAD y BOM. | `docs/calidad/eco/` | Alta | 8 | S16-02 |
| S16-04 | Especificación congelada de motor | Desde logs de campo: empuje, potencia continua/pico, Kv, masa máx., temperatura, ciclo de trabajo, interfaz de montaje. | `docs/requisitos/spec_motor.md` | Alta | 6 | S16-02 |
| S16-05 | Especificación congelada de electrónica y baterías | Corrientes reales, power budget, energía y C-rate medidos, temperaturas, requisitos de BMS. | `docs/requisitos/spec_electronica_baterias.md` | Alta | 6 | S16-02 |
| S16-06 | Gate G4: validación de campo y congelamiento de specs | Targets de prioridad Alta cumplidos con COTS; specs de motor, electrónica y baterías aprobadas. | `docs/revisiones/G4_campo.md` | Alta | 3 | S16-05 |

### S17 · Motor propio: diseño electromagnético

**Fase:** F8 - Motor propio · **Objetivo:** Diseño de motor validado por cálculo y FEMM contra la spec congelada.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S17-01 | Topología y materiales | Outrunner (12N14P o 24N28P según tamaño), acero silicio 0.2 mm, imanes N52H en arco, cobre clase H; misma interfaz de montaje del COTS. | `engineering/motor_design/topologia.md` | Alta | 8 | S16-04 |
| S17-02 | Cálculo analítico del motor | Vueltas por diente, Kv, resistencia, pérdidas en cobre y hierro, densidad de corriente. | `engineering/motor_design/analytic.py` | Alta | 12 | S17-01 |
| S17-03 | Simulación electromagnética 2D (FEMM) | pyfemm: flujo, cogging, back-EMF y torque; iterar hasta cumplir la spec. | `engineering/motor_design/femm/` | Alta | 16 | S17-02 |
| S17-04 | Análisis térmico en altura | Red térmica a carga continua con aire de 5,000 msnm; T bobinado < 120 °C. | `engineering/motor_design/thermal.py` | Alta | 6 | S17-03 |
| S17-05 | Cotizar proveedores de piezas de motor | Estatores laminados, imanes, rodamientos, campanas CNC (Perú vs China) a 10/100/1000 unidades. | `manufacturing/costeo/cotizaciones_motor.md` | Alta | 6 | S17-01 |
| S17-06 | Make-vs-buy preliminar | Costo unitario propio vs motor COTS caracterizado en S10 (hoja Costo_Motor). | `manufacturing/costeo/make_vs_buy_motor.md` | Alta | 4 | S17-05 |

### S18 · Motor propio: CAD, planos y proceso de fabricación

**Fase:** F8 - Motor propio · **Objetivo:** Motor dibujado, proceso y útiles definidos, materiales pedidos.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S18-01 | CAD del motor en OpenSCAD + ensamble FreeCAD | Campana, base, eje, rodamientos y retención en OpenSCAD; ensamble y verificación de ajustes H7/g6 en FreeCAD. | `cad/openscad/motor/, cad/freecad/motor/` | Alta | 16 | S17-03 |
| S18-02 | Planos de fabricación del motor | FreeCAD TechDraw con tolerancias, GD&T básico, materiales y acabados. | `cad/freecad/motor/planos/` | Alta | 8 | S18-01 |
| S18-03 | Proceso de bobinado y útiles | Esquema de bobinado (estrella/triángulo), jig de bobinado y prensa de imanes. | `manufacturing/procesos/motor_bobinado.md` | Alta | 8 | S18-01 |
| S18-04 | Balanceo y control de calidad del motor | Procedimiento: Kv, resistencia fase-fase, hipot, vibración y balanceo del rotor. | `manufacturing/calidad/qc_motor.md` | Alta | 6 | S18-03 |
| S18-05 | Fabricar útiles de producción del motor | Jig de bobinado, prensa de pegado de imanes y soporte de balanceo. | `manufacturing/utiles/` | Alta | 8 | S18-03 |
| S18-06 | Pedido de materiales para 12 motores prototipo | Estatores, imanes, alambre, rodamientos, campanas; seguimiento de plazos. | `manufacturing/bom/motor_prototipo.csv` | Alta | 2 | S18-02 |

### S19 · Motor propio: prototipos, pruebas y decisión · Gate G5

**Fase:** F8 - Motor propio · **Objetivo:** Motores propios fabricados y comparados con el COTS; decisión de fabricar o comprar.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S19-01 | Fabricar 12 motores prototipo | Bobinado, pegado de imanes, ensamble y balanceo; registrar tiempos reales para el costeo. | `hardware/prototipos/motores/` | Alta | 24 | S18-06 |
| S19-02 | Caracterizar motores propios | Mismas pruebas que el COTS en S10: Kv, Rm, I0, empuje vs throttle, g/W, temperatura. | `docs/ingenieria/motor_test_report.md` | Alta | 12 | S19-01 |
| S19-03 | Durabilidad y vibración | 10 h de funcionamiento continuo y vibración con acelerómetro. | `docs/ingenieria/motor_test_report.md` | Alta | 6 | S19-02 |
| S19-04 | Vuelo con motores propios | Instalar en un DS-I; comparar autonomía y temperaturas vs COTS. | `docs/evidencias/vuelos/motor_propio.md` | Alta | 6 | S19-03 |
| S19-05 | Gate G5: decisión make-vs-buy del motor | ADR con datos de costo y rendimiento; si el propio no gana, el producto sale con el COTS. | `docs/decisiones.md (ADR motor)` | Alta | 3 | S19-04 |

### S20 · Electrónica y baterías propias: diseño

**Fase:** F9 - Electrónica y baterías propias · **Objetivo:** PCB, packs de batería y ESC propios diseñados contra la spec congelada; BOM dentro del target.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S20-01 | Arquitectura eléctrica de producto | Diagrama de bloques de potencia, señal y datos; qué se integra en placa propia y qué queda COTS. | `electronics/arquitectura.md` | Alta | 6 | S16-05 |
| S20-02 | Decisión de controladora de vuelo | Mantener Pixhawk estándar vs controladora propia (hardware abierto FMU); ADR con costo. | `docs/decisiones.md (ADR FC)` | Alta | 6 | S20-01 |
| S20-03 | PCB de distribución de potencia | KiCad: PDB + sensor de corriente/voltaje + BEC 5 V/12 V; reglas IPC y DRC limpio. | `electronics/kicad/pdb/` | Alta | 24 | S20-01 |
| S20-04 | Packs de batería propios 21700 + BMS | 6S (DS-I) y 12S (DS-D); BMS con balanceo y protección; proceso de soldadura por puntos. | `electronics/battery/` | Alta | 12 | S16-05 |
| S20-05 | ESC con firmware abierto (AM32) | Seleccionar o diseñar hardware compatible AM32/DShot; corriente = Imax medida × 1.3-1.5. | `electronics/esc/` | Alta | 8 | S19-05 |
| S20-06 | Design-to-cost: cerrar la brecha del BOM de DS-I | BOM preliminar ≈ US$943 vs target US$600. Palancas: FC integrada, RTK como opción, cámara, computadora a bordo opcional. | `docs/negocio/design_to_cost_ds-i.md` | Alta | 8 | S20-02 |

### S21 · Electrónica y baterías propias: fabricación e integración · Gate G6

**Fase:** F9 - Electrónica y baterías propias · **Objetivo:** Componentes propios integrados en DS-I y DS-D y validados en vuelo.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S21-01 | Fabricar y probar PCBs | Fabricación externa, ensamble y pruebas eléctricas. | `electronics/kicad/pdb/pruebas.md` | Alta | 8 | S20-03 |
| S21-02 | Fabricar packs de batería | Soldadura por puntos, BMS, caja; pruebas de capacidad y ciclos acelerados. | `electronics/battery/pruebas.md` | Alta | 12 | S20-04 |
| S21-03 | Integrar componentes propios en DS-I y DS-D | Motor (si G5 aprueba), PCB, baterías y ESC; actualizar cableado y parámetros PX4. | `hardware/px4_params/` | Alta | 12 | S21-02 |
| S21-04 | Vuelos de validación vs prototipo COTS | Autonomía, temperaturas y estabilidad; no peor que el COTS en más de 5 %. | `docs/evidencias/vuelos/componentes_propios.md` | Alta | 10 | S21-03 |
| S21-05 | Gate G6: componentes propios validados | Acta con comparación COTS vs propio y decisión por componente. | `docs/revisiones/G6_componentes.md` | Alta | 3 | S21-04 |

### S22 · Calidad y regulación

**Fase:** F10 - Calidad y regulación · **Objetivo:** Sistema de calidad básico y expediente regulatorio listos para vender.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S22-01 | FMEA de diseño y de proceso | Modos de falla, severidad, ocurrencia, detección; acciones para RPN altos. | `docs/calidad/fmea.md` | Alta | 8 | S21-05 |
| S22-02 | Plan de control de calidad | Inspección de entrada, puntos de control en proceso y registros por número de serie. | `manufacturing/calidad/plan_control.md` | Alta | 6 | S22-01 |
| S22-03 | Ensayo de protección IP54 | Prueba de polvo y salpicadura (interna o laboratorio) sobre unidad de producto. | `docs/calidad/ensayo_ip54.md` | Alta | 6 | S21-05 |
| S22-04 | Marco regulatorio MTC/DGAC | Registro, categorías por peso, BVLOS, operación de varios drones a la vez; requisitos para comercializar. | `docs/requisitos/regulacion.md` | Alta | 8 | - |
| S22-05 | Requisitos de seguridad de las minas cliente | Normas internas, permisos, seguros exigidos, homologación de equipos. | `docs/requisitos/seguridad_minera.md` | Alta | 4 | S22-04 |
| S22-06 | Expediente regulatorio y seguros | Documentación para registro, seguro de responsabilidad civil y manual de operación conforme. | `docs/requisitos/expediente_regulatorio.md` | Alta | 6 | S22-05 |

### S23 · Planos y manuales de fabricación y ensamble

**Fase:** F11 - Paquete de fabricación y comercial · **Objetivo:** Paquete técnico completo para que un tercero fabrique y ensamble el dron.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S23-01 | Planos definitivos Rev A | FreeCAD TechDraw desde los sólidos de OpenSCAD: tolerancias, materiales, acabados; control de revisiones. | `manufacturing/planos/` | Alta | 24 | S22-02 |
| S23-02 | Plano de ensamble general y explosionados | Desde los ensambles FreeCAD: vistas explosionadas con globos y lista de partes por modelo. | `manufacturing/planos/ensamble/` | Alta | 12 | S23-01 |
| S23-03 | Manual de fabricación | Piezas impresas, corte de carbono, motor (si aplica), packs de batería y PCB. | `manufacturing/manuales/fabricacion.md` | Alta | 14 | S23-01 |
| S23-04 | Manual de ensamble paso a paso | Fotos, torques, fijador de roscas y tiempos estándar por paso. | `manufacturing/manuales/ensamble.md` | Alta | 14 | S23-02 |
| S23-05 | Pruebas de aceptación de fin de línea (ATP) | Prueba funcional y de vuelo por cada dron fabricado. | `manufacturing/calidad/atp.md` | Alta | 6 | S23-04 |
| S23-06 | Manual de operación, mantenimiento y checklist | Operación del enjambre, mantenimiento preventivo, checklist de vuelo. | `docs/operacion/` | Alta | 10 | S23-04 |

### S24 · BOM final, costeo y presupuestos (Release) · Gate G7

**Fase:** F11 - Paquete de fabricación y comercial · **Objetivo:** Costos y presupuestos cerrados; release v1.0 de fabricación.

| ID | Tarea | Detalle / criterio de aceptación | Entregable | Prio | h | Depende de |
|---|---|---|---|---|---|---|
| S24-01 | BOM final multinivel | Pieza, proveedor, código, precio a 1/10/100/1000, plazo de entrega y alternativa. | `manufacturing/bom/bom_final.xlsx` | Alta | 12 | S23-01 |
| S24-02 | Costeo unitario | Materiales + mano de obra (tiempos estándar) + overhead + garantía; curva por volumen. | `manufacturing/costeo/costeo_unitario.xlsx` | Alta | 8 | S24-01 |
| S24-03 | Presupuesto de producción piloto | Lote de 10 unidades + CAPEX de taller + capital de trabajo. | `docs/negocio/presupuesto_piloto.md` | Alta | 6 | S24-02 |
| S24-04 | Precio de venta y modelos de negocio | Venta, servicio (DaaS) y suscripción vs kits DJI; punto de equilibrio. | `docs/negocio/pricing.md` | Alta | 8 | S24-02 |
| S24-05 | Gate G7: release de fabricación v1.0 | Paquete completo revisado; tag git mfg-v1.0. | `docs/revisiones/G7_release.md` | Alta | 3 | S24-04 |

## Entregables finales

- **Repositorio estructurado y entorno reproducible** (Software) → `tools/setup_wsl.sh` · tarea S01-04
- **Cadena CAD OpenSCAD → FreeCAD documentada** (CAD) → `docs/cad-flujo.md` · tarea S01-06
- **PRD / requisitos v1.0** (Informe) → `docs/requisitos/PRD.md` · tarea S02-01
- **Targets vs DJI y costo objetivo** (Informe) → `docs/negocio/target_cost.md` · tarea S02-04
- **Librería de cálculo de ingeniería** (Software) → `engineering/` · tarea S03-07
- **Informe de diseño preliminar** (Informe) → `docs/ingenieria/diseno_preliminar.md` · tarea S04-07
- **Modelos SDF y mundos de mina** (Simulación) → `simulation/xtdrone/` · tarea S05-02
- **Evidencia de simulación de historias de usuario** (Informe) → `docs/evidencias/simulacion/` · tarea S06-06
- **CAD paramétrico DS-I (OpenSCAD)** (CAD) → `cad/openscad/inspection/` · tarea S07-02
- **Ensamble DS-I en FreeCAD** (CAD) → `cad/freecad/inspection/` · tarea S07-03
- **CAD DS-D y mecanismo de carga (OpenSCAD)** (CAD) → `cad/openscad/delivery/` · tarea S08-02
- **Ensamble DS-D en FreeCAD** (CAD) → `cad/freecad/delivery/` · tarea S08-03
- **Selección de componentes comerciales** (Informe) → `docs/ingenieria/seleccion_cots.md` · tarea S09-01
- **Diagrama de cableado del prototipo** (Plano) → `hardware/wiring.md` · tarea S09-05
- **Informe de caracterización de motores COTS** (Informe) → `docs/ingenieria/motor_cots_report.md` · tarea S10-03
- **Prototipo DS-I volando** (Hardware) → `docs/evidencias/vuelos/ds-i/` · tarea S11-05
- **Prototipo DS-D volando con carga** (Hardware) → `docs/evidencias/vuelos/ds-d/` · tarea S12-04
- **Software de enjambre en hardware** (Software) → `control/swarm/` · tarea S13-01
- **Estación de tierra (app) MVP** (Software) → `app/` · tarea S14-03
- **Informe de pruebas de campo** (Informe) → `docs/evidencias/campo/informe.md` · tarea S15-06
- **Especificación congelada del motor** (Informe) → `docs/requisitos/spec_motor.md` · tarea S16-04
- **Especificación congelada de electrónica y baterías** (Informe) → `docs/requisitos/spec_electronica_baterias.md` · tarea S16-05
- **Diseño electromagnético del motor** (Informe) → `engineering/motor_design/` · tarea S17-03
- **Planos de fabricación del motor** (Plano) → `cad/freecad/motor/planos/` · tarea S18-02
- **Informe de motor propio y decisión make-vs-buy** (Informe) → `docs/ingenieria/motor_test_report.md` · tarea S19-05
- **PCB de distribución de potencia** (Electrónica) → `electronics/kicad/pdb/` · tarea S20-03
- **Packs de batería propios** (Electrónica) → `electronics/battery/` · tarea S21-02
- **FMEA** (Informe) → `docs/calidad/fmea.md` · tarea S22-01
- **Expediente regulatorio** (Informe) → `docs/requisitos/expediente_regulatorio.md` · tarea S22-06
- **Planos definitivos Rev A** (Plano) → `manufacturing/planos/` · tarea S23-01
- **Planos de ensamble y explosionados** (Plano) → `manufacturing/planos/ensamble/` · tarea S23-02
- **Manual de fabricación** (Manual) → `manufacturing/manuales/fabricacion.md` · tarea S23-03
- **Manual de ensamble** (Manual) → `manufacturing/manuales/ensamble.md` · tarea S23-04
- **Pruebas de aceptación (ATP)** (Manual) → `manufacturing/calidad/atp.md` · tarea S23-05
- **Manual de operación y mantenimiento** (Manual) → `docs/operacion/` · tarea S23-06
- **BOM final multinivel con proveedores** (BOM) → `manufacturing/bom/bom_final.xlsx` · tarea S24-01
- **Costeo unitario** (Presupuesto) → `manufacturing/costeo/costeo_unitario.xlsx` · tarea S24-02
- **Presupuesto de producción piloto** (Presupuesto) → `docs/negocio/presupuesto_piloto.md` · tarea S24-03
- **Precio de venta y modelo de negocio** (Presupuesto) → `docs/negocio/pricing.md` · tarea S24-04

## Riesgos principales

- **[20]** Pérdida de empuje en altura (aire ≈ 40 % menos denso a 5,000 msnm) → drones subdimensionados → Diseñar a 5,000 msnm desde S03; TWR ≥ 2 en altura; validar en S15 (S04)
- **[16]** Capacidad del equipo (horas) insuficiente → Comparar horas plan vs capacidad por sprint; priorizar 'Alta' (S01)
- **[15]** Restricciones regulatorias para BVLOS / enjambre → Permisos mínimos para pruebas en S15; análisis completo en S22; operar dentro de la concesión minera (S15)
- **[12]** El motor propio no alcanza el costo o la eficiencia del COTS → Gate G5 con datos; el producto sale con COTS si el propio no gana (S19)
- **[12]** Plazos de importación y aduanas retrasan prototipos → Pedido de largo plazo en S09; proveedores alternativos (S09)
- **[12]** Brecha simulación-realidad → Calibrar modelos con banco de pruebas (S10) y vuelos (S11) (S10)
- **[12]** Polvo y abrasión dañan motores y electrónica → Carcasa IP54 desde S07, rodamientos sellados, ensayo IP en S22 (S07)
- **[12]** Multitrayecto GNSS / EMI en tajos profundos → GNSS multibanda + RTK, separación EMI, failsafe de pérdida de GNSS (S09)
- **[10]** Incendio o fallo térmico de baterías Li-ion → Packs comerciales con BMS en prototipo; protocolo de carga y caja ignífuga (S09)
- **[10]** Accidente en pruebas de campo → Vuelo atado primero, zona acordonada, checklist, seguro RC (S11)
- **[9]** Motor/electrónica propios cambian masa o dimensiones y obligan a rediseñar el frame → Interfaz de montaje estándar y envolvente de masa fijadas en S07 y en la spec de S16 (S16)
- **[9]** Baja de precios de DJI o competidores chinos baratos → Diferenciar por altura, enjambre, IP y ecosistema abierto (S24)
- **[8]** Enlaces MAVLink sin cifrar (ciberseguridad) → Firma MAVLink 2, cifrado del enlace de telemetría (S13)
- **[4]** PC insuficiente para simular el enjambre → Medir en S01; reducir RTF o usar nube (S01)

## Evaluación del estado inicial

**Puntos fuertes:**

- **Visión y mercado claros:** Nicho definido (minería) con historias de usuario concretas y casos reales (Rio Tinto, Quellaveco).
- **Benchmark comercial real:** Fichas técnicas DJI M4E, M400, D-RTK 3 y Terra más cotizaciones con precios: base objetiva para fijar targets.
- **Stack 100 % abierto:** PX4, XTDrone, OpenSCAD, FreeCAD y Python: costo de licencias cero, alineado con el objetivo de bajo costo.
- **División CAD clara:** OpenSCAD es la fuente paramétrica que edita el agente (texto, versionable); FreeCAD es la herramienta del usuario para ver, ensamblar, exportar y hacer planos.
- **Control portable:** Diseñar contra PX4/MAVSDK permite pasar de simulación a hardware real sin reescribir.
- **Flujo sim-first con iteración:** Misión → simulación → cálculo → CAD → re-simulación reduce prototipos fallidos y costo.
- **Specs de componentes propios basadas en datos:** Motor, electrónica y baterías se diseñan al final, con requisitos medidos en vuelo y campo, no supuestos.
- **Factores de seguridad explícitos:** Valores numéricos definidos (empuje, corriente, estructura, batería) desde el inicio.
- **Pensado para trabajar con un agente de IA:** Monorepo, convenciones y reglas por carpeta documentadas.

**Mejoras (y dónde se atienden):**

- **No existe código ni estructura todavía:** Todo está en documentos; nada es ejecutable o verificable. → Crear estructura y entorno (S01)
- **Requisitos sin cuantificar:** No hay kg, minutos, km, msnm ni °C objetivo en el PDF; no se puede dimensionar ni verificar. → PRD + tabla de targets (S02)
- **No se considera la altitud:** A 4,500-5,000 msnm el aire es ≈ 40 % menos denso: hélices y motores dimensionados a nivel del mar fallan. → Caso de diseño a 5,000 msnm (S03)
- **Sin costo objetivo ni análisis de costos:** El objetivo es ser barato, pero no hay BOM objetivo, precio meta ni make-vs-buy. → Target costing + hojas de costos (S02)
- **Componentes propios, calidad y regulación aún sin plan detallado:** Por decisión del equipo se abordan al final, con specs medidas; el plan ya los incluye en F8-F10. → Prototipos COTS → specs → diseño propio (S16)
- **Sin plan de verificación:** No hay bancos de prueba, campañas de vuelo ni control de cambios definidos. → Fases F5 y F7 (S10)
- **Script del PDF con ruta fija:** generar_flujo_drones_mineria.py escribe en /home/workdir (no existe aquí) y nombra a otro asistente como autor. → Corregir el script (S01)
- **Archivos pesados sin control:** PDFs y JPEGs sueltos en la raíz, sin LFS ni .gitignore. → Git LFS + docs/referencias/ (S01)
- **Delivery subterráneo sin GNSS:** La historia de minas subterráneas requiere navegación sin GPS (VIO/LiDAR): gran alcance técnico. → Dejar para v2; v1 = tajo abierto (S02)

## Supuestos a validar

- Costos del BOM y del motor son estimaciones de mercado 2026 en USD; se reemplazan por cotizaciones reales (S09, S17, S24).
- Capacidad de 80 h/sprint (≈ 1 persona a tiempo completo); si el equipo es mayor, se pueden paralelizar F6 con F5 y F8 con F9.
- v1 cubre minería a tajo abierto; navegación subterránea sin GNSS queda para v2.
- La decisión de fabricar el motor se toma con datos en el Gate G5; si el propio no gana, el producto sale con el motor COTS.
