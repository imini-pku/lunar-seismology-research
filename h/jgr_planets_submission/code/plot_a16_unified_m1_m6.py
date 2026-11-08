"""Build integrated A16/S12 M1-M6 figures from the common station table.

The figure treats M1--M6 as one continuous model ladder.  M1--M4 are the
short-window baseline states; M5/M6 add the low-velocity state while keeping
the A16 geometry and heterogeneous background.  The missing low-V/no-
heterogeneity cells are reported as a design limitation, not silently
interpreted as a complete three-factor experiment.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[1]
WORKSPACE = SCRIPT.parents[2]
LOCAL_PACKAGES = WORKSPACE / "work" / "python_pkgs"
if LOCAL_PACKAGES.is_dir():
    sys.path.insert(0, str(LOCAL_PACKAGES))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

DERIVED = ROOT / "data" / "derived"
FIGURES = ROOT / "figures" / "synthesis"
TABLE = DERIVED / "low_velocity_station_metrics.csv"

ORDER = ["M1", "M2", "M3", "M4", "M5", "M6"]
LABELS = {
    "M1": "M1\nflat / no H",
    "M2": "M2\ntopo / no H",
    "M3": "M3\nflat / H",
    "M4": "M4\ntopo / H",
    "M5": "M5\nflat / H / low-V",
    "M6": "M6\ntopo / H / low-V",
}
COLORS = {
    "M1": "#0072B2",
    "M2": "#D55E00",
    "M3": "#009E73",
    "M4": "#CC79A7",
    "M5": "#E69F00",
    "M6": "#56B4E9",
}


def style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.0,
            "axes.titlesize": 10.0,
            "axes.labelsize": 9.0,
            "xtick.labelsize": 8.0,
            "ytick.labelsize": 8.0,
            "legend.fontsize": 8.0,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
        }
    )


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not TABLE.is_file():
        raise FileNotFoundError(TABLE)
    data = pd.read_csv(TABLE)
    primary = data[(data["included_primary"] == 1) & (data["model"].isin(ORDER))].copy()
    summary = primary.groupby("model", sort=False)[
        [
            "peak_amplitude",
            "total_energy",
            "tmax_s",
            "t95_s",
            "T90_s",
            "Z_fraction",
            "R_fraction",
            "T_fraction",
        ]
    ].median().reindex(ORDER)
    summary["energy_ratio_to_M1"] = summary["total_energy"] / summary.loc["M1", "total_energy"]
    summary["T90_ratio_to_M1"] = summary["T90_s"] / summary.loc["M1", "T90_s"]
    summary.insert(0, "model", summary.index)
    return primary, summary.reset_index(drop=True)


def figure_ladder(summary: pd.DataFrame) -> Path:
    x = np.arange(len(ORDER))
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.1), constrained_layout=False)
    fig.subplots_adjust(left=0.07, right=0.98, bottom=0.11, top=0.88, wspace=0.25, hspace=0.32)

    ax = axes[0, 0]
    ax.plot(x, summary["energy_ratio_to_M1"], color="#222222", marker="o", lw=1.6, label="median energy / M1")
    ax.plot(x, summary["T90_ratio_to_M1"], color="#C44E52", marker="D", lw=1.4, label="median T90 / M1")
    ax.set_yscale("log")
    ax.set_ylabel("Ratio to M1 (log scale)")
    ax.set_title("(a) Integrated energy and duration along the M1–M6 ladder")
    ax.axvline(3.5, color="#777777", ls="--", lw=0.8)
    ax.text(3.55, 0.92, "low-V states", transform=ax.get_xaxis_transform(), fontsize=8, color="#666666")
    ax.legend(loc="upper left", frameon=False)
    ax.grid(axis="y", alpha=0.2)

    ax = axes[0, 1]
    ax.plot(x, summary["tmax_s"], color="#0072B2", marker="o", lw=1.6, label="median tmax")
    ax.plot(x, summary["t95_s"], color="#E69F00", marker="s", lw=1.5, label="median t95")
    ax.axhline(658.29, color="#222222", ls="--", lw=1.0, label="Apollo S12 tmax")
    ax.axhline(2804.62, color="#222222", ls=":", lw=1.0, label="Apollo S12 t95")
    ax.set_ylabel("Time after impact (s)")
    ax.set_title("(b) Peak and cumulative-time migration")
    ax.set_ylim(0, 3050)
    ax.axvline(3.5, color="#777777", ls="--", lw=0.8)
    ax.legend(loc="upper left", frameon=False, ncol=2, handlelength=2.2)
    ax.grid(axis="y", alpha=0.2)

    ax = axes[1, 0]
    for metric, color, marker, label in [
        ("Z_fraction", "#0072B2", "o", "Z"),
        ("R_fraction", "#D55E00", "s", "R"),
        ("T_fraction", "#009E73", "^", "T"),
    ]:
        ax.plot(x, 100.0 * summary[metric], color=color, marker=marker, lw=1.6, label=label)
    ax.set_ylabel("Median component energy (%)")
    ax.set_ylim(-2, 78)
    ax.set_title("(c) Three-component redistribution")
    ax.axvline(3.5, color="#777777", ls="--", lw=0.8)
    ax.legend(loc="center left", frameon=False, ncol=3)
    ax.grid(axis="y", alpha=0.2)

    ax = axes[1, 1]
    ax.plot(x, summary["peak_amplitude"], color="#9467BD", marker="o", lw=1.6, label="median peak amplitude")
    ax.set_ylabel("Median peak amplitude (native units)")
    ax.set_title("(d) Peak amplitude is not a sufficient proxy for duration")
    ax.axvline(3.5, color="#777777", ls="--", lw=0.8)
    ax.grid(axis="y", alpha=0.2)
    ax.legend(loc="upper left", frameon=False)

    for ax in axes.flat:
        ax.set_xticks(x, [LABELS[m] for m in ORDER])
        ax.tick_params(axis="x", pad=4)
        ax.set_xlim(-0.35, 5.35)
    fig.suptitle("A16/S12 unified model ladder: M1 → M6", fontsize=13, fontweight="bold")
    out = FIGURES / "Figure_A16_M1_M6_unified_ladder.png"
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    plt.close(fig)
    return out


def figure_tmax_distance(primary: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(14.0, 4.8), sharey=True, constrained_layout=False)
    fig.subplots_adjust(left=0.06, right=0.99, bottom=0.19, top=0.72, wspace=0.08)
    for ax, ray in zip(axes, ["1", "2", "3"]):
        ray_data = primary[primary["ray"] == ray]
        for model in ORDER:
            d = ray_data[ray_data["model"] == model]
            if d.empty:
                continue
            ax.scatter(d["distance_km"], d["tmax_s"], s=5, alpha=0.18, color=COLORS[model], linewidths=0)
            coef = np.polyfit(d["distance_km"], d["tmax_s"], 1)
            xx = np.linspace(float(d["distance_km"].min()), float(d["distance_km"].max()), 100)
            ax.plot(xx, np.polyval(coef, xx), color=COLORS[model], lw=1.2, alpha=0.9)
        ax.set_title(f"Ray {ray}")
        ax.set_xlabel("Source distance (km)")
        ax.grid(alpha=0.18)
        ax.set_xlim(0, 245)
        ax.set_ylim(0, 430)
    axes[0].set_ylabel("Peak-energy time, tmax (s)")
    handles = [Line2D([0], [0], color=COLORS[m], marker="o", lw=1.3, ms=4, label=m) for m in ORDER]
    fig.legend(handles=handles, labels=[f"{m}: {LABELS[m].replace(chr(10), ' / ')}" for m in ORDER], loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.88))
    fig.suptitle("A16/S12 peak-energy migration across the unified M1–M6 ladder", y=0.985, fontsize=12.5, fontweight="bold")
    out = FIGURES / "Figure_A16_M1_M6_tmax_distance.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def figure_rise_time_diagnostic(primary: pd.DataFrame) -> Path:
    """Diagnose the apparent plateau-linear-plateau rise-time pattern.

    The upper row uses the common 50--245 s window used for cross-state
    effects.  The lower row uses the 50--395 s M5/M6 extended diagnostics.
    The middle row plots t05 and tmax separately so endpoint clipping is
    visible instead of being folded into a single rise-time curve.
    """

    extended_path = DERIVED / "low_velocity_extended_window_metrics.csv"
    extended = pd.read_csv(extended_path)
    extended = extended[(extended["included_primary"] == 1) & extended["ray"].isin(["1", "2", "3"])].copy()
    extended["rise_to_tmax_s"] = extended["tmax_s"] - extended["t05_s"]
    ray_colors = {"1": "#0072B2", "2": "#D55E00", "3": "#009E73"}
    fig, axes = plt.subplots(3, 2, figsize=(12.8, 10.4), sharex="col", constrained_layout=False)
    fig.subplots_adjust(left=0.075, right=0.98, bottom=0.08, top=0.88, wspace=0.14, hspace=0.27)
    for col, model in enumerate(["M5", "M6"]):
        cdata = primary[(primary["model"] == model) & primary["ray"].isin(["1", "2", "3"])].copy()
        edata = extended[extended["model"] == model]
        for ax in (axes[0, col], axes[1, col]):
            ax.axvspan(0, 35, color="#999999", alpha=0.08, lw=0)
            ax.axvspan(120, 245, color="#999999", alpha=0.08, lw=0)
            ax.grid(alpha=0.18)
        ax = axes[0, col]
        for ray in ["1", "2", "3"]:
            d = cdata[cdata["ray"] == ray]
            ax.scatter(d["distance_km"], d["rise_to_tmax_s"], s=6, alpha=0.18, color=ray_colors[ray], linewidths=0)
            if len(d) >= 5:
                b = pd.cut(d["distance_km"], np.arange(0, 251, 10), right=False)
                med = d.assign(bin=b).groupby("bin", observed=True)[["distance_km", "rise_to_tmax_s"]].median()
                ax.plot(med["distance_km"], med["rise_to_tmax_s"], color=ray_colors[ray], lw=1.7, label=f"Ray {ray}")
        ax.axhline(0, color="#555555", ls="--", lw=0.8)
        ax.set_ylabel("tmax − t05 (s)")
        ax.set_title(f"{model}: common 50–245 s window")
        ax.text(0.02, 0.94, "near: tmax floor\nfar: tmax ceiling", transform=ax.transAxes, va="top", fontsize=8, color="#666666")
        ax.legend(frameon=False, loc="upper left", ncol=3)

        ax = axes[1, col]
        for ray in ["1", "2", "3"]:
            d = cdata[cdata["ray"] == ray]
            ax.scatter(d["distance_km"], d["t05_s"], s=5, alpha=0.13, color=ray_colors[ray], linewidths=0)
            ax.scatter(d["distance_km"], d["tmax_s"], s=5, alpha=0.13, color=ray_colors[ray], marker="s", linewidths=0)
        ax.axhline(50, color="#555555", ls=":", lw=0.8, label="50 s start")
        ax.axhline(245, color="#555555", ls="--", lw=0.8, label="245 s end")
        ax.set_ylabel("Time in common window (s)")
        ax.set_title(f"{model}: t05 and tmax separately")
        ax.legend(frameon=False, loc="upper left", ncol=2)
        ax.grid(alpha=0.18)

        ax = axes[2, col]
        for ray in ["1", "2", "3"]:
            d = edata[edata["ray"] == ray]
            ax.scatter(d["distance_km"], d["rise_to_tmax_s"], s=6, alpha=0.18, color=ray_colors[ray], linewidths=0)
            if len(d) >= 5:
                b = pd.cut(d["distance_km"], np.arange(0, 241, 10), right=False)
                med = d.assign(bin=b).groupby("bin", observed=True)[["distance_km", "rise_to_tmax_s"]].median()
                ax.plot(med["distance_km"], med["rise_to_tmax_s"], color=ray_colors[ray], lw=1.7)
        ax.axhline(0, color="#555555", ls="--", lw=0.8)
        ax.set_ylabel("tmax − t05 (s)")
        ax.set_xlabel("Source distance (km)")
        ax.set_title(f"{model}: extended 50–395 s diagnostic")
        ax.grid(alpha=0.18)
        ax.set_xlim(0, 245)
    fig.suptitle("M5/M6 rise-time diagnostic: apparent plateau–linear–plateau trend", fontsize=13, fontweight="bold")
    out = FIGURES / "Figure_A16_M5_M6_rise_time_diagnostic.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def write_rise_summary(primary: pd.DataFrame) -> Path:
    """Write segment slopes and endpoint-hit fractions for auditability."""

    extended = pd.read_csv(DERIVED / "low_velocity_extended_window_metrics.csv")
    extended = extended[(extended["included_primary"] == 1) & extended["ray"].isin(["1", "2", "3"])].copy()
    extended["rise_to_tmax_s"] = extended["tmax_s"] - extended["t05_s"]
    rows: list[dict[str, object]] = []
    segments = [("near", 6.0, 35.0), ("middle", 40.0, 120.0), ("far", 120.0, 245.0)]
    for window, frame, start, end in [
        ("common_50_245s", primary, 50.0, 245.0),
        ("extended_50_395s", extended, 50.0, 395.0),
    ]:
        for model in ["M5", "M6"]:
            for ray in ["1", "2", "3"]:
                d = frame[(frame["model"] == model) & (frame["ray"] == ray)].copy()
                if window == "common_50_245s":
                    d["rise_to_tmax_s"] = d["tmax_s"] - d["t05_s"]
                for segment, lo, hi in segments:
                    x = d[(d["distance_km"] >= lo) & (d["distance_km"] < hi)]
                    if len(x) < 5:
                        continue
                    slope = float(np.polyfit(x["distance_km"], x["rise_to_tmax_s"], 1)[0])
                    rows.append(
                        {
                            "window": window,
                            "model": model,
                            "ray": ray,
                            "segment": segment,
                            "n": len(x),
                            "rise_slope_s_per_km": slope,
                            "rise_median_s": float(x["rise_to_tmax_s"].median()),
                            "t05_median_s": float(x["t05_s"].median()),
                            "tmax_median_s": float(x["tmax_s"].median()),
                            "tmax_at_start_pct": float((x["tmax_s"] <= start + 0.05).mean() * 100.0),
                            "tmax_at_end_pct": float((x["tmax_s"] >= end - 0.05).mean() * 100.0),
                        }
                    )
    out = DERIVED / "A16_M5_M6_rise_time_diagnostic_summary.csv"
    pd.DataFrame(rows).to_csv(out, index=False, float_format="%.6g")
    return out


def main() -> None:
    style()
    primary, summary = load()
    DERIVED.mkdir(parents=True, exist_ok=True)
    summary.to_csv(DERIVED / "A16_M1_M6_unified_summary.csv", index=False, float_format="%.8g")
    outputs = [figure_ladder(summary), figure_tmax_distance(primary), figure_rise_time_diagnostic(primary), write_rise_summary(primary)]
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
