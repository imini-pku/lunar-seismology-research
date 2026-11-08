"""Auditable per-record Apollo cleaning. Never modifies archive or v2 arrays.

Zhang 2025 motivates the artifact classes, bit-flip constraint and step-response
fit. Numerical screening thresholds here are project choices, not paper values.
Glitch fits require a separate reviewed acceptance list before subtraction.
"""
from pathlib import Path
import sys, json, csv, hashlib, argparse
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.build/waveform_dependencies'))
import numpy as np
from scipy.ndimage import median_filter, maximum_filter1d
from scipy.signal import find_peaks, butter, sosfiltfilt, welch
from scipy.optimize import least_squares
from obspy import read, read_inventory, Trace, UTCDateTime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

OUT = ROOT / 'data/processed/individual_cleaning_20261103'
RES = ROOT / 'results/individual_cleaning_20261103'
FIG = ROOT / 'figures/individual_cleaning_20261103'
for p in [OUT, RES, FIG]: p.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,
                     'pdf.fonttype':42, 'font.size':9, 'path.simplify':False})
BANDS = [(.3,.5),(.5,.9),(.3,.9),(.9,1.5)]
WINDOW = (-610,3610)

def rows(path):
    return list(csv.DictReader((ROOT/path).open(encoding='utf-8-sig')))

def writecsv(path, data):
    keys = list(dict.fromkeys(k for r in data for k in r))
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(data)

def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def runs(mask):
    z=np.diff(np.r_[False,mask,False].astype(int))
    return list(zip(np.where(z==1)[0],np.where(z==-1)[0]))

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def load(key):
    p=ROOT/'data/processed/waveform_comparison_v2'/f'{key}.npz'
    with np.load(p) as d: a={k:d[k].copy() for k in d.files if k!='metadataJSON'}
    a['meta']=json.loads(str(np.load(p)['metadataJSON']))
    return a

def despike(raw, gaps):
    """Only an isolated one-sample, unique single-bit reversal is eligible.
    No replacement with a smooth interpolant. Reject neighbourhoods with gaps.
    """
    y=raw.copy(); logs=[]; changed=np.zeros(len(y),bool)
    for i in np.where((~gaps[2:-2]) & (abs(raw[2:-2]-(raw[1:-3]+raw[3:-1])/2)>=16))[0]+2:
        a=max(0,i-33);b=min(len(y),i+34)
        if a==0 or b==len(y) or gaps[a:b].any(): continue
        neigh=np.r_[np.diff(raw[a:i]),np.diff(raw[i+1:b])]
        scale=max(1.,float(np.median(abs(neigh))))
        pred=(raw[i-1]+raw[i+1])/2
        err=abs(raw[i]-pred)
        if err < max(16,16*scale): continue
        if abs(raw[i-1]-raw[i+1])>max(3,2*scale): continue
        tol=max(1.,.25*scale)
        possibilities=[(k,int(raw[i])^(1<<k)) for k in range(4,10)
                       if abs((int(raw[i])^(1<<k))-pred)<=tol]
        if len(possibilities)!=1: continue
        bit,new=possibilities[0]
        # Corrected point must also agree with the second neighbours.
        if max(abs(new-raw[i-2]),abs(new-raw[i+2]))>max(4,3*scale): continue
        logs.append(dict(index=int(i),raw_DU=float(raw[i]),corrected_DU=float(new),bit_zero_based=bit,
                         neighbour_prediction_DU=float(pred),local_diff_scale_DU=scale,
                         rule='unique_single_bit_reversal; project_conservative_rule'))
        y[i]=new;changed[i]=True
    return y,changed,logs

def clip_masks(y,gaps,sta,fs):
    rail=(~gaps)&((y<=0)|(y>=1023));internal=np.zeros(len(y),bool);logs=[]
    if sta=='S14':
        # Inspect all reported internal levels, without assuming their epoch.
        for level in [319,383,447,511,575,639]:
            for a,b in runs((y==level)&~gaps):
                if b-a<3: continue
                l=max(0,a-int(2*fs));r=min(len(y),b+int(2*fs))
                if gaps[l:r].any() or a==l or b==r: continue
                left=y[l:a]-level;right=y[b:r]-level
                upper=(np.all(left<=0) and np.all(right<=0) and min(left.min(),right.min())<=-4
                       and left.min()<=-3 and right.min()<=-3)
                lower=(np.all(left>=0) and np.all(right>=0) and max(left.max(),right.max())>=4
                       and left.max()>=3 and right.max()>=3)
                if upper or lower:
                    internal[a:b]=True
                    logs.append(dict(start_index=int(a),stop_index=int(b),level_DU=level,
                                     status='suspected_internal_clipping_not_proven'))
    # One-second padding before segmented response removal. Larger edge masks follow.
    exclude=maximum_filter1d((rail|internal).astype(int),size=2*int(np.ceil(fs))+1)>0
    exclude &= ~gaps
    return rail,internal,exclude,logs

def templates():
    """Peaked-mode step responses using Zhang's released transfer expression.
    Correct FFT bins; no claim of bitwise MATLAB replication. Fit amplitudes
    absorb scale. All project event dates fall outside listed flat-mode dates.
    """
    dt=1/53.;n=32768;s=2j*np.pi*np.fft.rfftfreq(n,dt)
    bank=[]
    for f0 in [.055,.06667,.078]:
      for h in [.7,.85,1.0]:
       for k2 in [1.3e-5,1.6e-5,1.9e-5]:
        lp=(8.72665**2/(s*s+2*np.cos(np.pi/8)*8.72665*s+8.72665**2))**2
        lp*= (8.72665**2/(s*s+2*np.cos(3*np.pi/8)*8.72665*s+8.72665**2))**2
        loop=500000/(s*s+2*h*(2*np.pi*f0)*s+(2*np.pi*f0)**2)*47.62/(47.62+s)
        acc=204.8*31.6*s/(.0628+s)*lp*loop/(1+k2*loop)
        astep=np.zeros(len(s),complex);astep[1:]=acc[1:]/s[1:]
        astep[0]=204.8*31.6/.0628*loop[0]/(1+k2*loop[0])
        arr=np.array([np.fft.irfft(astep,n),np.fft.irfft(acc,n),np.fft.irfft(s*acc,n)]).T
        arr=arr[:int(180/dt)];arr/=np.max(abs(arr),axis=0)
        bank.append((dict(f0_hz=f0,h=h,K2=k2),np.arange(len(arr))*dt,arr))
    return bank

def detect_and_fit(y,gaps,t,fs,bank,exclude):
    work=y.copy();work[gaps]=np.nan
    baseline=median_filter(np.where(gaps,np.nanmedian(work),work),size=201)
    err=np.abs(work-baseline);diff=np.diff(work)
    global_scale=max(1.,float(np.nanmedian(abs(diff))))
    peaks,_=find_peaks(np.nan_to_num(err),prominence=max(12,12*global_scale),distance=int(40*fs))
    # Only isolated strong transients relative to adjacent 20 s background.
    results=[]
    for peak in peaks:
        i0=peak-int(8*fs);i1=peak+int(100*fs)
        if i0<0 or i1>len(y): continue
        before=work[max(0,peak-int(30*fs)):max(1,peak-int(10*fs))]
        noise=max(1.,float(np.nanstd(before)))
        if not np.isfinite(noise) or err[peak]<8*noise: continue
        rec=dict(peak_index=int(peak),peak_time_s=float(t[peak]),start_index=int(i0),stop_index=int(i1),
                 amplitude_over_pre_noise=float(err[peak]/noise),status='candidate_unresolved')
        if gaps[i0:i1].any() or exclude[i0:i1].any():
            rec['reason']='gap_or_clipping_in_fit_window';results.append(rec);continue
        xx=t[i0:i1]-t[peak];yy=y[i0:i1]
        trend=np.column_stack([np.ones(len(xx)),xx/100])
        base=trend@np.linalg.lstsq(trend,yy,rcond=None)[0]
        sse0=np.sum((yy-base)**2);best=None
        for pars,tt,gg in bank:
            for onset in np.arange(-5.,.01,.25):
                q=xx-onset
                G=np.column_stack([np.interp(q,tt,gg[:,k],left=0,right=0) for k in range(3)])
                X=np.column_stack([G,trend]);coef=np.linalg.lstsq(X,yy,rcond=None)[0]
                fit=X@coef;sse=np.sum((yy-fit)**2)
                if best is None or sse<best[0]:best=(sse,pars,onset,coef,G@coef[:3],fit)
        sse,pars,onset,coef,component,fit=best
        vr=1-sse/sse0 if sse0 else 0
        rec.update(parameters=pars,onset_relative_peak_s=float(onset),variance_reduction=float(vr),
                   residual_rms_DU=float(np.sqrt(sse/len(xx))),pre_noise_DU=noise,
                   status='fit_candidate_review_required' if vr>.9 else 'poor_fit_no_subtraction',
                   component=component.tolist(),fit=fit.tolist())
        results.append(rec)
    return results

def audit():
    bank=templates();allfits=[];summary=[];spikes=[];clips=[]
    for p in sorted((ROOT/'data/processed/waveform_comparison_v2').glob('*.npz')):
        key=p.stem;d=load(key);raw=d['raw_counts'];gap=d['original_gap_mask'];t=d['t'];fs=d['meta']['effective_fs_hz']
        y,mask,log=despike(raw,gap)
        for r in log:r.update(record=key,time_s=float(t[r['index']]))
        spikes+=log
        rail,internal,exclude,cl=clip_masks(y,gap,key.split('_')[1],fs)
        for r in cl:r.update(record=key,start_s=float(t[r['start_index']]),end_s=float(t[r['stop_index']-1]))
        clips+=cl
        fits=detect_and_fit(y,gap,t,fs,bank,exclude)
        for j,r in enumerate(fits):r.update(record=key,fit_id=f'{key}_G{j+1:02d}')
        allfits+=fits
        r=dict(record=key,spike_samples=int(mask.sum()),rail_samples=int(rail.sum()),internal_suspect_samples=int(internal.sum()),
               glitch_candidates=len(fits),good_fit_candidates=sum(f['status']=='fit_candidate_review_required' for f in fits))
        summary.append(r);print(r,flush=True)
    dump(RES/'glitch_fits.json',allfits);writecsv(RES/'initial_audit.csv',summary)
    writecsv(RES/'spike_corrections.csv',spikes);writecsv(RES/'internal_clip_candidates.csv',clips)
    plot_fits(allfits)

def plot_fits(fits):
    fitted=[r for r in fits if 'fit' in r]
    for page in range((len(fitted)+11)//12):
        fig,axs=plt.subplots(6,2,figsize=(17,18));axs=axs.ravel()
        for ax,r in zip(axs,fitted[page*12:(page+1)*12]):
            d=load(r['record']);a,b=r['start_index'],r['stop_index'];t=d['t'][a:b]
            y,_,_=despike(d['raw_counts'],d['original_gap_mask']);y=y[a:b]
            ax.plot(t,y,color='#333333',lw=.7,label='原始去尖峰后')
            ax.plot(t,r['fit'],color='#b33b2e',lw=1,label='拟合（尚未接受）')
            ax.plot(t,y-np.asarray(r['component']),color='#167d8d',lw=.7,label='减除后的候选')
            ax.set_title(f"{r['fit_id']} | VR={r['variance_reduction']:.3f}",fontsize=10)
            ax.set(xlabel='ATT 时间 / s',ylabel='DU');ax.grid(alpha=.15)
        for ax in axs[len(fitted[page*12:(page+1)*12]):]:ax.axis('off')
        axs[0].legend(fontsize=8);fig.tight_layout();fig.savefig(FIG/f'glitch_fit_review_{page+1:02d}.png',dpi=130);plt.close(fig)

def refine():
    fits=json.loads((RES/'glitch_fits.json').read_text(encoding='utf-8'))
    dt=1/53.;n=32768;s=2j*np.pi*np.fft.rfftfreq(n,dt);tt=np.arange(int(180/dt))*dt
    lp=(8.72665**2/(s*s+2*np.cos(np.pi/8)*8.72665*s+8.72665**2))**2
    lp*= (8.72665**2/(s*s+2*np.cos(3*np.pi/8)*8.72665*s+8.72665**2))**2
    for r in fits:
        if 'fit' not in r:continue
        d=load(r['record']);a,b=r['start_index'],r['stop_index']
        y,_,_=despike(d['raw_counts'],d['original_gap_mask']);yy=y[a:b];xx=d['t'][a:b]-r['peak_time_s']
        trend=np.column_stack([np.ones(len(xx)),xx/100])
        def calc(p):
            f0,h,k,onset=p;w0=2*np.pi*f0
            loop=500000/(s*s+2*h*w0*s+w0*w0)*47.62/(47.62+s)
            acc=204.8*31.6*s/(.0628+s)*lp*loop/(1+k*1e-5*loop)
            astep=np.zeros(len(s),complex);astep[1:]=acc[1:]/s[1:]
            astep[0]=204.8*31.6/.0628*loop[0]/(1+k*1e-5*loop[0])
            arr=np.array([np.fft.irfft(astep,n),np.fft.irfft(acc,n),np.fft.irfft(s*acc,n)]).T[:len(tt)]
            arr/=np.max(abs(arr),axis=0)
            G=np.column_stack([np.interp(xx-onset,tt,arr[:,j],left=0,right=0) for j in range(3)])
            X=np.column_stack([G,trend]);co=np.linalg.lstsq(X,yy,rcond=None)[0]
            return X@co,G@co[:3]
        pars=r['parameters'];x0=[pars['f0_hz'],pars['h'],pars['K2']/1e-5,r['onset_relative_peak_s']]
        x0=np.clip(x0,[.04500001,.60000001,1.30000001,-5.99999],[.08499999,1.09999999,1.89999999,.49999])
        opt=least_squares(lambda p:calc(p)[0]-yy,x0,bounds=([.045,.6,1.3,-6],[.085,1.1,1.9,.5]),
                          diff_step=1e-3,max_nfev=80,xtol=1e-6,ftol=1e-6,gtol=1e-6)
        fit,component=calc(opt.x);base=trend@np.linalg.lstsq(trend,yy,rcond=None)[0]
        sse=np.sum((yy-fit)**2);vr=1-sse/np.sum((yy-base)**2)
        r.update(coarse_variance_reduction=r['variance_reduction'],variance_reduction=float(vr),
                 parameters=dict(f0_hz=float(opt.x[0]),h=float(opt.x[1]),K2=float(opt.x[2]*1e-5)),
                 onset_relative_peak_s=float(opt.x[3]),residual_rms_DU=float(np.sqrt(sse/len(xx))),
                 fit=fit.tolist(),component=component.tolist(),optimizer_success=bool(opt.success),
                 status='fit_candidate_review_required' if vr>.9 else 'poor_fit_no_subtraction')
        print(r['fit_id'],round(vr,4),flush=True)
    dump(RES/'glitch_fits.json',fits);plot_fits(fits)

def response_chain(y,missing,stats,origin,t,inventory):
    fs=1/np.median(np.diff(t));work=y.copy();work[missing]=np.nan
    # No interpolation across excluded artifacts. No interpolation across gaps.
    outputs={f'{lo:g}-{hi:g}':np.full(len(y),np.nan) for lo,hi in BANDS}
    resp=np.full(len(y),np.nan);edge=np.zeros(len(y),bool);short=np.zeros(len(y),bool);logs=[]
    for a,b in runs(np.isfinite(work)):
        dur=(b-a)/fs
        if dur<60:short[a:b]=True;continue
        tr=Trace(work[a:b].copy(),header=dict(stats));tr.stats.starttime=origin+float(t[a]);tr.stats.sampling_rate=6.625
        tr.detrend('linear');tr.detrend('demean')
        try:
            tr.remove_response(inventory=inventory,output='VEL',pre_filt=[.05,.1,1.5,2.],water_level=None,zero_mean=True,taper=True,taper_fraction=.03)
            resp[a:b]=tr.data
            for lo,hi in BANDS:outputs[f'{lo:g}-{hi:g}'][a:b]=sosfiltfilt(butter(4,[lo,hi],fs=fs,btype='bandpass',output='sos'),tr.data)
            n=int(np.ceil(max(20,.03*dur)*fs));edge[a:min(a+n,b)]=True;edge[max(a,b-n):b]=True
            logs.append(dict(start_index=int(a),stop_index=int(b),duration_s=float(dur),edge_each_side_s=float(n/fs),status='ok'))
        except Exception as e:logs.append(dict(start_index=int(a),stop_index=int(b),status='failed',error=str(e)))
    return outputs,resp,edge,short,logs

def process():
    fits=json.loads((RES/'glitch_fits.json').read_text(encoding='utf-8'))
    accepted_path=RES/'reviewed_glitch_decisions.json'
    decisions=json.loads(accepted_path.read_text(encoding='utf-8')) if accepted_path.exists() else {}
    catalogue=rows('data/raw/literature/Liu2025_ACC/event_window_glitch_catalogue.csv')
    invpath=ROOT/'data/raw/impact_metadata/stationxml.xa.0.sxml';inv=read_inventory(str(invpath))
    pairs=rows('results/impact_pairs_literature.csv');records=[];bands=[];allsegments=[];checks=[]
    for pair in pairs:
      eid,sta=pair['event_id'],pair['station']
      stream=read(str(ROOT/'data/raw/impact_modern'/f'{eid}_{sta}_MP_ATT.mseed'))
      for ch in ['MHZ','MH1','MH2']:
        key=f'{eid}_{sta}_{ch}';base=dict(record=key,event_id=eid,station=sta,channel=ch,distance_km=float(pair['distance_published_km']))
        if not (ROOT/'data/processed/waveform_comparison_v2'/f'{key}.npz').exists():
            records.append(dict(base,status='missing_archive',note='S14 MHZ 已知故障时段，档案未返回；未补造'));continue
        d=load(key);meta=d['meta'];t=d['t'];raw=d['raw_counts'];gaps=d['original_gap_mask'];fs=meta['effective_fs_hz']
        src=ROOT/meta['source_file'];assert sha(src)==meta['source_sha256']
        tr=stream.select(channel=ch).copy();tr.merge(method=1,fill_value=None);tr=tr[0]
        assert np.array_equal(raw,np.asarray(np.ma.filled(tr.data,-1),float))
        y,spmask,splog=despike(raw,gaps)
        rail,internal,excluded,cl=clip_masks(y,gaps,sta,fs)
        glcomponent=np.zeros(len(y));glmask=np.zeros(len(y),bool);accepted=[];unresolved=[]
        ownfits=[r for r in fits if r['record']==key]
        owncatalog=[r for r in catalogue if r['event_id']==eid and r['station_code']==sta and r['Component']==ch]
        for r in ownfits:
            decision=decisions.get(r['fit_id'],{})
            if decision.get('action')=='subtract':
                assert 'component' in r and r['variance_reduction']>.9
                a,b=r['start_index'],r['stop_index'];assert not glmask[a:b].any()
                glcomponent[a:b]+=np.asarray(r['component']);glmask[a:b]=True;accepted.append(r['fit_id'])
            else:unresolved.append(r['fit_id'])
        y-=glcomponent
        clean=y.copy();clean[gaps|excluded]=np.nan
        # Bridge <=2 original missing samples solely as computational support;
        # never bridge exclusions; restore all original gaps after response removal.
        computational=clean.copy();temporary=np.zeros(len(y),bool)
        for a,b in runs(gaps):
            if b-a<=2 and a>0 and b<len(y) and np.isfinite(clean[a-1]) and np.isfinite(clean[b]):
                computational[a:b]=np.interp(np.arange(a,b),[a-1,b],[clean[a-1],clean[b]]);temporary[a:b]=True
        origin=UTCDateTime(meta['origin_earth_received'])
        filt,resp,edge,short,seg=response_chain(computational,~np.isfinite(computational),tr.stats,origin,t,inv)
        # Also exclude +/- 10 s around temporarily bridged original gaps from screening.
        gapguard=(maximum_filter1d(temporary.astype(int),size=2*int(np.ceil(10*fs))+1)>0)
        for val in list(filt.values())+[resp]:val[gaps|excluded]=np.nan
        edge[gaps|excluded]=False
        for s in seg:s['record']=key
        allsegments+=seg
        transientmask=np.zeros(len(y),bool)
        for r in ownfits:
            if r['fit_id'] in unresolved:transientmask[r['start_index']:r['stop_index']]=True
        catalogue_mask=np.zeros(len(y),bool);unmatched_catalogue=[]
        for c in owncatalog:
            ct0,ct1=float(c['start_relative_s']),float(c['end_relative_s'])
            matched=[r for r in ownfits if ct0-10<=r['peak_time_s']<=ct1+10]
            if any(r['fit_id'] in accepted for r in matched):continue
            # Catalogue nominal times have not been proven identical to local ATT;
            # use explicit 10 s association tolerance and a 100 s response tail.
            cm=(t>=ct0-10)&(t<=max(ct1+10,ct0+100))
            catalogue_mask|=cm
            if not matched:unmatched_catalogue.append(c)
        transientmask|=catalogue_mask
        safe=(~edge)&(~short)&(~gapguard)&(~transientmask)&(~excluded)&(~gaps)
        # Start inside the long-record taper guard (about -474 s), rather than
        # mechanically failing every quiet record on an edge-contaminated window.
        noise=(t>=-450)&(t<=-50);signal=(t>=max(50,base['distance_km']/8))&(t<=1800)
        vals=raw[noise&~gaps];qr=float(np.ptp(np.percentile(vals,[5,95]))) if len(vals) else 0
        quant=len(np.unique(vals))<5 or qr<=1
        ownbands=[]
        def psd(window):
            spans=runs(window&safe&np.isfinite(resp))
            if not spans:return None
            a,b=max(spans,key=lambda p:p[1]-p[0])
            if (b-a)/fs<120:return None
            return welch(resp[a:b],fs=fs,nperseg=int(120*fs),detrend='linear')
        pn=psd(noise);ps=psd(signal)
        for lo,hi in BANDS:
            label=f'{lo:g}-{hi:g}';v=filt[label];valid=safe&np.isfinite(v)
            nf=float(valid[noise].mean());sf=float(valid[signal].mean())
            nn=v[noise&valid];ss=v[signal&valid]
            snr=float(np.sqrt(np.mean(ss**2))/np.sqrt(np.mean(nn**2))) if len(nn) and len(ss) and np.mean(nn**2)>0 else None
            frac=None
            if pn is not None and ps is not None:
                ff,pp=ps;fn,qq=pn;k=(ff>=lo)&(ff<=hi)
                frac=float(np.mean(pp[k]/np.maximum(np.interp(ff[k],fn,qq),1e-60)>=9))
            reasons=[]
            if quant:reasons.append('quantization_limited_noise')
            if nf<.95 or sf<.95:reasons.append('safe_window_coverage_below_95pct')
            if snr is None or snr<3:reasons.append('RMS_SNR_below_3_or_unavailable')
            if frac is None or frac<.6:reasons.append('PSD_support_below_60pct_or_unavailable')
            if meta['clock']['status']!='local_affine_ATT_corrected':reasons.append('unresolved_clock')
            br=dict(base,band_hz=label,rms_SNR=snr,PSD_fraction_ratio_ge9=frac,noise_safe_fraction=nf,signal_safe_fraction=sf,
                    noise_quantization_limited=quant,screen_pass=not reasons,reason=';'.join(reasons),formal_qualified=False)
            bands.append(br);ownbands.append(br)
        # Prespecified preference: common broad band, then narrow low band, then upper band.
        # High band remains diagnostic and is never selected just for a high SNR.
        passed=[b['band_hz'] for b in ownbands if b['screen_pass']]
        selected=next((k for k in ['0.3-0.9','0.3-0.5','0.5-0.9'] if k in passed),'0.3-0.5')
        selected_ok=selected in passed
        info=dict(base,status='processed_screen_pass_not_final' if selected_ok else 'processed_diagnostic_only',selected_band_hz=selected,
                  selected_band_screen_pass=selected_ok,pass_bands=';'.join(passed),spike_corrected_samples=int(spmask.sum()),
                  glitch_subtracted_count=len(accepted),glitch_unresolved_count=len(unresolved),glitch_ids_subtracted=accepted,
                  published_catalogue_rows=len(owncatalog),catalogue_unmatched_rows=len(unmatched_catalogue),
                  unresolved_transient_intervals=len(runs(transientmask)),
                  raw_gap_pct=float(100*gaps.mean()),rail_samples=int(rail.sum()),suspected_internal_clip_samples=int(internal.sum()),
                  excluded_pct=float(100*excluded.mean()),processing_edge_pct=float(100*edge.mean()),
                  short_segment_pct=float(100*short.mean()),temporary_gap_samples=int(temporary.sum()),
                  noise_quantization_limited=quant,noise_DU_p95_p05=qr,
                  noise_window_s=[-450,-50],signal_window_s=[max(50,base['distance_km']/8),1800],
                  selected_band_rms_SNR=next(b['rms_SNR'] for b in ownbands if b['band_hz']==selected),
                  S14_offset_correction='not_applied_table2_epochs_start_1973' if sta=='S14' else 'not_applicable',
                  ATT_offset_s=meta['clock']['offset_at_event_s'],ATT_residual_p99_s=meta['clock'].get('residual_p99_s'),
                  effective_fs_hz=fs,source_file=meta['source_file'],source_sha256=sha(src),stationxml_sha256=sha(invpath),
                  nominal_response_only=True,formal_qualified=False,
                  accepted_glitch_decisions={k:decisions[k] for k in accepted},
                  calibration_status='no_matching_command_in_Liu2025_published_table_within_event_window; not proof_of_no_calibration',
                  diagnostic_limit='Unresolved transients retained and flagged, not automatically deleted; no assurance of artifact-free data.')
        np.savez_compressed(OUT/f'{key}.npz',t_ATT_s=t,t_nominal_s=d['t_nominal_s'],raw_counts=raw,cleaned_counts=clean,
             original_gap_mask=gaps,spike_correction_mask=spmask,glitch_subtracted_counts=glcomponent,
             glitch_subtraction_window=glmask,unresolved_transient_mask=transientmask,published_unresolved_catalogue_mask=catalogue_mask,rail_mask=rail,
             suspected_internal_clip_mask=internal,artifact_exclusion_mask=excluded,processing_edge_mask=edge,
             short_segment_mask=short,temporary_gap_mask=temporary,temporary_gap_guard_mask=gapguard,
             screening_safe_mask=safe,velocity_response_m_s=resp,velocity_selected_m_s=filt[selected],
             **{f'velocity_{k.replace(".","p").replace("-","_")}_m_s':v for k,v in filt.items()},
             metadataJSON=np.array(json.dumps(info,ensure_ascii=False)))
        info['npz']=str((OUT/f'{key}.npz').relative_to(ROOT));records.append(info)
        # Verify exact reconstruction of all finite cleaned counts outside exclusions.
        expected=raw.copy()
        for q in splog:expected[q['index']]=q['corrected_DU']
        expected-=glcomponent
        valid=np.isfinite(clean)
        checks.append(dict(record=key,raw_exact_archive=True,source_hash_unchanged=True,
                           changes_exactly_logged=bool(np.array_equal(clean[valid],expected[valid])),
                           original_gaps_preserved=bool(np.isnan(filt[selected][gaps]).all()),
                           excluded_samples_nan=bool(np.isnan(filt[selected][excluded]).all()),
                           failed_segments=sum(s['status']=='failed' for s in seg)))
        print(key,selected,'screen',selected_ok,'spikes',int(spmask.sum()),'glitches',len(accepted),flush=True)
    writecsv(RES/'per_record_processing.csv',records);writecsv(RES/'per_record_band_screen.csv',bands)
    dump(RES/'segment_log.json',allsegments);dump(RES/'integrity_checks.json',checks)
    dump(RES/'per_record_processing.json',records)
    good=[r for r in records if r['status']!='missing_archive']
    summary=dict(date='2026-11-03',event_count=len(set(r['event_id'] for r in records)),pair_count=len(pairs),slots=len(records),
        actual_records=len(good),missing_records=[r['record'] for r in records if r['status']=='missing_archive'],
        corrected_spike_samples=sum(r['spike_corrected_samples'] for r in good),
        records_with_spike_correction=sum(r['spike_corrected_samples']>0 for r in good),
        subtracted_glitches=sum(r['glitch_subtracted_count'] for r in good),
        unresolved_transients=sum(r['glitch_unresolved_count'] for r in good),
        records_with_rails=sum(r['rail_samples']>0 for r in good),
        records_with_internal_clip_suspects=sum(r['suspected_internal_clip_samples']>0 for r in good),
        selected_band_screen_pass_records=sum(r['selected_band_screen_pass'] for r in good),
        diagnostic_only_records=sum(not r['selected_band_screen_pass'] for r in good),
        formal_inversion_qualified_records=0,integrity_all_pass=all(all(r[k] for k in ['raw_exact_archive','source_hash_unchanged','changes_exactly_logged','original_gaps_preserved','excluded_samples_nan']) and r['failed_segments']==0 for r in checks))
    dump(RES/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))

def strip(ax,t,mask,y,color):
    dt=np.median(np.diff(t));spans=[(t[a],(b-a)*dt) for a,b in runs(mask)]
    if spans:ax.broken_barh(spans,(y,.07),transform=ax.get_xaxis_transform(),color=color,lw=0,zorder=5)

def draw_row(axes,r,index,labels=False):
    rawax,cleanax,velax,noteax=axes
    for ax in [rawax,cleanax,velax]:
        ax.set_xlim(WINDOW);ax.set_xticks([0,1200,2400,3600]);ax.tick_params(labelsize=6,pad=1)
        ax.yaxis.set_major_locator(MaxNLocator(3));ax.grid(alpha=.15);ax.axvline(0,color='#888888',lw=.5,ls='--')
        ax.ticklabel_format(axis='y',style='plain',useOffset=False)
    rawax.set_ylabel(f"{r['event_id']}\n{r['station']} {r['channel']}\n{r['distance_km']:g} km",fontsize=7,labelpad=9)
    noteax.axis('off')
    if r['status']=='missing_archive':
        for ax in [rawax,cleanax,velax]:
            ax.text(.5,.5,'档案未返回：S14 MHZ 故障时段',ha='center',va='center',transform=ax.transAxes,fontsize=7,color='#666666');ax.set_yticks([])
        noteax.text(0,.8,'缺失记录：不填补、不替代\n原始／处理后均无观测波形',fontsize=8,va='top');return
    d=np.load(OUT/f"{r['record']}.npz");t=d['t_ATT_s'];raw=d['raw_counts'].copy();raw[d['original_gap_mask']]=np.nan
    clean=d['cleaned_counts'];v=d['velocity_selected_m_s']*1e9
    rawax.plot(t,raw,color='#293a48',lw=.35);cleanax.plot(t,clean,color='#176b73',lw=.35)
    finite=np.r_[raw[np.isfinite(raw)],clean[np.isfinite(clean)]];lo,hi=finite.min(),finite.max();pad=max(1,(hi-lo)*.08)
    rawax.set_ylim(lo-pad,hi+pad);cleanax.set_ylim(lo-pad,hi+pad)
    velax.plot(t,v,color='#166b80',lw=.35)
    ed=d['processing_edge_mask'];velax.plot(t,np.where(ed,v,np.nan),color='#c27d26',lw=.45)
    for ax in [rawax,cleanax,velax]:
        strip(ax,t,d['original_gap_mask'],.94,'#555555')
        strip(ax,t,d['artifact_exclusion_mask'],.86,'#ba483d')
        strip(ax,t,d['unresolved_transient_mask'],.78,'#9863ab')
        strip(ax,t,d['glitch_subtraction_window'],.70,'#187c68')
    sm=d['spike_correction_mask']
    if sm.any():cleanax.plot(t[sm],clean[sm],'o',ms=2,color='#ca7a11',mfc='none')
    sn=r['selected_band_rms_SNR'];sntext='不可算' if sn is None else f'{sn:.1f}'
    flag='通过初筛＊' if r['selected_band_screen_pass'] else '仅诊断，未通过初筛'
    text=(f"尖峰修正 {r['spike_corrected_samples']} 点；瞬变减除 {r['glitch_subtracted_count']} 处\n"
          f"待核瞬变 {r['unresolved_transient_intervals']} 段；量程端点 {r['rail_samples']} 点\n"
          f"疑似内部削顶 {r['suspected_internal_clip_samples']} 点；原缺样 {r['raw_gap_pct']:.2f}%\n"
          f"{r['selected_band_hz']} Hz；RMS SNR={sntext}；{flag}\n"
          f"{'噪声受量化限制；' if r['noise_quantization_limited'] else ''}ATT {r['ATT_offset_s']:+.2f} s；名义响应 [N22]\n"
          f"目录命中 {r['published_catalogue_rows']} 条 [L25]；{'S14 未套用偏移表' if r['station']=='S14' else '异常规则 [Z25]＋项目判据'}")
    noteax.text(0,.99,text,fontsize=7.4,va='top',linespacing=1.25)

def plot():
    rec=json.loads((RES/'per_record_processing.json').read_text(encoding='utf-8'))
    def render(rr,name,full=False):
        n=len(rr);fig,axs=plt.subplots(n,4,figsize=(23,1.15*n+2.7),squeeze=False,
              gridspec_kw={'width_ratios':[1.2,1.2,1.2,1.05]})
        fig.subplots_adjust(left=.075,right=.985,top=1-1.55/(1.15*n+2.7),bottom=.8/(1.15*n+2.7),hspace=.42,wspace=.24)
        fig.suptitle('Apollo 人工撞击记录｜逐事件、台站、分量的独立清洗与处理',fontsize=20,y=1-.15/(1.15*n+2.7))
        fig.text(.075,1-.7/(1.15*n+2.7),
          f"{len(set(r['event_id'] for r in rr))} 个事件 · {len(set((r['event_id'],r['station']) for r in rr))} 组事件—台站 · {n} 个分量槽位  |  原始与清洗 DU 使用相同纵轴；速度列独立纵轴；无归一化",fontsize=11)
        fig.text(.075,1-1.04/(1.15*n+2.7),
          '顶部标记：灰＝原始缺样；红＝饱和／疑似削顶排除；紫＝未决瞬变（保留）；绿＝已减除候选。橙色速度＝处理边缘。＊通过初筛仍不等于可直接反演。',fontsize=10)
        for ax,title in zip(axs[0],['① 原始数字计数 / DU','② 清洗后数字计数 / DU','③ 去响应＋逐条频带判断 / nm/s','④ 本条记录的处理与限制']):ax.set_title(title,fontsize=12,pad=14,loc='left')
        for i,(aa,r) in enumerate(zip(axs,rr)):draw_row(aa,r,i)
        for ax in axs[-1,:3]:ax.set_xlabel('相对地球接收撞击时刻 / s（ATT 校时）',fontsize=9)
        fig.text(.075,.2/(1.15*n+2.7),
          '[Z25] Zhang et al. (2025), 10.1029/2025EA004710；[L25] Liu et al. (2025), 10.1029/2025JE009277；[N22] Nunn et al. (2022), 10.3847/PSJ/ac87af。\n'
          '本图为可追溯的保守清洗结果；缺口未补造，名义增益未完全校准。全记录约 −600～3600 s；短于 60 s 的片段不做去响应。版本：2026-11-03。',fontsize=9)
        fig.savefig(FIG/f'{name}.png',dpi=150,facecolor='white')
        fig.savefig(FIG/f'{name}.pdf',facecolor='white');plt.close(fig)
    render(rec,'Apollo_全部原始与独立处理波形_总图',True)
    for eid in dict.fromkeys(r['event_id'] for r in rec):
        render([r for r in rec if r['event_id']==eid],f'{eid}_原始与独立处理')
    print('plotted full atlas and 9 event sheets',flush=True)

def tests():
    rng=np.random.default_rng(20261103);t=np.arange(10000)/6.625
    x=np.rint(512+2*np.sin(2*np.pi*.4*t)+rng.normal(0,.25,len(t)))
    corrupted=x.copy();idx=np.arange(100,9900,80);bits=rng.integers(5,10,len(idx))
    for i,b in zip(idx,bits):corrupted[i]=int(corrupted[i])^(1<<b)
    clean,mask,log=despike(corrupted,np.zeros(len(x),bool));clean0,mask0,_=despike(x,np.zeros(len(x),bool))
    sinus=np.rint(512+150*np.sin(2*np.pi*.7*t)*np.exp(-((t-600)/250)**2))
    _,mwave,_=despike(sinus,np.zeros(len(x),bool))
    report=dict(injected_spikes=len(idx),correctly_recovered=int(np.sum(clean[idx]==x[idx])),
                injected_changed=int(mask[idx].sum()),false_changes_outside_injected=int(np.sum(mask&~np.isin(np.arange(len(x)),idx))),
                uncorrupted_noise_false_changes=int(mask0.sum()),oscillatory_wave_false_changes=int(mwave.sum()),
                limitation='Synthetic sanity checks only; not a measured real-data precision or recall.')
    assert report['false_changes_outside_injected']==0 and report['uncorrupted_noise_false_changes']==0 and report['oscillatory_wave_false_changes']==0
    dump(RES/'synthetic_spike_checks.json',report);print(report)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['audit','refine','process','plot','tests']);a=p.parse_args()
    globals()[a.stage]()
