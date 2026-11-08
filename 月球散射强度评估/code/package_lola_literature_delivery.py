"""Package the reviewed report, native LOLA crop and observed Apollo records."""
from pathlib import Path
import csv
import hashlib
import json
import re
import zipfile
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/地形与文献模型修订_20261029'
OUT.mkdir(parents=True, exist_ok=True)
MAIN = ROOT / 'docs/12_LOLA地形底图与散射模型文献依据.md'

def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def rows(rel):
    with (ROOT / rel).open(encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

selected = set()
def include(p):
    p = p.resolve()
    assert p.is_relative_to(ROOT), p
    assert p.exists(), p
    if p.is_dir():
        for q in p.rglob('*'):
            if q.is_file() and '__pycache__' not in q.parts:
                selected.add(q)
    else:
        selected.add(p)

for rel in [
    'docs/12_LOLA地形底图与散射模型文献依据.md',
    'docs/scattering_references.bib', 'docs/expanded_lunar_references.bib',
    'docs/recent_lunar_references.bib',
    'reports/expanded_lunar_literature.md', 'reports/model_choice_provenance_audit.md',
    'reports/recent_literature_root.md', 'reports/instrument_band_audit.md',
    'reports/impact_literature_audit.md',
    'config/scattering_model_design_v2_annotated.json',
    'results/model_choice_provenance.csv', 'results/model_family_sources.csv',
    'results/literature_expansion_records.json', 'results/recent_reference_metadata.json',
    'results/literature_metadata_expanded', 'data/raw/literature_metadata_expansion',
    'results/impact_audit', 'results/impact_terrain',
    'figures/impact_terrain', 'figures/impact_audit',
    'data/raw/impact_waveforms_darts', 'data/raw/impact_modern',
    'data/raw/impact_metadata', 'data/processed/impact_reference',
    'data/raw/lola_impact_64/ldem_64_W38_E40_S18_N40_native.npz',
    'data/raw/lola_impact_64/ldem_64.lbl', 'data/raw/lola_impact_64/README.md',
    'code/plot_impact_lola_terrain.py', 'code/build_impact_geometry_audit.py',
    'code/audit_impact_waveforms_darts.py', 'code/audit_modern_impact_records.py',
    'code/plot_impact_representative_records.py', 'code/plot_modern_impact_audit.py',
    'code/package_lola_literature_delivery.py', 'requirements_impact.txt',
]:
    include(ROOT / rel)
for p in (ROOT / 'results').glob('impact_*.csv'):
    include(p)
for p in (ROOT / 'results').glob('impact_*.json'):
    include(p)

# Follow local Markdown dependencies, including directory links.
checked = set()
links_checked = 0
while True:
    pending = [p for p in selected if p.suffix == '.md' and p not in checked]
    if not pending:
        break
    for p in pending:
        checked.add(p)
        for raw in re.findall(r'\]\(([^)]+)\)', p.read_text(encoding='utf-8-sig')):
            target = raw.strip().strip('<>')
            if target.startswith(('https:', 'http:', 'mailto:', '#')):
                continue
            target = unquote(target.split('#')[0])
            if not target:
                continue
            include(p.parent / target)
            links_checked += 1

assert '<!--' not in MAIN.read_text(encoding='utf-8')
events = rows('results/impact_audit/events_and_domains.csv')
pairs = rows('results/impact_pairs_literature.csv')
families = rows('results/model_family_sources.csv')
choices = rows('results/model_choice_provenance.csv')
assert len(events) == 9 and len(pairs) == 21
assert len(families) == 10 and len(choices) == 36
assert len({r['choice_id'] for r in choices}) == 36
assert all(r['source'] and r['classification'] for r in families)
assert all(r['source_doi_or_url'] and r['evidence_class'] for r in choices)
assert len(list((ROOT / 'figures/impact_terrain').glob('*.png'))) == 20
assert len(list((ROOT / 'figures/impact_terrain').glob('*.pdf'))) == 20
provenance = json.loads((ROOT / 'results/impact_terrain/lola_data_provenance.json').read_text(encoding='utf-8'))
crop = ROOT / 'data/raw/lola_impact_64/ldem_64_W38_E40_S18_N40_native.npz'
assert digest(crop) == provenance['crop_sha256']
assert digest(ROOT / 'data/raw/lola_impact_64/ldem_64.lbl') == provenance['label_sha256']
assert len(list((ROOT / 'data/raw/impact_modern').glob('*.mseed'))) == 21
assert len(list((ROOT / 'data/processed/impact_reference').glob('*.npz'))) == 60
for r in rows('results/impact_waveform_inventory.csv'):
    assert digest(ROOT / r['sac_path']) == r['sha256_sac']
for r in json.loads((ROOT / 'results/impact_modern_download_log.json').read_text(encoding='utf-8')):
    assert digest(ROOT / r['file']) == r['sha256']

readme = '''# Apollo地形与散射模型：详细报告资料包

更新：2026-10-29。本次以Markdown为正式交付；旧PPT未同步更新，也未收入本包。

## 阅读顺序

1. **主报告：[LOLA地形底图、散射模型依据与模拟设计](docs/12_LOLA地形底图与散射模型文献依据.md)**。先看第2—4节的事件、台站和记录，再看第5—7节的参数与文献，最后看模拟流程和逐事件图册。
2. [21对观测综合表](results/impact_audit/combined_event_station_audit.csv)和[逐记录频带表](results/impact_audit/modern_band_by_pair.csv)。
3. [36项模型选择来源](results/model_choice_provenance.csv)、[10类模型分支](results/model_family_sources.csv)、[带来源的设计配置](config/scattering_model_design_v2_annotated.json)。
4. [扩展文献核查](reports/expanded_lunar_literature.md)、[近期研究核查](reports/recent_literature_root.md)、[逐项选择审计](reports/model_choice_provenance_audit.md)。

## 主要数据与状态

- 9次人工撞击、21个实际源—站配对：文献分类16对清晰、5对低信噪比；8个近距候选域包含11条路径。
- 20组LOLA地形PNG/PDF，包括总图、九事件分图和八近距域；原生采样64像素/度，南北间距约474 m。
- 81个JAXA SAC及压缩原件、21个EarthScope MiniSEED、60条名义响应校正NPZ预览与元数据。正式可反演频带仍待逐时增益和异常核验；自动初筛通过不能直接作为准入。
- 0.3—0.5 Hz是首轮公共试验频带。更宽频带须逐事件、分量和时间窗验证。
- 文献原值、模型迁移假设与本项目试验值分别标注。最大扰动、RMS、相关尺度和散射平均自由程不混用。
- **新增CGFD3D波场运行数为0**。目前交付模型设计及数据审计，没有声称找到区域最优模型。收到运行配置后先验证介质、网格、稳定性与边界，再开展观测比较。

## 地形数据与复现

`data/raw/lola_impact_64/`包含官方标签和3712×4992原生裁片；`results/impact_terrain/`包含来源、HTTP分块、SHA-256、坐标和图件校验记录。源条带171 MB保留在项目工作区，不重复收入本包；所有图件可直接使用包内裁片复现，无需下载该条带。

在解压后的根目录安装`requirements_impact.txt`所列依赖后，执行：

```text
python code/plot_impact_lola_terrain.py --plot-only
```

图中的50 km缓冲和400 km候选阈值是规划参数，并未证明晚时尾波或平面近似收敛。地形色标是相对参考球面的高程，不能直接当作地质类别或地下散射强度。

## 版本与校验

本包保留`docs/10`、`docs/11`作为观测与设计补充，最新模型依据以`docs/12`和v2配置为准。`figures/impact_audit/`用于原始波形与历史几何审计；正式地形图均在`figures/impact_terrain/`。不含旧PPT、旧材料NetCDF预览、过期DEM或完整历史项目。

`manifest_sha256.csv`列出所有内容文件的大小和SHA-256。`reports/lola_literature_delivery_validation.json`记录数量、链接、原始记录哈希和地形数据校验。本包可解压后整体保存；请保持相对目录结构，以便Markdown图片和数据链接正常打开。
'''
(OUT / '阅读说明.md').write_text(readme.replace('](docs/', '](../../docs/').replace('](results/', '](../../results/').replace('](reports/', '](../../reports/').replace('](config/', '](../../config/'), encoding='utf-8')
qa = {
    'date': '2026-10-29', 'events': 9, 'recorded_pairs': 21,
    'literature_clear_pairs': 16, 'literature_low_SNR_pairs': 5,
    'terrain_PNG': 20, 'terrain_PDF': 20,
    'model_families_with_sources': 10, 'model_choices_with_sources': 36,
    'local_Markdown_links_resolved': links_checked, 'checked_Markdown_files': len(checked),
    'native_LOLA_crop_sha256_verified': True, 'official_label_sha256_verified': True,
    'legacy_SAC_sha256_verified': 81, 'modern_MiniSEED_sha256_verified': 21,
    'modern_processed_NPZ_included': 60, 'new_CGFD3D_wave_runs': 0,
    'formal_band_qualification_pending': True,
    'terrain_figures_visually_inspected': ['overview', 'nine-event montage', 'eight-local-domain montage', 'A12LM', 'A14LM', 'A15LM', 'A17LM'],
    'excluded_large_duplicate': '171 MB full-longitude strip; native crop included for offline plotting',
    'PPT_updated_this_revision': False,
}
qpath = ROOT / 'reports/lola_literature_delivery_validation.json'
qpath.write_text(json.dumps(qa, indent=2, ensure_ascii=False), encoding='utf-8')
include(qpath)
manifest = OUT / 'manifest_sha256.csv'
with manifest.open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['path', 'bytes', 'sha256'])
    w.writerow(['README.md', len(readme.encode('utf-8')), hashlib.sha256(readme.encode('utf-8')).hexdigest()])
    for p in sorted(selected):
        w.writerow([p.relative_to(ROOT).as_posix(), p.stat().st_size, digest(p)])
archive = OUT / 'Apollo地形与散射模型_详实报告资料包.zip'
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    z.writestr('README.md', readme)
    for p in sorted(selected):
        z.write(p, p.relative_to(ROOT).as_posix())
    z.write(manifest, 'manifest_sha256.csv')
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for r in csv.DictReader(manifest.open(encoding='utf-8-sig')):
        b = z.read(r['path'])
        assert len(b) == int(r['bytes']) and hashlib.sha256(b).hexdigest() == r['sha256']
result = {'archive': archive.name, 'archive_bytes': archive.stat().st_size,
          'archive_sha256': digest(archive), 'content_files': len(selected) + 1,
          'zip_crc_passed': True, 'all_manifest_hashes_verified_from_zip': True,
          'local_Markdown_links_resolved': links_checked}
(OUT / 'package_validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
