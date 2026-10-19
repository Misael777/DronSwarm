# Registro de decisiones técnicas (ADR)

Cada decisión relevante se registra aquí. Estados: **Propuesta** (espera aprobación del equipo), **Aceptada**, **Reemplazada**.

Plantilla:

```
## ADR-NNN · Título
- Estado: Propuesta | Aceptada | Reemplazada por ADR-XXX
- Fecha: AAAA-MM-DD
- Tarea: Sxx-yy
### Contexto
### Decisión
### Consecuencias
```

---

## ADR-001 · Licencia y propiedad intelectual
- Estado: **Propuesta** (decide el equipo)
- Fecha: 2026-10-17
- Tarea: S01-03

### Contexto
El objetivo es vender drones y competir en precio. El stack base es abierto (PX4 es BSD-3, OpenSCAD y FreeCAD son GPL/LGPL, pero eso no afecta a los diseños que hagamos con ellos). El repositorio en GitHub es privado.

### Opciones
| Opción | Ventaja | Riesgo |
|---|---|---|
| A. Todo propietario (sin licencia pública) | Protege frame, motor, PCB y software | Menos comunidad |
| B. Software abierto (Apache-2.0), hardware propietario | Atrae colaboradores al software de enjambre; protege lo que se vende | Competidores pueden usar el software |
| C. Todo abierto | Máxima visibilidad | Cualquiera puede fabricar el producto |

### Recomendación
**A ahora, revisar B en el Gate G4 (S16)**. Mientras el producto no esté validado no hay nada que ganar abriendo el código, y se puede abrir después; cerrar algo ya publicado no es posible. Hasta que se decida no se agrega archivo `LICENSE` (sin licencia = todos los derechos reservados).

### Consecuencias
- Respetar las licencias de terceros: PX4 (BSD-3) permite uso comercial; si se modifica código GPL (p. ej. XTDrone) y se distribuye, ese código debe abrirse.
- Firmware AM32 (ESC) es GPL-3: si se distribuye modificado, publicar los cambios.

---

## ADR-002 · Stack de simulación en Ubuntu 22.04
- Estado: **Propuesta** (cambia una decisión del PDF; decide el equipo)
- Fecha: 2026-10-17
- Tarea: S01-04

### Contexto
El PDF eligió XTDrone como simulador principal. XTDrone v1 está hecho para Ubuntu 18.04/20.04 con ROS 1 (Melodic/Noetic) y Gazebo Classic; la WSL del proyecto es **Ubuntu 22.04**, donde ROS 1 no existe. PX4 v1.15 instala en 22.04 **Gazebo Garden (gz-sim 7)** y soporta varios vehículos de forma nativa (una instancia de PX4 por dron, cada una con su puerto MAVLink).

### Decisión propuesta
- **Núcleo:** PX4 **v1.15.4** SITL + **Gazebo Garden (gz-sim 7)** + **MAVSDK-Python** (todo el control de enjambre en `control/`, hablando MAVLink).
- **Sin interfaz gráfica / CI:** PX4 **SIH** (simulador interno de PX4, sin Gazebo) para pruebas automáticas rápidas.
- **ROS 2 Humble** opcional (`tools/setup_wsl.sh --ros2`) solo si se usan paquetes ROS (percepción, mapas).
- **XTDrone/XTDrone2:** referencia para algoritmos de formación, no dependencia. Si se necesita XTDrone v1 tal cual, correrlo en un contenedor Docker con Ubuntu 20.04.

### Consecuencias
- Se evita mantener ROS 1 en un sistema que no lo soporta.
- El código de enjambre propio (MAVSDK) corre igual en SIH, Gazebo y dron real (principio de portabilidad del PDF).
- Hay que escribir el lanzador multi-dron (`simulation/xtdrone/launch/`), que XTDrone traía hecho.

---

## ADR-003 · Roles de las herramientas CAD
- Estado: **Aceptada** (decisión del usuario, 2026-10-17)
- Tarea: S01-06

### Decisión
- **OpenSCAD** (`cad/openscad/`): fuente paramétrica. La escribe y edita el agente; es texto y se versiona en git.
- **FreeCAD** (`cad/freecad/`): el usuario visualiza, ensambla, revisa interferencias, exporta y hace planos (TechDraw).
- Exportación: `tools/cad/export_scad.sh` genera **STEP sólido** (vía FreeCAD en línea de comandos) para FreeCAD y **STL** para simulación e impresión 3D. No usar STL para planos: una malla no tiene caras ni aristas acotables.

---

## ADR-004 · Componentes comerciales primero, componentes propios al final
- Estado: **Aceptada** (decisión del usuario, 2026-10-17)

### Decisión
Los prototipos (S09-S12) usan motores, ESC, controladora y baterías comerciales. Con datos de vuelo y campo se congelan las especificaciones (Gate G4, S16); recién entonces se diseñan motor (S17-S19), electrónica y baterías propias (S20-S21), y se abordan calidad y regulación (S22). Cada componente propio debe superar al comercial (Gates G5 y G6).

### Consecuencias
- El frame fija desde S07 una interfaz de montaje de motor estándar y una envolvente de masa para no rediseñar después.
- Para volar en campo (S15) se necesita igual el registro MTC de los prototipos y el permiso de la mina.

---

## ADR-005 · Control portable vía PX4
- Estado: **Aceptada** (del documento de flujo de trabajo)

Todo el código de control y misiones habla con PX4 por MAVLink (MAVSDK; ROS 2/px4_msgs si hace falta), nunca con APIs propias de Gazebo o Unreal.

---

## ADR-006 · Hélices comerciales
- Estado: **Aceptada** (del documento de flujo de trabajo)

Hélices comerciales con datos medidos de empuje vs RPM, seleccionadas en Python. Diseño propio (BEMT/CFD) solo si se justifica con datos.

---

## ADR-007 · Entorno Python
- Estado: **Aceptada**
- Fecha: 2026-10-17
- Tarea: S01-07

Dependencias declaradas en `pyproject.toml`; entorno en `.venv` creado con `uv`; lint con `ruff`; tests con `pytest`; CI en GitHub Actions (`.github/workflows/ci.yml`).

---

## ADR-008 · Seguimiento del plan
- Estado: **Aceptada**
- Fecha: 2026-10-17

`docs/plan/DronSwarm_Plan_de_Trabajo.xlsx` es la fuente de verdad del progreso; `docs/plan/PLAN_DE_TRABAJO.md` lo es del alcance. Ambos se generan desde `tools/plan/plan_data.py`. Al regenerar, el progreso registrado en el Excel se conserva.

---

## ADR-009 · Uso de la GPU
- Estado: **Aceptada** (pedido del usuario, 2026-10-17)

### Contexto
Laptop híbrida AMD integrada + NVIDIA RTX 3050 Ti (4 GB). OpenGL en WSL usa por defecto la AMD, y con ella Gazebo se cae al renderizar cámaras.

### Decisión
- OpenGL siempre en la NVIDIA: `MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA` (en `~/.bashrc`, `setup_wsl.sh` y `run_gz_multi.sh`).
- Cómputo CUDA (PyTorch cu124) en un entorno aparte, `~/.venvs/gpu`, para no inflar el entorno del repo; se integra al repo cuando empiece la visión artificial.
- La física de la simulación sigue en CPU; la GPU es para sensores, visión, procesamiento fotogramétrico y render.

## ADR-010 · Arquitectura del enjambre
- Estado: **Propuesta** (S06, para aprobar en el Gate G1)

### Contexto
El enjambre debe mantener formaciones, esquivar drones y obstáculos y tolerar una radio imperfecta en minas a cielo
abierto, con un control que pase sin cambios de la simulación al dron real (ADR-005).

### Decisión
- **Consenso distribuido** como control de formación: cada dron conoce la ruta de la misión, cargada antes del vuelo, y
  corrige su puesto con los estados de sus vecinos recibidos por radio. El líder-seguidor queda solo como alternativa,
  porque todo depende de un dron y su error de formación fue ~70 % mayor en la campaña Monte Carlo.
- **Evitación reactiva** sobre la orden de velocidad: repulsión por cercanía, predicción del acercamiento a 5 s con sesgo a
  la derecha (rotonda espontánea) y campo de guiado alrededor de obstáculos (sin mínimos locales).
- **Protocolo de pérdida de radio entre drones**, conocido por todos de antemano: el dron sin noticias por 0.8 s frena
  y sube 8 m a una capa reservada, y los demás esquivan su última posición conocida durante 20 s. Después actúa el
  failsafe de PX4 (RTL por pérdida de enlace).
- La estación de tierra solo secuencia las fases de la misión; no es parte del lazo de control.
- La seguridad se juzga con un árbitro independiente: en simulación, el monitor del mundo con la posición real de
  Gazebo (`simulation/plugins/safety`); en campo, RTK y logs.

### Consecuencias
- Mismo código en el simulador cinemático (Monte Carlo), en SITL (MAVSDK offboard) y, más adelante, en la computadora a bordo.
- Los parámetros están dimensionados para DS-I (3 m entre centros). Los enjambres mixtos con DS-D o DS-H necesitan
  márgenes según el tamaño de cada dron (pendiente, v2).
- La radio real debe sostener 10 Hz por dron con latencia p95 < 100 ms. Se verifica en campo en el S14.

## ADR-011 · Frame del DS-I e interfaz de motor estándar (DMI)
- Estado: **Propuesta** (S07-01, para el CDR del Gate G2)

### Contexto
El DS-I (quad X, 672 mm entre ejes, hélices de 17") necesita un frame barato, fabricable en Perú con servicios
comunes (corte CNC de carbono e impresión 3D) y preparado para cambiar al motor propio al final del proyecto (S17+).

### Decisión
- **Placas centrales de carbono de 3 mm cortadas por CNC** (Ø168 mm), separadas 26 mm por **4 bloques de brazo
  impresos en PA12-CF** que abrazan los tubos. Los tubos de los brazos son de carbono enrollado Ø20×1 mm.
- **Brazos fijos, no plegables:** el dron mide ~1.1 m con hélices y se transporta con las hélices quitadas. Plegar
  agrega bisagras, juego y ~40 g sin necesidad a este tamaño. El DS-D sí pliega (ADR-012).
- **Interfaz de motor DronSwarm (DMI):** placa con 4 ranuras radiales a 90°. DMI-S acepta 4×M3 en círculos de
  Ø16-25 mm (motores 28xx-41xx) y DMI-L acepta 4×M4 en Ø30-42 mm (50xx-70xx). Los motores COTS del S09 y el motor
  propio del S17+ deben caer en ese rango: así el frame no cambia al reemplazar el motor.
- **Tren de aterrizaje:** patas de tubo Ø12 abrazadas a los brazos (base de 300 mm entre pies) con **pies
  amortiguadores de TPU 85A** (giroide al 15 %, ~30 mm de carrera). Con un pie macizo, una caída de 1 m daba
  ~4.5 kN por pata; con el amortiguador, ~0.9 kN (FEA: abrazadera FS 3.6, tubo del brazo FS 2.2).
- **Electrónica en una carcasa IP54 impresa** sobre la placa superior: junta EPDM en canal, 8 tornillos M3 con
  arandela de nylon, prensaestopa M12 y ventila de membrana ePTFE. Batería abajo-atrás, transversal (cambio rápido
  con 2 correas); cámara adelante-abajo sobre 4 amortiguadores de silicona.
- Todo el frame es **paramétrico desde la spec v1** (`tools/cad/gen_cad_params.py`): si cambia el dimensionamiento,
  se regeneran las piezas.

### Consecuencias
- El frame pesa 52 g más que lo presupuestado en el S04 (+1.9 % del MTOW): empuje/peso 2.04 a 5,000 msnm y
  ~30.4 min de autonomía, todavía dentro del escenario D.
- Los tornillos que atraviesan la placa dentro de la carcasa necesitan arandela de nylon o sellador para el IP54.
- El PA12-CF impreso es más débil entre capas (~50 %): las piezas se orientan en la impresora según
  `docs/ingenieria/dfm_dfa_ds-i.md`.

## ADR-012 · Frame del DS-D: brazos desmontables y liberación de carga a prueba de fallas
- Estado: **Propuesta** (S08, para el CDR del Gate G2). **Se aparta del plan** (que decía "brazos plegables"): decide el usuario.

### Contexto
El DS-D (hexa, 1,453 mm entre ejes, hélices de 26") mide ~2.1 m con hélices: hay que reducirlo para
transportarlo en una camioneta. Con los empujes de diseño (FS 2.5), el momento en la raíz de cada brazo es ~138 N·m.

### Decisión
- **Brazos desmontables, no plegables, en la v1.** Cada tubo entra 54 mm en un bloque impreso (PA12-CF) entre las
  placas y se fija con 2 levas de apriete rápido. Los cables del motor llevan un conector XT60 en el bloque y el
  brazo se monta en ~20 s, sin herramientas. El primer diseño plegable, con bisagra de aluminio, pesaba 250 g por
  brazo (1.5 kg en total): 10 % del MTOW. Un plegable liviano y bien verificado queda para la v2, con datos de
  despliegue en campo.
- **Placas de carbono de 3 mm** (el S04 suponía 4 mm). El momento del brazo llega a las placas como una fuerza en
  su plano, y el aplastamiento en los agujeros M4 queda en ≈ 60 MPa.
- **Batería arriba-atrás (transversal) y carcasa IP54 arriba-adelante:** el centro de abajo queda libre para el
  mecanismo de carga, que descarga directo en la placa (la caja no cuelga de la batería).
- **Liberación a prueba de fallas:** gancho de aluminio 6061 trabado por un pasador con resorte. Sin energía queda
  trabado, y el servo solo actúa para soltar. Un micro-interruptor confirma "gancho cerrado" a la controladora.
- **Tren de esquíes** con patas inclinadas 16° (base de 440 mm entre esquíes) y zapatas de TPU.
- **Luces anticolisión** en los 6 brazos y **cámara FPV** adelante-abajo. Las protecciones de hélice no se
  diseñan en la v1: suman ~300 g y la operación en mina es lejos de personas (se revisa con la regulación, S22).

### Consecuencias
- El frame pesa 2.50 kg en CAD contra 2.65 kg presupuestados (con tornillería, ≈ presupuesto): se mantienen el
  escenario C (≥ 20 min con 5 kg) y el empuje/peso de 2.12.
- Montar el dron toma ~2 min (6 brazos), contra ~30 s de un plegable.
- El mecanismo de liberación es un concepto verificado por FEA (gancho FS 9.6): se valida con un prototipo impreso
  y ciclos de carga en el banco (S10).
