"""Plot downloaded modern records and joined simulation coverage, without fabricated gaps."""
from pathlib import Path
import csv,json
import numpy as np
from scipy.signal import butter,sosfiltfilt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from build_impact_geometry_audit import EVENTS,STATIONS,arc
ROOT=Path(__file__).resolve().parents[1];FIG=ROOT/'figures/impact_audit'
def read(path):
    with (ROOT/path).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def runs(mask):
    d=np.diff(np.r_[False,mask,False].astype(int));return zip(np.where(d==1)[0],np.where(d==-1)[0])
def display_filter(t,v):
    fs=1/np.median(np.diff(t));work=v.copy()
    for a,b in runs(~np.isfinite(work)):
        if b-a<=2 and a>0 and b<len(work):work[a:b]=np.interp(np.arange(a,b),[a-1,b],[work[a-1],work[b]])
    out=np.full(len(work),np.nan)
    for a,b in runs(np.isfinite(work)):
        if b-a<60*fs:continue
        out[a:b]=sosfiltfilt(butter(4,[.3,.9],fs=fs,btype='bandpass',output='sos'),work[a:b])
        ed=int(10*fs);out[a:a+ed]=np.nan;out[b-ed:b]=np.nan
    out[~np.isfinite(v)]=np.nan
    return out
def main():
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','DejaVu Sans'],'axes.unicode_minus':False,'font.size':10})
    pairs=read('results/impact_pairs_literature.csv');traces=read('results/impact_modern_trace_audit.csv')
    domains={r['event_id']:r for r in read('results/impact_audit/events_and_domains.csv')}
    local={r['event_id']:r for r in read('results/impact_audit/local_simulation_candidates.csv')}
    for eid in EVENTS:
        pp=[p for p in pairs if p['event_id']==eid]
        fig,axs=plt.subplots(len(pp),1,figsize=(8,4.5),layout='constrained',sharex=True,squeeze=False)
        for ax,p in zip(axs[:,0],pp):
            station=p['station'];channel='MH1' if station=='S14' and eid in ['A16SIVB','A17SIVB','A17LM'] else 'MHZ'
            row=next(r for r in traces if r['event_id']==eid and r['station']==station and r['channel']==channel)
            if not row.get('npz'):ax.text(.5,.5,'本通道缺失/排除',transform=ax.transAxes);continue
            with np.load(ROOT/row['npz']) as d:t=d['t'];v=d['velocity_m_s'];meta=json.loads(str(d['metadataJSON']))
            f=display_filter(t,v);use=(t>=-300)&(t<=3600);peak=np.nanmax(np.abs(f[use]));f=f/(peak or 1)
            clear=p['nunn2024_clear'].lower()=='true';color='#126A91' if clear else '#777777'
            ax.plot(t[use],f[use],color=color,lw=.45);ax.axvline(0,color='#777',ls='--',lw=.7)
            flags=[]
            if not clear:flags.append('低SNR')
            if channel=='MH1':flags.append('Z坏')
            if int(float(row.get('clipping_run_samples') or 0))>=3:flags.append('C')
            if row.get('noise_quantization_limited')=='True':flags.append('Q')
            ax.set_ylabel(station+' '+channel+'\n'+(' · '.join(flags) if flags else '代表分量'),rotation=0,ha='right',va='center',fontsize=11)
            ax.set(ylim=(-1.1,1.1),yticks=[0],xlim=(-300,3600));ax.grid(alpha=.18)
        axs[-1,0].set_xlabel('相对地面接收源时 / s；C：削顶待核，Q：前噪声量化',fontsize=11)
        fig.suptitle(eid+'：现代档案代表记录\n名义响应校正；0.3–0.9 Hz 显示滤波；逐道归一化；留白为缺口/边界排除',fontsize=11)
        fig.savefig(FIG/(eid+'_modern_records.png'),dpi=200);plt.close(fig)
        e=EVENTS[eid];dom=domains[eid]
        fig,ax=plt.subplots(figsize=(5.3,4.8),layout='constrained')
        for p in pp:
            v=STATIONS[p['station']];x,y,w=arc(e,v);clear=p['nunn2024_clear'].lower()=='true'
            ax.plot(x,y,color='#3F7899',ls='-' if clear else '--',lw=1.4)
            ax.scatter(v['lon'],v['lat'],marker='^',s=60,c='black',zorder=5)
            ax.annotate(p['station']+('†' if not clear else ''),(v['lon'],v['lat']),xytext=(3,7),textcoords='offset points',fontsize=10,weight='bold',bbox=dict(fc='white',ec='none',alpha=.8,pad=1))
        ax.scatter(e['lon'],e['lat'],marker='*',s=160,c='#C85B28',edgecolor='black',zorder=6)
        for r,c,ls,lw in [(dom,'#52687C','-',1.3)]+([(local[eid],'#C85B28','--',2)] if eid in local else []):
            ax.add_patch(Rectangle((float(r['west_degE']),float(r['south_degN'])),float(r['east_degE'])-float(r['west_degE']),float(r['north_degN'])-float(r['south_degN']),fill=False,ec=c,ls=ls,lw=lw))
        dx=float(dom['east_degE'])-float(dom['west_degE']);dy=float(dom['north_degN'])-float(dom['south_degN'])
        ax.set_xlim(float(dom['west_degE'])-.1*dx,float(dom['east_degE'])+.1*dx);ax.set_ylim(float(dom['south_degN'])-.13*dy,float(dom['north_degN'])+.13*dy)
        ax.set_aspect(1/np.cos(np.deg2rad((float(dom['south_degN'])+float(dom['north_degN']))/2)))
        ax.set(xlabel='经度 / °E',ylabel='纬度 / °N',title=eid+'：源、台站与范围')
        ax.grid(alpha=.2)
        fig.savefig(FIG/(eid+'_coverage_and_domain.png'),dpi=180);plt.close(fig)
    bs=read('results/impact_modern_band_screen.csv');passrows=[r for r in bs if r['provisional_record_screen']=='passes_provisional_screen']
    bands=['0.1-0.3','0.3-0.5','0.5-0.9','0.9-1.5'];names=[r['event_id']+'→'+r['station'] for r in pairs]
    vals=np.zeros((len(pairs),len(bands)),int)
    compact=[]
    for i,p in enumerate(pairs):
        row={'event_id':p['event_id'],'station':p['station'],'nunn2024_clear':p['nunn2024_clear']}
        for j,b in enumerate(bands):
            channels=[r['channel'] for r in passrows if r['event_id']==p['event_id'] and r['station']==p['station'] and r['band_hz']==b]
            vals[i,j]=len(channels);row[b]=';'.join(channels) if channels else '未通过本轮保守自动初筛'
        compact.append(row)
    with (ROOT/'results/impact_audit/modern_band_by_pair.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(compact[0]));w.writeheader();w.writerows(compact)
    fig,ax=plt.subplots(figsize=(8,10),layout='constrained');im=ax.imshow(vals,cmap='Blues',vmin=0,vmax=3,aspect='auto')
    ax.set_xticks(range(4),[b+' Hz' for b in bands]);ax.set_yticks(range(len(names)),names)
    for i in range(len(names)):
        for j in range(4):ax.text(j,i,str(vals[i,j]),ha='center',va='center',color='white' if vals[i,j]>=2 else '#263645')
    ax.set_title('现代档案：各子带通过保守自动初筛的分量数\n0 表示未通过该规则，不表示没有记录；尚非最终反演准入',fontsize=12)
    fig.colorbar(im,ax=ax,ticks=[0,1,2,3],label='分量数');fig.savefig(FIG/'modern_band_screen_matrix.png',dpi=180);plt.close(fig)
    print(json.dumps({'modern_record_figures':9,'coverage_figures':9,'provisional_trace_band_passes':len(passrows)},ensure_ascii=False))
if __name__=='__main__':main()
