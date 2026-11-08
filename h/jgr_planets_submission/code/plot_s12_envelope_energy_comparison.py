"""Plot S12 envelope and cumulative-energy comparisons for M1-M6 and Apollo."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).resolve()
SUBMISSION_ROOT = SCRIPT.parents[1]
WORKSPACE_ROOT = SCRIPT.parents[2]
LOCAL_PACKAGES = WORKSPACE_ROOT / "work" / "python_pkgs"
if LOCAL_PACKAGES.is_dir():
    sys.path.insert(0, str(LOCAL_PACKAGES))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy.ndimage import uniform_filter1d
from scipy.signal import hilbert

from analyze_low_velocity_models import (
    COMMON_DT_S,
    COMMON_END_S,
    COMMON_START_S,
    MODEL_COLORS,
    MODEL_FILES,
    MODEL_LABELS,
    OBSERVED_FILES,
    build_station_geometry,
    configure_plot_style,
    load_model,
    load_observed,
    source_scale,
)


FIGURE_DIR = SUBMISSION_ROOT / "figures" / "low_velocity"
DERIVED_DIR = SUBMISSION_ROOT / "data" / "derived"
SMOOTHING_S = 20.0


def envelope(time: np.ndarray, zen: np.ndarray) -> np.ndarray:
    intensity = np.sum(np.abs(hilbert(zen, axis=1)) ** 2, axis=0)
    samples = max(1, int(round(SMOOTHING_S / float(np.median(np.diff(time))))))
    return uniform_filter1d(intensity, samples, mode="nearest")


def energy_curve(time: np.ndarray, zen: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    keep = time >= COMMON_START_S
    t = np.asarray(time[keep], dtype=float)
    power = np.sum(np.asarray(zen[:, keep], dtype=float) ** 2, axis=0)
    dt = float(np.median(np.diff(t)))
    return t, np.cumsum(power, dtype=float) * dt


def value_at_or_before(time: np.ndarray, values: np.ndarray, target: float) -> float:
    index = int(np.searchsorted(time, target, side="right") - 1)
    index = max(0, min(index, values.size - 1))
    return float(values[index])


def main() -> None:
    configure_plot_style()
    geometry = build_station_geometry()
    common_time = np.arange(COMMON_START_S, COMMON_END_S + COMMON_DT_S / 2, COMMON_DT_S)
    extended_time = np.arange(COMMON_START_S, 395.0 + COMMON_DT_S / 2, COMMON_DT_S)
    records = {}
    for name, path in MODEL_FILES.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing {name}: {path}")
        records[name] = load_model(name, geometry, common_time, extended_time)
    for key, path in OBSERVED_FILES.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing observed {key}: {path}")
    observed = load_observed(geometry)

    traces: dict[str, tuple[np.ndarray, np.ndarray, float]] = {}
    traces["Observed"] = (observed.time, observed.zen, 1.0)
    for name, record in records.items():
        traces[name] = (record.s12_time, record.s12_zen, float(source_scale(observed, record)))

    obs_time, obs_zen, _ = traces["Observed"]
    obs_env = envelope(obs_time, obs_zen)
    obs_ref_mask = (obs_time >= COMMON_START_S) & (obs_time <= 1000.0)
    observed_peak_reference = max(float(np.max(obs_env[obs_ref_mask])), np.finfo(float).eps)

    # Figure 1: source-scaled envelope, with the Apollo tail visible to 1000 s.
    fig, ax = plt.subplots(figsize=(11.8, 5.7), constrained_layout=True)
    ax.plot(
        obs_time,
        np.maximum(obs_env / observed_peak_reference, 1e-12),
        color="#222222",
        linewidth=1.35,
        label="Apollo S12 observation",
        zorder=1,
    )
    envelope_max_ratio = float(np.nanmax(obs_env[obs_ref_mask] / observed_peak_reference))
    for name, (time, zen, scale) in traces.items():
        if name == "Observed":
            continue
        model_env = envelope(time, zen * scale)
        model_mask = (time >= COMMON_START_S) & (time <= 1000.0)
        envelope_max_ratio = max(
            envelope_max_ratio,
            float(np.nanmax(model_env[model_mask] / observed_peak_reference)),
        )
        ax.plot(
            time,
            np.maximum(model_env / observed_peak_reference, 1e-12),
            color=MODEL_COLORS[name],
            linewidth=1.0,
            alpha=0.9,
            label=name,
            zorder=2,
        )
    ax.axvline(COMMON_END_S, color="#777777", linestyle="--", linewidth=0.8, label="245 s boundary")
    ax.axvline(400.0, color="#777777", linestyle=":", linewidth=0.8, label="400 s boundary")
    ax.set_xlim(COMMON_START_S, 1000.0)
    ax.set_yscale("log")
    ax.set_ylim(1e-5, 1.3 * max(1.0, envelope_max_ratio))
    ax.set_xlabel("Time after impact (s)")
    ax.set_ylabel("20 s smoothed 3C envelope / observed peak")
    ax.set_title("S12 envelope comparison: M1-M6 versus Apollo observation")
    ax.legend(ncol=4, fontsize=8.0, loc="upper right")
    ax.text(
        0.01,
        0.02,
        "Models are source-scaled by the 50–245 s 3-C RMS ratio; model endpoints remain visible.",
        transform=ax.transAxes,
        fontsize=8.0,
        color="#555555",
    )
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    envelope_path = FIGURE_DIR / "Figure_S12_M1_M6_observed_envelope_comparison.png"
    fig.savefig(envelope_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # Figure 2: absolute cumulative energy and per-record normalized energy.
    energy_data: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    energy_summary: list[dict[str, object]] = []
    for name, (time, zen, scale) in traces.items():
        t, cumulative = energy_curve(time, zen * scale)
        energy_data[name] = (t, cumulative)
        total = float(cumulative[-1])
        t95 = float(t[np.searchsorted(cumulative, 0.95 * total, side="left")])
        energy_summary.append(
            {
                "record": name,
                "source_scale_50_245s_3c_rms": scale,
                "record_end_s": float(time[-1]),
                "cumulative_energy_total_scaled": total,
                "t95_squared_velocity_energy_s": t95,
                "fraction_before_250s": value_at_or_before(t, cumulative, 250.0) / total,
                "fraction_before_400s": value_at_or_before(t, cumulative, 400.0) / total,
            }
        )
    observed_reference_energy = value_at_or_before(*energy_data["Observed"], 245.0)
    observed_reference_energy = max(observed_reference_energy, np.finfo(float).eps)

    fig, axes = plt.subplots(2, 1, figsize=(11.8, 8.2), constrained_layout=True)
    for name, (time, cumulative) in energy_data.items():
        color = "#222222" if name == "Observed" else MODEL_COLORS[name]
        axes[0].plot(
            time,
            np.maximum(cumulative / observed_reference_energy, 1e-12),
            color=color,
            linewidth=1.15 if name == "Observed" else 0.95,
            alpha=0.9,
            label=name,
        )
        axes[1].plot(
            time,
            cumulative / cumulative[-1],
            color=color,
            linewidth=1.15 if name == "Observed" else 0.95,
            alpha=0.9,
            label=name,
        )
    for ax in axes:
        ax.axvline(COMMON_END_S, color="#777777", linestyle="--", linewidth=0.8)
        ax.axvline(400.0, color="#777777", linestyle=":", linewidth=0.8)
        ax.set_xlim(COMMON_START_S, 3000.0)
        ax.grid(True, alpha=0.22)
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Cumulative 3C energy / observed 50–245 s energy")
    axes[0].set_title("Absolute cumulative energy after shared source scaling")
    axes[1].set_ylim(0.0, 1.02)
    axes[1].set_ylabel("Cumulative energy / each record total")
    axes[1].set_xlabel("Time after impact (s)")
    axes[1].set_title("Normalized cumulative energy: record duration and coda coverage")
    axes[0].legend(ncol=4, fontsize=8.0, loc="upper left")
    axes[1].text(
        0.01,
        0.04,
        "Dashed = 245 s; dotted = 400 s. Normalized curves use each available record endpoint.",
        transform=axes[1].transAxes,
        fontsize=8.0,
        color="#555555",
    )
    fig.suptitle("S12 cumulative-energy comparison: M1-M6 versus Apollo observation", fontsize=12.5)
    energy_path = FIGURE_DIR / "Figure_S12_M1_M6_observed_energy_comparison.png"
    fig.savefig(energy_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    summary_path = DERIVED_DIR / "s12_m1_m6_observed_envelope_energy_summary.csv"
    with summary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(energy_summary[0]))
        writer.writeheader()
        writer.writerows(energy_summary)

    print(f"Wrote {envelope_path}")
    print(f"Wrote {energy_path}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
