// Biblioteca del motor DronSwarm (M6). Las medidas vienen de <dron>_motor_params.scad (generado). Unidades: mm.
// Sin hull/minkowski (CLAUDE.md): todo con cilindros, polígonos y extrusiones.
$fn = 160;

// ---------- láser ----------
module stator_lamination_2d() {           // lámina del estator: 0.2 mm de acero al silicio (NO20)
    difference() {
        circle(r = r_s);
        circle(r = r_bore);
        for (s = slots) polygon(s);
        translate([r_bore - 0.01, -1.0]) square([1.2, 2.0]);                 // chaveta: alinea las láminas y fija al tubo
    }
}
module rotor_ring_2d() {                  // anillo del rotor: acero común 1 mm, se apilan n_ring
    difference() {
        circle(r = r_out);
        circle(r = r_mag_out + fit_slide / 2);
        translate([r_mag_out, -0.75]) square([0.8, 1.5]);                     // marca de orientación (polo 1)
    }
}

// ---------- impresas ----------
module cap() {                            // tapa: lleva la hélice y el eje; el anillo del rotor entra 2 mm en la ranura
    hub_r = shaft / 2 + 3.5;
    difference() {
        union() {
            cylinder(r = r_out + 1.2, h = cap_t);
            translate([0, 0, -2]) difference() {                                 // pollera que abraza el anillo
                cylinder(r = r_out + 1.2, h = 2);
                translate([0, 0, -0.1]) cylinder(r = r_out + print_clear / 2, h = 2.2);
            }
            cylinder(r = hub_r, h = cap_t + 4);                                  // cubo del eje
        }
        translate([0, 0, -1]) cylinder(d = shaft + fit_press, h = cap_t + 6);   // eje a presión
        translate([0, 0, cap_t + 2]) rotate([0, 90, 0]) cylinder(d = 2.6, h = hub_r + 1);   // prisionero M3
        for (i = [0 : prop_n - 1]) rotate(360 / prop_n * i + 45)
            translate([prop_pcd / 2, 0, -1]) cylinder(d = prop_bolt, h = cap_t + 6);
        for (i = [0 : prop_n - 1]) rotate(360 / prop_n * i)                      // ventilación entre los tornillos de la hélice
            translate([0, 0, -1]) linear_extrude(cap_t + 2)
                polygon([[ (hub_r + 2) * cos(-14), (hub_r + 2) * sin(-14)], [ (r_mag_in - 3) * cos(-18), (r_mag_in - 3) * sin(-18)],
                         [ (r_mag_in - 3) * cos(18), (r_mag_in - 3) * sin(18)], [ (hub_r + 2) * cos(14), (hub_r + 2) * sin(14)]]);
    }
}

module base() {                           // base: tubo con los 2 rodamientos, sostiene el estator, se atornilla al DMI
    tube_h = l_stack + 2 * overhang + 1;
    difference() {
        union() {
            cylinder(r = max(r_bore + 5, dmi_pcd / 2 + 4), h = base_t);
            cylinder(r = r_bore + fit_press / 2, h = base_t + tube_h);               // el estator se pega sobre el tubo
            translate([r_bore - 0.2, -0.9, base_t]) cube([1.0, 1.8, tube_h]);        // chaveta (entra en la muesca de las láminas)
        }
        translate([0, 0, -1]) cylinder(d = bearing_od + fit_press, h = bearing_w + 1);                  // rodamiento inferior
        translate([0, 0, base_t + tube_h - bearing_w]) cylinder(d = bearing_od + fit_press, h = bearing_w + 1); // superior
        translate([0, 0, -1]) cylinder(d = shaft + 1.0, h = base_t + tube_h + 2);
        for (i = [0 : dmi_n - 1]) rotate(360 / dmi_n * i + 45) translate([dmi_pcd / 2, 0, -1]) cylinder(d = dmi_bolt, h = base_t + 2);
        translate([r_bore - 4, -2, -1]) cube([6, 4, base_t + 2]);                 // salida de los 3 cables de fase
    }
}

module magnet_jig() {                     // peine: se mete dentro del anillo y deja cada imán en su lugar (paso de polo exacto)
    rib = 2 * PI * r_mag_in / poles - magnet_w;      // espacio entre imanes en el diámetro interior
    difference() {
        union() {
            cylinder(r = r_mag_in - 0.15, h = l_stack + 4);
            for (i = [0 : poles - 1]) rotate(360 / poles * (i + 0.5))
                translate([r_mag_in - 0.5, -max(rib, 0.6) / 2, 0]) cube([h_magnet + 0.3, max(rib, 0.6) - 0.15, l_stack + 4]);
        }
        translate([0, 0, -1]) cylinder(r = r_mag_in - 3, h = l_stack + 6);
    }
}

module stack_mandrel() {                  // mandril de apilado: alinea las láminas por el agujero y la chaveta mientras cura el adhesivo
    difference() {
        union() {
            cylinder(r = r_bore - 0.05, h = l_stack + 10);
            translate([r_bore - 0.3, -0.9, 0]) cube([1.0, 1.8, l_stack + 10]);
            cylinder(r = r_s + 3, h = 3);
        }
        translate([0, 0, -1]) cylinder(d = 5.5, h = l_stack + 12);                // varilla roscada M5 para prensar
    }
}

module winding_holder() {                 // soporte para bobinar a mano: sujeta el estator por el agujero, con mango
    union() {
        cylinder(r = r_bore - 0.1, h = l_stack + 2);
        translate([r_bore - 0.4, -0.85, 0]) cube([1.0, 1.7, l_stack + 2]);
        translate([0, 0, -40]) cylinder(r = 7, h = 40);
    }
}

// ---------- ensamble (para ver) ----------
module assembly() {
    color("#b0b0b0") translate([0, 0, base_t + overhang]) linear_extrude(l_stack) stator_lamination_2d();
    color("#b87333") for (s = slots) translate([0, 0, base_t + 0.5]) linear_extrude(l_stack + 2 * overhang - 1) offset(r = -0.35) polygon(s);
    color("#4a4a4a") translate([0, 0, base_t + overhang - 1]) linear_extrude(l_stack + 2) rotor_ring_2d();
    color("#2a78d6") for (i = [0 : poles - 1]) rotate(360 / poles * i)
        translate([0, 0, base_t + overhang]) rotate_extrude(angle = 360 / poles * pole_arc)
            translate([r_mag_in, 0]) square([h_magnet, l_stack]);
    color("#eb6834") translate([0, 0, base_t + 2 * overhang + l_stack + 1]) cap();
    color("#eb6834", 0.9) base();
    color("#dddddd") translate([0, 0, -6]) cylinder(d = shaft, h = base_t + 2 * overhang + l_stack + cap_t + 14);
}
