"""Plot Z/R/T envelope correlation coefficients between M1-M6 and Apollo S12."""

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

from analyze_low_velocity_models import (
    COMMON_DT_S,
    COMMON_END_S,
    COMMON_START_S,
    MODEL_COLORS,
    MODEL_FILES,
    OBSERVED_FILES,
    best_lag_1d,
    build_station_geometry,
    configure_plot_style,
    load_model,
    load_observed,
    source_scale,
)
from plot_s12_component_envelopes import component_envelope, s12_zrt


FIGURE_DIR = SUBMISSION_ROOT / "figures" / "low_velocity"
DERIVED_DIR = SUBMISSION_ROOT / "data" / "derived"
COMPONENTS = ("Z", "R", "T")
COMPONENT_COLORS = {"Z": "#0072B2", "R": "#D55E00", "T": "#009E73"}


def correlation(first: np.ndarray, second: np.ndarray) -> float:
    value = float(np.corrcoef(first, second)[0, 1])
    return value if np.isfinite(value) else float("nan")


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

    observed_components = observed.zrt
    observed_env = np.vstack(
        [
            np.interp(
                common_time,
                observed.time,
                component_envelope(observed.time, observed_components[index]),
            )
            for index in range(3)
        ]
    )
    azimuth = float(geometry.azimuth_rad[0])
    rows: list[dict[str, object]] = []
    zero_lag: dict[str, list[float]] = {component: [] for component in COMPONENTS}
    best_lag: dict[str, list[float]] = {component: [] for component in COMPONENTS}
    best_lag_seconds: dict[str, list[float]] = {component: [] for component in COMPONENTS}

    for name, record in records.items():
        scale = float(source_scale(observed, record))
        model_components = s12_zrt(record.s12_zen, azimuth) * scale
        model_env = np.vstack(
            [
                np.interp(
                    common_time,
                    record.s12_time,
                    component_envelope(record.s12_time, model_components[index]),
                )
                for index in range(3)
            ]
        )
        for index, component in enumerate(COMPONENTS):
            zero = correlation(observed_env[index], model_env[index])
            best, lag_s = best_lag_1d(observed_env[index], model_env[index], COMMON_DT_S, maximum_lag_s=10.0)
            zero_lag[component].append(zero)
            best_lag[component].append(best)
            best_lag_seconds[component].append(lag_s)
            rows.append(
                {
                    "model": name,
                    "component": component,
                    "window_start_s": COMMON_START_S,
                    "window_end_s": COMMON_END_S,
                    "smoothing_s": 20.0,
                    "zero_lag_envelope_correlation": zero,
                    "best_lag_envelope_correlation_pm10s": best,
                    "best_lag_s": lag_s,
                    "source_scale_50_245s_3c_rms": scale,
                }
            )

    model_names = tuple(records)
    x = np.arange(len(model_names), dtype=float)
    fig, ax = plt.subplots(figsize=(10.8, 5.8), constrained_layout=True)
    for component in COMPONENTS:
        color = COMPONENT_COLORS[component]
        ax.plot(
            x,
            zero_lag[component],
            color=color,
            marker="o",
            markersize=5.2,
            linewidth=1.25,
            label=f"{component} zero lag",
        )
        ax.plot(
            x,
            best_lag[component],
            color=color,
            marker="s",
            markersize=4.8,
            markerfacecolor="white",
            markeredgewidth=1.0,
            linestyle="--",
            linewidth=1.0,
            label=f"{component} best lag ±10 s",
        )
    ax.axhline(0.0, color="#777777", linewidth=0.8)
    ax.axhline(1.0, color="#BBBBBB", linestyle=":", linewidth=0.8)
    ax.set_xlim(-0.35, len(model_names) - 0.65)
    ax.set_ylim(-1.0, 1.0)
    ax.set_xticks(x, model_names)
    ax.set_xlabel("Model")
    ax.set_ylabel("Envelope correlation coefficient")
    ax.set_title("S12 individual-component envelope correlation with Apollo observation")
    ax.legend(ncol=3, fontsize=8.2, loc="lower left")
    ax.text(
        0.99,
        0.02,
        "Common window: 50–245 s; envelopes are 20 s smoothed analytic amplitudes.",
        transform=ax.transAxes,
        ha="right",
        fontsize=8.0,
        color="#555555",
    )
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    output = FIGURE_DIR / "Figure_S12_M1_M6_observed_component_envelope_correlations.png"
    fig.savefig(output, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    summary_path = DERIVED_DIR / "s12_m1_m6_observed_component_envelope_correlations.csv"
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {output}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
