# JGR: Planets submission package

This directory is a clean, evidence-traceable revision of the original manuscript on lunar surface-topography effects. The scientific narrative is organized around a verified 2 x 2 numerical experiment:

| Model | Surface | Shallow heterogeneity |
|---|---|---|
| M1 | Flat | Absent |
| M2 | Flat | Present |
| M3 | Realistic topography | Absent |
| M4 | Realistic topography | Present |

The principal conclusion is deliberately bounded: topography and shallow heterogeneity broaden early lunar seismic waveforms and redistribute component energy, but the 250 s synthetics do not reproduce the approximately 3,000 s Apollo coda.

## Directory guide

- `manuscript/`: editable English source, final Word manuscript, and submission PDF.
- `supporting_information/`: methods, sensitivity results, and extended tables/figures.
- `figures/`: main-text and supporting figures in PNG and PDF formats.
- `data/derived/`: exact CSV tables supporting reported numerical values.
- `data/raw/`: selected NetCDF synthetics and Apollo three-component records.
- `code/`: analysis and document-building scripts.
- `provenance/`: input manifest, checksums, claim-to-evidence matrix, and known limitations.
- `submission_materials/`: cover letter, author checklist, and repository-deposit instructions.
- `source_archive/`: untouched copies of the original manuscript and review files.
- `reports/`: focused technical reports, including the half-space report, the 33-page low-velocity-layer report, and the 91-page six-model synthesis report.
- `config/data_catalog.json`: machine-readable path inventory joining the half-space archive and the A16/S12 archive.

## Literature-output archive rule

All manuscript, review-response, literature-analysis, and technical-report outputs must retain their formal copy inside the `h` project. Temporary render folders and external drive paths are not accepted as the only copy. Editable sources or build scripts should be retained beside every Word/PDF deliverable. The workspace-level inventory is `../LITERATURE_OUTPUTS_INDEX.md`.

## Reproduction

1. Create a Python environment with the packages listed in `requirements.txt`.
2. Edit `config/input_paths.example.json` only if the raw inputs are stored elsewhere.
3. Run `python code/make_publication_figures.py` to rebuild Figures 1 and 4 from the archived CSV tables.
4. Run `python code/build_documents.py` to rebuild the Word submission files.
5. Run `python code/analyze_halfspace_models.py` to audit the external half-space/A16 paths and rebuild the half-space tables and Figures HS1-HS9.
6. Run `python code/analyze_low_velocity_models.py` to rebuild the M5/M6 low-velocity metrics and Figures LV01-LV24.
7. Run `python code/generate_direct_evidence_figures.py` and then `python code/build_low_velocity_and_integrated_reports.py` to rebuild the direct-evidence figures and both final technical reports.

The remaining main figures are copied from the verified four-model analysis and are indexed in `provenance/figure_provenance.csv`.

## Latest low-velocity and synthesis deliverables

The 2026-08-20 archive adds M5 (flat + heterogeneity + low-velocity layer) and M6 (topography + heterogeneity + low-velocity layer) to the data catalog. Their archived NetCDF files are byte-identical to the E-drive sources. The low-velocity report contains 24 conclusion-image evidence units; the integrated report contains 76 units supported by 46 independent figures. Final editable and PDF copies are retained in `reports/`, and the portable package is `../outputs/LOW_VELOCITY_AND_FULL_SYNTHESIS_20260820_FINAL/`.

The standalone S12 comparison `figures/low_velocity/Figure_S12_M1_M6_observed_three_component.png` overlays M1-M6 with the filtered Apollo observation for Z/R/T over 0-400 s. Model traces use the shared 3-C RMS scaling over 50-245 s; the exact scale factors are recorded in `data/derived/s12_m1_m6_observed_scaling.csv`.

The companion figures `Figure_S12_M1_M6_observed_envelope_comparison.png` and `Figure_S12_M1_M6_observed_energy_comparison.png` show the 20-s smoothed 3-C envelope and both absolute and per-record normalized cumulative energy. Their summary metrics are stored in `data/derived/s12_m1_m6_observed_envelope_energy_summary.csv` and can be regenerated with `code/plot_s12_envelope_energy_comparison.py`.

For component-resolved inspection, `Figure_S12_M1_M6_observed_component_envelopes.png` shows separate 20-s smoothed analytic-amplitude envelopes for Z, R, and T, each normalized by the corresponding observed-component peak. It is regenerated with `code/plot_s12_component_envelopes.py`.

The coefficient figure `Figure_S12_M1_M6_observed_component_envelope_correlations.png` reports zero-lag and best-lag (±10 s) Pearson correlations for each Z/R/T envelope over the common 50–245 s window. Values are stored in `data/derived/s12_m1_m6_observed_component_envelope_correlations.csv`.

## Submission boundary

The local package is complete, but AGU requires an externally archived data/software record with a persistent identifier. No external repository upload was performed automatically. Follow `submission_materials/REPOSITORY_DEPOSIT.md`, then add the resulting DOI to the Open Research section before uploading to the journal.
