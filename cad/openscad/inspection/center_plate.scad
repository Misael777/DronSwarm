// DS-I · placas centrales de carbono (corte CNC). Unidades: mm.
//   which = "bottom" | "top";  mode = "3d" (STEP) | "2d" (DXF para el taller de corte)
//   openscad -D 'which="top"' -D 'mode="2d"' -o center_plate_top.dxf center_plate.scad

include <ds_i_frame.scad>

which = "bottom";
mode = "3d";

module plate_2d(which) {
    difference() {
        plate_outline();
        plate_common_holes();
        if (which == "bottom") {
            for (p = gimbal_mount_bolts) translate(p) circle(d = M3);
            for (p = battery_tray_bolts) translate(p) circle(d = M3);
            for (a = [0, 180]) rotate(a) translate([plate_d * 0.30, 0]) circle(d = 16);        // aligeramientos
            for (a = [90, 270]) rotate(a) translate([plate_d * 0.30, 0]) circle(d = 16);
            for (y = [-1, 1]) translate([battery_pos[0] - 4, y * 30]) rrect2d([8, 22], 2);    // ranuras de correa
        } else {
            fc_holes2d();
            for (p = housing_bolts) translate(p) circle(d = M3);
            translate(cable_gland_pos) circle(d = 12.5);                                         // prensaestopa M12
        }
    }
}
module fc_holes2d() { for (x = [-1, 1], y = [-1, 1]) translate([x * fc_pattern / 2, y * fc_pattern / 2]) circle(d = M3); }

// 3D con primitivas 3D (misma geometría que plate_2d). Cada grupo de agujeros es hijo directo del difference():
// el importador CSG de FreeCAD falla si se agrupan bajo una sola transformación.
module center_plate(which) {
    t = plate_t; h = t + 2;
    difference() {
        union() {
            cylinder(d = plate_d, h = t, $fn = 96);
            for (a = arm_angles) rotate(a) translate([r_block_out - block_len - 4, -block_w / 2 - 4, 0]) cube([block_len + 7, block_w + 8, t]);   // lóbulos rectos: la fresa redondea los interiores
        }
        for (a = arm_angles) rotate(a) translate([r_block_out, 0, -1])
            for (p = arm_block_bolts(tube_od, block_len, block_w)) translate([p[0], p[1], 0]) cylinder(d = M3, h = h);
        if (which == "bottom") for (p = concat(gimbal_mount_bolts, battery_tray_bolts)) translate([p[0], p[1], -1]) cylinder(d = M3, h = h);
        if (which == "bottom") for (a = [0, 90, 180, 270]) rotate(a) translate([plate_d * 0.30, 0, -1]) cylinder(d = 16, h = h);
        if (which == "bottom") for (y = [-1, 1]) translate([battery_pos[0] - 4, y * 30, -1]) rbox([8, 22, h], 2);
        if (which == "top") for (x = [-1, 1], y = [-1, 1]) translate([x * fc_pattern / 2, y * fc_pattern / 2, -1]) cylinder(d = M3, h = h);
        if (which == "top") for (p = housing_bolts) translate([p[0], p[1], -1]) cylinder(d = M3, h = h);
        if (which == "top") translate([cable_gland_pos[0], cable_gland_pos[1], -1]) cylinder(d = 12.5, h = h);
    }
}

if (mode == "2d") plate_2d(which); else center_plate(which);
