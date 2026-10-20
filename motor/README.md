# Motor propio DronSwarm

Subproyecto para diseñar, simular y fabricar nuestro propio motor brushless (y evaluar un reductor) para el DS-I y el DS-D.
Plan, fases y criterios: [PLAN.md](PLAN.md) · decisión: ADR-013 en [docs/decisiones.md](../docs/decisiones.md).

## Estado

| Fase | Estado | Resultado |
|---|---|---|
| M0 · Requisitos | ✅ | [requisitos/README.md](requisitos/README.md): puntos de operación, restricciones y metas por dron |
| M1 · Referencia comercial | ✅ | [informes/M1_referencia_cots.md](informes/M1_referencia_cots.md): modelo ajustado a la tabla del fabricante del MN4006 |
| M2 · Cálculo y optimización | ✅ | [informes/M2_diseno.md](informes/M2_diseno.md): DS-I 24N26P (+3.0 pt, +1.7 % de autonomía); DS-D 36N32P (+2.1 pt, +5.3 %) |
| M3 · Reductores | ✅ | [informes/M3_reductores.md](informes/M3_reductores.md): gana el **directo**; los reductores hechos en casa pierden 3-25 puntos de autonomía (ADR-014) |
| M4 · FEM 2D | ✅ | [informes/M4_fem.md](informes/M4_fem.md): Kv dentro de 3 %, cogging ≈ 0.1 %, sin desmagnetización (2 vueltas FEM → cálculo) |
| M5 · Térmico y mecánico | ✅ | [informes/M5_termico_mecanico.md](informes/M5_termico_mecanico.md): bobinado ≤ 51 / 96 °C a empuje máximo continuo, todo con FS ≥ 3.6 |
| M6 · Fabricación y compras | ✅ | DXF/STL en `cad/exports/motor/`, [fabricacion/README.md](fabricacion/README.md), [fabricacion/valores.md](fabricacion/valores.md) y [bom/Lista_Materiales_Motor.xlsx](bom/Lista_Materiales_Motor.xlsx): **US$24 (DS-I) y US$64 (DS-D) de material por motor** |
| M7 · Guía didáctica | ✅ | [docs/partes.html](docs/partes.html) (abrir en el navegador) |
| M8 · Prototipos y banco | pendiente (hardware) | fabricar 2 + 2, caracterizar en el banco del S10 y decidir en el Gate G5 |

## Comandos

```bash
.venv/bin/python -m motor.calculo.requirements    # M0 → requisitos/puntos_operacion.json + README
.venv/bin/python -m motor.calculo.reference       # M1 → informes/M1_referencia_cots.md
.venv/bin/python -m motor.calculo.optimize        # M2 → informes/M2_candidatos.json (~20 s)
.venv/bin/python -m motor.calculo.report_m2       # M2 → informes/M2_diseno.md, figuras y M2_elegidos.json
.venv/bin/python -m motor.reductores.gearbox      # M3 → informes/M3_reductores.md (~10 s)
bash motor/run_all.sh                               # TODO en orden (M0 → M7), ~12 min; la FEM necesita gmsh (uv pip install gmsh)
.venv/bin/pytest -q motor/tests
```

## Carpetas

- `requisitos/`: puntos de operación (generados) y `datos_cots/` (fichas y tablas de banco de los comerciales, con fuente).
- `calculo/`: Python. `materials.py` (acero eléctrico, imanes, cobre, plásticos), `requirements.py` (M0),
  `loss_model.py` y `reference.py` (M1), `winding.py` (combinaciones ranuras/polos), `design.py` (modelo del motor),
  `optimize.py` y `report_m2.py` (M2).
- `reductores/`: `gearbox.py` (M3: directo vs planetario, cicloidal, armónico, correa).
- `fem/`: `fem2d.py` (malla gmsh + solver Newton-Raphson propio) y `analysis.py` (M4).
- `calculo/m5.py`: red térmica y verificaciones mecánicas (M5).
- `fabricacion/`: `gen_cad.py` (OpenSCAD → DXF/STL), proceso y valores de control de calidad (M6).
- `bom/`: lista de compras y costo de fabricación (M6). `docs/`: guía HTML (M7).
- `informes/`: informes generados por fase (no editar a mano).
- `tests/`: pruebas de los cálculos.
