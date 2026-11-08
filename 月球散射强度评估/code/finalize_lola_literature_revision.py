"""Integrate verified maps, source-station audit and per-choice model provenance."""
from pathlib import Path
import json,csv,re
ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs/12_LOLA地形底图与散射模型文献依据.md'
def rows(p):return list(csv.DictReader((ROOT/p).open(encoding='utf-8-sig')))
events=rows('results/impact_audit/events_and_domains.csv')
pairs=rows('results/impact_audit/event_station_domains.csv')
local={r['event_id']:r for r in rows('results/impact_audit/local_simulation_candidates.csv')}
text=DOC.read_text(encoding='utf-8').replace('10.1093/gji/ggy379','10.1093/gji/ggy319').replace('10.1002/2016JE005071','10.1002/2016GL070883').replace('../results/impact_terrain/terrain_provenance.json','../results/impact_terrain/lola_data_provenance.json')
if '<!-- EVENT_TABLE -->' not in text:
    raise SystemExit('Report already finalized and scientifically reviewed; edit the Markdown directly instead of replaying the one-time integration.')
table=['| 撞击事件 | 地面接收时刻UT | 接收台站与重算距离/km | 近距候选台站 |','|---|---|---|---|']
gallery=[]
for e in events:
    eid=e['event_id'];pp=[p for p in pairs if p['event_id']==eid]
    sta='；'.join(f"{p['station']}{'†' if p['nunn2024_clear'].lower()!='true' else ''} {float(p['distance_km']):.1f}" for p in pp)
    table.append(f"| {eid} | {e['time_earth_received'].replace('T',' ')} | {sta} | {local[eid]['receivers'].replace(';','、') if eid in local else '无；远距检验'} |")
    gallery += [f"### {eid}",f"地面接收源时刻：{e['time_earth_received']}；撞击纬度{float(e['lat']):g}°、东经{float(e['lon']):g}°。有记录路径：{sta} km。†为文献低信噪比。",f"![{eid}地形、撞击源、台站和范围](../figures/impact_terrain/{eid}_terrain_domain.png)"]
    if eid in local:
        d=local[eid]
        gallery += [f"近距候选范围：东经{d['west_degE']}～{d['east_degE']}°，北纬{d['south_degN']}～{d['north_degN']}°；约{d['width_at_midlat_km']}×{d['height_km']} km。可查看[近距地形放大图](../figures/impact_terrain/{eid}_local_terrain_domain.png)。"]
    else:gallery+=['本事件保留全记录覆盖，暂不进入近距CGFD3D首批任务。']
    gallery += [f"![{eid}实际代表性波形](../figures/impact_audit/{eid}_modern_records.png)"]
    files='；'.join(f"[{p['station']}原始MiniSEED](../data/raw/impact_modern/{eid}_{p['station']}_MP_ATT.mseed)" for p in pp)
    gallery += [files+'。名义响应处理后的NPZ逐分量路径见[分量清单](../results/impact_modern_trace_audit.csv)，该清单同时记录缺口、时钟和频带状态。']
table += ['','†仅表示Nunn2024的低信噪比分类。精确坐标、文献距离与本项目重算距离分别保留，不将小数位数等同于位置精度。']
text=text.replace('<!-- EVENT_TABLE -->','\n'.join(table)).replace('<!-- EVENT_GALLERY -->','\n\n'.join(gallery))

lit='''| 研究与原文定位 | 对象、方法与参数 | 本项目怎样采用 |
|---|---|---|
| [Onodera2021](https://doi.org/10.1029/2020JE006406)，§2/Table2–3 | A14/A16 S-IVB→S12，二维P–SV；上/下a=0.2/0.6 km，上层底7.5 km，总深度南10/北20 km；波动上限28%/14% | 两层竞争结构；不把上限换成RMS；二维与三维幅度传播差异须检验。 |
| [Onodera2022](https://doi.org/10.1029/2022JE007558)，§2.2–2.4/§3.3 | 同两条S12路径，三维指数ACF；a=0.65 km，生成速度场1σ约5%–10%，强扰动至约10 km | 主起点。生成器ε=0.024–0.042和场的1σ分列；不是四区域各自反演。 |
| [Dainty与Toksöz1977](https://journal.geophysicsjournal.com/JofG/article/download/102/64)，p385–386/Fig6 | 直接比较A14LM→S14、A15LM→S15，0.45 Hz扩散包络；D约2 km²/s，Q=5000 | 给S14/S15增加独立包络基准；自由程不是a，未给连续随机场σ。 |
| [Jiang等2015](https://html.rhhz.net/dqwlxb/2015-5-1675.htm)，§2–4/Table3–4 | S12自然浅震/深震；二维，0.05–0.4 Hz；von Kármán，固定a=2 km、标准差约3%–5%、H=15 km、Q=6750 | 低σ长a竞争端元；a受原网格约束，不是独立反演值。移植到本频带和三维属于新检验。 |
| [Sollberger2016](https://doi.org/10.1002/2016GL070883)，§3–5/Fig4–5 | Apollo17局部主动源，二维浅部分层，界面4/60/410 m；von Kármán，逐层速度变化70/70/50/25% | 支持浅表高反差机制；百分比不是已核实RMS，a/Hurst仍缺附件核查。不能推广为10 km厚强层。 |
| [Keil2024](https://doi.org/10.1029/2024EA003742)，模拟部分/Appendix A | Apollo17 EP3与LSPE，二维；Hurst0.5、a=10 m、最大速度偏差70%；高频、百米局部尺度 | 独立浅层机制及随机实现敏感性先例；不用它给中周期百公里路径赋70% RMS。 |
| [Blanchette-Guertin2015 GRL](https://doi.org/10.1002/2015GL066151)，§1–4/Fig1–3 | 理想盆地声子法；外侧H=5–60 km，盆内0或5 km；显示源区和边缘散射能量贡献 | 支持H(x,y)、源侧/接收侧对照；不是A15实测层厚。 |
| [Blanchette-Guertin2015 JGR](https://doi.org/10.1002/2014JE004654)，Table1 | 声子法；H=5/15/30/60 km，界面最大对比25/75/95%，Qi=2000/4500/6500等 | 检查厚度、吸收与背景速度权衡；界面对比和散射间距不等于连续场σ和a。 |
| [Shi2023](https://doi.org/10.1029/2022JE007676)，§2–4/Fig4,6–8 | Apollo浅源接收函数；二维指数ACF；a=1/4 km，ε=0.1/0.2等，浅部10–20 km；0.2–0.8 Hz | 较强扰动、较长尺度竞争与PRF稳定性检验；ε归一化待查，不视为本项目路径σ后验。 |
| [Zhang2022](https://doi.org/10.1029/2022JE007222)，§2–3/§5 | 月震全球波场；节点独立随机、最大计算幅度50%；约70%来自外推，深度20–130 km试验不敏感 | 高对比分支的动机；物理a未独立控制，不能称“σ50%–70%已验证”。 |
| [Nunn2024](https://doi.org/10.3847/PSJ/ad83d2)，Table2/§5 | 多人工撞击，AxiSEM3D；最大±50%，线性减至20/50/80 km为零 | 与主族分开比较；需控制离散谱和背景，不能把节点尺度当月球相关尺度。 |
| [Gillet2017](https://doi.org/10.1016/j.pepi.2016.11.001)，深度扩散模型 | 多事件综合；最上10 km D约2 km²/s、Qsc≤10，Qi约2400；更深散射过渡约80–100 km | 独立能量输运约束；强层深度与广义过渡深度分开，不由D唯一解a/σ。 |
| [Kim2025](https://doi.org/10.1029/2024GL114506)，§2/SI引用 | 转换波/偏振的三维合成验证使用a=750 m、15%速度/密度非均质；SI未取得 | 支持早到偏振与独立背景检查；15%统计定义暂不升级为RMS，非区域散射反演。 |
| [Torrent Duch2025](https://doi.org/10.1029/2025JE009090)，§5–6 | S16尾波自相关晚到更稳定；弱局地散射与更锐利界面均可解释 | 保留区域强弱的双向假设；不预设高地最强，也不直接赋a=1–4 km。 |
| [Eaton2024](https://doi.org/10.1093/gji/ggae098)，§3–4/Fig9 | 包含A14LM→S14、A15SIVB→S12、A17SIVB→S12；多尺度熵与频率相关 | 增加统计状态辅助诊断；注意低能量频带和噪声影响。未提供本项目a/σ/H三元组。 |
| [Onodera2025会议摘要](https://www.hou.usra.edu/meetings/lpsc2025/pdf/1144.pdf)，两页 | Szilard虚拟源站，地形+随机介质；a=.65 km，1σ10%，上20 km扰动 | 联合地形/介质/界面试验先例；会议模拟，非真实Apollo反演。 |
'''
text=text.replace('<!-- LITERATURE_TABLE -->',lit)
models=[
dict(id='R0',name='背景与地形控制',parameters='无随机扰动；平坦/真实地形各一组',purpose='有多少波形可由背景、界面和地形解释',source=['10.3847/PSJ/ad83d2'],locator='无随机背景及地形比较；本项目四组归因设计',status='第一优先',classification='project_control_informed_by_lunar_simulation'),
dict(id='R1',name='浅层各向同性指数场',parameters='a=.65 km，σv=.10，H=10 km，ν=.5；H边缘1 km余弦渐变',purpose='作为两条S12路径的三维起点',source=['10.1029/2022JE007558'],locator='§2.2–2.4/§3.3；1 km余弦不是原文反演值',status='第一优先',classification='lunar_path_reference_plus_project_taper'),
dict(id='R2',name='连续随深度渐弱',parameters='σv(z)=.10exp(−z/5 km)，23–24 km归零',purpose='检验有无明确强层底界的差别',source=['10.1016/j.pepi.2016.11.001'],locator='深度趋势有依据；5 km衰减长度及24 km截断均为项目假设',status='基准通过后',classification='project_hypothesis_no_direct_numeric_lunar_constraint'),
dict(id='R3',name='两尺度分层',parameters='上/下a=.2/.6 km，7.5 km层界，总深10/20 km；若用σ=.10/.05须另标项目版本',purpose='检验层化与南北路径差异',source=['10.1029/2020JE006406'],locator='Table2–3；原文28/14%为上限式表述，不能换成项目RMS',status='基准通过后',classification='two_dimensional_reference_requires_three_dimensional_retest'),
dict(id='R4',name='统计各向异性',parameters='ah=1.3 km，az=.65 km，其余同R1',purpose='检验水平延伸非均质的效果',source=['10.1093/gji/ggy319'],locator='谱形式的一般理论；该尺度比是项目选择，不是月球测值',status='后置探索',classification='general_theory_plus_project_ratio'),
dict(id='R5',name='高对比深层分支',parameters='有界最大±.5，线性减到20/50/80 km为零',purpose='检验更厚破碎层与长路径波形',source=['10.3847/PSJ/ad83d2','10.1029/2022JE007222'],locator='Nunn Table2/§5；Zhang只实际计算至最大50%，未独立控制a',status='独立竞争；先数值检查',classification='bounded_contrast_not_RMS_and_grid_scale_requires_control'),
dict(id='R6',name='弱扰动长尺度',parameters='a=2 km，σ=.03/.05，H=15 km；von Kármán谱形待原文细节复核',purpose='检验不同a–σ组合能否解释相同观测',source=['10.6038/cjg20150519'],locator='§2–4/Table3–4；原观测0.05–0.4 Hz、二维、自然月震',status='独立竞争；三维迁移试验',classification='other_lunar_events_model_transfer_not_direct_impact_prior'),
dict(id='R7',name='横向层厚与源/站侧分离',parameters='H(x,y)；先固定σ与a，分开源侧、接收侧和全路径扰动',purpose='检验盆缘与跨地质单元路径',source=['10.1002/2015GL066151'],locator='§1–4/Fig1–3；实际分区须有独立依据，不由DEM颜色阈值决定',status='优先于完全自由各向异性',classification='lunar_mechanism_model_project_geometry_to_define'),
dict(id='R8',name='较长尺度较强扰动',parameters='a=1/4 km、ε=.1/.2等，H=10/20 km',purpose='结合接收函数/相干性排除包络等效模型',source=['10.1029/2022JE007676'],locator='§2–4/Fig4,6–8；ε实现归一化待核，不直接写σ',status='参数定义核实后',classification='receiver_function_evidence_not_path_RMS_inversion'),
dict(id='S',name='独立浅层场地分支',parameters='近站低速分层及浅表随机反差；不把米级a推广到全路径',purpose='检查是否将场地共振误归为深部散射',source=['10.1029/2022JE007396','10.1002/2016GL070883','10.1029/2024EA003742'],locator='Amrouche§6；Sollberger§3–5；Keil AppendixA',status='单独网格/场地敏感性',classification='near_surface_evidence_separate_scale')]
mt=['| 模型 | 参数与结构 | 要检验的问题 | 文献、采用边界与优先级 |','|---|---|---|---|']
for m in models:
    cite='；'.join(f'[{d}](https://doi.org/{d})' for d in m['source'])
    mt.append(f"| {m['id']} {m['name']} | {m['parameters']} | {m['purpose']} | {cite}；{m['locator']}。{m['status']}。 |")
text=text.replace('<!-- MODEL_TABLE -->','\n'.join(mt))
text=text.replace('“原生数据”','“原生发布网格”')
text=text.replace('主月球三维参考见','一般von Kármán的a并不恒等于1/e距离；只有指数特例才有这一关系。主月球三维参考见')
text=text.replace('### 8.2 地形对照','Garcia2019作者数据在2026年发布v2，新增M1/M2/M3均值和±1标准差表。该标准差属于背景反演不确定性，不是短尺度随机场σv；逐深度上下界也不是一个联合后验样本。本轮核实了版本与文件说明，下载限流，未声称已取得该套数字模型。[作者数据v2](https://doi.org/10.5281/zenodo.21476963)。VPREMOON还须使用[2012勘误Table6](https://doi.org/10.1016/j.pepi.2012.03.009)，避免旧表和QP/QS身份错误。\n\n### 8.2 地形对照')
text=text.replace('具体输入格式、网格方向和导出接口以用户后续提供的生产配置为准。','CGFD3D相关方法依据为[Zhang et al., 2012，曲线网格自由表面与验证](https://doi.org/10.1111/j.1365-246X.2012.05472.x)和[Zhang et al., 2014，变形网格吸收边界](https://doi.org/10.1093/gji/ggu124)。强散射误差累积还参考[Bracale et al., 2026](https://doi.org/10.1093/gji/ggaf504)；其理想介质数值不作月球先验。具体输入格式、网格方向和导出接口以用户后续提供的生产配置为准。')
text=text.replace('三是项目预算，不是文献规定。','三是项目预算，不是文献规定；实现平均的理论讨论参考[Bracale2026](https://doi.org/10.1093/gji/ggaf504)。')
text=text.replace('无垂向夸大','无垂向夸大')
DOC.write_text(text,encoding='utf-8')

old=json.loads((ROOT/'config/scattering_model_design.json').read_text(encoding='utf-8'))
cfg={
 'version':'2026-10-29-literature-terrain-revision-v2','solver':'CGFD3D','status':'scientific_design_not_solver_input','formal_waveform_runs_executed':0,
 'supersedes_for_planning':'config/scattering_model_design.json',
 'legacy_material_previews':'Existing R1/R2/R4 NetCDFs retain their old parameters; this file does not regenerate them.',
 'units':old['units'],'modelling_unit':'event + actual receiving stations + geographic domain; terrain labels are interpretation only',
 'reference':{'family':'R1','a_m':650,'sigma_v_standard_deviation':.1,'H_m':10000,'nu':.5,'primary_doi':'10.1029/2022JE007558','scope':'A14 and A16 SIVB impacts received at S12','fidelity':'inspired starting model, not exact reproduction'},
 'frequency':{'common_initial_hz':[.3,.5],'first_extension_hz':[.5,.9],'conditional_higher_extension_hz':[.9,1.5],'sources':['10.3847/PSJ/ad83d2','10.1029/2022JE007558'],'admission':'per event, component and time window; nominal response previews not finally certified'},
 'main_search':{'a_m':[200,2000],'sigma_v':[.02,.15],'H_m':[3500,20000],'classification':'project_search_envelope_not_regional_confidence_interval','source_inspiration':['10.1029/2022JE007558','10.1029/2020JE006406']},
 'initial_values':{'a_m':[300,650,1300],'sigma_v':[.05,.1,.15],'H_m':[3500,10000,20000],'classification':'project_design_around_literature_reference'},
 'families':models,
 'controls':{'density_beta_legacy_preview':.8,'density_beta_initial_comparison':[0,.8],'density_beta_classification':'project_hypothesis_no_direct_lunar_0.8_measurement','vp_vs_field_correlation':1,'vp_vs_correlation_classification':'project_dimension_reduction','initial_seed_ids':old['controls']['seed_ids'],'seed_count_status':'screening_budget_only_expand_until_stable','R1_taper_width_m':1000,'taper_classification':'project_smoothing_choice','geographic_buffer_km':50,'buffer_status':'not_proven_propagation_boundary','terrain':['flat','LOLA_real_height'],'terrain_source':'LOLA LDEM_64 V3.1 native 64 pix/degree'},
 'background_branches':{'S12_reference':'10.1029/2022JE007558 section2.3','independent_models':['10.1007/s11214-019-0613-y','10.5281/zenodo.21476963','10.1016/j.pepi.2012.03.009'],'new_v2_numerical_tables_downloaded':False,'note':'Do not treat background ±1SD as short-scale sigma_v or a joint sample.'},
 'duration':{'debug_s':600,'conditional_target_s':3600,'requires':'observed late window + domain/grid/PML convergence','classification':'project_target_not_completed_simulation'},
 'scope_of_legacy_88_jobs':'two S12 reference paths only; not full regional program',
 'decision_ledger':'results/model_choice_provenance.csv','report':'docs/12_LOLA地形底图与散射模型文献依据.md'}
(ROOT/'config/scattering_model_design_v2_annotated.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
with (ROOT/'results/model_family_sources.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(models[0]));w.writeheader()
    for m in models:w.writerow({**m,'source':';'.join(m['source'])})
print(json.dumps({'report':str(DOC),'characters':len(text),'families':len(models),'events':len(events)},ensure_ascii=False))
