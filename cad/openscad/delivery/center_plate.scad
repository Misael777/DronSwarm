// DS-D · placas centrales de carbono de 4 mm (corte CNC).  which = "bottom" | "top";  mode = "3d" | "2d" (DXF)
// Cada grupo de agujeros es hijo directo del difference() (ver reglas en common/ds_lib.scad).
include <ds_d_frame.scad>
which = "bottom";
mode = "3d";

module center_plate(which) {
    t = plate_t; h = t + 2;
    difference() {
        cylinder(d = plate_d, h = t, $fn = 120);
        for (a = arm_angles) rotate(a) translate([r_block_out, 0, -1])
            for (p = block_bolts()) translate([p[0], p[1], 0]) cylinder(d = M4, h = h);
        if (which == "bottom") for (p = concat(release_bolts, gear_mount_bolts)) translate([p[0], p[1], -1]) cylinder(d = M4, h = h);
        if (which == "bottom") for (y = [-1, 1]) translate([fpv_pos[0], y * 15, -1]) cylinder(d = M3, h = h);
        if (which == "bottom") for (a = [30, 90, 150, 210, 270, 330]) rotate(a) translate([105, 0, -1]) cylinder(d = 44, h = h);
        if (which == "top") for (p = concat(housing_bolts, battery_tray_bolts)) translate([p[0], p[1], -1]) cylinder(d = M3, h = h);
        if (which == "top") translate([cable_gland_pos[0], cable_gland_pos[1], -1]) cylinder(d = 16.5, h = h);   // prensaestopa M16
        // arriba solo fuera de la carcasa IP54 (un agujero bajo la carcasa sería una entrada de agua)
        if (which == "top") for (a = [90, 150, 210, 270]) rotate(a) translate([105, 0, -1]) cylinder(d = 44, h = h);
    }
}

module plate_2d(which) projection(cut = true) translate([0, 0, -plate_t / 2]) center_plate(which);
if (mode == "2d") plate_2d(which); else center_plate(which);
