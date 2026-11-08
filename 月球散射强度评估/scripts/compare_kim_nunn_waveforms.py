"""Matched stored-input comparison, without new signal processing."""
from pathlib import Path
import sys,csv,json
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'.build/waveform_dependencies'))
from obspy import read,UTCDateTime
from scipy.io import loadmat
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pymupdf

out=root/'figures/kim_nunn_comparison_20261103';out.mkdir(parents=True,exist_ok=True)
rs=list(csv.DictReader(open(root/'results/kim2026_audit_20261103/waveform_inventory.csv',encoding='utf-8-sig')))
origins={r['event_id']:UTCDateTime(r['time_earth_received']) for r in csv.DictReader(open(root/'results/impact_audit/events_and_domains.csv',encoding='utf-8-sig'))}
base=root/'data/raw/published_waveform_sources'
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Microsoft YaHei','DejaVu Sans'],'axes.unicode_minus':False,'font.size':10,'path.simplify':False,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
mapping={'Z':'MHZ','N':'MH1','E':'MH2'}
def load(event,station):
    r=next(r for r in rs if r['event']==event and r['station']==station)
    kim=loadmat(base/'Kim2026'/Path(r['archive_file']).relative_to('dataset'),squeeze_me=True)
    name=event.replace('SIVB','_S-IVB').replace('LM','_LM')+'_'+station+'.MSEED'
    p=base/'cerinunn_impact_simulations/input_files/local_MSEED'/name
    return kim,read(str(p)) if p.exists() else None,p

cases=[('A13SIVB','S12',-60,600,'01_A13SIVB_S12_early','近零平台在两套存储输入中均可见；不能视为 Kim 新增或已修复的证据'),('A13SIVB','S12',240,320,'02_A13SIVB_S12_plateau','局部放大：保留真实零值；Nunn 的 −1 缺样码仅以断线显示'),('A14SIVB','S12',-60,3600,'03_A14SIVB_S12_coda','同一台站的长尾波对照；两列使用同一时间范围和同一纵轴范围'),('A14LM','S14',-60,3600,'04_A14LM_S14_coda','S14 尾波与突变的存储输入对照；此图不代表完成异常清洗'),('A17LM','S14',-60,3600,'05_A17LM_S14_missingZ','Nunn 输入未包含 MHZ，Kim 的 Z 来源尚待核实；不能自动视为补回有效垂直观测')]
audit=[]
with PdfPages(out/'Kim2026_vs_Nunn2024_五组对比.pdf') as pdf:
    for event,station,lo,hi,name,note in cases:
        kim,st,p=load(event,station);kt=kim['time']
        fig,axes=plt.subplots(3,2,figsize=(15,10),sharex=True)
        fig.subplots_adjust(left=.075,right=.98,bottom=.17,top=.81,wspace=.15,hspace=.43)
        fig.suptitle(f'{event} → {station}  |  Nunn 2024 与 Kim 2026',fontsize=19,fontweight='bold',y=.97)
        fig.text(.5,.925,'公开存储输入对照，不是两套最终处理输出；不新增滤波、去均值、归一化或重采样',ha='center',fontsize=11)
        fig.text(.5,.89,note,ha='center',fontsize=10,color='#8C3B17')
        fig.text(.29,.85,'Nunn：MiniSEED 归档输入 · 6.625 Hz',ha='center',fontsize=12,color='#17658D',fontweight='bold')
        fig.text(.77,.85,'Kim：作者 uniform.mat · 10 Hz',ha='center',fontsize=12,color='#AA4B10',fontweight='bold')
        for i,(kc,nc) in enumerate(mapping.items()):
            a,b=axes[i];sel=(kt>=lo)&(kt<=hi);kv=kim[kc][sel]
            candidates=st.select(channel=nc) if st else []
            values=[kv];plotted=0;missing=0
            for tr in candidates:
                nt=tr.times()+float(tr.stats.starttime-origins[event]);take=(nt>=lo)&(nt<=hi)
                nv=np.array(tr.data,dtype=float);missing+=int(np.sum(nv[take]==-1));nv[nv==-1]=np.nan
                ln,=a.plot(nt[take],nv[take],color='#17658D',lw=.65,rasterized=True)
                assert np.array_equal(ln.get_ydata(),nv[take],equal_nan=True)
                values.append(nv[take]);plotted+=int(take.sum())
            if not candidates:
                a.set_facecolor('#F2F2F2');a.text(.5,.5,'公开输入中无 MHZ\n不使用其他通道替代',ha='center',va='center',transform=a.transAxes,fontsize=13,color='#555555')
            ln,=b.plot(kt[sel],kv,color='#AA4B10',lw=.65,rasterized=True)
            assert np.array_equal(ln.get_ydata(),kv,equal_nan=True)
            vv=np.concatenate(values);vmin=np.nanmin(vv);vmax=np.nanmax(vv);pad=max((vmax-vmin)*.07,1)
            for ax in [a,b]:
                ax.set_ylim(vmin-pad,vmax+pad);ax.set_xlim(lo,hi);ax.set_ylabel('振幅（DU）');ax.grid(alpha=.16);ax.ticklabel_format(style='plain',useOffset=False)
                if lo<=0<=hi:ax.axvline(0,color='#777777',lw=.7,ls='--')
            a.set_title(nc+f'  |  窗内缺样码 {missing} 点' if candidates else nc+'  |  无该通道',loc='left',fontsize=10)
            b.set_title(kc+('  |  原始通道来源待核实' if not candidates else '  |  作者分量标签'),loc='left',fontsize=10)
            audit.append(dict(case=name,event=event,station=station,kim_component=kc,nunn_channel=nc,nunn_points=plotted,nunn_missing_codes=missing,kim_points=len(kv),kim_zero_points=int(np.sum(kv==0)),window_start=lo,window_end=hi))
        axes[-1,0].set_xlabel('相对目录撞击时刻 / s（地球接收时间）');axes[-1,1].set_xlabel('作者存储相对时间 / s（零点待独立核验）')
        fig.text(.075,.035,'横向同一行共用纵轴范围；不同分量不强行共用纵轴。未作时间平移、幅值配准或极性翻转。\nMH1 / N、MH2 / E 为名义分量对照，Kim 的原始通道映射未完全核实；不据此拟合逐点残差。\n来源：Nunn DOI 10.3847/PSJ/ad83d2（作者仓库输入）；Kim 数据 DOI 10.6084/m9.figshare.32814290。',fontsize=9,color='#444444')
        fig.savefig(out/(name+'.png'),dpi=170,facecolor='white');pdf.savefig(fig,dpi=170);plt.close(fig)
with open(out/'comparison_windows.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=audit[0]);w.writeheader();w.writerows(audit)
(out/'provenance.json').write_text(json.dumps({'comparison_level':'stored input, not complete published processing output','new_filter':False,'resampling':False,'normalization':False,'mean_removal':False,'time_shift':False,'missing_display':'Nunn -1 -> NaN for drawing only; genuine zeros retained','cases':cases},ensure_ascii=False,indent=2),encoding='utf-8')
pdf=pymupdf.open(out/'Kim2026_vs_Nunn2024_五组对比.pdf');assert len(pdf)==5
pdf[0].get_pixmap(matrix=pymupdf.Matrix(1,1)).save(out/'qa_page1.png')
print('Verified 5 PDF pages, 5 comparison figures, 30 panels')
