// DS-D · ensamble (ver inspection/assembly.scad: place() dibuja y anuncia cada pieza para tools/cad/build_frame.py).
include <ds_d_frame.scad>
use <center_plate.scad>
use <arm_socket.scad>
use <arm_tube.scad>
use <motor_mount.scad>
use <battery_tray.scad>
use <housing.scad>
use <gear_mount.scad>
use <leg_tube.scad>
use <skid_tube.scad>
use <skid_tee.scad>
use <skid_pad.scad>
use <payload_release.scad>
use <fpv_mount.scad>
use <light_mount.scad>
use <refs.scad>

show_refs = true;
module place(name, file, defs, t, r = [0, 0, 0], kind = "part") {
    echo(str("PLACE|", name, "|", file, "|", defs, "|", t, "|", r, "|", kind));
    if (kind == "part" || show_refs) translate(t) rotate(r) children();
}
function rz(a, v) = [v[0] * cos(a) - v[1] * sin(a), v[0] * sin(a) + v[1] * cos(a), v[2]];

mm_pt = 6;
motor_top_z = tube_z + mm_pt + tube_od / 2 + 1;
top_z = plate_gap + plate_t;                     // cara superior de la placa superior

place("center_plate_bottom", "center_plate.scad", "which=\"bottom\"", [0, 0, -plate_t]) center_plate("bottom");
place("center_plate_top", "center_plate.scad", "which=\"top\"", [0, 0, plate_gap]) center_plate("top");
for (i = [0 : 5]) {
    a = arm_angles[i];
    place(str("arm_socket_", i), "arm_socket.scad", "", rz(a, [r_block_out, 0, 0]), [0, 0, a]) arm_socket();
    place(str("arm_tube_", i), "arm_tube.scad", "", rz(a, [tube_start, 0, tube_z]), [0, 0, a]) arm_tube();
    place(str("motor_mount_", i), "motor_mount.scad", "", rz(a, [arm_radius, 0, motor_top_z]), [0, 0, a]) motor_mount(tube_od, motor_iface, sleeve = mm_sleeve, wall = 4);
    place(str("light_mount_", i), "light_mount.scad", "", rz(a, [arm_radius - 90, 0, tube_z]), [0, 0, a]) light_mount();
    place(str("motor_", i), "refs.scad", "which=\"motor\"", rz(a, [arm_radius, 0, motor_top_z]), [0, 0, a], "ref") ref("motor");
    place(str("prop_", i), "refs.scad", "which=\"prop\"", rz(a, [arm_radius, 0, motor_top_z + motor_h + 8]), [0, 0, a], "ref") ref("prop");
    place(str("esc_", i), "refs.scad", "which=\"esc\"", rz(a, [r_block_out - block_len - 34, 0, 7]), [0, 0, a], "ref") ref("esc");
}
// arriba: batería y carcasa
place("battery_tray", "battery_tray.scad", "", [battery_pos[0], 0, top_z]) battery_tray();
place("battery", "refs.scad", "which=\"battery\"", [battery_pos[0], 0, top_z + 4], [0, 0, 0], "ref") ref("battery");
place("housing", "housing.scad", "", [housing_pos[0], 0, top_z]) housing();
place("fc_stack", "refs.scad", "which=\"fc_stack\"", [housing_pos[0] - 20, 0, top_z + 4], [0, 0, 0], "ref") ref("fc_stack");
place("companion", "refs.scad", "which=\"companion\"", [housing_pos[0] + 20, 0, top_z + 32], [0, 0, 0], "ref") ref("companion");
place("gnss", "refs.scad", "which=\"gnss\"", [housing_pos[0], 0, top_z + housing_size[2] + 6], [0, 0, 0], "ref") ref("gnss");
// abajo: liberación de carga, FPV, tren
place("release_body", "payload_release.scad", "which=\"body\"", [0, 0, -plate_t]) release_body();
place("release_hook", "payload_release.scad", "which=\"hook\"", [0, 0, -plate_t]) release_hook();
place("servo", "refs.scad", "which=\"servo\"", [21, 0, -plate_t - 41], [0, 0, 0], "ref") ref("servo");
place("payload_box", "refs.scad", "which=\"payload_box\"", [-12, 0, -plate_t - 71 - 9.5 - 20], [0, 0, 0], "ref") ref("payload_box");
place("fpv_mount", "fpv_mount.scad", "", [fpv_pos[0], 0, -plate_t]) fpv_mount();
place("fpv_cam", "refs.scad", "which=\"fpv_cam\"", [fpv_pos[0] + 2, 0, -plate_t - 18], [0, 20, 0], "ref") ref("fpv_cam");
for (k = [0 : 3]) {
    sx = k < 2 ? 1 : -1; sy = k % 2 == 0 ? 1 : -1;
    t_rot = sy > 0 ? 0 : 180;                     // las del lado −y van giradas 180°
    place(str("gear_mount_", k), "gear_mount.scad", "", [sx * leg_x, sy * leg_y_top, -plate_t], [0, 0, t_rot]) gear_mount();
    place(str("leg_tube_", k), "leg_tube.scad", "",
          [sx * leg_x, sy * (leg_y_top + leg_in_top * sin(leg_tilt)), -plate_t - 6 - leg_in_top * cos(leg_tilt)],
          [sy * leg_tilt, 0, 0]) leg_tube();
    place(str("skid_tee_", k), "skid_tee.scad", "", [sx * leg_x, sy * skid_y, skid_z], [0, 0, t_rot]) skid_tee();
    place(str("skid_pad_", k), "skid_pad.scad", "", [sx * (skid_len / 2 - 60), sy * skid_y, skid_z]) skid_pad();
}
for (s = [0 : 1]) place(str("skid_tube_", s), "skid_tube.scad", "", [0, (s == 0 ? 1 : -1) * skid_y, skid_z]) skid_tube();
