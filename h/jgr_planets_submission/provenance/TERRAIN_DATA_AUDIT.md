# Terrain-data reading convention

**Status:** verified  
**Verification date:** 2026-09-07  
**Primary reference:** `D:\software\CGFD3D_v26.03\revise\usefiles\newfigure6_part3_1.m`

## Canonical rule

The CGFD3D terrain text files are not image arrays with the conventional NumPy `[y, x]` order. Let `A = load(file)` be the raw two-dimensional text matrix. The reference MATLAB code performs:

```matlab
dem = A';
dem = dem(:);
elev = dem(sub2ind([ny,nx], y_idx, x_idx));
```

For the square grids used by this project, this is equivalent to selecting:

```python
elevation = raw[x_index, y_index]
```

Thus the project convention is:

- first matrix dimension: `x`;
- second matrix dimension: `y`;
- MATLAB index calculation: `round(coordinate_km / domain_km * (n - 1)) + 1`;
- Python conversion: zero-based indices after applying the same nearest-node rule;
- for the positive coordinates used here, `floor(value + 0.5)` reproduces MATLAB `round`.

## Scope

This convention applies to all terrain-derived quantities, including point elevation, slope components, path profiles, cumulative relief, roughness, depression candidates, and terrain-effect correlations. It applies to both the 100 km half-space grids and the 300 km A16/S12 grid.

The audited half-space profile in `newfigure6_part3_1.m` uses nearest-grid sampling. Bilinear interpolation may be used only in explicitly labeled A16 path-profile diagnostics, and must still use the same `x`-first/`y`-second orientation.

## Data sources

- Half-space terrain: `D:\software\CGFD3D_v26.03\revise\prep_medium\new2_Z_4000_topo.txt` and its resolution variants.
- A16/S12 terrain: `D:\software\CGFD3D_v26.03\revise\prep_medium\rel3_Z_300_1500_topo.txt` and the packaged copy `data/raw/rel3_Z_300_1500_topo.txt`.
- The packaged A16/S12 terrain file and the external file were verified to have identical SHA-256: `B440E5C59BF27E925D398BBA65F0BA2CAE9BE349CAA517B4086B3622D37FCF9C`.

## Code locations

- `code/verified_legacy/plot_releasy_waveform_comparison.py`: common A16/S12 point sampler;
- `code/verified_legacy/generate_path_based_ray_analysis.py`: A16/S12 path-profile sampler;
- `code/analyze_halfspace_models.py`: half-space grid orientation, map display, center profile, and slope axes;
- `投稿文件/新数据陨石坑跨越分析_2026-09-06/analyze_crater_crossings.py`: audited 800-station half-space profile sampler.

The old orientation-sensitive derived tables were retained alongside corrected tables in `投稿文件/地形读取复查_2026-09-07/` for comparison. The corrected tables in `data/derived/` are the active project inputs.

