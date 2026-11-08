"""Validate and package the event-led Apollo audit; no wave propagation is run."""
from pathlib import Path
import csv, json, hashlib, zipfile, shutil, importlib.metadata
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/撞击记录与散射建模_20261029'
OUT.mkdir(parents=True, exist_ok=True)
def rows(rel):
    return list(csv.DictReader((ROOT/rel).open(encoding='utf-8-sig')))
events = rows('results/impact_audit/events_and_domains.csv')
pairs = rows('results/impact_pairs_literature.csv')
stations = {r['station']:r for r in rows('results/impact_audit/stations.csv')}
domains = rows('results/impact_audit/event_station_domains.csv')
local = rows('results/impact_audit/local_simulation_candidates.csv')
legacy = rows('results/impact_waveform_inventory.csv')
modern = rows('results/impact_modern_trace_audit.csv')
bands = rows('results/impact_modern_band_screen.csv')
summary = json.loads((ROOT/'results/impact_modern_summary.json').read_text(encoding='utf-8'))
assert len(events)==9 and len(pairs)==len(domains)==21
assert sum(r['nunn2024_clear'].lower()=='true' for r in pairs)==16
assert len(local)==8 and sum(len(r['receivers'].replace(';',',').split(',')) for r in local)==11
assert len(legacy)==81 and len(modern)==63 and len(bands)==240
assert summary['processed_trace_files']==60 and summary['provisional_pass_rows']==30
assert summary['qualified_band_count']==0 and summary['ATT_corrected_trace_count']==60
event_lookup = {r['event_id']:r for r in events}
for d in domains:
    for p in [event_lookup[d['event_id']], stations[d['station']]]:
        assert float(d['west_degE']) <= float(p['lon']) <= float(d['east_degE'])
        assert float(d['south_degN']) <= float(p['lat']) <= float(d['north_degN'])
for r in legacy:
    p=ROOT/r['sac_path']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256_sac']
    assert p.stat().st_size == 632 + 4*int(r['npts'])
    z=p.parent/r['filename']
    assert hashlib.sha256(z.read_bytes()).hexdigest()==r['sha256_compressed']
for r in modern:
    assert not r['qualified_band']
    if r['npz']:
        with np.load(ROOT/r['npz']) as d:
            assert len(d['t'])==len(d['velocity_m_s'])==len(d['original_gap_mask'])
            assert np.all(np.diff(d['t'])>0)
            assert np.all(np.isnan(d['velocity_m_s'][d['original_gap_mask'].astype(bool)]))
        assert r['clock_status']=='local_affine_ATT_corrected'
    else:
        assert r['status']=='known_bad_channel_epoch'
for r in json.loads((ROOT/'results/impact_modern_download_log.json').read_text(encoding='utf-8')):
    assert hashlib.sha256((ROOT/r['file']).read_bytes()).hexdigest()==r['sha256']

notes = json.loads((ROOT/'.build/presentation/impact_revision/slide_notes.json').read_text(encoding='utf-8'))
(OUT/'组会讲解备注.md').write_text('# Apollo 撞击记录与散射建模：逐页讲解备注\n\n'+'\n\n'.join(f"## {r['slide']:02d} {r['title']}\n\n{r['note']}" for r in notes),encoding='utf-8')
readme = '''# Apollo 撞击记录与散射建模资料包

更新：2026-10-29。研究入口按“撞击事件 → 实际接收台站 → 记录 → 频带 → 模拟范围 → 散射模型”组织。

## 先看什么

1. 本目录的24页组会PPT和《组会讲解备注.md》。前半部分逐事件展示位置、范围和真实记录。
2. `docs/10_撞击事件台站与模拟域审计.md`：九事件、21个配对的总审计与逐事件索引。
3. `docs/11_按撞击路径约束的散射模型设计.md`：文献约束、三个参数的定义、源与场地控制、分阶段模型检验。
4. `figures/impact_audit/impact_station_overview.png`：全部撞击和接收台站。
5. `figures/impact_audit/nine_event_simulation_domains.png`：九事件全部记录覆盖框；`local_candidate_simulation_domains.png`：八事件11条近距候选路径的范围框。后者含50 km规划缓冲，尚未验证吸收边界和晚时尾波收敛。
6. `results/impact_audit/combined_event_station_audit.csv`：逐配对距离、分量和记录索引；`modern_band_by_pair.csv`：逐配对频带筛查。

## 数据在哪里

- `data/raw/impact_waveforms_darts/`：81个JAXA压缩原件和81个解压SAC。旧档案物理单位和完整处理历史未重新认证；不对它们盲目重复去响应。
- `data/raw/impact_modern/`：21个EarthScope MiniSEED，含中周期MP与ATT，窗口为地面接收源时刻前600秒至后3600秒。
- `data/raw/impact_metadata/`：PDS名义StationXML、通道时段、仪器说明和增益/模式相关日志。完整逐时增益重建仍待核验。
- `data/processed/impact_reference/`：60条名义响应校正速度预览，NPZ中有`t`、`velocity_m_s`、`raw_counts`、`original_gap_mask`和`metadata`。t以NASA地面接收源时刻为零；缺口保留为NaN。未重复减去月地传播的约1.3秒。
- `results/impact_modern_trace_audit.csv`：63条候选MP分量中，3条1972年S14坏MHZ被排除，其余60条完成名义响应和局部ATT时钟检查。
- `results/impact_modern_band_screen.csv`：240个“分量×子频带”筛查，30项通过当前初筛；这不是30个独立事件。`qualified_band`尚为空，表示正式反演还需增益和异常核验，不能解释为没有有效观测。
- `figures/impact_audit/*_modern_records.png`：逐事件代表性记录，0.3–0.9 Hz用于展示，逐道归一化，不用于直接比较绝对振幅。
- `results/scattering_models/`：前阶段三份材料预览。它们不是已验证CGFD3D生产输入；`config/scattering_run_manifest.csv`的88项只是两条S12参考路径的候选试验，不是全区域计算结果。

## 频带和参数的使用边界

首轮公共比较采用0.3–0.5 Hz；0.3–0.9 Hz来自撞击记录的总体文献经验，实际可用带宽必须按事件、分量和时间窗确认。0.3–1.5 Hz有两条S12路径的文献先例，不能直接授权所有台站。S12短周期通道故障、1972年S14垂直通道故障均已单列。

散射起点采用Onodera 2022三维指数相关模型的a≈0.65 km、生成速度场标准差约5%–10%、强扰动至约10 km。首轮a=0.30/0.65/1.30 km、σv=5/10/15%、H=3.5/10/20 km是本项目试验设计。二维文献的最大扰动和三维RMS不能直接互换；Nunn节点±50%不是σv=50%。S14/S15的起点是待验证迁移假设；S16目前主要用于远距预测验证。

## 如何复核

`code/`保留数据审计、几何、制图和材料生成脚本。Python主要依赖见`requirements_impact.txt`；本资料包不包含本机依赖缓存。下载记录、SHA256和来源URL保留在`results/`及元数据目录。脚本以项目根目录为基准。`compile_impact_audit_report.py`只生成基础报告，直接重跑会覆盖已补充的现代档案段落；修改报告前保留当前版本。

已核对原始文件SHA256、SAC字节数、源站是否在框内、配对数量和处理结果中的缺口；PPT通过结构检查，并逐页查看24张渲染图。未通过本机PowerPoint再次排版核验。

新的CGFD3D传播计算尚未运行。收到真实运行配置后，先做输入和域收敛，再比较观测和合成波形；当前不宣称获得了区域最优模型。
'''
(OUT/'阅读说明.md').write_text(readme,encoding='utf-8')
(ROOT/'requirements_impact.txt').write_text('numpy\nscipy\nmatplotlib\npandas\nrequests\nobspy\nunlzw3\nnetCDF4\n',encoding='utf-8')
qa = dict(date='2026-10-29', events=9, recorded_pairs=21, literature_clear_pairs=16,
          literature_low_SNR_pairs=5, local_event_domains=8, local_candidate_pairs=11,
          legacy_SAC_files=81, legacy_compressed_files=81, modern_raw_pairs=21,
          modern_processed_traces=60, excluded_bad_S14_MHZ=3, band_screen_rows=240,
          provisional_pass_rows=30, certified_band_rows=0, source_station_inside_boxes=True,
          waveform_hashes_verified=True, missing_samples_remain_NaN=True,
          PPT_rendered_slides_inspected=list(range(1,25)), native_PowerPoint_verified=False,
          new_CGFD3D_wave_propagation_runs=0)
(ROOT/'reports/impact_delivery_validation.json').write_text(json.dumps(qa,indent=2),encoding='utf-8')
shutil.copy2(ROOT/'.build/presentation/impact_revision/validation.json',OUT/'PPT结构验证.json')
shutil.copy2(ROOT/'reports/impact_delivery_validation.json',OUT/'交付完整性验证.json')

selected = set()
def add(p):
    if p.is_file(): selected.add(p)
    elif p.is_dir(): selected.update(q for q in p.rglob('*') if q.is_file())
for rel in ['docs/10_撞击事件台站与模拟域审计.md','docs/11_按撞击路径约束的散射模型设计.md','docs/08_区域散射参考模型与参数范围.md','docs/09_CGFD3D散射建模与波形筛选方案.md','docs/scattering_references.bib','results/impact_audit','results/scattering_models','figures/impact_audit','data/raw/impact_waveforms_darts','data/raw/impact_modern','data/raw/impact_metadata','data/processed/impact_reference','requirements_impact.txt']:
    add(ROOT/rel)
for pattern in ['results/impact*.*','reports/impact*.*','reports/instrument_band_agent.md','code/*impact*.py','code/build_scattering_models.py','code/validate_and_plot_model_design.py','config/scattering*']:
    for p in ROOT.glob(pattern): add(p)
for p in OUT.iterdir():
    if p.is_file() and p.suffix.lower()!='.zip': add(p)
manifest = [dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(selected)]
mp=OUT/'文件清单_SHA256.json'
mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
selected.add(mp)
archive = OUT/'Apollo撞击记录与模型审计_资料包_20261029.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(selected): z.write(p,p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(selected)
print(json.dumps(dict(validation=qa,archive=str(archive),files=len(selected),archive_bytes=archive.stat().st_size),ensure_ascii=False,indent=2))
