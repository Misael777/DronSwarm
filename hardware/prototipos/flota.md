# Flota de prototipos (S12-06)

Plan del CDR: **por etapas**. Primero 2 DS-I + 1 DS-D para validar en el S11-S12; después se completa hasta 6 unidades
(4 DS-I + 2 DS-D) para el enjambre de campo (S13-S15), según la decisión G2-2.

## Registro de unidades (llenar)

| Unidad | Tipo | Controladora (n.º de serie) | ID MAVLink (`MAV_SYS_ID`) | Motores (lote) | Baterías | Masa al despegue | Horas de vuelo | Estado | Última revisión |
|---|---|---|---|---|---|---|---|---|---|
| DS-I #1 | DS-I | | 1 | | B-I-01, B-I-02 | | 0 | en armado | |
| DS-I #2 | DS-I | | 2 | | B-I-03, B-I-04 | | 0 | pendiente | |
| DS-D #1 | DS-D | | 10 | | B-D-01, B-D-02 | | 0 | pendiente | |
| DS-I #3 | DS-I | | 3 | | | | 0 | etapa 2 | |
| DS-I #4 | DS-I | | 4 | | | | 0 | etapa 2 | |
| DS-D #2 | DS-D | | 11 | | | | 0 | etapa 2 | |

Cada unidad tiene un **`MAV_SYS_ID` distinto** (el enjambre los necesita) y su propio archivo de parámetros exportado
desde QGC después de calibrarla: `hardware/px4_params/unidades/<unidad>.params`.

## Lista antes de cada vuelo (por unidad)

1. Hélices sin fisuras y apretadas; brazos y levas cerrados (DS-D); patas y pies firmes.
2. Batería: voltaje por celda ± 20 mV, sin hinchazón, conector sin quemaduras; registrar el ciclo.
3. QGC: sin errores de prearmado, GNSS con RTK fijo (o al menos 3D con HDOP < 1), brújula consistente.
4. Geocerca y punto de retorno cargados; failsafes según `hardware/px4_params/README.md`.
5. DS-D: micro-interruptor "gancho cerrado" en verde con la caja enganchada.

## Mantenimiento

| Cada | Qué |
|---|---|
| 10 h de vuelo | Rodamientos de los motores (giro a mano), apriete de soportes y bloques, ajuste de las levas |
| 50 ciclos de batería | Resistencia interna de los packs (retirar si sube más de 30 %) |
| Caída o golpe | Inspección completa del frame (fisuras en el PA12, delaminación del carbono) antes de volver a volar |
