# Parámetros de PX4 de los prototipos (S11-02, S12-02)

`ds-i.params` y `ds-d.params` los genera `tools/px4/gen_params.py` desde el dimensionamiento, la selección COTS (S09) y
lo aprendido en simulación (S06). Cada parámetro lleva una línea `#` encima que explica por qué tiene ese valor.

## Cómo cargarlos

1. Firmware PX4 **1.15.x** en la Pixhawk 6C (QGroundControl → Firmware). Es la misma versión validada en SITL.
2. QGC → Parámetros → Herramientas → **Restablecer a valores de fábrica** → reiniciar.
3. QGC → Parámetros → Herramientas → **Cargar desde archivo** → `ds-i.params` (o `ds-d.params`) → reiniciar.
4. **Revisar en QGC** cada parámetro de la lista de abajo. QGC avisa si uno no existe: un nombre equivocado se ignora
   sin aviso en el dron.

## Qué verificar a mano

| Parámetro | Por qué revisarlo |
|---|---|
| `PWM_AUX_TIM0/1`, `PWM_AUX_FUNC1..n` | PX4 los crea al compilar para la placa; no existen en SITL. Confirmar en **QGC → Actuadores** que los motores 1..n salen por DShot600 en las salidas FMU y que el orden y el sentido de giro coinciden con el dibujo de QGC (prueba de motores **sin hélices**). |
| `DSHOT_TEL_CFG`, `MAV_0/1/2_CONFIG`, `GPS_1_CONFIG`, `SER_*_BAUD` | Ídem (puertos serie de la 6C). Si QGC no los muestra, el puerto tiene otro nombre en esa placa: ajustarlo en QGC y corregir `gen_params.py`. |
| `MOT_POLE_COUNT` | Polos del motor según la ficha: MN4006 y M6C12 → contar los imanes. Si está mal, las rpm del filtro notch salen mal. |
| `MPC_THR_HOVER` | Es solo el valor inicial: el estimador de hover lo corrige en el primer vuelo. |
| `BAT1_CAPACITY`, `BAT1_V_EMPTY` | Ajustar con la primera descarga real en el banco (curva de voltaje del pack). |
| `GF_*` | La mina define la geocerca real: cargarla como polígono desde QGC (Plan → Geocerca). |
| `PD_GRIPPER_*` (DS-D) | Asignar la función **Gripper** a AUX 7 en QGC → Actuadores y probar abrir/cerrar en tierra. |

## Ya validado en simulación

`CA_ROTOR*` (geometría), `CA_FAILURE_MODE`, `COM_ACT_FAIL_ACT`, `MC_AIRMODE` (motor caído en DS-D), `NAV_DLL_ACT`,
`COM_LOW_BAT_ACT` con los umbrales mineros, `GF_ACTION` y `GF_PREDICT` (S06). `EKF2_OF_CTRL` con flujo óptico **no**
se probó en SITL: se valida en el vuelo atado (S11-04).
