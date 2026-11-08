"""Assemble the raw-first waveform report and a verifiable focused data package."""
from pathlib import Path
import csv
import hashlib
import json
import re
import zipfile
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/原始与处理波形对照_20261029'
OUT.mkdir(parents=True, exist_ok=True)
DOC = ROOT / 'docs/13_原始波形与处理对照.md'

def readcsv(rel):
    with (ROOT / rel).open(encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

events = readcsv('results/impact_audit/events_and_domains.csv')
pairs = readcsv('results/impact_pairs_literature.csv')
traces = readcsv('results/waveform_comparison/trace_stage_comparison.csv')
summary = json.loads((ROOT / 'results/waveform_comparison/summary.json').read_text(encoding='utf-8'))
assert len(events) == 9 and len(pairs) == 21 and len(traces) == 63
assert summary['processed_trace_count'] == 60
assert summary['all_raw_counts_match_archive'] and summary['all_time_axes_verified']

raw, processed = [], []
for e in events:
    eid = e['event_id']
    stations = e['recorded_stations'].replace(';', '、')
    raw.append(f"### {eid}：原始档案\n\n源时刻（地面接收）：{e['time_earth_received']}；有记录台站：{stations}。\n\n![{eid}原始三分量数字计数，名义时间轴](../figures/waveform_comparison/{eid}_raw_archive_overview.png)\n\n[原始图PDF](../figures/waveform_comparison/{eid}_raw_archive_overview.pdf)\n")
    processed.append(f"### {eid}：响应校正与带通后\n\n![{eid}名义响应校正后0.3至0.9Hz三分量速度，ATT时间轴](../figures/waveform_comparison/{eid}_processed_03_09_overview.png)\n\n[速度图PDF](../figures/waveform_comparison/{eid}_processed_03_09_overview.pdf)；[文献窄带位移参照：0.3–0.5 Hz](../figures/waveform_comparison/{eid}_literature_displacement_03_05_overview.png)（[PDF](../figures/waveform_comparison/{eid}_literature_displacement_03_05_overview.pdf)）。\n")

pairlines = ['| 事件 | 台站 | 震中距/km（文献） | 三阶段图 | 原始文件 |', '|---|---|---:|---|---|']
for p in pairs:
    eid, station = p['event_id'], p['station']
    pairlines.append(f"| {eid} | {station} | {float(p['distance_published_km']):.1f} | [PNG](../figures/waveform_comparison/{eid}_{station}_three_stages.png) / [PDF](../figures/waveform_comparison/{eid}_{station}_three_stages.pdf) | [MiniSEED](../data/raw/impact_modern/{eid}_{station}_MP_ATT.mseed) |")

gap = '''### 两个缺口放大实例

下图用于区分真正缺样与处理影响。没有曲线的原始缺样仍然保留；橙色处理值被显示出来，是为了检查边缘行为，不代表缺测被恢复为观测。

![A15LM S15 MHZ晚尾波缺口的原始与处理对照](../figures/waveform_comparison/A15LM_S15_MHZ_gap_zoom.png)

![A14SIVB S12 MHZ早期窗口的原始与处理对照](../figures/waveform_comparison/A14SIVB_S12_MHZ_gap_zoom.png)

### 代表性分量的覆盖率对照

下表分母为ATT展示窗（−300至3600秒）内返回的样点数，不是完整日记录。旧显示空白含原始缺样和旧处理排除；新显示空白仍包括缺样及未计算短段。橙色影响区即使有数值，也未正式认证。

| 记录 | 原始缺样 | 旧图空白 | 新图空白 | 新图橙色影响区 | 短段未处理 |
|---|---:|---:|---:|---:|---:|
'''
for key in [('A14SIVB','S12','MHZ'), ('A15LM','S15','MHZ'), ('A17SIVB','S14','MH1')]:
    r = next(r for r in traces if (r['event_id'], r['station'], r['channel']) == key)
    cells = [f"{100*float(r[k]):.2f}%" for k in ['raw_gap_fraction','old_display_blank_fraction','new_display_blank_fraction','new_processing_edge_fraction','short_unprocessed_fraction']]
    gap += '| ' + ' / '.join(key) + ' | ' + ' | '.join(cells) + ' |\n'
gap += '\n完整63个分量位置的状态见[逐道阶段审计](../results/waveform_comparison/trace_stage_comparison.csv)。3个缺失位置不计入60条已取得记录。\n'

outputs = f'''- [原始档案](../data/raw/impact_modern/)：21个MiniSEED，保留哈希记录。
- [本轮分阶段数据](../data/processed/waveform_comparison_v2/)：60个NPZ，分别保存名义/ATT时间、原始计数、响应后速度、两种带通速度、窄带位移及全部掩码。
- [阶段审计表](../results/waveform_comparison/trace_stage_comparison.csv)、[连续段日志](../results/waveform_comparison/segment_processing_log.json)、[汇总](../results/waveform_comparison/summary.json)。
- [图件清单](../results/waveform_comparison/figure_manifest.json)：50组PNG/PDF，包括9幅原始总览、9幅速度总览、9幅位移参照、21幅三阶段图和2幅局部诊断。
- [8条文献/代码来源](../results/waveform_processing_sources.json)、[新增清洗论文BibTeX](waveform_cleaning_reference.bib)。
- [独立原始数据核验](../results/waveform_raw_integrity_audit.json)。

本轮计算成功的连续段为{summary['total_successful_segments']}段；{summary['total_short_segments']}段因不足60秒保留原始记录但不作响应计算。速度链失败{summary['total_failed_segments']}段，位移支路状态另见汇总与段日志。这是处理执行状态，不能等同于物理模型或绝对幅值通过验证。

复现所需依赖见[requirements_impact.txt](../requirements_impact.txt)。在项目根目录运行：

```text
python code/build_waveform_stage_comparison.py
```

只重绘已有结果可加`--plot-only`；只处理数据可加`--process-only`。原始输入和此前预览文件保持独立，新结果不会覆盖旧NPZ。原始数值、缺样掩码、时间映射和处理状态均可以逐道追踪。
'''
text = DOC.read_text(encoding='utf-8')
for marker, value in [('RAW_GALLERY','\n'.join(raw)), ('PROCESSED_GALLERY','\n'.join(processed)), ('PAIR_TABLE','\n'.join(pairlines)), ('GAP_EXAMPLES',gap), ('OUTPUT_INDEX',outputs)]:
    text = text.replace(f'<!-- {marker} -->', value)
assert '<!--' not in text
DOC.write_text(text, encoding='utf-8')

selected = set()
def include(path):
    path = path.resolve()
    assert path.is_relative_to(ROOT) and path.exists(), path
    if path.is_dir():
        selected.update(x for x in path.rglob('*') if x.is_file() and '__pycache__' not in x.parts)
    else:
        selected.add(path)

for rel in ['docs/13_原始波形与处理对照.md', 'docs/waveform_cleaning_reference.bib',
            'reports/waveform_processing_literature_review.md',
            'reports/waveform_cleaning_citation_validation.json',
            'results/waveform_processing_sources.json', 'results/waveform_raw_integrity_audit.json',
            'results/waveform_comparison', 'figures/waveform_comparison',
            'data/processed/waveform_comparison_v2', 'data/processed/impact_reference',
            'data/raw/impact_modern', 'data/raw/impact_metadata',
            'data/raw/literature_metadata_expansion/2025EA004710.json',
            'results/impact_audit/events_and_domains.csv', 'results/impact_pairs_literature.csv',
            'results/impact_modern_trace_audit.csv', 'results/impact_modern_download_log.json',
            'code/build_waveform_stage_comparison.py', 'code/finalize_waveform_comparison_delivery.py',
            'requirements_impact.txt']:
    include(ROOT / rel)

seen = set()
links = 0
while True:
    pending = [p for p in selected if p.suffix == '.md' and p not in seen]
    if not pending: break
    for p in pending:
        seen.add(p)
        for target in re.findall(r'\]\(([^)]+)\)', p.read_text(encoding='utf-8-sig')):
            target = unquote(target.strip().strip('<>').split('#')[0])
            if not target or target.startswith(('https:', 'http:', 'mailto:')): continue
            include(p.parent / target)
            links += 1

pngs = list((ROOT / 'figures/waveform_comparison').glob('*.png'))
pdfs = list((ROOT / 'figures/waveform_comparison').glob('*.pdf'))
assert len(pngs) == 50 and len(pdfs) == 50, (len(pngs),len(pdfs))
assert len(list((ROOT/'data/processed/waveform_comparison_v2').glob('*.npz'))) == 60
readme = '''# Apollo原始与处理波形对照资料包

更新：2026-10-29。请先打开 **[主报告](docs/13_原始波形与处理对照.md)**，依次查看原始波形、处理总览和同一时间轴上的三阶段对照。

- 9次人工撞击、21个事件—台站配对、60条实际分量记录；3个S14 MHZ未由原始档案返回。
- 50组PNG/PDF：全部原始三分量、速度总览、文献窄带位移参照、逐配对三阶段图及缺口放大。
- 原始数字计数逐点核对，无峰值归一化；灰色为真实缺样，橙色为待验证的处理影响区。
- 包含21个原始MiniSEED、60个新阶段NPZ、此前60个参考NPZ（供时标和历史处理对照）、响应元数据、审计表和处理代码。
- 新数据只是可追溯检查结果，尚未完成增益认证、自动去glitch或反演频带准入；没有新的CGFD3D合成波形。

保持解压后的目录结构。主报告中的图片与数据链接采用相对路径，原始MiniSEED可用ObsPy等地震数据软件读取。

复现依赖见`requirements_impact.txt`；运行`python code/build_waveform_stage_comparison.py`。文献来源和未核验事项在报告中逐项列出。`manifest_sha256.csv`为逐文件校验清单。
'''
(OUT/'阅读说明.md').write_text(readme.replace('](docs/','](../../docs/'), encoding='utf-8')
manifest = OUT / 'manifest_sha256.csv'
with manifest.open('w', newline='', encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['path','bytes','sha256'])
    w.writerow(['README.md',len(readme.encode('utf-8')),hashlib.sha256(readme.encode('utf-8')).hexdigest()])
    for p in sorted(selected): w.writerow([p.relative_to(ROOT).as_posix(),p.stat().st_size,sha(p)])
archive=OUT/'Apollo原始波形与处理对照_资料包.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    z.writestr('README.md',readme)
    for p in sorted(selected):z.write(p,p.relative_to(ROOT).as_posix())
    z.write(manifest,'manifest_sha256.csv')
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for r in csv.DictReader(manifest.open(encoding='utf-8-sig')):
        b=z.read(r['path']);assert len(b)==int(r['bytes']) and hashlib.sha256(b).hexdigest()==r['sha256']
qa=dict(archive=archive.name,bytes=archive.stat().st_size,sha256=sha(archive),content_files=len(selected)+1,
        local_links_checked=links,PNG_count=len(pngs),PDF_count=len(pdfs),original_records=21,processed_components=60,
        CRC_passed=True,all_manifest_hashes_verified_from_zip=True,formal_inversion_qualification=False)
(OUT/'package_validation.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(qa,ensure_ascii=False,indent=2))
