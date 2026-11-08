"""Create a near-side LOLA relief map with all candidate-region windows."""
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
from matplotlib.patches import Rectangle, Patch
from matplotlib.lines import Line2D


def main(project_root="."):
    root = Path(project_root)
    cfg = json.loads((root / "config/candidate_region_map.json").read_text(encoding="utf-8"))
    dem = np.memmap(root / "data/raw/dem/ldem_64_float.img", dtype="<f4", mode="r", shape=(11520, 23040))
    lon = np.linspace(-180 + 0.0078125, 180 - 0.0078125, 23040)
    lat = np.linspace(90 - 0.0078125, -90 + 0.0078125, 11520)
    extent = cfg["map_extent"]
    xmask = (lon >= extent[0] - 1) & (lon <= extent[1] + 1)
    ymask = (lat >= extent[2] - 1) & (lat <= extent[3] + 1)
    z = dem[np.ix_(ymask, xmask)][::2, ::2] * 1000
    xx, yy = lon[xmask][::2], lat[ymask][::2]
    light = LightSource(azdeg=315, altdeg=42)
    shade = light.hillshade(z, vert_exag=1.5, dx=1, dy=1)

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(13, 9), constrained_layout=True)
    im = ax.imshow(z, extent=[xx.min(), xx.max(), yy.min(), yy.max()], origin="upper", cmap="terrain", aspect="auto")
    ax.imshow(shade, extent=[xx.min(), xx.max(), yy.min(), yy.max()], origin="upper", cmap="gray", alpha=.25, aspect="auto")

    colors = {"A12_mare": "#1f77b4", "A14_fra_mauro": "#d95f02", "A15_hadley_apennine": "#2ca02c", "A16_descartes_cayley": "#9467bd"}
    for name, region in cfg["regions"].items():
        x0, x1, y0, y1 = region["bounds"]
        color = colors[name]
        ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, fill=False, lw=2.5, ec=color, zorder=5))
        slon, slat = region["station"]
        ax.scatter(slon, slat, marker="*", s=150, c=color, ec="black", lw=.7, zorder=7)
        ax.text(x0 + .5, y1 - 1.2, region["label"], color=color, fontsize=10, weight="bold", va="top", zorder=8,
                bbox=dict(facecolor="white", alpha=.75, edgecolor="none", pad=2))

    feature_styles = {
        "mare": ("#1f77b4", "o"), "ejecta": ("#d95f02", "D"),
        "highland": ("#9467bd", "^"), "basin_margin": ("#e377c2", "s"), "crater_highland": ("#8c564b", "P")
    }
    for feature in cfg["features"]:
        color, marker = feature_styles[feature["kind"]]
        ax.scatter(feature["lon"], feature["lat"], s=60, c=color, marker=marker, ec="white", lw=.5, zorder=9)
        ax.annotate(feature["label"], (feature["lon"], feature["lat"]), xytext=(5, 5), textcoords="offset points", fontsize=8,
                    color="black", bbox=dict(facecolor="white", alpha=.65, edgecolor="none", pad=1.5), zorder=10)

    region_handles = [Patch(facecolor="none", edgecolor=colors[n], lw=2, label=r["label"]) for n, r in cfg["regions"].items()]
    feature_handles = [Line2D([0], [0], marker=v[1], color="w", markerfacecolor=v[0], markeredgecolor="white", markersize=8, label=k)
                       for k, v in {"月海": feature_styles["mare"], "喷出物/破碎带": feature_styles["ejecta"], "高地": feature_styles["highland"], "盆地边缘": feature_styles["basin_margin"], "陨石坑高地": feature_styles["crater_highland"]}.items()]
    ax.legend(handles=region_handles + feature_handles, loc="lower left", fontsize=8, framealpha=.9, ncol=2)
    ax.set(xlim=extent[:2], ylim=extent[2:], xlabel="Longitude (°E)", ylabel="Latitude (°)")
    ax.set_title("Apollo 候选区域地形起伏总图\nLOLA LDEM_64（约 0.47 km 网格；彩框为区域初筛窗口）", fontsize=15)
    ax.grid(alpha=.2)
    cb = fig.colorbar(im, ax=ax, shrink=.75, pad=.02)
    cb.set_label("相对 1737.4 km 参考半径的高度（m）")
    fig.savefig(root / "figures/candidate_regions_terrain_overview.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
