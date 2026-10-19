// DS-I · bloque de brazo entre placas (impreso PA12-CF, ×4). Sujeta el tubo y separa las placas.
// Local: el tubo sale por +x desde x = 0; altura z ∈ [0, plate_gap]. Imprimir de costado (cara y = −w/2 en la cama).
include <ds_i_frame.scad>
arm_block(tube_od, plate_gap, block_len, block_w);
