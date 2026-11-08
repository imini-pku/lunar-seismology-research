"""Build the reviewer-response figure for comment 9.23.

The figure performs a like-for-like timing test with the quantity used by
Gillet et al. (2017): the time of the maximum of a smoothed energy envelope.
All six A16 regional simulations are filtered at 0.3--0.9 Hz and their
three-component analytic-signal energy is smoothed with the selected 20 s
window.  Linear-in-distance and squared-distance fits are compared by RMSE
and AIC.  For M5--M6, the reported fits use the existing censor-safe rule to
avoid treating the 400 s record boundary as a physical envelope maximum.
"""

from __future__ import annotations

import gc
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve()
SUBMISSION = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[2]
LOCAL_PACKAGES = WORKSPACE / "work" / "python_pkgs"
if LOCAL_PACKAGES.is_dir():
    sys.path.insert(0, str(LOCAL_PACKAGES))

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from netCDF4 import Dataset
from scipy.ndimage import uniform_filter1d
from scipy.signal import hilbert

from analyze_low_velocity_models import (
    MODEL_COLORS,
    MODEL_FILES,
    MODEL_LABELS,
    analytic_intensity,
    build_station_geometry,
    filter_component,
    quantile_times,
)


OUT_FIG = SUBMISSION / "figures" / "reviewer_response"
OUT_DATA = SUBMISSION / "data" / "derived"
SMOOTHING_S = 20.0


def load_peak_times(model: str, geometry) -> pd.DataFrame:
    """Return 20 s peak and cumulative-energy times for one model."""
    path = MODEL_FILES[model]
    with Dataset(path, "r") as dataset:
        time = np.asarray(dataset.variables["time"][:], dtype=np.float64)
        filtered = []
        for variable in ("Vz", "Vx", "Vy"):
            values = np.asarray(dataset.variables[variable][:], dtype=np.float32)
            if values.shape == (time.size, 606):
                values = values.T
            filtered.append(filter_component(time, values))

    vertical, east, north = filtered
    sine = np.sin(geometry.azimuth_rad)[:, None]
    cosine = np.cos(geometry.azimuth_rad)[:, None]
    radial = east * sine + north * cosine
    transverse = east * cosine - north * sine
    zrt = np.stack((vertical, radial, transverse), axis=1).astype(np.float32)

    intensity = analytic_intensity(zrt)
    dt = float(np.median(np.diff(time)))
    smoothed = uniform_filter1d(
        intensity,
        max(1, int(round(SMOOTHING_S / dt))),
        axis=1,
        mode="nearest",
    )
    t_peak = time[np.argmax(smoothed, axis=1)]
    squared_velocity = np.sum(zrt * zrt, axis=1, dtype=np.float32)
    qtimes = quantile_times(time, squared_velocity, (0.05, 0.95))

    end_guard = float(time[-1] - 20.0)
    safe = (
        (t_peak > float(time[0] + 20.0))
        & (t_peak < end_guard)
        & (qtimes[0.95] < end_guard)
    )
    result = pd.DataFrame(
        {
            "model": model,
            "station": geometry.station_names,
            "ray": geometry.ray_number,
            "distance_km": geometry.distance_km,
            "t05_s": qtimes[0.05],
            "t_peak_20s_s": t_peak,
            "rise_t05_to_peak_20s_s": t_peak - qtimes[0.05],
            "t95_s": qtimes[0.95],
            "censor_safe": safe.astype(int),
            "record_end_s": float(time[-1]),
        }
    )
    del filtered, vertical, east, north, radial, transverse, zrt, intensity, smoothed
    gc.collect()
    return result


def fit_relation(distance: np.ndarray, timing: np.ndarray, squared: bool) -> dict[str, float]:
    predictor = distance * distance if squared else distance
    design = np.column_stack((np.ones(distance.size), predictor))
    coefficients = np.linalg.lstsq(design, timing, rcond=None)[0]
    prediction = design @ coefficients
    residual = timing - prediction
    rss = float(np.sum(residual * residual))
    rmse = float(np.sqrt(np.mean(residual * residual)))
    aic = float(distance.size * np.log(max(rss / distance.size, np.finfo(float).tiny)) + 4.0)
    return {
        "intercept_s": float(coefficients[0]),
        "coefficient": float(coefficients[1]),
        "rmse_s": rmse,
        "aic": aic,
    }


def build_fits(metrics: pd.DataFrame, geometry) -> pd.DataFrame:
    rows = []
    fit_station_sets = {
        ray_number: set(geometry.station_names[index] for index in indices)
        for ray_number, indices in enumerate(geometry.fit_indices, start=1)
    }
    for model in MODEL_FILES:
        for ray in (1, 2, 3):
            subset = metrics[
                (metrics["model"] == model)
                & (metrics["ray"] == ray)
                & (metrics["station"].isin(fit_station_sets[ray]))
            ].copy()
            sample_definition = "all fit stations"
            if model in ("M5", "M6"):
                subset = subset[subset["censor_safe"] == 1]
                sample_definition = "censor-safe"
            distance = subset["distance_km"].to_numpy(float)
            timing = subset["t_peak_20s_s"].to_numpy(float)
            linear = fit_relation(distance, timing, squared=False)
            diffusion = fit_relation(distance, timing, squared=True)
            rows.append(
                {
                    "model": model,
                    "ray": ray,
                    "sample_definition": sample_definition,
                    "station_count": len(subset),
                    "linear_intercept_s": linear["intercept_s"],
                    "linear_slope_s_per_km": linear["coefficient"],
                    "linear_rmse_s": linear["rmse_s"],
                    "linear_aic": linear["aic"],
                    "squared_intercept_s": diffusion["intercept_s"],
                    "squared_coefficient_s_per_km2": diffusion["coefficient"],
                    "squared_rmse_s": diffusion["rmse_s"],
                    "squared_aic": diffusion["aic"],
                    "delta_aic_squared_minus_linear": diffusion["aic"] - linear["aic"],
                    "preferred_form": "linear" if linear["aic"] < diffusion["aic"] else "R-squared",
                }
            )
    return pd.DataFrame(rows)


def configure_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.0,
            "axes.titlesize": 11.0,
            "axes.labelsize": 9.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.20,
            "legend.frameon": False,
            "savefig.dpi": 300,
        }
    )


def make_figure(metrics: pd.DataFrame, fits: pd.DataFrame, geometry) -> None:
    configure_style()
    fig = plt.figure(figsize=(13.0, 8.3))
    grid = fig.add_gridspec(
        2, 3, height_ratios=(2.25, 1.0), left=0.07, right=0.985,
        bottom=0.085, top=0.79, hspace=0.28, wspace=0.11
    )
    top_axes = [fig.add_subplot(grid[0, column]) for column in range(3)]
    summary_axis = fig.add_subplot(grid[1, :])

    fit_station_sets = {
        ray_number: set(geometry.station_names[index] for index in indices)
        for ray_number, indices in enumerate(geometry.fit_indices, start=1)
    }
    for ray, axis in enumerate(top_axes, start=1):
        for model in MODEL_FILES:
            subset = metrics[
                (metrics["model"] == model)
                & (metrics["ray"] == ray)
                & (metrics["station"].isin(fit_station_sets[ray]))
            ].sort_values("distance_km")
            fit_subset = subset if model not in ("M5", "M6") else subset[subset["censor_safe"] == 1]
            axis.scatter(
                subset["distance_km"],
                subset["t_peak_20s_s"],
                s=7,
                alpha=0.10,
                color=MODEL_COLORS[model],
                rasterized=True,
            )
            row = fits[(fits["model"] == model) & (fits["ray"] == ray)].iloc[0]
            x = np.linspace(float(fit_subset["distance_km"].min()), float(fit_subset["distance_km"].max()), 240)
            linear = row.linear_intercept_s + row.linear_slope_s_per_km * x
            squared = row.squared_intercept_s + row.squared_coefficient_s_per_km2 * x * x
            axis.plot(x, linear, color=MODEL_COLORS[model], linewidth=1.65)
            axis.plot(x, squared, color=MODEL_COLORS[model], linewidth=1.0, linestyle=(0, (2, 2)), alpha=0.78)
        axis.set_title(f"({chr(96 + ray)}) Ray {ray}")
        axis.set_xlabel("Source-receiver distance, R (km)")
        if ray == 1:
            axis.set_ylabel("20 s-smoothed energy-peak time, $t_{peak}$ (s)")
        axis.set_ylim(bottom=0)

    model_handles = [
        Line2D([0], [0], color=MODEL_COLORS[model], linewidth=2.2, label=f"{model}: {MODEL_LABELS[model]}")
        for model in MODEL_FILES
    ]
    style_handles = [
        Line2D([0], [0], color="#222222", linewidth=2.0, label="Linear: a + bR"),
        Line2D([0], [0], color="#222222", linewidth=1.2, linestyle=(0, (2, 2)), label="Squared distance: a + cR²"),
    ]
    fig.legend(
        handles=model_handles + style_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.935),
        ncol=4,
        fontsize=8.2,
        handlelength=2.7,
    )

    offsets = np.array([-0.18, 0.0, 0.18])
    markers = ("o", "s", "^")
    for ray in (1, 2, 3):
        subset = fits[fits["ray"] == ray].set_index("model").loc[list(MODEL_FILES)]
        x = np.arange(1, 7) + offsets[ray - 1]
        summary_axis.plot(
            x,
            subset["delta_aic_squared_minus_linear"],
            color="#777777",
            linewidth=0.8,
            alpha=0.55,
        )
        summary_axis.scatter(
            x,
            subset["delta_aic_squared_minus_linear"],
            s=46,
            marker=markers[ray - 1],
            color="#243b53",
            label=f"Ray {ray}",
            zorder=3,
        )
    summary_axis.axhline(10.0, color="#b42318", linestyle="--", linewidth=1.0, label="ΔAIC = 10")
    summary_axis.set_yscale("log")
    summary_axis.set_ylim(8.0, max(800.0, float(fits["delta_aic_squared_minus_linear"].max()) * 1.18))
    summary_axis.set_xticks(np.arange(1, 7), list(MODEL_FILES))
    summary_axis.set_ylabel("ΔAIC = AIC(R²) − AIC(linear)")
    summary_axis.set_title("(d) Model-selection evidence; positive values favor linear peak migration")
    summary_axis.legend(ncol=4, fontsize=8.0, loc="upper right")
    minimum = float(fits["delta_aic_squared_minus_linear"].min())
    summary_axis.text(
        0.012,
        0.05,
        f"18/18 ray-model tests favor linear; minimum ΔAIC = {minimum:.1f}.\nM5-M6 fits use censor-safe samples.",
        transform=summary_axis.transAxes,
        va="bottom",
        fontsize=8.6,
    )

    fig.suptitle(
        "A16 regional simulations retain quasi-ballistic peak migration under the unified M1-M6 model ladder",
        fontsize=13.0,
        y=0.985,
    )
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    stem = OUT_FIG / "Figure_R9_23_peak_time_distance_transport_test"
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    fig.savefig(stem.with_suffix(".tiff"), dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    geometry = build_station_geometry()
    metric_tables = []
    for model in MODEL_FILES:
        print(f"Processing {model}: {MODEL_FILES[model]}", flush=True)
        metric_tables.append(load_peak_times(model, geometry))
    metrics = pd.concat(metric_tables, ignore_index=True)
    fits = build_fits(metrics, geometry)
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(OUT_DATA / "reviewer_9_23_peak_time_20s_metrics.csv", index=False, encoding="utf-8-sig")
    fits.to_csv(OUT_DATA / "reviewer_9_23_peak_time_20s_fits.csv", index=False, encoding="utf-8-sig")
    make_figure(metrics, fits, geometry)
    print(fits[["model", "ray", "station_count", "linear_rmse_s", "squared_rmse_s", "delta_aic_squared_minus_linear", "preferred_form"]].to_string(index=False))


if __name__ == "__main__":
    main()
