"""Import and validate the 216-station concentric-ring half-space geometry.

The source text is archived verbatim in data/raw. This script creates a derived
CSV with distance and azimuth relative to the verified (50,000, 50,000) m center.
It rejects any geometry other than 9 radii x 24 azimuths = 216 stations.
"""
from __future__ import annotations

import csv
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "raw" / "halfspace_216_ring_receivers.station"
OUTPUT = ROOT / "data" / "derived" / "halfspace_216_ring_receiver_geometry.csv"
CENTER_X_M = 50_000.0
CENTER_Y_M = 50_000.0


def main() -> None:
    rows = []
    for line in SOURCE.read_text(encoding="utf-8-sig").splitlines():
        fields = line.split()
        if len(fields) < 6 or not fields[0].startswith("r"):
            continue
        name, physical, depth3d, x, y, z = fields[:6]
        x_m, y_m, z_m = float(x), float(y), float(z)
        dx, dy = x_m - CENTER_X_M, y_m - CENTER_Y_M
        rows.append({
            "station_name": name,
            "is_physical_coord": int(physical),
            "is_3dim_depth": int(depth3d),
            "x_m": f"{x_m:.12g}",
            "y_m": f"{y_m:.12g}",
            "z_m": f"{z_m:.12g}",
            "distance_km": f"{math.hypot(dx, dy) / 1000:.6f}",
            "azimuth_deg_from_positive_x": f"{math.degrees(math.atan2(dy, dx)) % 360:.6f}",
        })

    if len(rows) != 216:
        raise ValueError(f"Expected 216 stations, found {len(rows)}")
    radii = sorted({round(float(row["distance_km"]), 6) for row in rows})
    azimuths = sorted({round(float(row["azimuth_deg_from_positive_x"]), 6) for row in rows})
    if radii != [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0]:
        raise ValueError(f"Unexpected radii: {radii}")
    if len(azimuths) != 24 or any(abs(a - 15.0 * i) > 1e-6 for i, a in enumerate(azimuths)):
        raise ValueError(f"Expected 24 azimuths at 15-degree spacing, found {azimuths}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Validated 216 stations: 9 radii x 24 azimuths")
    print(OUTPUT)


if __name__ == "__main__":
    main()
