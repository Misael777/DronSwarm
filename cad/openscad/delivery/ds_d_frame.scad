// DS-D · geometría compartida del frame: posiciones derivadas de los parámetros (spec v1). Unidades: mm.
// Ejes: x adelante, y izquierda, z arriba. z = 0 es la cara superior de la placa inferior.
// Hexa con brazos desmontables (bloques con levas entre las placas, ADR-012), batería y carcasa arriba,
// mecanismo de liberación de la carga al centro abajo, tren de esquíes.

include <ds_d_params.scad>
use <../common/ds_lib.scad>
include <../common/ds_lib.scad>

arm_angles = [0, 60, 120, 180, 240, 300];      // igual que el SDF/PX4 (rotor 0 adelante)
// Brazos desmontables (ADR-012): el tubo entra en un bloque impreso entre las placas y se fija con 2 levas de
// apriete rápido; los cables del motor tienen un conector en el bloque. Se monta/desmonta sin herramientas.
block_len = 60;
block_w = tube_od + 20;
r_block_out = plate_d / 2 - 3;                  // cara exterior del bloque
tube_insert = 54;                               // el tubo entra hasta un tope interior
tube_z = plate_gap / 2;
tube_start = r_block_out - tube_insert;
tube_len = arm_radius - tube_start - 6;
mm_sleeve = 30;

// Arriba: batería transversal atrás y carcasa adelante. Abajo: liberación al centro, FPV adelante
battery_pos = [-60, 0];
housing_size = [130, 110, 62];
housing_pos = [90, 0];
housing_flange = 10;
housing_bolts = [for (x = [-1, 0, 1], y = [-1, 1]) [housing_pos[0] + x * (housing_size[0] / 2 + 6), y * (housing_size[1] / 2 + 6)]];   // fuera del canal de la junta
battery_tray_bolts = [for (x = [-1, 1], y = [-1, 1]) [battery_pos[0] + x * 50, y * 95]];
release_bolts = [for (x = [-1, 1], y = [-1, 1]) [x * 35, y * 20]];
cable_gland_pos = [housing_pos[0] - housing_size[0] / 2 + 20, 0];
fpv_pos = [plate_d / 2 - 30, 0];

// Tren de esquíes: 4 patas inclinadas desde la placa inferior hasta dos esquíes longitudinales (base ancha)
leg_x = 100;                                    // patas en x = ±leg_x
leg_y_top = 110;                                // arriba, bajo la placa
skid_y = 220;                                   // esquíes en y = ±skid_y
skid_len = 560;
gear_tube = 16;                                 // tubos Ø16×1
gear_wall = 1.0;
ground_z = -leg_h;
skid_z = ground_z + gear_tube / 2 + 6;          // eje del esquí (sobre su zapata de TPU de 6 mm)
gear_mount_h = 30;                              // soporte impreso bajo la placa
// pivotes: el del soporte (bajo la placa) y el de la T (eje del esquí); la pata va de uno a otro
pivot_top = [leg_y_top, -plate_t - 6];
pivot_bot = [skid_y, skid_z];
leg_dy = pivot_bot[0] - pivot_top[0];
leg_dz = pivot_top[1] - pivot_bot[1];
leg_tilt = atan(leg_dy / leg_dz);               // inclinación hacia afuera (en torno a x)
leg_in_top = 4;                                 // el tubo termina 4 mm antes del pivote del soporte
leg_in_bot = 10;                                // y 10 mm después del eje del esquí
leg_len = sqrt(leg_dy * leg_dy + leg_dz * leg_dz) - leg_in_top - leg_in_bot;
gear_mount_bolts = [for (sx = [-1, 1], sy = [-1, 1], d = [[-14, -10], [14, -10], [-14, 10], [14, 10]]) [sx * leg_x + d[0], sy * leg_y_top + d[1]]];

motor_d = motor_iface == "L" ? 62 : 38;
motor_h = motor_iface == "L" ? 36 : 26;
function block_bolts() = [for (x = [-block_len + 7, -block_len / 2, -7], y = [-1, 1]) [x, y * (block_w / 2 - 4.5)]];
