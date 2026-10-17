#!/usr/bin/env python3
"""Grafica altura, velocidad vertical y empuje de un log de PX4 (.ulg).

    python tools/sitl/plot_flight.py docs/evidencias/sitl/smoke_test.ulg docs/evidencias/sitl/smoke_test.png
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from pyulog import ULog  # noqa: E402


def topic(ulog: ULog, name: str):
    for d in ulog.data_list:
        if d.name == name:
            return d.data
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ulg", type=Path)
    ap.add_argument("png", type=Path)
    ap.add_argument("--title", default="PX4 SITL (SIH) · prueba de humo: despegue a 10 m, hover y aterrizaje")
    a = ap.parse_args()

    ulog = ULog(str(a.ulg))
    t0 = ulog.start_timestamp
    pos = topic(ulog, "vehicle_local_position")
    thrust = topic(ulog, "vehicle_thrust_setpoint")
    status = topic(ulog, "vehicle_status")

    fig, axes = plt.subplots(3, 1, figsize=(9, 7), sharex=True, dpi=150)
    t = (pos["timestamp"] - t0) / 1e6
    axes[0].plot(t, -pos["z"], color="#2c5282")
    axes[0].set_ylabel("Altura [m]")
    axes[0].axhline(10, ls="--", lw=0.8, color="#a0aec0")
    axes[1].plot(t, -pos["vz"], color="#2c5282")
    axes[1].set_ylabel("Vel. vertical [m/s]")
    if thrust is not None:
        tt = (thrust["timestamp"] - t0) / 1e6
        axes[2].plot(tt, -thrust["xyz[2]"], color="#c05621")
        axes[2].set_ylabel("Empuje normalizado")
    if status is not None:
        ts = (status["timestamp"] - t0) / 1e6
        armed = status["arming_state"] == 2
        for ax in axes:
            ax.fill_between(ts, 0, 1, where=armed, step="post", color="#c6f6d5", alpha=0.5,
                            transform=ax.get_xaxis_transform(), label="armado")
    axes[2].set_xlabel("Tiempo [s]")
    for ax in axes:
        ax.grid(alpha=0.3)
    axes[0].set_title(a.title, fontsize=10)
    hover = None
    if thrust is not None:
        mask = (-pos["z"] > 8)
        if mask.any():
            t_hover = t[mask]
            sel = (tt >= t_hover.min()) & (tt <= t_hover.max())
            hover = float(np.median(-thrust["xyz[2]"][sel]))
            axes[2].axhline(hover, ls="--", lw=0.8, color="#a0aec0")
    a.png.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(a.png)
    print(f"PNG: {a.png} · altura máx {(-pos['z']).max():.2f} m · empuje de hover {hover:.2f}" if hover else f"PNG: {a.png}")


if __name__ == "__main__":
    main()
