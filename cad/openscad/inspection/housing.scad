// DS-I · carcasa IP54 de la electrónica (impresa PA12-CF o ASA, paredes 2.0 mm, ≥ 5 perímetros) sobre la placa
// superior. IP54: junta de EPDM Ø2 mm en un canal de la brida, 8 tornillos M3 con arandela de nylon, prensaestopa M12
// para cables, ventila de membrana M12 (ePTFE) para igualar presión, y un domo para el GNSS arriba.
// Dentro: controladora (sobre amortiguadores de goma), ESC 4 en 1, computadora a bordo y radio.
// Local: brida apoyada en z = 0, centrada en el origen.
include <ds_i_frame.scad>
wall = 2.0;                                 // ≥ 5 perímetros de 0.4 mm
module housing() {
    L = housing_size[0]; W = housing_size[1]; H = housing_size[2];
    difference() {
        union() {
            crbox([L, W, H], 10);
            crbox([L + 2 * housing_flange, W + 2 * housing_flange, 4], 12);                     // brida
            translate([10, 0, H]) cylinder(d = 46, h = 6);                                        // base del GNSS
        }
        translate([0, 0, -1]) crbox([L - 2 * wall, W - 2 * wall, H - wall + 1], 8);            // interior
        for (p = housing_bolts) translate([p[0], p[1], -1]) cylinder(d = M3, h = 6);
        // canal de la junta (Ø2 mm EPDM) en la cara inferior de la brida, entre la pared y los tornillos
        difference() {
            translate([0, 0, -1]) crbox([L + 5.2, W + 5.2, 2.6], 11);
            translate([0, 0, -2]) crbox([L + 1.2, W + 1.2, 5], 11);
        }
        translate([-L / 2 - 1, -W / 4, H * 0.55]) rotate([0, 90, 0]) cylinder(d = 12.2, h = wall + 2);   // ventila de membrana M12
        translate([10, 0, H - wall - 1]) cylinder(d = 10, h = wall + 8);                        // cable del GNSS
    }
}
housing();
