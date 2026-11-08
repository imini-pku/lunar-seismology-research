# Low-velocity simulation input audit

The two user-supplied project folders contain only `output/station.nc`. The data have been copied into `jgr_planets_submission/data/raw/` and verified by SHA-256.

## Confirmed from the files

- NETCDF4 files with r1-r606, seq_no 0-605, Vx/Vy/Vz, and finite samples.
- M5 uses the same station/time prefix as M3; M6 uses the same station/time prefix as M4.
- M5/M6 extend to approximately 400 s; M1-M4 end at approximately 250 s.
- The validated REL3 station generator is therefore used for coordinates and per-station R/T rotation.
- Cumulative-energy times use squared three-component filtered velocity, matching REL3 and half-space definitions; T90=t95-t05.
- Inferential effect estimates use the same 57 spatial-block medians for the point estimate, bootstrap interval, and Wilcoxon test; station-level medians are retained as descriptive fields.

## Not recoverable from the supplied folders

- Low-velocity-layer thickness, Vp, Vs, density, Q, and whether the layer follows topography.
- Random-medium strength, correlation length, realization/seed, and whether heterogeneity occupies the low-velocity layer.
- Exact source file, source normalization, grid spacing, boundary settings, and run command.

The older REL3 figure describing a 1 km candidate layer is a theoretical diagnostic and is not treated as metadata for M5/M6.

## Checksums

- M1: `D0714E05DCEAAA7A4357D63EA5236D96C37566A6656915147959DAE748C83D78` (95,829,014 bytes)
- M2: `485DEB23798450B90315FB4EBE83340E2004EFCF9113504E435B56BADFD18AD8` (121,360,498 bytes)
- M3: `55E738A98A2651191D80219031E5FE6BD5E6FC355B159B7F7B86E69575CBAA7A` (95,829,014 bytes)
- M4: `270E1D5D64D926C4EB8A98AD2E6DAFEFEE10D745FE148F7B7C10CCB73B3D8C16` (121,360,498 bytes)
- M5: `E2E49715DC7D92AB2034A5302AB730D89E659F31211033705A637CD3FF451D31` (153,273,034 bytes)
- M6: `DC1F95129B0A93DC49EB7D3D3B1A62D22471DA248979CBCC6531BE3772E76E76` (194,120,498 bytes)
