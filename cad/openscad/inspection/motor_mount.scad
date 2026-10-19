// DS-I · soporte de motor con interfaz DMI (impreso PA12-CF, ×4). Local: eje del motor en el origen,
// cara de apoyo del motor en z = 0, el tubo entra desde −x.
include <ds_i_frame.scad>
motor_mount(tube_od, motor_iface, sleeve = mm_sleeve);
