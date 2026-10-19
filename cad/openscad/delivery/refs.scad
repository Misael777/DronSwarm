// DS-D · componentes comerciales de referencia (no se fabrican). Medidas típicas; se confirman en S09.
include <ds_d_frame.scad>
which = "motor";
module ref(which) {
    if (which == "motor") cylinder(d = motor_d, h = motor_h);
    if (which == "prop") cylinder(d = prop_d, h = 2, $fn = 120);
    if (which == "battery") crbox([battery_dims[1], battery_dims[0], battery_dims[2]], 5);
    if (which == "fc_stack") crbox([36, 36, 24], 3);
    if (which == "companion") crbox([65, 35, 14], 3);
    if (which == "esc") crbox([60, 28, 14], 3);                 // ESC 80 A por motor, en el espacio entre placas
    if (which == "gnss") cylinder(d = 40, h = 12);
    if (which == "servo") translate([-20, -10, 0]) cube([40, 20, 38]);
    if (which == "fpv_cam") translate([-10, -9.5, -9.5]) cube([20, 19, 19]);
    if (which == "led") cylinder(d = 20, h = 6);
    if (which == "payload_box") union() {                         // caja estándar de 5 kg con anilla
        translate([0, 0, -payload_box[2]]) crbox([payload_box[0], payload_box[1], payload_box[2]], 8);
        cylinder(d = 8, h = 10);                                    // vástago del cáncamo, unido a la anilla
        translate([0, 0, 20]) rotate([0, 90, 0]) difference() { cylinder(d = 24, h = 5, center = true); cylinder(d = 14, h = 7, center = true); }
    }
}
ref(which);
