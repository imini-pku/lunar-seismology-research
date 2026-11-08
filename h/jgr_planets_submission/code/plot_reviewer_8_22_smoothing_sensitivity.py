"""Figure for Reviewer 2 comment 8.22: envelope-smoothing sensitivity."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT.parent))

import analyze_low_velocity_models as lv


OUT_DIR = lv.SUBMISSION_ROOT / "figures" / "reviewer_response"
CSV_OUT = lv.DERIVED_DIR / "reviewer_8_22_smoothing_sensitivity.csv"

DISPLAY_LABELS = {
    "Observed": "Apollo S12 observation",
    "M1": "M1  Flat / no H",
    "M2": "M2  Topography / no H",
    "M3": "M3  Flat / H",
    "M4": "M4  Topography / H",
    "M5": "M5  Flat / H / low-V",
    "M6": "M6  Topography / H / low-V",
}

COLORS = {
    "Observed": "#222222",
    "M1": "#0072B2",
    "M2": "#D55E00",
    "M3": "#009E73",
    "M4": "#CC79A7",
    "M5": "#E69F00",
    "M6": "#56B4E9",
}

MARKERS = {
    "Observed": "o",
    "M1": "s",
    "M2": "^",
    "M3": "D",
    "M4": "v",
    "M5": "P",
    "M6": "X",
}


def model_s12(name: str) -> tuple[lv.np.ndarray, lv.np.ndarray]:
    """Read and filter only the S12 receiver, avoiding a full 606-station reload."""
    with lv.Dataset(lv.MODEL_FILES[name], "r") as dataset:
        time = lv.np.asarray(dataset.variables["time"][:], dtype=float)
        traces = []
        for variable in ("Vz", "Vx", "Vy"):
            values = dataset.variables[variable]
            if values.shape[0] == 606:
                trace = lv.np.asarray(values[0, :], dtype=float)
            elif values.shape[1] == 606:
                trace = lv.np.asarray(values[:, 0], dtype=float)
            else:
                raise ValueError(f"Unexpected {name}/{variable} shape: {values.shape}")
            traces.append(trace)
    zen = lv.filter_component(time, lv.np.vstack(traces))
    return time, zen


def sensitivity(time: lv.np.ndarray, zen: lv.np.ndarray) -> tuple[list[dict[str, float]], dict[float, lv.np.ndarray]]:
    intensity = lv.np.sum(lv.np.abs(lv.hilbert(zen, axis=1)) ** 2, axis=0)
    dt = float(lv.np.median(lv.np.diff(time)))
    cumulative = lv.np.cumsum(intensity, dtype=float) * dt
    t05 = float(time[min(lv.np.searchsorted(cumulative, 0.05 * cumulative[-1]), time.size - 1)])
    rows: list[dict[str, float]] = []
    smoothed: dict[float, lv.np.ndarray] = {}
    for window in lv.SMOOTHING_WINDOWS_S:
        curve = lv.uniform_filter1d(
            intensity,
            max(1, int(round(window / dt))),
            mode="nearest",
        )
        tmax = float(time[int(lv.np.argmax(curve))])
        rows.append(
            {
                "smoothing_window_s": float(window),
                "t05_s": t05,
                "peak_energy_time_s": tmax,
                "rise_time_t05_to_peak_s": tmax - t05,
            }
        )
        smoothed[float(window)] = curve
    return rows, smoothed


def main() -> None:
    lv.configure_plot_style()
    lv.plt.rcParams.update(
        {
            "font.size": 9.2,
            "axes.titlesize": 10.5,
            "axes.labelsize": 9.8,
            "legend.fontsize": 8.2,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    geometry = lv.build_station_geometry()
    observed = lv.load_observed(geometry)
    records: dict[str, tuple[lv.np.ndarray, lv.np.ndarray]] = {
        "Observed": (observed.time, observed.zen)
    }
    for name in ("M1", "M2", "M3", "M4", "M5", "M6"):
        records[name] = model_s12(name)

    all_rows: list[dict[str, object]] = []
    curves: dict[str, dict[float, lv.np.ndarray]] = {}
    for name, (time, zen) in records.items():
        rows, smooth = sensitivity(time, zen)
        curves[name] = smooth
        for row in rows:
            all_rows.append({"record": name, "description": DISPLAY_LABELS[name], **row})

    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)

    by_record = {
        name: [row for row in all_rows if row["record"] == name]
        for name in records
    }
    selected_window = 20.0
    deviations = []
    for rows in by_record.values():
        values = lv.np.asarray([float(row["peak_energy_time_s"]) for row in rows])
        selected = float(
            next(
                row["peak_energy_time_s"]
                for row in rows
                if float(row["smoothing_window_s"]) == selected_window
            )
        )
        deviations.append(abs(selected - float(lv.np.median(values))))
    mean_selected_deviation = float(lv.np.mean(deviations))
    max_selected_deviation = float(lv.np.max(deviations))

    fig = lv.plt.figure(figsize=(11.3, 8.3))
    grid = fig.add_gridspec(3, 1, height_ratios=(1.35, 1.0, 1.0), hspace=0.37)
    ax0 = fig.add_subplot(grid[0])
    ax1 = fig.add_subplot(grid[1])
    ax2 = fig.add_subplot(grid[2], sharex=ax1)

    # Panel a: the observed envelope itself under all requested windows.
    obs_time = records["Observed"][0]
    window_colors = lv.plt.cm.viridis(lv.np.linspace(0.08, 0.88, len(lv.SMOOTHING_WINDOWS_S)))
    for color, window in zip(window_colors, lv.SMOOTHING_WINDOWS_S, strict=True):
        curve = curves["Observed"][float(window)]
        visible = (obs_time >= 0.0) & (obs_time <= 1000.0)
        scale = max(float(lv.np.max(curve[visible])), lv.EPS)
        selected = float(window) == selected_window
        ax0.plot(
            obs_time[visible],
            curve[visible] / scale,
            color=color,
            label=f"{window:g} s" + (" (selected)" if selected else ""),
            linewidth=2.3 if selected else 1.0,
            zorder=4 if selected else 2,
        )
    ax0.set_xlim(0, 1000)
    ax0.set_ylim(-0.02, 1.06)
    ax0.set_ylabel("Normalized 3-C energy envelope")
    ax0.set_xlabel("Time after impact (s)")
    ax0.set_title("(a) Apollo S12 envelope at six smoothing-window durations", loc="left", fontweight="bold")
    ax0.legend(title="Window", ncol=6, loc="upper left")

    # Panels b-c: peak and rise-time sensitivity for observation and all six models.
    for name, rows in by_record.items():
        x = lv.np.asarray([float(row["smoothing_window_s"]) for row in rows])
        peak = lv.np.asarray([float(row["peak_energy_time_s"]) for row in rows])
        rise = lv.np.asarray([float(row["rise_time_t05_to_peak_s"]) for row in rows])
        style = {
            "color": COLORS[name],
            "marker": MARKERS[name],
            "markersize": 5.5 if name == "Observed" else 4.7,
            "linewidth": 2.0 if name == "Observed" else 1.25,
            "label": DISPLAY_LABELS[name],
        }
        ax1.plot(x, peak, **style)
        ax2.plot(x, rise, **style)

    observed_peak = lv.np.asarray(
        [float(row["peak_energy_time_s"]) for row in by_record["Observed"]]
    )
    ax1.axhspan(float(observed_peak.min()), float(observed_peak.max()), color="#BDBDBD", alpha=0.18, linewidth=0)
    ax1.annotate(
        f"Observed median = {lv.np.median(observed_peak):.1f} s\nrange = {observed_peak.min():.1f}–{observed_peak.max():.1f} s",
        xy=(60, float(lv.np.median(observed_peak))),
        xytext=(64, 545),
        arrowprops={"arrowstyle": "->", "color": "#444444", "lw": 0.9},
        color="#333333",
        ha="left",
        va="top",
    )
    ax1.set_ylim(0, 820)
    ax1.set_ylabel("Smoothed energy-peak time (s)")
    ax1.set_title("(b) Peak-time sensitivity", loc="left", fontweight="bold")
    ax1.legend(ncol=2, loc="center left", bbox_to_anchor=(0.01, 0.58))
    ax1.axvline(selected_window, color="#555555", linestyle="--", linewidth=1.0)
    ax1.annotate(
        "20 s selected\nmean |deviation| = "
        f"{mean_selected_deviation:.1f} s; maximum = {max_selected_deviation:.1f} s",
        xy=(selected_window, 320),
        xytext=(27, 370),
        arrowprops={"arrowstyle": "->", "color": "#555555", "lw": 0.9},
        color="#333333",
        ha="left",
        va="center",
    )

    ax2.axhline(0, color="#777777", linewidth=0.8)
    ax2.set_ylim(-80, 540)
    ax2.set_ylabel("Rise time from 5% energy to peak (s)")
    ax2.set_xlabel("Envelope smoothing-window duration (s)")
    ax2.set_title("(c) Rise-time sensitivity", loc="left", fontweight="bold")
    ax2.set_xticks(lv.SMOOTHING_WINDOWS_S)
    ax2.axvline(selected_window, color="#555555", linestyle="--", linewidth=1.0)

    for axis in (ax0, ax1, ax2):
        axis.grid(True, color="#D9D9D9", alpha=0.65, linewidth=0.6)
        axis.spines[["top", "right"]].set_visible(False)

    fig.suptitle(
        "Sensitivity of energy-envelope peak and rise times to smoothing-window duration",
        fontsize=13.2,
        fontweight="bold",
        y=0.985,
    )
    fig.text(
        0.5,
        0.952,
        "Three-component analytic-signal energy, band-pass filtered at 0.3–0.9 Hz; H denotes heterogeneous structure",
        ha="center",
        color="#555555",
        fontsize=9.1,
    )
    fig.subplots_adjust(left=0.09, right=0.985, bottom=0.075, top=0.915)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = OUT_DIR / "Figure_R8_22_envelope_smoothing_sensitivity_selected20s"
    fig.savefig(base.with_suffix(".png"), dpi=400, bbox_inches="tight", facecolor="white")
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    fig.savefig(
        base.with_suffix(".tiff"),
        dpi=400,
        bbox_inches="tight",
        facecolor="white",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    lv.plt.close(fig)


if __name__ == "__main__":
    main()
