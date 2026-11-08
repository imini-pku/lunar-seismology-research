"""Plot preliminary LOLA relief windows and located Apollo events."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource

STATIONS = {"A12": (-3.0128, -23.4216), "A14": (-3.6450, -17.4719), "A15": (26.1320, -3.6330), "A16": (-8.9734, 15.5010)}


def main(project_root="."):
    root = Path(project_root)
    dem = np.memmap(root / "data/raw/dem/ldem_64_float.img", dtype="<f4", mode="r", shape=(11520, 23040))
    lon = np.linspace(-180 + 0.0078125, 180 - 0.0078125, 23040)
    lat = np.linspace(90 - 0.0078125, -90 + 0.0078125, 11520)
    events = pd.read_csv(root / "results/apollo_located_events_deduplicated.csv")
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    light = LightSource(azdeg=315, altdeg=45)
    stats = []
    for ax, (station, (slat, slon)) in zip(axes.flat, STATIONS.items()):
        lon_mask, lat_mask = (lon >= slon - 15) & (lon <= slon + 15), (lat >= slat - 15) & (lat <= slat + 15)
        z = dem[np.ix_(lat_mask, lon_mask)][::2, ::2] * 1000
        xx, yy = lon[lon_mask][::2], lat[lat_mask][::2]
        shade = light.hillshade(z, vert_exag=1.8, dx=1, dy=1)
        ax.imshow(z, extent=[xx.min(), xx.max(), yy.min(), yy.max()], origin="upper", cmap="terrain", aspect="auto")
        ax.imshow(shade, extent=[xx.min(), xx.max(), yy.min(), yy.max()], origin="upper", cmap="gray", alpha=.25, aspect="auto")
        for kind, color, marker in [("DMQ", "#1f77b4", "o"), ("SMQ", "#d62728", "s"), ("AI", "#9467bd", "^"), ("NI", "#2ca02c", "x")]:
            subset = events[(events.region == station) & (events.event_type == kind)]
            if len(subset): ax.scatter(subset.lon, subset.lat, s=35, c=color, marker=marker, label=kind, zorder=5)
        ax.scatter([slon], [slat], s=90, c="black", marker="*", label="station", zorder=6)
        ax.set(title=f"{station} candidate window", xlabel="Longitude (°E)", ylabel="Latitude (°)")
        ax.grid(alpha=.2)
        stats.append({"region": station, "elevation_min_m": float(np.nanmin(z)), "elevation_max_m": float(np.nanmax(z)), "local_relief_m": float(np.nanmax(z) - np.nanmin(z))})
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5)
    fig.suptitle("Apollo candidate-region terrain relief and located-event coverage\nLOLA LDEM_64 (about 0.47 km grid; preliminary audit windows)")
    fig.savefig(root / "figures/regional_candidate_terrain_relief.png", dpi=220, bbox_inches="tight")
    (root / "results/regional_terrain_summary.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
