"""Verificaciones de las netlists versionadas (electronics/kicad/*/*.net) contra hojas de datos y el port de PX4.

No necesitan KiCad: leen las netlists ya generadas por electronics/build_netlists.sh.
"""

import re
from pathlib import Path

import pytest

from electronics.netlist import load, refs_by_value

ROOT = Path(__file__).resolve().parents[2]
BOARDS = ["esc_ds_d", "esc_ds_i", "fc", "gnss", "bms_ds_i", "bms_ds_d", "charger"]

# Números de pin por nombre (símbolos de KiCad 8 de cada encapsulado)
H743_LQFP100 = {"PC13": "7", "PC14": "8", "PC15": "9", "PE4": "3", "PE5": "4", "PE6": "5", "PB2": "36", "PD4": "85",
                "PA8": "67", "PE11": "41", "PE13": "43", "PE14": "44", "PD14": "61", "PD15": "62", "PA0": "22", "PA1": "23",
                "PC6": "63", "PC7": "64", "PB9": "96", "PD10": "57", "PD11": "58"}
G071_QFN32 = {"PA10": "21", "PB15": "17", "PA9": "19", "PB0": "15", "PA8": "18", "PA7": "14", "PB7": "31", "PA2": "9",
              "PA0": "7", "PA1": "8", "PA3": "10", "PA6": "13", "PB6": "30", "PA4": "11", "PA5": "12"}


def net_with(nets: dict, ref: str, pin: str) -> str:
    hits = [n for n, nodes in nets.items() if any(r == ref and p == pin for r, p, _ in nodes)]
    assert len(hits) == 1, f"{ref}.{pin} en {hits}"
    return hits[0]


def refs_on(nets: dict, net: str) -> set:
    return {(r, p) for r, p, _ in nets[net]}


@pytest.mark.parametrize("board", BOARDS)
def test_netlist_exists_and_no_dangling_power(board):
    parts, nets = load(board)
    assert len(parts) > 20
    for rail in ("GND",):
        assert rail in nets and len(nets[rail]) > 5


def test_fc_spi_matches_px4_port():
    """Los CS/DRDY de spi.cpp del target dronswarm_fmu-v1 son los pines cableados a cada IMU en el esquema."""
    parts, nets = load("fc")
    mcu = refs_by_value(parts, "STM32H743")[0]
    spi = (ROOT / "electronics/fc/px4/boards/dronswarm/fmu-v1/src/spi.cpp").read_text()
    imu = refs_by_value(parts, "IIM-42652")[0]
    bmi = refs_by_value(parts, "BMI088")[0]
    expect = {"DRV_IMU_DEVTYPE_IIM42652": ((imu, "12"), (imu, "4")),     # AP_CS, INT1
              "DRV_ACC_DEVTYPE_BMI088": ((bmi, "14"), (bmi, "16")),      # CSB1, INT1
              "DRV_GYR_DEVTYPE_BMI088": ((bmi, "5"), (bmi, "12"))}       # CSB2, INT3
    for dev, (cs_pin, drdy_pin) in expect.items():
        m = re.search(dev + r", SPI::CS\{GPIO::Port(\w), GPIO::Pin(\d+)\}, SPI::DRDY\{GPIO::Port(\w), GPIO::Pin(\d+)\}", spi)
        assert m, dev
        cs, drdy = f"P{m.group(1)}{m.group(2)}", f"P{m.group(3)}{m.group(4)}"
        assert cs_pin in refs_on(nets, net_with(nets, mcu, H743_LQFP100[cs])), (dev, cs)
        assert drdy_pin in refs_on(nets, net_with(nets, mcu, H743_LQFP100[drdy])), (dev, drdy)
    # Alimentación de sensores conmutada por PB2 (initSPIBus(..., {GPIO::PortB, GPIO::Pin2}))
    assert "{GPIO::PortB, GPIO::Pin2}" in spi
    ldo_en = net_with(nets, mcu, H743_LQFP100["PB2"])
    assert any(parts[r]["value"].startswith("TLV75533") for r, _ in refs_on(nets, ldo_en))


def test_fc_pwm_outputs_match_timer_config():
    parts, nets = load("fc")
    mcu = refs_by_value(parts, "STM32H743")[0]
    tc = (ROOT / "electronics/fc/px4/boards/dronswarm/fmu-v1/src/timer_config.cpp").read_text()
    pins = [f"P{p}{n}" for p, n in re.findall(r"\{GPIO::Port(\w), GPIO::Pin(\d+)\}\)", tc)]
    assert pins == ["PA8", "PE11", "PE13", "PE14", "PD14", "PD15", "PA0", "PA1"]
    for pin in pins:
        n = net_with(nets, mcu, H743_LQFP100[pin])
        res = [r for r, _ in refs_on(nets, n) if r != mcu]
        assert len(res) == 1 and parts[res[0]]["value"] == "47"      # 47 Ω en serie hacia el conector J_PWM


@pytest.mark.parametrize("board,driver_pins", [("esc_ds_d", {"A": ("18", "19")}), ("esc_ds_i", {"A": ("1", "4")})])
def test_esc_am32_phase_a(board, driver_pins):
    """AM32 G0_G: fase A alta = PA10, baja = PB15; llegan a las entradas alta/baja del driver de la fase A."""
    parts, nets = load(board)
    mcu = refs_by_value(parts, "STM32G071")[0]
    hi, lo = net_with(nets, mcu, G071_QFN32["PA10"]), net_with(nets, mcu, G071_QFN32["PB15"])
    hi_pin, lo_pin = driver_pins["A"]
    drv_hi = {r for r, p in refs_on(nets, hi) if p == hi_pin and parts[r]["value"] in ("LMG1210", "DRV8300DPW")}
    drv_lo = {r for r, p in refs_on(nets, lo) if p == lo_pin and parts[r]["value"] in ("LMG1210", "DRV8300DPW")}
    assert drv_hi and drv_hi == drv_lo


def test_esc_ds_i_has_four_channels():
    parts, _ = load("esc_ds_i")
    assert len(refs_by_value(parts, "STM32G071")) == 4
    assert len(refs_by_value(parts, "DRV8300DPW")) == 4
    assert len(refs_by_value(parts, "CSD18503Q5A")) == 24


@pytest.mark.parametrize("board,afe,vc", [
    ("bms_ds_i", "BQ7693003", {"27": 0, "26": 1, "25": 2, "24": 2, "23": 2, "22": 3, "21": 3, "20": 4, "19": 5, "18": 5, "17": 5, "16": 6}),
    ("bms_ds_d", "BQ7694003", {"41": 0, "40": 1, "39": 2, "38": 3, "37": 3, "36": 4, "35": 4, "34": 5, "33": 6, "32": 7, "31": 7,
                               "30": 8, "29": 8, "28": 9, "27": 10, "26": 11, "25": 11, "24": 12}),
])
def test_bms_cell_connections(board, afe, vc):
    """Pines VC del BQ769x0 → nodo de celda según las tablas 9-3 / 9-4 de SLUSBK2I (con Rc de 1 k)."""
    parts, nets = load(board)
    u = refs_by_value(parts, afe)[0]
    for pin, node in vc.items():
        assert net_with(nets, u, pin) == f"VC_N{node}", (pin, node)


def test_gnss_reserved_pins_unconnected():
    parts, nets = load("gnss")
    u = refs_by_value(parts, "LG290P")[0]
    for pin in ("1", "2", "5", "17"):
        assert not any(any(r == u and p == pin for r, p, _ in nodes) for nodes in nets.values())
