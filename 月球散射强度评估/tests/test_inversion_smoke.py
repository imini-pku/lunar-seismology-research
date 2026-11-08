"""Small synthetic twin for the first-pass proxy inversion."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


def test_synthetic_twin(tmp_path: Path) -> None:
    source = tmp_path / "metrics.csv"
    rows = []
    # Two regions with known negative log-energy coefficients -0.02 and -0.05.
    for event_index in range(6):
        for station_index in range(3):
            # Vary both path segments across events and stations so the design
            # matrix tests a genuinely identifiable case.
            basin = 3.0 + station_index + 0.31 * event_index + 0.11 * event_index * station_index
            crater = 2.0 + event_index * 0.2 + 0.17 * station_index + 0.07 * (event_index % 2) * station_index
            nuisance = 0.1 * event_index + 0.03 * station_index
            response = nuisance - 0.02 * basin - 0.05 * crater
            rows.append({
                "event_id": f"e{event_index}", "station_id": f"s{station_index}", "region_id": "mixed",
                "frequency_hz": "0.5", "window_start_s": "245", "window_end_s": "1000",
                "distance_km": str(10 + event_index + 2 * station_index + 0.5 * event_index * station_index),
                "log_energy_obs": str(response), "log_energy_ref": "0", "sigma_log_energy": "0.1",
                "path_km__basin_plain": str(basin), "path_km__crater_floor": str(crater),
            })
    with source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    output = tmp_path / "out"
    script = Path(__file__).parents[1] / "code" / "invert_regional_scattering.py"
    subprocess.run([sys.executable, str(script), "--input", str(source), "--output", str(output), "--bootstrap", "20"], check=True)
    result = (output / "regional_scattering_proxy.csv").read_text(encoding="utf-8")
    assert "basin_plain" in result
    assert "crater_floor" in result
