// DS-I · adaptador de cámara con 4 amortiguadores de silicona (placas impresas PA12-CF). Aísla la cámara de la
// vibración de los motores (1P ≈ 52 Hz en hover): amortiguadores 30-40 Shore A, frecuencia propia ≈ 10-15 Hz.
//   which = "top" (va contra la placa del frame) | "bottom" (lleva la cámara)
// Local: cara superior del adaptador en z = 0; los amortiguadores ocupan z ∈ [−t − damper_h, −t].
include <ds_i_frame.scad>
which = "top";
damper_pts = [for (x = [-1, 1], y = [-1, 1]) [x * 20, y * 25]];
module gimbal_plate(which) {
    if (which == "top")
        difference() {
            translate([0, 0, -gm_t]) crbox([60, 72, gm_t], 5);
            for (p = gimbal_mount_bolts) translate([p[0] - (gimbal_pos[0] - 15), p[1], -gm_t - 1]) cylinder(d = M3, h = gm_t + 2);
            for (p = damper_pts) translate([p[0], p[1], -gm_t - 1]) cylinder(d = M3, h = gm_t + 2);
        }
    else
        difference() {
            translate([15, 0, -2 * gm_t - damper_h]) crbox([90, 72, gm_t], 5);
            for (p = damper_pts) translate([p[0], p[1], -2 * gm_t - damper_h - 1]) cylinder(d = M3, h = gm_t + 2);
            for (y = [-1, 1]) translate([15, y * 31, -2 * gm_t - damper_h - 1]) cylinder(d = M3, h = gm_t + 2);   // cámara
            translate([15, 0, -2 * gm_t - damper_h - 1]) cylinder(d = 20, h = gm_t + 2);       // paso de cable
        }
}
gimbal_plate(which);
