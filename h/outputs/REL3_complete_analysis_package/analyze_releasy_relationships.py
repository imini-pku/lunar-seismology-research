"""Factorial analysis of topography and scattering effects on CGFD3D waveforms."""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
LOCAL_PACKAGES = SCRIPT_DIR.parent / "work" / "python_pkgs"
if LOCAL_PACKAGES.is_dir():
    sys.path.insert(0, str(LOCAL_PACKAGES))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset
from scipy.signal import butter, sosfiltfilt
from scipy.stats import spearmanr

from plot_releasy_waveform_comparison import (
    EARTHQUAKE_SOURCE_XY,
    MODELS,
    TOPOGRAPHY_FILE,
    build_station_geometry,
    load_topography,
    sample_topography,
)


OUTPUT_DIR = SCRIPT_DIR / "releasy_relationship_analysis"
FILTER_LOW_HZ = 0.3
FILTER_HIGH_HZ = 0.9
FILTER_ORDER = 4
TRIM_STATIONS_PER_RAY_END = 5
ROUGHNESS_WINDOW_STATIONS = 11
SPATIAL_BLOCK_STATIONS = 10
EPSILON = 1.0e-30

PAIR_DEFINITIONS = {
    "scatter_flat": (0, 1),
    "scatter_topography": (2, 3),
    "topography_no_scatter": (0, 2),
    "topography_scatter": (1, 3),
}

PAIR_LABELS = {
    "scatter_flat": "Scatter effect, flat",
    "scatter_topography": "Scatter effect, topography",
    "topography_no_scatter": "Topography effect, no scatter",
    "topography_scatter": "Topography effect, scatter",
    "interaction": "Topography × scatter interaction",
}

PAIR_COLORS = {
    "scatter_flat": "#D55E00",
    "scatter_topography": "#CC79A7",
    "topography_no_scatter": "#0072B2",
    "topography_scatter": "#009E73",
    "interaction": "#333333",
}

MODEL_SHORT_NAMES = ("M1", "M2", "M3", "M4")


@dataclass
class AnalysisModel:
    name: str
    color: str
    time: np.ndarray
    filtered: np.ndarray
    dominant_frequency_hz: np.ndarray


def load_analysis_model(model_index: int) -> AnalysisModel:
    config = MODELS[model_index]
    with Dataset(config.nc_file, "r") as dataset:
        time = np.asarray(dataset.variables["time"][:], dtype=np.float64)
        raw = np.asarray(dataset.variables["Vz"][:], dtype=np.float32)
    if raw.shape == (time.size, 606):
        raw = raw.T
    if raw.shape != (606, time.size):
        raise ValueError(f"Unexpected Vz shape {raw.shape} in {config.nc_file}")

    sample_interval = float(np.median(np.diff(time)))
    sample_rate = 1.0 / sample_interval
    demeaned = raw - raw.mean(axis=1, keepdims=True)
    spectrum = np.abs(np.fft.rfft(demeaned, axis=1))
    frequency = np.fft.rfftfreq(time.size, sample_interval)
    spectrum[:, 0] = 0.0
    dominant_frequency = frequency[np.argmax(spectrum, axis=1)]

    sos = butter(
        FILTER_ORDER,
        (FILTER_LOW_HZ, FILTER_HIGH_HZ),
        btype="bandpass",
        fs=sample_rate,
        output="sos",
    )
    filtered = sosfiltfilt(sos, raw, axis=1).astype(np.float32)
    return AnalysisModel(
        name=config.name,
        color=config.color,
        time=time,
        filtered=filtered,
        dominant_frequency_hz=dominant_frequency,
    )


def waveform_metrics(model: AnalysisModel) -> dict[str, np.ndarray]:
    waveform = model.filtered
    time = model.time
    sample_interval = float(np.median(np.diff(time)))
    absolute = np.abs(waveform)
    peak_index = np.argmax(absolute, axis=1)
    peak_time = time[peak_index]
    peak_amplitude = absolute[np.arange(606), peak_index]
    energy_samples = waveform * waveform
    total_energy = energy_samples.sum(axis=1) * sample_interval
    rms = np.sqrt(np.mean(energy_samples, axis=1))

    cumulative = np.cumsum(energy_samples, axis=1)
    cumulative /= np.maximum(cumulative[:, -1:], EPSILON)
    index_05 = np.argmax(cumulative >= 0.05, axis=1)
    index_95 = np.argmax(cumulative >= 0.95, axis=1)
    duration_90 = time[index_95] - time[index_05]

    coda_fraction = np.empty(606, dtype=np.float64)
    for station_index in range(606):
        coda_start_time = peak_time[station_index] + 15.0
        coda_start = int(np.searchsorted(time, coda_start_time))
        coda_energy = energy_samples[station_index, coda_start:].sum()
        coda_fraction[station_index] = coda_energy / max(
            float(energy_samples[station_index].sum()), EPSILON
        )

    return {
        "peak_time_s": peak_time,
        "log_peak_amplitude": np.log(np.maximum(peak_amplitude, EPSILON)),
        "log_total_energy": np.log(np.maximum(total_energy, EPSILON)),
        "log_rms": np.log(np.maximum(rms, EPSILON)),
        "log_duration_90_s": np.log(np.maximum(duration_90, sample_interval)),
        "coda_fraction": coda_fraction,
        "dominant_frequency_hz": model.dominant_frequency_hz,
    }


def aligned_waveform_correlation(
    first: AnalysisModel, second: AnalysisModel
) -> np.ndarray:
    start_time = max(float(first.time[0]), float(second.time[0]))
    end_time = min(float(first.time[-1]), float(second.time[-1]))
    sample_interval = max(
        float(np.median(np.diff(first.time))),
        float(np.median(np.diff(second.time))),
    )
    common_time = np.arange(start_time, end_time + 0.5 * sample_interval, sample_interval)
    correlation = np.empty(606, dtype=np.float64)
    for station_index in range(606):
        first_trace = np.interp(
            common_time, first.time, first.filtered[station_index]
        )
        second_trace = np.interp(
            common_time, second.time, second.filtered[station_index]
        )
        first_trace -= first_trace.mean()
        second_trace -= second_trace.mean()
        denominator = np.linalg.norm(first_trace) * np.linalg.norm(second_trace)
        correlation[station_index] = (
            np.dot(first_trace, second_trace) / denominator
            if denominator > 0.0
            else np.nan
        )
    return correlation


def rolling_standard_deviation(values: np.ndarray, window: int) -> np.ndarray:
    kernel = np.ones(window, dtype=np.float64)
    finite = np.isfinite(values)
    count = np.convolve(finite.astype(float), kernel, mode="same")
    sum_value = np.convolve(np.where(finite, values, 0.0), kernel, mode="same")
    sum_square = np.convolve(
        np.where(finite, values * values, 0.0), kernel, mode="same"
    )
    mean = sum_value / np.maximum(count, 1.0)
    variance = sum_square / np.maximum(count, 1.0) - mean * mean
    result = np.sqrt(np.maximum(variance, 0.0))
    result[count == 0.0] = np.nan
    return result


def build_station_features(
    station_xy: np.ndarray,
    ray_station_indices: tuple[np.ndarray, ...],
) -> dict[str, np.ndarray]:
    epicentral_distance = np.linalg.norm(
        station_xy - EARTHQUAKE_SOURCE_XY, axis=1
    ) / 1000.0
    elevation = sample_topography(load_topography(), station_xy)
    ray_number = np.zeros(606, dtype=int)
    slope_abs = np.full(606, np.nan)
    roughness = np.full(606, np.nan)
    path_mean_elevation = np.full(606, np.nan)
    path_mean_abs_slope = np.full(606, np.nan)
    path_relief_range = np.full(606, np.nan)
    trim_mask = np.zeros(606, dtype=bool)

    for current_ray, indices in enumerate(ray_station_indices, start=1):
        ray_number[indices] = current_ray
        distance = epicentral_distance[indices]
        terrain = elevation[indices]
        slope = np.abs(np.gradient(terrain, distance))
        slope_abs[indices] = slope
        roughness[indices] = rolling_standard_deviation(
            terrain, ROUGHNESS_WINDOW_STATIONS
        )
        path_mean_elevation[indices] = np.cumsum(terrain) / np.arange(
            1, indices.size + 1
        )
        path_mean_abs_slope[indices] = np.cumsum(slope) / np.arange(
            1, indices.size + 1
        )
        path_relief_range[indices] = np.maximum.accumulate(
            terrain
        ) - np.minimum.accumulate(terrain)
        trim_mask[
            indices[
                TRIM_STATIONS_PER_RAY_END : -TRIM_STATIONS_PER_RAY_END
            ]
        ] = True

    return {
        "ray": ray_number,
        "distance_km": epicentral_distance,
        "elevation_km": elevation,
        "absolute_slope": slope_abs,
        "roughness_11km": roughness,
        "path_mean_elevation_km": path_mean_elevation,
        "path_mean_absolute_slope": path_mean_abs_slope,
        "path_relief_range_km": path_relief_range,
        "trim_mask": trim_mask,
    }


def build_effect_metrics(
    model_metrics: tuple[dict[str, np.ndarray], ...],
    models: tuple[AnalysisModel, ...],
) -> dict[str, np.ndarray]:
    effects: dict[str, np.ndarray] = {}
    metric_names = tuple(model_metrics[0].keys())
    for pair_name, (first_index, second_index) in PAIR_DEFINITIONS.items():
        for metric_name in metric_names:
            effects[f"{pair_name}__{metric_name}"] = (
                model_metrics[second_index][metric_name]
                - model_metrics[first_index][metric_name]
            )
        correlation = aligned_waveform_correlation(
            models[first_index], models[second_index]
        )
        effects[f"{pair_name}__waveform_dissimilarity"] = 1.0 - correlation

    for metric_name in metric_names:
        effects[f"interaction__{metric_name}"] = (
            model_metrics[3][metric_name]
            - model_metrics[2][metric_name]
            - model_metrics[1][metric_name]
            + model_metrics[0][metric_name]
        )
    return effects


def residualize_by_ray(
    values: np.ndarray,
    distance: np.ndarray,
    ray_number: np.ndarray,
    mask: np.ndarray,
    polynomial_degree: int = 3,
) -> np.ndarray:
    residual = np.full(values.shape, np.nan, dtype=np.float64)
    for current_ray in (1, 2, 3):
        indices = np.where(
            mask
            & (ray_number == current_ray)
            & np.isfinite(values)
            & np.isfinite(distance)
        )[0]
        if indices.size < 8:
            continue
        degree = min(polynomial_degree, indices.size - 2)
        coefficients = np.polyfit(distance[indices], values[indices], degree)
        residual[indices] = values[indices] - np.polyval(
            coefficients, distance[indices]
        )
    return residual


def standardize_by_ray(
    values: np.ndarray,
    ray_number: np.ndarray,
) -> np.ndarray:
    standardized = np.full(values.shape, np.nan, dtype=np.float64)
    for current_ray in (1, 2, 3):
        indices = np.where(
            (ray_number == current_ray) & np.isfinite(values)
        )[0]
        if indices.size < 2:
            continue
        standard_deviation = float(np.std(values[indices], ddof=1))
        if standard_deviation <= 0.0:
            continue
        standardized[indices] = (
            values[indices] - np.mean(values[indices])
        ) / standard_deviation
    return standardized


def spatial_block_means(
    predictor: np.ndarray,
    outcome: np.ndarray,
    ray_number: np.ndarray,
    mask: np.ndarray,
    block_size: int = SPATIAL_BLOCK_STATIONS,
) -> tuple[np.ndarray, np.ndarray]:
    predictor_blocks: list[float] = []
    outcome_blocks: list[float] = []
    for current_ray in (1, 2, 3):
        indices = np.where(
            mask
            & (ray_number == current_ray)
            & np.isfinite(predictor)
            & np.isfinite(outcome)
        )[0]
        for start in range(0, indices.size, block_size):
            block = indices[start : start + block_size]
            if block.size < block_size // 2:
                continue
            predictor_blocks.append(float(np.mean(predictor[block])))
            outcome_blocks.append(float(np.mean(outcome[block])))
    return np.asarray(predictor_blocks), np.asarray(outcome_blocks)


def benjamini_hochberg(p_values: np.ndarray) -> np.ndarray:
    count = p_values.size
    order = np.argsort(p_values)
    ordered = p_values[order]
    adjusted = ordered * count / np.arange(1, count + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    result = np.empty(count, dtype=np.float64)
    result[order] = np.clip(adjusted, 0.0, 1.0)
    return result


def compute_relationship_statistics(
    effects: dict[str, np.ndarray],
    features: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    predictor_names = (
        "elevation_km",
        "absolute_slope",
        "roughness_11km",
        "path_mean_elevation_km",
        "path_mean_absolute_slope",
        "path_relief_range_km",
    )
    distance = features["distance_km"]
    ray_number = features["ray"]
    trimmed = features["trim_mask"]
    records: list[dict[str, object]] = []

    for outcome_name, outcome in effects.items():
        outcome_residual = standardize_by_ray(
            residualize_by_ray(outcome, distance, ray_number, trimmed),
            ray_number,
        )
        for predictor_name in predictor_names:
            predictor = features[predictor_name]
            predictor_residual = standardize_by_ray(
                residualize_by_ray(predictor, distance, ray_number, trimmed),
                ray_number,
            )
            valid = np.isfinite(outcome_residual) & np.isfinite(predictor_residual)
            if valid.sum() < 20:
                continue
            point_rho, point_p_value = spearmanr(
                predictor_residual[valid], outcome_residual[valid]
            )
            block_predictor, block_outcome = spatial_block_means(
                predictor_residual,
                outcome_residual,
                ray_number,
                trimmed,
            )
            rho, p_value = spearmanr(block_predictor, block_outcome)
            untrimmed_mask = ray_number > 0
            untrimmed_outcome = standardize_by_ray(
                residualize_by_ray(
                    outcome, distance, ray_number, untrimmed_mask
                ),
                ray_number,
            )
            untrimmed_predictor = standardize_by_ray(
                residualize_by_ray(
                    predictor, distance, ray_number, untrimmed_mask
                ),
                ray_number,
            )
            untrimmed_valid = np.isfinite(untrimmed_outcome) & np.isfinite(
                untrimmed_predictor
            )
            untrimmed_rho = spearmanr(
                untrimmed_predictor[untrimmed_valid],
                untrimmed_outcome[untrimmed_valid],
            ).statistic
            ray_rho: list[float] = []
            for current_ray in (1, 2, 3):
                ray_valid = valid & (ray_number == current_ray)
                if ray_valid.sum() >= 8:
                    ray_rho.append(
                        float(
                            spearmanr(
                                predictor_residual[ray_valid],
                                outcome_residual[ray_valid],
                            ).statistic
                        )
                    )
                else:
                    ray_rho.append(np.nan)
            records.append(
                {
                    "outcome": outcome_name,
                    "predictor": predictor_name,
                    "rho": float(rho),
                    "p_value": float(p_value),
                    "block_n": int(block_predictor.size),
                    "point_rho": float(point_rho),
                    "point_p_value": float(point_p_value),
                    "point_n": int(valid.sum()),
                    "untrimmed_rho": float(untrimmed_rho),
                    "ray1_rho": ray_rho[0],
                    "ray2_rho": ray_rho[1],
                    "ray3_rho": ray_rho[2],
                    "outcome_residual": outcome_residual,
                    "predictor_residual": predictor_residual,
                }
            )

    q_values = benjamini_hochberg(
        np.asarray([record["p_value"] for record in records], dtype=float)
    )
    for record, q_value in zip(records, q_values, strict=True):
        record["q_value"] = float(q_value)
        sign = np.sign(record["rho"])
        ray_values = np.asarray(
            [record["ray1_rho"], record["ray2_rho"], record["ray3_rho"]],
            dtype=float,
        )
        record["consistent_ray_count"] = int(
            np.sum(np.sign(ray_values[np.isfinite(ray_values)]) == sign)
        )
        record["trim_sign_stable"] = bool(
            np.sign(record["rho"]) == np.sign(record["untrimmed_rho"])
        )
    return records


def write_wide_station_table(
    features: dict[str, np.ndarray],
    model_metrics: tuple[dict[str, np.ndarray], ...],
    effects: dict[str, np.ndarray],
) -> None:
    feature_names = tuple(
        name for name in features if name not in {"trim_mask", "ray"}
    )
    model_metric_columns = [
        (f"{MODEL_SHORT_NAMES[index]}__{metric_name}", metric_values)
        for index, metrics in enumerate(model_metrics)
        for metric_name, metric_values in metrics.items()
    ]
    effect_columns = list(effects.items())
    output_file = OUTPUT_DIR / "station_level_metrics.csv"
    with output_file.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "station",
                "ray",
                "included_in_primary_analysis",
                *feature_names,
                *[name for name, _ in model_metric_columns],
                *[name for name, _ in effect_columns],
            ]
        )
        for station_index in range(606):
            writer.writerow(
                [
                    f"r{station_index + 1}",
                    "S12" if station_index == 0 else features["ray"][station_index],
                    int(features["trim_mask"][station_index]),
                    *[
                        f"{features[name][station_index]:.9g}"
                        for name in feature_names
                    ],
                    *[
                        f"{values[station_index]:.9g}"
                        for _, values in model_metric_columns
                    ],
                    *[
                        f"{values[station_index]:.9g}"
                        for _, values in effect_columns
                    ],
                ]
            )


def write_relationship_table(records: list[dict[str, object]]) -> None:
    columns = (
        "outcome",
        "predictor",
        "rho",
        "p_value",
        "q_value",
        "block_n",
        "point_rho",
        "point_p_value",
        "point_n",
        "untrimmed_rho",
        "ray1_rho",
        "ray2_rho",
        "ray3_rho",
        "consistent_ray_count",
        "trim_sign_stable",
    )
    output_file = OUTPUT_DIR / "distance_controlled_relationships.csv"
    with output_file.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def write_effect_summary_by_ray(
    effects: dict[str, np.ndarray],
    features: dict[str, np.ndarray],
) -> None:
    metrics = (
        "peak_time_s",
        "log_peak_amplitude",
        "log_total_energy",
        "log_duration_90_s",
        "coda_fraction",
        "dominant_frequency_hz",
        "waveform_dissimilarity",
    )
    output_file = OUTPUT_DIR / "factorial_effect_summary_by_ray.csv"
    columns = (
        "comparison",
        "metric",
        "ray",
        "station_count",
        "median",
        "q25",
        "q75",
    )
    with output_file.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for comparison in (*PAIR_DEFINITIONS.keys(), "interaction"):
            for metric in metrics:
                effect_key = f"{comparison}__{metric}"
                if effect_key not in effects:
                    continue
                for ray in (1, 2, 3):
                    mask = features["trim_mask"] & (features["ray"] == ray)
                    values = effects[effect_key][mask]
                    values = values[np.isfinite(values)]
                    writer.writerow(
                        {
                            "comparison": comparison,
                            "metric": metric,
                            "ray": ray,
                            "station_count": values.size,
                            "median": float(np.median(values)),
                            "q25": float(np.percentile(values, 25)),
                            "q75": float(np.percentile(values, 75)),
                        }
                    )


def compute_robustness_sensitivity(
    records: list[dict[str, object]],
    effects: dict[str, np.ndarray],
    features: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    selected = []
    used_outcomes: set[str] = set()
    for record in sorted(records, key=lambda item: -abs(item["rho"])):
        if record["outcome"] in used_outcomes:
            continue
        selected.append(record)
        used_outcomes.add(record["outcome"])
        if len(selected) == 18:
            break

    variants = tuple(
        (degree, block_size)
        for degree in (2, 3, 4)
        for block_size in (5, 10, 20)
    )
    distance = features["distance_km"]
    ray_number = features["ray"]
    trimmed = features["trim_mask"]
    sensitivity_records: list[dict[str, object]] = []
    for record in selected:
        outcome = effects[record["outcome"]]
        predictor = features[record["predictor"]]
        rho_values = []
        variant_values: dict[str, float] = {}
        for degree, block_size in variants:
            outcome_residual = standardize_by_ray(
                residualize_by_ray(
                    outcome,
                    distance,
                    ray_number,
                    trimmed,
                    polynomial_degree=degree,
                ),
                ray_number,
            )
            predictor_residual = standardize_by_ray(
                residualize_by_ray(
                    predictor,
                    distance,
                    ray_number,
                    trimmed,
                    polynomial_degree=degree,
                ),
                ray_number,
            )
            block_predictor, block_outcome = spatial_block_means(
                predictor_residual,
                outcome_residual,
                ray_number,
                trimmed,
                block_size=block_size,
            )
            rho = float(spearmanr(block_predictor, block_outcome).statistic)
            rho_values.append(rho)
            variant_values[f"degree{degree}_block{block_size}"] = rho
        rho_array = np.asarray(rho_values)
        primary_sign = np.sign(record["rho"])
        sensitivity_records.append(
            {
                "outcome": record["outcome"],
                "predictor": record["predictor"],
                "primary_rho": record["rho"],
                "median_rho": float(np.nanmedian(rho_array)),
                "minimum_rho": float(np.nanmin(rho_array)),
                "maximum_rho": float(np.nanmax(rho_array)),
                "same_sign_variants": int(
                    np.sum(np.sign(rho_array) == primary_sign)
                ),
                "variants": variant_values,
            }
        )
    return sensitivity_records


def write_robustness_table(records: list[dict[str, object]]) -> None:
    variant_names = tuple(records[0]["variants"].keys())
    columns = (
        "outcome",
        "predictor",
        "primary_rho",
        "median_rho",
        "minimum_rho",
        "maximum_rho",
        "same_sign_variants",
        *variant_names,
    )
    output_file = OUTPUT_DIR / "robustness_sensitivity.csv"
    with output_file.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for record in records:
            row = {key: value for key, value in record.items() if key != "variants"}
            row.update(record["variants"])
            writer.writerow(row)


def plot_robustness_sensitivity(records: list[dict[str, object]]) -> None:
    variant_names = tuple(records[0]["variants"].keys())
    matrix = np.asarray(
        [
            [record["variants"][variant] for variant in variant_names]
            for record in records
        ]
    )
    fig, axis = plt.subplots(
        figsize=(12.5, max(7.5, 0.47 * len(records))),
        constrained_layout=True,
    )
    image = axis.imshow(
        matrix,
        aspect="auto",
        cmap="coolwarm",
        vmin=-0.8,
        vmax=0.8,
    )
    axis.set_xticks(np.arange(len(variant_names)))
    axis.set_xticklabels(
        [
            name.replace("degree", "poly ").replace("_block", ", block ")
            + " stations"
            for name in variant_names
        ],
        rotation=35,
        ha="right",
    )
    axis.set_yticks(np.arange(len(records)))
    axis.set_yticklabels(
        [
            f"{record['outcome'].replace('__', ' / ')} vs "
            f"{record['predictor']}"
            for record in records
        ],
        fontsize=7,
    )
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            axis.text(
                column,
                row,
                f"{matrix[row, column]:.2f}",
                ha="center",
                va="center",
                fontsize=6,
                color="white" if abs(matrix[row, column]) > 0.45 else "black",
            )
    axis.set_title(
        "Sensitivity to distance-trend degree and spatial-block scale"
    )
    fig.colorbar(image, ax=axis, label="Spearman rho")
    fig.savefig(
        OUTPUT_DIR / "analysis_robustness_sensitivity.png",
        dpi=230,
        bbox_inches="tight",
    )
    plt.close(fig)


def smooth_profile(values: np.ndarray, window: int = 9) -> np.ndarray:
    kernel = np.ones(window, dtype=float)
    finite = np.isfinite(values)
    numerator = np.convolve(np.where(finite, values, 0.0), kernel, mode="same")
    denominator = np.convolve(finite.astype(float), kernel, mode="same")
    result = numerator / np.maximum(denominator, 1.0)
    result[denominator == 0.0] = np.nan
    return result


def plot_effect_profiles(
    effects: dict[str, np.ndarray],
    features: dict[str, np.ndarray],
    ray_station_indices: tuple[np.ndarray, ...],
) -> None:
    profile_metrics = (
        (
            "peak_time_s",
            "Arrival-time effect (s)",
            tuple(PAIR_DEFINITIONS) + ("interaction",),
        ),
        (
            "log_peak_amplitude",
            "Log peak-amplitude ratio",
            tuple(PAIR_DEFINITIONS) + ("interaction",),
        ),
        (
            "waveform_dissimilarity",
            "Waveform dissimilarity (1-r)",
            tuple(PAIR_DEFINITIONS),
        ),
    )
    fig, axes = plt.subplots(3, 3, figsize=(17, 12), constrained_layout=True)
    distance = features["distance_km"]
    for row_index, indices in enumerate(ray_station_indices):
        for column_index, (metric, ylabel, comparisons) in enumerate(
            profile_metrics
        ):
            axis = axes[row_index, column_index]
            for comparison in comparisons:
                key = f"{comparison}__{metric}"
                if key not in effects:
                    continue
                values = effects[key][indices]
                axis.plot(
                    distance[indices],
                    values,
                    color=PAIR_COLORS[comparison],
                    alpha=0.16,
                    linewidth=0.7,
                )
                axis.plot(
                    distance[indices],
                    smooth_profile(values),
                    color=PAIR_COLORS[comparison],
                    linewidth=1.5,
                    label=PAIR_LABELS[comparison],
                )
            axis.axhline(0.0, color="black", linewidth=0.7, alpha=0.7)
            axis.set_title(f"Ray {row_index + 1}")
            axis.set_xlabel("Epicentral distance (km)")
            axis.set_ylabel(ylabel)
            axis.grid(alpha=0.25)
            if row_index == 0:
                axis.legend(fontsize=7)
    fig.suptitle(
        "Distance profiles of topography, scattering, and interaction effects",
        fontsize=15,
    )
    fig.savefig(
        OUTPUT_DIR / "analysis_effect_profiles.png",
        dpi=230,
        bbox_inches="tight",
    )
    plt.close(fig)


def plot_relationship_heatmap(records: list[dict[str, object]]) -> None:
    predictor_names = (
        "elevation_km",
        "absolute_slope",
        "roughness_11km",
        "path_mean_elevation_km",
        "path_mean_absolute_slope",
        "path_relief_range_km",
    )
    metric_order = (
        "peak_time_s",
        "log_peak_amplitude",
        "log_total_energy",
        "log_duration_90_s",
        "coda_fraction",
        "dominant_frequency_hz",
        "waveform_dissimilarity",
    )
    outcome_names = []
    for comparison in (*PAIR_DEFINITIONS.keys(), "interaction"):
        for metric in metric_order:
            outcome = f"{comparison}__{metric}"
            if any(record["outcome"] == outcome for record in records):
                outcome_names.append(outcome)

    lookup = {
        (record["outcome"], record["predictor"]): record for record in records
    }
    matrix = np.full((len(outcome_names), len(predictor_names)), np.nan)
    significant = np.zeros_like(matrix, dtype=bool)
    for row, outcome in enumerate(outcome_names):
        for column, predictor in enumerate(predictor_names):
            record = lookup.get((outcome, predictor))
            if record is None:
                continue
            matrix[row, column] = record["rho"]
            significant[row, column] = record["q_value"] < 0.05

    fig_height = max(10.0, 0.30 * len(outcome_names))
    fig, axis = plt.subplots(figsize=(11.5, fig_height), constrained_layout=True)
    image = axis.imshow(
        matrix,
        aspect="auto",
        cmap="coolwarm",
        vmin=-0.65,
        vmax=0.65,
    )
    axis.set_xticks(np.arange(len(predictor_names)))
    axis.set_xticklabels(
        (
            "Elevation",
            "|Slope|",
            "Local roughness",
            "Path mean elevation",
            "Path mean |slope|",
            "Path relief range",
        ),
        rotation=30,
        ha="right",
    )
    axis.set_yticks(np.arange(len(outcome_names)))
    axis.set_yticklabels(
        [name.replace("__", " / ").replace("_", " ") for name in outcome_names],
        fontsize=7,
    )
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            if np.isfinite(matrix[row, column]):
                marker = "*" if significant[row, column] else ""
                axis.text(
                    column,
                    row,
                    f"{matrix[row, column]:.2f}{marker}",
                    ha="center",
                    va="center",
                    fontsize=6,
                    color=(
                        "white"
                        if abs(matrix[row, column]) > 0.42
                        else "black"
                    ),
                )
    axis.set_title(
        "Distance-controlled Spearman relationships with terrain (* FDR q<0.05)"
    )
    fig.colorbar(image, ax=axis, label="Spearman rho")
    fig.savefig(
        OUTPUT_DIR / "analysis_terrain_relationship_heatmap.png",
        dpi=230,
        bbox_inches="tight",
    )
    plt.close(fig)


def select_top_relationships(
    records: list[dict[str, object]], count: int = 6
) -> list[dict[str, object]]:
    candidates = sorted(
        records,
        key=lambda record: (
            record["q_value"] >= 0.05,
            -abs(record["rho"]),
        ),
    )
    selected: list[dict[str, object]] = []
    used_outcomes: set[str] = set()
    for record in candidates:
        if record["outcome"] in used_outcomes:
            continue
        selected.append(record)
        used_outcomes.add(record["outcome"])
        if len(selected) == count:
            break
    return selected


def plot_top_relationships(
    records: list[dict[str, object]], features: dict[str, np.ndarray]
) -> None:
    selected = select_top_relationships(records)
    fig, axes = plt.subplots(2, 3, figsize=(16, 9.5), constrained_layout=True)
    ray_number = features["ray"]
    ray_colors = ("#0072B2", "#D55E00", "#009E73")
    for axis, record in zip(axes.ravel(), selected, strict=True):
        x_values = record["predictor_residual"]
        y_values = record["outcome_residual"]
        for current_ray, color in zip((1, 2, 3), ray_colors, strict=True):
            valid = (
                (ray_number == current_ray)
                & np.isfinite(x_values)
                & np.isfinite(y_values)
            )
            axis.scatter(
                x_values[valid],
                y_values[valid],
                s=10,
                alpha=0.46,
                color=color,
                label=f"Ray {current_ray}",
            )
        valid = np.isfinite(x_values) & np.isfinite(y_values)
        if valid.sum() >= 10:
            coefficients = np.polyfit(x_values[valid], y_values[valid], 1)
            line_x = np.linspace(
                np.nanpercentile(x_values[valid], 1),
                np.nanpercentile(x_values[valid], 99),
                100,
            )
            axis.plot(
                line_x,
                np.polyval(coefficients, line_x),
                color="black",
                linewidth=1.2,
            )
        axis.axhline(0.0, color="gray", linewidth=0.6)
        axis.axvline(0.0, color="gray", linewidth=0.6)
        axis.set_xlabel(
            record["predictor"].replace("_", " ") + " residual"
        )
        axis.set_ylabel(record["outcome"].replace("__", " / ") + " residual")
        axis.set_title(
            f"rho={record['rho']:.2f}, q={record['q_value']:.2g}, "
            f"rays consistent={record['consistent_ray_count']}/3"
        )
        axis.grid(alpha=0.22)
        axis.legend(fontsize=7)
    fig.suptitle(
        "Strongest terrain relationships after removing distance trends",
        fontsize=15,
    )
    fig.savefig(
        OUTPUT_DIR / "analysis_top_terrain_relationships.png",
        dpi=230,
        bbox_inches="tight",
    )
    plt.close(fig)


def plot_dominant_frequency_profiles(
    models: tuple[AnalysisModel, ...],
    features: dict[str, np.ndarray],
    ray_station_indices: tuple[np.ndarray, ...],
) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(16.5, 11), constrained_layout=True)
    distance = features["distance_km"]
    elevation = features["elevation_km"]
    for row, indices in enumerate(ray_station_indices):
        frequency_axis = axes[row, 0]
        terrain_axis = axes[row, 1]
        for model in models:
            frequency_axis.plot(
                distance[indices],
                model.dominant_frequency_hz[indices],
                color=model.color,
                linewidth=1.0,
                marker="o",
                markersize=2.2,
                label=model.name,
            )
        frequency_axis.set_title(f"Ray {row + 1}: raw-waveform dominant frequency")
        frequency_axis.set_xlabel("Epicentral distance (km)")
        frequency_axis.set_ylabel("Dominant frequency (Hz)")
        frequency_axis.grid(alpha=0.25)
        frequency_axis.legend(fontsize=7)

        terrain = elevation[indices]
        finite_terrain = terrain[np.isfinite(terrain)]
        span = max(float(np.ptp(finite_terrain)), 0.5)
        lower = float(np.min(finite_terrain)) - 0.1 * span
        upper = max(0.0, float(np.max(finite_terrain))) + 0.08 * span
        terrain_axis.plot(distance[indices], terrain, color="#333333", linewidth=1.1)
        terrain_axis.fill_between(
            distance[indices], terrain, lower, color="#A67C52", alpha=0.55
        )
        terrain_axis.set_ylim(lower, upper)
        terrain_axis.set_title(f"Ray {row + 1}: topographic profile")
        terrain_axis.set_xlabel("Epicentral distance (km)")
        terrain_axis.set_ylabel("Elevation (km)")
        terrain_axis.grid(alpha=0.25)
    fig.suptitle(
        "Original-waveform dominant frequency and topography",
        fontsize=15,
    )
    fig.savefig(
        OUTPUT_DIR / "analysis_dominant_frequency_profiles.png",
        dpi=230,
        bbox_inches="tight",
    )
    plt.close(fig)


def write_summary(
    models: tuple[AnalysisModel, ...],
    effects: dict[str, np.ndarray],
    features: dict[str, np.ndarray],
    records: list[dict[str, object]],
) -> None:
    trimmed = features["trim_mask"]
    lines = [
        "REL3 waveform relationship analysis",
        "===================================",
        "",
        "Primary analysis excludes the first and last five stations of each ray.",
        "Cubic distance trends are removed independently within each ray and residuals",
        "are standardized by ray. Primary Spearman correlations use non-overlapping",
        "10-station spatial-block means. q values use Benjamini-Hochberg FDR.",
        "",
        "S12 raw dominant frequencies:",
    ]
    for model in models:
        lines.append(f"- {model.name}: {model.dominant_frequency_hz[0]:.6f} Hz")

    lines.extend(["", "Median factorial effects across trimmed stations:"])
    summary_metrics = (
        "peak_time_s",
        "log_peak_amplitude",
        "log_total_energy",
        "log_duration_90_s",
        "coda_fraction",
        "dominant_frequency_hz",
    )
    for comparison in (*PAIR_DEFINITIONS.keys(), "interaction"):
        lines.append(f"- {PAIR_LABELS[comparison]}:")
        for metric in summary_metrics:
            values = effects[f"{comparison}__{metric}"][trimmed]
            lines.append(
                f"  {metric}: median={np.nanmedian(values):.6g}, "
                f"IQR=[{np.nanpercentile(values, 25):.6g}, "
                f"{np.nanpercentile(values, 75):.6g}]"
            )

    lines.extend(["", "Strongest distance-controlled terrain relationships:"])
    ranked = sorted(records, key=lambda record: -abs(record["rho"]))
    for record in ranked[:30]:
        lines.append(
            f"- {record['outcome']} vs {record['predictor']}: "
            f"rho={record['rho']:.4f}, q={record['q_value']:.4g}, "
            f"block_n={record['block_n']}, point_rho={record['point_rho']:.4f}, "
            f"untrimmed_rho={record['untrimmed_rho']:.4f}, "
            f"ray_rho=({record['ray1_rho']:.3f}, "
            f"{record['ray2_rho']:.3f}, {record['ray3_rho']:.3f})"
        )
    (OUTPUT_DIR / "analysis_summary.txt").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    station_xy, ray_station_indices = build_station_geometry()
    features = build_station_features(station_xy, ray_station_indices)
    models = tuple(load_analysis_model(index) for index in range(4))
    model_metrics = tuple(waveform_metrics(model) for model in models)
    effects = build_effect_metrics(model_metrics, models)
    records = compute_relationship_statistics(effects, features)

    write_wide_station_table(features, model_metrics, effects)
    write_relationship_table(records)
    write_effect_summary_by_ray(effects, features)
    write_summary(models, effects, features, records)
    plot_effect_profiles(effects, features, ray_station_indices)
    plot_relationship_heatmap(records)
    plot_top_relationships(records, features)
    plot_dominant_frequency_profiles(models, features, ray_station_indices)
    robustness_records = compute_robustness_sensitivity(
        records, effects, features
    )
    write_robustness_table(robustness_records)
    plot_robustness_sensitivity(robustness_records)
    print(f"Analysis complete: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
