// DS-I · abrazadera de pata sobre el brazo (impresa PA12-CF, ×4). Local: eje del brazo = eje x en el origen;
// el tubo de la pata baja por −z desde el casquillo. Ranura horizontal en +y cerrada por un tornillo M3 vertical.
include <ds_i_frame.scad>
module leg_clamp(len = 22, wall = 4) {
    od = tube_od + 2 * wall;
    sock = leg_tube + 2 * wall;
    difference() {
        union() {
            translate([-len / 2, 0, 0]) rotate([0, 90, 0]) cylinder(d = od, h = len);
            translate([-len / 2, od / 2 - 3, -5]) cube([len, 11, 10]);                         // oreja de apriete
            translate([0, 0, -od / 2 - 22]) cylinder(d = sock, h = 22 + od / 2 - 3);            // casquillo de la pata
        }
        translate([-len / 2 - 1, 0, 0]) rotate([0, 90, 0]) cylinder(d = tube_od + 0.3, h = len + 2);
        translate([-len / 2 - 1, 0, -0.8]) cube([len + 2, od / 2 + 10, 1.6]);                   // ranura de apriete
        translate([0, od / 2 + 3.5, 0]) cylinder(d = M3, h = 12, center = true);                // tornillo
        translate([0, 0, -od / 2 - 23]) cylinder(d = leg_tube + 0.3, h = 21);                   // tubo de la pata
        translate([0, 0, -od / 2 - 12]) rotate([90, 0, 0]) cylinder(d = M3, h = sock + 2, center = true);   // pasador
    }
}
leg_clamp();
