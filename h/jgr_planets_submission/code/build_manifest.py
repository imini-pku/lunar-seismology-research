"""Write SHA-256 and size manifests for the reproducibility package."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "provenance" / "input_manifest_sha256.csv"


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> None:
    targets = []
    for folder in (ROOT / "data" / "raw", ROOT / "data" / "derived"):
        targets.extend(path for path in folder.rglob("*") if path.is_file())
    targets.extend(
        path
        for path in (ROOT / "provenance").iterdir()
        if path.is_file() and path.suffix.lower() in {".sh", ".m"}
    )
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("relative_path", "bytes", "sha256"))
        for path in sorted(targets):
            writer.writerow((path.relative_to(ROOT).as_posix(), path.stat().st_size, digest(path)))
    print(f"Wrote {len(targets)} checksums to {OUTPUT}")


if __name__ == "__main__":
    main()
