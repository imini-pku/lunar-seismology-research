"""Literature-guided envelope, coda, frequency, and terrain analysis."""

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
from scipy.ndimage import median_filter, uniform_filter1d
from scipy.signal import butter, hilbert, sosfiltfilt
from scipy.stats import spearmanr

from analyze_releasy_relationships import (
    PAIR_DEFINITIONS,
    benjamini_hochberg,
    build_station_features,
    residualize_by_ray,
    spatial_block_means,
    standardize_by_ray,
)
from plot_releasy_waveform_comparison import MODELS, build_station_geometry


OUTPUT_DIR = SCRIPT_DIR / "releasy_relationship_analysis" / "literature_guided"
FILTER_ORDER = 4
EPSILON = 1.0e-30
MODEL_SHORT_NAMES = ("M1", "M2", "M3", "M4")
BANDS = {
    "broad": (0.3, 0.9, 0.6),
    "low": (0.3, 0.5, 0.4),
    "middle": (0.5, 0.7, 0.6),
    "high": (0.7, 0.9, 0.8),
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
PRIMARY_METRICS = (
    "broad__tmax_s",
    "broad__log_rise_time_s",
    "broad__log_decay_td_s",
    "broad__log_effective_qc",
    "broad__log_peak_amplitude",
    "broad__log_total_energy",
    "broad__log_duration_90_s",
    "broad__log_impulsiveness_snr",
    "broad__coda_fraction_15s",
    "spectral_softening_log_ratio",
    "high_to_low_total_energy_log_ratio",
)
TERRAIN_PREDICTORS = (
    "elevation_km",
    "absolute_slope",
    "roughness_11km",
    "path_mean_elevation_km",
    "path_mean_absolute_slope",
    "path_relief_range_km",
)


@dataclass
class RawModel:
    name: str
    color: str
    time: np.ndarray
    waveforms: np.ndarray


def load_raw_model(model_index: int) -> RawModel:
    config = MODELS[model_index]
    with Dataset(config.nc_file, "r") as dataset:
        time = np.asarray(dataset.variables["time"][:], dtype=np.float64)
        waveforms = np.asarray(dataset.variables["Vz"][:], dtype=np.float32)
    if waveforms.shape == (time.size, 606):
        waveforms = waveforms.T
    if waveforms.shape != (606, time.size):
        raise ValueError(f"Unexpected Vz shape {waveforms.shape} in {config.nc_file}")
    return RawModel(config.name, config.color, time, waveforms)


def window_energy(
    intensity: np.ndarray,
    time: np.ndarray,
    reference_times: np.ndarray,
    start_offset: float,
    end_offset: float,
) -> np.ndarray:
    result = np.full(606, np.nan, dtype=np.float64)
    for station_index, reference_time in enumerate(reference_times):
        start = int(np.searchsorted(time, reference_time + start_offset))
        end = int(np.searchsorted(time, reference_time + end_offset))
        start = max(0, min(start, time.size - 1))
        end = max(start + 1, min(end, time.size))
        result[station_index] = np.sum(intensity[station_index, start:end])
    return result


def fit_log_decay_window(
    time: np.ndarray,
    smoothed_intensity: np.ndarray,
    start_time: float,
    duration_s: float,
    center_frequency_hz: float,
) -> tuple[float, float, float, float]:
    sample_interval = float(np.median(np.diff(time)))
    fit_start = int(np.searchsorted(time, start_time))
    fit_end = int(np.searchsorted(time, start_time + duration_s))
    fit_end = min(fit_end, time.size - int(round(5.0 / sample_interval)))
    if fit_end - fit_start < int(round(20.0 / sample_interval)):
        return np.nan, np.nan, np.nan, np.nan
    stride = max(1, int(round(0.25 / sample_interval)))
    fit_indices = np.arange(fit_start, fit_end, stride)
    fit_time = time[fit_indices]
    fit_energy = smoothed_intensity[fit_indices]
    floor = max(float(np.max(smoothed_intensity)) * 1.0e-12, EPSILON)
    fit_log_energy = np.log(np.maximum(fit_energy, floor))
    coefficients = np.polyfit(fit_time, fit_log_energy, 1)
    prediction = np.polyval(coefficients, fit_time)
    residual_sum = float(np.sum((fit_log_energy - prediction) ** 2))
    total_sum = float(np.sum((fit_log_energy - np.mean(fit_log_energy)) ** 2))
    r_squared = 1.0 - residual_sum / max(total_sum, EPSILON)
    slope = float(coefficients[0])
    if slope >= 0.0:
        return np.nan, np.nan, r_squared, float(fit_time[-1] - fit_time[0])
    decay_td = -1.0 / slope
    effective_qc = 2.0 * np.pi * center_frequency_hz * decay_td
    return decay_td, effective_qc, r_squared, float(fit_time[-1] - fit_time[0])


def envelope_metrics(
    time: np.ndarray,
    filtered: np.ndarray,
    center_frequency_hz: float,
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    sample_interval = float(np.median(np.diff(time)))
    intensity = np.abs(hilbert(filtered, axis=1)) ** 2
    smoothed_envelopes: list[np.ndarray] = []
    tmax_candidates: list[np.ndarray] = []
    for periods in (5.0, 10.0, 20.0):
        window_seconds = periods / center_frequency_hz
        window_samples = max(3, int(round(window_seconds / sample_interval)))
        smoothed = uniform_filter1d(
            intensity,
            size=window_samples,
            axis=1,
            mode="nearest",
        )
        smoothed_envelopes.append(smoothed)
        tmax_candidates.append(time[np.argmax(smoothed, axis=1)])

    smoothed = smoothed_envelopes[1]
    tmax_stack = np.asarray(tmax_candidates)
    tmax = tmax_stack[1]
    tmax_sensitivity = np.std(tmax_stack, axis=0, ddof=1)

    cumulative = np.cumsum(intensity, axis=1)
    cumulative /= np.maximum(cumulative[:, -1:], EPSILON)
    index_05 = np.argmax(cumulative >= 0.05, axis=1)
    index_95 = np.argmax(cumulative >= 0.95, axis=1)
    time_05 = time[index_05]
    duration_90 = time[index_95] - time_05
    rise_time = np.maximum(tmax - time_05, sample_interval)

    peak_amplitude = np.max(np.abs(filtered), axis=1)
    total_energy = np.sum(filtered * filtered, axis=1) * sample_interval
    coda_energy = window_energy(
        intensity,
        time,
        tmax,
        15.0,
        float(time[-1] - time[0]),
    )
    coda_fraction = coda_energy / np.maximum(np.sum(intensity, axis=1), EPSILON)

    impulsiveness_snr = np.full(606, np.nan, dtype=np.float64)
    decay_td = np.full(606, np.nan, dtype=np.float64)
    effective_qc = np.full(606, np.nan, dtype=np.float64)
    coda_fit_r2 = np.full(606, np.nan, dtype=np.float64)
    fit_window_s = np.full(606, np.nan, dtype=np.float64)
    qc_lapse_log_std = np.full(606, np.nan, dtype=np.float64)
    qc_lapse_log_slope_per_s = np.full(606, np.nan, dtype=np.float64)
    decay_start_offset = max(5.0, 5.0 / center_frequency_hz)
    for station_index, maximum_time in enumerate(tmax):
        peak_start = int(np.searchsorted(time, maximum_time - 2.5))
        peak_end = int(np.searchsorted(time, maximum_time + 2.5))
        coda_start = int(np.searchsorted(time, maximum_time + 2.5))
        coda_end = int(np.searchsorted(time, maximum_time + 7.5))
        peak_start = max(0, peak_start)
        peak_end = max(peak_start + 1, min(peak_end, time.size))
        coda_start = max(0, min(coda_start, time.size - 1))
        coda_end = max(coda_start + 1, min(coda_end, time.size))
        peak_rms = np.sqrt(np.mean(filtered[station_index, peak_start:peak_end] ** 2))
        coda_rms = np.sqrt(np.mean(filtered[station_index, coda_start:coda_end] ** 2))
        impulsiveness_snr[station_index] = peak_rms / max(coda_rms, EPSILON)

        primary_fit = fit_log_decay_window(
            time,
            smoothed[station_index],
            maximum_time + decay_start_offset,
            60.0,
            center_frequency_hz,
        )
        decay_td[station_index], effective_qc[station_index] = primary_fit[:2]
        coda_fit_r2[station_index], fit_window_s[station_index] = primary_fit[2:]

        lapse_centers: list[float] = []
        lapse_log_qc: list[float] = []
        for additional_offset in (0.0, 10.0, 20.0):
            window_start = maximum_time + decay_start_offset + additional_offset
            _, window_qc, window_r2, actual_duration = fit_log_decay_window(
                time,
                smoothed[station_index],
                window_start,
                40.0,
                center_frequency_hz,
            )
            if np.isfinite(window_qc) and window_r2 >= 0.3:
                lapse_centers.append(window_start + actual_duration / 2.0)
                lapse_log_qc.append(float(np.log(window_qc)))
        if len(lapse_log_qc) >= 2:
            qc_lapse_log_std[station_index] = float(
                np.std(lapse_log_qc, ddof=1)
            )
            qc_lapse_log_slope_per_s[station_index] = float(
                np.polyfit(lapse_centers, lapse_log_qc, 1)[0]
            )

    metrics = {
        "tmax_s": tmax,
        "tmax_5period_s": tmax_stack[0],
        "tmax_10period_s": tmax_stack[1],
        "tmax_20period_s": tmax_stack[2],
        "tmax_sensitivity_s": tmax_sensitivity,
        "log_rise_time_s": np.log(np.maximum(rise_time, sample_interval)),
        "log_decay_td_s": np.log(np.maximum(decay_td, sample_interval)),
        "log_effective_qc": np.log(np.maximum(effective_qc, EPSILON)),
        "coda_fit_r2": coda_fit_r2,
        "fit_window_s": fit_window_s,
        "qc_lapse_log_std": qc_lapse_log_std,
        "qc_lapse_log_slope_per_s": qc_lapse_log_slope_per_s,
        "log_peak_amplitude": np.log(np.maximum(peak_amplitude, EPSILON)),
        "log_total_energy": np.log(np.maximum(total_energy, EPSILON)),
        "log_duration_90_s": np.log(np.maximum(duration_90, sample_interval)),
        "log_impulsiveness_snr": np.log(np.maximum(impulsiveness_snr, EPSILON)),
        "coda_fraction_15s": coda_fraction,
    }
    return metrics, intensity


def process_model(model_index: int) -> dict[str, np.ndarray]:
    model = load_raw_model(model_index)
    sample_interval = float(np.median(np.diff(model.time)))
    sample_rate = 1.0 / sample_interval
    metrics: dict[str, np.ndarray] = {}
    broad_tmax: np.ndarray | None = None
    early_energy: dict[str, np.ndarray] = {}
    late_energy: dict[str, np.ndarray] = {}
    for band_name, (low_hz, high_hz, center_hz) in BANDS.items():
        sos = butter(
            FILTER_ORDER,
            (low_hz, high_hz),
            btype="bandpass",
            fs=sample_rate,
            output="sos",
        )
        filtered = sosfiltfilt(sos, model.waveforms, axis=1)
        band_metrics, intensity = envelope_metrics(
            model.time,
            filtered,
            center_hz,
        )
        for metric_name, values in band_metrics.items():
            metrics[f"{band_name}__{metric_name}"] = values
        if band_name == "broad":
            broad_tmax = band_metrics["tmax_s"]
        else:
            if broad_tmax is None:
                raise RuntimeError("Broad band must be processed first")
            early_energy[band_name] = window_energy(
                intensity, model.time, broad_tmax, 0.0, 20.0
            )
            late_energy[band_name] = window_energy(
                intensity, model.time, broad_tmax, 40.0, 80.0
            )

    high_to_low_early = early_energy["high"] / np.maximum(
        early_energy["low"], EPSILON
    )
    high_to_low_late = late_energy["high"] / np.maximum(
        late_energy["low"], EPSILON
    )
    high_total = np.exp(metrics["high__log_total_energy"])
    low_total = np.exp(metrics["low__log_total_energy"])
    metrics["spectral_softening_log_ratio"] = np.log(
        np.maximum(high_to_low_late, EPSILON)
        / np.maximum(high_to_low_early, EPSILON)
    )
    metrics["high_to_low_total_energy_log_ratio"] = np.log(
        np.maximum(high_total, EPSILON) / np.maximum(low_total, EPSILON)
    )
    return metrics


def build_effects(
    model_metrics: tuple[dict[str, np.ndarray], ...]
) -> dict[str, np.ndarray]:
    effects: dict[str, np.ndarray] = {}
    for comparison, (first_index, second_index) in PAIR_DEFINITIONS.items():
        for metric_name in model_metrics[0]:
            effects[f"{comparison}__{metric_name}"] = (
                model_metrics[second_index][metric_name]
                - model_metrics[first_index][metric_name]
            )
    for metric_name in model_metrics[0]:
        effects[f"interaction__{metric_name}"] = (
            model_metrics[3][metric_name]
            - model_metrics[2][metric_name]
            - model_metrics[1][metric_name]
            + model_metrics[0][metric_name]
        )
    return effects


def compute_terrain_relationships(
    effects: dict[str, np.ndarray],
    features: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    distance = features["distance_km"]
    ray = features["ray"]
    trimmed = features["trim_mask"]
    for comparison in (*PAIR_DEFINITIONS.keys(), "interaction"):
        for metric_name in PRIMARY_METRICS:
            outcome_name = f"{comparison}__{metric_name}"
            outcome = effects[outcome_name]
            outcome_residual = standardize_by_ray(
                residualize_by_ray(outcome, distance, ray, trimmed), ray
            )
            for predictor_name in TERRAIN_PREDICTORS:
                predictor = features[predictor_name]
                predictor_residual = standardize_by_ray(
                    residualize_by_ray(predictor, distance, ray, trimmed), ray
                )
                block_predictor, block_outcome = spatial_block_means(
                    predictor_residual,
                    outcome_residual,
                    ray,
                    trimmed,
                )
                if block_predictor.size < 12:
                    continue
                statistic = spearmanr(block_predictor, block_outcome)
                ray_rhos = []
                for ray_number in (1, 2, 3):
                    valid = (
                        trimmed
                        & (ray == ray_number)
                        & np.isfinite(predictor_residual)
                        & np.isfinite(outcome_residual)
                    )
                    ray_rhos.append(
                        float(
                            spearmanr(
                                predictor_residual[valid], outcome_residual[valid]
                            ).statistic
                        )
                    )
                records.append(
                    {
                        "outcome": outcome_name,
                        "predictor": predictor_name,
                        "rho": float(statistic.statistic),
                        "p_value": float(statistic.pvalue),
                        "block_n": int(block_predictor.size),
                        "ray1_rho": ray_rhos[0],
                        "ray2_rho": ray_rhos[1],
                        "ray3_rho": ray_rhos[2],
                        "outcome_residual": outcome_residual,
                        "predictor_residual": predictor_residual,
                    }
                )
    q_values = benjamini_hochberg(
        np.asarray([record["p_value"] for record in records])
    )
    for record, q_value in zip(records, q_values, strict=True):
        record["q_value"] = float(q_value)
        ray_rhos = np.asarray(
            [record["ray1_rho"], record["ray2_rho"], record["ray3_rho"]]
        )
        record["consistent_ray_count"] = int(
            np.sum(np.sign(ray_rhos) == np.sign(record["rho"]))
        )
    return records


def compute_signature_persistence(
    effects: dict[str, np.ndarray],
    features: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    distance = features["distance_km"]
    ray = features["ray"]
    trimmed = features["trim_mask"]
    comparisons = (
        ("topography_no_scatter", "topography_scatter", "topography"),
        ("scatter_flat", "scatter_topography", "scattering"),
    )
    for first, second, signature in comparisons:
        for metric_name in PRIMARY_METRICS:
            first_residual = standardize_by_ray(
                residualize_by_ray(
                    effects[f"{first}__{metric_name}"], distance, ray, trimmed
                ),
                ray,
            )
            second_residual = standardize_by_ray(
                residualize_by_ray(
                    effects[f"{second}__{metric_name}"], distance, ray, trimmed
                ),
                ray,
            )
            first_blocks, second_blocks = spatial_block_means(
                first_residual, second_residual, ray, trimmed
            )
            statistic = spearmanr(first_blocks, second_blocks)
            records.append(
                {
                    "signature": signature,
                    "metric": metric_name,
                    "rho": float(statistic.statistic),
                    "p_value": float(statistic.pvalue),
                    "block_n": int(first_blocks.size),
                }
            )
    q_values = benjamini_hochberg(
        np.asarray([record["p_value"] for record in records])
    )
    for record, q_value in zip(records, q_values, strict=True):
        record["q_value"] = float(q_value)
    return records


def fit_piecewise_profile(
    distance: np.ndarray,
    values: np.ndarray,
) -> dict[str, float]:
    order = np.argsort(distance)
    x = distance[order]
    y = values[order]
    y = median_filter(y, size=11, mode="nearest")
    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]
    if x.size < 50:
        return {name: np.nan for name in (
            "breakpoint_km", "slope_before", "slope_after", "delta_aic"
        )}
    linear_design = np.column_stack((np.ones(x.size), x))
    linear_coefficients, _, _, _ = np.linalg.lstsq(linear_design, y, rcond=None)
    linear_residual = y - linear_design @ linear_coefficients
    linear_sse = float(np.sum(linear_residual * linear_residual))
    best: dict[str, float] | None = None
    candidates = x[20:-20:2]
    for breakpoint in candidates:
        hinge = np.maximum(0.0, x - breakpoint)
        design = np.column_stack((np.ones(x.size), x, hinge))
        coefficients, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
        residual = y - design @ coefficients
        sse = float(np.sum(residual * residual))
        if best is None or sse < best["sse"]:
            best = {
                "breakpoint_km": float(breakpoint),
                "slope_before": float(coefficients[1]),
                "slope_after": float(coefficients[1] + coefficients[2]),
                "sse": sse,
            }
    if best is None:
        raise RuntimeError("No breakpoint candidates")
    n = x.size
    linear_aic = n * np.log(max(linear_sse / n, EPSILON)) + 2 * 2
    piecewise_aic = n * np.log(max(best["sse"] / n, EPSILON)) + 2 * 4
    best["delta_aic"] = float(linear_aic - piecewise_aic)
    best.pop("sse")
    return best


def compute_breakpoints(
    effects: dict[str, np.ndarray],
    features: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    metric_names = (
        "broad__tmax_s",
        "broad__log_rise_time_s",
        "broad__log_decay_td_s",
        "broad__log_impulsiveness_snr",
    )
    for comparison in PAIR_DEFINITIONS:
        for metric_name in metric_names:
            values = effects[f"{comparison}__{metric_name}"]
            for ray_number in (1, 2, 3):
                mask = features["trim_mask"] & (features["ray"] == ray_number)
                fit = fit_piecewise_profile(
                    features["distance_km"][mask], values[mask]
                )
                records.append(
                    {
                        "comparison": comparison,
                        "metric": metric_name,
                        "ray": ray_number,
                        **fit,
                    }
                )
    return records


def compute_spatial_lags(
    effects: dict[str, np.ndarray],
    features: dict[str, np.ndarray],
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    metrics = (
        "broad__tmax_s",
        "broad__log_rise_time_s",
        "broad__log_decay_td_s",
        "broad__log_peak_amplitude",
        "broad__log_total_energy",
        "broad__log_impulsiveness_snr",
    )
    distance = features["distance_km"]
    ray = features["ray"]
    trimmed = features["trim_mask"]
    for comparison in ("topography_no_scatter", "topography_scatter"):
        for metric_name in metrics:
            outcome = residualize_by_ray(
                effects[f"{comparison}__{metric_name}"],
                distance,
                ray,
                trimmed,
            )
            for predictor_name in ("absolute_slope", "roughness_11km"):
                predictor = residualize_by_ray(
                    features[predictor_name], distance, ray, trimmed
                )
                for ray_number in (1, 2, 3):
                    indices = np.where(trimmed & (ray == ray_number))[0]
                    best_lag = 0
                    best_rho = np.nan
                    for lag in range(-30, 31):
                        if lag < 0:
                            predictor_values = predictor[indices[-lag:]]
                            outcome_values = outcome[indices[:lag]]
                        elif lag > 0:
                            predictor_values = predictor[indices[:-lag]]
                            outcome_values = outcome[indices[lag:]]
                        else:
                            predictor_values = predictor[indices]
                            outcome_values = outcome[indices]
                        valid = np.isfinite(predictor_values) & np.isfinite(
                            outcome_values
                        )
                        rho = float(
                            spearmanr(
                                predictor_values[valid], outcome_values[valid]
                            ).statistic
                        )
                        if not np.isfinite(best_rho) or abs(rho) > abs(best_rho):
                            best_lag = lag
                            best_rho = rho
                    records.append(
                        {
                            "comparison": comparison,
                            "metric": metric_name,
                            "predictor": predictor_name,
                            "ray": ray_number,
                            "best_lag_km": best_lag,
                            "rho_at_best_lag": best_rho,
                        }
                    )
    return records


def write_station_table(
    features: dict[str, np.ndarray],
    model_metrics: tuple[dict[str, np.ndarray], ...],
    effects: dict[str, np.ndarray],
) -> None:
    feature_names = tuple(
        name for name in features if name not in {"ray", "trim_mask"}
    )
    model_columns = [
        (f"{MODEL_SHORT_NAMES[index]}__{name}", values)
        for index, metrics in enumerate(model_metrics)
        for name, values in metrics.items()
    ]
    effect_columns = list(effects.items())
    columns = (
        "station",
        "ray",
        "included_in_primary_analysis",
        *feature_names,
        *[name for name, _ in model_columns],
        *[name for name, _ in effect_columns],
    )
    with (OUTPUT_DIR / "literature_guided_station_metrics.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for station_index in range(606):
            writer.writerow(
                (
                    f"r{station_index + 1}",
                    "S12" if station_index == 0 else int(features["ray"][station_index]),
                    int(features["trim_mask"][station_index]),
                    *[features[name][station_index] for name in feature_names],
                    *[values[station_index] for _, values in model_columns],
                    *[values[station_index] for _, values in effect_columns],
                )
            )


def write_effect_summary(
    effects: dict[str, np.ndarray],
    features: dict[str, np.ndarray],
) -> None:
    columns = (
        "comparison",
        "metric",
        "ray",
        "n",
        "median",
        "q25",
        "q75",
        "positive_fraction",
        "negative_fraction",
    )
    with (OUTPUT_DIR / "literature_guided_effect_summary.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for comparison in (*PAIR_DEFINITIONS.keys(), "interaction"):
            for metric_name in PRIMARY_METRICS:
                values = effects[f"{comparison}__{metric_name}"]
                for ray_number in (0, 1, 2, 3):
                    if ray_number == 0:
                        mask = features["trim_mask"]
                    else:
                        mask = features["trim_mask"] & (
                            features["ray"] == ray_number
                        )
                    selected = values[mask]
                    selected = selected[np.isfinite(selected)]
                    writer.writerow(
                        {
                            "comparison": comparison,
                            "metric": metric_name,
                            "ray": "all" if ray_number == 0 else ray_number,
                            "n": selected.size,
                            "median": float(np.median(selected)),
                            "q25": float(np.percentile(selected, 25)),
                            "q75": float(np.percentile(selected, 75)),
                            "positive_fraction": float(np.mean(selected > 0.0)),
                            "negative_fraction": float(np.mean(selected < 0.0)),
                        }
                    )


def block_bootstrap_median(
    values: np.ndarray,
    mask: np.ndarray,
    ray: np.ndarray,
    random_generator: np.random.Generator,
    iterations: int = 2000,
) -> tuple[float, float, float, int]:
    blocks: list[np.ndarray] = []
    for ray_number in (1, 2, 3):
        indices = np.where(mask & (ray == ray_number) & np.isfinite(values))[0]
        for start in range(0, indices.size, 10):
            block = values[indices[start : start + 10]]
            if block.size >= 5:
                blocks.append(block)
    if not blocks:
        return np.nan, np.nan, np.nan, 0
    bootstrap_medians = np.empty(iterations, dtype=np.float64)
    for iteration in range(iterations):
        selected_blocks = random_generator.integers(0, len(blocks), len(blocks))
        sample = np.concatenate([blocks[index] for index in selected_blocks])
        bootstrap_medians[iteration] = np.nanmedian(sample)
    observed = float(np.nanmedian(values[mask]))
    return (
        observed,
        float(np.percentile(bootstrap_medians, 2.5)),
        float(np.percentile(bootstrap_medians, 97.5)),
        len(blocks),
    )


def write_block_bootstrap_effects(
    effects: dict[str, np.ndarray],
    features: dict[str, np.ndarray],
) -> None:
    columns = (
        "comparison",
        "metric",
        "ray",
        "median",
        "bootstrap_ci_low",
        "bootstrap_ci_high",
        "spatial_block_count",
        "ci_excludes_zero",
    )
    random_generator = np.random.default_rng(20260802)
    with (OUTPUT_DIR / "literature_guided_block_bootstrap_effects.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for comparison in (*PAIR_DEFINITIONS.keys(), "interaction"):
            for metric_name in PRIMARY_METRICS:
                values = effects[f"{comparison}__{metric_name}"]
                for ray_number in (0, 1, 2, 3):
                    if ray_number == 0:
                        mask = features["trim_mask"]
                    else:
                        mask = features["trim_mask"] & (
                            features["ray"] == ray_number
                        )
                    median, ci_low, ci_high, block_count = block_bootstrap_median(
                        values,
                        mask,
                        features["ray"],
                        random_generator,
                    )
                    writer.writerow(
                        {
                            "comparison": comparison,
                            "metric": metric_name,
                            "ray": "all" if ray_number == 0 else ray_number,
                            "median": median,
                            "bootstrap_ci_low": ci_low,
                            "bootstrap_ci_high": ci_high,
                            "spatial_block_count": block_count,
                            "ci_excludes_zero": int(
                                np.sign(ci_low) == np.sign(ci_high)
                                and ci_low != 0.0
                                and ci_high != 0.0
                            ),
                        }
                    )


def write_frequency_summary(
    model_metrics: tuple[dict[str, np.ndarray], ...],
    features: dict[str, np.ndarray],
) -> None:
    columns = (
        "model",
        "ray",
        "band",
        "center_frequency_hz",
        "station_count",
        "median_tmax_s",
        "median_tmax_sensitivity_s",
        "median_rise_time_s",
        "median_decay_td_s",
        "median_effective_qc",
        "median_coda_fit_r2",
        "fraction_coda_fit_r2_ge_0_5",
        "median_qc_lapse_log_std",
        "median_qc_lapse_log_slope_per_s",
        "median_impulsiveness_snr",
    )
    with (OUTPUT_DIR / "literature_guided_frequency_summary.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for model_index, metrics in enumerate(model_metrics):
            for ray_number in (1, 2, 3):
                mask = features["trim_mask"] & (features["ray"] == ray_number)
                for band_name, (_, _, center_hz) in BANDS.items():
                    r2_values = metrics[f"{band_name}__coda_fit_r2"][mask]
                    finite_r2 = r2_values[np.isfinite(r2_values)]
                    writer.writerow(
                        {
                            "model": MODEL_SHORT_NAMES[model_index],
                            "ray": ray_number,
                            "band": band_name,
                            "center_frequency_hz": center_hz,
                            "station_count": int(np.sum(mask)),
                            "median_tmax_s": float(
                                np.nanmedian(metrics[f"{band_name}__tmax_s"][mask])
                            ),
                            "median_tmax_sensitivity_s": float(
                                np.nanmedian(
                                    metrics[f"{band_name}__tmax_sensitivity_s"][mask]
                                )
                            ),
                            "median_rise_time_s": float(
                                np.exp(
                                    np.nanmedian(
                                        metrics[f"{band_name}__log_rise_time_s"][mask]
                                    )
                                )
                            ),
                            "median_decay_td_s": float(
                                np.exp(
                                    np.nanmedian(
                                        metrics[f"{band_name}__log_decay_td_s"][mask]
                                    )
                                )
                            ),
                            "median_effective_qc": float(
                                np.exp(
                                    np.nanmedian(
                                        metrics[f"{band_name}__log_effective_qc"][mask]
                                    )
                                )
                            ),
                            "median_coda_fit_r2": float(np.nanmedian(finite_r2)),
                            "fraction_coda_fit_r2_ge_0_5": float(
                                np.mean(finite_r2 >= 0.5)
                            ),
                            "median_qc_lapse_log_std": float(
                                np.nanmedian(
                                    metrics[f"{band_name}__qc_lapse_log_std"][mask]
                                )
                            ),
                            "median_qc_lapse_log_slope_per_s": float(
                                np.nanmedian(
                                    metrics[
                                        f"{band_name}__qc_lapse_log_slope_per_s"
                                    ][mask]
                                )
                            ),
                            "median_impulsiveness_snr": float(
                                np.exp(
                                    np.nanmedian(
                                        metrics[
                                            f"{band_name}__log_impulsiveness_snr"
                                        ][mask]
                                    )
                                )
                            ),
                        }
                    )


def write_frequency_trends(
    model_metrics: tuple[dict[str, np.ndarray], ...],
    features: dict[str, np.ndarray],
) -> None:
    columns = (
        "model",
        "ray",
        "qc_frequency_exponent",
        "decay_td_frequency_exponent",
        "tmax_frequency_slope_s_per_hz",
        "impulsiveness_frequency_exponent",
    )
    frequencies = np.asarray([BANDS[name][2] for name in ("low", "middle", "high")])
    with (OUTPUT_DIR / "literature_guided_frequency_trends.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for model_index, metrics in enumerate(model_metrics):
            for ray_number in (1, 2, 3):
                mask = features["trim_mask"] & (features["ray"] == ray_number)
                median_log_qc = np.asarray(
                    [
                        np.nanmedian(metrics[f"{band}__log_effective_qc"][mask])
                        for band in ("low", "middle", "high")
                    ]
                )
                median_log_td = np.asarray(
                    [
                        np.nanmedian(metrics[f"{band}__log_decay_td_s"][mask])
                        for band in ("low", "middle", "high")
                    ]
                )
                median_tmax = np.asarray(
                    [
                        np.nanmedian(metrics[f"{band}__tmax_s"][mask])
                        for band in ("low", "middle", "high")
                    ]
                )
                median_log_snr = np.asarray(
                    [
                        np.nanmedian(
                            metrics[f"{band}__log_impulsiveness_snr"][mask]
                        )
                        for band in ("low", "middle", "high")
                    ]
                )
                writer.writerow(
                    {
                        "model": MODEL_SHORT_NAMES[model_index],
                        "ray": ray_number,
                        "qc_frequency_exponent": float(
                            np.polyfit(np.log(frequencies), median_log_qc, 1)[0]
                        ),
                        "decay_td_frequency_exponent": float(
                            np.polyfit(np.log(frequencies), median_log_td, 1)[0]
                        ),
                        "tmax_frequency_slope_s_per_hz": float(
                            np.polyfit(frequencies, median_tmax, 1)[0]
                        ),
                        "impulsiveness_frequency_exponent": float(
                            np.polyfit(np.log(frequencies), median_log_snr, 1)[0]
                        ),
                    }
                )


def write_tmax_smoothing_summary(
    effects: dict[str, np.ndarray],
    features: dict[str, np.ndarray],
) -> None:
    columns = (
        "comparison",
        "ray",
        "median_delta_tmax_5period_s",
        "median_delta_tmax_10period_s",
        "median_delta_tmax_20period_s",
        "median_range_across_windows_s",
    )
    with (OUTPUT_DIR / "literature_guided_tmax_smoothing_sensitivity.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for comparison in (*PAIR_DEFINITIONS.keys(), "interaction"):
            for ray_number in (0, 1, 2, 3):
                if ray_number == 0:
                    mask = features["trim_mask"]
                else:
                    mask = features["trim_mask"] & (
                        features["ray"] == ray_number
                    )
                window_effects = np.vstack(
                    [
                        effects[f"{comparison}__broad__tmax_{period}period_s"][mask]
                        for period in (5, 10, 20)
                    ]
                )
                writer.writerow(
                    {
                        "comparison": comparison,
                        "ray": "all" if ray_number == 0 else ray_number,
                        "median_delta_tmax_5period_s": float(
                            np.nanmedian(window_effects[0])
                        ),
                        "median_delta_tmax_10period_s": float(
                            np.nanmedian(window_effects[1])
                        ),
                        "median_delta_tmax_20period_s": float(
                            np.nanmedian(window_effects[2])
                        ),
                        "median_range_across_windows_s": float(
                            np.nanmedian(
                                np.nanmax(window_effects, axis=0)
                                - np.nanmin(window_effects, axis=0)
                            )
                        ),
                    }
                )


def write_dict_table(filename: str, records: list[dict[str, object]]) -> None:
    if not records:
        return
    columns = tuple(
        key
        for key in records[0]
        if key not in {"outcome_residual", "predictor_residual"}
    )
    with (OUTPUT_DIR / filename).open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def plot_frequency_dependence(
    model_metrics: tuple[dict[str, np.ndarray], ...],
    features: dict[str, np.ndarray],
) -> None:
    frequencies = np.asarray([BANDS[name][2] for name in ("low", "middle", "high")])
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.5), constrained_layout=True)
    for column, ray_number in enumerate((1, 2, 3)):
        mask = features["trim_mask"] & (features["ray"] == ray_number)
        for model_index, metrics in enumerate(model_metrics):
            tmax_values = [
                np.nanmedian(metrics[f"{band}__tmax_s"][mask])
                for band in ("low", "middle", "high")
            ]
            qc_values = [
                np.exp(np.nanmedian(metrics[f"{band}__log_effective_qc"][mask]))
                for band in ("low", "middle", "high")
            ]
            axes[0, column].plot(
                frequencies,
                tmax_values,
                marker="o",
                color=MODELS[model_index].color,
                label=MODEL_SHORT_NAMES[model_index],
            )
            axes[1, column].plot(
                frequencies,
                qc_values,
                marker="o",
                color=MODELS[model_index].color,
                label=MODEL_SHORT_NAMES[model_index],
            )
        axes[0, column].set_title(f"Ray {ray_number}")
        axes[0, column].set_ylabel("Median envelope tmax (s)")
        axes[1, column].set_ylabel("Median effective coda Qc")
        axes[1, column].set_xlabel("Band center frequency (Hz)")
        axes[1, column].set_yscale("log")
        for axis in axes[:, column]:
            axis.grid(alpha=0.25)
    axes[0, 0].legend(ncol=2)
    fig.suptitle("Literature-guided frequency dependence of envelope metrics")
    fig.savefig(
        OUTPUT_DIR / "literature_frequency_dependence.png",
        dpi=230,
        bbox_inches="tight",
    )
    plt.close(fig)


def plot_scattering_separation(
    effects: dict[str, np.ndarray],
    features: dict[str, np.ndarray],
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4), constrained_layout=True)
    for axis, comparison in zip(
        axes, ("scatter_flat", "scatter_topography"), strict=True
    ):
        x_values = effects[f"{comparison}__broad__tmax_s"]
        y_values = effects[f"{comparison}__broad__log_effective_qc"]
        for ray_number, color in zip((1, 2, 3), ("#0072B2", "#D55E00", "#009E73")):
            mask = (
                features["trim_mask"]
                & (features["ray"] == ray_number)
                & np.isfinite(x_values)
                & np.isfinite(y_values)
            )
            axis.scatter(
                x_values[mask],
                y_values[mask],
                s=12,
                alpha=0.45,
                color=color,
                label=f"Ray {ray_number}",
            )
        axis.axvline(0.0, color="0.4", lw=0.8)
        axis.axhline(0.0, color="0.4", lw=0.8)
        axis.set_title(PAIR_LABELS[comparison])
        axis.set_xlabel("Change in envelope tmax (s)")
        axis.set_ylabel("Change in log effective Qc")
        axis.grid(alpha=0.25)
    axes[0].legend()
    fig.suptitle("Separating envelope broadening from late-coda decay")
    fig.savefig(
        OUTPUT_DIR / "literature_scattering_tmax_vs_qc.png",
        dpi=230,
        bbox_inches="tight",
    )
    plt.close(fig)


def plot_breakpoint_profiles(
    effects: dict[str, np.ndarray],
    features: dict[str, np.ndarray],
    breakpoints: list[dict[str, object]],
) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(12.5, 10.5), constrained_layout=True)
    for axis, ray_number in zip(axes, (1, 2, 3), strict=True):
        mask = features["trim_mask"] & (features["ray"] == ray_number)
        distance = features["distance_km"][mask]
        order = np.argsort(distance)
        for comparison in ("scatter_flat", "scatter_topography"):
            values = effects[f"{comparison}__broad__tmax_s"][mask][order]
            smooth = median_filter(values, size=11, mode="nearest")
            axis.plot(
                distance[order],
                smooth,
                color=PAIR_COLORS[comparison],
                label=PAIR_LABELS[comparison],
            )
            record = next(
                item
                for item in breakpoints
                if item["comparison"] == comparison
                and item["metric"] == "broad__tmax_s"
                and item["ray"] == ray_number
            )
            if record["delta_aic"] > 6.0:
                axis.axvline(
                    record["breakpoint_km"],
                    color=PAIR_COLORS[comparison],
                    ls="--",
                    alpha=0.8,
                )
        axis.axhline(0.0, color="0.4", lw=0.8)
        axis.set_title(f"Ray {ray_number}")
        axis.set_ylabel("Scattering-induced Δtmax (s)")
        axis.grid(alpha=0.25)
    axes[-1].set_xlabel("Epicentral distance (km)")
    axes[0].legend()
    fig.suptitle("Distance transitions in scattering-induced envelope delay")
    fig.savefig(
        OUTPUT_DIR / "literature_scattering_breakpoints.png",
        dpi=230,
        bbox_inches="tight",
    )
    plt.close(fig)


def plot_top_terrain_relationships(
    records: list[dict[str, object]],
) -> None:
    selected: list[dict[str, object]] = []
    used_outcomes: set[str] = set()
    for record in sorted(records, key=lambda item: -abs(item["rho"])):
        if record["outcome"] in used_outcomes:
            continue
        selected.append(record)
        used_outcomes.add(record["outcome"])
        if len(selected) == 8:
            break
    fig, axes = plt.subplots(2, 4, figsize=(17, 8), constrained_layout=True)
    for axis, record in zip(axes.flat, selected, strict=True):
        predictor = record["predictor_residual"]
        outcome = record["outcome_residual"]
        valid = np.isfinite(predictor) & np.isfinite(outcome)
        axis.scatter(predictor[valid], outcome[valid], s=10, alpha=0.35)
        axis.set_title(
            f"ρ={record['rho']:.2f}, q={record['q_value']:.2g}", fontsize=10
        )
        axis.set_xlabel(record["predictor"].replace("_", " "), fontsize=8)
        axis.set_ylabel(record["outcome"].replace("__", " / "), fontsize=7)
        axis.grid(alpha=0.2)
    fig.suptitle("Strongest distance-controlled literature-guided terrain relations")
    fig.savefig(
        OUTPUT_DIR / "literature_top_terrain_relationships.png",
        dpi=230,
        bbox_inches="tight",
    )
    plt.close(fig)


def plot_model_metric_synthesis(
    model_metrics: tuple[dict[str, np.ndarray], ...],
    features: dict[str, np.ndarray],
) -> None:
    trimmed = features["trim_mask"]
    specifications = (
        ("Envelope tmax", "broad__tmax_s", False, "s"),
        ("Rise time", "broad__log_rise_time_s", True, "s"),
        ("Decay td", "broad__log_decay_td_s", True, "s"),
        ("Impulsiveness SNR", "broad__log_impulsiveness_snr", True, "ratio"),
        ("Coda fraction after 15 s", "broad__coda_fraction_15s", False, "fraction"),
        ("Late/early spectral shift", "spectral_softening_log_ratio", False, "log ratio"),
    )
    fig, axes = plt.subplots(2, 3, figsize=(14.5, 8.3), constrained_layout=True)
    for axis, (title, metric_name, exponentiate, unit) in zip(
        axes.flat, specifications, strict=True
    ):
        values = np.asarray(
            [
                np.nanmedian(metrics[metric_name][trimmed])
                for metrics in model_metrics
            ]
        )
        if exponentiate:
            values = np.exp(values)
        axis.bar(
            MODEL_SHORT_NAMES,
            values,
            color=[model.color for model in MODELS],
            alpha=0.85,
        )
        axis.set_title(title)
        axis.set_ylabel(unit)
        axis.grid(axis="y", alpha=0.25)
        if np.all(values > 0.0) and np.max(values) / np.min(values) > 8.0:
            axis.set_yscale("log")
        for index, value in enumerate(values):
            axis.text(
                index,
                value,
                f"{value:.2f}",
                ha="center",
                va="bottom" if value >= 0 else "top",
                fontsize=8,
            )
    fig.suptitle("Four-model synthesis of literature-guided envelope metrics")
    fig.savefig(
        OUTPUT_DIR / "literature_model_metric_synthesis.png",
        dpi=230,
        bbox_inches="tight",
    )
    plt.close(fig)


def plot_factorial_effect_heatmap(
    effects: dict[str, np.ndarray],
    features: dict[str, np.ndarray],
) -> None:
    trimmed = features["trim_mask"]
    comparisons = (*PAIR_DEFINITIONS.keys(), "interaction")
    metrics = (
        ("Peak amplitude", "broad__log_peak_amplitude"),
        ("Total energy", "broad__log_total_energy"),
        ("Rise time", "broad__log_rise_time_s"),
        ("Decay td", "broad__log_decay_td_s"),
        ("Duration 90%", "broad__log_duration_90_s"),
        ("Impulsiveness", "broad__log_impulsiveness_snr"),
    )
    matrix = np.asarray(
        [
            [
                np.nanmedian(effects[f"{comparison}__{metric_name}"][trimmed])
                for _, metric_name in metrics
            ]
            for comparison in comparisons
        ]
    )
    fig, axis = plt.subplots(figsize=(11.5, 6.8), constrained_layout=True)
    image = axis.imshow(matrix, aspect="auto", cmap="coolwarm", vmin=-3.0, vmax=3.0)
    axis.set_xticks(np.arange(len(metrics)))
    axis.set_xticklabels([label for label, _ in metrics], rotation=25, ha="right")
    axis.set_yticks(np.arange(len(comparisons)))
    axis.set_yticklabels([PAIR_LABELS[name] for name in comparisons])
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            value = matrix[row, column]
            axis.text(
                column,
                row,
                f"×{np.exp(value):.2f}",
                ha="center",
                va="center",
                fontsize=9,
                color="white" if abs(value) > 1.2 else "black",
            )
    axis.set_title("Median multiplicative effects from the 2×2 factorial design")
    fig.colorbar(image, ax=axis, label="Median log ratio")
    fig.savefig(
        OUTPUT_DIR / "literature_factorial_effect_heatmap.png",
        dpi=230,
        bbox_inches="tight",
    )
    plt.close(fig)


def write_machine_summary(
    model_metrics: tuple[dict[str, np.ndarray], ...],
    effects: dict[str, np.ndarray],
    features: dict[str, np.ndarray],
    terrain_records: list[dict[str, object]],
    signature_records: list[dict[str, object]],
    breakpoints: list[dict[str, object]],
) -> None:
    trimmed = features["trim_mask"]
    lines = [
        "Literature-guided REL3 analysis",
        "===============================",
        "",
        "Envelope tmax uses a 10-period running mean of analytic-signal intensity.",
        "Sensitivity is the standard deviation across 5, 10, and 20-period windows.",
        "Effective Qc is fitted over a 60 s post-maximum intensity-decay window.",
        "It is a finite-record diagnostic, not a unique intrinsic-attenuation inversion.",
        "",
        "Model medians across trimmed ray stations:",
    ]
    for model_index, metrics in enumerate(model_metrics):
        valid_qc = np.isfinite(metrics["broad__log_effective_qc"][trimmed])
        lines.append(f"- {MODEL_SHORT_NAMES[model_index]}:")
        lines.append(
            f"  broad tmax={np.nanmedian(metrics['broad__tmax_s'][trimmed]):.4f} s"
        )
        lines.append(
            "  broad rise time="
            f"{np.exp(np.nanmedian(metrics['broad__log_rise_time_s'][trimmed])):.4f} s"
        )
        lines.append(
            "  broad decay td="
            f"{np.exp(np.nanmedian(metrics['broad__log_decay_td_s'][trimmed])):.4f} s"
        )
        lines.append(
            "  broad effective Qc="
            f"{np.exp(np.nanmedian(metrics['broad__log_effective_qc'][trimmed])):.4f}"
        )
        lines.append(
            f"  valid Qc fits={np.sum(valid_qc)}/{np.sum(trimmed)}"
        )
        lines.append(
            "  median coda fit R2="
            f"{np.nanmedian(metrics['broad__coda_fit_r2'][trimmed]):.4f}"
        )
        lines.append(
            "  fraction coda fit R2>=0.5="
            f"{np.nanmean(metrics['broad__coda_fit_r2'][trimmed] >= 0.5):.4f}"
        )
        lines.append(
            "  median log-Qc lapse variability="
            f"{np.nanmedian(metrics['broad__qc_lapse_log_std'][trimmed]):.4f}"
        )
        lines.append(
            "  impulsiveness SNR="
            f"{np.exp(np.nanmedian(metrics['broad__log_impulsiveness_snr'][trimmed])):.4f}"
        )
        lines.append(
            "  spectral softening log ratio="
            f"{np.nanmedian(metrics['spectral_softening_log_ratio'][trimmed]):.4f}"
        )

    lines.extend(["", "Median pair effects across trimmed stations:"])
    for comparison in (*PAIR_DEFINITIONS.keys(), "interaction"):
        lines.append(f"- {PAIR_LABELS[comparison]}:")
        for metric_name in PRIMARY_METRICS:
            values = effects[f"{comparison}__{metric_name}"][trimmed]
            lines.append(
                f"  {metric_name}: median={np.nanmedian(values):.6g}, "
                f"IQR=[{np.nanpercentile(values, 25):.6g}, "
                f"{np.nanpercentile(values, 75):.6g}]"
            )

    lines.extend(["", "Strongest terrain relationships:"])
    for record in sorted(terrain_records, key=lambda item: -abs(item["rho"]))[:30]:
        lines.append(
            f"- {record['outcome']} vs {record['predictor']}: "
            f"rho={record['rho']:.4f}, q={record['q_value']:.4g}, "
            f"ray=({record['ray1_rho']:.3f},{record['ray2_rho']:.3f},"
            f"{record['ray3_rho']:.3f})"
        )

    lines.extend(["", "Signature persistence:"])
    for record in sorted(signature_records, key=lambda item: -abs(item["rho"])):
        lines.append(
            f"- {record['signature']} {record['metric']}: "
            f"rho={record['rho']:.4f}, q={record['q_value']:.4g}"
        )

    lines.extend(["", "Piecewise distance transitions with delta AIC > 6:"])
    for record in breakpoints:
        if record["delta_aic"] > 6.0:
            lines.append(
                f"- {record['comparison']} {record['metric']} ray {record['ray']}: "
                f"break={record['breakpoint_km']:.2f} km, "
                f"slope_before={record['slope_before']:.4g}, "
                f"slope_after={record['slope_after']:.4g}, "
                f"delta_AIC={record['delta_aic']:.2f}"
            )
    (OUTPUT_DIR / "literature_guided_summary.txt").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    station_xy, ray_station_indices = build_station_geometry()
    features = build_station_features(station_xy, ray_station_indices)
    model_metrics = tuple(process_model(index) for index in range(4))
    effects = build_effects(model_metrics)
    terrain_records = compute_terrain_relationships(effects, features)
    signature_records = compute_signature_persistence(effects, features)
    breakpoints = compute_breakpoints(effects, features)
    lag_records = compute_spatial_lags(effects, features)

    write_station_table(features, model_metrics, effects)
    write_effect_summary(effects, features)
    write_block_bootstrap_effects(effects, features)
    write_frequency_summary(model_metrics, features)
    write_frequency_trends(model_metrics, features)
    write_tmax_smoothing_summary(effects, features)
    write_dict_table("literature_guided_terrain_relationships.csv", terrain_records)
    write_dict_table("literature_guided_signature_persistence.csv", signature_records)
    write_dict_table("literature_guided_breakpoints.csv", breakpoints)
    write_dict_table("literature_guided_spatial_lags.csv", lag_records)
    write_machine_summary(
        model_metrics,
        effects,
        features,
        terrain_records,
        signature_records,
        breakpoints,
    )
    plot_frequency_dependence(model_metrics, features)
    plot_scattering_separation(effects, features)
    plot_breakpoint_profiles(effects, features, breakpoints)
    plot_top_terrain_relationships(terrain_records)
    plot_model_metric_synthesis(model_metrics, features)
    plot_factorial_effect_heatmap(effects, features)
    print(f"Literature-guided analysis complete: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
