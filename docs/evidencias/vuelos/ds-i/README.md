# Vuelos de prueba del DS-I #1 (S11-04, S11-05, S11-06)

> Plan escrito antes de volar. Cada ensayo deja su log (`.ulg`), el resultado del análisis (JSON) y una línea en la
> tabla de resultados. **Pendiente: requiere el prototipo armado y calibrado** (`hardware/calibration.md`).

## Reglas de seguridad (todas las pruebas)

- Lugar abierto, sin personas a menos de 30 m; piloto con el kill switch en la mano; segundo observador.
- Primero **vuelo atado**: cuerda de 3 m a un peso de 20 kg o una estaca, desde el centro del tren.
- Batería cargada y balanceada; se aborta si el voltaje de una celda baja de 3.3 V bajo carga.
- Viento ≤ 6 m/s en los primeros vuelos.

## Secuencia

| # | Prueba | Cómo | Criterio | Análisis |
|---|---|---|---|---|
| 1 | Vuelo atado (S11-04) | Modo Estabilizado, 1 m de altura, 60 s; luego Posición | Despega recto, sin oscilaciones; responde a las palancas | — |
| 2 | Vibración (S11-04) | Hover de 60 s en Posición, a 3 m | Métrica de vibración p95 < 15 m/s² (máx. 30) | `tools/flight/vibration.py vuelo.ulg --png …` |
| 3 | Filtros (S11-04) | Si el pico no es armónico de las rpm: notch fijo según la recomendación; repetir el 2 | Pico bajo control, sin resonancia | ídem |
| 4 | Autotune (S11-05) | PX4 1.15: `MC_AT_EN` = 1, en Altitud/Posición a 10 m con viento < 4 m/s, activar el autotune desde QGC o el RC | Termina sin abortar; respuesta escalón sin sobrepaso > 15 % | revisión en Flight Review (logs.px4.io o local) |
| 5 | Hover de precisión (S11-05) | Posición, 60 s, sin tocar las palancas | Desvío ≤ ± 0.5 m horizontal y vertical (RTK) | Flight Review: posición estimada vs referencia |
| 6 | Envolvente (S11-05) | Tramo recto de 300 m a 15 m/s (`MPC_XY_VEL_MAX` = 15) ida y vuelta | Alcanza 15 m/s y frena sin sobrepaso > 1 m | ídem |
| 7 | Flujo óptico | Desactivar el GNSS en vuelo (`EKF2_GPS_CTRL` = 0) a 3 m, en Posición | Sostiene posición ± 1 m con el flujo óptico (el problema del S06) | ídem |
| 8 | Failsafes | Apagar el RC y luego la telemetría a 20 m | RTL automático (como en SITL, S06) | modos de vuelo en el log |
| 9 | Autonomía (S11-06) | Batería completa, hover a 5 m hasta la alarma del 25 % (RTL) | Potencia de hover dentro de ± 10 % del modelo | `tools/flight/endurance.py vuelo.ulg --vehicle DS-I --mass <balanza> --site-alt <m> --ambient <°C>` |

## Resultados (llenar)

| Fecha | Prueba | Log | Resultado | ¿Cumple? | Notas |
|---|---|---|---|---|---|
| | | | | | |

La autonomía medida (prueba 9) se compara con el modelo **en las condiciones del lugar**, y la herramienta la proyecta
a 4,500 msnm. La de altura real se mide en el S15.
