# Half-space and A16 data audit

Audit date: 2026-08-17  
Machine-readable catalog: `config/data_catalog.json`  
File-level inventory and SHA-256 checksums: `provenance/halfspace_input_audit.csv`

## Resolution-name interpretation

The suffixes `400/200/100/40/25/16/10` are sampling counts over an approximately 100 km scale, not resolutions in meters. Cross-checking the original manuscript, project-folder names, and terrain relief gives the following physical mapping:

| Project suffix | Physical resolution |
|---:|---:|
| `0.125_old` / base `4000_topo` file | 0.125 km |
| `400` | 0.25 km |
| `200` | 0.5 km |
| `1` / terrain suffix `100` | 1 km |
| `40` | 2.5 km |
| `25` | 4 km |
| `16` | 6.25 km |
| `10` | 10 km |

This interpretation reproduces the six resolutions described in the original manuscript and the additional 0.25 and 0.5 km models described in the reviewer response.

## NetCDF comparability

- All half-space NetCDF files span approximately 100 s and contain `Vx`, `Vy`, and `Vz` plus `station_name`.
- Native sampling intervals differ from 0.0027 to 0.0180 s. Each trace is therefore filtered at its native rate, then interpolated to a shared 0.02 s grid through 99.88 s.
- The topographic-resolution series and layering switch each contain 216 receivers named `r1-r216`.
- All available 216-receiver `test.station` files are byte-identical (SHA-256 `60bba378270e87772b66c5079bf705aa439949ead2fe8f1cdd8abe1ad24472f0`).
- The 0.125 km `_old` folder contains only `output`; its 216 names are matched to the identical station geometry retained in `E:\project_use1_topo_0.125\test.station`.

### Archived 216-receiver geometry

The user-supplied station list was imported on 6 September 2026 as
`data/raw/halfspace_216_ring_receivers.station` (SHA-256
`b8344a38b863b898ea0f6cf64d9724b64b1bdc4e4113c554ec7de53c0c9b9db8`).
After whitespace normalization, it is identical to
`E:\project_use1_topo_0.125\test.station` and the other retained 216-receiver
station files. The derived table
`data/derived/halfspace_216_ring_receiver_geometry.csv` (SHA-256
`bb85982ca9194a33f3847cd318d04cee5fe460b1ea322512820cf8b672608930`)
adds distance and azimuth fields without changing the supplied coordinates.
Validation confirms nine radii (5–45 km at 5 km spacing) and 24 azimuths
(0–345° at 15° spacing), giving 216 stations. This is a concentric-ring,
multi-azimuth geometry, not three receiver paths and not the r1–r800 75° line.
The reproducible importer is `code/import_halfspace_216_receiver_geometry.py`.

## Recovered geometry for the 800-receiver pair

`E:\project_use1_topo_0.125\output\station.nc` and `E:\project_use1_layer\output\station.nc` each contain 800 nonzero receivers named `r1-r800`. Their current project `test.station` files contain a different 216-receiver geometry and must not be joined to these NetCDF records.

The correct geometry is independently documented by two archived sources:

- `D:\software\CGFD3D_v26.03\revise\usefiles\newfigure6_part3_3.m` sets `epi_dist = station_index * 50 / 1000` km and `azimuth_deg = 75` and uses r20-r760 for the 1-38 km distance profile.
- `D:\software\CGFD3D_v26.03\revise\cgfd3d.revise.use1.topo.0.125.Q.sh` lists all coordinates from r1 through r800 and places the source at (50000,50000) m.

The resulting receiver line is

`x_i = 50000 + 50 i cos(75°)`, `y_i = 50000 + 50 i sin(75°)`, `R_i = 0.05 i km`, for `i=1,...,800`.

The formula and listed coordinates agree to better than 0.001 mm. The full geometry is archived as `data/derived/halfspace_800_receiver_geometry.csv`; the analysis rotates X/Y to R/T using the verified 75° azimuth. Distance-dependent plots use r20-r760, while all-receiver effect-size summaries retain r1-r800.

## A16/S12 linkage

The catalog records both the four external A16 simulation paths and the packaged copies under `data/raw`, as well as the three Apollo components and the A16 topography file. The four external A16 project folders do not retain run-local station files; their 606-receiver geometry remains reproducible through `code/verified_legacy/plot_releasy_waveform_comparison.py::build_station_geometry`.

## Reproduction

Run `python code/analyze_halfspace_models.py` from `jgr_planets_submission`. The script validates the two receiver-geometry sources, writes all half-space tables to `data/derived`, figures to `figures/halfspace`, and refreshes `provenance/halfspace_input_audit.csv`.
