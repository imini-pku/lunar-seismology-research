"""Plot separate Z, R, and T analytic-amplitude envelopes at S12."""

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
COMPONENTS = ("Z", "R", "T")


def component_envelope(time: np.ndarray, trace: np.ndarray) -> np.ndarray:
    amplitude = np.abs(hilbert(np.asarray(trace, dtype=float)))
    samples = max(1, int(round(SMOOTHING_S / float(np.median(np.diff(time))))))
    return uniform_filter1d(amplitude, samples, mode="nearest")


def s12_zrt(zen: np.ndarray, azimuth_rad: float) -> np.ndarray:
    vertical, east, north = np.asarray(zen, dtype=float)
    sine = float(np.sin(azimuth_rad))
    cosine = float(np.cos(azimuth_rad))
    radial = east * sine + north * cosine
    transverse = east * cosine - north * sine
    return np.vstack((vertical, radial, transverse))


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

    fields: dict[str, tuple[np.ndarray, np.ndarray, float]] = {
        "Observed": (observed.time, observed.zrt, 1.0)
    }
    azimuth = float(geometry.azimuth_rad[0])
    for name, record in records.items():
        fields[name] = (record.s12_time, s12_zrt(record.s12_zen, azimuth), float(source_scale(observed, record)))

    normalized: dict[str, list[np.ndarray]] = {}
    summaries: list[dict[str, object]] = []
    for component_index, component in enumerate(COMPONENTS):
        observed_time, observed_field, _ = fields["Observed"]
        observed_env = component_envelope(observed_time, observed_field[component_index])
        observed_window = (observed_time >= COMMON_START_S) & (observed_time <= 1000.0)
        reference = max(float(np.max(observed_env[observed_window])), np.finfo(float).eps)
        normalized[component] = []
        for name, (time, field, scale) in fields.items():
            env = component_envelope(time, field[component_index] * scale)
            normalized[component].append(env / reference)
            available = (time >= COMMON_START_S) & (time <= 1000.0)
            peak_index = int(np.argmax(env[available]))
            available_indices = np.flatnonzero(available)
            peak_time = float(time[available_indices[peak_index]])
            summaries.append(
                {
                    "record": name,
                    "component": component,
                    "source_scale_50_245s_3c_rms": scale,
                    "observed_component_peak_reference": reference,
                    "envelope_peak_time_s_50_1000": peak_time,
                    "record_end_s": float(time[-1]),
                }
            )

    fig, axes = plt.subplots(3, 1, figsize=(11.8, 9.4), sharex=True, constrained_layout=True)
    for component_index, component in enumerate(COMPONENTS):
        ax = axes[component_index]
        reference_max = 0.0
        for name, (time, _field, _scale) in fields.items():
            env = normalized[component][0 if name == "Observed" else list(records).index(name) + 1]
            mask = (time >= COMMON_START_S) & (time <= 1000.0)
            reference_max = max(reference_max, float(np.nanmax(env[mask])))
            color = "#222222" if name == "Observed" else MODEL_COLORS[name]
            ax.plot(
                time,
                np.maximum(env, 1e-12),
                color=color,
                linewidth=1.35 if name == "Observed" else 0.95,
                alpha=0.9,
                label=name,
            )
        ax.axvline(COMMON_END_S, color="#777777", linestyle="--", linewidth=0.8)
        ax.axvline(400.0, color="#777777", linestyle=":", linewidth=0.8)
        ax.set_xlim(COMMON_START_S, 1000.0)
        ax.set_ylim(1e-5, 1.25 * max(1.0, reference_max))
        ax.set_yscale("log")
        ax.set_ylabel(f"{component} envelope / observed {component} peak")
        ax.set_title(f"{component} component: 20 s smoothed analytic-amplitude envelope", loc="left")
        if component_index == 0:
            ax.legend(ncol=4, fontsize=8.0, loc="upper right")
    axes[-1].set_xlabel("Time after impact (s)")
    axes[-1].text(
        0.01,
        0.04,
        "Dashed = 245 s; dotted = 400 s. Each row is normalized by the observed component peak.",
        transform=axes[-1].transAxes,
        fontsize=8.0,
        color="#555555",
    )
    fig.suptitle("S12 individual-component envelopes: M1-M6 versus Apollo observation", fontsize=12.5)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    output = FIGURE_DIR / "Figure_S12_M1_M6_observed_component_envelopes.png"
    fig.savefig(output, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    summary_path = DERIVED_DIR / "s12_m1_m6_observed_component_envelope_summary.csv"
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    print(f"Wrote {output}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
