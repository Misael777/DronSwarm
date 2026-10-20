# Motor propio DronSwarm

Subproyecto para diseñar, simular y fabricar nuestro propio motor brushless (y evaluar un reductor) para el DS-I y el DS-D.
Plan, fases y criterios: [PLAN.md](PLAN.md) · decisión: ADR-013 en [docs/decisiones.md](../docs/decisiones.md).

## Estado

| Fase | Estado | Resultado |
|---|---|---|
| M0 · Requisitos | ✅ | [requisitos/README.md](requisitos/README.md): puntos de operación, restricciones y metas por dron |
| M1 · Referencia comercial | ✅ | [informes/M1_referencia_cots.md](informes/M1_referencia_cots.md): a superar 84.8 % (DS-I) y 87.3 % (DS-D) en hover |
| M2 · Cálculo y optimización | ✅ | [informes/M2_diseno.md](informes/M2_diseno.md): DS-I 24N22P (+4.1 pt, +3.1 % de autonomía, US$12); DS-D 36N32P (+2.0 pt, −54 g, +5.7 %, US$32) |
| M3 · Reductores | ✅ | [informes/M3_reductores.md](informes/M3_reductores.md): gana el **directo**; los reductores hechos en casa pierden 3-25 puntos de autonomía, el armónico no es viable (ADR-014) |
| M4 · FEM 2D | siguiente | |
| M5-M8 | pendiente | |

## Comandos

```bash
.venv/bin/python -m motor.calculo.requirements    # M0 → requisitos/puntos_operacion.json + README
.venv/bin/python -m motor.calculo.reference       # M1 → informes/M1_referencia_cots.md
.venv/bin/python -m motor.calculo.optimize        # M2 → informes/M2_candidatos.json (~20 s)
.venv/bin/python -m motor.calculo.report_m2       # M2 → informes/M2_diseno.md, figuras y M2_elegidos.json
.venv/bin/python -m motor.reductores.gearbox      # M3 → informes/M3_reductores.md (~10 s)
.venv/bin/pytest -q motor/tests
```

## Carpetas

- `requisitos/`: puntos de operación (generados) y `datos_cots/` (fichas y tablas de banco de los comerciales, con fuente).
- `calculo/`: Python. `materials.py` (acero eléctrico, imanes, cobre, plásticos), `requirements.py` (M0),
  `loss_model.py` y `reference.py` (M1), `winding.py` (combinaciones ranuras/polos), `design.py` (modelo del motor),
  `optimize.py` y `report_m2.py` (M2).
- `reductores/`: `gearbox.py` (M3: directo vs planetario, cicloidal, armónico, correa).
- `informes/`: informes generados por fase (no editar a mano).
- `tests/`: pruebas de los cálculos.
