# Electrónica propia DronSwarm (S20-S22)

Plan y estado: [PLAN.md](PLAN.md) · decisiones: ADR-015 y ADR-016 en `docs/decisiones.md`.

| Carpeta | Contenido |
|---|---|
| `requisitos/` | E0: requisitos eléctricos (generado por `calculo/requisitos.py`) |
| `calculo/` | E1 GaN vs silicio, E3 decisión del ESC del DS-I, packs de batería y cargador |
| `informes/` | Informes generados (E1, E3, E5, S20-07) |
| `skidl/` | Esquemas como código (SKIDL): `esc_ds_d`, `esc_ds_i`, `fc`, `gnss`, `bms`, `charger` + bloques y piezas propias |
| `kicad/` | Netlists, biblioteca `DronSwarm.pretty`, placas KiCad, ruteo y archivos de fabricación (ver `kicad/README.md`) |
| `fc/` | Target de PX4 `dronswarm_fmu-v1` y su documentación |
| `bom/` | E7: listas de materiales por placa y `Presupuesto_Electronica.xlsx` |
| `pruebas/` | E8: procedimientos de fabricación, banco, HITL, GNSS e integración |
| `tests/` | Pruebas de las netlists contra hojas de datos y el port de PX4 |

```bash
bash electronics/build_netlists.sh                       # esquemas → netlists (ERC)
source ~/.local/opt/kicad8/env.sh
/usr/bin/python3 electronics/kicad/gen_footprints.py      # huellas propias
/usr/bin/python3 electronics/kicad/make_boards.py         # placas desde las netlists
/usr/bin/python3 electronics/kicad/route_boards.py gnss   # ruteo automático + DRC
bash electronics/kicad/fab_outputs.sh gnss                # Gerber, taladros, posiciones, BOM
bash electronics/fc/build_px4.sh                          # firmware PX4 de la controladora
.venv/bin/python electronics/bom/gen_presupuesto.py      # presupuesto
.venv/bin/pytest -q electronics/tests
```

Herramientas locales sin sudo: KiCad 8.0.9 en `~/.local/opt/kicad8` (paquetes del PPA oficial, firma verificada),
GCC ARM 9-2020-q2 en `~/.local/opt/`, Freerouting 2.5 con JRE 25 en `~/.local/opt/`.
