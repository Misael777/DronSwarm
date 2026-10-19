# Gate G3 · Prototipos validados en vuelo

- Sprint: S12 · Tarea: S12-07
- Estado: **Plantilla. Pendiente de los vuelos reales** (S11-S12). Se completa con los resultados de
  `docs/evidencias/vuelos/` y del banco (`docs/ingenieria/motor_cots_report.md`).

## Criterio del gate (plan)
DS-I y DS-D vuelan estables; carga al 110 %; motor caído controlado; autonomía ± 10 % del modelo.

## Resultados contra los targets

| Criterio | Objetivo | DS-I | DS-D | Evidencia | ¿Cumple? |
|---|---|---|---|---|---|
| Vuelo estable, autotune completo | sin oscilaciones; sobrepaso ≤ 15 % | | | vuelos/ds-*/README.md | |
| Vibración | métrica p95 < 15 m/s² | | | vibration.py | |
| Hover de precisión | ± 0.5 m | | | | |
| Velocidad máxima | DS-I ≥ 15 m/s · DS-D ≥ 10 m/s | | | | |
| Posición sin GNSS (flujo óptico) | ± 1 m a 3 m | | | | |
| Failsafes (RC, enlace, batería, geocerca) | RTL o aterrizaje según la tabla | | | | |
| Autonomía vs modelo | ± 10 % (potencia de hover) | | | endurance.py | |
| Carga al 110 % (DS-D) | throttle de hover ≤ 75 % | — | | vuelos/ds-d/carga.md | |
| Liberación a prueba de fallas (DS-D) | sin energía no suelta | — | | vuelos/ds-d/carga.md | |
| Motor caído (DS-D) | aterrizaje autónomo, impacto < 1.5 m/s | — | | vuelos/ds-d/motor_out.md | |
| Motores en el banco | Kv ± 5 %, potencia de hover ± 10 % del modelo | | | motor_cots_report.md | |

## No conformidades y acciones

| # | Descripción | Causa | Acción | Responsable | Estado |
|---|---|---|---|---|---|
| | | | | | |

## Resultado
_(Aprobado / Aprobado con observaciones / Rechazado; fecha; tag git `g3-v1.0`.)_
