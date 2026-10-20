# Motor propio DronSwarm

Subproyecto para diseñar, simular y fabricar nuestro propio motor brushless (y evaluar un reductor) para el DS-I y el DS-D.
Plan, fases y criterios: [PLAN.md](PLAN.md) · decisión: ADR-013 en [docs/decisiones.md](../docs/decisiones.md).

## Estado

| Fase | Estado | Resultado |
|---|---|---|
| M0 · Requisitos | ✅ | [requisitos/README.md](requisitos/README.md): puntos de operación, restricciones y metas por dron |
| M1 · Referencia comercial | ✅ | [informes/M1_referencia_cots.md](informes/M1_referencia_cots.md): a superar 84.8 % (DS-I) y 87.3 % (DS-D) en hover |
| M2 · Cálculo y optimización | en curso | |
| M3-M8 | pendiente | |

## Comandos

```bash
.venv/bin/python -m motor.calculo.requirements    # M0 → requisitos/puntos_operacion.json + README
.venv/bin/python -m motor.calculo.reference       # M1 → informes/M1_referencia_cots.md
.venv/bin/pytest -q motor/tests
```

## Carpetas

- `requisitos/`: puntos de operación (generados) y `datos_cots/` (fichas y tablas de banco de los comerciales, con fuente).
- `calculo/`: Python. `materials.py` (acero eléctrico, imanes, cobre, plásticos), `requirements.py` (M0),
  `loss_model.py` y `reference.py` (M1).
- `informes/`: informes generados por fase (no editar a mano).
- `tests/`: pruebas de los cálculos.
