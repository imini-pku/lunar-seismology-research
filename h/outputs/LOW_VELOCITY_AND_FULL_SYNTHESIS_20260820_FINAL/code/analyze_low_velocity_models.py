"""Analyze the two new A16/S12 low-velocity-layer simulations.

The script preserves the validated REL3 processing conventions while making
the new comparison-window asymmetry explicit.  M1-M4 end at about 250 s;
M5-M6 end at about 400 s.  Cross-generation effects are therefore calculated
only in the common 50-245 s window.  The 50-395 s window is descriptive for
M5-M6 and is never used to manufacture an apparent low-velocity-layer effect.

Outputs are written inside jgr_planets_submission:
  data/derived/low_velocity_*.csv|json
  figures/low_velocity/Figure_LV*.png
  provenance/low_velocity_input_audit.csv

No exact layer thickness or velocity is inferred: the two supplied project
folders contain output/station.nc only and no run manifest.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SCRIPT = Path(__file__).resolve()
SUBMISSION_ROOT = SCRIPT.parents[1]
WORKSPACE_ROOT = SCRIPT.parents[2]
LOCAL_PACKAGES = WORKSPACE_ROOT / "work" / "python_pkgs"
if LOCAL_PACKAGES.is_dir():
    sys.path.insert(0, str(LOCAL_PACKAGES))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from netCDF4 import Dataset
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, correlate, correlation_lags, detrend, hilbert, sosfiltfilt, spectrogram
from scipy.stats import spearmanr, wilcoxon


RAW_DIR = SUBMISSION_ROOT / "data" / "raw"
DERIVED_DIR = SUBMISSION_ROOT / "data" / "derived"
FIGURE_DIR = SUBMISSION_ROOT / "figures" / "low_velocity"
PROVENANCE_DIR = SUBMISSION_ROOT / "provenance"

MODEL_FILES = {
    "M1": RAW_DIR / "M1_flat_no_heterogeneity_station.nc",
    "M2": RAW_DIR / "M2_flat_heterogeneity_station.nc",
    "M3": RAW_DIR / "M3_topography_no_heterogeneity_station.nc",
    "M4": RAW_DIR / "M4_topography_heterogeneity_station.nc",
    "M5": RAW_DIR / "M5_flat_heterogeneity_low_velocity_station.nc",
    "M6": RAW_DIR / "M6_topography_heterogeneity_low_velocity_station.nc",
}

MODEL_LABELS = {
    "M1": "Flat / no heterogeneity",
    "M2": "Flat / heterogeneity",
    "M3": "Topography / no heterogeneity",
    "M4": "Topography / heterogeneity",
    "M5": "Flat / heterogeneity / low-V",
    "M6": "Topography / heterogeneity / low-V",
}

MODEL_COLORS = {
    "M1": "#0072B2",
    "M2": "#D55E00",
    "M3": "#009E73",
    "M4": "#CC79A7",
    "M5": "#E69F00",
    "M6": "#56B4E9",
}

OBSERVED_FILES = {
    "Z": RAW_DIR / "16s.12.BHZ.SAC",
    "E": RAW_DIR / "16s.12.BHE.SAC",
    "N": RAW_DIR / "16s.12.BHN.SAC",
}

SOURCE_XY_M = np.array([161_310.0, 207_630.0])
COMMON_START_S = 50.0
COMMON_END_S = 245.0
EXTENDED_END_S = 395.0
OBSERVED_END_S = 3_000.0
COMMON_DT_S = 0.02
FILTER_BAND_HZ = (0.3, 0.9)
FILTER_ORDER = 4
SMOOTHING_WINDOWS_S = (5.0, 10.0, 20.0, 40.0, 60.0, 100.0)
EPS = np.finfo(float).tiny
RNG_SEED = 20260817

POSITIVE_METRICS = ("peak_amplitude", "total_energy", "rms", "T90_s")
TIME_METRICS = ("tmax_s", "t05_s", "t50_s", "t95_s", "rise_to_tmax_s")
FRACTION_METRICS = ("Z_fraction", "R_fraction", "T_fraction", "late_fraction_after_120s")

EFFECTS = {
    "low_flat": ("M5", "M2", "Low-velocity effect, flat heterogeneous background"),
    "low_topography": ("M6", "M4", "Low-velocity effect, topographic heterogeneous background"),
    "topography_no_low": ("M4", "M2", "Topography effect, no low-velocity layer"),
    "topography_low": ("M6", "M5", "Topography effect, low-velocity background"),
}


@dataclass
class Geometry:
    station_xy_m: np.ndarray
    ray_indices: tuple[np.ndarray, ...]
    primary_indices: np.ndarray
    fit_indices: tuple[np.ndarray, ...]
    distance_km: np.ndarray
    azimuth_rad: np.ndarray
    ray_number: np.ndarray
    station_names: list[str]
    blocks: list[np.ndarray]


@dataclass
class ModelRecord:
    name: str
    time_native: np.ndarray
    common_zrt: np.ndarray
    extended_zrt: np.ndarray | None
    common_metrics: dict[str, np.ndarray]
    extended_metrics: dict[str, np.ndarray] | None
    s12_time: np.ndarray
    s12_zen: np.ndarray
    raw_dominant_frequency_s12_hz: np.ndarray
    input_meta: dict[str, object]


@dataclass
class ObservedRecord:
    time: np.ndarray
    zen: np.ndarray
    zrt: np.ndarray
    raw_dominant_frequency_hz: np.ndarray
    sac_orientation: dict[str, tuple[float, float]]


def configure_plot_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 300,
            "font.family": "DejaVu Sans",
            "font.size": 8.8,
            "axes.titlesize": 10.2,
            "axes.labelsize": 9.0,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "grid.linewidth": 0.6,
            "legend.frameon": False,
            "lines.linewidth": 1.1,
        }
    )


def save_figure(fig: plt.Figure, filename: str) -> Path:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURE_DIR / filename
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def build_station_geometry() -> Geometry:
    ray_targets = np.array(
        [[197_256.0, 59_703.0], [100_000.0, 140_000.0], [213_000.0, 247_000.0]]
    )
    station_xy = [[197_256.0, 59_703.0]]
    ray_indices: list[np.ndarray] = []
    station_index = 1
    for target in ray_targets:
        direction = target - SOURCE_XY_M
        direction /= np.linalg.norm(direction)
        current: list[int] = []
        distance_m = 1_000.0
        while True:
            point = SOURCE_XY_M + direction * distance_m
            if not (0.0 <= point[0] <= 300_000.0 and 0.0 <= point[1] <= 300_000.0):
                break
            station_xy.append([round(float(point[0])), round(float(point[1]))])
            current.append(station_index)
            station_index += 1
            distance_m += 1_000.0
        ray_indices.append(np.asarray(current, dtype=int))
    xy = np.asarray(station_xy, dtype=float)
    if xy.shape != (606, 2):
        raise RuntimeError(f"Expected 606 receivers, generated {xy.shape[0]}")
    expected = ((1, 213), (214, 453), (454, 605))
    actual = tuple((int(indices[0]), int(indices[-1])) for indices in ray_indices)
    if actual != expected:
        raise RuntimeError(f"Unexpected receiver ranges: {actual}")
    offsets = xy - SOURCE_XY_M
    distance_km = np.linalg.norm(offsets, axis=1) / 1_000.0
    # Azimuth clockwise from north. Vx=E, Vy=N in the REL3 outputs.
    azimuth_rad = np.arctan2(offsets[:, 0], offsets[:, 1])
    ray_number = np.zeros(606, dtype=int)
    for number, indices in enumerate(ray_indices, start=1):
        ray_number[indices] = number
    primary = np.concatenate([indices[5:-5] for indices in ray_indices])
    fit_indices = tuple(
        indices[5:-5][distance_km[indices[5:-5]] >= 10.0] for indices in ray_indices
    )
    blocks: list[np.ndarray] = []
    for indices in ray_indices:
        main = indices[5:-5]
        for start in range(0, (main.size // 10) * 10, 10):
            blocks.append(main[start : start + 10])
    if len(primary) != 575 or len(blocks) != 57:
        raise RuntimeError(f"Unexpected primary/block counts: {len(primary)}/{len(blocks)}")
    return Geometry(
        station_xy_m=xy,
        ray_indices=tuple(ray_indices),
        primary_indices=primary,
        fit_indices=fit_indices,
        distance_km=distance_km,
        azimuth_rad=azimuth_rad,
        ray_number=ray_number,
        station_names=[f"r{i}" for i in range(1, 607)],
        blocks=blocks,
    )


def decode_station_names(variable: np.ndarray) -> list[str]:
    result: list[str] = []
    for row in np.asarray(variable):
        text = b"".join(np.asarray(row).astype("S1").tolist()).split(b"\x00", 1)[0]
        result.append(text.decode("utf-8", errors="replace").strip())
    return result


def dominant_frequency(time: np.ndarray, traces: np.ndarray) -> np.ndarray:
    dt = float(np.median(np.diff(time)))
    prepared = detrend(np.asarray(traces, dtype=np.float64), axis=-1, type="linear")
    spectrum = np.abs(np.fft.rfft(prepared, axis=-1))
    frequency = np.fft.rfftfreq(time.size, d=dt)
    spectrum[..., 0] = 0.0
    return frequency[np.argmax(spectrum, axis=-1)]


def filter_component(time: np.ndarray, traces: np.ndarray) -> np.ndarray:
    dt = float(np.median(np.diff(time)))
    sos = butter(
        FILTER_ORDER,
        FILTER_BAND_HZ,
        btype="bandpass",
        fs=1.0 / dt,
        output="sos",
    )
    prepared = detrend(np.asarray(traces, dtype=np.float64), axis=-1, type="linear")
    return sosfiltfilt(sos, prepared, axis=-1).astype(np.float32)


def interpolate_field(time: np.ndarray, field: np.ndarray, target_time: np.ndarray) -> np.ndarray:
    output = np.empty((field.shape[0], field.shape[1], target_time.size), dtype=np.float32)
    for station in range(field.shape[0]):
        for component in range(field.shape[1]):
            output[station, component] = np.interp(target_time, time, field[station, component])
    return output


def analytic_intensity(field: np.ndarray) -> np.ndarray:
    intensity = np.zeros((field.shape[0], field.shape[2]), dtype=np.float32)
    for component in range(field.shape[1]):
        analytic = hilbert(field[:, component, :], axis=1)
        intensity += (analytic.real * analytic.real + analytic.imag * analytic.imag).astype(np.float32)
    return intensity


def quantile_times(time: np.ndarray, intensity: np.ndarray, quantiles: Iterable[float]) -> dict[float, np.ndarray]:
    cumulative = np.cumsum(intensity, axis=1, dtype=np.float64)
    cumulative /= np.maximum(cumulative[:, -1, None], EPS)
    return {
        quantile: time[np.argmax(cumulative >= quantile, axis=1)]
        for quantile in quantiles
    }


def compute_metrics(time: np.ndarray, zrt: np.ndarray, start_s: float, end_s: float) -> dict[str, np.ndarray]:
    keep = (time >= start_s) & (time <= end_s)
    if not np.any(keep):
        raise ValueError(f"Window {start_s}-{end_s} s does not overlap record")
    window_time = time[keep]
    field = np.asarray(zrt[:, :, keep], dtype=np.float32)
    dt = float(np.median(np.diff(window_time)))
    component_energy = np.sum(field * field, axis=2, dtype=np.float64) * dt
    total_energy = np.sum(component_energy, axis=1)
    vector_squared = np.sum(field * field, axis=1, dtype=np.float32)
    peak_amplitude = np.sqrt(np.max(vector_squared, axis=1))
    duration = max(float(window_time[-1] - window_time[0]), dt)
    rms = np.sqrt(total_energy / (3.0 * duration))
    fraction = component_energy / np.maximum(total_energy[:, None], EPS)
    # REL3 and the half-space workflow define cumulative-energy times from
    # squared filtered velocity.  Keep the analytic-signal intensity only for
    # the smoothed peak-energy time so T90/t05/t50/t95 remain comparable to the
    # existing project database.
    qtimes = quantile_times(window_time, vector_squared, (0.05, 0.50, 0.90, 0.95))
    intensity = analytic_intensity(field)
    candidate_tmax: list[np.ndarray] = []
    for smoothing_s in SMOOTHING_WINDOWS_S:
        sample_count = max(1, int(round(smoothing_s / dt)))
        smooth = uniform_filter1d(intensity, sample_count, axis=1, mode="nearest")
        candidate_tmax.append(window_time[np.argmax(smooth, axis=1)])
    candidate = np.stack(candidate_tmax)
    tmax = np.median(candidate, axis=0)
    energy_after_120 = np.sum(
        field[:, :, window_time >= 120.0] ** 2, axis=(1, 2), dtype=np.float64
    ) * dt
    energy_after_200 = np.sum(
        field[:, :, window_time >= 200.0] ** 2, axis=(1, 2), dtype=np.float64
    ) * dt
    final_20_start = max(start_s, end_s - 20.0)
    terminal_energy = np.sum(
        field[:, :, window_time >= final_20_start] ** 2,
        axis=(1, 2),
        dtype=np.float64,
    ) * dt
    return {
        "peak_amplitude": peak_amplitude.astype(float),
        "total_energy": total_energy,
        "rms": rms,
        "Z_fraction": fraction[:, 0],
        "R_fraction": fraction[:, 1],
        "T_fraction": fraction[:, 2],
        "t05_s": qtimes[0.05],
        "t50_s": qtimes[0.50],
        "t90_quantile_s": qtimes[0.90],
        "t95_s": qtimes[0.95],
        "T90_s": qtimes[0.95] - qtimes[0.05],
        "tmax_s": tmax,
        "tmax_min_s": np.min(candidate, axis=0),
        "tmax_max_s": np.max(candidate, axis=0),
        "tmax_std_s": np.std(candidate, axis=0, ddof=1),
        "rise_to_tmax_s": tmax - qtimes[0.05],
        "late_fraction_after_120s": energy_after_120 / np.maximum(total_energy, EPS),
        "late_fraction_after_200s": energy_after_200 / np.maximum(total_energy, EPS),
        "terminal_20s_fraction": terminal_energy / np.maximum(total_energy, EPS),
    }


def inspect_model_file(path: Path) -> dict[str, object]:
    with Dataset(path, "r") as dataset:
        time = np.asarray(dataset.variables["time"][:], dtype=float)
        names = decode_station_names(dataset.variables["station_name"][:])
        seq = np.asarray(dataset.variables["seq_no"][:], dtype=int)
        dimensions = {name: len(value) for name, value in dataset.dimensions.items()}
        variables = sorted(dataset.variables)
        finite = True
        for component in ("Vx", "Vy", "Vz"):
            variable = dataset.variables[component]
            for start in range(0, variable.shape[0], 64):
                sample = np.asarray(variable[start : start + 64, :])
                if not np.isfinite(sample).all():
                    finite = False
                    break
    diffs = np.diff(time)
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "dimensions": dimensions,
        "variables": variables,
        "station_names": names,
        "seq_no": seq,
        "time_start_s": float(time[0]),
        "time_end_s": float(time[-1]),
        "sample_count": int(time.size),
        "median_dt_s": float(np.median(diffs)),
        "minimum_dt_s": float(np.min(diffs)),
        "maximum_dt_s": float(np.max(diffs)),
        "all_finite": finite,
    }


def load_model(name: str, geometry: Geometry, common_time: np.ndarray, extended_time: np.ndarray) -> ModelRecord:
    path = MODEL_FILES[name]
    meta = inspect_model_file(path)
    with Dataset(path, "r") as dataset:
        time = np.asarray(dataset.variables["time"][:], dtype=np.float64)
        s12_raw_zen = np.vstack(
            [
                np.asarray(dataset.variables[variable][0, :], dtype=np.float64)
                for variable in ("Vz", "Vx", "Vy")
            ]
        )
        raw_frequency = dominant_frequency(time, s12_raw_zen)
        filtered: list[np.ndarray] = []
        for variable in ("Vz", "Vx", "Vy"):
            values = np.asarray(dataset.variables[variable][:], dtype=np.float32)
            if values.shape == (time.size, 606):
                values = values.T
            if values.shape != (606, time.size):
                raise ValueError(f"Unexpected {name}/{variable} shape: {values.shape}")
            filtered.append(filter_component(time, values))
    vertical, east, north = filtered
    sine = np.sin(geometry.azimuth_rad)[:, None]
    cosine = np.cos(geometry.azimuth_rad)[:, None]
    radial = east * sine + north * cosine
    transverse = east * cosine - north * sine
    zrt = np.stack((vertical, radial, transverse), axis=1).astype(np.float32)
    s12_zen = np.vstack((vertical[0], east[0], north[0])).astype(np.float32)
    common_metrics = compute_metrics(time, zrt, COMMON_START_S, COMMON_END_S)
    if name in ("M5", "M6"):
        extended_zrt = interpolate_field(time, zrt, extended_time)
        common_zrt = extended_zrt[:, :, : common_time.size]
        extended_metrics = compute_metrics(time, zrt, COMMON_START_S, EXTENDED_END_S)
    else:
        common_zrt = interpolate_field(time, zrt, common_time)
        extended_zrt = None
        extended_metrics = None
    return ModelRecord(
        name=name,
        time_native=time,
        common_zrt=common_zrt,
        extended_zrt=extended_zrt,
        common_metrics=common_metrics,
        extended_metrics=extended_metrics,
        s12_time=time,
        s12_zen=s12_zen,
        raw_dominant_frequency_s12_hz=raw_frequency,
        input_meta=meta,
    )


def read_sac(path: Path) -> tuple[np.ndarray, np.ndarray, float, float]:
    raw = path.read_bytes()
    if len(raw) < 632:
        raise ValueError(f"SAC file is too short: {path}")
    header_floats = None
    header_integers = None
    byte_order = ""
    for candidate in ("<", ">"):
        floats = np.frombuffer(raw, dtype=f"{candidate}f4", count=70, offset=0)
        integers = np.frombuffer(raw, dtype=f"{candidate}i4", count=40, offset=280)
        if 1 <= int(integers[6]) <= 20 and 0 < int(integers[9]) < 10_000_000:
            header_floats = floats
            header_integers = integers
            byte_order = candidate
            break
    if header_floats is None or header_integers is None:
        raise ValueError(f"Could not determine SAC byte order: {path}")
    count = int(header_integers[9])
    data = np.frombuffer(raw, dtype=f"{byte_order}f4", count=count, offset=632).astype(float)
    dt = float(header_floats[0])
    start = float(header_floats[5])
    time = start + np.arange(count, dtype=float) * dt
    return time, data, float(header_floats[57]), float(header_floats[58])


def load_observed(geometry: Geometry) -> ObservedRecord:
    channels: dict[str, tuple[np.ndarray, np.ndarray, float, float]] = {
        key: read_sac(path) for key, path in OBSERVED_FILES.items()
    }
    time = channels["Z"][0]
    for key in ("E", "N"):
        if channels[key][0].shape != time.shape or not np.allclose(channels[key][0], time, atol=1e-3):
            raise ValueError(f"Observed {key} time grid differs from Z")
    vertical = channels["Z"][1]
    horizontal = np.vstack((channels["E"][1], channels["N"][1]))
    azimuths = np.deg2rad([channels["E"][2], channels["N"][2]])
    orientation = np.column_stack((np.cos(azimuths), np.sin(azimuths)))
    north, east = np.linalg.solve(orientation, horizontal)
    raw_zen = np.vstack((vertical, east, north))
    frequency = dominant_frequency(time, raw_zen)
    filtered_zen = filter_component(time, raw_zen)
    sine = float(np.sin(geometry.azimuth_rad[0]))
    cosine = float(np.cos(geometry.azimuth_rad[0]))
    radial = filtered_zen[1] * sine + filtered_zen[2] * cosine
    transverse = filtered_zen[1] * cosine - filtered_zen[2] * sine
    zrt = np.vstack((filtered_zen[0], radial, transverse))
    orientation_meta = {
        key: (channels[key][2], channels[key][3]) for key in ("Z", "E", "N")
    }
    return ObservedRecord(time, filtered_zen, zrt, frequency, orientation_meta)


def median_iqr(values: np.ndarray) -> dict[str, float]:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {"q10": math.nan, "q25": math.nan, "median": math.nan, "q75": math.nan, "q90": math.nan}
    q10, q25, med, q75, q90 = np.quantile(finite, (0.10, 0.25, 0.50, 0.75, 0.90))
    return {"q10": float(q10), "q25": float(q25), "median": float(med), "q75": float(q75), "q90": float(q90)}


def block_values(values: np.ndarray, blocks: list[np.ndarray]) -> np.ndarray:
    return np.asarray([np.nanmedian(values[indices]) for indices in blocks], dtype=float)


def bootstrap_block_median(values: np.ndarray, blocks: list[np.ndarray], iterations: int = 5000) -> tuple[float, float]:
    rng = np.random.default_rng(RNG_SEED)
    block_median = np.asarray([np.nanmedian(values[indices]) for indices in blocks], dtype=float)
    estimates = np.empty(iterations, dtype=float)
    for index in range(iterations):
        sample = rng.choice(block_median, size=block_median.size, replace=True)
        estimates[index] = np.nanmedian(sample)
    low, high = np.nanquantile(estimates, (0.025, 0.975))
    return float(low), float(high)


def bh_fdr(p_values: list[float]) -> list[float]:
    values = np.asarray(p_values, dtype=float)
    order = np.argsort(values)
    ranked = values[order]
    adjusted = ranked * values.size / np.arange(1, values.size + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    result = np.empty_like(adjusted)
    result[order] = np.minimum(adjusted, 1.0)
    return result.tolist()


def effect_values(records: dict[str, ModelRecord], effect: str, metric: str) -> np.ndarray:
    numerator, denominator, _ = EFFECTS[effect]
    first = records[numerator].common_metrics[metric]
    second = records[denominator].common_metrics[metric]
    if metric in POSITIVE_METRICS:
        return np.log(np.maximum(first, EPS) / np.maximum(second, EPS))
    return first - second


def cubic_residual(values: np.ndarray, distance: np.ndarray, indices: np.ndarray) -> np.ndarray:
    output = np.full(values.shape, np.nan, dtype=float)
    x = distance[indices]
    y = values[indices]
    finite = np.isfinite(x) & np.isfinite(y)
    coefficients = np.polyfit(x[finite], y[finite], deg=3)
    residual = y[finite] - np.polyval(coefficients, x[finite])
    scale = float(np.std(residual, ddof=1))
    normalized = (residual - np.mean(residual)) / (scale if scale > 0 else 1.0)
    output[indices[finite]] = normalized
    return output


def detrended_block_pair(
    first: np.ndarray,
    second: np.ndarray,
    geometry: Geometry,
) -> tuple[np.ndarray, np.ndarray]:
    first_residual = np.full(606, np.nan)
    second_residual = np.full(606, np.nan)
    for ray in geometry.ray_indices:
        indices = ray[5:-5]
        one = cubic_residual(first, geometry.distance_km, indices)
        two = cubic_residual(second, geometry.distance_km, indices)
        first_residual[indices] = one[indices]
        second_residual[indices] = two[indices]
    return block_values(first_residual, geometry.blocks), block_values(second_residual, geometry.blocks)


def paired_pearson(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    a = np.asarray(first, dtype=np.float64).reshape(first.shape[0], -1)
    b = np.asarray(second, dtype=np.float64).reshape(second.shape[0], -1)
    a -= np.mean(a, axis=1, keepdims=True)
    b -= np.mean(b, axis=1, keepdims=True)
    denominator = np.sqrt(np.sum(a * a, axis=1) * np.sum(b * b, axis=1))
    return np.sum(a * b, axis=1) / np.maximum(denominator, EPS)


def best_envelope_correlation(
    first: np.ndarray,
    second: np.ndarray,
    sample_interval_s: float,
    maximum_lag_s: float = 10.0,
) -> tuple[np.ndarray, np.ndarray]:
    first_intensity = uniform_filter1d(analytic_intensity(first), 250, axis=1, mode="nearest")[:, ::5]
    second_intensity = uniform_filter1d(analytic_intensity(second), 250, axis=1, mode="nearest")[:, ::5]
    dt = sample_interval_s * 5.0
    correlations = np.empty(first.shape[0], dtype=float)
    lags_s = np.empty(first.shape[0], dtype=float)
    for station in range(first.shape[0]):
        a = first_intensity[station].astype(float)
        b = second_intensity[station].astype(float)
        a -= np.mean(a)
        b -= np.mean(b)
        correlation = correlate(a, b, mode="full", method="fft")
        lags = correlation_lags(a.size, b.size, mode="full")
        keep = np.abs(lags * dt) <= maximum_lag_s
        selected_lags = lags[keep]
        lag = int(selected_lags[np.argmax(correlation[keep])])
        if lag < 0:
            aa = a[:lag]
            bb = b[-lag:]
        elif lag > 0:
            aa = a[lag:]
            bb = b[:-lag]
        else:
            aa, bb = a, b
        denominator = math.sqrt(float(np.sum(aa * aa) * np.sum(bb * bb)))
        correlations[station] = float(np.sum(aa * bb) / denominator) if denominator else math.nan
        lags_s[station] = lag * dt
    return correlations, lags_s


def source_scale(observed: ObservedRecord, model: ModelRecord) -> float:
    target = observed.time[(observed.time >= COMMON_START_S) & (observed.time <= COMMON_END_S)]
    observed_samples = np.vstack([np.interp(target, observed.time, row) for row in observed.zen])
    model_samples = np.vstack([np.interp(target, model.s12_time, row) for row in model.s12_zen])
    observed_rms = float(np.sqrt(np.mean(observed_samples * observed_samples)))
    model_rms = float(np.sqrt(np.mean(model_samples * model_samples)))
    return observed_rms / model_rms if model_rms else 1.0


def one_record_metrics(time: np.ndarray, zen: np.ndarray) -> dict[str, float]:
    intensity = np.sum(np.abs(hilbert(zen, axis=1)) ** 2, axis=0)
    dt = float(np.median(np.diff(time)))
    cumulative = np.cumsum(intensity, dtype=float) * dt
    quantile_time = lambda q: float(time[min(np.searchsorted(cumulative, q * cumulative[-1]), time.size - 1)])
    candidate = []
    for smoothing_s in SMOOTHING_WINDOWS_S:
        smooth = uniform_filter1d(intensity, max(1, int(round(smoothing_s / dt))), mode="nearest")
        candidate.append(float(time[np.argmax(smooth)]))
    t05 = quantile_time(0.05)
    return {
        "tmax_median_s": float(np.median(candidate)),
        "tmax_min_s": float(np.min(candidate)),
        "tmax_max_s": float(np.max(candidate)),
        "tmax_std_s": float(np.std(candidate, ddof=1)),
        "t05_s": t05,
        "t50_s": quantile_time(0.50),
        "t95_s": quantile_time(0.95),
        "rise_t05_to_tmax_s": float(np.median(candidate)) - t05,
        "energy_fraction_before_250s": float(cumulative[min(np.searchsorted(time, 250.0), time.size - 1)] / cumulative[-1]),
        "energy_fraction_before_400s": float(cumulative[min(np.searchsorted(time, 400.0), time.size - 1)] / cumulative[-1]),
    }


def observed_model_table(observed: ObservedRecord, records: dict[str, ModelRecord]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    observed_metrics = one_record_metrics(observed.time, observed.zen)
    rows.append(
        {
            "record": "Observed A16S12",
            "source_scale": 1.0,
            "raw_dominant_frequency_Z_hz": observed.raw_dominant_frequency_hz[0],
            "raw_dominant_frequency_E_hz": observed.raw_dominant_frequency_hz[1],
            "raw_dominant_frequency_N_hz": observed.raw_dominant_frequency_hz[2],
            **observed_metrics,
            "early_waveform_correlation_Z": np.nan,
            "early_waveform_correlation_E": np.nan,
            "early_waveform_correlation_N": np.nan,
            "early_3c_waveform_correlation": np.nan,
            "early_3c_normalized_rmse": np.nan,
            "early_envelope_correlation_zero_lag": np.nan,
            "early_envelope_correlation_best_lag": np.nan,
            "best_envelope_lag_s": np.nan,
        }
    )
    target = observed.time[(observed.time >= COMMON_START_S) & (observed.time <= COMMON_END_S)]
    observed_common = np.vstack([np.interp(target, observed.time, row) for row in observed.zen])
    observed_envelope = uniform_filter1d(
        np.sum(np.abs(hilbert(observed_common, axis=1)) ** 2, axis=0),
        max(1, int(round(5.0 / np.median(np.diff(target))))),
        mode="nearest",
    )
    for name, record in records.items():
        scale = source_scale(observed, record)
        model_common = np.vstack([np.interp(target, record.s12_time, row) for row in record.s12_zen]) * scale
        correlations = [float(np.corrcoef(observed_common[i], model_common[i])[0, 1]) for i in range(3)]
        corr3 = float(np.corrcoef(observed_common.ravel(), model_common.ravel())[0, 1])
        nrmse = float(
            np.sqrt(np.mean((observed_common - model_common) ** 2))
            / np.sqrt(np.mean(observed_common**2))
        )
        model_envelope = uniform_filter1d(
            np.sum(np.abs(hilbert(model_common, axis=1)) ** 2, axis=0),
            max(1, int(round(5.0 / np.median(np.diff(target))))),
            mode="nearest",
        )
        envelope_zero = float(np.corrcoef(observed_envelope, model_envelope)[0, 1])
        envelope_best, envelope_lag = best_lag_1d(observed_envelope, model_envelope, float(np.median(np.diff(target))))
        rows.append(
            {
                "record": name,
                "source_scale": scale,
                "raw_dominant_frequency_Z_hz": record.raw_dominant_frequency_s12_hz[0],
                "raw_dominant_frequency_E_hz": record.raw_dominant_frequency_s12_hz[1],
                "raw_dominant_frequency_N_hz": record.raw_dominant_frequency_s12_hz[2],
                **one_record_metrics(record.s12_time, record.s12_zen),
                "early_waveform_correlation_Z": correlations[0],
                "early_waveform_correlation_E": correlations[1],
                "early_waveform_correlation_N": correlations[2],
                "early_3c_waveform_correlation": corr3,
                "early_3c_normalized_rmse": nrmse,
                "early_envelope_correlation_zero_lag": envelope_zero,
                "early_envelope_correlation_best_lag": envelope_best,
                "best_envelope_lag_s": envelope_lag,
            }
        )
    return pd.DataFrame(rows)


def best_lag_1d(first: np.ndarray, second: np.ndarray, dt: float, maximum_lag_s: float = 10.0) -> tuple[float, float]:
    best = -np.inf
    best_lag = 0
    maximum = int(round(maximum_lag_s / dt))
    for lag in range(-maximum, maximum + 1):
        if lag < 0:
            a, b = first[:lag], second[-lag:]
        elif lag > 0:
            a, b = first[lag:], second[:-lag]
        else:
            a, b = first, second
        if a.size < 2:
            continue
        value = float(np.corrcoef(a, b)[0, 1])
        if value > best:
            best = value
            best_lag = lag
    return best, best_lag * dt


def metrics_long_table(records: dict[str, ModelRecord], geometry: Geometry) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for name, record in records.items():
        for station_index, station_name in enumerate(geometry.station_names):
            row: dict[str, object] = {
                "model": name,
                "station": station_name,
                "station_index_zero_based": station_index,
                "ray": "S12" if station_index == 0 else int(geometry.ray_number[station_index]),
                "included_primary": int(station_index in set(geometry.primary_indices.tolist())),
                "distance_km": geometry.distance_km[station_index],
                "x_m": geometry.station_xy_m[station_index, 0],
                "y_m": geometry.station_xy_m[station_index, 1],
            }
            for metric, values in record.common_metrics.items():
                row[metric] = values[station_index]
            rows.append(row)
    return pd.DataFrame(rows)


def effects_long_table(records: dict[str, ModelRecord], geometry: Geometry) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    metrics = (*POSITIVE_METRICS, *TIME_METRICS, *FRACTION_METRICS)
    for effect, (_, _, label) in EFFECTS.items():
        for metric in metrics:
            values = effect_values(records, effect, metric)
            scale = "log_ratio" if metric in POSITIVE_METRICS else "difference"
            for station_index in geometry.primary_indices:
                rows.append(
                    {
                        "effect": effect,
                        "effect_label": label,
                        "metric": metric,
                        "scale": scale,
                        "station": geometry.station_names[station_index],
                        "ray": int(geometry.ray_number[station_index]),
                        "distance_km": geometry.distance_km[station_index],
                        "value": values[station_index],
                        "ratio_or_value": math.exp(values[station_index]) if scale == "log_ratio" else values[station_index],
                    }
                )
    return pd.DataFrame(rows)


def summarize_effects(records: dict[str, ModelRecord], geometry: Geometry) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    p_rows: list[float] = []
    metrics = (*POSITIVE_METRICS, *TIME_METRICS, *FRACTION_METRICS)
    for effect, (_, _, label) in EFFECTS.items():
        for metric in metrics:
            values = effect_values(records, effect, metric)
            primary = values[geometry.primary_indices]
            station_stats = median_iqr(primary)
            ci_low, ci_high = bootstrap_block_median(values, geometry.blocks)
            blocks = block_values(values, geometry.blocks)
            block_stats = median_iqr(blocks)
            try:
                p_value = float(wilcoxon(blocks, zero_method="wilcox", alternative="two-sided").pvalue)
            except ValueError:
                p_value = 1.0
            p_rows.append(p_value)
            rows.append(
                {
                    "effect": effect,
                    "effect_label": label,
                    "metric": metric,
                    "scale": "log_ratio" if metric in POSITIVE_METRICS else "difference",
                    **block_stats,
                    **{f"station_{key}": value for key, value in station_stats.items()},
                    "bootstrap95_low": ci_low,
                    "bootstrap95_high": ci_high,
                    "fraction_positive": float(np.mean(primary > 0)),
                    "spatial_block_count": len(blocks),
                    "wilcoxon_block_p": p_value,
                }
            )
    q_values = bh_fdr(p_rows)
    for row, q_value in zip(rows, q_values, strict=True):
        row["BH_FDR_q"] = q_value
        if row["scale"] == "log_ratio":
            for key in ("q10", "q25", "median", "q75", "q90", "bootstrap95_low", "bootstrap95_high"):
                row[f"ratio_{key}"] = math.exp(float(row[key]))
            for key in ("q10", "q25", "median", "q75", "q90"):
                row[f"ratio_station_{key}"] = math.exp(float(row[f"station_{key}"]))
    return pd.DataFrame(rows)


def summarize_models(records: dict[str, ModelRecord], geometry: Geometry) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for name, record in records.items():
        for metric, values in record.common_metrics.items():
            stats = median_iqr(values[geometry.primary_indices])
            rows.append({"window": "common_50_245s", "model": name, "metric": metric, **stats, "n": 575})
        if record.extended_metrics is not None:
            for metric, values in record.extended_metrics.items():
                stats = median_iqr(values[geometry.primary_indices])
                rows.append({"window": "extended_50_395s", "model": name, "metric": metric, **stats, "n": 575})
    return pd.DataFrame(rows)


def per_ray_summary(records: dict[str, ModelRecord], geometry: Geometry) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    metrics = ("peak_amplitude", "total_energy", "T90_s", "tmax_s", "t50_s", "t95_s", "T_fraction")
    for effect, (_, _, label) in EFFECTS.items():
        for ray_number, ray in enumerate(geometry.ray_indices, start=1):
            indices = ray[5:-5]
            for metric in metrics:
                values = effect_values(records, effect, metric)[indices]
                rows.append(
                    {
                        "effect": effect,
                        "effect_label": label,
                        "ray": ray_number,
                        "metric": metric,
                        "scale": "log_ratio" if metric in POSITIVE_METRICS else "difference",
                        **median_iqr(values),
                        "fraction_positive": float(np.mean(values > 0)),
                        "n": int(values.size),
                    }
                )
    return pd.DataFrame(rows)


def interaction_table(records: dict[str, ModelRecord], geometry: Geometry) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    metrics = (*POSITIVE_METRICS, *TIME_METRICS, *FRACTION_METRICS)
    for metric in metrics:
        topo_low = effect_values(records, "topography_low", metric)
        topo_no_low = effect_values(records, "topography_no_low", metric)
        interaction = topo_low - topo_no_low
        primary = interaction[geometry.primary_indices]
        ci_low, ci_high = bootstrap_block_median(interaction, geometry.blocks)
        blocks = block_values(interaction, geometry.blocks)
        station_stats = median_iqr(primary)
        rows.append(
            {
                "metric": metric,
                "scale": "log_ratio_interaction" if metric in POSITIVE_METRICS else "difference_interaction",
                **median_iqr(blocks),
                **{f"station_{key}": value for key, value in station_stats.items()},
                "bootstrap95_low": ci_low,
                "bootstrap95_high": ci_high,
                "fraction_positive": float(np.mean(primary > 0)),
            }
        )
    common = records["M2"].common_zrt
    interaction_wave = records["M6"].common_zrt - records["M5"].common_zrt - records["M4"].common_zrt + common
    low_main = records["M5"].common_zrt - common
    topo_main = records["M4"].common_zrt - common
    for component, label in enumerate(("Z", "R", "T")):
        numerator = np.sqrt(np.mean(interaction_wave[:, component] ** 2, axis=1))
        denominator = np.sqrt(np.mean(low_main[:, component] ** 2, axis=1)) + np.sqrt(np.mean(topo_main[:, component] ** 2, axis=1))
        ratio = numerator / np.maximum(denominator, EPS)
        primary = ratio[geometry.primary_indices]
        blocks = block_values(ratio, geometry.blocks)
        station_stats = median_iqr(primary)
        rows.append(
            {
                "metric": f"waveform_interaction_ratio_{label}",
                "scale": "rms_ratio",
                **median_iqr(blocks),
                **{f"station_{key}": value for key, value in station_stats.items()},
                "bootstrap95_low": bootstrap_block_median(ratio, geometry.blocks)[0],
                "bootstrap95_high": bootstrap_block_median(ratio, geometry.blocks)[1],
                "fraction_positive": float(np.mean(primary > 0)),
            }
        )
    return pd.DataFrame(rows)


def correlation_tables(records: dict[str, ModelRecord], geometry: Geometry) -> pd.DataFrame:
    path_file = DERIVED_DIR / "station_level_metrics.csv"
    path_data = pd.read_csv(path_file)
    path_data["station_index"] = path_data["station"].str.extract(r"(\d+)").astype(int) - 1
    path_relief = np.full(606, np.nan)
    mean_slope = np.full(606, np.nan)
    for row in path_data.itertuples():
        path_relief[int(row.station_index)] = float(row.path_relief_range_km)
        mean_slope[int(row.station_index)] = float(row.path_mean_absolute_slope)
    rows: list[dict[str, object]] = []
    tests: list[float] = []
    metrics = ("peak_amplitude", "total_energy", "T90_s", "tmax_s", "T_fraction")
    for metric in metrics:
        comparisons = {
            "topography_signature_no_low_vs_low": (
                effect_values(records, "topography_no_low", metric),
                effect_values(records, "topography_low", metric),
            ),
            "low_velocity_signature_flat_vs_topography": (
                effect_values(records, "low_flat", metric),
                effect_values(records, "low_topography", metric),
            ),
        }
        for relation, (first, second) in comparisons.items():
            block_first, block_second = detrended_block_pair(first, second, geometry)
            rho, p_value = spearmanr(block_first, block_second)
            tests.append(float(p_value))
            rows.append(
                {
                    "relation": relation,
                    "metric": metric,
                    "predictor": "first_effect",
                    "n_blocks": len(block_first),
                    "spearman_rho": float(rho),
                    "p_value": float(p_value),
                }
            )
        topo_low = effect_values(records, "topography_low", metric)
        for predictor_name, predictor in (("path_relief_range_km", path_relief), ("path_mean_absolute_slope", mean_slope)):
            block_predictor, block_effect = detrended_block_pair(predictor, topo_low, geometry)
            rho, p_value = spearmanr(block_predictor, block_effect)
            tests.append(float(p_value))
            rows.append(
                {
                    "relation": "path_predictor_vs_topography_effect_with_low_velocity",
                    "metric": metric,
                    "predictor": predictor_name,
                    "n_blocks": len(block_predictor),
                    "spearman_rho": float(rho),
                    "p_value": float(p_value),
                }
            )
    q_values = bh_fdr(tests)
    for row, q_value in zip(rows, q_values, strict=True):
        row["BH_FDR_q"] = q_value
    return pd.DataFrame(rows)


def waveform_similarity_table(records: dict[str, ModelRecord], geometry: Geometry) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for effect, first_name, second_name in (
        ("low_flat", "M5", "M2"),
        ("low_topography", "M6", "M4"),
        ("topography_no_low", "M4", "M2"),
        ("topography_low", "M6", "M5"),
    ):
        first = records[first_name].common_zrt
        second = records[second_name].common_zrt
        corr3 = paired_pearson(first, second)
        component_corr = [paired_pearson(first[:, index : index + 1], second[:, index : index + 1]) for index in range(3)]
        if effect in ("low_flat", "low_topography"):
            envelope_corr, envelope_lag = best_envelope_correlation(first, second, COMMON_DT_S)
        else:
            envelope_corr = np.full(606, np.nan)
            envelope_lag = np.full(606, np.nan)
        for station in geometry.primary_indices:
            rows.append(
                {
                    "effect": effect,
                    "station": geometry.station_names[station],
                    "ray": int(geometry.ray_number[station]),
                    "distance_km": geometry.distance_km[station],
                    "zero_lag_3c_correlation": corr3[station],
                    "zero_lag_Z_correlation": component_corr[0][station],
                    "zero_lag_R_correlation": component_corr[1][station],
                    "zero_lag_T_correlation": component_corr[2][station],
                    "best_5s_envelope_correlation_within_10s": envelope_corr[station],
                    "best_envelope_lag_s": envelope_lag[station],
                }
            )
    return pd.DataFrame(rows)


def distance_fit_table(records: dict[str, ModelRecord], geometry: Geometry) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for name in ("M5", "M6"):
        values = records[name].extended_metrics["tmax_s"]  # type: ignore[index]
        t95 = records[name].extended_metrics["t95_s"]  # type: ignore[index]
        for ray_number, indices in enumerate(geometry.fit_indices, start=1):
            sample_masks = {
                "all_primary": np.ones(indices.size, dtype=bool),
                # Sensitivity sample removes peak times near either analysis
                # boundary and records whose t95 is within 20 s of the end.
                "censor_safe": (
                    (values[indices] > COMMON_START_S + 20.0)
                    & (values[indices] < EXTENDED_END_S - 20.0)
                    & (t95[indices] < EXTENDED_END_S - 20.0)
                ),
            }
            for sample_definition, sample_mask in sample_masks.items():
                fit_indices = indices[sample_mask]
                distance = geometry.distance_km[fit_indices]
                response = values[fit_indices]
                linear_x = np.column_stack((np.ones(fit_indices.size), distance))
                squared_x = np.column_stack((np.ones(fit_indices.size), distance**2))
                linear_coef = np.linalg.lstsq(linear_x, response, rcond=None)[0]
                squared_coef = np.linalg.lstsq(squared_x, response, rcond=None)[0]
                linear_prediction = linear_x @ linear_coef
                squared_prediction = squared_x @ squared_coef
                linear_rss = float(np.sum((response - linear_prediction) ** 2))
                squared_rss = float(np.sum((response - squared_prediction) ** 2))
                n = fit_indices.size
                linear_rmse = math.sqrt(linear_rss / n)
                squared_rmse = math.sqrt(squared_rss / n)
                linear_aic = n * math.log(max(linear_rss / n, EPS)) + 4.0
                squared_aic = n * math.log(max(squared_rss / n, EPS)) + 4.0
                rows.append(
                    {
                        "model": name,
                        "ray": ray_number,
                        "sample_definition": sample_definition,
                        "station_count": n,
                        "excluded_boundary_count": int(indices.size - n),
                        "linear_intercept_s": linear_coef[0],
                        "linear_slope_s_per_km": linear_coef[1],
                        "linear_effective_peak_migration_speed_km_s": 1.0 / linear_coef[1],
                        "linear_rmse_s": linear_rmse,
                        "linear_aic": linear_aic,
                        "squared_intercept_s": squared_coef[0],
                        "squared_coefficient_s_per_km2": squared_coef[1],
                        "squared_rmse_s": squared_rmse,
                        "squared_aic": squared_aic,
                        "delta_aic_squared_minus_linear": squared_aic - linear_aic,
                        "preferred_form": "linear" if linear_aic < squared_aic else "squared_distance",
                    }
                )
    return pd.DataFrame(rows)


def extended_summary(records: dict[str, ModelRecord], geometry: Geometry) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for name in ("M5", "M6"):
        record = records[name]
        metrics = record.extended_metrics
        assert metrics is not None
        common_energy = record.common_metrics["total_energy"]
        extended_energy = metrics["total_energy"]
        after_common = 1.0 - common_energy / np.maximum(extended_energy, EPS)
        for station in range(606):
            rows.append(
                {
                    "model": name,
                    "station": geometry.station_names[station],
                    "ray": "S12" if station == 0 else int(geometry.ray_number[station]),
                    "included_primary": int(station in set(geometry.primary_indices.tolist())),
                    "distance_km": geometry.distance_km[station],
                    "energy_fraction_245_395s": after_common[station],
                    "terminal_20s_fraction": metrics["terminal_20s_fraction"][station],
                    "t05_s": metrics["t05_s"][station],
                    "t50_s": metrics["t50_s"][station],
                    "t95_s": metrics["t95_s"][station],
                    "T90_s": metrics["T90_s"][station],
                    "tmax_s": metrics["tmax_s"][station],
                    "t95_within_20s_of_end": int(metrics["t95_s"][station] >= EXTENDED_END_S - 20.0),
                }
            )
    return pd.DataFrame(rows)


def input_audit(records: dict[str, ModelRecord]) -> pd.DataFrame:
    reference_names = records["M1"].input_meta["station_names"]
    reference_seq = records["M1"].input_meta["seq_no"]
    rows: list[dict[str, object]] = []
    for name, record in records.items():
        meta = record.input_meta
        rows.append(
            {
                "model": name,
                "model_label": MODEL_LABELS[name],
                "path": meta["path"],
                "size_bytes": meta["size_bytes"],
                "sha256": meta["sha256"],
                "time_start_s": meta["time_start_s"],
                "time_end_s": meta["time_end_s"],
                "sample_count": meta["sample_count"],
                "median_dt_s": meta["median_dt_s"],
                "station_count": len(meta["station_names"]),
                "station_names_match_M1": list(meta["station_names"]) == list(reference_names),
                "sequence_matches_M1": bool(np.array_equal(meta["seq_no"], reference_seq)),
                "all_finite": meta["all_finite"],
                "variables": ";".join(meta["variables"]),
                "run_manifest_present": False if name in ("M5", "M6") else "not_reaudited_here",
            }
        )
    return pd.DataFrame(rows)


def choose_representative_stations(records: dict[str, ModelRecord], geometry: Geometry) -> dict[str, int]:
    low_flat_energy = effect_values(records, "low_flat", "total_energy")
    low_topo_tmax = effect_values(records, "low_topography", "tmax_s")
    interaction = effect_values(records, "topography_low", "total_energy") - effect_values(records, "topography_no_low", "total_energy")
    primary = geometry.primary_indices
    median_energy = float(np.median(low_flat_energy[primary]))
    median_station = int(primary[np.argmin(np.abs(low_flat_energy[primary] - median_energy))])
    high_delay_target = float(np.quantile(low_topo_tmax[primary], 0.90))
    high_delay = int(primary[np.argmin(np.abs(low_topo_tmax[primary] - high_delay_target))])
    strong_interaction_target = float(np.quantile(np.abs(interaction[primary]), 0.95))
    strong_interaction = int(primary[np.argmin(np.abs(np.abs(interaction[primary]) - strong_interaction_target))])
    matched = {}
    for ray_number, ray in enumerate(geometry.ray_indices, start=1):
        index = int(ray[np.argmin(np.abs(geometry.distance_km[ray] - 100.0))])
        matched[f"ray{ray_number}_100km"] = index
    return {
        "S12": 0,
        "median_low_energy_effect": median_station,
        "high_low_velocity_delay": high_delay,
        "strong_topography_low_interaction": strong_interaction,
        **matched,
    }


def ecdf(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    finite = np.sort(np.asarray(values, dtype=float)[np.isfinite(values)])
    return finite, np.arange(1, finite.size + 1) / finite.size


def smooth_profile(distance: np.ndarray, values: np.ndarray, width: int = 11) -> tuple[np.ndarray, np.ndarray]:
    order = np.argsort(distance)
    x = distance[order]
    y = values[order]
    return x, uniform_filter1d(y, size=min(width, y.size), mode="nearest")


def plot_input_audit(audit: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8), constrained_layout=True)
    ax = axes[0]
    for y, row in enumerate(audit.itertuples()):
        color = MODEL_COLORS[row.model]
        ax.plot([row.time_start_s, row.time_end_s], [y, y], color=color, linewidth=4.0, solid_capstyle="round")
        ax.scatter([row.time_end_s], [y], color=color, s=35, zorder=3)
        ax.text(row.time_end_s + 5.0, y, f"{row.sample_count:,} samples; dt={row.median_dt_s:.3f} s", va="center", fontsize=7.8)
    ax.axvline(COMMON_END_S, color="#555555", linestyle="--", linewidth=1.0, label="Common comparison end (245 s)")
    ax.axvline(EXTENDED_END_S, color="#777777", linestyle=":", linewidth=1.0, label="Low-V analysis end (395 s)")
    ax.set_yticks(range(len(audit)), audit["model"])
    ax.set_xlim(-5, 465)
    ax.set_xlabel("Time after impact (s)")
    ax.set_title("Record-length and sampling audit")
    # Keep the legend away from the M1/M2 endpoint labels near 245 s.
    ax.legend(loc="upper left", fontsize=7.5)
    ax = axes[1]
    y = np.arange(len(audit))
    checks = np.column_stack(
        [
            audit["station_names_match_M1"].astype(bool),
            audit["sequence_matches_M1"].astype(bool),
            audit["all_finite"].astype(bool),
        ]
    ).astype(float)
    image = ax.imshow(checks, vmin=0, vmax=1, cmap="Blues", aspect="auto")
    for row in range(checks.shape[0]):
        for col in range(checks.shape[1]):
            ax.text(col, row, "PASS" if checks[row, col] else "FAIL", ha="center", va="center", color="white" if checks[row, col] else "#333333", fontsize=8)
    ax.set_yticks(y, audit["model"])
    ax.set_xticks(range(3), ["r1-r606 names", "seq 0-605", "finite samples"], rotation=20, ha="right")
    ax.set_title("Structural comparability")
    ax.grid(False)
    image.set_clim(0, 1)
    fig.suptitle("LV01 | The two new files are structurally comparable, but their longer records require two analysis windows", fontsize=12)
    save_figure(fig, "Figure_LV01_input_audit.png")


def plot_design_matrix() -> None:
    fig, ax = plt.subplots(figsize=(8.4, 5.3), constrained_layout=True)
    ax.set_xlim(-0.62, 1.62)
    ax.set_ylim(-0.58, 1.58)
    cells = {"M2": (0, 0), "M4": (1, 0), "M5": (0, 1), "M6": (1, 1)}
    for name, (x, y) in cells.items():
        ax.scatter(x, y, s=1800, color=MODEL_COLORS[name], alpha=0.18, edgecolor=MODEL_COLORS[name], linewidth=2.0)
        ax.text(x, y + 0.08, name, ha="center", va="center", fontsize=15, fontweight="bold", color=MODEL_COLORS[name])
        ax.text(x, y - 0.10, ("Topo" if x else "Flat") + " / " + ("Low-V" if y else "No low-V"), ha="center", va="center", fontsize=7.5)
    arrow = dict(arrowstyle="->", linewidth=1.5, color="#444444")
    ax.annotate("", xy=(0.84, -0.06), xytext=(0.16, -0.06), arrowprops=arrow)
    ax.text(0.50, -0.20, "Topography effect\nwithout low-V", ha="center", va="top", fontsize=8)
    ax.annotate("", xy=(0.84, 0.94), xytext=(0.16, 0.94), arrowprops=arrow)
    ax.text(0.50, 0.77, "Topography effect\nwith low-V", ha="center", va="top", fontsize=8)
    ax.annotate("", xy=(-0.10, 0.84), xytext=(-0.10, 0.16), arrowprops=arrow)
    ax.text(-0.22, 0.50, "Low-V effect\nflat", ha="right", va="center", fontsize=8)
    ax.annotate("", xy=(1.10, 0.84), xytext=(1.10, 0.16), arrowprops=arrow)
    ax.text(1.22, 0.50, "Low-V effect\ntopography", ha="left", va="center", fontsize=8)
    ax.text(0.5, 1.37, "Interaction = [M6-M5] - [M4-M2]", ha="center", fontsize=10, color="#5B2C6F")
    ax.text(
        0.5,
        -0.43,
        "All four cells contain heterogeneity; identical realization/seed is not verified",
        ha="center",
        fontsize=8.5,
        color="#555555",
    )
    ax.set_xticks([0, 1], ["Flat", "Topography"])
    ax.set_yticks([0, 1], ["No low-V", "Low-V"])
    ax.set_xlabel("Surface factor")
    ax.set_ylabel("Low-velocity factor")
    ax.set_title("LV02 | Identifiable conditional 2 x 2 design")
    ax.grid(False)
    save_figure(fig, "Figure_LV02_identifiable_design.png")


def plot_s12_common_waveforms(records: dict[str, ModelRecord], common_time: np.ndarray) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(12.0, 8.0), sharex=True, constrained_layout=True)
    comparisons = (("M2", "M5", "Flat heterogeneous background"), ("M4", "M6", "Topographic heterogeneous background"))
    for column, (base, low, title) in enumerate(comparisons):
        field_base = records[base].common_zrt[0]
        field_low = records[low].common_zrt[0]
        scale = max(float(np.max(np.abs(field_base))), float(np.max(np.abs(field_low))), EPS)
        for component, label in enumerate(("Z", "R", "T")):
            ax = axes[component, column]
            ax.plot(common_time, field_base[component] / scale, color=MODEL_COLORS[base], label=base)
            ax.plot(common_time, field_low[component] / scale, color=MODEL_COLORS[low], label=low, alpha=0.86)
            ax.set_ylabel(f"{label} / shared 3C scale")
            if component == 0:
                ax.set_title(title)
                ax.legend(loc="upper right")
            if component == 2:
                ax.set_xlabel("Time after impact (s)")
    fig.suptitle("LV03 | S12: the low-velocity models alter phase structure and prolong all three components", fontsize=12)
    save_figure(fig, "Figure_LV03_s12_common_waveforms.png")


def plot_s12_extended(records: dict[str, ModelRecord], extended_time: np.ndarray) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(11.0, 8.5), constrained_layout=True)
    for name in ("M5", "M6"):
        field = records[name].extended_zrt[0]  # type: ignore[index]
        intensity = np.sum(np.abs(hilbert(field, axis=1)) ** 2, axis=0)
        smooth = uniform_filter1d(intensity, max(1, int(round(20.0 / COMMON_DT_S))), mode="nearest")
        axes[0].plot(extended_time, smooth / np.max(smooth), color=MODEL_COLORS[name], label=name)
        cumulative = np.cumsum(intensity) / np.sum(intensity)
        axes[1].plot(extended_time, cumulative, color=MODEL_COLORS[name], label=name)
        for component, label in enumerate(("Z", "R", "T")):
            axes[2].plot(extended_time, uniform_filter1d(np.abs(hilbert(field[component])), 250), color=MODEL_COLORS[name], alpha=0.30 + component * 0.25, linestyle=("-", "--", ":")[component], label=f"{name}-{label}")
    for ax in axes:
        ax.axvline(COMMON_END_S, color="#555555", linestyle="--", linewidth=1.0)
        ax.axvspan(COMMON_END_S, EXTENDED_END_S, color="#999999", alpha=0.08)
        ax.set_xlim(COMMON_START_S, EXTENDED_END_S)
    axes[0].set_ylabel("Normalized 20 s 3C energy")
    axes[0].legend(ncol=2)
    axes[0].set_title("Energy envelope")
    axes[1].set_ylabel("Cumulative recorded energy")
    axes[1].set_ylim(0, 1.02)
    axes[1].set_title("Energy accumulation")
    axes[2].set_yscale("log")
    axes[2].set_ylabel("5 s component envelope")
    axes[2].set_xlabel("Time after impact (s)")
    axes[2].legend(ncol=3, fontsize=7)
    axes[2].set_title("Z/R/T envelopes (log scale)")
    fig.suptitle("LV04 | Much of the S12 low-velocity energy occurs after the old 250 s endpoint", fontsize=12)
    save_figure(fig, "Figure_LV04_s12_extended_energy.png")


def plot_low_effect_distributions(records: dict[str, ModelRecord], geometry: Geometry) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.0), constrained_layout=True)
    panels = (
        ("total_energy", "Energy ratio", True),
        ("peak_amplitude", "Peak-amplitude ratio", True),
        ("T90_s", "T90 ratio", True),
        ("tmax_s", "Peak-energy-time change (s)", False),
    )
    effects = ("low_flat", "low_topography")
    for ax, (metric, label, ratio) in zip(axes.ravel(), panels, strict=True):
        data = []
        for effect in effects:
            values = effect_values(records, effect, metric)[geometry.primary_indices]
            data.append(np.exp(values) if ratio else values)
        violin = ax.violinplot(data, positions=[1, 2], showmedians=True, showextrema=False, widths=0.75)
        for body, color in zip(violin["bodies"], (MODEL_COLORS["M5"], MODEL_COLORS["M6"]), strict=True):
            body.set_facecolor(color)
            body.set_edgecolor(color)
            body.set_alpha(0.35)
        violin["cmedians"].set_color("#222222")
        ax.set_xticks([1, 2], ["M5/M2\nflat", "M6/M4\ntopography"])
        ax.set_ylabel(label)
        ax.axhline(1.0 if ratio else 0.0, color="#555555", linestyle="--")
        if ratio:
            ax.set_yscale("log")
    fig.suptitle("LV05 | Low-velocity effects are dominated by energy accumulation and delay, not uniform peak amplification", fontsize=12)
    save_figure(fig, "Figure_LV05_low_effect_distributions.png")


def plot_low_effect_by_ray(records: dict[str, ModelRecord], geometry: Geometry) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.0, 4.4), constrained_layout=True)
    panels = (("total_energy", "Energy ratio", True), ("T90_s", "T90 ratio", True), ("tmax_s", "Peak-time change (s)", False))
    offsets = (-0.10, 0.10)
    for ax, (metric, ylabel, ratio) in zip(axes, panels, strict=True):
        for effect_index, effect in enumerate(("low_flat", "low_topography")):
            for ray_number, ray in enumerate(geometry.ray_indices, start=1):
                values = effect_values(records, effect, metric)[ray[5:-5]]
                plotted = np.exp(values) if ratio else values
                q25, median, q75 = np.quantile(plotted, (0.25, 0.5, 0.75))
                x = ray_number + offsets[effect_index]
                color = MODEL_COLORS["M5" if effect == "low_flat" else "M6"]
                ax.plot([x, x], [q25, q75], color=color, linewidth=3)
                ax.scatter(x, median, color=color, s=42, zorder=3, marker="o" if effect_index == 0 else "D")
        ax.axhline(1.0 if ratio else 0.0, color="#555555", linestyle="--")
        ax.set_xticks([1, 2, 3], ["Ray 1", "Ray 2", "Ray 3"])
        ax.set_ylabel(ylabel)
        if ratio:
            ax.set_yscale("log")
    handles = [
        Line2D([0], [0], color=MODEL_COLORS["M5"], marker="o", label="M5/M2 flat"),
        Line2D([0], [0], color=MODEL_COLORS["M6"], marker="D", label="M6/M4 topography"),
    ]
    axes[0].legend(handles=handles, fontsize=8)
    fig.suptitle("LV06 | The low-velocity response is strongly path dependent", fontsize=12)
    save_figure(fig, "Figure_LV06_low_effect_by_ray.png")


def plot_component_fractions(records: dict[str, ModelRecord], geometry: Geometry) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.5), constrained_layout=True)
    models = ("M1", "M2", "M3", "M4", "M5", "M6")
    x = np.arange(len(models))
    for component, (metric, label) in enumerate((("Z_fraction", "Z"), ("R_fraction", "R"), ("T_fraction", "T"))):
        ax = axes[component]
        for index, name in enumerate(models):
            values = records[name].common_metrics[metric][geometry.primary_indices]
            q25, med, q75 = np.quantile(values, (0.25, 0.5, 0.75))
            ax.plot([index, index], [q25, q75], color=MODEL_COLORS[name], linewidth=4, alpha=0.75)
            ax.scatter(index, med, color=MODEL_COLORS[name], s=46, zorder=3)
        ax.plot(x, [np.median(records[name].common_metrics[metric][geometry.primary_indices]) for name in models], color="#777777", linewidth=0.8, alpha=0.7)
        ax.set_xticks(x, models)
        ax.set_ylabel(f"{label} energy fraction")
        ax.set_ylim(-0.02, 0.82)
        ax.set_title(f"{label} component")
    fig.suptitle("LV07 | Low-velocity models further redistribute energy from Z into horizontal and transverse motion", fontsize=12)
    save_figure(fig, "Figure_LV07_component_fractions.png")


def plot_t_fraction_effects(records: dict[str, ModelRecord], geometry: Geometry) -> None:
    effects = ("low_flat", "low_topography", "topography_no_low", "topography_low")
    labels = ("Low-V\nflat", "Low-V\ntopography", "Topography\nno low-V", "Topography\nlow-V")
    data = [effect_values(records, effect, "T_fraction")[geometry.primary_indices] * 100.0 for effect in effects]
    fig, ax = plt.subplots(figsize=(10.0, 5.0), constrained_layout=True)
    violin = ax.violinplot(data, positions=np.arange(1, 5), showmedians=True, showextrema=False, widths=0.78)
    colors = (MODEL_COLORS["M5"], MODEL_COLORS["M6"], MODEL_COLORS["M4"], "#5B2C6F")
    for body, color in zip(violin["bodies"], colors, strict=True):
        body.set_facecolor(color)
        body.set_edgecolor(color)
        body.set_alpha(0.35)
    violin["cmedians"].set_color("#222222")
    ax.axhline(0, color="#555555", linestyle="--")
    ax.set_xticks(np.arange(1, 5), labels)
    ax.set_ylabel("Change in T energy fraction (percentage points)")
    ax.set_title("LV08 | Transverse conversion depends on both the surface and the low-velocity background")
    save_figure(fig, "Figure_LV08_transverse_conversion.png")


def plot_factorial_cells(records: dict[str, ModelRecord], geometry: Geometry) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 8.0), constrained_layout=True)
    panels = (("total_energy", "Median energy", True), ("peak_amplitude", "Median peak", True), ("T90_s", "Median T90 (s)", False), ("t50_s", "Median t50 (s)", False))
    for ax, (metric, label, log_y) in zip(axes.ravel(), panels, strict=True):
        for low, models, color, marker in (
            (False, ("M2", "M4"), "#555555", "o"),
            (True, ("M5", "M6"), "#5B2C6F", "D"),
        ):
            medians = [np.median(records[name].common_metrics[metric][geometry.primary_indices]) for name in models]
            ax.plot([0, 1], medians, color=color, marker=marker, markersize=7, label="Low-V" if low else "No low-V")
            for x, name, value in zip((0, 1), models, medians, strict=True):
                ax.text(x, value, f" {name}", va="bottom", fontsize=7.5, color=MODEL_COLORS[name])
        ax.set_xticks([0, 1], ["Flat", "Topography"])
        ax.set_ylabel(label)
        if log_y:
            ax.set_yscale("log")
        ax.legend(fontsize=7.5)
    fig.suptitle(
        "LV09 | Topographic energy effect weakens from amplification to near-neutrality in the low-velocity run",
        fontsize=12,
    )
    save_figure(fig, "Figure_LV09_conditional_factorial_cells.png")


def plot_factorial_cells_from_derived(station_metrics_path: Path) -> None:
    """Rebuild LV09 from the canonical station-metric table only.

    This lightweight path is useful for wording-only figure revisions: it
    preserves the exact primary-station medians without re-filtering all six
    NetCDF files or modifying any derived statistics.
    """
    metrics = pd.read_csv(station_metrics_path)
    primary = metrics[metrics["included_primary"] == 1]
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 8.0), constrained_layout=True)
    panels = (("total_energy", "Median energy", True), ("peak_amplitude", "Median peak", True), ("T90_s", "Median T90 (s)", False), ("t50_s", "Median t50 (s)", False))
    for ax, (metric, label, log_y) in zip(axes.ravel(), panels, strict=True):
        for low, models, color, marker in (
            (False, ("M2", "M4"), "#555555", "o"),
            (True, ("M5", "M6"), "#5B2C6F", "D"),
        ):
            medians = [float(primary.loc[primary["model"] == name, metric].median()) for name in models]
            ax.plot([0, 1], medians, color=color, marker=marker, markersize=7, label="Low-V" if low else "No low-V")
            for x, name, value in zip((0, 1), models, medians, strict=True):
                ax.text(x, value, f" {name}", va="bottom", fontsize=7.5, color=MODEL_COLORS[name])
        ax.set_xticks([0, 1], ["Flat", "Topography"])
        ax.set_ylabel(label)
        if log_y:
            ax.set_yscale("log")
        ax.legend(fontsize=7.5)
    fig.suptitle(
        "LV09 | Topographic energy effect weakens from amplification to near-neutrality in the low-velocity run",
        fontsize=12,
    )
    save_figure(fig, "Figure_LV09_conditional_factorial_cells.png")


def plot_interaction_distributions(records: dict[str, ModelRecord], geometry: Geometry) -> None:
    panels = (
        (("total_energy", "peak_amplitude", "T90_s"), ("ln energy", "ln peak", "ln T90"), "Log-ratio interaction"),
        (("tmax_s", "t50_s", "t95_s"), ("tmax", "t50", "t95"), "Timing interaction (s)"),
        (("Z_fraction", "R_fraction", "T_fraction"), ("Z", "R", "T"), "Component-fraction interaction (percentage points)"),
    )
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.9), constrained_layout=True)
    for ax, (metrics, labels, ylabel) in zip(axes, panels, strict=True):
        data = []
        for metric in metrics:
            interaction = effect_values(records, "topography_low", metric) - effect_values(records, "topography_no_low", metric)
            values = interaction[geometry.primary_indices]
            if metric.endswith("_fraction"):
                values = values * 100.0
            data.append(values)
        violin = ax.violinplot(data, positions=np.arange(1, len(data) + 1), showmedians=True, showextrema=False, widths=0.78)
        for body in violin["bodies"]:
            body.set_facecolor("#5B2C6F")
            body.set_edgecolor("#5B2C6F")
            body.set_alpha(0.32)
        violin["cmedians"].set_color("#222222")
        ax.axhline(0, color="#555555", linestyle="--")
        ax.set_xticks(np.arange(1, len(data) + 1), labels)
        ax.set_ylabel(ylabel)
    fig.suptitle("LV10 | Topography-by-low-velocity interaction is metric-specific rather than uniformly additive", fontsize=12)
    save_figure(fig, "Figure_LV10_interaction_distributions.png")


def plot_effect_persistence(records: dict[str, ModelRecord], geometry: Geometry, correlations: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.3), constrained_layout=True)
    for ax, metric in zip(axes, ("peak_amplitude", "total_energy", "T90_s"), strict=True):
        first = effect_values(records, "topography_no_low", metric)
        second = effect_values(records, "topography_low", metric)
        x, y = detrended_block_pair(first, second, geometry)
        rho_row = correlations[(correlations["relation"] == "topography_signature_no_low_vs_low") & (correlations["metric"] == metric)].iloc[0]
        ax.scatter(x, y, s=24, facecolor="#5B2C6F", edgecolor="white", linewidth=0.4, alpha=0.75)
        ax.axhline(0, color="#777777", linewidth=0.7)
        ax.axvline(0, color="#777777", linewidth=0.7)
        ax.set_xlabel("Topography effect without low-V\n(distance-controlled block score)")
        ax.set_ylabel("Topography effect with low-V")
        ax.set_title(f"{metric.replace('_', ' ')}\nSpearman rho={rho_row.spearman_rho:.2f}, q={rho_row.BH_FDR_q:.2g}")
    fig.suptitle("LV11 | Test of whether the spatial topographic signature survives the low-velocity background", fontsize=12)
    save_figure(fig, "Figure_LV11_topography_signature_persistence.png")


def plot_path_relief_low_effect(records: dict[str, ModelRecord], geometry: Geometry, correlations: pd.DataFrame) -> None:
    path_data = pd.read_csv(DERIVED_DIR / "station_level_metrics.csv")
    relief = np.full(606, np.nan)
    for row in path_data.itertuples():
        index = int(str(row.station)[1:]) - 1
        relief[index] = float(row.path_relief_range_km)
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2), constrained_layout=True)
    for ax, metric in zip(axes, ("peak_amplitude", "total_energy", "T90_s"), strict=True):
        effect = effect_values(records, "topography_low", metric)
        block_relief, block_effect = detrended_block_pair(relief, effect, geometry)
        row = correlations[(correlations["relation"] == "path_predictor_vs_topography_effect_with_low_velocity") & (correlations["predictor"] == "path_relief_range_km") & (correlations["metric"] == metric)].iloc[0]
        ax.scatter(block_relief, block_effect, color="#6C3483", s=25, alpha=0.75)
        ax.axhline(0, color="#777777", linewidth=0.7)
        ax.axvline(0, color="#777777", linewidth=0.7)
        ax.set_xlabel("Path-relief residual block score")
        ax.set_ylabel(f"{metric.replace('_', ' ')} effect")
        ax.set_title(f"rho={row.spearman_rho:.2f}, q={row.BH_FDR_q:.2g}")
    fig.suptitle("LV12 | Path relief is re-tested, rather than assumed to control topography in the low-velocity model", fontsize=12)
    save_figure(fig, "Figure_LV12_path_relief_low_velocity.png")


def plot_distance_tmax(records: dict[str, ModelRecord], geometry: Geometry, fits: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10.5, 9.5), constrained_layout=True)
    for ray_number, ax in enumerate(axes, start=1):
        indices = geometry.fit_indices[ray_number - 1]
        distance = geometry.distance_km[indices]
        for name in ("M5", "M6"):
            tmax_all = records[name].extended_metrics["tmax_s"]  # type: ignore[index]
            t95_all = records[name].extended_metrics["t95_s"]  # type: ignore[index]
            tmax = tmax_all[indices]
            safe = (tmax > COMMON_START_S + 20.0) & (tmax < EXTENDED_END_S - 20.0) & (t95_all[indices] < EXTENDED_END_S - 20.0)
            ax.scatter(distance[safe], tmax[safe], s=10, alpha=0.34, color=MODEL_COLORS[name])
            ax.scatter(distance[~safe], tmax[~safe], s=18, alpha=0.58, facecolor="none", edgecolor=MODEL_COLORS[name], marker="x")
            row = fits[(fits["model"] == name) & (fits["ray"] == ray_number) & (fits["sample_definition"] == "censor_safe")].iloc[0]
            x = np.linspace(distance.min(), distance.max(), 200)
            ax.plot(x, row.linear_intercept_s + row.linear_slope_s_per_km * x, color=MODEL_COLORS[name], label=f"{name} censor-safe: {row.linear_slope_s_per_km:.2f} s/km")
        ax.set_ylabel("Median peak-energy time (s)")
        ax.set_title(f"Ray {ray_number}")
        ax.legend(ncol=2, fontsize=8)
    axes[-1].set_xlabel("Epicentral distance (km)")
    fig.suptitle("LV13 | Low-velocity models slow and disorder peak migration; boundary-affected points are marked x", fontsize=12)
    save_figure(fig, "Figure_LV13_low_velocity_tmax_distance.png")


def plot_fit_comparison(fits: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 8.0), constrained_layout=True)
    for column, sample in enumerate(("all_primary", "censor_safe")):
        for model_index, name in enumerate(("M5", "M6")):
            subset = fits[(fits["model"] == name) & (fits["sample_definition"] == sample)].sort_values("ray")
            x = np.arange(1, 4) + (model_index - 0.5) * 0.08
            axes[0, column].plot(x, subset["linear_rmse_s"], marker="o", color=MODEL_COLORS[name], label=f"{name} linear")
            axes[0, column].plot(x, subset["squared_rmse_s"], marker="x", linestyle="--", color=MODEL_COLORS[name], label=f"{name} R-squared")
            axes[1, column].plot(x, subset["delta_aic_squared_minus_linear"], marker="o", color=MODEL_COLORS[name], label=name)
        axes[0, column].set_title("All primary stations" if sample == "all_primary" else "Censor-safe sensitivity sample")
        axes[0, column].set_xticks([1, 2, 3], ["Ray 1", "Ray 2", "Ray 3"])
        axes[0, column].set_ylabel("RMSE (s)")
        axes[0, column].legend(fontsize=7.1, ncol=2)
        axes[1, column].set_xticks([1, 2, 3], ["Ray 1", "Ray 2", "Ray 3"])
        axes[1, column].axhline(0, color="#555555", linestyle="--")
        axes[1, column].set_ylabel("Delta AIC: R-squared minus linear")
        axes[1, column].legend(fontsize=7.5)
    fig.suptitle("LV14 | Linear distance remains preferred in both full and censor-safe 400 s-window fits", fontsize=12)
    save_figure(fig, "Figure_LV14_linear_vs_diffusion.png")


def plot_similarity(similarity: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), constrained_layout=True)
    for effect, color, label in (("low_flat", MODEL_COLORS["M5"], "M5 vs M2"), ("low_topography", MODEL_COLORS["M6"], "M6 vs M4")):
        subset = similarity[similarity["effect"] == effect]
        for metric, linestyle in (("zero_lag_3c_correlation", "-"), ("best_5s_envelope_correlation_within_10s", "--")):
            x, y = ecdf(subset[metric].to_numpy(float))
            axes[0].plot(x, y, color=color, linestyle=linestyle, label=f"{label}; {'waveform' if metric.startswith('zero') else 'envelope'}")
        axes[1].scatter(subset["zero_lag_3c_correlation"], subset["best_5s_envelope_correlation_within_10s"], s=9, alpha=0.28, color=color, label=label)
    axes[0].set_xlabel("Correlation")
    axes[0].set_ylabel("Empirical cumulative fraction")
    axes[0].legend(fontsize=7.3)
    axes[1].axvline(0, color="#777777", linewidth=0.7)
    axes[1].axhline(0, color="#777777", linewidth=0.7)
    axes[1].set_xlabel("Zero-lag three-component waveform correlation")
    axes[1].set_ylabel("Best 5 s-envelope correlation (±10 s)")
    axes[1].legend(fontsize=8)
    fig.suptitle("LV15 | Low-velocity models can preserve envelope evolution while changing waveform phase", fontsize=12)
    save_figure(fig, "Figure_LV15_waveform_envelope_similarity.png")


def plot_representatives(records: dict[str, ModelRecord], geometry: Geometry, common_time: np.ndarray, selected: dict[str, int]) -> None:
    keys = ("median_low_energy_effect", "high_low_velocity_delay", "strong_topography_low_interaction", "ray2_100km")
    fig, axes = plt.subplots(len(keys), 2, figsize=(12.0, 10.5), sharex=True, constrained_layout=True)
    for row_index, key in enumerate(keys):
        station = selected[key]
        for column, (base, low, title) in enumerate((("M2", "M5", "Flat"), ("M4", "M6", "Topography"))):
            ax = axes[row_index, column]
            first = records[base].common_zrt[station]
            second = records[low].common_zrt[station]
            scale = max(np.max(np.abs(first)), np.max(np.abs(second)), EPS)
            for component, linestyle in enumerate(("-", "--", ":")):
                ax.plot(common_time, first[component] / scale, color=MODEL_COLORS[base], linestyle=linestyle, alpha=0.65)
                ax.plot(common_time, second[component] / scale, color=MODEL_COLORS[low], linestyle=linestyle, alpha=0.85)
            ax.set_title(f"{key.replace('_', ' ')} | {title}: {base}->{low}\n{geometry.station_names[station]}, R={geometry.distance_km[station]:.1f} km", fontsize=8.7)
            ax.set_ylabel("Shared scale")
    for ax in axes[-1]:
        ax.set_xlabel("Time (s)")
    legend = [
        Line2D([0], [0], color="#444444", linestyle="-", label="Z"),
        Line2D([0], [0], color="#444444", linestyle="--", label="R"),
        Line2D([0], [0], color="#444444", linestyle=":", label="T"),
    ]
    axes[0, 0].legend(handles=legend, ncol=3, fontsize=7.5)
    fig.suptitle("LV16 | Data-selected representative stations confirm that medians are not caused by one trace", fontsize=12)
    save_figure(fig, "Figure_LV16_representative_station_atlas.png")


def plot_observed_six_models(observed: ObservedRecord, records: dict[str, ModelRecord]) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(11.5, 9.5), constrained_layout=True)
    obs_intensity = np.sum(np.abs(hilbert(observed.zen, axis=1)) ** 2, axis=0)
    obs_smooth = uniform_filter1d(obs_intensity, max(1, int(round(20.0 / np.median(np.diff(observed.time))))), mode="nearest")
    reference = max(float(np.max(obs_smooth[(observed.time >= 50) & (observed.time <= 1000)])), EPS)
    axes[0].plot(observed.time, obs_smooth / reference, color="#222222", label="Observed", linewidth=1.4)
    cumulative_obs = np.cumsum(obs_intensity) / np.sum(obs_intensity)
    axes[1].plot(observed.time, cumulative_obs, color="#222222", label="Observed", linewidth=1.4)
    axes[2].plot(observed.time, obs_smooth / reference, color="#222222", label="Observed", linewidth=1.4)
    for name, record in records.items():
        scale = source_scale(observed, record)
        intensity = np.sum(np.abs(hilbert(record.s12_zen * scale, axis=1)) ** 2, axis=0)
        smooth = uniform_filter1d(intensity, max(1, int(round(20.0 / np.median(np.diff(record.s12_time))))), mode="nearest")
        axes[0].plot(record.s12_time, smooth / reference, color=MODEL_COLORS[name], label=name, alpha=0.85)
        axes[1].plot(record.s12_time, np.cumsum(intensity) / np.sum(intensity), color=MODEL_COLORS[name], label=name, alpha=0.85)
        axes[2].plot(record.s12_time, smooth / reference, color=MODEL_COLORS[name], label=name, alpha=0.85)
    axes[0].set_xlim(50, 1000)
    axes[0].set_yscale("log")
    axes[0].set_ylabel("20 s energy / observed peak")
    axes[0].set_title("Envelope amplitude after one shared 3C source scale")
    axes[0].legend(ncol=4, fontsize=7.5)
    axes[1].set_xlim(50, 3000)
    axes[1].set_ylim(0, 1.02)
    axes[1].set_ylabel("Fraction of each available record")
    axes[1].set_title("Recorded-energy accumulation (different endpoints are explicit)")
    axes[2].set_xlim(50, 400)
    axes[2].set_ylabel("20 s energy / observed peak")
    axes[2].set_xlabel("Time after impact (s)")
    axes[2].set_title("Early-window zoom")
    fig.suptitle("LV17 | Low-velocity models move the early envelope toward Apollo but remain far too short", fontsize=12)
    save_figure(fig, "Figure_LV17_observed_six_model_envelopes.png")


def plot_observed_metrics(table: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(14.0, 4.5), constrained_layout=True)
    records = table["record"].tolist()
    y = np.arange(len(records))
    colors = ["#222222" if value.startswith("Observed") else MODEL_COLORS[value] for value in records]
    panels = (
        ("tmax_median_s", "Peak-energy time (s)"),
        ("t95_s", "Recorded-energy t95 (s)"),
        ("early_envelope_correlation_best_lag", "Early envelope correlation"),
        ("early_3c_waveform_correlation", "Early 3C waveform correlation"),
    )
    for ax, (column, title) in zip(axes, panels, strict=True):
        values = table[column].to_numpy(float)
        ax.scatter(values, y, c=colors, s=48)
        ax.set_yticks(y, records if ax is axes[0] else [])
        ax.set_xlabel(title)
        if "correlation" in column:
            ax.axvline(0, color="#777777", linestyle="--")
        if column in ("tmax_median_s", "t95_s"):
            ax.set_xscale("log")
    fig.suptitle("LV18 | Improved envelope timing does not remove the Apollo duration and phase gap", fontsize=12)
    save_figure(fig, "Figure_LV18_observed_metric_comparison.png")


def plot_time_frequency(observed: ObservedRecord, records: dict[str, ModelRecord]) -> None:
    entries: list[tuple[str, np.ndarray, np.ndarray, float]] = []
    observed_time = np.arange(50.0, 1_000.0 + COMMON_DT_S / 2, COMMON_DT_S)
    observed_z = np.interp(observed_time, observed.time, observed.zrt[0])
    entries.append(("Observed A16S12", observed_time, observed_z, 1000.0))
    entries.append(("M4", np.arange(50.0, 245.0 + COMMON_DT_S / 2, COMMON_DT_S), records["M4"].common_zrt[0, 0], 245.0))
    for name in ("M5", "M6"):
        entries.append((name, np.arange(50.0, 395.0 + COMMON_DT_S / 2, COMMON_DT_S), records[name].extended_zrt[0, 0], 395.0))  # type: ignore[index]
    fig, axes = plt.subplots(4, 1, figsize=(11.0, 10.5), constrained_layout=True)
    for ax, (name, time, trace, end) in zip(axes, entries, strict=True):
        nperseg = int(round(20.0 / COMMON_DT_S))
        noverlap = int(round(18.0 / COMMON_DT_S))
        frequency, segment_time, power = spectrogram(trace, fs=1.0 / COMMON_DT_S, window="hann", nperseg=nperseg, noverlap=noverlap, mode="psd")
        keep = (frequency >= 0.2) & (frequency <= 1.2)
        db = 10 * np.log10(np.maximum(power[keep], EPS))
        db -= np.max(db)
        mesh = ax.pcolormesh(time[0] + segment_time, frequency[keep], db, shading="auto", cmap="magma", vmin=-40, vmax=0)
        ax.set_ylim(0.2, 1.2)
        ax.set_xlim(50, end)
        ax.set_ylabel("Hz")
        ax.set_title(name, loc="left")
    axes[-1].set_xlabel("Time after impact (s)")
    fig.colorbar(mesh, ax=axes, label="Power relative to panel maximum (dB)", shrink=0.75)
    fig.suptitle("LV19 | Low-velocity models shift and prolong spectral energy but do not reproduce the Apollo time-frequency extent", fontsize=12)
    save_figure(fig, "Figure_LV19_time_frequency.png")


def plot_tail_censoring(extended: pd.DataFrame) -> None:
    primary = extended[extended["included_primary"] == 1]
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.4), constrained_layout=True)
    for name in ("M5", "M6"):
        subset = primary[primary["model"] == name]
        for ax, column, label in (
            (axes[0], "energy_fraction_245_395s", "Energy fraction after 245 s"),
            (axes[1], "t95_s", "t95 (s)"),
            (axes[2], "terminal_20s_fraction", "Final 20 s energy fraction"),
        ):
            x, y = ecdf(subset[column].to_numpy(float))
            ax.plot(x, y, color=MODEL_COLORS[name], label=name)
            ax.set_xlabel(label)
            ax.set_ylabel("Empirical cumulative fraction")
    axes[1].axvline(375.0, color="#777777", linestyle="--", label="within 20 s of analysis end")
    axes[1].axvline(395.0, color="#222222", linestyle=":")
    axes[0].legend()
    axes[1].legend(fontsize=7.5)
    fig.suptitle("LV20 | The 400 s records improve coverage but still right-censor a substantial subset", fontsize=12)
    save_figure(fig, "Figure_LV20_tail_censoring.png")


def plot_low_delay_distance(records: dict[str, ModelRecord], geometry: Geometry) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10.0, 9.0), constrained_layout=True)
    for ray_number, (ax, ray) in enumerate(zip(axes, geometry.ray_indices, strict=True), start=1):
        indices = ray[5:-5]
        for effect, color, label in (("low_flat", MODEL_COLORS["M5"], "M5-M2"), ("low_topography", MODEL_COLORS["M6"], "M6-M4")):
            delta = effect_values(records, effect, "tmax_s")[indices]
            x, y = smooth_profile(geometry.distance_km[indices], delta, 11)
            ax.scatter(geometry.distance_km[indices], delta, s=7, color=color, alpha=0.18)
            ax.plot(x, y, color=color, label=label)
        ax.axhline(0, color="#777777", linestyle="--")
        ax.set_ylabel("Common-window tmax change (s)")
        ax.set_title(f"Ray {ray_number}")
        ax.legend()
    axes[-1].set_xlabel("Epicentral distance (km)")
    fig.suptitle("LV21 | Low-velocity delay is distance-structured, nonmonotonic, and path dependent", fontsize=12)
    save_figure(fig, "Figure_LV21_low_velocity_delay_distance.png")


def plot_effect_forest(summary: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.3, 5.4), constrained_layout=True)
    ratio_metrics = ("total_energy", "peak_amplitude", "T90_s")
    time_metrics = ("tmax_s", "t50_s")
    for effect_index, effect in enumerate(("low_flat", "low_topography")):
        color = MODEL_COLORS["M5" if effect == "low_flat" else "M6"]
        offset = (-0.08, 0.08)[effect_index]
        for metric_index, metric in enumerate(ratio_metrics):
            row = summary[(summary["effect"] == effect) & (summary["metric"] == metric)].iloc[0]
            y = metric_index + offset
            axes[0].plot([row.ratio_bootstrap95_low, row.ratio_bootstrap95_high], [y, y], color=color, linewidth=3)
            axes[0].scatter(row.ratio_median, y, color=color, s=45)
        for metric_index, metric in enumerate(time_metrics):
            row = summary[(summary["effect"] == effect) & (summary["metric"] == metric)].iloc[0]
            y = metric_index + offset
            axes[1].plot([row.bootstrap95_low, row.bootstrap95_high], [y, y], color=color, linewidth=3)
            axes[1].scatter(row["median"], y, color=color, s=45)
        row = summary[(summary["effect"] == effect) & (summary["metric"] == "T_fraction")].iloc[0]
        axes[2].plot([row.bootstrap95_low * 100.0, row.bootstrap95_high * 100.0], [effect_index, effect_index], color=color, linewidth=3)
        axes[2].scatter(row["median"] * 100.0, effect_index, color=color, s=45)
    axes[0].axvline(1, color="#777777", linestyle="--")
    axes[0].set_xscale("log")
    axes[0].set_yticks(range(3), ["Total energy", "Peak amplitude", "T90"])
    axes[0].set_xlabel("Median factor with spatial-block 95% interval")
    axes[1].axvline(0, color="#777777", linestyle="--")
    axes[1].set_yticks(range(2), ["tmax", "t50"])
    axes[1].set_xlabel("Median change with spatial-block 95% interval")
    axes[1].set_ylabel("Timing metric (s)")
    axes[2].axvline(0, color="#777777", linestyle="--")
    axes[2].set_yticks([0, 1], ["M5/M2 flat", "M6/M4 topography"])
    axes[2].set_xlabel("T-fraction change (percentage points)\nwith spatial-block 95% interval")
    handles = [Line2D([0], [0], color=MODEL_COLORS["M5"], marker="o", label="M5/M2 flat"), Line2D([0], [0], color=MODEL_COLORS["M6"], marker="o", label="M6/M4 topography")]
    axes[0].legend(handles=handles, fontsize=8)
    fig.suptitle("LV22 | Spatial-block uncertainty confirms which low-velocity effects are robust", fontsize=12)
    save_figure(fig, "Figure_LV22_effect_forest.png")


def plot_component_profiles(records: dict[str, ModelRecord], geometry: Geometry) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10.5, 9.0), constrained_layout=True)
    for ray_number, (ax, ray) in enumerate(zip(axes, geometry.ray_indices, strict=True), start=1):
        indices = ray[5:-5]
        for name in ("M2", "M4", "M5", "M6"):
            distance, smooth = smooth_profile(geometry.distance_km[indices], records[name].common_metrics["T_fraction"][indices], 11)
            ax.plot(distance, smooth, color=MODEL_COLORS[name], label=name)
        ax.set_ylabel("T energy fraction")
        ax.set_title(f"Ray {ray_number}")
        ax.set_ylim(-0.02, 0.75)
        ax.legend(ncol=4, fontsize=7.5)
    axes[-1].set_xlabel("Epicentral distance (km)")
    fig.suptitle("LV23 | Transverse conversion remains spatially heterogeneous in the low-velocity models", fontsize=12)
    save_figure(fig, "Figure_LV23_transverse_fraction_profiles.png")


def plot_common_extended(records: dict[str, ModelRecord], geometry: Geometry) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.6), constrained_layout=True)
    panels = (("tmax_s", "Median tmax (s)"), ("t95_s", "Median t95 (s)"), ("T90_s", "Median T90 (s)"))
    for ax, (metric, label) in zip(axes, panels, strict=True):
        for index, name in enumerate(("M5", "M6")):
            common = np.median(records[name].common_metrics[metric][geometry.primary_indices])
            extended = np.median(records[name].extended_metrics[metric][geometry.primary_indices])  # type: ignore[index]
            x = np.array([0, 1]) + (index - 0.5) * 0.06
            ax.plot(x, [common, extended], color=MODEL_COLORS[name], marker="o", label=name)
            vertical = 8 if index == 0 else -13
            ax.annotate(f"{common:.1f}", (x[0], common), xytext=(0, vertical), textcoords="offset points", ha="center", fontsize=7.3)
            ax.annotate(f"{extended:.1f}", (x[1], extended), xytext=(0, vertical), textcoords="offset points", ha="center", fontsize=7.3)
        ax.set_xticks([0, 1], ["50-245 s", "50-395 s"])
        ax.set_ylabel(label)
        ax.legend()
    fig.suptitle("LV24 | Peak and duration timing estimates depend on the available low-velocity record window", fontsize=12)
    save_figure(fig, "Figure_LV24_common_vs_extended.png")


def write_evidence_index(
    summary: pd.DataFrame,
    extended: pd.DataFrame,
    observed_table: pd.DataFrame,
    fits: pd.DataFrame,
    correlations: pd.DataFrame,
) -> pd.DataFrame:
    def effect_row(effect: str, metric: str) -> pd.Series:
        return summary[(summary["effect"] == effect) & (summary["metric"] == metric)].iloc[0]

    low_flat_energy = effect_row("low_flat", "total_energy")
    low_topo_energy = effect_row("low_topography", "total_energy")
    low_flat_t90 = effect_row("low_flat", "T90_s")
    low_topo_t90 = effect_row("low_topography", "T90_s")
    low_flat_tmax = effect_row("low_flat", "tmax_s")
    low_topo_tmax = effect_row("low_topography", "tmax_s")
    topo_no_low_energy = effect_row("topography_no_low", "total_energy")
    topo_low_energy = effect_row("topography_low", "total_energy")
    ext_primary = extended[extended["included_primary"] == 1]
    ext_m5 = ext_primary[ext_primary["model"] == "M5"]
    ext_m6 = ext_primary[ext_primary["model"] == "M6"]
    obs = observed_table.iloc[0]
    m5 = observed_table[observed_table["record"] == "M5"].iloc[0]
    m6 = observed_table[observed_table["record"] == "M6"].iloc[0]
    fit_min = fits.loc[fits["sample_definition"] == "all_primary", "delta_aic_squared_minus_linear"].min()
    fit_min_safe = fits.loc[fits["sample_definition"] == "censor_safe", "delta_aic_squared_minus_linear"].min()
    persistence = correlations[(correlations["relation"] == "topography_signature_no_low_vs_low") & (correlations["metric"] == "total_energy")].iloc[0]
    persistence_t90 = correlations[(correlations["relation"] == "topography_signature_no_low_vs_low") & (correlations["metric"] == "T90_s")].iloc[0]
    rows = [
        ("LV01", "Input files are structurally aligned but have unequal record lengths", "positive", "Figure_LV01_input_audit.png", "All six files contain the same r1-r606 sequence and finite Vx/Vy/Vz samples; M5-M6 extend to 400 s, so 50-245 s and 50-395 s have different inferential roles."),
        ("LV02", "Only a heterogeneity-present topography x low-velocity conditional design is identifiable", "exclusion", "Figure_LV02_identifiable_design.png", "M2/M4/M5/M6 identify four conditional contrasts; missing low-velocity/no-heterogeneity cells and unverified random seeds prevent a complete three-factor interaction."),
        ("LV03", "Low velocity changes S12 phase structure across Z, R, and T", "positive", "Figure_LV03_s12_common_waveforms.png", "Shared-scale S12 traces show that the change is not a scalar amplitude correction."),
        ("LV04", "A large fraction of low-velocity S12 energy lies after 245 s", "positive", "Figure_LV04_s12_extended_energy.png", f"The low-velocity S12 records continue accumulating energy through the extended window; M5 and M6 t95 are {m5.t95_s:.1f} and {m6.t95_s:.1f} s."),
        ("LV05", "The low-velocity runs increase integrated energy, duration, and delay", "conditional", "Figure_LV05_low_effect_distributions.png", f"Spatial-block median energy factors are {low_flat_energy.ratio_median:.2f} (flat) and {low_topo_energy.ratio_median:.2f} (topography), while T90 factors are {low_flat_t90.ratio_median:.2f} and {low_topo_t90.ratio_median:.2f}; absolute amplitude/energy attribution assumes unchanged source and run settings."),
        ("LV06", "The low-velocity effect is path dependent", "positive", "Figure_LV06_low_effect_by_ray.png", "Ray-specific medians differ substantially; a single global multiplier would hide propagation-direction dependence."),
        ("LV07", "Low velocity further redistributes energy among Z, R, and T", "positive", "Figure_LV07_component_fractions.png", "The new models reduce median Z fraction and increase horizontal/transverse fractions relative to their M2/M4 baselines."),
        ("LV08", "Transverse conversion is background dependent", "positive", "Figure_LV08_transverse_conversion.png", "T-fraction changes differ between flat and topographic backgrounds and cannot be represented by a universal conversion factor."),
        ("LV09", "The marginal topographic effect changes across the low-velocity runs", "conditional", "Figure_LV09_conditional_factorial_cells.png", f"The spatial-block median topographic energy factor changes from {topo_no_low_energy.ratio_median:.2f} without low velocity to {topo_low_energy.ratio_median:.2f} with low velocity; causal attribution remains conditional on unverified run equivalence."),
        ("LV10", "Topography-by-low-velocity interaction is metric-specific and mixed", "positive", "Figure_LV10_interaction_distributions.png", "Interactions are supported for selected amplitude, energy, timing, late-energy and T-fraction metrics, while T90, tmax, t95, Z and R intervals include zero; the effect is not uniformly nonadditive."),
        ("LV11", "Peak and energy topographic fingerprints are retained more clearly than T90", "positive", "Figure_LV11_topography_signature_persistence.png", f"Distance-controlled block correlation for total-energy topographic effects is rho={persistence.spearman_rho:.2f} (q={persistence.BH_FDR_q:.2g}), whereas T90 is not significant (q={persistence_t90.BH_FDR_q:.2g})."),
        ("LV12", "Path relief must be re-evaluated in the low-velocity background", "positive", "Figure_LV12_path_relief_low_velocity.png", "The report tests the relationship directly rather than importing the no-low-velocity result."),
        ("LV13", "Low-velocity runs slow and disorder energy-peak migration within the 400 s window", "positive", "Figure_LV13_low_velocity_tmax_distance.png", f"Spatial-block median common-window tmax shifts are {low_flat_tmax['median']:.1f} s and {low_topo_tmax['median']:.1f} s; boundary-affected stations are explicitly marked and excluded in sensitivity slopes."),
        ("LV14", "The main energy ridge remains closer to linear distance than R-squared diffusion", "exclusion", "Figure_LV14_linear_vs_diffusion.png", f"All ray-model fits prefer the linear form in the full and censor-safe samples; minimum Delta AIC favoring linear is {fit_min:.1f} and {fit_min_safe:.1f}, respectively. These are descriptive 400 s-window tests."),
        ("LV15", "Envelope similarity can improve while waveform phase remains poor", "positive", "Figure_LV15_waveform_envelope_similarity.png", "Zero-lag three-component correlation and lag-tolerant energy-envelope correlation measure different properties and are reported together."),
        ("LV16", "Data-selected traces verify the distribution-level effects", "positive", "Figure_LV16_representative_station_atlas.png", "Representative stations are selected by effect quantiles and matched distance, not by visual preference."),
        ("LV17", "Low velocity moves the early S12 envelope toward Apollo but does not reproduce the long coda", "positive", "Figure_LV17_observed_six_model_envelopes.png", f"M5/M6 peak-energy times ({m5.tmax_median_s:.1f}/{m6.tmax_median_s:.1f} s) are later than M1-M4 but remain far earlier than the observed {obs.tmax_median_s:.1f} s."),
        ("LV18", "Timing improvement does not solve the phase and duration mismatch", "exclusion", "Figure_LV18_observed_metric_comparison.png", f"M5/M6 early 3C waveform correlations are {m5.early_3c_waveform_correlation:.3f}/{m6.early_3c_waveform_correlation:.3f}; observed t95 is {obs.t95_s:.1f} s."),
        ("LV19", "The low-velocity time-frequency pattern remains much shorter than Apollo", "exclusion", "Figure_LV19_time_frequency.png", "Low-velocity synthetics prolong band-limited energy to 400 s, whereas observed energy remains strong over much longer times."),
        ("LV20", "Some 400 s low-velocity metrics remain right censored", "uncertain", "Figure_LV20_tail_censoring.png", f"Primary stations with t95 in the final 20 s: M5={int(ext_m5.t95_within_20s_of_end.sum())}, M6={int(ext_m6.t95_within_20s_of_end.sum())}."),
        ("LV21", "Low-velocity delay is distance-structured, nonmonotonic, and path dependent", "positive", "Figure_LV21_low_velocity_delay_distance.png", "The delay grows, saturates or declines over different distance intervals and rays, ruling out one constant static correction."),
        ("LV22", "Spatial-block intervals separate robust effects from unstable medians", "positive", "Figure_LV22_effect_forest.png", "Bootstrap intervals use 57 nonoverlapping 10-station spatial blocks rather than treating 575 neighboring stations as independent."),
        ("LV23", "Transverse conversion varies systematically along the three profiles", "positive", "Figure_LV23_transverse_fraction_profiles.png", "M5/M6 T-fraction profiles show that conversion is spatially structured rather than a single model-wide percentage."),
        ("LV24", "Low-velocity peak and duration timing estimates depend strongly on the available window", "exclusion", "Figure_LV24_common_vs_extended.png", "Cross-model effects use 50-245 s; extended tmax/t95/T90 values are reported separately and flagged near the 395 s boundary."),
    ]
    frame = pd.DataFrame(rows, columns=("conclusion_id", "title", "evidence_class", "figure_file", "takeaway"))
    frame["figure_path"] = frame["figure_file"].map(lambda value: str(FIGURE_DIR / value))
    frame.to_csv(DERIVED_DIR / "low_velocity_conclusion_evidence_index.csv", index=False, encoding="utf-8-sig")
    return frame


def write_summary_json(
    records: dict[str, ModelRecord],
    geometry: Geometry,
    audit: pd.DataFrame,
    model_summary: pd.DataFrame,
    effect_summary: pd.DataFrame,
    interaction: pd.DataFrame,
    correlations: pd.DataFrame,
    fits: pd.DataFrame,
    extended: pd.DataFrame,
    observed_table: pd.DataFrame,
    evidence: pd.DataFrame,
    representatives: dict[str, int],
) -> dict[str, object]:
    def table_records(frame: pd.DataFrame) -> list[dict[str, object]]:
        clean = frame.replace({np.nan: None})
        return json.loads(clean.to_json(orient="records"))

    payload: dict[str, object] = {
        "analysis_version": "2026-08-20.2",
        "processing": {
            "filter": "fourth-order 0.3-0.9 Hz Butterworth, zero phase",
            "pre_filter": "linear detrend at native sampling",
            "common_window_s": [COMMON_START_S, COMMON_END_S],
            "extended_low_velocity_window_s": [COMMON_START_S, EXTENDED_END_S],
            "common_interpolation_dt_s": COMMON_DT_S,
            "primary_station_count": int(geometry.primary_indices.size),
            "spatial_block_count": len(geometry.blocks),
            "cumulative_energy_time_definition": "cumulative sum of three-component squared filtered velocity; T90=t95-t05, matching REL3 and half-space workflows",
            "peak_energy_time_definition": "median tmax over multiple smoothing windows applied to three-component analytic-signal intensity",
            "inferential_estimator": "median of 57 nonoverlapping 10-station block medians, with block bootstrap and Wilcoxon on the same block medians",
            "receiver_geometry": "REL3 606-station geometry reconstructed by the validated generator; Vx/Vy rotated to R/T at each station",
        },
        "identifiability": {
            "available": ["M5/M2", "M6/M4", "M6/M5", "M4/M2", "(M6-M5)-(M4-M2)"],
            "unavailable": ["low-velocity effect without heterogeneity", "low-velocity x heterogeneity interaction", "full topography x heterogeneity x low-velocity interaction"],
            "manifest_limit": "M5/M6 project folders contain station.nc only; exact low-velocity parameters, source identity, Q, grid, and random seed are not encoded in the files.",
        },
        "input_audit": table_records(audit.drop(columns=[])),
        "model_summary": table_records(model_summary),
        "effect_summary": table_records(effect_summary),
        "interaction_summary": table_records(interaction),
        "correlations": table_records(correlations),
        "distance_fits": table_records(fits),
        "extended_summary": {
            name: {
                column: median_iqr(
                    extended[(extended["model"] == name) & (extended["included_primary"] == 1)][column].to_numpy(float)
                )
                for column in ("energy_fraction_245_395s", "terminal_20s_fraction", "t95_s", "T90_s", "tmax_s")
            }
            for name in ("M5", "M6")
        },
        "observed_model_comparison": table_records(observed_table),
        "evidence_index": table_records(evidence),
        "representative_stations": {
            key: {
                "station_index_zero_based": value,
                "station": geometry.station_names[value],
                "ray": "S12" if value == 0 else int(geometry.ray_number[value]),
                "distance_km": float(geometry.distance_km[value]),
                "selection_role": key,
            }
            for key, value in representatives.items()
        },
        "quality_flags": {
            "all_input_checks_pass": bool(audit[["station_names_match_M1", "sequence_matches_M1", "all_finite"]].astype(bool).all().all()),
            "right_censor_threshold_s": EXTENDED_END_S - 20.0,
            "distance_fit_sensitivity": "censor_safe excludes tmax within 20 s of either analysis boundary and t95 within 20 s of the 395 s endpoint",
            "old_theoretical_low_layer_figure_is_not_new_data": True,
        },
    }
    output = DERIVED_DIR / "low_velocity_analysis_summary.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def write_provenance_note(audit: pd.DataFrame) -> None:
    rows = [
        "# Low-velocity simulation input audit",
        "",
        "The two user-supplied project folders contain only `output/station.nc`. The data have been copied into `jgr_planets_submission/data/raw/` and verified by SHA-256.",
        "",
        "## Confirmed from the files",
        "",
        "- NETCDF4 files with r1-r606, seq_no 0-605, Vx/Vy/Vz, and finite samples.",
        "- M5 uses the same station/time prefix as M2; M6 uses the same station/time prefix as M4.",
        "- M5/M6 extend to approximately 400 s; M1-M4 end at approximately 250 s.",
        "- The validated REL3 station generator is therefore used for coordinates and per-station R/T rotation.",
        "- Cumulative-energy times use squared three-component filtered velocity, matching REL3 and half-space definitions; T90=t95-t05.",
        "- Inferential effect estimates use the same 57 spatial-block medians for the point estimate, bootstrap interval, and Wilcoxon test; station-level medians are retained as descriptive fields.",
        "",
        "## Not recoverable from the supplied folders",
        "",
        "- Low-velocity-layer thickness, Vp, Vs, density, Q, and whether the layer follows topography.",
        "- Random-medium strength, correlation length, realization/seed, and whether heterogeneity occupies the low-velocity layer.",
        "- Exact source file, source normalization, grid spacing, boundary settings, and run command.",
        "",
        "The older REL3 figure describing a 1 km candidate layer is a theoretical diagnostic and is not treated as metadata for M5/M6.",
        "",
        "## Checksums",
        "",
    ]
    for row in audit.itertuples():
        rows.append(f"- {row.model}: `{row.sha256}` ({int(row.size_bytes):,} bytes)")
    (PROVENANCE_DIR / "LOW_VELOCITY_DATA_AUDIT.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def validate_outputs(evidence: pd.DataFrame, derived_files: list[Path]) -> None:
    missing_figures = [Path(path) for path in evidence["figure_path"] if not Path(path).is_file()]
    missing_derived = [path for path in derived_files if not path.is_file() or path.stat().st_size == 0]
    if missing_figures or missing_derived:
        raise RuntimeError(f"Missing outputs: figures={missing_figures}; derived={missing_derived}")
    for path in evidence["figure_path"]:
        if Path(path).stat().st_size < 40_000:
            raise RuntimeError(f"Suspiciously small figure: {path}")
    if evidence["conclusion_id"].duplicated().any():
        raise RuntimeError("Duplicate conclusion IDs")


def main() -> None:
    configure_plot_style()
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)
    for name, path in MODEL_FILES.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing {name}: {path}")
    for name, path in OBSERVED_FILES.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing observed {name}: {path}")

    geometry = build_station_geometry()
    common_time = np.arange(COMMON_START_S, COMMON_END_S + COMMON_DT_S / 2, COMMON_DT_S)
    extended_time = np.arange(COMMON_START_S, EXTENDED_END_S + COMMON_DT_S / 2, COMMON_DT_S)
    records: dict[str, ModelRecord] = {}
    for name in MODEL_FILES:
        print(f"Loading and filtering {name}: {MODEL_FILES[name]}", flush=True)
        records[name] = load_model(name, geometry, common_time, extended_time)
    observed = load_observed(geometry)

    audit = input_audit(records)
    audit.to_csv(PROVENANCE_DIR / "low_velocity_input_audit.csv", index=False, encoding="utf-8-sig")
    write_provenance_note(audit)
    model_summary = summarize_models(records, geometry)
    model_summary.to_csv(DERIVED_DIR / "low_velocity_model_summary.csv", index=False, encoding="utf-8-sig")
    station_metrics = metrics_long_table(records, geometry)
    station_metrics.to_csv(DERIVED_DIR / "low_velocity_station_metrics.csv", index=False, encoding="utf-8-sig")
    effects_long = effects_long_table(records, geometry)
    effects_long.to_csv(DERIVED_DIR / "low_velocity_effect_station_metrics.csv", index=False, encoding="utf-8-sig")
    effect_summary = summarize_effects(records, geometry)
    effect_summary.to_csv(DERIVED_DIR / "low_velocity_effect_summary.csv", index=False, encoding="utf-8-sig")
    ray_summary = per_ray_summary(records, geometry)
    ray_summary.to_csv(DERIVED_DIR / "low_velocity_effect_summary_by_ray.csv", index=False, encoding="utf-8-sig")
    interaction = interaction_table(records, geometry)
    interaction.to_csv(DERIVED_DIR / "low_velocity_interaction_summary.csv", index=False, encoding="utf-8-sig")
    correlations = correlation_tables(records, geometry)
    correlations.to_csv(DERIVED_DIR / "low_velocity_spatial_relationships.csv", index=False, encoding="utf-8-sig")
    similarity = waveform_similarity_table(records, geometry)
    similarity.to_csv(DERIVED_DIR / "low_velocity_waveform_similarity.csv", index=False, encoding="utf-8-sig")
    fits = distance_fit_table(records, geometry)
    fits.to_csv(DERIVED_DIR / "low_velocity_time_distance_fits.csv", index=False, encoding="utf-8-sig")
    extended = extended_summary(records, geometry)
    extended.to_csv(DERIVED_DIR / "low_velocity_extended_window_metrics.csv", index=False, encoding="utf-8-sig")
    observed_table = observed_model_table(observed, records)
    observed_table.to_csv(DERIVED_DIR / "A16S12_observed_six_model_comparison_metrics.csv", index=False, encoding="utf-8-sig")
    representatives = choose_representative_stations(records, geometry)
    (DERIVED_DIR / "low_velocity_representative_stations.json").write_text(
        json.dumps(representatives, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("Generating 24 low-velocity evidence figures", flush=True)
    plot_input_audit(audit)
    plot_design_matrix()
    plot_s12_common_waveforms(records, common_time)
    plot_s12_extended(records, extended_time)
    plot_low_effect_distributions(records, geometry)
    plot_low_effect_by_ray(records, geometry)
    plot_component_fractions(records, geometry)
    plot_t_fraction_effects(records, geometry)
    plot_factorial_cells(records, geometry)
    plot_interaction_distributions(records, geometry)
    plot_effect_persistence(records, geometry, correlations)
    plot_path_relief_low_effect(records, geometry, correlations)
    plot_distance_tmax(records, geometry, fits)
    plot_fit_comparison(fits)
    plot_similarity(similarity)
    plot_representatives(records, geometry, common_time, representatives)
    plot_observed_six_models(observed, records)
    plot_observed_metrics(observed_table)
    plot_time_frequency(observed, records)
    plot_tail_censoring(extended)
    plot_low_delay_distance(records, geometry)
    plot_effect_forest(effect_summary)
    plot_component_profiles(records, geometry)
    plot_common_extended(records, geometry)

    evidence = write_evidence_index(effect_summary, extended, observed_table, fits, correlations)
    write_summary_json(
        records,
        geometry,
        audit,
        model_summary,
        effect_summary,
        interaction,
        correlations,
        fits,
        extended,
        observed_table,
        evidence,
        representatives,
    )
    derived_files = [
        DERIVED_DIR / "low_velocity_analysis_summary.json",
        DERIVED_DIR / "low_velocity_model_summary.csv",
        DERIVED_DIR / "low_velocity_station_metrics.csv",
        DERIVED_DIR / "low_velocity_effect_station_metrics.csv",
        DERIVED_DIR / "low_velocity_effect_summary.csv",
        DERIVED_DIR / "low_velocity_effect_summary_by_ray.csv",
        DERIVED_DIR / "low_velocity_interaction_summary.csv",
        DERIVED_DIR / "low_velocity_spatial_relationships.csv",
        DERIVED_DIR / "low_velocity_waveform_similarity.csv",
        DERIVED_DIR / "low_velocity_time_distance_fits.csv",
        DERIVED_DIR / "low_velocity_extended_window_metrics.csv",
        DERIVED_DIR / "A16S12_observed_six_model_comparison_metrics.csv",
        DERIVED_DIR / "low_velocity_conclusion_evidence_index.csv",
        PROVENANCE_DIR / "low_velocity_input_audit.csv",
        PROVENANCE_DIR / "LOW_VELOCITY_DATA_AUDIT.md",
    ]
    validate_outputs(evidence, derived_files)
    print(f"Completed. Figures: {FIGURE_DIR}")
    print(f"Summary: {DERIVED_DIR / 'low_velocity_analysis_summary.json'}")


if __name__ == "__main__":
    if "--figure-lv09-from-derived" in sys.argv:
        configure_plot_style()
        FIGURE_DIR.mkdir(parents=True, exist_ok=True)
        plot_factorial_cells_from_derived(DERIVED_DIR / "low_velocity_station_metrics.csv")
        print(f"Updated {FIGURE_DIR / 'Figure_LV09_conditional_factorial_cells.png'}")
    else:
        main()
