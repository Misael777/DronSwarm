// DS-D · bloque de brazo desmontable (impreso PA12-CF, ×6), entre las placas con 6 × M4.
// El tubo entra 54 mm hasta un tope y se fija con 2 levas de apriete rápido (tipo tija de bicicleta) sobre dos
// ranuras; un conector XT60 en la cara interior une los cables del motor. Sin herramientas: ≈ 20 s por brazo.
// Local: el tubo sale por +x desde x = 0; altura z ∈ [0, plate_gap].
include <ds_d_frame.scad>
module arm_socket() {
    difference() {
        translate([-block_len, -block_w / 2, 0]) rbox([block_len, block_w, plate_gap], 3);
        translate([-tube_insert, 0, tube_z]) rotate([0, 90, 0]) cylinder(d = tube_od + 0.25, h = tube_insert + 1);   // tubo
        translate([-block_len - 1, 0, tube_z]) rotate([0, 90, 0]) cylinder(d = 11, h = block_len);                    // cables
        for (x = [-14, -40]) translate([x - 1.5, -block_w / 2 - 1, tube_z]) cube([3, block_w / 2 + 1, plate_gap]);   // ranuras de apriete
        for (x = [-14, -40]) translate([x, -block_w / 2 + 5, tube_z + tube_od / 2 + 2.6]) rotate([90, 0, 0]) cylinder(d = 5.3, h = 30, center = true);   // eje de la leva
        for (p = block_bolts()) translate([p[0], p[1], -1]) cylinder(d = M4, h = plate_gap + 2);
        translate([-block_len + 4, -11, tube_z - 8]) cube([12, 22, 16]);                                                // conector XT60
    }
}
arm_socket();
