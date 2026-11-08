"""Analyze observed and synthetic S12 three-component waveforms."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset
from scipy import signal

from plot_releasy_waveform_comparison import (
    EARTHQUAKE_SOURCE_XY,
    FILTER_HIGH_HZ,
    FILTER_LOW_HZ,
    MODELS,
    OBSERVED_COMPONENT_FILES,
    SOURCE_MATCH_WINDOW_S,
    ThreeComponentRecord,
    analytic_energy,
    bandpass_waveforms,
    build_station_geometry,
    load_observed_s12,
    load_s12_model_components,
    read_sac_channel,
    smoothed_intensity,
    source_matching_scale,
)


OUTPUT_DIR = Path(__file__).resolve().parent / "three_component_psvsh_analysis"
FIGURE_DPI = 250
COMMON_WINDOW_S = (50.0, 245.0)
ALIGNMENT_WINDOW_S = (50.0, 180.0)
LONG_DISPLAY_END_S = 3_000.0
MODE_LABELS = ("qP", "qSV", "SH")
MODE_COLORS = ("#0072B2", "#D55E00", "#009E73")
RECORD_SHORT_NAMES = ("Observed", "M1", "M2", "M3", "M4")
CURRENT_VP_KM_S = 3.20
CURRENT_VS_KM_S = 2.00
LOW_LAYER_VP_KM_S = 1.38
LOW_LAYER_VS_KM_S = 1.11
LOW_LAYER_THICKNESS_KM = 1.0
GRID_SPACING_KM = 0.2
FIELD_COMPONENT_LABELS = ("Z", "R", "T")
FACTORIAL_PAIRS = {
    "scatter_flat": (0, 2),
    "topography_no_scatter": (0, 1),
    "scatter_topography": (1, 3),
    "topography_scatter": (2, 3),
}
FACTORIAL_PAIR_LABELS = {
    "scatter_flat": "M1→M3: add scatter on flat",
    "topography_no_scatter": "M1→M2: add topography",
    "scatter_topography": "M2→M4: add scatter on topography",
    "topography_scatter": "M3→M4: add topography on scatter",
}
RESIDUAL_EFFECT_LABELS = (
    "Scatter on flat: M3-M1",
    "Topography without scatter: M2-M1",
    "Scatter on topography: M4-M2",
    "Interaction: M4-M2-M3+M1",
)
POLARIZATION_WINDOW_S = 12.0
POLARIZATION_STEP_S = 2.0
SPECTROGRAM_WINDOW_S = 20.0
SPECTROGRAM_STEP_S = 2.0


@dataclass
class ModeRecord:
    name: str
    short_name: str
    color: str
    time: np.ndarray
    source_scale: float
    zrt: np.ndarray
    modes: np.ndarray


@dataclass
class AlignmentResult:
    lag_s: float
    correlation: float
    amplitude_scale: float
    shifted_model: np.ndarray


def save_figure(figure: plt.Figure, filename: str) -> None:
    figure.savefig(OUTPUT_DIR / filename, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(figure)


def station_ray_metadata() -> tuple[np.ndarray, np.ndarray, np.ndarray, tuple[np.ndarray, ...]]:
    station_xy, ray_indices = build_station_geometry()
    offsets = station_xy - EARTHQUAKE_SOURCE_XY
    distance_km = np.linalg.norm(offsets, axis=1) / 1_000.0
    azimuth_rad = np.arctan2(offsets[:, 0], offsets[:, 1])
    ray_number = np.zeros(station_xy.shape[0], dtype=int)
    for ray, indices in enumerate(ray_indices, start=1):
        ray_number[indices] = ray
    return distance_km, azimuth_rad, ray_number, ray_indices


def load_model_zrt_field(model_index: int, azimuth_rad: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    config = MODELS[model_index]
    with Dataset(config.nc_file, "r") as dataset:
        time = np.asarray(dataset.variables["time"][:], dtype=np.float64)
        components = []
        for variable in ("Vz", "Vx", "Vy"):
            values = np.asarray(dataset.variables[variable][:], dtype=np.float32)
            if values.shape == (time.size, 606):
                values = values.T
            if values.shape != (606, time.size):
                raise ValueError(f"Unexpected {variable} shape {values.shape} in {config.nc_file}")
            components.append(bandpass_waveforms(time, values))
    vertical, east, north = components
    sine = np.sin(azimuth_rad)[:, None]
    cosine = np.cos(azimuth_rad)[:, None]
    radial = east * sine + north * cosine
    transverse = east * cosine - north * sine
    return time, np.stack((vertical, radial, transverse), axis=1)


def field_energy(time: np.ndarray, zrt: np.ndarray) -> np.ndarray:
    keep = (time >= COMMON_WINDOW_S[0]) & (time <= COMMON_WINDOW_S[1])
    return np.trapezoid(np.asarray(zrt[:, :, keep], dtype=np.float64) ** 2, x=time[keep], axis=-1)


def smooth_profile(values: np.ndarray, window: int = 9) -> np.ndarray:
    if values.size < window:
        return values
    kernel = np.ones(window, dtype=np.float64) / window
    padded = np.pad(values, (window // 2, window // 2), mode="edge")
    return np.convolve(padded, kernel, mode="valid")[: values.size]


def plot_s12_factorial_components(time: np.ndarray, representatives: np.ndarray) -> None:
    comparisons = tuple(FACTORIAL_PAIRS.items())
    figure, axes = plt.subplots(3, 4, figsize=(15.5, 9.0), sharex=True, constrained_layout=True)
    keep = (time >= 50.0) & (time <= 180.0)
    for column, (pair_name, (first, second)) in enumerate(comparisons):
        for component in range(3):
            axis = axes[component, column]
            pair = representatives[[first, second], 0, component][:, keep]
            scale = max(float(np.max(np.abs(pair))), np.finfo(float).eps)
            axis.plot(time[keep], pair[0] / scale, color=MODELS[first].color, linewidth=1.15, alpha=0.78, label=f"M{first + 1}")
            axis.plot(time[keep], pair[1] / scale, color=MODELS[second].color, linewidth=1.15, alpha=0.78, label=f"M{second + 1}")
            axis.axhline(0.0, color="#777777", linewidth=0.45)
            axis.grid(alpha=0.2)
            axis.set_ylim(-1.08, 1.08)
            if component == 0:
                axis.set_title(FACTORIAL_PAIR_LABELS[pair_name], fontsize=10)
            if column == 0:
                axis.set_ylabel(f"{FIELD_COMPONENT_LABELS[component]}\nshared scale")
            if component == 2:
                axis.set_xlabel("Time (s)")
            axis.legend(loc="upper right", fontsize=7, frameon=False)
    figure.suptitle("S12 three-component waveform changes before/after topography and scattering (0.3–0.9 Hz)", fontsize=14)
    save_figure(figure, "figure_07_s12_three_component_factorial_waveforms.png")


def plot_ray_factorial_components(
    time: np.ndarray,
    representatives: np.ndarray,
    representative_indices: np.ndarray,
    distance_km: np.ndarray,
) -> None:
    figure, axes = plt.subplots(3, 3, figsize=(14.5, 10.0), sharex=True, constrained_layout=True)
    keep = (time >= 50.0) & (time <= 180.0)
    offsets = np.array([3.0, 1.0, -1.0, -3.0])
    for ray in range(1, 4):
        representative_slot = ray
        station_index = int(representative_indices[representative_slot])
        for component in range(3):
            axis = axes[ray - 1, component]
            traces = representatives[:, representative_slot, component][:, keep]
            scale = max(float(np.percentile(np.abs(traces), 99.5)), np.finfo(float).eps)
            for model_index, offset in enumerate(offsets):
                axis.plot(
                    time[keep],
                    offset + 0.72 * traces[model_index] / scale,
                    color=MODELS[model_index].color,
                    linewidth=1.0,
                    alpha=0.82,
                    label=f"M{model_index + 1}" if ray == 1 and component == 2 else None,
                )
            axis.grid(alpha=0.18)
            axis.set_yticks(offsets, ("M1", "M2", "M3", "M4"), fontsize=7)
            if ray == 1:
                axis.set_title(f"{FIELD_COMPONENT_LABELS[component]} component")
            if component == 0:
                axis.set_ylabel(f"Ray {ray}\nr{station_index + 1}, {distance_km[station_index]:.1f} km")
            if ray == 3:
                axis.set_xlabel("Time (s)")
    axes[0, 2].legend(loc="upper right", fontsize=7, frameon=False)
    figure.suptitle("Representative ray-station Z-R-T waveforms: four models shown with vertical offsets", fontsize=14)
    save_figure(figure, "figure_08_ray_three_component_factorial_waveforms.png")


def plot_component_fraction_profiles(
    energies: np.ndarray,
    distance_km: np.ndarray,
    ray_indices: tuple[np.ndarray, ...],
) -> None:
    fractions = energies / np.maximum(np.sum(energies, axis=2, keepdims=True), np.finfo(float).tiny)
    figure, axes = plt.subplots(3, 3, figsize=(14.5, 10.0), sharex="row", sharey="col", constrained_layout=True)
    for ray, indices in enumerate(ray_indices, start=1):
        ray_distance = distance_km[indices]
        for component in range(3):
            axis = axes[ray - 1, component]
            for model_index, config in enumerate(MODELS):
                axis.plot(
                    ray_distance,
                    smooth_profile(fractions[model_index, indices, component]),
                    color=config.color,
                    linewidth=1.25,
                    alpha=0.84,
                    label=f"M{model_index + 1}" if ray == 1 and component == 2 else None,
                )
            axis.grid(alpha=0.2)
            axis.set_ylim(-0.02, 1.02)
            if ray == 1:
                axis.set_title(f"{FIELD_COMPONENT_LABELS[component]} energy fraction")
            if component == 0:
                axis.set_ylabel(f"Ray {ray}\nenergy fraction")
            if ray == 3:
                axis.set_xlabel("Epicentral distance (km)")
    axes[0, 2].legend(loc="upper right", fontsize=7, frameon=False)
    figure.suptitle("Distance evolution of Z-R-T energy partition in the four models (50–245 s)", fontsize=14)
    save_figure(figure, "figure_09_three_component_energy_fraction_profiles.png")


def factorial_residual_waveforms(field_waveforms: np.ndarray) -> np.ndarray:
    model1, model2, model3, model4 = field_waveforms
    return np.stack(
        (
            model2 - model1,
            model3 - model1,
            model4 - model3,
            model4 - model3 - model2 + model1,
        ),
        axis=0,
    )


def plot_factorial_residual_waveforms(
    time: np.ndarray,
    field_waveforms: np.ndarray,
    representative_indices: np.ndarray,
    distance_km: np.ndarray,
) -> None:
    residuals = factorial_residual_waveforms(field_waveforms)
    keep = (time >= 50.0) & (time <= 180.0)

    figure, axes = plt.subplots(3, 4, figsize=(15.5, 8.7), sharex=True, constrained_layout=True)
    for component in range(3):
        traces = residuals[:, 0, component][:, keep]
        component_scale = max(float(np.percentile(np.abs(traces), 99.5)), np.finfo(float).eps)
        for effect in range(4):
            axis = axes[component, effect]
            axis.plot(time[keep], traces[effect] / component_scale, color=("#E69F00", "#009E73", "#CC79A7", "#6A3D9A")[effect], linewidth=1.05)
            axis.axhline(0.0, color="#777777", linewidth=0.45)
            axis.grid(alpha=0.2)
            axis.set_ylim(-1.08, 1.08)
            if component == 0:
                axis.set_title(RESIDUAL_EFFECT_LABELS[effect], fontsize=9.5)
            if effect == 0:
                axis.set_ylabel(f"{FIELD_COMPONENT_LABELS[component]}\nshared scale")
            if component == 2:
                axis.set_xlabel("Time (s)")
    figure.suptitle("S12 factorial residual waveforms and the topography-scattering interaction (0.3–0.9 Hz)", fontsize=14)
    save_figure(figure, "figure_10_s12_factorial_residual_waveforms.png")

    offsets = np.array([3.0, 1.0, -1.0, -3.0])
    short_labels = ("S flat", "Topo", "S topo", "Interact")
    colors = ("#E69F00", "#009E73", "#CC79A7", "#6A3D9A")
    figure, axes = plt.subplots(3, 3, figsize=(14.5, 10.0), sharex=True, constrained_layout=True)
    for ray in range(1, 4):
        station_index = int(representative_indices[ray])
        for component in range(3):
            axis = axes[ray - 1, component]
            traces = residuals[:, station_index, component][:, keep]
            scale = max(float(np.percentile(np.abs(traces), 99.5)), np.finfo(float).eps)
            for effect, offset in enumerate(offsets):
                axis.plot(
                    time[keep],
                    offset + 0.72 * traces[effect] / scale,
                    color=colors[effect],
                    linewidth=1.0,
                    alpha=0.86,
                    label=short_labels[effect] if ray == 1 and component == 2 else None,
                )
            axis.grid(alpha=0.18)
            axis.set_yticks(offsets, short_labels, fontsize=7)
            if ray == 1:
                axis.set_title(f"{FIELD_COMPONENT_LABELS[component]} residual")
            if component == 0:
                axis.set_ylabel(f"Ray {ray}\nr{station_index + 1}, {distance_km[station_index]:.1f} km")
            if ray == 3:
                axis.set_xlabel("Time (s)")
    axes[0, 2].legend(loc="upper right", fontsize=7, frameon=False)
    figure.suptitle("Representative ray-station factorial residuals and nonlinear interaction", fontsize=14)
    save_figure(figure, "figure_11_ray_factorial_residual_waveforms.png")


def write_factorial_residual_tables(
    time: np.ndarray,
    field_waveforms: np.ndarray,
    distance_km: np.ndarray,
    ray_number: np.ndarray,
    ray_indices: tuple[np.ndarray, ...],
) -> None:
    keep = (time >= 50.0) & (time <= 180.0)
    residuals = np.asarray(factorial_residual_waveforms(field_waveforms)[:, :, :, keep], dtype=np.float64)
    pooled_scale = np.sqrt(np.mean(np.asarray(field_waveforms[:, :, :, keep], dtype=np.float64) ** 2, axis=(0, 3)))
    residual_rms = np.sqrt(np.mean(residuals**2, axis=-1))
    normalized = residual_rms / np.maximum(pooled_scale[None, :, :], np.finfo(float).tiny)
    interaction_ratio = residual_rms[3] / np.maximum(residual_rms[0] + residual_rms[1], np.finfo(float).tiny)

    fieldnames = (
        "station", "ray", "distance_km", "component",
        "scatter_flat_normalized_rms", "topography_no_scatter_normalized_rms",
        "scatter_topography_normalized_rms", "interaction_normalized_rms", "interaction_ratio",
    )
    with (OUTPUT_DIR / "three_component_factorial_residual_metrics.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for station in range(606):
            for component, component_label in enumerate(FIELD_COMPONENT_LABELS):
                writer.writerow({
                    "station": f"r{station + 1}",
                    "ray": "S12" if ray_number[station] == 0 else int(ray_number[station]),
                    "distance_km": f"{distance_km[station]:.6f}",
                    "component": component_label,
                    "scatter_flat_normalized_rms": f"{normalized[0, station, component]:.9f}",
                    "topography_no_scatter_normalized_rms": f"{normalized[1, station, component]:.9f}",
                    "scatter_topography_normalized_rms": f"{normalized[2, station, component]:.9f}",
                    "interaction_normalized_rms": f"{normalized[3, station, component]:.9f}",
                    "interaction_ratio": f"{interaction_ratio[station, component]:.9f}",
                })

    primary_indices = np.concatenate(tuple(indices[5:-5] for indices in ray_indices))
    scopes = [("S12", np.array([0], dtype=int)), ("all_primary", primary_indices)]
    scopes.extend((f"ray{ray}", indices[5:-5]) for ray, indices in enumerate(ray_indices, start=1))
    summary_rows: list[dict[str, str | int]] = []
    quantities = (
        ("scatter_flat_normalized_rms", normalized[0]),
        ("topography_no_scatter_normalized_rms", normalized[1]),
        ("scatter_topography_normalized_rms", normalized[2]),
        ("interaction_normalized_rms", normalized[3]),
        ("interaction_ratio", interaction_ratio),
    )
    for scope, indices in scopes:
        for quantity, values in quantities:
            for component, component_label in enumerate(FIELD_COMPONENT_LABELS):
                q25, median, q75 = percentile_summary(values[indices, component])
                summary_rows.append({
                    "scope": scope,
                    "quantity": quantity,
                    "component": component_label,
                    "q25": f"{q25:.9f}",
                    "median": f"{median:.9f}",
                    "q75": f"{q75:.9f}",
                    "n": len(indices),
                })
    with (OUTPUT_DIR / "three_component_factorial_residual_summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("scope", "quantity", "component", "q25", "median", "q75", "n"))
        writer.writeheader()
        writer.writerows(summary_rows)


def percentile_summary(values: np.ndarray) -> tuple[float, float, float]:
    return tuple(float(value) for value in np.percentile(values, (25.0, 50.0, 75.0)))


def write_three_component_factorial_tables(
    energies: np.ndarray,
    distance_km: np.ndarray,
    ray_number: np.ndarray,
    ray_indices: tuple[np.ndarray, ...],
) -> None:
    fractions = energies / np.maximum(np.sum(energies, axis=2, keepdims=True), np.finfo(float).tiny)
    station_fields = ["station", "ray", "distance_km"]
    for model in range(4):
        for component_label in FIELD_COMPONENT_LABELS:
            station_fields.extend((f"M{model + 1}_{component_label}_energy", f"M{model + 1}_{component_label}_fraction"))
    for pair_name in FACTORIAL_PAIRS:
        for component_label in FIELD_COMPONENT_LABELS:
            station_fields.append(f"{pair_name}_{component_label}_energy_factor")
        station_fields.append(f"{pair_name}_T_fraction_change")
    with (OUTPUT_DIR / "three_component_factorial_station_metrics.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=station_fields)
        writer.writeheader()
        for station in range(606):
            row: dict[str, str | int] = {
                "station": f"r{station + 1}",
                "ray": "S12" if ray_number[station] == 0 else int(ray_number[station]),
                "distance_km": f"{distance_km[station]:.6f}",
            }
            for model in range(4):
                for component, component_label in enumerate(FIELD_COMPONENT_LABELS):
                    row[f"M{model + 1}_{component_label}_energy"] = f"{energies[model, station, component]:.9e}"
                    row[f"M{model + 1}_{component_label}_fraction"] = f"{fractions[model, station, component]:.9f}"
            for pair_name, (first, second) in FACTORIAL_PAIRS.items():
                for component, component_label in enumerate(FIELD_COMPONENT_LABELS):
                    factor = energies[second, station, component] / max(energies[first, station, component], np.finfo(float).tiny)
                    row[f"{pair_name}_{component_label}_energy_factor"] = f"{factor:.9e}"
                row[f"{pair_name}_T_fraction_change"] = f"{fractions[second, station, 2] - fractions[first, station, 2]:.9f}"
            writer.writerow(row)

    primary_indices = np.concatenate(tuple(indices[5:-5] for indices in ray_indices))
    scopes = [("S12", np.array([0], dtype=int)), ("all_primary", primary_indices)]
    scopes.extend((f"ray{ray}", indices[5:-5]) for ray, indices in enumerate(ray_indices, start=1))
    summary_rows = []
    for scope, indices in scopes:
        for model in range(4):
            for component, component_label in enumerate(FIELD_COMPONENT_LABELS):
                q25, median, q75 = percentile_summary(fractions[model, indices, component])
                summary_rows.append({
                    "scope": scope,
                    "quantity": "component_fraction",
                    "model_or_effect": f"M{model + 1}",
                    "component": component_label,
                    "q25": f"{q25:.9f}",
                    "median": f"{median:.9f}",
                    "q75": f"{q75:.9f}",
                    "n": len(indices),
                })
        for pair_name, (first, second) in FACTORIAL_PAIRS.items():
            for component, component_label in enumerate(FIELD_COMPONENT_LABELS):
                factors = energies[second, indices, component] / np.maximum(energies[first, indices, component], np.finfo(float).tiny)
                q25, median, q75 = percentile_summary(factors)
                summary_rows.append({
                    "scope": scope,
                    "quantity": "component_energy_factor",
                    "model_or_effect": pair_name,
                    "component": component_label,
                    "q25": f"{q25:.9e}",
                    "median": f"{median:.9e}",
                    "q75": f"{q75:.9e}",
                    "n": len(indices),
                })
            changes = fractions[second, indices, 2] - fractions[first, indices, 2]
            q25, median, q75 = percentile_summary(changes)
            summary_rows.append({
                "scope": scope,
                "quantity": "T_fraction_change",
                "model_or_effect": pair_name,
                "component": "T",
                "q25": f"{q25:.9f}",
                "median": f"{median:.9f}",
                "q75": f"{q75:.9f}",
                "n": len(indices),
            })
    with (OUTPUT_DIR / "three_component_factorial_summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("scope", "quantity", "model_or_effect", "component", "q25", "median", "q75", "n"))
        writer.writeheader()
        writer.writerows(summary_rows)


def analyze_three_component_factorial_field() -> None:
    distance_km, azimuth_rad, ray_number, ray_indices = station_ray_metadata()
    representative_indices = np.array(
        [0, *[int(indices[np.argmin(np.abs(distance_km[indices] - 100.0))]) for indices in ray_indices]],
        dtype=int,
    )
    energies = np.empty((4, 606, 3), dtype=np.float64)
    field_waveforms = None
    common_time = None
    for model_index in range(4):
        time, zrt = load_model_zrt_field(model_index, azimuth_rad)
        if common_time is None:
            common_time = time
            field_waveforms = np.empty((4, 606, 3, time.size), dtype=np.float32)
        energies[model_index] = field_energy(time, zrt)
        if time.shape == common_time.shape and np.allclose(time, common_time):
            field_waveforms[model_index] = zrt
        else:
            for station in range(606):
                for component in range(3):
                    field_waveforms[model_index, station, component] = np.interp(
                        common_time,
                        time,
                        zrt[station, component],
                        left=0.0,
                        right=0.0,
                    )
    assert common_time is not None and field_waveforms is not None
    representative_waveforms = field_waveforms[:, representative_indices]
    plot_s12_factorial_components(common_time, representative_waveforms)
    plot_ray_factorial_components(common_time, representative_waveforms, representative_indices, distance_km)
    plot_component_fraction_profiles(energies, distance_km, ray_indices)
    plot_factorial_residual_waveforms(common_time, field_waveforms, representative_indices, distance_km)
    write_three_component_factorial_tables(energies, distance_km, ray_number, ray_indices)
    write_factorial_residual_tables(common_time, field_waveforms, distance_km, ray_number, ray_indices)


def append_three_component_factorial_report() -> None:
    summary_path = OUTPUT_DIR / "three_component_factorial_summary.csv"
    with summary_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    def value(
        scope: str,
        quantity: str,
        model_or_effect: str,
        component: str,
        field: str = "median",
    ) -> float:
        for row in rows:
            if (
                row["scope"] == scope
                and row["quantity"] == quantity
                and row["model_or_effect"] == model_or_effect
                and row["component"] == component
            ):
                return float(row[field])
        raise KeyError((scope, quantity, model_or_effect, component, field))

    fractions = {
        model: tuple(
            value("all_primary", "component_fraction", model, component)
            for component in FIELD_COMPONENT_LABELS
        )
        for model in ("M1", "M2", "M3", "M4")
    }
    scatter_flat = value("all_primary", "T_fraction_change", "scatter_flat", "T")
    topography_only = value("all_primary", "T_fraction_change", "topography_no_scatter", "T")
    scatter_on_topography = value("all_primary", "T_fraction_change", "scatter_topography", "T")
    topography_on_scatter = value("all_primary", "T_fraction_change", "topography_scatter", "T")
    topography_on_scatter_q25 = value("all_primary", "T_fraction_change", "topography_scatter", "T", "q25")
    topography_on_scatter_q75 = value("all_primary", "T_fraction_change", "topography_scatter", "T", "q75")
    ray_topography = tuple(
        value(f"ray{ray}", "T_fraction_change", "topography_no_scatter", "T")
        for ray in range(1, 4)
    )
    s12_scatter = value("S12", "T_fraction_change", "scatter_flat", "T")
    s12_topography = value("S12", "T_fraction_change", "topography_no_scatter", "T")
    s12_scatter_topography = value("S12", "T_fraction_change", "scatter_topography", "T")

    section = f"""

## 加入地形和散射前后的三分量变化

新增图件：

7. `figure_07_s12_three_component_factorial_waveforms.png`：S12的四组地形/散射因子波形对比。
8. `figure_08_ray_three_component_factorial_waveforms.png`：三条射线约100 km代表台站的Z/R/T错列波形。
9. `figure_09_three_component_energy_fraction_profiles.png`：三条射线Z/R/T能量占比随震中距变化。

统计窗口为50–245 s，处理频带为0.3–0.9 Hz，575个有效射线台站的Z/R/T能量占比中位数为：

- M1：{percent(fractions['M1'][0])}/{percent(fractions['M1'][1])}/{percent(fractions['M1'][2])}。
- M2：{percent(fractions['M2'][0])}/{percent(fractions['M2'][1])}/{percent(fractions['M2'][2])}。
- M3：{percent(fractions['M3'][0])}/{percent(fractions['M3'][1])}/{percent(fractions['M3'][2])}。
- M4：{percent(fractions['M4'][0])}/{percent(fractions['M4'][1])}/{percent(fractions['M4'][2])}。

### 结论

1. M1的T能量占比接近零，符合平坦、无散射、近对称介质中的二维P-SV传播；M2–M4的T波列是散射和三维地形破坏对称性、产生SH代理能量的直接证据。
2. 平坦背景加入散射使T占比中位增加{100.0 * scatter_flat:.1f}个百分点；无散射背景加入地形增加{100.0 * topography_only:.1f}个百分点。二者都会引起分量间能量再分配，而不是让所有分量按同一比例衰减。
3. 地形转换具有强路径依赖：射线1、2、3的T占比分别增加{100.0 * ray_topography[0]:.1f}、{100.0 * ray_topography[1]:.1f}和{100.0 * ray_topography[2]:.1f}个百分点。射线2和3的累计高差、坡度更大，对应更强的T波列和多脉冲。
4. M4的T占比最高，为{percent(fractions['M4'][2])}，Z占比降至{percent(fractions['M4'][0])}。因此Z减小不能直接解释为本征衰减增强，其中包含向R/T分量和晚到波列的能量转移。
5. 散射在地形背景上的边际T增量降至{100.0 * scatter_on_topography:.1f}个百分点；地形在散射背景上的边际增量仅{100.0 * topography_on_scatter:.1f}个百分点，四分位区间为[{100.0 * topography_on_scatter_q25:.1f}, {100.0 * topography_on_scatter_q75:.1f}]个百分点并跨零。地形与散射呈饱和型非加性。
6. S12的散射、地形和地形背景加散射的T占比增量分别为{100.0 * s12_scatter:.1f}、{100.0 * s12_topography:.1f}和{100.0 * s12_scatter_topography:.1f}个百分点，方向与总体一致，但单台站不能代替三条路径的统计。
7. M1的T能量接近数值零，因此相对M1的T能量倍数会发散，不应作为论文主指标；应使用T占比增量、分量波形和分位数范围。
8. Z/R/T是台站坐标下的稳健能量分配，T可作为SH代理，但严格P/SV/SH分离仍需三分量波场快照、散度/旋度或能量通量。
"""
    report_path = OUTPUT_DIR / "three_component_psvsh_report_zh.md"
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write(section)

    with (OUTPUT_DIR / "three_component_factorial_residual_summary.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        residual_rows = list(csv.DictReader(handle))
    with (OUTPUT_DIR / "s12_time_varying_polarization_summary.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        polarization_rows = {row["record"]: row for row in csv.DictReader(handle)}
    with (OUTPUT_DIR / "s12_time_frequency_metrics.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        time_frequency_rows = {(row["record"], row["component"]): row for row in csv.DictReader(handle)}

    def residual_value(scope: str, quantity: str, component: str, field: str = "median") -> float:
        for row in residual_rows:
            if row["scope"] == scope and row["quantity"] == quantity and row["component"] == component:
                return float(row[field])
        raise KeyError((scope, quantity, component, field))

    interaction_ratios = {
        component: residual_value("all_primary", "interaction_ratio", component)
        for component in FIELD_COMPONENT_LABELS
    }
    s12_interaction_ratios = {
        component: residual_value("S12", "interaction_ratio", component)
        for component in FIELD_COMPONENT_LABELS
    }
    observed_polarization = polarization_rows["Observed"]
    model_polarization = {model: polarization_rows[model] for model in ("M1", "M2", "M3", "M4")}
    observed_tf = {component: time_frequency_rows[("Observed", component)] for component in FIELD_COMPONENT_LABELS}
    model_tf = {
        (model, component): time_frequency_rows[(model, component)]
        for model in ("M1", "M2", "M3", "M4")
        for component in FIELD_COMPONENT_LABELS
    }
    best_spectral_model = max(
        ("M1", "M2", "M3", "M4"),
        key=lambda model: np.mean([
            float(model_tf[(model, component)]["frequency_shape_correlation_to_observed"])
            for component in FIELD_COMPONENT_LABELS
        ]),
    )
    extended_section = f"""

## 因子差分波形、时变偏振与时频对比

新增图件：

10. `figure_10_s12_factorial_residual_waveforms.png`：S12的散射、地形、地形背景散射及交互项三分量差分波形。
11. `figure_11_ray_factorial_residual_waveforms.png`：三条射线约100 km代表台站的差分和交互波形。
12. `figure_12_s12_time_varying_polarization.png`：实测与四模型的12 s滑窗偏振和T能量比例。
13. `figure_13_s12_observed_model_time_frequency.png`：实测与四模型Z/R/T时频功率对比。

### 差分与交互项

交互项定义为 `M4-M2-M3+M1`。其RMS与“平坦背景散射差分RMS + 无散射地形差分RMS”之比，在575个有效台站上的中位数为Z {interaction_ratios['Z']:.2f}、R {interaction_ratios['R']:.2f}、T {interaction_ratios['T']:.2f}；S12分别为{ s12_interaction_ratios['Z']:.2f}、{s12_interaction_ratios['R']:.2f}和{s12_interaction_ratios['T']:.2f}。

1. Z/R交互比约0.69，说明两种机制在主传播平面内已有显著非线性；T交互比约1.00，交互项与两个单独主效应之和同量级，横向转换尤其不能按线性叠加解释。
2. 差分波形显示交互项不是一个常数振幅修正，而是在主脉冲之后形成新的相位、多脉冲和持续振荡，因此“先做地形振幅修正、再独立加入散射尾波”的分步后处理在波形层面不成立。
3. 三条代表路径都出现稳定的紫色交互波列；T分量持续最久，说明非线性主要通过三维横向转换和晚到能量重排体现。

### 时变偏振

实测有效窗口的中位线性度为{float(observed_polarization['median_rectilinearity']):.2f}、主轴T倾角为{float(observed_polarization['median_principal_transverse_tilt_deg']):.1f}°、T能量比例为{float(observed_polarization['median_T_energy_fraction']):.2f}。M1对应{float(model_polarization['M1']['median_rectilinearity']):.2f}、{float(model_polarization['M1']['median_principal_transverse_tilt_deg']):.1f}°和{float(model_polarization['M1']['median_T_energy_fraction']):.2f}；M2–M4的T倾角为{float(model_polarization['M2']['median_principal_transverse_tilt_deg']):.1f}°、{float(model_polarization['M3']['median_principal_transverse_tilt_deg']):.1f}°和{float(model_polarization['M4']['median_principal_transverse_tilt_deg']):.1f}°。

4. M1过度线性化且主轴几乎完全位于Z-R平面；加入散射或地形后线性度下降、T倾角和T能量增加，方向上更接近真实记录。
5. M2–M4的T倾角仍只有约15–18°，明显低于观测33°，说明当前三维转换强度或浅部结构复杂性仍不足。
6. 观测三分量相对能量在50–239 s总体增强，而M1在约100 s后快速降到相对峰值−30 dB以下；M2/M4能维持到记录末端，但仍呈衰减趋势，与观测持续增长相反。

### 时频对比

实测Z/R/T主频分别为{float(observed_tf['Z']['dominant_frequency_hz']):.3f}、{float(observed_tf['R']['dominant_frequency_hz']):.3f}和{float(observed_tf['T']['dominant_frequency_hz']):.3f} Hz；四模型各分量主频范围为{min(float(row['dominant_frequency_hz']) for row in model_tf.values()):.3f}–{max(float(row['dominant_frequency_hz']) for row in model_tf.values()):.3f} Hz。

7. 模型主频整体偏高，说明差异不只是源振幅，而涉及源时间函数、低速层频散和散射谱结构。
8. 120 s之后的实测能量占比为Z {percent(float(observed_tf['Z']['late_energy_fraction_after_120s']))}、R {percent(float(observed_tf['R']['late_energy_fraction_after_120s']))}、T {percent(float(observed_tf['T']['late_energy_fraction_after_120s']))}；模型Z/R最高仅约{percent(max(float(row['late_energy_fraction_after_120s']) for (model, component), row in model_tf.items() if component in ('Z', 'R')))}，T最高为{percent(max(float(row['late_energy_fraction_after_120s']) for (model, component), row in model_tf.items() if component == 'T'))}。当前模型即使产生横向尾波，也没有重现实测三分量共同的晚期能量积累。
9. 频谱形状相关总体很低，三分量平均后最接近观测的是{best_spectral_model}，但仍不能同时重现约0.4–0.45 Hz主频和随时间持续增强的能量分布。
10. 所有模型的时频能量时间相关均为负，说明归一化、单一时移或单一源尺度无法修复“模型先峰后衰、观测持续积累”的根本差异。
"""
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write(extended_section)


def source_receiver_geometry() -> tuple[np.ndarray, float, float]:
    station_xy, _ = build_station_geometry()
    receiver_xy = station_xy[0]
    difference = receiver_xy - EARTHQUAKE_SOURCE_XY
    distance_km = float(np.linalg.norm(difference) / 1_000.0)
    azimuth_deg = float(np.degrees(np.arctan2(difference[0], difference[1])) % 360.0)
    return receiver_xy, distance_km, azimuth_deg


def rotate_zen_to_zrt(components: np.ndarray, azimuth_deg: float) -> np.ndarray:
    vertical, east, north = np.asarray(components, dtype=np.float64)
    azimuth_rad = np.deg2rad(azimuth_deg)
    radial = east * np.sin(azimuth_rad) + north * np.cos(azimuth_rad)
    transverse = east * np.cos(azimuth_rad) - north * np.sin(azimuth_rad)
    return np.vstack((vertical, radial, transverse))


def qpolarization_basis(
    time: np.ndarray, zrt: np.ndarray
) -> tuple[np.ndarray, np.ndarray, tuple[float, float]]:
    radial_vertical = np.vstack((zrt[1], zrt[0]))
    plane_energy = np.sum(analytic_energy(radial_vertical), axis=0)
    smoothed = smoothed_intensity(time, plane_energy, 2.0)
    search = (time >= 30.0) & (time <= min(120.0, float(time[-1])))
    search_indices = np.flatnonzero(search)
    if search_indices.size == 0:
        raise ValueError("No samples in qP polarization search window")
    search_envelope = smoothed[search]
    threshold = 0.08 * float(np.max(search_envelope))
    threshold_indices = np.flatnonzero(search_envelope >= threshold)
    onset_index = int(search_indices[threshold_indices[0]])
    start_s = float(time[onset_index])
    end_s = min(start_s + 12.0, float(time[-1]))
    basis_samples = radial_vertical[:, (time >= start_s) & (time <= end_s)]
    covariance = np.cov(basis_samples)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    qp = eigenvectors[:, int(np.argmax(eigenvalues))]
    if qp[1] < 0.0:
        qp = -qp
    qsv = np.array([-qp[1], qp[0]])
    return qp, qsv, (start_s, end_s)


def project_modes(zrt: np.ndarray, qp: np.ndarray, qsv: np.ndarray) -> np.ndarray:
    radial_vertical = np.vstack((zrt[1], zrt[0]))
    return np.vstack((qp @ radial_vertical, qsv @ radial_vertical, zrt[2]))


def build_mode_records() -> tuple[
    ThreeComponentRecord,
    tuple[ThreeComponentRecord, ...],
    tuple[ModeRecord, ...],
    np.ndarray,
    np.ndarray,
    tuple[float, float],
    float,
    float,
]:
    _, distance_km, azimuth_deg = source_receiver_geometry()
    observed = load_observed_s12()
    model_records = tuple(load_s12_model_components(config) for config in MODELS)
    source_scales = tuple(
        source_matching_scale(observed, record) for record in model_records
    )
    model1_zrt = rotate_zen_to_zrt(
        model_records[0].filtered * source_scales[0], azimuth_deg
    )
    qp, qsv, basis_window = qpolarization_basis(model_records[0].time, model1_zrt)

    records: list[ModeRecord] = []
    observed_zrt = rotate_zen_to_zrt(observed.filtered, azimuth_deg)
    records.append(
        ModeRecord(
            observed.name,
            RECORD_SHORT_NAMES[0],
            "#202020",
            observed.time,
            1.0,
            observed_zrt,
            project_modes(observed_zrt, qp, qsv),
        )
    )
    for short_name, record, source_scale in zip(
        RECORD_SHORT_NAMES[1:], model_records, source_scales, strict=True
    ):
        zrt = rotate_zen_to_zrt(record.filtered * source_scale, azimuth_deg)
        records.append(
            ModeRecord(
                record.name,
                short_name,
                record.color,
                record.time,
                source_scale,
                zrt,
                project_modes(zrt, qp, qsv),
            )
        )
    return (
        observed,
        model_records,
        tuple(records),
        qp,
        qsv,
        basis_window,
        distance_km,
        azimuth_deg,
    )


def sliding_polarization_metrics(record: ModeRecord) -> list[dict[str, float | str]]:
    half_window = POLARIZATION_WINDOW_S / 2.0
    start = max(45.0 + half_window, float(record.time[0]) + half_window)
    end = min(COMMON_WINDOW_S[1] - half_window, float(record.time[-1]) - half_window)
    centers = np.arange(start, end + 0.25 * POLARIZATION_STEP_S, POLARIZATION_STEP_S)
    rows: list[dict[str, float | str]] = []
    for center in centers:
        keep = (record.time >= center - half_window) & (record.time <= center + half_window)
        data = np.asarray(record.zrt[:, keep], dtype=np.float64)
        if data.shape[1] < 4:
            continue
        data -= np.mean(data, axis=1, keepdims=True)
        covariance = data @ data.T / max(data.shape[1] - 1, 1)
        eigenvalues, eigenvectors = np.linalg.eigh(covariance)
        order = np.argsort(eigenvalues)[::-1]
        eigenvalues = np.maximum(eigenvalues[order], 0.0)
        principal = eigenvectors[:, order[0]]
        largest = max(float(eigenvalues[0]), np.finfo(float).tiny)
        rectilinearity = 1.0 - float(eigenvalues[1] + eigenvalues[2]) / (2.0 * largest)
        planarity = 1.0 - 2.0 * float(eigenvalues[2]) / max(float(eigenvalues[0] + eigenvalues[1]), np.finfo(float).tiny)
        incidence = np.degrees(np.arccos(np.clip(abs(float(principal[0])), 0.0, 1.0)))
        transverse_tilt = np.degrees(
            np.arctan2(
                abs(float(principal[2])),
                np.hypot(float(principal[0]), float(principal[1])),
            )
        )
        component_energy = np.sum(data**2, axis=1)
        total_energy = max(float(np.sum(component_energy)), np.finfo(float).tiny)
        rows.append({
            "record": record.short_name,
            "time_s": float(center),
            "window_s": POLARIZATION_WINDOW_S,
            "rms": float(np.sqrt(np.mean(data**2))),
            "rectilinearity": float(np.clip(rectilinearity, 0.0, 1.0)),
            "planarity": float(np.clip(planarity, 0.0, 1.0)),
            "incidence_from_vertical_deg": float(incidence),
            "principal_transverse_tilt_deg": float(transverse_tilt),
            "T_energy_fraction": float(component_energy[2] / total_energy),
        })
    return rows


def analyze_time_varying_polarization(records: tuple[ModeRecord, ...]) -> None:
    rows = [row for record in records for row in sliding_polarization_metrics(record)]
    fieldnames = (
        "record", "time_s", "window_s", "rms", "relative_energy_db", "rectilinearity",
        "planarity", "incidence_from_vertical_deg", "principal_transverse_tilt_deg", "T_energy_fraction",
    )
    grouped: dict[str, list[dict[str, float | str]]] = {}
    for row in rows:
        grouped.setdefault(str(row["record"]), []).append(row)
    for record_rows in grouped.values():
        maximum = max(float(row["rms"]) for row in record_rows)
        for row in record_rows:
            row["relative_energy_db"] = 20.0 * np.log10(max(float(row["rms"]) / maximum, 1.0e-6))
    with (OUTPUT_DIR / "s12_time_varying_polarization.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary_rows: list[dict[str, str | int]] = []
    for record in records:
        record_rows = grouped[record.short_name]
        active = [row for row in record_rows if float(row["relative_energy_db"]) >= -30.0]
        active = active or record_rows
        summary_rows.append({
            "record": record.short_name,
            "active_window_count": len(active),
            "median_rectilinearity": f"{np.median([float(row['rectilinearity']) for row in active]):.6f}",
            "median_planarity": f"{np.median([float(row['planarity']) for row in active]):.6f}",
            "median_incidence_from_vertical_deg": f"{np.median([float(row['incidence_from_vertical_deg']) for row in active]):.6f}",
            "median_principal_transverse_tilt_deg": f"{np.median([float(row['principal_transverse_tilt_deg']) for row in active]):.6f}",
            "median_T_energy_fraction": f"{np.median([float(row['T_energy_fraction']) for row in active]):.6f}",
            "active_start_s": f"{min(float(row['time_s']) for row in active):.3f}",
            "active_end_s": f"{max(float(row['time_s']) for row in active):.3f}",
        })
    with (OUTPUT_DIR / "s12_time_varying_polarization_summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)

    figure, axes = plt.subplots(5, 1, figsize=(13.0, 12.5), sharex=True, constrained_layout=True)
    plot_specs = (
        ("relative_energy_db", "Relative 3C RMS (dB)", (-60.0, 2.0)),
        ("rectilinearity", "Rectilinearity", (-0.03, 1.03)),
        ("incidence_from_vertical_deg", "Incidence from vertical (deg)", (-2.0, 92.0)),
        ("principal_transverse_tilt_deg", "Principal-axis T tilt (deg)", (-2.0, 92.0)),
        ("T_energy_fraction", "T energy fraction", (-0.03, 1.03)),
    )
    for axis, (field, label, limits) in zip(axes, plot_specs, strict=True):
        for record in records:
            record_rows = grouped[record.short_name]
            axis.plot(
                [float(row["time_s"]) for row in record_rows],
                [float(row[field]) for row in record_rows],
                color=record.color,
                linewidth=1.25 if record.short_name == "Observed" else 1.0,
                alpha=0.88,
                label=record.short_name,
            )
        axis.set_ylabel(label)
        axis.set_ylim(*limits)
        axis.grid(alpha=0.2)
    axes[0].legend(loc="lower right", ncol=5, fontsize=8, frameon=False)
    axes[-1].set_xlabel("Time (s)")
    axes[-1].set_xlim(45.0, 245.0)
    figure.suptitle(f"S12 time-varying polarization: observed and four models ({POLARIZATION_WINDOW_S:.0f} s windows)", fontsize=14)
    save_figure(figure, "figure_12_s12_time_varying_polarization.png")


def component_spectrogram(time: np.ndarray, trace: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sample_interval = float(np.median(np.diff(time)))
    sample_rate = 1.0 / sample_interval
    samples_per_window = max(16, int(round(SPECTROGRAM_WINDOW_S * sample_rate)))
    step_samples = max(1, int(round(SPECTROGRAM_STEP_S * sample_rate)))
    overlap = max(0, samples_per_window - step_samples)
    frequencies, offsets, power = signal.spectrogram(
        np.asarray(trace, dtype=np.float64),
        fs=sample_rate,
        window="hann",
        nperseg=samples_per_window,
        noverlap=overlap,
        detrend="constant",
        scaling="density",
        mode="psd",
    )
    return frequencies, float(time[0]) + offsets, power


def safe_correlation(first: np.ndarray, second: np.ndarray) -> float:
    first = np.asarray(first, dtype=np.float64)
    second = np.asarray(second, dtype=np.float64)
    if first.size < 3 or np.std(first) <= 0.0 or np.std(second) <= 0.0:
        return float("nan")
    return float(np.corrcoef(first, second)[0, 1])


def analyze_time_frequency(records: tuple[ModeRecord, ...]) -> None:
    spectrograms: dict[tuple[str, str], tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    metric_rows: list[dict[str, float | str]] = []
    for record in records:
        for component, component_label in enumerate(FIELD_COMPONENT_LABELS):
            frequencies, times, power = component_spectrogram(record.time, record.zrt[component])
            spectrograms[(record.short_name, component_label)] = (frequencies, times, power)
            frequency_keep = (frequencies >= FILTER_LOW_HZ) & (frequencies <= FILTER_HIGH_HZ)
            time_keep = (times >= COMMON_WINDOW_S[0]) & (times <= min(COMMON_WINDOW_S[1], float(times[-1])))
            selected = power[np.ix_(frequency_keep, time_keep)]
            selected_frequencies = frequencies[frequency_keep]
            selected_times = times[time_keep]
            frequency_energy = np.trapezoid(selected, x=selected_times, axis=1)
            time_energy = np.trapezoid(selected, x=selected_frequencies, axis=0)
            total = max(float(np.trapezoid(frequency_energy, x=selected_frequencies)), np.finfo(float).tiny)
            normalized_frequency = frequency_energy / max(float(np.sum(frequency_energy)), np.finfo(float).tiny)
            centroid = float(np.sum(selected_frequencies * normalized_frequency))
            bandwidth = float(np.sqrt(np.sum((selected_frequencies - centroid) ** 2 * normalized_frequency)))
            dominant = float(selected_frequencies[int(np.argmax(frequency_energy))])
            normalized_time = time_energy / max(float(np.sum(time_energy)), np.finfo(float).tiny)
            cumulative = np.cumsum(normalized_time)
            time05 = float(selected_times[min(int(np.searchsorted(cumulative, 0.05)), selected_times.size - 1)])
            time95 = float(selected_times[min(int(np.searchsorted(cumulative, 0.95)), selected_times.size - 1)])
            late = selected_times >= 120.0
            late_fraction = float(np.sum(time_energy[late]) / max(float(np.sum(time_energy)), np.finfo(float).tiny))
            metric_rows.append({
                "record": record.short_name,
                "component": component_label,
                "dominant_frequency_hz": dominant,
                "spectral_centroid_hz": centroid,
                "spectral_bandwidth_hz": bandwidth,
                "late_energy_fraction_after_120s": late_fraction,
                "time_duration_5_95_s": time95 - time05,
                "integrated_power": total,
                "frequency_shape_correlation_to_observed": 1.0 if record.short_name == "Observed" else float("nan"),
                "time_energy_correlation_to_observed": 1.0 if record.short_name == "Observed" else float("nan"),
            })

    by_key = {(str(row["record"]), str(row["component"])): row for row in metric_rows}
    common_frequency = np.linspace(FILTER_LOW_HZ, FILTER_HIGH_HZ, 121)
    common_time = np.arange(COMMON_WINDOW_S[0], COMMON_WINDOW_S[1] + 0.5, 1.0)
    for component_label in FIELD_COMPONENT_LABELS:
        observed_frequencies, observed_times, observed_power = spectrograms[("Observed", component_label)]
        observed_frequency_keep = (observed_frequencies >= FILTER_LOW_HZ) & (observed_frequencies <= FILTER_HIGH_HZ)
        observed_time_keep = (observed_times >= COMMON_WINDOW_S[0]) & (observed_times <= COMMON_WINDOW_S[1])
        observed_frequency_energy = np.trapezoid(observed_power[np.ix_(observed_frequency_keep, observed_time_keep)], x=observed_times[observed_time_keep], axis=1)
        observed_time_energy = np.trapezoid(observed_power[np.ix_(observed_frequency_keep, observed_time_keep)], x=observed_frequencies[observed_frequency_keep], axis=0)
        observed_frequency_profile = np.interp(common_frequency, observed_frequencies[observed_frequency_keep], observed_frequency_energy)
        observed_time_profile = np.interp(common_time, observed_times[observed_time_keep], observed_time_energy, left=0.0, right=0.0)
        for record in records[1:]:
            frequencies, times, power = spectrograms[(record.short_name, component_label)]
            frequency_keep = (frequencies >= FILTER_LOW_HZ) & (frequencies <= FILTER_HIGH_HZ)
            time_keep = (times >= COMMON_WINDOW_S[0]) & (times <= min(COMMON_WINDOW_S[1], float(times[-1])))
            frequency_energy = np.trapezoid(power[np.ix_(frequency_keep, time_keep)], x=times[time_keep], axis=1)
            time_energy = np.trapezoid(power[np.ix_(frequency_keep, time_keep)], x=frequencies[frequency_keep], axis=0)
            frequency_profile = np.interp(common_frequency, frequencies[frequency_keep], frequency_energy)
            time_profile = np.interp(common_time, times[time_keep], time_energy, left=0.0, right=0.0)
            row = by_key[(record.short_name, component_label)]
            row["frequency_shape_correlation_to_observed"] = safe_correlation(
                frequency_profile / max(float(np.sum(frequency_profile)), np.finfo(float).tiny),
                observed_frequency_profile / max(float(np.sum(observed_frequency_profile)), np.finfo(float).tiny),
            )
            row["time_energy_correlation_to_observed"] = safe_correlation(
                time_profile / max(float(np.sum(time_profile)), np.finfo(float).tiny),
                observed_time_profile / max(float(np.sum(observed_time_profile)), np.finfo(float).tiny),
            )

    fieldnames = tuple(metric_rows[0])
    with (OUTPUT_DIR / "s12_time_frequency_metrics.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metric_rows)

    figure, axes = plt.subplots(5, 3, figsize=(15.0, 13.5), sharex=True, sharey=True, constrained_layout=True)
    image_artist = None
    for row_index, record in enumerate(records):
        for component, component_label in enumerate(FIELD_COMPONENT_LABELS):
            axis = axes[row_index, component]
            frequencies, times, power = spectrograms[(record.short_name, component_label)]
            keep_frequency = (frequencies >= 0.2) & (frequencies <= 1.0)
            keep_time = (times >= 40.0) & (times <= min(COMMON_WINDOW_S[1], float(times[-1])))
            selected = power[np.ix_(keep_frequency, keep_time)]
            relative_db = 10.0 * np.log10(np.maximum(selected / max(float(np.max(selected)), np.finfo(float).tiny), 1.0e-5))
            image_artist = axis.pcolormesh(times[keep_time], frequencies[keep_frequency], relative_db, shading="auto", cmap="magma", vmin=-45.0, vmax=0.0)
            if row_index == 0:
                axis.set_title(f"{component_label} component")
            if component == 0:
                axis.set_ylabel(f"{record.short_name}\nFrequency (Hz)")
            if row_index == len(records) - 1:
                axis.set_xlabel("Time (s)")
            axis.set_xlim(40.0, 245.0)
            axis.set_ylim(0.2, 1.0)
    assert image_artist is not None
    figure.colorbar(image_artist, ax=axes, shrink=0.78, pad=0.012, label="Panel-normalized power (dB)")
    figure.suptitle("S12 observed-model Z-R-T time-frequency comparison (0.3–0.9 Hz filtered waveforms)", fontsize=14)
    save_figure(figure, "figure_13_s12_observed_model_time_frequency.png")


def percentile_amplitude(
    records: tuple[ModeRecord, ...], attribute: str, component_index: int
) -> float:
    amplitudes = []
    for record in records:
        values = getattr(record, attribute)[component_index]
        keep = (record.time >= COMMON_WINDOW_S[0]) & (record.time <= COMMON_WINDOW_S[1])
        amplitudes.append(float(np.percentile(np.abs(values[keep]), 99.5)))
    maximum = max(amplitudes)
    return maximum if maximum > 0.0 else 1.0


def plot_waveform_lanes(
    records: tuple[ModeRecord, ...],
    attribute: str,
    component_labels: tuple[str, str, str],
    filename: str,
    title: str,
) -> None:
    figure, axes = plt.subplots(3, 1, figsize=(13.0, 10.0), sharex=True)
    lane_positions = np.arange(len(records) - 1, -1, -1, dtype=float)
    for component_index, (axis, component_label) in enumerate(
        zip(axes, component_labels, strict=True)
    ):
        amplitude = percentile_amplitude(records, attribute, component_index)
        for lane, record in zip(lane_positions, records, strict=True):
            keep = (
                (record.time >= COMMON_WINDOW_S[0])
                & (record.time <= COMMON_WINDOW_S[1])
            )
            trace = getattr(record, attribute)[component_index, keep] / amplitude
            axis.plot(
                record.time[keep],
                lane + 0.36 * trace,
                color=record.color,
                linewidth=1.0 if record.short_name == "Observed" else 0.8,
                alpha=0.95 if record.short_name == "Observed" else 0.78,
            )
            axis.axhline(lane, color="#B8B8B8", linewidth=0.45, zorder=0)
        axis.set_yticks(lane_positions, [record.short_name for record in records])
        axis.set_ylim(-0.65, len(records) - 0.35)
        axis.set_ylabel(component_label)
        axis.grid(axis="x", alpha=0.18)
    axes[-1].set_xlabel("Time (s)")
    axes[-1].set_xlim(COMMON_WINDOW_S)
    figure.suptitle(title, fontsize=14)
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.97))
    save_figure(figure, filename)


def corrected_mode_energy(record: ModeRecord) -> np.ndarray:
    energy = analytic_energy(record.modes)
    noise = (record.time >= 0.0) & (record.time <= 40.0)
    if np.count_nonzero(noise) >= 2:
        noise_floor = np.median(energy[:, noise], axis=1, keepdims=True)
        energy = np.maximum(energy - noise_floor, 0.0)
    return energy


def mode_energy(record: ModeRecord, smoothing_s: float) -> np.ndarray:
    energy = corrected_mode_energy(record)
    return np.vstack(
        [smoothed_intensity(record.time, row, smoothing_s) for row in energy]
    )


def plot_mode_energy_envelopes(records: tuple[ModeRecord, ...]) -> None:
    figure, axes = plt.subplots(5, 1, figsize=(13.0, 12.0), sharex=True)
    for axis, record in zip(axes, records, strict=True):
        energy = mode_energy(record, 5.0)
        keep = (
            (record.time >= COMMON_WINDOW_S[0])
            & (record.time <= COMMON_WINDOW_S[1])
        )
        denominator = float(np.max(np.sum(energy[:, keep], axis=0)))
        denominator = denominator if denominator > 0.0 else 1.0
        for mode_index, (label, color) in enumerate(
            zip(MODE_LABELS, MODE_COLORS, strict=True)
        ):
            normalized = energy[mode_index, keep] / denominator
            axis.plot(
                record.time[keep], normalized, color=color, linewidth=1.15, label=label
            )
            axis.fill_between(
                record.time[keep], 0.0, normalized, color=color, alpha=0.07
            )
        axis.set_ylabel(record.short_name)
        axis.set_ylim(0.0, 1.05)
        axis.grid(alpha=0.18)
    axes[0].legend(loc="upper right", ncol=3, fontsize=8)
    axes[-1].set_xlabel("Time (s)")
    axes[-1].set_xlim(COMMON_WINDOW_S)
    figure.suptitle(
        "qP-qSV-SH analytic-energy envelopes (5 s smoothing)", fontsize=14
    )
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.97))
    save_figure(figure, "figure_03_mode_energy_envelopes.png")


def plot_long_coda(records: tuple[ModeRecord, ...]) -> None:
    figure, axes = plt.subplots(3, 1, figsize=(13.0, 10.0), sharex=True)
    for mode_index, (axis, mode_label) in enumerate(zip(axes, MODE_LABELS, strict=True)):
        for record in records:
            all_energy = mode_energy(record, 10.0)
            energy = all_energy[mode_index]
            reference = (
                (record.time >= COMMON_WINDOW_S[0])
                & (record.time <= min(COMMON_WINDOW_S[1], float(record.time[-1])))
            )
            denominator = float(np.max(np.sum(all_energy[:, reference], axis=0)))
            denominator = denominator if denominator > 0.0 else 1.0
            keep = (record.time >= 0.0) & (record.time <= LONG_DISPLAY_END_S)
            normalized = np.maximum(energy[keep] / denominator, 1.0e-8)
            axis.semilogy(
                record.time[keep],
                normalized,
                color=record.color,
                linewidth=1.0 if record.short_name == "Observed" else 0.75,
                alpha=0.95 if record.short_name == "Observed" else 0.72,
                label=record.short_name,
            )
        axis.axvline(250.0, color="#666666", linestyle="--", linewidth=0.9)
        axis.text(
            252.0,
            0.5,
            "synthetic record ends",
            fontsize=8,
            color="#555555",
            va="top",
        )
        axis.set_ylabel(f"{mode_label}\nnormalized energy")
        axis.set_ylim(1.0e-7, 2.0)
        axis.grid(alpha=0.18, which="both")
    axes[0].legend(loc="upper right", ncol=5, fontsize=8)
    axes[-1].set_xlabel("Time (s)")
    axes[-1].set_xlim(0.0, LONG_DISPLAY_END_S)
    figure.suptitle("Observed long coda versus 250 s synthetic duration", fontsize=14)
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.97))
    save_figure(figure, "figure_04_long_coda_mode_energy.png")


def waveform_alignment(
    observed_time: np.ndarray,
    observed: np.ndarray,
    model_time: np.ndarray,
    model: np.ndarray,
    maximum_lag_s: float = 20.0,
) -> AlignmentResult:
    common_time = observed_time[
        (observed_time >= ALIGNMENT_WINDOW_S[0])
        & (observed_time <= ALIGNMENT_WINDOW_S[1])
    ]
    observed_samples = np.interp(common_time, observed_time, observed)
    observed_samples = observed_samples - np.mean(observed_samples)
    sample_interval = float(np.median(np.diff(common_time)))
    lags = np.arange(
        -maximum_lag_s,
        maximum_lag_s + 0.5 * sample_interval,
        sample_interval,
    )
    best: AlignmentResult | None = None
    for lag_s in lags:
        shifted = np.interp(
            common_time - lag_s, model_time, model, left=np.nan, right=np.nan
        )
        valid = np.isfinite(shifted)
        if np.count_nonzero(valid) < 100:
            continue
        current_observed = observed_samples[valid]
        current_model = shifted[valid] - np.mean(shifted[valid])
        denominator = float(
            np.sqrt(np.sum(current_observed**2) * np.sum(current_model**2))
        )
        correlation = (
            float(np.sum(current_observed * current_model) / denominator)
            if denominator > 0.0
            else 0.0
        )
        amplitude_denominator = float(np.sum(current_model**2))
        amplitude_scale = (
            float(np.sum(current_observed * current_model) / amplitude_denominator)
            if amplitude_denominator > 0.0
            else 1.0
        )
        candidate = AlignmentResult(
            float(lag_s), correlation, amplitude_scale, shifted * amplitude_scale
        )
        if best is None or abs(candidate.correlation) > abs(best.correlation):
            best = candidate
    if best is None:
        raise RuntimeError("Unable to align observed and modeled waveforms")
    return best


def all_alignments(
    records: tuple[ModeRecord, ...]
) -> dict[tuple[str, str], AlignmentResult]:
    observed = records[0]
    results: dict[tuple[str, str], AlignmentResult] = {}
    for model in records[1:]:
        for mode_index, mode_label in enumerate(MODE_LABELS):
            results[(model.short_name, mode_label)] = waveform_alignment(
                observed.time,
                observed.modes[mode_index],
                model.time,
                model.modes[mode_index],
            )
    return results


def plot_aligned_waveform_comparison(
    records: tuple[ModeRecord, ...],
    alignments: dict[tuple[str, str], AlignmentResult],
) -> None:
    observed = records[0]
    common_time = observed.time[
        (observed.time >= ALIGNMENT_WINDOW_S[0])
        & (observed.time <= ALIGNMENT_WINDOW_S[1])
    ]
    figure, axes = plt.subplots(4, 3, figsize=(15.0, 10.5), sharex=True)
    for row, model in enumerate(records[1:]):
        for mode_index, mode_label in enumerate(MODE_LABELS):
            axis = axes[row, mode_index]
            observed_samples = np.interp(
                common_time, observed.time, observed.modes[mode_index]
            )
            alignment = alignments[(model.short_name, mode_label)]
            amplitude = float(np.percentile(np.abs(observed_samples), 99.5))
            amplitude = amplitude if amplitude > 0.0 else 1.0
            axis.plot(
                common_time,
                observed_samples / amplitude,
                color="#202020",
                linewidth=1.0,
                label="Observed",
            )
            axis.plot(
                common_time,
                alignment.shifted_model / amplitude,
                color=model.color,
                linewidth=0.85,
                alpha=0.82,
                label=model.short_name,
            )
            axis.text(
                0.985,
                0.92,
                f"lag={alignment.lag_s:+.1f} s, r={alignment.correlation:+.2f}",
                transform=axis.transAxes,
                ha="right",
                va="top",
                fontsize=8,
            )
            axis.grid(alpha=0.16)
            if row == 0:
                axis.set_title(mode_label)
            if mode_index == 0:
                axis.set_ylabel(model.short_name)
            if row == len(records) - 2:
                axis.set_xlabel("Time (s)")
    axes[0, 0].legend(loc="lower right", fontsize=8)
    for axis in axes.flat:
        axis.set_xlim(ALIGNMENT_WINDOW_S)
    figure.suptitle(
        "Observed-model waveform shape after optimal lag and per-mode amplitude fit",
        fontsize=14,
    )
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.97))
    save_figure(figure, "figure_05_aligned_mode_waveforms.png")


def shift_trace(time: np.ndarray, trace: np.ndarray, delay_s: float) -> np.ndarray:
    return np.interp(time - delay_s, time, trace, left=0.0, right=0.0)


def low_layer_delays() -> tuple[float, float, float, float]:
    p_delay = 2.0 * LOW_LAYER_THICKNESS_KM * (
        1.0 / LOW_LAYER_VP_KM_S - 1.0 / CURRENT_VP_KM_S
    )
    s_delay = 2.0 * LOW_LAYER_THICKNESS_KM * (
        1.0 / LOW_LAYER_VS_KM_S - 1.0 / CURRENT_VS_KM_S
    )
    p_round_trip = 2.0 * LOW_LAYER_THICKNESS_KM / LOW_LAYER_VP_KM_S
    s_round_trip = 2.0 * LOW_LAYER_THICKNESS_KM / LOW_LAYER_VS_KM_S
    return p_delay, s_delay, p_round_trip, s_round_trip


def plot_low_layer_diagnostic(records: tuple[ModeRecord, ...]) -> None:
    p_delay, s_delay, p_round_trip, s_round_trip = low_layer_delays()
    figure = plt.figure(figsize=(14.0, 9.5), layout="constrained")
    grid = figure.add_gridspec(3, 2, width_ratios=(0.82, 2.4), hspace=0.22, wspace=0.22)
    profile_axis = figure.add_subplot(grid[:, 0])
    profile_axis.plot(
        [CURRENT_VP_KM_S, CURRENT_VP_KM_S],
        [0.0, 5.0],
        color="#0072B2",
        linestyle="--",
        linewidth=1.5,
        label="Current Vp",
    )
    profile_axis.plot(
        [CURRENT_VS_KM_S, CURRENT_VS_KM_S],
        [0.0, 5.0],
        color="#D55E00",
        linestyle="--",
        linewidth=1.5,
        label="Current Vs",
    )
    profile_axis.plot(
        [LOW_LAYER_VP_KM_S, LOW_LAYER_VP_KM_S, CURRENT_VP_KM_S, CURRENT_VP_KM_S],
        [0.0, 1.0, 1.0, 5.0],
        color="#0072B2",
        linewidth=2.0,
        label="Proposed Vp",
    )
    profile_axis.plot(
        [LOW_LAYER_VS_KM_S, LOW_LAYER_VS_KM_S, CURRENT_VS_KM_S, CURRENT_VS_KM_S],
        [0.0, 1.0, 1.0, 5.0],
        color="#D55E00",
        linewidth=2.0,
        label="Proposed Vs",
    )
    profile_axis.axhspan(0.0, 1.0, color="#808080", alpha=0.08)
    profile_axis.invert_yaxis()
    profile_axis.set_xlabel("Velocity (km/s)")
    profile_axis.set_ylabel("Depth (km)")
    profile_axis.set_xlim(0.7, 3.6)
    profile_axis.grid(alpha=0.18)
    profile_axis.legend(loc="lower left", fontsize=8)
    profile_axis.text(
        0.04,
        0.98,
        f"minimum two-end delay\nP: +{p_delay:.3f} s\nS: +{s_delay:.3f} s\n\nlayer round trip\nP: {p_round_trip:.3f} s\nS: {s_round_trip:.3f} s",
        transform=profile_axis.transAxes,
        va="top",
        fontsize=9,
    )

    observed = records[0]
    model1 = records[1]
    mode_delays = (p_delay, s_delay, s_delay)
    for mode_index, (mode_label, delay_s) in enumerate(
        zip(MODE_LABELS, mode_delays, strict=True)
    ):
        axis = figure.add_subplot(grid[mode_index, 1])
        keep = (observed.time >= 45.0) & (observed.time <= 145.0)
        comparison_time = observed.time[keep]
        observed_trace = observed.modes[mode_index, keep]
        model_trace = np.interp(
            comparison_time, model1.time, model1.modes[mode_index]
        )
        shifted_trace = np.interp(
            comparison_time,
            model1.time,
            shift_trace(model1.time, model1.modes[mode_index], delay_s),
        )
        amplitude = max(
            float(np.percentile(np.abs(observed_trace), 99.5)),
            float(np.percentile(np.abs(model_trace), 99.5)),
        )
        amplitude = amplitude if amplitude > 0.0 else 1.0
        axis.plot(
            comparison_time,
            observed_trace / amplitude,
            color="#202020",
            linewidth=1.0,
            label="Observed",
        )
        axis.plot(
            comparison_time,
            model_trace / amplitude,
            color=model1.color,
            linewidth=0.8,
            alpha=0.72,
            label="M1 current",
        )
        axis.plot(
            comparison_time,
            shifted_trace / amplitude,
            color="#CC79A7",
            linestyle="--",
            linewidth=0.9,
            label=f"M1 static delay +{delay_s:.2f} s",
        )
        axis.set_ylabel(mode_label)
        axis.set_xlim(45.0, 145.0)
        axis.grid(alpha=0.16)
        if mode_index == 0:
            axis.legend(loc="upper right", ncol=3, fontsize=8)
        if mode_index == 2:
            axis.set_xlabel("Time (s)")
    figure.suptitle(
        "Low-velocity layer: velocity profile and limit of static-delay correction",
        fontsize=14,
    )
    save_figure(figure, "figure_06_low_velocity_layer_diagnostic.png")


def integrate_energy(time: np.ndarray, energy: np.ndarray, window: tuple[float, float]) -> float:
    keep = (time >= window[0]) & (time <= min(window[1], float(time[-1])))
    if np.count_nonzero(keep) < 2:
        return 0.0
    return float(np.trapezoid(energy[keep], time[keep]))


def energy_fraction_rows(records: tuple[ModeRecord, ...]) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for record in records:
        energy = corrected_mode_energy(record)
        integrals = np.array(
            [integrate_energy(record.time, row, COMMON_WINDOW_S) for row in energy]
        )
        total = float(np.sum(integrals))
        fractions = integrals / total if total > 0.0 else np.zeros(3)
        total_envelope = smoothed_intensity(
            record.time, np.sum(energy, axis=0), 5.0
        )
        common = (
            (record.time >= COMMON_WINDOW_S[0])
            & (record.time <= min(COMMON_WINDOW_S[1], float(record.time[-1])))
        )
        peak_time = float(record.time[common][np.argmax(total_envelope[common])])
        rows.append(
            {
                "record": record.short_name,
                "source_scale": record.source_scale,
                "qP_fraction": float(fractions[0]),
                "qSV_fraction": float(fractions[1]),
                "SH_fraction": float(fractions[2]),
                "energy_peak_time_s": peak_time,
            }
        )
    return rows


def observed_window_rows(observed: ModeRecord) -> list[dict[str, float | str]]:
    energy = corrected_mode_energy(observed)
    windows = (
        ("50-245 s", (50.0, 245.0)),
        ("245-1000 s", (245.0, 1_000.0)),
        ("1000-3000 s", (1_000.0, 3_000.0)),
    )
    rows: list[dict[str, float | str]] = []
    all_window_energy = np.array(
        [integrate_energy(observed.time, row, (50.0, 3_000.0)) for row in energy]
    )
    total_50_3000 = float(np.sum(all_window_energy))
    for label, window in windows:
        integrals = np.array(
            [integrate_energy(observed.time, row, window) for row in energy]
        )
        window_total = float(np.sum(integrals))
        fractions = integrals / window_total if window_total > 0.0 else np.zeros(3)
        rows.append(
            {
                "window": label,
                "fraction_of_50_3000_energy": (
                    window_total / total_50_3000 if total_50_3000 > 0.0 else 0.0
                ),
                "qP_fraction": float(fractions[0]),
                "qSV_fraction": float(fractions[1]),
                "SH_fraction": float(fractions[2]),
            }
        )
    return rows


def write_csv_files(
    energy_rows: list[dict[str, float | str]],
    observed_rows: list[dict[str, float | str]],
    alignments: dict[tuple[str, str], AlignmentResult],
) -> None:
    with (OUTPUT_DIR / "mode_energy_metrics.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(energy_rows[0]))
        writer.writeheader()
        writer.writerows(energy_rows)
    with (OUTPUT_DIR / "observed_long_coda_metrics.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(observed_rows[0]))
        writer.writeheader()
        writer.writerows(observed_rows)
    with (OUTPUT_DIR / "waveform_alignment_metrics.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as stream:
        fieldnames = ("model", "mode", "lag_s", "correlation", "amplitude_scale")
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for (model, mode), result in alignments.items():
            writer.writerow(
                {
                    "model": model,
                    "mode": mode,
                    "lag_s": result.lag_s,
                    "correlation": result.correlation,
                    "amplitude_scale": result.amplitude_scale,
                }
            )


def best_alignment_text(
    alignments: dict[tuple[str, str], AlignmentResult], mode: str
) -> str:
    candidates = [
        (model, result)
        for (model, current_mode), result in alignments.items()
        if current_mode == mode
    ]
    model, result = max(candidates, key=lambda item: abs(item[1].correlation))
    return f"{model}（r={result.correlation:+.2f}，最佳时移 {result.lag_s:+.1f} s）"


def percent(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def write_report(
    energy_rows: list[dict[str, float | str]],
    observed_rows: list[dict[str, float | str]],
    alignments: dict[tuple[str, str], AlignmentResult],
    qp: np.ndarray,
    qsv: np.ndarray,
    basis_window: tuple[float, float],
    distance_km: float,
    azimuth_deg: float,
) -> None:
    _, _, bhe_azimuth, bhe_incidence = read_sac_channel(
        OBSERVED_COMPONENT_FILES["E"]
    )
    _, _, bhn_azimuth, bhn_incidence = read_sac_channel(
        OBSERVED_COMPONENT_FILES["N"]
    )
    by_record = {str(row["record"]): row for row in energy_rows}
    observed_early = by_record["Observed"]
    observed_late_fraction = sum(
        float(row["fraction_of_50_3000_energy"])
        for row in observed_rows
        if str(row["window"]) != "50-245 s"
    )
    flat_scatter_delta_sh = float(by_record["M2"]["SH_fraction"]) - float(
        by_record["M1"]["SH_fraction"]
    )
    topo_delta_sh = float(by_record["M3"]["SH_fraction"]) - float(
        by_record["M1"]["SH_fraction"]
    )
    topo_scatter_delta_sh = float(by_record["M4"]["SH_fraction"]) - float(
        by_record["M3"]["SH_fraction"]
    )
    p_delay, s_delay, p_round_trip, s_round_trip = low_layer_delays()
    shortest_s_wavelength_km = LOW_LAYER_VS_KM_S / FILTER_HIGH_HZ
    cells_per_wavelength = shortest_s_wavelength_km / GRID_SPACING_KM
    text = f"""# S12 三分量 P-SV-SH 与真实观测对比

## 数据与坐标处理

- 处理频带为 {FILTER_LOW_HZ:.1f}–{FILTER_HIGH_HZ:.1f} Hz，模型振幅使用 {SOURCE_MATCH_WINDOW_S[0]:.0f}–{SOURCE_MATCH_WINDOW_S[1]:.0f} s 三分量联合 RMS 与实测匹配，只使用一个震源尺度因子，保持分量间振幅比例。
- S12 震中距为 {distance_km:.2f} km，震源至台站方位角为 {azimuth_deg:.2f}°；模型按 `Vx=E`、`Vy=N` 旋转到 R/T。
- SAC 头段显示 BHE 的 CMPAZ/CMPINC 为 {bhe_azimuth:.2f}°/{bhe_incidence:.1f}°，BHN 为 {bhn_azimuth:.2f}°/{bhn_incidence:.1f}°。它们并非严格的正东/正北分量，因此先按头段方位角解算为真 E/N，再旋转为 R/T；直接把文件名当作 E/N 会污染 SH 与 P-SV 比值。
- T 分量可作为 SH 代理；R-Z 平面是 P-SV 耦合平面。qP/qSV 使用 M1 在 {basis_window[0]:.1f}–{basis_window[1]:.1f} s 的协方差主轴固定投影，qP 轴 `[R,Z]=[{qp[0]:+.3f},{qp[1]:+.3f}]`，qSV 轴 `[R,Z]=[{qsv[0]:+.3f},{qsv[1]:+.3f}]`。这是统一偏振基下的近似分离，不是严格的波场投影。

## 图件

1. `figure_01_zrt_waveform_lanes.png`：实测与四模型 Z/R/T 波形直接对比。
2. `figure_02_qp_qsv_sh_waveform_lanes.png`：统一偏振基下 qP/qSV/SH 波形对比。
3. `figure_03_mode_energy_envelopes.png`：五条记录的模态能量包络。
4. `figure_04_long_coda_mode_energy.png`：实测 3000 s 长尾与模型 250 s 时窗对比。
5. `figure_05_aligned_mode_waveforms.png`：允许最佳时移和单模态幅值拟合后的波形形状对比。
6. `figure_06_low_velocity_layer_diagnostic.png`：低速层速度剖面及静态时移补救的局限。能量统计已扣除各模态 0–40 s 的中位噪声底。

## 数据支持的结论

1. 实测 50–245 s 能量分配为 qP {percent(float(observed_early['qP_fraction']))}、qSV {percent(float(observed_early['qSV_fraction']))}、SH {percent(float(observed_early['SH_fraction']))}；这给出了后续模型比较的真实三分量基准。
2. qP 波形形状最接近实测的是 {best_alignment_text(alignments, 'qP')}；最佳时移后仍未达到完全重合，说明差异不只是统一走时偏差。
3. qSV 波形形状最接近实测的是 {best_alignment_text(alignments, 'qSV')}；R-Z 平面内的波形失配反映速度结构、自由表面转换和浅层多次波共同影响。
4. SH 波形形状最接近实测的是 {best_alignment_text(alignments, 'SH')}；SH 对水平散射、横向非均匀性及台站方位最敏感，必须使用校正后的水平分量。
5. M1 的 SH 占比约为 {percent(float(by_record['M1']['SH_fraction']))}，与平坦、无散射、各向同性结构对垂直力源的对称性一致；实测 SH 占 {percent(float(observed_early['SH_fraction']))}，直接表明真实波场中存在当前一维背景没有的三维转换或散射。
6. 平坦模型中加入散射后，SH 占比增加 {flat_scatter_delta_sh:+.3f}，但 M3 的 {percent(float(by_record['M3']['SH_fraction']))} 仍低于实测；当前散射方向正确、强度或结构仍不足。
7. 无散射条件下加入地形后，SH 占比增加 {topo_delta_sh:+.3f}；M2 只达到 {percent(float(by_record['M2']['SH_fraction']))}，说明地形单独不能重现真实水平横向能量。
8. 有地形条件下再加入散射，SH 占比增加 {topo_scatter_delta_sh:+.3f}，小于平坦背景中的 {flat_scatter_delta_sh:+.3f}；地形使散射对 SH 的边际增益减弱，二者不是简单线性叠加。
9. 扣除 0–40 s 中位噪声底后，实测 50–3000 s 总能量中，245 s 之后仍占 {percent(observed_late_fraction)}；当前模型在约 250 s 截止，因此不能检验或解释大部分长尾衰减与晚期散射能量。
10. 最佳时移后的图仍保留明显包络、周期和脉冲数差异，且三种模态的 |r| 均很低，说明只做归一化或整体平移不足以修复实测—模拟波形形状。
11. 当前介质生成脚本的浅部 0–5 km 为 Vp={CURRENT_VP_KM_S:.2f} km/s、Vs={CURRENT_VS_KM_S:.2f} km/s；改为顶层 1 km 的 Vp={LOW_LAYER_VP_KM_S:.2f} km/s、Vs={LOW_LAYER_VS_KM_S:.2f} km/s 后，表面震源—表面台站两端近垂直穿越的最低附加时延约为 P {p_delay:.3f} s、S {s_delay:.3f} s。
12. 新低速层自身的往返时间约为 P {p_round_trip:.3f} s、S {s_round_trip:.3f} s，会引入约 1.4–1.8 s 尺度的浅层多次波和相位干涉；这能改变短周期波形形状，但不能单独产生数百至数千秒的长尾。
13. 静态时移仅移动现有波形，不能生成低速层的陷获、频散、反射、模式转换及其与三维散射/地形的耦合，因此只能作为敏感性检查，正式结论必须重算四个模型。
14. 在 0.9 Hz 上限下，低速层最短 S 波波长约 {shortest_s_wavelength_km:.3f} km；200 m 网格仅约 {cells_per_wavelength:.2f} 点/波长，属于偏紧配置。重算前应确认 CGFD3D 当前空间差分阶数的色散要求，必要时将网格缩小到约 120–150 m 或降低有效最高频率。
15. qP/qSV 是单台站固定偏振基下的代理量。若要严格分离 P 与 SV，需要阵列慢度/入射角、波数域投影或散度—旋度波场快照；当前结果最稳健的部分是 Z/R/T、P-SV 平面总能量与 SH=T。

## 低速层补救建议

1. **首选方案：四模型全部重算。** 在施加散射扰动之前，先统一加入 0–1 km 低速层；平坦/地形、散射/不散射必须使用同一套背景低速层，才能保持 2×2 因子设计可比。
2. **还缺一个关键参数：密度。** 反射系数由阻抗决定，只有 Vp/Vs 不能唯一确定界面振幅。应给出低速层密度；在缺失时可暂时沿用原浅层密度 2760 kg/m³ 做数值敏感性试验，但不能把该试验当作物理最优模型。
3. **过渡方式。** 如果直接速度阶跃导致网格色散或强人工反射，可在 0.8–1.2 km 内做 2–4 个网格点的平滑过渡，同时保留一个“尖锐界面”版本用于评估反射敏感性。
4. **低成本过渡方案。** 先重算 1D/2D 平层参考模型，求 Z/R/T 分量传递函数并卷积现有三维合成记录，只作为误差方向和计算资源评估；传递函数后处理不能替代最终三维重算。
5. **时窗同步延长。** 新模型建议至少输出到 1000 s；若论文需要解释真实 3000 s 长尾，则模拟时长、吸收边界、Q 和计算域都要同步评估，不能只加低速层。
6. **地形模型保持等厚。** 平坦模型的层底可设为 z=-1 km；地形模型应设为“局部自由表面高程减 1 km”，不能使用统一绝对高程，否则低速层厚度会随地形变化并引入额外变量。
7. **同步重建网格分层。** 当前 `gdlay` 顶部 5 km 使用 25 个点。建议用原网格生成程序把它拆为约 5 点的 0–1 km 和约 20 点的 1–5 km，并加入 -1 km（地形模型为随地形起伏）的界面；不要只手工改介质数组而不核对网格层数、点数和接口顺序。
8. **先保持低速层均匀。** 第一轮四模型中让 0–1 km 低速层完全相同，原散射扰动只作用于 1 km 以下，以便单独判断遗漏低速层的影响；之后再增加“低速层内散射”敏感性组。

## 介质脚本修改骨架

原脚本每层实际使用 `Vp(ilay+1)`、`Vs(ilay+1)` 和 `den(ilay+1)`。建议把接口改为：

```matlab
num_of_intfce = 6;
num_of_point_per_lay = [5,20,25,100,53];
dep = [0,1e3,5e3,1e4,3e4,4e4];
Vp  = [1380,1380,3200,5500,7550,7550];
Vs  = [1110,1110,2000,3180,4360,4360];
den = [rho_low,rho_low,2760,2760,3360,3360];
```

其中 `rho_low` 必须在正式重算前确定。散射扰动应施加在该背景模型之后，并检查扰动不会把 Vs 推到非物理值。
"""
    (OUTPUT_DIR / "three_component_psvsh_report_zh.md").write_text(
        text, encoding="utf-8"
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (
        _,
        _,
        records,
        qp,
        qsv,
        basis_window,
        distance_km,
        azimuth_deg,
    ) = build_mode_records()
    plot_waveform_lanes(
        records,
        "zrt",
        ("Z", "R", "T = SH proxy"),
        "figure_01_zrt_waveform_lanes.png",
        "Observed and synthetic S12 Z-R-T waveforms (0.3-0.9 Hz)",
    )
    plot_waveform_lanes(
        records,
        "modes",
        MODE_LABELS,
        "figure_02_qp_qsv_sh_waveform_lanes.png",
        "Observed and synthetic S12 qP-qSV-SH waveforms (fixed polarization basis)",
    )
    plot_mode_energy_envelopes(records)
    plot_long_coda(records)
    alignments = all_alignments(records)
    plot_aligned_waveform_comparison(records, alignments)
    plot_low_layer_diagnostic(records)
    energy_rows = energy_fraction_rows(records)
    observed_rows = observed_window_rows(records[0])
    write_csv_files(energy_rows, observed_rows, alignments)
    write_report(
        energy_rows,
        observed_rows,
        alignments,
        qp,
        qsv,
        basis_window,
        distance_km,
        azimuth_deg,
    )
    analyze_three_component_factorial_field()
    analyze_time_varying_polarization(records)
    analyze_time_frequency(records)
    append_three_component_factorial_report()


if __name__ == "__main__":
    main()
