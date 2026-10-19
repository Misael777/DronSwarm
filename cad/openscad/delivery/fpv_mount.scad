// DS-D · soporte de cámara FPV (impreso PA12-CF): cámara de 19 mm inclinada 20° hacia abajo, adelante bajo la placa.
// Local: cara contra la placa en z = 0, centrado en fpv_pos.
include <ds_d_frame.scad>
module fpv_mount() difference() {
    union() {
        translate([-12, -21, -4]) cube([24, 42, 4]);
        for (y = [-1, 1]) translate([-8, y * 12.5 - 2, -28]) cube([16, 4, 26]);
    }
    for (y = [-1, 1]) translate([0, y * 15, -5]) cylinder(d = M3, h = 6);
    for (y = [-1, 1]) translate([0, y * 12.5, -18]) rotate([90, 0, 0]) cylinder(d = 2.2, h = 8, center = true);   // M2 de la cámara
}
fpv_mount();
