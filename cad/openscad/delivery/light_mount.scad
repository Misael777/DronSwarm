// DS-D · soporte de luz anticolisión en el brazo (impreso PA12-CF, ×6): abrazadera al tubo + base de LED de 20 mm
// orientada hacia afuera y abajo (rojo a la izquierda, verde a la derecha, blanco destellante atrás).
// Local: eje del brazo = eje x en el origen.
include <ds_d_frame.scad>
module light_mount(len = 16, wall = 3) difference() {
    union() {
        translate([-len / 2, 0, 0]) rotate([0, 90, 0]) cylinder(d = tube_od + 2 * wall, h = len);
        translate([0, 0, -tube_od / 2 - 12]) cylinder(d = 24, h = 10);
        translate([-len / 2, (tube_od + 2 * wall) / 2 - 3, -3]) cube([len, 8, 6]);
    }
    translate([-len / 2 - 1, 0, 0]) rotate([0, 90, 0]) cylinder(d = tube_od + 0.3, h = len + 2);
    translate([-len / 2 - 1, 0, -0.75]) cube([len + 2, tube_od, 1.5]);
    translate([0, (tube_od + 2 * wall) / 2 + 2, 0]) cylinder(d = M3, h = 10, center = true);
    translate([0, 0, -tube_od / 2 - 13]) cylinder(d = 20.4, h = 8);                       // LED
}
light_mount();
