"""Draw Figure R4: waveform-shape and energy convergence versus topography resolution."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "derived" / "halfspace_resolution_station_metrics.csv"
OUT = ROOT / "figures" / "reviewer_response"


def read_metrics() -> dict[int, dict[str, list[float]]]:
    grouped: dict[int, dict[str, list[float]]] = {}
    with DATA.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            resolution = int(float(row["resolution_m"]))
            target = grouped.setdefault(
                resolution,
                {"maximum_correlation_within_2s": [], "absolute_energy_relative_error": []},
            )
            for column in target:
                value = row[column]
                if value:
                    target[column].append(float(value))
    return grouped


def quantiles(
    grouped: dict[int, dict[str, list[float]]], column: str
) -> dict[int, dict[str, float]]:
    result: dict[int, dict[str, float]] = {}
    for resolution, columns in grouped.items():
        q10, q25, q50, q75, q90 = np.quantile(
            np.asarray(columns[column], dtype=float), [0.10, 0.25, 0.50, 0.75, 0.90]
        )
        result[resolution] = {
            "p10": float(q10),
            "q25": float(q25),
            "median": float(q50),
            "q75": float(q75),
            "p90": float(q90),
        }
    return result


def series(summary: dict[int, dict[str, float]], resolutions: np.ndarray, key: str) -> np.ndarray:
    return np.asarray([summary[int(resolution)][key] for resolution in resolutions], dtype=float)


def main() -> None:
    grouped = read_metrics()
    corr = quantiles(grouped, "maximum_correlation_within_2s")
    energy = quantiles(grouped, "absolute_energy_relative_error")
    for values in energy.values():
        for key in values:
            values[key] *= 100.0

    # Equal spacing keeps every tested grid visible; labels preserve the true scale.
    resolutions_m = np.array([10000, 6250, 4000, 2500, 1000, 500, 250, 125])
    positions = np.arange(resolutions_m.size)
    labels = ["10", "6.25", "4", "2.5", "1", "0.5", "0.25", "0.125"]
    mpl.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 9.5,
            "axes.linewidth": 0.8,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    blue = "#2166AC"
    blue_light = "#92C5DE"
    orange = "#D6604D"
    green = "#1B7837"
    gray = "#555555"

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.55), sharex=True)

    # (a) Lag-tolerant three-component waveform-shape correlation.
    ax = axes[0]
    ax.fill_between(
        positions,
        series(corr, resolutions_m, "p10"),
        series(corr, resolutions_m, "p90"),
        color=blue_light,
        alpha=0.32,
        linewidth=0,
        label="10th–90th percentile",
    )
    ax.plot(
        positions,
        series(corr, resolutions_m, "median"),
        color=blue,
        marker="o",
        markersize=5.2,
        linewidth=1.8,
        label="Median",
        zorder=3,
    )
    ax.axhline(0.95, color=gray, linestyle="--", linewidth=1.0, label="Shape criterion: r = 0.95")
    idx500 = int(np.where(resolutions_m == 500)[0][0])
    idx250 = int(np.where(resolutions_m == 250)[0][0])
    corr500 = corr[500]["median"]
    corr250 = corr[250]["median"]
    ax.scatter(idx500, corr500, s=82, color=orange, edgecolor="white", linewidth=0.9, zorder=5)
    ax.scatter(idx250, corr250, s=70, marker="D", color=green, edgecolor="white", linewidth=0.9, zorder=5)
    ax.annotate(
        f"0.5 km: r = {corr500:.3f}\nshape retained",
        xy=(idx500, corr500),
        xytext=(-90, -49),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "color": orange, "lw": 1.1},
        color=orange,
        ha="left",
        va="top",
        fontweight="bold",
    )
    ax.annotate(
        f"0.25 km: r = {corr250:.3f}",
        xy=(idx250, corr250),
        xytext=(7, -34),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "color": green, "lw": 1.0},
        color=green,
        ha="left",
        va="top",
    )
    ax.set_ylim(0.15, 1.025)
    ax.set_ylabel("Maximum 3-C correlation within ±2 s")
    ax.set_title("(a) Waveform-shape convergence", loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="lower right", fontsize=8.3)

    # (b) Absolute energy error. Symmetric-log keeps the exact zero of the
    # reference model visible while retaining the orders-of-magnitude range.
    ax = axes[1]
    ax.fill_between(
        positions,
        series(energy, resolutions_m, "p10"),
        series(energy, resolutions_m, "p90"),
        color="#F4A582",
        alpha=0.27,
        linewidth=0,
        label="10th–90th percentile",
    )
    ax.plot(
        positions,
        series(energy, resolutions_m, "median"),
        color=orange,
        marker="o",
        markersize=5.2,
        linewidth=1.8,
        label="Median",
        zorder=3,
    )
    ax.axhline(10.0, color=gray, linestyle="--", linewidth=1.0, label="Energy criterion: 10%")
    err500 = energy[500]["median"]
    err250 = energy[250]["median"]
    ax.scatter(idx500, err500, s=82, color=orange, edgecolor="white", linewidth=0.9, zorder=5)
    ax.scatter(idx250, err250, s=70, marker="D", color=green, edgecolor="white", linewidth=0.9, zorder=5)
    ax.annotate(
        f"0.5 km: {err500:.1f}%\nenergy not converged",
        xy=(idx500, err500),
        xytext=(-92, 45),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "color": orange, "lw": 1.1},
        color=orange,
        ha="left",
        va="bottom",
        fontweight="bold",
    )
    ax.annotate(
        f"0.25 km: {err250:.1f}%\njoint convergence",
        xy=(idx250, err250),
        xytext=(8, 33),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "color": green, "lw": 1.0},
        color=green,
        ha="left",
        va="bottom",
    )
    ax.annotate(
        "0% (reference)",
        xy=(positions[-1], 0.0),
        xytext=(-5, 12),
        textcoords="offset points",
        ha="right",
        va="bottom",
        color=gray,
    )
    ax.set_yscale("symlog", linthresh=10.0, linscale=1.0, base=10)
    ax.set_ylim(-0.25, 10000)
    ax.set_yticks([0, 5, 10, 20, 100, 1000, 10000])
    ax.set_yticklabels(["0", "5", "10", "20", "100", "1,000", "10,000"])
    ax.set_ylabel("Absolute relative energy error (%)")
    ax.set_title("(b) Energy convergence", loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="upper left", fontsize=8.3)

    for ax in axes:
        ax.set_xticks(positions, labels)
        ax.set_xlabel("Nominal topography resolution (km; finer →)")
        ax.grid(axis="y", color="#D9D9D9", linewidth=0.6, alpha=0.8)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", rotation=0)

    fig.suptitle(
        "Topographic-resolution convergence in the 0.3–0.9 Hz band",
        fontsize=13,
        fontweight="bold",
        y=0.995,
    )
    fig.text(
        0.5,
        0.935,
        "Relative to the 0.125 km reference model; 216 three-component stations",
        ha="center",
        va="top",
        color=gray,
        fontsize=9.2,
    )
    fig.subplots_adjust(left=0.085, right=0.985, bottom=0.15, top=0.84, wspace=0.27)

    OUT.mkdir(parents=True, exist_ok=True)
    base = OUT / "Figure_R4_resolution_shape_energy_convergence"
    fig.savefig(base.with_suffix(".png"), dpi=400, bbox_inches="tight", facecolor="white")
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    fig.savefig(
        base.with_suffix(".tiff"),
        dpi=400,
        bbox_inches="tight",
        facecolor="white",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(fig)

    # Machine-readable values used by the two highlighted conclusions.
    highlighted = [
        {
                "resolution_km": 0.5,
                "median_maximum_3c_correlation_pm2s": corr500,
                "median_absolute_energy_error_percent": err500,
                "interpretation": "waveform shape retained; energy not converged",
        },
        {
                "resolution_km": 0.25,
                "median_maximum_3c_correlation_pm2s": corr250,
                "median_absolute_energy_error_percent": err250,
                "interpretation": "joint waveform-energy convergence",
        },
    ]
    with (OUT / "Figure_R4_highlighted_values.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(highlighted[0]))
        writer.writeheader()
        writer.writerows(highlighted)


if __name__ == "__main__":
    main()
