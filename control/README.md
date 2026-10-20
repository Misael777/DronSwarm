# Control de enjambre y misiones

Todo habla con PX4 por MAVSDK/MAVLink: el mismo código pasa de SITL a HITL y al dron real (ADR-005, ADR-010).

| Carpeta | Contenido |
|---|---|
| `swarm/` | Formación por consenso, evitación y protocolo de pérdida de radio (`swarm.py`, S06); red del enjambre (`net.py`), nodo por dron (`node.py`), estación de tierra (`gcs.py`), asignación de tareas (`task_allocation.py`) (S13) |
| `missions/` | Inspección (grilla + órbita, disparo de cámara y geoetiquetas para ODM), entrega con liberación, levantamiento por sectores (HU-08) |
| `mavsdk_nodes/` | Servicios de la computadora a bordo: mavlink-router, systemd, watchdog |
| `tests/` | Pruebas unitarias |

## Arquitectura del enjambre en hardware (S13)

```text
  Estación de tierra (gcs.py)                         cada dron: Raspberry Pi 5
  ─ secuencia las fases de la misión          ┌──────────────────────────────────────────────┐
  ─ difunde la REF (centro, puestos,   ──REF─►│ node.py: Agent del S06 (consenso + evitación  │──MAVSDK──► PX4 (offboard
    obstáculos) a 10 Hz                       │ + protocolo de pérdida de radio)              │   por velocidad)
  ─ ABORTAR TODO (Ctrl+C) → RTL       ◄─STATE─│ difunde su STATE a 10 Hz, recibe los vecinos  │
                                              └──────────────────────────────────────────────┘
                 red del enjambre: UDP multicast (malla Wi-Fi/ESP-NOW puenteada, o LTE privada de la mina)
```

- Cada dron decide **su propia** velocidad. La tierra no controla: si se cae, los drones se detienen a los 2 s sin
  referencia y hacen RTL a los 10 s.
- Si un nodo se cuelga, el watchdog lo reinicia (PX4 queda en Hold mientras tanto) y el nodo retoma el vuelo.

## Camino SITL → HITL → real

1. **SITL distribuido:** `SCENE=swarm MODELS=ds_i,ds_i,ds_i,ds_i,ds_i,ds_i MISSION=swarm_dist bash tools/sitl/run_gz_multi.sh`.
   Son 6 procesos nodo (como las 6 Raspberry Pi) y la tierra, por el transporte local, con la radio emulada en cada receptor.
2. **HITL:** las Raspberry Pi reales corren `node.py --transport multicast` contra Pixhawk en HITL
   (`hardware/calibration.md`), en la red real del enjambre.
3. **Real:** lo mismo con los drones en vuelo. Primero 2 drones en formación amplia (≥ 10 m), luego 3 y luego 6.
