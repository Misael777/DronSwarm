# Control de enjambre y misiones

- Todo el código habla con PX4 vía MAVSDK/MAVLink (portable: SITL → HITL → dron real).
- `swarm/` — formación, consenso, evitación, asignación de tareas.
- `missions/` — inspección y delivery.
- `mavsdk_nodes/` — servicios de la computadora a bordo.
- `tests/` — pruebas unitarias y de regresión SITL.
