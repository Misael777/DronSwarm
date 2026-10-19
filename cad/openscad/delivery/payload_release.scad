// DS-D · mecanismo de liberación de la carga, a prueba de fallas (S08-02).
//
// Gancho de aluminio 6061 de 6 mm que gira sobre un perno M5. Un pasador de acero Ø5, empujado por un resorte,
// traba la punta del gancho: SIN ENERGÍA EL GANCHO QUEDA TRABADO. Para soltar, el servo tira del pasador
// (≈ 8 mm) y el peso de la caja abre el gancho; el anillo de la caja se desliza afuera. Un micro-interruptor
// confirma "gancho cerrado" a la controladora (comprobación antes de despegar y confirmación de entrega).
//
//   which = "body" (cuerpo impreso PA12-CF, va al centro de la placa inferior con 4 × M4)
//         | "hook" (gancho, aluminio 6061-T6 de 6 mm, corte por agua o fresado)
// Local: cara de apoyo contra la placa en z = 0; el cuerpo cuelga hacia −z. Pivote del gancho en (−20, 0, −52).
// El servo (tipo estándar 40 × 20 × 38 mm) va adentro, atrás (x > 0), y tira del pasador por una varilla.

include <ds_d_frame.scad>
which = "body";
mode = "3d";                                      // "2d": contorno del gancho para corte por agua/láser (DXF)
rel_h = 62;
hook_t = 6;
pivot = [-20, -52];                               // (x, z) del perno del gancho
latch_z = -46;                                    // eje del pasador de traba (paralelo a x)

module release_body(w = 3) {
    difference() {
        translate([-45, -30, -rel_h]) cube([90, 60, rel_h]);
        // vaciado: carcasa de 3 mm (la carga entra por el perno y sube por las paredes a los 4 × M4)
        translate([-45 + w, -30 + w, -rel_h + w]) cube([90 - 2 * w, 60 - 2 * w, rel_h - 2 * w]);
        for (p = release_bolts) translate([p[0], p[1], -8]) cylinder(d = M4, h = 9);
        translate([-46, -hook_t / 2 - 0.5, -rel_h - 1]) cube([92, hook_t + 1, 30]);          // ranura del gancho
        translate([pivot[0], 0, pivot[1]]) rotate([90, 0, 0]) cylinder(d = 5.3, h = 62, center = true);   // perno M5
        translate([-10, 0, latch_z]) rotate([0, 90, 0]) cylinder(d = 5.2, h = 60);         // guía del pasador
        translate([-46, -11, -30]) cube([6, 22, 12]);                                       // salida de cables
    }
    // columnas de los tornillos (M4 a la placa) y bujes del perno y del pasador
    difference() {
        union() {
            for (p = release_bolts) translate([p[0], p[1], -14]) cylinder(d = 10, h = 14);
            for (y = [-1, 1]) translate([pivot[0], y * (30 - w / 2 - 4), pivot[1]]) rotate([90, 0, 0]) cylinder(d = 12, h = 8 + w, center = true);
            translate([-14, -6, latch_z - 6]) cube([14, 12, 12]);
        }
        for (p = release_bolts) translate([p[0], p[1], -15]) cylinder(d = M4, h = 16);
        translate([pivot[0], 0, pivot[1]]) rotate([90, 0, 0]) cylinder(d = 5.3, h = 62, center = true);
        translate([-11, 0, latch_z]) rotate([0, 90, 0]) cylinder(d = 5.2, h = 24);
        translate([-46, -hook_t / 2 - 0.5, -rel_h - 1]) cube([92, hook_t + 1, 30]);
    }
}

// Perfil del gancho en el plano xz (polígono simple: sin booleanas 2D)
module hook_profile() polygon([
    [-30, -44], [-10, -44], [-10, -50], [18, -50], [18, -44], [26, -44], [26, -58],
    [6, -58], [6, -84], [-30, -84]]);
module release_hook() {
    difference() {
        rotate([90, 0, 0]) translate([0, 0, -hook_t / 2]) linear_extrude(height = hook_t) hook_profile();
        translate([pivot[0], 0, pivot[1]]) rotate([90, 0, 0]) cylinder(d = 5.3, h = 10, center = true);
        translate([-12, 0, -71]) rotate([90, 0, 0]) cylinder(d = 18, h = 10, center = true);   // boca: aquí cuelga el anillo
        translate([-12, -5, -90]) cube([30, 10, 19]);                                        // salida del anillo
    }
}

if (mode == "2d") projection(cut = true) rotate([90, 0, 0]) release_hook();
else if (which == "body") release_body(); else release_hook();
