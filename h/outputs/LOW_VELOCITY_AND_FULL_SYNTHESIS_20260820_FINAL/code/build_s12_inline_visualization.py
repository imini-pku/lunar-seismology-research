"""Create the thread-local inline visualization for the S12 comparison PNG."""

from __future__ import annotations

import base64
from pathlib import Path


SCRIPT = Path(__file__).resolve()
SUBMISSION_ROOT = SCRIPT.parents[1]
FIGURE_DIR = SUBMISSION_ROOT / "figures" / "low_velocity"
VIS_DIR = Path(
    r"C:\Users\Administrator\.codex\visualizations\2026\08\14\019fff28-00c3-7a03-81d2-ccaa3cc41926"
)
VISUALS = (
    (
        "Figure_S12_M1_M6_observed_three_component.png",
        "s12-m1-m6-observed-three-component.html",
        "s12-m1-m6-observed-three-component",
        "M1-M6 and Apollo S12 observed Z R T three-component waveforms from 0 to 400 seconds",
    ),
    (
        "Figure_S12_M1_M6_observed_envelope_comparison.png",
        "s12-m1-m6-observed-envelope.html",
        "s12-m1-m6-observed-envelope",
        "M1-M6 and Apollo S12 20 second smoothed three-component envelope comparison",
    ),
    (
        "Figure_S12_M1_M6_observed_energy_comparison.png",
        "s12-m1-m6-observed-energy.html",
        "s12-m1-m6-observed-energy",
        "M1-M6 and Apollo S12 cumulative three-component energy comparison",
    ),
    (
        "Figure_S12_M1_M6_observed_component_envelopes.png",
        "s12-m1-m6-observed-component-envelopes.html",
        "s12-m1-m6-observed-component-envelopes",
        "Separate Z R T analytic-amplitude envelopes for M1-M6 and Apollo S12",
    ),
    (
        "Figure_S12_M1_M6_observed_component_envelope_correlations.png",
        "s12-m1-m6-observed-component-envelope-correlations.html",
        "s12-m1-m6-observed-component-envelope-correlations",
        "Z R T envelope correlation coefficients for M1-M6 against Apollo S12",
    ),
)


def main() -> None:
    VIS_DIR.mkdir(parents=True, exist_ok=True)
    for figure_name, html_name, root_id, alt_text in VISUALS:
        png = FIGURE_DIR / figure_name
        if not png.is_file():
            raise FileNotFoundError(png)
        encoded = base64.b64encode(png.read_bytes()).decode("ascii")
        fragment = (
            f'<div id="{root_id}">\n'
            f'<img src="data:image/png;base64,{encoded}" alt="{alt_text}">\n'
            "</div>\n"
        )
        output = VIS_DIR / html_name
        output.write_text(fragment, encoding="utf-8")
        print(output)
        print(f"bytes={output.stat().st_size}")


if __name__ == "__main__":
    main()
