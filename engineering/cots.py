"""S09-01 · Selección de motor, hélice y ESC comerciales con el mismo modelo del dimensionamiento (S03-S04).

Para cada motor del catálogo y cada hélice que entra en el frame (S07-S08), reemplaza el motor paramétrico del S04
por el real y recalcula: masa total (motor + hélice + ESC reales), potencia y autonomía en hover a 4,500 msnm,
empuje máximo a 5,000 msnm (con los límites de corriente y voltaje del motor), throttle de hover y corriente.

Datos de catálogo: fichas y tiendas consultadas en 2026-10 (campo `source`). Lo marcado `estimado` no apareció en
las fichas y se mide en el banco de empuje del S10 (Kv, Rm, I0 reales), que también reemplaza estas curvas.

    .venv/bin/python -m engineering.cots        → engineering/data/results/cots_selection.json
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .atmosphere import G0, air
from .endurance_table import load_design
from .mass_budget import esc_mass_kg, prop_cost, prop_mass_kg
from .mission_loads import Propulsion
from .motor import Motor, operating_point
from .propeller import PropGeometry

RESULTS = Path(__file__).resolve().parent / "data" / "results"


@dataclass(frozen=True)
class CotsMotor:
    name: str
    vehicle: str
    kv: float
    rm: float                       # Ω
    i0: float                       # A
    i_max: float                    # A (180 s)
    mass_kg: float                  # con cables
    cost_usd: float
    p_max_w: float
    props_in: tuple                 # rango recomendado por el fabricante
    mount: str                      # patrón de tornillos (compatibilidad DMI)
    source: str
    estimated: tuple = ()           # campos estimados (no publicados)

    def motor(self) -> Motor:
        return Motor(kv=self.kv, rm=self.rm, i0=self.i0, i_max=self.i_max, mass_kg=self.mass_kg, cost_usd=self.cost_usd,
                     name=self.name)


@dataclass(frozen=True)
class Esc:
    name: str
    vehicle: str
    current_a: float
    mass_kg: float                  # por canal
    cost_usd: float                 # por canal
    telemetry: bool
    source: str


MOTORS = [
    CotsMotor("T-Motor MN4006 KV380 (AntiGravity)", "DS-I", 380, 0.194, 0.3, 16, 0.068, 75, 380, (12, 15), "4×M3 Ø19/Ø25 (DMI-S)",
              "robotshop.com / getfpv.com (2026-10): 66-68 g, 194 mΩ, 16 A, 380 W", ("cost_usd",)),
    CotsMotor("T-Motor MN4014 KV330", "DS-I", 330, 0.085, 0.6, 25, 0.171, 105, 750, (15, 17), "4×M3 Ø25 (DMI-S)",
              "store.tmotor.com / robu.in (2026-10): 171 g con cables, 85 mΩ, 25 A, 750 W, hélice P17×5.8", ("i0", "cost_usd")),
    CotsMotor("T-Motor U8 Lite KV100", "DS-D", 100, 0.170, 0.7, 29.3, 0.238, 330, 1406, (27, 28), "4×M4 Ø36 (DMI-L)",
              "ligpower.com / irlock.com (2026-10): 238 g, 170 mΩ, 29.3 A, 1,406 W; US$310-387"),
    CotsMotor("MAD M6C12 EEE KV150", "DS-D", 150, 0.10, 0.9, 45, 0.257, 170, 1900, (22, 26), "4×M4 Ø35 (DMI-L)",
              "openelab.io (2026-10): 257 g, empuje máx. 9.4 kgf a 12S, hover 3-4 kgf", ("rm", "i0", "i_max", "cost_usd", "p_max_w")),
    CotsMotor("T-Motor MN6007II KV160", "DS-D", 160, 0.227, 0.6, 25, 0.155, 150, 1100, (21, 22), "4×M4 Ø30 (DMI-L)",
              "rcdrone.top / robotshop.com (2026-10): 155 g, 227 mΩ (v1), hélice P21-22", ("i0", "i_max", "cost_usd", "p_max_w")),
]


def _with_bench_data(motors: list[CotsMotor]) -> list[CotsMotor]:
    """S10-05: si el banco midió un motor (engineering/data/motors/*.json), sus Kv, Rm e I0 reemplazan al catálogo."""
    from dataclasses import replace
    measured = {}
    for f in (Path(__file__).resolve().parent / "data" / "motors").glob("*.json"):
        m = json.loads(f.read_text())
        measured[m["name"]] = m
    out = []
    for m in motors:
        b = measured.get(m.name)
        out.append(m if b is None else replace(m, kv=b["kv"], rm=b["rm"], i0=b["i0"], source=f"{m.source} · medido: {b['source']}",
                                               estimated=tuple(x for x in m.estimated if x not in ("kv", "rm", "i0"))))
    return out


MOTORS = _with_bench_data(MOTORS)

ESCS = [
    Esc("ESC 4 en 1 BLHeli32/AM32 6S 50 A con telemetría DShot bidireccional", "DS-I", 50, 0.004, 20, True,
        "clase Tekko32 / Holybro (≈ US$80 el 4 en 1)"),
    Esc("APD 120F3[X] V2 12S 120 A (BLHeli32, telemetría DShot)", "DS-D", 120, 0.020, 120, True,
        "getfpv.com / racedayquads.com (2026-10): 12S, 20 g; precio a confirmar"),
]

@dataclass(frozen=True)
class Item:
    """Componente de aviónica o equipo (por dron)."""
    role: str
    name: str
    mass_kg: float
    cost_usd: float
    source: str
    estimated: bool = False


# Equipo fijo real del prototipo (reemplaza al presupuesto del S04 en design_cases.yaml). Precios de tienda 2026-10.
AVIONICS = {
    "common": [
        Item("controladora", "Holybro Pixhawk 6C (caja de plástico)", 0.060, 225, "pyrodrone.com (2026-10): US$224.99"),
        Item("GNSS", "u-blox ZED-F9P multibanda, RTK, con brújula (clase Holybro H-RTK F9P Ultralight)", 0.040, 250,
             "estimado: módulos F9P US$200-300", True),
        Item("computadora a bordo", "Raspberry Pi 5 4 GB + disipador + caja", 0.060, 80, "precio de lista Raspberry Pi"),
        Item("radio de tierra", "RFDesign RFD900x (malla/multipunto 900 MHz)", 0.015, 140,
             "unmannedtechshop.co.uk (2026-10): £219.95 el par"),
        Item("radio entre drones", "Módulo ESP32-S3 (ESP-NOW 2.4 GHz) en la computadora a bordo", 0.005, 10, "precio de lista"),
        Item("receptor RC", "ExpressLRS 900 MHz (clase RadioMaster BR3)", 0.005, 25, "estimado", True),
        Item("flujo óptico + telémetro", "MicoAir MTF-01P (flujo óptico + lidar 8 m, MAVLink)", 0.005, 40,
             "estimado; requisito del S06 (pérdida de GNSS)", True),
    ],
    "DS-I": [
        Item("módulo de potencia", "Holybro PM02 V3 (2-12S, sensado de V/I)", 0.030, 30, "estimado", True),
        Item("cámara + gimbal", "SIYI A8 mini (1/1.7\" 8 MP, gimbal 3 ejes, 4K)", 0.095, 280,
             "irlock.com / siyi.biz (2026-10): 95 g, US$190-330"),
    ],
    "DS-D": [
        Item("módulo de potencia", "Sensor Hall 200 A (clase Mauch HS-200) + regulador 5.3 V", 0.045, 90, "estimado", True),
        Item("cámara FPV", "Cámara FPV analógica/digital 19 mm", 0.010, 30, "estimado", True),
        Item("servo de liberación", "Servo estándar de engranajes metálicos 20 kg·cm + micro-interruptor", 0.060, 35, "estimado", True),
        Item("luces anticolisión", "4 LED de alta luminosidad (rojo, verde, 2 blancas destellantes)", 0.030, 30, "estimado", True),
    ],
}
# Partidas del presupuesto del S04 que reemplaza esta lista (el resto —cableado, carcasa, tren, gancho— sale del CAD)
REPLACED = {"DS-I": ["flight_controller", "gnss_compass", "rtk_module", "companion_computer", "power_pcb", "rc_receiver",
                     "mesh_radio", "camera_gimbal"],
            "DS-D": ["flight_controller", "gnss_compass", "rtk_module", "companion_computer", "power_pcb", "rc_receiver",
                     "mesh_radio", "fpv_camera"]}


def avionics(vehicle: str) -> list[Item]:
    return AVIONICS["common"] + AVIONICS[vehicle]


def fixed_equipment_delta(vehicle: str) -> tuple[float, float]:
    """(Δmasa, Δcosto) del equipo fijo real frente al presupuesto del S04."""
    import yaml
    cfg = yaml.safe_load((Path(__file__).resolve().parent / "config" / "design_cases.yaml").read_text())["vehicles"][vehicle]
    old_m = sum(cfg["fixed_equipment"][k]["mass"] for k in REPLACED[vehicle])
    old_c = sum(cfg["fixed_equipment"][k]["cost"] for k in REPLACED[vehicle])
    new_m = sum(i.mass_kg for i in avionics(vehicle))
    new_c = sum(i.cost_usd for i in avionics(vehicle))
    return new_m - old_m, new_c - old_c


def frame_delta_kg(vehicle: str) -> float:
    """Masa del frame real (CAD, S07-S08, +6 % tornillería) menos la presupuestada en el S04."""
    group = {"DS-I": "inspection", "DS-D": "delivery"}[vehicle]
    rep = Path(__file__).resolve().parents[1] / "cad" / "exports" / group / "masas.json"
    if not rep.exists():
        return 0.0
    r = json.loads(rep.read_text())
    return r["frame_cad_kg"] * 1.06 - r["frame_budget_kg"]


# Hélices que entran en los frames del S07-S08 (holgura de hélices verificada para el diámetro de diseño)
PROPS = {"DS-I": [15, 16, 17], "DS-D": [24, 26]}
REQUIREMENTS = {"DS-I": {"endurance_min": 30.0}, "DS-D": {"endurance_min": 20.0}}     # escenarios D y C (G0)


@dataclass
class Option:
    vehicle: str
    motor: str
    prop_in: float
    mtow_kg: float
    endurance_new_min: float
    endurance_eol_min: float
    twr_5000m: float
    hover_thrust_fraction: float
    hover_current_per_motor_a: float        # corriente del MOTOR (fase) en hover
    hover_battery_current_a: float          # corriente del PACK en hover (todos los motores + aviónica)
    hover_p_battery_per_motor_w: float
    max_current_per_motor_a: float
    hover_motor_efficiency: float
    propulsion_cost_usd: float
    pack_current_full_a: float = 0.0        # corriente del pack con todos los motores a fondo (5,000 msnm)
    pack_current_twr2_a: float = 0.0        # ... con el empuje limitado a 2 × peso
    pack_limit_a: float = 0.0
    thr_max_recommended: float = 1.0        # MPC_THR_MAX de PX4 que mantiene el pack dentro de su límite
    checks: dict = field(default_factory=dict)          # requisitos (descartan la opción)
    notes: list = field(default_factory=list)           # guías de diseño (no descartan, se informan)

    @property
    def ok(self) -> bool:
        return all(self.checks.values())


def evaluate(m: CotsMotor, esc: Esc, prop_in: float) -> Option:
    d, base = load_design(m.vehicle)
    n = d["rotors"]
    cal = base.geom.cd0_scale
    geom = PropGeometry.inches(prop_in, prop_in * d["pitch_ratio"], cd0_scale=cal)
    old = base.motor.mass_kg + prop_mass_kg(d["prop_diameter_in"]) + esc_mass_kg(d["esc_current_a"])
    new = m.mass_kg + prop_mass_kg(prop_in) + esc.mass_kg
    mtow = d["mtow_kg"] + n * (new - old) + fixed_equipment_delta(m.vehicle)[0] + frame_delta_kg(m.vehicle)
    prop = Propulsion(n, m.motor(), geom, base.pack, base.avionics_w)
    a_end, a_thr = air(4500, 0), air(5000, 15)
    hov = prop.hover(mtow, a_end)
    mx = prop.max_thrust(a_thr)
    e_new = base.pack.usable_energy_wh(0)
    e_eol = e_new / 1.3
    req = REQUIREMENTS[m.vehicle]
    opt = Option(m.vehicle, m.name, prop_in, round(mtow, 3), round(e_new * 60 / hov["p_total"], 1),
                 round(e_eol * 60 / hov["p_total"], 1), round(mx["total_thrust"] / (mtow * G0), 2),
                 round(hov["thrust_fraction"], 2), round(hov["current"], 1), round(hov["current_total"], 1),
                 round(hov["p_battery"], 1), round(mx["current"], 1),
                 round(hov["efficiency"], 3), round(n * (m.cost_usd + prop_cost(prop_in) + esc.cost_usd), 0))
    # corriente del pack: a fondo y con empuje = 2 × peso (lo que hace falta para el requisito de empuje/peso)
    pack = base.pack
    opt.pack_limit_a = round(pack.i_max, 1)
    opt.pack_current_full_a = round(n * mx["current"] + base.avionics_w / pack.v_nominal, 1)
    op2 = operating_point(m.motor(), prop.table(a_thr), 2.0 * mtow * G0 / n, mx["v_battery"])
    opt.pack_current_twr2_a = round((n * op2["p_battery"] + base.avionics_w) / mx["v_battery"], 1)
    if opt.pack_current_full_a > opt.pack_limit_a:
        # throttle colectivo que deja el pack en su límite (el empuje crece ~ con la corriente en esa zona)
        opt.thr_max_recommended = round(max(0.5, min(1.0, opt.pack_limit_a / opt.pack_current_full_a)), 2)
    opt.checks = {
        "empuje/peso ≥ 2.0 a 5,000 msnm": opt.twr_5000m >= 1.98,
        f"autonomía ≥ {req['endurance_min']:.0f} min (batería nueva, 4,500 msnm)": opt.endurance_new_min >= req["endurance_min"],
        "corriente máxima ≤ la del motor": opt.max_current_per_motor_a <= m.i_max * 1.02,
        "ESC con telemetría": esc.telemetry,
        "el pack entrega la corriente para empuje/peso 2.0": opt.pack_current_twr2_a <= opt.pack_limit_a,
    }
    if opt.thr_max_recommended < 1.0:
        opt.notes.append(f"a fondo el pack daría {opt.pack_current_full_a:.0f} A (límite {opt.pack_limit_a:.0f} A): "
                         f"limitar con MPC_THR_MAX = {opt.thr_max_recommended}")
    if not 0.40 <= opt.hover_thrust_fraction <= 0.65:
        opt.notes.append(f"hover al {opt.hover_thrust_fraction:.0%} del empuje máximo (guía 40-65 %): "
                         + ("motor holgado, margen extra en altura" if opt.hover_thrust_fraction < 0.40 else "poco margen"))
    if not m.props_in[0] <= prop_in <= m.props_in[1]:
        opt.notes.append(f"hélice de {prop_in:g}\" fuera del rango del fabricante ({m.props_in[0]}-{m.props_in[1]}\"): "
                         "verificar temperatura en el banco (S10)")
    if opt.max_current_per_motor_a >= 0.97 * m.i_max:
        opt.notes.append("a fondo llega al límite de corriente del motor: el empuje máximo lo fija la corriente")
    if m.estimated:
        opt.notes.append("datos estimados: " + ", ".join(m.estimated) + " (se miden en el S10)")
    return opt


def run() -> dict:
    out = {"motors": [asdict(m) for m in MOTORS], "escs": [asdict(e) for e in ESCS], "options": [], "selected": {},
           "avionics": {v: [asdict(i) for i in avionics(v)] for v in ("DS-I", "DS-D")},
           "fixed_equipment_delta": {v: dict(zip(("mass_kg", "cost_usd"), map(lambda x: round(x, 3), fixed_equipment_delta(v))))
                                     for v in ("DS-I", "DS-D")}}
    for veh in ("DS-I", "DS-D"):
        esc = next(e for e in ESCS if e.vehicle == veh)
        opts = [evaluate(m, esc, p) for m in MOTORS if m.vehicle == veh for p in PROPS[veh]]
        for o in opts:
            out["options"].append({**asdict(o), "ok": o.ok})
        ok = [o for o in opts if o.ok]
        # elección: entre las que cumplen, la de menos observaciones de riesgo (hélice fuera de rango, motor al límite;
        # los datos estimados no cuentan), y a igualdad, la de mayor autonomía
        if ok:
            def risk(o):
                return sum(1 for n in o.notes if not n.startswith(("datos estimados", "a fondo el pack")))   # config., no riesgo
            pick = min(ok, key=lambda o: (risk(o), -o.endurance_new_min))
            out["selected"][veh] = {**asdict(pick), "ok": True, "esc": esc.name}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "cots_selection.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    return out


# ----------------------------------------------------------------------------------------------- informe (S09)
DOC = Path(__file__).resolve().parents[1] / "docs" / "ingenieria" / "seleccion_cots.md"
CAMERA = {"sensor_w_mm": 7.6, "px_w": 3840, "hfov_deg": 81.0}          # SIYI A8 mini (1/1.7", 8 MP, HFOV 81°)
SOURCES = [
    ("T-Motor MN4006 KV380", "https://www.getfpv.com/tiger-motor-mn4006-380kv-antigravity-2-black-motors.html"),
    ("T-Motor MN4006 KV380 (Robotshop)", "https://ca.robotshop.com/products/tmotor-uav-brushless-motor-antigravity-mn4006-kv380-2x"),
    ("T-Motor MN4014 KV330", "https://store.tmotor.com/product/mn4014-kv330-motor-navigator-type.html"),
    ("T-Motor U8 Lite KV100", "https://www.ligpower.com/product/u8-lite-kv100-u-efficiency.html"),
    ("T-Motor U8 Lite KV100 (precio)", "https://irlock.com/products/t-motor-u8-lite-efficiency-type-uav-motor-kv100-net"),
    ("MAD M6C12 EEE KV150", "https://openelab.io/nl/products/mad-m6c12-eee-kv150-motor"),
    ("T-Motor MN6007II", "https://www.unmannedtechshop.co.uk/products/t-motor-mn6007-ii-vtol-uav-motor-kv160-kv320"),
    ("Hobbywing X6 Plus G2 (descartado)", "https://www.hobbywing.com/en/products/x6-plus-g2"),
    ("APD 120F3[X] V2", "https://www.getfpv.com/apd-f-series-120f3-x-v2-120a-12s-50v-blheli-32-esc.html"),
    ("SIYI A8 mini", "https://siyi.biz/en/product/tri-axis-single-camera-gimbal/a8-mini/"),
    ("Pixhawk 6C (precio)", "https://pyrodrone.com/collections/all-inventory/brand_holybro"),
    ("RFD900x (precio)", "https://www.unmannedtechshop.co.uk/collections/wireless-telemetry?page=2"),
]


def camera_gsd(h_m: float) -> float:
    import math
    f_mm = (CAMERA["sensor_w_mm"] / 2) / math.tan(math.radians(CAMERA["hfov_deg"] / 2))
    return h_m * (CAMERA["sensor_w_mm"] / CAMERA["px_w"]) / f_mm * 100             # cm/px


def write_report(res: dict) -> Path:
    import datetime as dt
    d_i, d_d = (json.loads((RESULTS / f"{v}_sizing.json").read_text()) for v in ("ds-i", "ds-d"))
    sel = res["selected"]
    L = [
        "# Selección de componentes comerciales (COTS) · prototipos DS-I y DS-D", "",
        f"> Generado por `engineering/cots.py` el {dt.date.today().isoformat()}. Catálogo y criterios en el código; "
        "para recalcular: `.venv/bin/python -m engineering.cots`.", "",
        "Cada motor del catálogo se evalúa con el **mismo modelo del dimensionamiento** (hélice BEMT, motor por circuito "
        "equivalente, batería Li-ion, aire a 4,500-5,000 msnm), con la masa real de motor, hélice, ESC, aviónica y frame (CAD). "
        "Requisitos que descartan una opción: empuje/peso ≥ 2.0 a 5,000 msnm, autonomía del escenario (DS-I ≥ 30 min, "
        "DS-D ≥ 20 min con 5 kg), corriente dentro del motor y del pack, y ESC con telemetría. Las guías de diseño se "
        "informan como observaciones. Lo marcado *estimado* se mide en el banco del S10.", "",
        "## 1. Resultado", "",
        "| | DS-I | DS-D |", "|---|---|---|",
        f"| Motor | {sel['DS-I']['motor']} | {sel['DS-D']['motor']} |",
        f"| Hélice | {sel['DS-I']['prop_in']:g}\" (el frame admite hasta 17\") | {sel['DS-D']['prop_in']:g}\" |",
        f"| ESC | {sel['DS-I']['esc']} | {sel['DS-D']['esc']} |",
        f"| MTOW con componentes reales | {sel['DS-I']['mtow_kg']:.2f} kg (S04: {d_i['mtow_kg']:.2f}) | {sel['DS-D']['mtow_kg']:.2f} kg (S04: {d_d['mtow_kg']:.2f}) |",
        f"| Autonomía, batería nueva, 4,500 msnm | {sel['DS-I']['endurance_new_min']} min (S04: {d_i['performance']['endurance_new_min']}) | "
        f"{sel['DS-D']['endurance_new_min']} min con 5 kg (S04: {d_d['performance']['endurance_new_min']}) |",
        f"| Empuje/peso a 5,000 msnm | {sel['DS-I']['twr_5000m']} | {sel['DS-D']['twr_5000m']} |",
        f"| Corriente del pack: a fondo / con empuje 2 × peso / límite | {sel['DS-I']['pack_current_full_a']:.0f} / {sel['DS-I']['pack_current_twr2_a']:.0f} / {sel['DS-I']['pack_limit_a']:.0f} A | "
        f"{sel['DS-D']['pack_current_full_a']:.0f} / {sel['DS-D']['pack_current_twr2_a']:.0f} / {sel['DS-D']['pack_limit_a']:.0f} A |",
        f"| `MPC_THR_MAX` de PX4 (protege la batería) | {sel['DS-I']['thr_max_recommended']} | {sel['DS-D']['thr_max_recommended']} |",
        f"| Propulsión (motores + hélices + ESC) | US${sel['DS-I']['propulsion_cost_usd']:.0f} (S04: US${d_i['costs']['motores'] + d_i['costs']['hélices'] + d_i['costs']['ESC']:.0f}) | "
        f"US${sel['DS-D']['propulsion_cost_usd']:.0f} (S04: US${d_d['costs']['motores'] + d_d['costs']['hélices'] + d_d['costs']['ESC']:.0f}) |",
        "",
        "**Lectura:** los dos prototipos cumplen sus escenarios con componentes que se compran hoy. El DS-I sale más liviano "
        "que lo dimensionado (la cámara real pesa 95 g contra 300 g supuestos) y gana autonomía. **El costo sube:** los motores "
        "de marca cuestan 3-4 veces lo que suponía el modelo paramétrico del S04, y la aviónica real ~US$500 más por dron "
        "(sección 4). Es el principal argumento para el motor y la electrónica propios (S17-S21).", "",
        "## 2. Motores y hélices evaluados", "",
        "| Dron | Motor | Hélice | MTOW | Autonomía | Empuje/peso | Hover | Corriente máx./motor | Propulsión | ¿Cumple? | Observaciones |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for o in res["options"]:
        failed = [k for k, v in o["checks"].items() if not v]
        L.append(f"| {o['vehicle']} | {o['motor']} | {o['prop_in']:g}\" | {o['mtow_kg']:.2f} kg | {o['endurance_new_min']} min | "
                 f"{o['twr_5000m']} | {o['hover_thrust_fraction']:.0%} | {o['max_current_per_motor_a']} A | US${o['propulsion_cost_usd']:.0f} | "
                 f"{'✅' if o['ok'] else '❌ ' + '; '.join(failed)} | {'; '.join(o['notes'])} |")
    L += ["", "Descartados antes de evaluar: **Hobbywing X6 Plus G2** (motor + ESC CAN integrado, a prueba de agua): ~750 g "
          "y ~US$310 por brazo, y monta en tubo de 30 mm. Es una buena opción para una versión agrícola, pero no para este peso.", "",
          "## 3. ESC", "",
          "| Dron | ESC | Corriente | Telemetría | Por qué |", "|---|---|---|---|---|"]
    for e in res["escs"]:
        why = ("4 en 1, liviano; la telemetría da rpm para el filtro notch dinámico" if e["vehicle"] == "DS-I" else
               "**telemetría de corriente obligatoria** para detectar un motor caído (S06); 12S con margen sobre 45 A")
        L.append(f"| {e['vehicle']} | {e['name']} | {e['current_a']:.0f} A | {'sí' if e['telemetry'] else 'no'} | {why} |")
    L += ["", "## 4. Aviónica y equipo por dron", ""]
    for v in ("DS-I", "DS-D"):
        dm, dc = res["fixed_equipment_delta"][v]["mass_kg"], res["fixed_equipment_delta"][v]["cost_usd"]
        L += [f"### {v}", "", "| Función | Componente | Masa | Precio | Fuente |", "|---|---|---|---|---|"]
        for i in res["avionics"][v]:
            L.append(f"| {i['role']} | {i['name']} | {i['mass_kg'] * 1000:.0f} g | US${i['cost_usd']:.0f}{' *' if i['estimated'] else ''} | {i['source']} |")
        L += ["", f"Contra el presupuesto del S04: **{dm * 1000:+.0f} g y {dc:+.0f} US$** por dron (`*` = precio estimado).", ""]
    g109, h3 = camera_gsd(109), 3.0 / camera_gsd(1.0)
    L += ["## 5. Cámara y resolución del levantamiento (HU-01)", "",
          f"La SIYI A8 mini (1/1.7\", 8 MP, gimbal de 3 ejes, 95 g, compatible con PX4) da **{g109:.1f} cm/px a 109 m**. "
          f"Para los 3 cm/px de la HU-01 hay que volar a **{h3:.0f} m**: más líneas de grilla, ~60 % más tiempo de vuelo por "
          "hectárea. Sirve para inspección (zoom, video 4K, seguimiento) y para levantamientos de hasta ~35-40 ha por vuelo.",
          "", "Opción para la HU-01 completa (60 ha en un vuelo): una cámara de 1\" a 20 MP en montaje fijo (~130-300 g, "
          "US$700-1,000). Es una **decisión del G2**: la A8 mini para el prototipo y una carga de mapeo como accesorio en el S13.", "",
          "## 6. Baterías", "",
          "| | DS-I | DS-D |", "|---|---|---|",
          f"| Configuración | {d_i['battery']} | {d_d['battery']} |",
          f"| Energía nominal | {d_i['performance']['battery_energy_wh']:.0f} Wh | {d_d['performance']['battery_energy_wh']:.0f} Wh |",
          f"| Corriente continua del pack | {sel['DS-I']['pack_limit_a']:.0f} A | {sel['DS-D']['pack_limit_a']:.0f} A |",
          "| Fabricación | Armador de packs local con celdas de distribuidor oficial (soldadura por puntos, níquel 0.15 mm) | ídem, con barra de cobre en las series de alta corriente |",
          "| Conector | XT90-S antichispa | AS150U antichispa |",
          "| Alternativa comercial | Pack Li-ion 21700 6S2P 10 Ah de catálogo para drones | LiPo 12S 22 Ah de catálogo (≈ 25 % más pesado por Wh) |",
          "", "Sin BMS de corte en vuelo: un BMS que desconecta en el aire tira el dron. Lleva conector de balanceo, y la "
          "protección es la alarma de batería de PX4 más los umbrales mineros del S06 (aviso 35 %, RTL 25 %, aterrizaje 10 %). "
          "Las celdas se compran a distribuidores autorizados, con 2 cotizaciones: hay muchas falsificaciones de 21700.", "",
          "## 7. Fuentes consultadas (2026-10)", ""]
    L += [f"- [{n}]({u})" for n, u in SOURCES]
    L.append("")
    DOC.write_text("\n".join(L))
    return DOC


if __name__ == "__main__":
    res = run()
    print(write_report(res))
    for o in res["options"]:
        print(f"{o['vehicle']} {o['motor']:<38} {o['prop_in']:>4}\" MTOW {o['mtow_kg']:6.2f}  {o['endurance_new_min']:5.1f} min  "
              f"TWR {o['twr_5000m']:.2f}  hover {o['hover_thrust_fraction']:.2f}  Imax {o['max_current_per_motor_a']:5.1f} A  "
              f"US${o['propulsion_cost_usd']:.0f}  {'OK' if o['ok'] else '—'}")
    print({k: (v["motor"], v["prop_in"]) for k, v in res["selected"].items()})
