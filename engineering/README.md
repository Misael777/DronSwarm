# Cálculos de ingeniería (Python)

Modelos del S03 y dimensionamiento del S04. Todo se ejecuta desde la raíz del repo con `.venv/bin/python -m ...`.

| Módulo | Qué calcula | Tarea |
|---|---|---|
| `atmosphere.py` | Densidad, presión, viscosidad (ISA + temperatura real) | S03-01 |
| `safety_factors.py` + `config/` | Factores de seguridad y casos de diseño (requisitos del PRD) | S03-02 |
| `propeller.py` | Hélice por BEMT con corrección de Reynolds; acepta datos medidos (CSV) | S03-03 |
| `motor.py` | Motor BLDC por circuito equivalente; motor paramétrico para dimensionar | S03-04 |
| `battery.py` | Packs Li-ion 21700: energía útil, caída de voltaje, frío, límite de corriente | S03-05 |
| `mission_loads.py` | Potencia en hover y crucero, autonomía, misión de entrega | S03-06 |
| `validation.py` | Calibración con DJI M4E y verificación con DJI M400 | S03-07 |
| `design.py`, `mass_budget.py` | Motor para un TWR, iteración de MTOW, masas, costos y verificaciones | S04-01 |
| `optimizer.py` | Barrido hélice × paso × celdas × paralelo; elige el menor costo | S04-02 |
| `inertia.py` | Inercias y CG para el SDF de Gazebo | S04-05 |
| `structures.py` | Brazos de carbono: resistencia, deflexión, frecuencia natural | S04-06 |
| `sizing.py` | Escenarios de requisitos de DS-I y DS-D + informe | S04-03/04/07 |

```bash
.venv/bin/python -m engineering.validation     # S03-07 (≈ 4 s)
.venv/bin/python -m engineering.sizing         # S04 completo (≈ 2.5 min) → docs/ingenieria/diseno_preliminar.md
```

Para cambiar un requisito: editar `config/design_cases.yaml` y volver a correr `sizing`.
Resultados en `data/results/`. Caso de diseño: 5,000 msnm a 15 °C (empuje) y 4,500 msnm a 0 °C (autonomía).
