# Estructura de Repositorio y Guía para Agente IA  
## Enjambre de Drones para Minería — Simulación, Ingeniería y Fabricación

**Documento de referencia para humanos y agentes de IA**  
Stack principal: XTDrone (Gazebo + PX4 + ROS) · Python · OpenSCAD + FreeCAD · AirSim/Unreal (opcional) · PX4 real

---

## 1. Decisión de arquitectura de repos

### Recomendación: monorepo

Al inicio del proyecto se usa **un solo repositorio (monorepo)**.  
Motivos:

- Un agente de IA ve todo el contexto (cálculos, simulación, control, CAD, docs) en un solo lugar.
- Facilita versionar juntos cambios de ingeniería + simulación + control.
- Más simple de clonar y mantener en WSL.
- Evita sincronizar tags/versiones entre varios repos al principio.

**Cuándo pasar a multi-repo:** solo si el equipo crece mucho, o si `cad/` / `app/` / assets de Unreal se vuelven demasiado pesados. En ese caso el monorepo actual puede quedar como **repo central de integración** y se extraen repos satélite.

| Criterio                         | Monorepo (elegido) | Multi-repo        |
|----------------------------------|--------------------|-------------------|
| Facilidad para agente IA         | Alta               | Baja              |
| Facilidad en WSL                 | Alta               | Media             |
| Versionado conjunto              | Natural            | Hay que coordinar |
| Escalabilidad a equipo grande    | Media              | Mejor             |
| Complejidad al inicio            | Baja               | Alta              |

---

## 2. Estructura de carpetas del monorepo

```text
DronSwarm/
│
├── README.md
├── LICENSE
├── .gitignore
├── .gitattributes                 # (opcional) Git LFS para meshes
│
├── CLAUDE.md                      # guía corta para el agente (lee esto primero)
├── pyproject.toml                 # dependencias Python (entorno .venv con uv)
│
├── docs/                          # Documentación general del proyecto
│   ├── plan/                      # Plan de trabajo: Excel (seguimiento) + PLAN_DE_TRABAJO.md
│   ├── flujo/                     # PDF del flujo completo
│   ├── referencias/               # Fichas DJI y cotizaciones (benchmark)
│   ├── requisitos/                # PRD, historias, targets, trazabilidad
│   ├── negocio/                   # Costo objetivo, precios, presupuestos
│   ├── revisiones/                # Actas de Gates G0-G7
│   ├── evidencias/                # Resultados de simulación, vuelos y campo
│   ├── cad-flujo.md               # OpenSCAD → STEP → FreeCAD
│   ├── historias-usuario.md
│   ├── arquitectura.md
│   ├── decisiones.md              # ADRs / decisiones técnicas
│   ├── setup-wsl.md
│   └── glossary.md
│
├── engineering/                   # Cálculos de ingeniería (Python)
│   ├── README.md
│   ├── requirements.txt
│   ├── safety_factors.py          # Factores de seguridad centralizados
│   ├── thrust_motors.py           # Empuje, motores, hélices
│   ├── battery_sizing.py
│   ├── propeller_scaling.py
│   ├── mission_loads.py           # Cargas derivadas de misiones
│   ├── data/
│   │   ├── motors/                # Tablas / datasheets
│   │   ├── propellers/
│   │   └── results/               # Salidas de cálculos
│   ├── notebooks/                 # Jupyter de exploración
│   └── tests/
│
├── simulation/
│   ├── README.md
│   ├── xtdrone/                   # Todo lo específico de XTDrone/Gazebo
│   │   ├── models/                # SDF + meshes de drones propios
│   │   │   ├── inspection_drone/
│   │   │   └── delivery_drone/
│   │   ├── worlds/                # Mundos tipo mina
│   │   ├── launch/
│   │   ├── scripts/               # Arranque, formaciones, logs
│   │   └── config/
│   ├── airsim/                    # Settings y scripts AirSim (fase visual)
│   │   ├── settings.json
│   │   ├── scripts/
│   │   └── README.md
│   └── common/                    # Utilidades compartidas entre sims
│
├── control/                       # Algoritmos de enjambre y misiones (portable)
│   ├── README.md
│   ├── requirements.txt
│   ├── swarm/
│   │   ├── formation.py
│   │   ├── consensus.py
│   │   └── avoidance.py
│   ├── missions/
│   │   ├── inspection.py
│   │   └── delivery.py
│   ├── mavsdk_nodes/              # o paquetes ROS2
│   ├── ros2_ws/                   # (opcional) workspace ROS2 del proyecto
│   └── tests/
│
├── cad/                           # Diseño mecánico
│   ├── README.md
│   ├── openscad/                  # FUENTE paramétrica (.scad) — la edita el agente
│   │   ├── inspection/
│   │   ├── delivery/
│   │   └── motor/
│   ├── freecad/                   # Ensambles, revisión y planos (.FCStd) — los usa el usuario
│   │   ├── inspection/
│   │   ├── delivery/
│   │   └── motor/
│   ├── exports/                   # CSG/STEP (sólidos) para FreeCAD; STL, DAE, FBX para simulación
│   └── bom/                       # Lista de materiales, notas de fabricación
│
├── app/                           # App de control (fase posterior)
│   ├── README.md
│   ├── backend/
│   └── frontend/
│
├── hardware/                      # Paso a flota real
│   ├── README.md
│   ├── px4_params/
│   ├── wiring.md
│   ├── checklist_vuelo.md
│   └── calibration.md
│
├── tools/                         # Scripts de utilidad y setup
│   ├── setup_wsl.sh
│   ├── export_cad_to_sdf.py
│   ├── extract_xtdrone_logs.py
│   └── run_formation_xtdrone.sh
│
└── .github/                       # (opcional)
    └── workflows/
        └── lint-python.yml
```

---

## 3. Responsabilidad de cada carpeta (para el agente)

| Carpeta        | Qué contiene                                      | Qué puede modificar el agente                          | Qué no debe tocar a la ligera      |
|----------------|---------------------------------------------------|--------------------------------------------------------|------------------------------------|
| `docs/`        | Decisiones, arquitectura, historias de usuario    | Actualizar docs cuando cambie el diseño                | —                                  |
| `engineering/` | Cálculos Python, factores de seguridad, datos     | Fórmulas, scripts, resultados, tests                   | Borrar datasheets sin respaldo     |
| `simulation/xtdrone/` | Modelos SDF, worlds, launch, scripts        | SDF, launch, scripts de misión                         | Instalar PX4/XTDrone del sistema   |
| `simulation/airsim/`  | Settings y scripts AirSim                   | settings.json, scripts de demo                         | Binarios de Unreal                 |
| `control/`     | Enjambre, misiones, MAVSDK/ROS                    | Lógica de formación, misiones, tests                   | Parámetros PX4 de vuelo real sin revisión |
| `cad/`         | OpenSCAD (fuente) + FreeCAD (ensambles) + exports | Editar `.scad` y regenerar exports                     | Editar `.FCStd` del usuario sin aviso |
| `hardware/`    | Params PX4, checklists                            | Documentar params y procedimientos                     | Valores de seguridad de vuelo      |
| `tools/`       | Setup y utilidades                                | Mejorar scripts de automatización                      | —                                  |
| `app/`         | App de operador                                   | Backend/frontend cuando exista                         | —                                  |

---

## 4. Flujo de trabajo que el agente debe respetar

```text
1. Historias de usuario / misiones (docs/)
        ↓
2. Simulación de misiones en XTDrone (simulation/xtdrone/)
        ↓
3. Extracción de variables (empuje, corriente, tiempo de vuelo…)
        ↓
4. Cálculos de ingeniería en Python (engineering/) con factores de seguridad
        ↓
5. Diseño / ajuste CAD (cad/) e importación a XTDrone
        ↓
6. Iterar 2–5 hasta diseño estable
        ↓
7. (Opcional) AirSim + Unreal para videos y visión (simulation/airsim/)
        ↓
8. Portar control a hardware real (control/ + hardware/)
```

**Principio clave:** el código de control debe hablar con **PX4** (MAVLink / MAVSDK / ROS2 `px4_msgs`), no con Gazebo ni Unreal directamente. Así es portable entre XTDrone, AirSim y el drone real.

---

## 5. Variables de ingeniería (referencia rápida para el agente)

### 5.1 Se calculan en `engineering/` (Python)

- Peso total (MTOW)
- Empuje total requerido (con factor de seguridad 1.8–2.5 × peso)
- Empuje por motor
- Diámetro / paso de hélice
- KV y corriente de motor
- Capacidad de batería (Wh) y tiempo de vuelo
- Inercias y centro de gravedad

### 5.2 Se validan / refinan con logs de XTDrone

- Consumo real de corriente con carga
- Empuje efectivo vs peso en misión
- Estabilidad con carga descentrada
- Respuesta a viento y obstáculos
- Tiempo de vuelo bajo misión real
- Comportamiento en formación

### 5.3 Factores de seguridad por defecto

| Variable              | Factor típico      |
|-----------------------|--------------------|
| Empuje total          | 1.8 – 2.5 × peso   |
| Corriente de motor    | 1.3 – 1.5 ×        |
| Capacidad de batería  | 1.3 – 1.5 ×        |
| Estructura / brazos   | 2.0 – 3.0 ×        |
| ESC                   | 1.3 – 1.5 ×        |
| Tiempo de vuelo       | +20–30% margen     |

Hélices: prioritariamente **comerciales** + cálculo en Python. Diseño propio (BEMT) solo si se justifica.

---

## 6. Setup en WSL (Ubuntu)

### 6.1 Rutas sugeridas

```text
~/DronSwarm/                       ← monorepo (este repo)
~/PX4-Autopilot/                   ← firmware PX4 (oficial)
~/XTDrone/                         ← o XTDrone2 (según versión)
```

El monorepo **no** debe contener una copia completa de PX4 ni de Unreal. Solo:

- launch files propios
- modelos SDF / meshes propios
- scripts de arranque
- documentación de cómo lanzar

### 6.2 Pasos básicos

1. Clonar el monorepo en `~/DronSwarm`.
2. Instalar PX4 y XTDrone según su documentación oficial (fuera del monorepo).
3. Ejecutar `tools/setup_wsl.sh` (dependencias Python, MAVSDK, etc.).
4. Enlazar o copiar launch/modelos del monorepo hacia el entorno XTDrone/PX4 según `docs/setup-wsl.md`.
5. Usar Git LFS para STL/FBX pesados si hace falta.

### 6.3 `.gitignore` mínimo recomendado

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/
*.egg-info/
.pytest_cache/
.ipynb_checkpoints/

# Simulación / logs
*.bag
*.ulog
*.log
results/
simulation/**/build/

# CAD temporal
*.FCBak
*.fcstd1
cad/**/temp/

# Unreal / AirSim pesados
Binaries/
DerivedDataCache/
Intermediate/
Saved/
*.exe

# OS
.DS_Store
Thumbs.db
```

---

## 7. Convenciones para el agente de IA

1. **Leer primero:** `README.md`, `docs/arquitectura.md`, `docs/decisiones.md` y el `README.md` de la carpeta que vaya a modificar.
2. **No mezclar capas:** cálculos en `engineering/`, lógica de enjambre en `control/`, modelos de simulación en `simulation/`.
3. **Portabilidad:** cualquier nodo de control nuevo debe usar interfaces PX4 (MAVSDK/MAVROS/px4_msgs), no APIs solo de Gazebo.
4. **Documentar cambios de diseño:** si se cambia un factor de seguridad, un motor o una formación, actualizar `docs/decisiones.md` o el README de la carpeta.
5. **No borrar datos de ingeniería** (`engineering/data/`) sin confirmación.
6. **CAD:** la fuente paramétrica es OpenSCAD (`cad/openscad/`) y la edita el agente. FreeCAD (`cad/freecad/`) es la herramienta del usuario para ver, ensamblar, exportar y hacer planos. El agente regenera los exports (CSG/STEP sólidos para FreeCAD, STL/DAE para simulación) y no sobrescribe `.FCStd` sin avisar.
7. **Tests:** añadir o actualizar tests en `engineering/tests/` y `control/tests/` cuando se cambie lógica crítica.
8. **Un solo idioma de docs técnicas:** español (o el que defina el equipo); código y nombres de variables en inglés.

---

## 8. Stack de referencia (no sustituir sin decisión explícita)

| Rol                         | Herramienta principal        |
|----------------------------|------------------------------|
| Simulación control/enjambre| XTDrone (Gazebo + PX4 + ROS) |
| Cálculos de ingeniería     | Python (NumPy, SciPy)        |
| Diseño mecánico (fuente)   | OpenSCAD (lo edita el agente) |
| Ensamble, revisión, planos | FreeCAD (lo usa el usuario)   |
| Visual / visión / demos    | AirSim + Unreal (opcional)   |
| Autopiloto                 | PX4                          |
| Comunicación control       | MAVLink / MAVSDK / ROS2      |
| App operador               | A definir (Flutter / web)    |

Complementos útiles y gratuitos: **eCalc** (selección rápida de motores/hélices), **QGroundControl** (telemetría y params).

---

## 9. Resumen ejecutivo para el agente

- Trabajar siempre sobre el **monorepo** `DronSwarm`.
- Respetar el flujo: misión → XTDrone → variables → Python → CAD → iterar → (AirSim) → hardware.
- Control portable vía PX4.
- Ingeniería en `engineering/` con factores de seguridad.
- Simulación XTDrone en `simulation/xtdrone/`.
- No instalar PX4/Unreal dentro del repo; solo configs y modelos propios.
- Documentar decisiones relevantes en `docs/`.

Este documento es la guía de estructura y convenciones del proyecto. Cualquier cambio de arquitectura de carpetas o de stack debe registrarse en `docs/decisiones.md`.
