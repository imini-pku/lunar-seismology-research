"""Rebuild the three station columns from checked primary sources, not fitted waveforms."""
from pathlib import Path
import csv, json, hashlib, re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'docs/研究设计总册_20261029'; OUT=D/'三台站区域模型'
SRC=ROOT/'data/raw/background_models/regional_audit/regional_constraints_20261105.json'
C=json.loads(SRC.read_text(encoding='utf8')); fixed=C['fixed_missing_structure']
plt.rcParams.update({'font.sans-serif':['Microsoft YaHei'],'axes.unicode_minus':False,'font.size':10,'svg.fonttype':'none'})
def csvread(p): return list(csv.DictReader(p.open(encoding='utf-8-sig')))
stations={x['station']:x for x in csvread(ROOT/'results/impact_audit/stations.csv')}
events={x['event_id']:x for x in csvread(ROOT/'results/impact_audit/events_and_domains.csv')}
pairs=csvread(ROOT/'results/impact_audit/event_station_domains.csv')
dem=np.load(ROOT/'data/raw/lola_impact_64/ldem_64_W38_E40_S18_N40_native.npz')
lon,lat,dn=dem['longitude_degE'],dem['latitude_degN'],dem['dn']; scale=float(dem['height_scale_m'])/1000
def height(la,lo):
    la,lo=np.atleast_1d(la),np.atleast_1d(lo)
    return dn[np.abs(lat[:,None]-la).argmin(axis=0),np.abs(lon[:,None]-lo).argmin(axis=0)]*scale
def track(e,s,n=350):
    def xyz(x):
        a,b=np.deg2rad([float(x['lat']),float(x['lon'])]);return np.array([np.cos(a)*np.cos(b),np.cos(a)*np.sin(b),np.sin(a)])
    u,v=xyz(e),xyz(s);angle=np.arccos(np.clip(u@v,-1,1));t=np.linspace(0,1,n)
    q=(np.sin((1-t)*angle)[:,None]*u+np.sin(t*angle)[:,None]*v)/np.sin(angle)
    return t*angle*1737.4,np.rad2deg(np.arcsin(q[:,2])),np.rad2deg(np.arctan2(q[:,1],q[:,0]))
def read_nd(p):
    rows=[];mantle=False
    for line in p.read_text().splitlines():
        if line.strip()=='mantle':mantle=True
        try:
            v=list(map(float,line.split()))
            if len(v)==6 and mantle and v[0]<=150:rows.append(v)
        except ValueError:pass
    return np.array(rows)
M2=read_nd(ROOT/'data/raw/background_models/ISSI_MOON_M2.nd')
G11=read_nd(ROOT/'data/raw/background_models/MoonGarcia_PEPI_2011.nd')
colors={'S12':'#0072B2','S14':'#D55E00','S15':'#009E73'}
names={'S12':'月海邻域','S14':'Fra Mauro喷出物区','S15':'Hadley–Apennine盆缘月海'}
old={s:json.loads((OUT/f'{s}_模型定义.json').read_text(encoding='utf8')) for s in colors}

def profile(s,d):
    d=np.asarray(d,dtype=float); n=len(d); c=C[s]; hs=old[s]['station']['lola_height_km']
    vp=np.full(n,5.2);vs=np.full(n,3.0);rho=np.full(n,2762.)
    for l in c['shallow_layers']:
        ix=(d>=l['top_km'])&(d<l['bottom_km']);vp[ix]=l['vp'];vs[ix]=l['vs'];rho[ix]=l['adopted_rho']
    last=c['shallow_layers'][-1];ix=(d>=.5)&(d<1)
    t=(d[ix]-.5)/.5;vp[ix]=(1-t)*last['vp']+t*5.2;vs[ix]=(1-t)*last['vs']+t*3
    mantle=d>=c['moho_km'];ref=d[mantle]-hs
    vp[mantle]=np.interp(ref,M2[:,0],M2[:,1]);vs[mantle]=np.interp(ref,M2[:,0],M2[:,2])
    rho[mantle]=1000*np.interp(ref,G11[:,0],G11[:,3])
    qs=np.where(mantle,2133.,5000.);qk=np.full(n,1e6)
    ratio=4/3*(vs/vp)**2;qp=1/(ratio/qs+(1-ratio)/qk)
    return np.column_stack([vp,vs,rho,qp,qs,qk])

def plot_depths(s,maximum):
    jumps=[x['bottom_km'] for x in C[s]['shallow_layers'][:2]]+[C[s]['moho_km']]
    base=np.r_[np.linspace(0,min(1,maximum),601),np.linspace(1,maximum,401) if maximum>1 else [],.5,1]
    return np.sort(np.unique(np.r_[base[base<=maximum],*[np.array([x-1e-8,x]) for x in jumps if x<=maximum]]))

def T(d,c,w):return .5*(1+np.cos(np.pi*np.clip((d-c+w/2)/w,0,1)))
def sigma(d,H=10,b=5/9,s=.09,dm=35):return (.01+(b*s-.01)*T(d,H+2.5,5)+(s-b*s)*T(d,H/2,1))*T(d,dm-.5,1)

all_layers=[];checks=[]
for s in colors:
    c=C[s];st=stations[s];spec=old[s];hs=spec['station']['lola_height_km'];H=c['moho_km'];Dmoho=H-hs
    sp=[p for p in pairs if p['station']==s and p['domain_role']=='local_candidate_pending_QC']
    w,e,so,no=spec['planning_bounds_deg'];ev_id=spec['reference_section'].split('_')[0]
    dist,slat,slon=track(events[ev_id],st);h=height(slat,slon)
    # Every layer carries independent provenance for velocity, density, and Q.
    layers=[]
    def add(a,b,v1,v2,r1,r2,rule,vsrc,rsrc,kind):
        row={'station':s,'top_local_depth_km':a,'bottom_local_depth_km':b,'Vp_top_km_s':v1[0],'Vp_bottom_km_s':v2[0],
             'Vs_top_km_s':v1[1],'Vs_bottom_km_s':v2[1],'rho_top_kg_m3':r1,'rho_bottom_kg_m3':r2,
             'Qkappa':1000000,'Qmu_Qs':5000 if b<=H else 2133,'interpolation':rule,'velocity_source':vsrc,'density_source':rsrc,
             'Q_source':'Nunn2024 section4.1.2; Qp=1/(L/Qmu+(1-L)/Qkappa)','evidence_class':kind}
        layers.append(row)
    for l in c['shallow_layers']:
        add(l['top_km'],l['bottom_km'],[l['vp'],l['vs']],[l['vp'],l['vs']],l['adopted_rho'],l['adopted_rho'],'constant','Amrouche2022 Fig11 p17',l['density_evidence'],'I velocity; I/G density; G Q')
    z=c['shallow_layers'][-1]
    add(.5,1,[z['vp'],z['vs']],[5.2,3],2762,2762,'linear Vp/Vs; constant density','project splice from Amrouche to Zhang2026 network crust','Garcia2011 mean crust','P')
    add(1,H,[5.2,3],[5.2,3],2762,2762,'constant','Zhang2026 section4 network mean, NOT local-layer inversion','Garcia2011 mean crust','network-average velocity; G density/Q; O Moho')
    # Knot samples reproduce both archived mantle curves without inventing a deep regional inversion.
    knots=np.sort(np.unique(np.r_[H,100,M2[:,0]+hs,G11[:,0]+hs]));knots=knots[(knots>=H)&(knots<=100)]
    for a,b in zip(knots[:-1],knots[1:]):
        va,vb=profile(s,[a,b]);add(float(a),float(b),va[:2],vb[:2],va[2],vb[2],'linear','Garcia2019 ISSI_MOON_M2.nd mantle at reference depth d-h_station','Garcia2011 mantle at reference depth d-h_station','G')
    with (OUT/f'{s}_背景参数.csv').open('w',encoding='utf-8-sig',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=list(layers[0]));wr.writeheader();wr.writerows(layers)
    all_layers+=layers
    dd=plot_depths(s,100);v=profile(s,dd)
    with (OUT/f'{s}_背景剖面采样.csv').open('w',encoding='utf-8-sig',newline='') as f:
        wr=csv.writer(f);wr.writerow(['local_depth_km','Vp_km_s','Vs_km_s','rho_kg_m3','Qp','Qs','Qkappa']);wr.writerows(np.column_stack([dd,v]))
    nu=(v[:,0]**2-2*v[:,1]**2)/(2*(v[:,0]**2-v[:,1]**2))
    checks.append({'station':s,'min_K_over_rho':float(np.min(v[:,0]**2-4*v[:,1]**2/3)),'min_poisson':float(nu.min()),
                   'positive_finite':bool(np.all(np.isfinite(v)) and np.all(v>0)),'moho_local_km':H,'moho_reference_km':Dmoho,
                   'min_vs_km_s':float(v[:,1].min()),'density_replacements':2,'not_simulated':True})
    spec.update(version=C['version'],status='REGIONAL_HYBRID_DESIGN_NOT_INVERTED_NOT_PRODUCTION_INPUT',local_evidence='Amrouche2022 Fig11 + Zhang2026 TableS8; density replacement and splice explicitly project choices')
    spec['background']={'table':f'{s}_背景参数.csv','sampled_profile':f'{s}_背景剖面采样.csv','same_fallback_as_other_regions':False,
       'shallow_layers':c['shallow_layers'],'regional_moho_local_km':H,'regional_moho_sd_km':c['moho_sd_km'],'moho_reference_depth_km':Dmoho,
       'geometry':'R=1737.4 km; d=z_ref+h(x,y); shallow interfaces at d=0.06/0.12 and 0.20/0.25/0.30; splice d=0.5..1; Moho z_ref=H_station-h_station',
       'lateral_extension':'station column assumed representative throughout its own event domain; NOT a measured 3D regional model',
       'network_crust_vp_vs':[5.2,3.0],'crust_density':2762,'mantle_velocity':'ISSI_MOON_M2.nd','mantle_density':'MoonGarcia_PEPI_2011.nd',
       'Q':{'Qkappa':1e6,'Qmu_crust':5000,'Qmu_upper_mantle':2133,'Qp':'local background Vp/Vs conversion','source':'10.3847/PSJ/ad83d2'},
       'source_constraints_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'limitations':fixed['critical_limitations']}
    (OUT/f'{s}_模型定义.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf8')
    fig=plt.figure(figsize=(16,11),layout='constrained');gs=fig.add_gridspec(2,8,height_ratios=[1,1.1])
    axm=fig.add_subplot(gs[0,:4]);axsec=fig.add_subplot(gs[0,4:]);axs=[fig.add_subplot(gs[1,i:i+2]) for i in [0,2,4,6]]
    ii=np.flatnonzero((lat>=so-.25)&(lat<=no+.25))[::2];jj=np.flatnonzero((lon>=w-.25)&(lon<=e+.25))[::2]
    im=axm.pcolormesh(lon[jj],lat[ii],dn[np.ix_(ii,jj)]*scale,cmap='terrain',vmin=-5,vmax=5,shading='nearest',rasterized=True)
    for k,p in enumerate(sp,1):
        ev=events[p['event_id']];_,la,lo=track(ev,st);axm.plot(lo,la,color='#8b244c',lw=.8)
        axm.scatter(float(ev['lon']),float(ev['lat']),s=25,c='white',edgecolor='black',zorder=4)
        axm.annotate(str(k),(float(ev['lon']),float(ev['lat'])),xytext=(5,5),textcoords='offset points',bbox={'fc':'white','ec':'none','alpha':.8,'pad':.4},zorder=6)
    axm.scatter(float(st['lon']),float(st['lat']),marker='^',s=95,c='red',edgecolor='white',zorder=5)
    axm.annotate(s,(float(st['lon']),float(st['lat'])),xytext=(7,-15),textcoords='offset points',fontweight='bold',bbox={'fc':'white','ec':'none','alpha':.8},zorder=7)
    axm.add_patch(Rectangle((w,so),e-w,no-so,fill=False,ec='#222',ls='--',lw=1))
    axm.set(xlim=(w-.25,e+.25),ylim=(so-.25,no+.25),xlabel='经度 (°E)',ylabel='纬度 (°N)',title=f'(a) 实际LOLA地形；{len(sp)}条候选路径')
    axm.set_aspect(1/np.cos(np.deg2rad((so+no)/2)));fig.colorbar(im,ax=axm,shrink=.8,label='高程 (km)',pad=.02)
    axsec.fill_between(dist,-h,1-h,color='#e8ca9c',label='区域浅层＋衔接段')
    axsec.fill_between(dist,1-h,Dmoho,color='#c9c5df',label='网络平均壳背景')
    axsec.fill_between(dist,Dmoho,60,color='#c8d5c8',label='平均月幔')
    axsec.plot(dist,-h,'k',lw=1);axsec.axhline(Dmoho,color=colors[s],lw=2,label=f'莫霍：本站壳厚{H:.1f} km')
    axsec.plot(dist,10-h,'--',color='#555',label='散射H=10 km示例')
    axsec.text(0,-4,ev_id,ha='left');axsec.text(dist[-1],-4,s,ha='right')
    axsec.set(xlim=(0,dist[-1]),ylim=(60,-7),xlabel='源—站大圆距离 (km)',ylabel='参考球面以下深度 (km)',title='(b) 地形＋本项目固定界面实现（垂向夸大）')
    axsec.legend(fontsize=9,loc='lower left',ncol=2)
    shallow=plot_depths(s,1);sv=profile(s,shallow)
    for col,lab,sty in [(0,'Vp','-'),(1,'Vs','--')]:axs[0].plot(sv[:,col],shallow*1000,sty,lw=2,label=lab,color=['#0072B2','#D55E00'][col])
    axs[0].axhspan(500,1000,facecolor='#ddd',alpha=.5);axs[0].text(.03,.06,'灰区：项目衔接段',transform=axs[0].transAxes,fontsize=9)
    axs[0].set(ylim=(1000,0),xlim=(0,5.6),xlabel='速度 (km/s)',ylabel='当地地表以下深度 (m)',title='(c) 区域浅部速度')
    axs[0].legend(fontsize=9);axs[0].grid(alpha=.2)
    axs[1].plot(sv[:,2]/1000,shallow*1000,color=colors[s],lw=2,label='本版固定密度')
    for l in c['shallow_layers'][1:]:axs[1].scatter(l['published_rho']/1000,(l['top_km']+l['bottom_km'])*500,marker='x',c='#aa3333',s=45)
    axs[1].scatter([],[],marker='x',c='#aa3333',label='原文拟合值，未采用')
    axs[1].set(ylim=(1000,0),xlim=(2.2,4.65),xlabel='密度 (g/cm³)',title='(d) 区域密度与后备值');axs[1].tick_params(labelleft=False);axs[1].legend(fontsize=8);axs[1].grid(alpha=.2)
    for col,lab,sty in [(0,'Vp','-'),(1,'Vs','--')]:axs[2].plot(v[:,col],dd,sty,lw=2,label=lab,color=['#0072B2','#D55E00'][col])
    axs[2].axhspan(H-c['moho_sd_km'],H+c['moho_sd_km'],color=colors[s],alpha=.12)
    axs[2].axhline(H,c=colors[s],ls=':',label=f'Hc={H:.1f} km')
    axs[2].set(ylim=(100,0),xlim=(0,8.5),xlabel='速度 (km/s)',ylabel='当地地表以下深度 (km)',title='(e) 全背景与区域莫霍');axs[2].legend(fontsize=8);axs[2].grid(alpha=.2)
    axs[3].plot(v[:,3]/1000,dd,'-',label='Qp（换算）',lw=2);axs[3].plot(v[:,4]/1000,dd,'--',label='Qs（统一后备）',lw=2)
    axs[3].set(ylim=(100,0),xlim=(0,19),xlabel='本征Q / 1000',title='(f) 固定本征吸收');axs[3].tick_params(labelleft=False);axs[3].grid(alpha=.2);axs[3].legend(fontsize=8)
    fig.text(.5,.985,f'M-{s}｜{names[s]}：区域结构更新',ha='center',va='top',fontsize=19)
    fig.text(.5,.945,'浅部速度／界面：Amrouche 2022；壳厚：Zhang 2026 Table S8；缺项与衔接逐项标明',ha='center',va='top',fontsize=12)
    fig.text(.5,.005,'密度采用岩样启发的表层值＋Garcia平均后备，未照搬原文高拟合密度；Q按Nunn 2024。\n(e)阴影为文献壳厚±1σ，本次输入固定于均值；全域横向延拓属于项目假设。尚未计算波形或得到最优散射参数。',ha='center',fontsize=10)
    fig.get_layout_engine().set(rect=(0,.065,1,.84));fig.savefig(OUT/f'{s}_区域模型总图.png',dpi=170);fig.savefig(OUT/f'{s}_区域模型总图.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(5,5),layout='constrained');d=np.linspace(0,50,1001)
    for hv,sty,col in [(5,':','#666'),(10,'-',colors[s]),(20,'--','#b14c63')]:ax.plot(sigma(d,H=hv,dm=H)*100,d,sty,c=col,label=f'H={hv} km')
    ax.axhline(H,c='black',ls=':',label=f'区域莫霍{H} km');ax.set(ylim=(50,0),xlabel='相对速度标准差 (%)',ylabel='当地深度 (km)',title=f'{s}散射深度候选（非反演结果）');ax.legend();ax.grid(alpha=.2)
    fig.savefig(OUT/f'{s}_散射深度候选.png',dpi=170);plt.close(fig)
    rows=[]
    for l in c['shallow_layers']:
        q=profile(s,[(l['top_km']+l['bottom_km'])/2])[0]
        rows.append(f'| {1000*l["top_km"]:.0f}–{1000*l["bottom_km"]:.0f} m | {l["vp"]:.2f} | {l["vs"]:.2f} | {l["adopted_rho"]:.0f} | {q[3]:.0f} | 5000 | 区域解释速度；密度见下文 |')
    tab='\n'.join(rows)
    evt='\n'.join(f'| {k} | {p["event_id"]} | {float(p["distance_km"]):.2f} | '+('训练' if p['event_id'] in spec['train'] else '留出检查')+' | '+('缺MHZ，仅合格水平分量' if p['pair_id']=='A16SIVB_S14' else '逐分量质控准入')+' |' for k,p in enumerate(sp,1))
    note='S14的200–500 m解释层Vp/Vs=4/3，对应泊松比−1/7。其体积模量仍为正，数值上可构造各向同性稳定弹性体，但缺乏独立月壳岩石约束；必须作为弱证据输入明确列出，不能因为出现在论文中就称其唯一可靠。' if s=='S14' else 'S12与S15的最表层速度相同是来源模型的实际设定；两地浅层厚度和中间层速度不同，不能为了全表不同再任意改动。'
    doc=f'''# M-{s}｜{names[s]}区域模型

版本：2026-11-05区域结构更新版。替代本目录上一版共同平均背景。**这是有完整数值与出处的区域化混合正演设计，不是原论文模型复现，不是已完成反演，也不是CGFD3D生产配置。**

![{s}区域结构总图]({s}_区域模型总图.png)

## 1. 本区确定采用的背景

本站位于({float(st['lon']):.5f}°E, {float(st['lat']):.5f}°N)，LOLA采样高程{hs:.4f} km。区域莫霍采用[Zhang 2026补充表S8](https://doi.org/10.1029/2025JE009453)：**{H:.1f}±{c['moho_sd_km']:.1f} km**，±表示后验标准差；正演固定为{H:.1f} km，不随散射候选改变。

| 当地地表以下深度 | Vp km/s | Vs km/s | ρ kg/m³ | Qp | Qs | 证据性质 |
|---|---:|---:|---:|---:|---:|---|
{tab}
| 500–1000 m | {z['vp']:.2f}→5.20 | {z['vs']:.2f}→3.00 | 2762 | 按速度比逐点计算 | 5000 | 项目线性衔接，非实测层 |
| 1–{H:.1f} km | 5.20 | 3.00 | 2762 | {profile(s,[2])[0,3]:.0f} | 5000 | Zhang网络平均速度＋Garcia平均密度 |
| 莫霍以下至100 km | M2逐节点插值 | M2逐节点插值 | Garcia逐节点插值 | 按速度比逐点计算 | 2133 | 月球平均后备 |

完整逐层端点在[背景参数CSV]({s}_背景参数.csv)，包含材料值、插值方式及各参数独立来源；[逐点采样CSV]({s}_背景剖面采样.csv)可直接重画图。注意背景CSV已改为“层顶/层底及端点值”格式，不能按旧六列文件读取。重复/相邻界面严格保留跳变，不跨跳变平滑。

**浅层速度和两个界面来自[Amrouche 2022 Figure 11，PDF第17页](https://doi.org/10.1029/2022JE007396)，属于非唯一场地响应解释模型。** 仅取原图展示的前500 m；500 m截断及回接至1 km是本项目设计，不是发现了500 m界面。1 km以下采用[Zhang 2026 §4](https://doi.org/10.1029/2025JE009453)网络共同壳速度；其5.20±0.05、3.00±0.03 km/s不是各站独立深度剖面，不能将该标准差当成整套混合模型的不确定度。

{note}

## 2. 密度和Q为什么仍有共同部分

本区表层密度{c['shallow_layers'][0]['adopted_rho']} kg/m³沿用Amrouche基于样品的等效近地表设定，不能用于表示最上面几米松散月壤。中间层/基底的原文拟合密度分别为{c['shallow_layers'][1]['published_rho']}、{c['shallow_layers'][2]['published_rho']} kg/m³；缺乏独立区域密度支持，本版不采用这些调参值。改用[Garcia 2011](https://doi.org/10.1016/j.pepi.2011.06.015)平均月壳2762 kg/m³，并明确这是后备值。图(d)的叉号保留原文值供核查，实线才是本版输入。改变密度会改变阻抗和H/V响应，不能继续声称达到原作者的拟合系数。

月幔速度采用[Garcia 2019公开M2归档](https://zenodo.org/records/21476963)，月幔密度用同归档的Garcia2011剖面。由于本站没有完整密度剖面，且本任务不是重力反演，未照搬Zhang重力计算的统一密度假设；本模型不宣称复现其重力拟合。

本征Q采用[Nunn 2024 §4.1.2](https://doi.org/10.3847/PSJ/ad83d2)：Qκ=10⁶，壳内Qμ=Qs=5000，莫霍下到当前100 km底界Qs=2133。逐点L=4Vs²/(3Vp²)，Qp=[L/Qs+(1−L)/Qκ]⁻¹。三地没有可靠独立Q层表，因此共同吸收设定是明确的补足，不是证明三地吸收一样。Amrouche的Q=100/300为场地模拟假设，本任务不把它当成实测本征Q。

## 3. 地形、界面和横向范围

使用实际PDS LOLA LDEM_64原生裁片，64像元/度，赤道间距约474 m；显示图抽样不增加分辨率。令参考球半径R=1737.4 km，高程h(x,y)，参考深度z_ref=R−r，当地深度d=z_ref+h。浅层界面随地表，莫霍固定为z_ref={Dmoho:.4f} km，即本站地表至莫霍为{H:.1f} km。这是将文献壳厚映射到项目坐标的实现选择，不是Zhang发布的LOLA三维莫霍。其他位置的当地壳厚为{Dmoho:.4f}+h(x,y)。月幔归档曲线按z_ref采样，图(c–f)按本站当地深度显示。

地表起伏固定；不再额外设置旧模型的12 km内壳界面，因为本版采用Zhang的有效单层壳与区域浅层组合，当前没有本站12 km界面的独立约束。图(b)前1 km包含三个薄层及衔接段；详细结构要看图(c)，不能从60 km纵轴中判断薄层不存在。

本版将台站代表柱延拓到该区域的源站模拟域，这是固定的横向均一性假设。原文并未证明这套浅层结构覆盖整条几十至几百公里路径。S12/S14域有重叠，三套独立模型不能拼成一张唯一三维真实地质图。散射结果应称“在指定固定背景下的路径组有效参数”。

## 4. 事件与记录

| 图中编号 | 撞击事件 | 震中距 km | 用途 | 分量说明 |
|---|---|---:|---|---|
{evt}

规划框为已审计路径缓冲范围的并集；不是地质单元边界，也不是已验收的吸收边界。真实记录、处理和逐分量缺项沿用[第01章](../01_事件台站与记录图册.md)、[第03章](../03_波形处理与反演准入.md)，本轮未重新处理波形。S15只有一条近距事件，不能把随机种子当独立观测。

## 5. 散射参数仍单独反演

保持三维各向同性冯卡尔曼模型，ν=0.5为本项目明确选择。θ_{s}=(a,σ0,b,H)独立于其他台站；起点4.5 km、9%、5/9、10 km。候选a=0.2/0.65/1.3/2/4.5/6 km，σ0=5/9/10/15%，b=5/9、0.85、1，H=3.5/5/10/20 km。Vp、Vs用同一相对随机场；ρ和Q不加随机扰动。

![{s}散射深度候选]({s}_散射深度候选.png)

强度函数沿用第07章，莫霍截断改为本区的新固定莫霍。H不是壳厚，不把文献壳厚标准差纳入散射搜索。1%弱尾段、余弦过渡等均是项目设计。[Onodera 2022](https://doi.org/10.1029/2022JE007558)为分深度三维随机介质方法参照，并不直接给出本站的最优参数。

## 6. 接入CGFD3D之前必须完成的验证

固定背景已经改变，原“共同平均模型”的网格估算不可原样用。最慢Vs={v[:,1].min():.2f} km/s；以10点/最短S波长估算，1 Hz时平均背景上限间距约{v[:,1].min()*100:.0f} m；还要解析60/120 m薄层及随机场导致的更低速度。该估算不是求解器收敛结论，最终取决于旧生产阶数、曲线网格、最高准入频率与时间步。

先检验无随机扰动的走时、数值稳定性及背景场地响应，再冻结背景搜索散射参数。Amrouche密度替换和500–1000 m衔接均会影响波形；Zhang原来对浅部作的走时校正也已改变。因此新壳厚在本混合模型里是文献先验，不能声称新背景已联合拟合了该文全部走时。若固定背景明显偏离观测，应修正背景并重启该区搜索，不能让散射强度吸收系统背景误差。

完整证据、采用/舍弃理由见[区域结构审计](../09_三区域结构文献核对与背景更新.md)。[本区JSON设计](./{s}_模型定义.json)仍不是CGFD3D运行配置。
'''
    (OUT/f'{s}_区域模型说明.md').write_text(doc,encoding='utf8')

# Cross-region comparison with common scales and source/implementation separation.
fig,axs=plt.subplots(2,3,figsize=(15,10),layout='constrained')
for s,sty in zip(colors,['-','--','-.']):
    ds=plot_depths(s,.5);v=profile(s,ds)
    for j,col in enumerate([0,1,2]):axs[0,j].plot(v[:,col]/(1000 if col==2 else 1),ds*1000,sty,c=colors[s],lw=2,label=s)
    d=plot_depths(s,60);v=profile(s,d);axs[1,1].plot(v[:,1],d,sty,c=colors[s],lw=2,label=s)
    axs[1,2].plot(v[:,3]/1000,d,sty,c=colors[s],lw=2,label=s+' Qp')
for j,(title,xlab,lim) in enumerate([('浅部Vp：不同的解释模型','Vp (km/s)',(0,4.5)),('浅部Vs：不同的解释模型','Vs (km/s)',(0,3.3)),('浅部密度：采用值','ρ (g/cm³)',(2.2,3.45))]):
    axs[0,j].set(ylim=(500,0),xlim=lim,xlabel=xlab,ylabel='当地深度 (m)',title=title);axs[0,j].grid(alpha=.2);axs[0,j].legend()
for i,s in enumerate(colors):
    c=C[s];axs[1,0].errorbar(i,c['moho_km'],yerr=c['moho_sd_km'],fmt='o',c=colors[s],capsize=5,ms=7)
    axs[1,0].annotate(f'{c["moho_km"]} ± {c["moho_sd_km"]}',(i,c['moho_km']),xytext=(0,12),textcoords='offset points',ha='center')
axs[1,0].set(xticks=[0,1,2],xticklabels=list(colors),xlim=(-.5,2.5),ylim=(52,25),ylabel='当地地表至莫霍 (km)',title='Zhang 2026 Table S8：均值 ± 1σ');axs[1,0].grid(axis='y',alpha=.2)
axs[1,1].set(ylim=(60,0),xlim=(0,5),xlabel='Vs (km/s)',ylabel='当地深度 (km)',title='全壳Vs：深部共同背景＋不同莫霍');axs[1,1].legend();axs[1,1].grid(alpha=.2)
axs[1,2].set(ylim=(60,0),xlim=(0,19),xlabel='Qp / 1000',ylabel='当地深度 (km)',title='Qp差异来自速度比／界面换算');axs[1,2].legend();axs[1,2].grid(alpha=.2)
fig.text(.5,.985,'S12 · S14 · S15｜有区域依据的部分分别建模',ha='center',va='top',fontsize=19)
fig.text(.5,.943,'Amrouche 2022浅层解释速度与界面；Zhang 2026区域壳厚；密度/Q缺项明确采用共同后备',ha='center',va='top',fontsize=12)
fig.text(.5,.004,'实线/虚线均为本项目固定输入，不是区域反演结果。表层密度有区域依据，深部密度仍缺独立约束。\n原文3800–4500 kg/m³等中间层／基底拟合密度未采用；Qs统一为壳5000、幔2133，Qp由Vp/Vs换算。',ha='center',fontsize=10)
fig.get_layout_engine().set(rect=(0,.07,1,.85));fig.savefig(OUT/'三台站区域结构对比.png',dpi=180);fig.savefig(OUT/'三台站区域结构对比.svg');plt.close(fig)

(OUT/'区域结构数值核验.json').write_text(json.dumps({'version':C['version'],'checks':checks,'scientific_status':'conditional hybrid design; source extraction verified; baseline waveforms NOT validated'},ensure_ascii=False,indent=2),encoding='utf8')
idx={'version':C['version'],'scope':list(colors),'status':'REGIONAL_HYBRID_DESIGN_ONLY','parameters_shared':False,'background_is_common_fallback':False,'common_deep_crust_and_Q':True,'planned_runs':489,'source_constraints':str(SRC.relative_to(ROOT)),'regions':checks}
(OUT/'三区域交付索引.json').write_text(json.dumps(idx,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(idx,ensure_ascii=False))
