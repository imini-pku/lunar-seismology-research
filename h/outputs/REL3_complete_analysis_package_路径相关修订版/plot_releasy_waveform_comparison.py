"""Plot waveform comparisons for four CGFD3D release simulations."""

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
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, detrend, hilbert, sosfiltfilt


@dataclass(frozen=True)
class ModelConfig:
    name: str
    nc_file: Path
    color: str


MODELS = (
    ModelConfig(
        "Model 1: Flat, no scatter",
        Path(r"E:\project_releasy_flat_noscatter\output\station.nc"),
        "#0072B2",
    ),
    ModelConfig(
        "Model 2: Flat, scatter",
        Path(r"E:\project_releasy_flat_scatter\output\station.nc"),
        "#D55E00",
    ),
    ModelConfig(
        "Model 3: Topography, no scatter",
        Path(r"E:\project_releasy_topo_noscatter\output\station.nc"),
        "#009E73",
    ),
    ModelConfig(
        "Model 4: Topography, scatter",
        Path(r"E:\project_releasy_topo_scatter\output\station.nc"),
        "#CC79A7",
    ),
)

COMPONENT = "Vz"
TIME_WINDOW: tuple[float, float] | None = None
FILTER_LOW_HZ = 0.3
FILTER_HIGH_HZ = 0.9
FILTER_ORDER = 4
STATION_STRIDE = 20
FIGURE_DPI = 250
S12_LINE_ALPHA = 0.68
PEAK_SMOOTHING_WINDOWS_S = (5.0, 10.0, 20.0, 40.0, 60.0, 100.0)
FIT_MIN_DISTANCE_KM = 10.0
FIT_TRIM_RAY_END_STATIONS = 5
OBSERVED_COMPONENT_FILES = {
    "Z": Path(r"D:\software\CGFD3D_v26.03\revise\usefiles\16s.12.BHZ.txt"),
    "E": Path(r"D:\software\CGFD3D_v26.03\revise\usefiles\16s.12.BHE.sac"),
    "N": Path(r"D:\software\CGFD3D_v26.03\revise\usefiles\16s.12.BHN.sac"),
}
MODEL_COMPONENT_VARIABLES = ("Vz", "Vx", "Vy")
COMPONENT_LABELS = ("Z", "E", "N")
SOURCE_MATCH_WINDOW_S = (50.0, 245.0)
OBSERVED_DISPLAY_END_S = 3_000.0
ENVELOPE_DISPLAY_END_S = 1_000.0
OUTPUT_DIR = SCRIPT_DIR / "releasy_waveform_figures_python"
# Active source in prep_source/rel3.src, referenced by the simulation shell script.
EARTHQUAKE_SOURCE_XY = np.array([161_310.0, 207_630.0])
TOPOGRAPHY_FILE = Path(
    r"D:\software\CGFD3D_v26.03\revise\prep_medium\rel3_Z_300_1500_topo.txt"
)


@dataclass
class WaveformModel:
    config: ModelConfig
    time: np.ndarray
    waveforms: np.ndarray
    dominant_frequencies_hz: np.ndarray


@dataclass
class ThreeComponentRecord:
    name: str
    color: str
    time: np.ndarray
    raw: np.ndarray
    filtered: np.ndarray
    dominant_frequencies_hz: np.ndarray


@dataclass
class PeakTimeStatistics:
    median_s: np.ndarray
    minimum_s: np.ndarray
    maximum_s: np.ndarray
    standard_deviation_s: np.ndarray


def build_station_geometry() -> tuple[np.ndarray, tuple[np.ndarray, ...]]:
    """Reproduce the ordering in gen_rel_station.py exactly."""
    ray_start = np.array([161_310.0, 207_630.0])
    ray_targets = np.array(
        [
            [197_256.0, 59_703.0],
            [100_000.0, 140_000.0],
            [213_000.0, 247_000.0],
        ]
    )
    station_xy = [[197_256.0, 59_703.0]]
    ray_station_indices: list[np.ndarray] = []
    station_index = 1

    for target in ray_targets:
        direction = target - ray_start
        direction /= np.linalg.norm(direction)
        current_ray: list[int] = []
        distance_along_ray = 1_000.0
        while True:
            point = ray_start + direction * distance_along_ray
            if not (0.0 <= point[0] <= 300_000.0 and 0.0 <= point[1] <= 300_000.0):
                break
            station_xy.append([round(float(point[0])), round(float(point[1]))])
            current_ray.append(station_index)
            station_index += 1
            distance_along_ray += 1_000.0
        ray_station_indices.append(np.asarray(current_ray, dtype=int))

    geometry = np.asarray(station_xy, dtype=float)
    if geometry.shape != (606, 2):
        raise RuntimeError(f"Generated {geometry.shape[0]} stations instead of 606")
    expected_ranges = ((1, 213), (214, 453), (454, 605))
    for ray_index, (indices, expected) in enumerate(
        zip(ray_station_indices, expected_ranges, strict=True), start=1
    ):
        actual = (int(indices[0]), int(indices[-1]))
        if actual != expected:
            raise RuntimeError(f"Unexpected station range for ray {ray_index}: {actual}")
    return geometry, tuple(ray_station_indices)


def dominant_frequencies(time: np.ndarray, waveforms: np.ndarray) -> np.ndarray:
    sample_interval = float(np.median(np.diff(time)))
    demeaned = detrend(np.asarray(waveforms, dtype=np.float64), axis=-1, type="linear")
    amplitude_spectrum = np.abs(np.fft.rfft(demeaned, axis=-1))
    frequencies = np.fft.rfftfreq(time.size, d=sample_interval)
    amplitude_spectrum[..., 0] = 0.0
    return frequencies[np.argmax(amplitude_spectrum, axis=-1)]


def bandpass_waveforms(time: np.ndarray, waveforms: np.ndarray) -> np.ndarray:
    sample_interval = float(np.median(np.diff(time)))
    sample_rate = 1.0 / sample_interval
    if FILTER_HIGH_HZ >= sample_rate / 2.0:
        raise ValueError(
            f"Filter upper corner {FILTER_HIGH_HZ} Hz exceeds Nyquist "
            f"frequency {sample_rate / 2.0:.3f} Hz"
        )
    sos = butter(
        FILTER_ORDER,
        (FILTER_LOW_HZ, FILTER_HIGH_HZ),
        btype="bandpass",
        fs=sample_rate,
        output="sos",
    )
    prepared = detrend(
        np.asarray(waveforms, dtype=np.float64), axis=-1, type="linear"
    )
    return sosfiltfilt(sos, prepared, axis=-1).astype(np.float32)


def load_model(config: ModelConfig) -> WaveformModel:
    if not config.nc_file.is_file():
        raise FileNotFoundError(config.nc_file)

    with Dataset(config.nc_file, "r") as dataset:
        if COMPONENT not in dataset.variables:
            raise KeyError(f"{COMPONENT!r} not found in {config.nc_file}")
        time = np.asarray(dataset.variables["time"][:], dtype=np.float64)
        waveforms = np.asarray(dataset.variables[COMPONENT][:], dtype=np.float32)

    if waveforms.ndim != 2:
        raise ValueError(f"Unexpected {COMPONENT} shape in {config.nc_file}: {waveforms.shape}")
    if waveforms.shape == (time.size, 606):
        waveforms = waveforms.T
    if waveforms.shape != (606, time.size):
        raise ValueError(
            f"Expected {COMPONENT} dimensions (606, time), got {waveforms.shape} "
            f"in {config.nc_file}"
        )

    if TIME_WINDOW is not None:
        start_time, end_time = TIME_WINDOW
        keep = (time >= start_time) & (time <= end_time)
        if not np.any(keep):
            raise ValueError(f"TIME_WINDOW {TIME_WINDOW} does not overlap {config.nc_file}")
        time = time[keep]
        waveforms = waveforms[:, keep]

    dominant_frequencies_hz = dominant_frequencies(time, waveforms)
    filtered_waveforms = bandpass_waveforms(time, waveforms)
    return WaveformModel(
        config=config,
        time=time,
        waveforms=filtered_waveforms,
        dominant_frequencies_hz=dominant_frequencies_hz,
    )


def read_sac_channel(
    file_path: Path,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    if not file_path.is_file():
        raise FileNotFoundError(file_path)
    raw = file_path.read_bytes()
    if len(raw) < 632:
        raise ValueError(f"SAC file is too short: {file_path}")

    header_floats: np.ndarray | None = None
    header_integers: np.ndarray | None = None
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
        raise ValueError(f"Unable to determine SAC byte order: {file_path}")

    sample_count = int(header_integers[9])
    expected_size = 632 + sample_count * 4
    if len(raw) < expected_size:
        raise ValueError(
            f"SAC file {file_path} contains {len(raw)} bytes; "
            f"at least {expected_size} are required"
        )
    sample_interval = float(header_floats[0])
    start_time = float(header_floats[5])
    data = np.frombuffer(
        raw, dtype=f"{byte_order}f4", count=sample_count, offset=632
    ).astype(np.float64)
    time = start_time + np.arange(sample_count, dtype=np.float64) * sample_interval
    component_azimuth_deg = float(header_floats[57])
    component_incidence_deg = float(header_floats[58])
    return time, data, component_azimuth_deg, component_incidence_deg


def read_sac_evenly_sampled(file_path: Path) -> tuple[np.ndarray, np.ndarray]:
    time, data, _, _ = read_sac_channel(file_path)
    return time, data


def load_observed_s12() -> ThreeComponentRecord:
    for file_path in OBSERVED_COMPONENT_FILES.values():
        if not file_path.is_file():
            raise FileNotFoundError(file_path)

    vertical_table = np.loadtxt(OBSERVED_COMPONENT_FILES["Z"], dtype=np.float64)
    if vertical_table.ndim != 2 or vertical_table.shape[1] < 2:
        raise ValueError(
            f"Expected two columns in {OBSERVED_COMPONENT_FILES['Z']}, "
            f"got {vertical_table.shape}"
        )
    time = vertical_table[:, 0]
    horizontal_channels = []
    horizontal_azimuths_deg = []
    for component in ("E", "N"):
        component_time, component_data, component_azimuth_deg, component_incidence_deg = (
            read_sac_channel(OBSERVED_COMPONENT_FILES[component])
        )
        if component_time.shape != time.shape or not np.allclose(
            component_time, time, atol=1.0e-3, rtol=0.0
        ):
            raise ValueError(
                f"Observed {component} time samples do not match the Z component"
            )
        if not np.isclose(component_incidence_deg, 90.0, atol=1.0):
            raise ValueError(
                f"Observed {component} is not horizontal: CMPINC={component_incidence_deg}"
            )
        horizontal_channels.append(component_data)
        horizontal_azimuths_deg.append(component_azimuth_deg)

    azimuths_rad = np.deg2rad(horizontal_azimuths_deg)
    orientation = np.column_stack(
        (np.cos(azimuths_rad), np.sin(azimuths_rad))
    )
    if abs(float(np.linalg.det(orientation))) < 0.1:
        raise ValueError(
            "Observed horizontal SAC orientations are too close to parallel"
        )
    north, east = np.linalg.solve(orientation, np.vstack(horizontal_channels))
    raw = np.vstack((vertical_table[:, 1], east, north))
    return ThreeComponentRecord(
        name="Observed A16S12",
        color="#222222",
        time=time,
        raw=raw,
        filtered=bandpass_waveforms(time, raw),
        dominant_frequencies_hz=dominant_frequencies(time, raw),
    )


def load_s12_model_components(config: ModelConfig) -> ThreeComponentRecord:
    with Dataset(config.nc_file, "r") as dataset:
        time = np.asarray(dataset.variables["time"][:], dtype=np.float64)
        component_rows = []
        for variable_name in MODEL_COMPONENT_VARIABLES:
            if variable_name not in dataset.variables:
                raise KeyError(f"{variable_name!r} not found in {config.nc_file}")
            variable = np.asarray(dataset.variables[variable_name][:], dtype=np.float32)
            if variable.shape == (time.size, 606):
                variable = variable.T
            if variable.shape != (606, time.size):
                raise ValueError(
                    f"Unexpected {variable_name} shape {variable.shape} in "
                    f"{config.nc_file}"
                )
            component_rows.append(variable[0])
    raw = np.vstack(component_rows)
    return ThreeComponentRecord(
        name=config.name,
        color=config.color,
        time=time,
        raw=raw,
        filtered=bandpass_waveforms(time, raw),
        dominant_frequencies_hz=dominant_frequencies(time, raw),
    )


def analytic_energy(waveforms: np.ndarray) -> np.ndarray:
    return np.abs(hilbert(waveforms, axis=-1)) ** 2


def peak_time_statistics(
    time: np.ndarray,
    intensity: np.ndarray,
    smoothing_windows_s: tuple[float, ...] = PEAK_SMOOTHING_WINDOWS_S,
) -> PeakTimeStatistics:
    sample_interval = float(np.median(np.diff(time)))
    candidate_times = []
    for smoothing_window_s in smoothing_windows_s:
        sample_count = max(1, int(round(smoothing_window_s / sample_interval)))
        smoothed = uniform_filter1d(
            intensity, sample_count, axis=-1, mode="nearest"
        )
        candidate_times.append(time[np.argmax(smoothed, axis=-1)])
    candidates = np.asarray(candidate_times, dtype=np.float64)
    return PeakTimeStatistics(
        median_s=np.median(candidates, axis=0),
        minimum_s=np.min(candidates, axis=0),
        maximum_s=np.max(candidates, axis=0),
        standard_deviation_s=np.std(candidates, axis=0, ddof=1),
    )


def shared_scale(traces: list[np.ndarray]) -> float:
    scale = max(float(np.max(np.abs(trace))) for trace in traces)
    return scale if scale > 0.0 else 1.0


def save_figure(fig: plt.Figure, filename: str) -> None:
    fig.savefig(OUTPUT_DIR / filename, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)


def plot_s12(models: tuple[WaveformModel, ...]) -> None:
    panel_models = ((0, 1), (0, 2), (1, 3), (0, 1, 2, 3))
    panel_titles = (
        "Model 1 + Model 2",
        "Model 1 + Model 3",
        "Model 2 + Model 4",
        "All four models",
    )
    all_s12 = [model.waveforms[0] for model in models]
    scale = shared_scale(all_s12)

    fig, axes = plt.subplots(2, 2, figsize=(14, 8.2), constrained_layout=True)
    for axis, model_indices, title in zip(
        axes.ravel(), panel_models, panel_titles, strict=True
    ):
        for model_index in model_indices:
            model = models[model_index]
            axis.plot(
                model.time,
                model.waveforms[0] / scale,
                color=model.config.color,
                linewidth=1.15,
                alpha=S12_LINE_ALPHA,
                label=model.config.name,
            )
        axis.set_title(title)
        axis.set_xlabel("Time (s)")
        axis.set_ylabel(r"Normalized $V_z$")
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
    fig.suptitle("S12 (r1) waveform comparison, 0.3-0.9 Hz bandpass", fontsize=15)
    save_figure(fig, "figure1_S12_comparison.png")


def plot_offset_station(
    models: tuple[WaveformModel, ...],
    station_index: int,
    ray_number: int,
    epicentral_distance_km: float,
) -> None:
    traces = [model.waveforms[station_index] for model in models]
    scale = shared_scale(traces)
    vertical_offset = 2.4

    fig, axis = plt.subplots(figsize=(12, 6.2), constrained_layout=True)
    for model_index, model in enumerate(models):
        axis.plot(
            model.time,
            model.waveforms[station_index] / scale + model_index * vertical_offset,
            color=model.config.color,
            linewidth=0.9,
        )
    axis.set_yticks(np.arange(4) * vertical_offset)
    axis.set_yticklabels([model.config.name for model in models])
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Model (normalized traces with vertical offset)")
    axis.set_title(
        f"Ray {ray_number}, r{station_index + 1}, "
        f"epicentral distance {epicentral_distance_km:.2f} km, "
        f"0.3-0.9 Hz bandpass"
    )
    axis.grid(alpha=0.25)
    axis.set_ylim(-1.25, 3 * vertical_offset + 1.25)
    save_figure(
        fig,
        f"figure{ray_number + 1}_ray{ray_number}_r{station_index + 1:03d}_offset.png",
    )


def compute_peak_energy_times(
    models: tuple[WaveformModel, ...],
) -> PeakTimeStatistics:
    median = np.empty((606, len(models)), dtype=np.float64)
    minimum = np.empty_like(median)
    maximum = np.empty_like(median)
    standard_deviation = np.empty_like(median)
    for model_index, model in enumerate(models):
        statistics = peak_time_statistics(
            model.time, analytic_energy(model.waveforms)
        )
        median[:, model_index] = statistics.median_s
        minimum[:, model_index] = statistics.minimum_s
        maximum[:, model_index] = statistics.maximum_s
        standard_deviation[:, model_index] = statistics.standard_deviation_s
    return PeakTimeStatistics(median, minimum, maximum, standard_deviation)


def load_topography() -> np.ndarray:
    if not TOPOGRAPHY_FILE.is_file():
        raise FileNotFoundError(TOPOGRAPHY_FILE)
    topography = np.loadtxt(TOPOGRAPHY_FILE, dtype=np.float32)
    if topography.ndim != 2 or topography.shape[0] != topography.shape[1]:
        raise ValueError(
            f"Expected a square topography grid, got {topography.shape} in "
            f"{TOPOGRAPHY_FILE}"
        )
    return topography


def sample_topography(topography: np.ndarray, station_xy: np.ndarray) -> np.ndarray:
    """Bilinearly sample a [y, x] grid spanning 0-300 km on both axes."""
    grid_size = topography.shape[0]
    fractional_x = station_xy[:, 0] / 300_000.0 * (grid_size - 1)
    fractional_y = station_xy[:, 1] / 300_000.0 * (grid_size - 1)
    x0 = np.clip(np.floor(fractional_x).astype(int), 0, grid_size - 1)
    y0 = np.clip(np.floor(fractional_y).astype(int), 0, grid_size - 1)
    x1 = np.clip(x0 + 1, 0, grid_size - 1)
    y1 = np.clip(y0 + 1, 0, grid_size - 1)
    wx = fractional_x - x0
    wy = fractional_y - y0

    corner_values = np.column_stack(
        (
            topography[y0, x0],
            topography[y0, x1],
            topography[y1, x0],
            topography[y1, x1],
        )
    )
    corner_weights = np.column_stack(
        (
            (1.0 - wx) * (1.0 - wy),
            wx * (1.0 - wy),
            (1.0 - wx) * wy,
            wx * wy,
        )
    )
    finite = np.isfinite(corner_values)
    valid_weights = np.where(finite, corner_weights, 0.0)
    weight_sum = valid_weights.sum(axis=1)
    weighted_sum = np.where(finite, corner_values, 0.0) * valid_weights
    sampled = np.full(station_xy.shape[0], np.nan, dtype=np.float64)
    valid_rows = weight_sum > 0.0
    sampled[valid_rows] = weighted_sum.sum(axis=1)[valid_rows] / weight_sum[valid_rows]
    return sampled


def write_peak_energy_csv(
    models: tuple[WaveformModel, ...],
    peak_times: PeakTimeStatistics,
    ray_station_indices: tuple[np.ndarray, ...],
    epicentral_distance_km: np.ndarray,
) -> None:
    ray_lookup = np.zeros(606, dtype=int)
    for ray_number, indices in enumerate(ray_station_indices, start=1):
        ray_lookup[indices] = ray_number

    csv_file = OUTPUT_DIR / "figure5_peak_energy_times.csv"
    with csv_file.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "station",
                "ray",
                "epicentral_distance_km",
                *[
                    column
                    for model in models
                    for column in (
                        f"{model.config.name}_peak_energy_time_median_s",
                        f"{model.config.name}_peak_energy_time_min_s",
                        f"{model.config.name}_peak_energy_time_max_s",
                        f"{model.config.name}_peak_energy_time_std_s",
                    )
                ],
            ]
        )
        for station_index in range(606):
            ray_label = "S12" if station_index == 0 else ray_lookup[station_index]
            writer.writerow(
                [
                    f"r{station_index + 1}",
                    ray_label,
                    f"{epicentral_distance_km[station_index]:.6f}",
                    *[
                        f"{value:.6f}"
                        for model_index in range(len(models))
                        for value in (
                            peak_times.median_s[station_index, model_index],
                            peak_times.minimum_s[station_index, model_index],
                            peak_times.maximum_s[station_index, model_index],
                            peak_times.standard_deviation_s[
                                station_index, model_index
                            ],
                        )
                    ],
                ]
            )


def write_dominant_frequency_csv(
    models: tuple[WaveformModel, ...],
    ray_station_indices: tuple[np.ndarray, ...],
    epicentral_distance_km: np.ndarray,
) -> None:
    ray_lookup = np.zeros(606, dtype=int)
    for ray_number, indices in enumerate(ray_station_indices, start=1):
        ray_lookup[indices] = ray_number

    csv_file = OUTPUT_DIR / "raw_waveform_dominant_frequencies.csv"
    with csv_file.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "station",
                "ray",
                "epicentral_distance_km",
                *[f"{model.config.name}_dominant_frequency_hz" for model in models],
            ]
        )
        for station_index in range(606):
            ray_label = "S12" if station_index == 0 else ray_lookup[station_index]
            writer.writerow(
                [
                    f"r{station_index + 1}",
                    ray_label,
                    f"{epicentral_distance_km[station_index]:.6f}",
                    *[
                        f"{model.dominant_frequencies_hz[station_index]:.6f}"
                        for model in models
                    ],
                ]
            )


def plot_peak_energy_times(
    models: tuple[WaveformModel, ...],
    peak_times: PeakTimeStatistics,
    ray_station_indices: tuple[np.ndarray, ...],
    epicentral_distance_km: np.ndarray,
    terrain_elevation_km: np.ndarray,
) -> None:
    fig = plt.figure(figsize=(17, 10.5), constrained_layout=True)
    grid = fig.add_gridspec(3, 2, width_ratios=(2.7, 1.25))
    for ray_number, station_indices in enumerate(ray_station_indices, start=1):
        arrival_axis = fig.add_subplot(grid[ray_number - 1, 0])
        terrain_axis = fig.add_subplot(grid[ray_number - 1, 1])
        order = np.argsort(epicentral_distance_km[station_indices])
        sorted_indices = station_indices[order]
        for model_index, model in enumerate(models):
            arrival_axis.plot(
                epicentral_distance_km[sorted_indices],
                peak_times.median_s[sorted_indices, model_index],
                color=model.config.color,
                linewidth=1.0,
                marker="o",
                markersize=2.5,
                label=model.config.name,
            )
            arrival_axis.fill_between(
                epicentral_distance_km[sorted_indices],
                peak_times.minimum_s[sorted_indices, model_index],
                peak_times.maximum_s[sorted_indices, model_index],
                color=model.config.color,
                alpha=0.08,
                linewidth=0.0,
            )
        arrival_axis.set_title(f"Ray {ray_number}: smoothed peak-energy time")
        arrival_axis.set_xlabel("Epicentral distance (km)")
        arrival_axis.set_ylabel("Peak-energy time (s)")
        arrival_axis.grid(alpha=0.25)
        arrival_axis.legend(fontsize=8)

        distance = epicentral_distance_km[sorted_indices]
        elevation = terrain_elevation_km[sorted_indices]
        terrain_axis.plot(distance, elevation, color="#333333", linewidth=1.15)
        finite_elevation = elevation[np.isfinite(elevation)]
        elevation_span = max(float(np.ptp(finite_elevation)), 0.5)
        lower_limit = float(np.min(finite_elevation)) - 0.10 * elevation_span
        upper_limit = max(0.0, float(np.max(finite_elevation))) + 0.08 * elevation_span
        terrain_axis.fill_between(
            distance,
            elevation,
            lower_limit,
            color="#A67C52",
            alpha=0.55,
            interpolate=True,
        )
        terrain_axis.axhline(0.0, color="black", linewidth=0.7, alpha=0.7)
        terrain_axis.set_title(f"Ray {ray_number}: topographic profile")
        terrain_axis.set_xlabel("Epicentral distance (km)")
        terrain_axis.set_ylabel("Elevation (km)")
        terrain_axis.set_xlim(arrival_axis.get_xlim())
        terrain_axis.set_ylim(lower_limit, upper_limit)
        terrain_axis.grid(alpha=0.25)
    fig.suptitle(
        "Peak-energy time (median and range across 5-100 s smoothing) "
        "and topography versus distance",
        fontsize=15,
    )
    save_figure(fig, "figure5_peak_energy_time_vs_epicentral_distance.png")


def fit_distance_dependence(
    distance_km: np.ndarray, peak_time_s: np.ndarray
) -> dict[str, float]:
    linear_design = np.column_stack((np.ones(distance_km.size), distance_km))
    diffusion_design = np.column_stack(
        (np.ones(distance_km.size), distance_km * distance_km)
    )
    linear_coefficients = np.linalg.lstsq(
        linear_design, peak_time_s, rcond=None
    )[0]
    diffusion_coefficients = np.linalg.lstsq(
        diffusion_design, peak_time_s, rcond=None
    )[0]
    linear_prediction = linear_design @ linear_coefficients
    diffusion_prediction = diffusion_design @ diffusion_coefficients
    total_sum_squares = float(np.sum((peak_time_s - np.mean(peak_time_s)) ** 2))

    result: dict[str, float] = {
        "linear_intercept_s": float(linear_coefficients[0]),
        "linear_slope_s_per_km": float(linear_coefficients[1]),
        "diffusion_intercept_s": float(diffusion_coefficients[0]),
        "diffusion_coefficient_s_per_km2": float(diffusion_coefficients[1]),
    }
    for fit_name, prediction in (
        ("linear", linear_prediction),
        ("diffusion", diffusion_prediction),
    ):
        residual = peak_time_s - prediction
        sum_squared_error = float(np.sum(residual * residual))
        result[f"{fit_name}_rmse_s"] = float(
            np.sqrt(sum_squared_error / peak_time_s.size)
        )
        result[f"{fit_name}_r_squared"] = (
            1.0 - sum_squared_error / total_sum_squares
            if total_sum_squares > 0.0
            else np.nan
        )
        result[f"{fit_name}_aic"] = float(
            peak_time_s.size
            * np.log(max(sum_squared_error / peak_time_s.size, 1.0e-30))
            + 4.0
        )
    result["delta_aic_diffusion_minus_linear"] = (
        result["diffusion_aic"] - result["linear_aic"]
    )
    return result


def write_and_plot_distance_fits(
    models: tuple[WaveformModel, ...],
    peak_times: PeakTimeStatistics,
    ray_station_indices: tuple[np.ndarray, ...],
    epicentral_distance_km: np.ndarray,
) -> None:
    summary_rows = []
    fig, axes = plt.subplots(3, 4, figsize=(17, 10.5), constrained_layout=True)
    for ray_index, station_indices in enumerate(ray_station_indices):
        fit_indices = station_indices[
            epicentral_distance_km[station_indices] >= FIT_MIN_DISTANCE_KM
        ]
        if FIT_TRIM_RAY_END_STATIONS:
            fit_indices = fit_indices[:-FIT_TRIM_RAY_END_STATIONS]
        order = np.argsort(epicentral_distance_km[fit_indices])
        fit_indices = fit_indices[order]
        distance = epicentral_distance_km[fit_indices]

        for model_index, model in enumerate(models):
            peak_time = peak_times.median_s[fit_indices, model_index]
            fit = fit_distance_dependence(distance, peak_time)
            linear_prediction = (
                fit["linear_intercept_s"]
                + fit["linear_slope_s_per_km"] * distance
            )
            diffusion_prediction = (
                fit["diffusion_intercept_s"]
                + fit["diffusion_coefficient_s_per_km2"] * distance * distance
            )
            axis = axes[ray_index, model_index]
            axis.plot(distance, peak_time, color="#777777", linewidth=0.8)
            axis.plot(
                distance,
                linear_prediction,
                color="#0072B2",
                linewidth=1.4,
                label="a + bR",
            )
            axis.plot(
                distance,
                diffusion_prediction,
                color="#D55E00",
                linewidth=1.4,
                linestyle="--",
                label=r"a + cR$^2$",
            )
            axis.set_title(f"Ray {ray_index + 1}, Model {model_index + 1}")
            axis.set_xlabel("Distance (km)")
            axis.set_ylabel("Peak-energy time (s)")
            axis.grid(alpha=0.22)
            axis.text(
                0.03,
                0.96,
                f"RMSE: {fit['linear_rmse_s']:.2f} / "
                f"{fit['diffusion_rmse_s']:.2f} s\n"
                f"ΔAIC(R²-linear)={fit['delta_aic_diffusion_minus_linear']:.1f}",
                transform=axis.transAxes,
                ha="left",
                va="top",
                fontsize=7.5,
                bbox={"facecolor": "white", "alpha": 0.78, "edgecolor": "none"},
            )
            if ray_index == 0 and model_index == 0:
                axis.legend(fontsize=8)
            summary_rows.append(
                {
                    "ray": ray_index + 1,
                    "model": model_index + 1,
                    "model_name": model.config.name,
                    "station_count": fit_indices.size,
                    **fit,
                    "preferred_form": (
                        "linear"
                        if fit["linear_aic"] < fit["diffusion_aic"]
                        else "diffusion_R_squared"
                    ),
                }
            )
    fig.suptitle(
        "Peak-energy time: ballistic linear form versus diffusion R² form",
        fontsize=15,
    )
    save_figure(fig, "figure5b_peak_time_linear_vs_diffusion_fit.png")

    csv_file = OUTPUT_DIR / "figure5b_peak_time_fit_summary.csv"
    with csv_file.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)


def source_matching_scale(
    observed: ThreeComponentRecord, model: ThreeComponentRecord
) -> float:
    comparison_end = min(
        SOURCE_MATCH_WINDOW_S[1], observed.time[-1], model.time[-1]
    )
    comparison_time = observed.time[
        (observed.time >= SOURCE_MATCH_WINDOW_S[0])
        & (observed.time <= comparison_end)
    ]
    observed_samples = np.vstack(
        [np.interp(comparison_time, observed.time, row) for row in observed.filtered]
    )
    model_samples = np.vstack(
        [np.interp(comparison_time, model.time, row) for row in model.filtered]
    )
    observed_rms = float(np.sqrt(np.mean(observed_samples * observed_samples)))
    model_rms = float(np.sqrt(np.mean(model_samples * model_samples)))
    return observed_rms / model_rms if model_rms > 0.0 else 1.0


def total_energy_intensity(record: ThreeComponentRecord) -> np.ndarray:
    return np.sum(analytic_energy(record.filtered), axis=0)


def smoothed_intensity(
    time: np.ndarray, intensity: np.ndarray, smoothing_window_s: float
) -> np.ndarray:
    sample_interval = float(np.median(np.diff(time)))
    sample_count = max(1, int(round(smoothing_window_s / sample_interval)))
    return uniform_filter1d(intensity, sample_count, mode="nearest")


def energy_quantile_time(
    time: np.ndarray, intensity: np.ndarray, quantile: float
) -> float:
    sample_interval = float(np.median(np.diff(time)))
    cumulative = np.cumsum(intensity, dtype=np.float64) * sample_interval
    target = quantile * cumulative[-1]
    return float(time[min(np.searchsorted(cumulative, target), time.size - 1)])


def energy_fraction_before(
    time: np.ndarray, intensity: np.ndarray, end_time_s: float
) -> float:
    sample_interval = float(np.median(np.diff(time)))
    cumulative = np.cumsum(intensity, dtype=np.float64) * sample_interval
    sample_index = min(np.searchsorted(time, end_time_s, side="right"), time.size) - 1
    return float(cumulative[max(sample_index, 0)] / cumulative[-1])


def pearson_correlation(first: np.ndarray, second: np.ndarray) -> float:
    first_centered = np.asarray(first, dtype=np.float64) - np.mean(first)
    second_centered = np.asarray(second, dtype=np.float64) - np.mean(second)
    denominator = float(
        np.sqrt(np.sum(first_centered**2) * np.sum(second_centered**2))
    )
    return (
        float(np.sum(first_centered * second_centered) / denominator)
        if denominator > 0.0
        else np.nan
    )


def best_lagged_correlation(
    observed: np.ndarray,
    model: np.ndarray,
    sample_interval: float,
    maximum_lag_s: float = 10.0,
) -> tuple[float, float]:
    maximum_lag_samples = int(round(maximum_lag_s / sample_interval))
    best_correlation = -np.inf
    best_lag_samples = 0
    for lag_samples in range(-maximum_lag_samples, maximum_lag_samples + 1):
        if lag_samples < 0:
            first = observed[:lag_samples]
            second = model[-lag_samples:]
        elif lag_samples > 0:
            first = observed[lag_samples:]
            second = model[:-lag_samples]
        else:
            first = observed
            second = model
        correlation = pearson_correlation(first, second)
        if correlation > best_correlation:
            best_correlation = correlation
            best_lag_samples = lag_samples
    return best_correlation, best_lag_samples * sample_interval


def plot_observed_three_components(observed: ThreeComponentRecord) -> None:
    display = observed.time <= OBSERVED_DISPLAY_END_S
    raw_scale = shared_scale([row[display] for row in observed.raw])
    filtered_scale = shared_scale([row[display] for row in observed.filtered])
    fig, axes = plt.subplots(3, 2, figsize=(15, 9.5), constrained_layout=True)
    for component_index, component_label in enumerate(COMPONENT_LABELS):
        axes[component_index, 0].plot(
            observed.time[display],
            observed.raw[component_index, display] / raw_scale,
            color="#555555",
            linewidth=0.55,
        )
        axes[component_index, 1].plot(
            observed.time[display],
            observed.filtered[component_index, display] / filtered_scale,
            color="#0072B2",
            linewidth=0.65,
        )
        axes[component_index, 0].set_ylabel(
            f"{component_label} / global 3C scale"
        )
        axes[component_index, 1].set_ylabel(
            f"{component_label} / global 3C scale"
        )
        for axis in axes[component_index]:
            axis.set_xlabel("Time after impact (s)")
            axis.grid(alpha=0.22)
    axes[0, 0].set_title("Original observations (native units)")
    axes[0, 1].set_title("0.3-0.9 Hz band-pass filtered")
    fig.suptitle(
        "Observed A16S12 three-component record (single scale preserves Z/E/N ratios)",
        fontsize=15,
    )
    save_figure(fig, "figure6_A16S12_observed_three_components.png")


def plot_observed_model_comparison(
    observed: ThreeComponentRecord,
    model_records: tuple[ThreeComponentRecord, ...],
    source_scales: tuple[float, ...],
) -> None:
    comparison_end = min(
        SOURCE_MATCH_WINDOW_S[1],
        observed.time[-1],
        *(record.time[-1] for record in model_records),
    )
    observed_keep = (
        (observed.time >= SOURCE_MATCH_WINDOW_S[0])
        & (observed.time <= comparison_end)
    )
    amplitude_scale = shared_scale(
        [observed.filtered[index, observed_keep] for index in range(3)]
    )
    fig, axes = plt.subplots(3, 2, figsize=(16, 10), constrained_layout=True)
    for component_index, component_label in enumerate(COMPONENT_LABELS):
        observed_trace = observed.filtered[component_index] / amplitude_scale
        observed_envelope = smoothed_intensity(
            observed.time,
            np.abs(hilbert(observed.filtered[component_index])),
            5.0,
        )
        axes[component_index, 0].plot(
            observed.time,
            observed_trace,
            color=observed.color,
            linewidth=1.05,
            label=observed.name,
            zorder=6,
        )
        axes[component_index, 1].plot(
            observed.time,
            observed_envelope / amplitude_scale,
            color=observed.color,
            linewidth=1.05,
            label=observed.name,
            zorder=6,
        )
        for model_record, source_scale in zip(
            model_records, source_scales, strict=True
        ):
            scaled_trace = source_scale * model_record.filtered[component_index]
            axes[component_index, 0].plot(
                model_record.time,
                scaled_trace / amplitude_scale,
                color=model_record.color,
                linewidth=0.85,
                alpha=0.76,
                label=model_record.name,
            )
            axes[component_index, 1].plot(
                model_record.time,
                smoothed_intensity(
                    model_record.time, np.abs(hilbert(scaled_trace)), 5.0
                )
                / amplitude_scale,
                color=model_record.color,
                linewidth=0.9,
                alpha=0.78,
                label=model_record.name,
            )
        axes[component_index, 0].set_xlim(
            SOURCE_MATCH_WINDOW_S[0], comparison_end
        )
        axes[component_index, 1].set_xlim(
            SOURCE_MATCH_WINDOW_S[0], ENVELOPE_DISPLAY_END_S
        )
        axes[component_index, 1].axvspan(
            comparison_end,
            ENVELOPE_DISPLAY_END_S,
            color="#DDDDDD",
            alpha=0.22,
            label="No synthetic samples" if component_index == 0 else None,
        )
        axes[component_index, 0].set_ylabel(
            f"{component_label} source-matched amplitude"
        )
        axes[component_index, 1].set_ylabel(
            f"{component_label} envelope"
        )
        for axis in axes[component_index]:
            axis.set_xlabel("Time after impact (s)")
            axis.grid(alpha=0.22)
    axes[0, 0].set_title("Filtered waveforms, common 50-245 s window")
    axes[0, 1].set_title("5 s-smoothed envelopes; observation shown to 1000 s")
    axes[0, 0].legend(fontsize=7.5, ncol=2)
    axes[0, 1].legend(fontsize=7.5, ncol=2)
    fig.suptitle(
        "A16S12 observation versus four S12 synthetics; one 3C RMS scale per model",
        fontsize=15,
    )
    save_figure(fig, "figure7_A16S12_observed_vs_four_models.png")


def plot_observed_envelope_diagnostics(
    observed: ThreeComponentRecord,
    model_records: tuple[ThreeComponentRecord, ...],
    source_scales: tuple[float, ...],
) -> None:
    records = (observed, *model_records)
    intensities = tuple(total_energy_intensity(record) for record in records)
    scaled_intensities = (
        intensities[0],
        *(scale * scale * intensity for scale, intensity in zip(
            source_scales, intensities[1:], strict=True
        )),
    )
    observed_reference = float(
        np.max(smoothed_intensity(observed.time, intensities[0], 20.0))
    )
    peak_statistics = tuple(
        peak_time_statistics(record.time, intensity)
        for record, intensity in zip(records, intensities, strict=True)
    )

    fig, axes = plt.subplots(3, 1, figsize=(14, 11), constrained_layout=True)
    for record, intensity in zip(records, scaled_intensities, strict=True):
        axes[0].plot(
            record.time,
            smoothed_intensity(record.time, intensity, 20.0) / observed_reference,
            color=record.color,
            linewidth=1.1,
            label=record.name,
        )
    axes[0].set_xlim(0.0, ENVELOPE_DISPLAY_END_S)
    axes[0].axvspan(
        min(record.time[-1] for record in model_records),
        ENVELOPE_DISPLAY_END_S,
        color="#DDDDDD",
        alpha=0.22,
    )
    axes[0].set_ylabel("20 s-smoothed 3C energy / observed peak")
    axes[0].set_title("Three-component energy envelopes after source-energy matching")
    axes[0].grid(alpha=0.22)
    axes[0].legend(fontsize=8, ncol=2)

    for record, intensity in zip(records, intensities, strict=True):
        sample_interval = float(np.median(np.diff(record.time)))
        cumulative = np.cumsum(intensity, dtype=np.float64) * sample_interval
        axes[1].plot(
            record.time,
            cumulative / cumulative[-1],
            color=record.color,
            linewidth=1.1,
            label=record.name,
        )
    axes[1].set_xlim(0.0, ENVELOPE_DISPLAY_END_S)
    axes[1].set_ylim(-0.02, 1.02)
    axes[1].axvspan(
        min(record.time[-1] for record in model_records),
        ENVELOPE_DISPLAY_END_S,
        color="#DDDDDD",
        alpha=0.22,
    )
    axes[1].set_ylabel("Fraction of each available record's energy")
    axes[1].set_title("Recorded-energy accumulation (synthetics end at 250 s)")
    axes[1].grid(alpha=0.22)

    for record, statistics in zip(records, peak_statistics, strict=True):
        intensity = total_energy_intensity(record)
        sample_interval = float(np.median(np.diff(record.time)))
        candidate_times = []
        for smoothing_window_s in PEAK_SMOOTHING_WINDOWS_S:
            sample_count = max(
                1, int(round(smoothing_window_s / sample_interval))
            )
            smooth = uniform_filter1d(intensity, sample_count, mode="nearest")
            candidate_times.append(record.time[np.argmax(smooth)])
        axes[2].plot(
            PEAK_SMOOTHING_WINDOWS_S,
            candidate_times,
            color=record.color,
            marker="o",
            linewidth=1.1,
            label=(
                f"{record.name}: median {float(statistics.median_s):.1f} s"
            ),
        )
    axes[2].set_xlabel("Envelope smoothing-window duration (s)")
    axes[2].set_ylabel("3C peak-energy time (s)")
    axes[2].set_title("Rise-time sensitivity requested by Reviewer #2")
    axes[2].grid(alpha=0.22)
    axes[2].legend(fontsize=8, ncol=2)
    fig.suptitle(
        "A16S12 envelope duration and peak-time diagnostics",
        fontsize=15,
    )
    save_figure(fig, "figure8_A16S12_envelope_rise_time_diagnostics.png")


def write_observed_model_metrics(
    observed: ThreeComponentRecord,
    model_records: tuple[ThreeComponentRecord, ...],
    source_scales: tuple[float, ...],
) -> None:
    records = (observed, *model_records)
    rows: list[dict[str, str | float]] = []
    observed_comparison_end = min(
        SOURCE_MATCH_WINDOW_S[1],
        observed.time[-1],
        *(record.time[-1] for record in model_records),
    )
    comparison_time = observed.time[
        (observed.time >= SOURCE_MATCH_WINDOW_S[0])
        & (observed.time <= observed_comparison_end)
    ]
    observed_comparison = np.vstack(
        [np.interp(comparison_time, observed.time, row) for row in observed.filtered]
    )
    observed_total_envelope = smoothed_intensity(
        comparison_time,
        np.sum(analytic_energy(observed_comparison), axis=0),
        5.0,
    )

    for record_index, record in enumerate(records):
        intensity = total_energy_intensity(record)
        statistics = peak_time_statistics(record.time, intensity)
        t05 = energy_quantile_time(record.time, intensity, 0.05)
        row: dict[str, str | float] = {
            "record": record.name,
            "source_scale_to_observed_3c_rms_50_245s": (
                1.0 if record_index == 0 else source_scales[record_index - 1]
            ),
            "raw_dominant_frequency_Z_hz": record.dominant_frequencies_hz[0],
            "raw_dominant_frequency_E_hz": record.dominant_frequencies_hz[1],
            "raw_dominant_frequency_N_hz": record.dominant_frequencies_hz[2],
            "peak_energy_time_median_s": float(statistics.median_s),
            "peak_energy_time_min_s": float(statistics.minimum_s),
            "peak_energy_time_max_s": float(statistics.maximum_s),
            "peak_energy_time_std_s": float(statistics.standard_deviation_s),
            "energy_t05_s": t05,
            "rise_duration_t05_to_peak_median_s": float(statistics.median_s) - t05,
            "energy_t50_s": energy_quantile_time(record.time, intensity, 0.50),
            "energy_t95_s": energy_quantile_time(record.time, intensity, 0.95),
            "recorded_energy_fraction_before_250s": energy_fraction_before(
                record.time, intensity, 250.0
            ),
            "recorded_energy_fraction_before_1000s": energy_fraction_before(
                record.time, intensity, 1_000.0
            ),
            "early_waveform_correlation_Z": "",
            "early_waveform_correlation_E": "",
            "early_waveform_correlation_N": "",
            "early_3c_waveform_correlation": "",
            "early_3c_normalized_rmse": "",
            "early_3c_envelope_correlation_zero_lag": "",
            "early_3c_envelope_correlation_best_lag": "",
            "best_envelope_lag_model_shift_s": "",
        }
        if record_index > 0:
            source_scale = source_scales[record_index - 1]
            model_comparison = np.vstack(
                [
                    np.interp(comparison_time, record.time, component)
                    for component in record.filtered
                ]
            )
            scaled_model = source_scale * model_comparison
            component_correlations = [
                pearson_correlation(observed_comparison[index], scaled_model[index])
                for index in range(3)
            ]
            for component_label, correlation in zip(
                COMPONENT_LABELS, component_correlations, strict=True
            ):
                row[f"early_waveform_correlation_{component_label}"] = correlation
            row["early_3c_waveform_correlation"] = pearson_correlation(
                observed_comparison.ravel(), scaled_model.ravel()
            )
            observed_rms = float(
                np.sqrt(np.mean(observed_comparison * observed_comparison))
            )
            row["early_3c_normalized_rmse"] = float(
                np.sqrt(np.mean((observed_comparison - scaled_model) ** 2))
                / observed_rms
            )
            model_total_envelope = smoothed_intensity(
                comparison_time,
                np.sum(analytic_energy(scaled_model), axis=0),
                5.0,
            )
            row["early_3c_envelope_correlation_zero_lag"] = pearson_correlation(
                observed_total_envelope, model_total_envelope
            )
            best_correlation, best_lag = best_lagged_correlation(
                observed_total_envelope,
                model_total_envelope,
                float(np.median(np.diff(comparison_time))),
            )
            row["early_3c_envelope_correlation_best_lag"] = best_correlation
            row["best_envelope_lag_model_shift_s"] = best_lag
        rows.append(row)

    csv_file = OUTPUT_DIR / "A16S12_observed_model_comparison_metrics.csv"
    with csv_file.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    station_xy, ray_station_indices = build_station_geometry()
    epicentral_distance_km = np.linalg.norm(
        station_xy - EARTHQUAKE_SOURCE_XY, axis=1
    ) / 1_000.0

    models = tuple(load_model(config) for config in MODELS)
    write_dominant_frequency_csv(models, ray_station_indices, epicentral_distance_km)
    plot_s12(models)

    for ray_number, station_indices in enumerate(ray_station_indices, start=1):
        selected = station_indices[::STATION_STRIDE]
        if selected[-1] != station_indices[-1]:
            selected = np.append(selected, station_indices[-1])
        for station_index in selected:
            plot_offset_station(
                models,
                int(station_index),
                ray_number,
                float(epicentral_distance_km[station_index]),
            )

    peak_times = compute_peak_energy_times(models)
    terrain_elevation_km = sample_topography(load_topography(), station_xy)
    write_peak_energy_csv(
        models, peak_times, ray_station_indices, epicentral_distance_km
    )
    plot_peak_energy_times(
        models,
        peak_times,
        ray_station_indices,
        epicentral_distance_km,
        terrain_elevation_km,
    )
    write_and_plot_distance_fits(
        models, peak_times, ray_station_indices, epicentral_distance_km
    )

    observed = load_observed_s12()
    model_records = tuple(load_s12_model_components(config) for config in MODELS)
    source_scales = tuple(
        source_matching_scale(observed, record) for record in model_records
    )
    plot_observed_three_components(observed)
    plot_observed_model_comparison(observed, model_records, source_scales)
    plot_observed_envelope_diagnostics(observed, model_records, source_scales)
    write_observed_model_metrics(observed, model_records, source_scales)
    print(
        "Observed raw dominant frequencies (Z/E/N): "
        + ", ".join(
            f"{frequency:.6f} Hz"
            for frequency in observed.dominant_frequencies_hz
        )
    )
    print(
        "Model source-matching factors (M1-M4, one factor for all 3 components): "
        + ", ".join(f"{scale:.6g}" for scale in source_scales)
    )
    print(f"Finished. Figures saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
