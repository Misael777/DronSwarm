// DS-D · carcasa IP54 de la electrónica (impresa PA12-CF/ASA, paredes 2.4 mm) sobre la placa superior, adelante.
// Junta EPDM Ø2 mm en canal, 6 × M3 con arandela de nylon, prensaestopa M16, ventila ePTFE M12, domo de GNSS.
// Local: brida en z = 0, centrada en el origen (se ubica en housing_pos).
include <ds_d_frame.scad>
wall = 2.4;
module housing() {
    L = housing_size[0]; W = housing_size[1]; H = housing_size[2];
    difference() {
        union() {
            crbox([L, W, H], 12);
            crbox([L + 2 * housing_flange, W + 2 * housing_flange, 4], 14);
            translate([0, 0, H]) cylinder(d = 50, h = 6);
        }
        translate([0, 0, -1]) crbox([L - 2 * wall, W - 2 * wall, H - wall + 1], 10);
        for (p = housing_bolts) translate([p[0] - housing_pos[0], p[1], -1]) cylinder(d = M3, h = 6);
        difference() {
            translate([0, 0, -1]) crbox([L + 5.2, W + 5.2, 2.6], 13);
            translate([0, 0, -2]) crbox([L + 1.2, W + 1.2, 5], 13);
        }
        translate([L / 2 - 1, W / 4, H * 0.55]) rotate([0, 90, 0]) cylinder(d = 12.2, h = wall + 2);
        translate([0, 0, H - wall - 1]) cylinder(d = 10, h = wall + 8);
    }
}
housing();
