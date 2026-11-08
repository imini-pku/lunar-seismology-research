
from pathlib import Path
import sys,io,json,csv,hashlib,concurrent.futures,traceback
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.build/waveform_dependencies'))
import numpy as np,requests
from scipy.signal import butter,sosfiltfilt,welch
from obspy import read,read_inventory,UTCDateTime,Trace
RAW=ROOT/'data/raw/impact_modern';RAW.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'data/processed/impact_reference';OUT.mkdir(parents=True,exist_ok=True)
RES=ROOT/'results';RES.mkdir(exist_ok=True)
events={r['event_id']:r for r in csv.DictReader((RES/'impact_audit/events_and_domains.csv').open(encoding='utf-8-sig'))}
pairs=list(csv.DictReader((RES/'impact_pairs_literature.csv').open(encoding='utf-8-sig')))
INV=read_inventory(str(ROOT/'data/raw/impact_metadata/stationxml.xa.0.sxml'))
ENDPOINT='https://service.earthscope.org/fdsnws/dataselect/1/query'
bands=[(.1,.3),(.3,.5),(.5,.9),(.9,1.5)]
def runs(mask):
    d=np.diff(np.r_[False,mask,False].astype(int))
    return list(zip(np.where(d==1)[0],np.where(d==-1)[0]))
def download(pair):
    event=events[pair['event_id']];origin=UTCDateTime(event['time_earth_received'])
    path=RAW/(pair['event_id']+'_'+pair['station']+'_MP_ATT.mseed')
    params=dict(net='XA',sta=pair['station'],loc='*',cha='MH?,ATT',starttime=str(origin-600),endtime=str(origin+3600))
    record=dict(event_id=pair['event_id'],station=pair['station'],endpoint=ENDPOINT,params=params,file=str(path.relative_to(ROOT)))
    try:
        if not path.exists():
            s=requests.Session();s.trust_env=False;r=s.get(ENDPOINT,params=params,timeout=40)
            record['http_status']=r.status_code;record['url']=r.url;r.raise_for_status()
            if r.status_code!=200:raise RuntimeError('No data')
            path.write_bytes(r.content)
        data=path.read_bytes();st=read(io.BytesIO(data));record.update(status='downloaded',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),traces=len(st))
    except Exception as e:record.update(status='failed',error=str(e))
    return record
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
    downloads=list(ex.map(download,pairs))
(RES/'impact_modern_download_log.json').write_text(json.dumps(downloads,indent=2),encoding='utf-8')
rows=[];bandrows=[]
for pair,d in zip(pairs,downloads):
    eid=pair['event_id'];sta=pair['station'];origin=UTCDateTime(events[eid]['time_earth_received'])
    if d['status']!='downloaded':continue
    st=read(str(ROOT/d['file']))
    att=st.select(channel='ATT');clock=dict(status='missing_ATT',offset_at_event_s=None,slope=None,residual_p99_s=None)
    if len(att):
        tt=[];yy=[]
        for tr in att:
            x=float(tr.stats.starttime-origin)+np.arange(tr.stats.npts)*tr.stats.delta
            y=np.asarray(tr.data,dtype=float)-float(origin)
            good=np.isfinite(y)&(np.asarray(tr.data)!=-1)&(np.abs(y-x)<60)  # Pre-1970 Unix timestamps are legitimately negative.
            tt.extend(x[good]);yy.extend(y[good])
        x=np.asarray(tt);y=np.asarray(yy)
        if len(x)>100:
            coef=np.polyfit(x,y,1)
            for _ in range(3):
                er=y-np.polyval(coef,x);med=np.median(er);mad=np.median(np.abs(er-med));keep=np.abs(er-med)<max(.03,10*mad)
                coef=np.polyfit(x[keep],y[keep],1)
            er=y[keep]-np.polyval(coef,x[keep]);p99=float(np.quantile(abs(er),.99))
            clock=dict(status='local_affine_ATT_corrected' if p99<.05 else 'ATT_nonlinear_or_jumps_unresolved',offset_at_event_s=float(coef[1]),slope=float(coef[0]),residual_p99_s=p99,retained_fraction=float(keep.mean()),n_ATT=len(x))
    for channel in ['MHZ','MH1','MH2']:
        sel=st.select(channel=channel);fault=(sta=='S14' and channel=='MHZ' and origin>=UTCDateTime('1972-03-12') and origin<UTCDateTime('1976-11-17'))
        common=dict(event_id=eid,station=sta,channel=channel,nunn2024_clear=pair['nunn2024_clear'],published_supported_band='0.3-0.9 Hz general; 0.3-0.5 Hz comparison',qualified_band='',time_reference='NASA Earth-received origin; no lunar-light-time subtraction')
        if fault or not len(sel):
            common.update(status='known_bad_channel_epoch' if fault else 'no_trace_returned',npz='',reason='S14 MHZ excluded 1972-03-12 to 1976-11-17' if fault else 'not returned by FDSN')
            rows.append(common);continue
        ids=sorted(set(t.id for t in sel))
        if len(ids)!=1:
            common.update(status='multiple_locations_need_review',npz='',reason=';'.join(ids));rows.append(common);continue
        sel.merge(method=1,fill_value=None);tr=sel[0]
        raw=np.asarray(np.ma.filled(tr.data,-1),dtype=float);mask=(raw==-1)|~np.isfinite(raw)
        gaps=runs(mask);maxgap=max([b-a for a,b in gaps]+[0])*tr.stats.delta
        clipping=np.logical_and(~mask,np.logical_or(raw<=0,raw>=1023))
        clipping_max=max([b-a for a,b in runs(clipping)]+[0])
        t=float(tr.stats.starttime-origin)+np.arange(len(raw))*tr.stats.delta
        if clock['status']=='local_affine_ATT_corrected':t=clock['slope']*t+clock['offset_at_event_s']
        fs=1/np.median(np.diff(t))
        # Keep gaps as NaN in output; interpolation of <=2 samples only serves stable local response processing.
        smallfilled=raw.copy()
        for a,b in gaps:
            if b-a<=2 and a>0 and b<len(raw):smallfilled[a:b]=np.interp(np.arange(a,b),[a-1,b],[raw[a-1],raw[b]])
        remaining=(smallfilled==-1)|~np.isfinite(smallfilled)
        velocity=np.full(len(raw),np.nan)
        errors=[];response_segments=0
        for a,b in runs(~remaining):
            if b-a<fs*60:continue
            seg=Trace(data=smallfilled[a:b].astype(np.float64),header=dict(tr.stats))
            seg.stats.starttime=origin+float(t[a]);seg.stats.sampling_rate=6.625
            # Response stored for nominal 6.625 Hz; actual drift is small and retained in output t.
            try:
                seg.detrend('linear');seg.detrend('demean')
                seg.remove_response(inventory=INV,output='VEL',pre_filt=[.05,.1,1.5,2.0],water_level=None,zero_mean=True,taper=True,taper_fraction=.03)
                velocity[a:b]=seg.data;response_segments+=1
                edge=int(10*fs);velocity[a:min(a+edge,b)]=np.nan;velocity[max(a,b-edge):b]=np.nan
            except Exception as e:errors.append(str(e))
        velocity[mask]=np.nan
        noise=(t>=-500)&(t<=-50);sigstart=max(50,float(pair['distance_published_km'])/8.)
        signal=(t>=sigstart)&(t<=1800)
        validnoise=raw[noise&~mask]
        unique=len(np.unique(validnoise))
        quantile_range=float(np.ptp(np.percentile(validnoise,[5,95]))) if len(validnoise) else 0
        quantlimited=unique<5 or quantile_range<=1
        info=dict(common,source_file=d['file'],location=tr.stats.location,response='PDS nominal StationXML; gain-command history not fully reconstructed',input_units='raw DU',output_units='m/s nominally calibrated',prefilter_hz=[.05,.1,1.5,2.],clock=clock,original_delta_s=float(tr.stats.delta),effective_fs_hz=float(fs),gap_fraction=float(mask.mean()),max_gap_s=float(maxgap),rail_sample_count=int(clipping.sum()),max_rail_run_samples=int(clipping_max),noise_unique_DU=unique,noise_p95_p05_DU=quantile_range,noise_quantization_limited=quantlimited,noise_window_s=[-500,-50],signal_window_s=[sigstart,1800],response_segments=response_segments,response_errors=errors,limitation='Provisional spectral screen; nominal gain, local affine ATT correction, and whole-growth signal window; not certified late-coda band')
        fname=eid+'_'+sta+'_'+channel+'.npz'
        np.savez_compressed(OUT/fname,t=t,velocity_m_s=velocity,raw_counts=raw,original_gap_mask=mask,metadataJSON=np.array(json.dumps(info)))
        passed=[]
        for flo,fhi in bands:
            bandkey=f'{flo:g}-{fhi:g}'
            filtered=np.full(len(raw),np.nan)
            valid=np.isfinite(velocity)
            # Filter each uninterrupted span; omit an extra 10s at span edges.
            for a,b in runs(valid):
                if b-a<fs*60:continue
                try:
                    z=sosfiltfilt(butter(4,[flo,fhi],fs=fs,btype='bandpass',output='sos'),velocity[a:b])
                    filtered[a:b]=z
                    edge=int(10*fs);filtered[a:a+edge]=np.nan;filtered[b-edge:b]=np.nan
                except ValueError:pass
            nn=filtered[noise];ss=filtered[signal]
            nf=float(np.isfinite(nn).mean()) if len(nn) else 0;sf=float(np.isfinite(ss).mean()) if len(ss) else 0
            rmsn=float(np.sqrt(np.nanmean(nn**2))) if np.any(np.isfinite(nn)) else np.nan
            rmss=float(np.sqrt(np.nanmean(ss**2))) if np.any(np.isfinite(ss)) else np.nan
            ratio=rmss/rmsn if rmsn>0 else np.nan
            # Compare periodograms only on longest finite segment within each physical window.
            def longest_psd(window):
                runs0=runs(window&np.isfinite(velocity))
                if not runs0:return None,None
                a,b=max(runs0,key=lambda x:x[1]-x[0])
                if b-a<fs*120:return None,None
                return welch(velocity[a:b],fs=fs,nperseg=min(int(fs*120),b-a),detrend='linear')
            fn,pn=longest_psd(noise);ff,ps=longest_psd(signal)
            frac=np.nan
            if fn is not None and ff is not None:
                k=(ff>=flo)&(ff<=fhi)
                rat=ps[k]/np.maximum(np.interp(ff[k],fn,pn),1e-60)
                frac=float(np.mean(rat>=9))
            reasons=[]
            if clock['status']!='local_affine_ATT_corrected':reasons.append('ATT_clock_unresolved')
            if quantlimited:reasons.append('noise_quantization_limited')
            if nf<.95 or sf<.95:reasons.append('insufficient_gapfree_window')
            if clipping_max>=3:reasons.append('possible_clipping')
            if not np.isfinite(ratio) or ratio<3:reasons.append('RMS_SNR_below_3')
            if not np.isfinite(frac) or frac<.6:reasons.append('PSD_fraction_below_0.6')
            status='passes_provisional_screen' if not reasons else 'not_qualified_by_screen'
            if not reasons:passed.append(bandkey)
            bandrows.append(dict(event_id=eid,station=sta,channel=channel,location=tr.stats.location,band_hz=bandkey,published_supported_band=common['published_supported_band'],provisional_record_screen=status,qualified_band='',rms_signal_noise_ratio=ratio,PSD_fraction_power_ratio_ge9=frac,noise_finite_fraction=nf,signal_finite_fraction=sf,noise_quantization_limited=quantlimited,reason=';'.join(reasons),clock_status=clock['status'],nominal_gain_only=True,npz=str((OUT/fname).relative_to(ROOT))))
        common.update(status='nominal_response_corrected_provisional',npz=str((OUT/fname).relative_to(ROOT)),location=tr.stats.location,reason=';'.join(errors),provisional_pass_bands=';'.join(passed),gap_fraction=float(mask.mean()),max_gap_s=maxgap,clipping_run_samples=clipping_max,noise_quantization_limited=quantlimited,clock_status=clock['status'],ATT_offset_at_event_s=clock['offset_at_event_s'],ATT_residual_p99_s=clock['residual_p99_s'])
        rows.append(common)
    print(eid,sta,'processed',flush=True)
def writecsv(path,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
writecsv(RES/'impact_modern_trace_audit.csv',rows)
writecsv(RES/'impact_modern_band_screen.csv',bandrows)
summary=dict(downloaded_pairs=sum(d['status']=='downloaded' for d in downloads),failed_pairs=sum(d['status']!='downloaded' for d in downloads),trace_rows=len(rows),processed_trace_files=sum(bool(r.get('npz')) for r in rows),bad_or_missing=[r for r in rows if not r.get('npz')],band_rows=len(bandrows),provisional_pass_rows=sum(r['provisional_record_screen']=='passes_provisional_screen' for r in bandrows),qualified_band_count=0,qualification_note='Nominal gain only; quantitative gain reconstruction and manual QC remain. No final certified band claimed.')
summary['ATT_corrected_trace_count']=sum(r.get('clock_status')=='local_affine_ATT_corrected' for r in rows)
summary['ATT_unresolved_trace_count']=sum(bool(r.get('npz')) and r.get('clock_status')!='local_affine_ATT_corrected' for r in rows)
(RES/'impact_modern_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))

