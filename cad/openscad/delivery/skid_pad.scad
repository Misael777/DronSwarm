// DS-D · zapata del esquí (impresa TPU 85A, giroide 20 %, ×4): amortigua el aterrizaje y protege el tubo.
// Local: abraza el esquí (eje x en el origen); apoya en el suelo en z = −(gear_tube / 2 + 6).
include <ds_d_frame.scad>
module skid_pad(len = 90) difference() {
    translate([-len / 2, -14, -gear_tube / 2 - 6]) cube([len, 28, gear_tube / 2 + 9]);
    translate([-len / 2 - 1, 0, 0]) rotate([0, 90, 0]) cylinder(d = gear_tube + 0.2, h = len + 2);
    translate([-len / 2 - 1, -gear_tube * 0.3, 0]) cube([len + 2, gear_tube * 0.6, 10]);
}
skid_pad();
