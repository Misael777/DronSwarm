# Evidencia de simulación por historia de usuario

> Generado por `tools/evidence_report.py` el 2026-10-19 a partir de los resultados guardados en `docs/evidencias/`. No editar a mano.

Todo esto es **simulación**: PX4 real (el mismo autopiloto que volará) con drones modelados desde el dimensionamiento, en Gazebo. Las colisiones las mide un monitor del mundo con la posición real de cada dron, no el código que se prueba. Lo que la simulación no puede probar (cámara real, radio real, motores reales) se valida en los prototipos (S10-S16).

## Matriz por historia

| Historia | Prueba | Resultado medido | Criterio | Estado |
|---|---|---|---|---|
| HU-01 | Grilla fotogramétrica sobre el tajo (DS-I, mina simulada, S05) | 55 fotos, error medio de posición 0.7 m, grilla en 277 s | GSD ≤ 3 cm/px; ortofoto ≤ 5 cm (la ortofoto se valida con ODM en campo) | ✅ vuelo · ODM pendiente (S13) |
| HU-02 | Órbita de talud dentro del tajo (DS-I, S05) | bajó a 15 m bajo el borde | GSD ≤ 1 cm/px a 30 m de la fachada | 🟡 parcial: falta misión de fachada |
| HU-06 | Entrega de 5 kg al fondo del tajo con liberación (DS-D, S05) | caja liberada a 0.09 m del objetivo | entrega + liberación + regreso; 3 km con ≥ 20 % de batería | ✅ en simulación; 3 km verificado por cálculo (+114 % de margen) |
| (pedido) | Carga cooperativa: 3 DS-D levantan 10 kg (S05) | caja a 3.37 m, trasladada 15.7 m | levantar, trasladar y aterrizar | ✅ vista previa (reparto de carga: v2) |
| HU-08 | 6 DS-I levantan un área por sectores y 'abortar todo' (PX4 + Gazebo) | sectores asignados, capas 30-80 m, separación mínima 3D 11.77 m, todos en casa 107.2 s después de abortar | sectores, altitudes separadas, nunca < 10 m, abortar con un botón | ✅ cumple |
| HU-08 | Enjambre de 6 en formación cerrada: V, torre, círculo, cruce, regreso (PX4 + Gazebo, 20 corridas) | 0 corridas con colisión; separación mínima 2.23 m; torre a 3.11 m | 0 colisiones en 20 corridas (S06-03) | ✅ cumple |
| HU-08 | Simulador rápido: 1600 corridas en 8 condiciones (radio con 30-50 % de pérdida, caída de radio, viento) | 0 corridas con colisión; separación mínima 1.31 m | 0 colisiones | ✅ cumple |
| HU-09 | Motor caído en DS-D con detección (ESC con telemetría) | aterrizó a 50.1 m de casa y a 0.0 m del punto de la falla; llegada al suelo 0.77 m/s; inclinación máx. 11.4°; modos PX4: HOLD → TAKEOFF → HOLD → LAND → HOLD; perdió 6.8 m de altura en 10 s | se sostiene y aterriza sin golpe | ✅ cumple |
| HU-09 | Motor caído en DS-H (8 motores) con detección | aterrizó a 50.2 m de casa y a 0.2 m del punto de la falla; llegada al suelo 0.74 m/s; inclinación máx. 12.6°; modos PX4: HOLD → TAKEOFF → HOLD → LAND → HOLD; perdió 6.8 m de altura en 10 s | se sostiene y aterriza sin golpe | ✅ cumple |
| HU-09 | Motor caído en DS-D sin detección | aterrizó a 49.9 m de casa y a 0.2 m del punto de la falla; llegada al suelo 11.83 m/s; inclinación máx. 14.7°; modos PX4: HOLD → TAKEOFF → HOLD → LAND → HOLD; perdió 20.6 m de altura en 10 s. _Corrida del 2026-10-18 antes de separar los casos: PX4 no se entera de la falla (sin corriente de ESC en SITL) y sigue contando con el motor muerto._ | ídem (muestra por qué hace falta la detección) | ❌ no cumple |
| HU-09 | Pérdida de GNSS (DS-I) | aterrizó a 109.7 m de casa y a 59.7 m del punto de la falla; llegada al suelo 0.81 m/s; inclinación máx. 95.5°; modos PX4: HOLD → TAKEOFF → HOLD → LAND → HOLD. _Sin GNSS PX4 desciende sin control horizontal (modo LAND sin posición): el viento de 4 m/s lo arrastró 59.7 m y al tocar suelo con velocidad lateral se volcó (95.5° según el log; el valor original de 195.7° venía de sumar ángulos de Euler y se corrigió con el cuaternión). Mitigación: flujo óptico + telémetro._ | aterrizaje seguro sin alejarse > 25 m | ❌ no cumple |
| HU-09 | Batería crítica (DS-I) | aterrizó a 0.1 m de casa y a 50.3 m del punto de la falla; llegada al suelo 0.7 m/s; inclinación máx. 20.2°; modos PX4: HOLD → TAKEOFF → HOLD → RETURN_TO_LAUNCH → LAND → HOLD | RTL automático y aterrizaje en casa | ✅ cumple |
| HU-09 | Pérdida de enlace con la estación (DS-I) | aterrizó a 0.1 m de casa y a 49.9 m del punto de la falla; llegada al suelo 0.7 m/s; inclinación máx. 16.0°; modos PX4: HOLD → TAKEOFF → HOLD | RTL automático y aterrizaje en casa | ✅ cumple |
| HU-10 | Geocerca de 70 × 70 m (DS-I) | misión que cruza la geocerca: rechazada; distancia máx. a la base 0.3 m (límite 35.0 m); orden rechazada o detenido dentro (TimeoutError); RTL ordenado; aterrizó a 0.1 m de casa | misión rechazada y el dron no cruza el límite | ✅ cumple |
| HU-01/02 | Inspección con el DS-I **diseñado en CAD** (masa y malla reales, S07) | 55 fotos, error medio 0.75 m, órbita a 14 m bajo el borde | igual que S05 | ✅ cumple |
| HU-06 | Entrega con el DS-D **diseñado en CAD** (S08) | caja liberada a 0.26 m del objetivo | igual que S05 | ✅ cumple |
| HU-08 | Enjambre mixto DS-I + DS-D (CAD) + DS-H en formación (S08) | 4 de 4 drones completaron | formación de 4 drones de 3 tamaños | ✅ cumple |
| HU-03 | Corredor de faja transportadora | — | video 4K georreferenciado de 3 km | pendiente (misión de corredor, S13) |
| HU-04, HU-05, HU-11 | Procesamiento fotogramétrico (ODM) | — | DEM ±5 cm, modelo en ≤ 30 min, sin licencias | pendiente (S13) |
| HU-07 | Envío de muestras | cubierto por la entrega HU-06 | caja sellada, registro en bitácora | 🟡 bitácora pendiente (DS-GCS) |
| HU-12 | Mantenimiento rápido | — | cambio de motor/hélice/batería en minutos | pendiente (diseño mecánico, S07-S09) |
| HU-13 | Mina subterránea | — | — | v2 |

## Simulador rápido del enjambre (Monte Carlo)

Mismo código de control que en PX4 + Gazebo, con dinámica simplificada para correr cientos de casos: viento con ráfagas, ruido de GNSS y la radio simulada (retardo, pérdidas, alcance). `sin evitación` es el control: muestra que el escenario sí exige esquivar.

| Condición | Corridas | Con colisión | Separación mín. | Torre (libre) | Error de formación p95 |
|---|---|---|---|---|---|
| consenso nominal | 200 | 0 | 1.92 m | 2.67 m | 2.36 m |
| consenso perdida 30 | 200 | 0 | 1.86 m | 2.72 m | 2.36 m |
| consenso perdida 50 | 200 | 0 | 1.77 m | 2.64 m | 2.37 m |
| consenso viento 8 | 200 | 0 | 2.02 m | 0.98 m | 2.5 m |
| consenso wifi 24 | 200 | 0 | 1.92 m | 2.67 m | 2.36 m |
| caida radio en transito | 200 | 0 | 1.43 m | 2.67 m | 2.35 m |
| caida radio en cruce | 200 | 0 | 2.12 m | 2.67 m | 2.35 m |
| lider seguidor nominal | 200 | 0 | 1.31 m | 2.66 m | 4.05 m |
| sin evitacion | 200 | 200 | 0.01 m | -0.04 m | 2.3 m |

Figuras: `enjambre_cinematico/trayectorias_nominal.png`, `trayectorias_caida_radio_en_cruce.png` y la animación `enjambre_nominal.gif`.

## Cálculo ↔ simulación

| Dron | Vuelo | Error de rpm | Empuje/peso | Autonomía a las rpm medidas / calculada |
|---|---|---|---|---|
| DS-D | entrega | -0.1 % | 0.999 | 20.4 / 20.3 min |
| DS-D | hover_cad | -0.1 % | 0.999 | 20.4 / 20.3 min |
| DS-H | circuito | +0.0 % | 1.001 | 16.4 / 16.4 min |
| DS-I | hover_cad | -0.2 % | 0.995 | 30.6 / 30.5 min |
| DS-I | inspeccion | +1.6 % | 1.031 | 30.1 / 31.3 min |

Coherencia del modelo del simulador con el diseño (mismas constantes); la validación independiente es el banco de empuje (S10).

## Carpetas

- `enjambre_cinematico/` campaña Monte Carlo · `enjambre_sitl/` enjambre en PX4 + Gazebo · `hu08_sectores/` levantamiento por sectores
- `fallas/<caso>/` inyección de fallas · `calculo_vs_sim/` métricas de vuelo contra el dimensionamiento
- Misiones del S05 (inspección, entrega, carga cooperativa): `docs/evidencias/sitl/`
- Para verlo en vivo: `./dronswarm.sh` → **N** (con ventana de Gazebo).
