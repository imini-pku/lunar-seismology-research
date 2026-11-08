# Supporting Information for

# Surface Topography and Shallow Heterogeneity Control Early Lunar Seismic Envelopes but Not the Apollo Long Coda

Tianxiong Wu, Yanbin Wang, and Wei Zhang

## Contents

This Supporting Information contains extended processing definitions, robustness tests, full distance-fit statistics, observation-model metrics, and provenance limits for the four completed simulations.

## Text S1. Signal-processing details

Synthetic NetCDF variables Vx, Vy, and Vz were read with their native time coordinates. Paired models have different native sample intervals, so any waveform subtraction or correlation was evaluated after interpolation to the coarser common interval over the overlapping time range. Station-level scalar metrics were first computed on each native filtered record and only then paired. Filtering used a fourth-order Butterworth bandpass from 0.3 to 0.9 Hz applied forward and backward.

T90 is t95-t05, where t05 and t95 are the first times at which cumulative squared velocity reaches 5% and 95% of its final value. For each positive metric X, a factorial effect is ln(XB/XA). Values shown as factors in the manuscript are exp[median ln(XB/XA)], which is the median stationwise ratio on a multiplicative scale; this need not equal the ratio of the two separate model medians.

## Text S2. Peak-time smoothing sensitivity

For observation-model peak-time comparisons, three-component analytic-signal energy was smoothed with 5, 10, 20, 40, 60, and 100 s windows. The reported value is the median over windows, and the minimum and maximum are retained as a smoothing sensitivity range. For the M3-M1 station ensemble, smoothing windows equal to 5, 10, and 20 dominant periods yield median energy-peak delays of 2.679, 5.244, and 7.695 s, respectively. The positive direction is robust; the exact number is not a window-independent material property.

## Text S3. Spatial dependence and false-discovery control

The first and last five receivers on each profile were removed. Predictor and response were independently fitted with cubic distance trends within each profile. Residuals were standardized by profile and averaged in sequential nonoverlapping blocks of 10 receivers. Blocks containing fewer than five receivers were omitted. Spearman correlations use the resulting 57 block means. Benjamini-Hochberg q values control the false-discovery rate across the tested predictor-response family. Sensitivity tables supplied in `data/derived` vary polynomial degree and block size.

## Table S1. Median stationwise factorial effects

| Conditional effect | Peak-time shift (s) | Peak-amplitude factor | Total-energy factor | T90 factor |
|---|---:|---:|---:|---:|
| Heterogeneity, flat surface (M3/M1) | 2.546 | 0.293 | 0.259 | 18.170 |
| Heterogeneity, topographic surface (M4/M2) | 1.650 | 0.686 | 0.867 | 2.181 |
| Topography, no heterogeneity (M2/M1) | 0.089 | 0.792 | 0.716 | 5.309 |
| Topography, heterogeneous medium (M4/M3) | 0.798 | 1.012 | 1.061 | 1.162 |

## Table S2. Three-component median energy fractions

| Model | Vertical | Radial | Transverse |
|---|---:|---:|---:|
| M1 | 0.701 | 0.299 | approximately 0 |
| M2 | 0.564 | 0.276 | 0.161 |
| M3 | 0.546 | 0.247 | 0.204 |
| M4 | 0.489 | 0.273 | 0.234 |

## Table S3. Apollo S12 comparison

| Record | Median peak time (s) | t05-to-peak (s) | t95 (s) | Early 3C correlation | Normalized RMSE |
|---|---:|---:|---:|---:|---:|
| Observed Apollo 16 impact | 658.294 | 375.080 | 2804.625 | - | - |
| M1 | 85.728 | 2.299 | 86.469 | -0.004 | 1.417 |
| M2 | 96.525 | 13.500 | 110.490 | -0.010 | 1.421 |
| M3 | 92.397 | 16.473 | 160.683 | 0.036 | 1.388 |
| M4 | 93.675 | 13.800 | 152.520 | 0.001 | 1.414 |

## Text S4. Model-provenance boundary

The flat no-heterogeneity run script verifies a 1,500 x 1,500 x 300 grid, 250 s time window, elastic-isotropic equation, harmonic equivalent-medium treatment, 30-point exponential absorbing layers, traction-image free surface, and 606 receivers. The archived layered-medium generator lists 34 velocity samples defining 33 layers. A separate random-medium generator contains a four-layer, 5% von Karman example, but the completed M3 and M4 output directories do not contain a run-local manifest proving that this exact generator and parameter set produced those NetCDF files. Accordingly, the paper does not quote a unique stochastic amplitude or correlation length. This is a repository-deposit issue to resolve from production logs, not a parameter to infer from waveforms after the fact.

## Figure S1. Smoothed peak-time sensitivity

The supplied sensitivity figure shows that heterogeneity delays the ensemble energy peak for multiple smoothing scales, while the precise delay grows with the smoothing window.

## Figure S2. S12 time-frequency comparison

The observation retains energy far beyond the modeled duration. Within the common early window, frequency content and temporal evolution also differ, supporting a propagation-model mismatch rather than a scalar amplitude mismatch.
