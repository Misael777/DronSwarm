"""E4 · Controladora de vuelo DronSwarm FMU (estándar abierto Pixhawk FMUv6, PX4) → electronics/kicad/fc/fc.net

Pines idénticos a la placa de referencia abierta `px4_fmu-v6c` sin coprocesador PX4IO (boards/px4/fmu-v6c en PX4 v1.15):
el port de PX4 (electronics/fc/px4/) cambia solo lo que difiere (sensores, salidas, RC por UART). Ver
electronics/fc/px4_port.md.

  MCU      STM32H743VIT6 (LQFP-100), cristal 16 MHz (HSE, también reloj del RTC y del FDCAN)
  IMU      SPI1: IIM-42652 (industrial −40/+105 °C, CS PC13, DRDY PE6) + BMI088 (acel. CS PC15 DRDY PE4, giro CS PC14
           DRDY PE5); 3.3 V de sensores conmutado (PB2), calefactor resistivo (PB9) para 45 °C en frío de altura
  I2C4     interno: barómetro MS5611 (0x77), magnetómetro IST8310 (0x0C), EEPROM 24LC64 de calibración (0x50)
  SPI2     FRAM MB85RS256B (parámetros, CS PD4)
  SDMMC2   microSD (logs)
  UART     TELEM1 = UART7 (con control de flujo, Raspberry Pi) · TELEM2 = UART5 (con flujo, RFD900x) · TELEM3 = USART2
           (cámara) · GPS1 = USART1 + I2C1 · GPS2 = UART8 + I2C2 (flujo óptico) · RC = USART6 (CRSF/ELRS) ·
           consola = USART3 (puerto de depuración con SWD)
  CAN      CAN1 (PD0/PD1), CAN2 (PB5/PB13) con TCAN330
  Salidas  8 DShot/PWM: TIM1 CH1-4 (PA8 PE11 PE13 PE14), TIM4 CH3-4 (PD14 PD15), TIM5 CH1-2 (PA0 PA1)
  Energía  2 entradas POWER (5 V + medición de V e I de la batería) con prioridad (TPS2116) + USB-C; periféricos por
           interruptores con límite de 1 A (TPS2561); 3.3 V principal y de sensores (TLV75533)

    source ~/.local/opt/kicad8/env.sh
    .venv/bin/python electronics/skidl/fc.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FP_C0603, FP_C0805, FP_LED, FP_R1206, C, R, finish, nc, nc_net, rail  # noqa: E402
from dsparts import BMI088  # noqa: E402
from skidl import Net, Part, Pin, generate_netlist, subcircuit  # noqa: E402

FP_SOIC8 = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
FP_GH = "Connector_JST:JST_GH_SM{n:02d}B-GHS-TB_1x{n:02d}-1MP_P1.25mm_Horizontal"

gnd = rail("GND")
v5 = rail("5V")             # salida del selector de entradas (TPS2116 + USB)
v5p = rail("5V_PERIPH")     # puertos UART/GPS/RC, 1 A
v5h = rail("5V_HIPOWER")    # puertos CAN, 1 A
v3 = rail("3V3")            # MCU, FRAM, microSD, CAN
v3s = rail("3V3_SENSORS")   # IMU, barómetro, magnetómetro, EEPROM
brick1, brick2, vbus = rail("BRICK1_5V"), rail("BRICK2_5V"), rail("USB_VBUS")


def gh(nets: list, ref: str) -> None:
    """Conector JST-GH (estándar Pixhawk) con las nets en orden de pin."""
    j = Part("Connector_Generic", f"Conn_01x{len(nets):02d}", ref=ref, footprint=FP_GH.format(n=len(nets)))
    for i, n in enumerate(nets, 1):
        j[i] += n


@subcircuit
def mcu_core() -> Part:
    mcu = Part("MCU_ST_STM32H7", "STM32H743VITx")
    mcu["VDD"] += v3
    mcu["VSS"] += gnd
    mcu["VBAT"] += v3                                                  # sin batería de respaldo (RTC desde HSE, como v6c)
    for _ in range(6):
        C("100n")[1, 2] += v3, gnd
    C("4.7u", FP_C0805)[1, 2] += v3, gnd
    vdda = rail("VDDA")
    Part("Device", "FerriteBead_Small", value="600R@100MHz", footprint="Inductor_SMD:L_0603_1608Metric")[1, 2] += v3, vdda
    mcu["VDDA", "VREF+"] += vdda
    mcu["VSSA"] += gnd
    C("1u", FP_C0603)[1, 2] += vdda, gnd
    C("100n")[1, 2] += vdda, gnd
    vcap = Net("VCAP")
    for pin in mcu["VCAP"]:                                            # pines 48 y 73: el mismo nodo interno
        pin.func = Pin.types.PASSIVE
    mcu["VCAP"] += vcap
    for _ in range(2):
        C("2.2u", FP_C0603)[1, 2] += vcap, gnd                         # 2 × 2.2 µF en VCAP (regulador interno LDO)
    nrst = Net("NRST")
    mcu["NRST"] += nrst
    C("100n")[1, 2] += nrst, gnd
    R("10k")[1, 2] += mcu["BOOT0"], gnd
    xin, xout = Net("HSE_IN"), Net("HSE_OUT")
    xtal = Part("Device", "Crystal_GND24", value="16MHz 10pF", footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm")
    xtal[1, 3] += xin, xout
    xtal[2, 4] += gnd
    C("12p/C0G")[1, 2] += xin, gnd
    C("12p/C0G")[1, 2] += xout, gnd
    mcu["PH0"] += xin
    mcu["PH1"] += xout
    return mcu


@subcircuit
def power(mcu: Part) -> None:
    # Selector: POWER1 tiene prioridad; pasa a POWER2 si POWER1 cae bajo 1.0 V × (1 + 35.7k/10k) = 4.57 V
    mux = Part("Power_Management", "TPS2116DRL")
    mux["VIN1", "MODE"] += brick1
    mux["VIN2"] += brick2
    for pin in mux["VOUT"]:                                            # pines 2 y 7: la misma salida
        pin.func = Pin.types.PASSIVE
    mux["VOUT"] += v5
    mux["GND"] += gnd
    pr1 = Net("MUX_PR1")
    R("35.7k")[1, 2] += brick1, pr1
    R("10k")[1, 2] += pr1, gnd
    mux["PR1"] += pr1
    nc(mux, "ST")
    for n in (brick1, brick2):
        C("10u/10V", FP_C0805)[1, 2] += n, gnd
    Part("Device", "D_Schottky", value="PMEG2010", footprint="Diode_SMD:D_SOD-123")["A", "K"] += vbus, v5   # USB como 3ª fuente
    C("22u/10V", FP_C0805)[1, 2] += v5, gnd
    # Detección de cada fuente (activo bajo en PA15 / PB12 / PE15, pull-up interno): 2N7002 conduce si la entrada > ~3.5 V
    for src, pin in ((brick1, "PA15"), (brick2, "PB12"), (vbus, "PE15")):
        g = Net(f"DET_{src.name}")
        R("10k")[1, 2] += src, g
        R("10k")[1, 2] += g, gnd
        q = Part("Transistor_FET", "2N7002", footprint="Package_TO_SOT_SMD:SOT-23")
        q["G"] += g
        q["S"] += gnd
        q["D"] += mcu[pin]
    # Interruptores de periféricos: OUT1 = 5V_PERIPH (PE2 enciende, PE3 falla), OUT2 = 5V_HIPOWER (PC10, PC11)
    sw = Part("Interface_USB", "TPS2561")
    sw["IN"] += v5
    sw["GND", "PAD"] += gnd
    sw["OUT1"] += v5p
    sw["OUT2"] += v5h
    R("56k")[1, 2] += sw["ILM"], gnd                                   # I_lim = 56000 / 56 kΩ ≈ 1.0 A por canal
    sw["EN1"] += mcu["PE2"]
    sw["EN2"] += mcu["PC10"]
    R("100k")[1, 2] += mcu["PE2"], gnd                                 # apagados hasta que PX4 los habilite
    R("100k")[1, 2] += mcu["PC10"], gnd
    sw["~{FAULT1}"] += mcu["PE3"]
    sw["~{FAULT2}"] += mcu["PC11"]
    R("10k")[1, 2] += mcu["PE3"], v3
    R("10k")[1, 2] += mcu["PC11"], v3
    for n in (v5p, v5h):
        C("22u/10V", FP_C0805)[1, 2] += n, gnd
    # 3.3 V principal (siempre) y de sensores (PB2, para reiniciar las IMU desde PX4)
    for out, en in ((v3, v5), (v3s, mcu["PB2"])):
        ldo = Part("Regulator_Linear", "TLV75533PDBV")
        ldo["IN"] += v5
        ldo["EN"] += en
        ldo["OUT"] += out
        ldo["GND"] += gnd
        nc(ldo, "NC")
        C("1u", FP_C0603)[1, 2] += v5, gnd
        C("10u/10V", FP_C0805)[1, 2] += out, gnd
    R("100k")[1, 2] += mcu["PB2"], gnd
    # 5 V medido (PA4, ADC1 INP18): divisor 1:2
    v5s = Net("SCALED_V5")
    R("10k")[1, 2] += v5, v5s
    R("10k")[1, 2] += v5s, gnd
    C("100n")[1, 2] += v5s, gnd
    mcu["PA4"] += v5s


@subcircuit
def power_port(k: int, brick: Net, mcu: Part, v_pin: str, i_pin: str) -> None:
    """Puerto POWER estándar Pixhawk (JST-GH 6: VCC, VCC, CURRENT, VOLTAGE, GND, GND) con filtro RC al ADC."""
    cur, vol = Net(f"BATT{k}_I"), Net(f"BATT{k}_V")
    for src, pin in ((cur, i_pin), (vol, v_pin)):
        a = Net(f"{src.name}_ADC")
        R("1k")[1, 2] += src, a
        C("100n")[1, 2] += a, gnd
        mcu[pin] += a
    gh([brick, brick, cur, vol, gnd, gnd], f"J_POWER{k}")


@subcircuit
def imus(mcu: Part) -> None:
    sck, mosi, miso = Net("SPI1_SCK"), Net("SPI1_MOSI"), Net("SPI1_MISO")
    mcu["PA5"] += sck
    mcu["PA7"] += mosi
    mcu["PA6"] += miso
    # IIM-42652 (DRV_IMU_DEVTYPE_IIM42652)
    u = Part("Sensor_Motion", "IIM-42652")
    u["VDD", "VDDIO"] += v3s
    u["GND"] += gnd
    C("100n")[1, 2] += v3s, gnd
    C("2.2u", FP_C0603)[1, 2] += v3s, gnd
    u["AP_CS"] += mcu["PC13"]
    u["AP_SCL/AP_SCLK"] += sck
    u["AP_SDA/AP_SDIO/AP_SDI"] += mosi
    u["AP_SDO/AP_AD0"] += miso
    u["INT1/INT"] += mcu["PE6"]
    nc(u, "INT2/FSYNC/CLKIN")
    u["RESV"] += nc_net()                                                    # reservados (2, 3, 10, 11): sin conectar
    # BMI088: acelerómetro CSB1 / giróscopo CSB2, PS a GND = SPI (tabla 14)
    b = BMI088()
    b["VDD", "VDDIO"] += v3s
    b["GNDA", "GNDIO", "PS", "NC"] += gnd
    C("100n")[1, 2] += v3s, gnd
    C("100n")[1, 2] += v3s, gnd
    b["CSB1"] += mcu["PC15"]
    b["CSB2"] += mcu["PC14"]
    b["SCK"] += sck
    b["SDI"] += mosi
    b["SDO1", "SDO2"] += miso
    b["INT1"] += mcu["PE4"]                                            # DRDY acelerómetro
    b["INT3"] += mcu["PE5"]                                            # DRDY giróscopo
    nc(b, "INT2", "INT4")
    for cs in ("PC13", "PC14", "PC15"):
        R("10k")[1, 2] += mcu[cs], v3s                                 # CS en alto mientras arranca el MCU
    # Calefactor de las IMU: 10 × 150 Ω (1206) desde 5 V = 1.7 W máx., PWM desde PB9
    g, d = Net("HEATER_G"), Net("HEATER_D")
    R("100")[1, 2] += mcu["PB9"], g
    R("100k")[1, 2] += g, gnd
    q = Part("Transistor_FET", "AO3400A")
    q["G"] += g
    q["S"] += gnd
    q["D"] += d
    for _ in range(10):
        R("150", FP_R1206)[1, 2] += v5, d


@subcircuit
def i2c4_sensors(mcu: Part) -> None:
    scl, sda = Net("I2C4_SCL"), Net("I2C4_SDA")
    mcu["PD12"] += scl
    mcu["PD13"] += sda
    R("2.2k")[1, 2] += scl, v3s
    R("2.2k")[1, 2] += sda, v3s
    baro = Part("Sensor_Pressure", "MS5611-01BA")
    baro["VDD", "PS"] += v3s                                           # PS alto = I2C
    baro["GND", "CSB"] += gnd                                          # CSB bajo → dirección 0x77
    baro["SCLK"] += scl
    baro["SDI/SDA"] += sda
    nc(baro, "SDO")
    C("100n")[1, 2] += v3s, gnd
    mag = Part("Sensor_Magnetic", "IST8310")
    mag["AVDD", "DVDD"] += v3s
    mag["VSS", "CAD0", "CAD1"] += gnd                                  # dirección 0x0C
    mag["SCL"] += scl
    mag["SDA"] += sda
    mag["~{RST}"] += v3s
    C("1u", FP_C0603)[1, 2] += mag["C1"], gnd
    C("100n")[1, 2] += mag["VPP"], gnd
    C("100n")[1, 2] += v3s, gnd
    nc(mag, "DRDY", "NC")
    ee = Part("Memory_EEPROM", "24LC64", footprint=FP_SOIC8)
    ee["VCC"] += v3s
    ee["GND", "A0", "A1", "A2", "WP"] += gnd                           # 0x50
    ee["SCL"] += scl
    ee["SDA"] += sda
    C("100n")[1, 2] += v3s, gnd


@subcircuit
def storage(mcu: Part) -> None:
    fram = Part("Memory_NVRAM", "MB85RS256B", footprint=FP_SOIC8)
    fram["VDD", "~{WP}", "~{HOLD}"] += v3
    fram["GND"] += gnd
    fram["~{CS}"] += mcu["PD4"]
    fram["SCK"] += mcu["PD3"]
    fram["SI"] += mcu["PC3_C"]
    fram["SO"] += mcu["PC2_C"]
    R("10k")[1, 2] += mcu["PD4"], v3
    C("100n")[1, 2] += v3, gnd
    sd = Part("Connector", "Micro_SD_Card_Det1", footprint="Connector_Card:microSD_HC_Hirose_DM3AT-SF-PEJM5")
    sd["VDD"] += v3
    sd["VSS", "SHIELD"] += gnd
    C("10u/10V", FP_C0805)[1, 2] += v3, gnd
    for sig, pin in (("CLK", "PD6"), ("CMD", "PD7"), ("DAT0", "PB14"), ("DAT1", "PB15"), ("DAT2", "PB3"), ("DAT3/CD", "PB4")):
        sd[sig] += mcu[pin]
        if sig != "CLK":
            R("47k")[1, 2] += mcu[pin], v3
    nc(sd, "DET")


@subcircuit
def usb(mcu: Part) -> None:
    j = Part("Connector", "USB_C_Receptacle_USB2.0_16P", footprint="Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12")
    j["VBUS"] += vbus
    j["GND"] += gnd
    j["CC1"] & R("5.1k") & gnd
    j["CC2"] & R("5.1k") & gnd
    dp, dm = Net("USB_DP"), Net("USB_DM")
    j["D+"] += dp
    j["D-"] += dm
    nc(j, "SBU1", "SBU2")
    shield = Net("USB_SHIELD")
    j["SHIELD"] += shield
    R("1M")[1, 2] += shield, gnd
    C("4.7n/100V", FP_C0603)[1, 2] += shield, gnd
    esd = Part("Power_Protection", "USBLC6-2SC6", footprint="Package_TO_SOT_SMD:SOT-23-6")
    esd["I/O1"] += dp
    esd["I/O2"] += dm
    esd["VBUS"] += vbus
    esd["GND"] += gnd
    mcu["PA12"] += dp
    mcu["PA11"] += dm
    vs = Net("USB_VBUS_SENSE")                                         # PA9: 5 V → 3.0 V
    R("22k")[1, 2] += vbus, vs
    R("33k")[1, 2] += vs, gnd
    mcu["PA9"] += vs


@subcircuit
def can(mcu: Part, k: int, tx: str, rx: str) -> None:
    t = Part("Interface_CAN_LIN", "TCAN330", footprint="Package_TO_SOT_SMD:SOT-23-8")
    t["VCC"] += v3
    t["GND", "S", "SHDN"] += gnd                                       # modo normal
    C("100n")[1, 2] += v3, gnd
    t["TXD"] += mcu[tx]
    t["RXD"] += mcu[rx]
    h, low = Net(f"CAN{k}_H"), Net(f"CAN{k}_L")
    t["CANH"] += h
    t["CANL"] += low
    gh([v5h, h, low, gnd], f"J_CAN{k}")


def uart_port(mcu: Part, ref: str, tx: str, rx: str, extra: list | None = None, power: Net = v5p) -> None:
    """UART con 22 Ω en serie (bordes) hacia el conector: 5 V, TX, RX, [extra…], GND."""
    nets = []
    for pin in (tx, rx):
        n = Net(f"{ref}_{pin}")
        R("22")[1, 2] += mcu[pin], n
        nets.append(n)
    for pin in extra or []:
        if isinstance(pin, Net):
            nets.append(pin)
        else:
            n = Net(f"{ref}_{pin}")
            R("22")[1, 2] += mcu[pin], n
            nets.append(n)
    gh([power, *nets, gnd], ref)


@subcircuit
def i2c_ext(mcu: Part, scl: str, sda: str, k: int) -> tuple:
    a, b = Net(f"I2C{k}_SCL"), Net(f"I2C{k}_SDA")
    mcu[scl] += a
    mcu[sda] += b
    R("2.2k")[1, 2] += a, v3
    R("2.2k")[1, 2] += b, v3
    return a, b


@subcircuit
def outputs(mcu: Part) -> None:
    pins = ("PA8", "PE11", "PE13", "PE14", "PD14", "PD15", "PA0", "PA1")
    nets = []
    for k, pin in enumerate(pins, 1):
        n = Net(f"PWM{k}")
        R("47")[1, 2] += mcu[pin], n
        nets.append(n)
    j = Part("Connector_Generic", "Conn_01x10", ref="J_PWM", footprint=FP_GH.format(n=10))
    for i, n in enumerate([*nets, gnd, gnd], 1):
        if i <= 10:
            j[i] += n


@subcircuit
def indicators(mcu: Part) -> None:
    led = Part("Device", "LED_RGB", footprint="LED_SMD:LED_Kingbright_AAA3528ESGCT")
    led["RA", "GA", "BA"] += v3
    R("1k")[1, 2] += led["RK"], mcu["PD10"]                            # rojo (activo bajo)
    R("1k")[1, 2] += led["BK"], mcu["PD11"]                            # azul (activo bajo)
    nc(led, "GK")
    pwr = Part("Device", "LED", value="verde", footprint=FP_LED)
    R("1k")[1, 2] += v3, pwr["A"]
    pwr["K"] += gnd
    # Zumbador magnético (PB0, TIM3 CH3) con 2N7002 y diodo de rueda libre
    g, d = Net("BUZZ_G"), Net("BUZZ_D")
    R("100")[1, 2] += mcu["PB0"], g
    R("100k")[1, 2] += g, gnd
    q = Part("Transistor_FET", "2N7002", footprint="Package_TO_SOT_SMD:SOT-23")
    q["G"] += g
    q["S"] += gnd
    q["D"] += d
    bz = Part("Device", "Buzzer", footprint="Buzzer_Beeper:Buzzer_CUI_CPT-9019S-SMT")
    bz["+"] += v5
    bz["-"] += d
    Part("Device", "D_Schottky", value="BAT54", footprint="Diode_SMD:D_SOD-323")["A", "K"] += d, v5


def fc() -> None:
    mcu = mcu_core()
    power(mcu)
    power_port(1, brick1, mcu, "PC5", "PC4")                           # BATT1: V en INP8, I en INP4
    power_port(2, brick2, mcu, "PB1", "PA2")                           # BATT2: V en INP5, I en INP14
    imus(mcu)
    i2c4_sensors(mcu)
    storage(mcu)
    usb(mcu)
    can(mcu, 1, "PD1", "PD0")
    can(mcu, 2, "PB13", "PB5")
    scl1, sda1 = i2c_ext(mcu, "PB8", "PB7", 1)
    scl2, sda2 = i2c_ext(mcu, "PB10", "PB11", 2)
    uart_port(mcu, "J_TELEM1", "PE8", "PE7", ["PE10", "PE9"])          # CTS, RTS
    uart_port(mcu, "J_TELEM2", "PC12", "PD2", ["PC9", "PC8"])          # CTS, RTS
    uart_port(mcu, "J_TELEM3", "PD5", "PA3")
    uart_port(mcu, "J_GPS1", "PB6", "PA10", [scl1, sda1])
    uart_port(mcu, "J_GPS2", "PE1", "PE0", [scl2, sda2])
    uart_port(mcu, "J_RC", "PC6", "PC7")
    # Depuración (estándar Pixhawk debug, JST-SH 6): 3V3, consola TX/RX (USART3), SWDIO, SWCLK, GND
    j = Part("Connector_Generic", "Conn_01x06", ref="J_DEBUG", footprint="Connector_JST:JST_SH_SM06B-SRSS-TB_1x06-1MP_P1.00mm_Horizontal")
    j[1, 2, 3, 4, 5, 6] += v3, mcu["PD8"], mcu["PD9"], mcu["PA13"], mcu["PA14"], gnd
    Part("Connector", "TestPoint", footprint="TestPoint:TestPoint_Pad_D1.0mm")[1] += mcu["NRST"]
    outputs(mcu)
    indicators(mcu)
    # Pines sin uso (en v6c: versión de hardware PE12/PC0/PC1, PX4IO; aquí libres): net explícita sin ERC
    for pin in mcu.pins:
        if not pin.is_connected():
            pin += nc_net()


fc()
generate_netlist(file_=finish("fc"))
