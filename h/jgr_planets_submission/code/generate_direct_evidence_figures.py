"""Generate direct-evidence figures added during the final report audit.

The integrated report originally paired three conclusions with figures that
were scientifically related but did not display the claimed quantity itself.
This script creates dedicated, reproducible figures for (1) station-specific
Vx/Vy-to-R/T rotation, (2) the relative diagnostic value of three topographic
path predictors, and (3) the background dependence of the topographic energy
effect.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "jgr_planets_submission"
DERIVED = PROJECT / "data" / "derived"
FIGURES = PROJECT / "figures" / "synthesis"

BLUE = "#1769aa"
ORANGE = "#d17a00"
TEAL = "#087f8c"
GRAY = "#6b7280"
RED = "#b42318"


def configure_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10.5,
            "axes.titlesize": 12.5,
            "axes.labelsize": 10.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.20,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.dpi": 300,
        }
    )


def save(fig: plt.Figure, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / name, bbox_inches="tight", dpi=300)
    plt.close(fig)


def make_rotation_figure() -> None:
    source_x_m, source_y_m = 161_310.0, 207_630.0
    metrics = pd.read_csv(DERIVED / "low_velocity_station_metrics.csv")
    geometry = (
        metrics[["station", "ray", "distance_km", "x_m", "y_m"]]
        .drop_duplicates("station")
        .sort_values("station")
        .copy()
    )
    geometry["east_km"] = (geometry["x_m"] - source_x_m) / 1000.0
    geometry["north_km"] = (geometry["y_m"] - source_y_m) / 1000.0

    fig, (ax, ax_formula) = plt.subplots(
        1, 2, figsize=(10.4, 5.25), gridspec_kw={"width_ratios": [1.38, 1.0]}
    )
    colors = {"S12": GRAY, "1": BLUE, "2": ORANGE, "3": TEAL}
    labels = {"S12": "S12 anchor", "1": "Ray 1", "2": "Ray 2", "3": "Ray 3"}
    for ray, group in geometry.groupby("ray"):
        ray_name = str(ray)
        ax.plot(
            group["east_km"],
            group["north_km"],
            ".",
            ms=6.0 if ray_name == "S12" else 3.0,
            color=colors.get(ray_name, GRAY),
            alpha=0.72,
            label=labels.get(ray_name, ray_name),
        )
    ax.scatter(0, 0, marker="*", s=190, color=RED, edgecolor="white", linewidth=0.8, zorder=5, label="Source")

    representatives: list[dict[str, float | int | str]] = []
    for ray in (1, 2, 3):
        group = geometry[geometry["ray"].astype(str) == str(ray)]
        row = group.iloc[(group["distance_km"] - group["distance_km"].median()).abs().argmin()]
        dx, dy = float(row["east_km"]), float(row["north_km"])
        phi = float(np.arctan2(dx, dy))
        radial = np.array([np.sin(phi), np.cos(phi)])
        transverse = np.array([np.cos(phi), -np.sin(phi)])
        arrow_len = 10.0
        ax.quiver(dx, dy, *(arrow_len * radial), angles="xy", scale_units="xy", scale=1, color=BLUE, width=0.0055, zorder=6)
        ax.quiver(dx, dy, *(arrow_len * transverse), angles="xy", scale_units="xy", scale=1, color=ORANGE, width=0.0055, zorder=6)
        ax.text(dx + arrow_len * radial[0], dy + arrow_len * radial[1], "R", color=BLUE, weight="bold", ha="center", va="center")
        ax.text(dx + arrow_len * transverse[0], dy + arrow_len * transverse[1], "T", color=ORANGE, weight="bold", ha="center", va="center")
        representatives.append(
            {
                "station": row["station"],
                "ray": ray,
                "distance_km": float(row["distance_km"]),
                "azimuth_deg_clockwise_from_north": float(np.degrees(phi) % 360.0),
                "radial_east": float(radial[0]),
                "radial_north": float(radial[1]),
                "transverse_east": float(transverse[0]),
                "transverse_north": float(transverse[1]),
            }
        )

    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xlabel("East offset from source (km)")
    ax.set_ylabel("North offset from source (km)")
    ax.set_title("(a) Receiver profiles and local R/T bases", loc="left", weight="bold", fontsize=11.5)
    ax.legend(loc="best", frameon=False, ncol=2, fontsize=9)

    ax_formula.axis("off")
    ax_formula.set_title("(b) Station-specific rotation", loc="left", weight="bold", fontsize=11.5)
    ax_formula.text(
        0.03,
        0.82,
        r"$\phi_i=\mathrm{atan2}(x_i-x_s,\ y_i-y_s)$",
        transform=ax_formula.transAxes,
        fontsize=14,
        color="#243447",
    )
    ax_formula.text(
        0.03,
        0.61,
        r"$R_i=V_x\sin\phi_i+V_y\cos\phi_i$" + "\n" + r"$T_i=V_x\cos\phi_i-V_y\sin\phi_i$",
        transform=ax_formula.transAxes,
        fontsize=15,
        linespacing=1.8,
        color="#243447",
    )
    ax_formula.text(
        0.03,
        0.35,
        r"$V_x^2+V_y^2=R_i^2+T_i^2$",
        transform=ax_formula.transAxes,
        fontsize=14,
        color=TEAL,
        weight="bold",
    )
    ax_formula.text(
        0.03,
        0.08,
        "The horizontal norm is conserved, but its radial/transverse\npartition changes with station azimuth. Treating Vx/Vy as R/T\ntherefore mixes component energy across the three profiles.",
        transform=ax_formula.transAxes,
        fontsize=10.2,
        linespacing=1.45,
        color="#374151",
    )
    fig.suptitle("A02 | Horizontal components require station-specific rotation", x=0.02, ha="left", fontsize=14, weight="bold", color="#124e78")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, "Figure_A02_rt_rotation_geometry.png")
    pd.DataFrame(representatives).to_csv(DERIVED / "direct_evidence_rt_rotation_examples.csv", index=False)


def make_path_metric_figure() -> None:
    relationships = pd.read_csv(DERIVED / "distance_controlled_relationships.csv")
    contexts = {
        "topography_no_scatter": "Topography effect, no heterogeneity",
        "topography_scatter": "Topography effect, heterogeneous background",
    }
    outcomes = {
        "log_peak_amplitude": "Peak amplitude",
        "log_total_energy": "Total energy",
        "log_duration_90_s": "T90",
    }
    predictors = {
        "path_relief_range_km": ("Cumulative path relief", BLUE, "o"),
        "path_mean_absolute_slope": ("Mean absolute slope", ORANGE, "s"),
        "elevation_km": ("Receiver elevation", GRAY, "^"),
    }
    selected: list[dict[str, object]] = []
    for context, context_label in contexts.items():
        for outcome, outcome_label in outcomes.items():
            full_outcome = f"{context}__{outcome}"
            for predictor, (predictor_label, _, _) in predictors.items():
                row = relationships[(relationships["outcome"] == full_outcome) & (relationships["predictor"] == predictor)]
                if len(row) != 1:
                    raise ValueError(f"Missing path relationship: {full_outcome}, {predictor}")
                r = row.iloc[0]
                selected.append(
                    {
                        "context": context,
                        "context_label": context_label,
                        "outcome": outcome,
                        "outcome_label": outcome_label,
                        "predictor": predictor,
                        "predictor_label": predictor_label,
                        "rho": float(r["rho"]),
                        "q_value": float(r["q_value"]),
                        "block_n": int(r["block_n"]),
                    }
                )
    result = pd.DataFrame(selected)
    result.to_csv(DERIVED / "direct_evidence_path_metric_correlations.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(10.7, 5.35), sharex=True, sharey=True)
    y_base = np.arange(len(outcomes))[::-1]
    offsets = {"path_relief_range_km": 0.20, "path_mean_absolute_slope": 0.0, "elevation_km": -0.20}
    for ax, (context, context_label) in zip(axes, contexts.items()):
        subset = result[result["context"] == context]
        for predictor, (label, color, marker) in predictors.items():
            rows = subset[subset["predictor"] == predictor].set_index("outcome")
            xs = [float(rows.loc[o, "rho"]) for o in outcomes]
            ys = y_base + offsets[predictor]
            ax.plot(xs, ys, linestyle="none", marker=marker, ms=8.0, color=color, label=label)
            for x, y, o in zip(xs, ys, outcomes):
                q = float(rows.loc[o, "q_value"])
                ax.text(x + (0.025 if x >= 0 else -0.025), y, f"{x:+.2f}", ha="left" if x >= 0 else "right", va="center", fontsize=8.3, color=color)
                if q >= 0.05:
                    ax.scatter([x], [y], marker=marker, s=66, facecolor="white", edgecolor=color, linewidth=1.4, zorder=4)
        ax.axvline(0, color="#9ca3af", lw=1)
        ax.set_xlim(-0.86, 0.86)
        ax.set_yticks(y_base, list(outcomes.values()))
        ax.set_xlabel(r"Distance-controlled Spearman $\rho$ (57 spatial blocks)")
        ax.set_title(context_label, loc="left", weight="bold")
    fig.suptitle("A14–A15 | Path-integrated metrics outperform receiver elevation", x=0.02, ha="left", fontsize=14, weight="bold", color="#124e78")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.90), ncol=3, frameon=False, fontsize=9.1)
    fig.text(0.02, 0.01, "Filled symbols: BH-FDR q < 0.05; open symbols: q ≥ 0.05. Signs follow each effect definition.", fontsize=8.7, color="#4b5563")
    fig.tight_layout(rect=(0, 0.04, 1, 0.82))
    save(fig, "Figure_A14_A15_path_metric_diagnostics.png")


def make_topographic_energy_figure() -> None:
    with (DERIVED / "halfspace_analysis_summary.json").open("r", encoding="utf-8") as handle:
        halfspace = json.load(handle)["topography_switch"]
    effects = pd.read_csv(DERIVED / "low_velocity_effect_summary.csv")

    rows = [
        {
            "background": "Half-space high-resolution profile",
            "contrast": "Topography / flat",
            "estimate": float(halfspace["energy_ratio_median"]),
            "lower": float(halfspace["energy_ratio_q25"]),
            "upper": float(halfspace["energy_ratio_q75"]),
            "interval": "station IQR (800 receivers)",
        }
    ]
    for effect_name, background, contrast in (
        ("topography_no_low", "A16 heterogeneous background", "M4 / M3"),
        ("topography_low", "A16 heterogeneous + low velocity", "M6 / M5"),
    ):
        r = effects[(effects["effect"] == effect_name) & (effects["metric"] == "total_energy")]
        if len(r) != 1:
            raise ValueError(f"Missing total-energy effect for {effect_name}")
        row = r.iloc[0]
        rows.append(
            {
                "background": background,
                "contrast": contrast,
                "estimate": float(row["ratio_median"]),
                "lower": float(row["ratio_bootstrap95_low"]),
                "upper": float(row["ratio_bootstrap95_high"]),
                "interval": "95% spatial-block bootstrap CI (57 blocks)",
            }
        )
    result = pd.DataFrame(rows)
    result.to_csv(DERIVED / "direct_evidence_topographic_energy_factors.csv", index=False)

    fig, ax = plt.subplots(figsize=(9.8, 4.9))
    y = np.arange(len(result))[::-1]
    colors = [BLUE, ORANGE, TEAL]
    for yi, (_, row), color in zip(y, result.iterrows(), colors):
        lo, est, hi = float(row["lower"]), float(row["estimate"]), float(row["upper"])
        ax.errorbar(est, yi, xerr=[[est - lo], [hi - est]], fmt="o", ms=9, capsize=5, lw=2.2, color=color, ecolor=color, zorder=3)
        ax.text(hi * 1.09, yi, f"{est:.3f}  [{lo:.3f}, {hi:.3f}]", va="center", ha="left", fontsize=10, color=color, weight="bold")
    ax.axvline(1.0, color="#4b5563", lw=1.2, ls="--")
    ax.text(1.05, 0.95, "no net topographic energy effect", transform=ax.get_xaxis_transform(), fontsize=9, color="#4b5563", va="top")
    ax.set_xscale("log")
    ax.set_xlim(0.005, 5.7)
    ax.set_yticks(y, [f"{r.background}\n({r.contrast})" for r in result.itertuples()])
    ax.set_xlabel("Topographic total-energy factor (log scale)")
    ax.set_title("SYN01 | The topographic energy effect is conditional on background", loc="left", weight="bold", color="#124e78", fontsize=14)
    ax.grid(axis="x", which="both", alpha=0.24)
    ax.grid(axis="y", visible=False)
    ax.text(0.0052, -0.73, "Half-space interval = receiver IQR; A16 intervals = 95% spatial-block bootstrap CIs.\nAbsolute energy contrasts remain conditional on equivalent run/source settings.", fontsize=8.8, color="#4b5563", va="top")
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    save(fig, "Figure_SYN01_topographic_energy_effects.png")


def make_multistage_chain_figure() -> None:
    rows = [
        {
            "stage": "1. Controlled\nhalf-space",
            "scientific_role": "Topographic redistribution,\nR/T conversion, and\nnumerical convergence",
            "transport_test": "r20–r760:\nlinear R preferred\nover simple R²",
            "paper_role": "Mechanism + convergence",
        },
        {
            "stage": "2. A16 M1–M4\nfactorial baseline",
            "scientific_role": "Heterogeneity-driven\nbroadening and conditional\nnonadditivity",
            "transport_test": "12/12 fits prefer linear\nΔAIC = 268–672",
            "paper_role": "Regional factorial test",
        },
        {
            "stage": "3. M5/M6 low-velocity\nextension",
            "scientific_role": "Largest simulated delay\nand retained late energy",
            "transport_test": "6/6 censor-safe fits\nprefer linear\nmin ΔAIC = 12.79",
            "paper_role": "Conditional extension",
        },
        {
            "stage": "4. Apollo A16S12\nexclusion test",
            "scientific_role": "Observed duration remains\noutside the simulated regime",
            "transport_test": "t95 = 2804.6 s observed\nvs 368–382 s for M5/M6",
            "paper_role": "External validation",
        },
    ]
    pd.DataFrame(rows).to_csv(DERIVED / "direct_evidence_multistage_chain.csv", index=False)

    fig, ax = plt.subplots(figsize=(11.0, 5.35))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    xs = [0.13, 0.38, 0.63, 0.88]
    colors = [BLUE, ORANGE, TEAL, RED]
    for i, (x, row, color) in enumerate(zip(xs, rows, colors)):
        if i < len(xs) - 1:
            ax.annotate("", xy=(xs[i + 1] - 0.105, 0.565), xytext=(x + 0.105, 0.565), arrowprops={"arrowstyle": "-|>", "lw": 2.1, "color": "#64748b"})
        box = mpl.patches.FancyBboxPatch(
            (x - 0.105, 0.29),
            0.21,
            0.55,
            boxstyle="round,pad=0.014,rounding_size=0.02",
            facecolor=mpl.colors.to_rgba(color, 0.08),
            edgecolor=color,
            linewidth=2.0,
        )
        ax.add_patch(box)
        ax.text(x, 0.80, row["stage"], ha="center", va="top", fontsize=10.2, weight="bold", color=color, linespacing=1.08)
        ax.text(x, 0.645, row["scientific_role"], ha="center", va="center", fontsize=8.4, color="#1f2937", linespacing=1.25)
        ax.plot([x - 0.083, x + 0.083], [0.535, 0.535], color=mpl.colors.to_rgba(color, 0.45), lw=1.0)
        ax.text(x, 0.455, row["transport_test"], ha="center", va="center", fontsize=8.1, color="#334155", linespacing=1.2)
        ax.text(x, 0.325, row["paper_role"], ha="center", va="bottom", fontsize=8.3, weight="bold", color=color)
    ax.text(0.50, 0.205, "Mechanism hierarchy", ha="center", va="center", fontsize=11.5, weight="bold", color="#124e78")
    ax.text(
        0.50,
        0.125,
        "topographic redistribution  →  heterogeneity-driven broadening  →  low-velocity retention  →  Apollo exclusion",
        ha="center",
        va="center",
        fontsize=9.8,
        color="#334155",
    )
    ax.text(
        0.50,
        0.045,
        "Across all modeled stages, the main-energy ridge remains closer to linear distance than to a simple R² strong-diffusion scaling.",
        ha="center",
        va="center",
        fontsize=8.9,
        color="#4b5563",
    )
    fig.suptitle("SYN08/SYN13/SYN15 | Multistage evidence chain and manuscript logic", x=0.02, ha="left", fontsize=14, weight="bold", color="#124e78")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, "Figure_SYN08_SYN13_SYN15_evidence_chain.png")


def main() -> None:
    configure_style()
    make_rotation_figure()
    make_path_metric_figure()
    make_topographic_energy_figure()
    make_multistage_chain_figure()
    print("Created 4 direct-evidence figures and their derived tables.")


if __name__ == "__main__":
    main()
