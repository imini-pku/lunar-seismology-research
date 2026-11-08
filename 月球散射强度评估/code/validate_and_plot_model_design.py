from pathlib import Path
import json,sys,csv
import numpy as np
from netCDF4 import Dataset
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from build_scattering_models import random_field,background
from score_scattering_waveforms import score

ROOT=Path(__file__).resolve().parents[1]
FIG=ROOT/'figures/model_design';FIG.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','DejaVu Sans'],'axes.unicode_minus':False,'font.size':11})
qa=json.loads((ROOT/'results/scattering_models/material_QA.json').read_text(encoding='utf-8'))
checks={}
for item in qa['models']:
    with Dataset('medium',memory=(ROOT/item['file']).read_bytes()) as d:
        vp=d['vp'][:].filled() if hasattr(d['vp'][:],'filled') else d['vp'][:]
        vs=np.asarray(d['vs'][:]);rho=np.asarray(d['rho'][:]);eta=np.asarray(d['eta'][:])
        checks[item['id']+'_finite_positive_elastic']=bool(np.isfinite(vp).all() and np.all(rho>0) and np.all(vs>0) and np.all(vp**2>4*vs**2/3))
        checks[item['id']+'_normalized_eta']=bool(abs(eta.mean())<1e-6 and abs(eta.std()-1)<1e-5)
        checks[item['id']+'_coupled_vp_vs']=bool(np.allclose(vp/vs,(background(np.arange(256)*100)[0]/background(np.arange(256)*100)[1])[:,None,None],rtol=2e-6))

a=random_field((32,32,32),100,(650,650,650),.5,123,pad=8)
b=random_field((32,32,32),100,(650,650,650),.5,123,pad=8)
c=random_field((32,32,32),100,(650,650,650),.5,124,pad=8)
checks['seed_reproducibility']=bool(np.array_equal(a,b) and not np.array_equal(a,c))
# Analytic test signals only. These are not Apollo data or propagated waveforms.
t=np.arange(-100,3300,.5)
base=np.exp(-((t-600)/220)**2)*np.cos(2*np.pi*.45*t)
obs=np.column_stack([base,.7*base,.3*base])
same=score(t,obs,obs)
scaled=score(t,obs,obs*3)
shift=score(t,obs,np.roll(obs,200,axis=0))
checks['score_identity']=same['total_provisional']<1e-10
checks['common_amplitude_invariance']=scaled['total_provisional']<1e-8
checks['time_shift_penalty']=shift['total_provisional']>.1
try:score(t[:2000],obs[:2000],obs[:2000])
except ValueError: checks['short_window_rejected']=True
else:checks['short_window_rejected']=False
with (ROOT/'config/scattering_run_manifest.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
checks['unique_88_planned_runs']=len(rows)==88 and len({r['run_id'] for r in rows})==88
result={'checks':checks,'all_passed':all(checks.values()),'checks_count':len(checks),
        'material_files':3,'planned_runs':len(rows),'wave_propagation_runs':0,
        'score_test_input':'analytic Gaussian-windowed sinusoids, not Apollo data',
        'identity_score':same['total_provisional'],'shifted_score':shift['total_provisional']}
(ROOT/'reports/scattering_workflow_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
assert result['all_passed'],result

fig,axs=plt.subplots(1,3,figsize=(12,5),layout='constrained',sharey=True)
for ax,item in zip(axs,qa['models']):
    with Dataset('medium',memory=(ROOT/item['file']).read_bytes()) as d:
        eta=np.asarray(d['eta'][:]);vp=np.asarray(d['vp'][:]);z=np.asarray(d['depth'][:])
    vp0=background(z)[0];pert=(vp[:,48,:]/vp0[:,None]-1)*100
    im=ax.imshow(pert,origin='upper',extent=[0,9.5,25.5,0],aspect='auto',cmap='RdBu_r',vmin=-30,vmax=30)
    ax.set_title({'R1':'R1 近均匀强层','R2':'R2 随深度渐弱','R4':'R4 水平长相关'}[item['id']])
    ax.set_xlabel('水平距离 / km');ax.set_ylim(25.5,0)
axs[0].set_ylabel('参考面下深度 / km')
fig.colorbar(im,ax=axs,label='相对 Vp 扰动 / %（端点外饱和）',shrink=.85,extend='both')
fig.suptitle('实际生成的三维介质切片：材料预览，非波场模拟',fontsize=15)
fig.savefig(FIG/'material_sections.png',dpi=180);plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(11.5,5),layout='constrained')
colors=['#0072B2','#D55E00','#009E73']
for item,col in zip(qa['models'],colors):
    zz=np.arange(256)*.1
    axs[0].plot(np.array(item['target_sigma_v'])*100,zz,label=item['id']+' 目标',color=col)
    axs[0].plot(np.array(item['realized_sigma_v_by_depth'])*100,zz,ls=':',color=col,alpha=.65)
    axs[1].plot(np.arange(26)*.1,item['acf_x'],color=col,label=item['id']+' 水平')
    if item['id']=='R4':axs[1].plot(np.arange(26)*.1,item['acf_z'],color=col,ls='--',label='R4 垂向')
axs[1].plot(np.arange(26)*.1,np.exp(-np.arange(26)*.1/.65),'k:',label='连续指数 ACF，a=0.65 km')
axs[0].invert_yaxis();axs[0].set(xlabel='速度扰动标准差 / %',ylabel='深度 / km',title='实线为目标，点线为水平切片实测')
axs[1].set(xlabel='间距 / km',ylabel='归一化自相关',title='有限网格上的实际相关函数',ylim=(-.1,1.03))
for ax in axs:ax.legend(fontsize=9);ax.grid(alpha=.2)
fig.savefig(FIG/'material_statistics.png',dpi=180);plt.close(fig)

z=np.linspace(0,80,801)
fig,axs=plt.subplots(1,2,figsize=(11.5,5),layout='constrained',sharey=True)
for H in [3.5,10,20]:
    sig=np.where(z<H,.1,0)
    axs[0].plot(sig*100,z,label=f'R1 H={H:g} km')
for H,col in zip([20,50,80],colors):
    axs[1].plot(50*np.maximum(1-z/H,0),z,label=f'R5 H={H:g} km',color=col)
axs[0].set(xlabel='标准差 σv / %',ylabel='深度 / km',title='主分支：标准差定义（边界示意）',xlim=(-1,17))
axs[1].set(xlabel='最大幅度 δmax / %',title='竞争分支：有界最大扰动',xlim=(-2,55))
axs[0].invert_yaxis()
for ax in axs:ax.legend();ax.grid(alpha=.2)
fig.savefig(FIG/'depth_family_comparison.png',dpi=180);plt.close(fig)

fig,ax=plt.subplots(figsize=(11,4.5),layout='constrained')
paths=['A12 月海','A14 喷出物','A15 盆地边缘','A16 高地'];x=[-23.4249,-17.47768,3.62991,15.4986];y=[-3.0098,-3.64419,26.13406,-8.9759]
for i in range(4):ax.scatter(x[i],y[i],s=130,marker=['o','s','^','D'][i],color=['#0072B2','#D55E00','#009E73','#CC79A7'][i]);ax.annotate(paths[i],(x[i],y[i]),xytext=(6,9 if i!=1 else -19),textcoords='offset points')
ax.set(xlim=(-32,27),ylim=(-15,34),xlabel='东经 / °',ylabel='纬度 / °',title='候选台站位置示意（NASA ALSEP 坐标，不表示地质边界）');ax.grid(alpha=.2)
fig.savefig(FIG/'station_locations.png',dpi=180);plt.close(fig)
print(json.dumps(result,ensure_ascii=False))
