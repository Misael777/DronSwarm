// DronSwarm · librería común de piezas del frame (S07-S08). Unidades: mm.
//
// Reglas (ADR-003): sin hull()/minkowski()/offset() — FreeCAD los convierte en malla y el STEP deja de ser un
// sólido válido. Las formas redondeadas se arman con uniones de cubos y cilindros. El importador CSG de FreeCAD
// también falla con booleanas 2D y con varios operandos agrupados bajo una sola transformación: cada grupo de
// agujeros debe ser hijo directo del difference(), con su propio translate.
//
// Interfaz de motor DronSwarm (DMI, ADR-011): placa con 4 ranuras radiales a 90°, de modo que el mismo soporte
// acepta varios patrones comerciales y, más adelante, el motor propio (S17+) se diseña para caer en el mismo rango.
//   DMI-S: 4×M3, círculo de tornillos Ø16-Ø25 (motores 28xx-41xx, ≤ 600 W)
//   DMI-L: 4×M4, círculo de tornillos Ø30-Ø42 (motores 50xx-70xx, ≤ 2 kW)

$fn = 48;

M3 = 3.3; M3_HEAD = 6.0; M3_NUT = 6.4;     // pasante, cabeza, tuerca (entre caras + juego)
M4 = 4.4; M4_HEAD = 7.5;
M5 = 5.4;

function dmi_bolt(iface) = iface == "L" ? M4 : M3;
function dmi_r(iface) = iface == "L" ? [15, 21] : [8, 12.5];   // radio mínimo y máximo de las ranuras
function dmi_plate_d(iface) = iface == "L" ? 56 : 36;
function dmi_center(iface) = iface == "L" ? 16 : 10;            // eje, seguro y paso de cables

// Rectángulo con esquinas redondeadas (2D) y su extrusión
module rrect2d(size, r) {
    r2 = min(r, size[0] / 2 - 0.01, size[1] / 2 - 0.01);
    union() {
        translate([r2, 0]) square([size[0] - 2 * r2, size[1]]);
        translate([0, r2]) square([size[0], size[1] - 2 * r2]);
        for (x = [r2, size[0] - r2], y = [r2, size[1] - r2]) translate([x, y]) circle(r = r2);
    }
}
// Caja redondeada con primitivas 3D (sin booleanas 2D: el importador CSG de FreeCAD falla con ellas)
module rbox(size, r) {
    r2 = min(r, size[0] / 2 - 0.01, size[1] / 2 - 0.01);
    union() {
        translate([r2, 0, 0]) cube([size[0] - 2 * r2, size[1], size[2]]);
        translate([0, r2, 0]) cube([size[0], size[1] - 2 * r2, size[2]]);
        for (x = [r2, size[0] - r2], y = [r2, size[1] - r2]) translate([x, y, 0]) cylinder(r = r2, h = size[2]);
    }
}
module crbox(size, r) { translate([-size[0] / 2, -size[1] / 2, 0]) rbox(size, r); }   // centrado en x/y

// Ranura (2D) entre dos puntos sobre el eje x
module slot2d(r0, r1, w) {
    union() {
        translate([r0, -w / 2]) square([r1 - r0, w]);
        translate([r0, 0]) circle(d = w);
        translate([r1, 0]) circle(d = w);
    }
}

// Agujeros de la interfaz de motor (para restar de una placa de espesor t)
module slot3d(r0, r1, w, h) {
    union() {
        translate([r0, -w / 2, 0]) cube([r1 - r0, w, h]);
        translate([r0, 0, 0]) cylinder(d = w, h = h);
        translate([r1, 0, 0]) cylinder(d = w, h = h);
    }
}
module dmi_holes(iface, t) {
    r = dmi_r(iface);
    translate([0, 0, -1]) union() {
        cylinder(d = dmi_center(iface), h = t + 2);
        for (a = [45, 135, 225, 315]) rotate(a) slot3d(r[0], r[1], dmi_bolt(iface), t + 2);
    }
}

// Soporte de motor en la punta del brazo: manguito sobre el tubo + placa DMI arriba
//   el tubo entra por -x; la placa queda centrada en el eje del motor (origen), cara superior en z = 0
module motor_mount(tube_d, iface = "S", sleeve = 34, wall = 3.5) {
    od = tube_d + 2 * wall;
    pd = dmi_plate_d(iface);
    pt = iface == "L" ? 6 : 4;
    zc = -pt - tube_d / 2 - 1;                 // eje del tubo bajo la placa
    difference() {
        union() {
            translate([0, 0, -pt]) cylinder(d = pd, h = pt);                         // placa DMI
            translate([-sleeve - pd / 2 + 6, 0, zc]) rotate([0, 90, 0])
                cylinder(d = od, h = sleeve + pd / 2 - 6 + 4);                       // manguito
            translate([-sleeve - pd / 2 + 6, -od / 2, zc]) cube([sleeve + pd / 2 - 2, od, -zc - pt + 0.01]);  // alma
            translate([-sleeve - pd / 2 + 6, -5, zc - od / 2 - 7]) cube([sleeve, 10, 8]);   // oreja de apriete
        }
        dmi_holes(iface, pt + 0.02, $fn = 32);
        translate([-sleeve - pd / 2 + 5, 0, zc]) rotate([0, 90, 0]) cylinder(d = tube_d + 0.3, h = sleeve + pd / 2 - 3); // tubo
        translate([-sleeve - pd / 2 + 4, -1, zc - od / 2 - 8]) cube([sleeve + 1, 2, od / 2 + 6]);   // ranura de apriete
        for (x = [0.3, 0.75]) translate([-sleeve - pd / 2 + 6 + x * sleeve, 0, zc - od / 2 - 3])
            rotate([90, 0, 0]) cylinder(d = M3, h = 30, center = true);                // tornillos de apriete
        translate([-pd / 2 - 2, 0, zc]) rotate([0, 90, 0]) cylinder(d = 7, h = pd);   // salida de cables del tubo
    }
}

// Bloque de brazo entre las dos placas centrales (impreso PA12-CF): sujeta el tubo y separa las placas.
//   el tubo sale por +x desde el origen; el bloque ocupa x ∈ [-len, 0], altura = gap
module arm_block(tube_d, gap, len = 40, width = 0, bolt = M3) {
    w = width > 0 ? width : tube_d + 14;
    difference() {
        translate([-len, -w / 2, 0]) rbox([len, w, gap], 2);
        translate([-len - 1, 0, gap / 2]) rotate([0, 90, 0]) cylinder(d = tube_d + 0.2, h = len + 2);   // tubo
        translate([-len - 1, -0.75, gap / 2]) cube([len + 2, 1.5, gap / 2 + 1]);                        // ranura de apriete
        for (p = arm_block_bolts(tube_d, len, w)) translate([p[0], p[1], -1]) cylinder(d = bolt, h = gap + 2);
        translate([-len * 0.5, 0, gap * 0.78]) rotate([90, 0, 0]) cylinder(d = M3, h = w + 2, center = true);  // apriete
    }
}
function arm_block_bolts(tube_d, len, w) =
    [for (x = [-len + 6, -6], y = [-(w / 2 - 3.6), w / 2 - 3.6]) [x, y]];

// Patrón de controladora de vuelo (agujeros M3 en cuadrado)
module fc_holes(pattern, t) {
    for (x = [-1, 1], y = [-1, 1]) translate([x * pattern / 2, y * pattern / 2, -1]) cylinder(d = M3, h = t + 2);
}
