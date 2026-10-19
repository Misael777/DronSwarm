// DS-D · pata del tren: tubo de carbono Ø16×1.5 (×4). Local: eje z, desde z = 0 hacia abajo.
include <ds_d_frame.scad>
module leg_tube() translate([0, 0, -leg_len]) difference() {
    cylinder(d = gear_tube, h = leg_len, $fn = 48);
    translate([0, 0, -1]) cylinder(d = gear_tube - 2 * gear_wall, h = leg_len + 2, $fn = 48);
}
leg_tube();
