// DS-D · unión pata-esquí (impresa PA12-CF, ×4): abrazadera del esquí + casquillo inclinado de la pata.
// Local: eje del esquí = eje x en el origen; la pata sube inclinada leg_tilt hacia −y (hacia el centro).
include <ds_d_frame.scad>
module skid_tee() {
    od = gear_tube + 8;
    difference() {
        union() {
            translate([-17, 0, 0]) rotate([0, 90, 0]) cylinder(d = od, h = 34);
            rotate([leg_tilt, 0, 0]) cylinder(d = od, h = 32);
        }
        translate([-18, 0, 0]) rotate([0, 90, 0]) cylinder(d = gear_tube + 0.3, h = 36);
        rotate([leg_tilt, 0, 0]) translate([0, 0, 10]) cylinder(d = gear_tube + 0.3, h = 24);
        rotate([leg_tilt, 0, 0]) translate([0, 0, 22]) rotate([0, 90, 0]) cylinder(d = M4, h = od + 2, center = true);
        translate([0, 0, 0]) rotate([90, 0, 0]) cylinder(d = M4, h = od + 2, center = true);
    }
}
skid_tee();
