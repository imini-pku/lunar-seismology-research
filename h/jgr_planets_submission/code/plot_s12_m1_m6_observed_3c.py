"""Plot S12 Z/R/T waveforms for M1-M6 against the Apollo observation.

The model traces use the same 3-C RMS source scaling used by the project
comparison tables (50-245 s).  The panel window is 0-400 s so that M1-M4,
M5-M6, and the observed record share one time axis; the shaded interval after
245 s marks the part unavailable in the short M1-M4 records.
"""

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
PLOT_START_S = 0.0
PLOT_END_S = 400.0


def clipped_interp(time: np.ndarray, values: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Interpolate without extrapolating beyond the available record."""

    result = np.full(target.shape, np.nan, dtype=float)
    keep = (target >= float(time[0])) & (target <= float(time[-1]))
    result[keep] = np.interp(target[keep], time, values)
    return result


def s12_zrt_from_zen(zen: np.ndarray, azimuth_rad: float) -> np.ndarray:
    """Rotate filtered S12 Z/E/N into Z/R/T using the project convention."""

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

    target = np.arange(PLOT_START_S, PLOT_END_S + COMMON_DT_S / 2, COMMON_DT_S)
    observed_field = np.vstack(
        [clipped_interp(observed.time, observed.zrt[component], target) for component in range(3)]
    )
    model_fields: dict[str, np.ndarray] = {}
    scales: dict[str, float] = {}
    rows: list[dict[str, object]] = []
    azimuth = float(geometry.azimuth_rad[0])
    for name, record in records.items():
        scale = float(source_scale(observed, record))
        model_zrt = s12_zrt_from_zen(record.s12_zen, azimuth)
        model_fields[name] = np.vstack(
            [clipped_interp(record.s12_time, model_zrt[component], target) for component in range(3)]
        ) * scale
        scales[name] = scale
        rows.append(
            {
                "model": name,
                "label": MODEL_LABELS[name],
                "source_scale_50_245s_3c_rms": scale,
                "native_end_s": float(record.s12_time[-1]),
                "station": "S12 (first station, r1)",
                "components": "Z/R/T",
            }
        )

    all_fields = [observed_field, *[model_fields[name] for name in records]]
    y_limits: list[tuple[float, float]] = []
    for component in range(3):
        maximum = max(float(np.nanmax(np.abs(field[component]))) for field in all_fields)
        maximum = max(maximum, np.finfo(float).eps)
        y_limits.append((-1.06 * maximum, 1.06 * maximum))

    short_labels = {
        "M1": "Flat / no H",
        "M2": "Topo / no H",
        "M3": "Flat / H",
        "M4": "Topo / H",
        "M5": "Flat / H / low-V",
        "M6": "Topo / H / low-V",
    }
    components = ("Z", "R", "T")
    fig, axes = plt.subplots(
        3,
        6,
        figsize=(18.0, 8.8),
        sharex=True,
        sharey="row",
        constrained_layout=False,
    )
    fig.subplots_adjust(left=0.055, right=0.995, bottom=0.085, top=0.865, wspace=0.075, hspace=0.16)

    for row_index, component in enumerate(components):
        for column_index, name in enumerate(records):
            ax = axes[row_index, column_index]
            ax.axvspan(COMMON_END_S, PLOT_END_S, color="#777777", alpha=0.055, linewidth=0)
            ax.axvline(COMMON_END_S, color="#777777", linestyle="--", linewidth=0.65, alpha=0.75)
            ax.plot(
                target,
                observed_field[row_index],
                color="#222222",
                linewidth=0.85,
                alpha=0.78,
                zorder=1,
            )
            ax.plot(
                target,
                model_fields[name][row_index],
                color=MODEL_COLORS[name],
                linewidth=0.9,
                alpha=0.92,
                zorder=2,
            )
            ax.set_xlim(PLOT_START_S, PLOT_END_S)
            ax.set_ylim(*y_limits[row_index])
            ax.set_title(name + "\n" + short_labels[name], fontsize=8.0, pad=4.0)
            if column_index == 0:
                ax.set_ylabel(f"{component}  (source-scaled velocity)")
            if row_index == 2:
                ax.set_xlabel("Time after impact (s)")
            if row_index == 0 and column_index == 0:
                ax.text(
                    COMMON_END_S + 2.0,
                    y_limits[row_index][1] * 0.88,
                    "245 s",
                    fontsize=7.0,
                    color="#666666",
                    ha="left",
                    va="top",
                )

    handles = [
        Line2D([0], [0], color="#222222", linewidth=1.0, label="Apollo S12 observation"),
        Line2D([0], [0], color=MODEL_COLORS["M1"], linewidth=1.0, label="Colored trace = model"),
        Line2D([0], [0], color="#777777", linestyle="--", linewidth=0.8, label="245 s common-window boundary"),
    ]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.93), ncol=3, fontsize=8.5)
    fig.suptitle(
        "S12 station: M1-M6 three-component waveforms against Apollo observation",
        fontsize=13,
        y=0.975,
    )
    fig.text(
        0.5,
        0.018,
        "Models are scaled by their observed/model 3-C RMS ratio over 50-245 s; shading marks the extension beyond the M1-M4 record window.",
        ha="center",
        fontsize=8.0,
        color="#555555",
    )
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    output = FIGURE_DIR / "Figure_S12_M1_M6_observed_three_component.png"
    fig.savefig(output, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    scaling_path = DERIVED_DIR / "s12_m1_m6_observed_scaling.csv"
    with scaling_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {output}")
    print(f"Wrote {scaling_path}")
    for name, scale in scales.items():
        print(f"{name}: source_scale={scale:.8g}")


if __name__ == "__main__":
    main()
