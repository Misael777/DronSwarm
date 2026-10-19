// DS-D · bandeja de batería sobre la placa superior (impresa PA12-CF). Batería 12S5P transversal (220 mm en y),
// 2 correas con hebilla de leva + topes; 4.7 kg: los topes evitan que se corra en frenadas (5 g de diseño).
// Local: apoyo sobre la placa en z = 0; centrada en battery_pos.
include <ds_d_frame.scad>
tray_t = 3;
module battery_tray() {
    bw = battery_dims[1]; bl = battery_dims[0];
    difference() {
        union() {
            crbox([bw + 14, bl + 14, tray_t], 5);
            for (y = [-1, 1]) translate([-(bw + 14) / 2, y * (bl / 2 + 3.5) - 3.5, 0]) cube([bw + 14, 5, tray_t + 14]);
        }
        for (p = battery_tray_bolts) translate([p[0] - battery_pos[0], p[1], -1]) cylinder(d = M3, h = tray_t + 2);
        for (y = [-1, 1]) translate([-5, y * 55 - 13, -1]) cube([10, 26, tray_t + 2]);      // correas
        for (x = [-1, 1], y = [-1, 1]) translate([x * bw / 4.5, y * bl / 4, -1]) cylinder(d = 40, h = tray_t + 2);
    }
}
battery_tray();
