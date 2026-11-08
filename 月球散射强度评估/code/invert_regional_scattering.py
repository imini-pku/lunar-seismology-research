"""First-pass robust regional scattering-proxy inversion.

The response is ``log_energy_obs - log_energy_ref``.  For each frequency and
time window the script fits event and station intercepts, log-distance, and
path-length coefficients.  A negative path coefficient implies an attenuation
proxy ``g_proxy_km-1 = -beta``.  This is deliberately a proxy until synthetic
calibration maps it to a physical scattering coefficient or mean free path.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable

import numpy as np


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def finite(value: str) -> float:
    number = float(value)
    if not np.isfinite(number):
        raise ValueError("non-finite value")
    return number


def design_matrix(rows: list[dict[str, str]], path_columns: list[str]) -> tuple[np.ndarray, list[str], np.ndarray, np.ndarray]:
    events = sorted({row["event_id"] for row in rows})
    stations = sorted({row["station_id"] for row in rows})
    columns = ["intercept", "log_distance"] + path_columns
    columns += [f"event::{event}" for event in events[1:]]
    columns += [f"station::{station}" for station in stations[1:]]
    matrix = np.zeros((len(rows), len(columns)), dtype=float)
    matrix[:, 0] = 1.0
    matrix[:, 1] = [np.log(finite(row["distance_km"])) for row in rows]
    for index, name in enumerate(path_columns, start=2):
        matrix[:, index] = [finite(row[name]) for row in rows]
    offset = 2 + len(path_columns)
    for index, event in enumerate(events[1:], start=offset):
        matrix[:, index] = [float(row["event_id"] == event) for row in rows]
    offset += len(events) - 1
    for index, station in enumerate(stations[1:], start=offset):
        matrix[:, index] = [float(row["station_id"] == station) for row in rows]
    response = np.array([finite(row["log_energy_obs"]) - finite(row["log_energy_ref"]) for row in rows])
    sigma = np.array([finite(row["sigma_log_energy"]) for row in rows])
    return matrix, columns, response, sigma


def weighted_lstsq(matrix: np.ndarray, response: np.ndarray, sigma: np.ndarray, weights: np.ndarray | None = None) -> np.ndarray:
    row_weights = 1.0 / np.square(sigma)
    if weights is not None:
        row_weights *= weights
    scale = np.sqrt(row_weights)
    return np.linalg.lstsq(matrix * scale[:, None], response * scale, rcond=None)[0]


def robust_fit(matrix: np.ndarray, response: np.ndarray, sigma: np.ndarray, iterations: int = 20) -> tuple[np.ndarray, np.ndarray]:
    weights = np.ones(len(response), dtype=float)
    beta = weighted_lstsq(matrix, response, sigma)
    for _ in range(iterations):
        residual = response - matrix @ beta
        mad = np.median(np.abs(residual - np.median(residual)))
        scale = max(1.4826 * mad, 1e-8)
        huber = np.minimum(1.0, 1.345 * scale / np.maximum(np.abs(residual), 1e-12))
        new_beta = weighted_lstsq(matrix, response, sigma, huber)
        if np.max(np.abs(new_beta - beta)) < 1e-9:
            beta = new_beta
            break
        beta = new_beta
        weights = huber
    return beta, response - matrix @ beta


def bootstrap_coefficients(
    rows: list[dict[str, str]], matrix: np.ndarray, response: np.ndarray, sigma: np.ndarray,
    reps: int, seed: int,
) -> np.ndarray:
    events = np.array([row["event_id"] for row in rows])
    unique_events = np.unique(events)
    if reps <= 0 or len(unique_events) < 2:
        return np.empty((0, matrix.shape[1]))
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(reps):
        sampled = rng.choice(unique_events, size=len(unique_events), replace=True)
        indices = np.concatenate([np.flatnonzero(events == event) for event in sampled])
        try:
            if np.linalg.matrix_rank(matrix[indices]) < matrix.shape[1]:
                continue
            draws.append(robust_fit(matrix[indices], response[indices], sigma[indices], iterations=10)[0])
        except np.linalg.LinAlgError:
            continue
    return np.asarray(draws)


def fit_stratum(rows: list[dict[str, str]], path_columns: list[str], bootstrap: int, seed: int) -> tuple[list[dict[str, object]], dict[str, object]]:
    matrix, names, response, sigma = design_matrix(rows, path_columns)
    rank = int(np.linalg.matrix_rank(matrix))
    condition = float(np.linalg.cond(matrix)) if rank == matrix.shape[1] else float("inf")
    diagnostic = {
        "n_rows": len(rows),
        "n_events": len({row["event_id"] for row in rows}),
        "n_stations": len({row["station_id"] for row in rows}),
        "design_columns": names,
        "rank": rank,
        "n_columns": matrix.shape[1],
        "condition_number": condition,
        "status": "pass" if rank == matrix.shape[1] and condition < 1e8 else "review",
    }
    if diagnostic["status"] != "pass":
        return [], diagnostic
    beta, residual = robust_fit(matrix, response, sigma)
    draws = bootstrap_coefficients(rows, matrix, response, sigma, bootstrap, seed)
    output: list[dict[str, object]] = []
    for name in path_columns:
        index = names.index(name)
        coefficient = float(beta[index])
        record: dict[str, object] = {
            "region_id": name.removeprefix("path_km__"),
            "beta_log_per_km": coefficient,
            "g_proxy_km-1": -coefficient,
            "n_rows": len(rows),
            "n_events": diagnostic["n_events"],
            "n_stations": diagnostic["n_stations"],
            "condition_number": condition,
        }
        if len(draws):
            record["g_proxy_ci95_low"] = float(np.quantile(-draws[:, index], 0.025))
            record["g_proxy_ci95_high"] = float(np.quantile(-draws[:, index], 0.975))
        else:
            record["g_proxy_ci95_low"] = None
            record["g_proxy_ci95_high"] = None
        output.append(record)
    diagnostic["residual_rms"] = float(np.sqrt(np.mean(np.square(residual))))
    diagnostic["bootstrap_success"] = int(len(draws))
    if bootstrap > 0 and len(draws) < max(20, bootstrap // 5):
        diagnostic["status"] = "review"
        diagnostic["bootstrap_warning"] = "too few full-rank event bootstrap replicates for a stable interval"
    return output, diagnostic


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20261016)
    args = parser.parse_args()
    rows = read_rows(args.input)
    rows = [row for row in rows if (row.get("quality_flag") or "pass").lower() not in {"exclude", "fail"}]
    required = {"event_id", "station_id", "frequency_hz", "window_start_s", "window_end_s", "distance_km", "log_energy_obs", "log_energy_ref", "sigma_log_energy"}
    missing = required - set(rows[0] if rows else {})
    if missing:
        raise SystemExit(f"missing required columns: {', '.join(sorted(missing))}")
    path_columns = sorted(name for name in rows[0] if name.startswith("path_km__"))
    if not path_columns:
        raise SystemExit("no path_km__<region_id> columns found")
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (row["frequency_hz"], row["window_start_s"], row["window_end_s"])
        groups.setdefault(key, []).append(row)

    records: list[dict[str, object]] = []
    diagnostics: dict[str, object] = {}
    for group_index, (key, group_rows) in enumerate(sorted(groups.items())):
        output, diagnostic = fit_stratum(group_rows, path_columns, args.bootstrap, args.seed + group_index)
        frequency, start, end = key
        group_name = f"f={frequency};t={start}-{end}"
        diagnostics[group_name] = diagnostic
        for record in output:
            record.update({"frequency_hz": float(frequency), "window_start_s": float(start), "window_end_s": float(end)})
            records.append(record)

    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "regional_scattering_proxy.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = ["region_id", "frequency_hz", "window_start_s", "window_end_s", "beta_log_per_km", "g_proxy_km-1", "g_proxy_ci95_low", "g_proxy_ci95_high", "n_rows", "n_events", "n_stations", "condition_number"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    (args.output / "fit_diagnostics.json").write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output / "run_manifest.json").write_text(json.dumps({"input": str(args.input), "bootstrap": args.bootstrap, "seed": args.seed, "interpretation": "proxy_only_until_synthetic_calibration"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} regional proxy estimates to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
