"""Assemble a portable, source-bounded research design; no wave solver is run."""
from pathlib import Path
import csv, json, re, shutil, math, hashlib, zipfile, collections
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'docs/研究设计总册_20261029'
OUT=ROOT/'outputs/综合研究设计_20261029'
for d in [DEST,OUT,DEST/'assets',DEST/'tables',DEST/'sources',DEST/'references']:
    d.mkdir(parents=True,exist_ok=True)

def read(rel): return (ROOT/rel).read_text(encoding='utf-8-sig')
def csvread(rel):
    with (ROOT/rel).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(name,text): (DEST/name).write_text(text.strip()+'\n',encoding='utf-8')
def table(head,rows):
    def cell(x):return str(x).replace('|',' / ').replace('\n','；')
    return '\n'.join(['| '+' | '.join(head)+' |','|'+'|'.join(['---']*len(head))+'|']+['| '+' | '.join(cell(x) for x in row)+' |' for row in rows])
def csvwrite(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def yes(v):return str(v).lower()=='true'
def fmt(x,n=2):
    try:return f'{float(x):.{n}f}'
    except:return '—'
def pct(x):return fmt(float(x)*100,2)+'%' if x!='' else '—'

events=csvread('results/impact_audit/events_and_domains.csv')
stations=csvread('results/impact_audit/stations.csv')
pairs=csvread('results/impact_audit/combined_event_station_audit.csv')
domains=csvread('results/impact_audit/local_simulation_candidates.csv')
traces=csvread('results/waveform_comparison/trace_stage_comparison.csv')
bands=csvread('results/impact_audit/modern_band_by_pair.csv')
summary=json.loads(read('results/waveform_comparison/summary.json'))
model=json.loads(read('config/scattering_model_design_v2_annotated.json'))
ep={e['event_id']:e for e in events}; sp={s['station']:s for s in stations}
pairidx={(p['event_id'],p['station']):p for p in pairs}
domainidx={d['event_id']:d for d in domains}
tridx=collections.defaultdict(list)
for t in traces:tridx[(t['event_id'],t['station'])].append(t)
heights={x['site']:x['native_pixel_height_m'] for x in csvread('results/impact_terrain/site_height_checks.csv')}

copylist=[
 'results/impact_audit/stations.csv','results/impact_audit/events_and_domains.csv',
 'results/impact_audit/combined_event_station_audit.csv','results/impact_audit/local_simulation_candidates.csv',
 'results/impact_audit/modern_band_by_pair.csv','results/impact_modern_band_screen.csv',
 'results/impact_modern_trace_audit.csv','results/waveform_comparison/trace_stage_comparison.csv',
 'results/model_choice_provenance.csv','results/model_family_sources.csv',
 'config/scattering_run_manifest.csv','results/impact_terrain/site_height_checks.csv']
for rel in copylist:shutil.copy2(ROOT/rel,DEST/'tables'/Path(rel).name)
for rel in ['results/waveform_comparison/summary.json','results/waveform_comparison/numerical_validation.json',
 'results/waveform_raw_integrity_audit.json','results/impact_terrain/lola_data_provenance.json',
 'config/scattering_model_design_v2_annotated.json','reports/zhang2025_review_validation.json',
 'data/raw/literature/Zhang2025_Cleaning_Apollo/publisher_pdf_web_extracted.txt',
 'data/raw/literature/Zhang2025_Cleaning_Apollo/acquisition_status.json',
 'data/raw/literature/Zhang2025_Cleaning_Apollo/crossref_metadata.json']:
    shutil.copy2(ROOT/rel,DEST/'sources'/Path(rel).name)
for p in (ROOT/'docs').glob('*.bib'):shutil.copy2(p,DEST/'references'/p.name)
write('references/README.md','# 参考文献文件\n\n保留既有四份BibTeX，不静默改写引用键或合并不同字段。文献参数的证据强度以第五册和逐项来源表为准，BibTeX只解决书目信息。\n\n'+ '\n'.join(f'- [{p.name}]({p.name})' for p in sorted((DEST/'references').glob('*.bib'))))

for p in (ROOT/'figures/waveform_comparison').glob('*.png'):shutil.copy2(p,DEST/'assets'/p.name)
terrainnames=['impact_station_terrain_overview','nine_event_terrain_domains','local_candidate_terrain_domains']
terrainnames += [e['event_id']+'_terrain_domain' for e in events]
terrainnames += [d['event_id']+'_local_terrain_domain' for d in domains]
for name in terrainnames:shutil.copy2(ROOT/'figures/impact_terrain'/f'{name}.png',DEST/'assets'/f'{name}.png')

# New graphics use tables/formulas; no synthetic seismograms or AI imagery.
font=FontProperties(fname='C:/Windows/Fonts/msyh.ttc')
plt.rcParams.update({'font.family':font.get_name(),'axes.unicode_minus':False,'font.size':11,'savefig.dpi':170})
fig,ax=plt.subplots(figsize=(11.5,9.0),layout='constrained')
fig.get_layout_engine().set(rect=(0,.055,1,.945))
for i,e in enumerate(events):
    for j,s in enumerate(stations):
        key=(e['event_id'],s['station']);p=pairidx.get(key)
        if p:
            clear=yes(p['nunn2024_clear']);n=sum(yes(t['archive_channel_present']) for t in tridx[key])
            ax.add_patch(Rectangle((j-.47,i-.44),.94,.88,facecolor='#c8e2f3' if clear else '#ffe3aa',edgecolor='#516273',hatch=None if clear else '//',lw=.8))
            ax.text(j,i,('C' if clear else 'L')+f'{n}\n{float(p["distance_km"]):.1f} km',ha='center',va='center',fontsize=11)
        else:
            ax.add_patch(Rectangle((j-.47,i-.44),.94,.88,facecolor='#f3f3f3',edgecolor='#dddddd',lw=.5))
            ax.text(j,i,'—',ha='center',va='center',color='#888888')
ax.set(xlim=(-.55,3.55),ylim=(8.55,-.65),yticks=range(9),yticklabels=[e['event_id']+'  '+e['time_earth_received'][:10] for e in events],xticks=range(4),xticklabels=[s['station'] for s in stations])
ax.xaxis.tick_top();ax.tick_params(length=0);[x.set_visible(False) for x in ax.spines.values()]
ax.set_title('9次人工撞击—4台站记录覆盖\n21个配对；60条实际中周期分量；3条S14垂直分量未返回',fontsize=16,pad=42)
fig.text(.5,.016,'C：文献清晰；L：文献低信噪比；数字：实际分量数；—：本样本无配对。分类不等于最终反演准入。',ha='center',fontsize=10)
fig.savefig(DEST/'assets/event_station_coverage_matrix.png');plt.close(fig)

d=np.linspace(0,25,501);rho=2308+786*(1-np.exp(-d*1000/9800));phi=1-rho/3094
vp=7150*np.sqrt(1-phi)*np.exp((phi/2-7)*phi/(2*(1-phi)))/1000
ratio=2+(np.sqrt(3)-2)*np.clip((d-10)/2,0,1)
w=.5*(1+np.cos(np.pi*np.clip((d-9.5),0,1)))
fig,axes=plt.subplots(1,3,figsize=(14,6.3),layout='constrained')
axes[0].plot(vp,d,label='Vp');axes[0].plot(vp/ratio,d,'--',label='Vs');axes[0].set(xlabel='速度 / km/s',ylabel='约定深度 / km',title='B0：S12参考背景');axes[0].invert_yaxis()
axes[1].plot(10*w,d,label='R1：10%平台 + 余弦渐消');axes[1].plot(10*np.exp(-d/5)*np.clip(24-d,0,1),d,'--',label='R2：指数渐弱 + 23–24 km归零');axes[1].set(xlabel='目标相对速度标准差 / %',ylabel='约定深度 / km',title='项目深度权重定义');axes[1].invert_yaxis()
r=np.linspace(0,4,501)
for a,ls in zip([.3,.65,1.3],['--','-',':']):axes[2].plot(r,np.exp(-r/a),ls,label=f'a={a:.2f} km')
axes[2].axhline(np.exp(-1),color='#777777',ls='--',lw=.7);axes[2].set(xlabel='空间间距r / km',ylabel='归一化自相关C(r)/C(0)',title='指数场：相同RMS，不同相关尺度',ylim=(0,1.02))
for ax in axes:ax.grid(alpha=.2);ax.legend(fontsize=8.5)
fig.suptitle('模型定义示意｜非观测反演结果、非传播模拟结果',fontsize=16)
fig.savefig(DEST/'assets/model_reference_profiles.png');plt.close(fig)

# Explicit event-level plan: 64 planned jobs; no solver configurations invented.
jobs=[]
for dom in domains:
    e=ep[dom['event_id']]
    aux=[]
    for st in e['recorded_stations'].split(';'):
        s=sp[st]
        if st not in dom['receivers'].split(';') and float(dom['west_degE'])<=float(s['lon'])<=float(dom['east_degE']) and float(dom['south_degN'])<=float(s['lat'])<=float(dom['north_degN']):aux.append(st)
    for terrain in ['flat','LOLA_real_height']:
        for family,seed in [('R0',''),('R1','20261029'),('R1','20261030'),('R1','20261031')]:
            jobs.append(dict(run_id=f'V3_{e["event_id"]}_{terrain}_{family}_{seed or "none"}',event_id=e['event_id'],domain_id=e['event_id']+'_local_v1',target_receivers=dom['receivers'],auxiliary_receivers=';'.join(aux),family=family,background='B0_Onodera2022_inspired',terrain=terrain,depth_definition='Dsurf_vertical_below_local_surface',a_km=.65 if family=='R1' else '',sigma_v=.1 if family=='R1' else 0,H_midpoint_km=10 if family=='R1' else '',taper_width_km=1 if family=='R1' else '',nu=.5 if family=='R1' else '',density_beta=0,Qi_proposed=2400,Qi_implementation='pending_solver_configuration',seed=seed,source_family='equivalent_source_pending_benchmark',west_degE=dom['west_degE'],east_degE=dom['east_degE'],south_degN=dom['south_degN'],north_degN=dom['north_degN'],analysis_band_candidate_hz='0.3-0.5',duration_debug_s=600,duration_conditional_target_s=3600,first_stage=e['event_id'] in ['A14SIVB','A16SIVB'],mesh_and_dt='pending_convergence',status='planned_not_executed'))
csvwrite(DEST/'tables/event_baseline_jobs_v3.csv',jobs)
spec={'version':'2026-10-29-consolidated-scientific-plan-v3','solver':'CGFD3D','is_solver_input':False,'propagation_runs_executed':0,'reference':{'a_m':650,'sigma_v':.1,'H_midpoint_m':10000,'taper_width_m':1000,'nu':.5,'density_beta_new_baseline':0,'density_beta_sensitivity':.8,'depth':'Dsurf_vertical_below_local_surface','Qi_proposed':2400,'Qi_implementation':'pending'},'parent_design':'sources/scattering_model_design_v2_annotated.json','jobs':'tables/event_baseline_jobs_v3.csv','jobs_total':64,'first_stage_subset':16,'target_pairs':11,'auxiliary_pairs':['A17SIVB_S14'],'legacy_88_not_additive':True,'old_materials_unchanged':True,'numeric_choices_are':'literature inspired starting point plus explicitly labelled project assumptions'}
write('tables/consolidated_model_spec_v3.json',json.dumps(spec,ensure_ascii=False,indent=2))

qualification=[]
for p in pairs:
 for ch in ['MHZ','MH1','MH2']:
  for band in ['0.3-0.5','0.5-0.9','0.9-1.5']:
   qualification.append(dict(event_id=p['event_id'],station=p['station'],channel=ch,band_hz=band,quantity='',window_start_s='',window_end_s='',processing_version='',archive_present=next(yes(t['archive_channel_present']) for t in tridx[(p['event_id'],p['station'])] if t['channel']==ch),gain_verified='',orientation_verified='',clock_verified='',artifact_class='',mask_file='',snr_early='',snr_late='',allowed_metrics='',qualification_status='not_yet_assessed',reason='',review_date=''))
csvwrite(DEST/'tables/qualification_template.csv',qualification)

resource=[]
for d0 in domains:
    nx=math.ceil(float(d0['width_at_midlat_km'])/.1)+1;ny=math.ceil(float(d0['height_km'])/.1)+1;nz=401;n=nx*ny*nz
    resource.append(dict(event_id=d0['event_id'],dx_assumed_m=100,depth_assumed_km=40,nx=nx,ny=ny,nz=nz,nodes=n,array_count_assumed=32,bytes_per_value_assumed=4,memory_GiB_excluding_extras=n*32*4/1024**3,status='illustrative_not_production_mesh'))
csvwrite(DEST/'tables/resource_estimates.csv',resource)

joined=[]
for p in pairs:
    ts=tridx[(p['event_id'],p['station'])];existing=[t for t in ts if yes(t['archive_channel_present'])]
    joined.append(dict(event_id=p['event_id'],station=p['station'],distance_recomputed_km=p['distance_km'],distance_published_km=p['distance_published_km'],distance_deg=p['distance_deg'],literature_clear=p['nunn2024_clear'],components_present=';'.join(t['channel'] for t in existing),components_absent=';'.join(t['channel'] for t in ts if not yes(t['archive_channel_present'])),n_components=len(existing),raw_gap_pct_min=min(float(t['raw_gap_fraction'])*100 for t in existing),raw_gap_pct_max=max(float(t['raw_gap_fraction'])*100 for t in existing),display_window_ATT_s='-300:3600',raw_archive_project_path=f'data/raw/impact_modern/{p["event_id"]}_{p["station"]}_MP_ATT.mseed',three_stage_figure=f'assets/{p["event_id"]}_{p["station"]}_three_stages.png',band_screen_version='legacy_impact_reference_not_v2_recomputed',final_qualification='pending'))
csvwrite(DEST/'tables/pair_record_summary_current.csv',joined)

# First volume: full tables and all nine original/processed event galleries.
intro='''# 第一册｜事件、台站、地形与实际记录图册

版本：2026-10-29。主样本为9次Apollo人工撞击，非完整天然撞击或深浅月震目录。本册把源站位置、地形底图、覆盖范围、实际波形和缺失项集中展示。原始数据身份和处理方法见第三册；模型及范围选择见第二、四册。

## 1. 已核实覆盖及统计口径

本项目实际取得21个事件—台站配对的现代档案，63个候选中周期分量位置中60条有返回，3条S14 MHZ未返回并落在已知故障期；另存81个旧档案SAC供对照。Nunn2024将21对中的16对判为清晰、5对判为低信噪比。这是文献分类，不等于最终可反演配对数。

![事件与台站覆盖矩阵](assets/event_station_coverage_matrix.png)

图1：C/L分别表示文献清晰/低信噪比，后随实际分量数；距离来自统一球面重算。灰格表示本样本无配对，不自动判定该站当时停机。最终频带和时间窗仍须逐道准入。

## 2. 台站坐标、观测覆盖与研究角色

坐标使用NASA公布的ALSEP位置，而非登月舱位置；东经、北纬为正，西经、南纬为负。参考系为DE421的Mean Earth/Polar Axis。小数位保留来源精度，不表示已经独立测到相应定位精度。[NASA台站来源](https://nssdc.gsfc.nasa.gov/planetary/lunar/lunar_sites.html)
'''
roles={'S12':'风暴洋/月海邻近参考走廊；两条已研究S-IVB路径为起点','S14':'Fra Mauro喷出物与破碎区背景；与S12共同事件联合','S15':'Hadley–Apennine/盆缘背景；A15LM近距验证','S16':'Descartes/Cayley高地背景；目前以远距检验为主'}
rows=[]
for s in stations:
 ps=[p for p in pairs if p['station']==s['station']]; nt=sum(yes(t['archive_channel_present']) for t in traces if t['station']==s['station'])
 rows.append([s['station'],s['lat'],s['lon'],heights[s['station']],len(ps),sum(yes(p['nunn2024_clear']) for p in ps),nt,f'{min(float(p["distance_km"]) for p in ps):.1f}–{max(float(p["distance_km"]) for p in ps):.1f}',roles[s['station']]])
intro+= '\n'+table(['台站','纬度°N','经度°E','LOLA像元高程/m','记录事件','文献清晰','实有MP分量','距离范围/km','研究角色'],rows)
lat1,lat2=map(math.radians,[float(sp['S12']['lat']),float(sp['S14']['lat'])]);dl=math.radians(float(sp['S14']['lon'])-float(sp['S12']['lon']));da=lat2-lat1
sep=1737.4*2*math.asin(math.sqrt(math.sin(da/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dl/2)**2))
intro+=f'''\n\nS12与S14球面相距约{sep:.1f} km，可作为联合研究走廊，但不能合成一个虚拟台站。表中LOLA高程来自原生像元，相对1737.4 km参考球，不是独立测量的台站精密海拔。S15台站位于低处不意味着周边没有山地；“高地”地质单元也不能按高程正负简单划分。

本样本中S12有9次记录、S14有6次、S15有4次、S16有2次。S16只有一条文献清晰人工撞击配对，距离约851 km，无法独立约束局地高地的a、σv、H三个参数。S12短周期传感器故障；S14部分垂直通道故障；当前主比较限定中周期MHZ/MH1/MH2，不能以旧SP文件存在认定SP可用。

按Zhang2025 Table1整理的LP运行总跨度如下，首末时刻取到秒；这不表示跨度内没有停机、模式切换或通道故障。

| 台站 | 表中LP最早起始/UTC | 最后结束/UTC | 本样本的模式及限制 |
|---|---|---|---|
| S12 | 1969-11-19 14:23:23 | 1977-09-30 18:50:51 | 本批事件处于peaked模式时段；SP故障 |
| S14 | 1971-02-05 17:44:33 | 1977-09-30 18:50:51 | 本批处于peaked时段；1972年三次撞击的MHZ未返回 |
| S15 | 1971-07-31 18:52:00 | 1977-09-30 18:50:51 | 本批记录处于peaked时段；A15 S-IVB早于部署 |
| S16 | 1972-04-21 20:20:00 | 1977-09-30 18:50:51 | 本批记录处于peaked时段；A16 S-IVB早于部署 |

模式判断来自运行表，仍须用具体响应历元和增益历史逐道复核，不能取代仪器检查。[Zhang2025原文Table1](https://doi.org/10.1029/2025EA004710)。

## 3. 全部事件及源参数

事件名称中的A16表示Apollo16任务撞击，并不表示由S16接收。A16 S-IVB撞击时S16尚未部署。LM表示登月舱上升级，S-IVB表示土星上面级；两类入射条件不同。[NASA撞击来源](https://nssdc.gsfc.nasa.gov/planetary/lunar/apollo_impact.html)
'''
energies={'A12LM':('1.68','3.36e16','3.7'),'A13SIVB':('2.58','4.63e17','76'),'A14SIVB':('2.54','4.52e17','69'),'A14LM':('1.68','3.25e16','3.6'),'A15SIVB':('2.58','4.61e17','62'),'A15LM':('1.70','3.44e16','3.2'),'A16SIVB':('2.5–2.6','4.59e17','约79'),'A17SIVB':('2.55','4.71e17','55'),'A17LM':('1.67','3.15e16','4.9')}
source_rows=[]
for e in events:
 v,en,ang=energies[e['event_id']]
 source_rows.append([e['event_id'],e['time_earth_received'].replace('T',' '),e['lat'],e['lon'],v,fmt(float(en)*1e-7,0),ang,e['recorded_stations'].replace(';','、')])
intro+='\n'+table(['事件','地面接收时刻/UTC','纬度°N','经度°E','撞速/km s⁻¹','撞击动能/J','相对水平入射角/°','记录台站'],source_rows)
intro+='''

NASA原表能量单位erg，本表仅乘10⁻⁷转为J；撞击动能不等于地震辐射能。时刻为地面接收，约晚于月面真实撞击1.3 s；现有图未擅自扣除。A16 S-IVB时刻与能量为估计，起时约有4 s不确定性；源方位和耦合效率尚待核实。元数据见[tables/events_and_domains.csv](tables/events_and_domains.csv)。

## 4. 地形底图与范围框

底图为NASA/PDS LOLA LDEM_64 V3.1，原生64像元/度，即0.015625°，南北间距约474 m；东西间距乘cos纬度。相对早期0.25°底图线性采样细16倍，但采样间距不等于所有位置的独立地形分辨率。产品包含栅格化插值；正式模型若网格更细，不得把插值出来的细节当作新观测。[LOLA产品入口](https://pds-geosciences.wustl.edu/missions/lro/lola.htm)

当前裁片覆盖38°W–40°E、18°S–40°N，DN×0.5得到米高程，相对1737.4 km参考球，像元中心注册。地形提取和经度拼接核验见[地形溯源](sources/lola_data_provenance.json)。旧尺寸不符的float图未采用。

星号为源、三角为台站；大圆连线是地理示意，不代表散射能量只走线附近。全记录框包含该事件全部已记录站，近距候选框按文献清晰且<400 km选择。两类框都不是地质单元边界或已收敛的生产域。图上不另标不足2 km的窄小地貌；该制图要求不限制地下相关尺度a。

![全部源站与真实LOLA底图](assets/impact_station_terrain_overview.png)

![九事件全记录覆盖域](assets/nine_event_terrain_domains.png)

![八个近距候选域](assets/local_candidate_terrain_domains.png)

## 5. 21个实际配对与缺失分量

距离统一以R=1737.4 km及NASA坐标重算。保留文献距离列用于追溯，原波形图注可能仍使用文献距离，差异不能被误判成源站身份改变。缺样率范围为实际返回分量在ATT −300至3600 s展示窗内的最小—最大值；不是整日档案覆盖率。
'''
pairrows=[]
for p in joined:
 pairrows.append([p['event_id'],p['station'],fmt(p['distance_recomputed_km'],1),fmt(p['distance_published_km'],1),'清晰' if yes(p['literature_clear']) else '低SNR',p['components_present'].replace(';','/'),p['components_absent'] or '无',f'{p["raw_gap_pct_min"]:.2f}–{p["raw_gap_pct_max"]:.2f}',f'[三阶段]({p["three_stage_figure"]})'])
intro+='\n'+table(['事件','站','重算/km','文献/km','文献类别','实有分量','缺失','原始缺样/%','逐站检查图'],pairrows)
intro+='''

三条S14 MHZ缺失对应A16SIVB、A17SIVB、A17LM；没有拿其他事件/分量填补。文件存在不等于数据完整，原始缺样也不同于处理裁边；分量级63行明细见[tables/trace_stage_comparison.csv](tables/trace_stage_comparison.csv)。

## 6. 近距候选域清单

8个事件域覆盖11条首轮目标路径。一个事件的多个接收器可以由同次传播同时输出，所以配对数不等于作业数。地理框已有50 km缓冲，仍需第四册的扩域、底界与PML验证。
'''
intro+='\n'+table(['事件','目标接收器','西/东边界°E','南/北边界°N','东西×南北/km'],[[d['event_id'],d['receivers'].replace(';','、'),d['west_degE']+' / '+d['east_degE'],d['south_degN']+' / '+d['north_degN'],d['width_at_midlat_km']+' × '+d['height_km']] for d in domains])
intro+='''

## 7. 逐事件记录图册：先原始，再处理

每组先显示地形/范围，再显示未去响应DU，最后显示名义响应校正的0.3–0.9 Hz速度。原始总览为名义时间；处理总览为ATT校正时间，两者不宜直接作亚秒对齐判断。单站三阶段图使用同一ATT轴。各图不逐道归一化；纵轴刻度可能不同，应读单位和刻度。

橙色为处理边缘标记，灰色为原始缺样；短段未处理和缺失分量另列。图件是现有处理的可追溯展示，不等同最终反演准入。0.3–0.5 Hz位移参照另列链接，与速度图区分。
'''
for i,e in enumerate(events,1):
 eid=e['event_id'];ps=[p for p in pairs if p['event_id']==eid]
 intro+=f'\n### 7.{i} {eid}\n\n'
 intro+=f'地面接收时刻：{e["time_earth_received"]}；源位置：{e["lat"]}°N，{e["lon"]}°E。配对：'+ '；'.join(p['station']+f' {float(p["distance_km"]):.1f} km'+('（低SNR）' if not yes(p['nunn2024_clear']) else '') for p in ps)+'。\n\n'
 if eid in domainidx:
  dom=domainidx[eid];intro+=f'近距目标站：{dom["receivers"].replace(";","、")}；规划尺寸约{dom["width_at_midlat_km"]}×{dom["height_km"]} km。[近距图](assets/{eid}_local_terrain_domain.png)。\n\n'
 else:intro+='本事件保留远距记录，尚未列入近距首批CGFD3D域。\n\n'
 intro+=f'![{eid}撞击源、台站及LOLA覆盖域](assets/{eid}_terrain_domain.png)\n\n'
 intro+=f'**原始档案：DU，名义时间。**\n\n![{eid}原始记录](assets/{eid}_raw_archive_overview.png)\n\n'
 intro+=f'**处理预览：0.3–0.9 Hz名义速度，ATT时间。**\n\n![{eid}处理记录](assets/{eid}_processed_03_09_overview.png)\n\n'
 intro+=f'[独立0.3–0.5 Hz位移参照](assets/{eid}_literature_displacement_03_05_overview.png)；'+ '；'.join(f'[{p["station"]}三阶段](assets/{eid}_{p["station"]}_three_stages.png)' for p in ps)+'。\n'
intro+='''

## 8. 资料使用边界与下一步

本图册的“丰富记录”指当前人工撞击样本中已审计配对，不是各地貌均有均衡独立样本。S12资料最多，S16不足以开展同等自由度的局地反演；特定陨石坑的独立样本尚未成立。天然撞击、深月震及浅月震可作为扩展，但需新的震源和覆盖审计。

阅读包包含完整图件、统计表和模型规范，不复制原始MiniSEED、旧SAC、派生NPZ或大幅DEM。原始文件在工程中的路径已写入[tables/pair_record_summary_current.csv](tables/pair_record_summary_current.csv)，此前波形资料包保存可复核数据。本次整理没有改写任何观测样点。
'''
write('01_事件台站与记录图册.md',intro)

# Fill manuscript tables from machine-readable records; keep source templates idempotent.
familyrows=[]
for f in model['families']:
 familyrows.append([f['id']+' '+f['name'],f['parameters'],f['purpose'],'；'.join(f'[原文{j+1}](https://doi.org/{doi})' for j,doi in enumerate(f['source'])),f['locator'],f['status']])
replacements={
 '02_散射模型与参数设计.md':{'MODEL_FAMILY_TABLE':table(['模型','参数/结构','检验问题','来源','定义与迁移边界','阶段'],familyrows)},
 '03_波形处理与反演准入.md':{
  'GAP_EXAMPLES':table(['记录','原始缺样','旧显示空白','新显示空白','新边缘标记','短段未处理'],[[t['event_id']+'→'+t['station']+' '+t['channel'],pct(t['raw_gap_fraction']),pct(t['old_display_blank_fraction']),pct(t['new_display_blank_fraction']),pct(t['new_processing_edge_fraction']),pct(t['short_unprocessed_fraction'])] for t in traces if (t['event_id'],t['station'],t['channel']) in [('A14SIVB','S12','MHZ'),('A15LM','S15','MHZ')]]),
  'BAND_SCREEN_TABLE':table(['事件','台站','0.1–0.3 Hz','0.3–0.5 Hz','0.5–0.9 Hz','0.9–1.5 Hz'],[[b['event_id'],b['station']]+[b[k].replace('未通过本轮保守自动初筛','—').replace(';','/') for k in ['0.1-0.3','0.3-0.5','0.5-0.9','0.9-1.5']] for b in bands])},
 '04_CGFD3D模拟与验证流程.md':{'RESOURCE_TABLE':table(['事件域','Nx×Ny×Nz','节点数/十亿','32数组估算/GiB'],[[x['event_id'],f'{x["nx"]}×{x["ny"]}×{x["nz"]}',f'{x["nodes"]/1e9:.2f}',f'{x["memory_GiB_excluding_extras"]:.0f}'] for x in resource])}}
for name,repl in replacements.items():
 p=DEST/name;s=p.read_text(encoding='utf-8')
 for key,val in repl.items():
  pattern=r'<!-- '+key+r' -->(?:[\s\S]*?<!-- END_'+key+r' -->)?'
  s,n=re.subn(pattern,lambda m:'<!-- '+key+' -->\n'+val+'\n<!-- END_'+key+' -->',s,count=1)
  assert n==1,(name,key)
 if name.startswith('02_') and 'assets/model_reference_profiles.png' not in s:
  s=s.replace('## 7. 十类模型及竞争顺序','![背景、目标RMS与ACF定义示意](assets/model_reference_profiles.png)\n\n图：B0及R1/R2深度曲线为模型定义；右侧为解析指数ACF。不是已生成介质的实际统计，更不是反演结果。\n\n## 7. 十类模型及竞争顺序')
 p.write_text(s,encoding='utf-8')

# Retain existing literature evidence table without upgrading its status.
old=read('docs/12_LOLA地形底图与散射模型文献依据.md')
matrix=old.split('| 研究与原文定位 |',1)[1].split('\n\n',1)[0]
matrix='| 研究与原文定位 |'+matrix
refs=[
 ('NASA-I','NASA：Apollo撞击位置、时刻、速度与动能','https://nssdc.gsfc.nasa.gov/planetary/lunar/apollo_impact.html','数据表及注释；本次官网复核','坐标/源条件，非地震辐射能'),
 ('NASA-S','NASA：ALSEP坐标','https://nssdc.gsfc.nasa.gov/planetary/lunar/lunar_sites.html','ALSEP行；本次官网复核','源站统一参考系'),
 ('LOLA','NASA/PDS LOLA数据产品','https://pds-geosciences.wustl.edu/missions/lro/lola.htm','LDEM_64标签及本地溯源','采样约474 m，非绝对有效分辨率保证'),
 ('N22','Nunn等2022：Apollo档案恢复','https://doi.org/10.3847/PSJ/ac87af','档案方法及官方示例；已有项目核查','原始计数/时标/响应，不是全部伪信号清洗'),
 ('N24','Nunn等2024：人工撞击与三维模拟','https://doi.org/10.3847/PSJ/ad83d2','Table1/2，§2/5；已有正文核查，本轮IOP入口未成功返回','记录覆盖、0.3–0.5 Hz比较、高对比模型'),
 ('O21','Onodera等2021：二维人工撞击路径','https://doi.org/10.1029/2020JE006406','§2，Table2–3；已有正文核查','两层尺度与上限幅度，不作RMS换算'),
 ('O22','Onodera等2022：三维散射定量评估','https://doi.org/10.1029/2022JE007558','§2.2–2.6、§3.3；已有正文核查，本次出版社入口复核','两条S12路径主参考'),
 ('B14','Besserer等2014：月壳密度/孔隙度','https://doi.org/10.1002/2014GL060240','通过O22 §2.3及来源审计引用','背景依据，不是σv来源'),
 ('J15','Jiang等2015：月震散射数值模型','https://doi.org/10.6038/cjg20150519','§2–4，Table3–4；中文期刊全文已核查','二维自然月震的低σ长a竞争场景'),
 ('D77','Dainty与Toksöz1977：月球扩散包络','https://journal.geophysicsjournal.com/JofG/article/download/102/64','p385–386/Fig6；已有公开原文核查','A14LM/S14、A15LM/S15；D不等于a'),
 ('G17','Gillet等2017：深度变化散射与吸收','https://doi.org/10.1016/j.pepi.2016.11.001','扩散/衰减模型；已有核查','D、Q与过渡深度，非随机场唯一映射'),
 ('BG15G','Blanchette-Guertin等2015 GRL：侧向层厚','https://doi.org/10.1002/2015GL066151','§1–4/Fig1–3；已有正文核查','H(x,y)和源区贡献的机制证据'),
 ('BG15J','Blanchette-Guertin等2015 JGR：声子模拟','https://doi.org/10.1002/2014JE004654','Table1；已有正文核查','界面对比、厚度及Q的替代参数化'),
 ('SO16','Sollberger等2016：Apollo17浅层主动源','https://doi.org/10.1002/2016GL070883','§3–5/Fig4–5；支持材料未取得','浅部高反差；a和百分比统计定义仍有限制'),
 ('KE24','Keil等2024：浅部散射与主动源','https://doi.org/10.1029/2024EA003742','模拟部分/AppendixA；已有正文核查','a=10 m等局部高频场景，不推广到百公里域'),
 ('AM22','Amrouche等2022：浅部结构与场地','https://doi.org/10.1029/2022JE007396','§6；已有项目来源审计','浅层场地分支，非a/σ/H区域反演'),
 ('SH23','Shi等2023：散射对接收函数的影响','https://doi.org/10.1029/2022JE007676','§2–4/Fig4/6–8；ε归一化待核','长尺度分支；不直接将ε写为RMS'),
 ('Z22','Zhang等2022：全球波场浅部非均质','https://doi.org/10.1029/2022JE007222','§2–3/5；已有正文核查','最大扰动/节点尺度与物理a分开'),
 ('K25','Kim等2025：转换波与偏振','https://doi.org/10.1029/2024GL114506','§2及SI引用；SI未取得','15%统计定义未升级为RMS'),
 ('TD25','Torrent Duch等2025：S16尾波自相关','https://doi.org/10.1029/2025JE009090','§5–6；已有正文核查','弱局地散射与更锐利界面均保留'),
 ('E24','Eaton2024：熵与频率相关','https://doi.org/10.1093/gji/ggae098','§3–4/Fig9；已有正文核查','辅助统计，不给a/σ/H三元组'),
 ('O25A','Onodera等2025 LPSC会议摘要','https://www.hou.usra.edu/meetings/lpsc2025/pdf/1144.pdf','两页会议模拟；非期刊区域反演','虚拟源站的机制设计'),
 ('Z25','Zhang等2025：Methods for Cleaning Apollo Passive Seismic Data','https://doi.org/10.1029/2025EA004710','17页正文已读；SI未核实；作者代码未运行','glitch与S14采集问题，详见附录'),
 ('SE18','Sato与Emoto2018：ACF/PSD与波动散射','https://doi.org/10.1093/gji/ggy319','§2/式2a–b；已有来源审计','一般理论；地球数值不转作月球先验'),
 ('GA19','Garcia等2019：月球内部结构综述/模型','https://doi.org/10.1007/s11214-019-0613-y','模型及作者数据；新数值表未接入','独立背景；背景不确定性不是短尺度σv'),
 ('VP12','Garcia等2012：VPREMOON勘误','https://doi.org/10.1016/j.pepi.2012.03.009','Table6；已有来源审计','背景表须用勘误，QP/QS非散射Q'),
 ('Z12','Zhang等2012：曲线网格地震波数值方法','https://doi.org/10.1111/j.1365-246X.2012.05472.x','§2–5；已有方法来源审计','数值基准，不保证本项目具体网格合格'),
 ('Z14','Zhang等2014：曲线网格吸收边界','https://doi.org/10.1093/gji/ggu124','理论/测试；已有来源审计','边界方法；50 km等数值仍为项目选择')]
catalog=table(['编号','研究/入口','正文定位与当前状态','用于本项目时的限制'],[[a,f'[{b}]({c})',d,e] for a,b,c,d,e in refs])
p=DEST/'05_文献依据与论文组织.md';s=p.read_text(encoding='utf-8')
for key,val in [('LITERATURE_MATRIX',matrix),('REFERENCE_CATALOG',catalog)]:
 s,n=re.subn(r'<!-- '+key+r' -->(?:[\s\S]*?<!-- END_'+key+r' -->)?',lambda m:'<!-- '+key+' -->\n'+val+'\n<!-- END_'+key+' -->',s,count=1);assert n==1
p.write_text(s,encoding='utf-8')
csvwrite(DEST/'tables/reference_catalog.csv',[dict(id=a,description=b,url=c,evidence_status=d,scope_limit=e) for a,b,c,d,e in refs])

# Portable review appendix: map internal references to bundled sources or new volumes.
mapping={
 'docs/13_原始波形与处理对照.md':'03_波形处理与反演准入.md',
 'docs/waveform_cleaning_reference.bib':'references/waveform_cleaning_reference.bib',
 'results/impact_audit/events_and_domains.csv':'tables/events_and_domains.csv',
 'results/waveform_raw_integrity_audit.json':'sources/waveform_raw_integrity_audit.json',
 'reports/zhang2025_methods_evidence.md':'sources/zhang2025_methods_evidence.md',
 'reports/waveform_processing_literature_review.md':'sources/waveform_processing_literature_review.md',
 'data/raw/literature/Zhang2025_Cleaning_Apollo/publisher_pdf_web_extracted.txt':'sources/publisher_pdf_web_extracted.txt',
 'data/raw/literature/Zhang2025_Cleaning_Apollo/acquisition_status.json':'sources/acquisition_status.json',
 'data/raw/literature/Zhang2025_Cleaning_Apollo/crossref_metadata.json':'sources/crossref_metadata.json'}
def portable_md(src,dst):
    import os
    raw=read(src)
    def sub(m):
        label,target=m.groups()
        if target.startswith(('https:','http:','#')):return m.group(0)
        rel=(ROOT/Path(src).parent/target).resolve().relative_to(ROOT).as_posix()
        if rel in mapping:
            path=os.path.relpath(DEST/mapping[rel],(DEST/dst).parent).replace('\\','/')
            return f'[{label}]({path})'
        return label+'（原工程路径：`'+rel+'`）'
    raw=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',sub,raw)
    write(dst,raw)
portable_md('docs/14_Zhang2025_Apollo数据清洗论文综述.md','附录_Zhang2025数据清洗论文综述.md')
portable_md('reports/zhang2025_methods_evidence.md','sources/zhang2025_methods_evidence.md')
portable_md('reports/waveform_processing_literature_review.md','sources/waveform_processing_literature_review.md')

# An index is a reading guide, not a replacement for the complete volumes.
index='''# 月球散射强度评估｜完整研究设计总册

综合版：2026-10-29。研究单位为真实撞击事件、实际接收站、传播域及合格时窗。求解器沿用CGFD3D，运行配置待接入；新正式传播计算0项，未产生最优散射模型结论。

## 1. 这一套文档解决什么问题

这套资料将零散版本统一为可独立阅读的设计：先列清楚哪些撞击被哪些台站记录，给出地形底图、源站距离、实际波形和缺失项，再说明怎样处理并选择可信频段，最后定义带文献依据的散射介质、计算矩阵、验证方法与论文结构。此前地形必要性试验作为动机，不替代本轮真实资料与模型验证。

## 2. 建议阅读顺序

| 文档 | 完整内容 | 适合解决的问题 |
|---|---|---|
| [合订本](月球散射研究设计_完整合订本.md) | 本导读、五册正文及Zhang2025附录 | 希望连续阅读或另存一份完整材料 |
| [第一册：事件台站与记录图册](01_事件台站与记录图册.md) | 9事件、4台站、21配对、坐标/距离/源条件、LOLA域、逐事件原始和处理图 | 到底有哪些观测、在哪里、记录如何 |
| [第二册：散射模型与参数设计](02_散射模型与参数设计.md) | 背景公式、ACF/PSD、a/σ/H、深度/地形、10类模型、源/Q和耦合 | 每一个参数为何这样设、哪些有直接文献约束 |
| [第三册：波形处理与准入](03_波形处理与反演准入.md) | 原始保全、时标、响应、滤波、缺口、旧频带初筛、清洗与指标 | 哪些曲线可看、哪些量真正可以进入反演 |
| [第四册：CGFD3D模拟与验证](04_CGFD3D模拟与验证流程.md) | 接口、曲率、网格/算力、64项事件基线、旧88项关系、收敛与留出 | 如何把设计变成可信模拟，怎样挑选可接受模型 |
| [第五册：文献与论文组织](05_文献依据与论文组织.md) | 证据矩阵、28项编号入口、地貌约束、论文主线与扩样 | 怎样写论证，哪些结论不能提前下 |
| [附录：Zhang2025综述](附录_Zhang2025数据清洗论文综述.md) | 17页正文方法、S14问题、样本分母、图页导读及迁移限制 | 如何理解并应用清洗论文 |

## 3. 已完成、已规划和待接入

| 项目 | 当前状态 |
|---|---|
| 人工撞击覆盖 | 9事件、21配对；文献16清晰/5低SNR；S12/S14/S15/S16分别9/6/4/2事件 |
| 实际分量 | 63个候选中周期位置中60条存在；3条S14 MHZ未返回 |
| 地形 | LOLA LDEM_64原生裁片及20幅地形PNG；高程/经度/来源已记录 |
| 波形展示 | 50幅原始、处理、位移、三阶段及缺口图；原始计数逐点核对 |
| 最终质量准入 | 尚未签发；旧240项频带检查30项初筛通过，未按新版处理重算 |
| 材料预览 | 3个小体积NetCDF，非源站完整域、非生产输入 |
| 运行计划 | 本册新增64项事件级基线，首批16项是其子集；旧88项另有有限范围 |
| 正式模拟/最优模型 | 新传播0项；没有区域最优参数或后验结果 |

## 4. 最重要的模型选择

主起点采用S12两条人工撞击三维研究启发的各向同性指数场：a=0.65 km、σv=10%、强扰动深度约10 km。新设计将H明确为1 km余弦渐消的中心，固定密度作为首轮控制，βρ=0.8作为敏感性分支。主比较先选0.3–0.5 Hz，只有逐道/分窗质控允许才扩展到0.5–0.9及0.9–1.5 Hz。

a=0.2–2 km、σv=2%–15%、H=3.5–20 km是围绕文献的项目搜索包络，不是四个区域已测得的范围。先检验共享统计结构，再检查有限的路径差异；S15及S16资料量不同，不强行给所有地貌同样数量的自由参数。

本册保留背景、地形、源、场地、Q、随机实现与处理误差这些竞争解释。S12/S14联合时共享同事件源参数，接收站和场地项保留独立。高地不预设最强散射；特定陨石坑尚未形成独立样本。

## 5. 第一轮执行顺序

1. 在原始DU域复核两条S12参考路径，补充内部削顶和孤立glitch检查，冻结最终可用分量/子带/时窗。
2. 用真实CGFD3D配置完成单位、源、坐标、自由表面和均匀/分层基准，再接入LOLA及随机介质。
3. 先完成参考事件的16项基线与数值收敛；再按需要执行旧参数筛查的规范化版本，探索联合参数权衡。
4. 预测未参与拟合的S12事件和S12/S14共同事件，随后扩展S15，最后在合适几何中检验远距与S16。
5. 根据独立预测与可辨识性报告可接受参数集合或界限，再组织区域地质解释与论文。

这些阶段按完成条件推进，不在运行配置和实测性能未知时虚构日程或总耗时。

## 6. 如何使用本包

Markdown正文与assets中的PNG共同构成可移交的阅读材料，移动或解压时保留目录关系。tables含完整事件、台站、配对、频带、模型来源、作业清单和资源估算；sources含关键核验和论文正文提取文本；references保留BibTeX。图件直接来自本项目真实资料或明确标记的模型公式示意。

本包是设计与证据阅读包，不是全部原始数据仓库：不含MiniSEED/SAC/派生NPZ/大幅DEM/CGFD3D程序和真实运行配置。原始工程路径列在配对表，工程中此前的数据资料包仍有效。任何本文的候选清洗或模型测试都不能被记作已完成实验。
'''
write('00_阅读指南与总体方案.md',index)

# Source manifest supports traceability without distributing the large input archives.
manifest=[]
for rel in copylist+['docs/12_LOLA地形底图与散射模型文献依据.md','docs/13_原始波形与处理对照.md','docs/14_Zhang2025_Apollo数据清洗论文综述.md','config/scattering_model_design_v2_annotated.json','code/build_scattering_models.py','code/build_waveform_stage_comparison.py']:
 p=ROOT/rel;manifest.append({'source_project_path':rel,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
write('sources/input_source_manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))

order=['00_阅读指南与总体方案.md','01_事件台站与记录图册.md','02_散射模型与参数设计.md','03_波形处理与反演准入.md','04_CGFD3D模拟与验证流程.md','05_文献依据与论文组织.md','附录_Zhang2025数据清洗论文综述.md']
combined='# 月球散射强度评估：模型设计、观测记录与实施流程完整合订本\n\n2026-10-29｜所有图件相对路径与分册共用。正式CGFD3D传播尚未执行。\n\n'
for name in order:
 s=(DEST/name).read_text(encoding='utf-8')
 s=re.sub(r'^(#{1,5}) ',lambda m:m.group(1)+'# ',s,flags=re.M)
 s=re.sub(r'<!--[^>]*-->', '',s)
 combined+='\n\n---\n\n'+s
write('月球散射研究设计_完整合订本.md',combined)

print(json.dumps({'folder':str(DEST),'events':len(events),'pairs':len(pairs),'trace_slots':len(traces),'real_traces':sum(yes(t['archive_channel_present']) for t in traces),'new_jobs':len(jobs),'first_subset':sum(x['first_stage'] for x in jobs),'new_job_status':sorted(set(j['status'] for j in jobs)),'station_S12_S14_distance_km':sep,'combined_characters':len(combined),'pngs':len(list((DEST/'assets').glob('*.png')))},ensure_ascii=False,indent=2))
