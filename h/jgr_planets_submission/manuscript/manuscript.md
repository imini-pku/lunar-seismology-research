# Surface Topography and Shallow Heterogeneity Control Early Lunar Seismic Envelopes but Not the Apollo Long Coda

Tianxiong Wu^1,2^, Yanbin Wang^1,2^, and Wei Zhang^3^

^1^ Department of Geophysics, School of Earth and Space Sciences, Peking University, Beijing 100871, China  
^2^ State Key Laboratory of Earthquake Dynamics and Forecasting, Peking University, Beijing 100871, China  
^3^ Department of Earth and Space Sciences, Southern University of Science and Technology, Shenzhen, Guangdong 518055, China

Corresponding author: Yanbin Wang (ybwang@pku.edu.cn)

## Key Points

- Surface relief, heterogeneity, and low velocity form one conditionally coupled M1–M6 ladder.
- Low velocity gives the largest peak delay, but depends on the topographic and heterogeneous background.
- All synthetics remain finite-duration and far shorter than the Apollo coda.

## Abstract

Apollo seismograms have emergent onsets and exceptionally long codas, but the coupled roles of surface relief, subsurface heterogeneity, and low-velocity structure remain uncertain. We analyze six three-dimensional elastic states in one A16/S12 model ladder: M1–M4 form the flat/topographic by homogeneous/heterogeneous baseline, and M5–M6 add a low-velocity state while retaining the A16 geometry and heterogeneous background. The same source and receiver sequence are processed from 0.3 to 0.9 Hz; 575 profile receivers are used for the primary spatial analysis. In the ladder, heterogeneity increases median T90 by a factor of 18.2 on the flat surface, topography increases it by 5.31 without heterogeneity, and the combined M4 state shows nonadditive saturation. Adding the low-velocity state shifts median tmax to 173–185 s and t95 to about 231 s, while increasing the transverse fraction to 28.9–29.3%. Across all six states and three profiles, peak-energy time remains closer to linear distance than squared-distance diffusion. At Apollo 12 station S12, the low-velocity states improve early envelope timing but remain far earlier than the observed peak near 658 s and t95 near 2,805 s. The tested topography, heterogeneity, and low-velocity state therefore control measurable early scattering signatures but are jointly insufficient to explain the lunar long coda.

## Plain Language Summary

Seismic signals recorded on the Moon continue ringing much longer than typical earthquake records. We use one six-state computer experiment to follow a wavefield as it encounters flat or rough topography, shallow broken-rock heterogeneity, and finally a low-velocity state. The first four states separate the topographic and heterogeneous effects; the last two show how a low-velocity layer acts on an already complex wavefield. All three processes spread energy and generate transverse motion, but their effects depend on the background and do not simply add. The low-velocity states delay the modeled peak and retain more late energy, yet every synthetic signal remains far shorter than the Apollo 16 impact record at station S12. The results identify which early signatures are explained by the tested near-surface physics and which require deeper, stronger, multiscale scattering and longer simulations.

Keywords: lunar seismology; topographic scattering; seismic coda; numerical modeling; Apollo; wave propagation

## 1 Introduction

Apollo seismic records differ from terrestrial seismograms in their emergent arrivals, severe phase mixing, and codas lasting hundreds to thousands of seconds. These features are commonly attributed to strong scattering in a dry, fractured regolith and megaregolith combined with weak intrinsic attenuation (Nunn et al., 2020). Coda analyses and numerical studies have shown that the strength, thickness, and correlation scales of shallow heterogeneity can substantially change lunar envelopes (Blanchette-Guertin et al., 2012, 2015; Gillet et al., 2017; Onodera et al., 2021, 2022). Yet the Moon also has extreme surface relief, and a free surface containing craters, rims, and slopes can reflect, diffract, focus, and convert seismic energy.

Topographic effects are well established in terrestrial wave propagation. Irregular free surfaces can amplify or deamplify motion, generate scattered phases, and convert P-SV energy into transverse motion (Hartzell et al., 1994; Pitarka & Irikura, 1996; Rodgers et al., 2010; Zhang et al., 2012). Recent high-frequency studies further show that topography can dominate local waveform differences and bias structural inference if omitted (Pienkowska et al., 2025; Zheng et al., 2024). Because lunar relief is widespread and atmospheric and hydrological erosion are negligible, its integrated effect may be especially important. However, a rough surface and a heterogeneous subsurface can produce similar envelope broadening, so a topography-only comparison cannot identify either contribution cleanly.

Previous versions of this study emphasized crater-scale examples and qualitative resolution comparisons. Those experiments demonstrated waveform sensitivity to surface shape but did not place low-velocity trapping on the same evidence chain as topographic and volumetric scattering. Here we reorganize the problem as one six-state numerical experiment. M1–M4 independently vary surface topography and shallow heterogeneity; M5–M6 add a low-velocity state in the heterogeneous background while retaining the same A16 receiver system. We ask five questions: (1) Which waveform changes are introduced at each stage of the M1–M6 ladder? (2) Do topography, heterogeneity, and low-velocity retention interact nonlinearly? (3) Are topographic effects better predicted by receiver elevation or by relief accumulated along the propagation path? (4) Does the peak-energy ridge remain ballistic or become diffusion-like? (5) Do the six modeled envelopes approach the Apollo 16 impact observation at station S12?

Our analysis distinguishes an effect from an explanation. A mechanism may measurably broaden a 250 s synthetic record without being sufficient to explain a coda that contains most of its energy after the synthetic has ended. This distinction leads to a constrained result: realistic surface relief and the tested shallow heterogeneity produce strong, reproducible early-waveform signatures, but neither individually nor jointly reaches the diffusive, long-duration regime of the Apollo observation.

## 2 Numerical Experiment and Data

### 2.1 Six-state A16/S12 model ladder

We analyze three-dimensional elastic simulations computed with CGFD3D, a collocated-grid finite-difference solver that represents an irregular free surface with curvilinear coordinates and a traction-image boundary treatment (Zhang & Chen, 2006; Zhang et al., 2012; Wang et al., 2022). The computational grid contains 1,500 x 1,500 x 300 points. A 30-point absorbing layer is applied on the four lateral boundaries and the bottom; the top is a traction-free surface. Each simulation spans 250 s and saves three-component velocity at 606 receivers. The source and station geometry follow the Apollo 16 artificial-impact configuration used in the original project.

The six states form one continuous A16/S12 ladder (Figure 1). M1 has a flat free surface and no random heterogeneity. M2 replaces the flat surface with realistic lunar topography but has no random heterogeneity. M3 adds shallow random heterogeneity to the flat surface. M4 contains both topography and heterogeneity. M5 adds the supplied low-velocity state to the flat heterogeneous background, and M6 adds the same class of low-velocity state to the topographic heterogeneous background. Thus M5/M6 are conditionally comparable to M3/M4, not independent low-velocity-only controls. All models use the same A16 source and receiver sequence; 575 primary profile receivers are retained. M1–M4 records are approximately 250 s, whereas M5/M6 extend to approximately 400 s. The archived layered-model generator contains 33 layers over the modeled depth range, with P-wave velocity increasing from approximately 2.54 to 6.90 km/s and S-wave velocity from approximately 1.27 to 3.98 km/s. Because complete run-time manifests were not colocated with every NetCDF output, we restrict absolute amplitude and energy interpretation to conditional run-level contrasts and do not invert for a unique low-velocity or heterogeneity parameter set.

[[FIGURE:Figure_1_experiment_design.png]]

### 2.2 Receivers and Apollo observation

One receiver represents Apollo station S12. The remaining receivers form three approximately radial profiles. To reduce endpoint artifacts, the first and last five receivers on each profile are excluded, leaving 575 receivers for the primary spatial analysis. Results for S12 are analyzed separately. Epicentral distance is computed from the shared source coordinate. Topographic elevation is sampled at each receiver, and three cumulative path descriptors are formed along each profile: mean elevation, mean absolute slope, and relief range (the maximum elevation encountered minus the minimum elevation encountered from the source-side end to a receiver). These profile-based quantities are proxies for the surface geometry encountered by the propagating wavefield, not full three-dimensional ray integrals.

The observational comparison uses the three-component Apollo 16 impact record at Apollo 12 station S12. We compare the 50-245 s interval shared by the observation and synthetics for waveform similarity, while cumulative observed energy is evaluated to 3,000 s. A single root-mean-square scale factor is estimated for all three components of each model over the shared interval. We do not scale individual components or tune separate time windows, so component ratios and waveform mismatch remain visible.

### 2.3 Signal processing and metrics

All synthetic and observed traces are demeaned and filtered with a fourth-order, zero-phase Butterworth bandpass from 0.3 to 0.9 Hz. This band overlaps the approximately 0.43 Hz dominant frequency of the observed three-component record. Unless stated otherwise, cross-state effects use the shared 50–245 s window; M5/M6 late-energy diagnostics additionally use 50–395 s and are never mixed with the shorter-record duration values.

For a trace v(t), total recorded energy is proportional to the time integral of v(t)^2. The 90% duration, T90, is the interval between the times at which cumulative energy reaches 5% and 95%. Peak time and peak amplitude are taken from the maximum absolute filtered velocity in the station-level factorial analysis. For the Apollo comparison, energy-peak time is calculated from the squared analytic-signal amplitude summed over three components and smoothed with windows from 5 to 100 s; the reported value is the median across six windows. Late-energy fraction begins 15 s after the trace peak. Positive metrics are compared as logarithmic ratios, while time metrics are direct differences.

To describe component redistribution, horizontal traces are rotated into radial and transverse directions using the source-receiver azimuth. Component energy fractions are then computed as EZ/(EZ+ER+ET), ER/(EZ+ER+ET), and ET/(EZ+ER+ET). Because transverse energy in M1 is near numerical zero, transverse conversion is reported as an energy-fraction change rather than an unstable ratio.

### 2.4 Spatial inference and interaction

Factorial effects are defined by paired contrasts: heterogeneity on a flat surface is M3-M1, heterogeneity with topography is M4-M2, topography without heterogeneity is M2-M1, and topography with heterogeneity is M4-M3. For positive metric X, the contrast is ln(XB/XA). The second-order interaction is the difference between the two conditional effects. A negative duration interaction means that the combined broadening is smaller than the sum expected from independent log-scale effects.

For terrain relationships, both the response and predictor are detrended separately along each profile with a cubic function of epicentral distance, standardized within profile, and averaged in nonoverlapping blocks of 10 adjacent receivers. Spearman rank correlation is then computed on 57 block means. False-discovery rates are controlled with the Benjamini-Hochberg procedure. Profile-specific correlations are also reported because an aggregate relation is not assumed to generalize to every direction. Sensitivity tests vary detrending degree and block size and are supplied in the Supporting Information.

## 3 Results

### 3.1 The A16 response is a continuous M1–M6 model ladder

The unified station analysis shows a staged, conditionally coupled response (Figure 8). M1 is a compact flat-surface reference. M2 introduces topographic redistribution and transverse motion without the strong broadening associated with heterogeneity, whereas M3 adds heterogeneous broadening on the flat surface. M4 combines the two processes but does not equal the sum of M2-M1 and M3-M1. The low-velocity states then move the same heterogeneous wavefield to a later regime: median tmax is 184.6 s in M5 and 173.1 s in M6, compared with 58.3–64.9 s in M1-M4, and median t95 is approximately 231 s in both low-velocity states. The median transverse fraction rises to 28.9% and 29.3% in M5 and M6, respectively.

The sequence is therefore a mechanism ladder, not a ranking of unrelated simulations. M3/M5 compare low-velocity behavior on a flat heterogeneous background, while M4/M6 compare it on a topographic heterogeneous background. Because no low-velocity homogeneous state is available, the M5/M6 transitions are conditional states rather than an independently estimable three-factor main effect.

[[FIGURE:Figure_A16_M1_M6_unified_ladder.png]]

### 3.2 Heterogeneity strongly broadens and weakens the flat-surface wavefield

The flat, homogeneous reference M1 produces compact, high-amplitude arrivals. Adding heterogeneity (M3-M1) changes the waveform at nearly every receiver (Figure 2). Across the 575 primary receivers, median peak amplitude becomes 0.293 of M1 and total energy becomes 0.259. Median T90 increases from 2.57 s in M1 to 50.63 s in M3, corresponding to a stationwise median factor of 18.2. The median peak-time shift based on maximum absolute velocity is 2.55 s, with substantial path dependence; a smoothed analytic-energy measure gives a 5.24 s median delay at the 10-period smoothing scale and preserves a positive delay under shorter and longer windows (Supporting Information).

The contrast therefore is better characterized as broadening and coherent-peak loss than as a single universal time delay. Heterogeneity redirects and spreads energy, and the exact envelope maximum moves with smoothing scale when multiple late arrivals have comparable amplitude.

[[FIGURE:Figure_2_factorial_waveforms.png]]

### 3.3 Topography broadens low-amplitude energy and converts components

Topography alone (M2-M1) has a smaller but systematic duration effect. Median T90 rises from 2.57 s in M1 to 14.50 s in M2, and the median stationwise duration factor is 5.31. Median peak amplitude and total energy become 0.792 and 0.716 of M1. The near-zero median peak-time shift (0.089 s) shows that the strongest coherent arrival often remains at nearly the same time even as low-amplitude energy is redistributed later in the record. Thus a large duration ratio does not by itself demonstrate diffusion; the denominator is short and much of the added window contains weak scattered energy.

Component fractions provide independent evidence for three-dimensional conversion (Figure 3). Median Z/R/T energy fractions are 70.1%/29.9%/approximately 0% in M1, 56.4%/27.6%/16.1% in M2, 54.6%/24.7%/20.4% in M3, and 48.9%/27.3%/23.4% in M4. Both topography and heterogeneity break the symmetry of the flat reference and generate transverse motion. The combined model has the largest median transverse fraction, but the increment is not the sum of the separate increments.

[[FIGURE:Figure_3_component_energy.png]]

### 3.4 Path relief predicts topographic effects along two profiles

Receiver elevation alone incompletely describes topographic scattering because it samples only one point. After removing the distance trend, cumulative relief range is strongly associated with the topography-only contrast along profiles 2 and 3 (Figure 4). For peak amplitude, the profile-specific Spearman correlations are -0.753 and -0.802; for total energy they are -0.824 and -0.801; and for T90 they are +0.750 and +0.792. Across the 57 spatial blocks, the respective correlations are -0.736, -0.731, and +0.659, with false-discovery-rate-adjusted q values no greater than 1.42 x 10^-6^ for these three relations.

Profile 1 does not show the same topography-only relation: its correlations between path relief and peak amplitude, total energy, and T90 are -0.130, -0.095, and +0.008. The result is therefore directional rather than a universal lunar scaling law. Mean absolute slope supplies complementary information about how frequently the profile encounters inclined surface segments, but relief range is the stronger predictor for coherent amplitude and energy in this experiment.

[[FIGURE:Figure_4_path_relief.png]]

### 3.5 Topography and heterogeneity interact nonadditively

The two processes show strong saturation on a logarithmic duration scale. Heterogeneity increases median stationwise T90 by a factor of 18.2 on the flat surface (M3/M1), but by only 2.18 when topography is already present (M4/M2). Conversely, topography increases T90 by a factor of 5.31 without heterogeneity (M2/M1), but by only 1.16 in the heterogeneous background (M4/M3). The same qualitative saturation appears in representative three-component interaction residuals (Figure 5).

Nonadditivity is expected when both perturbations act on the same finite packet of coherent energy. The first process can already transfer much of that packet into later arrivals and transverse motion, leaving the second process with a different incident wavefield. This result warns against adding independently estimated topographic and volumetric scattering corrections. It does not by itself identify a unique physical saturation mechanism, because the simulations contain only one realization and strength of heterogeneity.

[[FIGURE:Figure_5_interaction_residual.png]]

### 3.6 Energy transport remains ballistic rather than diffusive

If late energy were governed by a simple diffusion process, a characteristic envelope time would scale approximately with squared distance. We compare linear tmax=a+bR and diffusion-form tmax=a+cR^2^ relations across all three profiles and all six states (Figures 6 and 9). The M1–M4 combinations strongly prefer the linear relation, and the low-velocity M5/M6 fits retain the same preference while showing larger slopes and residual scatter. The low-velocity censor-safe comparisons still favor linear migration, with a minimum ΔAIC of about 12.8. The unified plot shows that the low-velocity state delays the peak-energy ridge but does not convert it into a squared-distance diffusion law.

Topography, heterogeneity, and the low-velocity state clearly perturb the waveforms, but the movement of the main energy packet remains dominated by finite-speed propagation. The modeled regime is therefore not equivalent to the strong multiple-scattering regime inferred for the full lunar coda.

[[FIGURE:Figure_6_linear_diffusion.png]]

### 3.7 The six synthetics do not reproduce the Apollo long coda

The Apollo comparison provides a decisive scale test (Figures 7 and 10). Across six envelope-smoothing windows, the observed three-component energy peak has a median time of 658.3 s (range 647.1-770.4 s). M1-M4 peak at 85.7, 92.4, 96.5, and 93.7 s, while M5/M6 peak at 213.2 and 272.5 s at S12. The low-velocity states therefore move the envelope in the correct direction, but remain hundreds of seconds early.

The cumulative-energy mismatch is larger. The 95% energy times are 86.5, 160.7, 110.5, and 152.5 s for M1-M4, approximately 368–382 s for M5/M6 in the extended records, but 2,804.6 s for the observation. Only 4.0% of the observed 50-3,000 s energy lies before 250 s. The observation takes 375.1 s to rise from 5% cumulative energy to its median smoothed peak; all six synthetics rise much faster. The low-velocity states can improve early envelope similarity while leaving phase correlations near zero. Amplitude rescaling cannot correct this joint phase, component, and duration mismatch.

[[FIGURE:Figure_7_observed_models.png]]

[[FIGURE:Figure_S12_M1_M6_observed_envelope_comparison.png]]

## 4 Discussion

### 4.1 What topography explains

The factorial contrasts establish three robust topographic signatures. First, topography widens the recorded-energy window without necessarily delaying the largest coherent pulse. Second, it converts energy into transverse motion, consistent with loss of the P-SV symmetry of a flat interface. Third, its spatial effect is related more closely to geometry accumulated along the profile than to elevation at the receiver. These signatures are relevant to source interpretation, landing-site seismology, and forward modeling of future lunar networks. A topography-free model can misattribute converted phases or duration changes to subsurface structure.

The results also define what topography does not explain in the present experiment. The topography-only model remains compact relative to Apollo, and the combined model does not move toward a squared-distance envelope-time relation. Claims that cratered relief is a principal cause of the observed long coda are therefore not supported by these simulations. The strongest defensible statement is that relief modifies early scattering and component partitioning.

### 4.2 Why the combined effect is conditional across M1–M6

The nonadditive interaction is scientifically important because real lunar wavefields encounter irregular interfaces, broken material, and potentially low-velocity traps in sequence. In a linear elastic solver, wave propagation is linear for a fixed medium, but the difference between two different media need not be additive. Surface and volume perturbations alter the incident field seen by one another, and duration metrics are nonlinear summaries of the entire trace. The nearly saturated T90 in M4 and the different M5/M6 responses show that the low-velocity state acts on a wavefield whose coherence and polarization have already been modified by the earlier stages.

Additional realizations are needed to distinguish systematic saturation from realization-specific interference. A future design should add low-velocity/no-heterogeneity controls and vary heterogeneity strength, horizontal and vertical correlation length, low-velocity thickness, topographic scale, and source frequency. The present six states identify a continuous conditional mechanism chain but cannot map a complete three-factor response surface.

### 4.3 Missing physics implied by the Apollo mismatch

The observation-model comparison points to missing propagation physics rather than a source-amplitude problem. Even the 400 s M5/M6 records truncate the time interval containing most of the observed energy, while normalized waveform and phase correlations remain poor in the common early window. Candidate deficiencies include a thicker and more strongly scattering megaregolith, depth-dependent correlation scales, crater-related subsurface damage, lateral variations in regolith thickness, stronger velocity gradients near the surface, intrinsic attenuation structure, and scattering below the current perturbed layer (Blanchette-Guertin et al., 2015; Gillet et al., 2017; Onodera et al., 2021, 2022).

Longer synthetics are the first requirement for testing these mechanisms. A 3,000-5,000 s output window, combined with energy-conserving boundaries and convergence checks, would permit direct comparison of late-envelope decay and diffusion diagnostics. Multiple stochastic realizations are also required for uncertainty caused by random-medium phase. Source-time-function and impact-coupling sensitivity should be evaluated, but the more than 2,400 s gap in 95% energy time cannot plausibly be removed by scalar source matching alone.

### 4.4 Limitations

This study has five explicit limits. First, M1-M4 are 250 s long and M5/M6 are 400 s long, so none can test the full Apollo coda. Second, only one random-medium realization and strength are available. Third, cumulative surface relief along receiver profiles is a geometric proxy, not a three-dimensional Fresnel-volume or ray-path integral. Fourth, only one Apollo impact-station pair is compared, so no observed distance-scaling law is estimated. Fifth, the six output files lack fully colocated run manifests and low-velocity/no-heterogeneity controls; paired comparisons are reliable because processing is identical, but exact low-velocity and heterogeneity parameters must be confirmed from the original production archive before physical inversion or public repository deposit.

These limits motivate the evidence hierarchy used here: station-level paired effects and broad observation-model exclusions are treated as strong results; path correlations are restricted to profiles where they reproduce; unique crater, layer-depth, or diffusion interpretations are not claimed.

## 5 Conclusions

The A16/S12 experiment is most clearly interpreted as one six-state model ladder rather than four baseline models plus a separate low-velocity study.

1. **The ladder separates successive mechanisms.** M1→M2 isolates topographic redistribution, M1→M3 isolates heterogeneous broadening, M2/M3→M4 reveals nonadditive coupling, and M3→M5/M4→M6 show how a low-velocity state acts on already heterogeneous wavefields.

2. **Heterogeneity is the strongest early broadening mechanism in the baseline states.** It increases median stationwise T90 by a factor of 18.2 on the flat surface while reducing coherent peak amplitude and finite-window energy.

3. **Topography controls polarization and path dependence.** It increases T90 by a factor of 5.31 without heterogeneity, produces a median 16.1% T fraction, and yields the strongest relief–response relations along two of the three profiles.

4. **The low-velocity state produces the largest peak-time delay and late-energy retention in the tested ladder.** M5/M6 have median tmax of 184.6/173.1 s, median t95 near 231 s, and T fractions of 28.9%/29.3%. These are conditional responses because both low-velocity states include heterogeneity.

5. **The six-model peak-energy ridge remains finite-speed and distance structured.** Low velocity increases migration slopes and scatter, but the data do not support a simple squared-distance diffusion law.

6. **The Apollo mismatch remains multidimensional.** M5/M6 improve early envelope timing, but all six models remain far earlier than the Apollo S12 peak near 658 s and t95 near 2,805 s; phase, transverse details, frequency–duration extent, and full coda length remain unresolved.

Realistic relief, shallow heterogeneity, and low-velocity retention are therefore necessary ingredients for accurate early lunar waveform modeling, but the tested combination is not sufficient to explain the Apollo long coda. Future simulations should add low-velocity/no-heterogeneity controls, extend outputs to thousands of seconds, and jointly vary deeper multiscale scattering, Q, source coupling, and stochastic realizations.

## Acknowledgments

This study was supported by the National Natural Science Foundation of China (Grant 41930103). We thank the Apollo Passive Seismic Experiment teams and the producers of the SLDEM2015 and GRAIL products. The authors also acknowledge the developers of CGFD3D.

## Open Research

SLDEM2015 topography is publicly available from the MIT/LOLA archive (https://imbrium.mit.edu/BROWSE/SLDEM2015/TILES/), and GRAIL products are available from the NASA Planetary Data System (https://pds-geosciences.wustl.edu/missions/grail/default.htm). CGFD3D is available at https://github.com/zw-sustech/CGFD3D. The exact derived tables, selected synthetic station files, Apollo traces used here, analysis scripts, and input checksums are assembled in the companion archival package supplied with this manuscript. A persistent repository DOI must be inserted here after author-approved deposit and before journal submission; no DOI has been fabricated in this local draft.

## Author Contributions

Tianxiong Wu: Conceptualization, methodology, investigation, formal analysis, visualization, writing - original draft. Yanbin Wang: Conceptualization, supervision, funding acquisition, writing - review and editing. Wei Zhang: Software, numerical methodology, resources, writing - review and editing. All authors should confirm this statement before submission.

## References

Barker, M. K., Mazarico, E., Neumann, G. A., Zuber, M. T., Haruyama, J., & Smith, D. E. (2016). A new lunar digital elevation model from the Lunar Orbiter Laser Altimeter and SELENE Terrain Camera. Icarus, 273, 346-355. https://doi.org/10.1016/j.icarus.2015.07.039

Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate: A practical and powerful approach to multiple testing. Journal of the Royal Statistical Society: Series B, 57(1), 289-300. https://doi.org/10.1111/j.2517-6161.1995.tb02031.x

Blanchette-Guertin, J., Johnson, C. L., & Lawrence, J. F. (2012). Investigation of scattering in lunar seismic coda. Journal of Geophysical Research: Planets, 117, E06003. https://doi.org/10.1029/2011JE004042

Blanchette-Guertin, J., Johnson, C. L., & Lawrence, J. F. (2015). Effects of lateral variations in megaregolith thickness on predicted lunar seismic signals. Geophysical Research Letters, 42, 10,117-10,125. https://doi.org/10.1002/2015GL066151

Blanchette-Guertin, J., Johnson, C. L., & Lawrence, J. F. (2015). Modeling seismic energy propagation in highly scattering environments. Journal of Geophysical Research: Planets, 120, 515-537. https://doi.org/10.1002/2014JE004654

Gillet, K., Margerin, L., Calvet, M., & Monnereau, M. (2017). Scattering attenuation profile of the Moon: Implications for shallow moonquakes and the structure of the megaregolith. Physics of the Earth and Planetary Interiors, 262, 28-40. https://doi.org/10.1016/j.pepi.2016.11.001

Hartzell, S. H., Carver, D. L., & King, K. W. (1994). Initial investigation of site and topographic effects at Robinwood Ridge, California. Bulletin of the Seismological Society of America, 84, 1336-1349.

Lognonne, P., Gagnepain-Beyneix, J., & Chenet, H. (2003). A new seismic model of the Moon: Implications for structure, thermal evolution and formation of the Moon. Earth and Planetary Science Letters, 211, 27-44. https://doi.org/10.1016/S0012-821X(03)00172-9

Nunn, C., Garcia, R. F., Nakamura, Y., et al. (2020). Lunar seismology: A data and instrumentation review. Space Science Reviews, 216, 89. https://doi.org/10.1007/s11214-020-00709-3

Nunn, C., Fernando, B. A., & Panning, M. P. (2024). Artificial impacts on the Moon: Modeling 3D seismic propagation effects with AxiSEM3D. The Planetary Science Journal, 5, 246. https://doi.org/10.3847/PSJ/ad83d2

Onodera, K., Kawamura, T., Tanaka, S., Ishihara, Y., & Maeda, T. (2021). Numerical simulation of lunar seismic wave propagation: Investigation of subsurface scattering properties near Apollo 12 landing site. Journal of Geophysical Research: Planets, 126, e2020JE006406. https://doi.org/10.1029/2020JE006406

Onodera, K., Kawamura, T., Tanaka, S., Ishihara, Y., & Maeda, T. (2022). Quantitative evaluation of lunar seismic scattering and comparison between the Earth, Mars, and the Moon. Journal of Geophysical Research: Planets, 127, e2022JE007558. https://doi.org/10.1029/2022JE007558

Pienkowska, M., Nippress, S. E. J., Bowers, D., & Nissen-Meyer, T. (2025). Ringing mountain ranges: Teleseismic signature of the interaction of high-frequency wavefields with near-source topography at the Degelen nuclear test site. Geophysical Journal International, 240, 621-637.

Pitarka, A., & Irikura, K. (1996). Modeling 3D surface topography by finite-difference method: Kobe-JMA station site, Japan, case study. Geophysical Research Letters, 23, 2729-2732. https://doi.org/10.1029/96GL02493

Rodgers, A. J., Petersson, N. A., & Sjogreen, B. (2010). Simulation of topographic effects on seismic waves from shallow explosions near the North Korean nuclear test site with emphasis on shear wave generation. Journal of Geophysical Research: Solid Earth, 115, B11309. https://doi.org/10.1029/2010JB007707

Wang, W., Zhang, Z., Zhang, W., Yu, H., Liu, Q., Zhang, W., & Chen, X. (2022). CGFDM3D-EQR: A platform for rapid response to earthquake disasters in 3D complex media. Seismological Research Letters, 93, 2320-2334. https://doi.org/10.1785/0220210309

Wieczorek, M. A., et al. (2013). The crust of the Moon as seen by GRAIL. Science, 339, 671-675. https://doi.org/10.1126/science.1231530

Zhang, W., & Chen, X. (2006). Traction image method for irregular free surface boundaries in finite difference seismic wave simulation. Geophysical Journal International, 167, 337-353. https://doi.org/10.1111/j.1365-246X.2006.03113.x

Zhang, W., Zhang, Z., & Chen, X. (2012). Three-dimensional elastic wave numerical modelling in the presence of surface topography by a collocated-grid finite-difference method on curvilinear grids. Geophysical Journal International, 190, 358-378. https://doi.org/10.1111/j.1365-246X.2012.05472.x

Zheng, K., Wang, Y., & Zhao, L. (2024). Topography effect on seismic waveform tomography: A quantitative study. Geophysical Journal International, 237, 302-314.

## Figure Captions

Figure 1. A16/S12 base model geometry and receiver-profile design. The plotted design panel shows the M1–M4 factorial nodes; the M5/M6 low-velocity nodes are added on the same geometry and are shown explicitly in Figure 8. The first and last five receivers on each profile are excluded from primary spatial inference. Relief profiles are geometric sampling proxies and should not be interpreted as three-dimensional ray paths.

Figure 2. Three-component baseline waveforms along the three receiver profiles. Traces are rotated to vertical, radial, and transverse components and filtered from 0.3 to 0.9 Hz. Shared scales within each panel preserve the relative changes among M1-M4; the all-six ladder is summarized in Figure 8.

Figure 3. Vertical, radial, and transverse energy fractions for 575 primary receivers. The baseline panels show M1-M4; Figure 8 and the Supporting Information extend the same component accounting through M5/M6. Transverse energy is near zero in M1 and increases along the full ladder. Fractions describe redistribution among components, not intrinsic absorption.

Figure 4. Distance-controlled relations between cumulative path relief and topography-only waveform effects. Predictors and responses were cubic-detrended and standardized within each receiver profile; points are nonoverlapping 10-station block means. Profiles 2 and 3 show lower peak amplitude and total energy and longer T90 with increasing relief, whereas profile 1 does not support the same generalization.

Figure 5. Three-component factorial interaction residuals at station S12. The residual I=M4-M2-M3+M1 isolates nonadditivity between topography and heterogeneity. The residual is compared with the two isolated main effects using common component scales. A nonzero residual demonstrates interaction but does not uniquely identify its physical mechanism.

Figure 6. Energy-peak time versus epicentral distance for all three profiles and the four baseline models. Each panel compares a linear-distance fit with a squared-distance diffusion-form fit. Figure 9 extends the same diagnostic to M1-M6.

Figure 7. Apollo 16 impact observation at station S12 compared with the four baseline synthetics. A single three-component root-mean-square source scale is applied to each model. The six-state observation comparison is provided in Figure 10.

Figure 8. Unified A16/S12 M1–M6 model ladder. Panels show median energy and T90 ratios to M1, median tmax and t95 with Apollo reference times, Z/R/T energy fractions, and peak amplitude. M5/M6 are conditional low-velocity states on heterogeneous backgrounds, not independent low-velocity-only controls.

Figure 9. Peak-energy time versus distance for all six A16/S12 states and three profiles. M5/M6 have larger slopes and scatter than M1-M4, but the peak-energy ridge remains distance-structured rather than a simple squared-distance diffusion law.

Figure 10. Apollo S12 envelope comparison for M1-M6. The low-velocity states move the early energy envelope toward the observation but remain far too early and too short in cumulative duration.
