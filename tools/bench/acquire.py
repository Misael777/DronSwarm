#!/usr/bin/env python3
"""S10-02 · Adquisición del banco de empuje: corre una secuencia de ensayo y guarda el CSV crudo + metadatos.

    # banco real (ESP32 por USB):
    .venv/bin/python tools/bench/acquire.py sweep --port /dev/ttyUSB0 --motor "T-Motor MN4006 KV380 (AntiGravity)" \\
        --prop 15 --esc "4 en 1 50 A" --battery "6S2P 50S" --site-alt 150 --ambient 20
    # sin hardware (modelo de ingeniería con ruido), para probar el análisis:
    .venv/bin/python tools/bench/acquire.py sweep --simulate --motor "MAD M6C12 EEE KV150" --prop 26 --battery 12S5P

Ensayos: noload (sin hélice: Kv, I0) · sweep (5-100 % en pasos de 5 %) · hover (empuje fijo 10 min, temperatura).
Calibración: `acquire.py calibrate --port …` (pide masas patrón).
Seguridad: el firmware corta solo si no recibe comandos en 1 s, si pasa la corriente o la temperatura, o con `S`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchlib import DATA, RAW_COLS, Calibration, Meta, SimBench, write_raw  # noqa: E402

STEP_S, AVG_S = 4.0, 2.0


class SerialBench:
    def __init__(self, port: str):
        import serial  # pyserial: solo hace falta con el banco real
        self.s = serial.Serial(port, 921600, timeout=0.05)
        time.sleep(2)
        self.s.reset_input_buffer()

    def cmd(self, c: str):
        self.s.write((c + "\n").encode())

    def read_rows(self, seconds: float, throttle: int) -> list[dict]:
        rows, t_end, buf = [], time.monotonic() + seconds, b""
        while time.monotonic() < t_end:
            self.cmd(f"T{throttle}")                       # mantiene vivo el watchdog del firmware
            buf += self.s.read(4096)
            *lines, buf = buf.split(b"\n")
            for ln in lines:
                txt = ln.decode(errors="ignore").strip()
                if txt.startswith("ABORT"):
                    raise RuntimeError(f"el banco abortó: {txt}")
                parts = txt.split(",")
                if len(parts) == len(RAW_COLS) and parts[0].isdigit():
                    rows.append(dict(zip(RAW_COLS, parts)))
            time.sleep(0.2)
        return rows


def throttle_plan(test: str, hover_us: int | None) -> list[tuple[int, float]]:
    if test == "noload":
        return [(1000 + p * 10, STEP_S) for p in list(range(20, 85, 10)) + [100]]   # a fondo: el Kv se mide al 100 %
    if test == "sweep":
        return [(1000 + p * 10, STEP_S) for p in range(5, 105, 5)]
    if test == "hover":
        return [(hover_us or 1500, 600.0)]
    raise ValueError(test)


def run_sim(a, plan) -> list[dict]:
    pitch = 0.45                                       # relación paso/diámetro del dimensionamiento
    v = 3.7 * int(a.battery.split("S")[0])
    sim = SimBench(a.motor, a.prop, pitch, v, a.site_alt, a.ambient, seed=a.seed, no_prop=(a.test == "noload"))
    rows, t = [], 0
    for us, dur in plan:
        for _ in range(int(dur * 50)):
            rows.append(sim.sample(t, us))
            t += 20
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("test", choices=["noload", "sweep", "hover", "calibrate"])
    ap.add_argument("--port")
    ap.add_argument("--simulate", action="store_true", help="banco virtual (modelo de ingeniería + ruido)")
    ap.add_argument("--motor", default="T-Motor MN4006 KV380 (AntiGravity)")
    ap.add_argument("--prop", type=float, default=15)
    ap.add_argument("--esc", default="")
    ap.add_argument("--battery", default="6S2P 50S")
    ap.add_argument("--vehicle")
    ap.add_argument("--site-alt", type=float, default=150)
    ap.add_argument("--ambient", type=float, default=20)
    ap.add_argument("--pressure", type=float, help="presión del lugar [hPa] (mejor que la altitud)")
    ap.add_argument("--hover-us", type=int)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()

    if a.test == "calibrate":
        b = SerialBench(a.port)
        cal = Calibration.load()
        b.cmd("Z")
        input("Celdas en cero. Pon 2.000 kg sobre el punto de empuje y presiona Enter…")
        r = b.read_rows(3, 1000)
        thr = sum(float(x["thrust_raw"]) for x in r) / len(r)
        cal.thrust_n_per_count = 2.0 * 9.80665 / thr
        for side, key in (("A", "torque_a_raw"), ("B", "torque_b_raw")):
            input(f"Quita la masa. Pon 1.000 kg sobre la celda de torque {side} y presiona Enter…")
            r = b.read_rows(3, 1000)
            setattr(cal, f"torque_{side.lower()}_n_per_count", 9.80665 / abs(sum(float(x[key]) for x in r) / len(r)))
        cal.save()
        print("calibración guardada en", DATA / "calibracion.json")
        return

    plan = throttle_plan(a.test, a.hover_us)
    meta = Meta(a.motor, f"{a.prop:g}\"", a.prop, a.esc, a.battery, a.test, a.site_alt, a.ambient, a.pressure, a.vehicle,
                notes="simulado (modelo de ingeniería)" if a.simulate else "")
    if a.simulate:
        rows = run_sim(a, plan)
    else:
        if not a.port:
            raise SystemExit("falta --port (o --simulate)")
        b = SerialBench(a.port)
        b.cmd("T1000")
        b.cmd("A")
        rows = []
        try:
            for us, dur in plan:
                print(f"  throttle {us} µs durante {dur:.0f} s", flush=True)
                rows += b.read_rows(dur, us)
        finally:
            b.cmd("S")
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = "".join(ch if ch.isalnum() else "_" for ch in f"{a.motor}_{a.prop:g}in")[:60]
    out = a.out or DATA / f"{slug}_{a.test}_{stamp}{'_sim' if a.simulate else ''}.csv"
    write_raw(out, rows, meta)
    print(out)


if __name__ == "__main__":
    main()
