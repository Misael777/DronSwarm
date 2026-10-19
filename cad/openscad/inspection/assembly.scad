// DS-I · ensamble. Cada pieza se declara con place(): se dibuja aquí y además se anuncia (echo "PLACE|…") para que
// tools/cad/build_assembly.py arme el ensamble de FreeCAD con las piezas STEP en su posición.
// z = 0 es la cara superior de la placa inferior; x adelante.
include <ds_i_frame.scad>
use <center_plate.scad>
use <arm_block.scad>
use <arm_tube.scad>
use <motor_mount.scad>
use <leg_clamp.scad>
use <leg_tube.scad>
use <foot.scad>
use <battery_tray.scad>
use <gimbal_mount.scad>
use <housing.scad>
use <refs.scad>

show_refs = true;

// t = traslación, r = rotación [rx, ry, rz] en grados (primero x, luego y, luego z; igual que rotate())
module place(name, file, defs, t, r = [0, 0, 0], kind = "part") {
    echo(str("PLACE|", name, "|", file, "|", defs, "|", t, "|", r, "|", kind));
    if (kind == "part" || show_refs) translate(t) rotate(r) children();
}
function rz(a, v) = [v[0] * cos(a) - v[1] * sin(a), v[0] * sin(a) + v[1] * cos(a), v[2]];

mm_pt = motor_iface == "L" ? 6 : 4;
motor_top_z = tube_z + mm_pt + tube_od / 2 + 1;          // cara de apoyo del motor sobre el soporte

place("center_plate_bottom", "center_plate.scad", "which=\"bottom\"", [0, 0, -plate_t]) center_plate("bottom");
place("center_plate_top", "center_plate.scad", "which=\"top\"", [0, 0, plate_gap]) center_plate("top");
for (i = [0 : 3]) {
    a = arm_angles[i];
    place(str("arm_block_", i), "arm_block.scad", "", rz(a, [r_block_out, 0, 0]), [0, 0, a]) arm_block(tube_od, plate_gap, block_len, block_w);
    place(str("arm_tube_", i), "arm_tube.scad", "", rz(a, [r_block_out - block_len + 4, 0, tube_z]), [0, 0, a]) arm_tube();
    place(str("motor_mount_", i), "motor_mount.scad", "", rz(a, [arm_radius, 0, motor_top_z]), [0, 0, a]) motor_mount(tube_od, motor_iface, sleeve = mm_sleeve);
    place(str("leg_clamp_", i), "leg_clamp.scad", "", rz(a, [leg_r, 0, tube_z]), [0, 0, a]) leg_clamp();
    place(str("leg_tube_", i), "leg_tube.scad", "", rz(a, [leg_r, 0, leg_top_z]), [0, 0, a]) leg_tube();
    place(str("foot_", i), "foot.scad", "", rz(a, [leg_r, 0, leg_top_z - leg_len + 12]), [0, 0, a]) foot();
    place(str("motor_", i), "refs.scad", "which=\"motor\"", rz(a, [arm_radius, 0, motor_top_z]), [0, 0, a], "ref") ref("motor");
    place(str("prop_", i), "refs.scad", "which=\"prop\"", rz(a, [arm_radius, 0, motor_top_z + motor_h + 6]), [0, 0, a], "ref") %ref("prop");
}
place("battery_tray", "battery_tray.scad", "", [battery_pos[0], 0, -plate_t]) battery_tray();
place("battery", "refs.scad", "which=\"battery\"", [battery_pos[0], 0, -plate_t - tray_t], [0, 0, 0], "ref") ref("battery");
place("gimbal_plate_top", "gimbal_mount.scad", "which=\"top\"", [gimbal_pos[0] - 15, 0, -plate_t]) gimbal_plate("top");
place("gimbal_plate_bottom", "gimbal_mount.scad", "which=\"bottom\"", [gimbal_pos[0] - 15, 0, -plate_t]) gimbal_plate("bottom");
for (k = [0 : 3]) place(str("damper_", k), "refs.scad", "which=\"damper\"", [gimbal_pos[0] - 15 + (k < 2 ? -20 : 20), (k % 2 == 0 ? -25 : 25), -plate_t - gm_t - damper_h], [0, 0, 0], "ref") ref("damper");
place("gimbal_camera", "refs.scad", "which=\"gimbal\"", [gimbal_pos[0], 0, -plate_t - 2 * gm_t - damper_h], [0, 0, 0], "ref") ref("gimbal");
place("housing", "housing.scad", "", [0, 0, plate_gap + plate_t]) housing();
place("fc_stack", "refs.scad", "which=\"fc_stack\"", [0, 0, plate_gap + plate_t + 6], [0, 0, 0], "ref") ref("fc_stack");
place("companion", "refs.scad", "which=\"companion\"", [0, 0, plate_gap + plate_t + 34], [0, 0, 0], "ref") ref("companion");
place("gnss", "refs.scad", "which=\"gnss\"", [10, 0, plate_gap + plate_t + housing_size[2] + 6], [0, 0, 0], "ref") ref("gnss");
