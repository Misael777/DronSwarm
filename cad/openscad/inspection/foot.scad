// DS-I · pie amortiguador de la pata (impreso TPU 85A, relleno giroide 15 %, 2 perímetros, ×4).
// Es el elemento elástico del tren: ≈ 30 mm de carrera útil, rigidez ≈ 30 N/mm. Con un pie macizo de TPU 95A el
// tren queda casi rígido (≈ 750 N/mm) y una caída de 1 m daría ≈ 4.5 kN por pata (ver docs/ingenieria/fea_frames.md).
// Local: el tubo de la pata encaja desde z = 0 hacia abajo (12 mm); el pie llega a z = −foot_h.
include <ds_i_frame.scad>
module foot() difference() {
    union() {
        translate([0, 0, -14]) cylinder(d = leg_tube + 8, h = 14);
        translate([0, 0, -foot_h]) cylinder(d1 = 34, d2 = 26, h = foot_h - 14);
    }
    translate([0, 0, -12]) cylinder(d = leg_tube + 0.2, h = 13);
}
foot();
