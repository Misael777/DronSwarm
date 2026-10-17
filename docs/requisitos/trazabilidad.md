# Matriz de trazabilidad requisito → verificación

- Estado: **Borrador para Gate G0** · Tarea: S02-05
- Métodos: **C** = cálculo (engineering/), **S** = simulación, **B** = banco de pruebas, **V** = vuelo de prototipo, **F** = campo en altura, **R** = revisión documental.

| Requisito | Descripción corta | Método | Sprint(s) | Evidencia |
|---|---|---|---|---|
| RNF-05 | TWR ≥ 2 a 5,000 msnm | C → B → F | S04, S10, S15 | `docs/ingenieria/diseno_preliminar.md`, `motor_cots_report.md`, `evidencias/campo/altura.md` |
| RNF-03 | Hover DS-I ≥ 35 min a 4,500 msnm | C → S → V → F | S04, S05, S11, S15 | `evidencias/vuelos/ds-i/autonomia.md` |
| RNF-04 | Hover DS-D ≥ 25 min con 5 kg | C → S → V → F | S04, S05, S12, S15 | `evidencias/campo/delivery.md` |
| RNF-06 | IP54 | R → F → ensayo | S07, S15, S22 | `docs/calidad/ensayo_ip54.md` |
| RNF-07 | RTK ≤ 2 cm + 1 ppm | F | S15 | `evidencias/campo/inspeccion.md` |
| RNF-08 | Enlace ≥ 5 / 8 km | C → F | S09, S15 | `ingenieria/radio_link_budget.md` |
| RNF-01/02 | Precio ≤ 1,500 / 3,500 | R | S02, S20, S24 | `negocio/target_cost.md`, `negocio/pricing.md` |
| RNF-09 | Tiempo de ensamble | V (cronometrado) | S11, S12, S23 | `manufacturing/manuales/ensamble.md` |
| RNF-10 | Ciclos de batería | B | S16, S21 | `calidad/confiabilidad.md`, `electronics/battery/pruebas.md` |
| RNF-11 | Firma MAVLink 2 | S → V | S13 | `control/mavsdk_nodes/` |
| RF-01 | Misiones grilla/órbita/corredor | S → V | S05, S13 | `control/missions/` |
| RF-02 | Geoetiquetado RTK | V → F | S13, S15 | `evidencias/campo/inspeccion.md` |
| RF-03/04 | Enjambre de 6, asignación | S → F | S06, S13, S16 | `evidencias/campo/enjambre.md` |
| RF-05 | Evitación de colisiones | S → F | S06, S16 | `control/swarm/avoidance.py` + tests |
| RF-06 | Liberación de carga fail-safe | V | S12 | `evidencias/vuelos/ds-d/carga.md` |
| RF-07 | Failsafes | S → V | S06, S11, S12 | `simulation/xtdrone/scripts/fault_injection.py` |
| RF-08 | Geocerca | S → V | S11, S14 | `hardware/px4_params/` |
| RF-09 | Procesamiento ODM | F | S14, S15 | `app/processing/` |
| RF-11 | Abortar global | S → F | S14, S16 | `app/` |
| HU-01..12 | Historias de usuario | S → F | S06, S15, S16 | `evidencias/simulacion/`, `evidencias/campo/` |
