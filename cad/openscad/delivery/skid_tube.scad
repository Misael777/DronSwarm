// DS-D · esquí: tubo de carbono Ø16×1.5 × skid_len (×2). Local: eje x centrado en el origen.
include <ds_d_frame.scad>
module skid_tube() translate([-skid_len / 2, 0, 0]) rotate([0, 90, 0]) difference() {
    cylinder(d = gear_tube, h = skid_len, $fn = 48);
    translate([0, 0, -1]) cylinder(d = gear_tube - 2 * gear_wall, h = skid_len + 2, $fn = 48);
}
skid_tube();
