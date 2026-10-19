# Prueba controlada de motor caído · DS-D (S12-05)

Objetivo: comprobar en vuelo real lo verificado en SITL (S06). Al perder un motor, PX4 lo detecta por la telemetría de
corriente, lo retira de la asignación (`CA_FAILURE_MODE` = 1) y aterriza solo (`COM_ACT_FAIL_ACT` = 2), con
`MC_AIRMODE` = 1.

## Cómo se corta un motor en vuelo

La inyección de fallas de PX4 1.15 solo altera la telemetría y no apaga el motor. Por eso se usa un **corte físico de la
señal**: un relé de estado sólido en el cable DShot del motor 1, comandado por un canal libre del RC (interruptor
protegido). Al abrirse, el ESC deja de recibir señal y para el motor, y su telemetría informa corriente 0: eso es lo que
detecta PX4. Es lo más parecido a un ESC que se quema.

## Secuencia (sin carga primero, después con 5 kg)

| Paso | Qué | Criterio |
|---|---|---|
| 1 | En tierra, sin hélices: activar el relé con el dron armado | `failure_detector_status` marca el motor 1; QGC avisa "Motor failure"; los demás siguen |
| 2 | Vuelo atado a 2 m sobre pasto, cuerda de 5 m | Al cortar: actitud dentro de ± 30°, pérdida de altura < 1 m, aterrizaje automático |
| 3 | Libre a **15 m** sobre pasto, sin carga, viento < 4 m/s | Aterrizaje autónomo; desvío < 5 m; impacto < 1.5 m/s (log) |
| 4 | Ídem con la caja de 5 kg | Ídem (en SITL: aterrizó a 0.77 m/s, inclinación máx. 11°) |

Se aborta en cualquier momento cerrando el relé (el motor vuelve). Si PX4 no lo detecta en el paso 1, **no se vuela**:
revisar `DSHOT_TEL_CFG` y la telemetría de corriente.

## Resultados (llenar)

| Fecha | Paso | Log | Detección [ms] | Pérdida de altura | Inclinación máx. | Impacto | ¿Cumple? |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
