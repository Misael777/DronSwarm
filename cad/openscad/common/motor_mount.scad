// Soporte de motor para brazo de tubo de carbono — pieza paramétrica.
// Pieza de prueba de la cadena OpenSCAD → STEP → FreeCAD (S01-06) y borrador de la
// interfaz de montaje de motor estándar (ADR-004). Unidades: mm.

/* [Tubo del brazo] */
tube_d = 20;            // diámetro exterior del tubo de carbono
clamp_len = 30;         // largo de la abrazadera sobre el tubo
clamp_wall = 3;         // espesor de pared de la abrazadera
clamp_gap = 2;          // ranura para apretar la abrazadera
clamp_bolt_d = 3.2;     // agujero pasante M3 de la abrazadera

/* [Motor] */
plate_d = 42;           // diámetro de la placa de motor
plate_t = 4;            // espesor de la placa
motor_bolt_d = 3.2;     // M3
motor_bolt_pattern = [16, 19];  // patrón de tornillos (los más comunes en motores 22xx-28xx)
center_hole_d = 8;      // paso del eje / cables

$fn = 64;

module clamp() {
    od = tube_d + 2 * clamp_wall;
    difference() {
        union() {
            rotate([0, 90, 0]) cylinder(d = od, h = clamp_len);
            // orejas para el tornillo de apriete
            translate([0, -clamp_gap / 2 - 4, -od / 2 - 6]) cube([clamp_len, clamp_gap + 8, 8]);
        }
        rotate([0, 90, 0]) translate([0, 0, -1]) cylinder(d = tube_d, h = clamp_len + 2);
        translate([-1, -clamp_gap / 2, -od / 2 - 7]) cube([clamp_len + 2, clamp_gap, od / 2 + 7]);
        for (x = [clamp_len * 0.3, clamp_len * 0.7])
            translate([x, 0, -od / 2 - 2]) rotate([90, 0, 0]) cylinder(d = clamp_bolt_d, h = 20, center = true);
    }
}

module motor_plate() {
    od = tube_d + 2 * clamp_wall;
    translate([clamp_len + plate_d / 2 - od / 2, 0, od / 2 - plate_t])
        difference() {
            cylinder(d = plate_d, h = plate_t);
            translate([0, 0, -1]) cylinder(d = center_hole_d, h = plate_t + 2);
            for (a = [0, 90, 180, 270]) {
                r = motor_bolt_pattern[(a / 90) % 2] / 2;
                rotate([0, 0, a]) translate([r, 0, -1]) cylinder(d = motor_bolt_d, h = plate_t + 2);
            }
        }
}

module motor_mount() {
    od = tube_d + 2 * clamp_wall;
    clamp();
    motor_plate();
    // nervio que une abrazadera y placa: perfil 2D extruido (no usar hull/minkowski:
    // FreeCAD los convierte en malla y el sólido deja de ser válido para planos)
    translate([0, clamp_wall, 0]) rotate([90, 0, 0])
        linear_extrude(height = 2 * clamp_wall)
            polygon([[clamp_len - 8, 0], [clamp_len, 0], [clamp_len + 6, od / 2 - plate_t],
                     [clamp_len + 6, od / 2], [clamp_len - 8, od / 2]]);
}

motor_mount();
