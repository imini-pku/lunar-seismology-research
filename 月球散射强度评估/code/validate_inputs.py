"""Validate the regional-scattering input table without changing any data.

The validator is intentionally conservative: missing references, incomplete path
columns, non-positive distances, duplicated event/station/window rows, and failed
quality flags are reported for review instead of being silently repaired.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

REQUIRED = {
    "event_id",
    "station_id",
    "region_id",
    "frequency_hz",
    "window_start_s",
    "window_end_s",
    "distance_km",
    "log_energy_obs",
    "log_energy_ref",
    "sigma_log_energy",
}


def as_float(value: str, field: str, row_number: int, errors: list[str]) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"row {row_number}: {field} is not numeric: {value!r}")
        return None
    if number != number or number in (float("inf"), float("-inf")):
        errors.append(f"row {row_number}: {field} is not finite")
        return None
    return number


def validate(path: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "input": str(path),
        "status": "pass",
        "rows": 0,
        "events": 0,
        "stations": 0,
        "frequencies": [],
        "regions": [],
        "path_columns": [],
        "errors": [],
        "warnings": [],
    }
    if not path.exists():
        report["status"] = "missing"
        report["errors"].append(f"input file does not exist: {path}")
        return report

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = sorted(REQUIRED - fields)
        report["path_columns"] = sorted(name for name in fields if name.startswith("path_km__"))
        if missing:
            report["errors"].append(f"missing required columns: {', '.join(missing)}")
            report["status"] = "fail"
        if not report["path_columns"]:
            report["errors"].append("no path_km__<region_id> columns found")
            report["status"] = "fail"

        seen: set[tuple[str, str, str, str, str]] = set()
        events: set[str] = set()
        stations: set[str] = set()
        frequencies: set[float] = set()
        regions: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            report["rows"] += 1
            event = (row.get("event_id") or "").strip()
            station = (row.get("station_id") or "").strip()
            region = (row.get("region_id") or "").strip()
            freq = (row.get("frequency_hz") or "").strip()
            start = (row.get("window_start_s") or "").strip()
            end = (row.get("window_end_s") or "").strip()
            key = (event, station, freq, start, end)
            if key in seen:
                report["warnings"].append(f"row {row_number}: duplicated event/station/frequency/window key")
            seen.add(key)
            events.add(event)
            stations.add(station)
            if region:
                regions.add(region)

            freq_value = as_float(freq, "frequency_hz", row_number, report["errors"])
            start_value = as_float(start, "window_start_s", row_number, report["errors"])
            end_value = as_float(end, "window_end_s", row_number, report["errors"])
            distance = as_float(row.get("distance_km", ""), "distance_km", row_number, report["errors"])
            sigma = as_float(row.get("sigma_log_energy", ""), "sigma_log_energy", row_number, report["errors"])
            as_float(row.get("log_energy_obs", ""), "log_energy_obs", row_number, report["errors"])
            as_float(row.get("log_energy_ref", ""), "log_energy_ref", row_number, report["errors"])
            if freq_value is not None:
                frequencies.add(freq_value)
                if freq_value <= 0:
                    report["errors"].append(f"row {row_number}: frequency_hz must be positive")
            if start_value is not None and end_value is not None and end_value <= start_value:
                report["errors"].append(f"row {row_number}: window_end_s must exceed window_start_s")
            if distance is not None and distance <= 0:
                report["errors"].append(f"row {row_number}: distance_km must be positive")
            if sigma is not None and sigma <= 0:
                report["errors"].append(f"row {row_number}: sigma_log_energy must be positive")
            for column in report["path_columns"]:
                value = as_float(row.get(column, ""), column, row_number, report["errors"])
                if value is not None and value < 0:
                    report["errors"].append(f"row {row_number}: {column} cannot be negative")
            if "path_length_total_km" in fields:
                total = as_float(row.get("path_length_total_km", ""), "path_length_total_km", row_number, report["errors"])
                if total is not None:
                    segment_values = []
                    for column in report["path_columns"]:
                        value = row.get(column, "")
                        if value not in {"", "NA", "nan"}:
                            try:
                                segment_values.append(float(value))
                            except ValueError:
                                pass
                    segment_total = sum(segment_values)
                    if total <= 0:
                        report["errors"].append(f"row {row_number}: path_length_total_km must be positive")
                    elif abs(segment_total - total) > max(0.01, 1e-3 * total):
                        report["warnings"].append(f"row {row_number}: path segments do not close to path_length_total_km")
            if "path_coverage_fraction" in fields:
                coverage = as_float(row.get("path_coverage_fraction", ""), "path_coverage_fraction", row_number, report["errors"])
                if coverage is not None and not 0 <= coverage <= 1:
                    report["errors"].append(f"row {row_number}: path_coverage_fraction must be between 0 and 1")
            if "segment_count" in fields:
                segment_count = as_float(row.get("segment_count", ""), "segment_count", row_number, report["errors"])
                if segment_count is not None and (segment_count < 1 or segment_count != int(segment_count)):
                    report["errors"].append(f"row {row_number}: segment_count must be a positive integer")
            if (row.get("quality_flag") or "pass").lower() in {"exclude", "fail"}:
                report["warnings"].append(f"row {row_number}: quality_flag excludes this row")

    report["events"] = len(events - {""})
    report["stations"] = len(stations - {""})
    report["frequencies"] = sorted(frequencies)
    report["regions"] = sorted(regions)
    if report["errors"]:
        report["status"] = "fail"
    elif report["warnings"]:
        report["status"] = "review"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/metrics_long.csv"))
    parser.add_argument("--report", type=Path, help="optional JSON report path")
    args = parser.parse_args()
    report = validate(args.input)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] in {"pass", "review"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
