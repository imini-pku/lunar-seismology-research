# Project design review

## Current scientific core

The project now answers one focused question: how do realistic lunar surface relief and shallow random heterogeneity independently and jointly alter early seismic waveforms, and are those changes sufficient to reproduce an Apollo long coda?

The four completed simulations are treated as a factorial experiment rather than as unrelated examples. This permits four conditional effects and one interaction to be calculated without changing source or receiver geometry. The observation is used as an exclusion test, not as a successful fit.

## Improvements implemented

- Replaced the old topography-only narrative with a four-model factorial design.
- Removed visible tracked deletions and rebuilt the English manuscript from a clean source.
- Replaced qualitative waveform claims with stationwise amplitude, energy, T90, component-fraction, interaction, and distance-scaling metrics.
- Added spatial blocking, distance detrending, profile-specific checks, false-discovery control, and smoothing sensitivity.
- Reframed the Apollo comparison with a single three-component scale per model and preserved the negative waveform result.
- Added seven main figures, two supporting figures, three supporting tables, a cover letter, a claim-to-evidence matrix, raw inputs, derived data, and reproducibility scripts.
- Rendered and visually inspected the complete Word manuscript and Supporting Information.
- Added a checksum-audited data catalog that links the half-space archive, its eight topographic-resolution models, the layering comparison, and all A16/S12 external and packaged paths.
- Reprocessed all half-space comparisons with native-rate three-component filtering, common-time alignment, energy/T90 metrics, waveform similarity, lag sensitivity, and linear-versus-diffusion-form diagnostics.

## Claims deliberately removed or narrowed

- The simulations do not show that topography explains the Apollo long coda.
- A linear peak-time-distance trend is not presented as diffusion.
- Crater diameter alone is not treated as a sufficient topographic descriptor.
- The profile-relief relation is restricted to profiles 2 and 3.
- Exact random-medium amplitude, correlation length, and layer depth are not quoted because the production manifest is incomplete.
- The full half-space resolution archive is now verified. A 0.5 km threshold is supported for lag-tolerant waveform shape, but not for energy convergence; a combined correlation-and-energy criterion supports approximately 0.25 km. This distinction has not yet been inserted into the main manuscript pending author approval.

## Newly documented limitations

- The two requested topography-switch NetCDF files use an r1-r800 line at 75° and 50 m spacing, not the current 216-receiver `test.station` geometry. The exact 800 coordinates are recovered from the original run script and verified against `newfigure6_part3_3.m`; distance analysis now uses r20-r760 (1-38 km), matching the MATLAB logic.
- The 800-receiver archive samples one azimuthal profile. Its distance dependence is therefore a path-specific result and should not be generalized as an isotropic attenuation law or a global crater-scale relation.
- The project-folder and terrain suffixes encode sampling counts, not meter values. The verified physical sequence is 0.125, 0.25, 0.5, 1, 2.5, 4, 6.25, and 10 km.
- The half-space and A16 effect sizes are contextual comparisons, not a controlled cross-region factorial contrast.

## Remaining external or author-only actions

The paper is locally complete but not yet eligible for final portal upload. The authors must verify the M2/M4 production manifest, approve authorship/funding statements, deposit data and software in a DOI-issuing repository, and insert that DOI in Open Research. These actions require author authority and cannot be inferred from the waveform files.
