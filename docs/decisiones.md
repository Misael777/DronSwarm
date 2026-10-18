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
