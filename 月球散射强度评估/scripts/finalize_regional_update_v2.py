"""Synchronize the current regional design entry points and verify delivery consistency."""
from pathlib import Path
import json, csv, re, hashlib
from urllib.parse import unquote
import numpy as np
import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/'docs/研究设计总册_20261029'
OUT = D/'三台站区域模型'
VERSION = '2026-11-05-regional-v2'
notice = '> 区域结构更新（2026-11-05）：当前只采用S12、S14、S15三套独立模型，固定背景、莫霍、Q及材料CSV以[第08章](08_S12_S14_S15三个区域模型.md)和[第09章](09_三区域结构文献核对与背景更新.md)为准。本章旧M1/完整VPREMOON共同背景、W共享区域、12 km共同内壳界面及旧计算计数均保留追溯，不再作为执行输入。冯卡尔曼数学定义可继续参考，深度函数莫霍截断须换为本次区域界面；不新增其他模型族。尚未运行新波场。'
for prefix in ['02_', '04_', '06_', '07_']:
    p=next(D.glob(prefix+'*.md')); s=p.read_text(encoding='utf8')
    # Replace the superseded introductory notices, leaving historical body intact.
    s=re.sub(r'^> (?:当前范围更新|最新详细方案|区域结构更新).*\n\n', '', s, flags=re.M)
    head,body=s.split('\n',1)
    p.write_text(head+'\n\n'+notice+'\n'+body,encoding='utf8')

guide='''# 月球散射强度评估｜阅读指南与当前方案

更新：2026-11-05，版本2026-11-05-regional-v2。**当前任务仅为S12、S14、S15三套独立区域模型。浅部、莫霍及吸收背景已按新核对资料更新；新的CGFD3D传播仍为0项，尚无区域最优散射参数。**

## 1. 从哪里开始读

| 入口 | 内容与当前用途 |
|---|---|
| [第08章：三站当前模型](08_S12_S14_S15三个区域模型.md) | 最新数值摘要、三站结构对比图、各区总图和独立搜索安排；优先阅读 |
| [第09章：文献与采用理由](09_三区域结构文献核对与背景更新.md) | 原文完整浅层表、精确壳厚、密度/Q采用和舍弃理由、模型拼接限制 |
| [S12模型说明](三台站区域模型/S12_区域模型说明.md) | 7条近距候选，3训练/4留出；实际地形、逐层参数、事件与散射深度 |
| [S14模型说明](三台站区域模型/S14_区域模型说明.md) | 3条近距候选，2训练/1留出；最慢Vs=0.20 km/s，需要重新核算网格 |
| [S15模型说明](三台站区域模型/S15_区域模型说明.md) | 1条近距候选，无独立留出事件；不能把随机种子当独立观测 |
| [第一册：记录与分布](01_事件台站与记录图册.md) | 历史全目录9事件/4站/21对审计；当前仅使用三站合格子集 |
| [第二册：散射定义](02_散射模型与参数设计.md) | 冯卡尔曼场及来源；旧背景、区域分组和计数已由第08/09章覆盖 |
| [第三册：波形与准入](03_波形处理与反演准入.md) | 数据与缺口处理证据；本轮未重新处理波形或签发新质量准入 |
| [第四册：求解与验证](04_CGFD3D模拟与验证流程.md) | 求解器、几何、收敛原则；旧作业清单和资源估算仅作历史记录 |
| [第五册：论文与文献](05_文献依据与论文组织.md) | 前期证据矩阵和论文组织；本轮新增结构资料以第09章补充 |
| [第06章：旧背景参数](06_具体模型参数与剖面图.md) | 平均背景资料留档，不能再用旧图代替本次三站模型 |
| [第07章：数学和验证细节](07_源站路径与固定背景下的详细模拟方案.md) | 保留随机场与数值验收规则；区域、背景和计算总数由第08/09章覆盖 |
| [Zhang2025清洗综述](附录_Zhang2025数据清洗论文综述.md) | 原始方法综述，区别于本次Zhang2026结构论文 |
| [完整合订本](月球散射研究设计_完整合订本.md) | 先放最新第08/09章，再放其余完整分册；保留修订边界 |

## 2. 本轮真正完成的内容

1. 核对Amrouche 2022 Figure 11的三站Vp、Vs、密度与界面；区分原文参数和项目采用值。
2. 核对Zhang 2026补充表S8：S12/S14/S15壳厚分别35.6±2.7、37.5±3.5、40.8±7.4 km，固定均值用于本次设计。
3. 三地浅部结构及莫霍已分别入表；没有完整区域约束的深部速度、密度和本征吸收使用明确注明的共同后备。
4. 更新三套LOLA源站/结构图、一个结构对比图、三张散射深度候选图、背景CSV及模型定义JSON。
5. 完成来源取值、单位、分段、弹性正模量及Q公式核查；尚未完成正演波形、收敛或观测拟合验证。

模型的关键限制：Amrouche浅层是非唯一解释，密度替换和深部拼接影响响应；S14部分层的负泊松比及S12/S15密度逆转必须保留为弱证据/拼接限制。不能把这些混合输入称为已被原论文联合验证的三套地下模型。

## 3. 接下来执行的单一路线

先按最新各区固定背景验证无随机扰动的走时、场地响应和CGFD3D网格，再冻结背景，仅搜索各区三维冯卡尔曼θ=(a,σ0,b,H)。不再开展多个模型族或额外科学问题的比较矩阵。

初值a=4.5 km、σ0=9%、b=5/9、H=10 km；ν=0.5固定。a候选0.2/0.65/1.3/2/4.5/6 km，σ0为5/9/10/15%，b为5/9、0.85、1，H为3.5/5/10/20 km。Vp和Vs同相对扰动，ρ和Q固定。489次传播是分阶段规划总数，不是已经完成的计算，也不是全参数笛卡尔积。

## 4. 文件与版本边界

三台站区域模型目录中的CSV/JSON才是当前设计表，旧tables目录中的平均背景和旧运行矩阵保留供追溯。所有CSV字段、单位和来源见对应说明。旧三站共同平均背景已备份至历史版本/20261105_共同平均背景。

真实记录、LOLA和既有处理成果不因本轮结构更新而自动通过新版质控。JSON仍需接入用户此前提到的CGFD3D生产配置，不能直接视为已适配求解器的运行文件。
'''
(D/'00_阅读指南与总体方案.md').write_text(guide,encoding='utf8')

order=['00_阅读指南与总体方案.md','08_S12_S14_S15三个区域模型.md','09_三区域结构文献核对与背景更新.md']
order += [next(D.glob(f'{i:02d}_*.md')).name for i in range(1,8)]
order += ['附录_Zhang2025数据清洗论文综述.md']
combined='# 月球散射研究设计完整合订本\n\n2026-11-05区域结构更新。优先展示当前第08/09章；历史正文中的背景和计数不覆盖新版。新传播0项。\n'
for name in order:
    s=(D/name).read_text(encoding='utf8')
    s=re.sub(r'^(#{1,5}) ',lambda m:m.group(1)+'# ',s,flags=re.M)
    combined+='\n\n---\n\n'+s
(D/'月球散射研究设计_完整合订本.md').write_text(combined,encoding='utf8')

# Register the PDFs with verified identities; retain previous download attempts as history.
lib=ROOT/'docs/参考文献'; statefile=lib/'下载记录/文献状态.json'
state=json.loads(statefile.read_text(encoding='utf8'))
papers=[('10.1029/2022je007396','Amrouche',2022,'Effects of Lunar Near-Surface Geology on Moonquakes Ground Motion Amplification'),
        ('10.1029/2025je009453','Zhang',2026,'Lateral Variations in Lunar Crustal Thickness Inferred From Apollo Seismic and GRAIL Gravity Data')]
pdf_audit=[]
for doi,author,year,title in papers:
    p=lib/f'{author} {year} {title}.pdf'; pdf=fitz.open(p); first=''.join(x.get_text() for x in list(pdf)[:2]); identity=doi.lower() in first.lower()
    assert identity, (doi,'DOI not found in PDF first pages')
    entry=next((x for x in state if x.get('doi','').lower()==doi),None)
    if entry is None:
        entry={'doi':doi,'author':author,'year':year,'title':title,'type':'journal-article','cited_in':[]};state.append(entry)
    entry.update(status='saved',filename=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                 source='verified local publisher PDF; 2026-11-05 regional structure audit',
                 validation={'pages':len(pdf),'identity_verified':identity,'doi_found_in_first_two_pages':identity,'checked_location':'Fig11 PDF p17' if author=='Amrouche' else 'Main text and SI Table S8'})
    cited='docs/研究设计总册_20261029/09_三区域结构文献核对与背景更新.md'
    if cited not in entry.setdefault('cited_in',[]):entry['cited_in'].append(cited)
    pdf_audit.append({k:entry[k] for k in ['doi','filename','bytes','sha256','validation']})
    pdf.close()
si=lib/'Zhang 2026 SI for Lateral Variations in Lunar Crustal Thickness Inferred From Apollo Seismic and GRAIL Gravity Data.pdf'
pdf=fitz.open(si); s8=pdf[26].get_text()
assert all(t in s8 for t in ['35.6','37.5','40.8','2.7','3.5','7.4']), 'S8 exact numbers not found'
pdf_audit.append({'parent_doi':papers[1][0],'role':'Supporting Information','filename':si.name,'pages':len(pdf),'verified_table':'S8, PDF p27','sha256':hashlib.sha256(si.read_bytes()).hexdigest()})
for e in state:
    if e.get('doi','').lower()==papers[1][0]: e['supplementary_files']=[si.name]
statefile.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf8')
(lib/'下载记录/20261105_区域结构文献补充核验.json').write_text(json.dumps(pdf_audit,ensure_ascii=False,indent=2),encoding='utf8')

# Independent checks: serialized layer tables agree with the source constraints and samples.
C=json.loads((ROOT/'data/raw/background_models/regional_audit/regional_constraints_20261105.json').read_text(encoding='utf8'))
checks=[]
for st in ['S12','S14','S15']:
    spec=json.loads((OUT/f'{st}_模型定义.json').read_text(encoding='utf8'))
    rows=list(csv.DictReader((OUT/f'{st}_背景参数.csv').open(encoding='utf-8-sig')))
    assert spec['version']==VERSION
    for r,l in zip(rows,C[st]['shallow_layers']):
        assert float(r['Vp_top_km_s'])==l['vp'] and float(r['Vs_top_km_s'])==l['vs'] and float(r['rho_top_kg_m3'])==l['adopted_rho']
    assert float(rows[0]['top_local_depth_km'])==0 and float(rows[-1]['bottom_local_depth_km'])==100
    assert all(abs(float(a['bottom_local_depth_km'])-float(b['top_local_depth_km']))<1e-10 for a,b in zip(rows[:-1],rows[1:]))
    a=np.genfromtxt(OUT/f'{st}_背景剖面采样.csv',delimiter=',',names=True,encoding='utf-8-sig')
    L=4/3*(a['Vs_km_s']/a['Vp_km_s'])**2
    assert np.allclose(a['Qp'],1/(L/a['Qs']+(1-L)/a['Qkappa']))
    assert np.all(a['Vp_km_s']**2-4*a['Vs_km_s']**2/3>0)
    assert np.isclose(spec['background']['regional_moho_local_km'],C[st]['moho_km'])
    assert np.isclose(spec['background']['moho_reference_depth_km']+spec['station']['lola_height_km'],C[st]['moho_km'])
    checks.append({'station':st,'layer_table_matches_sources':True,'contiguous_0_100km':True,'positive_bulk_shear_moduli':True,'Q_formula_matches':True,'geometry_matches':True,'sample_count':len(a)})

docs=[D/'08_S12_S14_S15三个区域模型.md',D/'09_三区域结构文献核对与背景更新.md',D/'00_阅读指南与总体方案.md']+list(OUT.glob('*说明.md'))
bad=[]
for p in docs:
    for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf8')):
        if target.startswith(('http:','https:','#')):continue
        dest=(p.parent/unquote(target.split('#')[0])).resolve()
        if not dest.exists():bad.append({'document':p.name,'target':target})
assert not bad,bad
images=[]
for p in OUT.glob('*.png'):
    with Image.open(p) as im:
        im.verify()
    with Image.open(p) as im: images.append({'file':p.name,'width':im.width,'height':im.height})
report={'version':VERSION,'parameter_checks':checks,'local_links_missing':bad,'images':images,
        'visual_review':'comparison and S12/S14/S15 six-panel figures reviewed; annotations and unit scales inspected',
        'PDF_source_audit':pdf_audit,'numerical_input_consistency_passed':True,
        'not_completed':['CGFD3D input adaptation','waveform fitting','grid convergence','physical validation of hybrid shallow layers'],
        'limitations':['S14 published basement ratio implies negative Poisson ratio','S12/S15 adopted density splice has inversion','changed densities and shallow correction do not preserve source-paper fits']}
(D/'区域结构更新核验_20261105.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
manifest=[]
for p in sorted(D.rglob('*')):
    if p.is_file() and p.name!='文件清单_SHA256.json':
        manifest.append({'path':p.relative_to(D).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(D/'文件清单_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'status':'verified','regional_models':len(checks),'images':len(images),'new_PDF_audit':len(pdf_audit),'broken_current_document_links':len(bad),'combined_characters':len(combined)},ensure_ascii=False))
