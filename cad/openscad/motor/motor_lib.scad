// Biblioteca mecánica del motor DronSwarm (M6). Medidas de <dron>_motor_params.scad (generado). Unidades: mm.
// z = 0 en la cara de montaje de la base. Sin hull/minkowski (CLAUDE.md): perfiles de revolución, polígonos y extrusiones.
// Ajustes y cadena de tolerancias: motor/fabricacion/tolerancias.md. Agujeros impresos: nominal + hole_comp (calibrar).
$fn = 120;
r_t = r_s - h_tip;  r_b = r_t - h_slot;
function hd(d) = d + hole_comp;                           // diámetro a modelar para un agujero impreso
R_seat = hd(brg_D + fit_bearing_seat) / 2;
R_sh = (brg_Da - 0.2) / 2;
R_bore_cap = hd(shaft + fit_shaft_in_cap) / 2;
R_skirt_in = hd(2 * r_out + fit_ring_in_skirt) / 2;
r_cap = r_out + fit_ring_in_skirt / 2 + 1.6;
R_sp = wave_D / 2;
R_rec = hd(shim_D + 0.6) / 2;
half_pitch = 180 / ns;
pole_half = 180 / poles;

// ===================== LÁSER (DXF) =====================
module stator_lamination_2d() {           // 0.20 mm NO20. Esquinas de ranura con radio 0.3 (incluido en "slots")
    difference() {
        circle(r = r_s);
        circle(r = r_bore);
        for (s = slots) polygon(s);
        translate([r_bore - 0.01, -key_w / 2]) square([key_depth, key_w]);              // muesca de chaveta
    }
}
module rotor_ring_2d() {                  // 1.0 mm DC01. Interior poligonal: una cara plana por imán (asiento y ubicación)
    apo = r_mag_out + 0.05;                                                           // 0.05: juego para el epoxi
    difference() {
        circle(r = r_out);
        rotate(pole_half) circle(r = apo / cos(pole_half), $fn = poles);              // caras planas centradas en los polos
        for (a = [0, 180]) rotate(a + pole_half) translate([r_out, 0]) circle(r = 0.5, $fn = 24);   // muescas de alineación
        rotate(pole_half) translate([r_out - 0.6, -0.4]) square([0.8, 0.8]);          // marca del polo 1 (orientación)
    }
}

// ===================== PERFILES DE REVOLUCIÓN =====================
module base_body() {
    ch = chamfer;
    rotate_extrude() polygon([
        [R_seat + lead_in, 0], [r_flange - ch, 0], [r_flange, ch], [r_flange, base_t - ch], [r_flange - ch, base_t],
        [r_shoulder, base_t], [r_shoulder, z_s0], [r_tube, z_s0], [r_tube, z_tube - 0.3], [r_tube - 0.3, z_tube],
        [R_seat + lead_in, z_tube], [R_seat, z_tube - lead_in], [R_seat, z_tube - brg_B], [R_sh, z_tube - brg_B],
        [R_sh, h_low + brg_B], [R_seat, h_low + brg_B], [R_seat, lead_in]]);
}
module base() {                           // PETG/ASA/PA-CF. Imprimir con la brida sobre la cama
    difference() {
        union() {
            base_body();
            for (a = [0]) rotate(a) translate([r_tube - 0.3, -(key_w - fit_key) / 2, z_s0])   // chaveta del estator
                cube([key_depth - 0.2 + 0.3, key_w - fit_key, z_tube - z_s0 - 0.5]);
        }
        for (i = [0 : dmi_n - 1]) rotate(360 / dmi_n * i + 45)                         // insertos roscados desde abajo
            translate([dmi_pcd / 2, 0, -0.01]) cylinder(d = hd(ins_hole), h = ins_depth);
        for (i = [0 : dmi_n - 1]) rotate(360 / dmi_n * i + 45)
            translate([dmi_pcd / 2, 0, -0.01]) cylinder(d1 = hd(ins_hole) + 0.8, d2 = hd(ins_hole), h = 0.4);
        // canal de los 3 cables de fase, con chaflán en los bordes
        rotate(180) translate([r_tube - 1.5, -wire_ch_w / 2, base_t - wire_ch_d]) cube([r_flange, wire_ch_w, wire_ch_d + 1]);
        rotate(180) for (sgn = [-1, 1]) translate([r_tube - 1.5, sgn * wire_ch_w / 2, base_t]) rotate([45 * sgn, 0, 0])
            translate([0, -0.4, -0.4]) cube([r_flange, 0.8, 0.8]);
        if (r_tube - R_sh > 7) for (i = [0 : 5]) rotate(30 + 60 * i)                    // alivianado (DS-D)
            translate([(r_tube + R_sh) / 2, 0, base_t + 1.0]) cylinder(d = r_tube - R_sh - 3.0, h = z_tube);
    }
}

module cap_body() {
    ch = chamfer;
    rotate_extrude() polygon([
        [R_bore_cap, z_sp], [R_sp, z_sp], [R_sp, z_cap], [r_mag_in + 0.3, z_cap], [r_mag_in + 0.3, z_r1],
        [R_skirt_in, z_r1], [R_skirt_in, z_r1 - skirt_l + lead_in], [R_skirt_in + lead_in, z_r1 - skirt_l],
        [r_cap - ch, z_r1 - skirt_l], [r_cap, z_r1 - skirt_l + ch], [r_cap, z_cap + cap_t - ch], [r_cap - ch, z_cap + cap_t],
        [r_plateau, z_cap + cap_t], [r_plateau, z_pt - ch], [r_plateau - ch, z_pt], [R_rec, z_pt], [R_rec, z_rb],
        [R_bore_cap, z_rb]]);
}
module cap() {                            // tapa: hélice + eje (agujero en D) + anillo del rotor. Imprimir boca abajo
    difference() {
        union() {
            cap_body();
            // plano del agujero en D: bloquea el giro de la tapa sobre el eje
            intersection() {
                translate([0, 0, z_sp]) cylinder(r = R_bore_cap + 0.01, h = z_rb - z_sp);
                translate([shaft / 2 - flat + hole_comp / 2, -10, z_sp]) cube([10, 20, z_rb - z_sp]);
            }
        }
        for (i = [0 : prop_n - 1]) rotate(360 / prop_n * i + 45)                     // insertos de la hélice (desde arriba)
            translate([prop_pcd / 2, 0, z_pt - ins_depth]) cylinder(d = hd(ins_hole), h = ins_depth + 0.01);
        for (i = [0 : prop_n - 1]) rotate(360 / prop_n * i + 45)
            translate([prop_pcd / 2, 0, z_pt - 0.4]) cylinder(d1 = hd(ins_hole), d2 = hd(ins_hole) + 0.8, h = 0.41);
        for (i = [0 : 5]) rotate(60 * i)                                                // ventilación
            translate([0, 0, z_cap - 0.01]) linear_extrude(cap_t + 0.02) polygon(concat(
                [for (a = [-20 : 5 : 20]) [(r_plateau + 1.2) * cos(a), (r_plateau + 1.2) * sin(a)]],
                [for (a = [20 : -5 : -20]) [(r_mag_in - 1.2) * cos(a), (r_mag_in - 1.2) * sin(a)]]));
    }
}

module shaft_part() {                     // acero plata h6, ranuras DIN 6799, plano para la tapa, chaflanes 0.3 × 45°
    R = shaft / 2; Rg = clip_groove_d / 2; c0 = 0.3;
    difference() {
        rotate_extrude($fn = 64) polygon([
            [0, shaft_bot], [R - c0, shaft_bot], [R, shaft_bot + c0], [R, z_g1], [Rg, z_g1], [Rg, z_g1 + clip_m], [R, z_g1 + clip_m],
            [R, z_g2], [Rg, z_g2], [Rg, z_g2 + clip_m], [R, z_g2 + clip_m], [R, shaft_top - c0], [R - c0, shaft_top], [0, shaft_top]]);
        translate([R - flat, -R - 1, z_sp]) cube([R, 2 * R + 2, z_rb - z_sp]);
    }
}

// ===================== NORMALIZADOS (para el ensamble) =====================
module bearing_part() {                   // rodamiento rígido de bolas con tapas ZZ
    t = (brg_D - brg_d) / 2;
    rotate_extrude($fn = 64) {
        translate([brg_d / 2, 0]) square([t * 0.32, brg_B]);
        translate([brg_D / 2 - t * 0.32, 0]) square([t * 0.32, brg_B]);
        translate([brg_d / 2 + t * 0.32, 0.15]) square([t * 0.36, 0.25]);
        translate([brg_d / 2 + t * 0.32, brg_B - 0.4]) square([t * 0.36, 0.25]);
    }
}
module washer(d, D, t) { linear_extrude(t) difference() { circle(d = D, $fn = 48); circle(d = d, $fn = 32); } }
module e_clip() {
    linear_extrude(clip_s) difference() {
        circle(d = clip_od, $fn = 48); circle(d = clip_groove_d, $fn = 32);
        polygon([[0, 0], [clip_od, -clip_od * 0.45], [clip_od, clip_od * 0.45]]);
    }
}
module insert_part() { color("#c9a227") cylinder(d = ins_hole + 0.2, h = ins_depth - 1.0, $fn = 24); }

// ===================== BOBINADO Y ROTOR (para el ensamble) =====================
module coil_end(j) {
    phi = 360 * j / ns;
    intersection() {
        difference() { circle(r = r_t - 0.25); circle(r = r_b + 0.25); }
        polygon([[0, 0], [2 * r_s * cos(phi - half_pitch * 0.98), 2 * r_s * sin(phi - half_pitch * 0.98)],
                 [2 * r_s * cos(phi), 2 * r_s * sin(phi)], [2 * r_s * cos(phi + half_pitch * 0.98), 2 * r_s * sin(phi + half_pitch * 0.98)]]);
    }
}
module winding() {
    for (j = [0 : ns - 1]) {
        ph = coils[j];
        col = (ph == "A" || ph == "a") ? "#2a78d6" : (ph == "B" || ph == "b") ? "#eb6834" : "#1baf7a";
        color(col) {
            translate([0, 0, z_s0]) linear_extrude(l_stack) offset(r = -0.12) {
                polygon(halves[2 * j]); polygon(halves[2 * ((j - 1 + ns) % ns) + 1]);
            }
            translate([0, 0, z_s0 - overhang + 0.2]) linear_extrude(overhang - 0.2) offset(r = -0.12) coil_end(j);
            translate([0, 0, z_s1]) linear_extrude(overhang - 0.2) offset(r = -0.12) coil_end(j);
        }
    }
}
module magnets() {                        // bloques planos apoyados en las caras del anillo poligonal
    for (k = [0 : poles - 1]) rotate(360 * k / poles)
        color(k % 2 == 0 ? "#d55181" : "#6250d6")
            translate([r_mag_out - h_magnet, -magnet_w / 2, z_s0]) cube([h_magnet, magnet_w, l_stack]);
}

// ===================== ÚTILES (impresos) =====================
module magnet_jig() {                     // peine: centra cada imán en su cara plana (polaridad alternada: ver brújula)
    rib = 2 * (r_mag_out - h_magnet) * tan(pole_half) - magnet_w;
    difference() {
        union() {
            cylinder(r = r_mag_out - h_magnet - 0.15, h = l_stack + 4);
            for (i = [0 : poles - 1]) rotate(360 / poles * (i + 0.5))
                translate([r_mag_out - h_magnet - 0.5, -max(rib - 0.15, 0.5) / 2, 0]) cube([h_magnet + 0.3, max(rib - 0.15, 0.5), l_stack + 4]);
        }
        translate([0, 0, -1]) cylinder(r = r_mag_out - h_magnet - 3, h = l_stack + 6);
    }
}
module ring_glue_jig() {                  // concentricidad: centra el anillo (por su exterior) con el eje de la tapa (por el agujero)
    h = z_r1 - z_r0 - 1;
    difference() {
        union() { cylinder(r = r_out + 3, h = 3); cylinder(r = r_out + 3, h = 3 + h); }
        translate([0, 0, 3]) cylinder(r = hd(2 * r_out + 0.05) / 2, h = h + 1);       // copa: aloja el anillo
    }
    cylinder(d = shaft - 0.02, h = 3 + h + (z_pt - z_r1) + 6);                         // perno: entra en el agujero de la tapa
}
module stack_mandrel() {                  // apilado de láminas: chaveta + varilla M5 para prensar
    difference() {
        union() {
            cylinder(r = r_bore - 0.05, h = l_stack + 10);
            translate([r_bore - 0.3, -(key_w - fit_key) / 2, 0]) cube([key_depth - 0.2 + 0.3, key_w - fit_key, l_stack + 10]);
            cylinder(r = r_s + 3, h = 3);
        }
        translate([0, 0, -1]) cylinder(d = hd(5.0), h = l_stack + 12);
    }
}
module winding_holder() {                 // sujeta el estator por el agujero y la chaveta; mango para la morsa
    union() {
        cylinder(r = r_bore - 0.1, h = l_stack + 2);
        translate([r_bore - 0.4, -(key_w - fit_key) / 2, 0]) cube([key_depth - 0.2 + 0.4, key_w - fit_key, l_stack + 2]);
        translate([0, 0, -40]) cylinder(r = 7, h = 40);
    }
}
module fit_coupon() {                     // probeta de ajustes: imprimir y probar rodamiento, eje e inserto; elegir hole_comp
    offs = [-0.10, -0.05, 0.00, 0.05, 0.10, 0.15];
    difference() {
        translate([0, 0, 0]) cube([len(offs) * (brg_D + 5) + 4, 2 * (brg_D + 6), 6]);
        for (i = [0 : len(offs) - 1]) {
            x = 2 + (brg_D + 5) * (i + 0.5);
            translate([x, brg_D / 2 + 4, -0.1]) cylinder(d = brg_D + fit_bearing_seat + offs[i], h = 6.2);
            translate([x, 1.5 * brg_D + 8, -0.1]) cylinder(d = shaft + offs[i], h = 6.2);
            translate([x - 1.5, 0.6, 5.4]) linear_extrude(0.7) text(str(offs[i] * 100), size = 2.2, halign = "center");
        }
    }
}

// ===================== ENSAMBLE =====================
module stator_stack() { color("#9aa0a6") translate([0, 0, z_s0]) linear_extrude(l_stack) stator_lamination_2d(); }
module rotor_ring() { color("#4a4a4a") translate([0, 0, z_r0]) linear_extrude(z_r1 - z_r0) rotor_ring_2d(); }
module keep_half() { translate([-200, -400, -50]) cube([400, 400, 400]); }      // conserva y < 0 (corte por el plano XZ)
module show(col, cut) {                   // cada pieza se corta y se pasa a malla por separado: el corte se ve con colores
    if (cut) color(col) render(convexity = 8) intersection() { children(); keep_half(); }
    else color(col) children();
}
module assembly(explode = 0, cut = false) {
    e = explode;
    show("#f2a65a", cut) base();
    for (i = [0 : dmi_n - 1]) show("#c9a227", cut) rotate(360 / dmi_n * i + 45) translate([dmi_pcd / 2, 0, 0.6 - e * 0.3]) insert_part();
    show("#c0c4c8", cut) translate([0, 0, h_low - e * 0.6]) bearing_part();
    show("#c0c4c8", cut) translate([0, 0, z_tube - brg_B + e * 0.2]) bearing_part();
    show("#8a8f94", cut) translate([0, 0, h_low - shim_t - e * 0.8]) washer(shim_d, shim_D, shim_t);
    show("#5f6368", cut) translate([0, 0, z_g1 - e * 1.0]) e_clip();
    show("#9aa0a6", cut) translate([0, 0, e * 0.6]) stator_stack();
    translate([0, 0, e * 0.6]) if (cut) render(convexity = 8) intersection() { winding(); keep_half(); } else winding();
    show("#8a8f94", cut) translate([0, 0, z_tube + e * 1.0]) washer(shim_d, shim_D, shim_t);
    show("#b0b4b8", cut) translate([0, 0, z_tube + shim_t + e * 1.1]) washer(wave_d, wave_D, wave_h_work);
    show("#3a3a3a", cut) translate([0, 0, e * 1.6]) rotor_ring();
    translate([0, 0, e * 1.6]) if (cut) render(convexity = 8) intersection() { magnets(); keep_half(); } else magnets();
    show("#eb6834", cut) translate([0, 0, e * 1.6]) cap();
    for (i = [0 : prop_n - 1]) show("#c9a227", cut) translate([0, 0, e * 1.6]) rotate(360 / prop_n * i + 45)
        translate([prop_pcd / 2, 0, z_pt - ins_depth + 0.2]) insert_part();
    show("#8a8f94", cut) translate([0, 0, z_rb + e * 2.0]) washer(shim_d, shim_D, shim_t);
    show("#5f6368", cut) translate([0, 0, z_g2 + e * 2.1]) e_clip();
    show("#d9d9d9", cut) translate([0, 0, e * 0.3]) shaft_part();
}
