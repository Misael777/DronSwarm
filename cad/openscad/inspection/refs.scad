// DS-I · componentes comerciales de referencia (no se fabrican): sirven para holguras, interferencias y masas.
// Medidas típicas de hoja de datos; se confirman en la selección del S09.   which = nombre del componente
include <ds_i_frame.scad>
which = "motor";
module ref(which) {
    if (which == "motor") cylinder(d = motor_d, h = motor_h);                                   // base en z = 0
    if (which == "prop") cylinder(d = prop_d, h = 2, $fn = 96);                                 // disco de la hélice
    if (which == "battery") translate([0, 0, -battery_dims[2]]) crbox([battery_dims[1], battery_dims[0], battery_dims[2]], 4);
    if (which == "gimbal") translate([0, 0, -gimbal_box[2]]) crbox([gimbal_box[0], gimbal_box[1], gimbal_box[2]], 8);
    if (which == "damper") cylinder(d = 9, h = 10);
    if (which == "fc_stack") crbox([36, 36, 24], 3);                                           // FC + ESC 4 en 1
    if (which == "companion") crbox([65, 35, 14], 3);
    if (which == "gnss") cylinder(d = 40, h = 12);
}
ref(which);
