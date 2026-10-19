// DS-I · bandeja de batería bajo la placa inferior (impresa PA12-CF). La batería (6S2P, transversal) se sujeta con
// dos correas con hebilla que pasan por las ranuras de la placa; topes laterales para cambio rápido.
// Local: cara de apoyo contra la placa en z = 0, la batería cuelga hacia −z; centrada en battery_pos.
include <ds_i_frame.scad>
module battery_tray(t = tray_t) {
    bw = battery_dims[1];     // a lo largo de x (la batería va transversal: su largo en y)
    bl = battery_dims[0];
    difference() {
        union() {
            translate([0, 0, -t]) crbox([bw + 12, bl + 12, t], 4);
            for (y = [-1, 1]) translate([-(bw + 12) / 2, y * (bl / 2 + 3) - 3, -t - 12]) cube([bw + 12, 6, 12]);   // topes
        }
        for (p = battery_tray_bolts) translate([p[0] - battery_pos[0], p[1], -t - 1]) cylinder(d = M3, h = t + 2);
        for (y = [-1, 1]) translate([-4, y * 30 - 11, -t - 1]) cube([8, 22, t + 2]);                 // correas
        for (x = [-1, 1], y = [-1, 1]) translate([x * bw / 4.5, y * bl / 4, -t - 1]) cylinder(d = 24, h = t + 2);  // aligeramiento
    }
}
battery_tray();
