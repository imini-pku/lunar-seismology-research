"""Reproducible three-component analysis of the half-space simulation archive.

The script reads ``config/data_catalog.json`` and writes derived CSV/JSON tables,
an input audit, and publication-ready figures.  It does not modify source data.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = SCRIPT_DIR.parent
WORKSPACE_DIR = PACKAGE_DIR.parent
LOCAL_PACKAGES = WORKSPACE_DIR / "work" / "python_pkgs"
if LOCAL_PACKAGES.is_dir():
    sys.path.insert(0, str(LOCAL_PACKAGES))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm
from netCDF4 import Dataset, chartostring
from scipy.interpolate import interp1d
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, detrend, fftconvolve, sosfiltfilt


CATALOG_FILE = PACKAGE_DIR / "config" / "data_catalog.json"
DERIVED_DIR = PACKAGE_DIR / "data" / "derived"
FIGURE_DIR = PACKAGE_DIR / "figures" / "halfspace"
PROVENANCE_DIR = PACKAGE_DIR / "provenance"

FILTER_LOW_HZ = 0.3
FILTER_HIGH_HZ = 0.9
FILTER_ORDER = 4
COMMON_DT_S = 0.02
COMMON_END_S = 99.88
EPSILON = 1.0e-30
COMPONENTS = ("Vx", "Vy", "Vz")
COMPONENT_LABELS = ("X", "Y", "Z")
RADIAL_COMPONENT_LABELS = ("R", "T", "Z")
COLORS = {
    "reference": "#0072B2",
    "comparison": "#D55E00",
    "layered": "#009E73",
    "accent": "#CC79A7",
    "neutral": "#4D4D4D",
}


@dataclass
class Record:
    label: str
    path: Path
    time: np.ndarray
    data: np.ndarray  # station x component x time
    names: list[str]


def configure_plotting() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "figure.dpi": 130,
            "savefig.dpi": 300,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.2,
            "grid.linewidth": 0.55,
        }
    )


def common_time() -> np.ndarray:
    return np.arange(0.0, COMMON_END_S + 0.5 * COMMON_DT_S, COMMON_DT_S)


def decode_station_names(variable: np.ndarray) -> list[str]:
    try:
        return [str(value).strip() for value in chartostring(variable)]
    except Exception:
        return [
            b"".join(row).decode("utf-8", "ignore").strip("\x00 ")
            for row in variable
        ]


def read_nc_inventory(path: Path) -> dict[str, object]:
    with Dataset(path, "r") as dataset:
        time = np.asarray(dataset.variables["time"][:], dtype=np.float64)
        names = decode_station_names(dataset.variables["station_name"][:])
        return {
            "receiver_count": len(names),
            "time_sample_count": int(time.size),
            "time_start_s": float(time[0]),
            "time_end_s": float(time[-1]),
            "median_dt_s": float(np.median(np.diff(time))),
            "first_station": names[0],
            "last_station": names[-1],
        }


def load_filtered_record(label: str, path: Path, target_time: np.ndarray) -> Record:
    with Dataset(path, "r") as dataset:
        native_time = np.asarray(dataset.variables["time"][:], dtype=np.float64)
        names = decode_station_names(dataset.variables["station_name"][:])
        if target_time[-1] > native_time[-1] + 1.0e-6:
            raise ValueError(f"Requested {target_time[-1]} s beyond {path} ({native_time[-1]} s)")
        dt = float(np.median(np.diff(native_time)))
        sample_rate = 1.0 / dt
        sos = butter(
            FILTER_ORDER,
            (FILTER_LOW_HZ, FILTER_HIGH_HZ),
            btype="bandpass",
            fs=sample_rate,
            output="sos",
        )
        component_arrays: list[np.ndarray] = []
        for component in COMPONENTS:
            raw = np.asarray(dataset.variables[component][:], dtype=np.float32)
            if raw.shape == (native_time.size, len(names)):
                raw = raw.T
            prepared = detrend(raw.astype(np.float64), axis=1, type="linear")
            filtered = sosfiltfilt(sos, prepared, axis=1)
            if np.array_equal(native_time, target_time):
                resampled = filtered
            else:
                resampled = interp1d(
                    native_time,
                    filtered,
                    axis=1,
                    kind="linear",
                    bounds_error=True,
                    assume_sorted=True,
                )(target_time)
            component_arrays.append(resampled.astype(np.float32))
    data = np.stack(component_arrays, axis=1)
    return Record(label=label, path=path, time=target_time, data=data, names=names)


def record_metrics(record: Record) -> dict[str, np.ndarray]:
    dt = float(np.median(np.diff(record.time)))
    squared = np.square(record.data.astype(np.float64))
    component_energy = squared.sum(axis=2) * dt
    total_energy = component_energy.sum(axis=1)
    intensity = squared.sum(axis=1)
    cumulative = np.cumsum(intensity, axis=1)
    cumulative /= np.maximum(cumulative[:, -1:], EPSILON)
    i05 = np.argmax(cumulative >= 0.05, axis=1)
    i95 = np.argmax(cumulative >= 0.95, axis=1)
    peak_index = np.argmax(intensity, axis=1)
    vector_peak = np.sqrt(intensity[np.arange(intensity.shape[0]), peak_index])
    return {
        "total_energy": total_energy,
        "component_energy": component_energy,
        "component_fraction": component_energy / np.maximum(total_energy[:, None], EPSILON),
        "t05_s": record.time[i05],
        "t95_s": record.time[i95],
        "t90_s": record.time[i95] - record.time[i05],
        "peak_time_s": record.time[peak_index],
        "vector_peak": vector_peak,
        "rms_3c": np.sqrt(np.mean(intensity, axis=1)),
    }


def lag_optimized_correlation(
    first: np.ndarray,
    second: np.ndarray,
    maximum_lag_s: float = 2.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return the maximum full-record 3C correlation within a small time lag.

    Full-record norms are used for a stable, bounded similarity measure; the
    omitted edge samples are less than 2% of the 100 s comparison window.
    """
    cross_component = fftconvolve(first, second[..., ::-1], mode="full", axes=-1)
    cross = np.sum(cross_component, axis=1)
    center = first.shape[-1] - 1
    maximum_lag_samples = int(round(maximum_lag_s / COMMON_DT_S))
    selected = cross[:, center - maximum_lag_samples : center + maximum_lag_samples + 1]
    denominator = np.sqrt(
        np.sum(first * first, axis=(1, 2)) * np.sum(second * second, axis=(1, 2))
    )
    selected /= np.maximum(denominator[:, None], EPSILON)
    best_index = np.argmax(selected, axis=1)
    best = selected[np.arange(selected.shape[0]), best_index]
    lag = (best_index - maximum_lag_samples) * COMMON_DT_S
    return best, lag


def paired_metrics(
    reference: Record,
    comparison: Record,
    include_lag_optimized: bool = False,
    component_labels: tuple[str, str, str] = COMPONENT_LABELS,
) -> pd.DataFrame:
    if reference.names != comparison.names:
        raise ValueError(f"Station-name mismatch between {reference.path} and {comparison.path}")
    if not np.array_equal(reference.time, comparison.time):
        raise ValueError("Records must share a common time vector")
    first = reference.data.astype(np.float64)
    second = comparison.data.astype(np.float64)
    dot = np.sum(first * second, axis=(1, 2))
    norm_first = np.sqrt(np.sum(first * first, axis=(1, 2)))
    norm_second = np.sqrt(np.sum(second * second, axis=(1, 2)))
    correlation = dot / np.maximum(norm_first * norm_second, EPSILON)
    shape_nrmse = np.sqrt(np.maximum(0.0, 2.0 - 2.0 * correlation))
    first_metrics = record_metrics(reference)
    second_metrics = record_metrics(comparison)
    rows = {
        "station": reference.names,
        "three_component_correlation": correlation,
        "shape_nrmse": shape_nrmse,
        "energy_ratio": second_metrics["total_energy"]
        / np.maximum(first_metrics["total_energy"], EPSILON),
        "peak_amplitude_ratio": second_metrics["vector_peak"]
        / np.maximum(first_metrics["vector_peak"], EPSILON),
        "t90_ratio": second_metrics["t90_s"]
        / np.maximum(first_metrics["t90_s"], COMMON_DT_S),
        "t90_difference_s": second_metrics["t90_s"] - first_metrics["t90_s"],
        "peak_time_shift_s": second_metrics["peak_time_s"] - first_metrics["peak_time_s"],
        "reference_t90_s": first_metrics["t90_s"],
        "comparison_t90_s": second_metrics["t90_s"],
    }
    for index, component in enumerate(component_labels):
        rows[f"reference_{component}_energy_fraction"] = first_metrics[
            "component_fraction"
        ][:, index]
        rows[f"comparison_{component}_energy_fraction"] = second_metrics[
            "component_fraction"
        ][:, index]
        rows[f"{component}_energy_fraction_change"] = (
            second_metrics["component_fraction"][:, index]
            - first_metrics["component_fraction"][:, index]
        )
    if include_lag_optimized:
        best, lag = lag_optimized_correlation(first, second)
        rows["maximum_correlation_within_2s"] = best
        rows["lag_at_maximum_correlation_s"] = lag
    return pd.DataFrame(rows)


def percentile_summary(frame: pd.DataFrame, comparison: str) -> dict[str, object]:
    summary: dict[str, object] = {"comparison": comparison, "station_count": len(frame)}
    for column in (
        "three_component_correlation",
        "shape_nrmse",
        "energy_ratio",
        "peak_amplitude_ratio",
        "t90_ratio",
        "t90_difference_s",
        "peak_time_shift_s",
    ):
        values = frame[column].to_numpy(dtype=float)
        for label, quantile in (("p10", 0.10), ("q25", 0.25), ("median", 0.50), ("q75", 0.75), ("p90", 0.90)):
            summary[f"{column}_{label}"] = float(np.nanquantile(values, quantile))
    if "maximum_correlation_within_2s" in frame:
        for column in ("maximum_correlation_within_2s", "lag_at_maximum_correlation_s"):
            values = frame[column].to_numpy(dtype=float)
            for label, quantile in (("p10", 0.10), ("median", 0.50), ("p90", 0.90)):
                summary[f"{column}_{label}"] = float(np.nanquantile(values, quantile))
    return summary


def write_dataframe(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig", float_format="%.9g")


def ecdf(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.sort(values[np.isfinite(values)])
    return x, np.arange(1, x.size + 1, dtype=float) / max(x.size, 1)


def nearest_indices(values: np.ndarray, quantiles: tuple[float, ...]) -> list[int]:
    return [int(np.nanargmin(np.abs(values - np.nanquantile(values, q)))) for q in quantiles]


def plot_pair_waveforms(
    reference: Record,
    comparison: Record,
    metrics: pd.DataFrame,
    output: Path,
    reference_label: str,
    comparison_label: str,
    title: str,
    component_labels: tuple[str, str, str] = COMPONENT_LABELS,
) -> None:
    station_indices = nearest_indices(
        metrics["three_component_correlation"].to_numpy(), (0.10, 0.50, 0.90)
    )
    fig, axes = plt.subplots(3, 3, figsize=(13.2, 8.2), sharex=True, constrained_layout=True)
    for column, station_index in enumerate(station_indices):
        scale = max(
            float(np.max(np.abs(reference.data[station_index]))),
            float(np.max(np.abs(comparison.data[station_index]))),
            EPSILON,
        )
        for component_index, component_label in enumerate(component_labels):
            axis = axes[component_index, column]
            axis.plot(
                reference.time,
                reference.data[station_index, component_index] / scale,
                color=COLORS["reference"],
                linewidth=0.75,
                label=reference_label,
            )
            axis.plot(
                comparison.time,
                comparison.data[station_index, component_index] / scale,
                color=COLORS["comparison"] if comparison_label != "Layered" else COLORS["layered"],
                linewidth=0.75,
                alpha=0.85,
                label=comparison_label,
            )
            axis.set_ylabel(f"{component_label} / shared scale")
            if component_index == 0:
                row = metrics.iloc[station_index]
                distance = (
                    f" | distance={row['distance_km']:.2f} km"
                    if "distance_km" in metrics.columns
                    else ""
                )
                axis.set_title(
                    f"{reference.names[station_index]}{distance} | "
                    f"corr={row['three_component_correlation']:.3f}, "
                    f"E ratio={row['energy_ratio']:.2f}"
                )
            if component_index == 2:
                axis.set_xlabel("Time (s)")
    axes[0, 0].legend(loc="upper right", frameon=False)
    fig.suptitle(title, fontsize=13)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def plot_pair_metrics(
    metrics: pd.DataFrame,
    output: Path,
    title: str,
    color: str,
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.4, 3.9), constrained_layout=True)
    scatter = axes[0].scatter(
        metrics["three_component_correlation"],
        np.log10(np.maximum(metrics["energy_ratio"], EPSILON)),
        c=np.clip(metrics["t90_difference_s"], -20.0, 20.0),
        cmap="coolwarm",
        s=13,
        alpha=0.68,
        linewidths=0,
    )
    axes[0].axhline(0.0, color="0.35", linewidth=0.75)
    axes[0].set_xlabel("Three-component zero-lag correlation")
    axes[0].set_ylabel("log10 energy ratio")
    cbar = fig.colorbar(scatter, ax=axes[0], shrink=0.84)
    cbar.set_label("T90 difference (s), clipped")

    for column, label, linestyle in (
        ("three_component_correlation", "3C correlation", "-"),
        ("shape_nrmse", "Shape NRMSE", "--"),
    ):
        x, y = ecdf(metrics[column].to_numpy(dtype=float))
        axes[1].plot(x, y, color=color, linewidth=1.5, linestyle=linestyle, label=label)
    axes[1].set_xlabel("Similarity / misfit value")
    axes[1].set_ylabel("Cumulative station fraction")
    axes[1].legend(frameon=False)

    for component, marker in zip(COMPONENT_LABELS, ("o", "s", "^"), strict=True):
        before = metrics[f"reference_{component}_energy_fraction"].to_numpy()
        after = metrics[f"comparison_{component}_energy_fraction"].to_numpy()
        axes[2].scatter(
            before,
            after,
            s=11,
            alpha=0.48,
            marker=marker,
            label=component,
        )
    axes[2].plot([0, 1], [0, 1], color="0.35", linewidth=0.8, linestyle="--")
    axes[2].set_xlim(0, 1)
    axes[2].set_ylim(0, 1)
    axes[2].set_xlabel("Reference component-energy fraction")
    axes[2].set_ylabel("Comparison component-energy fraction")
    axes[2].legend(frameon=False)
    fig.suptitle(title, fontsize=13)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def topography_switch_distance_bins(
    metrics: pd.DataFrame,
    station_range: tuple[int, int],
    bin_width_km: float = 1.0,
) -> pd.DataFrame:
    first, last = station_range
    selected = metrics[
        metrics["station_index"].between(first, last, inclusive="both")
    ].copy()
    minimum = float(selected["distance_km"].min())
    maximum = float(selected["distance_km"].max())
    edges = np.arange(minimum, maximum + bin_width_km + 1.0e-9, bin_width_km)
    selected["distance_bin"] = pd.cut(
        selected["distance_km"],
        bins=edges,
        include_lowest=True,
        right=True,
    )
    columns = (
        "three_component_correlation",
        "energy_ratio",
        "peak_amplitude_ratio",
        "t90_ratio",
        "t90_difference_s",
        "R_energy_fraction_change",
        "T_energy_fraction_change",
        "Z_energy_fraction_change",
    )
    rows: list[dict[str, float | int]] = []
    for interval, group in selected.groupby("distance_bin", observed=True):
        row: dict[str, float | int] = {
            "distance_bin_start_km": float(interval.left),
            "distance_bin_end_km": float(interval.right),
            "distance_bin_center_km": 0.5 * float(interval.left + interval.right),
            "station_count": int(len(group)),
            "station_index_first": int(group["station_index"].min()),
            "station_index_last": int(group["station_index"].max()),
        }
        for column in columns:
            values = group[column].to_numpy(dtype=float)
            row[f"{column}_p10"] = float(np.nanquantile(values, 0.10))
            row[f"{column}_median"] = float(np.nanmedian(values))
            row[f"{column}_p90"] = float(np.nanquantile(values, 0.90))
        rows.append(row)
    return pd.DataFrame(rows)


def plot_topography_switch_distance(
    metrics: pd.DataFrame,
    bins: pd.DataFrame,
    output: Path,
    station_range: tuple[int, int],
) -> None:
    selected = metrics[
        metrics["station_index"].between(*station_range, inclusive="both")
    ].copy()
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.5), constrained_layout=True)

    x_offset = (metrics["x_m"] - metrics["source_x_m"]) / 1_000.0
    y_offset = (metrics["y_m"] - metrics["source_y_m"]) / 1_000.0
    axes[0, 0].plot(x_offset, y_offset, color=COLORS["reference"], linewidth=1.2)
    axes[0, 0].scatter(
        x_offset.iloc[::20],
        y_offset.iloc[::20],
        c=metrics["distance_km"].iloc[::20],
        cmap="viridis",
        s=11,
        linewidths=0,
    )
    axes[0, 0].scatter([0.0], [0.0], marker="*", s=90, color=COLORS["comparison"], label="Source")
    axes[0, 0].annotate("r1", (x_offset.iloc[0], y_offset.iloc[0]), xytext=(5, 2), textcoords="offset points")
    axes[0, 0].annotate("r800", (x_offset.iloc[-1], y_offset.iloc[-1]), xytext=(5, -3), textcoords="offset points")
    axes[0, 0].set_aspect("equal", adjustable="box")
    axes[0, 0].set_xlabel("X offset from source (km)")
    axes[0, 0].set_ylabel("Y offset from source (km)")
    axes[0, 0].set_title("r1-r800: 75° line, 50 m spacing")
    axes[0, 0].legend(frameon=False, loc="upper left")

    def add_metric_panel(
        axis,
        column: str,
        ylabel: str,
        logarithmic: bool = False,
        reference_value: float | None = None,
    ) -> None:
        axis.scatter(
            selected["distance_km"],
            selected[column],
            s=7,
            alpha=0.25,
            color=COLORS["reference"],
            linewidths=0,
        )
        center = bins["distance_bin_center_km"].to_numpy(dtype=float)
        median = bins[f"{column}_median"].to_numpy(dtype=float)
        p10 = bins[f"{column}_p10"].to_numpy(dtype=float)
        p90 = bins[f"{column}_p90"].to_numpy(dtype=float)
        axis.fill_between(center, p10, p90, color=COLORS["reference"], alpha=0.15)
        axis.plot(center, median, color=COLORS["reference"], linewidth=1.5, label="1 km-bin median")
        if reference_value is not None:
            axis.axhline(reference_value, color="0.35", linewidth=0.75, linestyle="--")
        if logarithmic:
            axis.set_yscale("log")
        axis.set_xlim(1.0, 38.0)
        axis.set_xlabel("Epicentral distance (km); r20-r760")
        axis.set_ylabel(ylabel)
        axis.legend(frameon=False)

    add_metric_panel(
        axes[0, 1],
        "three_component_correlation",
        "3C zero-lag correlation",
        reference_value=0.0,
    )
    axes[0, 1].set_ylim(-1.0, 1.0)
    add_metric_panel(
        axes[0, 2],
        "energy_ratio",
        "With/without-topography energy ratio",
        logarithmic=True,
        reference_value=1.0,
    )
    add_metric_panel(
        axes[1, 0],
        "peak_amplitude_ratio",
        "With/without-topography peak ratio",
        logarithmic=True,
        reference_value=1.0,
    )
    add_metric_panel(
        axes[1, 1],
        "t90_ratio",
        "With/without-topography T90 ratio",
        logarithmic=True,
        reference_value=1.0,
    )

    center = bins["distance_bin_center_km"].to_numpy(dtype=float)
    for component, color, linestyle in (
        ("R", COLORS["reference"], "-"),
        ("T", COLORS["comparison"], "--"),
        ("Z", COLORS["layered"], ":"),
    ):
        median = bins[f"{component}_energy_fraction_change_median"].to_numpy(dtype=float)
        p10 = bins[f"{component}_energy_fraction_change_p10"].to_numpy(dtype=float)
        p90 = bins[f"{component}_energy_fraction_change_p90"].to_numpy(dtype=float)
        axes[1, 2].fill_between(center, p10, p90, color=color, alpha=0.09)
        axes[1, 2].plot(
            center,
            median,
            color=color,
            linestyle=linestyle,
            linewidth=1.5,
            label=component,
        )
    axes[1, 2].axhline(0.0, color="0.35", linewidth=0.75, linestyle="--")
    axes[1, 2].set_xlim(1.0, 38.0)
    axes[1, 2].set_xlabel("Epicentral distance (km); r20-r760")
    axes[1, 2].set_ylabel("Component-energy fraction change")
    axes[1, 2].legend(frameon=False, ncol=3)
    fig.suptitle("Topography effects along the true r1-r800 receiver line", fontsize=13)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def parse_station_file(path: Path) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    lines = path.read_text(encoding="utf-8").splitlines()[3:]
    for line in lines:
        fields = line.split()
        if len(fields) < 6:
            continue
        rows.append(
            {
                "station": fields[0],
                "x_m": float(fields[3]),
                "y_m": float(fields[4]),
                "z_m": float(fields[5]),
            }
        )
    frame = pd.DataFrame(rows)
    source_x = 50_000.0
    source_y = 50_000.0
    frame["distance_km"] = np.hypot(frame["x_m"] - source_x, frame["y_m"] - source_y) / 1_000.0
    frame["azimuth_deg"] = (
        np.degrees(np.arctan2(frame["y_m"] - source_y, frame["x_m"] - source_x)) % 360.0
    )
    return frame


def build_800_receiver_geometry(switch: dict[str, object]) -> pd.DataFrame:
    """Reconstruct and validate the line geometry used by the r1-r800 archive."""
    specification = switch["receiver_geometry"]
    count = int(specification["station_count"])
    first = int(specification["station_index_first"])
    last = int(specification["station_index_last"])
    spacing_m = float(specification["station_spacing_m"])
    source_x_m = float(specification["source_x_m"])
    source_y_m = float(specification["source_y_m"])
    azimuth_deg = float(specification["azimuth_deg_from_positive_x"])
    if count != last - first + 1:
        raise ValueError("The configured r1-r800 station count is inconsistent")

    matlab_path = Path(switch["receiver_geometry_matlab_reference"])
    matlab_text = matlab_path.read_text(encoding="utf-8", errors="ignore")
    azimuth_match = re.search(r"azimuth_deg\s*=\s*([0-9.]+)", matlab_text)
    spacing_match = re.search(
        r"epi_dist\s*=\s*stations\s*\*\s*([0-9.]+)\s*/\s*1000",
        matlab_text,
    )
    range_match = re.search(r"stations\s*=\s*([0-9]+)\s*:\s*1\s*:\s*([0-9]+)", matlab_text)
    if azimuth_match is None or spacing_match is None or range_match is None:
        raise ValueError(f"Could not recover the station logic from {matlab_path}")
    if not math.isclose(float(azimuth_match.group(1)), azimuth_deg, abs_tol=1.0e-9):
        raise ValueError("MATLAB and catalog azimuths differ")
    if not math.isclose(float(spacing_match.group(1)), spacing_m, abs_tol=1.0e-9):
        raise ValueError("MATLAB and catalog station spacings differ")
    preferred = tuple(int(value) for value in specification["preferred_distance_analysis_station_range"])
    if preferred != (int(range_match.group(1)), int(range_match.group(2))):
        raise ValueError("MATLAB station subset differs from the cataloged analysis subset")

    run_script_path = Path(switch["receiver_geometry_run_script"])
    station_pattern = re.compile(
        r"^r([0-9]+)\s+1\s+1\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$"
    )
    exact_rows: list[dict[str, float | int | str]] = []
    for line in run_script_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = station_pattern.match(line.strip())
        if match is None:
            continue
        station_index = int(match.group(1))
        if first <= station_index <= last:
            exact_rows.append(
                {
                    "station": f"r{station_index}",
                    "station_index": station_index,
                    "x_m": float(match.group(2)),
                    "y_m": float(match.group(3)),
                    "z_m": float(match.group(4)),
                }
            )
    geometry = pd.DataFrame(exact_rows).sort_values("station_index").reset_index(drop=True)
    if len(geometry) != count or geometry["station_index"].tolist() != list(range(first, last + 1)):
        raise ValueError(f"The run script does not contain one exact coordinate for each r1-r800 receiver")

    angle = math.radians(azimuth_deg)
    index = geometry["station_index"].to_numpy(dtype=float)
    expected_x = source_x_m + index * spacing_m * math.cos(angle)
    expected_y = source_y_m + index * spacing_m * math.sin(angle)
    geometry["formula_position_error_mm"] = 1_000.0 * np.hypot(
        geometry["x_m"].to_numpy(dtype=float) - expected_x,
        geometry["y_m"].to_numpy(dtype=float) - expected_y,
    )
    if float(geometry["formula_position_error_mm"].max()) > 0.002:
        raise ValueError("The exact run-script coordinates do not match the 75-degree/50-m formula")
    geometry["distance_km"] = np.hypot(
        geometry["x_m"] - source_x_m,
        geometry["y_m"] - source_y_m,
    ) / 1_000.0
    geometry["azimuth_deg"] = (
        np.degrees(
            np.arctan2(
                geometry["y_m"] - source_y_m,
                geometry["x_m"] - source_x_m,
            )
        )
        % 360.0
    )
    geometry["source_x_m"] = source_x_m
    geometry["source_y_m"] = source_y_m
    geometry["geometry_source"] = str(run_script_path)
    return geometry


def rotate_record_to_radial_transverse(record: Record, geometry: pd.DataFrame) -> Record:
    if record.names != geometry["station"].tolist():
        raise ValueError(f"Receiver names in {record.path} do not match the reconstructed geometry")
    angle = np.radians(geometry["azimuth_deg"].to_numpy(dtype=float))[:, None]
    vx = record.data[:, 0, :].astype(np.float64)
    vy = record.data[:, 1, :].astype(np.float64)
    rotated = np.empty_like(record.data, dtype=np.float32)
    rotated[:, 0, :] = (vx * np.cos(angle) + vy * np.sin(angle)).astype(np.float32)
    rotated[:, 1, :] = (-vx * np.sin(angle) + vy * np.cos(angle)).astype(np.float32)
    rotated[:, 2, :] = record.data[:, 2, :]
    return Record(
        label=record.label,
        path=record.path,
        time=record.time,
        data=rotated,
        names=record.names,
    )


def resolution_analysis(catalog: dict[str, object], target_time: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    entries = sorted(catalog["half_space"]["topographic_resolution"], key=lambda item: item["resolution_m"])
    reference_entry = next(item for item in entries if item["resolution_m"] == 125)
    reference = load_filtered_record("125 m", Path(reference_entry["station_nc"]), target_time)
    geometry = parse_station_file(Path(reference_entry["station_file"]))
    if list(geometry["station"]) != reference.names:
        raise ValueError("Resolution-series station names do not match the station file")

    station_frames: list[pd.DataFrame] = []
    summary_rows: list[dict[str, object]] = []
    for entry in entries:
        resolution = int(entry["resolution_m"])
        if resolution == 125:
            comparison = reference
        else:
            comparison = load_filtered_record(f"{resolution} m", Path(entry["station_nc"]), target_time)
        metrics = paired_metrics(reference, comparison, include_lag_optimized=True)
        metrics.insert(0, "resolution_m", resolution)
        metrics = metrics.merge(geometry, on="station", how="left", validate="one_to_one")
        metrics["absolute_energy_relative_error"] = np.abs(metrics["energy_ratio"] - 1.0)
        station_frames.append(metrics)
        row = percentile_summary(metrics, f"{resolution}m_vs_125m")
        row["resolution_m"] = resolution
        row["median_absolute_energy_relative_error"] = float(
            np.nanmedian(metrics["absolute_energy_relative_error"])
        )
        row["p90_absolute_energy_relative_error"] = float(
            np.nanquantile(metrics["absolute_energy_relative_error"], 0.90)
        )
        row["fraction_correlation_ge_0_90"] = float(
            np.mean(metrics["three_component_correlation"] >= 0.90)
        )
        row["fraction_maximum_correlation_ge_0_90"] = float(
            np.mean(metrics["maximum_correlation_within_2s"] >= 0.90)
        )
        row["fraction_energy_error_le_0_10"] = float(
            np.mean(metrics["absolute_energy_relative_error"] <= 0.10)
        )
        summary_rows.append(row)
    station_metrics = pd.concat(station_frames, ignore_index=True)
    summary = pd.DataFrame(summary_rows).sort_values("resolution_m")
    return station_metrics, summary


def plot_resolution_convergence(summary: pd.DataFrame, output: Path) -> None:
    x = summary["resolution_m"].to_numpy(dtype=float)
    fig, axes = plt.subplots(1, 3, figsize=(13.4, 4.1), constrained_layout=True)
    median = summary["three_component_correlation_median"].to_numpy(dtype=float)
    p10 = summary["three_component_correlation_p10"].to_numpy(dtype=float)
    p90 = summary["three_component_correlation_p90"].to_numpy(dtype=float)
    axes[0].plot(x, median, color=COLORS["reference"], marker="o", label="Median")
    axes[0].fill_between(x, p10, p90, color=COLORS["reference"], alpha=0.18, label="10-90%")
    axes[0].axhline(0.95, color="0.35", linewidth=0.8, linestyle="--", label="0.95 guide")
    axes[0].plot(
        x,
        summary["maximum_correlation_within_2s_median"],
        color=COLORS["accent"],
        marker="s",
        linestyle=":",
        label="Median after ±2 s lag search",
    )
    axes[0].set_ylabel("3C correlation with 125 m model")
    axes[0].legend(frameon=False)

    axes[1].plot(
        x,
        np.maximum(summary["median_absolute_energy_relative_error"], 1.0e-3),
        color=COLORS["comparison"],
        marker="o",
        label="Median absolute error",
    )
    axes[1].plot(
        x,
        np.maximum(summary["p90_absolute_energy_relative_error"], 1.0e-3),
        color=COLORS["comparison"],
        marker="s",
        linestyle="--",
        label="90th percentile",
    )
    axes[1].axhline(0.10, color="0.35", linewidth=0.8, linestyle=":", label="10% guide")
    axes[1].set_yscale("log")
    axes[1].set_ylabel("Absolute relative energy error")
    axes[1].legend(frameon=False)

    axes[2].plot(
        x,
        summary["t90_ratio_median"],
        color=COLORS["layered"],
        marker="o",
        label="Median",
    )
    axes[2].fill_between(
        x,
        summary["t90_ratio_p10"],
        summary["t90_ratio_p90"],
        color=COLORS["layered"],
        alpha=0.18,
        label="10-90%",
    )
    axes[2].axhline(1.0, color="0.35", linewidth=0.8, linestyle="--")
    axes[2].set_ylabel("T90 ratio to 125 m model")
    axes[2].legend(frameon=False)
    for axis in axes:
        axis.set_xscale("log")
        axis.invert_xaxis()
        axis.set_xlabel("Nominal topography resolution (m; finer to right)")
        axis.set_xticks([10000, 4000, 1000, 500, 250, 125])
        axis.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    fig.suptitle("Half-space waveform convergence relative to the 125 m topography model", fontsize=13)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def plot_resolution_station_map(station_metrics: pd.DataFrame, output: Path) -> None:
    resolutions = sorted(station_metrics["resolution_m"].unique(), reverse=True)
    pivot = station_metrics.pivot(index="resolution_m", columns="station", values="three_component_correlation")
    pivot = pivot.reindex(resolutions)
    fig, axes = plt.subplots(1, 2, figsize=(13.3, 4.9), constrained_layout=True)
    image = axes[0].imshow(
        pivot.to_numpy(),
        aspect="auto",
        interpolation="nearest",
        vmin=-0.2,
        vmax=1.0,
        cmap="viridis",
    )
    axes[0].set_yticks(range(len(resolutions)), [f"{value} m" for value in resolutions])
    axes[0].set_xlabel("Station index (r1-r216)")
    axes[0].set_ylabel("Topography resolution")
    axes[0].set_title("3C waveform correlation with 125 m reference")
    fig.colorbar(image, ax=axes[0], shrink=0.88, label="Correlation")

    coarse = station_metrics[station_metrics["resolution_m"] == max(resolutions)].copy()
    angle = np.radians(coarse["azimuth_deg"].to_numpy())
    radius = coarse["distance_km"].to_numpy()
    polar = fig.add_subplot(1, 2, 2, projection="polar")
    axes[1].remove()
    marks = polar.scatter(
        angle,
        radius,
        c=coarse["three_component_correlation"],
        cmap="viridis",
        vmin=-0.2,
        vmax=1.0,
        s=24,
        linewidths=0,
    )
    polar.set_title(f"Spatial pattern at {max(resolutions)} m")
    polar.set_theta_zero_location("E")
    polar.set_theta_direction(1)
    polar.grid(alpha=0.25)
    fig.colorbar(marks, ax=polar, shrink=0.88, label="Correlation")
    fig.suptitle("Resolution sensitivity is station- and azimuth-dependent", fontsize=13)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def load_topography_metrics(catalog: dict[str, object]) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    entries = sorted(catalog["half_space"]["topographic_resolution"], key=lambda item: item["resolution_m"])
    reference_entry = next(item for item in entries if item["resolution_m"] == 125)
    reference = np.loadtxt(reference_entry["topography_txt"], dtype=np.float32)
    profiles: dict[str, np.ndarray] = {"125": reference[reference.shape[0] // 2].astype(float)}
    maps: dict[str, np.ndarray] = {"reference": reference[::20, ::20].astype(float)}
    rows: list[dict[str, object]] = []
    for entry in entries:
        resolution = int(entry["resolution_m"])
        array = reference if resolution == 125 else np.loadtxt(entry["topography_txt"], dtype=np.float32)
        if array.shape != reference.shape:
            raise ValueError(f"Topography shape mismatch for {entry['topography_txt']}: {array.shape}")
        difference = array.astype(np.float64) - reference.astype(np.float64)
        centered_a = array.astype(np.float64) - float(np.mean(array))
        centered_b = reference.astype(np.float64) - float(np.mean(reference))
        correlation = float(
            np.sum(centered_a * centered_b)
            / max(np.linalg.norm(centered_a) * np.linalg.norm(centered_b), EPSILON)
        )
        slope_x = np.diff(array.astype(np.float64), axis=1) / 0.1
        slope_y = np.diff(array.astype(np.float64), axis=0) / 0.1
        rows.append(
            {
                "resolution_m": resolution,
                "rows": array.shape[0],
                "columns": array.shape[1],
                "minimum_elevation_km": float(np.min(array)),
                "maximum_elevation_km": float(np.max(array)),
                "relief_km": float(np.ptp(array)),
                "elevation_standard_deviation_km": float(np.std(array)),
                "rms_difference_from_125m_km": float(np.sqrt(np.mean(difference * difference))),
                "mae_difference_from_125m_km": float(np.mean(np.abs(difference))),
                "maximum_absolute_difference_from_125m_km": float(np.max(np.abs(difference))),
                "elevation_correlation_with_125m": correlation,
                "rms_x_slope_km_per_km": float(np.sqrt(np.mean(slope_x * slope_x))),
                "rms_y_slope_km_per_km": float(np.sqrt(np.mean(slope_y * slope_y))),
            }
        )
        if resolution in (10000, 4000, 1000, 125):
            profiles[str(resolution)] = array[array.shape[0] // 2].astype(float)
        if resolution == 10000:
            maps["difference_10000_minus_125"] = difference[::20, ::20]
        if resolution != 125:
            del array
    return pd.DataFrame(rows).sort_values("resolution_m"), {**profiles, **maps}


def plot_topography_resolution(metrics: pd.DataFrame, arrays: dict[str, np.ndarray], output: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 8.2), constrained_layout=True)
    image = axes[0, 0].imshow(arrays["reference"], origin="lower", cmap="terrain")
    axes[0, 0].set_title("125 m topography (20x display decimation)")
    axes[0, 0].set_xlabel("Grid x / 20")
    axes[0, 0].set_ylabel("Grid y / 20")
    fig.colorbar(image, ax=axes[0, 0], shrink=0.83, label="Elevation (km)")

    diff = arrays["difference_10000_minus_125"]
    limit = float(np.nanquantile(np.abs(diff), 0.99))
    image2 = axes[0, 1].imshow(
        diff,
        origin="lower",
        cmap="coolwarm",
        norm=TwoSlopeNorm(vmin=-limit, vcenter=0.0, vmax=limit),
    )
    axes[0, 1].set_title("10 km minus 125 m elevation")
    axes[0, 1].set_xlabel("Grid x / 20")
    axes[0, 1].set_ylabel("Grid y / 20")
    fig.colorbar(image2, ax=axes[0, 1], shrink=0.83, label="Difference (km)")

    sample_index = np.arange(arrays["125"].size)[::10]
    for resolution, color in zip((10000, 4000, 1000, 125), ("#D55E00", "#CC79A7", "#009E73", "#0072B2"), strict=True):
        axes[1, 0].plot(
            sample_index * 0.1,
            arrays[str(resolution)][::10],
            color=color,
            linewidth=0.85,
            label=f"{resolution} m",
        )
    axes[1, 0].set_xlabel("Center-row distance (km)")
    axes[1, 0].set_ylabel("Elevation (km)")
    axes[1, 0].set_title("Center-row profiles")
    axes[1, 0].legend(frameon=False, ncol=2)

    x = metrics["resolution_m"].to_numpy(dtype=float)
    axes[1, 1].plot(
        x,
        metrics["rms_difference_from_125m_km"] * 1_000.0,
        marker="o",
        color=COLORS["comparison"],
        label="RMS elevation difference",
    )
    axes[1, 1].set_xscale("log")
    axes[1, 1].invert_xaxis()
    axes[1, 1].set_xlabel("Nominal resolution (m; finer to right)")
    axes[1, 1].set_ylabel("RMS difference from 125 m (m)")
    second = axes[1, 1].twinx()
    second.plot(
        x,
        metrics["elevation_correlation_with_125m"],
        marker="s",
        color=COLORS["reference"],
        linestyle="--",
        label="Elevation correlation",
    )
    second.set_ylabel("Elevation correlation")
    axes[1, 1].set_title("Terrain convergence")
    lines, labels = axes[1, 1].get_legend_handles_labels()
    lines2, labels2 = second.get_legend_handles_labels()
    axes[1, 1].legend(lines + lines2, labels + labels2, frameon=False, loc="best")
    fig.suptitle("Topography files used by the half-space resolution series", fontsize=13)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def smoothed_peak_times(record: Record, window_s: float) -> np.ndarray:
    intensity = np.sum(np.square(record.data.astype(np.float64)), axis=1)
    samples = max(1, int(round(window_s / COMMON_DT_S)))
    smooth = uniform_filter1d(intensity, size=samples, axis=1, mode="nearest")
    return record.time[np.argmax(smooth, axis=1)]


def fit_form(distance: np.ndarray, peak_time: np.ndarray, squared: bool) -> dict[str, float]:
    predictor = distance * distance if squared else distance
    design = np.column_stack([np.ones_like(predictor), predictor])
    coefficients, *_ = np.linalg.lstsq(design, peak_time, rcond=None)
    fitted = design @ coefficients
    residual = peak_time - fitted
    rss = float(np.sum(residual * residual))
    tss = float(np.sum((peak_time - np.mean(peak_time)) ** 2))
    n = peak_time.size
    return {
        "intercept_s": float(coefficients[0]),
        "slope": float(coefficients[1]),
        "rmse_s": float(np.sqrt(rss / n)),
        "r_squared": 1.0 - rss / max(tss, EPSILON),
        "aic": float(n * np.log(max(rss / n, EPSILON)) + 2 * 2),
    }


def time_distance_analysis(
    uniform: Record, layered: Record, geometry: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    station_rows: list[dict[str, object]] = []
    for record, model_label in ((uniform, "Uniform half-space"), (layered, "Layered")):
        for window in (2.0, 5.0, 10.0):
            peak = smoothed_peak_times(record, window)
            for station, distance, azimuth, value in zip(
                record.names,
                geometry["distance_km"],
                geometry["azimuth_deg"],
                peak,
                strict=True,
            ):
                station_rows.append(
                    {
                        "model": model_label,
                        "smoothing_window_s": window,
                        "station": station,
                        "distance_km": distance,
                        "azimuth_deg": azimuth,
                        "peak_energy_time_s": value,
                    }
                )
            for squared, form in ((False, "linear_R"), (True, "diffusion_R2")):
                fit = fit_form(geometry["distance_km"].to_numpy(), peak, squared)
                rows.append(
                    {
                        "model": model_label,
                        "smoothing_window_s": window,
                        "form": form,
                        **fit,
                    }
                )
    return pd.DataFrame(station_rows), pd.DataFrame(rows)


def plot_time_distance(stations: pd.DataFrame, fits: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.6), constrained_layout=True)
    for axis, model, color in zip(
        axes,
        ("Uniform half-space", "Layered"),
        (COLORS["reference"], COLORS["layered"]),
        strict=True,
    ):
        subset = stations[(stations["model"] == model) & (stations["smoothing_window_s"] == 5.0)]
        grouped = subset.groupby("distance_km")["peak_energy_time_s"]
        distance = np.asarray(sorted(grouped.groups), dtype=float)
        median = grouped.median().reindex(distance).to_numpy()
        low = grouped.quantile(0.10).reindex(distance).to_numpy()
        high = grouped.quantile(0.90).reindex(distance).to_numpy()
        axis.fill_between(distance, low, high, color=color, alpha=0.16, label="Azimuthal 10-90%")
        axis.plot(distance, median, color=color, marker="o", label="Azimuthal median")
        grid = np.linspace(float(distance.min()), float(distance.max()), 200)
        fit_subset = fits[(fits["model"] == model) & (fits["smoothing_window_s"] == 5.0)]
        for form, linestyle, label in (("linear_R", "--", "Linear in R"), ("diffusion_R2", ":", "Linear in R^2")):
            row = fit_subset[fit_subset["form"] == form].iloc[0]
            predictor = grid if form == "linear_R" else grid * grid
            axis.plot(
                grid,
                row["intercept_s"] + row["slope"] * predictor,
                color="0.25",
                linestyle=linestyle,
                linewidth=1.1,
                label=f"{label}; RMSE={row['rmse_s']:.2f} s",
            )
        axis.set_title(model)
        axis.set_xlabel("Epicentral distance (km)")
        axis.set_ylabel("5 s-smoothed 3C peak-energy time (s)")
        axis.legend(frameon=False)
    fig.suptitle("Half-space peak-energy time: ballistic and diffusion-form diagnostics", fontsize=13)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def a16_cross_region_summary(halfspace_metrics: pd.DataFrame) -> pd.DataFrame:
    source = pd.read_csv(DERIVED_DIR / "station_level_metrics.csv")
    primary = source[source["included_in_primary_analysis"] == 1]
    rows = []
    for metric, halfspace_column, a16_column in (
        ("Peak amplitude ratio", "peak_amplitude_ratio", "topography_no_scatter__log_peak_amplitude"),
        ("Total energy ratio", "energy_ratio", "topography_no_scatter__log_total_energy"),
        ("T90 ratio", "t90_ratio", "topography_no_scatter__log_duration_90_s"),
    ):
        hs = halfspace_metrics[halfspace_column].to_numpy(dtype=float)
        a16 = np.exp(primary[a16_column].to_numpy(dtype=float))
        for region, values in (("Half-space archive", hs), ("A16 factorial M3/M1", a16)):
            rows.append(
                {
                    "metric": metric,
                    "region": region,
                    "p10": float(np.nanquantile(values, 0.10)),
                    "median": float(np.nanmedian(values)),
                    "p90": float(np.nanquantile(values, 0.90)),
                    "n": int(np.isfinite(values).sum()),
                }
            )
    return pd.DataFrame(rows)


def plot_cross_region(summary: pd.DataFrame, output: Path) -> None:
    metrics = list(summary["metric"].drop_duplicates())
    fig, axes = plt.subplots(1, len(metrics), figsize=(12.4, 3.9), constrained_layout=True)
    for axis, metric in zip(axes, metrics, strict=True):
        subset = summary[summary["metric"] == metric]
        for index, (_, row) in enumerate(subset.iterrows()):
            color = COLORS["reference"] if row["region"] == "Half-space archive" else COLORS["accent"]
            marker = "o" if row["region"] == "Half-space archive" else "s"
            axis.errorbar(
                row["median"],
                index,
                xerr=[[row["median"] - row["p10"]], [row["p90"] - row["median"]]],
                fmt=marker,
                color=color,
                capsize=3,
                linewidth=1.3,
                label=row["region"],
            )
        axis.axvline(1.0, color="0.35", linestyle="--", linewidth=0.8)
        axis.set_yticks([0, 1], subset["region"].tolist())
        axis.set_xlabel("Ratio (median with 10-90% station range)")
        axis.set_title(metric)
        if metric == "T90 ratio":
            axis.set_xscale("log")
    fig.suptitle("Topography-only effect sizes: half-space archive versus A16 factorial model", fontsize=13)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def collect_input_paths(catalog: dict[str, object]) -> list[tuple[str, Path]]:
    items: list[tuple[str, Path]] = []
    switch = catalog["half_space"]["topography_switch"]
    for key in (
        "with_topography_station_nc",
        "without_topography_station_nc",
        "with_topography_project_station_file",
        "without_topography_project_station_file",
        "receiver_geometry_matlab_reference",
        "receiver_geometry_run_script",
        "topography_txt",
    ):
        items.append((f"half_space.topography_switch.{key}", Path(switch[key])))
    for entry in catalog["half_space"]["topographic_resolution"]:
        resolution = entry["resolution_m"]
        for key in ("station_nc", "station_file", "topography_txt"):
            items.append((f"half_space.resolution.{resolution}m.{key}", Path(entry[key])))
    layering = catalog["half_space"]["layering_switch"]
    for key in ("uniform_half_space_station_nc", "layered_station_nc", "shared_station_file", "topography_txt"):
        items.append((f"half_space.layering_switch.{key}", Path(layering[key])))
    for key, value in catalog["a16_s12"]["external_simulations"].items():
        items.append((f"a16_s12.external_simulations.{key}", Path(value)))
    for key, value in catalog["a16_s12"]["observation_external"].items():
        items.append((f"a16_s12.observation_external.{key}", Path(value)))
    items.append(("a16_s12.topography_external", Path(catalog["a16_s12"]["topography_external"])))
    unique: dict[str, tuple[str, Path]] = {}
    for role, path in items:
        unique.setdefault(str(path).lower(), (role, path))
    return list(unique.values())


def build_input_audit(catalog: dict[str, object]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for role, path in collect_input_paths(catalog):
        exists = path.is_file()
        row: dict[str, object] = {"role": role, "path": str(path), "exists": exists}
        if exists:
            stat = path.stat()
            row.update(
                {
                    "size_bytes": stat.st_size,
                    "modified_local": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                    "sha256": sha256(path),
                }
            )
            if path.suffix.lower() == ".nc" and path.name == "station.nc":
                row.update(read_nc_inventory(path))
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    configure_plotting()
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    target_time = common_time()

    print("Auditing input paths and checksums...")
    audit = build_input_audit(catalog)
    write_dataframe(audit, PROVENANCE_DIR / "halfspace_input_audit.csv")
    if not bool(audit["exists"].all()):
        missing = audit.loc[~audit["exists"], "path"].tolist()
        raise FileNotFoundError(f"Missing catalog inputs: {missing}")

    print("Analyzing the 800-station topography switch...")
    switch = catalog["half_space"]["topography_switch"]
    no_topography = load_filtered_record(
        "Without topography", Path(switch["without_topography_station_nc"]), target_time
    )
    with_topography = load_filtered_record(
        "With topography", Path(switch["with_topography_station_nc"]), target_time
    )
    topography_switch_geometry = build_800_receiver_geometry(switch)
    if (
        no_topography.names != topography_switch_geometry["station"].tolist()
        or with_topography.names != no_topography.names
    ):
        raise ValueError("The 800-receiver NetCDF station names do not match the recovered geometry")
    write_dataframe(
        topography_switch_geometry,
        DERIVED_DIR / "halfspace_800_receiver_geometry.csv",
    )
    no_topography_rt = rotate_record_to_radial_transverse(
        no_topography, topography_switch_geometry
    )
    with_topography_rt = rotate_record_to_radial_transverse(
        with_topography, topography_switch_geometry
    )
    topography_switch_metrics = paired_metrics(
        no_topography_rt,
        with_topography_rt,
        component_labels=RADIAL_COMPONENT_LABELS,
    ).merge(
        topography_switch_geometry,
        on="station",
        how="left",
        validate="one_to_one",
    )
    write_dataframe(
        topography_switch_metrics,
        DERIVED_DIR / "halfspace_topography_switch_station_metrics.csv",
    )
    preferred_range = tuple(
        int(value)
        for value in switch["receiver_geometry"]["preferred_distance_analysis_station_range"]
    )
    topography_switch_bins = topography_switch_distance_bins(
        topography_switch_metrics,
        preferred_range,
    )
    write_dataframe(
        topography_switch_bins,
        DERIVED_DIR / "halfspace_topography_switch_distance_bins.csv",
    )
    plot_pair_waveforms(
        no_topography_rt,
        with_topography_rt,
        topography_switch_metrics,
        FIGURE_DIR / "Figure_HS1_topography_switch_waveforms.png",
        "Without topography",
        "With topography",
        "Half-space three-component waveforms: topography switch",
        component_labels=RADIAL_COMPONENT_LABELS,
    )
    plot_topography_switch_distance(
        topography_switch_metrics,
        topography_switch_bins,
        FIGURE_DIR / "Figure_HS2_topography_switch_metrics.png",
        preferred_range,
    )

    print("Analyzing the 216-station topographic-resolution series...")
    resolution_station, resolution_summary = resolution_analysis(catalog, target_time)
    write_dataframe(resolution_station, DERIVED_DIR / "halfspace_resolution_station_metrics.csv")
    write_dataframe(resolution_summary, DERIVED_DIR / "halfspace_resolution_summary.csv")
    plot_resolution_convergence(
        resolution_summary, FIGURE_DIR / "Figure_HS3_resolution_convergence.png"
    )
    plot_resolution_station_map(
        resolution_station, FIGURE_DIR / "Figure_HS4_resolution_station_pattern.png"
    )

    print("Analyzing the topography grids...")
    topography_metrics, topography_arrays = load_topography_metrics(catalog)
    write_dataframe(topography_metrics, DERIVED_DIR / "halfspace_topography_grid_metrics.csv")
    plot_topography_resolution(
        topography_metrics,
        topography_arrays,
        FIGURE_DIR / "Figure_HS5_topography_grid_resolution.png",
    )

    print("Analyzing the 216-station layering switch...")
    layering = catalog["half_space"]["layering_switch"]
    uniform = load_filtered_record(
        "Uniform half-space", Path(layering["uniform_half_space_station_nc"]), target_time
    )
    layered = load_filtered_record("Layered", Path(layering["layered_station_nc"]), target_time)
    layering_metrics = paired_metrics(uniform, layered)
    geometry = parse_station_file(Path(layering["shared_station_file"]))
    if uniform.names != list(geometry["station"]) or layered.names != uniform.names:
        raise ValueError("Layering comparison station names do not match the shared station file")
    layering_metrics = layering_metrics.merge(geometry, on="station", how="left", validate="one_to_one")
    write_dataframe(layering_metrics, DERIVED_DIR / "halfspace_layering_switch_station_metrics.csv")
    plot_pair_waveforms(
        uniform,
        layered,
        layering_metrics,
        FIGURE_DIR / "Figure_HS6_layering_switch_waveforms.png",
        "Uniform half-space",
        "Layered",
        "Three-component waveforms: uniform half-space versus layered model",
    )
    plot_pair_metrics(
        layering_metrics,
        FIGURE_DIR / "Figure_HS7_layering_switch_metrics.png",
        "Stationwise effects of replacing the uniform half-space with layering",
        COLORS["layered"],
    )

    print("Testing peak-energy time against R and R^2 forms...")
    time_distance_stations, time_distance_fits = time_distance_analysis(uniform, layered, geometry)
    write_dataframe(time_distance_stations, DERIVED_DIR / "halfspace_time_distance_station_metrics.csv")
    write_dataframe(time_distance_fits, DERIVED_DIR / "halfspace_time_distance_fit_summary.csv")
    plot_time_distance(
        time_distance_stations,
        time_distance_fits,
        FIGURE_DIR / "Figure_HS8_time_distance_diagnostics.png",
    )

    print("Building the half-space/A16 cross-region comparison...")
    cross_region = a16_cross_region_summary(topography_switch_metrics)
    write_dataframe(cross_region, DERIVED_DIR / "halfspace_a16_cross_region_summary.csv")
    plot_cross_region(
        cross_region,
        FIGURE_DIR / "Figure_HS9_halfspace_a16_effect_comparison.png",
    )

    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "processing": {
            "bandpass_hz": [FILTER_LOW_HZ, FILTER_HIGH_HZ],
            "filter_order": FILTER_ORDER,
            "common_dt_s": COMMON_DT_S,
            "comparison_end_s": COMMON_END_S,
        },
        "topography_switch": percentile_summary(
            topography_switch_metrics, "with_topography / without_topography"
        ),
        "topography_switch_receiver_geometry": {
            "station_count": int(len(topography_switch_geometry)),
            "distance_first_km": float(topography_switch_geometry["distance_km"].iloc[0]),
            "distance_last_km": float(topography_switch_geometry["distance_km"].iloc[-1]),
            "median_azimuth_deg": float(
                np.median(topography_switch_geometry["azimuth_deg"])
            ),
            "maximum_formula_position_error_mm": float(
                topography_switch_geometry["formula_position_error_mm"].max()
            ),
            "preferred_distance_analysis_station_range": list(preferred_range),
        },
        "layering_switch": percentile_summary(
            layering_metrics, "layered / uniform_half_space"
        ),
        "resolution_summary": resolution_summary.to_dict(orient="records"),
        "topography_grid_summary": topography_metrics.to_dict(orient="records"),
        "time_distance_fits": time_distance_fits.to_dict(orient="records"),
        "cross_region": cross_region.to_dict(orient="records"),
        "data_quality_notes": [
            "The two 800-receiver NetCDF files are paired by station_name r1-r800.",
            "Their exact geometry is reconstructed and checked against newfigure6_part3_3.m and cgfd3d.revise.use1.topo.0.125.Q.sh: source (50000,50000) m, azimuth 75 degrees, 50 m spacing, r1=0.05 km through r800=40 km.",
            "The present 216-receiver test.station files are a different receiver geometry and are not used for the 800-receiver topography switch.",
            "The 800-receiver horizontal components are rotated from X/Y to radial/transverse using the recovered 75-degree azimuth.",
            "The archived 125 m _old directory lacks test.station; the identical 216-name geometry in E:/project_use1_topo_0.125/test.station is used for the resolution series.",
            "All waveform comparisons use separate native-rate filtering followed by interpolation to 50 Hz.",
        ],
    }
    (DERIVED_DIR / "halfspace_analysis_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Finished. Figures: {FIGURE_DIR}")


if __name__ == "__main__":
    main()
