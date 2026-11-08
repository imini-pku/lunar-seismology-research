"""Build English publication figures from archived, verified CSV tables."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "derived"
MAIN = ROOT / "figures" / "main"
MAIN.mkdir(parents=True, exist_ok=True)

COLORS = {1: "#0072B2", 2: "#D55E00", 3: "#009E73"}
MODEL_COLORS = {"M1": "#222222", "M2": "#D55E00", "M3": "#0072B2", "M4": "#CC79A7"}


def style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.dpi": 300,
        }
    )


def save(fig: plt.Figure, stem: str) -> None:
    fig.savefig(MAIN / f"{stem}.png", bbox_inches="tight", facecolor="white")
    fig.savefig(MAIN / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figure_1(df: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(7.3, 6.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=(1.05, 1.0))

    ax = fig.add_subplot(gs[0, 0])
    ax.set_xlim(-0.5, 1.5)
    ax.set_ylim(-0.5, 1.5)
    labels = {
        (0, 0): ("M1", "flat\nno heterogeneity"),
        (1, 0): ("M2", "flat\nheterogeneity"),
        (0, 1): ("M3", "topography\nno heterogeneity"),
        (1, 1): ("M4", "topography\nheterogeneity"),
    }
    for (x, y), (model, desc) in labels.items():
        ax.scatter(x, y, s=1200, marker="s", color=MODEL_COLORS[model], alpha=0.14,
                   edgecolor=MODEL_COLORS[model], linewidth=1.5)
        ax.text(x, y + 0.08, model, ha="center", va="center", weight="bold", fontsize=12)
        ax.text(x, y - 0.16, desc, ha="center", va="center", fontsize=8)
    ax.annotate("add heterogeneity", xy=(1, 1.38), xytext=(0, 1.38),
                arrowprops=dict(arrowstyle="->", color="#555555"), ha="center")
    ax.annotate("add topography", xy=(-0.38, 1), xytext=(-0.38, 0),
                arrowprops=dict(arrowstyle="->", color="#555555"), va="center", rotation=90)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("(a) 2 x 2 numerical experiment", loc="left", weight="bold")

    ax = fig.add_subplot(gs[0, 1])
    primary = df[df["included_in_primary_analysis"] == 1]
    for ray in (1, 2, 3):
        sub = primary[primary["ray"].astype(str) == str(ray)].sort_values("distance_km")
        ax.plot(sub["distance_km"], sub["elevation_km"], color=COLORS[ray], lw=1.6,
                label=f"Profile {ray} (n={len(sub)})")
    ax.set_xlabel("Epicentral distance (km)")
    ax.set_ylabel("Surface elevation (km)")
    ax.legend(frameon=False, loc="best")
    ax.set_title("(b) Receiver-profile topography", loc="left", weight="bold")

    ax = fig.add_subplot(gs[1, :])
    ax.axis("off")
    steps = [
        (0.08, "606 receivers\nthree components"),
        (0.31, "0.3-0.9 Hz\npaired metrics"),
        (0.54, "575 profile receivers\ndistance control"),
        (0.77, "factorial effects\nand interaction"),
        (0.95, "Apollo S12\nexclusion test"),
    ]
    for index, (x, label) in enumerate(steps):
        ax.text(x, 0.52, label, ha="center", va="center", transform=ax.transAxes,
                bbox=dict(boxstyle="round,pad=0.45", facecolor="#F2F4F7", edgecolor="#6B7280"))
        if index < len(steps) - 1:
            ax.annotate("", xy=(steps[index + 1][0] - 0.08, 0.52), xytext=(x + 0.08, 0.52),
                        xycoords=ax.transAxes, textcoords=ax.transAxes,
                        arrowprops=dict(arrowstyle="->", lw=1.2, color="#4B5563"))
    ax.text(0.01, 0.96, "(c) Evidence workflow", transform=ax.transAxes,
            ha="left", va="top", weight="bold", fontsize=10)
    ax.text(0.5, 0.06,
            "Path relief is a profile-based surface proxy; Apollo comparison is one impact-station pair.",
            transform=ax.transAxes, ha="center", va="bottom", color="#555555", fontsize=8)
    save(fig, "Figure_1_experiment_design")


def residualize(values: np.ndarray, distance: np.ndarray, degree: int = 3) -> np.ndarray:
    valid = np.isfinite(values) & np.isfinite(distance)
    output = np.full_like(values, np.nan, dtype=float)
    fit = np.polyfit(distance[valid], values[valid], degree)
    residual = values[valid] - np.polyval(fit, distance[valid])
    output[valid] = (residual - residual.mean()) / residual.std(ddof=1)
    return output


def blocks(x: np.ndarray, y: np.ndarray, size: int = 10) -> tuple[np.ndarray, np.ndarray]:
    bx, by = [], []
    valid = np.isfinite(x) & np.isfinite(y)
    indices = np.flatnonzero(valid)
    for start in range(0, len(indices), size):
        take = indices[start:start + size]
        if len(take) >= size // 2:
            bx.append(np.mean(x[take]))
            by.append(np.mean(y[take]))
    return np.asarray(bx), np.asarray(by)


def figure_4(df: pd.DataFrame) -> None:
    primary = df[df["included_in_primary_analysis"] == 1].copy()
    metrics = [
        ("topography_no_scatter__log_peak_amplitude", "Topographic effect on peak amplitude"),
        ("topography_no_scatter__log_total_energy", "Topographic effect on total energy"),
        ("topography_no_scatter__log_duration_90_s", "Topographic effect on T90"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.65), constrained_layout=True)
    for ax, (column, ylabel) in zip(axes, metrics, strict=True):
        all_x, all_y = [], []
        for ray in (1, 2, 3):
            sub = primary[primary["ray"].astype(str) == str(ray)].sort_values("distance_km")
            x = residualize(sub["path_relief_range_km"].to_numpy(float), sub["distance_km"].to_numpy(float))
            y = residualize(sub[column].to_numpy(float), sub["distance_km"].to_numpy(float))
            bx, by = blocks(x, y)
            rho = spearmanr(bx, by).statistic
            ax.scatter(bx, by, s=20, color=COLORS[ray], alpha=0.78,
                       label=f"P{ray}: rho={rho:+.2f}")
            if ray in (2, 3):
                all_x.extend(bx)
                all_y.extend(by)
        slope, intercept = np.polyfit(np.asarray(all_x), np.asarray(all_y), 1)
        line_x = np.linspace(min(all_x), max(all_x), 100)
        ax.plot(line_x, intercept + slope * line_x, color="#333333", lw=1.2, ls="--")
        ax.axhline(0, color="#BBBBBB", lw=0.6)
        ax.axvline(0, color="#BBBBBB", lw=0.6)
        ax.set_xlabel("Distance-controlled path relief")
        ax.set_ylabel(ylabel)
        ax.legend(frameon=False, fontsize=7, loc="best")
    axes[0].set_title("(a) Coherent peak", loc="left", weight="bold")
    axes[1].set_title("(b) Recorded energy", loc="left", weight="bold")
    axes[2].set_title("(c) Energy duration", loc="left", weight="bold")
    fig.suptitle("Cumulative relief predicts topographic effects on profiles 2 and 3", weight="bold")
    save(fig, "Figure_4_path_relief")


def figure_s1() -> None:
    table = pd.read_csv(DATA / "literature_guided_tmax_smoothing_sensitivity.csv")
    table = table[table["comparison"] == "scatter_flat"].copy()
    windows = np.asarray([5, 10, 20], dtype=float)
    columns = [
        "median_delta_tmax_5period_s",
        "median_delta_tmax_10period_s",
        "median_delta_tmax_20period_s",
    ]
    fig, ax = plt.subplots(figsize=(5.6, 3.4), constrained_layout=True)
    labels = {"all": "All profiles", "1": "Profile 1", "2": "Profile 2", "3": "Profile 3"}
    colors = {"all": "#222222", "1": COLORS[1], "2": COLORS[2], "3": COLORS[3]}
    for _, row in table.iterrows():
        ray = str(row["ray"])
        values = row[columns].to_numpy(dtype=float)
        ax.plot(windows, values, marker="o", lw=1.7, color=colors[ray], label=labels[ray])
    ax.axhline(0, color="#999999", lw=0.8)
    ax.set_xticks(windows, ["5 periods", "10 periods", "20 periods"])
    ax.set_ylabel("Median M2-M1 energy-peak delay (s)")
    ax.set_title("Peak-delay direction is robust; magnitude depends on smoothing", weight="bold")
    ax.legend(frameon=False, ncol=2)
    out = ROOT / "figures" / "supporting"
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "Figure_S1_smoothing_sensitivity.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(out / "Figure_S1_smoothing_sensitivity.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    style()
    table = pd.read_csv(DATA / "station_level_metrics.csv")
    figure_1(table)
    figure_4(table)
    figure_s1()
    print(f"Wrote publication figures to {MAIN}")


if __name__ == "__main__":
    main()
