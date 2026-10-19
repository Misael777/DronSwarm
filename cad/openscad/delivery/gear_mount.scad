// DS-D · soporte de pata bajo la placa inferior (impreso PA12-CF, ×4): casquillo inclinado leg_tilt hacia afuera.
// Local: cara contra la placa en z = 0, centrado en (±leg_x, ±leg_y_top); el casquillo baja inclinado hacia +y
// (las del lado −y se colocan giradas 180° en el ensamble).
include <ds_d_frame.scad>
module gear_mount() {
    sock = gear_tube + 9;
    difference() {
        union() {
            translate([0, 0, -8]) crbox([44, 36, 8], 4);
            translate([0, 0, -6]) rotate([leg_tilt, 0, 0]) translate([0, 0, -gear_mount_h + 6]) cylinder(d = sock, h = gear_mount_h - 4);   // no asoma sobre z = 0
        }
        for (d = [[-14, -10], [14, -10], [-14, 10], [14, 10]]) translate([d[0], d[1], -9]) cylinder(d = M4, h = 10);
        translate([0, 0, -6]) rotate([leg_tilt, 0, 0]) translate([0, 0, -gear_mount_h + 4]) cylinder(d = gear_tube + 0.3, h = 22);
        translate([0, 0, -6]) rotate([leg_tilt, 0, 0]) translate([0, 0, -gear_mount_h + 14]) rotate([0, 90, 0]) cylinder(d = M4, h = sock + 2, center = true);
    }
}
gear_mount();
