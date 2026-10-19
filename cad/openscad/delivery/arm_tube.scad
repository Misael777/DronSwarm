// DS-D · brazo: tubo de carbono enrollado Ø22×1.5 (compra, corte a medida, ×6). Local: eje x desde x = 0.
include <ds_d_frame.scad>
module arm_tube() rotate([0, 90, 0]) difference() {
    cylinder(d = tube_od, h = tube_len, $fn = 64);
    translate([0, 0, -1]) cylinder(d = tube_od - 2 * tube_wall, h = tube_len + 2, $fn = 64);
}
arm_tube();
