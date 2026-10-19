// DS-D · soporte de motor DMI-L (4×M4 en Ø30-42; impreso PA12-CF, ×6). Local: eje del motor en el origen,
// cara de apoyo en z = 0, el tubo entra desde −x.
include <ds_d_frame.scad>
motor_mount(tube_od, motor_iface, sleeve = mm_sleeve, wall = 4);
