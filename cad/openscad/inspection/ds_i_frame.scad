// DS-I · geometría compartida del frame: posiciones derivadas de los parámetros (spec v1). Unidades: mm.
// Ejes: x adelante, y izquierda, z arriba. z = 0 es la cara superior de la placa inferior.
// Cada pieza vive en su propio archivo (center_plate.scad, arm_block.scad, …) e incluye este.

include <ds_i_params.scad>
use <../common/ds_lib.scad>
include <../common/ds_lib.scad>

arm_angles = [45, 135, 225, 315];         // quad X
block_len = 40;
block_w = tube_od + 14;
r_block_out = plate_d / 2 - 3;            // extremo exterior del bloque de brazo
tube_z = plate_gap / 2;                   // eje de los tubos
tube_len = arm_radius - r_block_out + block_len - 8;   // dentro del bloque hasta el soporte de motor
leg_offset = 70;                          // patas abrazadas al brazo, a esta distancia del bloque
leg_r = r_block_out + leg_offset;
leg_tube = 12;                            // tubo de las patas Ø12×1
battery_pos = [-28, 0];                   // batería transversal, atrás, bajo la placa
gimbal_pos = [62, 0];                     // cámara adelante, colgada con amortiguadores
housing_size = [120, 90, 58];             // carcasa IP54 sobre la placa superior
housing_pos = [0, 0];

// Contorno de las placas centrales (2D): círculo con lóbulos bajo cada bloque de brazo
module plate_outline() {
    union() {
        circle(d = plate_d, $fn = 96);
        for (a = arm_angles) rotate(a) translate([r_block_out - block_len - 4, -block_w / 2 - 4]) square([block_len + 7, block_w + 8]);
    }
}

// Agujeros comunes a ambas placas: tornillos de los bloques
module plate_common_holes() {
    for (a = arm_angles) rotate(a) translate([r_block_out, 0])
        for (p = arm_block_bolts(tube_od, block_len, block_w)) translate(p) circle(d = M3);
}

// Posiciones de piezas montadas en las placas
gimbal_mount_bolts = [for (x = [-25, 25], y = [-32, 32]) [gimbal_pos[0] - 15 + x, y]];   // adaptador bajo la placa
battery_tray_bolts = [for (x = [-30, 30], y = [-46, 46]) [battery_pos[0] + x, y]];
housing_flange = 10;
// tornillos de la brida a 6 mm de la pared (afuera del canal de la junta, que va de 0.6 a 2.6 mm)
housing_bolts = [[66, 0], [-66, 0], [0, 51], [0, -51], [40, 51], [40, -51], [-40, 51], [-40, -51]];
cable_gland_pos = [-housing_size[0] / 2 + 18, 0];      // paso de cables al interior de la carcasa (prensaestopa M12)
motor_d = motor_iface == "L" ? 62 : 38;   // motor de referencia (COTS, se confirma en S09)
motor_h = motor_iface == "L" ? 36 : 26;
tray_t = 3;                               // bandeja de batería
gm_t = 4;                                 // placas del adaptador de cámara
damper_h = 10;                            // amortiguadores de silicona
foot_h = 45;                              // pie amortiguador de TPU (≈ 30 mm de carrera)
foot_stroke = 30;
// Altura de las patas por condición de diseño: con el pie comprimido, la cámara no toca el suelo (10 mm de margen)
gimbal_bottom_z = -plate_t - 2 * gm_t - damper_h - gimbal_box[2];
ground_z = gimbal_bottom_z - foot_stroke - 10;
leg_top_z = tube_z - (tube_od + 8) / 2 - 2;     // tope del tubo de la pata dentro de la abrazadera
leg_len = (leg_top_z - ground_z) - (foot_h - 12);
mm_sleeve = 26;                           // manguito del soporte de motor (FEA: FS 37 con 34 mm, se acorta)
