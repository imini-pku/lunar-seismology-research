"""Audit published author assets and reproduce only explicitly identified functions.

No project deglitcher, filter, detrend, deconvolution, rotation, or clock correction.
Nunn util.py is imported unchanged. Xiao's removal function is extracted verbatim
from the deposited notebook; neither notebook is executed wholesale.
"""
from pathlib import Path
import ast, base64, csv, hashlib, importlib.util, json, sys, warnings
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.build/waveform_dependencies'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from obspy import read, UTCDateTime

SRC = ROOT/'data/raw/published_waveform_sources'
OUT = ROOT/'results/published_waveforms_20261103'
FIG = ROOT/'figures/published_waveforms_20261103'
DER = ROOT/'data/processed/author_code_reproduction_20261103'
for p in [OUT, FIG, DER]: p.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,
                     'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p, obj): p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else str(x)),encoding='utf-8')
def csvout(p,rows):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader();w.writerows(rows)
events=list(csv.DictReader((ROOT/'results/impact_audit/events_and_domains.csv').open(encoding='utf-8-sig')))
pairs=list(csv.DictReader((ROOT/'results/impact_pairs_literature.csv').open(encoding='utf-8-sig')))
lookup={(r['event_id'],r['station']):r for r in pairs}
srcn=SRC/'cerinunn_impact_simulations'
util=srcn/'util.py'
spec=importlib.util.spec_from_file_location('nunn2024_author_util',util)
nunn=importlib.util.module_from_spec(spec);spec.loader.exec_module(nunn)
rawpaths=list((srcn/'input_files/local_MSEED').glob('*.MSEED'))
original_hashes={str(p.relative_to(ROOT)):sha(p) for p in rawpaths}
original_hashes[str(util.relative_to(ROOT))]=sha(util)
channels=['MHZ','MH1','MH2']
rows=[];plot_index=[];trace_inventory=[];all_arrays={}

def raw_name(eid,station):
    if eid.endswith('SIVB'): return eid[:-4]+'_S-IVB_'+station+'.MSEED'
    return eid[:-2]+'_LM_'+station+'.MSEED'

for event in events:
    eid=event['event_id'];origin=UTCDateTime(event['time_earth_received'])
    stations=[p['station'] for p in pairs if p['event_id']==eid]
    for sta in stations:
        path=srcn/'input_files/local_MSEED'/raw_name(eid,sta);stream=read(str(path))
        for tr in stream:
            trace_inventory.append({'file':path.name,'id':tr.id,'start':str(tr.stats.starttime),
                                    'end':str(tr.stats.endtime),'npts':tr.stats.npts,'sampling_rate':tr.stats.sampling_rate})
        for cha in channels:
            key=f'{eid}_{sta}_{cha}';trs=list(stream.select(channel=cha))
            row={'event':eid,'station':sta,'channel':cha,'distance_km':lookup[(eid,sta)]['distance_published_km'],
                 'input':str(path.relative_to(ROOT)),'author_raw_exists':bool(trs),
                 'input_samples':0,'missing_samples':0,'author_interpolated_samples':0,
                 'filled_samples_inside_long_gaps':0,'measured_samples_changed':0,
                 'method':'Nunn2024 util.linear_interpolation(interpolation_limit=1)' if trs else 'missing',
                 'new_bandpass':'none','response_removed':False,
                 'frequency_reference_Hz':'0.2-0.95 (literature reference only)' if trs else 'N/A',
                 'individual_trust_band':'not established' if trs else 'N/A',
                 'selection':'basic preparation only; not fully deglitched' if trs else 'not available'}
            if not trs:
                rows.append(row);continue
            assert len(trs)==1, (key,'segmented input needs explicit handling')
            tr=trs[0];raw=tr.data.copy();processed=tr.copy()
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',FutureWarning)
                nunn.linear_interpolation(processed,interpolation_limit=1)
            source_mask=(raw==-1)|np.ma.getmaskarray(raw)
            remaining_mask=np.ma.getmaskarray(processed.data)
            filled=source_mask & ~remaining_mask
            valid=~source_mask
            changed=np.count_nonzero(np.asarray(processed.data)[valid]!=np.asarray(raw)[valid])
            assert changed==0, key
            # This is an audit of pandas limit semantics, NOT a processing rule.
            edges=np.flatnonzero(np.diff(np.r_[False,source_mask,False].astype(int)))
            long_filled=sum(int(filled[a:b].sum()) for a,b in edges.reshape(-1,2) if b-a>1)
            time=tr.stats.starttime-origin+np.arange(len(raw))*tr.stats.delta
            row.update(input_samples=len(raw),missing_samples=int(source_mask.sum()),
                       author_interpolated_samples=int(filled.sum()),filled_samples_inside_long_gaps=long_filled,
                       measured_samples_changed=changed)
            rows.append(row)
            arr={'time_seconds':time,'raw_DU':np.asarray(raw),'raw_missing_mask':source_mask,
                 'nunn_basic_DU':np.asarray(processed.data),'nunn_remaining_mask':remaining_mask,
                 'author_filled_mask':filled}
            np.savez_compressed(DER/(key+'.npz'),**arr)
            all_arrays[key]=arr
    # At most two stations (six component rows) on each sheet.
    for g in range(0,len(stations),2):
        group=stations[g:g+2]; nrow=len(group)*3
        fig=plt.figure(figsize=(16,1.45*nrow+1.65))
        grid=fig.add_gridspec(nrow,3,width_ratios=[4.4,4.4,2.2],left=.065,right=.99,bottom=.085,top=.88,wspace=.19,hspace=.38)
        for j,(sta,cha) in enumerate((s,c) for s in group for c in channels):
            key=f'{eid}_{sta}_{cha}';row=next(r for r in rows if (r['event'],r['station'],r['channel'])==(eid,sta,cha))
            ax=fig.add_subplot(grid[j,0]);bx=fig.add_subplot(grid[j,1]);tx=fig.add_subplot(grid[j,2]);tx.axis('off')
            if key not in all_arrays:
                for a in [ax,bx]:
                    a.set_facecolor('#f4f4f4');a.text(.5,.5,'作者缓存中无该分量\n不生成替代波形',ha='center',va='center',transform=a.transAxes)
                    a.set_xticks([]);a.set_yticks([])
                ax.set_ylabel(f'{sta} · {cha}\nDU');tx.text(0,.5,'缺失项\n可信频段：不适用',va='center')
                continue
            v=all_arrays[key];t=v['time_seconds'];win=(t>=-600)&(t<=5400)
            y=np.ma.array(v['raw_DU'],mask=v['raw_missing_mask']);z=np.ma.array(v['nunn_basic_DU'],mask=v['nunn_remaining_mask'])
            ax.plot(t[win]/60,y[win],color='#4d5662',lw=.45,rasterized=True)
            bx.plot(t[win]/60,z[win],color='#006c91',lw=.45,rasterized=True)
            f=v['author_filled_mask']&win
            if f.any():bx.plot(t[f]/60,v['nunn_basic_DU'][f],'.',color='#ce7519',ms=2)
            finite=np.asarray(y[win].compressed());limits=(finite.min(),finite.max()) if len(finite) else (0,1)
            pad=max((limits[1]-limits[0])*.08,1)
            for a in [ax,bx]:
                a.set_xlim(-10,90);a.set_ylim(limits[0]-pad,limits[1]+pad);a.axvline(0,color='#c43b3b',lw=.7,ls='--')
                a.grid(alpha=.15);a.tick_params(labelsize=8)
                if j==nrow-1:a.set_xlabel('相对撞击时间 / min（档案名义时轴）')
            ax.set_ylabel(f'{sta} · {cha}\nDU',fontsize=9)
            tx.text(0,.98,f"距离 {float(row['distance_km']):.1f} km\n作者函数：缺样掩码＋有限插值\n缺样 {row['missing_samples']} 点；补入 {row['author_interpolated_samples']} 点\n实测点改动：0\n滤波 / 去响应：均未执行\n去 glitch / 削顶修复：未执行\n参考 0.2–0.95 Hz，逐条可信带待核",va='top',fontsize=8.2,linespacing=1.45)
            if j==0:
                ax.set_title('原始档案 DU（−1 缺样码不连线）',fontsize=11,pad=9)
                bx.set_title('Nunn 2024 作者基础函数复现 · 未滤波',fontsize=11,pad=9)
        fig.suptitle(f'{eid}  |  {"、".join(group)}  |  原始与作者代码基础预处理对照',fontsize=15,y=.975)
        fig.text(.065,.928,'右列不是“全面清洗完成”：保留仪器响应、异常和原有直流电平；两列同一纵轴，不逐条归一化。',fontsize=10,color='#6d4520')
        fig.text(.065,.022,'来源：Nunn et al. (2024), 10.3847/PSJ/ad83d2；GitHub impact_simulations/util.py。橙点为作者函数补入的缺样值，不能当作实测数据。',fontsize=8.5)
        name=f'{eid}_{"_".join(group)}_author_basic'
        fig.savefig(FIG/(name+'.png'),dpi=150);fig.savefig(FIG/(name+'.pdf'));plt.close(fig)
        plot_index.append({'event':eid,'stations':group,'png':name+'.png','type':'author basic reproduction, not complete cleaning'})

# Reproduce the exact published exclusion function on its own supplied data and windows.
xp=SRC/'MrXiaoXiao_Apollo_Disturbance_Detection/Reproduce_figures_in_the_manuscript'
notebook=xp/'Reproduce_Figures6_7_S23_S30.ipynb'
nb=json.loads(notebook.read_text(encoding='utf-8'))
function_source=None
for c in nb['cells']:
    s=''.join(c.get('source',[]))
    if 'def remove_detected_windows(' in s:
        node=next(n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name=='remove_detected_windows')
        function_source=ast.get_source_segment(s,node);break
assert function_source is not None
(OUT/'xiao_remove_detected_windows_verbatim.py').write_text(function_source+'\n',encoding='utf-8')
ns={'np':np};exec(compile(function_source,str(notebook),'exec'),ns)
xiao=[]
for f in sorted(xp.glob('EV_*.npy')):
    eid='A'+f.name.split('_')[1]+'SIVB';ev=next(e for e in events if e['event_id']==eid);t0=UTCDateTime(ev['time_earth_received'])
    # Payloads were inspected: only numpy/ObsPy reconstruction classes; SHA256 matches Git LFS.
    obj=np.load(f,allow_pickle=True).item()
    fig,axes=plt.subplots(3,1,figsize=(13.2,8.4),sharex=True)
    nfull=0;nkept=0;span_list=[];pieces=[]
    for key,entry in obj.items():
        tr=entry['trace'];data=tr.data.astype(np.float64);windows=[list(w) for w in entry['windows']]
        # Same boundary adjustment as the author's calling notebook cell.
        if windows[0][0] < 0: windows[0][0] = 0
        time=np.arange(len(data))*tr.stats.delta
        ft,fy=ns['remove_detected_windows'](time,data,windows)
        rel=time+(tr.stats.starttime-t0);frel=ft+(tr.stats.starttime-t0)
        sel=(rel>=-600)&(rel<=5400);fsel=(frel>=-600)&(frel<=5400)
        eventwin=(rel>=0)&(rel<=3600);keptwin=(frel>=0)&(frel<=3600)
        nfull+=int(eventwin.sum());nkept+=int(keptwin.sum())
        # Save only relevant excerpts of the reproduced output; native retained times remain irregular.
        pieces.append((frel[fsel],fy[fsel]))
        y=np.ma.masked_equal(data[sel],-1);axes[0].plot(rel[sel]/60,y,color='#56606b',lw=.5)
        axes[1].plot(rel[sel]/60,y,color='#56606b',lw=.5)
        kept_t=frel[fsel];kept_y=fy[fsel]
        # Break plotting lines at deleted windows: do not connect distant retained samples.
        cuts=np.r_[0,np.flatnonzero(np.diff(kept_t)>tr.stats.delta*1.5)+1,len(kept_t)]
        for a,b in zip(cuts[:-1],cuts[1:]):
            axes[2].plot(kept_t[a:b]/60,np.ma.masked_equal(kept_y[a:b],-1),color='#007c83',lw=.55)
        for a,b in windows:
            # Preserve the exact published Python slice semantics, including negative/out-of-range bounds.
            sa,sb,_=slice(int(a),int(b)+1).indices(len(data))
            if sb<=sa:continue
            ta=(tr.stats.starttime-t0)+sa*tr.stats.delta;tb=(tr.stats.starttime-t0)+(sb-1)*tr.stats.delta
            if tb>=-600 and ta<=5400:
                axes[1].axvspan(max(-600,ta)/60,min(5400,tb)/60,color='#e8a2a2',alpha=.45,lw=0)
                span_list.append([ta,tb])
    rawarr=all_arrays[eid+'_S12_MHZ'];visible=(rawarr['time_seconds']>=-600)&(rawarr['time_seconds']<=5400)&~rawarr['raw_missing_mask']
    lo=float(rawarr['raw_DU'][visible].min());hi=float(rawarr['raw_DU'][visible].max());pad=max((hi-lo)*.08,1)
    titles=['作者 NPY 中的观测输入（未滤波）','同一输入＋作者提供的排除时间窗（粉色）','原样调用作者删窗函数后的剩余点（未滤波；不补回被删信号）']
    for ax,title in zip(axes,titles):
        ax.set_title(title,loc='left',fontsize=11);ax.set_ylabel('DU');ax.set_ylim(lo-pad,hi+pad);ax.set_xlim(-10,90);ax.axvline(0,color='#bd3535',ls='--',lw=.8);ax.grid(alpha=.15)
    removed=100*(1-nkept/nfull) if nfull else None
    axes[-1].set_xlabel('相对撞击时间 / min（作者数据名义时轴）')
    fig.suptitle(f'{eid} · S12 · MHZ  |  Xiao 2025 作者代码适用性检查',fontsize=15,y=.98)
    fig.text(.085,.91,f'撞击后 0–60 min 的存储采样点排除比例：{removed:.1f}%（含输入中的缺样码；不是能量比例）。',fontsize=11,color='#a23832')
    fig.text(.085,.025,'Before/After = 撞击前后各 10 天，不是清洗前后。此删窗用于长周期研究，会删除撞击尾波；本项目不采用为散射反演输入。\n来源：Xiao et al. (2025), 10.1785/0120250012；作者公开 NPY、windows 与 remove_detected_windows 函数。',fontsize=9)
    fig.subplots_adjust(top=.855,bottom=.13,hspace=.4,left=.085,right=.985)
    name=eid+'_S12_MHZ_Xiao_author_exclusion'
    fig.savefig(FIG/(name+'.png'),dpi=150);fig.savefig(FIG/(name+'.pdf'));plt.close(fig)
    outt=np.concatenate([a for a,b in pieces]);outy=np.concatenate([b for a,b in pieces])
    np.savez_compressed(DER/(name+'.npz'),retained_relative_time_seconds=outt,retained_DU=outy)
    xiao.append({'event':eid,'station':'S12','channel':'MHZ','file':f.name,'sha256':sha(f),
                 'stored_keys':list(obj),'removed_sample_percent_0_60min':removed,
                 'author_windows_seconds':span_list,'selection':'reject for scattering-coda inversion',
                 'reproduced_function':'remove_detected_windows; unchanged source; no mean removal, spectrum or filtering',
                 'figure':name+'.png'})

csvout(OUT/'逐记录作者处理与频段状态.csv',rows)
dump(OUT/'source_trace_inventory.json',trace_inventory)
dump(OUT/'split_figure_index.json',plot_index)
dump(OUT/'xiao_author_window_audit.json',xiao)
dump(OUT/'raw_hashes_before_after.json',{'before':original_hashes,'after':{p:sha(ROOT/p) for p in original_hashes}})
assert original_hashes=={p:sha(ROOT/p) for p in original_hashes}
dump(OUT/'execution_summary.json',{'events':len(events),'event_station_pairs':len(pairs),
    'component_slots':len(rows),'actual_components':sum(r['author_raw_exists'] for r in rows),
    'nunn_basic_figures':len(plot_index),'xiao_diagnostic_figures':len(xiao),
    'total_source_missing_samples':sum(r['missing_samples'] for r in rows),
    'total_author_filled_samples':sum(r['author_interpolated_samples'] for r in rows),
    'filled_samples_in_long_gaps':sum(r['filled_samples_inside_long_gaps'] for r in rows),
    'measured_samples_changed':sum(r['measured_samples_changed'] for r in rows),
    'new_filters':0,'deconvolutions':0,'custom_glitch_fits':0,'fully_cleaned_qualified_components':0,
    'source_util_sha256':sha(util),'xiao_function_sha256':sha(OUT/'xiao_remove_detected_windows_verbatim.py'),
    'numpy':np.__version__,'pandas':pd.__version__,
    'scope':'author basic preparation and rejected author exclusion demonstration; not full cleaning'})
print((OUT/'execution_summary.json').read_text(encoding='utf-8'))
