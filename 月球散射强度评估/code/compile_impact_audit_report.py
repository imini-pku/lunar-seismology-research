"""Join verified event geometry, public file inventory, and literature evidence."""
from pathlib import Path
import csv,json
ROOT=Path(__file__).resolve().parents[1]
def read(p):
    with (ROOT/p).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def write(p,rows):
    with (ROOT/p).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def md(rows,cols):
    return '| '+' | '.join(x[1] for x in cols)+' |\n|'+'|'.join(['---']*len(cols))+'|\n'+'\n'.join('| '+' | '.join(str(r.get(k,'')) for k,_ in cols)+' |' for r in rows)
def main():
    es=read('results/impact_audit/events_and_domains.csv');ps=read('results/impact_audit/event_station_domains.csv')
    inv=read('results/impact_waveform_inventory.csv');dls=read('results/impact_event_station_download_summary.csv')
    di={(r['event_id'],r['station']):r for r in dls}
    rows=[]
    for p in ps:
        dl=di[p['event_id'],p['station']];fr=[r for r in inv if r['event_id']==p['event_id'] and r['station']==p['station']]
        lp=[r for r in fr if r['component'].startswith('LP')]
        badz=p['station']=='S14' and p['event_id'] in ['A16SIVB','A17SIVB','A17LM']
        rows.append({**p,'downloaded_components':dl['downloaded_components'],'downloaded_files':len(fr),
         'LP_min_duration_min':round(min(float(r['duration_s']) for r in lp)/60,1),
         'LP_max_duration_min':round(max(float(r['duration_s']) for r in lp)/60,1),
         'display_component':'LPX' if badz else 'LPZ',
         'published_common_comparison_band_Hz':'0.3-0.5',
         'published_candidate_band_Hz':'0.3-0.9',
         'published_path_extension_band_Hz':'0.3-1.5' if p['station']=='S12' and p['event_id'] in ['A14SIVB','A16SIVB'] else '',
         'band_evidence':'literature; not a certification of every archived component',
         'excluded_components':'LPZ/MHZ faulty epoch' if badz else 'SPZ/SHZ failed sensor' if p['station']=='S12' else '',
         'legacy_physical_units':'not verified; do not repeat deconvolution',
         'source_records':'results/impact_waveform_inventory.csv','geometry_source':p['geometry_source']})
    write('results/impact_audit/combined_event_station_audit.csv',rows)
    sts=[]
    for s in ['S12','S14','S15','S16']:
        pp=[p for p in rows if p['station']==s]
        sts.append({'station':s,'pairs':len(pp),'literature_clear':sum(str(p['nunn2024_clear']).lower()=='true' for p in pp),
                    'downloaded_files':sum(p['downloaded_files'] for p in pp),'min_distance_km':min(float(p['distance_km']) for p in pp),
                    'max_distance_km':max(float(p['distance_km']) for p in pp)})
    write('results/impact_audit/station_summary.csv',sts)
    evdisplay=[]
    for e in es:
        pp=[p for p in rows if p['event_id']==e['event_id']]
        evdisplay.append({'event':e['event_id'],'time':e['time_earth_received'].replace('T',' '),'coord':f"{e['lat']}, {e['lon']}",
          'stations':'；'.join(p['station']+('†' if str(p['nunn2024_clear']).lower()!='true' else '') for p in pp),
          'distance':'；'.join(p['station']+': '+p['distance_km'] for p in pp),'files':sum(p['downloaded_files'] for p in pp)})
    body='''# 人工撞击事件、接收台站、实际记录与模拟范围审计

2026-10-29。本轮按“事件—有记录的台站—实际文件—可用分量与频带—模拟范围—参考散射模型”的顺序重建研究入口。范围是九次 Apollo 人工撞击；不是所有天然撞击或深月震的完整审计。

## 已确认的数据范围

实际取得 JAXA DARTS 的81个压缩原件及其81个SAC解压文件，覆盖9事件、21个事件—台站组合，包括63个LP分量和18个SP分量。每个文件的下载地址、SHA256、头段、起止时间、采样间隔及异常统计见[完整分量清单](../results/impact_waveform_inventory.csv)。文件存在不保证通道有效。

[Nunn et al. 2024 §2/Table1/Fig1](https://doi.org/10.3847/PSJ/ad83d2) 对同样的21个组合，展示16个清晰记录，另5个标记低信噪比。下文†表示该文低信噪比，属于文献判定，不能冒充本轮反演合格数。S14在1972年的MHZ故障；有旧SAC文件也不得作为可用Z分量。

'''+md(sts,[('station','台站'),('pairs','已记录事件数'),('literature_clear','文献清晰数'),('downloaded_files','已下载分量文件'),('min_distance_km','最短距离/km'),('max_distance_km','最长距离/km')])+'''

## 事件时刻、位置与台站

源坐标取[NASA撞击位置表](https://nssdc.gsfc.nasa.gov/planetary/lunar/apollo_impact.html)，台站取[NASA ALSEP坐标](https://nssdc.gsfc.nasa.gov/planetary/lunar/lunar_sites.html)，使用月球半径1737.4 km重算球面震中距。纬度为北正、经度为东正，负经度为西经。SIVB位置已包含LRO更新，LM遗留位置的精度较低，保留其原始有效位数。

时刻是NASA表中的**地面接收时刻**，约比月面实际时刻晚1.3 s；A16 SIVB时刻估计误差约±4 s。未将这个1.3 s盲目重复施加给已有档案。原SAC头的O标记和旧坐标另外保留。

'''+md(evdisplay,[('event','事件'),('time','NASA地面接收时刻/UT'),('coord','纬度, 经度/°'),('stations','有记录台站'),('distance','重算距离/km'),('files','分量文件数')])+'''

![撞击事件与接收台站](../figures/impact_audit/impact_station_overview.png)

A16 SIVB发生时S16尚未部署；不能因任务编号为A16就把它算到S16高地区域。相同原则适用于A15 SIVB与S15。

## 每次模拟的地理范围

这里提供两层框：

1. **全部记录覆盖框**：逐事件含所有已记录台站，包括远距和低信噪比台站，用于核对覆盖是否遗漏；不作为九个已经定稿的生产计算域。
2. **局部模拟候选框**：取文献清晰且震中距<400 km的11条路径，按同一事件合并接收点，得到8个局部候选框。400 km是本轮计算规划阈值，不是物理定律。最终是否入选还取决于响应、饱和、时间和频带核验。

两种框均沿球面大圆路径采样后取包围框，并在各方向加约50 km缓冲；框住的是计算覆盖，不是地貌或地质单元。50 km也不是经过验证的尾波吸收边界。全波模拟仍需扩大横向范围、底界和PML作收敛检验；长尾横向传播可能要求更宽域。

![全部记录覆盖框](../figures/impact_audit/nine_event_simulation_domains.png)

![局部模拟候选框](../figures/impact_audit/local_candidate_simulation_domains.png)

逐事件全部框：[events_and_domains.csv](../results/impact_audit/events_and_domains.csv)；逐事件—台站配对框：[event_station_domains.csv](../results/impact_audit/event_station_domains.csv)；局部候选框：[local_simulation_candidates.csv](../results/impact_audit/local_simulation_candidates.csv)。均保存经纬度上下限、几何宽高、缓冲及用途。

例如A15 LM的全记录框包含S12/S14两个千公里级低信噪比接收点，约915×1010 km；近站S15的局部候选框约193×107 km。A16 SIVB对S15的1100 km路径应放入远距验证，不能迫使S12/S14的局部试验使用整个巨大覆盖框。

## 具体记录与显示方式

每事件的完整分量原图与0.3–0.9 Hz显示滤波图均在[figures/impact_audit](../figures/impact_audit)。紧凑图每站选一个代表分量：优先LPZ，1972年S14改LPX。原始图和筛查表保留所有分量，不因缺陷删除档案证据。

旧DARTS SAC头既有IDISP也有IVEL标志，但处理历史和单位未完全核定，故显示图统一用“归一化档案振幅”，**不是已认证的m或m/s**。逐道归一化只能比较形态，不能用来比较台站间绝对幅度或三分量能量。不能把新StationXML直接套在这些旧SAC上再次去响应。

详细记录汇总：[combined_event_station_audit.csv](../results/impact_audit/combined_event_station_audit.csv)。全长LP文件约128–269分钟，图示首3600秒不是原档案的全部时长；末段恒值填充与早期分析窗已分开统计。

## 台站有效频带：可用结论与核验边界

| 台站/通道 | 文献支持的首轮带 | 可检验扩展 | 必须排除或核对 |
|---|---|---|---|
| S12 MP三分量 | 0.3–0.5 Hz | 合格记录0.5–0.9 Hz；A14/A16 SIVB两路径文献曾用0.3–1.5 Hz | SHZ全任务失效；源前量化噪声、近距削顶、水平轴180°/270° |
| S14 MP | 0.3–0.5 Hz | 合格的水平或1971年三分量扩至0.9 Hz | 1972-03-12至1976-11-17 MHZ故障；若干LPY台阶/饱和风险 |
| S15 MP三分量 | 0.3–0.5 Hz | 各记录分别检验0.5–0.9 Hz | A15 LM近站与千公里远路径分开；增益/缺口/时钟 |
| S16 MP三分量 | 0.3–0.5 Hz | A17 SIVB记录检验0.5–0.9 Hz | A17 LM低SNR；长路径不可等同局地高地参数 |

“有效频带”不是台站固定标签。0.3–0.5 Hz来自Nunn2024的统一波形比较；0.3–0.9 Hz是该文总体良好SNR范围，不表示21对每分量和每个晚时窗都通过。Onodera2022的0.3–1.5 Hz只对应两条S12路径。[仪器审计](../reports/instrument_band_agent.md)保存响应、采样、工作模式及校准来源。

MP名义采样率6.625 Hz，Nyquist3.3125 Hz；SP名义53 Hz，Nyquist26.5 Hz。Nyquist不能当作有效滤波上限。PDS StationXML中名义响应epoch甚至覆盖失效通道，因此也不能据此推断通道一直正常。

旧SAC的前噪声常为粗量化信号并有脉冲，自动PSD比会虚高。本轮对五个子带保存Welch谱比，并加入噪声窗/极值/故障警报；[频谱初筛表](../results/impact_waveform_spectral_screen.csv)中的失败只表示未通过该自动认证规则，**不表示文献记录不存在或整条没有科学价值**。现代原始档案的响应校正结果与局限另存，最终反演准入需逐事件、台站、分量及时间窗决定。

## 区域参考散射参数

| 适用路径/模型 | 空间相关尺度a | 速度扰动强度 | 扰动深度 | 证据范围 |
|---|---|---|---|---|
| A14/A16 SIVB→S12，Onodera2022 | 0.65 km，指数自相关 | 生成速度场1σ=5%–10% | 优选强扰动至约10 km | 两条真实S12路径的直接三维参考，不是S14/S16的反演 |
| 同两路径，Onodera2021 | 上层0.2、下层0.6 km | “最高”28%/14%，不直接转成RMS | 上层7.5 km；总深度南10、北20 km | 二维P–SV及其分析窗口条件 |
| S12/S14附近联合、A15 LM→S15局部 | 以0.65 km作迁移起点 | 以5%–10%作迁移起点 | 以10 km作迁移起点 | 需要当前路径数据重新检验，无四区域独立实测三元组 |
| 多路径深层竞争模型，Nunn2024 | 无独立固定物理a，节点尺度受网格影响 | 最大±50%，不是σ=50% | 幅度线性减至20/50/80 km为零 | 全球/远距竞争分支；局部近距仍失配 |
| S16接收路径 | 尚无本组数据独立确定值 | 尚无独立值 | 尚无独立值 | 850–985 km路径混合源区、沿途结构和场地效应 |

数值与定义按原文分别保留，不能合并成“各区域散射5%–50%”。完整证据表见[文献审计](../reports/impact_literature_agent.md)与[按路径的模型设计](11_按撞击路径约束的散射模型设计.md)。Gillet扩散系数、平均自由程、散射Q与随机介质相关尺度a不直接互换；Amrouche的几十米低速场地层也不是公里尺度随机散射层。

## 后续顺序

先完成已下载记录的处理一致性，再复现A14/A16 SIVB→S12；用A14 LM、A15 SIVB等同源多站记录约束S12/S14差异；单独建立A15 LM→S15的近距模型；S16先作长路径预测检验，同时补充更靠近S16、定位可信的天然撞击。

首轮只开放a、速度扰动标准差和深度三个主参数；固定源与背景做敏感性，再逐步检验背景梯度、吸收、各向异性和局部场地层。每个模型用多个随机实现；按完整事件留出，避免同一撞击的不同台站泄漏。LM与SIVB冲击角不同，必须分别建源。

前版88个运行只是两条S12路径的试验子集，本轮不把它们当作四个区域已落实的完整计划。当前新的CGFD3D传播运行数仍为0；需收到用户准备提供的运行配置，并通过域、网格和波形检查后才能给出最佳模型。
'''
    (ROOT/'docs/10_撞击事件台站与模拟域审计.md').write_text(body,encoding='utf8')
    print(json.dumps({'events':len(es),'pairs':len(rows),'station_summary':sts},ensure_ascii=False))
if __name__=='__main__':main()
