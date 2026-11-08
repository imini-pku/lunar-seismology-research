# A16/S12 terrain restoration — 9 September 2026

The user confirmed the pre-orientation-fix Path 2 profile, including its deep depression at approximately 75–110 km, and requested restoration. This decision supersedes the prior plotting interpretation for A16/S12.

The following active derived tables were restored byte-for-byte from the `before_orientation_fix` files in `投稿文件/地形读取复查_2026-09-07`: station_level_metrics, path_profile_samples, distance_controlled_relationships, factorial_effect_summary_by_ray, and robustness_sensitivity.

The replaced tables and the previous Figure 6 builder were backed up in `数据图表/绘图数据/TerrainRestore_Backup_20260909_162026`. Original figure versions are retained. The latest Figure 6 is v05, with an independent restored-terrain Path 2 diagnostic v02. The builder `17_Fig06_CompactEvolution_Path2Audit_v04.py` now emits these restored versions directly from the archive.

This operation restores the archived analysis; it does not independently validate the simulation surface mesh. Before any future terrain recomputation, verify the original model grid and its coordinate convention. Do not overwrite the restored tables by rerunning the previously rejected raw[x,y] sampling pipeline. The half-space datasets and waveform simulations were not changed by this restoration.
