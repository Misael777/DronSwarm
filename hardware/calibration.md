# Calibraciones y HITL (S11-03)

Orden obligatorio antes del primer vuelo de cada dron. Todo **sin hélices**, salvo donde se indica. Registrar cada paso
en la hoja del dron (`hardware/prototipos/flota.md`).

## 1. En el banco de trabajo (sin hélices)

| Paso | Cómo | Criterio |
|---|---|---|
| Sensores | QGC → Sensores: acelerómetro (6 caras), giróscopo, nivel del horizonte | Sin errores; nivel con el dron sobre sus patas |
| Brújula | QGC → Sensores → Brújula, lejos de metales (no en la mesa de trabajo) | Calibración completa; `COM_ARM_MAG_ANG` < 30° |
| Interferencia de la brújula | QGC → Calibrar compensación de potencia, o vuelo atado con `logger` + revisión | Interferencia < 30 % del campo terrestre a throttle de hover |
| Radio (RC) | QGC → Radio: palancas y modos de vuelo (Posición, Altitud, Misión, RTL) | Kill switch en un interruptor protegido |
| ESC y motores | QGC → Actuadores → prueba de motores, uno por uno, al 5 % | Orden y sentido de giro iguales al dibujo de QGC |
| Telemetría de ESC | `listener esc_status` en la consola MAVLink | rpm, voltaje y **corriente** de cada ESC llegan (DS-D: obligatorio para motor caído) |
| Batería | Comparar el voltaje y la corriente de QGC con multímetro y pinza | ± 2 % |
| Flujo óptico | `listener vehicle_optical_flow` y `distance_sensor`, moviendo el dron a mano a 1 m del piso | Distancia correcta ± 5 cm; flujo responde al movimiento |
| Failsafes | Apagar el RC, desconectar la telemetría, bajar `BAT1_V_CHARGED` para simular batería baja | QGC muestra el failsafe y la acción configurada (sin armar) |
| Gancho (DS-D) | Abrir y cerrar desde QGC; con el servo sin energía, tirar del gancho con 10 kg | Se mantiene trabado sin energía |

## 2. HITL (hardware in the loop)

La controladora real corre PX4 con el simulador en el PC: prueba la misión, los failsafes y el control del enjambre con
el hardware de vuelo y **sin riesgo**.

1. QGC → Configuración → Seguridad: activar **HITL** y reiniciar. Hélices quitadas y batería desconectada (alimentación por USB).
2. Arrancar el simulador SIH de PX4 en modo HITL (ver la documentación de PX4 1.15, "Hardware in the Loop") con la
   geometría del dron: los `CA_ROTOR*` de `ds-i.params` son los mismos del SITL.
3. Cargar la misión de inspección (`control/missions/inspection.py`, adaptada para conectarse por UDP de QGC) y volarla
   completa. Repetir los failsafes del S06: pérdida de enlace, batería crítica y geocerca.
4. La Raspberry Pi (conectada por TELEM2) corre el control del enjambre contra el HITL: verifica la latencia real del
   puerto serie (< 20 ms en el lazo de 10 Hz).
5. Desactivar HITL antes de volar.
