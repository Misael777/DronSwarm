# DronSwarm

Proyecto mecatrónico para diseñar y fabricar drones propios de bajo costo para minería y operarlos en enjambre con control avanzado.

- **DS-I (inspección):** compite con DJI Matrice 4E. Target: ≤ US$1,500, ≥ 35 min a 4,500 msnm, IP54.
- **DS-D (delivery):** compite con DJI Matrice 400. Target: ≤ US$3,500, 5 kg a 4,500 msnm.
- **Diferenciadores:** operación a ≥ 5,000 msnm, enjambre nativo, ecosistema abierto (PX4), sin licencias.

## Probar

```bash
./dronswarm.sh        # consola de pruebas: simulaciones, CAD, plan y diagnóstico
```
Detalle en [docs/como-probar.md](docs/como-probar.md).

## Documentos clave

| Documento | Para qué |
|---|---|
| [docs/plan/DronSwarm_Plan_de_Trabajo.xlsx](docs/plan/DronSwarm_Plan_de_Trabajo.xlsx) | Seguimiento del plan (24 sprints) |
| [docs/plan/PLAN_DE_TRABAJO.md](docs/plan/PLAN_DE_TRABAJO.md) | Plan técnico detallado |
| [docs/guia-estructura-repo.md](docs/guia-estructura-repo.md) | Estructura y convenciones |
| [docs/decisiones.md](docs/decisiones.md) | Decisiones técnicas (ADR) |
| [docs/setup-wsl.md](docs/setup-wsl.md) | Instalación del entorno |

## Estructura

`engineering/` cálculos · `simulation/` PX4 + Gazebo · `control/` enjambre y misiones · `cad/` OpenSCAD + FreeCAD ·
`electronics/` · `manufacturing/` · `hardware/` · `app/` · `tools/` · `docs/`
