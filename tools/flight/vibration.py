#!/usr/bin/env python3
"""S11-04 · Vibración desde un log de PX4 (.ulg): métricas de vibración, espectro de la aceleración y filtros.

- Métrica de PX4 (vehicle_imu_status.accel_vibration_metric): < 15 m/s² bien, 15-30 aceptable, > 30 hay que corregir.
- FFT de la aceleración (sensor_combined) en vuelo: picos contra 1P y 2P de las rpm medidas (esc_status o salidas).
- Recomendación: filtro notch dinámico por rpm de ESC (IMU_GYRO_DNF_EN) o, si no hay telemetría, notch fijo en el pico.

    .venv/bin/python tools/flight/vibration.py logs/…/vuelo.ulg --png vib.png --out vib.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from pyulog import ULog


def topic(u: ULog, name: str):
    for d in u.data_list:
        if d.name == name:
            return d.data
    return None


def analyze(path: Path) -> dict:
    u = ULog(str(path))
    sc = topic(u, "sensor_combined")

    land = topic(u, "vehicle_land_detected")
    t = sc["timestamp"] / 1e6
    acc = np.column_stack([sc[f"accelerometer_m_s2[{i}]"] for i in range(3)])
    # tramo en vuelo
    flying = np.ones_like(t, dtype=bool)
    if land is not None:
        k = np.clip(np.searchsorted(land["timestamp"] / 1e6, t) - 1, 0, len(land["timestamp"]) - 1)
        flying = ~land["landed"][k].astype(bool)
    if flying.sum() < 512:
        raise ValueError("el log no tiene tramo en vuelo suficiente")
    a = acc[flying]
    fs = 1 / np.median(np.diff(t[flying]))
    a = a - a.mean(axis=0)
    n = 2 ** int(np.log2(min(len(a), 2 ** 15)))
    win = np.hanning(n)
    spec = np.abs(np.fft.rfft(a[:n] * win[:, None], axis=0)) * 2 / win.sum()
    freqs = np.fft.rfftfreq(n, 1 / fs)
    mag = np.linalg.norm(spec, axis=1)
    band = freqs > 5
    peak_f = float(freqs[band][np.argmax(mag[band])])
    # rpm de referencia: telemetría de ESC si existe, si no las salidas a los motores (en SITL son rad/s)
    rpm = None
    esc = topic(u, "esc_status")
    if esc is not None and "esc[0].esc_rpm" in esc:
        rpm = float(np.median(esc["esc[0].esc_rpm"][esc["esc[0].esc_rpm"] > 0]))
    imu = topic(u, "vehicle_imu_status")
    vib = float(np.percentile(imu["accel_vibration_metric"], 95)) if imu is not None else None
    res = {"log": path.name, "sample_rate_hz": round(fs), "flight_samples": int(flying.sum()),
           "accel_vibration_metric_p95": round(vib, 2) if vib is not None else None,
           "accel_rms_m_s2": [round(float(x), 3) for x in np.sqrt((a ** 2).mean(axis=0))],
           "peak_hz": round(peak_f, 1), "rpm_esc_median": round(rpm) if rpm else None}
    if rpm:
        f1 = rpm / 60
        res.update({"f_1p_hz": round(f1, 1), "f_2p_hz": round(2 * f1, 1),
                    "peak_is_rotor_harmonic": any(abs(peak_f - k * f1) / (k * f1) < 0.08 for k in (1, 2, 3))})
    level = "sin métrica" if vib is None else ("bien" if vib < 15 else "aceptable" if vib < 30 else "CORREGIR")
    res["verdict"] = level
    res["recommendation"] = (
        "Vibración alta: revisar balanceo de hélices, apriete de los soportes de motor y aislamiento de la controladora "
        "antes de afinar filtros." if level == "CORREGIR" else
        "Filtro notch dinámico por rpm de ESC (IMU_GYRO_DNF_EN = 1); si no hay telemetría de ESC, "
        f"notch fijo IMU_GYRO_NF0_FRQ = {peak_f:.0f} Hz con IMU_GYRO_NF0_BW = {max(10, peak_f * 0.3):.0f} Hz.")
    res["_spectrum"] = (freqs, mag)

    return res


def plot(res: dict, png: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    f, m = res["_spectrum"]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.semilogy(f, m, lw=0.8)
    for key, lab in (("f_1p_hz", "1P"), ("f_2p_hz", "2P")):
        if res.get(key):
            ax.axvline(res[key], color="C3", ls="--", lw=0.8)
            ax.annotate(lab, (res[key], m.max()), fontsize=8, color="C3")
    ax.set_xlabel("frecuencia [Hz]")
    ax.set_ylabel("aceleración [m/s²]")
    ax.set_title(f"Espectro de vibración en vuelo · pico {res['peak_hz']} Hz · {res['verdict']}", fontsize=10)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(png, dpi=120)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ulg", type=Path)
    ap.add_argument("--png", type=Path)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    res = analyze(a.ulg)
    if a.png:
        plot(res, a.png)
    out = {k: v for k, v in res.items() if not k.startswith("_")}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if a.out:
        a.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
