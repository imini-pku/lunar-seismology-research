from pathlib import Path
import json,csv,hashlib,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'docs/研究设计总册_20261029'; OUT=D/'三台站区域模型';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.sans-serif':['Microsoft YaHei'],'axes.unicode_minus':False,'font.size':10})
def readcsv(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
stations={x['station']:x for x in readcsv(ROOT/'results/impact_audit/stations.csv')}
events={x['event_id']:x for x in readcsv(ROOT/'results/impact_audit/events_and_domains.csv')}
pairs=readcsv(ROOT/'results/impact_audit/event_station_domains.csv')
dem=np.load(ROOT/'data/raw/lola_impact_64/ldem_64_W38_E40_S18_N40_native.npz')
lon,lat=dem['longitude_degE'],dem['latitude_degN'];dn=dem['dn'];scale=float(dem['height_scale_m'])/1000
raw=ROOT/'data/raw/background_models/MoonGarcia_PEPI_2011.nd'
rows=[]
for l in raw.read_text().splitlines():
    try:
        a=list(map(float,l.split()))
        if len(a)==6 and a[0]<=110:rows.append(a)
    except ValueError:pass
bg=np.array(rows)
def height(la,lo):
    la=np.atleast_1d(la);lo=np.atleast_1d(lo)
    i=np.abs(lat[:,None]-la).argmin(axis=0);j=np.abs(lon[:,None]-lo).argmin(axis=0)
    return dn[i,j]*scale
def track(e,s,n=350):
    def xyz(x):
        a,b=np.deg2rad([float(x['lat']),float(x['lon'])]);return np.array([np.cos(a)*np.cos(b),np.cos(a)*np.sin(b),np.sin(a)])
    u,v=xyz(e),xyz(s);ang=np.arccos(np.clip(u@v,-1,1));t=np.linspace(0,1,n)
    q=(np.sin((1-t)*ang)[:,None]*u+np.sin(t*ang)[:,None]*v)/np.sin(ang)
    la=np.rad2deg(np.arcsin(q[:,2]));lo=np.rad2deg(np.arctan2(q[:,1],q[:,0]))
    return t*ang*1737.4,la,lo
def T(d,c,w):return .5*(1+np.cos(np.pi*np.clip((d-c+w/2)/w,0,1)))
def sigma(d,H=10,b=5/9,s=.09,dm=28):return (.01+(b*s-.01)*T(d,H+2.5,5)+(s-b*s)*T(d,H/2,1))*T(d,dm-.5,1)
info={
 'S12':{'title':'月海邻域','section':'A16SIVB','train':['A14SIVB','A16SIVB','A15SIVB'],'holdout':['A12LM','A13SIVB','A14LM','A17SIVB'],'constraint':'Kim2025局地壳厚32.2±6.7 km、平均Vs=2.6±0.4 km/s；Onodera2022对A14/A16 SIVB→S12给出直接三维散射建模参照。','note':'文献约束最直接，优先拟合多事件，并用另外4个事件检查预测。'},
 'S14':{'title':'Fra Mauro喷出物／破碎高地区域','section':'A14LM','train':['A15SIVB','A16SIVB'],'holdout':['A14LM'],'constraint':'当前已核查资料尚未汇齐独立的完整局地Vp/Vs/ρ/Q层表；不能把S12局地参数直接当作S14已知值。','note':'A16SIVB→S14仅合格水平分量参与；A14LM作为独立事件检查。'},
 'S15':{'title':'Hadley–Apennine盆地边缘区域','section':'A15LM','train':['A15LM'],'holdout':[],'constraint':'Kim2025局地壳厚29.4±6.0 km、平均Vs=2.2±0.3 km/s；仍不足以唯一重建完整速度/密度/Q剖面。','note':'近距候选仅1个事件，不能把不同种子当作独立事件；优先报告条件范围。'}
}
summary=[]
for sid,m in info.items():
    st=stations[sid];sp=[p for p in pairs if p['station']==sid and p['domain_role']=='local_candidate_pending_QC']
    assert len(sp)=={'S12':7,'S14':3,'S15':1}[sid]
    w=min(float(p['west_degE']) for p in sp);e=max(float(p['east_degE']) for p in sp)
    so=min(float(p['south_degN']) for p in sp);no=max(float(p['north_degN']) for p in sp)
    hs=float(height(float(st['lat']),float(st['lon']))[0]);dm=28+hs
    dist,slat,slon=track(events[m['section']],st);h=height(slat,slon)
    fig=plt.figure(figsize=(16,10),layout='constrained');gs=fig.add_gridspec(2,6,height_ratios=[1,1.05])
    axmap=fig.add_subplot(gs[0,:3]);axsec=fig.add_subplot(gs[0,3:])
    axs=[fig.add_subplot(gs[1,0:2]),fig.add_subplot(gs[1,2:3]),fig.add_subplot(gs[1,3:4]),fig.add_subplot(gs[1,4:6])]
    il=np.flatnonzero((lat>=so-.25)&(lat<=no+.25))[::2];jl=np.flatnonzero((lon>=w-.25)&(lon<=e+.25))[::2]
    im=axmap.pcolormesh(lon[jl],lat[il],dn[np.ix_(il,jl)]*scale,cmap='terrain',vmin=-5,vmax=5,shading='nearest',rasterized=True)
    for k,p in enumerate(sp,1):
        ev=events[p['event_id']];_,la,lo=track(ev,st)
        axmap.plot(lo,la,color='#8b244c',lw=.8,alpha=.85)
        axmap.scatter(float(ev['lon']),float(ev['lat']),marker='o',s=25,facecolor='white',edgecolor='black',zorder=4)
        axmap.annotate(str(k),(float(ev['lon']),float(ev['lat'])),xytext=(5,6),textcoords='offset points',fontsize=10,fontweight='bold',bbox={'fc':'white','ec':'none','alpha':.75,'pad':.5},zorder=6)
    axmap.scatter(float(st['lon']),float(st['lat']),marker='^',s=95,c='red',edgecolors='white',zorder=5)
    axmap.annotate(sid,(float(st['lon']),float(st['lat'])),xytext=(7,-14),textcoords='offset points',fontweight='bold',bbox={'fc':'white','ec':'none','alpha':.8},zorder=7)
    axmap.add_patch(Rectangle((w,so),e-w,no-so,fill=False,ec='#222222',ls='--',lw=1.2))
    axmap.set(xlim=(w-.25,e+.25),ylim=(so-.25,no+.25),xlabel='经度 (°E)',ylabel='纬度 (°N)',title=f'(a) 实际LOLA地形与{len(sp)}条候选路径')
    axmap.set_aspect(1/np.cos(np.deg2rad((so+no)/2)))
    fig.colorbar(im,ax=axmap,label='参考球面高程 (km)',shrink=.85,pad=.02)
    for upper,lower,c,label in [(-h,1-h,'#f1d4a5','表层'),(1-h,12,'#e4bda7','上月壳'),(12,28,'#bcb4d1','下月壳'),(28,40,'#d2d6cd','月幔')]:
        axsec.fill_between(dist,upper,lower,color=c,label=label)
    axsec.plot(dist,-h,'k',lw=1);axsec.plot(dist,10-h,'--',color='#0072B2',label='H=10 km（散射）')
    axsec.text(0,-4,m['section'],ha='left',fontsize=10);axsec.text(dist[-1],-4,sid,ha='right',fontsize=10)
    axsec.set(xlim=(0,dist[-1]),ylim=(40,-7),xlabel='源—站大圆路径距离 (km)',ylabel='参考球面以下深度 (km)',title='(b) 代表路径：真实地形＋固定背景分层')
    axsec.legend(loc='lower left',ncol=3,fontsize=8)
    for i,(ax,cols,labels,xlabel) in enumerate(zip(axs[:3],[[1,2],[3],[4,5]],[['Vp','Vs'],['ρ'],['Qp','Qs']],['速度 (km/s)','密度 (g/cm³)','本征Q'])):
        for col,label,style in zip(cols,labels,['-','--']):ax.plot(bg[:,col],bg[:,0],style,label=label,lw=1.8)
        ax.set(ylim=(100,0),xlabel=xlabel,title=['(c) 固定速度','(d) 固定密度','(e) 固定Q'][i])
        if i==0:ax.set_ylabel('参考柱深度 (km)')
        else:ax.tick_params(labelleft=False)
        ax.grid(alpha=.2);ax.axhline(28,color='gray',ls=':',lw=.8);ax.legend(fontsize=9)
        if i==2:ax.set_xticks([4000,6750,9000]);ax.tick_params(axis='x',rotation=45)
    dd=np.linspace(0,35,1001)
    for H,col,style in zip([5,10,20],['#999999','#0072B2','#D55E00'],[':','-','--']):
        axs[3].plot(sigma(dd,H=H,dm=dm)*100,dd,style,color=col,lw=2,label=f'H={H} km')
    axs[3].axhline(dm,color='black',ls=':',lw=.8)
    axs[3].set(ylim=(35,0),xlabel='相对速度标准差 (%)',ylabel='当地地表以下深度 (km)',title=f'(f) {sid}独立待拟合的深度参数')
    axs[3].legend(fontsize=9);axs[3].grid(alpha=.2)
    fig.text(.5,.985,f'M-{sid}｜{m["title"]}',ha='center',va='top',fontsize=18)
    fig.text(.5,.945,'背景与地形固定；散射参数独立搜索（当前为设计输入，未反演）',ha='center',va='top',fontsize=13)
    fig.text(.5,.002,'来源：PDS LOLA LDEM_64；Garcia 2011/2019归档；散射函数参考Onodera 2022方法并由项目定义。\n(c–e)为h=0参考柱；(f)示例σ0=9%、b=5/9，使用本站高程；(b)垂向夸大。数字对应区域文档中的事件表。',ha='center',fontsize=9)
    fig.get_layout_engine().set(rect=(0,.06,1,.83))
    png=OUT/f'{sid}_区域模型总图.png';fig.savefig(png,dpi=170);plt.close(fig)
    with (OUT/f'{sid}_背景参数.csv').open('w',encoding='utf-8-sig',newline='') as f:
        wr=csv.writer(f);wr.writerow(['reference_depth_km','Vp_km_s','Vs_km_s','rho_kg_m3','Qp','Qs']);xx=bg.copy();xx[:,3]*=1000;wr.writerows(xx)
    with (OUT/f'{sid}_代表路径地形.csv').open('w',encoding='utf-8-sig',newline='') as f:
        wr=csv.writer(f);wr.writerow(['distance_km','lat','lon','height_km']);wr.writerows(zip(dist,slat,slon,h))
    spec={'region':sid,'model_id':'M-'+sid,'scope':'separate station-labelled effective model, not a shared W parameter vector','status':'DESIGN_NOT_INVERTED_NOT_PRODUCTION_INPUT','station':{'lat':float(st['lat']),'lon':float(st['lon']),'lola_height_km':hs},'planning_bounds_deg':[w,e,so,no],'bounds_note':'union of 50km buffered pair extents, not station-local geology boundary or validated PML extent','background':{'origin':'Garcia2011 archived by Garcia2019','table':f'{sid}_背景参数.csv','source_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'same_fallback_as_other_regions':True,'surface':'LOLA','interfaces':'surface depth1 km; reference depth12 and28 km','Q_interpolation':'linear between original nodes; no smoothing across repeated-depth jumps'},'scattering':{'parameter_id':f'theta_{sid}','independent_of_other_station_parameters':True,'family':'3D von Karman','nu':.5,'initial':{'a_km':4.5,'sigma0':.09,'b':5/9,'H_km':10},'a_search_km':[.2,.65,1.3,2,4.5,6],'sigma0_search':[.05,.09,.1,.15],'b_search':[5/9,.85,1],'H_search_km':[3.5,5,10,20],'weak_sigma':.01,'estimated_parameters':None},'train':m['train'],'holdout':m['holdout'],'pairs':[p['pair_id'] for p in sp],'reference_section':m['section']+'_'+sid,'local_evidence':m['constraint']}
    (OUT/f'{sid}_模型定义.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
    tab='\n'.join(f'| {k} | {p["event_id"]} → {sid} | {float(p["distance_km"]):.2f} | '+('训练' if p['event_id'] in m['train'] else '独立事件检查')+' | '+('仅合格水平分量' if p['pair_id']=='A16SIVB_S14' else '逐分量质控后准入')+' |' for k,p in enumerate(sp,1))
    text=f'''# M-{sid}｜{m['title']}模拟模型

版本：2026-11-05，三台站独立交付版。该模型拥有独立的θ_{sid}=(a_{sid},σ0_{sid},b_{sid},H_{sid})。当前给出固定背景和候选散射输入，未获得最优反演结果；S12/S14不再强制共享参数。

![{sid}区域模型总图]({sid}_区域模型总图.png)

## 1. 本区覆盖及观测

站位：({float(st['lon']):.5f}°E，{float(st['lat']):.5f}°N)。LOLA原生像元近邻高程约{hs:.3f} km（参考球R=1737.4 km），不是本轮新测量。

本区当前有{len(sp)}条近距候选记录。图中虚线框是各路径50 km缓冲框的并集包络，范围为经度{w:.5f}至{e:.5f}°E、纬度{so:.5f}至{no:.5f}°N。它覆盖震源与台站，不是以台站为中心的实测地质边界；实际生产域还须通过尾波边界检查。

| 图中编号 | 事件—台站 | 距离/km | 用途 | 分量说明 |
|---|---|---:|---|---|
{tab}

{m['note']} 本区参数描述这些记录能约束的有效介质，不将全部散射解释为本站正下方。图(b)沿{m['section']}→{sid}展示，其他事件仍各自使用真实地形与域，不能把这张剖面挤出成全部三维结构。

## 2. 固定背景：Vp、Vs、密度、Q及地下界面

{m['constraint']} 目前仍采用Garcia2011完整月球平均后备背景；本区没有通过人为改变几个数来制造“独有模型”。这些局地约束不会被自动平铺成整个走廊的实测结构。

| 参考深度/节点 | Vp km/s | Vs km/s | 密度 kg/m³ | Qp | Qs |
|---|---:|---:|---:|---:|---:|
| 0–1 km | 1.00 | 0.50 | 2600 | 6750 | 6750 |
| 1–12 km | 3.20 | 1.80 | 2762 | 6750 | 6750 |
| 12–28 km | 5.50 | 3.30 | 2762 | 6750 | 6750 |
| 28 km下侧 | 7.54 | 4.34 | 3312 | 6750 | 6750 |
| 40 km | 7.55 | 4.34 | 3314 | 6750 | 6750 |
| 65.4 km | 7.57 | 4.35 | 3318 | 9000 | 4000 |
| 90 km | 7.59 | 4.36 | 3322 | 9000 | 4000 |
| 110 km | 7.61 | 4.37 | 3325 | 9000 | 4000 |

表格为h=0参考柱；本区三维界面严格定义为：自由表面r=R+h；表层底r=R+h−1 km；上/下月壳界面r=R−12 km；莫霍r=R−28 km。本站局地地表到后备莫霍约{dm:.3f} km，这个数由后备几何与LOLA推算，不是本站壳厚测量。连续月幔段使用原始节点线性插值；Q代表本征吸收，不能加上散射Q重复衰减。图(c–e)统一画参考柱，避免把地形坐标变化误认为背景材料差别。

[本区完整背景CSV]({sid}_背景参数.csv)；[模型定义JSON]({sid}_模型定义.json)；[代表路径原生地形采样]({sid}_代表路径地形.csv)。CSV密度已转为kg/m³。来源：[Garcia2011](https://doi.org/10.1016/j.pepi.2011.06.015)、[Garcia2019归档](https://zenodo.org/records/21476963)。

## 3. 本区独立散射参数

统一三维冯卡尔曼，ν固定0.5；Vp/Vs使用同一个零均值相对扰动场，密度/Q固定。ν是本次明确设计选择，不是已经核定的旧生产ν。起点为a=4.5 km、σ0=9%、b=5/9、H=10 km。

| 参数 | 本区候选 |
|---|---|
| a_{sid} | 0.2、0.65、1.3、2、4.5、6 km |
| σ0_{sid} | 5%、9%、10%、15% |
| b_{sid} | 5/9、0.85、1 |
| H_{sid} | 3.5、5、10、20 km |

名义深度函数：0–H/2为σ0，H/2–H为bσ0，H–H+5 km余弦过渡到1%，更深保持1%并在固定莫霍上方最后1 km降为0；中间分界平滑宽1 km。H改变不修改任何平均速度、密度或Q界面。1%弱尾段、过渡宽度和莫霍截断均为项目假设，非Onodera原表精确值。图(f)用本站实际高程换算莫霍深度，显示H=5/10/20三个候选；线条不是反演结果。

完整函数及FFT、ACF/PSD验收继承[详细方案§5–7](../07_源站路径与固定背景下的详细模拟方案.md)。[Onodera2022](https://doi.org/10.1029/2022JE007558)提供三维指数特例及分深度扰动的方法参照；新参数范围是本项目搜索设计，不能称本站已测置信区间。

## 4. 本区实施顺序及解释边界

训练事件：{', '.join(m['train'])}。独立检查事件：{', '.join(m['holdout']) if m['holdout'] else '无可用近距独立事件'}。

先固定b=5/9、H=10，搜索24组a/σ0；再围绕3组入围点调整b/H，去重后共57组候选；最终3个候选使用5种子。种子只用于稳定性，不能当作新观测。所有数据与合成采用相同准入频带、响应处理和缺样掩码。网格、源、Q与曲率接口必须先完成检查，本定义不能直接作为CGFD3D运行文件。

最终输出本区独立接受集合和θ_{sid}估计；缺乏分辨能力时报告范围而非唯一值。三个区域当前可以使用相同初始参数，但不强制其拟合结果相同，也不预设高地比月海更强。

## 5. 图件说明

图(a)为PDS LOLA LDEM_64原生产品的显示抽样，色标统一−5至5 km；台站三角形、事件圆圈、路径与规划框分别编码。图(b)使用大圆剖面原生像元近邻高程，垂向夸大。生产地形采用已约定的双线性映射并固定，不将显示抽样视为新的地形分辨率。图(c–e)为作者背景节点，图(f)为项目设计函数；图中没有伪造随机三维材料或传播结果。
'''
    (OUT/f'{sid}_区域模型说明.md').write_text(text,encoding='utf-8')
    summary.append({'station':sid,'pairs':len(sp),'train':len(m['train']),'holdout':len(m['holdout']),'height':hs,'bounds':[w,e,so,no]})

guide='''# S12、S14、S15三个台站区域的独立模型

版本：2026-11-05。按用户明确范围，本版只交付M-S12、M-S14、M-S15，移除S16的模型任务，并替代上一版W组共享参数的组织方式。数学定义及数值验收继续采用第07章，区域组织以本文件为准。

## 1. 三套独立模型

| 模型 | 地区标识 | 近距候选数 | 训练/独立检查事件 | 模型说明与图 |
|---|---|---:|---|---|
| M-S12 | S12月海邻域 | 7 | 3/4 | [说明与总图](三台站区域模型/S12_区域模型说明.md) |
| M-S14 | S14 Fra Mauro喷出物/破碎高地 | 3 | 2/1 | [说明与总图](三台站区域模型/S14_区域模型说明.md) |
| M-S15 | S15 Hadley–Apennine盆地边缘 | 1 | 1/0 | [说明与总图](三台站区域模型/S15_区域模型说明.md) |

每区分别给出真实地形、源站关系、固定背景分层、Vp/Vs、ρ、Q及独立待估的(a,σ0,b,H)。当前完整背景采用同一可靠归档的月球平均后备模型；不能仅为画出差异而改动缺乏依据的密度/Q或速度。地方壳厚/平均Vs作为已有约束单列，尚未拼成虚构的完整区域层表。三个地区最终参数是否不同，由各自记录决定。

## 2. 图件

![S12](三台站区域模型/S12_区域模型总图.png)

![S14](三台站区域模型/S14_区域模型总图.png)

![S15](三台站区域模型/S15_区域模型总图.png)

## 3. 独立参数与共同实施规则

θ12、θ14、θ15分别拟合；三个初值都为a=4.5 km、σ0=9%、b=5/9、H=10 km，均为设计起点，不是最优值。相关尺度搜索0.2/0.65/1.3/2/4.5/6 km，σ0搜索5/9/10/15%，深度搜索3.5/5/10/20 km。同一搜索范围避免预设哪个地区强。每区一个固定背景及吸收设置，任何候选都不修改背景来获得更好的散射拟合。

以台站名称命名的区域模型仍由对应的源站记录约束，不等同于本站正下方的纯局地物性。S12和S14规划域重叠，两套独立有效模型不可直接在重叠处拼成一张唯一三维物性图。现阶段分别报告；若以后要求跨区统一预测，需要另外定义一致的空间参数场。这不妨碍本次三台站区域的独立模型交付。

## 4. 更新后的计算计数

每区阶段A为24组、阶段B去重后累计57组；最终3候选新增4种子，每个训练事件合计69次候选传播。S12训练3事件为207次，S14训练2事件为138次，S15训练1事件为69次；合计414次。S12的4个及S14的1个留出事件按3候选×5种子检查，共75次。总体规划489次传播，不含网格/域验收；尚未运行。

因为S12/S14现在具有独立介质参数，同一撞击事件不能无条件复用一次波场；故上一版共享W组的336次计数作废。每区57组仍是分阶段筛选，并非完整288组全网格搜索。

## 5. 交付文件

每区包含一份Markdown说明、一张六面板PNG、一份固定背景CSV、一份代表路径地形CSV和一份模型定义JSON。背景原始节点、LOLA裁片及参数出处可沿链接追溯。JSON是模型设计描述，不是已适配CGFD3D的生产配置。图件为数值背景和真实地形加设计函数，未产生模拟波形或区域最优散射结果。
'''
(D/'08_S12_S14_S15三个区域模型.md').write_text(guide,encoding='utf-8')
latest={'scope':['S12','S14','S15'],'status':'DESIGN_ONLY','parameters_shared':False,'background_is_common_fallback':True,'regions':summary,'planned_runs':489}
(OUT/'三区域交付索引.json').write_text(json.dumps(latest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(latest,ensure_ascii=False))
