from pathlib import Path
import csv, json, hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

R=Path(__file__).resolve().parents[1]
D=R/'docs/研究设计总册_20261029'
A=D/'assets'; T=D/'tables'
plt.rcParams.update({'font.sans-serif':['Microsoft YaHei'], 'axes.unicode_minus':False,'font.size':11})
raw=R/'data/raw/background_models/MoonGarcia_PEPI_2011.nd'
rows=[]
for line in raw.read_text().splitlines():
    try:
        row=list(map(float,line.split()))
        if len(row)==6: rows.append(row)
    except ValueError: pass
x=np.array(rows); shallow=x[x[:,0]<=110].copy()
with (T/'固定背景_Garcia2011_原始节点_0_110km.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['depth_km','Vp_km_s','Vs_km_s','rho_g_cm3','Qp','Qs']);w.writerows(shallow)
fig,axs=plt.subplots(1,4,figsize=(14,6),sharey=True)
for ax,col,label in zip(axs,[1,2,3,4],['Vp (km/s)','Vs (km/s)','密度 (g/cm³)','本征 Q']):
    ax.plot(shallow[:,col],shallow[:,0],color='#0072B2',lw=2)
    if col==4:
        ax.plot(shallow[:,5],shallow[:,0],'--',color='#D55E00',label='Qs');ax.lines[0].set_label('Qp');ax.legend()
    for h in [1,12,28]:ax.axhline(h,color='gray',lw=.6,ls=':')
    ax.set_xlabel(label);ax.grid(alpha=.2)
axs[0].set_ylim(100,0);axs[0].set_ylabel('参考球面以下深度 (km)')
fig.suptitle('当前冻结的月球平均后备模型：VPREMOON 数值节点\n同一背景用于散射参数搜索；不是各区实测分层')
fig.text(.5,.015,'来源：Garcia 2011；Garcia 2019 作者归档 MoonGarcia_PEPI_2011.nd。重复深度保留界面两侧值。',ha='center',fontsize=10)
fig.tight_layout(rect=[0,.045,1,.9]);fig.savefig(A/'固定背景_速度密度Q.png',dpi=180);plt.close(fig)

def weight(d,h,width=1.):
    u=np.clip((d-(h-width/2))/width,0,1)
    return .5*(1+np.cos(np.pi*u))
def sigma(d,s=.09,b=5/9,H=10,dmoho=28):
    # All values are project design, not digitized Onodera profiles.
    t1=weight(d,H/2,1); t2=weight(d,H+2.5,5)
    v=.01+(b*s-.01)*t2+(s-b*s)*t1
    return v*weight(d,dmoho-.5,1)
d=np.linspace(0,32,1601)
fig,axs=plt.subplots(1,3,figsize=(14,6),sharey=True)
for s in [.05,.09,.10,.15]:axs[0].plot(sigma(d,s=s)*100,d,label=f'σ0={s*100:g}%')
for b in [5/9,.85,1]:axs[1].plot(sigma(d,b=b)*100,d,label=f'b={b:.3g}')
for H in [3.5,5,10,20]:axs[2].plot(sigma(d,H=H)*100,d,label=f'H={H:g} km')
for ax,title in zip(axs,['改变浅部强度；b=5/9，H=10 km','改变深浅幅度比；σ0=9%，H=10 km','改变强散射深度；σ0=9%，b=5/9']):
    ax.set_title(title,fontsize=11);ax.set_xlabel('相对速度扰动标准差 (%)');ax.grid(alpha=.2);ax.legend(fontsize=9);ax.axhline(28,color='gray',ls=':',lw=1)
axs[0].set_ylim(32,0);axs[0].set_ylabel('当地地表以下深度 d (km)')
fig.suptitle('统一冯卡尔曼模型的深度参数化（本项目设计，非 Onodera Figure 8 数值复刻）')
fig.text(.5,.015,'示例地表高程=0；强扰动结束后5 km过渡至1%弱扰动，最后1 km在固定莫霍前归零。',ha='center',fontsize=10)
fig.tight_layout(rect=[0,.045,1,.92]);fig.savefig(A/'散射强度深度_详细方案.png',dpi=180);plt.close(fig)
with (T/'散射深度函数_示例.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['depth_below_surface_km','sigma_percent_reference_sigma9_b5over9_H10']);w.writerows(zip(d,sigma(d)*100))

dem=np.load(R/'data/raw/lola_impact_64/ldem_64_W38_E40_S18_N40_native.npz')
events=list(csv.DictReader((R/'results/impact_audit/events_and_domains.csv').open(encoding='utf-8-sig')))
stations=list(csv.DictReader((R/'results/impact_audit/stations.csv').open(encoding='utf-8-sig')))
e=next(e for e in events if e['event_id']=='A16SIVB');s=next(s for s in stations if s['station']=='S12')
lat0,lat1=float(e['lat']),float(s['lat']);lon0,lon1=float(e['lon']),float(s['lon'])
# Spherical interpolation of the great-circle source-receiver section.
def unit(lat,lon):
    la,lo=np.deg2rad([lat,lon]);return np.array([np.cos(la)*np.cos(lo),np.cos(la)*np.sin(lo),np.sin(la)])
u,v=unit(lat0,lon0),unit(lat1,lon1);ang=np.arccos(u@v);t=np.linspace(0,1,500)
xyz=(np.sin((1-t)*ang)[:,None]*u+np.sin(t*ang)[:,None]*v)/np.sin(ang)
lats=np.rad2deg(np.arcsin(xyz[:,2]));lons=np.rad2deg(np.arctan2(xyz[:,1],xyz[:,0]))
ii=np.abs(dem['latitude_degN'][:,None]-lats).argmin(axis=0)
jj=np.abs(dem['longitude_degE'][:,None]-lons).argmin(axis=0)
h=dem['dn'][ii,jj]*float(dem['height_scale_m'])/1000;dist=t*ang*1737.4
fig,ax=plt.subplots(figsize=(12,5))
ax.fill_between(dist,-h,1-h,color='#f1d4a5',label='表层：当地地表下1 km')
ax.fill_between(dist,1-h,12,color='#e4bda7',label='上月壳：至参考深度12 km')
ax.fill_between(dist,12,28,color='#c0b6ce',label='下月壳：参考深度12–28 km')
ax.fill_between(dist,28,40,color='#d6d8d3',label='月幔：参考深度28 km以下')
ax.plot(dist,-h,'k',lw=1,label='实际 LOLA 地形（原生像元近邻采样）')
ax.plot(dist,10-h,'--',color='#0072B2',lw=1.5,label='散射参数 H=10 km：随当地地表')
for x0,z0,lab in [(dist[0],-h[0],'A16 S-IVB'),(dist[-1],-h[-1],'S12')]:
    ax.scatter(x0,z0,marker='*',s=90,c='black');ax.annotate(lab,(x0,z0),xytext=(0,12),textcoords='offset points',ha='left' if x0==0 else 'right')
ax.set_ylim(40,-7);ax.set_xlim(0,dist[-1]);ax.set_xlabel('沿源—站大圆路径距离 (km)');ax.set_ylabel('相对于参考球面的深度 (km)')
ax.set_title('实际地形与固定背景界面示意：A16 S-IVB → S12\n下部界面为后备模型假设；虚线是散射深度，不是速度界面')
ax.legend(loc='lower left',fontsize=9,ncol=2);fig.tight_layout();fig.savefig(A/'实际地形与固定分层_剖面.png',dpi=180);plt.close(fig)
with (T/'A16SIVB_S12_地形剖面.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['distance_km','lat','lon','height_km']);w.writerows(zip(dist,lats,lons,h))

with (T/'新版首轮24组散射参数.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['id','a_km','sigma0','b','h1_km','H_km','nu','deep_sigma','status'])
    n=0
    for a in [.2,.65,1.3,2,4.5,6]:
        for s in [.05,.09,.10,.15]:
            n+=1;w.writerow([f'SA{n:02d}',a,s,5/9,5,10,.5,.01,'design_not_run'])
spec={'status':'DESIGN_NOT_CGFD3D_PRODUCTION_CONFIG','version':'2026-11-05-detailed',
 'background':{'file':str(raw.relative_to(R)),'sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'fixed':True,'origin':'Garcia2011 model archived with Garcia2019; global fallback','interfaces':'surface+1km; reference-radius depths12km and28km','Q':'raw Qp Qs nodes; constant-Q approximation over admitted band'},
 'scattering':{'family':'3D von Karman','nu':.5,'nu_origin':'new explicit project selection matching exponential special case; NOT verified old production value','a_km':[.2,.65,1.3,2,4.5,6],'sigma0':[.05,.09,.10,.15],'b_stageA':5/9,'b_stageB':[5/9,.85,1],'H_stageA_km':10,'H_stageB_km':[3.5,5,10,20],'h1':'H/2','weak_sigma':.01,'density_random':False,'vp_vs_shared_field':True,'seeds':[1105,2113,3251,4421,5563]},
 'groups':{'W':'S12 S14 overlapping paths jointly, one effective model initially','N15':'A15LM S15 path effective model','S16':'long paths only; no local parameter claim'}}
(T/'详细模拟方案_固定项与搜索项.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
assert np.all(shallow[:,3]>0)
assert np.all(shallow[:,1]**2>4/3*shallow[:,2]**2)
assert np.all(np.isfinite(sigma(d))) and sigma(np.array([28.]))[0]==0
print(json.dumps({'figures':3,'first_stage_models':n,'material_stability':'passed','archive_md5':hashlib.md5((R/'data/raw/background_models/Garcia2019_supplement.zip').read_bytes()).hexdigest()},ensure_ascii=False))
