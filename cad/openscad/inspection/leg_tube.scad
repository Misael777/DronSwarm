// DS-I · pata: tubo de carbono Ø12×1 (compra, ×4). Local: eje z, desde z = 0 hacia abajo.
include <ds_i_frame.scad>
module leg_tube() translate([0, 0, -leg_len]) difference() {
    cylinder(d = leg_tube, h = leg_len, $fn = 48);
    translate([0, 0, -1]) cylinder(d = leg_tube - 2, h = leg_len + 2, $fn = 48);
}
leg_tube();
