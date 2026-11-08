"""Preliminary Apollo event, trace-flag, and station-window coverage audit."""
from pathlib import Path
import json
import re
from datetime import datetime

import numpy as np
import pandas as pd


STATIONS = {
    "A12": (-3.0128, -23.4216),
    "A14": (-3.6450, -17.4719),
    "A15": (26.1320, -3.6330),
    "A16": (-8.9734, 15.5010),
}


def angular_distance(lat, lon, lat0, lon0):
    p1, p2 = np.radians(lat), np.radians(lat0)
    dp, dl = np.radians(lat0 - lat), np.radians(lon0 - lon)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return np.degrees(2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))


def assign_region(lat, lon):
    distances = {
        station: angular_distance(lat, lon, *coords)
        for station, coords in STATIONS.items()
    }
    station = min(distances, key=distances.get)
    return (station, float(distances[station])) if distances[station] <= 15 else ("outside", float(distances[station]))


def event_class(comment):
    text = str(comment).upper()
    if "S-IVB" in text or "LM IMP" in text or "ARTIFICIAL" in text:
        return "AI"
    if re.search(r"\bDM\b|DEEP", text):
        return "DMQ"
    if re.search(r"\bSM\b|SHALLOW", text):
        return "SMQ"
    if "IMPACT" in text or re.search(r"\bNI\b|NATURAL", text):
        return "NI"
    return "other"


def load_located_events(raw):
    rows = []
    dm = pd.read_csv(raw / "nakamura_2005_dm_locations.csv")
    for _, row in dm.dropna(subset=["Lat", "Long"]).iterrows():
        region, distance = assign_region(row.Lat, row.Long)
        rows.append(("DMQ", row.Lat, row.Long, region, distance))
    sm = pd.read_csv(raw / "nakamura_1979_sm_locations.csv")
    for _, row in sm.dropna(subset=["Lat", "Long"]).iterrows():
        region, distance = assign_region(row.Lat, row.Long)
        rows.append(("SMQ", row.Lat, row.Long, region, distance))
    ai = pd.read_csv(raw / "nakamura_1983_ai_locations.csv")
    for _, row in ai.iterrows():
        region, distance = assign_region(row.Lat, row.Long)
        rows.append(("AI", row.Lat, row.Long, region, distance))
    impacts = pd.read_csv(raw / "gagnepian_2006_catalog.csv")
    for _, row in impacts.dropna(subset=["Lat", "Long"]).iterrows():
        kind = str(row.Type).strip()
        event_type = "NI" if kind == "M" else "AI" if ("LM" in kind or "S-IVB" in kind) else "other"
        region, distance = assign_region(row.Lat, row.Long)
        rows.append((event_type, row.Lat, row.Long, region, distance))
    events = pd.DataFrame(rows, columns=["event_type", "lat", "lon", "region", "distance_deg"])
    # Approximate deduplication across historical catalogs.
    events["lat_bin"] = events.lat.round(1)
    events["lon_bin"] = events.lon.round(1)
    return events.drop_duplicates(["event_type", "lat_bin", "lon_bin"]).drop(columns=["lat_bin", "lon_bin"])


def main(project_root="."):
    root = Path(project_root)
    raw = root / "data/raw/apollo_event_catalog"
    results = root / "results"
    results.mkdir(exist_ok=True)
    located = load_located_events(raw)
    located.to_csv(results / "apollo_located_events_deduplicated.csv", index=False)

    levent = pd.read_csv(raw / "levent.1008weber.csv", dtype=str, keep_default_na=False)
    summary = []
    for station in STATIONS:
        columns = [c for c in levent.columns if c.startswith(station[1:])]
        has_trace = levent[columns].apply(lambda row: any(str(value).strip() for value in row), axis=1)
        has_lp = levent[[c for c in columns if "LP" in c]].apply(lambda row: any(str(value).strip() for value in row), axis=1)
        has_sp = levent[[c for c in columns if "SP" in c]].apply(lambda row: any(str(value).strip() for value in row), axis=1)
        region_events = located[located.region == station]
        summary.append({
            "region": station,
            "station": station,
            "located_events": int(len(region_events)),
            "located_DMQ": int((region_events.event_type == "DMQ").sum()),
            "located_SMQ": int((region_events.event_type == "SMQ").sum()),
            "located_AI": int((region_events.event_type == "AI").sum()),
            "located_NI": int((region_events.event_type == "NI").sum()),
            "distance_min_deg": round(float(region_events.distance_deg.min()), 2) if len(region_events) else None,
            "distance_median_deg": round(float(region_events.distance_deg.median()), 2) if len(region_events) else None,
            "distance_max_deg": round(float(region_events.distance_deg.max()), 2) if len(region_events) else None,
            "waveform_event_rows": int(has_trace.sum()),
            "waveform_LP_rows": int(has_lp.sum()),
            "waveform_SP_rows": int(has_sp.sum()),
        })
    pd.DataFrame(summary).to_csv(results / "regional_coverage_audit.csv", index=False)
    metadata = {
        "created_utc": datetime.utcnow().isoformat() + "Z",
        "region_definition": "nearest Apollo 12/14/15/16 station within 15 degrees",
        "waveform_source": "levent.1008weber.csv trace availability columns",
        "frequency_bands": {"LP": "0.1-3 Hz", "SP": "1-10 Hz"},
        "caveat": "preliminary station-window audit; not a final geology-polygon or waveform-QC result",
    }
    (results / "regional_coverage_audit_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
